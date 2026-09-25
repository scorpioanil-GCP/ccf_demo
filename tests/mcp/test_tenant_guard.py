"""Tenant entitlement is mandatory on every MCP surface (SEC-018).

``SEC-018`` is the finding of record: :class:`~ccf_runtime.mcp.auth.TokenGrant`
carried ``client_id`` and ``scopes`` and **no tenant**, so a bearer minted for
tenant A reached tenant B's artifacts, queue and products. Authentication was
real and answered the wrong question — *who are you*, never *whose data is
this*.

``D-IMPL-353`` made the guard the MCP **mint site**: the tenancy floor below
still runs first, and what a body receives afterwards is a capability minted
for its declared action (``test_mint_site.py``). This module keeps the floor's
own evidence.

Every assertion below is drafted from *what would fail here*:

=========================================  ===================================
Invariant / finding                        What would fail here
=========================================  ===================================
``SEC-018``                                a verified bearer could name a
                                           foreign tenant on the wire and be
                                           served
the mandatory-wrapper property             a handler could reach the wire
                                           having never consulted the grant,
                                           because its author did not call a
                                           helper
fail-closed by default                     a grant carrying no tenant at all
                                           could be read as carrying every
                                           tenant
no untenanted reading                      a surface could be registered with
                                           no tenant to mint a capability for
``D-IMPL-129``                             the three agent/replay tools could
                                           stay ungated after the vocabulary
                                           they needed arrived
stdio ambient identity                     a process-ownership identity could
                                           authorize a *mutation* it never
                                           presented a credential for
=========================================  ===================================

Tenant, principal, scope and token names are test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from ccf.authz.actions import ACTION_ARTIFACT_READ, ACTION_ARTIFACT_WRITE
from ccf.authz.capability import ArtifactRead, ArtifactWrite, Authorized
from ccf_runtime.mcp.auth import (
    SourceBackedTokenVerifier,
    StaticTokenSource,
    TokenGrant,
)
from ccf_runtime.mcp.tenancy import (
    AmbientMutationRefused,
    CrossTenantRefused,
    TenantGuardedServer,
    TenantGuardViolation,
    TenantlessGrantRefused,
    UnverifiedTenantCallerRefused,
    ambient_stdio_identity,
    granted_tenants,
    tenant_claims,
    unguarded_surfaces,
)
from tests.mcp.guarded_servers import authorizer_granting

TENANT = "tenant-guard-own"
FOREIGN = "tenant-guard-foreign"
PRINCIPAL = "principal-guard"
SCOPE = "ccf:tenant-guard"

#: Lane HITL-DOOR owns ``hitl_server.py`` and adopts the wrapper's mint-site
#: API there (``authorizer=`` at construction; bodies taking ``authorized``;
#: ``door.build()``). Until that lands, the HITL leg of every roster test is
#: an expected failure that turns into a failure the moment it does — the
#: marker is the join's to remove, not to keep.
HITL_JOIN = (
    "join: awaits Lane HITL-DOOR adopting TenantGuardedServer's mint-site API"
    " in runtime/ccf_runtime/mcp/hitl_server.py (D-IMPL-353 §1.2 / §2 P4)"
)
SHIPPED_SERVERS = (
    "artifact",
    "hitl",
    "experience",
    "egress",
)


def _auth_settings() -> AuthSettings:
    return AuthSettings(
        issuer_url=AnyHttpUrl("https://issuer.invalid"),
        resource_server_url=AnyHttpUrl("https://guard.invalid/mcp"),
        required_scopes=[SCOPE],
    )


def _as_grant(grant: TokenGrant | None) -> Any:
    """Run under the auth contextvar the bearer middleware would populate.

    ``None`` stands for *no verified identity reached this call at all*, which
    is the state the middleware refuses before a handler runs and which the
    guard must refuse again on its own account.
    """
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

    ``FastMCP`` re-raises a handler's exception as its own ``ToolError`` or
    ``ResourceError``, so the guard's typed refusal arrives wrapped. Asserting
    on the wrapped refusal keeps these tests typed: a message match would pass
    for any refusal whose prose happened to line up, which is exactly how a
    test stops distinguishing *refused for the right reason* from *refused*.

    **Both chains are walked, and the resource-template path is why.** The tool
    path chains with ``from e`` so ``__cause__`` carries it; the template path
    re-wraps twice into a plain ``ValueError`` with no explicit chaining, so
    only ``__context__`` holds the original. A helper that read ``__cause__``
    alone would return the wrapper for every resource-template refusal and the
    test would report a *type* failure for a guard that fired correctly.
    """
    try:
        operation()
    except BaseException as raised:  # noqa: BLE001 - the subject under test
        seen: list[BaseException] = []
        current: BaseException | None = raised
        while current is not None and current not in seen:
            if isinstance(current, TenantGuardViolation):
                return current
            seen.append(current)
            current = current.__cause__ or current.__context__
        return raised
    raise AssertionError("the call was served; no refusal to inspect")


def _grant(*tenants: str) -> TokenGrant:
    return TokenGrant(
        client_id=PRINCIPAL, scopes=(SCOPE,), tenants=frozenset(tenants)
    )


# --- the grant itself ------------------------------------------------------


def test_the_grant_carries_tenants() -> None:
    """``TokenGrant`` names whose data its bearer may reach.

    The whole of ``SEC-018`` in one assertion: before this field the contract
    had no place to put the answer, so no surface could consult it.
    """
    grant = _grant(TENANT)
    assert grant.tenants == frozenset({TENANT})


def test_a_grant_names_no_tenant_by_default_and_that_means_none() -> None:
    """Absent is empty, and empty is *no* tenant — never *every* tenant.

    The direction is the security property. A deployment that forgets to scope
    a credential gets a credential that opens nothing, which is loud; the other
    reading is silent and total.
    """
    assert TokenGrant(client_id=PRINCIPAL, scopes=()).tenants == frozenset()


def test_the_verifier_carries_tenants_into_the_access_token() -> None:
    """The library's ``claims`` is the channel, so no library change is needed.

    ``AccessToken`` already carries ``claims``; the SDK's gap was never the
    transport. A verifier that dropped the tenant here would leave every
    downstream guard reading an empty set and refusing everything — the failure
    would be loud, but the tenant would never arrive.
    """
    verifier = SourceBackedTokenVerifier(
        source=StaticTokenSource(grants={"tok": _grant(TENANT, FOREIGN)})
    )
    token = anyio.run(verifier.verify_token, "tok")
    assert token is not None
    assert granted_tenants(token) == frozenset({TENANT, FOREIGN})


def test_the_verifier_carries_what_it_attested_about_authentication() -> None:
    """``D-IMPL-353`` §2 P6: the approver's assurance comes from the VERIFIED
    credential, never from a request body. The grant states how its bearer
    authenticated; the verifier carries that statement verbatim into the
    token's claims under ``AUTHENTICATION_CLAIM``, where the HITL doors read
    it — and only there.
    """
    from ccf.hitl.principal import AUTHENTICATION_CLAIM, AuthenticationClaims

    attested = AuthenticationClaims(
        identity_provider_ref="idp-guard",
        method="webauthn",
        assurance_level="aal3",
        session_ref="session-guard-1",
    )
    verifier = SourceBackedTokenVerifier(
        source=StaticTokenSource(
            grants={
                "tok": TokenGrant(
                    client_id=PRINCIPAL,
                    scopes=(SCOPE,),
                    tenants=frozenset({TENANT}),
                    authentication=attested,
                )
            }
        )
    )
    token = anyio.run(verifier.verify_token, "tok")
    assert token is not None
    assert (token.claims or {})[AUTHENTICATION_CLAIM] == attested.model_dump(mode="json")
    # The tenant axis is untouched by the second claim.
    assert granted_tenants(token) == frozenset({TENANT})


def test_a_grant_stating_no_authentication_writes_no_claim() -> None:
    """A credential whose verifier said nothing carries nothing — the doors
    refuse to mint a binding from silence rather than fill the blank. The
    sentinel is hash-transparent: every grant minted before the field existed
    said nothing, and its canonical bytes do not move."""
    from ccf.contracts.canonical import canonical_bytes
    from ccf.hitl.principal import AUTHENTICATION_CLAIM

    silent = _grant(TENANT)
    assert silent.authentication is None
    verifier = SourceBackedTokenVerifier(
        source=StaticTokenSource(grants={"tok": silent})
    )
    token = anyio.run(verifier.verify_token, "tok")
    assert token is not None
    assert AUTHENTICATION_CLAIM not in (token.claims or {})
    assert b"authentication" not in canonical_bytes(silent)


# --- the guard -------------------------------------------------------------


class _Guarded:
    """A server whose every surface is registered through the wrapper."""

    def __init__(self) -> None:
        door = TenantGuardedServer(
            FastMCP(
                "tenant-guard",
                stateless_http=True,
                json_response=True,
                token_verifier=SourceBackedTokenVerifier(
                    source=StaticTokenSource(grants={"tok": _grant(TENANT)})
                ),
                auth=_auth_settings(),
            ),
            authorizer=authorizer_granting(tenants=(TENANT, FOREIGN), scopes=(SCOPE,)),
        )
        entered: list[str] = []

        @door.tool(
            name="read_it",
            action=ACTION_ARTIFACT_READ,
            subject=door.from_argument("tenant"),
            resource=door.resource_route(),
            mutating=False,
        )
        def read_it(authorized: Authorized[ArtifactRead]) -> str:
            entered.append("read_it")
            return json.dumps({"read": authorized.tenant})

        @door.tool(
            name="write_it",
            action=ACTION_ARTIFACT_WRITE,
            subject=door.from_argument("tenant"),
            resource=door.resource_argument("value"),
            mutating=True,
        )
        def write_it(authorized: Authorized[ArtifactWrite], value: str) -> str:
            entered.append("write_it")
            return json.dumps({"wrote": value, "tenant": authorized.tenant})

        @door.tool(
            name="declared_it",
            action=ACTION_ARTIFACT_READ,
            subject=door.declared(TENANT),
            resource=door.resource_route(),
            mutating=False,
        )
        def declared_it(authorized: Authorized[ArtifactRead]) -> str:
            entered.append("declared_it")
            return json.dumps({"declared": authorized.tenant})

        self.door = door
        self.server = door.build()
        self.entered = entered


def _call(guarded: _Guarded, tool: str, args: dict[str, Any]) -> Any:
    return anyio.run(guarded.server.call_tool, tool, args)


def test_the_guard_admits_a_tenant_the_grant_carries() -> None:
    """The positive control. Without it every refusal below proves nothing."""
    guarded = _Guarded()
    reset = _as_grant(_grant(TENANT))
    try:
        _, structured = _call(guarded, "read_it", {"tenant": TENANT})
    finally:
        auth_context_var.reset(reset)
    assert json.loads(structured["result"])["read"] == TENANT


def test_the_guard_refuses_a_tenant_the_grant_does_not_carry() -> None:
    """``SEC-018`` itself: a verified bearer names a foreign tenant.

    The argument is the caller's and stays the caller's — what changed is that
    naming a foreign tenant is now *decided against the grant* rather than
    trusted, and the body never receives a capability for it.
    """
    guarded = _Guarded()
    reset = _as_grant(_grant(TENANT))
    try:
        refused = _refusal(lambda: _call(guarded, "read_it", {"tenant": FOREIGN}))
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, CrossTenantRefused)
    assert guarded.entered == []


def test_a_grant_carrying_no_tenant_reaches_nothing() -> None:
    """Fail-closed, asserted rather than assumed."""
    guarded = _Guarded()
    reset = _as_grant(_grant())
    try:
        refused = _refusal(lambda: _call(guarded, "read_it", {"tenant": TENANT}))
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, TenantlessGrantRefused)


def test_an_unverified_caller_reaches_nothing() -> None:
    """The guard refuses on its own account, not on the middleware's promise."""
    guarded = _Guarded()
    reset = _as_grant(None)
    try:
        refused = _refusal(lambda: _call(guarded, "read_it", {"tenant": TENANT}))
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, UnverifiedTenantCallerRefused)


def test_a_declared_subject_is_decided_against_the_grant_too() -> None:
    """A surface with no tenant argument is still a tenant's surface.

    ``get_lineage`` and ``get_replay_record`` take no arguments at all. Absence
    of a client parameter reduces steerability and never disclosure, so the
    deployment-declared tenant is what the grant is checked against.
    """
    guarded = _Guarded()
    reset = _as_grant(_grant(FOREIGN))
    try:
        refused = _refusal(lambda: _call(guarded, "declared_it", {}))
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, CrossTenantRefused)


def test_the_guard_runs_before_the_body() -> None:
    """A refused caller moves nothing — the body is never entered."""
    guarded = _Guarded()
    reset = _as_grant(_grant(TENANT))
    try:
        refused = _refusal(
            lambda: _call(guarded, "write_it", {"tenant": FOREIGN, "value": "v"})
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, CrossTenantRefused)
    assert guarded.entered == []


def test_the_input_schema_is_the_wires_not_the_bodys() -> None:
    """The guard is invisible to the protocol — and so is the capability.

    A wrapper that flattened handlers to ``*args, **kwargs`` would erase every
    tool's declared arguments; one that published the body's own signature
    would put ``authorized`` on the wire and take ``tenant`` off it. The
    schema carries exactly the wire parameters: the tenant the caller names
    and the body's own arguments, nothing else.
    """
    guarded = _Guarded()
    tools = {tool.name: tool for tool in anyio.run(guarded.server.list_tools)}
    assert set(tools["write_it"].inputSchema["required"]) == {"tenant", "value"}
    assert set(tools["read_it"].inputSchema["required"]) == {"tenant"}
    assert "required" not in tools["declared_it"].inputSchema or (
        tools["declared_it"].inputSchema["required"] == []
    )
    for tool in tools.values():
        assert "authorized" not in tool.inputSchema.get("properties", {})


# --- the wrapper is mandatory ----------------------------------------------


def test_a_surface_registered_behind_the_wrappers_back_is_caught() -> None:
    """The instrument that makes the wrapper mandatory rather than customary.

    A tool body that must *remember* to check tenancy is the defect class
    ``SEC-018`` belongs to; the repair is only real if forgetting is
    detectable. The ledger the wrapper keeps is compared against ``FastMCP``'s
    own registry, so a handler registered on the underlying server — the one
    way to bypass the guard — appears in the registry and not in the ledger.
    ``test_mint_site.py`` proves the same comparison is a boot failure at
    ``build``; this is the instrument on its own.
    """
    guarded = _Guarded()
    assert unguarded_surfaces(guarded.server) == frozenset()

    @guarded.server.tool(name="smuggled")
    def smuggled(tenant: str) -> str:
        return "ungoverned"

    assert unguarded_surfaces(guarded.server) == frozenset({"smuggled"})


@pytest.mark.parametrize("builder", SHIPPED_SERVERS)
def test_every_shipped_server_registers_every_surface_through_the_guard(
    builder: str, tmp_path: Any
) -> None:
    """All four shipped servers, every registration, no exceptions.

    Named per server rather than asserted over a total, because a count that
    is right with a wrong member audits clean forever (``verify rosters, not
    counts``). A builder returns ``door.build()``, which raises on a smuggled
    surface — so building at all is the assertion, and the explicit check is
    the instrument read back.
    """
    from tests.mcp.guarded_servers import build_for

    server = build_for(builder, tmp_path)
    assert unguarded_surfaces(server) == frozenset()


def test_every_server_builder_in_the_package_is_on_the_roster() -> None:
    """A fifth MCP server cannot ship uncovered by the test above.

    The roster test drives four named builders. That is a roster rather than a
    count, which is right — but it is a roster of what exists *today*, and a
    new ``build_*_server`` added to this package would simply not be driven by
    it. The guard would be absent and every test would stay green, which is the
    shape of a gate that stops being one without failing.

    So the population is derived from the package rather than restated: every
    public ``build_*_server`` found under ``runtime/ccf_runtime/mcp/`` must
    appear in ``tests/mcp/guarded_servers.py``'s roster. Adding a server and
    forgetting to cover it fails here.
    """
    import re

    from tests.mcp import guarded_servers

    package = pathlib.Path(guarded_servers.__file__).parents[2] / (
        "runtime/ccf_runtime/mcp"
    )
    found = {
        match.group(1)
        for module in package.glob("*.py")
        for match in re.finditer(
            r"^def (build_\w*server)\(", module.read_text(), re.M
        )
    }
    covered = set(
        re.findall(
            r"from ccf_runtime\.mcp\.\w+ import \(?[\s\w,]*?(build_\w*server)",
            pathlib.Path(guarded_servers.__file__).read_text(),
        )
    )
    assert found, "no server builder was found at all — the glob is wrong"
    assert found <= covered, (
        f"server builders with no tenant-guard coverage: {sorted(found - covered)};"
        " add them to tests/mcp/guarded_servers.py::build_for"
    )


@pytest.mark.parametrize("builder", SHIPPED_SERVERS)
def test_every_surface_on_every_shipped_server_names_a_tenant_reading(
    builder: str, tmp_path: Any
) -> None:
    """There is no untenanted reading any more (``D-IMPL-353`` §1.3).

    ``SEC-018`` pinned a two-member roster of surfaces that carried no tenant;
    the capability made that reading impossible — every mint names one tenant
    — so the roster is now empty by construction, and this asserts it over the
    ledger of every shipped server rather than over a pinned list: each entry
    selects its tenant from the wire, from the declaration, or from the sole
    member of the grant.
    """
    from ccf_runtime.mcp import tenancy
    from tests.mcp.guarded_servers import build_for

    server = build_for(builder, tmp_path)
    ledger = tenancy._LEDGERS[server]
    assert ledger, f"{builder}: an empty ledger measures nothing"
    for name, surface in ledger.items():
        readings = (
            surface.subject.argument is not None,
            surface.subject.declared is not None,
            surface.subject.grant,
        )
        assert sum(readings) == 1, (builder, name, surface.subject)


# --- the specific holes the finding named ----------------------------------


def test_the_three_agent_and_replay_tools_are_tenant_guarded(
    tmp_path: Any,
) -> None:
    """``D-IMPL-129`` closed on its tenancy limb.

    That ruling declined to decide ``list_agents``, ``invoke_agent`` and
    ``get_replay_record`` against ``ProductEntitlementPolicy``, whose grants
    say nothing about agents or replay records — inventing that semantic is
    what CLAUDE.md §11 forbids. It remains declined. **Tenancy is a different
    question and needs no new vocabulary**: the grant now carries the tenants
    its bearer may reach, and these three reach a tenant's agent population, a
    tenant's agent dispatch and a tenant's replay record.
    """
    from ccf_runtime.mcp.experience import (
        GET_REPLAY_RECORD_TOOL,
        INVOKE_AGENT_TOOL,
        LIST_AGENTS_TOOL,
    )
    from tests.mcp.guarded_servers import build_for

    server = build_for("experience", tmp_path)
    # Each case pairs a call with a grant that does NOT carry the tenant that
    # call acts on. The two argument-carrying tools act on the tenant they are
    # handed; `get_replay_record` carries no arguments and acts on the tenant
    # the deployment declared it under, so for that one the grant is what has
    # to differ.
    cases = (
        (LIST_AGENTS_TOOL, {"tenant": FOREIGN}, _grant(TENANT)),
        (
            INVOKE_AGENT_TOOL,
            {
                "tenant": FOREIGN,
                "definition_key": "k",
                "definition_version": "1.0.0",
                "skill": "s",
                "arguments": {},
            },
            _grant(TENANT),
        ),
        (GET_REPLAY_RECORD_TOOL, {}, _grant(FOREIGN)),
    )
    for tool, args, grant in cases:
        reset = _as_grant(grant)
        try:
            refused = _refusal(
                lambda t=tool, a=args: anyio.run(server.call_tool, t, a)
            )
        finally:
            auth_context_var.reset(reset)
        assert isinstance(refused, CrossTenantRefused), tool


def test_the_hitl_tenant_check_no_longer_waits_for_an_authorizer(
    tmp_path: Any,
) -> None:
    """The HITL door's tenant check was inert when no authorizer was bound.

    ``_enforce_tenant_authz`` opened ``if authorizer is None: return`` and the
    builder's ``authorizer`` defaulted to ``None`` — so the door's tenant
    check was optional *by construction*, its applicability decided by the
    deployer. Under ``D-IMPL-353`` there is no ``authorizer=None`` arm at all:
    the wrapper takes one at construction and the body receives a capability
    or nothing.
    """
    from ccf_runtime.mcp.hitl_server import HITL_QUEUE_URI_TEMPLATE
    from tests.mcp.guarded_servers import build_for

    server = build_for("hitl", tmp_path)
    foreign_queue = HITL_QUEUE_URI_TEMPLATE.format(tenant=FOREIGN)
    reset = _as_grant(_grant(TENANT))
    try:
        refused = _refusal(
            lambda: anyio.run(server.read_resource, foreign_queue)
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, CrossTenantRefused)


# --- stdio ambient identity ------------------------------------------------


def test_the_stdio_ambient_identity_is_scoped_to_one_tenant() -> None:
    """Process ownership authorizes the door's own tenant and no other."""
    identity = ambient_stdio_identity(
        credential="c", principal_id=PRINCIPAL, scope=SCOPE, tenant=TENANT
    )
    assert granted_tenants(identity) == frozenset({TENANT})


def test_the_stdio_ambient_identity_cannot_reach_a_mutating_surface() -> None:
    """Ambient identity reads; it does not write.

    MCP stdio carries no authentication channel, so ``serve_stdio`` states who
    its caller is rather than verifying it — the transport's boundary is
    process ownership. That is a defensible warrant for *reading* what the
    child was spawned to serve and not for *mutating* on an authority nobody
    presented. The loopback transport is untouched: its bearer auth is real and
    its identity is not ambient, so nothing here narrows it.
    """
    guarded = _Guarded()
    reset = auth_context_var.set(
        AuthenticatedUser(
            ambient_stdio_identity(
                credential="c",
                principal_id=PRINCIPAL,
                scope=SCOPE,
                tenant=TENANT,
            )
        )
    )
    try:
        _, structured = _call(guarded, "read_it", {"tenant": TENANT})
        assert json.loads(structured["result"])["read"] == TENANT
        refused = _refusal(
            lambda: _call(guarded, "write_it", {"tenant": TENANT, "value": "v"})
        )
        assert isinstance(refused, AmbientMutationRefused)
    finally:
        auth_context_var.reset(reset)
    assert guarded.entered == ["read_it"]


def test_a_remote_bearer_cannot_forge_or_clear_the_ambient_marker() -> None:
    """The marker is the verifier's to set, never the wire's.

    Claims reach a handler only from ``verify_token``, and this SDK's verifier
    composes them from the deployment's own ``TokenGrant``. A remote caller
    supplies a token string and nothing else, so it can neither plant the
    ambient marker nor strip it — which matters in the one direction that
    counts: stripping it is what would buy a mutation.
    """
    verifier = SourceBackedTokenVerifier(
        source=StaticTokenSource(grants={"tok": _grant(TENANT)})
    )
    token = anyio.run(verifier.verify_token, "tok")
    assert token is not None
    ambient = ambient_stdio_identity(
        credential="c", principal_id=PRINCIPAL, scope=SCOPE, tenant=TENANT
    )
    assert set(ambient.claims or {}) - set(token.claims or {})
