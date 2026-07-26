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
  (the ``archetypes`` axis vocabulary) onto bundle instances — all six ship
  as of the widening wave (05-03, AGNT-01; CLAUDE.md §6.3).
* No bundle carries prompt text, thresholds, half-life values, or domain
  vocabulary: archetypes are mechanism, and every tunable is a Control Plane
  value (CLAUDE.md §6.1, §11; D-IMPL-38).
"""

from __future__ import annotations

import re

import pytest

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


# --- All six archetypes (05-03 widening wave; AGNT-01; CLAUDE.md §6.3) ------


def test_the_registry_maps_exactly_the_six_shipped_identifiers() -> None:
    assert set(ARCHETYPES) == ARCHETYPE_IDS
    assert len(ARCHETYPES) == 6


@pytest.mark.parametrize("identifier", sorted(ARCHETYPE_IDS))
def test_every_bundle_conforms_and_answers_to_its_identifier(
    identifier: str,
) -> None:
    bundle = ARCHETYPES[identifier]
    assert isinstance(bundle, ArchetypeComponent)
    assert bundle.archetype_id == identifier


@pytest.mark.parametrize("identifier", sorted(ARCHETYPE_IDS))
def test_every_bundle_declares_typed_obligations_and_defaults(
    identifier: str,
) -> None:
    bundle = ARCHETYPES[identifier]
    pattern = bundle.fabric_interaction_pattern()
    assert isinstance(pattern, str) and pattern
    obligations = bundle.replay_obligations()
    assert isinstance(obligations, tuple)
    assert obligations, "every archetype must declare its replay obligations"
    for obligation in obligations:
        assert isinstance(obligation, ReplayObligation)
        assert isinstance(obligation, CCFContract)
        # Decidable identity — the D-IMPL-19 dedupe substrate.
        twin = ReplayObligation(
            name=obligation.name, obligation=obligation.obligation
        )
        assert canonical_bytes(twin) == canonical_bytes(obligation)
    defaults = bundle.configuration_defaults()
    assert isinstance(defaults, tuple)
    for default in defaults:
        assert isinstance(default, ConfigurationDefault)
        assert isinstance(default, CCFContract)


def _obligation_names(identifier: str) -> set[str]:
    return {o.name for o in ARCHETYPES[identifier].replay_obligations()}


def test_context_assembly_declares_the_emission_obligation() -> None:
    """The assembler pattern: typed products routed through L2 mechanism
    (DESIGN.md §3.2 — pattern declared; transport lands in I.3)."""
    names = _obligation_names("context_assembly")
    assert "emitted-product-replay-envelope" in names


def test_monitoring_surveillance_declares_trigger_and_freshness() -> None:
    names = _obligation_names("monitoring_surveillance")
    assert "trigger-activation-record" in names
    assert "freshness-reevaluation" in names


def test_content_generation_declares_citation_lineage() -> None:
    names = _obligation_names("content_generation")
    assert "passage-anchored-claims" in names


_DOMAIN_VOCABULARY = re.compile(
    r"credit|covenant|kyc|banking|onboarding|fulfillment|memo|pitch",
    re.IGNORECASE,
)
_NUMERIC_LITERAL = re.compile(r"^-?\d+(\.\d+)?$")


@pytest.mark.parametrize("identifier", sorted(ARCHETYPE_IDS))
def test_bundles_carry_mechanism_only_no_values(identifier: str) -> None:
    """No prompt text, thresholds, half-life values, or domain vocabulary in
    any bundle — spot assertions over serialized bundle content
    (CLAUDE.md §6.1, §11; D-IMPL-38)."""
    bundle = ARCHETYPES[identifier]
    serialized = b" ".join(
        [
            bundle.fabric_interaction_pattern().encode(),
            *(canonical_bytes(o) for o in bundle.replay_obligations()),
            *(canonical_bytes(d) for d in bundle.configuration_defaults()),
        ]
    ).decode()
    assert not _DOMAIN_VOCABULARY.search(serialized), serialized
    for default in bundle.configuration_defaults():
        assert not _NUMERIC_LITERAL.match(default.value), (
            "a numeric default is a calibration; calibrations live in the"
            f" Control Plane, never in a bundle (D-IMPL-38): {default!r}"
        )
