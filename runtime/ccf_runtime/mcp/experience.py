"""The Experience-surface MCP edge — Context Products and agents, one front door.

CLAUDE.md §8.3 ("MCP server — Context Products and agents exposed as MCP
Resources and MCP Tools. The primary surface for external agent runtimes
consuming the fabric") and §7.1 (the Experience Layer access surface);
SDK-defined — an extension beyond the whitepaper, and it says so. This is
front door 1 of the three v0 Experience Layer surfaces, and it discharges the
D-GATE-I.3 named deferral (EXPR-01).

**A fourth role, a fourth module (§7.1; T-07-22).** The egress role serves
live products to fabric-internal consumers; the artifact role persists
immutable artifacts at rest; the HITL role carries human authority. This
module is the *front door*: products **and** agents, for external agent
runtimes. Each role keeps its own module and its own URI scheme, and
``tests/invariants/test_mcp_role_separation.py`` is what keeps that true —
the sibling roles' schemes do not appear anywhere in this module and must
not.

**What this server cannot do (D-22-scoped).** It holds no fabric handle of
any kind: no graph read or write surface, no operator registry, no Control
Plane handle, and — decisively — **no agent construction path**. The agent
Tools resolve through injected Protocol callables the deployment supplies,
and the deployment's callables go through the Agent Factory and the Control
Plane exactly as every in-process client does (CLAUDE.md §6.4 — the factory
is the only construction path; T-07-20 — zero privileged paths). The honest
claim is the structural one: nothing on this module's shape offers a route
into L2, L3, or agent construction, and the source assertions in
``tests/crossproc/test_experience_edge.py`` grep this very file to keep it
that way.

**Tool prose is never authored here (CINV-01; D-IMPL-56).** An exposed
agent's listing composes artifact-carried values only — the definition's
declared name, version, and archetype composition — and each bound skill's
tool surface is rendered by the one shared derivation,
:func:`ccf.skills.toolsurface.render_tool_surface`. ``procedure`` skills
have no seam-2 tool surface by ruling and are omitted from the listing,
never defaulted into one (T-07-05).

**Tenancy is a per-call argument, never a constructor field** (INV-CH7-16;
T-07-21), following the egress precedent: one server over a shared
deployment must not be able to serve a product or list an agent into the
wrong tenant by positional accident.

**Authenticated (D-26).** The verifier/settings pair is required, and
required together, exactly as on the artifact server: a server given a
verifier and no settings would look authenticated and refuse nothing.

**And entitled (15.5-06).** Authentication was never the whole question. Until
this plan, this module's ``context_product`` resource served whatever the
deployment's resolver held to *any* verified caller, under whatever role that
caller's downstream chose — the same principal-free three-string signature the
egress edge and the HTTP route carry. **Why the front door is gated at all**,
since a later reader will ask why two MCP modules run the same check: this is
the surface external agent runtimes reach, the egress role is the
fabric-internal one, and a fabric whose external door is less governed than its
internal one has its threat model backwards. This phase's founding complaint is
*"an MCP server in front of a database"*; shipping the SDK's own front door
ungated would be that complaint, self-inflicted.

The entitlement source and the perspective resolver are therefore **required**
keyword-only parameters on the same terms as the verifier pair — there is no
inert configuration of this builder — and both they and the resolution order
are **imported** from :mod:`ccf_runtime.authz.product_entitlement`, never
re-declared here. That module is a package neither MCP role owns, which is what
lets three doors share one definition of "entitled" while
``tests/invariants/test_mcp_role_separation.py`` keeps the roles themselves
from importing each other. A second ``PerspectiveResolverProtocol`` in this
module would be a second reading of the phase's central security property.

**The tools were not (D-IMPL-128; D-IMPL-129), and here is every one of them.**
Until plan 16-24 the paragraph above was true of the ``context_product``
*resource* and of nothing else on this server. ``get_context`` took a tenant
and an entity from the client and handed both to the deployment's provider
having called neither of the two governance functions — one module, two doors
onto assembly, one of them gated. ``D-IMPL-128`` ruled that a missing gate on a
client-parameterised handler is **evidence about a class, not an incident**,
and required every tool this module can register to be checked for the same
shape. This is that class, enumerated. Two are now gated; **three are not**,
and ``D-IMPL-129`` rules that disposition rather than leaving it unstated.

============================  =========================  ====================  ===============================
Surface                       Client-supplied arguments  Reaches               Verdict
============================  =========================  ====================  ===============================
``context_product`` resource  tenant, class, version     the product resolver  entitled (15.5-06)
``get_context`` tool          tenant, entity             the context provider  entitled (D-IMPL-128 limb 1)
``get_lineage`` tool          none                       the lineage provider  entitled (D-IMPL-129)
``list_agents`` tool          tenant                     the agent directory   tenant-decided (``SEC-018``)
``invoke_agent`` tool         tenant, key, version,      the agent invoker     tenant-decided (``SEC-018``)
                              skill, arguments
``get_replay_record`` tool    none                       the replay reader     tenant-decided (``SEC-018``)
============================  =========================  ====================  ===============================

**Why the two gated ones could be gated.** ``get_context`` reaches Context
Product assembly, which is exactly what a
:class:`~ccf.products.entitlement.ProductEntitlementPolicy` decides by
construction; it is decided against the caller's **own** ``tenant`` argument, so
naming a foreign tenant means being decided against that tenant's policy rather
than trusted. ``get_lineage`` returns a *field of the vessel the resource
already serves whole*, so the policy deciding who may receive the class decides
who may receive a field of it — no new vocabulary is invented, and because that
tool carries no arguments at all its address is deployment-declared
(``lineage_tenant``, ``entitled_product_class``).

**Tenancy and product entitlement are different questions, and only one of
them was ever open** (``SEC-018``). The three tools above are now
**tenant-decided**: :class:`~ccf_runtime.mcp.tenancy.TenantGuardedServer`
installs the decision at registration, so each refuses a caller whose verified
grant does not carry the tenant the call acts on. That needed no new
vocabulary — :class:`~ccf_runtime.mcp.auth.TokenGrant` now says which tenants
its bearer may reach, and *whose agents, whose dispatch, whose replay record*
is answerable from it directly.

**What ``D-IMPL-129`` declined is still declined, and deliberately.** The
artifact these doors would be decided against for *product* entitlement is
``ProductEntitlementPolicy``, whose grants are ``permitted_schema_names`` and
``permitted_roles``
(``runtime/ccf_runtime/authz/product_entitlement.py::ProductEntitlementSourceProtocol``)
and which says nothing about agents and nothing about replay records. Deciding
an agent invocation against it would assert *entitlement to receive product
class C implies permission to invoke any agent in tenant T* — a semantic the
SDK would be **inventing**, which CLAUDE.md §11 forbids in those words. So
within the caller's own tenant these three still assert verified identity and
decide nothing further:

* ``list_agents`` discloses that tenant's agent population with declared
  versions, archetype compositions and bound skill tool surfaces.
* ``invoke_agent`` dispatches a declared agent's bound skill through the
  deployment's injected invoker. It is registered ``mutating``.
* ``get_replay_record`` serves the five-dimension Decision Replay record — the
  widest disclosure on this server, dimension 4 carrying perspective
  conditioning and principal identity.

**What would close the remaining limb**, named so a later phase completes a
design rather than reopening one:
``runtime/ccf_runtime/authz/protocol.py::TenantAuthorizerProtocol``
with new action ids beside
``runtime/ccf_runtime/authz/refusals.py::ACTION_PRODUCT_RETRIEVE``
and an adopter-registered policy artifact. That is a new required builder seam
and a new artifact type; ``D-IMPL-129`` assigns no owner, and until an
authorised authorization workstream opens it, **no plan may cite these three
tools' shipping as evidence that agent-scoped entitlement is unnecessary.**
The residual is bounded by the caller's own tenant, which it was not before.

**The three entitlement paths are delivery boundaries, and this module only
encodes them** (``D-IMPL-254``; ``D-IMPL-256`` (3), Dave: *"leaving them
untouched means 24.6 would knowingly ship another delivery seam violating the
very architecture the phase exists to establish"*). Each of the three calls
:func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement` and encodes
what comes back: an entitled
:class:`~ccf.projection.plan.Perspective` continues exactly as before, and a
:class:`~ccf.products.refusal.RefusalEnvelope` is returned as the response's
canonical bytes — the same governed shell the standing resource carries, so an
external MCP client reads one shape across the SDK's MCP doors and a governed
*"you may not"* never arrives as a transport error. **Replay belongs to the
determination step in** :mod:`ccf_runtime.authz.delivery_boundary`, which this
module calls and never re-implements: nothing here mints a record, reads a
clock, discloses, or catches
:class:`~ccf_runtime.authz.product_entitlement.ProductEntitlementRefused`. The
scope is exactly those three paths and the mechanism they need — *"not a
general experience-server rewrite"* — so ``ToolError`` on these paths remains
what it always was, the seams' own failures, and is not widened here.

Server name, bind address, token values, tenant identifiers, agent names,
principal identifiers, role names, and skill vocabulary are all deployment
values supplied by the caller. This module holds none of them (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import door_refusal, served_answer
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.serve import ServedProduct
from ccf.products.request import ProductRequest
from ccf.products.resolver import RefusalRecorderProtocol
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SkillCatalogEntry
from ccf.skills.toolsurface import render_tool_surface
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_MCP_RESOURCE,
    SURFACE_MCP_TOOL,
    govern_absence,
    govern_entitlement,
    recorded_boundary,
)
from ccf_runtime.mcp.tenancy import TenantGuardedServer
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementSourceProtocol,
    verified_grant,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "DEFAULT_INVOKE_AGENT_DESCRIPTION",
    "DEFAULT_LIST_AGENTS_DESCRIPTION",
    "DEFAULT_PRODUCT_RESOURCE_DESCRIPTION",
    "EXPERIENCE_PRODUCT_URI_SCHEME",
    "EXPERIENCE_PRODUCT_URI_TEMPLATE",
    "EXPERIENCE_TOOLS",
    "GET_CONTEXT_TOOL",
    "GET_LINEAGE_TOOL",
    "GET_REPLAY_RECORD_TOOL",
    "INVOKE_AGENT_TOOL",
    "LIST_AGENTS_TOOL",
    "AgentDirectoryProtocol",
    "AgentInvokerProtocol",
    "AgentToolCatalog",
    "AgentToolListing",
    "AgentToolSurface",
    "ContextProviderProtocol",
    "ExperienceProductNotServable",
    "ExperienceProductResolverProtocol",
    "ExposedAgent",
    "LineageProviderProtocol",
    "ReplayRecordReaderProtocol",
    "agent_tool_listing",
    "build_experience_server",
    "experience_product_uri",
]

#: The front-door product scheme. Its own scheme, deliberately: a replay
#: record holding a front-door address must never be confusable with an
#: egress (live, TTL-bound) or artifact (immutable, content-addressed)
#: address — the same repudiation split T-06-16 established for the first
#: two roles.
EXPERIENCE_PRODUCT_URI_SCHEME = "ccf-experience-product"

#: The templated resource this server registers: whose product, what kind,
#: which schema lane — the same three facts the egress edge addresses by.
EXPERIENCE_PRODUCT_URI_TEMPLATE = (
    f"{EXPERIENCE_PRODUCT_URI_SCHEME}://{{tenant}}/{{product_class}}/{{version}}"
)

#: Media type of the served product body — canonical JSON, and saying so is
#: what lets a consumer parse it without sniffing.
PRODUCT_MIME_TYPE = "application/json"

#: The agent-discovery Tool: registered agents for one tenant, with their
#: currently-bound skill surfaces.
LIST_AGENTS_TOOL = "list_agents"

#: The agent-invocation Tool: one bound skill of one declared agent,
#: dispatched through the deployment's injected factory path.
INVOKE_AGENT_TOOL = "invoke_agent"

#: The external context-consumption Tool: one tenant's entity-scoped
#: Context Product, resolved through the deployment's injected context
#: provider. Promoted from deployment-side composition and registered by
#: default (D-IMPL-74; Dave, 2026-08-02) — external context consumption is
#: the primary adoption path, so the front door serves it out of the box.
GET_CONTEXT_TOOL = "get_context"

#: The lineage Tool: the served product's lineage, resolved through the
#: deployment's injected lineage provider. Default-registered (D-IMPL-74).
GET_LINEAGE_TOOL = "get_lineage"

#: The replay-record Tool: the most-recent Decision Replay record as
#: canonical JSON, resolved through the deployment's injected reader.
#: Default-registered (D-IMPL-74).
GET_REPLAY_RECORD_TOOL = "get_replay_record"

#: Every Tool this server can register — the default allowlist. A
#: deployment passes a subset to :func:`build_experience_server` to keep a
#: tool off the wire entirely: a tool absent from the allowlist is never
#: registered, so ``tools/list`` cannot advertise it (D-IMPL-74, the D-05
#: exposure control; registration-time omission, never post-hoc filtering).
EXPERIENCE_TOOLS = frozenset(
    {
        LIST_AGENTS_TOOL,
        INVOKE_AGENT_TOOL,
        GET_CONTEXT_TOOL,
        GET_LINEAGE_TOOL,
        GET_REPLAY_RECORD_TOOL,
    }
)

#: What :data:`LIST_AGENTS_TOOL` advertises when the deployment supplies no
#: description of its own (D-13; Dave, 2026-08-02). The agent tools take a
#: default and the three consumption tools do not, deliberately: the agent
#: tools' shape is SDK mechanism, so the SDK can state it without authoring a
#: deployment's prose (CINV-01; CLAUDE.md §6.4).
DEFAULT_LIST_AGENTS_DESCRIPTION = (
    "List a tenant's exposed agents and their bound skill tool surfaces."
)

#: What :data:`INVOKE_AGENT_TOOL` advertises absent a deployment value (D-13).
DEFAULT_INVOKE_AGENT_DESCRIPTION = (
    "Invoke one bound skill of one declared agent for one tenant."
)

#: What the templated product resource advertises absent a deployment value
#: (D-14; Dave, 2026-08-02) — the same treatment, for the same reason.
DEFAULT_PRODUCT_RESOURCE_DESCRIPTION = (
    "Serve a tenant's gate-admitted Context Product as canonical JSON."
)


class ExperienceProductNotServable(LookupError):
    """The resolver has no gate-admitted product at that front-door address.

    Raised by a deployment's resolver, not by this module — the counterpart
    of :class:`ccf_runtime.mcp.egress.ProductNotServable` on this role's
    surface. A ``LookupError`` because it is an absence.

    **It does not cross the product resource as itself** (``D-IMPL-260``
    P-C): the handler catches exactly this type around its resolver call and
    hands it to :func:`~ccf_runtime.authz.delivery_boundary.govern_absence`,
    so the absence reaches the caller as the recorded, disclosed
    ``subject-unavailable`` shell every other door answers with. The agent
    tools that raise it for *their* absences are not product doors and keep
    their own posture.
    """


@runtime_checkable
class ExperienceProductResolverProtocol(Protocol):
    """What a deployment plugs into the front door's product leg.

    Structurally identical to
    :class:`~ccf_runtime.mcp.egress.ProductResolverProtocol`, so one
    deployment resolver can serve both roles — while the two modules stay
    separate (§7.1) and neither imports the other. Protocol rather than a base
    class (CLAUDE.md §11).

    **Widened alongside its egress twin, once** (``D-IMPL-108``). The two
    seams moved together deliberately: a deployment supplying one resolver to
    both doors must not find that only one of them forwards what it
    authorized. See the egress Protocol for why neither new argument is
    defaulted and why ``request`` is ``None`` on an MCP surface.

    **TWO REFUSALS THIS DOOR DOES NOT CALL, AND YOUR RESOLVER MUST.** Stated
    here in full rather than by cross-reference, because a resolver author
    reads the Protocol they are implementing and not its twin. The SDK ships
    both comparisons complete and tested, and no shipped door invokes either
    one — a ruling (``D-IMPL-113``, extended to the second refusal by
    ``D-IMPL-121``, Dave), not an omission:

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

    **Why the SDK does not do this for you.** This door never holds the
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
    ``archive/examples/04-cross-process/producer_child.py::resolve``. Both are
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
    ) -> ServedProduct | RefusalEnvelope:
        """Return the served product at that address, under ``perspective``, or the governed refusal.

        ``D-IMPL-260`` P-A: the only shapes a door releases — a
        :class:`~ccf.replay.serve.ServedProduct` (recorded before it was
        returned) or the recorded, disclosed
        :class:`~ccf.products.refusal.RefusalEnvelope` the SDK's recorder
        hands back. A bare vessel or a bare refusal value is refused at the
        door as :class:`~ccf.products.door.UngovernedResolverResult`.

        Args:
            tenant: The tenant the product is addressed under.
            product_class: The Context Product class being requested.
            version: The class's own semver lane (INV-CH7-49).
            perspective: The Π role-conditioning this door's entitlement
                authorized. Required and non-nullable — ``DI-15.5-03``.
            request: The caller's typed question, or ``None`` when the surface
                carries no way to ask. Required with no default; this door's
                URI template has no query surface, so it passes ``None``.

        Raises:
            ExperienceProductNotServable: no such product. The resource
                handler turns it into the governed ``subject-unavailable``
                shell (``D-IMPL-260`` P-C); it never reaches a caller as an
                error.
        """
        ...


class ExposedAgent(CCFContract):
    """One declared agent a deployment exposes on the front door.

    Artifact-carried values in their entirety (CINV-01): the Control Plane
    key and pinned version the invoker will construct against, the
    definition's own declared identity, and the agent's *currently-bound*
    skill entries (CLAUDE.md §6.2 channel 2 — skills the agent has not been
    granted do not exist from this surface).
    """

    definition_key: str
    definition_version: str
    name: str
    artifact_version: str
    archetypes: tuple[str, ...]
    skills: tuple[SkillCatalogEntry, ...]


class AgentToolSurface(CCFContract):
    """One bound skill's rendered seam-2 surface, per the shared derivation."""

    skill: str
    description: str
    input_schema: dict[str, Any]


class AgentToolListing(CCFContract):
    """One agent as an MCP Tool listing — identity plus rendered surfaces.

    ``description`` composes artifact-carried values only, in the
    :func:`ccf.skills.toolsurface.render_tool_surface` voice: declared name,
    declared version, declared archetype composition. Nothing is authored
    here (CINV-01; CLAUDE.md §6.4).
    """

    definition_key: str
    definition_version: str
    name: str
    artifact_version: str
    archetypes: tuple[str, ...]
    description: str
    tools: tuple[AgentToolSurface, ...]


class AgentToolCatalog(CCFContract):
    """What :data:`LIST_AGENTS_TOOL` returns for one tenant."""

    tenant: str
    agents: tuple[AgentToolListing, ...]


@runtime_checkable
class AgentDirectoryProtocol(Protocol):
    """Where the front door learns which agents one tenant exposes.

    The deployment's statement, resolved per call: which declared agents are
    reachable from outside is Control Plane configuration, and the SDK has
    business only with the signature.
    """

    def __call__(self, *, tenant: str) -> tuple[ExposedAgent, ...]:
        """Return the tenant's exposed agents; empty for an unknown tenant."""
        ...


@runtime_checkable
class AgentInvokerProtocol(Protocol):
    """The deployment's factory-path invocation seam (T-07-20).

    The callable a deployment supplies here is expected to construct the
    named agent through the Agent Factory against its Control Plane — the
    only supported construction path (CLAUDE.md §6.4) — dispatch the named
    bound skill, and land the decision in a Decision Replay record before
    returning. This module cannot do any of that itself, which is the
    structural half of the zero-privileged-paths claim; that the
    deployment's callable actually does it is demonstrated by
    ``tests/crossproc/test_experience_edge.py``, not assumed (D-22).
    """

    def __call__(
        self,
        *,
        tenant: str,
        definition_key: str,
        definition_version: str,
        skill: str,
        arguments: Mapping[str, str],
    ) -> str:
        """Invoke one bound skill; return the canonical-JSON result verbatim."""
        ...


@runtime_checkable
class ContextProviderProtocol(Protocol):
    """What a deployment plugs into :data:`GET_CONTEXT_TOOL`.

    SDK-defined, an extension beyond the whitepaper (CLAUDE.md §8.3 — the
    Experience front door; §7.1 — the Experience Layer access surface).
    The deployment resolves the entity-scoped product — and performs any
    serve-recording it owes its own replay posture — behind this seam; the
    module holds no fabric handle of any kind (T-07-20). Protocol rather
    than a base class (CLAUDE.md §11), keyword-only like every sibling seam.

    **Widened to receive the authorized perspective** (``D-IMPL-128`` limb 1,
    on ``D-IMPL-108``'s stated reasoning). ``perspective`` is required and has
    **no default**: a door that computes an authorized perspective and discards
    it is ``DI-15.5-03`` reintroduced one layer down, where nothing on the wire
    would show it, and a defaulted governance argument is one an implementor
    can be written without noticing.

    **Your obligation, and accepting the argument is not it.** A provider that
    takes ``perspective`` and ignores it has received the conditioning this
    door authorized and served regardless — the same defect, one layer
    further down. This product was assembled under some capacity; compare it
    with the one you are handed and refuse a mismatch. The shipped example
    performs exactly that comparison in
    ``archive/examples/external/00-hello-context/serve.py::context_provider``, beside a
    resolver doing the same thing for the resource leg.
    """

    def __call__(
        self, *, tenant: str, entity: str, perspective: Perspective
    ) -> str:
        """Return the entity-scoped Context Product as canonical JSON.

        Args:
            tenant: The tenant the product is addressed under — the caller's
                own argument, and the one the entitlement was decided against.
            entity: The entity the product is scoped to.
            perspective: The Π role-conditioning this door's entitlement
                authorized. Required and non-nullable; see the class
                docstring for what you owe it.

        Raises:
            ExperienceProductNotServable: nothing servable at that address, or
                the perspective is not the one this product was assembled
                under.
        """
        ...


@runtime_checkable
class LineageProviderProtocol(Protocol):
    """What a deployment plugs into :data:`GET_LINEAGE_TOOL`.

    SDK-defined (CLAUDE.md §8.3, §7.1). The deployment decides which
    product's lineage the front door serves; this module only carries the
    string it is handed (T-07-20).

    **Deliberately *not* widened alongside its sibling**, so the asymmetry
    reads as a decision rather than an oversight.
    :class:`ContextProviderProtocol` *resolves a product*, and ``D-IMPL-108``
    ruled that a resolution must receive the conditioning the door authorized.
    This seam returns a field of an **already-resolved** product and has no
    resolution to condition. Forwarding a perspective into it would imply a
    per-principal scoping of lineage the fabric cannot perform — an absence
    ``D-IMPL-119`` limb 2 measured on the shipped path and ``D-IMPL-124``
    Shape D was blocked on. The door still entitles the call; it just has
    nothing to hand you.
    """

    def __call__(self) -> str:
        """Return the served product's lineage as canonical JSON.

        Raises:
            ExperienceProductNotServable: no lineage is servable yet.
        """
        ...


@runtime_checkable
class ReplayRecordReaderProtocol(Protocol):
    """What a deployment plugs into :data:`GET_REPLAY_RECORD_TOOL`.

    SDK-defined (CLAUDE.md §8.3, §7.1). The deployment reads the
    most-recent Decision Replay record from wherever it persists records;
    this module never touches a store of its own (T-07-20).
    """

    def __call__(self) -> str:
        """Return the most-recent Decision Replay record as canonical JSON.

        Raises:
            ExperienceProductNotServable: no decision has been recorded yet.
        """
        ...


def experience_product_uri(
    *, tenant: str, product_class: str, version: str
) -> str:
    """Render the front-door URI for one product address.

    Exists so the server, the client, and the tests all agree what the URI
    *is* rather than each formatting it — the egress precedent.
    """
    return (
        f"{EXPERIENCE_PRODUCT_URI_SCHEME}://{tenant}/{product_class}/{version}"
    )


def _tool_address(*, tool: str, tenant: str, product_class: str) -> str:
    """Render the address a gated *tool* was decided against.

    The :attr:`~ccf.products.refusal.ResourceRequestIdentity.address` of a
    denial on :data:`GET_CONTEXT_TOOL` or :data:`GET_LINEAGE_TOOL`
    (``D-IMPL-256`` (1)). It sits beside :func:`experience_product_uri` for
    that function's own reason: the server, the tests and a replay reader agree
    what the address *is* rather than each formatting it.

    Two things it deliberately does not do. It never spells a scheme as a
    literal — it composes :data:`EXPERIENCE_PRODUCT_URI_SCHEME`, so the front
    door's addresses stay distinguishable from an egress or artifact address
    (T-06-16) and ``tests/invariants/test_mcp_role_separation.py`` keeps that
    true. And it carries **no version**, because these tools carry none: a
    version segment here would be a lane the SDK invented for an address the
    deployment never named.

    The tool travels as a fragment rather than a third path segment so a tool
    address cannot be misread as a product address whose version happens to be
    called ``get_context``: a resource address is three path segments with no
    fragment, a tool address is two with one.
    """
    return (
        f"{EXPERIENCE_PRODUCT_URI_SCHEME}://{tenant}/{product_class}#{tool}"
    )


def agent_tool_listing(agent: ExposedAgent) -> AgentToolListing:
    """Render one exposed agent's Tool listing — the pure derivation.

    Composes artifact-carried values only, and renders every bound skill
    through the one shared derivation (D-IMPL-56). ``procedure`` skills are
    omitted, never surfaced: they have no seam-2 tool surface by ruling —
    their instruction content travels by pinned reference through seam 1
    only (T-07-05).
    """
    surfaces: list[AgentToolSurface] = []
    for entry in agent.skills:
        if entry.skill_type == "procedure":
            continue
        rendered = render_tool_surface(entry)
        surfaces.append(
            AgentToolSurface(
                skill=entry.name,
                description=rendered.description,
                input_schema=rendered.input_schema,
            )
        )
    return AgentToolListing(
        definition_key=agent.definition_key,
        definition_version=agent.definition_version,
        name=agent.name,
        artifact_version=agent.artifact_version,
        archetypes=agent.archetypes,
        description=(
            f"{agent.name}@{agent.artifact_version}"
            f" [{','.join(agent.archetypes)}]"
        ),
        tools=tuple(surfaces),
    )


def _missing(tool: str) -> str:
    """The D-03 refusal, phrased once so every tool refuses alike."""
    return (
        f"{tool} is allowlisted but its provider or description was not"
        " supplied; a tool this server admits must have both"
        " (agent-tool descriptions default; their providers do not)"
    )


def _missing_address(tool: str, parameter: str) -> str:
    """The declared-address refusal — worded apart from :func:`_missing`.

    A sibling rather than a widening of ``_missing``'s condition, and the
    separation is load-bearing rather than stylistic. Two shipped D-03
    assertions allowlist ``get_context`` and assert only that the tool's name
    appears in the refusal; folding this check into the same condition or the
    same wording would make both of them pass off *this* check regardless of
    whether their own leg still worked, and a gate that stops being one
    without failing is the worst kind (T-16-24-13).
    """
    return (
        f"{tool} is allowlisted but {parameter} was not supplied; a gated"
        " consumption tool is decided against an address the deployment"
        " declares, never one the client names"
    )


def _unexposed_address(tool: str, parameter: str) -> str:
    """The other direction: a governance value for a door that never opens."""
    return (
        f"{parameter} was supplied but {tool} is not in the allowlist; a"
        " governance value behind a door this server does not open is inert"
        " configuration, and a deployment that believed the door was open"
        " would learn nothing"
    )


def build_experience_server(
    *,
    server_name: str,
    product_resolver: ExperienceProductResolverProtocol,
    agent_directory: AgentDirectoryProtocol | None = None,
    agent_invoker: AgentInvokerProtocol | None = None,
    context_provider: ContextProviderProtocol | None = None,
    lineage_provider: LineageProviderProtocol | None = None,
    replay_record_reader: ReplayRecordReaderProtocol | None = None,
    get_context_description: str | None = None,
    get_lineage_description: str | None = None,
    get_replay_record_description: str | None = None,
    list_agents_description: str | None = None,
    invoke_agent_description: str | None = None,
    product_resource_description: str | None = None,
    token_verifier: TokenVerifier,
    auth_settings: AuthSettings,
    entitlement_source: ProductEntitlementSourceProtocol,
    perspective_resolver: PerspectiveResolverProtocol,
    refusal_recorder: RefusalRecorderProtocol | None = None,
    entitled_product_class: str | None = None,
    lineage_tenant: str | None = None,
    replay_record_tenant: str | None = None,
    tool_allowlist: frozenset[str] | None = None,
) -> FastMCP:
    """Build the authenticated Experience-surface server over six seams.

    ``stateless_http=True`` is load-bearing rather than a tuning choice: it
    is what makes the client's session-per-call cheap (:mod:`ccf.mcp.client`,
    and the held-session bridge that deadlocks without it).
    ``json_response=True`` pairs with it.

    Both ``token_verifier`` and ``auth_settings`` are required, and required
    *together*, because ``FastMCP`` installs its authentication middleware
    only when both are present (D-26, the artifact-server precedent).

    The three external-consumption Tools (:data:`GET_CONTEXT_TOOL`,
    :data:`GET_LINEAGE_TOOL`, :data:`GET_REPLAY_RECORD_TOOL`) register by
    default (D-IMPL-74; Dave, 2026-08-02): external context consumption is
    the primary adoption path, so the front door serves it out of the box.
    Their description strings are deployment values supplied here — like
    ``server_name`` — because this module authors no tool prose (CINV-01;
    CLAUDE.md §6.4).

    ``tool_allowlist`` is the D-05 exposure control: a tool absent from it
    is never registered, so ``tools/list`` cannot advertise it and the
    model physically cannot call it. Omission happens at registration
    time — nothing is filtered after the fact. ``None`` (the default)
    registers every tool in :data:`EXPERIENCE_TOOLS`.

    **The allowlist fails closed (D-01; Dave, 2026-08-02).** An entry naming
    a tool this module does not have is a ``ValueError``, not a silent
    no-op: a deployment that misspells a tool name would otherwise serve a
    surface it did not intend and learn nothing about it. Enforcement lives
    here, in mechanism, rather than in each deployment's composition.

    **This door entitles, so it holds a recorder or it is not built
    (``D-IMPL-256`` (2)).** ``refusal_recorder`` is requiredness in the same
    D-03 voice as everything above, except that its condition is always met:
    the templated product resource is not allowlist-gated, so *every* server
    this builder produces makes governed determinations, and there is no
    recorder-less configuration of it. The ``None`` default exists so the
    omission is refused by the one typed error rather than by a bare
    ``TypeError`` that would say nothing about why — the check runs
    :func:`~ccf_runtime.authz.delivery_boundary.recorded_boundary` **first**,
    ahead of the allowlist and provider checks, because it is the only one
    whose premise is nothing at all; the posture itself is written on
    :class:`~ccf_runtime.authz.delivery_boundary.UnrecordableDeliveryBoundaryError`
    and nowhere else, so the three doors that raise it cannot drift into three
    explanations of one rule.

    **Allowlisted implies supplied (D-03/D-04; Dave, 2026-08-02).** The
    three consumption seams and their prose are Optional parameters with
    ``None`` defaults — callers that pass everything are unaffected — but a
    tool the allowlist admits with no provider or no description behind it
    raises at build time, named. Requiredness is conditional on exposure,
    which is the only place it can be stated once the surface is
    configurable. The agent Tools and the product resource take SDK default
    descriptions instead (D-12/D-13/D-14): their shape is SDK mechanism, so
    describing it authors nobody's domain prose (CINV-01; CLAUDE.md §6.4).

    **The gated consumption tools carry a declared address (D-IMPL-128 limb
    1).** ``get_context`` and ``get_lineage`` are now entitled rather than
    merely authenticated, and an entitlement decides on a *(tenant, class)*
    pair. ``entitled_product_class`` supplies the class and is
    **deployment-supplied, never client-supplied**, for a reason a reviewer
    can check against the handler: the class the entitlement is decided
    against has to be the class the injected provider actually serves, and
    only the deployment knows that — a client-supplied class would let a
    caller name a class it *is* entitled to while the provider returned one it
    is not, the entitlement checking one operand while the door serves
    another. Note the contrast with the ``context_product`` **resource**,
    which may take its class from the client precisely because that same value
    *addresses the resolver*, so check and serve cannot diverge there.
    ``lineage_tenant`` exists because :data:`GET_LINEAGE_TOOL` carries **no
    arguments at all** — there is no tenant on the wire, and inventing one
    would be the SDK holding a deployment value (CINV-01). :data:
    `GET_CONTEXT_TOOL` needs no such parameter: it has a wire ``tenant``, and
    deciding against the caller's own argument is exactly the point.

    Requiredness is conditional on exposure like every D-03 value, and it
    fails in **both** directions: a gated tool allowlisted without its
    declared value raises, and a declared value supplied for a tool the
    allowlist does not admit raises too.

    The rule applies to the agent *providers* on the same terms: a
    deployment that allowlists neither agent tool supplies neither
    ``agent_directory`` nor ``agent_invoker``, rather than handing in dead
    callables to satisfy a signature. ``product_resolver`` stays
    unconditionally required because the templated product resource is not
    allowlist-gated — it registers on every server this builder produces,
    so its seam is never dead.

    Args:
        server_name: The name this server advertises. Deployment identity.
        product_resolver: The deployment's assemble-and-gate path. Always
            required: it backs the templated product resource, which is
            not allowlist-gated.
        agent_directory: The deployment's per-tenant agent exposure behind
            :data:`LIST_AGENTS_TOOL`. Required when that tool is
            allowlisted (D-03).
        agent_invoker: The deployment's factory-path invocation seam
            behind :data:`INVOKE_AGENT_TOOL`. Required when that tool is
            allowlisted (D-03).
        context_provider: The deployment's entity-scoped product resolution
            (and any serve-recording it performs) behind
            :data:`GET_CONTEXT_TOOL`. Required when that tool is
            allowlisted (D-03).
        lineage_provider: The deployment's lineage serving behind
            :data:`GET_LINEAGE_TOOL`. Required when allowlisted (D-03).
        replay_record_reader: The deployment's most-recent-record read
            behind :data:`GET_REPLAY_RECORD_TOOL`. Required when
            allowlisted (D-03).
        get_context_description: The prose :data:`GET_CONTEXT_TOOL`
            advertises. A deployment value (CINV-01); required when that
            tool is allowlisted (D-03).
        get_lineage_description: The prose :data:`GET_LINEAGE_TOOL`
            advertises. A deployment value (CINV-01); required when
            allowlisted (D-03).
        get_replay_record_description: The prose
            :data:`GET_REPLAY_RECORD_TOOL` advertises. A deployment value
            (CINV-01); required when allowlisted (D-03).
        list_agents_description: Overrides
            :data:`DEFAULT_LIST_AGENTS_DESCRIPTION` (D-12/D-13).
        invoke_agent_description: Overrides
            :data:`DEFAULT_INVOKE_AGENT_DESCRIPTION` (D-12/D-13).
        product_resource_description: Overrides
            :data:`DEFAULT_PRODUCT_RESOURCE_DESCRIPTION` (D-14).
        token_verifier: Verifies presented bearer tokens
            (:mod:`ccf_runtime.mcp.auth` ships the reference implementation).
        auth_settings: Issuer, resource-server identity, required scopes —
            deployment values in their entirety.
        entitlement_source: The deployment's per-principal entitlement
            decision seam for the product leg (15.5-06).
            :class:`~ccf_runtime.authz.product_entitlement
            .ControlPlaneProductEntitlementSource` is the reference
            implementation. Required, not optional-and-inert: this is the
            front door, and a deployment must not be able to stand it up
            answering every verified caller with every class.
        perspective_resolver: The deployment's role-derivation seam. The
            front-door product URI carries three segments and no role among
            them, so the resolver is called with ``requested_role=None`` and
            derives the role from the verified grant; whatever it proposes
            is checked against the principal's grant before anything is
            served.
        refusal_recorder: The ONE minting seam every denial this door reaches
            is recorded through (``D-IMPL-256`` (2)). Optional in the
            signature and required in fact — see the paragraph above.
            :class:`~ccf.products.resolver.ReplayRefusalRecorder` is the
            reference implementation, built over the artifact store the
            deployment's resolver already holds.
        entitled_product_class: The Context Product class the gated
            consumption tools are entitled against. A **deployment** value —
            the class the injected providers actually serve. Required when
            :data:`GET_CONTEXT_TOOL` or :data:`GET_LINEAGE_TOOL` is
            allowlisted; refused when neither is.
        replay_record_tenant: The tenant :data:`GET_REPLAY_RECORD_TOOL` is
            decided under. Required exactly when that tool is allowlisted, on
            ``lineage_tenant``'s terms and for the same reason: the tool takes
            no arguments, so its tenant is the deployment's to declare and
            there is no client value that could stand in for it (``SEC-018``).
        lineage_tenant: The tenant :data:`GET_LINEAGE_TOOL` is decided under,
            since that tool carries no arguments to decide against. Required
            when it is allowlisted; refused when it is not.
        tool_allowlist: Which Tools to register; ``None`` registers all of
            :data:`EXPERIENCE_TOOLS`.

    Raises:
        UnrecordableDeliveryBoundaryError: no ``refusal_recorder`` was
            supplied, or the one supplied does not conform
            (``D-IMPL-256`` (2)). Checked first, so a door misconfigured two
            ways reports this one.
        ValueError: The allowlist names a tool outside
            :data:`EXPERIENCE_TOOLS` (D-01), or a tool it admits has no
            provider or no description supplied (D-03), or a gated
            consumption tool it admits has no declared address supplied, or a
            declared address was supplied for a tool it does not admit
            (D-IMPL-128 limb 1).

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision, and a
        library that picked an interface would be picking an exposure
        surface (T-06-14).
    """
    # FIRST, ahead of every other check: this builder always entitles, so the
    # recorder's requiredness is unconditional while every check below is
    # conditional on what the allowlist admits. A door misconfigured in two
    # ways must report the structural defect rather than the typo.
    recorder = recorded_boundary(
        refusal_recorder=refusal_recorder, builder="build_experience_server"
    )

    if tool_allowlist is not None:
        unknown = frozenset(tool_allowlist) - EXPERIENCE_TOOLS
        if unknown:
            raise ValueError(
                f"tool_allowlist names unknown tools: {sorted(unknown)};"
                f" this server registers {sorted(EXPERIENCE_TOOLS)}"
            )
    allowed = EXPERIENCE_TOOLS if tool_allowlist is None else frozenset(tool_allowlist)

    # The "supplied but not exposed" direction, checked here because it can
    # only fire for tools the allowlist EXCLUDES — so it cannot pre-empt the
    # D-03 provider/description refusals inside the blocks below, which own
    # the tools the allowlist admits.
    if entitled_product_class is not None and not (
        {GET_CONTEXT_TOOL, GET_LINEAGE_TOOL} & allowed
    ):
        raise ValueError(
            _unexposed_address(
                f"neither {GET_CONTEXT_TOOL} nor {GET_LINEAGE_TOOL}",
                "entitled_product_class",
            )
        )
    if lineage_tenant is not None and GET_LINEAGE_TOOL not in allowed:
        raise ValueError(
            _unexposed_address(GET_LINEAGE_TOOL, "lineage_tenant")
        )
    if replay_record_tenant is not None and GET_REPLAY_RECORD_TOOL not in allowed:
        raise ValueError(
            _unexposed_address(GET_REPLAY_RECORD_TOOL, "replay_record_tenant")
        )

    door = TenantGuardedServer(
        FastMCP(
            server_name,
            stateless_http=True,
            json_response=True,
            token_verifier=token_verifier,
            auth=auth_settings,
        )
    )
    server = door.fastmcp

    @door.resource(
        EXPERIENCE_PRODUCT_URI_TEMPLATE,
        subject=door.from_argument("tenant"),
        mutating=False,
        mime_type=PRODUCT_MIME_TYPE,
        description=(
            product_resource_description
            if product_resource_description is not None
            else DEFAULT_PRODUCT_RESOURCE_DESCRIPTION
        ),
    )
    def context_product(tenant: str, product_class: str, version: str) -> str:
        """Serve one gate-admitted Context Product as canonical JSON.

        Authenticate, then entitle, then resolve. The auth middleware refuses
        an unverified caller before this body runs;
        :func:`~ccf_runtime.authz.product_entitlement.verified_grant` refuses
        if it somehow did not; and the entitlement decides on the resolved
        role before ``product_resolver`` is reached, so a refused caller
        moves no fabric. **And the perspective that decision authorized is
        then forwarded** (``DI-15.5-03``, closed by ``D-IMPL-108``): the door
        no longer discards it, so the product an external caller receives is
        shaped under the conditioning this door approved rather than under
        whatever the deployment's resolver would have derived on its own.

        ``request=None`` because this URI template carries no query surface —
        see the egress edge's handler for why the SDK does not manufacture a
        request the caller never sent.

        Canonical bytes, not ``model_dump_json``: the same serialization the
        content address is computed over, so a consumer that hashes what it
        received gets the address the producer would.

        **A denial here is a recorded decision, and this handler only encodes
        it** (``D-IMPL-256`` (1)/(3); criterion 36). The governed step minted
        it at the entitlement source's own declared instant, under a
        :class:`~ccf.products.refusal.ResourceRequestIdentity` naming this
        surface and the URI the caller addressed, and disclosed it before
        returning. What crosses is the shell's canonical bytes — the same
        ``mime_type`` carrying two shapes, told apart by the top-level
        ``kind`` key a product does not have.
        """
        decided = govern_entitlement(
            grant=verified_grant(),
            tenant=tenant,
            product_class=product_class,
            product_version=version,
            requested_role=None,
            parameters={},
            asked_at=None,
            surface=SURFACE_MCP_RESOURCE,
            address=experience_product_uri(
                tenant=tenant, product_class=product_class, version=version
            ),
            entitlement_source=entitlement_source,
            perspective_resolver=perspective_resolver,
            refusal_recorder=recorder,
        )
        if isinstance(decided, RefusalEnvelope):
            return canonical_bytes(decided).decode("utf-8")
        addressed = experience_product_uri(
            tenant=tenant, product_class=product_class, version=version
        )
        try:
            resolved = product_resolver(
                tenant=tenant,
                product_class=product_class,
                version=version,
                perspective=decided,
                request=None,
            )
        except ExperienceProductNotServable as absent:
            # `D-IMPL-260` P-C: the typed absence is a governed determination,
            # recorded and disclosed at the boundary, crossing as the common
            # shell rather than as this transport's own error.
            return canonical_bytes(
                govern_absence(
                    grant=verified_grant(),
                    tenant=tenant,
                    product_class=product_class,
                    product_version=version,
                    parameters={},
                    asked_at=None,
                    surface=SURFACE_MCP_RESOURCE,
                    address=addressed,
                    perspective=decided,
                    absent=absent,
                    entitlement_source=entitlement_source,
                    refusal_recorder=recorder,
                )
            ).decode("utf-8")
        # `D-IMPL-260` P-B: the SAME two translation functions the egress
        # resource and the HTTP route read a resolver's answer through — a
        # returned refusal crosses as its shell, a served vessel as its bytes,
        # and anything else is the wiring defect `served_answer` names rather
        # than an `AttributeError` on `.product`.
        refusal = door_refusal(resolved)
        if refusal is not None:
            return canonical_bytes(refusal).decode("utf-8")
        return canonical_bytes(served_answer(resolved).product).decode("utf-8")

    if LIST_AGENTS_TOOL in allowed:
        # D-03 applies to the agent seams on the same terms as the three
        # consumption seams: requiredness is conditional on exposure. A
        # deployment that allowlists no agent tools hands in no agent
        # callables — it does not supply dead ones to satisfy a signature.
        if agent_directory is None:
            raise ValueError(_missing(LIST_AGENTS_TOOL))
        directory_seam = agent_directory

        @door.tool(
            name=LIST_AGENTS_TOOL,
            subject=door.from_argument("tenant"),
            mutating=False,
            description=(
                list_agents_description
                if list_agents_description is not None
                else DEFAULT_LIST_AGENTS_DESCRIPTION
            ),
        )
        def list_agents(tenant: str) -> str:
            """List one tenant's exposed agents with their rendered tool surfaces.

            **Tenant-decided, product-entitlement-undecided** — and the two
            halves are different questions (``SEC-018``; ``D-IMPL-129``). The
            ``tenant`` argument stays the caller's and is now decided against
            the verified grant before this body runs, so a client-chosen
            foreign tenant's agent population is no longer disclosed. What
            ``D-IMPL-129`` declined remains declined: this tool is still not
            decided against ``ProductEntitlementPolicy``, whose grants name
            schemas and roles and say nothing about agents, because inventing
            that semantic is what CLAUDE.md §11 forbids. Within the caller's
            own tenant, any verified caller still receives the listing.
            """
            verified_grant()
            catalog = AgentToolCatalog(
                tenant=tenant,
                agents=tuple(
                    agent_tool_listing(agent)
                    for agent in directory_seam(tenant=tenant)
                ),
            )
            return canonical_bytes(catalog).decode("utf-8")

    if INVOKE_AGENT_TOOL in allowed:
        if agent_invoker is None:
            raise ValueError(_missing(INVOKE_AGENT_TOOL))
        invoker_seam = agent_invoker

        @door.tool(
            name=INVOKE_AGENT_TOOL,
            subject=door.from_argument("tenant"),
            mutating=True,
            description=(
                invoke_agent_description
                if invoke_agent_description is not None
                else DEFAULT_INVOKE_AGENT_DESCRIPTION
            ),
        )
        def invoke_agent(
            tenant: str,
            definition_key: str,
            definition_version: str,
            skill: str,
            arguments: dict[str, str],
        ) -> str:
            """Invoke one agent's bound skill through the injected factory path.

            Passed through verbatim: what the deployment's invoker produced is
            what the wire carries — this module adds nothing and interprets
            nothing (T-07-20).

            **The sharpest of the three, and the one that most needed the
            tenant axis** (``SEC-018``; ``D-IMPL-129``). Every argument here is
            still the client's — but ``tenant`` is no longer *trusted*: it is
            decided against the verified grant before the invoker is reached,
            so a verified caller can no longer dispatch a declared agent's
            bound skill inside a tenant it holds no grant for. Registered
            ``mutating``, because an agent dispatch is not a read: a stated
            stdio identity cannot reach it at all.

            What ``D-IMPL-129`` declined remains declined — this is not
            decided against ``ProductEntitlementPolicy``, for the reason that
            ruling gives — and the remaining gap is now bounded by the
            caller's own tenant rather than unbounded.
            """
            verified_grant()
            return invoker_seam(
                tenant=tenant,
                definition_key=definition_key,
                definition_version=definition_version,
                skill=skill,
                arguments=arguments,
            )

    if GET_CONTEXT_TOOL in allowed:
        # Narrowed before the closure so the tool body captures a
        # non-Optional name (D-03's check is what makes that sound).
        if context_provider is None or get_context_description is None:
            raise ValueError(_missing(GET_CONTEXT_TOOL))
        # STRICTLY AFTER the D-03 check, and with its own wording. See
        # `_missing_address` for why that ordering is a security property of
        # the *test suite* rather than a matter of taste.
        if entitled_product_class is None:
            raise ValueError(
                _missing_address(GET_CONTEXT_TOOL, "entitled_product_class")
            )
        context_seam = context_provider
        context_class = entitled_product_class

        @door.tool(
            name=GET_CONTEXT_TOOL,
            subject=door.from_argument("tenant"),
            mutating=False, description=get_context_description
        )
        def get_context(tenant: str, entity: str) -> str:
            """Serve one tenant's entity-scoped product via the injected seam.

            Authenticate, then entitle, then resolve — and **the order is the
            security property**, not a style. Until ``D-IMPL-128`` limb 1 this
            body was ``return context_seam(tenant=tenant, entity=entity)``:
            both arguments client-supplied, no grant check, on the SDK's
            *external* front door, beside a resource on the same server that
            checked properly.

            It now runs the identical sequence that resource runs — the same
            call with the same argument set, ``requested_role=None`` included,
            not an equivalent-looking reimplementation. Two consequences worth
            naming: the entitlement is decided against **the caller's own
            ``tenant`` argument**, so naming a foreign tenant means being
            decided against that tenant's policy and refused rather than
            trusted; and the refusal happens before ``context_seam`` is
            reached, so a refused caller moves no fabric.

            The class is the deployment's, never the caller's — see the
            builder docstring for why check and serve would otherwise be free
            to diverge. And the perspective the decision authorized is
            **forwarded**, per ``D-IMPL-108``: a door that computed it and
            dropped it would be ``DI-15.5-03`` one layer down.

            **A denial here is a recorded decision, and this handler only
            encodes it** (``D-IMPL-256`` (1)/(3); criterion 36). The governed
            step minted it at the entitlement source's own declared instant,
            under a resource-request identity naming this tool's
            deployment-declared address, and disclosed it before returning;
            the shell's canonical bytes are what the tool answers, so the
            refusal is a governed response rather than a tool error.
            """
            decided = govern_entitlement(
                grant=verified_grant(),
                tenant=tenant,
                product_class=context_class,
                # No version on the wire, and saying so is the positive claim:
                # this tool addresses a class, not a lane.
                product_version=None,
                requested_role=None,
                # What the caller supplied — the request identity's
                # parameters, never a value this module chose.
                parameters={"entity": entity},
                asked_at=None,
                surface=SURFACE_MCP_TOOL,
                address=_tool_address(
                    tool=GET_CONTEXT_TOOL,
                    tenant=tenant,
                    product_class=context_class,
                ),
                entitlement_source=entitlement_source,
                perspective_resolver=perspective_resolver,
                refusal_recorder=recorder,
            )
            if isinstance(decided, RefusalEnvelope):
                return canonical_bytes(decided).decode("utf-8")
            return context_seam(
                tenant=tenant, entity=entity, perspective=decided
            )

    if GET_LINEAGE_TOOL in allowed:
        if lineage_provider is None or get_lineage_description is None:
            raise ValueError(_missing(GET_LINEAGE_TOOL))
        if entitled_product_class is None:
            raise ValueError(
                _missing_address(GET_LINEAGE_TOOL, "entitled_product_class")
            )
        if lineage_tenant is None:
            raise ValueError(
                _missing_address(GET_LINEAGE_TOOL, "lineage_tenant")
            )
        lineage_seam = lineage_provider
        lineage_class = entitled_product_class
        lineage_address_tenant = lineage_tenant

        @door.tool(
            name=GET_LINEAGE_TOOL,
            # No tenant on the wire — this tool takes no arguments at all — so
            # the decision is against the tenant the deployment declared the
            # tool's address under. The same value the entitlement is already
            # decided against, read once (`SEC-018`).
            subject=door.declared(lineage_address_tenant),
            mutating=False,
            description=get_lineage_description,
        )
        def get_lineage() -> str:
            """Serve the product's lineage via the injected seam, once entitled.

            Same sequence as :data:`GET_CONTEXT_TOOL`, decided against the
            **deployment-declared** address because this tool carries no wire
            arguments at all — absence of a client parameter reduces
            steerability, never disclosure, and before this it served a
            tenant's lineage to every verified caller.

            The licensing argument, so no reader thinks a vocabulary was
            invented: the lineage this tool serves is a *field of the vessel*
            the ``context_product`` resource serves whole, so the same policy
            that decides who may receive the class decides who may receive a
            field of it.

            **A denial here is a recorded decision, and this handler only
            encodes it** (``D-IMPL-256`` (1)/(3); criterion 36). The governed
            step minted it at the entitlement source's own declared instant,
            under a resource-request identity naming the address this
            deployment declared — the only address a tool with no wire
            arguments has — and disclosed it before returning.
            """
            authorized = govern_entitlement(
                grant=verified_grant(),
                tenant=lineage_address_tenant,
                product_class=lineage_class,
                product_version=None,
                requested_role=None,
                # This tool carries no wire arguments at all, so the request
                # identity's parameters are empty as a statement of fact.
                parameters={},
                asked_at=None,
                surface=SURFACE_MCP_TOOL,
                address=_tool_address(
                    tool=GET_LINEAGE_TOOL,
                    tenant=lineage_address_tenant,
                    product_class=lineage_class,
                ),
                entitlement_source=entitlement_source,
                perspective_resolver=perspective_resolver,
                refusal_recorder=recorder,
            )
            if isinstance(authorized, RefusalEnvelope):
                return canonical_bytes(authorized).decode("utf-8")
            # Bound, and then deliberately dropped in the open rather than
            # discarded silently: `LineageProviderProtocol` was not widened,
            # and its docstring says why. The decision is what mattered here,
            # not the conditioning.
            del authorized
            return lineage_seam()

    if GET_REPLAY_RECORD_TOOL in allowed:
        if replay_record_reader is None or get_replay_record_description is None:
            raise ValueError(_missing(GET_REPLAY_RECORD_TOOL))
        # STRICTLY AFTER the D-03 check and with its own wording, for the
        # reason `_missing_address` gives.
        if replay_record_tenant is None:
            raise ValueError(
                _missing_address(
                    GET_REPLAY_RECORD_TOOL, "replay_record_tenant"
                )
            )
        replay_seam = replay_record_reader
        replay_tenant = replay_record_tenant

        @door.tool(
            name=GET_REPLAY_RECORD_TOOL,
            subject=door.declared(replay_tenant),
            mutating=False,
            description=get_replay_record_description,
        )
        def get_replay_record() -> str:
            """Serve the most-recent replay record via the injected seam.

            The five-dimension record is the widest disclosure on this server,
            which is why it is decided rather than merely authenticated
            (``SEC-018``). This tool carries no arguments, so the decision is
            against the tenant the deployment declared it under
            (``replay_record_tenant``) — absence of a client parameter reduces
            steerability and never disclosure, so a caller holding no grant for
            that tenant is refused.

            What ``D-IMPL-129`` declined remains declined: no replay-scoped
            entitlement vocabulary is invented here. Within the declared
            tenant, any verified caller still receives the record.
            """
            verified_grant()
            return replay_seam()

    return server
