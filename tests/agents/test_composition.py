"""The D-IMPL-19 ordered-composition rules, unit-tested directly.

Written before the implementation per the TDD discipline (FEASIBILITY:
"explicit enough to unit-test directly"). The three D-IMPL-19 rules pinned
here, each on its own path:

* **Dedupe** — identical obligations contributed by two archetypes appear
  once in the composed result; identity is canonical bytes, never Python
  object identity.
* **Declaration order wins, with a reported conflict** — two archetypes
  declaring different defaults for the same configuration key resolve to the
  first-declared value, and the composition result carries the conflict as a
  typed fact. The *factory* converts the fact to ``warnings.warn``;
  composition itself stays pure (no I/O, no clock, no warnings).
* **Hard contradiction is a construction error** — the same obligation key
  contributed with incompatible required values raises the typed
  ``CompositionContradiction``, and factory construction fails on it.

Plus the composition example CLAUDE.md §6.3 names: a monitoring agent that
is also an assembler — the ``deal_monitor_assembler`` banking fixture
composing ``monitoring_surveillance`` + ``context_assembly`` — constructs
via the factory with its dimension-4 archetype tuple in declaration order.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.agent import Agent
from ccf.agents.archetypes import (
    ARCHETYPES,
    ArchetypeComponent,
    ConfigurationDefault,
    ReplayObligation,
)
from ccf.agents.composition import (
    ComposedArchetype,
    CompositionContradiction,
    DefaultConflict,
    compose,
)
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
)
from ccf.agents.factory import AgentFactory
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry

FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking"


class _Bundle:
    """A structural test bundle — conformance is structural, never nominal."""

    def __init__(
        self,
        identifier: str,
        obligations: tuple[ReplayObligation, ...] = (),
        defaults: tuple[ConfigurationDefault, ...] = (),
    ) -> None:
        self._id = identifier
        self._obligations = obligations
        self._defaults = defaults

    @property
    def archetype_id(self) -> str:
        return self._id

    def fabric_interaction_pattern(self) -> str:
        return f"{self._id}-pattern"

    def replay_obligations(self) -> tuple[ReplayObligation, ...]:
        return self._obligations

    def configuration_defaults(self) -> tuple[ConfigurationDefault, ...]:
        return self._defaults


_OBLIGATION = ReplayObligation(
    name="shared-capture", obligation="the shared value lands in replay"
)


# --- rule 1: dedupe identical obligations -----------------------------------


def test_identical_obligations_appear_once() -> None:
    """Identity is canonical bytes — a value-equal twin dedupes too."""
    twin = ReplayObligation(
        name=_OBLIGATION.name, obligation=_OBLIGATION.obligation
    )
    assert canonical_bytes(twin) == canonical_bytes(_OBLIGATION)
    composed = compose(
        (_Bundle("first", obligations=(_OBLIGATION,)),
         _Bundle("second", obligations=(twin,)))
    )
    assert composed.obligations == (_OBLIGATION,)
    assert composed.conflicts == ()


# --- rule 2: declaration order wins, conflict reported as a typed fact -------


def test_conflicting_defaults_resolve_by_declaration_order() -> None:
    first = _Bundle(
        "first",
        defaults=(ConfigurationDefault(name="cadence", value="on-trigger"),),
    )
    second = _Bundle(
        "second",
        defaults=(ConfigurationDefault(name="cadence", value="continuous"),),
    )
    composed = compose((first, second))
    assert composed.defaults == (
        ConfigurationDefault(name="cadence", value="on-trigger"),
    )
    assert len(composed.conflicts) == 1
    conflict = composed.conflicts[0]
    assert isinstance(conflict, DefaultConflict)
    assert isinstance(conflict, CCFContract)
    assert conflict.key == "cadence"
    assert conflict.winning_archetype == "first"
    assert conflict.losing_archetype == "second"


def test_identical_defaults_dedupe_without_a_conflict_fact() -> None:
    shared = ConfigurationDefault(name="cadence", value="on-trigger")
    composed = compose(
        (_Bundle("first", defaults=(shared,)),
         _Bundle("second", defaults=(shared,)))
    )
    assert composed.defaults == (shared,)
    assert composed.conflicts == ()


# --- rule 3: hard contradiction fails composition ----------------------------


def test_a_hard_contradiction_is_a_typed_error() -> None:
    """Same obligation key, incompatible required values — never mergeable."""
    first = _Bundle(
        "first",
        obligations=(
            ReplayObligation(name="capture", obligation="capture value A"),
        ),
    )
    second = _Bundle(
        "second",
        obligations=(
            ReplayObligation(name="capture", obligation="capture value B"),
        ),
    )
    with pytest.raises(CompositionContradiction):
        compose((first, second))


# --- purity and order-sensitivity --------------------------------------------


def test_composition_is_pure_and_order_sensitive() -> None:
    a = _Bundle(
        "a", defaults=(ConfigurationDefault(name="k", value="a-value"),)
    )
    b = _Bundle(
        "b", defaults=(ConfigurationDefault(name="k", value="b-value"),)
    )
    once = compose((a, b))
    again = compose((a, b))
    assert canonical_bytes(once) == canonical_bytes(again)
    reversed_result = compose((b, a))
    assert once.defaults[0].value == "a-value"
    assert reversed_result.defaults[0].value == "b-value"
    assert isinstance(once, ComposedArchetype)
    assert isinstance(once, CCFContract)


def test_composition_module_stays_pure_no_warnings_no_io() -> None:
    """warnings.warn lives in the factory; composition returns facts only."""
    source = Path("src/ccf/agents/composition.py").read_text()
    assert "warnings" not in source
    assert "datetime.now" not in source
    assert "open(" not in source


# --- factory integration ------------------------------------------------------


def _fixture(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "agents" / name).read_text()
    )
    return loaded


def _prompt_registered(plane: ControlPlaneRegistry) -> None:
    prompt_fixture: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "prompts" / "covenant_summary.yaml").read_text()
    )
    plane.register_typed(
        prompt_fixture["keys"]["prompt_artifact"],
        parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT),
        PROMPT_ARTIFACT,
    )


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    """A plane holding everything the deal_monitor_assembler references."""
    plane = ControlPlaneRegistry()
    _prompt_registered(plane)
    for reference in _fixture("deal_monitor_assembler.yaml")[
        "referenced_artifacts"
    ].values():
        artifact_class = declared_artifact_class(reference["class_id"])
        plane.register_typed(
            reference["key"],
            parse_artifact(
                {
                    "class_id": reference["class_id"],
                    "semver": reference["semver"],
                    "declaration": reference["declaration"],
                },
                artifact_class,
            ),
            artifact_class,
        )
    return plane


def _construct_fixture_agent(registry: ControlPlaneRegistry) -> Agent:
    fixture = _fixture("deal_monitor_assembler.yaml")
    definition = parse_artifact(
        fixture["agent_definition"], AGENT_DEFINITION
    )
    assert isinstance(definition, AgentDefinition)
    key = fixture["keys"]["agent_definition"]
    version = registry.register_versioned(key, definition, AGENT_DEFINITION)
    assert isinstance(version, str)
    return AgentFactory(control_plane=registry).construct(
        definition_key=key, definition_version=version
    )


def test_the_multi_archetype_fixture_constructs_in_declaration_order(
    registry: ControlPlaneRegistry,
) -> None:
    """The CLAUDE.md §6.3 example: a monitoring agent that is also an
    assembler; dimension-4 composition preserves declaration order."""
    agent = _construct_fixture_agent(registry)
    assert agent.identity.archetype_composition == (
        "monitoring_surveillance",
        "context_assembly",
    )
    assert tuple(c.archetype_id for c in agent.components) == (
        "monitoring_surveillance",
        "context_assembly",
    )


def test_the_factory_warns_on_an_order_resolved_default_conflict(
    registry: ControlPlaneRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The conflict fact becomes warnings.warn at the factory, naming the
    key and both archetypes (D-IMPL-19)."""
    conflicting: Mapping[str, ArchetypeComponent] = {
        **ARCHETYPES,
        "monitoring_surveillance": _Bundle(
            "monitoring_surveillance",
            defaults=(
                ConfigurationDefault(name="cadence", value="on-trigger"),
            ),
        ),
        "context_assembly": _Bundle(
            "context_assembly",
            defaults=(
                ConfigurationDefault(name="cadence", value="continuous"),
            ),
        ),
    }
    monkeypatch.setattr("ccf.agents.factory.ARCHETYPES", conflicting)
    with pytest.warns(UserWarning, match="cadence") as captured:
        _construct_fixture_agent(registry)
    text = str(captured[0].message)
    assert "monitoring_surveillance" in text
    assert "context_assembly" in text


def test_a_contradiction_fails_factory_construction(
    registry: ControlPlaneRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contradictory: Mapping[str, ArchetypeComponent] = {
        **ARCHETYPES,
        "monitoring_surveillance": _Bundle(
            "monitoring_surveillance",
            obligations=(
                ReplayObligation(name="capture", obligation="value A"),
            ),
        ),
        "context_assembly": _Bundle(
            "context_assembly",
            obligations=(
                ReplayObligation(name="capture", obligation="value B"),
            ),
        ),
    }
    monkeypatch.setattr("ccf.agents.factory.ARCHETYPES", contradictory)
    with pytest.raises(CompositionContradiction):
        _construct_fixture_agent(registry)
