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

Only the ``analytics_insights`` bundle ships in this plan (the D-02 slice
archetype); the remaining five land with the composition wave. The registry
maps definition-artifact ``archetypes``-axis identifiers onto bundle
instances, so the factory and the schema share one vocabulary
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


#: The shipped AnalyticsInsights bundle instance — mechanism, not an agent
#: (CLAUDE.md §6.1: archetypes are SDK code; agents are declared artifacts).
analytics_insights = _AnalyticsInsightsComponent()

#: Definition-artifact archetype identifiers → shipped bundle instances.
#: Deliberately a subset of :data:`~ccf.agents.definitions.ARCHETYPE_IDS`
#: until the remaining five bundles land: a definition declaring an archetype
#: the schema knows but no bundle realizes yet is a typed factory
#: construction error, never a silent no-op.
ARCHETYPES: Mapping[str, ArchetypeComponent] = {
    "analytics_insights": analytics_insights,
}
