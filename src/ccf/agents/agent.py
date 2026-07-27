"""The concrete final ``Agent`` (CLAUDE.md §6.1, §6.5 — SDK-defined).

**Final — archetype behavior composes via components, never subclassing**
(D-IMPL-11: a single concrete runtime class specialized entirely by artifact;
archetypes are Protocol-typed behavior bundles; no class hierarchy exists to
entangle). ``Agent`` is the factory's only output type: it carries the
identity block (definition content hash, versioned URI annotation, composed
archetype list — D-06), the validated definition, the composed
:class:`~ccf.agents.archetypes.ArchetypeComponent` bundles, the resolved
instruction artifacts, and the currently-bound skill mapping (empty until the
skilling wave populates it through governed grants).

**No reasoning loop.** There is no ``run``, ``loop``, ``step``, or ``plan``
here and never will be — the loop belongs to the harness (CLAUDE.md §6.5,
§7.3). ``Agent`` is the fabric-side representation a harness adapter binds
against, exposing exactly three fabric seams (DESIGN.md §3.1):

* :meth:`consume` — a typed Context Product in, held to the agent's context
  contract (axis 2) and to TTL validity: an expired product is
  contract-invalid, not stale, and is refused rather than degraded around
  (INV-CH6-05). No other fabric-read surface exists — no path from ``Agent``
  to L1–L5.
* :meth:`invoke_skill` — a currently-bound capability by name; an unbound
  name is a typed refusal (channel 2, CLAUDE.md §6.2).
* :meth:`emit_effect` — emission as a **returned typed value**. The agent
  never holds a graph write handle; whatever carries the effect onward does
  so through L2 (single-writer, CLAUDE.md §10).

Nothing here reads a clock — ``now`` is injected at :meth:`consume`, like
every other instant in the fabric.

**No construction token** (D-12, Dave's explicit ruling): ``Agent`` is a
normal public class whose constructor validates its inputs; the CINV-01c
factory-bypass lint is the no-bypass mechanism of record. The single
legitimate construction call site is :mod:`ccf.agents.factory`.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ccf.agents.archetypes import ArchetypeComponent
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    AgentDefinition,
    PromptArtifact,
)
from ccf.agents.errors import (
    AgentConstructionError,
    ConsumptionRefused,
    FalseGrantClaimError,
    SkillNotBound,
)
from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.products.contract import ContextProductContract
from ccf.replay.record import NO_GRANTS_SET_HASH, PerspectiveConditioning
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SkillCatalogEntry
from ccf.skills.grants import BoundSkillView

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ccf.skills.dispatch import (
        McpInvocation,
        SkillInvocation,
        ToolInvocation,
    )

__ccf_mode__ = "algorithmic"

__all__ = ["Agent", "AgentIdentity", "EmittedEffect"]


class AgentIdentity(CCFContract):
    """The D-06 identity block, captured at construction time.

    Derived-not-reconstructed: the factory computes these three values from
    the resolved definition at construction, and replay dimension 4 serializes
    them verbatim — a record that re-derived identity from live objects would
    describe recording-time state, not decision-time state (DESIGN.md §3.6).

    Attributes:
        definition_hash: Content hash of the definition — canonical identity
            (D-IMPL-26).
        definition_uri: The definition's versioned URI, carried as annotation
            per the D-IMPL-26 replay rule.
        archetype_composition: The declared archetype list, in D-IMPL-19
            declaration order.
    """

    definition_hash: str
    definition_uri: str
    archetype_composition: tuple[str, ...]


class EmittedEffect(CCFContract):
    """An agent's output, as a value the caller carries onward.

    The effect-capture seam (CLAUDE.md §7.3 seam 3) in fabric-side form:
    emission is a returned contract, never a write — nothing reaches L3
    except through L2 (single-writer, §10). The emitting agent's canonical
    identity travels with the payload so the effect stays attributable
    without consulting live state.

    Attributes:
        agent_definition_hash: Content hash of the emitting agent's
            definition (D-06).
        payload: What the agent produced. Canonical-serializability is the
            payload author's obligation, as everywhere else in the fabric.
    """

    agent_definition_hash: str
    payload: Mapping[str, Any]


def _validated_bound_skills(bound_skills: object) -> BoundSkillView | None:
    """Refuse anything but a ledger-produced view at the seam (WR-03).

    Typed ``object`` deliberately: the signature narrows to
    :class:`~ccf.skills.grants.BoundSkillView` statically, and this runtime
    check holds the same line against dynamically-injected mappings — the
    supported construction path admits no capability source other than the
    grant ledger (CLAUDE.md §6.2 channel 2).
    """
    if bound_skills is None:
        return None
    if not isinstance(bound_skills, BoundSkillView):
        raise AgentConstructionError(
            f"bound_skills is {type(bound_skills).__name__}, not the grant"
            " ledger's BoundSkillView; capabilities reach an agent only"
            " through governed grants — pass"
            " GrantLedger.bound_view(agent_definition_hash) or None"
            " (WR-03; CLAUDE.md §6.2)"
        )
    return bound_skills


class Agent:
    """One declared agent, running form (CLAUDE.md §6.1; D-IMPL-11).

    Final: do not subclass. Everything distinguishing one agent from another
    is serialized in its definition artifact; behavior composes through the
    attached archetype components. Construct through
    :class:`~ccf.agents.factory.AgentFactory` only (CLAUDE.md §6.4) — the
    constructor validates coherence but the factory is the supported path,
    enforced by the CINV-01c lint (D-12).

    Args:
        definition: The validated six-axis definition this agent realizes.
        identity: The construction-time identity block; must agree with
            ``definition`` (hash and composition), or construction is refused.
        components: The composed archetype bundles, in declaration order,
            one per declared archetype identifier.
        instruction_artifacts: Resolved prompt artifacts keyed by the
            binding's versioned URI (validated by the factory per D-13).
        bound_skills: The currently-bound skill view (channel 2), or ``None``
            for an agent granted nothing. Only the grant ledger's
            :class:`~ccf.skills.grants.BoundSkillView` is admissible (WR-03):
            capabilities reach an agent through governed grants exclusively,
            so an arbitrary mapping is refused at construction. Held by
            reference, deliberately: the factory passes the ledger's live
            view, so grants and revocations take effect at invoke time
            without the agent's identity ever changing (CLAUDE.md §6.2;
            D-07 — skill-set changes never touch agent identity).
        callable_registry: The deployment's boot-time
            :class:`~ccf.skills.callables.CallableRegistry`, which
            ``local_callable`` dispatch resolves against (D-19). ``None``
            means this deployment registered no callables, so every
            ``local_callable`` entry resolves to nothing — positively, and
            without importing anything. Held by reference, injected from the
            composition root, never an ambient lookup (D-23).

    Raises:
        AgentConstructionError: the inputs do not describe one coherent agent,
            or ``bound_skills`` is not a ledger-produced view.
    """

    def __init__(
        self,
        *,
        definition: AgentDefinition,
        identity: AgentIdentity,
        components: tuple[ArchetypeComponent, ...],
        instruction_artifacts: Mapping[str, PromptArtifact],
        bound_skills: BoundSkillView | None,
        callable_registry: CallableRegistry | None = None,
    ) -> None:
        expected_hash = content_hash(definition)
        if identity.definition_hash != expected_hash:
            raise AgentConstructionError(
                "identity.definition_hash does not equal the content hash of"
                f" the definition ({identity.definition_hash!r} !="
                f" {expected_hash!r}); agent identity is content identity"
                " (D-06, D-IMPL-26)"
            )
        expected_uri = artifact_uri(
            tenant_id=definition.tenant,
            artifact_class=AGENT_DEFINITION.class_id,
            name=definition.name,
            artifact_version=definition.artifact_version,
        )
        if identity.definition_uri != expected_uri:
            raise AgentConstructionError(
                "identity.definition_uri does not name the definition"
                f" ({identity.definition_uri!r} != {expected_uri!r}); the URI"
                " is derived from the definition's own naming triple and"
                " version, and replay dimension 4 serializes it verbatim —"
                " a drifted annotation would describe the decision as having"
                " been made under an artifact it was not (D-IMPL-26;"
                " DESIGN.md §3.6; IN-02)"
            )
        if identity.archetype_composition != definition.archetypes:
            raise AgentConstructionError(
                "identity.archetype_composition"
                f" {identity.archetype_composition!r} is not the definition's"
                f" declared archetype list {definition.archetypes!r}"
                " (D-IMPL-19 declaration order is identity)"
            )
        realized = tuple(component.archetype_id for component in components)
        if realized != definition.archetypes:
            raise AgentConstructionError(
                f"composed components realize {realized!r}, but the definition"
                f" declares {definition.archetypes!r}; every declared archetype"
                " must be realized by exactly its bundle, in order"
            )
        self._definition = definition
        self._identity = identity
        self._components = components
        self._instruction_artifacts = dict(instruction_artifacts)
        self._bound_skills = _validated_bound_skills(bound_skills)
        self._callable_registry = (
            callable_registry if callable_registry is not None else CallableRegistry()
        )

    @property
    def identity(self) -> AgentIdentity:
        """The construction-time identity block (D-06)."""
        return self._identity

    @property
    def definition(self) -> AgentDefinition:
        """The validated definition this agent realizes."""
        return self._definition

    @property
    def components(self) -> tuple[ArchetypeComponent, ...]:
        """The composed archetype bundles, in declaration order."""
        return self._components

    def _skills(self) -> Mapping[str, SkillCatalogEntry]:
        """The currently-bound skill mapping; empty when nothing is granted."""
        return self._bound_skills if self._bound_skills is not None else {}

    @property
    def bound_skill_names(self) -> tuple[str, ...]:
        """The currently-bound skill names, sorted (channel 2 snapshot)."""
        return tuple(sorted(self._skills()))

    def instruction_artifact(self, prompt_uri: str) -> PromptArtifact:
        """Return the resolved prompt artifact bound under ``prompt_uri``.

        Axis 6 introspection only — nothing here renders (D-13; rendering is
        adapter work in a later phase).

        Raises:
            KeyError: no instruction binding references ``prompt_uri``.
        """
        return self._instruction_artifacts[prompt_uri]

    def consume(
        self, product: ContextProductContract, *, now: datetime
    ) -> ContextProductContract:
        """Admit a Context Product under the agent's context contract (axis 2).

        The one fabric-read surface the class exposes (INV-CH6-05: agents
        consume context, never data). Admission is exact: the product's
        class and schema version must be declared in the contract, its tenant
        must be the agent's, and it must be unexpired at ``now``.

        Raises:
            ConsumptionRefused: the product is outside the contract, from
                another tenant, or TTL-expired (contract-invalid, not stale).
        """
        declared = {
            (consumed.product_class, consumed.schema_version)
            for consumed in self._definition.context_contract.consumes
        }
        if (product.schema_name, product.schema_version) not in declared:
            raise ConsumptionRefused(
                f"product {product.schema_name!r}@{product.schema_version!r}"
                " is not in this agent's context contract"
                f" (declared: {sorted(declared)!r}; CLAUDE.md §6.2 axis 2)"
            )
        if product.tenant_id != self._definition.tenant:
            raise ConsumptionRefused(
                f"product tenant {product.tenant_id!r} is not the agent's"
                f" tenant {self._definition.tenant!r}"
            )
        if product.expires_at <= now:
            raise ConsumptionRefused(
                f"product expired at {product.expires_at.isoformat()} and now"
                f" is {now.isoformat()}: a TTL-expired product is"
                " contract-invalid, not stale (INV-CH6-05)"
            )
        return product

    def invoke_skill(
        self, name: str, *, arguments: Mapping[str, str] | None = None
    ) -> SkillCatalogEntry | SkillInvocation | ToolInvocation | McpInvocation:
        """Invoke (or introspect) the currently-bound skill under ``name``.

        The channel-2 seam (CLAUDE.md §7.3 seam 2): skills the agent has not
        been granted do not exist from this surface. With ``arguments``, the
        bound catalog entry dispatches through
        :func:`ccf.skills.dispatch.dispatch_skill`; without, the bound entry
        is returned for introspection. Binding is resolved at invoke time
        from the ledger-backed :class:`~ccf.skills.grants.BoundSkillView`
        the factory injected (WR-03 — the view's values are catalog entries
        by construction), so grant and revocation take effect without
        touching agent identity (D-07).

        Raises:
            SkillNotBound: no grant currently binds ``name`` to this agent.
            ccf.agents.errors.NotYetBound: the bound entry is ``a2a`` and
                this build lacks the transport (D-08).
            ccf.skills.dispatch.McpSkillUnregistered: the bound entry is
                ``mcp`` and no ``McpSkillRegistry`` reaches this dispatch.
                The ``mcp`` transport is bound at
                :func:`ccf.skills.dispatch.dispatch_skill`; threading a
                registry from the factory through this method is a later
                plan's scope, so an ``mcp`` skill invoked *via an agent*
                still refuses today — with a wiring error naming the missing
                registry, rather than the old "no transport exists" claim,
                which is no longer true.
            ccf.skills.callables.CallableNotRegistered: the bound entry is a
                ``local_callable`` whose ``callable_ref`` names no key this
                deployment's composition root registered (D-19).
        """
        try:
            bound = self._skills()[name]
        except KeyError:
            raise SkillNotBound(
                f"no skill named {name!r} is currently bound to agent"
                f" {self._definition.name!r}; capabilities arrive only through"
                " governed grants (CLAUDE.md §6.2 channel 2)"
            ) from None
        if arguments is None:
            return bound
        # Imported at call time, not at module import: ``ccf.skills.dispatch``
        # raises ``ccf.agents.errors.NotYetBound``, so a module-level import
        # here would make ``ccf.skills`` and ``ccf.agents`` mutually
        # import-ordered — and an import graph whose success depends on which
        # module a caller reached first is exactly the non-determinism
        # D-IMPL-37 rejects for registries.
        from ccf.skills.dispatch import dispatch_skill

        return dispatch_skill(
            bound, arguments=arguments, callable_registry=self._callable_registry
        )

    def emit_effect(self, payload: Mapping[str, Any]) -> EmittedEffect:
        """Emit ``payload`` as a returned typed value (no write handle).

        Single-writer holds across this seam by construction: the return
        value is the entire effect; carrying it into the graph is L2's job,
        never the agent's (CLAUDE.md §10, §7.3 seam 3).
        """
        return EmittedEffect(
            agent_definition_hash=self._identity.definition_hash,
            payload=payload,
        )

    def perspective_conditioning(
        self, *, principal_id: str, grant_set_hash: str
    ) -> PerspectiveConditioning:
        """Serialize this agent's dimension-4 conditioning (D-06).

        A mechanical serialization of construction-time state — hash, URI
        annotation, composition — plus the in-force grant-set identity.
        ``grant_set_hash`` is the D-07 value the caller *captured* from the
        grant ledger at decision time (a serialized value, never re-derived
        here from live objects — DESIGN.md §3.6). **Required, with no
        default** (WR-01): a defaulted zero-grants claim on a skilled agent
        would record a false positive assertion into replay dimension 4, so
        the caller states the claim explicitly — and the positive
        :data:`~ccf.replay.record.NO_GRANTS_SET_HASH` claim is refused
        outright when this agent's bound skill-set is non-empty, because the
        agent itself knows zero grants cannot be true. The delegation chain
        is the single-element originating-principal chain in I.2 (extended,
        not re-shaped, by I.4).

        Raises:
            FalseGrantClaimError: ``grant_set_hash`` is the zero-grants claim
                while this agent's bound skill-set is non-empty (WR-01).
        """
        if grant_set_hash == NO_GRANTS_SET_HASH and len(self._skills()) > 0:
            raise FalseGrantClaimError(
                f"agent {self._definition.name!r} has"
                f" {len(self._skills())} currently-bound skill(s), so the"
                " zero-grants claim cannot be true; capture the in-force"
                " grant-set hash from"
                " GrantLedger.grant_set_hash(agent_definition_hash) at"
                " decision time (WR-01; D-07; CLAUDE.md §6.2)"
            )
        return PerspectiveConditioning(
            principal_id=principal_id,
            role=self._definition.perspective.role,
            agent_definition_hash=self._identity.definition_hash,
            agent_definition_uri=self._identity.definition_uri,
            archetype_composition=self._identity.archetype_composition,
            grant_set_hash=grant_set_hash,
            delegation_chain=(principal_id,),
        )
