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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf_runtime.mcp.auth import FileTokenSource, TokenGrant

from .conftest import Fabric, call

_VALID_HASH = "c" * 64
_AWARE_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)

_TOKEN = "hardening-token"
_CLIENT_ID = "hardening-auditor-1"
_TENANT = "auth-hardening-tenant"


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


class TestFailClosedGrantBranch:
    """Test 1: a non-TokenGrant grant object is refused, never fallen through."""

    def test_non_token_grant_object_is_refused_and_nothing_lands(
        self, fabric: Fabric
    ) -> None:
        from ccf_runtime.http_api.app import create_app
        from ccf_runtime.http_api.errors import ERROR_INVALID_GRANT

        tenant = f"{_TENANT}-impostor"
        app = create_app(_deps(fabric), auth=_ImpostorAuth())
        response = call(
            app,
            "POST",
            "/hitl/actions",
            json=_submission_body(subject_id="anyone-at-all", tenant=tenant),
            headers={"Authorization": f"Bearer {_TOKEN}"},
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
        self, fabric: Fabric, token_file: Path
    ) -> None:
        from ccf_runtime.http_api.app import create_app
        from ccf_runtime.http_api.auth import BearerTokenAuth
        from ccf_runtime.http_api.errors import ERROR_UNAUTHENTICATED

        app = create_app(
            _deps(fabric),
            auth=BearerTokenAuth(
                token_source=FileTokenSource(path=token_file)
            ),
        )
        response = call(app, "GET", "/hitl/queue?tenant=t")
        assert response.status_code == 401
        assert (
            response.json()["detail"]["error_code"] == ERROR_UNAUTHENTICATED
        )

    def test_subject_conflict_refusal_carries_its_code(
        self, fabric: Fabric, token_file: Path
    ) -> None:
        from ccf_runtime.http_api.app import create_app
        from ccf_runtime.http_api.auth import BearerTokenAuth
        from ccf_runtime.http_api.errors import ERROR_SUBJECT_CONFLICT

        tenant = f"{_TENANT}-conflict"
        app = create_app(
            _deps(fabric),
            auth=BearerTokenAuth(
                token_source=FileTokenSource(path=token_file)
            ),
        )
        response = call(
            app,
            "POST",
            "/hitl/actions",
            json=_submission_body(subject_id="someone-else", tenant=tenant),
            headers={"Authorization": f"Bearer {_TOKEN}"},
        )
        assert response.status_code == 403
        assert (
            response.json()["detail"]["error_code"] == ERROR_SUBJECT_CONFLICT
        )
        # The refusal never echoes the credential.
        assert _TOKEN not in response.text
        assert fabric.hitl.submissions(tenant=tenant) == ()

    def test_codes_are_distinct_and_signed_binding_codes_are_reserved(
        self,
    ) -> None:
        from ccf_runtime.http_api.errors import (
            ERROR_INVALID_GRANT,
            ERROR_SIGNED_BINDING_INVALID,
            ERROR_SIGNED_BINDING_REQUIRED,
            ERROR_SUBJECT_CONFLICT,
            ERROR_UNAUTHENTICATED,
        )

        codes = {
            ERROR_UNAUTHENTICATED,
            ERROR_SUBJECT_CONFLICT,
            ERROR_INVALID_GRANT,
            ERROR_SIGNED_BINDING_REQUIRED,
            ERROR_SIGNED_BINDING_INVALID,
        }
        assert len(codes) == 5
        assert all(isinstance(code, str) and code for code in codes)
