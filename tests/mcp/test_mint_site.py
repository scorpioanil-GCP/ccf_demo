"""The MCP wrapper is the second mint site (``D-IMPL-353`` §1.1) — every claim as a test.

:class:`~ccf_runtime.mcp.tenancy.TenantGuardedServer` decides tenancy, asks the
deployment's authorizer for the body's declared action on the body's declared
resource, and — on *allowed* and only then — mints an
:class:`~ccf_runtime.authz.capability.Authorized` of the kind that action maps
to and hands it to the body as its first argument. A body has no ``authorizer``
parameter and no ``tenant`` argument; it has ``authorized``.

Every assertion below is drafted from *what would fail here*:

=========================================  ===================================
Claim                                      What would fail here
=========================================  ===================================
§1.1 the mint follows the decision         a body could run under a refusal,
                                           or under a capability for another
                                           action
§1.3 exactly one tenant, the grant's        a multi-tenant grant could have a
                                           tenant picked for it, or a foreign
                                           tenant named on the wire served
§1.5(c) kind by identity                   a ``list_agents`` capability could
                                           be presented to a write handle
§2 P4 no ``authorizer=None`` arm           a builder could compose a door that
                                           decides nothing
§2 P9 raw registration is a boot failure   a handler could reach the wire
                                           having never been minted anything
stdio ambient identity                     a stated identity could be minted a
                                           mutating kind
§6 the round-trip                          the grant's tenants could fail to
                                           reach the mint through the library's
                                           own token object
=========================================  ===================================

Tenant, principal, scope, action and token names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from typing import Any

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.fastmcp import FastMCP

from ccf.contracts.canonical import content_hash
from ccf.authz import capability
from ccf.authz.capability import (
    ActionKind,
    AgentList,
    ArtifactRead,
    ArtifactWrite,
    Authorized,
    CapabilityBypassError,
    Execute,
    ReplayMint,
    kind_for_action,
    verify,
)
from ccf.authz.decision import AuthzDecision
from ccf_runtime.authz.protocol import TenantAuthorizerProtocol
from ccf.authz.actions import (
    ACTION_AGENT_LIST,
    ACTION_ARTIFACT_READ,
    ACTION_ARTIFACT_WRITE,
    ACTION_WORKFLOW_INVOKE,
)
from ccf_runtime.http_api.errors import ERROR_TENANT_UNAUTHORIZED
from ccf_runtime.mcp.auth import (
    SourceBackedTokenVerifier,
    StaticTokenSource,
    TokenGrant,
    tenant_claims,
)
from ccf_runtime.mcp.tenancy import (
    READ_KINDS,
    ActionUnauthorizedRefused,
    AmbientMutationRefused,
    AmbiguousTenantRefused,
    CrossTenantRefused,
    ResourceUnreadableRefused,
    TenantGuardedServer,
    TenantGuardViolation,
    TenantlessGrantRefused,
    UnguardedSurfaceError,
    UnverifiedTenantCallerRefused,
    ambient_stdio_identity,
)
from tests.mcp.guarded_servers import authorizer_granting

TENANT = "mint-tenant-own"
FOREIGN = "mint-tenant-foreign"
PRINCIPAL = "mint-principal"
SCOPE = "ccf:mint"
RESOURCE = "mint-resource/one"


# --- fixtures ---------------------------------------------------------------


def _grant(*tenants: str, scopes: tuple[str, ...] = (SCOPE,)) -> TokenGrant:
    return TokenGrant(client_id=PRINCIPAL, scopes=scopes, tenants=frozenset(tenants))


def _as_grant(grant: TokenGrant | None) -> Any:
    """Run under the auth contextvar the bearer middleware would populate."""
    if grant is None:
        return auth_context_var.set(None)
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


def _refusal(operation: Any) -> BaseException:
    """Drive ``operation`` and return the guard refusal underneath.

    ``FastMCP`` re-wraps a handler's exception; both ``__cause__`` and
    ``__context__`` are walked because the resource-template path chains
    implicitly (see ``test_tenant_guard.py::_refusal``).
    """
    try:
        operation()
    except BaseException as raised:  # noqa: BLE001 - the subject under test
        seen: list[BaseException] = []
        current: BaseException | None = raised
        while current is not None and current not in seen:
            if isinstance(current, (TenantGuardViolation, CapabilityBypassError)):
                return current
            seen.append(current)
            current = current.__cause__ or current.__context__
        return raised
    raise AssertionError("the call was served; no refusal to inspect")


@dataclass
class _RecordingAuthorizer:
    """A conforming authorizer that answers as told and remembers every ask.

    Written here, in the test, rather than imported: the SDK ships no
    permissive authorizer and this file does not add one to it. ``allow`` is
    the whole policy, and it is visible at the call site.
    """

    allow: bool = True
    asked: list[dict[str, Any]] = field(default_factory=list)

    def authorize(
        self, *, grant: TokenGrant, tenant: str, action_id: str, resource: str
    ) -> AuthzDecision:
        self.asked.append(
            {"grant": grant, "tenant": tenant, "action_id": action_id, "resource": resource}
        )
        return AuthzDecision(
            allowed=self.allow,
            matched_scope_pattern=tenant if self.allow else None,
            matched_resource_pattern=resource if self.allow else None,
            artifact_version="1.0.0",
            action_id=action_id,
            tenant=tenant,
            resource=resource,
            # What the SDK's authorizer always supplies: the id of the audit
            # event this decision is evidence of. Deterministic per ask here,
            # so a test that recomputes the decision recomputes the id.
            decision_id=content_hash(
                {"tenant": tenant, "action_id": action_id, "resource": resource}
            ),
        )


@dataclass
class _Probe:
    """A door with one read tool, one write tool and one template resource,
    each body recording the capability it was handed."""

    door: TenantGuardedServer
    server: FastMCP
    authorizer: _RecordingAuthorizer
    received: list[Authorized[Any]] = field(default_factory=list)


def _probe(*, authorizer: TenantAuthorizerProtocol | None = None) -> _Probe:
    recording = _RecordingAuthorizer() if authorizer is None else None
    door = TenantGuardedServer(
        FastMCP("mint-probe"),
        authorizer=recording if recording is not None else authorizer,  # type: ignore[arg-type]
    )
    received: list[Authorized[Any]] = []

    @door.tool(
        name="read_it",
        action=ACTION_ARTIFACT_READ,
        subject=door.from_argument("tenant"),
        resource=door.resource_argument("content_address"),
        mutating=False,
    )
    def read_it(authorized: Authorized[ArtifactRead], content_address: str) -> str:
        received.append(authorized)
        return json.dumps({"tenant": authorized.tenant, "resource": authorized.resource})

    @door.tool(
        name="write_it",
        action=ACTION_ARTIFACT_WRITE,
        subject=door.from_grant(),
        resource=door.resource_composed("{artifact_class}/{name}"),
        mutating=True,
    )
    def write_it(
        authorized: Authorized[ArtifactWrite], artifact_class: str, name: str
    ) -> str:
        received.append(authorized)
        return json.dumps({"tenant": authorized.tenant, "resource": authorized.resource})

    @door.tool(
        name="list_it",
        action=ACTION_AGENT_LIST,
        subject=door.from_argument("tenant"),
        resource=door.resource_route(),
        mutating=False,
    )
    def list_it(authorized: Authorized[AgentList]) -> str:
        received.append(authorized)
        return json.dumps({"tenant": authorized.tenant})

    @door.resource(
        "probe://{tenant}/{item}",
        action=ACTION_ARTIFACT_READ,
        subject=door.from_argument("tenant"),
        resource=door.resource_argument("item"),
        mutating=False,
    )
    def item(authorized: Authorized[ArtifactRead], item: str) -> str:
        received.append(authorized)
        return json.dumps({"tenant": authorized.tenant, "item": item})

    server = door.build()
    return _Probe(
        door=door,
        server=server,
        authorizer=recording if recording is not None else _RecordingAuthorizer(),
        received=received,
    )


def _call(probe: _Probe, tool: str, args: dict[str, Any]) -> Any:
    return anyio.run(probe.server.call_tool, tool, args)


# --- §1.1 the wrapper mints after the decision, and only then -----------------


def test_the_body_receives_a_genuine_capability_for_its_declared_action() -> None:
    """The positive control: a real ``Authorized`` of the declared kind, for
    the declared resource, under the selected tenant, for the verified
    principal — and ``verify`` accepts it for exactly that."""
    probe = _probe()
    reset = _as_grant(_grant(TENANT))
    try:
        _, structured = _call(probe, "read_it", {"tenant": TENANT, "content_address": RESOURCE})
    finally:
        auth_context_var.reset(reset)
    assert json.loads(structured["result"]) == {"tenant": TENANT, "resource": RESOURCE}
    (authorized,) = probe.received
    verify(authorized, kind=ArtifactRead, resource=RESOURCE)  # no raise
    assert authorized.kind is kind_for_action(ACTION_ARTIFACT_READ)
    assert authorized.tenant == TENANT
    assert authorized.principal == PRINCIPAL
    assert authorized.resource == RESOURCE


def test_the_mint_carries_the_decisions_identity() -> None:
    """``decision_id`` is the decision's OWN id — the audit event the
    authorizer appended for this allow (D-IMPL-353 §1.5a; the join) — so a
    replay reader can tie the capability to the record it is evidence of and
    to nothing else. Not a content hash of the decision tuple, which names no
    record at all; ``tests/mcp/test_decision_unmintable.py`` carries the
    refusal for a decision that names none."""
    probe = _probe()
    reset = _as_grant(_grant(TENANT))
    try:
        _call(probe, "read_it", {"tenant": TENANT, "content_address": RESOURCE})
    finally:
        auth_context_var.reset(reset)
    (asked,) = probe.authorizer.asked
    decision = probe.authorizer.authorize(**asked)
    assert decision.decision_id is not None
    assert probe.received[0].decision_id == decision.decision_id
    assert probe.received[0].decision_id != content_hash(decision)


def test_the_authorizer_is_asked_for_the_declared_action_and_resource() -> None:
    """The decision tuple is the door's declaration, never the caller's choice:
    the grant is the verified token's, the tenant is the selected one, the
    action is the registration's, the resource is read where the registration
    said to read it."""
    probe = _probe()
    reset = _as_grant(_grant(TENANT))
    try:
        _call(probe, "write_it", {"artifact_class": "c", "name": "n"})
    finally:
        auth_context_var.reset(reset)
    (asked,) = probe.authorizer.asked
    assert asked["grant"] == _grant(TENANT)
    assert asked["tenant"] == TENANT
    assert asked["action_id"] == ACTION_ARTIFACT_WRITE
    assert asked["resource"] == "c/n"
    assert probe.received[0].resource == "c/n"


def test_a_refusal_mints_nothing_and_the_body_is_never_entered() -> None:
    """The wrapper mints nothing on any refusal — the authorizer's *no* is a
    typed refusal carrying the shared constant (D-08), and the body has no
    capability to have been called with."""
    probe = _probe(authorizer=_RecordingAuthorizer(allow=False))
    reset = _as_grant(_grant(TENANT))
    try:
        refused = _refusal(
            lambda: _call(probe, "read_it", {"tenant": TENANT, "content_address": RESOURCE})
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, ActionUnauthorizedRefused)
    assert json.loads(str(refused))["error_code"] == ERROR_TENANT_UNAUTHORIZED
    assert probe.received == []


def test_the_tenancy_floor_runs_before_the_authorizer_is_asked() -> None:
    """A foreign tenant on the wire is refused at the floor: the authorizer is
    never consulted and nothing is minted, so a deployment's authorizer can
    never be the thing that lets a cross-tenant call through."""
    probe = _probe()
    reset = _as_grant(_grant(TENANT))
    try:
        refused = _refusal(
            lambda: _call(probe, "read_it", {"tenant": FOREIGN, "content_address": RESOURCE})
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, CrossTenantRefused)
    assert probe.authorizer.asked == []
    assert probe.received == []


@pytest.mark.parametrize(
    ("grant", "expected"),
    [
        (None, UnverifiedTenantCallerRefused),
        (_grant(), TenantlessGrantRefused),
    ],
    ids=["unverified", "tenantless"],
)
def test_the_floor_still_refuses_an_unverified_or_unscoped_caller(
    grant: TokenGrant | None, expected: type[BaseException]
) -> None:
    probe = _probe()
    reset = _as_grant(grant)
    try:
        refused = _refusal(
            lambda: _call(probe, "read_it", {"tenant": TENANT, "content_address": RESOURCE})
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, expected)
    assert probe.authorizer.asked == []


# --- §1.3 exactly one tenant, selected from the grant, never picked ----------


def test_a_surface_with_no_tenant_on_the_wire_takes_the_grants_sole_tenant() -> None:
    probe = _probe()
    reset = _as_grant(_grant(TENANT))
    try:
        _, structured = _call(probe, "write_it", {"artifact_class": "c", "name": "n"})
    finally:
        auth_context_var.reset(reset)
    assert json.loads(structured["result"])["tenant"] == TENANT
    assert probe.received[0].tenant == TENANT


def test_a_multi_tenant_grant_on_such_a_surface_is_ambiguous_and_refused() -> None:
    """The gate does not pick (§1.3). An operator credential spanning two
    tenants reaches a surface that names none, and the only two things a
    door could do are refuse or choose; it refuses, before the authorizer."""
    probe = _probe()
    reset = _as_grant(_grant(TENANT, FOREIGN))
    try:
        refused = _refusal(
            lambda: _call(probe, "write_it", {"artifact_class": "c", "name": "n"})
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, AmbiguousTenantRefused)
    assert probe.authorizer.asked == []
    assert probe.received == []


def test_a_multi_tenant_grant_naming_a_member_on_the_wire_is_served_as_that_member() -> None:
    """The other legitimate selection: the request names one and it is a
    member. Everything downstream sees that one tenant."""
    probe = _probe()
    reset = _as_grant(_grant(TENANT, FOREIGN))
    try:
        _call(probe, "read_it", {"tenant": FOREIGN, "content_address": RESOURCE})
    finally:
        auth_context_var.reset(reset)
    assert probe.received[0].tenant == FOREIGN
    assert probe.authorizer.asked[0]["tenant"] == FOREIGN


def test_the_body_has_no_tenant_argument_and_the_wire_still_does() -> None:
    """``tenant`` names which of the grant's tenants on the wire; it is consumed
    by the wrapper and never reaches the body. ``authorized`` is never on the
    wire. Measured on FastMCP's own input schema, not on the Python signature."""
    probe = _probe()
    tools = {tool.name: tool for tool in anyio.run(probe.server.list_tools)}
    assert set(tools["read_it"].inputSchema["required"]) == {"tenant", "content_address"}
    assert set(tools["write_it"].inputSchema["required"]) == {"artifact_class", "name"}
    assert set(tools["list_it"].inputSchema["required"]) == {"tenant"}
    for tool in tools.values():
        assert "authorized" not in tool.inputSchema.get("properties", {})


def test_a_template_resource_is_minted_and_its_tenant_segment_is_decided() -> None:
    """``get_access_token()`` is populated inside a resource read (the A1 spike
    verdict), so a template resource mints exactly as a tool does — and the
    ``{tenant}`` segment is a claim decided against the grant."""
    probe = _probe()
    reset = _as_grant(_grant(TENANT))
    try:
        contents = anyio.run(probe.server.read_resource, f"probe://{TENANT}/thing")
        refused = _refusal(
            lambda: anyio.run(probe.server.read_resource, f"probe://{FOREIGN}/thing")
        )
    finally:
        auth_context_var.reset(reset)
    (served,) = contents
    assert json.loads(str(served.content)) == {"tenant": TENANT, "item": "thing"}
    assert isinstance(refused, CrossTenantRefused)
    (authorized,) = probe.received
    verify(authorized, kind=ArtifactRead, resource="thing")


# --- §1.5(c) the kind is the declaration's; another kind dies at the seam ----


def test_a_list_agents_capability_cannot_be_used_as_a_write() -> None:
    """The control the task names: what a ``list_agents`` body receives dies
    at a write handle's ``verify`` — by identity, before any handle statement.
    The wrapper mints the declared kind and no other; the seam refuses the
    rest."""
    probe = _probe()
    reset = _as_grant(_grant(TENANT))
    try:
        _call(probe, "list_it", {"tenant": TENANT})
    finally:
        auth_context_var.reset(reset)
    (authorized,) = probe.received
    assert authorized.kind is AgentList
    with pytest.raises(CapabilityBypassError, match="kind"):
        verify(authorized, kind=ArtifactWrite, resource=ACTION_AGENT_LIST)
    with pytest.raises(CapabilityBypassError, match="kind"):
        verify(authorized, kind=Execute, resource=ACTION_AGENT_LIST)


def test_a_capability_for_one_resource_is_not_a_wand_for_another() -> None:
    probe = _probe()
    reset = _as_grant(_grant(TENANT))
    try:
        _call(probe, "write_it", {"artifact_class": "c", "name": "n"})
    finally:
        auth_context_var.reset(reset)
    (authorized,) = probe.received
    verify(authorized, kind=ArtifactWrite, resource="c/n")
    with pytest.raises(CapabilityBypassError, match="resource"):
        verify(authorized, kind=ArtifactWrite, resource="c/other")


# --- registration: what a door must state, refused at boot otherwise ---------


def test_registering_an_action_no_door_declares_fails_at_registration() -> None:
    door = TenantGuardedServer(FastMCP("reg"), authorizer=_RecordingAuthorizer())
    with pytest.raises(CapabilityBypassError, match="no door"):

        @door.tool(
            name="t",
            action="not.an.action",
            subject=door.from_grant(),
            resource=door.resource_route(),
            mutating=False,
        )
        def t(authorized: Authorized[Any]) -> str:
            return ""


def test_the_replay_mint_cannot_be_declared_by_a_door() -> None:
    door = TenantGuardedServer(FastMCP("reg"), authorizer=_RecordingAuthorizer())
    with pytest.raises(CapabilityBypassError, match="no door declares"):

        @door.tool(
            name="t",
            action=ReplayMint.action_id,
            subject=door.from_grant(),
            resource=door.resource_route(),
            mutating=True,
        )
        def t(authorized: Authorized[ReplayMint]) -> str:
            return ""


def test_a_body_without_the_capability_parameter_is_refused_at_registration() -> None:
    door = TenantGuardedServer(FastMCP("reg"), authorizer=_RecordingAuthorizer())
    with pytest.raises(ValueError, match="authorized"):

        @door.tool(
            name="t",
            action=ACTION_ARTIFACT_READ,
            subject=door.from_grant(),
            resource=door.resource_route(),
            mutating=False,
        )
        def t(content_address: str) -> str:
            return ""


def test_a_body_declaring_the_tenant_argument_is_refused_at_registration() -> None:
    """There is no second source for the tenant (§1.2): a body that also took
    ``tenant`` could read a value the wrapper did not decide."""
    door = TenantGuardedServer(FastMCP("reg"), authorizer=_RecordingAuthorizer())
    with pytest.raises(ValueError, match="tenant"):

        @door.tool(
            name="t",
            action=ACTION_ARTIFACT_READ,
            subject=door.from_argument("tenant"),
            resource=door.resource_route(),
            mutating=False,
        )
        def t(authorized: Authorized[ArtifactRead], tenant: str) -> str:
            return ""


def test_a_resource_argument_the_body_lacks_is_refused_at_registration() -> None:
    door = TenantGuardedServer(FastMCP("reg"), authorizer=_RecordingAuthorizer())
    with pytest.raises(ValueError, match="content_address"):

        @door.tool(
            name="t",
            action=ACTION_ARTIFACT_READ,
            subject=door.from_grant(),
            resource=door.resource_argument("content_address"),
            mutating=False,
        )
        def t(authorized: Authorized[ArtifactRead]) -> str:
            return ""


def test_an_unreadable_resource_argument_is_a_deny_never_a_skip() -> None:
    """The caller chooses what to send; every choice leads to the check running.
    A resource argument that is not a non-empty string denies before the
    authorizer is asked."""
    probe = _probe()
    reset = _as_grant(_grant(TENANT))
    try:
        refused = _refusal(
            lambda: _call(probe, "read_it", {"tenant": TENANT, "content_address": ""})
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, ResourceUnreadableRefused)
    assert probe.authorizer.asked == []


def test_the_ledger_records_what_each_surface_declared() -> None:
    probe = _probe()
    entry = probe.door.ledger["write_it"]
    assert entry.action == ACTION_ARTIFACT_WRITE
    assert entry.mutating is True
    assert entry.subject.grant is True
    assert entry.resource.template == "{artifact_class}/{name}"
    assert probe.door.ledger["list_it"].resource.route is True


# --- §2 P9: registration behind the wrapper is a boot failure ----------------


def test_a_server_already_carrying_a_surface_cannot_be_wrapped() -> None:
    raw = FastMCP("smuggled-before")

    @raw.tool(name="smuggled")
    def smuggled(tenant: str) -> str:
        return "ungoverned"

    with pytest.raises(UnguardedSurfaceError, match="smuggled"):
        TenantGuardedServer(raw, authorizer=_RecordingAuthorizer())


def test_a_surface_registered_behind_the_wrapper_fails_the_build() -> None:
    """The instrument that makes the wrapper mandatory, moved from a test to
    the builder's own return: a raw registration puts a name in FastMCP's
    registry and not in the ledger, and ``build`` refuses to hand back a
    server carrying one."""
    raw = FastMCP("smuggled-after")
    door = TenantGuardedServer(raw, authorizer=_RecordingAuthorizer())

    @door.tool(
        name="governed",
        action=ACTION_ARTIFACT_READ,
        subject=door.from_grant(),
        resource=door.resource_route(),
        mutating=False,
    )
    def governed(authorized: Authorized[ArtifactRead]) -> str:
        return ""

    @raw.tool(name="smuggled")
    def smuggled(tenant: str) -> str:
        return "ungoverned"

    with pytest.raises(UnguardedSurfaceError, match="smuggled"):
        door.build()


def test_the_raw_server_is_not_exposed_for_registration() -> None:
    door = TenantGuardedServer(FastMCP("closed"), authorizer=_RecordingAuthorizer())
    assert not hasattr(door, "fastmcp")
    assert not hasattr(door, "untenanted")


def test_a_registration_without_an_action_or_a_resource_is_a_type_error() -> None:
    """No defaulted registration: the keyword-only parameters have no defaults,
    so a surface cannot be added without its author stating all of them."""
    door = TenantGuardedServer(FastMCP("closed"), authorizer=_RecordingAuthorizer())
    for missing in ("action", "subject", "resource", "mutating"):
        kwargs: dict[str, Any] = {
            "name": "t",
            "action": ACTION_ARTIFACT_READ,
            "subject": door.from_grant(),
            "resource": door.resource_route(),
            "mutating": False,
        }
        del kwargs[missing]
        with pytest.raises(TypeError):
            door.tool(**kwargs)


def test_the_wrapper_itself_takes_no_defaulted_authorizer() -> None:
    """§2 P4 at the wrapper: there is no arm in which the authorizer is absent."""
    parameter = inspect.signature(TenantGuardedServer).parameters["authorizer"]
    assert parameter.default is inspect.Parameter.empty
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    with pytest.raises(TypeError):
        TenantGuardedServer(FastMCP("no-authorizer"))  # type: ignore[call-arg]


# --- stdio: a stated identity may be minted read kinds and nothing else -------


def _ambient() -> Any:
    return auth_context_var.set(
        AuthenticatedUser(
            ambient_stdio_identity(
                credential="c", principal_id=PRINCIPAL, scope=SCOPE, tenant=TENANT
            )
        )
    )


def test_an_ambient_identity_is_minted_a_read_kind() -> None:
    probe = _probe()
    reset = _ambient()
    try:
        _call(probe, "read_it", {"tenant": TENANT, "content_address": RESOURCE})
    finally:
        auth_context_var.reset(reset)
    (authorized,) = probe.received
    assert authorized.kind in READ_KINDS


def test_an_ambient_identity_is_refused_a_mutating_surface_before_any_mint() -> None:
    """The refusal precedes the authorizer, so a stated identity is never even
    decided for a mutating kind, let alone minted one."""
    probe = _probe()
    reset = _ambient()
    try:
        refused = _refusal(
            lambda: _call(probe, "write_it", {"artifact_class": "c", "name": "n"})
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, AmbientMutationRefused)
    assert probe.authorizer.asked == []
    assert probe.received == []


def test_a_mutating_kind_cannot_be_registered_as_a_read_surface() -> None:
    """The hole a per-site boolean would leave: a write action registered
    ``mutating=False`` would let an ambient identity be minted a write kind.
    The registration refuses the disagreement, so the ambient rule keys off a
    flag that cannot be false for a mutating kind."""
    door = TenantGuardedServer(FastMCP("reg"), authorizer=_RecordingAuthorizer())
    with pytest.raises(ValueError, match="mutating"):

        @door.tool(
            name="t",
            action=ACTION_ARTIFACT_WRITE,
            subject=door.from_grant(),
            resource=door.resource_route(),
            mutating=False,
        )
        def t(authorized: Authorized[ArtifactWrite]) -> str:
            return ""


def test_every_exported_kind_is_classified_read_or_mutating() -> None:
    """A roster, not a count: a kind added to the seam and left unclassified
    reads as mutating (the fail-closed direction) — this test makes the
    omission visible rather than silent."""
    exported = {
        getattr(capability, name)
        for name in capability.__all__
        if isinstance(getattr(capability, name), type)
        and issubclass(getattr(capability, name), ActionKind)
        and getattr(capability, name) is not ActionKind
    }
    mutating = {
        capability.ArtifactWrite,
        capability.AgentDeclare,
        capability.ConfigRegister,
        capability.HitlSubmit,
        capability.SkillCatalogRegister,
        capability.SkillGrant,
        capability.SkillRevoke,
        capability.Execute,
        capability.Resume,
        capability.ReplayMint,
    }
    assert READ_KINDS & mutating == frozenset()
    unclassified = exported - READ_KINDS - mutating
    assert unclassified == set(), sorted(kind.__name__ for kind in unclassified)


# --- §6 the round-trip, with the real library objects and no subclass --------


def test_the_round_trip_from_grant_to_mint_uses_the_librarys_own_token() -> None:
    """``TokenGrant(tenants=)`` → ``verify_token`` → ``AccessToken.claims`` →
    ``get_access_token()`` → ``granted_tenants`` → the wrapper mints a genuine
    ``Authorized`` whose tenant is a member of the grant's set. Every object
    is the real one; nothing is subclassed or stubbed."""
    grant = TokenGrant(client_id=PRINCIPAL, scopes=(SCOPE,), tenants=frozenset({TENANT, FOREIGN}))
    verifier = SourceBackedTokenVerifier(source=StaticTokenSource(grants={"tok": grant}))
    token = anyio.run(verifier.verify_token, "tok")
    assert isinstance(token, AccessToken)
    authorizer = authorizer_granting(tenants=(TENANT, FOREIGN), scopes=(SCOPE,))
    probe = _probe(authorizer=authorizer)
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        _call(probe, "read_it", {"tenant": FOREIGN, "content_address": RESOURCE})
    finally:
        auth_context_var.reset(reset)
    (authorized,) = probe.received
    assert type(authorized) is Authorized
    assert authorized.tenant in grant.tenants
    assert authorized.tenant == FOREIGN
    assert authorized.principal == grant.client_id
    verify(authorized, kind=ArtifactRead, resource=RESOURCE)


def test_the_round_trip_with_a_single_tenant_grant_and_no_tenant_on_the_wire() -> None:
    grant = TokenGrant(client_id=PRINCIPAL, scopes=(SCOPE,), tenants=frozenset({TENANT}))
    verifier = SourceBackedTokenVerifier(source=StaticTokenSource(grants={"tok": grant}))
    token = anyio.run(verifier.verify_token, "tok")
    assert token is not None
    probe = _probe(authorizer=authorizer_granting(tenants=(TENANT,), scopes=(SCOPE,)))
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        _call(probe, "write_it", {"artifact_class": "c", "name": "n"})
    finally:
        auth_context_var.reset(reset)
    (authorized,) = probe.received
    assert authorized.tenant == TENANT
    verify(authorized, kind=ArtifactWrite, resource="c/n")


def test_the_real_authorizer_denies_a_scope_the_mapping_does_not_name() -> None:
    """The deny side of the round-trip through the real interpreter: a real
    grant whose scope the mapping does not grant is refused at the mint site
    with the shared constant, and the body never runs."""
    grant = TokenGrant(client_id=PRINCIPAL, scopes=("ccf:other",), tenants=frozenset({TENANT}))
    probe = _probe(authorizer=authorizer_granting(tenants=(TENANT,), scopes=(SCOPE,)))
    reset = _as_grant(grant)
    try:
        refused = _refusal(
            lambda: _call(probe, "read_it", {"tenant": TENANT, "content_address": RESOURCE})
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, ActionUnauthorizedRefused)
    assert probe.received == []


def test_the_real_authorizer_decides_on_the_declared_action() -> None:
    """The same grant, allowed for reads and not for invocation: the action in
    the decision is the registration's, so a mapping can say *this scope reads
    and does not write*."""
    authorizer = authorizer_granting(
        tenants=(TENANT,), scopes=(SCOPE,), actions=(ACTION_ARTIFACT_READ,)
    )
    probe = _probe(authorizer=authorizer)
    reset = _as_grant(_grant(TENANT))
    try:
        _call(probe, "read_it", {"tenant": TENANT, "content_address": RESOURCE})
        refused = _refusal(
            lambda: _call(probe, "write_it", {"artifact_class": "c", "name": "n"})
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, ActionUnauthorizedRefused)
    assert [a.kind for a in probe.received] == [ArtifactRead]
    assert kind_for_action(ACTION_WORKFLOW_INVOKE) is Execute  # the vocabulary is the seam's
