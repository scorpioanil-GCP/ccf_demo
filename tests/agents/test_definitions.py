"""Six-axis agent definition schemas (CLAUDE.md §6.1/§6.2; D-IMPL-28).

Written before the implementation per the TDD discipline. The claims pinned
here:

* A valid six-axis YAML definition loads through the one supported path
  (``load_artifact``) into a typed ``AgentDefinition`` with every axis
  populated.
* The contract is closed-world: an unknown field is a rejection, and a missing
  axis is a rejection — no silent defaults (D-IMPL-38).
* Two-field versioning (D-IMPL-28): ``schema_version`` and ``artifact_version``
  are both required and both semver-validated.
* ``archetypes`` is a nonempty ordered list of *known* archetype identifiers.
* Instruction bindings are versioned-URI refs plus declared parameter names —
  the schema has no field that could carry an inline prompt (D-13).

All axis values live in the banking fixture YAML, none in this module
(No-Hardcoding Rule, §6.4).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    ARCHETYPE_IDS,
    AgentDefinition,
    InstructionBinding,
    PromptArtifact,
)
from ccf.controlplane.artifacts import ArtifactLoadError, load_artifact, parse_artifact

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "banking"
    / "agents"
    / "covenant_analytics.yaml"
)


def _document() -> dict[str, Any]:
    loaded = yaml.safe_load(FIXTURE.read_text())
    document: dict[str, Any] = loaded["agent_definition"]
    return document


def _mutated(**overrides: Any) -> dict[str, Any]:
    document = copy.deepcopy(_document())
    document.update(overrides)
    return document


# --- the happy path ----------------------------------------------------------


def test_a_valid_six_axis_definition_loads_via_load_artifact() -> None:
    text = yaml.safe_dump(_document())
    definition = load_artifact(text, AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    assert definition.name == "covenant-analytics"
    assert definition.tenant == "acme-bank"
    assert definition.archetypes == ("analytics_insights",)  # axis 1
    assert definition.context_contract.consumes  # axis 2
    assert definition.perspective.role == "credit-analyst"  # axis 3
    assert definition.policy_regime.ref.startswith("ccf-artifact://")  # axis 4
    assert definition.halflife_debt_profile.ref.startswith(
        "ccf-artifact://"
    )  # axis 5
    binding = definition.instruction_bindings[0]  # axis 6
    assert binding.prompt.startswith("ccf-artifact://")
    assert binding.parameters == ("entity_name", "as_of")


def test_the_artifact_class_constants_carry_the_contracts() -> None:
    assert AGENT_DEFINITION.class_id == "ccf.agent-definition"
    assert AGENT_DEFINITION.contract is AgentDefinition
    assert PROMPT_ARTIFACT.class_id == "ccf.prompt-artifact"
    assert PROMPT_ARTIFACT.contract is PromptArtifact


# --- closed world: extra=forbid, no silent defaults ---------------------------


def test_an_unknown_field_is_rejected() -> None:
    with pytest.raises(ArtifactLoadError):
        parse_artifact(_mutated(surprise="field"), AGENT_DEFINITION)


def test_a_missing_axis_is_rejected_not_defaulted() -> None:
    """Every axis is required (D-IMPL-38: no silent defaults)."""
    for axis in (
        "archetypes",
        "context_contract",
        "perspective",
        "policy_regime",
        "halflife_debt_profile",
        "instruction_bindings",
    ):
        document = copy.deepcopy(_document())
        del document[axis]
        with pytest.raises(ArtifactLoadError):
            parse_artifact(document, AGENT_DEFINITION)


# --- two-field versioning (D-IMPL-28) -----------------------------------------


def test_malformed_version_strings_fail_the_semver_validator() -> None:
    with pytest.raises(ArtifactLoadError):
        parse_artifact(_mutated(schema_version="one"), AGENT_DEFINITION)
    with pytest.raises(ArtifactLoadError):
        parse_artifact(_mutated(artifact_version="1.0"), AGENT_DEFINITION)


def test_both_version_fields_are_required() -> None:
    for version_field in ("schema_version", "artifact_version"):
        document = copy.deepcopy(_document())
        del document[version_field]
        with pytest.raises(ArtifactLoadError):
            parse_artifact(document, AGENT_DEFINITION)


# --- axis 1: archetypes ---------------------------------------------------------


def test_archetypes_must_be_nonempty() -> None:
    with pytest.raises(ArtifactLoadError):
        parse_artifact(_mutated(archetypes=[]), AGENT_DEFINITION)


def test_an_unknown_archetype_identifier_is_rejected() -> None:
    with pytest.raises(ArtifactLoadError):
        parse_artifact(_mutated(archetypes=["clairvoyance"]), AGENT_DEFINITION)


def test_the_six_shipped_archetype_identifiers_are_the_known_set() -> None:
    assert ARCHETYPE_IDS == frozenset(
        {
            "workflow",
            "document_intelligence",
            "analytics_insights",
            "monitoring_surveillance",
            "content_generation",
            "context_assembly",
        }
    )


# --- axis 6: instruction bindings are refs, never inline text (D-13) ----------


def test_instruction_bindings_are_refs_plus_parameter_names() -> None:
    definition = parse_artifact(_document(), AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    binding = definition.instruction_bindings[0]
    assert isinstance(binding, InstructionBinding)
    assert set(InstructionBinding.model_fields) == {"prompt", "parameters"}


def test_a_binding_ref_asking_for_latest_is_refused() -> None:
    document = copy.deepcopy(_document())
    document["instruction_bindings"][0]["prompt"] = (
        "ccf-artifact://acme-bank/prompt/covenant-summary@latest"
    )
    with pytest.raises(ArtifactLoadError):
        parse_artifact(document, AGENT_DEFINITION)


def test_an_inline_prompt_field_does_not_exist_on_the_schema() -> None:
    document = copy.deepcopy(_document())
    document["instruction_bindings"][0]["template"] = "summarise {{ entity }}"
    with pytest.raises(ArtifactLoadError):
        parse_artifact(document, AGENT_DEFINITION)


# --- the PromptArtifact contract ------------------------------------------------


def test_a_prompt_artifact_validates_with_two_field_versioning() -> None:
    prompt_fixture = (
        Path(__file__).parent.parent
        / "fixtures"
        / "banking"
        / "prompts"
        / "covenant_summary.yaml"
    )
    loaded = yaml.safe_load(prompt_fixture.read_text())
    artifact = parse_artifact(loaded["prompt_artifact"], PROMPT_ARTIFACT)
    assert isinstance(artifact, PromptArtifact)
    assert artifact.declared_parameters
    assert artifact.template
