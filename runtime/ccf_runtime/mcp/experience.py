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

Server name, bind address, token values, tenant identifiers, agent names,
and skill vocabulary are all deployment values supplied by the caller. This
module holds none of them (CINV-01).

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
from ccf.skills.catalog import SkillCatalogEntry
from ccf.skills.toolsurface import render_tool_surface

__ccf_mode__ = "algorithmic"

__all__ = [
    "EXPERIENCE_PRODUCT_URI_SCHEME",
    "EXPERIENCE_PRODUCT_URI_TEMPLATE",
    "INVOKE_AGENT_TOOL",
    "LIST_AGENTS_TOOL",
    "AgentDirectoryProtocol",
    "AgentInvokerProtocol",
    "AgentToolCatalog",
    "AgentToolListing",
    "AgentToolSurface",
    "ExperienceProductNotServable",
    "ExperienceProductResolverProtocol",
    "ExposedAgent",
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


class ExperienceProductNotServable(LookupError):
    """The resolver has no gate-admitted product at that front-door address.

    Raised by a deployment's resolver, not by this module — the counterpart
    of :class:`ccf_runtime.mcp.egress.ProductNotServable` on this role's
    surface. A ``LookupError`` because it is an absence.
    """


@runtime_checkable
class ExperienceProductResolverProtocol(Protocol):
    """What a deployment plugs into the front door's product leg.

    The same keyword-only three-string signature as the egress resolver, so
    one deployment resolver can serve both roles structurally — while the two
    modules stay separate (§7.1). Protocol rather than a base class
    (CLAUDE.md §11).
    """

    def __call__(
        self, *, tenant: str, product_class: str, version: str
    ) -> ServableProduct:
        """Return the gate-admitted product at that address.

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


def build_experience_server(
    *,
    server_name: str,
    product_resolver: ExperienceProductResolverProtocol,
    agent_directory: AgentDirectoryProtocol,
    agent_invoker: AgentInvokerProtocol,
    token_verifier: TokenVerifier,
    auth_settings: AuthSettings,
) -> FastMCP:
    """Build the authenticated Experience-surface server over three seams.

    ``stateless_http=True`` is load-bearing rather than a tuning choice: it
    is what makes the client's session-per-call cheap (:mod:`ccf.mcp.client`,
    and the held-session bridge that deadlocks without it).
    ``json_response=True`` pairs with it.

    Both ``token_verifier`` and ``auth_settings`` are required, and required
    *together*, because ``FastMCP`` installs its authentication middleware
    only when both are present (D-26, the artifact-server precedent).

    Args:
        server_name: The name this server advertises. Deployment identity.
        product_resolver: The deployment's assemble-and-gate path.
        agent_directory: The deployment's per-tenant agent exposure.
        agent_invoker: The deployment's factory-path invocation seam.
        token_verifier: Verifies presented bearer tokens
            (:mod:`ccf_runtime.mcp.auth` ships the reference implementation).
        auth_settings: Issuer, resource-server identity, required scopes —
            deployment values in their entirety.

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision, and a
        library that picked an interface would be picking an exposure
        surface (T-06-14).
    """
    server = FastMCP(
        server_name,
        stateless_http=True,
        json_response=True,
        token_verifier=token_verifier,
        auth=auth_settings,
    )

    @server.resource(EXPERIENCE_PRODUCT_URI_TEMPLATE, mime_type=PRODUCT_MIME_TYPE)
    def context_product(tenant: str, product_class: str, version: str) -> str:
        """Serve one gate-admitted Context Product as canonical JSON.

        Canonical bytes, not ``model_dump_json``: the same serialization the
        content address is computed over, so a consumer that hashes what it
        received gets the address the producer would.
        """
        servable = product_resolver(
            tenant=tenant, product_class=product_class, version=version
        )
        return canonical_bytes(servable.product).decode("utf-8")

    @server.tool(name=LIST_AGENTS_TOOL)
    def list_agents(tenant: str) -> str:
        """List one tenant's exposed agents with their rendered tool surfaces."""
        catalog = AgentToolCatalog(
            tenant=tenant,
            agents=tuple(
                agent_tool_listing(agent)
                for agent in agent_directory(tenant=tenant)
            ),
        )
        return canonical_bytes(catalog).decode("utf-8")

    @server.tool(name=INVOKE_AGENT_TOOL)
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
        return agent_invoker(
            tenant=tenant,
            definition_key=definition_key,
            definition_version=definition_version,
            skill=skill,
            arguments=arguments,
        )

    return server
