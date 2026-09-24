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
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from fastapi import Depends, FastAPI, Request
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
from ccf_runtime.http_api.errors import (
    ERROR_REQUEST_UNAUTHORIZED,
    ERROR_TENANT_UNAUTHORIZED,
)
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
#: The projection role this module's perspective resolver returns. No test
#: here reads a product, so it exists only because every app binds the seam.
ROLE = "authz-mcp-role"
#: A product class no test in this module asks for. The entitlement policy
#: every app binds requires a non-empty principal table, and naming a class
#: that is never requested says so rather than implying a reachable grant.
UNASKED_CLASS = "authz-mcp-class-no-test-asks-for"
#: The submission both doors are asked to route. One spelling, because the
#: scope mapping below names it as a RESOURCE and a policy that named a
#: different key than the requests send would deny for a reason no test
#: meant to assert.
EVENT_KEY = "authz-event-1"
TOKEN = "authz-mcp-token"
INSTANT = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
_VALID_HASH = "e" * 64
_AWARE_TIME = datetime(2026, 7, 31, 15, 0, tzinfo=UTC)
#: FastMCP DNS-rebinding defaults allow ``127.0.0.1:<port>`` (A1 spike).
BASE_URL = "http://127.0.0.1:8124"


def _clock() -> datetime:
    return INSTANT


def _mapping() -> ScopeMappingArtifact:
    """The two scopes this module decides with.

    ``resource_patterns`` is written exactly as wide as what the doors below
    actually name, and no wider. A blanket resource grant would still pass
    every assertion here and would quietly stop being evidence about the axis
    it was written for, so each pattern is a thing some door really acts on.

    **Three patterns for two actions, because the two doors do not name the
    resource the same way — and that asymmetry is the SDK's, not this
    fixture's.** The MCP HITL door acts on no addressable subject, so it names
    *itself*: it passes ``resource=action_id`` for both the queue read and the
    action submit. Its HTTP twin declares
    ``@authorizes(ACTION_HITL_QUEUE_READ, resource=ResourceBinding.route())``
    for the read — the same spelling — but
    ``resource=ResourceBinding.body("event_key")`` for the submit, which names
    the *submission*, not the door. So a deployment that wants one scope to
    authorize the submit at both doors has to name both vocabularies, which is
    what :data:`EVENT_KEY` is doing in this tuple. Measured: without it,
    ``test_both_doors_decide_identically_for_the_same_tuple`` splits on
    ``("tenant-a", ACTION_HITL_ACTION_SUBMIT)`` — MCP allows, HTTP denies.

    The field is required with no default, so an author cannot leave the axis
    opt-in (``SEC-002``).
    """
    return ScopeMappingArtifact(
        semver="1.0.0",
        scopes={
            SCOPE_EXACT: ScopeEntry(
                tenant_patterns=("tenant-a",),
                action_ids=(
                    ACTION_HITL_QUEUE_READ,
                    ACTION_HITL_ACTION_SUBMIT,
                ),
                resource_patterns=(
                    ACTION_HITL_QUEUE_READ,
                    ACTION_HITL_ACTION_SUBMIT,
                    EVENT_KEY,
                ),
            ),
            SCOPE_PREFIX: ScopeEntry(
                tenant_patterns=("tenant-b-*",),
                action_ids=(ACTION_HITL_QUEUE_READ,),
                resource_patterns=(ACTION_HITL_QUEUE_READ,),
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
        # The version is pinned, not resolved at decision time (``SEC-002``):
        # an authorizer that read "latest" would change its mind whenever the
        # Control Plane was written to, and a replayed decision could not be
        # reproduced against the mapping that actually made it.
        self.authorizer = ControlPlaneTenantAuthorizer(
            control_plane=self.registry,
            scope_mapping_key=MAPPING_KEY,
            scope_mapping_version=str(self.mapping_version),
            clock=_clock,
        )
        self.transport = InMemoryHitlTransport()
        token_file = tmp_path / "tokens.json"
        token_file.write_text(
            json.dumps(
                {
                    # BOTH tenants, deliberately. What this module tests is
                    # the per-action AUTHORIZER, so the credential has to reach
                    # the denied tenant for the authorizer to be what denies
                    # it. The tenancy floor and the action policy are two
                    # layers, and this fixture exercises the upper one
                    # (`SEC-018`).
                    TOKEN: {
                        "client_id": CLIENT_ID,
                        "scopes": [SCOPE_EXACT, SCOPE_PREFIX],
                        "tenants": sorted(EXERCISED_TENANTS),
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
    """Stand in for the bearer middleware on BOTH readers of the identity.

    Two modules read ``get_access_token``: the HITL door, for its per-action
    authorization, and :mod:`ccf_runtime.mcp.tenancy`, for the tenancy floor.
    Each imported the name into its own namespace, so one patch leaves the
    other reading the real (empty) context.

    **The grant carries every tenant this module exercises, deliberately.**
    What is under test here is the per-action AUTHORIZER — that it allows
    ``tenant-a``, allows only the read on ``tenant-b-7``, and denies
    ``tenant-z``. A credential that did not reach those tenants would be
    stopped by the tenancy floor first and the authorizer would never be the
    thing deciding, which is the whole subject (`SEC-018`).
    """
    import ccf_runtime.mcp.hitl_server as hitl_server
    import ccf_runtime.mcp.tenancy as tenancy

    from ccf_runtime.mcp.auth import TokenGrant, tenant_claims

    token = AccessToken(
        token=TOKEN,
        client_id=CLIENT_ID,
        scopes=[SCOPE_EXACT, SCOPE_PREFIX],
        claims=dict(
            tenant_claims(
                TokenGrant(
                    client_id=CLIENT_ID,
                    scopes=(SCOPE_EXACT, SCOPE_PREFIX),
                    tenants=EXERCISED_TENANTS,
                )
            )
        ),
    )
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: token)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: token)


#: Every tenant this module drives a door with. One roster, so the credential
#: cannot fall out of step with the cases (`SEC-018`).
EXERCISED_TENANTS = frozenset({"tenant-a", "tenant-b-7", "tenant-z"})


def _tool_arguments(tenant: str) -> dict[str, Any]:
    return {
        "tenant": tenant,
        "event_key": EVENT_KEY,
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
    # The client helper re-raises through the ASGI task group, so the
    # ``McpError`` carrying the payload sits in the exception chain; the
    # assertion walks the rendered chain for the shared constant.
    chain = ""
    try:
        _read_resource_over_the_wire(
            harness, hitl_queue_uri(tenant="tenant-z")
        )
    except BaseException as error:
        chain = "".join(traceback.format_exception(error))
    assert chain, "the deny must surface as a protocol error"
    assert McpError.__name__ in chain
    assert ERROR_TENANT_UNAUTHORIZED in chain


# --- cross-door consistency (D-02) ------------------------------------------


def _http_outcome(
    harness: Harness, root: Path, *, tenant: str, action_id: str
) -> bool:
    """The HTTP door's observed outcome for one (grant, tenant, action).

    **Rewritten for the posture that replaced the one it was built on**
    (``SEC-002``). The predecessor assembled a bare :class:`FastAPI`, mounted
    ``hitl_routes.build_router(deps, authorizer=...)`` on it, and supplied the
    verified identity with a route dependency that wrote
    ``request.state.token_grant`` directly. Every one of those is gone: the
    authorization gate is no longer a router argument but pure-ASGI
    middleware that ``create_app`` installs over the whole application, and a
    hand-mounted router therefore has **no gate at all** — the old shape would
    now measure an ungated door and report it as an allow.

    So the app is the shipped one. What the module claims is unchanged and is
    now load-bearing for a wider surface: the HTTP door and the MCP door,
    handed the **same** scope-mapping artifact at the **same** pinned version
    and the same grant, reach the same allow/deny for the same action.
    :func:`~http_api.gate_fixtures.authority` supplies the four seams this
    module has no opinion about, and the fifth — the authorizer, which is the
    entire subject — is replaced with the harness's own.

    Two differences between the doors are real and are asserted rather than
    papered over:

    * **The tenant is the grant's** (``tenant := grant.tenant``), so the
      credential is minted per case. The queue route's ``tenant`` query
      parameter and the submission body's ``tenant`` field may only *agree*
      with it; neither supplies it any more.
    * **The deny code differs by door.** The MCP door answers
      ``ERROR_TENANT_UNAUTHORIZED``; the HTTP gate answers the single
      ``ERROR_REQUEST_UNAUTHORIZED`` it emits for all five of its denial
      reasons, deliberately, so a caller cannot tell which axis refused it.
      The *decision* is what this module asserts is shared — not its
      rendering.
    """
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.products.entitlement import (
        PRODUCT_ENTITLEMENT_POLICY,
        ProductEntitlementGrant,
        ProductEntitlementPolicy,
        product_entitlement_key,
    )
    from ccf.products.resolver import ReplayRefusalRecorder
    from ccf.projection.plan import Perspective
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.dependencies import ApiDependencies

    from http_api.gate_fixtures import authority, probe

    # This module's OWN entitlement policy, naming this module's tenant and
    # no principal grants: nothing here asks for a product, and borrowing
    # another suite's registry would decide about another suite's vocabulary.
    entitlements = ControlPlaneRegistry()
    entitlements.register_typed(
        product_entitlement_key(tenant_id=tenant),
        ProductEntitlementPolicy(
            tenant_id=tenant,
            policy_version="1.0.0",
            # One principal, entitled to a class no test here asks for: the
            # policy requires a non-empty table, and this module's doors are
            # HITL doors that read no product at all.
            principals={
                CLIENT_ID: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({UNASKED_CLASS}),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(
        control_plane=entitlements, clock=_clock
    )
    seams = authority(
        tenant=tenant,
        # `authority` builds a wide authorizer inside a registry of its own,
        # and the line below throws it away: both doors have to decide against
        # ONE artifact at ONE pinned version or the comparison is vacuous. The
        # key is therefore never read.
        key=MAPPING_KEY,
        grants={TOKEN: (CLIENT_ID, (SCOPE_EXACT, SCOPE_PREFIX), tenant)},
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=ROLE
            )
        ),
        refusal_recorder=ReplayRefusalRecorder(
            artifact_store=FileArtifactStore(root=root / "artifacts"),
            replay_record_class="ccf.decision-replay-record",
            tenant_id=tenant,
            assembly_mode="algorithmic",
            policy_bundle_pin=None,
            disclosure_level_for=source.disclosure_level_for,
        ),
    )
    seams["authorizer"] = harness.authorizer

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
    app = create_app(deps, **seams)
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if action_id == ACTION_HITL_QUEUE_READ:
        response = probe(
            app, "GET", "/hitl/queue",
            params={"tenant": tenant}, headers=headers,
        )
    else:
        response = probe(
            app, "POST", "/hitl/actions",
            json=_http_submission(tenant), headers=headers,
        )
    assert response.status_code in (200, 403), response.text
    if response.status_code == 403:
        detail = response.json()["detail"]
        assert detail["error_code"] == ERROR_REQUEST_UNAUTHORIZED
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
        "event_key": EVENT_KEY,
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
    tmp_path: Path,
    tenant: str,
    action_id: str,
) -> None:
    """Same scope-mapping artifact + same grant => the same allow/deny
    outcome at both doors for the same action ID (D-02)."""
    assert _http_outcome(
        harness, tmp_path, tenant=tenant, action_id=action_id
    ) == _mcp_outcome(harness, tenant=tenant, action_id=action_id)
