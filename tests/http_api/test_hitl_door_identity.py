"""HITL HTTP door identity composition (07-20; D-IMPL-67 items 1 and 3).

The 7.1 mechanisms exist separately: ``principal_from_token_grant`` derives
a binding whose subject is the *verified* ``TokenGrant.client_id`` (07-16),
and ``create_app``'s optional auth hook stashes the verified grant on
``request.state.token_grant``. D-IMPL-67 rules that the HITL action door
must *compose* them: with a hook bound, the audited submission's subject IS
the verified identity — a conflicting caller-typed subject is a typed 403
refusal that never touches the transport — and with no hook bound the
recorded T-07-24 posture is byte-for-byte unchanged.

Test values are deployment vocabulary chosen by this test-as-deployment,
following the ``tests/http_api/test_auth.py`` precedent.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf_runtime.mcp.auth import FileTokenSource

from .conftest import Fabric, call

#: A syntactically valid lowercase sha256 hex digest (shape only).
_VALID_HASH = "b" * 64

_AWARE_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)

#: The one credential this test deployment recognises, and the identity it
#: verifies to. Test values, meaningful nowhere else.
_TOKEN = "door-token"
_CLIENT_ID = "auditor-1"

_TENANT = "identity-door-tenant"


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


def _submission_body(*, subject_id: str, tenant: str = _TENANT) -> dict[str, Any]:
    return {
        "event_key": "door-event-1",
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
                "session_ref": "door-session-1",
            },
            "action_time": _AWARE_TIME.isoformat(),
            "product_content_hash": _VALID_HASH,
        },
        "annotation": None,
    }


@pytest.fixture(scope="module")
def token_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("hitl-door-auth") / "tokens.json"
    path.write_text(
        json.dumps({_TOKEN: {"client_id": _CLIENT_ID, "scopes": ["hitl"]}}),
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


class TestConflictRefusal:
    """Test A: a conflicting body subject is a typed 403, transport untouched."""

    def test_a_conflicting_subject_is_403_and_nothing_lands(
        self, authed_app: Any, fabric: Fabric
    ) -> None:
        tenant = f"{_TENANT}-conflict"
        response = call(
            authed_app,
            "POST",
            "/hitl/actions",
            json=_submission_body(subject_id="someone-else", tenant=tenant),
            headers={"Authorization": f"Bearer {_TOKEN}"},
        )
        assert response.status_code == 403
        # The refusal names an identity conflict without echoing the token.
        assert "identity" in response.text.lower()
        assert _TOKEN not in response.text
        # Nothing was enqueued or recorded on the refused path.
        assert fabric.hitl.submissions(tenant=tenant) == ()


class TestDerivation:
    """Test B: the accepted submission's subject IS the verified client_id."""

    def test_b_accepted_subject_is_derived_from_the_grant(
        self, authed_app: Any, fabric: Fabric
    ) -> None:
        tenant = f"{_TENANT}-derive"
        body = _submission_body(subject_id=_CLIENT_ID, tenant=tenant)
        response = call(
            authed_app,
            "POST",
            "/hitl/actions",
            json=body,
            headers={"Authorization": f"Bearer {_TOKEN}"},
        )
        assert response.status_code == 200
        receipt = response.json()
        assert receipt["status"] == "submitted"
        assert (
            receipt["submission"]["principal"]["approver"]["subject_id"]
            == _CLIENT_ID
        )
        (recorded,) = fabric.hitl.submissions(tenant=tenant)
        principal = recorded.principal
        assert principal.approver.subject_id == _CLIENT_ID
        # Everything else the body stated travels verbatim.
        assert (
            principal.approver.identity_provider_ref
            == body["principal"]["approver"]["identity_provider_ref"]
        )
        assert (
            principal.authentication.method
            == body["principal"]["authentication"]["method"]
        )
        assert (
            principal.authentication.assurance_level
            == body["principal"]["authentication"]["assurance_level"]
        )
        assert (
            principal.authentication.session_ref
            == body["principal"]["authentication"]["session_ref"]
        )
        assert principal.action_time == _AWARE_TIME
        assert principal.product_content_hash == _VALID_HASH


class TestUnboundPostureUnchanged:
    """Test C: with no hook bound, the T-07-24 posture stands unchanged."""

    def test_c_unbound_door_accepts_an_arbitrary_subject(
        self, fabric: Fabric
    ) -> None:
        from ccf_runtime.http_api.app import create_app

        tenant = f"{_TENANT}-unbound"
        app = create_app(_deps(fabric))
        response = call(
            app,
            "POST",
            "/hitl/actions",
            json=_submission_body(subject_id="anyone-at-all", tenant=tenant),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "submitted"
        (recorded,) = fabric.hitl.submissions(tenant=tenant)
        assert recorded.principal.approver.subject_id == "anyone-at-all"
