"""L6 MCP egress — gate-admitted Context Products under ``ccf-product://``.

Whitepaper §8.3 Pattern 3 ("the fabric exposes Context Products as MCP
Resources; any MCP-capable agent runtime consumes them without knowing anything
about the fabric's internals"); SDK-defined framing per CLAUDE.md §7.1 (MCP as
a bidirectional surface, of which this is the egress edge) and §8.3 (the MCP
server as one of the three v0 Experience Layer front doors).

**What this server is not.** It is not the fabric. It holds a resolver the
deployment supplies and nothing else: no operator registry, no projection
engine, no Control Plane handle. Assembling and gating a product is the
deployment's business and happens before the resolver returns; this module's
whole job is to put an already-servable product on the wire under a stable URI.

**What this server cannot do.** It cannot write: it holds no graph write handle
and no graph read handle, and it imports nothing from the L3 graph package at
all. There is no field on it that could hold either — the resolver seam trades
in :class:`~ccf.products.gates.ServableProduct` and nothing else, and a
``ServableProduct`` is a read result someone else already produced. The honest
claim (D-21) is the structural one: nothing on this module's shape offers a
route into L2 or L3, and the lints plus the source assertion in
``tests/crossproc/test_mcp_egress.py`` — which greps this very source for those
names and fails if they appear — are what keep it that way. The single-writer
invariant (INV-CH7-10, CLAUDE.md §10) holds across this boundary because there
is no handle here to hold.

**Two schemes, deliberately disjoint.** ``ccf-product://`` addresses a *live*
product — assembled now, TTL-bound, valid until it expires. The artifact scheme
that :mod:`ccf.artifacts.protocol` owns addresses an *immutable* artifact at
rest, content-addressed and resolvable years later. One scheme for both would
let a live-assembly URI land in a replay record as though it named something
reproducible, which is the repudiation failure the split prevents (T-06-16).
The artifact scheme does not appear anywhere in this module and must not.

**Tenancy is a URI segment, resolved per call.** It is never a constructor
field, following the :class:`~ccf_runtime.cdc.adapter.CDCSourceAdapter`
precedent: one server over a shared fabric must not be able to serve a product
into the wrong tenant by positional accident (INV-CH7-16, T-06-13).

**Authenticated, and entitled, and neither is optional (15.5-06).** This
server previously constructed ``FastMCP`` with neither ``token_verifier`` nor
``auth``, and bound no authorizer of any kind: it answered everyone, with
every product its resolver held, conditioned on whatever the caller's
downstream chose. Both halves are now required constructor arguments.

The authentication pair is required *together*, because ``FastMCP`` installs
its authentication middleware only when both are present (D-26, the
artifact-server precedent) — and because that middleware is installed at
construction, a deployment cannot retrofit it onto the object this builder
returns. The governance pair
(:class:`~ccf_runtime.authz.product_entitlement.ProductEntitlementSourceProtocol`
and
:class:`~ccf_runtime.authz.product_entitlement.PerspectiveResolverProtocol`)
is required for a different reason, and the difference is worth stating
because it departs from a shipped pattern: ``http_api/routes/hitl.py``'s
authorizer is *inert when unbound* because it retrofits authorization onto a
door that had already shipped, whereas this door is receiving its first
authentication **and** its first authorization at once. An optional seam here
would ship exactly the gap ``docs/CONTEXT_PRODUCT_REVISION.md`` §11.2
measured, and would make deny-by-default a deployment's choice rather than
the SDK's. So the builder **raises** rather than building an inert door, in
the voice ``ProductClassRegistrationError`` uses: a door whose governance
configuration is absent must not become servable.

The entitlement decision itself, the resolution order, and the audit posture
live in :mod:`ccf_runtime.authz.product_entitlement` — one definition of
"entitled" for all three exposed product doors, in a package none of them
owns, because the role-separation invariant forbids the doors importing each
other.

Server name, bind address, tenant identifiers, product-class names, principal
identifiers, role names, and token values are all deployment values supplied
by the caller or carried on the wire. This module holds none of them
(CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from ccf.contracts.canonical import canonical_bytes
from ccf.products.gates import ServableProduct
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementSourceProtocol,
    entitled_perspective,
    verified_grant,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "PRODUCT_URI_SCHEME",
    "PRODUCT_URI_TEMPLATE",
    "ProductNotServable",
    "ProductResolverProtocol",
    "build_egress_server",
    "product_uri",
]

#: The L6 egress scheme. Live products only — see the module docstring on why
#: this is not the artifact scheme.
PRODUCT_URI_SCHEME = "ccf-product"

#: The templated resource this server registers. Three segments, because those
#: are the three facts that identify a product to a consumer who knows nothing
#: about the fabric: whose it is, what kind it is, and which schema lane.
PRODUCT_URI_TEMPLATE = (
    f"{PRODUCT_URI_SCHEME}://{{tenant}}/{{product_class}}/{{version}}"
)

#: Media type of the served body. The product is canonical JSON, and saying so
#: is what lets a consumer parse it without sniffing.
PRODUCT_MIME_TYPE = "application/json"


class ProductNotServable(LookupError):
    """The resolver has no gate-admitted product at that URI.

    Raised by a deployment's resolver, not by this module. A ``LookupError``
    because it is an absence — the counterpart of
    :class:`ccf.mcp.errors.McpResourceAbsent` on the client side. Discriminating
    it structurally *at the client* needs a typed signal on the wire, which is
    the artifact server's contract (06-RESEARCH.md Pitfall 2) and not something
    an egress read of a live product needs today.
    """


@runtime_checkable
class ProductResolverProtocol(Protocol):
    """What a deployment plugs into the egress server.

    Protocol rather than a base class (CLAUDE.md §11): the resolver is the
    deployment's assembly-and-gate path, and the SDK has no business owning its
    shape — only its signature.
    """

    def __call__(
        self, *, tenant: str, product_class: str, version: str
    ) -> ServableProduct:
        """Return the gate-admitted product at that address.

        Keyword-only, so a three-string signature cannot be called with the
        tenant and the class transposed.

        Raises:
            ProductNotServable: no such product.
        """
        ...


def product_uri(*, tenant: str, product_class: str, version: str) -> str:
    """Render the egress URI for one product address.

    Exists so the server, the client, and the tests all agree what a product
    URI *is* rather than each formatting it, which is how two of them drift.
    """
    return f"{PRODUCT_URI_SCHEME}://{tenant}/{product_class}/{version}"


def build_egress_server(
    *,
    server_name: str,
    resolver: ProductResolverProtocol,
    token_verifier: TokenVerifier,
    auth_settings: AuthSettings,
    entitlement_source: ProductEntitlementSourceProtocol,
    perspective_resolver: PerspectiveResolverProtocol,
) -> FastMCP:
    """Build the authenticated, entitled L6 egress server over ``resolver``.

    ``stateless_http=True`` is load-bearing, not a tuning choice: it is what
    makes the client's session-per-call cheap (:mod:`ccf.mcp.client`, and the
    held-session bridge that deadlocks without it) and what keeps a consumer
    free of session affinity — no sticky routing, no session to lose.
    ``json_response=True`` pairs with it so a plain HTTP client sees a plain
    JSON body rather than an event stream.

    Both ``token_verifier`` and ``auth_settings`` are required, and required
    *together*, because ``FastMCP`` installs its authentication middleware
    only when both are present (D-26, the artifact-server precedent). The
    reference verifier is
    :class:`~ccf_runtime.mcp.auth.SourceBackedTokenVerifier`; this module
    names it as the reference and holds no default instance, because a
    library that chose a token source would be choosing an identity provider.

    ``entitlement_source`` and ``perspective_resolver`` are required for the
    reason the module docstring gives: this door is being given its first
    governance, and an optional seam would make deny-by-default a
    deployment's choice. There is no inert configuration of this builder.

    Args:
        server_name: The name this server advertises. Deployment identity; the
            SDK holds no default for it.
        resolver: The deployment's assemble-and-gate path.
        token_verifier: Verifies presented bearer tokens
            (:mod:`ccf_runtime.mcp.auth` ships the reference implementation).
        auth_settings: Issuer, resource-server identity, required scopes —
            deployment values in their entirety.
        entitlement_source: The deployment's per-principal entitlement
            decision seam
            (:class:`~ccf_runtime.authz.product_entitlement.ControlPlaneProductEntitlementSource`
            is the reference implementation, resolving the tenant's policy
            per call and auditing both outcomes).
        perspective_resolver: The deployment's role-derivation seam. This
            surface's URI carries three segments and no role among them, so
            the resolver is called with ``requested_role=None`` and derives
            the role from the verified grant; whatever it proposes is checked
            against the principal's grant before anything is served.

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision, and a
        library that picked an interface would be picking an exposure surface
        (T-06-14).
    """
    server = FastMCP(
        server_name,
        stateless_http=True,
        json_response=True,
        token_verifier=token_verifier,
        auth=auth_settings,
    )

    @server.resource(PRODUCT_URI_TEMPLATE, mime_type=PRODUCT_MIME_TYPE)
    def context_product(tenant: str, product_class: str, version: str) -> str:
        """Serve one gate-admitted Context Product as canonical JSON.

        Authenticate, then entitle, then resolve — and never the other way
        round. The auth middleware rejects an unverified caller before this
        body runs at all; :func:`~ccf_runtime.authz.product_entitlement
        .verified_grant` refuses if it somehow did not; and the entitlement
        decides on the resolved role before ``resolver`` is reached, so a
        refused caller moves no fabric.

        Canonical bytes, not ``model_dump_json``: the same serialization the
        content address and the A2A signature are computed over, so a consumer
        that hashes what it received gets the address the producer would.

        **Where the resolved perspective stops, and why it stops there.**
        The entitled perspective is the subject of the decision, not a value
        this door forwards: ``ProductResolverProtocol`` is a three-string
        seam, so the deployment's assemble-and-gate path constructs its own
        ``Perspective`` behind it. What this door guarantees is therefore the
        *refusal* leg — a caller not entitled to the class, or to the role
        the deployment's resolver derives for it, is refused before any
        product is resolved. Threading the resolved perspective *into* the
        assembler is a reshaping of ``ProductResolverProtocol`` itself, with
        a blast radius across the dependency bundle, the CLI's ``--local``
        mode and two examples; it is deliberately not folded in here, and it
        is recorded rather than left to be inferred.
        """
        entitled_perspective(
            grant=verified_grant(),
            tenant=tenant,
            product_class=product_class,
            requested_role=None,
            entitlement_source=entitlement_source,
            perspective_resolver=perspective_resolver,
        )
        servable = resolver(
            tenant=tenant, product_class=product_class, version=version
        )
        return canonical_bytes(servable.product).decode("utf-8")

    return server
