"""The mandatory tenant guard over every MCP surface (``SEC-018``).

**SDK-defined** (CLAUDE.md §7.1, §8.3, §11). The finding of record:
:class:`~ccf_runtime.mcp.auth.TokenGrant` carried ``client_id`` and ``scopes``
and **no tenant**, so a bearer minted for tenant A reached tenant B's
artifacts, queue and products. The library's authentication was never the
weakness — ``mcp==1.28.1`` engages ``RequireAuthMiddleware`` correctly on the
HTTP transports. The gap was that the thing it verified could not express
whose data its bearer was entitled to.

Why a wrapper, and not a helper
-------------------------------
The obvious repair is a function each handler calls. That repair reproduces
the defect class it is repairing: a tool body that must *remember* to consult
the grant has its guard's applicability decided by its author, exactly as the
Tier-0 gate check had its applicability decided by its caller. So the guard is
not offered to handlers; it is **installed on them at registration**, and a
handler that never went through this module never reaches the wire governed.

Three independent controls make that stick, because the wrapper alone only
moves the forgetting one level up:

1. :meth:`TenantGuardedServer.tool` and :meth:`TenantGuardedServer.resource`
   take ``subject`` and ``mutating`` as **required keyword arguments**. There
   is no defaulted registration, so a surface cannot be added without its
   author stating whose tenant it acts on and whether it writes.
2. :func:`unguarded_surfaces` compares the wrapper's ledger against
   ``FastMCP``'s own registry. Registering on the underlying server — the one
   way to bypass the wrapper — puts a name in the registry and not in the
   ledger, and ``tests/mcp/test_tenant_guard.py`` fails.
3. :func:`untenanted_surfaces` pins the exact roster of surfaces that carry no
   tenant on the wire, so :meth:`TenantGuardedServer.untenanted` cannot quietly
   become the escape hatch that closes the finding on paper. A roster, not a
   count: a count that is right with a wrong member audits clean forever.

What this decides, and what it deliberately does not
-----------------------------------------------------
It decides **tenancy** — is the tenant this call acts on one the verified grant
carries — and nothing else. It is not an entitlement decision and does not
become one. :func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement`
still decides *which product class under which role*, against the deployment's
``ProductEntitlementPolicy``, and still runs. The two answer different
questions and the tenancy one used to have no answer at all.

That separation is what lets the three tools ``D-IMPL-129`` left open be
closed on their tenancy limb without inventing vocabulary. That ruling declined
to decide ``list_agents``, ``invoke_agent`` and ``get_replay_record`` against
``ProductEntitlementPolicy``, whose grants name schemas and roles and say
nothing about agents or replay records — CLAUDE.md §11 forbids the SDK
inventing that semantic. It remains declined. **Tenancy needs no new
vocabulary**: the grant now says which tenants its bearer may reach, and those
three reach a tenant's agent population, a tenant's agent dispatch and a
tenant's replay record.

Tenant identifiers, scope vocabulary and token material are deployment values
in their entirety. This module holds none of them (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Final, TypeVar
from weakref import WeakKeyDictionary

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.middleware.auth_context import get_access_token

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
    "AmbientMutationRefused",
    "CrossTenantRefused",
    "TENANT_CLAIM",
    "TenantGuardViolation",
    "TenantGuardedServer",
    "TenantSubject",
    "TenantlessGrantRefused",
    "UnverifiedTenantCallerRefused",
    "ambient_stdio_identity",
    "granted_tenants",
    "is_ambient_stdio",
    "tenant_claims",
    "unguarded_surfaces",
    "untenanted_surfaces",
]

_F = TypeVar("_F", bound=Callable[..., Any])


class TenantGuardViolation(RuntimeError):
    """Base for every refusal this guard raises.

    One base so a door that wants to translate all of them into its own
    protocol-native shell has a single thing to catch, and four leaves so a
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


class AmbientMutationRefused(TenantGuardViolation):
    """A stated (not verified) identity tried to reach a mutating surface.

    See :func:`ambient_stdio_identity` for why stdio has a stated identity at
    all, and why its warrant stops at reading.
    """


@dataclass(frozen=True)
class TenantSubject:
    """How one surface's tenant is determined — a closed, stated choice.

    Constructed only through :meth:`TenantGuardedServer.from_argument`,
    :meth:`TenantGuardedServer.declared` and
    :meth:`TenantGuardedServer.untenanted`, so the three readings are
    enumerable and a fourth cannot appear by accident.

    Attributes:
        argument: The handler parameter naming the tenant, when the caller
            supplies it. The argument stays the caller's — what changed is that
            naming a tenant is now *decided against the grant* rather than
            trusted.
        declared: The tenant fixed at registration, for a surface with no
            tenant on the wire. Absence of a client parameter reduces
            steerability and never disclosure, so the surface is still a
            tenant's surface and is still decided.
        untenanted: ``True`` when the surface's subject genuinely carries no
            tenant in the SDK's contracts. Such a surface still requires a
            verified, tenant-scoped grant; what it cannot do is compare.
    """

    argument: str | None = None
    declared: str | None = None
    untenanted: bool = False


#: Every surface registered ``untenanted``, across every server built in this
#: process. Module-level because the roster is a property of the SDK's shipped
#: surfaces rather than of any one server instance — see
#: :func:`untenanted_surfaces`.
_UNTENANTED: set[str] = set()

#: Each built server's ledger of guarded surface names. Keyed weakly so a
#: server built in a test does not outlive the test.
_LEDGERS: WeakKeyDictionary[FastMCP, dict[str, TenantSubject]] = (
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

    **What this narrows, relative to what shipped.** Two things, and the
    reviewers' complaint ("no ambient identity") is answered by both rather
    than by removing the transport's only workable identity:

    * The grant is scoped to **exactly one tenant** — the door's own. Before
      the tenant axis existed the stated identity had no tenant, so nothing
      about it was bounded; now process ownership authorizes the tenant the
      child was spawned to serve and no other.
    * It is **marked ambient**, and :class:`TenantGuardedServer` refuses every
      surface registered ``mutating=True`` to a marked identity. Process
      ownership is a defensible warrant for reading what the child exists to
      serve; it is not a warrant for writing on an authority nobody presented.

    The marker cannot be forged or cleared from the wire. Claims reach a
    handler only from
    :meth:`~ccf_runtime.mcp.auth.SourceBackedTokenVerifier.verify_token`, which
    composes them from the deployment's own grant; a remote caller supplies a
    token string and nothing else. Clearing is the direction that would buy
    something, and it is the direction the wire has no reach into.

    **The loopback transport is untouched.** Its bearer authentication is real
    because the middleware is on the HTTP app, its identity is not ambient, and
    nothing here narrows it. That distinction is the point of having two
    transports.

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

    The instrument that makes the wrapper mandatory rather than customary.
    ``FastMCP``'s managers are the authority on what is actually reachable;
    :class:`TenantGuardedServer`'s ledger is the record of what was governed.
    A surface in the first and not the second is a handler on the wire with no
    tenant decision behind it, which is the shape of ``SEC-018``.

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


def untenanted_surfaces() -> frozenset[str]:
    """Every surface registered as carrying no tenant on the wire.

    Pinned by ``tests/mcp/test_tenant_guard.py`` so that
    :meth:`TenantGuardedServer.untenanted` stays the two measured cases it was
    introduced for and does not become the route by which a later surface
    escapes the guard while the finding reads closed.
    """
    return frozenset(_UNTENANTED)


class TenantGuardedServer:
    """A ``FastMCP`` whose surfaces cannot be registered ungoverned.

    Holds the server rather than subclassing it, so the registration methods a
    handler author reaches are *these* — which require a subject — rather than
    the library's, which do not. The underlying instance stays available as
    :attr:`fastmcp` because a builder must still return a real ``FastMCP`` for
    the deployment to mount; reaching it to register is the bypass
    :func:`unguarded_surfaces` exists to catch.

    Args:
        server: The configured ``FastMCP`` to govern. Authentication
            configuration is the caller's — this class decides tenancy on a
            verified identity and never establishes one.
    """

    def __init__(self, server: FastMCP) -> None:
        self._server = server
        _LEDGERS[server] = {}

    @property
    def fastmcp(self) -> FastMCP:
        """The governed server, for mounting."""
        return self._server

    @property
    def ledger(self) -> Mapping[str, TenantSubject]:
        """Every surface registered through this wrapper, and how it is decided."""
        return dict(_LEDGERS[self._server])

    # --- the three subject readings ---------------------------------------

    @staticmethod
    def from_argument(name: str) -> TenantSubject:
        """The tenant is the handler parameter ``name``, decided against the grant."""
        return TenantSubject(argument=name)

    @staticmethod
    def declared(tenant: str) -> TenantSubject:
        """The tenant is fixed at registration — a surface with none on the wire."""
        return TenantSubject(declared=tenant)

    @staticmethod
    def untenanted() -> TenantSubject:
        """The subject carries no tenant in the SDK's contracts.

        Use only where the tenant is genuinely underivable, never where it is
        merely inconvenient — the roster is pinned by a test precisely because
        this is the reading that could hollow the guard out. A surface
        registered this way still refuses an unverified caller and still
        refuses a grant carrying no tenant; what it cannot do is compare.
        """
        return TenantSubject(untenanted=True)

    # --- registration ------------------------------------------------------

    def tool(
        self,
        *,
        name: str,
        subject: TenantSubject,
        mutating: bool,
        **kwargs: Any,
    ) -> Callable[[_F], _F]:
        """Register a tool whose body cannot run before the tenant is decided.

        ``subject`` and ``mutating`` are keyword-only and have no defaults, so
        adding a tool without deciding both is a ``TypeError`` at import rather
        than a silent ungoverned surface.

        Args:
            name: The tool name on the wire.
            subject: How this tool's tenant is determined.
            mutating: Whether the tool writes. A mutating tool is refused to a
                stated (ambient) identity — see :func:`ambient_stdio_identity`.
            **kwargs: Passed to ``FastMCP.tool`` untouched.
        """

        def register(handler: _F) -> _F:
            guarded = self._guard(handler, subject=subject, mutating=mutating)
            self._server.tool(name=name, **kwargs)(guarded)
            _LEDGERS[self._server][name] = subject
            if subject.untenanted:
                _UNTENANTED.add(name)
            # The GUARDED callable, never the bare one: returning `handler`
            # would leave an ungoverned alias bound to the module-level name
            # the body was defined under, and an in-process caller reaching
            # that name would skip the decision entirely.
            return guarded

        return register

    def resource(
        self,
        uri: str,
        *,
        subject: TenantSubject,
        mutating: bool,
        **kwargs: Any,
    ) -> Callable[[_F], _F]:
        """Register a resource whose body cannot run before the tenant is decided.

        That ``get_access_token()`` is populated inside a **resource** handler
        and not only inside a tool is shipped fact rather than assumption — the
        A1 spike verdict, ``tests/crossproc/test_fastmcp_resource_token_
        spike.py``, and the HITL queue resource has relied on it since.

        Args:
            uri: The URI or URI template this resource answers.
            subject: How this resource's tenant is determined.
            mutating: Whether the resource writes. Resources cannot mutate by
                protocol, so this is ``False`` for every one the SDK ships; it
                is a parameter rather than an assumption so the reading is
                stated at each site.
            **kwargs: Passed to ``FastMCP.resource`` untouched.
        """

        def register(handler: _F) -> _F:
            guarded = self._guard(handler, subject=subject, mutating=mutating)
            self._server.resource(uri, **kwargs)(guarded)
            _LEDGERS[self._server][uri] = subject
            if subject.untenanted:
                _UNTENANTED.add(uri)
            return guarded

        return register

    # --- the guard itself --------------------------------------------------

    def _guard(
        self, handler: _F, *, subject: TenantSubject, mutating: bool
    ) -> _F:
        """Wrap ``handler`` so the tenant decision precedes its first statement.

        ``functools.wraps`` is load-bearing rather than tidy: ``FastMCP``
        derives a tool's input schema from ``inspect.signature``, which follows
        ``__wrapped__``. A wrapper that flattened the handler to
        ``*args, **kwargs`` would erase every declared argument from the
        protocol — including the tenant argument this guard reads.
        """
        signature = inspect.signature(handler)
        if subject.argument is not None and subject.argument not in signature.parameters:
            raise ValueError(
                f"{handler.__name__!r} declares no parameter"
                f" {subject.argument!r}; a guard reading an argument the"
                " handler does not take would silently decide nothing"
                " (SEC-018)"
            )

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
            if not subject.untenanted:
                acting_on = self._acting_tenant(
                    subject, signature, args, kwargs
                )
                if acting_on not in held:
                    raise CrossTenantRefused(
                        f"the verified caller's grant does not carry tenant"
                        f" {acting_on!r}; the tenant a call acts on is decided"
                        " against the grant, never supplied by the call"
                        " (SEC-018)"
                    )
            return handler(*args, **kwargs)

        return guarded  # type: ignore[return-value]

    @staticmethod
    def _acting_tenant(
        subject: TenantSubject,
        signature: inspect.Signature,
        args: tuple[Any, ...],
        kwargs: Mapping[str, Any],
    ) -> str:
        """Which tenant this call acts on, read from the stated subject.

        Binding through the handler's own signature rather than reading
        ``kwargs`` directly, so a positional call and a keyword call reach the
        same decision — a guard that only saw keywords would be silently inert
        on the other calling convention.
        """
        if subject.declared is not None:
            return subject.declared
        assert subject.argument is not None  # checked at registration
        bound = signature.bind(*args, **dict(kwargs))
        bound.apply_defaults()
        value = bound.arguments[subject.argument]
        if not isinstance(value, str):
            raise CrossTenantRefused(
                f"the {subject.argument!r} argument is not a tenant name;"
                " a value that cannot be compared is refused rather than"
                " admitted (SEC-018)"
            )
        return value
