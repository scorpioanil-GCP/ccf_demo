"""The D-01 vertical slice — engine + real ApprovalGate, end to end (07-07).

The phase's structural-novelty proof, written before the fixtures it runs
against (TDD): a two-step banking workflow (skill step, then hitl-gate)
constructed through the WorkflowFactory executes step 1, suspends on the
real :class:`~ccf.hitl.approval_gate.ApprovalGate`, resumes on an approval
carrying a :class:`~ccf.hitl.principal.HumanPrincipalBinding`, and reaches
terminal — with the human action on replay dimension 2 (approver identity
plus product content hash, verbatim) and the step sequence on dimension 5,
both byte-equal to the blocks the gate and engine themselves serialized.

Also pinned here: the TOCTOU guard (T-07-39 — a product mutated between
suspend and the human action is detected by hash mismatch and refused);
two-approver distinguishability (D-23); the rejected-approval path as a
recorded transition; and the CINV-04 adversarial cases — a resolution
engineered to skip the dimension-2 landing, and a completion whose
dimension-5 block is not threaded, must both be detectable against the
positive sentinels, never silent.

Every workflow value lives in the banking fixture artifacts
(No-Hardcoding Rule §6.4); deleting the fixture files makes this module
fail to load its world. CINV-04 owning tests:

* hitl-action-capture  → ``test_the_human_action_lands_on_dimension_2_verbatim``
* workflow-trace-capture → ``test_the_step_sequence_lands_on_dimension_5_verbatim``
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.definitions import TASK_DEFINITION, TaskDefinition
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.hitl.approval_gate import (
    ApprovalGate,
    GateResolution,
    GateResolutionRefused,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    NO_HITL_ACTIONS,
    NO_WORKFLOW_TRACE,
    DecisionReplayRecord,
    PerspectiveConditioning,
    PolicyBinding,
    build_replay_record,
)
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from ccf.workflow.factory import Workflow, WorkflowFactory
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord

FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking"


def _load(relative: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((FIXTURES / relative).read_text())
    return loaded


def _ticking_clock() -> Any:
    state = {"now": datetime(2026, 7, 30, tzinfo=UTC)}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


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


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    """The payment-release closure: task, skill, gate policy, workflow."""
    plane = ControlPlaneRegistry(clock=_ticking_clock())
    task_fixture = _load("tasks/payment_release_task.yaml")
    _register_declared(plane, task_fixture["referenced_artifacts"])
    task = parse_artifact(task_fixture["task_definition"], TASK_DEFINITION)
    assert isinstance(task, TaskDefinition)
    workflow_fixture = _load("workflows/payment_release_workflow.yaml")
    plane.register_versioned(
        workflow_fixture["keys"]["task_definition"], task, TASK_DEFINITION
    )
    _register_declared(plane, workflow_fixture["referenced_artifacts"])
    return plane


def _workflow(registry: ControlPlaneRegistry) -> Workflow:
    fixture = _load("workflows/payment_release_workflow.yaml")
    definition = parse_artifact(
        fixture["workflow_definition"], WORKFLOW_DEFINITION
    )
    assert isinstance(definition, WorkflowDefinition)
    key = fixture["keys"]["workflow_definition"]
    version = registry.register_versioned(
        key, definition, WORKFLOW_DEFINITION
    )
    assert isinstance(version, str)
    return WorkflowFactory(control_plane=registry).construct(
        definition_key=key, definition_version=version
    )


class _Bindings:
    def __init__(self) -> None:
        self.ran: list[str] = []

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        self.ran.append(f"skill:{step_name}")
        return {"step": step_name}

    async def run_agent(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        self.ran.append(f"agent:{step_name}")
        return {"step": step_name}


def _world(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> tuple[WorkflowEngine, ApprovalGate, InMemoryHitlTransport, _Bindings]:
    """Engine and gate composed over ONE transport and ONE audit plane."""
    transport = InMemoryHitlTransport()
    bindings = _Bindings()
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=FileArtifactStore(root=tmp_path / "artifacts"),
        hitl_transport=transport,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=_ticking_clock(),
    )
    gate = ApprovalGate(
        transport=transport, audit=registry.audit_log, clock=_ticking_clock()
    )
    return engine, gate, transport, bindings


def _principal(
    approver_key: str, *, product_content_hash: str
) -> HumanPrincipalBinding:
    approver = _load("hitl.yaml")["approvers"][approver_key]
    return HumanPrincipalBinding(
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=product_content_hash,
    )


def _run_to_approval(
    engine: WorkflowEngine,
    gate: ApprovalGate,
    transport: InMemoryHitlTransport,
    workflow: Workflow,
    *,
    execution_id: str,
    approver_key: str = "credit_officer",
    action: str = "approve",
) -> tuple[WorkflowSuspended, GateResolution]:
    suspended = asyncio.run(
        engine.execute(workflow, execution_id=execution_id)
    )
    assert isinstance(suspended, WorkflowSuspended)
    (pending,) = [
        event
        for event in transport.pending(tenant=workflow.definition.tenant)
        if event.event_key == suspended.event_key
    ]
    resolution = gate.resolve(
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
        action=action,
        principal=_principal(
            approver_key, product_content_hash=pending.product_content_hash
        ),
    )
    assert isinstance(resolution, GateResolution)
    return suspended, resolution


def _replay_record(
    *,
    hitl_actions: str | None,
    workflow_step_sequence: str | None,
    delegation_chain: tuple[str, ...],
) -> DecisionReplayRecord:
    """Thread the gate's and engine's verbatim blocks through the 07-05
    keywords into dimensions 2 and 5."""
    boundary = datetime(2026, 2, 1, tzinfo=UTC)
    execution = ExecutionResult(
        plan_id="plan-1",
        operators_invoked=frozenset({"traversal.neighbors"}),
        steps=(
            ExecutionStep(
                operator_key="traversal.neighbors",
                category="traversal",
                parameter_hash="ph-1",
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(plan_id="plan-1", payload={"k": "v"}),
        view=GraphView(tenant_id="acme-bank", as_of=boundary),
    )
    product = ContextProductContract(
        schema_name="ccf.test-product",
        schema_version="1.0.0",
        plan_id="plan-1",
        tenant_id="acme-bank",
        temporal_boundary=boundary,
        expires_at=datetime(2026, 4, 1, tzinfo=UTC),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"v1"}),
            graph_snapshot_at=boundary,
        ),
        payload={"k": "v"},
    )
    return build_replay_record(
        execution=execution,
        product=product,
        perspective=Perspective(principal_id="principal-1", role="analyst"),
        policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
        assembly_mode="algorithmic",
        recorded_at=datetime(2026, 3, 1, tzinfo=UTC),
        agent_conditioning=PerspectiveConditioning(
            principal_id="principal-1",
            role="analyst",
            delegation_chain=delegation_chain,
        ),
        hitl_actions=hitl_actions,
        workflow_step_sequence=workflow_step_sequence,
    )


# --- the slice ----------------------------------------------------------------


def test_the_slice_suspends_on_the_real_gate_and_resumes_to_terminal(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """Skill step runs, the REAL gate suspends, approval resumes, terminal."""
    engine, gate, transport, bindings = _world(registry, tmp_path)
    workflow = _workflow(registry)
    suspended, resolution = _run_to_approval(
        engine, gate, transport, workflow, execution_id="exec-1"
    )
    assert bindings.ran == ["skill:verify-payment"]
    assert suspended.gate == "treasury-approval"
    assert resolution.outcome.approved is True
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="released")
    )
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == "released"


def test_the_gate_event_binds_the_suspend_time_product_hash(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """What the approver is shown IS the suspended state, by content hash."""
    engine, _, transport, _ = _world(registry, tmp_path)
    workflow = _workflow(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    (pending,) = transport.pending(tenant=workflow.definition.tenant)
    assert pending.product_content_hash == content_hash(record)


def test_the_human_action_lands_on_dimension_2_verbatim(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """CINV-04 hitl-action-capture owning test: dimension 2 records the
    gate's pre-serialized block byte-for-byte — approver identity and the
    product content hash the approver saw, verbatim."""
    engine, gate, transport, _ = _world(registry, tmp_path)
    workflow = _workflow(registry)
    suspended, resolution = _run_to_approval(
        engine, gate, transport, workflow, execution_id="exec-1"
    )
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="released")
    )
    assert isinstance(outcome, WorkflowCompleted)
    replay = _replay_record(
        hitl_actions=resolution.hitl_actions_block,
        workflow_step_sequence=outcome.step_sequence_block,
        delegation_chain=outcome.delegation_chain,
    )
    block = replay.policy_bindings.hitl_actions
    assert block == resolution.hitl_actions_block
    assert (
        resolution.record.submission.principal.approver.subject_id in block
    )
    assert resolution.record.event.product_content_hash in block


def test_the_step_sequence_lands_on_dimension_5_verbatim(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """CINV-04 workflow-trace-capture owning test: dimension 5 records the
    engine's pre-serialized step-sequence block byte-for-byte."""
    engine, gate, transport, _ = _world(registry, tmp_path)
    workflow = _workflow(registry)
    _, resolution = _run_to_approval(
        engine, gate, transport, workflow, execution_id="exec-1"
    )
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="released")
    )
    assert isinstance(outcome, WorkflowCompleted)
    replay = _replay_record(
        hitl_actions=resolution.hitl_actions_block,
        workflow_step_sequence=outcome.step_sequence_block,
        delegation_chain=outcome.delegation_chain,
    )
    assert (
        replay.content_generation_path.workflow_step_sequence
        == outcome.step_sequence_block
    )
    assert (
        replay.perspective_conditioning.delegation_chain
        == outcome.delegation_chain
    )


# --- TOCTOU (T-07-39) ---------------------------------------------------------


def test_a_mutation_between_suspend_and_action_is_detected(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The binding's hash equals the SUSPEND-TIME product hash; a product
    mutated between suspend and the human action mismatches and is refused."""
    engine, gate, transport, _ = _world(registry, tmp_path)
    workflow = _workflow(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    # The product mutates between suspend and the human action: the approver
    # reviews the mutated version, so their binding carries its hash — which
    # is not the hash bound at suspend time.
    mutated = record.model_copy(update={"execution_id": "exec-1-tampered"})
    assert content_hash(mutated) != content_hash(record)
    refusal = gate.resolve(
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
        action="approve",
        principal=_principal(
            "credit_officer", product_content_hash=content_hash(mutated)
        ),
    )
    assert isinstance(refusal, GateResolutionRefused)
    assert "suspend" in refusal.reason
    # No action reached the authority path; the event survives re-review.
    assert transport.submissions(tenant=workflow.definition.tenant) == ()
    assert len(transport.pending(tenant=workflow.definition.tenant)) == 1


# --- two approvers (D-23) -----------------------------------------------------


def test_two_approvers_are_distinguishable_in_replay(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """Two distinct HumanPrincipalBindings on two gates produce replay
    records answerable to 'who approved which' from the records alone."""
    engine, gate, transport, _ = _world(registry, tmp_path)
    workflow = _workflow(registry)
    replays: dict[str, DecisionReplayRecord] = {}
    for execution_id, approver_key in (
        ("exec-1", "credit_officer"),
        ("exec-2", "treasury_officer"),
    ):
        _, resolution = _run_to_approval(
            engine,
            gate,
            transport,
            workflow,
            execution_id=execution_id,
            approver_key=approver_key,
        )
        outcome = asyncio.run(
            engine.resume(
                workflow, execution_id=execution_id, decision="released"
            )
        )
        assert isinstance(outcome, WorkflowCompleted)
        replays[approver_key] = _replay_record(
            hitl_actions=resolution.hitl_actions_block,
            workflow_step_sequence=outcome.step_sequence_block,
            delegation_chain=outcome.delegation_chain,
        )
    approvers = _load("hitl.yaml")["approvers"]
    first = replays["credit_officer"].policy_bindings.hitl_actions
    second = replays["treasury_officer"].policy_bindings.hitl_actions
    assert first != second
    assert approvers["credit_officer"]["identity"]["subject_id"] in first
    assert approvers["treasury_officer"]["identity"]["subject_id"] in second
    assert approvers["treasury_officer"]["identity"]["subject_id"] not in first


# --- rejection routes as a recorded transition --------------------------------


def test_a_rejected_approval_routes_as_a_recorded_transition(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    engine, gate, transport, _ = _world(registry, tmp_path)
    workflow = _workflow(registry)
    _, resolution = _run_to_approval(
        engine, gate, transport, workflow, execution_id="exec-1",
        action="reject",
    )
    assert resolution.outcome.approved is False
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="rejected")
    )
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == "rejected"
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "terminal"
    assert record.trace[-1].target == "rejected"
    # Both the human rejection and the workflow resumption are on the ONE
    # audit plane: the rejection as hitl_action resolved=False.
    rejections = [
        event
        for event in registry.audit_log.events()
        if event.action == "hitl_action" and not event.resolved
    ]
    assert len(rejections) == 1


# --- CINV-04 adversarial cases (guard the path, not just the happy case) ------


def test_a_resolution_that_skips_the_dim_2_landing_is_detectable(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """A caller that resolves a gate but does not thread the block leaves
    the positive NO_HITL_ACTIONS sentinel — never the block — so the
    owning test's byte-equality assertion turns red on the skipped path."""
    engine, gate, transport, _ = _world(registry, tmp_path)
    workflow = _workflow(registry)
    _, resolution = _run_to_approval(
        engine, gate, transport, workflow, execution_id="exec-1"
    )
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="released")
    )
    assert isinstance(outcome, WorkflowCompleted)
    skipped = _replay_record(
        hitl_actions=None,  # the engineered skip
        workflow_step_sequence=outcome.step_sequence_block,
        delegation_chain=outcome.delegation_chain,
    )
    assert skipped.policy_bindings.hitl_actions == NO_HITL_ACTIONS
    assert (
        skipped.policy_bindings.hitl_actions != resolution.hitl_actions_block
    )


def test_a_completion_that_skips_the_dim_5_landing_is_detectable(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """Dimension 5's positive sentinel distinguishes 'not a workflow step'
    from a dropped trace — the skipped path cannot pass for the landed one."""
    engine, gate, transport, _ = _world(registry, tmp_path)
    workflow = _workflow(registry)
    _, resolution = _run_to_approval(
        engine, gate, transport, workflow, execution_id="exec-1"
    )
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="released")
    )
    assert isinstance(outcome, WorkflowCompleted)
    skipped = _replay_record(
        hitl_actions=resolution.hitl_actions_block,
        workflow_step_sequence=None,  # the engineered skip
        delegation_chain=outcome.delegation_chain,
    )
    assert (
        skipped.content_generation_path.workflow_step_sequence
        == NO_WORKFLOW_TRACE
    )
    assert (
        skipped.content_generation_path.workflow_step_sequence
        != outcome.step_sequence_block
    )
