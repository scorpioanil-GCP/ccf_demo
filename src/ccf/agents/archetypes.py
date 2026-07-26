"""Archetype component bundles (CLAUDE.md §6.1/§6.3 — SDK-defined).

**An archetype is a functional template the SDK ships** — a named bundle of
mechanism-level patterns with no identity, no prompts, no skills, no policy
bindings, and no domain values (CLAUDE.md §6.1). This module is where those
templates live: the :class:`ArchetypeComponent` Protocol every bundle
satisfies structurally (DESIGN.md §3.1 — archetypes conform structurally,
never nominally), and the shipped bundle instances the Agent Factory attaches
to the single concrete :class:`~ccf.agents.agent.Agent` in declaration order
(D-IMPL-11: composition over hierarchy; there is nothing to subclass).

Three declarations make up a bundle, and their types are deliberate:

* ``fabric_interaction_pattern()`` names the execution-and-fabric shape the
  archetype contributes — a mechanism identifier, not behavior. No bundle
  implements a reasoning loop; the loop belongs to the harness (§7.3, §6.5).
* ``replay_obligations()`` and ``configuration_defaults()`` return
  :class:`~ccf.contracts.base.CCFContract` values, so "identical" and
  "contradictory" are decidable via canonical bytes — the exact substrate the
  D-IMPL-19 composition rules (dedupe / declaration-order-with-warning /
  construction error) compare on when multi-archetype composition lands.

All six archetypes ship as bundles (CLAUDE.md §6.3; DESIGN.md §3.2): each
carries the *patterns* of its functional category as typed, decidable
values — never a prompt, a threshold, a half-life, or a domain vocabulary
word. Any tunable an archetype's pattern implies (an activation threshold,
a staleness tolerance) is a Control Plane value (D-IMPL-38); the bundle
declares only the mechanism identifier that says the value must exist and
must land in replay. The registry maps definition-artifact
``archetypes``-axis identifiers onto bundle instances, so the factory and
the schema share one vocabulary
(:data:`~ccf.agents.definitions.ARCHETYPE_IDS`).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "ARCHETYPES",
    "ArchetypeComponent",
    "ConfigurationDefault",
    "ReplayObligation",
    "analytics_insights",
    "content_generation",
    "context_assembly",
    "document_intelligence",
    "monitoring_surveillance",
    "workflow_task",
]


class ReplayObligation(CCFContract):
    """One replay obligation an archetype contributes (DESIGN.md §3.2).

    A contract value rather than prose-in-code so that two bundles
    contributing the same obligation are *provably* contributing the same
    obligation: identity is canonical bytes, which is what the D-IMPL-19
    dedupe rule deduplicates on.

    Attributes:
        name: Stable identifier of the obligation.
        obligation: What the archetype requires the replay record to carry.
    """

    name: str
    obligation: str


class ConfigurationDefault(CCFContract):
    """One configuration default an archetype contributes (D-IMPL-19).

    Values are strings because defaults participate in canonical comparison
    (the declaration-order-wins rule needs to *detect* a conflict before it
    can resolve one), and a float here would make that comparison
    platform-dependent. A numeric calibration is a Control Plane value and
    never appears in a bundle (CLAUDE.md §11; D-IMPL-38).

    Attributes:
        name: The configuration key the default applies to.
        value: The archetype's contributed default, as declared text.
    """

    name: str
    value: str


@runtime_checkable
class ArchetypeComponent(Protocol):
    """The typed behavior bundle every archetype satisfies (DESIGN.md §3.1).

    SDK-defined (CLAUDE.md §6.1/§6.3). A Protocol, not a base class: archetype
    conformance is structural, and users combine archetypes by declaration in
    the definition artifact — never by writing code against a hierarchy
    (D-IMPL-11/D-IMPL-19).
    """

    @property
    def archetype_id(self) -> str:
        """The definition-artifact identifier this bundle answers to."""
        ...

    def fabric_interaction_pattern(self) -> str:
        """Name the fabric-interaction shape this archetype contributes."""
        ...

    def replay_obligations(self) -> tuple[ReplayObligation, ...]:
        """The obligations this archetype places on the replay record."""
        ...

    def configuration_defaults(self) -> tuple[ConfigurationDefault, ...]:
        """The configuration defaults this archetype contributes, in order."""
        ...


class _AnalyticsInsightsComponent:
    """The AnalyticsInsights bundle (CLAUDE.md §6.3; DESIGN.md §3.2).

    Computation over Context Products: temporal analysis against the T
    dimension, threshold detection, cross-entity comparison, signal
    aggregation. The bundle carries the *patterns* of that category — its
    thresholds are Control Plane parameters (D-IMPL-38) and its inputs are
    contract-validated products only; neither appears here as a value.
    """

    @property
    def archetype_id(self) -> str:
        return "analytics_insights"

    def fabric_interaction_pattern(self) -> str:
        return "context-product-computation"

    def replay_obligations(self) -> tuple[ReplayObligation, ...]:
        return (
            ReplayObligation(
                name="consumed-product-references",
                obligation=(
                    "product versions and as-of times consumed land in"
                    " dimension 1 references"
                ),
            ),
        )

    def configuration_defaults(self) -> tuple[ConfigurationDefault, ...]:
        # Deliberately empty: an analytics calibration the SDK chose would be
        # a silent default (D-IMPL-38). Defaults exist as mechanism for the
        # D-IMPL-19 declaration-order rule, not as values this bundle supplies.
        return ()


class _WorkflowTaskComponent:
    """The Workflow/Task bundle (CLAUDE.md §6.3; DESIGN.md §3.2 — SDK
    extension).

    Procedural, multi-step decisioning against a task graph declared through
    the Task Factory — never code. The bundle carries the state-machine
    execution shape, deterministic step ordering, and structured idempotency
    as obligations; the task graph itself is a Control Plane artifact
    (No-Hardcoding Rule §6.4), and no step, route, or example workflow
    appears here as a value.
    """

    @property
    def archetype_id(self) -> str:
        return "workflow"

    def fabric_interaction_pattern(self) -> str:
        return "task-graph-state-machine"

    def replay_obligations(self) -> tuple[ReplayObligation, ...]:
        return (
            ReplayObligation(
                name="step-sequence-trace",
                obligation=(
                    "the executed step sequence lands in dimension 5; the"
                    " calling chain in dimension 4"
                ),
            ),
            ReplayObligation(
                name="structured-idempotency",
                obligation=(
                    "re-invocation with identical inputs and Control Plane"
                    " state is a no-op or an identical result, and the"
                    " record shows which"
                ),
            ),
        )

    def configuration_defaults(self) -> tuple[ConfigurationDefault, ...]:
        # No defaults: routing tables and retry calibrations are Control
        # Plane artifacts (D-IMPL-38), never bundle values.
        return ()


class _DocumentIntelligenceComponent:
    """The DocumentIntelligence bundle (CLAUDE.md §6.3; DESIGN.md §3.2).

    Ingest, metadata extraction, analysis, and generation over the Pattern 5
    unstructured pipeline, with passage-level lineage (whitepaper §7.10.3)
    baked into every output as an obligation — the anchors themselves are
    fabric-produced, never bundle values.
    """

    @property
    def archetype_id(self) -> str:
        return "document_intelligence"

    def fabric_interaction_pattern(self) -> str:
        return "unstructured-pipeline-derivation"

    def replay_obligations(self) -> tuple[ReplayObligation, ...]:
        return (
            ReplayObligation(
                name="passage-level-lineage",
                obligation=(
                    "passage anchors land in the L dimension of every"
                    " emitted product"
                ),
            ),
            ReplayObligation(
                name="document-derivation-trace",
                obligation=(
                    "the document-derivation path lands in dimension 5"
                ),
            ),
        )

    def configuration_defaults(self) -> tuple[ConfigurationDefault, ...]:
        return ()


class _MonitoringSurveillanceComponent:
    """The MonitoringSurveillance bundle (CLAUDE.md §6.3; DESIGN.md §3.2).

    Long-running, trigger-driven watch: event subscription against L1
    streams, threshold-based activation, λ_c-driven continuous
    re-evaluation. Activation conditions and thresholds are versioned
    Control Plane values (D-IMPL-38) — the bundle obliges their capture, it
    never supplies them.
    """

    @property
    def archetype_id(self) -> str:
        return "monitoring_surveillance"

    def fabric_interaction_pattern(self) -> str:
        return "trigger-driven-reevaluation"

    def replay_obligations(self) -> tuple[ReplayObligation, ...]:
        return (
            ReplayObligation(
                name="trigger-activation-record",
                obligation=(
                    "trigger condition, threshold version, and activation"
                    " timestamp land per invocation; each activation is an"
                    " independently replayable decision"
                ),
            ),
            ReplayObligation(
                name="freshness-reevaluation",
                obligation=(
                    "half-life-driven re-evaluation captures the decay"
                    " profile version in force at each activation"
                ),
            ),
        )

    def configuration_defaults(self) -> tuple[ConfigurationDefault, ...]:
        return ()


class _ContentGenerationComponent:
    """The ContentGeneration bundle (CLAUDE.md §6.3; DESIGN.md §3.2).

    Structured LLM output under template binding: templates are versioned
    prompt artifacts (axis 6), never inline (D-13/No-Hardcoding §6.4), and
    every claim is passage-anchored (whitepaper §7.10.3). Draft-and-review
    HITL integration is a seam declared here, realized by the HITL pillar.
    """

    @property
    def archetype_id(self) -> str:
        return "content_generation"

    def fabric_interaction_pattern(self) -> str:
        return "template-bound-generation"

    def replay_obligations(self) -> tuple[ReplayObligation, ...]:
        return (
            ReplayObligation(
                name="passage-anchored-claims",
                obligation=(
                    "every generated claim is passage-anchored; citation"
                    " lineage lands with the output"
                ),
            ),
            ReplayObligation(
                name="prompt-artifact-versions",
                obligation=(
                    "prompt-artifact versions in force land in dimensions"
                    " 3 and 5; review actions extend dimension 2"
                ),
            ),
        )

    def configuration_defaults(self) -> tuple[ConfigurationDefault, ...]:
        return ()


class _ContextAssemblyComponent:
    """The ContextAssembly bundle (CLAUDE.md §6.3; DESIGN.md §3.2/§3.4).

    Assembler producing typed Context Products for other agents — the
    recursive-enrichment and swarm-realized-operator case (whitepaper
    §6.6/§7.4.9, INV-CH7-32). The emission *pattern* is declared here:
    products reach L3 only through L2 mechanism (single-writer, CLAUDE.md
    §10); the transports (in-process, MCP egress, A2A) bind in I.3.
    """

    @property
    def archetype_id(self) -> str:
        return "context_assembly"

    def fabric_interaction_pattern(self) -> str:
        return "typed-product-emission"

    def replay_obligations(self) -> tuple[ReplayObligation, ...]:
        return (
            ReplayObligation(
                name="emitted-product-replay-envelope",
                obligation=(
                    "the emitted product is itself a replayable artifact"
                    " bound to the five-dimension envelope, distinct from"
                    " any consumer's inference trace; emission routes"
                    " through the single-writer assembly mechanism"
                ),
            ),
            ReplayObligation(
                name="policy-before-similarity",
                obligation=(
                    "policy composes before similarity at every assembly"
                    " step the archetype takes"
                ),
            ),
        )

    def configuration_defaults(self) -> tuple[ConfigurationDefault, ...]:
        return ()


#: The shipped bundle instances — mechanism, not agents (CLAUDE.md §6.1:
#: archetypes are SDK code; agents are declared artifacts).
analytics_insights = _AnalyticsInsightsComponent()
workflow_task = _WorkflowTaskComponent()
document_intelligence = _DocumentIntelligenceComponent()
monitoring_surveillance = _MonitoringSurveillanceComponent()
content_generation = _ContentGenerationComponent()
context_assembly = _ContextAssemblyComponent()

#: Definition-artifact archetype identifiers → shipped bundle instances.
#: Exactly the six identifiers the definition schema admits
#: (:data:`~ccf.agents.definitions.ARCHETYPE_IDS`): the factory and the
#: schema share one vocabulary, and a definition can never declare an
#: archetype no bundle realizes.
ARCHETYPES: Mapping[str, ArchetypeComponent] = {
    "workflow": workflow_task,
    "document_intelligence": document_intelligence,
    "analytics_insights": analytics_insights,
    "monitoring_surveillance": monitoring_surveillance,
    "content_generation": content_generation,
    "context_assembly": context_assembly,
}
