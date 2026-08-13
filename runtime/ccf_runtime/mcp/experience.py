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
from ccf.products.gates import ServableProduct
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SkillCatalogEntry
from ccf.skills.toolsurface import render_tool_surface
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementSourceProtocol,
    entitled_perspective,
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
            ExperienceProductNotServable: no such product.
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
    """

    def __call__(self, *, tenant: str, entity: str) -> str:
        """Return the entity-scoped Context Product as canonical JSON.

        Raises:
            ExperienceProductNotServable: nothing servable at that address.
        """
        ...


@runtime_checkable
class LineageProviderProtocol(Protocol):
    """What a deployment plugs into :data:`GET_LINEAGE_TOOL`.

    SDK-defined (CLAUDE.md §8.3, §7.1). The deployment decides which
    product's lineage the front door serves; this module only carries the
    string it is handed (T-07-20).
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

    **Allowlisted implies supplied (D-03/D-04; Dave, 2026-08-02).** The
    three consumption seams and their prose are Optional parameters with
    ``None`` defaults — callers that pass everything are unaffected — but a
    tool the allowlist admits with no provider or no description behind it
    raises at build time, named. Requiredness is conditional on exposure,
    which is the only place it can be stated once the surface is
    configurable. The agent Tools and the product resource take SDK default
    descriptions instead (D-12/D-13/D-14): their shape is SDK mechanism, so
    describing it authors nobody's domain prose (CINV-01; CLAUDE.md §6.4).

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
        tool_allowlist: Which Tools to register; ``None`` registers all of
            :data:`EXPERIENCE_TOOLS`.

    Raises:
        ValueError: The allowlist names a tool outside
            :data:`EXPERIENCE_TOOLS` (D-01), or a tool it admits has no
            provider or no description supplied (D-03).

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision, and a
        library that picked an interface would be picking an exposure
        surface (T-06-14).
    """
    if tool_allowlist is not None:
        unknown = frozenset(tool_allowlist) - EXPERIENCE_TOOLS
        if unknown:
            raise ValueError(
                f"tool_allowlist names unknown tools: {sorted(unknown)};"
                f" this server registers {sorted(EXPERIENCE_TOOLS)}"
            )
    allowed = EXPERIENCE_TOOLS if tool_allowlist is None else frozenset(tool_allowlist)

    server = FastMCP(
        server_name,
        stateless_http=True,
        json_response=True,
        token_verifier=token_verifier,
        auth=auth_settings,
    )

    @server.resource(
        EXPERIENCE_PRODUCT_URI_TEMPLATE,
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
        """
        perspective = entitled_perspective(
            grant=verified_grant(),
            tenant=tenant,
            product_class=product_class,
            requested_role=None,
            entitlement_source=entitlement_source,
            perspective_resolver=perspective_resolver,
        )
        servable = product_resolver(
            tenant=tenant,
            product_class=product_class,
            version=version,
            perspective=perspective,
            request=None,
        )
        return canonical_bytes(servable.product).decode("utf-8")

    if LIST_AGENTS_TOOL in allowed:
        # D-03 applies to the agent seams on the same terms as the three
        # consumption seams: requiredness is conditional on exposure. A
        # deployment that allowlists no agent tools hands in no agent
        # callables — it does not supply dead ones to satisfy a signature.
        if agent_directory is None:
            raise ValueError(_missing(LIST_AGENTS_TOOL))
        directory_seam = agent_directory

        @server.tool(
            name=LIST_AGENTS_TOOL,
            description=(
                list_agents_description
                if list_agents_description is not None
                else DEFAULT_LIST_AGENTS_DESCRIPTION
            ),
        )
        def list_agents(tenant: str) -> str:
            """List one tenant's exposed agents with their rendered tool surfaces."""
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

        @server.tool(
            name=INVOKE_AGENT_TOOL,
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
            """
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
        context_seam = context_provider

        @server.tool(
            name=GET_CONTEXT_TOOL, description=get_context_description
        )
        def get_context(tenant: str, entity: str) -> str:
            """Serve one tenant's entity-scoped product via the injected seam."""
            return context_seam(tenant=tenant, entity=entity)

    if GET_LINEAGE_TOOL in allowed:
        if lineage_provider is None or get_lineage_description is None:
            raise ValueError(_missing(GET_LINEAGE_TOOL))
        lineage_seam = lineage_provider

        @server.tool(
            name=GET_LINEAGE_TOOL, description=get_lineage_description
        )
        def get_lineage() -> str:
            """Serve the product's lineage via the injected seam."""
            return lineage_seam()

    if GET_REPLAY_RECORD_TOOL in allowed:
        if replay_record_reader is None or get_replay_record_description is None:
            raise ValueError(_missing(GET_REPLAY_RECORD_TOOL))
        replay_seam = replay_record_reader

        @server.tool(
            name=GET_REPLAY_RECORD_TOOL,
            description=get_replay_record_description,
        )
        def get_replay_record() -> str:
            """Serve the most-recent replay record via the injected seam."""
            return replay_seam()

    return server
