"""The mandatory guard over every MCP surface — and the MCP mint site.

**SDK-defined** (CLAUDE.md §7.1, §8.3, §11; ``SEC-018``; ``D-IMPL-353`` §1.1).
Two findings meet in this module and it answers both with one mechanism.

``SEC-018``: :class:`~ccf_runtime.mcp.auth.TokenGrant` carried ``client_id``
and ``scopes`` and **no tenant**, so a bearer minted for tenant A reached
tenant B's artifacts, queue and products. The library's authentication was
never the weakness — ``mcp==1.28.1`` engages ``RequireAuthMiddleware``
correctly on the HTTP transports. The gap was that the thing it verified could
not express whose data its bearer was entitled to.

``D-IMPL-353``: a checklist of doors each remembering to ask an authorizer does
not ensure anything. Authorization is a **capability**,
:class:`~ccf_runtime.authz.capability.Authorized`, minted at exactly two sites
after the deployment's authorizer returns *allowed* — the HTTP
:class:`~ccf_runtime.http_api.gate.AuthorizationGate` and **this wrapper** —
and required, as a typed first parameter with no default, by every handle that
mutates or reads tenant data. A body registered here has no ``authorizer``
parameter and no ``tenant`` argument. It has ``authorized``, or it has nothing
to hand any handle.

Why a wrapper, and not a helper
-------------------------------
The obvious repair is a function each handler calls. That repair reproduces
the defect class it is repairing: a tool body that must *remember* to consult
the grant has its guard's applicability decided by its author. So the guard is
not offered to handlers; it is **installed on them at registration**, and the
capability a body needs to do anything is minted by that installation and by
nothing else a body can reach.

Three independent controls make that stick:

1. :meth:`TenantGuardedServer.tool` and :meth:`TenantGuardedServer.resource`
   take ``action``, ``subject``, ``resource`` and ``mutating`` as **required
   keyword arguments**. There is no defaulted registration, so a surface cannot
   be added without its author stating what it does, whose tenant it acts on,
   what it acts on, and whether it writes.
2. **Registration behind the wrapper is a boot failure** (§2 P9).
   :func:`unguarded_surfaces` compares the wrapper's ledger against
   ``FastMCP``'s own registry, and :meth:`TenantGuardedServer.build` — the only
   way a builder obtains the server to mount — raises if the two disagree. So
   does the constructor, for a server that carried surfaces before it was
   wrapped. The raw ``FastMCP`` is not exposed for registration.
3. A body's first parameter is the capability. The wrapper mints it for the
   body's **declared** action (:func:`~ccf_runtime.authz.capability
   .kind_for_action`) on the body's **declared** resource under the **selected**
   tenant, and mints nothing on any refusal. What the body then hands to a
   handle is verified there by identity (§1.5c) — a ``list_agents`` capability
   presented to a write handle dies before the handle's first statement.

What this decides, in order
---------------------------
verified identity → ambient-mutation refusal → tenant selection (§1.3) →
resource extraction → the authorizer's four-axis decision → mint → body. The
order is the property: the tenancy floor runs before the authorizer is asked,
so a deployment's authorizer can never be what lets a cross-tenant call
through, and the ambient refusal runs before the mint, so a stated stdio
identity is never even decided for a mutating kind.

**Exactly one tenant per capability** (§1.3). ``TokenGrant.tenants`` is a set —
an operator credential legitimately spans tenants — but a *decision* is about
one. The wrapper selects it: the request names one and it is a member
(:meth:`~TenantGuardedServer.from_argument`); the deployment declared it and it
is a member (:meth:`~TenantGuardedServer.declared`); or the surface carries no
tenant and the grant holds exactly one (:meth:`~TenantGuardedServer.from_grant`).
Otherwise it **refuses as ambiguous — it does not pick.** There is no
*untenanted* reading any more: every capability names its tenant.

Tenant identifiers, scope vocabulary, action grants and token material are
deployment values in their entirety. This module holds none of them (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import functools
import inspect
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Final, TypeVar
from weakref import WeakKeyDictionary

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.fastmcp import FastMCP

from ccf.contracts.canonical import content_hash
from ccf.authz.capability import (
    ActionKind,
    AgentList,
    AgentRead,
    AgentVersions,
    ArtifactRead,
    Authorized,
    BackendsRead,
    ConfigKeysRead,
    ConfigResolve,
    ConfigVersionsRead,
    DocsRead,
    HealthRead,
    HitlQueueRead,
    OpenApiRead,
    ProductRetrieve,
    ReplayRead,
    SchemaList,
    SchemaRead,
    SkillCatalogRead,
    WorkflowStatusRead,
    kind_for_action,
    mint,
)
from ccf_runtime.authz.protocol import TenantAuthorizerProtocol
from ccf_runtime.http_api.errors import ERROR_TENANT_UNAUTHORIZED, refusal_detail
from ccf_runtime.mcp.auth import (
    AMBIENT_STDIO_CLAIM,
    TENANT_CLAIM,
    TokenGrant,
    granted_tenants,
    is_ambient_stdio,
    tenant_claims,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "AMBIENT_STDIO_CLAIM",
    "READ_KINDS",
    "ActionUnauthorizedRefused",
    "AmbientMutationRefused",
    "AmbiguousTenantRefused",
    "CrossTenantRefused",
    "GuardedSurface",
    "ResourceSubject",
    "ResourceUnreadableRefused",
    "TENANT_CLAIM",
    "TenantGuardViolation",
    "TenantGuardedServer",
    "TenantSubject",
    "TenantlessGrantRefused",
    "UnguardedSurfaceError",
    "UnverifiedTenantCallerRefused",
    "ambient_stdio_identity",
    "granted_tenants",
    "is_ambient_stdio",
    "tenant_claims",
    "unguarded_surfaces",
]

_F = TypeVar("_F", bound=Callable[..., Any])

#: The name every body's first parameter carries. Named once so the
#: registration check and the call site agree on it.
_CAPABILITY_PARAMETER: Final[str] = "authorized"

#: The kinds a **stated** (ambient stdio) identity may be minted. Process
#: ownership warrants reading what the child was spawned to serve; it does not
#: warrant a write on an authority nobody presented. **Anything absent from
#: this roster is mutating** — the fail-closed direction — and
#: :meth:`TenantGuardedServer.tool` refuses to register a surface whose action
#: mints an absent kind as ``mutating=False``, so the per-site flag the ambient
#: rule keys off cannot be false for a mutating kind. Pinned as a roster by
#: ``tests/mcp/test_mint_site.py``, which classifies every exported kind.
READ_KINDS: Final[frozenset[type[ActionKind]]] = frozenset(
    {
        AgentList,
        AgentRead,
        AgentVersions,
        ArtifactRead,
        BackendsRead,
        ConfigKeysRead,
        ConfigResolve,
        ConfigVersionsRead,
        DocsRead,
        HealthRead,
        HitlQueueRead,
        OpenApiRead,
        ProductRetrieve,
        ReplayRead,
        SchemaList,
        SchemaRead,
        SkillCatalogRead,
        WorkflowStatusRead,
    }
)


class TenantGuardViolation(RuntimeError):
    """Base for every refusal this guard raises.

    One base so a door that wants to translate all of them into its own
    protocol-native shell has a single thing to catch, and typed leaves so a
    test can tell *refused for the right reason* from *refused*.
    """


class UnverifiedTenantCallerRefused(TenantGuardViolation):
    """No verified access token accompanies this call.

    The bearer middleware refuses this before a handler runs. The guard refuses
    it again on its own account rather than on the middleware's promise,
    because a handler reachable by any path that skips the middleware — stdio,
    a mounted app, an in-process call — would otherwise be ungoverned.
    """


class TenantlessGrantRefused(TenantGuardViolation):
    """The verified grant names no tenant, so it reaches nothing.

    Fail-closed, and the loud direction: a deployment that forgot to scope a
    credential finds out immediately instead of shipping one that opens
    everything.
    """


class CrossTenantRefused(TenantGuardViolation):
    """The call acts on a tenant the verified grant does not carry.

    ``SEC-018`` itself.
    """


class AmbiguousTenantRefused(TenantGuardViolation):
    """The surface names no tenant and the grant holds more than one.

    ``D-IMPL-353`` §1.3: *the gate selects it from the grant's set — or the
    grant holds exactly one; otherwise refuse as ambiguous, the gate does not
    pick.* Choosing one would be a tenant decision the caller never made and
    the deployment never declared.
    """


class AmbientMutationRefused(TenantGuardViolation):
    """A stated (not verified) identity tried to reach a mutating surface.

    See :func:`ambient_stdio_identity` for why stdio has a stated identity at
    all, and why its warrant stops at reading. Raised **before** the authorizer
    is asked, so a stated identity is never minted a mutating kind.
    """


class ResourceUnreadableRefused(TenantGuardViolation):
    """The declared resource argument carries nothing a decision can be made on.

    A resource that is absent, empty or not a string is a **deny, never a
    skip**: the caller chooses what to send, and every choice leads to the
    check running (the HTTP gate's own rule, applied to arguments).
    """


class ActionUnauthorizedRefused(TenantGuardViolation):
    """The deployment's authorizer refused the declared action on the resource.

    The message is the shared refusal constant rendered protocol-natively
    (D-08): ``json.dumps(refusal_detail(ERROR_TENANT_UNAUTHORIZED, ...))``, the
    same body the HTTP door's 403 carries, so a client parses either door's
    denial the same way. **Nothing is minted on this path.**
    """


class UnguardedSurfaceError(RuntimeError):
    """A surface reached ``FastMCP``'s registry without going through the guard.

    Raised at construction (a server that already carried surfaces) and at
    :meth:`TenantGuardedServer.build` (a registration on the underlying server
    after wrapping). A boot failure rather than a refusal: the deployment has a
    handler on the wire with no capability behind it, and the fix is in the
    builder, not in the call.
    """


@dataclass(frozen=True)
class TenantSubject:
    """How one surface's tenant is selected — a closed, stated choice (§1.3).

    Constructed only through :meth:`TenantGuardedServer.from_argument`,
    :meth:`TenantGuardedServer.declared` and
    :meth:`TenantGuardedServer.from_grant`, so the three selections are
    enumerable and a fourth cannot appear by accident.

    Attributes:
        argument: The **wire** parameter naming the tenant, when the caller
            names it. It stays on the input schema — it selects *which* of a
            multi-tenant grant's tenants — but it is consumed by the wrapper
            and never reaches the body, which reads ``authorized.tenant``.
        declared: The tenant fixed at registration, for a surface with no
            tenant on the wire and a deployment-declared address.
        grant: ``True`` when the surface carries no tenant and declares none:
            the grant's sole tenant is the decision's, and a grant holding
            several is refused as ambiguous.
    """

    argument: str | None = None
    declared: str | None = None
    grant: bool = False


@dataclass(frozen=True)
class ResourceSubject:
    """Where the thing a surface acts on comes from — a closed, stated choice.

    The fourth axis of the decision (``SEC-002``): a scope mapping says which
    keys, addresses and classes an action reaches, so the wrapper must name the
    one this call acts on. Constructed only through the four
    :class:`TenantGuardedServer` readers.

    Attributes:
        argument: The wire parameter carrying the resource — a content
            address, a product class, a definition key.
        declared: A value fixed at registration — the class a deployment
            declared a tool's address under.
        route: ``True`` when the surface acts on no addressable subject; its
            own action id is the resource, so the axis has no exempt member.
        template: A ``str.format`` template over the wire arguments, for a
            resource spelled from several of them — the artifact store's
            ``"{artifact_class}/{name}"``, the same segments the naming key
            already uses (``D-IMPL-353`` §1.2).
    """

    argument: str | None = None
    declared: str | None = None
    route: bool = False
    template: str | None = None


@dataclass(frozen=True)
class GuardedSurface:
    """Everything one registration declared, as the ledger keeps it.

    Attributes:
        action: The door-declared action id the wrapper mints for.
        subject: How the tenant is selected.
        resource: Where the resource is read.
        mutating: Whether the surface writes.
    """

    action: str
    subject: TenantSubject
    resource: ResourceSubject
    mutating: bool


#: Each built server's ledger of guarded surfaces. Keyed weakly so a server
#: built in a test does not outlive the test.
_LEDGERS: WeakKeyDictionary[FastMCP, dict[str, GuardedSurface]] = (
    WeakKeyDictionary()
)


def ambient_stdio_identity(
    *, credential: str, principal_id: str, scope: str, tenant: str
) -> AccessToken:
    """The identity an MCP **stdio** host states for its caller.

    MCP stdio carries no authentication channel: ``FastMCP`` installs its
    bearer middleware on the HTTP app and there is no HTTP app on stdio, so a
    door that demanded a presented credential would refuse every caller. The
    transport's own security boundary is process ownership — the server is a
    child the deployment's client spawned, under the same user, on the same
    host — and stating the identity is how that boundary is made legible
    instead of smuggled.

    **What this narrows.** Two things, and the reviewers' complaint ("no
    ambient identity") is answered by both rather than by removing the
    transport's only workable identity:

    * The grant is scoped to **exactly one tenant** — the door's own. Process
      ownership authorizes the tenant the child was spawned to serve and no
      other.
    * It is **marked ambient**, and :class:`TenantGuardedServer` refuses every
      surface registered ``mutating=True`` to a marked identity **before the
      authorizer is asked** — so a stated identity may be minted a kind in
      :data:`READ_KINDS` and never a mutating one. Process ownership is a
      defensible warrant for reading what the child exists to serve; it is not
      a warrant for writing on an authority nobody presented.

    The marker cannot be forged or cleared from the wire. Claims reach a
    handler only from
    :meth:`~ccf_runtime.mcp.auth.SourceBackedTokenVerifier.verify_token`, which
    composes them from the deployment's own grant; a remote caller supplies a
    token string and nothing else.

    **The loopback transport is untouched.** Its bearer authentication is real
    because the middleware is on the HTTP app, its identity is not ambient, and
    nothing here narrows it.

    Args:
        credential: This boot's credential. Carried so the stated token is the
            same string the loopback transport would verify.
        principal_id: The declared principal the door serves.
        scope: The bearer scope the door requires.
        tenant: The one tenant this door serves as.
    """
    grant = TokenGrant(
        client_id=principal_id, scopes=(scope,), tenants=frozenset({tenant})
    )
    return AccessToken(
        token=credential,
        client_id=principal_id,
        scopes=[scope],
        claims={**tenant_claims(grant), AMBIENT_STDIO_CLAIM: True},
    )


def unguarded_surfaces(server: FastMCP) -> frozenset[str]:
    """Names registered on ``server`` that did not go through the guard.

    ``FastMCP``'s managers are the authority on what is actually reachable;
    :class:`TenantGuardedServer`'s ledger is the record of what was governed.
    A surface in the first and not the second is a handler on the wire with no
    capability behind it, which is the shape of ``SEC-018`` and of §2 P9.

    Templates are counted by their URI template rather than by function name,
    because that is the identity ``ResourceManager`` files them under.
    """
    ledger = _LEDGERS.get(server, {})
    registered = {tool.name for tool in server._tool_manager.list_tools()}
    registered |= {
        str(resource.uri) for resource in server._resource_manager.list_resources()
    }
    registered |= {
        template.uri_template
        for template in server._resource_manager.list_templates()
    }
    return frozenset(registered - set(ledger))


class TenantGuardedServer:
    """A ``FastMCP`` whose surfaces cannot be registered ungoverned — the MCP mint site.

    Holds the server rather than subclassing it, so the registration methods a
    handler author reaches are *these* — which require a declaration — rather
    than the library's, which do not. The underlying instance is handed back
    only by :meth:`build`, which refuses a server carrying any surface the
    ledger does not know.

    Args:
        server: The ``FastMCP`` to govern. Refused if it already carries a
            surface. Authentication configuration is the caller's — this class
            decides on a verified identity and never establishes one.
        authorizer: The deployment's authorizer. **Required**, with no
            default: there is no arm of this class in which the decision is
            skipped (§2 P4), and the lint refuses a defaulted authority type.

    Raises:
        UnguardedSurfaceError: ``server`` already carries a tool, resource or
            template.
    """

    def __init__(self, server: FastMCP, *, authorizer: TenantAuthorizerProtocol) -> None:
        self._server = server
        self._authorizer = authorizer
        _LEDGERS[server] = {}
        self._refuse_unguarded(when="wrapped")

    def build(self) -> FastMCP:
        """The governed server, for mounting — or refuse to hand one back.

        The one way a builder obtains the ``FastMCP`` it returns, so a
        registration on the underlying server after wrapping is a boot failure
        rather than a test failure (§2 P9).

        Raises:
            UnguardedSurfaceError: a surface reached the registry behind the
                wrapper's back.
        """
        self._refuse_unguarded(when="built")
        return self._server

    @property
    def ledger(self) -> Mapping[str, GuardedSurface]:
        """Every surface registered through this wrapper, and what it declared."""
        return dict(_LEDGERS[self._server])

    def _refuse_unguarded(self, *, when: str) -> None:
        smuggled = unguarded_surfaces(self._server)
        if smuggled:
            raise UnguardedSurfaceError(
                f"these surfaces were registered on the FastMCP behind the"
                f" guard and reach the wire with no capability behind them:"
                f" {sorted(smuggled)}; found when the server was {when}."
                " Register every tool and resource through"
                " TenantGuardedServer.tool / .resource (SEC-018; D-IMPL-353"
                " §2 P9)"
            )

    # --- the three tenant selections (§1.3) ---------------------------------

    @staticmethod
    def from_argument(name: str) -> TenantSubject:
        """The wire parameter ``name`` names the tenant; it must be a member of the grant."""
        return TenantSubject(argument=name)

    @staticmethod
    def declared(tenant: str) -> TenantSubject:
        """The tenant is fixed at registration; it must be a member of the grant."""
        return TenantSubject(declared=tenant)

    @staticmethod
    def from_grant() -> TenantSubject:
        """The surface carries no tenant: the grant's sole tenant, or refuse as ambiguous."""
        return TenantSubject(grant=True)

    # --- the four resource readings -------------------------------------------

    @staticmethod
    def resource_argument(name: str) -> ResourceSubject:
        """The resource is the wire parameter ``name``."""
        return ResourceSubject(argument=name)

    @staticmethod
    def resource_declared(value: str) -> ResourceSubject:
        """The resource is fixed at registration."""
        return ResourceSubject(declared=value)

    @staticmethod
    def resource_route() -> ResourceSubject:
        """The surface itself is the resource; its action id names it."""
        return ResourceSubject(route=True)

    @staticmethod
    def resource_composed(template: str) -> ResourceSubject:
        """The resource is ``template`` formatted over the wire arguments."""
        return ResourceSubject(template=template)

    # --- registration ----------------------------------------------------------

    def tool(
        self,
        *,
        name: str,
        action: str,
        subject: TenantSubject,
        resource: ResourceSubject,
        mutating: bool,
        **kwargs: Any,
    ) -> Callable[[_F], _F]:
        """Register a tool whose body runs only under a capability minted for it.

        Every declaration is keyword-only with no default, so adding a tool
        without stating all four is a ``TypeError`` at import rather than a
        silent ungoverned surface.

        Args:
            name: The tool name on the wire.
            action: The door-declared action id this tool performs. The kind
                the body receives is :func:`~ccf_runtime.authz.capability
                .kind_for_action` of it; an id no door declares is refused
                here.
            subject: How the tenant is selected.
            resource: Where the resource is read.
            mutating: Whether the tool writes. A mutating tool is refused to a
                stated (ambient) identity before any decision is made. Refused
                as ``False`` for an action whose kind is outside
                :data:`READ_KINDS`.
            **kwargs: Passed to ``FastMCP.tool`` untouched.
        """

        def register(handler: _F) -> _F:
            guarded, surface = self._guard(
                handler, action=action, subject=subject, resource=resource, mutating=mutating
            )
            self._server.tool(name=name, **kwargs)(guarded)
            _LEDGERS[self._server][name] = surface
            # The GUARDED callable, never the bare one: returning `handler`
            # would leave an ungoverned alias bound to the module-level name
            # the body was defined under.
            return guarded

        return register

    def resource(
        self,
        uri: str,
        *,
        action: str,
        subject: TenantSubject,
        resource: ResourceSubject,
        mutating: bool,
        **kwargs: Any,
    ) -> Callable[[_F], _F]:
        """Register a resource whose body runs only under a capability minted for it.

        That ``get_access_token()`` is populated inside a **resource** handler
        and not only inside a tool is shipped fact rather than assumption — the
        A1 spike verdict, ``tests/crossproc/test_fastmcp_resource_token_
        spike.py``.

        Args:
            uri: The URI or URI template this resource answers. A template's
                parameters are the wire parameters: the body declares every one
                of them except the tenant segment, which the wrapper consumes.
            action: The door-declared action id this resource performs.
            subject: How the tenant is selected.
            resource: Where the resource is read.
            mutating: Whether the resource writes. Resources cannot mutate by
                protocol, so this is ``False`` for every one the SDK ships; it
                is a parameter rather than an assumption so the reading is
                stated at each site.
            **kwargs: Passed to ``FastMCP.resource`` untouched.
        """

        def register(handler: _F) -> _F:
            guarded, surface = self._guard(
                handler, action=action, subject=subject, resource=resource, mutating=mutating
            )
            self._server.resource(uri, **kwargs)(guarded)
            _LEDGERS[self._server][uri] = surface
            return guarded

        return register

    # --- the guard itself ------------------------------------------------------

    def _guard(
        self,
        handler: _F,
        *,
        action: str,
        subject: TenantSubject,
        resource: ResourceSubject,
        mutating: bool,
    ) -> tuple[_F, GuardedSurface]:
        """Wrap ``handler`` so decision and mint precede its first statement.

        **The visible signature is the wire's, not the body's.** ``FastMCP``
        derives a tool's input schema and a template's parameter set from
        ``inspect.signature``, so the wrapper publishes the body's parameters
        minus ``authorized`` plus the tenant argument (when the subject names
        one). ``authorized`` is therefore never on the wire, and the tenant
        argument never reaches the body. Both ``__signature__`` and
        ``__annotations__`` are set, because the library reads the first and
        pydantic's ``validate_call`` may read the second.

        Raises:
            CapabilityBypassError: ``action`` is not one any door declares.
            ValueError: the body's first parameter is not ``authorized``; the
                body declares the tenant argument; ``mutating`` is ``False``
                for a kind outside :data:`READ_KINDS`; or a declared resource
                argument is not a wire parameter.
        """
        kind = kind_for_action(action)
        if not mutating and kind not in READ_KINDS:
            raise ValueError(
                f"{handler.__name__!r} declares action {action!r}, whose kind"
                f" {kind.__name__} is not a read kind, and is registered"
                " mutating=False; a stated stdio identity would then be minted"
                " a mutating kind. Register it mutating=True (D-IMPL-353;"
                " SEC-018)"
            )
        body = inspect.signature(handler, eval_str=True)
        parameters = list(body.parameters.values())
        if (
            not parameters
            or parameters[0].name != _CAPABILITY_PARAMETER
            or parameters[0].kind
            not in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ):
            raise ValueError(
                f"{handler.__name__!r} does not take the capability as its"
                f" first parameter; a body registered through the guard is"
                f" `def body({_CAPABILITY_PARAMETER}: Authorized[Kind], ...)`"
                " and reads its tenant from it — there is no other source"
                " (D-IMPL-353 §1.2)"
            )
        wire = parameters[1:]
        wire_names = {parameter.name for parameter in wire}
        if subject.argument is not None:
            if subject.argument in wire_names:
                raise ValueError(
                    f"{handler.__name__!r} declares a parameter"
                    f" {subject.argument!r} and is registered to select its"
                    " tenant from that wire argument; the body reads"
                    f" `{_CAPABILITY_PARAMETER}.tenant` and takes no tenant of"
                    " its own — a second source is what SEC-018 was"
                    " (D-IMPL-353 §1.2)"
                )
            wire = [
                inspect.Parameter(
                    subject.argument,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=str,
                ),
                *wire,
            ]
            wire_names.add(subject.argument)
        if resource.argument is not None and resource.argument not in wire_names:
            raise ValueError(
                f"{handler.__name__!r} declares no parameter"
                f" {resource.argument!r}; a guard reading a resource the wire"
                " does not carry would silently decide nothing (SEC-002)"
            )
        visible = body.replace(parameters=wire)
        surface = GuardedSurface(
            action=action, subject=subject, resource=resource, mutating=mutating
        )
        authorizer = self._authorizer

        @functools.wraps(handler)
        def guarded(*args: Any, **kwargs: Any) -> Any:
            token = get_access_token()
            if token is None:
                raise UnverifiedTenantCallerRefused(
                    "no verified access token accompanies this call; a"
                    " tenant-scoped surface decides on verified identities"
                    " only (SEC-018; D-26)"
                )
            if mutating and is_ambient_stdio(token):
                raise AmbientMutationRefused(
                    "this identity was stated by the stdio host rather than"
                    " verified from a presented credential; process ownership"
                    " warrants reading what this process was spawned to serve"
                    " and does not warrant mutating (SEC-018)"
                )
            held = granted_tenants(token)
            if not held:
                raise TenantlessGrantRefused(
                    "the verified grant names no tenant, so it reaches"
                    " nothing; a credential's tenants are a deployment value"
                    " and an unscoped credential is refused rather than"
                    " widened (SEC-018)"
                )
            bound = visible.bind(*args, **kwargs)
            bound.apply_defaults()
            arguments = dict(bound.arguments)
            tenant = _select_tenant(subject, arguments, held)
            target = _read_resource(resource, arguments, action=action)
            # The §6 round-trip's last step: the grant the authorizer decides
            # on is rebuilt from the VERIFIED token — the claims the verifier
            # composed from the deployment's own grant, never anything the
            # wire supplied.
            grant = TokenGrant(
                client_id=token.client_id, scopes=tuple(token.scopes), tenants=held
            )
            decision = authorizer.authorize(
                grant=grant, tenant=tenant, action_id=action, resource=target
            )
            if not decision.allowed:
                raise ActionUnauthorizedRefused(
                    json.dumps(
                        refusal_detail(
                            error_code=ERROR_TENANT_UNAUTHORIZED,
                            message=(
                                "the verified caller's grant does not"
                                f" authorize action {action!r} on"
                                f" {target!r} under tenant {tenant!r} against"
                                " the scope mapping in force (HARD-04;"
                                " D-IMPL-68 — deny-by-default)"
                            ),
                        )
                    )
                )
            authorized: Authorized[ActionKind] = mint(
                kind,
                decision=decision,
                principal=token.client_id,
                # The decision's own identity: the content address of the
                # exact tuple the authorizer returned *allowed* for.
                decision_id=content_hash(decision),
            )
            if subject.argument is not None:
                del arguments[subject.argument]
            return handler(authorized, **arguments)

        # The wire's signature, for FastMCP's schema and pydantic's validation.
        setattr(guarded, "__signature__", visible)
        setattr(
            guarded,
            "__annotations__",
            {
                **{parameter.name: parameter.annotation for parameter in wire},
                "return": body.return_annotation,
            },
        )
        return guarded, surface  # type: ignore[return-value]


def _select_tenant(
    subject: TenantSubject, arguments: Mapping[str, Any], held: frozenset[str]
) -> str:
    """The one tenant this call acts under, selected — never picked (§1.3)."""
    if subject.grant:
        if len(held) != 1:
            raise AmbiguousTenantRefused(
                "this surface carries no tenant and the verified grant holds"
                f" {len(held)}; a decision is about one tenant and the guard"
                " does not choose it (D-IMPL-353 §1.3)"
            )
        (only,) = held
        return only
    if subject.declared is not None:
        acting_on: object = subject.declared
    else:
        assert subject.argument is not None  # the three readings are closed
        acting_on = arguments[subject.argument]
    if not isinstance(acting_on, str) or not acting_on:
        raise CrossTenantRefused(
            "the tenant argument is not a tenant name; a value that cannot be"
            " compared is refused rather than admitted (SEC-018)"
        )
    if acting_on not in held:
        raise CrossTenantRefused(
            f"the verified caller's grant does not carry tenant"
            f" {acting_on!r}; the tenant a call acts on is decided against"
            " the grant, never supplied by the call (SEC-018)"
        )
    return acting_on


def _read_resource(
    resource: ResourceSubject, arguments: Mapping[str, Any], *, action: str
) -> str:
    """The thing this call acts on, read where the registration said to."""
    if resource.route:
        return action
    if resource.declared is not None:
        return resource.declared
    if resource.template is not None:
        try:
            composed = resource.template.format(**arguments)
        except (KeyError, IndexError, ValueError) as unformattable:
            raise ResourceUnreadableRefused(
                "the resource template names a wire argument this call did"
                " not carry; a resource that cannot be spelled is refused"
                " rather than skipped (SEC-002)"
            ) from unformattable
        return composed
    assert resource.argument is not None  # the four readings are closed
    value = arguments.get(resource.argument)
    if not isinstance(value, str) or not value:
        raise ResourceUnreadableRefused(
            f"the {resource.argument!r} argument carries no resource a"
            " decision can be made on; an unreadable resource is a deny,"
            " never a skip (SEC-002)"
        )
    return value
