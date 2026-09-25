"""Factory-construction micro-benchmarks (PERF-01; D-23).

Agent and workflow (task) construction through the only supported paths —
``AgentFactory.construct`` and ``WorkflowFactory.construct`` (CLAUDE.md
§6.4) — from the perf battery's neutral definition artifacts. All artifact
registration happens in session fixtures; the benchmarks time construction
only.

Timing judgments live only in ``perf/gate.py`` (D-02).
"""

from __future__ import annotations

from typing import Any, NamedTuple

import pytest

from ccf.agents.agent import Agent
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    TASK_DEFINITION,
    AgentDefinition,
    PromptArtifact,
    TaskDefinition,
)
from ccf.agents.factory import AgentFactory
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from ccf.workflow.factory import Workflow, WorkflowFactory

from perf.conftest import (
    execute_capability,
    register_typed_at_composition,
    register_versioned_at_composition,
)
from perf.suites.common import load_artifact


class FactoryEnv(NamedTuple):
    """A populated Control Plane plus the pinned definition addresses."""

    registry: ControlPlaneRegistry
    agent_key: str
    agent_version: str
    workflow_key: str
    workflow_version: str
    #: The ``Execute`` capability the factory takes its definition key from.
    workflow_execute: Any


def _register_references(registry: ControlPlaneRegistry, doc: Any) -> None:
    for reference in doc.get("referenced_artifacts", {}).values():
        artifact_class = declared_artifact_class(reference["class_id"])
        declared = parse_artifact(
            {
                "class_id": reference["class_id"],
                "semver": reference["semver"],
                "declaration": reference["declaration"],
            },
            artifact_class,
        )
        register_typed_at_composition(registry, reference["key"], declared, artifact_class)


@pytest.fixture(scope="session")
def factory_env() -> FactoryEnv:
    """Register the fixture-artifact closure once; benchmarks construct only."""
    agent_doc = load_artifact("agent.yaml")
    prompt_doc = load_artifact("prompt.yaml")
    task_doc = load_artifact("task.yaml")
    workflow_doc = load_artifact("workflow.yaml")

    registry = ControlPlaneRegistry()
    for doc in (agent_doc, task_doc, workflow_doc):
        _register_references(registry, doc)

    prompt = parse_artifact(prompt_doc["prompt_artifact"], PROMPT_ARTIFACT)
    assert isinstance(prompt, PromptArtifact)
    register_typed_at_composition(
        registry, prompt_doc["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )

    definition = parse_artifact(agent_doc["agent_definition"], AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    agent_key = agent_doc["keys"]["agent_definition"]
    agent_version = register_versioned_at_composition(
        registry, agent_key, definition, AGENT_DEFINITION
    )
    assert isinstance(agent_version, str)
    # The task's agent-step ref resolves at the URI-derived key.
    register_versioned_at_composition(
        registry,
        task_doc["keys"]["referenced_agent_definition"],
        definition,
        AGENT_DEFINITION,
    )

    task = parse_artifact(task_doc["task_definition"], TASK_DEFINITION)
    assert isinstance(task, TaskDefinition)
    register_versioned_at_composition(
        registry, workflow_doc["keys"]["task_definition"], task, TASK_DEFINITION
    )

    workflow = parse_artifact(
        workflow_doc["workflow_definition"], WORKFLOW_DEFINITION
    )
    assert isinstance(workflow, WorkflowDefinition)
    workflow_key = workflow_doc["keys"]["workflow_definition"]
    workflow_version = register_versioned_at_composition(
        registry, workflow_key, workflow, WORKFLOW_DEFINITION
    )
    assert isinstance(workflow_version, str)

    return FactoryEnv(
        workflow_execute=execute_capability(
            tenant=workflow.tenant, resource=workflow_key
        ),
        registry=registry,
        agent_key=agent_key,
        agent_version=agent_version,
        workflow_key=workflow_key,
        workflow_version=workflow_version,
    )


def test_agent_factory_construct(benchmark, factory_env: FactoryEnv) -> None:
    def construct() -> Agent:
        return AgentFactory(control_plane=factory_env.registry).construct(
            definition_key=factory_env.agent_key,
            definition_version=factory_env.agent_version,
        )

    agent = benchmark(construct)
    assert isinstance(agent, Agent)


def test_task_factory_construct(benchmark, factory_env: FactoryEnv) -> None:
    def construct() -> Workflow:
        return WorkflowFactory(control_plane=factory_env.registry).construct(
            factory_env.workflow_execute,
            definition_version=factory_env.workflow_version,
        )

    workflow = benchmark(construct)
    assert isinstance(workflow, Workflow)
