"""MCP-door tenant authorization — the HARD-04 matrix legs (10-03 T2).

TDD RED for plan 10-03 Task 2. ``build_hitl_server`` gains an optional
``authorizer`` (D-IMPL-68; D-06): when bound, the queue *resource* guards
``hitl.queue.read`` with the URI tenant segment via the A1-verified
mechanism (``get_access_token()`` inside the resource handler — spike
verdict in ``test_fastmcp_resource_token_spike.py``), and the action
*tool* guards ``hitl.action.submit`` with its ``tenant`` parameter after
the existing identity verification. A deny is protocol-native rendering
of the SAME shared constant the HTTP door uses (D-08):
``ValueError(json.dumps(refusal_detail(ERROR_TENANT_UNAUTHORIZED, ...)))``
— and a refused submit never touches the deployment's action route.

The direct-handler legs monkeypatch ``get_access_token`` exactly as
``tests/http_api/test_signed_binding_door.py`` does; the over-the-wire
legs drive the server's own streamable-HTTP ASGI app with a real bearer
token per the A1 spike harness. The cross-door consistency leg exercises
the *same* scope-mapping artifact and grant through the HTTP handlers and
the MCP handlers and asserts identical outcomes per (grant, tenant,
action_id) — the door-agnostic property D-02 buys.

Every scope string, tenant name, and token value is test deployment
vocabulary (CINV-01).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.shared.exceptions import McpError
from mcp.types import TextResourceContents
from pydantic import AnyHttpUrl, AnyUrl

from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.transport import (
    HitlActionSubmission,
    InMemoryHitlTransport,
    PendingHitlEvent,
)
from ccf.mcp.client import run_with_session
from ccf_runtime.authz.artifact import (
    SCOPE_MAPPING,
    ScopeEntry,
    ScopeMappingArtifact,
)
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.authz.refusals import (
    ACTION_HITL_ACTION_SUBMIT,
    ACTION_HITL_QUEUE_READ,
)
from ccf_runtime.http_api.errors import ERROR_TENANT_UNAUTHORIZED
from ccf_runtime.mcp.auth import (
    FileTokenSource,
    SourceBackedTokenVerifier,
    TokenGrant,
)
from ccf_runtime.mcp.hitl_server import (
    HITL_QUEUE_URI_TEMPLATE,
    SUBMIT_HITL_ACTION_TOOL,
    build_hitl_server,
    hitl_queue_uri,
)

MAPPING_KEY = "authz-mcp/scope-mapping"
SCOPE_EXACT = "authz:hitl-exact"
SCOPE_PREFIX = "authz:hitl-prefix"
CLIENT_ID = "authz-mcp-caller-1"
TOKEN = "authz-mcp-token"
INSTANT = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
_VALID_HASH = "e" * 64
_AWARE_TIME = datetime(2026, 7, 31, 15, 0, tzinfo=UTC)
#: FastMCP DNS-rebinding defaults allow ``127.0.0.1:<port>`` (A1 spike).
BASE_URL = "http://127.0.0.1:8124"


def _clock() -> datetime:
    return INSTANT


def _mapping() -> ScopeMappingArtifact:
    return ScopeMappingArtifact(
        semver="1.0.0",
        scopes={
            SCOPE_EXACT: ScopeEntry(
                tenant_patterns=("tenant-a",),
                action_ids=(
                    ACTION_HITL_QUEUE_READ,
                    ACTION_HITL_ACTION_SUBMIT,
                ),
            ),
            SCOPE_PREFIX: ScopeEntry(
                tenant_patterns=("tenant-b-*",),
                action_ids=(ACTION_HITL_QUEUE_READ,),
            ),
        },
    )


class Harness:
    """One registry, one authorizer, one server, one recording transport."""

    def __init__(self, tmp_path: Path) -> None:
        self.registry = ControlPlaneRegistry(clock=_clock)
        self.mapping_version = self.registry.register_typed(
            MAPPING_KEY, _mapping(), SCOPE_MAPPING
        )
        self.authorizer = ControlPlaneTenantAuthorizer(
            control_plane=self.registry,
            scope_mapping_key=MAPPING_KEY,
            clock=_clock,
        )
        self.transport = InMemoryHitlTransport()
        token_file = tmp_path / "tokens.json"
        token_file.write_text(
            json.dumps(
                {
                    TOKEN: {
                        "client_id": CLIENT_ID,
                        "scopes": [SCOPE_EXACT, SCOPE_PREFIX],
                    }
                }
            ),
            encoding="utf-8",
        )

        def queue_view(*, tenant: str) -> tuple[PendingHitlEvent, ...]:
            return ()

        def action_route(*, submission: HitlActionSubmission) -> str:
            self.transport.submit(submission=submission)
            return "{}"

        self.server = build_hitl_server(
            server_name="authz-mcp-hitl",
            queue_view=queue_view,
            action_route=action_route,
            token_verifier=SourceBackedTokenVerifier(
                source=FileTokenSource(path=token_file)
            ),
            auth_settings=AuthSettings(
                issuer_url=AnyHttpUrl("https://issuer.invalid"),
                resource_server_url=AnyHttpUrl(f"{BASE_URL}/mcp"),
                required_scopes=[SCOPE_EXACT],
            ),
            authorizer=self.authorizer,
        )

    def resource_fn(self) -> Any:
        template = self.server._resource_manager._templates[
            HITL_QUEUE_URI_TEMPLATE
        ]
        return template.fn

    def tool_fn(self) -> Any:
        return self.server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn

    def authz_events(
        self, *, tenant: str
    ) -> tuple[AuthzDecisionAuditEvent, ...]:
        return tuple(
            event
            for event in self.registry.audit_events()
            if isinstance(event, AuthzDecisionAuditEvent)
            and event.key == tenant
        )


@pytest.fixture()
def harness(tmp_path: Path) -> Harness:
    return Harness(tmp_path)


@pytest.fixture()
def verified_token(monkeypatch: pytest.MonkeyPatch) -> None:
    import ccf_runtime.mcp.hitl_server as hitl_server

    monkeypatch.setattr(
        hitl_server,
        "get_access_token",
        lambda: AccessToken(
            token=TOKEN,
            client_id=CLIENT_ID,
            scopes=[SCOPE_EXACT, SCOPE_PREFIX],
        ),
    )


def _tool_arguments(tenant: str) -> dict[str, Any]:
    return {
        "tenant": tenant,
        "event_key": "authz-event-1",
        "action": "approve",
        "subject_id": CLIENT_ID,
        "identity_provider_ref": "idp://acme-bank/dev-token-file",
        "method": "bearer-token",
        "assurance_level": "dev",
        "session_ref": "authz-session-1",
        "action_time": _AWARE_TIME.isoformat(),
        "product_content_hash": _VALID_HASH,
    }


# --- resource legs (hitl.queue.read) ----------------------------------------


def test_the_queue_resource_serves_an_authorized_tenant(
    harness: Harness, verified_token: None
) -> None:
    body = json.loads(harness.resource_fn()(tenant="tenant-a"))
    assert body == {"tenant": "tenant-a", "events": []}
    events = harness.authz_events(tenant="tenant-a")
    assert events and events[-1].resolved is True
    assert events[-1].version == harness.mapping_version
    assert events[-1].authz_action_id == ACTION_HITL_QUEUE_READ


def test_the_queue_resource_denies_with_the_shared_code(
    harness: Harness, verified_token: None
) -> None:
    with pytest.raises(ValueError) as denied:
        harness.resource_fn()(tenant="tenant-z")
    payload = json.loads(str(denied.value))
    assert payload["error_code"] == ERROR_TENANT_UNAUTHORIZED
    assert "message" in payload
    events = harness.authz_events(tenant="tenant-z")
    assert events and events[-1].resolved is False
    assert events[-1].version == harness.mapping_version


# --- tool legs (hitl.action.submit) -----------------------------------------


def test_the_action_tool_submits_for_an_authorized_tenant(
    harness: Harness, verified_token: None
) -> None:
    result = harness.tool_fn()(**_tool_arguments("tenant-a"))
    assert result == "{}"
    assert len(harness.transport.submissions(tenant="tenant-a")) == 1
    events = harness.authz_events(tenant="tenant-a")
    assert events and events[-1].resolved is True
    assert events[-1].authz_action_id == ACTION_HITL_ACTION_SUBMIT


def test_the_action_tool_denies_and_never_touches_the_route(
    harness: Harness, verified_token: None
) -> None:
    # tenant-b-7 matches only the read-scoped prefix entry: the submit
    # action is denied by default (T-10-01).
    with pytest.raises(ValueError) as denied:
        harness.tool_fn()(**_tool_arguments("tenant-b-7"))
    payload = json.loads(str(denied.value))
    assert payload["error_code"] == ERROR_TENANT_UNAUTHORIZED
    assert harness.transport.submissions(tenant="tenant-b-7") == ()
    events = harness.authz_events(tenant="tenant-b-7")
    assert events and events[-1].resolved is False


# --- over-the-wire legs (A1 spike harness) ----------------------------------


def _read_resource_over_the_wire(harness: Harness, uri: str) -> str:
    app = harness.server.streamable_http_app()

    async def operation(session: ClientSession) -> str:
        result = await session.read_resource(AnyUrl(uri))
        return "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    def client_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    async def with_lifespan() -> str:
        async with app.router.lifespan_context(app):
            return await run_with_session(
                url=f"{BASE_URL}/mcp",
                operation=operation,
                http_client_factory=client_factory,
            )

    return asyncio.run(with_lifespan())


def test_over_the_wire_the_verified_token_authorizes_the_read(
    harness: Harness,
) -> None:
    """No monkeypatching: the real middleware supplies the grant (A1)."""
    body = json.loads(
        _read_resource_over_the_wire(harness, hitl_queue_uri(tenant="tenant-a"))
    )
    assert body == {"tenant": "tenant-a", "events": []}


def test_over_the_wire_a_deny_carries_the_shared_code(
    harness: Harness,
) -> None:
    with pytest.raises(McpError) as denied:
        _read_resource_over_the_wire(
            harness, hitl_queue_uri(tenant="tenant-z")
        )
    assert ERROR_TENANT_UNAUTHORIZED in str(denied.value)


# --- cross-door consistency (D-02) ------------------------------------------


def _http_outcome(
    harness: Harness, *, tenant: str, action_id: str
) -> bool:
    """The HTTP door's observed outcome for one (grant, tenant, action)."""
    from fastapi import Depends, FastAPI, Request

    from ccf_runtime.http_api.dependencies import ApiDependencies
    from ccf_runtime.http_api.routes import hitl as hitl_routes

    def stash(request: Request) -> None:
        request.state.token_grant = TokenGrant(
            client_id=CLIENT_ID, scopes=(SCOPE_EXACT, SCOPE_PREFIX)
        )

    deps = ApiDependencies(
        control_plane=harness.registry,
        artifact_store=cast(Any, None),
        product_resolver=cast(Any, None),
        workflow_factory=cast(Any, None),
        workflow_engine=cast(Any, None),
        hitl_transport=harness.transport,
        skill_catalog=cast(Any, None),
        grant_ledger=cast(Any, None),
    )
    app = FastAPI()
    app.include_router(
        hitl_routes.build_router(deps, authorizer=harness.authorizer),
        prefix="/hitl",
        dependencies=[Depends(stash)],
    )

    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://fabric.invalid"
        ) as client:
            if action_id == ACTION_HITL_QUEUE_READ:
                return await client.get(
                    "/hitl/queue", params={"tenant": tenant}
                )
            return await client.post(
                "/hitl/actions", json=_http_submission(tenant)
            )

    response = asyncio.run(go())
    assert response.status_code in (200, 403)
    if response.status_code == 403:
        detail = response.json()["detail"]
        assert detail["error_code"] == ERROR_TENANT_UNAUTHORIZED
        return False
    return True


def _http_submission(tenant: str) -> dict[str, Any]:
    from ccf.hitl.principal import (
        ApproverIdentity,
        AuthenticationContext,
        HumanPrincipalBinding,
    )

    principal = HumanPrincipalBinding(
        approver=ApproverIdentity(
            subject_id=CLIENT_ID,
            identity_provider_ref="idp://acme-bank/dev-token-file",
        ),
        authentication=AuthenticationContext(
            method="bearer-token",
            assurance_level="dev",
            session_ref="authz-session-1",
        ),
        action_time=_AWARE_TIME,
        product_content_hash=_VALID_HASH,
    )
    return {
        "event_key": "authz-event-1",
        "tenant": tenant,
        "action": "approve",
        "principal": principal.model_dump(mode="json"),
        "annotation": None,
        "signed_binding": None,
    }


def _mcp_outcome(
    harness: Harness, *, tenant: str, action_id: str
) -> bool:
    """The MCP door's observed outcome for the same tuple."""
    try:
        if action_id == ACTION_HITL_QUEUE_READ:
            harness.resource_fn()(tenant=tenant)
        else:
            harness.tool_fn()(**_tool_arguments(tenant))
    except ValueError as error:
        payload = json.loads(str(error))
        assert payload["error_code"] == ERROR_TENANT_UNAUTHORIZED
        return False
    return True


@pytest.mark.parametrize(
    ("tenant", "action_id"),
    [
        ("tenant-a", ACTION_HITL_QUEUE_READ),
        ("tenant-a", ACTION_HITL_ACTION_SUBMIT),
        ("tenant-b-7", ACTION_HITL_QUEUE_READ),
        ("tenant-b-7", ACTION_HITL_ACTION_SUBMIT),
        ("tenant-z", ACTION_HITL_QUEUE_READ),
        ("tenant-z", ACTION_HITL_ACTION_SUBMIT),
    ],
)
def test_both_doors_decide_identically_for_the_same_tuple(
    harness: Harness,
    verified_token: None,
    tenant: str,
    action_id: str,
) -> None:
    """Same scope-mapping artifact + same grant => the same allow/deny
    outcome at both doors for the same action ID (D-02)."""
    assert _http_outcome(
        harness, tenant=tenant, action_id=action_id
    ) == _mcp_outcome(harness, tenant=tenant, action_id=action_id)
