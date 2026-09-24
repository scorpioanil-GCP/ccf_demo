"""R1 was-called derivation assertions (08-03 Task 3; 07-REVIEWS R1).

The R1 finding (Cursor, LOW): the HTTP happy-path proved *subject
equality*, not the derivation call — a regression that kept the 403
conflict check but passed the caller's body principal through on match
(skipping ``principal_from_token_grant``) would still have passed every
prior test; the MCP door's guard was similarly weak
(``inspect.getsource`` contains the name). These tests close R1 with
monkeypatch **wrapping** of the derivation (wrap, don't replace — the
real derivation still runs, so downstream contract assertions hold) and
call-count assertions on both named seams:

* the HTTP door (``ccf_runtime.http_api.routes.hitl``) — derivation IS
  invoked on the auth-bound path, and its return value IS the recorded
  principal (identity, not mere equality);
* the MCP door (``ccf_runtime.mcp.hitl_server``) — same assertion for
  the D-IMPL-20 primary authority channel.

And the negative guard: on the unauthenticated posture the derivation is
not called at all — no accidental derivation from a ``None`` grant.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf_runtime.mcp.auth import FileTokenSource

from http_api.conftest import Fabric, call

_VALID_HASH = "c" * 64
_AWARE_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
_TOKEN = "derivation-token"
#: The tenant the MCP leg acts on. One spelling, so the credential's scope
#: and the tool argument cannot drift apart (`SEC-018`).
_MCP_TENANT = "was-called-mcp-tenant"

_CLIENT_ID = "derivation-auditor-1"


def _submission_body(*, subject_id: str, tenant: str) -> dict[str, Any]:
    return {
        "event_key": "derivation-event-1",
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
                "session_ref": "derivation-session-1",
            },
            "action_time": _AWARE_TIME.isoformat(),
            "product_content_hash": _VALID_HASH,
        },
        "annotation": None,
    }


@pytest.fixture(scope="module")
def fabric(tmp_path_factory: pytest.TempPathFactory) -> Fabric:
    return Fabric(tmp_path_factory.mktemp("was-called"))


@pytest.fixture(scope="module")
def token_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("was-called-auth") / "tokens.json"
    path.write_text(
        json.dumps(
            {_TOKEN: {"client_id": _CLIENT_ID, "scopes": ["hitl"]}}
        ),
        encoding="utf-8",
    )
    return path


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


class _WrapCounter:
    """Wrap-and-count spy: the real derivation still runs (R1 discipline)."""

    def __init__(self, real: Any) -> None:
        self._real = real
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []
        self.returns: list[Any] = []

    def __call__(self, **kwargs: Any) -> Any:
        self.call_count += 1
        self.calls.append(kwargs)
        result = self._real(**kwargs)
        self.returns.append(result)
        return result


# --- Test 1: auth-bound HTTP path actually derives --------------------------


def test_http_auth_bound_path_invokes_the_derivation(
    fabric: Fabric, token_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ccf_runtime.http_api.routes.hitl as hitl_routes
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.auth import BearerTokenAuth

    spy = _WrapCounter(hitl_routes.principal_from_token_grant)
    monkeypatch.setattr(
        hitl_routes, "principal_from_token_grant", spy
    )
    app = create_app(
        _deps(fabric),
        auth=BearerTokenAuth(token_source=FileTokenSource(path=token_file)),
    )
    tenant = "was-called-auth-tenant"
    response = call(
        app,
        "POST",
        "/hitl/actions",
        json=_submission_body(subject_id=_CLIENT_ID, tenant=tenant),
        headers={"Authorization": f"Bearer {_TOKEN}"},
    )
    assert response.status_code == 200
    # The derivation WAS called — with the verified grant, exactly once.
    assert spy.call_count == 1
    assert spy.calls[0]["grant"].client_id == _CLIENT_ID
    # The recorded principal IS the derivation's return value — object
    # identity, not a value that merely equals it (the R1 regression a
    # pass-through-on-match would have hidden).
    (recorded,) = fabric.hitl.submissions(tenant=tenant)
    assert recorded.principal is spy.returns[0]


# --- Test 2: unauthenticated posture never derives --------------------------


def test_http_unauthenticated_posture_does_not_derive(
    fabric: Fabric, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No auth hook bound (T-07-24 posture): no derivation from no grant."""
    import ccf_runtime.http_api.routes.hitl as hitl_routes
    from ccf_runtime.http_api.app import create_app

    spy = _WrapCounter(hitl_routes.principal_from_token_grant)
    monkeypatch.setattr(
        hitl_routes, "principal_from_token_grant", spy
    )
    app = create_app(_deps(fabric), acknowledge_insecure_default=True)
    tenant = "was-called-unauth-tenant"
    response = call(
        app,
        "POST",
        "/hitl/actions",
        json=_submission_body(subject_id="as-sent-subject", tenant=tenant),
    )
    assert response.status_code == 200
    assert spy.call_count == 0
    # The submission travels exactly as sent on the recorded posture.
    (recorded,) = fabric.hitl.submissions(tenant=tenant)
    assert recorded.principal.approver.subject_id == "as-sent-subject"


# --- Test 3: the MCP door's derivation seam (R1 names it too) ---------------


def test_mcp_door_invokes_the_derivation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mcp.server.auth.provider import AccessToken
    from mcp.server.auth.settings import AuthSettings
    from pydantic import AnyHttpUrl

    import ccf_runtime.mcp.hitl_server as hitl_server
    from ccf.hitl.transport import HitlActionSubmission, PendingHitlEvent
    from ccf_runtime.mcp.auth import SourceBackedTokenVerifier
    from ccf_runtime.mcp.hitl_server import (
        SUBMIT_HITL_ACTION_TOOL,
        build_hitl_server,
    )

    spy = _WrapCounter(hitl_server.principal_from_token_grant)
    monkeypatch.setattr(
        hitl_server, "principal_from_token_grant", spy
    )
    token_file = tmp_path / "tokens.json"
    token_file.write_text(
        json.dumps(
            {"unit-token": {"client_id": _CLIENT_ID, "scopes": ["h"]}}
        ),
        encoding="utf-8",
    )
    routed: list[HitlActionSubmission] = []

    def action_route(*, submission: HitlActionSubmission) -> str:
        routed.append(submission)
        return "{}"

    def queue_view(*, tenant: str) -> tuple[PendingHitlEvent, ...]:
        return ()

    server = build_hitl_server(
        server_name="was-called-hitl",
        queue_view=queue_view,
        action_route=action_route,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=token_file)
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://unit.invalid/mcp"),
            required_scopes=["h"],
        ),
    )
    # BOTH readers of the verified identity: the door, for its subject
    # binding, and `ccf_runtime.mcp.tenancy`, for the tenancy floor installed
    # at registration. Each imported the name into its own namespace, so one
    # patch leaves the other reading the real (empty) context (`SEC-018`).
    import ccf_runtime.mcp.tenancy as tenancy

    from ccf_runtime.mcp.auth import TokenGrant, tenant_claims

    _token = AccessToken(
        token="unit-token",
        client_id=_CLIENT_ID,
        scopes=["h"],
        claims=dict(
            tenant_claims(
                TokenGrant(
                    client_id=_CLIENT_ID,
                    scopes=("h",),
                    tenants=frozenset({_MCP_TENANT}),
                )
            )
        ),
    )
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: _token)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: _token)
    tool = server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn
    tool(
        tenant=_MCP_TENANT,
        event_key="derivation-event-1",
        action="approve",
        subject_id=_CLIENT_ID,
        identity_provider_ref="idp://acme-bank/dev-token-file",
        method="bearer-token",
        assurance_level="dev",
        session_ref="derivation-session-1",
        action_time=_AWARE_TIME.isoformat(),
        product_content_hash=_VALID_HASH,
    )
    assert spy.call_count == 1
    assert spy.calls[0]["grant"].client_id == _CLIENT_ID
    (submission,) = routed
    assert submission.principal is spy.returns[0]
