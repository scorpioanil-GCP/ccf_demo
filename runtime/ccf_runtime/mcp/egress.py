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
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
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

    **Five arguments, not three, and the widening happened exactly once**
    (``D-IMPL-108``, Dave, 2026-08-11). Until plan ``15.5-15`` this was a
    three-string seam — ``(tenant, product_class, version)`` — and that shape
    was the sole reason for two separate gaps: ``DI-15.5-03`` (the door
    resolved an entitled :class:`~ccf.projection.plan.Perspective` and then
    discarded it, so a served product's conditioning was the deployment's
    private business rather than the door's decision) and plan ``15.5-08``'s
    undeliverable *"the request surface is validated where it crosses the
    door"*. Both were blocked on the same missing parameters, so both were
    added together rather than reshaping the same call sites twice.
    """

    def __call__(
        self,
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ServableProduct:
        """Return the gate-admitted product at that address, under ``perspective``.

        Keyword-only, so a signature of same-typed strings cannot be called
        with the tenant and the class transposed.

        Args:
            tenant: The tenant the product is addressed under. Established by
                the door from the URI, never claimed by the caller's body.
            product_class: The Context Product class being requested.
            version: The class's own semver lane (INV-CH7-49).
            perspective: The Π role-conditioning the **door** resolved and the
                deployment's entitlement policy **authorized**
                (:func:`~ccf_runtime.authz.product_entitlement
                .entitled_perspective`). Required and non-nullable, and
                deliberately not defaulted: the whole substance of
                ``DI-15.5-03`` is that a resolver quietly constructing its own
                perspective is indistinguishable from one honouring the door's,
                and a parameter defaulting to ``None`` would recreate exactly
                that ambiguity one layer down. A resolver that receives this
                and conditions on something else has diverged from the decision
                that admitted the call — which is now a visible act rather than
                the default.
            request: The typed question the caller asked
                (:class:`~ccf.products.request.ProductRequest`, ``D-IMPL-98``),
                already cross-checked by the door against the address it
                resolved, or ``None`` when **the surface carries no way to
                ask**. Required with no default; ``None`` is the positive
                assertion in the voice
                :paramref:`~ccf_runtime.authz.product_entitlement
                .PerspectiveResolverProtocol.__call__.requested_role` already
                uses on this same tree — the ``ccf-product://`` template has
                three segments and no query surface among them, so this door
                passes ``None`` and says so, rather than the SDK inventing a
                subject, an intent, a freshness figure and an instant nobody
                asked for. The HTTP door, which does have a query surface,
                passes a request whenever a caller supplies one.

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

        **Where the resolved perspective goes** (``DI-15.5-03``, closed by
        ``D-IMPL-108``). It is forwarded. The perspective this door's
        entitlement authorized is the perspective the deployment's
        assemble-and-gate path is handed — bound to a local name and passed,
        never re-derived and never discarded. Until plan ``15.5-15`` this
        handler called :func:`~ccf_runtime.authz.product_entitlement
        .entitled_perspective` for its refusal alone and threw the return
        value away, so the door proved that an unentitled caller was refused
        while leaving entirely unproven that the product it *did* serve was
        shaped under the perspective it had authorized. Those are different
        guarantees and only one of them was held.

        **What this door passes as the request, and why it is ``None``.**
        ``PRODUCT_URI_TEMPLATE`` is three path segments with no query surface,
        so no caller reaching this handler has supplied a
        :class:`~ccf.products.request.ProductRequest`. ``None`` is that fact
        stated positively. Manufacturing one here would mean the SDK choosing
        a subject, an intent and a freshness figure (CINV-01 values it must
        never hold) and reading a clock for ``asked_at`` — which is precisely
        the literal-instead-of-argument defect ``D-IMPL-98`` exists to remove,
        reintroduced one layer up.
        """
        perspective = entitled_perspective(
            grant=verified_grant(),
            tenant=tenant,
            product_class=product_class,
            requested_role=None,
            entitlement_source=entitlement_source,
            perspective_resolver=perspective_resolver,
        )
        servable = resolver(
            tenant=tenant,
            product_class=product_class,
            version=version,
            perspective=perspective,
            request=None,
        )
        return canonical_bytes(servable.product).decode("utf-8")

    return server
