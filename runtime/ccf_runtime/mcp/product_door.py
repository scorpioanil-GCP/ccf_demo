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
carrying the same nine attributes.

Identity over stdio, stated rather than smuggled
--------------------------------------------------
MCP stdio carries no authentication channel: ``FastMCP`` installs its bearer
middleware on the HTTP app and there is no HTTP app on stdio, so the door
would refuse every caller as unverified. The transport's own security
boundary is process ownership — this server is a child the deployment's
client spawned, under the same user, on the same host. So
:meth:`ProductDoor.serve_stdio` states who its stdio caller is, once, before
serving: the deployment's declared principal, under the declared scope. On
the loopback transport bearer auth is REAL and the identity is NOT pre-set.

Where the URLs come from (Dave, `D-IMPL-343` GO: *"Do not put URLs or tokens
in configuration."*)
--------------------------------------------------------------------------
The OAuth issuer and resource-server addresses are deployment ENVIRONMENT,
named in ``ccf_environment.yaml`` and read from the process environment by
name. The loopback transport is the one exception, and it is not an
exception to the rule: it binds its own port, so it KNOWS its own address
and advertises exactly that. The credential is read by name too; when the
variable is unset a development door mints one per boot and exposes it on
the :class:`ProductDoor`, because a child process has no operator to export
a secret for it, and a parent that wants to know the credential without a
side channel sets the variable.
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
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from ccf.controlplane.artifacts import EgressDoorBinding, ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.environment import EnvironmentDocument, resolve_value
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.resolver import RefusalRecorderProtocol, ResolverOutcome
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    PerspectiveResolverProtocol,
    ProductEntitlementSourceProtocol,
    TokenGrant,
)
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource
from ccf_runtime.mcp.egress import build_egress_server

__all__ = ["ProductDoor", "ServesProducts", "open_door"]


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
            entitlement_source=self._entitlement_source,
            perspective_resolver=self._perspective_resolver,
            refusal_recorder=self.product.refusal_recorder,
            expose_product_resource=False,
            expose_product_tool=True,
            product_tool_description=door.tool_description,
            producer_id=door.producer_id,
            producer_tenant=door.producer_tenant,
        )

    def serve_stdio(self) -> None:
        """Serve on stdio — the transport an MCP client spawns this process for.

        The issuer and resource-server addresses are read by the names the
        environment document declares (inert on this transport, required by
        the builder together with the verifier). The stdio caller's identity
        is established once, before anything is served — see the module
        docstring.
        """
        names = self.product.environment.door
        assert names is not None  # checked by `open_door`
        server = self.server(
            issuer_url=resolve_value(names.issuer_url, self._environ),
            resource_server_url=resolve_value(names.resource_server_url, self._environ),
        )
        auth_context_var.set(
            AuthenticatedUser(
                AccessToken(token=self.credential, client_id=self.principal_id, scopes=[self.scope])
            )
        )
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


def open_door(
    product: ServesProducts,
    *,
    environ: Mapping[str, str] | None = None,
    perspective_resolver: PerspectiveResolverProtocol | None = None,
    token_verifier: TokenVerifier | None = None,
    entitlement_source: ProductEntitlementSourceProtocol | None = None,
) -> ProductDoor:
    """Compose the standard door over ``product``; choose the transport afterwards.

    Derives, from EXISTING calls only: the entitlement policy that permits
    exactly the declared class under the declared role for the declared
    principal, registered into the product's ONE Control Plane (the hw1
    shape — never restated in a second document); the entitlement source over
    that registry with a wall clock (a door decision happens when it happens;
    the audit instant is never the question's); a static token source holding
    this boot's one credential; and a perspective resolver serving the
    VERIFIED caller under the declared role. Each of the last three is a typed
    override for the common partial departures — an identity provider, a
    role derived from scopes, several principals — and a deployment that
    departs further calls :func:`build_egress_server` with ``product.resolve``
    itself.

    Args:
        product: What to serve. Its ``door`` binding and its environment's
            ``door`` names are both required; either absent is refused by
            name.
        environ: Where the environment's names are resolved from;
            ``os.environ`` when omitted.
        perspective_resolver: Replaces the declared-role resolver.
        token_verifier: Replaces the static-credential verifier.
        entitlement_source: Replaces the Control Plane source.

    Raises:
        ValueError: the product declares no ``door:`` section, or its
            environment document names no door.
    """
    door = product.door
    if door is None:
        raise ValueError(
            f"{product.declaration.schema_name!r} declares no 'door' section;"
            " the standard door asserts the identity and advertises the prose"
            " that section declares, and holds no default for either"
            " (D-IMPL-343; CINV-01)"
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

    tenant = product.tenant_id
    principal = product.default_perspective.principal_id
    role = product.default_perspective.role
    scope = door.required_scope

    # The permitted class and role are the ones this deployment serves and
    # assembles under — off the declaration and the declared perspective,
    # never restated — so an entitlement cannot name a class this fabric does
    # not serve. Into the product's ONE registry: the per-question resolver
    # and the door read the same policy.
    product.control_plane.register_typed(
        product_entitlement_key(tenant_id=tenant),
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
        _token_verifier=(
            token_verifier
            if token_verifier is not None
            else SourceBackedTokenVerifier(
                source=StaticTokenSource(
                    grants={credential: TokenGrant(client_id=principal, scopes=(scope,))}
                )
            )
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
        _environ=resolved_environ,
    )
