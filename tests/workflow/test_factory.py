"""``WorkflowFactory.construct`` — ORCH-01's factory path, literal (CINV-01c).

Written before the implementation per the TDD discipline. The claims pinned
here: the factory resolves a registered ``ccf.workflow-definition`` and its
wrapped TaskDefinition through the Control Plane registry only and returns
a typed factory-built handle carrying the resolved pair plus provenance;
the registry-backed **semantic** layer refuses what the contract could not
see locally — a declared node absent from the resolved TaskDefinition's
steps (D-12), a gate policy on a step that is not hitl-gate-kind, an
exception ref that resolves to nothing (D-13); and the CINV-01c
factory-bypass coverage extends to the workflow surface (the lint cases
live in ``tests/lints/test_cinv01c_behavioral.py``); and, from D-IMPL-353,
``construct`` takes the definition key from an ``Execute``/``Resume``
capability's resource — there is no key parameter — and compares the
artifact's declared tenant with the capability's exactly once (§1.2/§1.3).

Every workflow in this module is constructed **via the factory from the
banking fixture artifacts** (CLAUDE.md §6.4); mutants are fixture
mutations registered under their own versions, never inline documents.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    TASK_DEFINITION,
    AgentDefinition,
    TaskDefinition,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.authz.actions import ACTION_ARTIFACT_READ
from ccf.authz.capability import (
    ArtifactRead,
    Authorized,
    CapabilityBypassError,
    Execute,
    mint,
)
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from ccf.workflow.factory import (
    Workflow,
    WorkflowConstructionError,
    WorkflowFactory,
    WorkflowIdentity,
    WorkflowTenantMismatchError,
)

from tests.workflow.capabilities import (
    PRINCIPAL,
    decision,
    execute_capability,
    resume_capability,
)
from http_api.composition_authority import (
    register_typed_at_composition,
    register_versioned_at_composition,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking"


def _load(relative: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((FIXTURES / relative).read_text())
    return loaded


def _workflow_fixture() -> dict[str, Any]:
    return _load("workflows/covenant_review_workflow.yaml")


def _workflow_definition(**mutations: Any) -> WorkflowDefinition:
    document = _workflow_fixture()["workflow_definition"]
    document.update(mutations)
    definition = parse_artifact(document, WORKFLOW_DEFINITION)
    assert isinstance(definition, WorkflowDefinition)
    return definition


def _register_declared(
    registry: ControlPlaneRegistry, references: dict[str, Any]
) -> None:
    for reference in references.values():
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


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    """A Control Plane holding everything the workflow's refs resolve to."""
    plane = ControlPlaneRegistry()
    # The wrapped task's own dependency closure: the agent definition its
    # agent step references, that agent's referenced artifacts, its prompt,
    # and the task's referenced skill.
    agent_fixture = _load("agents/covenant_analytics.yaml")
    prompt_fixture = _load("prompts/covenant_summary.yaml")
    prompt = parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT)
    register_typed_at_composition(plane, 
        prompt_fixture["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )
    _register_declared(plane, agent_fixture["referenced_artifacts"])
    agent = parse_artifact(agent_fixture["agent_definition"], AGENT_DEFINITION)
    assert isinstance(agent, AgentDefinition)
    task_fixture = _load("tasks/covenant_review_task.yaml")
    register_versioned_at_composition(plane, 
        task_fixture["keys"]["referenced_agent_definition"],
        agent,
        AGENT_DEFINITION,
    )
    _register_declared(plane, task_fixture["referenced_artifacts"])
    task = parse_artifact(task_fixture["task_definition"], TASK_DEFINITION)
    assert isinstance(task, TaskDefinition)
    # Registered at the URI-derived key the wrapper's ref names.
    register_versioned_at_composition(plane, 
        _workflow_fixture()["keys"]["task_definition"], task, TASK_DEFINITION
    )
    # The wrapper's own refs: exception handler and approval policy.
    _register_declared(plane, _workflow_fixture()["referenced_artifacts"])
    return plane


def _construct(
    registry: ControlPlaneRegistry, definition: WorkflowDefinition
) -> Workflow:
    key = _workflow_fixture()["keys"]["workflow_definition"]
    version = register_versioned_at_composition(registry, key, definition, WORKFLOW_DEFINITION)
    assert isinstance(version, str)
    return WorkflowFactory(control_plane=registry).construct(
        execute_capability(tenant=definition.tenant, resource=key),
        definition_version=version,
    )


# --- the supported path -------------------------------------------------------


def test_the_factory_constructs_the_fixture_workflow(
    registry: ControlPlaneRegistry,
) -> None:
    definition = _workflow_definition()
    workflow = _construct(registry, definition)
    assert isinstance(workflow, Workflow)
    assert workflow.definition == definition
    assert isinstance(workflow.task_definition, TaskDefinition)
    assert workflow.task_definition.name == "covenant-review"


def test_the_handle_carries_provenance_for_both_artifacts(
    registry: ControlPlaneRegistry,
) -> None:
    definition = _workflow_definition()
    workflow = _construct(registry, definition)
    identity = workflow.identity
    assert isinstance(identity, WorkflowIdentity)
    assert identity.definition_hash == content_hash(definition)
    assert identity.definition_uri == (
        f"ccf-artifact://{definition.tenant}/{WORKFLOW_DEFINITION.class_id}/"
        f"{definition.name}@{definition.artifact_version}"
    )
    assert identity.task_definition_hash == content_hash(
        workflow.task_definition
    )
    assert identity.task_definition_uri == definition.task_definition_ref


def test_nothing_constructed_here_can_execute(
    registry: ControlPlaneRegistry,
) -> None:
    """Execution is the engine's job (07-06), one level up from TaskFactory."""
    workflow = _construct(registry, _workflow_definition())
    for name in ("execute", "run", "step", "loop", "plan", "resume"):
        assert not hasattr(workflow, name)


# --- the registry-backed semantic layer ---------------------------------------


def test_a_node_absent_from_the_resolved_task_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    """The check the contract could not perform locally (D-12)."""
    document = _workflow_fixture()["workflow_definition"]
    document["artifact_version"] = "1.0.1"
    document["transitions"] = [
        {"source": "fetch-certificates", "target": "phantom-step"},
        {"source": "phantom-step", "target": "approved"},
    ]
    document["exception_refs"] = {}
    document["gate_policies"] = {}
    definition = parse_artifact(document, WORKFLOW_DEFINITION)
    assert isinstance(definition, WorkflowDefinition)
    with pytest.raises(WorkflowConstructionError, match="D-12"):
        _construct(registry, definition)


def test_a_gate_policy_on_a_non_hitl_gate_step_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    definition = _workflow_definition(
        artifact_version="1.0.2",
        gate_policies={
            "analyze-covenants": (
                "ccf-artifact://acme-bank/approval-policy/"
                "credit-officer@1.0.0"
            )
        },
    )
    with pytest.raises(WorkflowConstructionError, match="hitl-gate"):
        _construct(registry, definition)


def test_an_unresolvable_exception_ref_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    definition = _workflow_definition(
        artifact_version="1.0.3",
        exception_refs={
            "fetch-certificates": (
                "ccf-artifact://acme-bank/exception-handler/no-such@1.0.0"
            )
        },
    )
    with pytest.raises(WorkflowConstructionError, match="D-13"):
        _construct(registry, definition)


def test_a_task_ref_bound_to_a_non_task_class_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    definition = _workflow_definition(
        artifact_version="1.0.4",
        task_definition_ref=(
            "ccf-artifact://acme-bank/ccf.agent-definition/"
            "covenant-analytics@1.3.0"
        ),
    )
    with pytest.raises(WorkflowConstructionError, match="task-definition"):
        _construct(registry, definition)


def test_an_unresolvable_task_ref_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    definition = _workflow_definition(
        artifact_version="1.0.5",
        task_definition_ref=(
            "ccf-artifact://acme-bank/ccf.task-definition/no-such-task@1.0.0"
        ),
    )
    with pytest.raises(WorkflowConstructionError):
        _construct(registry, definition)


# --- factory-bypass (CINV-01c) ------------------------------------------------


def test_the_handle_refuses_a_forged_identity(
    registry: ControlPlaneRegistry,
) -> None:
    """A handle whose identity does not describe its definitions is refused."""
    definition = _workflow_definition()
    workflow = _construct(registry, definition)
    forged = WorkflowIdentity(
        definition_hash="0" * 64,
        definition_uri=workflow.identity.definition_uri,
        task_definition_hash=workflow.identity.task_definition_hash,
        task_definition_uri=workflow.identity.task_definition_uri,
    )
    factory_only = type(workflow)
    with pytest.raises(WorkflowConstructionError, match="content"):
        factory_only(
            definition=definition,
            task_definition=workflow.task_definition,
            identity=forged,
            definition_key=workflow.definition_key,
        )


# --- the capability at the factory (D-IMPL-353 §1.2/§1.3) ---------------------


def _registered(registry: ControlPlaneRegistry) -> tuple[WorkflowDefinition, str, str]:
    """The fixture definition registered under its fixture key; returns
    ``(definition, key, version)`` for tests that mint their own capability."""
    definition = _workflow_definition()
    key = _workflow_fixture()["keys"]["workflow_definition"]
    version = register_versioned_at_composition(registry, key, definition, WORKFLOW_DEFINITION)
    assert isinstance(version, str)
    return definition, key, version


def test_construct_takes_the_definition_key_from_the_capability(
    registry: ControlPlaneRegistry,
) -> None:
    definition, key, version = _registered(registry)
    authorized = execute_capability(tenant=definition.tenant, resource=key)
    workflow = WorkflowFactory(control_plane=registry).construct(
        authorized, definition_version=version
    )
    assert workflow.definition_key == key == authorized.resource
    assert workflow.definition == definition


def test_a_resume_capability_constructs_too(
    registry: ControlPlaneRegistry,
) -> None:
    """Both door-declared actions whose resource is a workflow key reach the
    factory; a ``Resume`` holder must be able to rebuild the handle."""
    definition, key, version = _registered(registry)
    workflow = WorkflowFactory(control_plane=registry).construct(
        resume_capability(tenant=definition.tenant, resource=key),
        definition_version=version,
    )
    assert workflow.definition_key == key


def test_a_tenant_mismatch_is_refused_once_at_construction(
    registry: ControlPlaneRegistry,
) -> None:
    """The ONE tenant comparison (§1.3): the artifact declares acme-bank; a
    capability for beta-bank on its key constructs nothing, and the typed
    refusal names both tenants and the key. It is a construction refusal,
    so existing ``WorkflowConstructionError`` handlers still catch it."""
    definition, key, version = _registered(registry)
    assert definition.tenant == "acme-bank"
    with pytest.raises(WorkflowTenantMismatchError) as refused:
        WorkflowFactory(control_plane=registry).construct(
            execute_capability(tenant="beta-bank", resource=key),
            definition_version=version,
        )
    assert isinstance(refused.value, WorkflowConstructionError)
    text = str(refused.value)
    assert "beta-bank" in text and "acme-bank" in text and key in text


def test_a_capability_of_another_kind_is_refused_at_construction(
    registry: ControlPlaneRegistry,
) -> None:
    """A genuine ``Authorized[ArtifactRead]`` for the very same key and
    tenant is the wrong kind: the factory performs Execute/Resume and
    nothing else (§1.5c)."""
    definition, key, version = _registered(registry)
    read = mint(
        ArtifactRead,
        decision=decision(
            tenant=definition.tenant, action=ACTION_ARTIFACT_READ, resource=key
        ),
        principal=PRINCIPAL,
        decision_id="authz-decision-read",
    )
    with pytest.raises(CapabilityBypassError, match="kind"):
        WorkflowFactory(control_plane=registry).construct(
            read,  # type: ignore[arg-type]
            definition_version=version,
        )


def test_a_retargeted_capability_cannot_dodge_the_tenant_comparison(
    registry: ControlPlaneRegistry,
) -> None:
    """§1.5g: a genuine acme-bank capability whose ``tenant`` is forced to
    beta-bank by ``object.__setattr__`` is refused by ``verify`` before the
    comparison runs — so the comparison can never see a tenant the mint did
    not bind."""
    definition, key, version = _registered(registry)
    retargeted: Authorized[Execute] = execute_capability(
        tenant=definition.tenant, resource=key
    )
    object.__setattr__(retargeted, "tenant", "beta-bank")
    with pytest.raises(CapabilityBypassError):
        WorkflowFactory(control_plane=registry).construct(
            retargeted, definition_version=version
        )


def test_the_handle_refuses_an_empty_definition_key(
    registry: ControlPlaneRegistry,
) -> None:
    """The handle carries the key it was resolved from; the empty string
    names no key (§1.2)."""
    definition = _workflow_definition()
    workflow = _construct(registry, definition)
    factory_only = type(workflow)
    with pytest.raises(WorkflowConstructionError, match="key"):
        factory_only(
            definition=definition,
            task_definition=workflow.task_definition,
            identity=workflow.identity,
            definition_key="",
        )
