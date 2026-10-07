"""HTTP door hardening (08-02 Task 2; 07-REVIEWS rounds 2-3 findings).

Two findings close here, TDD:

**Codex fail-closed.** The route gated hardened behavior on
``isinstance(grant, TokenGrant)`` and *fell through* to the caller-supplied
principal when the stashed object was anything else. The invariant must
fail closed: a non-``TokenGrant`` object at the door is a typed refusal —
the caller principal is NEVER used, and nothing lands on the transport.

**Ollama MEDIUM.** Refusal responses carry a machine-readable
``error_code`` field whose values are named constants exported from
``ccf_runtime.http_api.errors``; no test or client parses refusal prose.
``ERROR_SIGNED_BINDING_REQUIRED`` / ``ERROR_SIGNED_BINDING_INVALID`` are
exported now, reserved for 08-03's door mapping, so later plans never
invent strings.

Test values are deployment vocabulary chosen by this test-as-deployment,
following the ``tests/http_api/test_auth.py`` precedent.
"""

from __future__ import annotations

import json
from tests.composition import declared_erasure_trust, no_erasures
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf_runtime.mcp.auth import FileTokenSource, TokenGrant

from .conftest import Fabric, call
from .gate_fixtures import probe

_VALID_HASH = "c" * 64
_AWARE_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)

_TOKEN = "hardening-token"
_CLIENT_ID = "hardening-auditor-1"
_TENANT = "auth-hardening-tenant"


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


def _submission_body(*, subject_id: str, tenant: str) -> dict[str, Any]:
    return {
        "event_key": "hardening-event-1",
        "tenant": tenant,
        "action": "approve",
        "principal": {
            "approver": {
                "subject_id": subject_id,
                "identity_provider_ref": "idp://acme-bank/dev-token-file",
            },
            "authentication": {
                "method": "bearer-token",
                "assurance_level": "dev",
                "session_ref": "hardening-session-1",
            },
            "action_time": _AWARE_TIME.isoformat(),
            "product_content_hash": _VALID_HASH,
        },
        "annotation": None,
    }


class _ImpostorGrant:
    """Compatible-but-not-identical grant object (the Codex scenario).

    Duck-types ``TokenGrant``'s surface without being one — exactly the
    future-auth-hook shape the fail-closed branch must refuse.
    """

    client_id = _CLIENT_ID
    scopes = ("hitl",)


class _ImpostorAuth:
    """Auth hook returning a non-``TokenGrant`` object for any request."""

    def grant_for_request(
        self, *, authorization_header: str | None
    ) -> Any:
        return _ImpostorGrant()


@pytest.fixture(scope="module")
def token_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("auth-hardening") / "tokens.json"
    path.write_text(
        json.dumps({_TOKEN: {"client_id": _CLIENT_ID, "scopes": ["hitl"]}}),
        encoding="utf-8",
    )
    return path


#: The tenants this suite keeps its tests apart with, one credential each
#: (``SEC-002``: a credential names exactly one tenant).
_SUFFIXES = ("impostor", "conflict", "unauth")
_TOKENS = {
    f"{_TOKEN}-{suffix}": (
        _CLIENT_ID,
        ("gate:everything",),
        f"{_TENANT}-{suffix}",
    )
    for suffix in _SUFFIXES
}


def _seams(fabric: Fabric, root: Path, **overrides: Any) -> dict[str, Any]:
    """Everything ``create_app`` requires, with this suite's credentials."""
    from datetime import UTC, datetime

    from ccf.projection.plan import Perspective
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )

    from .gate_fixtures import authority
    from .test_product_declared_obligation_409 import (
        _entitlement_registry,
        _recorder,
    )

    source = ControlPlaneProductEntitlementSource(
        control_plane=_entitlement_registry(fabric),
        clock=lambda: datetime(2026, 8, 11, tzinfo=UTC),
    )
    seams = authority(
        tenant=tuple(f"{_TENANT}-{suffix}" for suffix in _SUFFIXES),
        key="auth-hardening/mapping",
        grants=_TOKENS,
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role="auth-hardening-role"
            )
        ),
        refusal_recorder=_recorder(fabric, root, source=source),
    )
    seams.update(overrides)
    return seams


class TestFailClosedGrantBranch:
    """Test 1: a non-TokenGrant grant object is refused, never fallen through."""

    def test_non_token_grant_object_is_refused_and_nothing_lands(
        self, fabric: Fabric, tmp_path: Path
    ) -> None:
        from ccf_runtime.http_api.app import create_app
        from ccf_runtime.http_api.errors import ERROR_INVALID_GRANT

        tenant = f"{_TENANT}-impostor"
        app = create_app(
            _deps(fabric),
            **_seams(fabric, tmp_path, auth=_ImpostorAuth()),
        )
        response = call(
            app,
            "POST",
            "/hitl/actions",
            json=_submission_body(subject_id="anyone-at-all", tenant=tenant),
            headers={"Authorization": f"Bearer {_TOKEN}-impostor"},
        )
        # Refused — the caller-supplied principal is NEVER used.
        assert response.status_code == 403
        assert response.json()["detail"]["error_code"] == ERROR_INVALID_GRANT
        # No HITL action was recorded on the refused path.
        assert fabric.hitl.submissions(tenant=tenant) == ()

    def test_impostor_is_not_a_token_grant(self) -> None:
        # The scenario is real: the impostor duck-types but is not the type.
        assert not isinstance(_ImpostorGrant(), TokenGrant)


class TestTypedErrorCodes:
    """Test 2: each refusal carries a distinct constant-valued error_code."""

    def test_unauthenticated_refusal_carries_its_code(
        self, fabric: Fabric, tmp_path: Path
    ) -> None:
        from ccf_runtime.http_api.app import create_app
        from ccf_runtime.http_api.auth import BearerTokenAuth
        from ccf_runtime.http_api.errors import ERROR_UNAUTHENTICATED

        app = create_app(_deps(fabric), **_seams(fabric, tmp_path))
        # `SEC-002` deleted the `?tenant=` parameter; the credential names the
        # tenant. What this leg is about is unchanged: no credential, 401, and
        # the typed code rather than prose.
        response = probe(app, "GET", "/hitl/queue")
        assert response.status_code == 401
        assert (
            response.json()["detail"]["error_code"] == ERROR_UNAUTHENTICATED
        )

    def test_a_caller_typed_subject_is_unrepresentable_at_the_body(
        self, fabric: Fabric, tmp_path: Path
    ) -> None:
        """D-IMPL-353 §2 P6 superseded the subject-conflict refusal: the body
        (:class:`ccf.hitl.transport.HitlActionRequest`) carries no
        ``principal`` at all, so a caller naming a subject is refused as a
        malformed body that names the field — there is no value that reaches
        a comparison, and nothing lands."""
        from ccf_runtime.http_api.app import create_app

        tenant = f"{_TENANT}-conflict"
        app = create_app(_deps(fabric), **_seams(fabric, tmp_path))
        response = call(
            app,
            "POST",
            "/hitl/actions",
            json=_submission_body(subject_id="someone-else", tenant=tenant),
            headers={"Authorization": f"Bearer {_TOKEN}-conflict"},
        )
        assert response.status_code == 422
        assert "principal" in response.text
        # The refusal never echoes the credential.
        assert _TOKEN not in response.text
        assert fabric.hitl.submissions(tenant=tenant) == ()

    def test_codes_are_distinct_and_signed_binding_codes_are_reserved(
        self,
    ) -> None:
        from ccf_runtime.http_api.errors import (
            ERROR_APPROVER_NOT_ELIGIBLE,
            ERROR_HITL_EVENT_REVALIDATION_REFUSED,
            ERROR_INVALID_GRANT,
            ERROR_SIGNED_BINDING_INVALID,
            ERROR_SIGNED_BINDING_MISMATCH,
            ERROR_SIGNED_BINDING_REQUIRED,
            ERROR_SIGNED_BINDING_STALE,
            ERROR_SUBJECT_CONFLICT,
            ERROR_UNAUTHENTICATED,
        )

        # Extended BY HAND under `D-IMPL-363` C4(a) / E6, and again under
        # `D-IMPL-366` (SEC-006) — this set is built from an import list and
        # cannot self-redden when a code is added.
        codes = {
            ERROR_UNAUTHENTICATED,
            ERROR_SUBJECT_CONFLICT,
            ERROR_INVALID_GRANT,
            ERROR_SIGNED_BINDING_REQUIRED,
            ERROR_SIGNED_BINDING_INVALID,
            ERROR_SIGNED_BINDING_MISMATCH,
            ERROR_SIGNED_BINDING_STALE,
            ERROR_APPROVER_NOT_ELIGIBLE,
            ERROR_HITL_EVENT_REVALIDATION_REFUSED,
        }
        assert len(codes) == 9
        assert ERROR_SIGNED_BINDING_MISMATCH == "signed-binding-mismatch"
        assert ERROR_SIGNED_BINDING_STALE == "signed-binding-stale"
        # SEC-006 (D-IMPL-366 G3 (a)): distinct from the signed-binding family.
        assert ERROR_APPROVER_NOT_ELIGIBLE == "approver-not-eligible"
        assert ERROR_HITL_EVENT_REVALIDATION_REFUSED == "hitl-event-revalidation-refused"
        assert all(isinstance(code, str) and code for code in codes)
