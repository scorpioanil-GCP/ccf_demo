"""The standard MCP egress door for an opened product (`D-IMPL-343`).

**SDK-defined** (CLAUDE.md §7.1, §8.3, §11); the design is
``docs/D-IMPL-343-DESIGN.md`` §5.4. Six example trees carried a copy of the
same ~106-line door body — a second Control Plane registry, a hand-built
entitlement policy, a token file minted into a temporary directory, two
refusal recorders over a second replay store, a thirteen-keyword
:func:`~ccf_runtime.mcp.egress.build_egress_server` call, the stdio identity
block and a loopback transport — and one copy had drifted from the contract
(`CP03C-F-07`). This module is that body, once, over the deployment's OWN
objects: the one registry, the one recorder, the declared ``door:`` binding
and the environment document's names.

What this door adds to the governed path: nothing. Every governance decision
is :func:`build_egress_server`'s — authenticate, entitle, resolve, disclose,
encode — and every determination is the product's. What is here is the
composition every door repeated, and the two transports.

The door takes a **structural** :class:`ServesProducts`, not a concrete
class, so a deployment composed by hand on the low road (an hw1-shaped
long-lived fabric with its own resolver) reaches the same door with the
pieces it already holds. The paved road's
:class:`~ccf.products.product.OpenedProduct` conforms; so does anything
carrying the same nine attributes. The door governs serving, not ingestion: a
low-road fabric's temporal write guard is its own composition's to compose
(`D-IMPL-364` SEC-008 B1, ruled outside scope).

Identity over stdio, stated rather than smuggled
--------------------------------------------------
MCP stdio carries no authentication channel: ``FastMCP`` installs its bearer
middleware on the HTTP app and there is no HTTP app on stdio, so the door
would refuse every caller as unverified. The transport's own security
boundary is process ownership — this server is a child the deployment's
client spawned, under the same user, on the same host. So
:meth:`ProductDoor.serve_stdio` is handed who its stdio caller is, once,
before serving: the CALLER composes that identity and passes it, and the door
fabricates none (`EX-03`/`EX-04`, `D-IMPL-361` §7.3). On the loopback
transport bearer auth is REAL and the identity is NOT pre-set.

**What that statement is now bounded by** (``SEC-018``). Reviewers were right
that an ambient identity is an identity nobody presented, and the answer is to
bound its warrant rather than to remove the only identity stdio can have. The
stated identity is built by
:func:`~ccf_runtime.mcp.tenancy.ambient_stdio_identity`, which scopes it to
**exactly this door's own tenant** — before the tenant axis existed it carried
none, so its reach was unbounded — and marks it *ambient*, which makes every
surface registered ``mutating`` refuse it outright. Process ownership warrants
reading what the child was spawned to serve; it does not warrant writing on an
authority nobody presented. None of this touches the loopback transport, whose
bearer authentication is real and whose identity is not ambient — keeping those
two transports distinguishable is the point of having both.

Where the URLs come from (Dave, `D-IMPL-343` GO: *"Do not put URLs or tokens
in configuration."*)
--------------------------------------------------------------------------
The OAuth issuer and resource-server addresses are what an HTTP door
advertises for OAuth discovery: the protected-resource metadata document and
the ``resource_metadata`` hint on a 401. No token check and no authorization
decision reads either one. They are deployment ENVIRONMENT, never
configuration, and neither transport this module runs reads them from it
(C2-A (b), ``D-IMPL-378``). The loopback transport binds its own port, so it
KNOWS its own address and advertises exactly that. The stdio transport has
no address and serves no HTTP, so nothing could advertise them there; it
supplies its own reserved values and starts with both variables unset. A
deployment that mounts :meth:`ProductDoor.server` under its own host passes
both, and the method holds no default for either. The credential is read by
name; when the variable is unset a development door mints one per boot and
exposes it on the :class:`ProductDoor`, because a child process has no
operator to export a secret for it, and a parent that wants to know the
credential without a side channel sets the variable.
"""

from __future__ import annotations

import os
import secrets
import socket
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from ccf.authz.actions import ACTION_PRODUCT_RETRIEVE
from ccf.authz.capability import (
    CompositionRegister,
    COMPOSITION_PRINCIPAL,
    Authorized,
    Register,
    mint_at_composition,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import EgressDoorBinding, ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.environment import EnvironmentDocument
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.resolver import RefusalRecorderProtocol, ResolverOutcome
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf_runtime.authz.artifact import SCOPE_MAPPING, ScopeEntry, ScopeMappingArtifact
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    PerspectiveResolverProtocol,
    ProductEntitlementSourceProtocol,
    TokenGrant,
)
from ccf_runtime.authz.protocol import (
    ControlPlaneTenantAuthorizer,
    TenantAuthorizerProtocol,
)
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource
from ccf_runtime.mcp.egress import build_egress_server

#: The stdio transport's own two addresses (C2-A (b), ``D-IMPL-378``), the way
#: :meth:`ProductDoor.serve_loopback` derives its own from the port it binds.
#: Stdio has no network address and serves no HTTP: ``FastMCP`` builds no
#: application, no metadata route and no ``WWW-Authenticate`` header on it, so
#: nothing ever advertises these. They exist only because
#: :func:`build_egress_server` takes auth settings together with the token
#: verifier (``D-03``). Both sit under the reserved ``.invalid`` domain
#: (RFC 2606; RFC 6761 section 6.4), which never resolves, and they reach no
#: transport but stdio: :meth:`ProductDoor.server` still requires both of its
#: own.
_STDIO_ISSUER_URL = "https://stdio.invalid"
_STDIO_RESOURCE_SERVER_URL = "https://stdio.invalid/mcp"

__all__ = [
    "ProductDoor",
    "ServesProducts",
    "StdioIdentityRequired",
    "open_door",
    "open_door_with_verifier",
    "scope_mapping_key",
]


@runtime_checkable
class ServesProducts(Protocol):
    """What a door needs from a product, structurally.

    Nine members, and every one is something a deployment already holds
    whether it opened its product on the paved road or composed it by hand:
    the tenant it runs as, the class it serves, the perspective it serves
    under, the ONE Control Plane the entitlement policy registers into, the
    ONE recorder every denial is appended through, the declared ``door:``
    binding, the environment document that names the door's credential and
    addresses, and a ``resolve`` conforming to
    :class:`~ccf_runtime.mcp.egress.ProductResolverProtocol`.
    """

    @property
    def tenant_id(self) -> str: ...

    @property
    def declaration(self) -> ProductClassDeclaration: ...

    @property
    def default_perspective(self) -> Perspective: ...

    @property
    def control_plane(self) -> ControlPlaneRegistry: ...

    @property
    def refusal_recorder(self) -> RefusalRecorderProtocol: ...

    @property
    def door(self) -> EgressDoorBinding | None: ...

    @property
    def environment(self) -> EnvironmentDocument: ...

    def resolve(
        self,
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ResolverOutcome: ...


class StdioIdentityRequired(ValueError):
    """``serve_stdio`` was called without a caller-composed identity (`EX-03`/`EX-04`, `D-IMPL-361` §7.3).

    SDK-defined (``CLAUDE.md`` §7.1). Stdio sets one identity for every caller
    of the process; the door refuses to author it.
    """


@dataclass(frozen=True)
class ProductDoor:
    """One opened door: the composition, held; the transport, chosen by the caller.

    Attributes:
        product: What the door serves.
        credential: The bearer credential this boot is reached with — read
            from the environment variable the document names, or minted per
            boot when it is unset.
        principal_id: The declared principal the door serves.
        role: The declared role it serves under.
        scope: The bearer scope it requires.
        tenant_id: The tenant it serves as — the server's advertised name.
        producer_id: The identity every outcome asserts (`D-IMPL-340`).
    """

    product: ServesProducts
    credential: str
    principal_id: str
    role: str
    scope: str
    tenant_id: str
    producer_id: str
    _token_verifier: TokenVerifier
    _authorizer: TenantAuthorizerProtocol
    _entitlement_source: ProductEntitlementSourceProtocol
    _perspective_resolver: PerspectiveResolverProtocol
    _environ: Mapping[str, str]

    def server(self, *, issuer_url: str, resource_server_url: str) -> FastMCP:
        """The configured, UNSTARTED ``FastMCP`` — mount it under your own host.

        The one :func:`build_egress_server` call every door used to spell:
        tool-only (a parameterized class has no standing answer), the
        product's own recorder, the declared identity asserted on every
        outcome (`D-IMPL-340` ruling 2 — supplied together or not at all).
        Hosting is the deployment's decision; a library that picked an
        interface would be picking an exposure surface.
        """
        door = self.product.door
        assert door is not None  # checked by `open_door`
        return build_egress_server(
            server_name=self.tenant_id,
            # The bound method: `ProductResolverProtocol` is a callable seam.
            # Measured the other way first — passing the product itself reached
            # the consumer as `producer-unavailable` (an opaque runtime failure
            # inside the door), which is exactly the failure the cross-process
            # proof exists to catch.
            resolver=self.product.resolve,
            token_verifier=self._token_verifier,
            auth_settings=AuthSettings(
                issuer_url=AnyHttpUrl(issuer_url),
                resource_server_url=AnyHttpUrl(resource_server_url),
                required_scopes=[self.scope],
            ),
            # The MCP mint site decides every surface against this
            # authorizer before its body runs (D-IMPL-353 §1.1).
            authorizer=self._authorizer,
            entitlement_source=self._entitlement_source,
            perspective_resolver=self._perspective_resolver,
            refusal_recorder=self.product.refusal_recorder,
            expose_product_resource=False,
            expose_product_tool=True,
            product_tool_description=door.tool_description,
            producer_id=door.producer_id,
            producer_tenant=door.producer_tenant,
        )

    def serve_stdio(self, *, identity: AuthenticatedUser | None = None) -> None:
        """Serve on stdio — the transport an MCP client spawns this process for.

        **Stdio is single-principal by construction** (`EX-03`/`EX-04`,
        `D-IMPL-361` §7.3): the transport carries no authentication channel, so
        one identity is set once, before anything is served, and it answers for
        EVERY caller of the process. The door therefore never composes that
        identity from its own fields; the CALLER composes the ambient identity
        — typically with
        :func:`~ccf_runtime.mcp.tenancy.ambient_stdio_identity` — and passes it
        here as ``identity``. A deployment that serves more than one principal
        uses :meth:`serve_loopback`, whose bearer authentication is real.

        ``identity`` is required. It is spelled ``| None`` only so that
        omitting it is refused with the typed :class:`StdioIdentityRequired`
        naming the ruling, rather than by an anonymous ``TypeError``; the
        refusal happens before the server is built or anything is set.

        **This transport reads neither advertised address** (C2-A (b),
        ``D-IMPL-378``). The issuer and resource-server addresses are OAuth
        discovery metadata for an HTTP application, and stdio builds none;
        no token check and no authorization decision reads them. So this
        transport supplies its own reserved values, the way
        :meth:`serve_loopback` derives its own, and never consults the
        environment document's names: it starts with both variables unset.
        Every refusal stays where it was: the tenancy guard, the authorizer
        under the pinned scope mapping, the entitlement policy.

        Args:
            identity: The ambient identity the caller composes for this
                process's one principal. Set verbatim, once.

        Raises:
            StdioIdentityRequired: ``identity`` was not an
                :class:`AuthenticatedUser` — the door states none of its own.
        """
        if not isinstance(identity, AuthenticatedUser):
            raise StdioIdentityRequired(
                "serve_stdio requires `identity=` — an AuthenticatedUser the "
                "caller composes (D-IMPL-361 §7.3, EX-03/EX-04): stdio is "
                "single-principal by construction, and the door does not "
                "fabricate an identity from its own fields."
            )
        server = self.server(
            issuer_url=_STDIO_ISSUER_URL,
            resource_server_url=_STDIO_RESOURCE_SERVER_URL,
        )
        auth_context_var.set(identity)
        server.run(transport="stdio")

    def serve_loopback(self, *, announce: Callable[[int], None]) -> None:
        """Bind an ephemeral loopback port, announce it once up, serve streamable HTTP.

        Bearer auth is REAL on this transport (the middleware is on the HTTP
        app), so no identity is pre-set: a caller without the boot's
        credential is refused by the door, not admitted by the harness. The
        door WRITES TO NO TERMINAL — readiness is handed to ``announce``, so
        the one module of a deployment that prints is the one that drives
        the run. The advertised addresses are the bound socket's own.
        """
        import anyio
        import uvicorn

        bound = socket.socket()
        bound.bind(("127.0.0.1", 0))
        bound.listen(64)
        port = bound.getsockname()[1]
        server = self.server(
            issuer_url=f"http://127.0.0.1:{port}",
            resource_server_url=f"http://127.0.0.1:{port}/mcp",
        )
        runner = uvicorn.Server(uvicorn.Config(server.streamable_http_app(), log_level="error"))

        async def run() -> None:
            async def ready() -> None:
                while not runner.started:
                    await anyio.sleep(0.005)
                announce(port)

            async with anyio.create_task_group() as group:
                group.start_soon(ready)
                await runner.serve(sockets=[bound])

        anyio.run(run)


def scope_mapping_key(*, tenant_id: str) -> str:
    """Return the Control Plane key one tenant's door scope mapping registers under.

    A derivation rather than a table, on the terms of
    :func:`~ccf.products.entitlement.product_entitlement_key`: the SDK
    supplies the shape of the key so the door and its authorizer cannot
    disagree about where a tenant's mapping lives, and supplies no tenant, so
    it holds no deployment's vocabulary (CINV-01).
    """
    # `{tenant}/{class}` — the grammar the registry reads the tenant from
    # (D-IMPL-353 §1.3); class-first until the D-IMPL-353 join corrected it.
    return f"{tenant_id}/{SCOPE_MAPPING.class_id}"


def open_door(
    product: ServesProducts,
    *,
    environ: Mapping[str, str] | None = None,
    perspective_resolver: PerspectiveResolverProtocol | None = None,
    entitlement_source: ProductEntitlementSourceProtocol | None = None,
) -> ProductDoor:
    """Compose the standard door over ``product``; choose the transport afterwards.

    Derives, from EXISTING calls only: the entitlement policy that permits
    exactly the declared class under the declared role for the declared
    principal, registered into the product's ONE Control Plane (the hw1
    shape — never restated in a second document); the entitlement source over
    that registry with a wall clock (a door decision happens when it happens;
    the audit instant is never the question's); a static token source holding
    this boot's one credential; a perspective resolver serving the VERIFIED
    caller under the declared role; and — ``D-IMPL-353`` — the scope mapping
    the door's authorizer decides under, granting the declared scope exactly
    the retrieve action on exactly the declared class for the declared tenant,
    registered into the same Control Plane and **pinned at the version that
    registration returns**, so a later registration under the key cannot
    widen a running door (``SEC-002``). The two seams that remain overridable
    are typed for the common partial departures — a role derived from scopes,
    several principals; a deployment with its own identity provider opens the
    same door through :func:`open_door_with_verifier`, and one that departs
    further calls :func:`build_egress_server` with ``product.resolve`` itself.

    Args:
        product: What to serve. Its ``door`` binding and its environment's
            ``door`` names are both required; either absent is refused by
            name.
        environ: Where the environment's names are resolved from;
            ``os.environ`` when omitted.
        perspective_resolver: Replaces the declared-role resolver.
        entitlement_source: Replaces the Control Plane source.

    Raises:
        ValueError: the product declares no ``door:`` section, its door
            binding asserts a ``producer_tenant`` other than the product's
            ``tenant_id`` (``D-IMPL-343`` R-6, refused before anything is
            registered), or its environment document names no door.
    """
    resolved_environ, credential = _boot_credential(product, environ)
    door = product.door
    assert door is not None  # checked by `_boot_credential`
    return _compose(
        product,
        environ=resolved_environ,
        credential=credential,
        token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(
                grants={
                    credential: TokenGrant(
                        client_id=product.default_perspective.principal_id,
                        scopes=(door.required_scope,),
                        # The one tenant this door serves (`SEC-018`).
                        tenants=frozenset({product.tenant_id}),
                    )
                }
            )
        ),
        perspective_resolver=perspective_resolver,
        entitlement_source=entitlement_source,
    )


def open_door_with_verifier(
    product: ServesProducts,
    *,
    token_verifier: TokenVerifier,
    environ: Mapping[str, str] | None = None,
    perspective_resolver: PerspectiveResolverProtocol | None = None,
    entitlement_source: ProductEntitlementSourceProtocol | None = None,
) -> ProductDoor:
    """The same door, verifying credentials through the deployment's own identity provider.

    A second constructor rather than an optional parameter on
    :func:`open_door` (``D-IMPL-353`` §4): an authority-typed parameter that
    admits ``None`` says an absent verifier is representable, and the lint
    refuses that shape whether or not ``None`` happened to mean *mint one*.
    Here the verifier is **required**; on :func:`open_door` it is the paved
    road's own static credential. Everything else — the entitlement policy,
    the scope mapping, the pinned authorizer, the declared-role resolver — is
    derived identically.

    The boot credential is still read or minted, because the stdio transport
    states it as the ambient identity's token and :class:`ProductDoor` exposes
    it; whether the deployment's verifier recognizes it is the deployment's
    statement, as every token it recognizes is.

    Args:
        product: What to serve, on :func:`open_door`'s terms.
        token_verifier: The deployment's verifier. Required.
        environ: Where the environment's names are resolved from.
        perspective_resolver: Replaces the declared-role resolver.
        entitlement_source: Replaces the Control Plane source.
    """
    resolved_environ, credential = _boot_credential(product, environ)
    return _compose(
        product,
        environ=resolved_environ,
        credential=credential,
        token_verifier=token_verifier,
        perspective_resolver=perspective_resolver,
        entitlement_source=entitlement_source,
    )


def _boot_credential(
    product: ServesProducts, environ: Mapping[str, str] | None
) -> tuple[Mapping[str, str], str]:
    """Refuse a product with no door, or whose door asserts another tenant; then read or mint this boot's credential."""
    door = product.door
    if door is None:
        raise ValueError(
            f"{product.declaration.schema_name!r} declares no 'door' section;"
            " the standard door asserts the identity and advertises the prose"
            " that section declares, and holds no default for either"
            " (D-IMPL-343; CINV-01)"
        )
    if door.producer_tenant != product.tenant_id:
        # `D-IMPL-343` R-6 on the structural path (`D-IMPL-378`, lane
        # 378d-replayfix): the rule `ccf.deployment.config` holds a derived
        # `door:` section to, applied to a binding a hand-composed deployment
        # hands in. Refused by name and never corrected, before the door
        # registers anything: a door asserting another tenant is refused
        # `producer-tenant-mismatch` by every consumer registered for this
        # product's tenant, and this moves that failure to composition.
        raise ValueError(
            f"the door binding asserts producer_tenant {door.producer_tenant!r}"
            f" and this deployment's tenant is {product.tenant_id!r}; the door"
            " asserts the tenant the deployment declares and a consumer holds"
            " the assertion to its own registration (D-IMPL-343 R-6; D-IMPL-340"
            " ruling 2) — state the deployment's tenant as the binding's"
            " producer_tenant"
        )
    names = product.environment.door
    if names is None:
        raise ValueError(
            "the environment document names no 'door' block; the credential,"
            " issuer and resource-server addresses are deployment environment"
            " and are read by the names declared there (D-IMPL-343)"
        )
    resolved_environ = os.environ if environ is None else environ
    credential = resolved_environ.get(names.credential.from_env) or secrets.token_urlsafe(32)
    return resolved_environ, credential


def _registration(
    control_plane: ControlPlaneRegistry, *, tenant: str, key: str, clock: Callable[[], datetime]
) -> Authorized[CompositionRegister]:
    """The composition recipe for ONE of the door's own keys (D-IMPL-354).

    The door is a composition root (§1.6): it records a ``composition`` event
    on the product's Control Plane audit log naming the key, and mints
    ``Register`` for exactly that key from that event's content address —
    for the tenant the door composes for. Both keys the door registers
    (:func:`~ccf.products.entitlement.product_entitlement_key`,
    :func:`scope_mapping_key`) are ``{tenant}/{class}``, so the registry's
    own tenant-segment check (§1.3) is a real check here, not a tautology:
    a key that did not belong to this tenant would be refused at the write.
    """
    event = control_plane.audit_log.append(
        action="composition",
        key=key,
        version=CompositionRegister.action_id,
        resolved=True,
        occurred_at=clock(),
        actor=COMPOSITION_PRINCIPAL,
    )
    return mint_at_composition(
        CompositionRegister,
        tenant=tenant,
        principal=COMPOSITION_PRINCIPAL,
        resource=key,
        decision_id=content_hash(event),
    )


def _compose(
    product: ServesProducts,
    *,
    environ: Mapping[str, str],
    credential: str,
    token_verifier: TokenVerifier,
    perspective_resolver: PerspectiveResolverProtocol | None,
    entitlement_source: ProductEntitlementSourceProtocol | None,
) -> ProductDoor:
    """The composition both constructors share, over a verifier already chosen."""
    door = product.door
    assert door is not None  # checked by `_boot_credential`
    tenant = product.tenant_id
    principal = product.default_perspective.principal_id
    role = product.default_perspective.role
    scope = door.required_scope

    def now() -> datetime:
        return datetime.now(UTC)

    # The permitted class and role are the ones this deployment serves and
    # assembles under — off the declaration and the declared perspective,
    # never restated — so an entitlement cannot name a class this fabric does
    # not serve. Into the product's ONE registry: the per-question resolver
    # and the door read the same policy. Under a `Register` minted by this
    # composition root for exactly that key (D-IMPL-354).
    product.control_plane.register_typed(
        _registration(
            product.control_plane,
            tenant=tenant, key=product_entitlement_key(tenant_id=tenant),
            clock=now,
        ),
        ProductEntitlementPolicy(
            tenant_id=tenant,
            policy_version=product.declaration.schema_version,
            principals={
                principal: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({product.declaration.schema_name}),
                    permitted_roles=frozenset({role}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )

    # The scope mapping the door's authorizer decides under (`D-IMPL-353`):
    # the declared scope reaches the declared tenant for exactly the retrieve
    # action on exactly the declared class — the same three facts the
    # entitlement above is derived from, in the authorizer's vocabulary. The
    # mapping's own semver lane rides the declaration's, and the authorizer
    # is pinned to the version this registration returns (`SEC-002`).
    mapping_version = product.control_plane.register_typed(
        _registration(
            product.control_plane,
            tenant=tenant, key=scope_mapping_key(tenant_id=tenant),
            clock=now,
        ),
        ScopeMappingArtifact(
            semver=product.declaration.schema_version,
            scopes={
                scope: ScopeEntry(
                    tenant_patterns=(tenant,),
                    action_ids=(ACTION_PRODUCT_RETRIEVE,),
                    resource_patterns=(product.declaration.schema_name,),
                )
            },
        ),
        SCOPE_MAPPING,
    )

    def declared_role(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        """Serve under the declared role, for the VERIFIED caller."""
        return Perspective(principal_id=grant.client_id, role=role)

    return ProductDoor(
        product=product,
        credential=credential,
        principal_id=principal,
        role=role,
        scope=scope,
        tenant_id=tenant,
        producer_id=door.producer_id,
        _token_verifier=token_verifier,
        _authorizer=ControlPlaneTenantAuthorizer(
            control_plane=product.control_plane,
            scope_mapping_key=scope_mapping_key(tenant_id=tenant),
            scope_mapping_version=mapping_version,
            clock=lambda: datetime.now(UTC),
        ),
        _entitlement_source=(
            entitlement_source
            if entitlement_source is not None
            else ControlPlaneProductEntitlementSource(
                control_plane=product.control_plane, clock=lambda: datetime.now(UTC)
            )
        ),
        _perspective_resolver=(
            perspective_resolver if perspective_resolver is not None else declared_role
        ),
        _environ=environ,
    )
