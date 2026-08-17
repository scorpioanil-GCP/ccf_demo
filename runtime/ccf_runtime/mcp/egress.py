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
only in **values someone else already produced**: a
:class:`~ccf.products.gates.ServableProduct`, the
:class:`~ccf.replay.serve.ServedProduct` that carries one alongside its replay
reference, or the :class:`~ccf.products.refusal.RefusalEnvelope` that stands
instead of one (``D-IMPL-148`` Addendum A; the translation lives in
:mod:`ccf.products.door`, and the seam's *declared* type is unchanged — see
:class:`ProductResolverProtocol`). None of the three is a handle. The honest
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

**Two surfaces, and what distinguishes them (``D-IMPL-126``; this extends
``D-IMPL-108`` rather than contradicting it).** The resource answers *the
class's standing answer*: three path segments, no query surface, and therefore
``request=None`` — which is the ruled shape and does not move. The opt-in tool
answers *a question*: the same three address segments plus whitepaper §6.3's
four axes (``subject``, ``intent``, ``freshness``, ``asked_at``), assembled at
the door into a :class:`~ccf.products.request.ProductRequest` before the
resolver is reached. The two are deliberately non-overlapping, and the
standing-answer case is the resource rather than a four-``None`` tool call.

The tool exists because a resource-only door cannot refute the reading that a
Context Product is a precalculated static object: which question gets answered
is entirely the server's choice when the caller has no way to ask one. It is
**opt-in** (:paramref:`build_egress_server.expose_product_tool`) because a
deployment that reviewed and approved a resource-only door must not acquire a
parameterised authorization surface it never assessed merely by upgrading —
deny-by-default, this module's stated posture, applied to exposure.

**The tool is not the weaker path, and that is structural.** It runs the same
:func:`~ccf_runtime.authz.product_entitlement.verified_grant` then
:func:`~ccf_runtime.authz.product_entitlement.entitled_perspective` sequence
with the identical arguments the resource passes, ``requested_role=None``
included; it **binds and forwards** the perspective that call returned rather
than re-deriving one (``DI-15.5-03``, below, is exactly that defect); it takes
no ``role`` parameter, so it is narrower than the resource beside it rather
than wider; and it addresses its request from its own path arguments, so a
request aimed at another class is unrepresentable rather than merely refused.

Server name, bind address, tenant identifiers, product-class names, principal
identifiers, role names, tool prose, and token values are all deployment
values supplied by the caller or carried on the wire. This module holds none
of them (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import DoorOutcome, door_refusal, served_answer
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
    "PRODUCT_REQUEST_TOOL",
    "PRODUCT_URI_SCHEME",
    "PRODUCT_URI_TEMPLATE",
    "NaiveAskedAtRefused",
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

#: The one parameterised Tool this server can expose, named here rather than
#: at each use site for the reason :func:`product_uri` exists: the server, the
#: tests and the docs must agree what the surface *is* rather than each
#: spelling it, which is how two of them drift. Registered only when a
#: deployment opts in (:func:`build_egress_server`).
PRODUCT_REQUEST_TOOL = "request_context_product"


class NaiveAskedAtRefused(ValueError):
    """``asked_at`` was presented to the product tool without a UTC offset.

    Refused at the boundary rather than passed on, on the
    :class:`~ccf_runtime.mcp.hitl_server.NaiveActionTimeRefused` precedent
    (D-IMPL-38): :class:`~ccf.products.request.ProductRequest` *accepts* a
    naive instant and the failure surfaces **later**, inside
    :func:`~ccf.contracts.canonical.canonical_bytes`, which would turn a
    client's malformed argument into an opaque server error and an unpinnable
    replay record — ``asked_at`` is the boundary a replay resolves against, so
    a replay must never have to guess which wall the caller's clock hung on.

    A named ``ValueError`` subclass rather than a bare one, so a deployment
    can catch *this* refusal, and rather than a typed ``ERROR_*`` code because
    it is a malformed argument and not a governance decision — the same line
    ``NaiveActionTimeRefused`` sits on, and not an inconsistency with D-08.
    """


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

    **THE DECLARED RETURN TYPE IS UNCHANGED, AND THE TOOL NOW TOLERATES TWO
    MORE SHAPES** (``D-IMPL-148`` Addendum A). Widening this Protocol's return
    type would reshape all three product doors and is a fourth door's worth of
    work that nothing has ruled — :mod:`ccf.products.resolver` records the same
    divergence from its own side. So the annotation below still says
    :class:`~ccf.products.gates.ServableProduct`, while the *tool* handler
    accepts, through :mod:`ccf.products.door`, whichever of these a deployment's
    resolver actually returns:

    * :class:`~ccf.products.gates.ServableProduct` — served, and **no replay
      reference**, because this vessel carries none;
    * :class:`~ccf.replay.serve.ServedProduct` — served, with the reference,
      which is what :class:`~ccf.products.resolver.GovernedResolver` returns and
      what makes the reference reach a consumer at all;
    * :class:`~ccf.products.refusal.RefusalEnvelope`, or any bare refusal value
      :data:`~ccf.products.refusal.REFUSAL_KINDS` names — the governed "no",
      returned rather than raised.

    Anything else is a wiring defect and raises ``TypeError``; it is never
    reported to a caller as a refusal the fabric made. The **resource** handler
    is unchanged and reads ``.product`` off what it was handed, as it always
    has.

    **TWO REFUSALS THIS DOOR DOES NOT CALL, AND YOUR RESOLVER MUST.** The SDK
    ships both comparisons complete and tested, and no shipped door invokes
    either one. That is a ruling (``D-IMPL-113``, extended to the second
    refusal by ``D-IMPL-121``, Dave), not an omission, and the consequences
    fall on the resolver you are about to write:

    - A resolver that does not call
      :func:`~ccf.products.request.refuse_request` **serves against an
      unchecked request** — the question is answered without ever being
      compared to the surface the product class declared it accepts, so a
      request addressed elsewhere, or carrying undeclared, missing or
      mistyped parameters, is answered rather than refused.
    - A resolver that does not call
      :func:`~ccf.products.bind.refuse_bound_payload` **serves an unvalidated
      payload against a schema its own class declared** — the declaration
      ships, and nothing on the path checks it, which from a consumer's seat
      is indistinguishable from there being no schema at all.

    **Why the SDK does not do this for you, stated so it reads as a boundary
    rather than a gap.** This door never holds the
    :class:`~ccf.products.contract.RegisteredProductClass`. It hands you a
    tenant, a class name, a version, a perspective and a request; the
    registered class — which is what both refusals compare against — is
    resolved *behind* this seam, inside your resolver. The SDK cannot call a
    comparison whose second operand it does not have, and reaching for it
    here would put an SDK-owned verdict on the serve path that ``D-IMPL-102``
    limb 3 declined.

    **Where a working example is.** The request refusal is called at
    ``examples/s1-01-hello-context-product/spine.py::assemble_and_serve``;
    the payload bind is called at
    ``examples/04-cross-process/producer_child.py::resolve``. Both are
    shipped, both run in CI, and both are this obligation discharged rather
    than described. ``CPS-03`` is recorded **Pending by design** under those
    two rulings for exactly this reason.
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
    expose_product_tool: bool = False,
    product_tool_description: str | None = None,
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

    **The parameterised tool is opt-in, and it takes two arguments rather
    than one** (``D-IMPL-126``). ``expose_product_tool`` defaults to ``False``
    and ``product_tool_description`` to ``None``; either without the other
    raises, in the ``D-03`` *requiredness is conditional on exposure* voice
    :func:`~ccf_runtime.mcp.experience.build_experience_server` already uses.
    Two arguments because *is this door open?* must be answerable by grepping
    for a boolean rather than inferred from whether a prose string happened
    to be supplied — a security surface is stated, never implied. Unlike the
    Experience server this module ships **no** default description constant:
    the prose an adopter's consumers read is a deployment value and not the
    SDK's to write (CINV-01; CLAUDE.md §6.4).

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
            against the principal's grant before anything is served. The
            tool is on the identical footing: it carries no ``role``
            parameter either, so it is never wider than the resource.
        expose_product_tool: Whether to register
            :data:`PRODUCT_REQUEST_TOOL`. ``False`` by default, so an
            existing deployment that upgrades and changes nothing gains no
            new door.
        product_tool_description: The prose that tool advertises. A
            deployment value (CINV-01); required exactly when
            ``expose_product_tool`` is ``True``.

    Raises:
        ValueError: ``expose_product_tool`` and ``product_tool_description``
            were not supplied together (D-03).

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision, and a
        library that picked an interface would be picking an exposure surface
        (T-06-14).
    """
    if expose_product_tool != (product_tool_description is not None):
        raise ValueError(
            "expose_product_tool and product_tool_description are supplied"
            " together or not at all: a tool exposed with no prose advertises"
            " nothing a consumer can read, and prose with no exposure is a"
            " description of a door that is not open. Requiredness is"
            " conditional on exposure (D-03), and the boolean is what makes"
            " 'is this door open?' answerable without inferring it from"
            " whether a string was supplied"
        )

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

    if expose_product_tool:

        @server.tool(
            name=PRODUCT_REQUEST_TOOL, description=product_tool_description
        )
        def request_context_product(
            tenant: str,
            product_class: str,
            version: str,
            subject: str,
            intent: str,
            freshness: str,
            asked_at: datetime,
            parameters: dict[str, Any] | None = None,
        ) -> str:
            """Serve the product that answers **this** question, as canonical JSON.

            The second surface of this door (``D-IMPL-126``, extending
            ``D-IMPL-108``). The resource beside it answers the class's
            standing answer; this answers a question, and the question is
            whitepaper §6.3's four axes — ``subject``, ``intent``,
            ``freshness``, ``asked_at`` — carried alongside the same three
            address segments the resource URI carries, so both surfaces
            address a product identically.

            **All four axes are required, deliberately.** The HTTP door
            refuses a *some-but-not-all* address because query parameters are
            individually omittable; a Tool's input schema can require them,
            which makes a partial address **unrepresentable** rather than
            refused — strictly stronger, and the same property that door
            already achieves for ``schema_name``. A caller wanting the
            class's standing answer reads the resource; it is not a call to
            this tool with four ``None``s, because there is no such call.

            **There is no ``role`` parameter.** The resource passes
            ``requested_role=None`` and lets the deployment's resolver derive
            the role from the verified grant; this does the same. A ``role``
            argument here would give the tool a wider surface than the
            resource beside it, which is the one thing a second door must
            never be.

            **The order below is the security property**, in
            :func:`~ccf_runtime.authz.product_entitlement
            .entitled_perspective`'s own phrasing, and it is the *identical*
            order and the identical call the resource makes:

            1. A timezone-naive ``asked_at`` is refused first, before any
               governance is consulted, because it is a malformed argument
               rather than a decision about a caller —
               :class:`NaiveAskedAtRefused`, on the
               :class:`~ccf_runtime.mcp.hitl_server.NaiveActionTimeRefused`
               precedent (D-IMPL-38).
            2. :func:`~ccf_runtime.authz.product_entitlement.verified_grant`
               reads the in-flight verified identity. That it is readable
               inside a **tool** handler is shipped fact, not assumption:
               ``hitl_server.py``'s authority tool does exactly this.
            3. :func:`~ccf_runtime.authz.product_entitlement
               .entitled_perspective` with the argument list the resource
               passes, ``requested_role=None`` included.
            4. **Its return value is bound and forwarded.** ``DI-15.5-03`` is
               the recorded defect where this very door *resolved an entitled
               perspective and then discarded it*; a new door that entitled
               correctly and then constructed its own would reproduce it
               exactly, and outcome parity against the resource would not
               see the difference. Never re-derived, never reconstructed.

            **The request's address is this door's, never the caller's.**
            ``schema_name`` and ``schema_version`` are bound to the
            ``product_class`` and ``version`` arguments *this handler already
            resolved and already entitled*, never to separate client fields,
            so a request addressed to another class cannot be expressed on
            this surface at all — the ``http_api/routes/product.py``
            property, transplanted.

            **``parameters`` is now carried, and the reason it once was not is
            kept rather than deleted, because half of it is still binding.**
            This paragraph used to read: *"``parameters`` is the empty mapping
            for that route's recorded reason: a flat tool-argument map cannot
            carry ``D-IMPL-103``'s declared nested types without the door
            guessing at coercions, and a declared-parameter surface here would
            make this tool wider than the HTTP door."* Its measured
            consequence was that *a product class whose request contract
            declares **any** required parameter is not reachable through this
            tool* — the door defect ``D-IMPL-133`` (Dave, 2026-08-14) ruled
            must be repaired: *"both doors carry ``parameters``."*

            The two halves of that reason resolved differently, and both
            resolutions are constraints on what this handler may do.

            *The coercion half is false as measured, and is why no coercion
            happens here.* A tool-argument map is **not** flat and not
            string-valued: MCP carries arguments as JSON, so a presented ``3``
            arrives an ``int``, a presented ``"3"`` arrives a ``str``, and a
            nested object arrives nested — ``D-IMPL-103``'s one level of
            declared nesting crosses intact with nothing to guess at. This
            handler therefore forwards the mapping **verbatim**. It coerces
            nothing, defaults nothing and inspects nothing; a wrong-typed value
            stays wrong-typed so that
            :func:`~ccf.products.request.refuse_request` can refuse it
            ``type-mismatch`` at the resolver, which is where ``D-IMPL-121``
            put every request verdict.

            *The width half is still binding, and is honoured by repairing
            both doors rather than neither.* ``D-IMPL-133`` is explicit that
            *"both, not one"* is the point — the HTTP route carried the
            identical hard-wiring in
            ``http_api/routes/product.py::build_router`` and now carries a
            mapping on the same terms, as self-describing JSON. Neither door is
            wider than the other, and
            ``tests/mcp/test_egress_parameters.py::assert_same_verdicts`` holds
            them to one shared case table so they cannot drift apart again.

            **The door still never validates**, which is why this is a repair
            of two lines rather than a seam widening: the declared world is
            closed at the resolver, against the
            :class:`~ccf.products.contract.RegisteredProductClass` this door
            never holds. An undeclared parameter is refused there
            (``undeclared-parameter``), and an omitted required one still
            reads ``missing-required-parameter`` — the difference being that
            it now names a caller who genuinely omitted it rather than every
            caller alike.

            Omitting the argument entirely is the empty mapping, which is the
            positive statement *this question needs nothing beyond its four
            axes*. It is optional rather than required because the four §6.3
            axes are the **address** and are required together, while the
            declared remainder is not part of the address — and because a
            deployment that adopted this tool before ``D-IMPL-133`` keeps
            working unchanged.

            **What this tool returns is a** :class:`~ccf.products.door.DoorOutcome`
            **and no longer the bare vessel** (``D-IMPL-148`` and its
            **Addendum A**, Dave, 2026-08-17). Two things ride the envelope that
            had nowhere to go while the return was the product's bytes alone:

            1. **A refusal, as the return value rather than a raise.** Measured
               against ``mcp==1.28.1``, FastMCP wraps a raised tool exception as
               ``ToolError: Error executing tool <name>: <message>`` and
               delivers it ``isError=True`` with that prose prefix, so a client
               wanting the governed answer would have to string-parse a server's
               wording. :func:`~ccf.products.door.door_refusal` renders what the
               resolver answered with — a ready-made
               :class:`~ccf.products.refusal.RefusalEnvelope` passes through
               untouched, a bare refusal value is translated against the
               question this handler carried.
            2. **The replay reference.** ``ServedProduct`` carries it and every
               shipped door discarded it, which
               :class:`~ccf.client.wire.WireOutcome` had already named *"a
               defect the client seam exists to fix rather than a feature
               request"*. It rides as a **sibling** of the vessel, never inside
               it: the vessel's bytes *are* the product, so anything carried
               within them changes the address they claim. The HTTP door
               publishes the identical string under
               :data:`~ccf_runtime.http_api.routes.REPLAY_REF_HEADER` because it
               has a header channel and this surface does not — the asymmetry is
               a property of the transports, exactly as
               :func:`~ccf_runtime.http_api.routes.canonical_response` already
               records for the content address.

            **The vessel is still not re-serialized, and that claim is now
            stated at the level it is true.** ``product_json`` carries the
            *identical* expression the resource returns —
            ``canonical_bytes(...).decode("utf-8")`` over the same vessel — as
            **text**, so ``sha256`` of it is the producer's content address with
            no second rendering anywhere on the path. What moved is the frame
            around those bytes, not the bytes; ``D-IMPL-119`` limb 3(b) and
            ``D-IMPL-124`` Shape B are still inherited by construction, because
            the whole vessel is still what gets serialized.

            **The resource beside this tool is deliberately unchanged.** It has
            no envelope and no header, its body *is* the vessel, and it carries
            no request — so it has no sibling channel for a reference and no
            question for a refusal envelope to name. Giving it one means making
            it a different resource, which is not what either ruling asked for.

            **A governance refusal is still raised and never enveloped.**
            ``ProductEntitlementRefused`` is decided *before* the resolver is
            reached, and entitlement at the client seam is on the v0 not-list;
            rendering it as a fabric refusal would say "the fabric answered no"
            about a caller the fabric never answered at all. The line is drawn
            here and asserted in
            ``tests/mcp/test_egress_refusal_envelope.py``.

            Raises:
                NaiveAskedAtRefused: ``asked_at`` carries no UTC offset.
                ProductEntitlementRefused: the caller is not entitled to this
                    class, or not to the resolved role. Deliberately raised
                    rather than enveloped — see above.
                ProductNotServable: the resolver has no product there.
                TypeError: the resolver answered with neither a served shape nor
                    a refusal this envelope translates — a wiring defect, and
                    never reported to a caller as a governed "no".
            """
            if (
                asked_at.tzinfo is None
                or asked_at.tzinfo.utcoffset(asked_at) is None
            ):
                raise NaiveAskedAtRefused(
                    f"asked_at {asked_at.isoformat()!r} carries no UTC"
                    " offset; the instant a question was asked as-of is the"
                    " boundary a replay resolves against and cannot be"
                    " ambiguous (D-IMPL-38)"
                )
            perspective = entitled_perspective(
                grant=verified_grant(),
                tenant=tenant,
                product_class=product_class,
                requested_role=None,
                entitlement_source=entitlement_source,
                perspective_resolver=perspective_resolver,
            )
            asked = ProductRequest(
                schema_name=product_class,
                schema_version=version,
                subject=subject,
                intent=intent,
                freshness=freshness,
                asked_at=asked_at,
                # Verbatim: no coercion, no defaulting, no inspection. The
                # declared world is closed at the resolver (D-IMPL-121), and a
                # door that touched these values would be rendering a verdict
                # it is not the one holding the class to compare against.
                parameters=dict(parameters or {}),
            )
            resolved = resolver(
                tenant=tenant,
                product_class=product_class,
                version=version,
                perspective=perspective,
                request=asked,
            )
            refusal = door_refusal(
                resolved,
                asked=asked,
                product_class=product_class,
                version=version,
            )
            if refusal is not None:
                return canonical_bytes(
                    DoorOutcome(
                        product_json=None, replay_ref=None, refusal=refusal
                    )
                ).decode("utf-8")
            answer = served_answer(resolved)
            return canonical_bytes(
                DoorOutcome(
                    product_json=canonical_bytes(answer.product).decode("utf-8"),
                    replay_ref=answer.replay_ref,
                    refusal=None,
                )
            ).decode("utf-8")

    return server
