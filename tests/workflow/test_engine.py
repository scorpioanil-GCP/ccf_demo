"""``WorkflowEngine`` — ORCH-01's execution half (07-06; CLAUDE.md §8.1).

Written before the implementation per the TDD discipline. The claims pinned
here, milestone by milestone:

**Milestone 1 (Task 1).** The engine's execute surface accepts ONLY the
WorkflowFactory-built handle (ORCH-01 "via the Task Factory", at the
execution boundary); a straight-line skill workflow runs to its declared
terminal with every transition audited and traced; broken wiring (a step ref
the engine's Control Plane cannot resolve) raises; an exception during a
node with an exception ref transitions to the ref'd target as a first-class
recorded transition, and an absent ref follows D-IMPL-61 propagate-to-
terminal semantics; a hitl-gate node suspends — typed suspended handle, not
an exception — persisting :class:`WorkflowStateRecord` keyed
``(tenant, execution_id)`` through the audited write surface only, with the
gate interaction going through the ``InMemoryHitlTransport`` stub (the real
ApprovalGate is 07-07 scope); and two tenants running the same workflow
shape concurrently never collide (D-23).

**Milestone 2 (Task 2).** ``resume`` loads and validates the persisted
record and continues to terminal; the execution trace writes through to the
ArtifactStore at each suspend AND at terminal (D-IMPL-18) while the live
suspended record stays native (D-IMPL-27); at terminal the step sequence
lands on replay dimension 5 verbatim and the workflow delegation chain
extends dimension 4 — byte-equality against what the engine serialized; and
resuming a nonexistent or already-terminal execution is a typed refusal,
audited ``resolved=False``.

Every workflow here is constructed **via the factory from the banking
fixture artifacts** (CLAUDE.md §6.4); node bindings are injected test
doubles for the deployment's composition-root bindings — the engine itself
names no harness and imports no dispatch target.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
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
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.workflow.definitions import (
    WORKFLOW_DEFINITION,
    WORKFLOW_FAILED_STATE,
    WorkflowDefinition,
)
from ccf.workflow.factory import Workflow, WorkflowFactory
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowExceptionRouted,
    WorkflowExecutionTypeError,
    WorkflowResumeRefused,
    WorkflowSuspended,
    WorkflowWiringError,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord

FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking"


def _load(relative: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((FIXTURES / relative).read_text())
    return loaded


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
        registry.register_typed(reference["key"], declared, artifact_class)


def _register_covenant_closure(plane: ControlPlaneRegistry) -> None:
    """Register everything the covenant-review workflow's refs resolve to."""
    prompt_fixture = _load("prompts/covenant_summary.yaml")
    prompt = parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT)
    plane.register_typed(
        prompt_fixture["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )
    agent_fixture = _load("agents/covenant_analytics.yaml")
    _register_declared(plane, agent_fixture["referenced_artifacts"])
    agent = parse_artifact(agent_fixture["agent_definition"], AGENT_DEFINITION)
    assert isinstance(agent, AgentDefinition)
    task_fixture = _load("tasks/covenant_review_task.yaml")
    plane.register_versioned(
        task_fixture["keys"]["referenced_agent_definition"],
        agent,
        AGENT_DEFINITION,
    )
    _register_declared(plane, task_fixture["referenced_artifacts"])
    task = parse_artifact(task_fixture["task_definition"], TASK_DEFINITION)
    assert isinstance(task, TaskDefinition)
    workflow_fixture = _load("workflows/covenant_review_workflow.yaml")
    plane.register_versioned(
        workflow_fixture["keys"]["task_definition"], task, TASK_DEFINITION
    )
    _register_declared(plane, workflow_fixture["referenced_artifacts"])


def _register_refresh_closure(plane: ControlPlaneRegistry) -> None:
    """Register the straight-line certificate-refresh workflow's closure."""
    task_fixture = _load("tasks/certificate_refresh_task.yaml")
    _register_declared(plane, task_fixture["referenced_artifacts"])
    task = parse_artifact(task_fixture["task_definition"], TASK_DEFINITION)
    assert isinstance(task, TaskDefinition)
    workflow_fixture = _load("workflows/certificate_refresh_workflow.yaml")
    plane.register_versioned(
        workflow_fixture["keys"]["task_definition"], task, TASK_DEFINITION
    )


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    plane = ControlPlaneRegistry(clock=_ticking_clock())
    _register_covenant_closure(plane)
    _register_refresh_closure(plane)
    return plane


def _construct(
    registry: ControlPlaneRegistry,
    workflow_fixture: str,
    **mutations: Any,
) -> Workflow:
    fixture = _load(workflow_fixture)
    document = fixture["workflow_definition"]
    document.update(mutations)
    definition = parse_artifact(document, WORKFLOW_DEFINITION)
    assert isinstance(definition, WorkflowDefinition)
    key = fixture["keys"]["workflow_definition"]
    if mutations:
        key = f"{definition.tenant}/workflows/{definition.name}"
    version = registry.register_versioned(key, definition, WORKFLOW_DEFINITION)
    assert isinstance(version, str)
    return WorkflowFactory(control_plane=registry).construct(
        definition_key=key, definition_version=version
    )


def _covenant(registry: ControlPlaneRegistry, **mutations: Any) -> Workflow:
    return _construct(
        registry, "workflows/covenant_review_workflow.yaml", **mutations
    )


def _refresh(registry: ControlPlaneRegistry, **mutations: Any) -> Workflow:
    return _construct(
        registry, "workflows/certificate_refresh_workflow.yaml", **mutations
    )


def _ticking_clock() -> Any:
    """A deterministic injected clock — no wall clock in any test path."""
    state = {"now": datetime(2026, 7, 30, tzinfo=UTC)}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


class _Bindings:
    """Injected node bindings — the deployment seam, stubbed for tests.

    ``failing`` names step names whose invocation raises, driving the
    exception paths without any routing value living in code.
    """

    def __init__(self, failing: frozenset[str] = frozenset()) -> None:
        self.failing = failing
        self.ran: list[str] = []

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        if step_name in self.failing:
            raise RuntimeError(f"skill {step_name!r} failed")
        self.ran.append(f"skill:{step_name}")
        return {"step": step_name}

    async def run_agent(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        if step_name in self.failing:
            raise RuntimeError(f"agent {step_name!r} failed")
        self.ran.append(f"agent:{step_name}")
        return {"step": step_name}


def _engine(
    registry: ControlPlaneRegistry,
    tmp_path: Path,
    *,
    failing: frozenset[str] = frozenset(),
) -> tuple[WorkflowEngine, InMemoryHitlTransport, _Bindings]:
    transport = InMemoryHitlTransport()
    bindings = _Bindings(failing=failing)
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=FileArtifactStore(root=tmp_path / "artifacts"),
        hitl_transport=transport,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=_ticking_clock(),
    )
    return engine, transport, bindings


# --- the factory boundary (ORCH-01) ------------------------------------------


def test_execute_refuses_a_raw_workflow_definition(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The execute surface accepts factory-built handles ONLY."""
    engine, _, _ = _engine(registry, tmp_path)
    fixture = _load("workflows/certificate_refresh_workflow.yaml")
    definition = parse_artifact(
        fixture["workflow_definition"], WORKFLOW_DEFINITION
    )
    with pytest.raises(WorkflowExecutionTypeError, match="WorkflowFactory"):
        asyncio.run(engine.execute(definition, execution_id="exec-1"))  # type: ignore[arg-type]


# --- straight-line execution --------------------------------------------------


def test_a_straight_line_skill_workflow_reaches_its_terminal(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    engine, _, bindings = _engine(registry, tmp_path)
    workflow = _refresh(registry)
    outcome = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == "refreshed"
    assert bindings.ran == [
        "skill:fetch-certificates",
        "skill:archive-certificates",
    ]


def test_every_transition_is_audited_and_traced(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    engine, _, _ = _engine(registry, tmp_path)
    workflow = _refresh(registry)
    outcome = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(outcome, WorkflowCompleted)
    transitions = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_transition"
    ]
    assert [(event.resolved) for event in transitions] == [True, True]
    key = f"{workflow.definition.tenant}/exec-1"
    assert all(event.key == key for event in transitions)
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    assert [
        (entry.source, entry.target) for entry in record.trace
    ] == [
        ("fetch-certificates", "archive-certificates"),
        ("archive-certificates", "refreshed"),
    ]


# --- broken wiring vs expected outcomes ---------------------------------------


def test_a_nonexistent_step_artifact_raises(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """Broken wiring raises; it is never a returned refusal."""
    workflow = _refresh(registry)
    sparse = ControlPlaneRegistry(clock=_ticking_clock())
    engine, _, _ = _engine(sparse, tmp_path)
    with pytest.raises(WorkflowWiringError, match="resolves to nothing"):
        asyncio.run(engine.execute(workflow, execution_id="exec-1"))


def test_an_exception_with_a_ref_routes_to_the_handler(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """A first-class recorded transition to the ref'd target (D-13)."""
    engine, _, _ = _engine(
        registry, tmp_path, failing=frozenset({"fetch-certificates"})
    )
    workflow = _covenant(registry)
    outcome = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(outcome, WorkflowExceptionRouted)
    assert outcome.handler_ref == (
        "ccf-artifact://acme-bank/exception-handler/"
        "certificate-fetch-failed@1.0.0"
    )
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    assert record.trace[-1].kind == "exception"
    assert record.trace[-1].source == "fetch-certificates"
    assert record.trace[-1].target == outcome.handler_ref
    exception_events = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_exception"
    ]
    assert len(exception_events) == 1 and exception_events[0].resolved


def test_an_absent_exception_ref_propagates_to_the_failed_terminal(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """D-IMPL-61 option-a: absence is a defined, audited transition."""
    engine, _, _ = _engine(
        registry, tmp_path, failing=frozenset({"archive-certificates"})
    )
    workflow = _refresh(registry)
    outcome = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == WORKFLOW_FAILED_STATE
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    assert record.trace[-1].kind == "exception"
    assert record.trace[-1].target == WORKFLOW_FAILED_STATE


# --- hitl-gate suspension -----------------------------------------------------


def test_reaching_a_hitl_gate_suspends_with_a_typed_handle(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    outcome = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(outcome, WorkflowSuspended)
    assert outcome.gate == "credit-officer-approval"
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "suspended"
    assert record.current_state == "credit-officer-approval"
    assert record.tenant == workflow.definition.tenant
    assert record.execution_id == "exec-1"
    assert record.workflow_definition_uri == workflow.identity.definition_uri
    pending = transport.pending(tenant=workflow.definition.tenant)
    assert len(pending) == 1
    assert pending[0].event_class == "approval-gate"
    assert pending[0].policy_ref == (
        "ccf-artifact://acme-bank/approval-policy/credit-officer@1.0.0"
    )
    suspended_events = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_suspended"
    ]
    assert len(suspended_events) == 1


def test_two_tenants_do_not_collide(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """(tenant, execution_id) keying — D-23."""
    engine, transport, _ = _engine(registry, tmp_path)
    acme = _covenant(registry)
    beta = _covenant(registry, tenant="beta-bank", artifact_version="1.1.0")
    first = asyncio.run(engine.execute(acme, execution_id="exec-1"))
    second = asyncio.run(engine.execute(beta, execution_id="exec-1"))
    assert isinstance(first, WorkflowSuspended)
    assert isinstance(second, WorkflowSuspended)
    acme_record = registry.state_store.get(WORKFLOW_STATE, "acme-bank/exec-1")
    beta_record = registry.state_store.get(WORKFLOW_STATE, "beta-bank/exec-1")
    assert isinstance(acme_record, WorkflowStateRecord)
    assert isinstance(beta_record, WorkflowStateRecord)
    assert acme_record.tenant == "acme-bank"
    assert beta_record.tenant == "beta-bank"
    assert len(transport.pending(tenant="acme-bank")) == 1
    assert len(transport.pending(tenant="beta-bank")) == 1
