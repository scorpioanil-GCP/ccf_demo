"""JSON Schema export for every I.2 definition-artifact contract (D-IMPL-28).

D-IMPL-28 rules "YAML artifacts + Pydantic v2 schemas + **exported JSON
Schema**": every artifact class a deployment authors documents against must
produce a JSON Schema via ``model_json_schema()``, closed-world
(``additionalProperties: false``) at every level, with all six specialization
axes visible on the agent definition.

``ARTIFACT_CONTRACTS`` is the module-level registry of exported contracts —
the skilling wave (05-05) extends the tuple, not the tests.

Schema output text is pydantic-version-sensitive (05-RESEARCH.md Pitfall 7),
so the pinned-version check runs as a skip-guard precondition in the repo's
deferral discipline: an environment off the pin skips with an explicit
reason rather than asserting against a shape another pydantic produced.
"""

from __future__ import annotations

from typing import Any

import pydantic
import pytest

from ccf.agents.definitions import AgentDefinition, PromptArtifact, TaskDefinition
from ccf.contracts.base import CCFContract
from ccf.skills.catalog import SkillCatalogEntry

PINNED_PYDANTIC = "2.13.4"

pytestmark = pytest.mark.skipif(
    pydantic.__version__ != PINNED_PYDANTIC,
    reason=(
        f"JSON Schema output is pydantic-version-sensitive (Pitfall 7):"
        f" pinned {PINNED_PYDANTIC}, found {pydantic.__version__} —"
        " re-pin before trusting schema assertions"
    ),
)

#: Every I.2 artifact contract with an exported JSON Schema. 05-05 appends
#: the skill contracts here; the tests below iterate this registry.
ARTIFACT_CONTRACTS: tuple[type[CCFContract], ...] = (
    AgentDefinition,
    TaskDefinition,
    PromptArtifact,
    SkillCatalogEntry,
)

#: The six specialization axes (CLAUDE.md §6.2 channel 1), as they appear on
#: the agent-definition schema.
SIX_AXIS_PROPERTIES: tuple[str, ...] = (
    "archetypes",
    "context_contract",
    "perspective",
    "policy_regime",
    "halflife_debt_profile",
    "instruction_bindings",
)


def _schemas_with_properties(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """The root schema plus every ``$defs`` entry that declares an object."""
    nested = [
        definition
        for definition in schema.get("$defs", {}).values()
        if definition.get("type") == "object"
    ]
    return [schema, *nested]


def test_the_pinned_pydantic_is_in_force() -> None:
    assert pydantic.__version__ == PINNED_PYDANTIC


@pytest.mark.parametrize("contract", ARTIFACT_CONTRACTS)
def test_every_artifact_contract_exports_a_json_schema(
    contract: type[CCFContract],
) -> None:
    schema = contract.model_json_schema()
    assert schema["type"] == "object"
    assert schema["title"] == contract.__name__
    assert schema["properties"]


@pytest.mark.parametrize("contract", ARTIFACT_CONTRACTS)
def test_every_exported_schema_is_closed_world_at_every_level(
    contract: type[CCFContract],
) -> None:
    """extra=forbid must survive export, on the root and every nested model."""
    schema = contract.model_json_schema()
    for candidate in _schemas_with_properties(schema):
        assert candidate.get("additionalProperties") is False, (
            f"{contract.__name__}: schema level {candidate.get('title')!r}"
            " is not closed-world"
        )


def test_the_agent_definition_schema_carries_all_six_axes() -> None:
    schema = AgentDefinition.model_json_schema()
    for axis in SIX_AXIS_PROPERTIES:
        assert axis in schema["properties"], f"axis {axis!r} missing"
        assert axis in schema["required"], f"axis {axis!r} not required"


def test_the_task_definition_schema_requires_ordered_steps() -> None:
    schema = TaskDefinition.model_json_schema()
    assert "steps" in schema["required"]
    assert schema["properties"]["steps"]["type"] == "array"
