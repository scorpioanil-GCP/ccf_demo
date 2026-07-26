"""The ``ArchetypeComponent`` Protocol and the analytics_insights bundle.

Written before the implementation per the TDD discipline (CLAUDE.md §6.1/§6.3;
D-IMPL-11). The claims pinned here:

* ``ArchetypeComponent`` is a ``@runtime_checkable`` Protocol exposing
  ``fabric_interaction_pattern()``, ``replay_obligations()``, and
  ``configuration_defaults()``; conformance is structural, never nominal.
* Obligation and default declarations are ``CCFContract`` values, so
  "identical" and "contradictory" are decidable via canonical bytes — the
  substrate the D-IMPL-19 composition rules (05-03) will compare on.
* The module-level registry maps definition-artifact archetype identifiers
  (the ``archetypes`` axis vocabulary) onto bundle instances; only
  ``analytics_insights`` ships in this plan.
"""

from __future__ import annotations

from ccf.agents.archetypes import (
    ARCHETYPES,
    ArchetypeComponent,
    ConfigurationDefault,
    ReplayObligation,
    analytics_insights,
)
from ccf.agents.definitions import ARCHETYPE_IDS
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes


def test_the_protocol_is_runtime_checkable_and_the_bundle_conforms() -> None:
    assert isinstance(analytics_insights, ArchetypeComponent)


def test_conformance_is_structural_not_nominal() -> None:
    """Any object with the three methods conforms — Protocol, not base class."""

    class Structural:
        @property
        def archetype_id(self) -> str:
            return "structural"

        def fabric_interaction_pattern(self) -> str:
            return "structural-pattern"

        def replay_obligations(self) -> tuple[ReplayObligation, ...]:
            return ()

        def configuration_defaults(self) -> tuple[ConfigurationDefault, ...]:
            return ()

    assert isinstance(Structural(), ArchetypeComponent)
    assert not isinstance(object(), ArchetypeComponent)


def test_replay_obligations_are_contract_values_with_decidable_identity() -> None:
    obligations = analytics_insights.replay_obligations()
    assert obligations, "the bundle must declare its replay obligations"
    for obligation in obligations:
        assert isinstance(obligation, ReplayObligation)
        assert isinstance(obligation, CCFContract)
    first = obligations[0]
    twin = ReplayObligation(name=first.name, obligation=first.obligation)
    assert canonical_bytes(twin) == canonical_bytes(first)


def test_configuration_defaults_are_contract_values() -> None:
    defaults = analytics_insights.configuration_defaults()
    assert isinstance(defaults, tuple)
    for default in defaults:
        assert isinstance(default, ConfigurationDefault)
    # The contract type itself canonicalizes — decidable identity for the
    # D-IMPL-19 declaration-order/conflict rules landing in 05-03.
    probe = ConfigurationDefault(name="probe", value="probe-value")
    assert isinstance(probe, CCFContract)
    assert canonical_bytes(probe) == canonical_bytes(
        ConfigurationDefault(name="probe", value="probe-value")
    )


def test_the_fabric_interaction_pattern_is_a_named_mechanism() -> None:
    pattern = analytics_insights.fabric_interaction_pattern()
    assert isinstance(pattern, str)
    assert pattern


def test_the_registry_keys_are_definition_artifact_identifiers() -> None:
    assert set(ARCHETYPES) <= ARCHETYPE_IDS
    assert ARCHETYPES["analytics_insights"] is analytics_insights
    assert analytics_insights.archetype_id == "analytics_insights"
