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
import copy
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal

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
from ccf.graph.protocols import GraphView
from ccf.hitl.approval_gate import ApprovalGate, GateResolution
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import HitlActionSubmission, InMemoryHitlTransport
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    DecisionReplayRecord,
    PerspectiveConditioning,
    PolicyBinding,
    ResolutionNotApplicable,
    build_replay_record,
)
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


def _replay_record(
    *, workflow_step_sequence: str, delegation_chain: tuple[str, ...]
) -> DecisionReplayRecord:
    """Build a replay record threading the engine's verbatim blocks through
    the 07-05 keywords (dim 5) and the dim-4 delegation chain."""
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
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        agent_conditioning=PerspectiveConditioning(
            principal_id="principal-1",
            role="analyst",
            delegation_chain=delegation_chain,
        ),
        workflow_step_sequence=workflow_step_sequence,
    )


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


class _PermissiveDebt:
    """A non-breaching DebtAssessmentBinding stub (07-17): every handoff
    assesses OK, so pre-existing claims are exercised unchanged."""

    async def assess(
        self, *, tenant: str, step_name: str, ref: str
    ) -> DebtAssessment:
        return DebtAssessment(
            debt=Decimal("0"),
            signal=DebtSignal.OK,
            factors=DebtFactors(
                freshness=Decimal("1"),
                completeness=Decimal("1"),
                semantic_consistency=Decimal("1"),
            ),
        )


def _engine(
    registry: ControlPlaneRegistry,
    tmp_path: Path,
    *,
    failing: frozenset[str] = frozenset(),
    debt: bool = True,
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
        debt_binding=_PermissiveDebt() if debt else None,
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


# --- milestone 2: resume, trace write-through, replay -------------------------


def test_suspend_resume_terminal_round_trip(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
    )
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == "approved"
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "terminal"
    resumed_events = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed"
    ]
    assert len(resumed_events) == 1 and resumed_events[0].resolved


def test_the_trace_writes_through_at_suspend_and_at_terminal(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """D-IMPL-18: trace artifacts at both write-through points; D-IMPL-27:
    the live suspended record stays native, never on the ArtifactStore."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
    )
    store = engine.artifact_store
    suspend_trace = store.get(
        content_address=suspended.trace_artifact.content_address
    )
    assert suspend_trace  # canonical bytes, present at suspend
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    # The live record is native state, not an artifact.
    assert not store.exists(content_address=content_hash(record))
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowCompleted)
    terminal_trace = store.get(
        content_address=outcome.trace_artifact.content_address
    )
    assert terminal_trace != suspend_trace  # the trace grew between the two


def test_the_step_sequence_and_delegation_chain_land_on_replay(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """Byte-equality: dim 5 records the engine's block verbatim; dim 4's
    chain extends with the workflow execution id and agent identities."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
    )
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowCompleted)
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    # The block is the canonical serialization of the trace the engine kept
    # — serialized once by the engine, recorded verbatim (07-05 keywords).
    assert outcome.step_sequence_block == canonical_bytes(
        record.trace
    ).decode("utf-8")
    assert outcome.delegation_chain[0] == f"workflow:{key}"
    assert (
        "ccf-artifact://acme-bank/ccf.agent-definition/covenant-analytics@1.3.0"
        in outcome.delegation_chain
    )
    # Threaded through the 07-05 keywords, the record stores both verbatim:
    # byte-equality on dimension 5, chain extension on dimension 4.
    replay = _replay_record(
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


def test_resuming_an_unknown_execution_is_a_typed_refusal(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    engine, _, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="no-such", decision="approved")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    refusals = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed" and not event.resolved
    ]
    assert len(refusals) == 1


def test_resuming_a_terminal_execution_is_a_typed_refusal(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    engine, _, _ = _engine(registry, tmp_path)
    workflow = _refresh(registry)
    completed = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(completed, WorkflowCompleted)
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="refreshed")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    assert "terminal" in outcome.reason


def test_resuming_with_an_undeclared_decision_is_a_typed_refusal(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """Routing is interpreted from the artifact only (CINV-01): a decision
    must name a declared transition target from the suspended gate."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    # A real approval is on the authority path, so the refusal below is
    # about routing and nothing else (SEC-001 ordering: authority first).
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
    )
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="escalated")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    assert "escalated" in outcome.reason


# --- SEC-001: a gate is authority, not a string ------------------------------
#
# The security review of 2026-09-23 found that ``resume`` advanced a
# gate-suspended execution on the caller's ``decision`` string alone: the
# HITL transport was written to at suspend and never read at resume, and the
# audit recorded ``resolved=True`` with no approver. These tests pin the
# restored control — they fail against the pre-fix engine.


def _binding(product_content_hash: str, *, subject_id: str = "officer-1"):
    """One approver's complete D-IMPL-21 binding over what they saw."""
    return HumanPrincipalBinding(
        approver=ApproverIdentity(
            subject_id=subject_id,
            identity_provider_ref="oidc://acme-bank/staff",
        ),
        authentication=AuthenticationContext(
            method="oidc",
            assurance_level="aal2",
            session_ref="sess-1",
        ),
        action_time=datetime(2026, 7, 30, 12, tzinfo=UTC),
        product_content_hash=product_content_hash,
    )


def _resolve_gate(
    registry: ControlPlaneRegistry,
    transport: InMemoryHitlTransport,
    *,
    tenant: str,
    event_key: str,
    action: str = "approve",
    subject_id: str = "officer-1",
) -> GateResolution:
    """Put a real human action through the real ApprovalGate."""
    pending = next(
        event
        for event in transport.pending(tenant=tenant)
        if event.event_key == event_key
    )
    gate = ApprovalGate(
        transport=transport,
        audit=registry.audit_log,
        clock=_ticking_clock(),
    )
    resolution = gate.resolve(
        tenant=tenant,
        event_key=event_key,
        action=action,
        principal=_binding(
            pending.product_content_hash, subject_id=subject_id
        ),
    )
    assert isinstance(resolution, GateResolution)
    return resolution


def test_resuming_a_gate_with_no_human_action_is_refused(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001. Naming a declared transition is not approving: with nothing
    returned through the HITL authority path, the gate does not open."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "suspended"  # the gate still holds
    assert len(transport.pending(tenant=workflow.definition.tenant)) == 1
    refusals = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed" and not event.resolved
    ]
    assert len(refusals) == 1


def test_a_refused_gate_resume_does_not_enumerate_the_declared_targets(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001 remedy 3. The refusal must not answer the caller's question
    for them by printing the transitions it would have accepted."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    # Approve first: the authority check is ordered ahead of the routing
    # check, so without a real human action this test would never reach the
    # branch that used to enumerate — and would pass vacuously. (It did,
    # until a sabotage run proved it.)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
    )
    declared = {
        transition.target
        for transition in workflow.definition.transitions
        if transition.source == "credit-officer-approval"
    }
    assert declared  # the fixture really does declare targets to leak
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="escalated")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    for target in declared:
        assert target not in outcome.reason


def test_a_resolved_gate_resumes_and_audits_the_approver(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001. With a real ApprovalGate resolution on the authority path
    the workflow advances, and the audit names who opened the gate."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
    )
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == "approved"
    resumed = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed"
    ]
    assert len(resumed) == 1
    assert resumed[0].resolved
    assert resumed[0].actor == "officer-1"


def test_a_rejection_authorizes_resumption_but_does_not_bind_the_target(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001 residual, pinned (D-IMPL-350).

    A recorded rejection IS a human action on the authority path, so it
    satisfies the gate-authority check and the workflow leaves the gate —
    that is how a rejection reaches its declared ``rejected`` terminal
    (``test_slice.py::
    test_a_rejected_approval_routes_as_a_recorded_transition``).

    What no artifact declares is WHICH target each verdict may take, so a
    rejection can still be routed down the approving branch. This test
    records that residual as executable evidence and goes RED the moment a
    verdict→target binding is declared and enforced — which is the point.
    """
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
        action="reject",
        subject_id="officer-2",
    )
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowCompleted)  # the residual, visible
    resumed = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed"
    ]
    # The audit does name the human whose action opened the gate, so the
    # divergence is at least answerable from the record.
    assert resumed[0].actor == "officer-2"


def test_another_executions_approval_does_not_open_this_gate(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001. The human action binds to the suspension it was taken
    against — an approval of exec-1 is not an approval of exec-2."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    first = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    second = asyncio.run(engine.execute(workflow, execution_id="exec-2"))
    assert isinstance(first, WorkflowSuspended)
    assert isinstance(second, WorkflowSuspended)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=first.event_key,
    )
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-2", decision="approved")
    )
    assert isinstance(outcome, WorkflowResumeRefused)


def test_a_submission_that_never_saw_this_suspension_is_not_authority(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001. The HITL action door is submit-only by ruling (D-IMPL-62)
    and does not itself compare hashes, so a submission naming the right
    gate while attesting to something else is a reachable shape. It is not
    authority: an approval authorizes the suspension it actually saw.
    """
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    transport.submit(
        submission=HitlActionSubmission(
            event_key=suspended.event_key,
            tenant=workflow.definition.tenant,
            action="approve",
            principal=_binding("0" * 64, subject_id="impostor"),
        )
    )
    # It really is on the authority path — the refusal below is the hash
    # binding refusing it, not an empty queue.
    assert len(transport.submissions(tenant=workflow.definition.tenant)) == 1
    outcome = asyncio.run(
        engine.resume(workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowResumeRefused)


def test_a_substituted_handle_cannot_turn_a_gate_into_an_ordinary_node(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001, the walk-around found by the close-panel attack on the first
    Tier-0 fix and reproduced before this test was written.

    ``definition_uri`` is built from the artifact's OWN declared tenant, name
    and artifact_version, so two definitions registered under different keys
    can carry the same URI. The first fix asked the caller's handle whether
    the suspended node was a gate; a handle whose task definition calls that
    node an ordinary step skipped the authority check entirely and completed
    the workflow with nobody's approval.

    Whether an execution is waiting on a human is the fabric's recorded fact,
    never the caller's claim.
    """
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)

    # A task definition that calls the gate node an ordinary skill step.
    task_fixture = _load("tasks/covenant_review_task.yaml")
    task_document = copy.deepcopy(task_fixture["task_definition"])
    borrowed_ref = next(
        step["ref"] for step in task_document["steps"] if step.get("ref")
    )
    for step in task_document["steps"]:
        if step["kind"] == "hitl-gate":
            step["kind"] = "skill"
            step["ref"] = borrowed_ref
    task_document["artifact_version"] = "9.9.9"
    substitute_task = parse_artifact(task_document, TASK_DEFINITION)
    registry.register_versioned(
        "acme-bank/ccf.task-definition/covenant-review-substitute",
        substitute_task,
        TASK_DEFINITION,
    )

    # A workflow definition with the SAME tenant/name/version — so the same
    # definition_uri — wrapping that task, under a different registry key.
    workflow_document = copy.deepcopy(
        _load("workflows/covenant_review_workflow.yaml")["workflow_definition"]
    )
    workflow_document["task_definition_ref"] = (
        "ccf-artifact://acme-bank/ccf.task-definition/"
        "covenant-review-substitute@9.9.9"
    )
    workflow_document["gate_policies"] = {}
    substitute = parse_artifact(workflow_document, WORKFLOW_DEFINITION)
    version = registry.register_versioned(
        "attacker/covenant-review", substitute, WORKFLOW_DEFINITION
    )
    handle = WorkflowFactory(control_plane=registry).construct(
        definition_key="attacker/covenant-review", definition_version=version
    )
    # The substitution really is indistinguishable by URI — otherwise this
    # test would be passing on the definition-uri check it exists to get past.
    assert handle.identity.definition_uri == workflow.identity.definition_uri

    outcome = asyncio.run(
        engine.resume(handle, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    assert transport.submissions(tenant=workflow.definition.tenant) == ()
    assert len(transport.pending(tenant=workflow.definition.tenant)) == 1
    record = registry.state_store.get(
        WORKFLOW_STATE, f"{workflow.definition.tenant}/exec-1"
    )
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "suspended"


def test_a_substituted_definition_is_refused_even_with_a_real_approval(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001, the substitution class rather than one instance.

    ``resume``'s own refusal says an execution "continues only under the
    definition it was started with" — but it compared ``definition_uri``,
    which the artifact declares about itself. A second definition under a
    different registry key carries the same URI while declaring different
    routing, so a genuine approver's action could be spent on a transition
    their workflow never declared. The execution is bound to the definition
    by content, not by the name that definition gives itself.
    """
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    # A real human really does approve this suspension.
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
    )

    document = copy.deepcopy(
        _load("workflows/covenant_review_workflow.yaml")["workflow_definition"]
    )
    document["transitions"] = list(document["transitions"]) + [
        {"source": "credit-officer-approval", "target": "elsewhere"}
    ]
    document["terminal_states"] = list(document["terminal_states"]) + [
        "elsewhere"
    ]
    substitute = parse_artifact(document, WORKFLOW_DEFINITION)
    version = registry.register_versioned(
        "attacker/covenant-review-routes", substitute, WORKFLOW_DEFINITION
    )
    handle = WorkflowFactory(control_plane=registry).construct(
        definition_key="attacker/covenant-review-routes",
        definition_version=version,
    )
    assert handle.identity.definition_uri == workflow.identity.definition_uri
    assert handle.identity.definition_hash != workflow.identity.definition_hash

    outcome = asyncio.run(
        engine.resume(handle, execution_id="exec-1", decision="elsewhere")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    record = registry.state_store.get(
        WORKFLOW_STATE, f"{workflow.definition.tenant}/exec-1"
    )
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "suspended"
