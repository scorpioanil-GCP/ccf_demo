"""``AgentFactory.construct`` — the only Agent construction path (CLAUDE.md §6.4).

Written before the implementation per the TDD discipline (D-IMPL-28, D-12;
DESIGN.md §3.5). The claims pinned here:

* The factory resolves the definition and every referenced artifact through
  Control Plane resolution at pinned versions — never raw storage, never a
  moving target (an ``@latest`` instruction ref fails construction at the
  schema front door).
* All six axes validate; archetype bundles compose in declaration order; a
  declared archetype no shipped bundle realizes is a typed construction error.
* A prompt-parameter mismatch in an instruction binding fails construction
  with ``PromptValidationError`` (D-13).
* The constructed identity block is derived at construction time:
  ``content_hash(definition)``, the definition's versioned URI, the declared
  archetype tuple (D-06 — derived, never reconstructed).

Every agent in this module is constructed **via the factory from the banking
fixture artifacts** (CLAUDE.md §6.4); mutant definitions are fixture
mutations registered under their own keys, never inline documents.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.agent import Agent
from ccf.agents.archetypes import analytics_insights
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    TASK_DEFINITION,
    AgentDefinition,
    ConsumedProduct,
    ContextContract,
    InstructionBinding,
    PerspectiveBinding,
    PromptArtifact,
    TaskDefinition,
    VersionedRef,
)
from ccf.agents.errors import AgentDefinitionError, PromptValidationError
from ccf.agents.factory import AgentFactory, ControlPlaneResolution, Task, TaskFactory
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    ArtifactLoadError,
    declared_artifact_class,
    load_artifact,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry, RefuseUnbumpedChange

FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking"


def _agent_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "agents" / "covenant_analytics.yaml").read_text()
    )
    return loaded


def _prompt_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "prompts" / "covenant_summary.yaml").read_text()
    )
    return loaded


def _definition() -> AgentDefinition:
    definition = parse_artifact(
        _agent_fixture()["agent_definition"], AGENT_DEFINITION
    )
    assert isinstance(definition, AgentDefinition)
    return definition


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    """A Control Plane holding every artifact the fixture definition references."""
    plane = ControlPlaneRegistry()
    prompt_fixture = _prompt_fixture()
    prompt = parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT)
    plane.register_typed(
        prompt_fixture["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )
    for reference in _agent_fixture()["referenced_artifacts"].values():
        artifact_class = declared_artifact_class(reference["class_id"])
        declared = parse_artifact(
            {
                "class_id": reference["class_id"],
                "semver": reference["semver"],
                "declaration": reference["declaration"],
            },
            artifact_class,
        )
        plane.register_typed(reference["key"], declared, artifact_class)
    return plane


def _registered_definition(
    registry: ControlPlaneRegistry, definition: AgentDefinition, key: str
) -> str:
    version = registry.register_versioned(key, definition, AGENT_DEFINITION)
    assert isinstance(version, str)
    return version


def _construct(
    registry: ControlPlaneRegistry, definition: AgentDefinition, key: str
) -> Agent:
    version = _registered_definition(registry, definition, key)
    return AgentFactory(control_plane=registry).construct(
        definition_key=key, definition_version=version
    )


# --- the supported path -------------------------------------------------------


def test_the_factory_constructs_the_fixture_agent(
    registry: ControlPlaneRegistry,
) -> None:
    definition = _definition()
    key = _agent_fixture()["keys"]["agent_definition"]
    agent = _construct(registry, definition, key)
    assert isinstance(agent, Agent)
    assert agent.definition == definition
    assert tuple(c.archetype_id for c in agent.components) == definition.archetypes
    assert agent.bound_skill_names == ()  # skilling is a later wave


def test_the_identity_block_is_derived_at_construction_time(
    registry: ControlPlaneRegistry,
) -> None:
    definition = _definition()
    key = _agent_fixture()["keys"]["agent_definition"]
    agent = _construct(registry, definition, key)
    assert agent.identity.definition_hash == content_hash(definition)
    assert agent.identity.definition_uri == (
        f"ccf-artifact://{definition.tenant}/{AGENT_DEFINITION.class_id}/"
        f"{definition.name}@{definition.artifact_version}"
    )
    assert agent.identity.archetype_composition == definition.archetypes


def test_the_registry_satisfies_the_factory_resolution_protocol() -> None:
    assert isinstance(ControlPlaneRegistry(), ControlPlaneResolution)


# --- pinned versions only (D-IMPL-26) -------------------------------------------


def test_a_latest_instruction_ref_fails_at_the_construction_front_door() -> None:
    """@latest is refused before a definition can even be registered."""
    document = _agent_fixture()["agent_definition"]
    document["instruction_bindings"][0]["prompt"] = (
        "ccf-artifact://acme-bank/prompt/covenant-summary@latest"
    )
    with pytest.raises(ArtifactLoadError):
        load_artifact(yaml.safe_dump(document), AGENT_DEFINITION)


def test_an_unresolvable_reference_fails_construction() -> None:
    """Nothing registered — the factory refuses rather than inventing state."""
    definition = _definition()
    key = _agent_fixture()["keys"]["agent_definition"]
    empty = ControlPlaneRegistry()
    with pytest.raises(AgentDefinitionError):
        _construct(empty, definition, key)


# --- six-axis validation and composition ----------------------------------------


def test_a_declared_archetype_without_a_shipped_bundle_is_refused(
    registry: ControlPlaneRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid schema identifier, no realizing bundle — typed construction
    error, never a silent no-op. All six bundles ship as of 05-03, so the
    unrealized state is simulated by narrowing the factory's registry view."""
    monkeypatch.setattr(
        "ccf.agents.factory.ARCHETYPES",
        {"analytics_insights": analytics_insights},
    )
    definition = _definition().model_copy(update={"archetypes": ("workflow",)})
    with pytest.raises(AgentDefinitionError):
        _construct(registry, definition, "acme-bank/agents/workflow-mutant")


def test_a_prompt_parameter_mismatch_fails_construction(
    registry: ControlPlaneRegistry,
) -> None:
    """D-13: a bad instruction binding fails factory construction."""
    original = _definition()
    binding = original.instruction_bindings[0]
    narrowed = InstructionBinding(
        prompt=binding.prompt, parameters=binding.parameters[:1]
    )
    definition = original.model_copy(
        update={"instruction_bindings": (narrowed,)}
    )
    with pytest.raises(PromptValidationError):
        _construct(registry, definition, "acme-bank/agents/mismatch-mutant")


def test_the_resolved_prompt_artifacts_travel_with_the_agent(
    registry: ControlPlaneRegistry,
) -> None:
    definition = _definition()
    key = _agent_fixture()["keys"]["agent_definition"]
    agent = _construct(registry, definition, key)
    binding = definition.instruction_bindings[0]
    resolved = agent.instruction_artifact(binding.prompt)
    assert isinstance(resolved, PromptArtifact)
    assert frozenset(resolved.declared_parameters) == frozenset(binding.parameters)


# --- the Task Factory: schema + construction only (D-11; CLAUDE.md §6.4/§8.1) ---


def _task_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "tasks" / "covenant_review_task.yaml").read_text()
    )
    return loaded


def _task_definition() -> TaskDefinition:
    definition = parse_artifact(
        _task_fixture()["task_definition"], TASK_DEFINITION
    )
    assert isinstance(definition, TaskDefinition)
    return definition


@pytest.fixture
def task_registry(registry: ControlPlaneRegistry) -> ControlPlaneRegistry:
    """The agent registry plus everything the task fixture's steps reference."""
    fixture = _task_fixture()
    for reference in fixture["referenced_artifacts"].values():
        artifact_class = declared_artifact_class(reference["class_id"])
        declared = parse_artifact(
            {
                "class_id": reference["class_id"],
                "semver": reference["semver"],
                "declaration": reference["declaration"],
            },
            artifact_class,
        )
        registry.register_typed(reference["key"], declared, artifact_class)
    # The agent step resolves the covenant_analytics definition through the
    # URI-derived Control Plane key (DESIGN.md §3.5).
    registry.register_versioned(
        fixture["keys"]["referenced_agent_definition"],
        _definition(),
        AGENT_DEFINITION,
    )
    return registry


def _construct_task(registry: ControlPlaneRegistry) -> Task:
    fixture = _task_fixture()
    definition = _task_definition()
    key = fixture["keys"]["task_definition"]
    version = registry.register_versioned(key, definition, TASK_DEFINITION)
    assert isinstance(version, str)
    return TaskFactory(control_plane=registry).construct(
        definition_key=key, definition_version=version
    )


def test_the_task_fixture_loads_into_a_task_definition() -> None:
    definition = _task_definition()
    assert definition.name == "covenant-review"
    assert tuple(step.kind for step in definition.steps) == (
        "skill",
        "agent",
        "hitl-gate",
    )


def test_an_unknown_task_field_is_refused() -> None:
    document = _task_fixture()["task_definition"]
    document["execution_engine"] = "none"
    with pytest.raises(ArtifactLoadError):
        parse_artifact(document, TASK_DEFINITION)


def test_a_task_missing_its_artifact_version_is_refused() -> None:
    document = _task_fixture()["task_definition"]
    del document["artifact_version"]
    with pytest.raises(ArtifactLoadError):
        parse_artifact(document, TASK_DEFINITION)


def test_a_skill_or_agent_step_without_a_pinned_ref_is_refused() -> None:
    document = _task_fixture()["task_definition"]
    del document["steps"][0]["ref"]
    with pytest.raises(ArtifactLoadError):
        parse_artifact(document, TASK_DEFINITION)


def test_a_hitl_gate_step_carrying_a_ref_is_refused() -> None:
    """hitl-gate steps validate structurally and carry no behavior in I.2."""
    document = _task_fixture()["task_definition"]
    document["steps"][2]["ref"] = (
        "ccf-artifact://acme-bank/hitl-policy/credit-approval@1.0.0"
    )
    with pytest.raises(ArtifactLoadError):
        parse_artifact(document, TASK_DEFINITION)


def test_the_task_factory_constructs_the_fixture_task(
    task_registry: ControlPlaneRegistry,
) -> None:
    definition = _task_definition()
    task = _construct_task(task_registry)
    assert isinstance(task, Task)
    assert task.definition == definition
    assert task.identity.definition_hash == content_hash(definition)
    assert task.identity.definition_uri == (
        f"ccf-artifact://{definition.tenant}/{TASK_DEFINITION.class_id}/"
        f"{definition.name}@{definition.artifact_version}"
    )


def test_the_constructed_task_has_no_execution_surface(
    task_registry: ControlPlaneRegistry,
) -> None:
    """D-11: schema + construction/validation only — no execution engine."""
    task = _construct_task(task_registry)
    for name in ("execute", "run", "step", "loop", "plan"):
        assert not hasattr(task, name)


def test_no_replay_capture_is_invented_for_tasks(
    task_registry: ControlPlaneRegistry,
) -> None:
    """RESEARCH Open Question 4: nothing executes, so nothing records."""
    task = _construct_task(task_registry)
    for name in ("perspective_conditioning", "replay_record", "emit_effect"):
        assert not hasattr(task, name)


def test_an_unresolvable_task_step_ref_fails_construction(
    registry: ControlPlaneRegistry,
) -> None:
    """The agent registry alone lacks the skill and agent-step targets."""
    definition = _task_definition()
    key = _task_fixture()["keys"]["task_definition"]
    version = registry.register_versioned(key, definition, TASK_DEFINITION)
    assert isinstance(version, str)
    with pytest.raises(AgentDefinitionError):
        TaskFactory(control_plane=registry).construct(
            definition_key=key, definition_version=version
        )


def test_a_task_prompt_parameter_mismatch_fails_construction(
    task_registry: ControlPlaneRegistry,
) -> None:
    """D-13 holds for task instruction bindings exactly as for agents."""
    original = _task_definition()
    binding = original.instruction_bindings[0]
    narrowed = InstructionBinding(
        prompt=binding.prompt, parameters=binding.parameters[:1]
    )
    definition = original.model_copy(update={"instruction_bindings": (narrowed,)})
    version = task_registry.register_versioned(
        "acme-bank/tasks/mismatch-mutant", definition, TASK_DEFINITION
    )
    assert isinstance(version, str)
    with pytest.raises(PromptValidationError):
        TaskFactory(control_plane=task_registry).construct(
            definition_key="acme-bank/tasks/mismatch-mutant",
            definition_version=version,
        )


def test_construction_is_deterministic_for_the_same_pinned_versions(
    registry: ControlPlaneRegistry,
) -> None:
    """DESIGN.md §3.5: identical versions produce identical configuration."""
    definition = _definition()
    key = _agent_fixture()["keys"]["agent_definition"]
    version = _registered_definition(registry, definition, key)
    factory = AgentFactory(control_plane=registry)
    first = factory.construct(definition_key=key, definition_version=version)
    second = factory.construct(definition_key=key, definition_version=version)
    assert content_hash(first.identity) == content_hash(second.identity)


# --- axis change => new version, all six axes (success criterion 4; D-05) -------
#
# Mutations are structural transformations of fixture-loaded data only —
# reordering, swapping a ref version string, reusing another fixture value —
# never new prompt or domain content (No-Hardcoding Rule §6.4).


def _bump_ref_version(ref: str) -> str:
    """Swap a pinned ref's version string: ...@1.0.0 -> ...@2.0.0."""
    base, _, version = ref.rpartition("@")
    major, _, rest = version.partition(".")
    return f"{base}@{int(major) + 1}.{rest}"


def _axis_mutants(original: AgentDefinition) -> dict[str, AgentDefinition]:
    """One structurally-mutated variant per specialization axis (§6.2)."""
    consumed = original.context_contract.consumes[0]
    binding = original.instruction_bindings[0]
    return {
        "archetype_binding": original.model_copy(
            update={"archetypes": original.archetypes + ("context_assembly",)}
        ),
        "context_contract": original.model_copy(
            update={
                "context_contract": ContextContract(
                    consumes=(
                        ConsumedProduct(
                            product_class=consumed.product_class,
                            schema_version=_bump_ref_version(
                                f"@{consumed.schema_version}"
                            ).lstrip("@"),
                        ),
                    )
                )
            }
        ),
        "perspective": original.model_copy(
            update={
                "perspective": PerspectiveBinding(
                    role=original.name,  # reused fixture value, not new content
                    selection_params=original.perspective.selection_params,
                )
            }
        ),
        "policy_regime": original.model_copy(
            update={
                "policy_regime": VersionedRef(
                    ref=_bump_ref_version(original.policy_regime.ref)
                )
            }
        ),
        "halflife_debt_profile": original.model_copy(
            update={
                "halflife_debt_profile": VersionedRef(
                    ref=_bump_ref_version(original.halflife_debt_profile.ref)
                )
            }
        ),
        "instruction_bindings": original.model_copy(
            update={
                "instruction_bindings": (
                    InstructionBinding(
                        prompt=binding.prompt,
                        parameters=tuple(reversed(binding.parameters)),
                    ),
                )
            }
        ),
    }


def test_every_axis_mutation_produces_a_distinct_content_hash() -> None:
    original = _definition()
    original_hash = content_hash(original)
    hashes = {
        axis: content_hash(mutant)
        for axis, mutant in _axis_mutants(original).items()
    }
    for axis, mutated_hash in hashes.items():
        assert mutated_hash != original_hash, f"axis {axis!r} hash unchanged"
    assert len(set(hashes.values())) == len(hashes), "two axes collided"


def test_every_unbumped_axis_change_is_refused_at_registration(
    registry: ControlPlaneRegistry,
) -> None:
    """D-05: changed content under an unchanged artifact_version is refused."""
    original = _definition()
    key = _agent_fixture()["keys"]["agent_definition"]
    version = _registered_definition(registry, original, key)
    for axis, mutant in _axis_mutants(original).items():
        outcome = registry.register_versioned(key, mutant, AGENT_DEFINITION)
        assert isinstance(outcome, RefuseUnbumpedChange), (
            f"axis {axis!r}: expected RefuseUnbumpedChange, got {outcome!r}"
        )
    # The refused mutants left no trace: the original still resolves alone.
    assert registry.versions(key) == (version,)


def test_a_bumped_axis_change_lands_in_dimension_four(
    registry: ControlPlaneRegistry,
) -> None:
    """A bumped variant registers, constructs, and shows its new hash in the
    replay record's Perspective Conditioning dimension (D-05, D-06)."""
    original = _definition()
    key = _agent_fixture()["keys"]["agent_definition"]
    _registered_definition(registry, original, key)
    # The axis-6 mutant (reordered binding parameters) still constructs:
    # membership matches the prompt artifact's declaration (D-13).
    mutant = _axis_mutants(original)["instruction_bindings"].model_copy(
        update={"artifact_version": "1.4.0"}
    )
    bumped_version = registry.register_versioned(key, mutant, AGENT_DEFINITION)
    assert isinstance(bumped_version, str)
    agent = AgentFactory(control_plane=registry).construct(
        definition_key=key, definition_version=bumped_version
    )
    conditioning = agent.perspective_conditioning(principal_id="analyst-1")
    assert conditioning.agent_definition_hash == content_hash(mutant)
    assert conditioning.agent_definition_hash != content_hash(original)
    assert conditioning.agent_definition_uri.endswith("@1.4.0")
