"""Auth-context-derived principal + HTTP auth hook tests (07-16; D-IMPL-21/66a).

Two surfaces under test:

- (``principal_from_token_grant`` was tested here until D-IMPL-353 §2 P6
  made the subject conflict unrepresentable: the door mints the binding from
  the capability's principal and the verified credential's claims —
  ``tests/http_api/test_hitl_door_identity.py`` holds that surface now.)
- ``ccf_runtime.http_api.auth`` — the minimal Protocol-based bearer hook
  over the D-26 ``TokenSourceProtocol`` machinery. **No longer optional at**
  ``create_app`` (``SEC-001``, superseding T-07.1-04 and the T-07-24 unbound
  posture): the hook is a required argument and the gate in front of the app
  has no arm that skips it. ``TestPostureIsGone`` is what the old
  ``TestPosturePreserved`` became.
"""

from __future__ import annotations

from tests.composition import declared_erasure_trust, no_erasures
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

import json
from pathlib import Path
from typing import Any

from ccf.hitl.principal import HumanPrincipalBinding
from ccf_runtime.mcp.auth import FileTokenSource, TokenGrant

from .conftest import Fabric, call
from .gate_fixtures import GateApp, probe

#: A syntactically valid lowercase sha256 hex digest (shape only — the
#: contract validator checks shape, not provenance).
_VALID_HASH = "a" * 64

_AWARE_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# HTTP auth hook (Task 2): optional at create_app; unbound default unchanged.
# ---------------------------------------------------------------------------


def _deps(fabric: Fabric) -> Any:
    from ccf_runtime.http_api.dependencies import ApiDependencies

    return ApiDependencies(erasure_index=no_erasures(), erasure_trust=declared_erasure_trust(), 
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
        workflow_factory=fabric.factory,
        workflow_engine=fabric.engine,
        hitl_transport=fabric.hitl,
        skill_catalog=fabric.catalog,
        grant_ledger=fabric.ledger,
    )


@pytest.fixture(scope="module")
def token_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("http-auth") / "tokens.json"
    path.write_text(
        json.dumps(
            {"recognised-token": {"client_id": "alice", "scopes": ["hitl"]}}
        ),
        encoding="utf-8",
    )
    return path


class TestHookBound:
    """Recognition, on the one app there is. Probed with no default header.

    ``probe`` rather than ``call``: ``call`` supplies a credential so route
    tests stay about routes, and evidence about *recognition* taken through a
    helper that supplies a credential would be evidence about the helper.
    """

    def test_c_missing_header_is_401(self, gate_app: GateApp) -> None:
        assert (
            probe(gate_app.app, "POST", "/hitl/actions", json={}).status_code
            == 401
        )
        assert (
            probe(gate_app.app, "GET", "/workflow/execution").status_code
            == 401
        )

    def test_c_unrecognised_token_is_401(self, gate_app: GateApp) -> None:
        response = probe(
            gate_app.app,
            "POST",
            "/hitl/actions",
            json={},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 401

    def test_c_non_bearer_scheme_is_401(self, gate_app: GateApp) -> None:
        response = probe(
            gate_app.app,
            "POST",
            "/hitl/actions",
            json={},
            headers={"Authorization": f"Basic {gate_app.token_everything}"},
        )
        assert response.status_code == 401

    def test_c_recognised_token_reaches_the_route(
        self, gate_app: GateApp
    ) -> None:
        """Recognition passes; the empty payload then fails validation.

        The body has to carry the field the route **declared** as its
        authorization resource — ``event_key`` — because the gate decides
        before validation and a body with no resource in it is a deny, not a
        422. The empty-body leg below is the other half of that pair, and it
        is the more interesting one: an unauthorized caller learns nothing
        about the route's schema, because the schema is never consulted.
        """
        response = probe(
            gate_app.app,
            "POST",
            "/hitl/actions",
            json={"event_key": "authz-probe-event"},
            headers=gate_app.auth(),
        )
        assert response.status_code == 422

    def test_c_a_body_with_no_declared_resource_is_denied_not_validated(
        self, gate_app: GateApp
    ) -> None:
        """A caller's choice of body leads to the check running, never past it.

        What would fail here: the gate skipping its resource read when the
        field is absent and falling through to the handler. That is the
        applicability-switch shape — the caller omits a field and the check
        does not happen.
        """
        response = probe(
            gate_app.app,
            "POST",
            "/hitl/actions",
            json={},
            headers=gate_app.auth(),
        )
        assert response.status_code == 403

    def test_e_health_needs_a_token_too(self, gate_app: GateApp) -> None:
        """The carve-out that used to exist, asserted as gone (``SEC-001``).

        This test previously read ``test_e_health_needs_no_token`` and
        asserted 200 with no credential. Liveness is now an action like any
        other: a path-based exemption is a branch whose condition is the
        caller's path, and the operational cost — a probe carries a
        credential — is paid in the deployment's scope mapping where it can
        be read.
        """
        assert probe(gate_app.app, "GET", "/health").status_code == 401
        assert (
            probe(
                gate_app.app, "GET", "/health", headers=gate_app.auth()
            ).status_code
            == 200
        )


class TestPostureIsGone:
    def test_d_there_is_no_hookless_application_to_build(
        self, fabric: Fabric
    ) -> None:
        """What ``test_d_no_hook_means_no_401_anywhere`` became.

        It used to build ``create_app(deps)`` bare and assert that ``GET
        /health`` answered 200 and ``POST /hitl/actions`` reached body
        validation — the T-07-24 posture, preserved on purpose. There is no
        such application now, and the ``TypeError`` is the whole assertion.
        """
        from ccf_runtime.http_api.app import create_app

        with pytest.raises(TypeError):
            create_app(_deps(fabric))  # type: ignore[call-arg]

    def test_an_authority_bearing_route_is_never_reachable_unauthenticated(
        self, gate_app: GateApp
    ) -> None:
        assert (
            probe(gate_app.app, "POST", "/hitl/actions", json={}).status_code
            == 401
        )


class TestTheBearerHookItself:
    """The hook in isolation: what it recognises, over a real token file."""

    @pytest.mark.parametrize(
        ("header", "expected"),
        [
            (None, None),
            ("", None),
            ("Bearer ", None),
            ("Basic recognised-token", None),
            ("Bearer wrong", None),
            ("Bearer recognised-token", "alice"),
            # RFC 9110 §11.1: the scheme comparison is case-insensitive.
            ("bEaReR recognised-token", "alice"),
        ],
    )
    def test_recognition(
        self, token_file: Path, header: str | None, expected: str | None
    ) -> None:
        from ccf_runtime.http_api.auth import BearerTokenAuth

        hook = BearerTokenAuth(token_source=FileTokenSource(path=token_file))
        grant = hook.grant_for_request(authorization_header=header)
        assert (grant.client_id if grant is not None else None) == expected
