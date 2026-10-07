"""The MCP wrapper mints from the decision's own id, or refuses (D-IMPL-353 §1.5a; the join).

Lane CAP-GATE's ``ControlPlaneTenantAuthorizer`` populates
``AuthzDecision.decision_id`` from the ``authz_decision`` audit event it
appends; the wrapper binds the capability to THAT id — the record the
capability is evidence of — never to a content hash of the decision tuple,
which names no record. An allow carrying no id, or deciding about a tenant,
action or resource other than the one the wrapper asked about, is refused as
``decision-unmintable``, typed, before anything is minted and before the body
runs — the mirror of the HTTP gate's refusal. Every claim below is drafted
from what would fail:

=====================================  =====================================
Claim                                  What would fail here
=====================================  =====================================
``decision_id`` is the decision's      a capability could name a record that
                                       does not exist
an allow with no id is refused         an untraceable authority could be
                                       minted from a deployment's authorizer
                                       that forgot to record
a misdirected allow is refused         an authorizer answering about another
                                       tenant/action/resource could open a
                                       body for this one
the body never runs on the refusal     the refusal would be a check the body
                                       could have ignored
=====================================  =====================================
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.fastmcp import FastMCP

from ccf.authz.actions import ACTION_AGENT_LIST
from ccf.authz.capability import AgentList, Authorized, verify
from ccf.authz.decision import AuthzDecision
from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.contracts.canonical import content_hash
from ccf_runtime.http_api.errors import ERROR_DECISION_UNMINTABLE
from ccf_runtime.mcp.auth import TokenGrant, tenant_claims
from ccf_runtime.mcp.tenancy import (
    DecisionUnmintableRefused,
    TenantGuardedServer,
    TenantGuardViolation,
)
from tests.mcp.guarded_servers import authorizer_granting

TENANT = "unmintable-tenant"
PRINCIPAL = "unmintable-principal"
SCOPE = "ccf:unmintable"


def _as_grant() -> Any:
    grant = TokenGrant(client_id=PRINCIPAL, scopes=(SCOPE,), tenants=frozenset({TENANT}))
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="in-process",
                client_id=grant.client_id,
                scopes=list(grant.scopes),
                claims=dict(tenant_claims(grant)),
            )
        )
    )


@dataclass
class _Rewriting:
    """A real authorizer whose allow is rewritten on the way out."""

    inner: Any
    rewrite: Any
    asked: int = 0

    def authorize(self, *, grant: TokenGrant, tenant: str, action_id: str, resource: str) -> AuthzDecision:
        self.asked += 1
        decision = self.inner.authorize(grant=grant, tenant=tenant, action_id=action_id, resource=resource)
        rewritten: AuthzDecision = self.rewrite(decision)
        return rewritten


@dataclass
class _World:
    server: FastMCP
    entered: list[object] = field(default_factory=list)


def _world(authorizer: Any) -> _World:
    entered: list[object] = []
    door = TenantGuardedServer(FastMCP("unmintable"), authorizer=authorizer)

    @door.tool(
        name="list_it",
        action=ACTION_AGENT_LIST,
        subject=door.from_grant(),
        resource=door.resource_route(),
        mutating=False,
        products=TenantGuardedServer.products_unknown("test fixture"),
    )
    def list_it(authorized: Authorized[AgentList]) -> str:
        entered.append(authorized)
        return "entered"

    return _World(server=door.build(), entered=entered)


def _call(world: _World) -> Any:
    reset = _as_grant()
    try:
        return anyio.run(world.server.call_tool, "list_it", {})
    finally:
        auth_context_var.reset(reset)


def _refusal(operation: Any) -> BaseException:
    try:
        operation()
    except BaseException as raised:  # noqa: BLE001 - the subject under test
        current: BaseException | None = raised
        while current is not None:
            if isinstance(current, TenantGuardViolation):
                return current
            current = current.__cause__ or current.__context__
        return raised
    raise AssertionError("the call was served; no refusal to inspect")


def test_the_minted_decision_id_is_the_allow_events_content_address() -> None:
    """Positive control: the capability names the authorizer's own record."""
    authorizer = authorizer_granting(tenants=(TENANT,), scopes=(SCOPE,))
    world = _world(authorizer)
    _call(world)
    (authorized,) = world.entered
    verify(authorized, kind=AgentList, resource=ACTION_AGENT_LIST)
    allows = [
        e
        for e in authorizer._control_plane.audit_log.events()
        if isinstance(e, AuthzDecisionAuditEvent) and e.resolved
    ]
    assert len(allows) == 1
    assert getattr(authorized, "decision_id") == content_hash(allows[0])


def test_an_allow_carrying_no_decision_id_is_refused_and_nothing_is_minted() -> None:
    world = _world(
        _Rewriting(
            inner=authorizer_granting(tenants=(TENANT,), scopes=(SCOPE,)),
            rewrite=lambda d: d.model_copy(update={"decision_id": None}),
        )
    )
    refused = _refusal(lambda: _call(world))
    assert isinstance(refused, DecisionUnmintableRefused)
    assert json.loads(str(refused))["error_code"] == ERROR_DECISION_UNMINTABLE
    assert world.entered == []


@pytest.mark.parametrize(
    "rewrite",
    [
        lambda d: d.model_copy(update={"tenant": "some-other-tenant"}),
        lambda d: d.model_copy(update={"action_id": "agent.read"}),
        lambda d: d.model_copy(update={"resource": "some-other-resource"}),
    ],
    ids=["tenant", "action", "resource"],
)
def test_a_misdirected_allow_is_refused_and_the_body_never_runs(rewrite: Any) -> None:
    world = _world(
        _Rewriting(inner=authorizer_granting(tenants=(TENANT,), scopes=(SCOPE,)), rewrite=rewrite)
    )
    refused = _refusal(lambda: _call(world))
    assert isinstance(refused, DecisionUnmintableRefused)
    assert world.entered == []


def test_a_deny_is_still_a_deny_not_an_unmintable() -> None:
    """The refusal class is about an ALLOW the wrapper cannot mint from; a
    deny keeps its own refusal."""
    from ccf_runtime.mcp.tenancy import ActionUnauthorizedRefused

    world = _world(authorizer_granting(tenants=(TENANT,), scopes=(SCOPE,), actions=()))
    refused = _refusal(lambda: _call(world))
    assert isinstance(refused, ActionUnauthorizedRefused)
    assert world.entered == []
