"""Auth-context-derived principal + HTTP auth hook tests (07-16; D-IMPL-21/66a).

Two surfaces under test:

- ``ccf_runtime.identity_binding.principal_from_token_grant`` — the first
  D-IMPL-21 reference identity-binding implementation: the approver's
  ``subject_id`` comes from the *verified* ``TokenGrant``, never from a
  caller-typed parameter (T-07.1-05).
- ``ccf_runtime.http_api.auth`` — the minimal Protocol-based bearer hook
  over the D-26 ``TokenSourceProtocol`` machinery, optional at
  ``create_app`` (T-07.1-04); the unbound default remains the recorded
  T-07-24 posture.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

import json
from pathlib import Path
from typing import Any

from ccf.hitl.principal import HumanPrincipalBinding
from ccf_runtime.identity_binding import principal_from_token_grant
from ccf_runtime.http_api.app import CcfInsecureDefaultWarning
from ccf_runtime.mcp.auth import FileTokenSource, TokenGrant

from .conftest import Fabric, call

#: A syntactically valid lowercase sha256 hex digest (shape only — the
#: contract validator checks shape, not provenance).
_VALID_HASH = "a" * 64

_AWARE_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def _derive(**overrides: object) -> HumanPrincipalBinding:
    kwargs: dict[str, object] = {
        "grant": TokenGrant(client_id="alice", scopes=("hitl:act",)),
        "identity_provider_ref": "idp://acme-bank/dev-token-file",
        "method": "bearer-token",
        "assurance_level": "dev",
        "session_ref": "session-1",
        "action_time": _AWARE_TIME,
        "product_content_hash": _VALID_HASH,
    }
    kwargs.update(overrides)
    return principal_from_token_grant(**kwargs)  # type: ignore[arg-type]


class TestPrincipalFromTokenGrant:
    def test_a_subject_id_is_the_verified_client_id(self) -> None:
        binding = _derive()
        assert isinstance(binding, HumanPrincipalBinding)
        assert binding.approver.subject_id == "alice"
        assert (
            binding.approver.identity_provider_ref
            == "idp://acme-bank/dev-token-file"
        )
        assert binding.authentication.method == "bearer-token"
        assert binding.authentication.assurance_level == "dev"
        assert binding.authentication.session_ref == "session-1"
        assert binding.action_time == _AWARE_TIME
        assert binding.product_content_hash == _VALID_HASH

    def test_a_no_subject_id_parameter_exists(self) -> None:
        import inspect

        signature = inspect.signature(principal_from_token_grant)
        assert "subject_id" not in signature.parameters

    def test_b_malformed_hash_is_rejected_unlaundered(self) -> None:
        with pytest.raises(ValidationError):
            _derive(product_content_hash="not-a-hash")

    def test_b_naive_action_time_is_rejected_unlaundered(self) -> None:
        from ccf.contracts.canonical import CanonicalizationError, canonical_bytes

        with pytest.raises((ValidationError, CanonicalizationError)):
            binding = _derive(action_time=datetime(2026, 7, 30, 12, 0))
            # If contract construction admits the naive datetime, the
            # canonical serializer must refuse it (D-IMPL-38).
            canonical_bytes(binding)


# ---------------------------------------------------------------------------
# HTTP auth hook (Task 2): optional at create_app; unbound default unchanged.
# ---------------------------------------------------------------------------


def _deps(fabric: Fabric) -> Any:
    from ccf_runtime.http_api.dependencies import ApiDependencies

    return ApiDependencies(
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


@pytest.fixture(scope="module")
def authed_app(fabric: Fabric, token_file: Path) -> Any:
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.auth import BearerTokenAuth

    return create_app(
        _deps(fabric),
        auth=BearerTokenAuth(token_source=FileTokenSource(path=token_file)),
    )


class TestHookBound:
    def test_c_missing_header_is_401(self, authed_app: Any) -> None:
        assert call(authed_app, "POST", "/hitl/actions", json={}).status_code == 401
        assert call(authed_app, "GET", "/workflow/execution").status_code == 401

    def test_c_unrecognised_token_is_401(self, authed_app: Any) -> None:
        response = call(
            authed_app,
            "POST",
            "/hitl/actions",
            json={},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 401

    def test_c_non_bearer_scheme_is_401(self, authed_app: Any) -> None:
        response = call(
            authed_app,
            "POST",
            "/hitl/actions",
            json={},
            headers={"Authorization": "Basic recognised-token"},
        )
        assert response.status_code == 401

    def test_c_recognised_token_reaches_the_route(self, authed_app: Any) -> None:
        response = call(
            authed_app,
            "POST",
            "/hitl/actions",
            json={},
            headers={"Authorization": "Bearer recognised-token"},
        )
        # Auth passed; the empty payload fails route validation, not auth.
        assert response.status_code == 422

    def test_e_health_needs_no_token(self, authed_app: Any) -> None:
        response = call(authed_app, "GET", "/health")
        assert response.status_code == 200


class TestPosturePreserved:
    def test_d_no_hook_means_no_401_anywhere(self, fabric: Fabric) -> None:
        from ccf_runtime.http_api.app import create_app

        # The bare construction is the point here — the D-IMPL-73 warning
        # fires and documents the posture this test asserts is preserved.
        with pytest.warns(CcfInsecureDefaultWarning):
            app = create_app(_deps(fabric))
        assert call(app, "GET", "/health").status_code == 200
        # Authority-bearing route: reaches route validation, never 401.
        assert call(app, "POST", "/hitl/actions", json={}).status_code == 422
