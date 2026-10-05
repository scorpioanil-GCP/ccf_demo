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
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml
from joserfc.jwk import ECKey

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
from ccf.controlplane.audit import (
    AuditEvent,
    WorkflowVerdictIntegrityAuditEvent,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.hitl.approval_gate import (
    GATE_ACTIONS,
    GATE_EVENT_CLASS,
    ApprovalGate,
    GateResolution,
)
from ccf.hitl.escalation import (
    EscalationHandOff,
    EscalationResolution,
    ExceptionEscalation,
    ExplicitEscalation,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.identity_binding import HitlActionClaims, sign_hitl_action
from ccf.hitl.transport import (
    HITL_POLICY,
    HitlActionSubmission,
    HitlPolicy,
    InMemoryHitlTransport,
    SignedBindingMismatchRefused,
    enforce_attestation,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
)
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
from ccf.workflow.factory import (
    Workflow,
    WorkflowConstructionError,
    WorkflowFactory,
)
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

from tests.composition import (
    register_fixture_approval_policies,
    register_typed_at_composition,
    without_approval_policies,
)
from tests.hitl.capabilities import submit_capability
from tests.workflow.capabilities import (
    execute_as,
    execute_capability,
    resume_as,
)
from http_api.composition_authority import (
    deployment_store,
    register_typed_at_composition,
    register_versioned_at_composition,
)

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
        register_typed_at_composition(registry, reference["key"], declared, artifact_class)


def _register_covenant_closure(
    plane: ControlPlaneRegistry, *, as_shipped: bool = False
) -> None:
    """Register everything the covenant-review workflow's refs resolve to.

    SEC-006 (`D-IMPL-366`): the gate's approval policy is registered as the
    TYPED ``ccf.approval-policy`` from ``approval_policies.yaml`` under the key
    the fixture's ref pins — the fixture file itself is untouched. With
    ``as_shipped=True`` the fixture's own PRE-CHANGE ``DeclaredArtifact``
    policy is registered instead, which the factory now refuses by ruling
    (§4 (5)): the shape the SEC-006 factory control exercises.
    """
    prompt_fixture = _load("prompts/covenant_summary.yaml")
    prompt = parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT)
    register_typed_at_composition(plane, 
        prompt_fixture["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )
    agent_fixture = _load("agents/covenant_analytics.yaml")
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
    workflow_fixture = _load("workflows/covenant_review_workflow.yaml")
    register_versioned_at_composition(plane, 
        workflow_fixture["keys"]["task_definition"], task, TASK_DEFINITION
    )
    if as_shipped:
        _register_declared(plane, workflow_fixture["referenced_artifacts"])
    else:
        _register_declared(
            plane, without_approval_policies(workflow_fixture["referenced_artifacts"])
        )
        register_fixture_approval_policies(plane)


def _register_refresh_closure(plane: ControlPlaneRegistry) -> None:
    """Register the straight-line certificate-refresh workflow's closure."""
    task_fixture = _load("tasks/certificate_refresh_task.yaml")
    _register_declared(plane, task_fixture["referenced_artifacts"])
    task = parse_artifact(task_fixture["task_definition"], TASK_DEFINITION)
    assert isinstance(task, TaskDefinition)
    workflow_fixture = _load("workflows/certificate_refresh_workflow.yaml")
    register_versioned_at_composition(plane, 
        workflow_fixture["keys"]["task_definition"], task, TASK_DEFINITION
    )


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    plane = ControlPlaneRegistry(clock=_ticking_clock())
    _register_covenant_closure(plane)
    _register_refresh_closure(plane)
    return plane


def _workflow_definition_document(
    workflow_fixture: str, **mutations: Any
) -> WorkflowDefinition:
    """Parse one fixture workflow definition, with optional mutations."""
    document = _load(workflow_fixture)["workflow_definition"]
    document.update(mutations)
    definition = parse_artifact(document, WORKFLOW_DEFINITION)
    assert isinstance(definition, WorkflowDefinition)
    return definition


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
    version = register_versioned_at_composition(registry, key, definition, WORKFLOW_DEFINITION)
    assert isinstance(version, str)
    return WorkflowFactory(control_plane=registry).construct(
        execute_capability(tenant=definition.tenant, resource=key),
        definition_version=version,
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
    transport: InMemoryHitlTransport | None = None,
) -> tuple[WorkflowEngine, InMemoryHitlTransport, _Bindings]:
    transport = InMemoryHitlTransport() if transport is None else transport
    bindings = _Bindings(failing=failing)
    engine = WorkflowEngine(
        control_plane=registry,
        # The trace class declared under Execute | Resume (D-IMPL-353 §1.2):
        # what this deployment's engine writes for itself.
        artifact_store=deployment_store(tmp_path / "artifacts", workflow_traces=True),
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
    genuine = execute_as(_refresh(registry))  # a real capability; a raw definition
    with pytest.raises(WorkflowExecutionTypeError, match="WorkflowFactory"):
        asyncio.run(engine.execute(genuine, definition, execution_id="exec-1"))  # type: ignore[arg-type]


# --- straight-line execution --------------------------------------------------


def test_a_straight_line_skill_workflow_reaches_its_terminal(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    engine, _, bindings = _engine(registry, tmp_path)
    workflow = _refresh(registry)
    outcome = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
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
    outcome = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
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
        asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))


def test_an_exception_with_a_ref_routes_to_the_handler(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """A first-class recorded transition to the ref'd target (D-13)."""
    engine, _, _ = _engine(
        registry, tmp_path, failing=frozenset({"fetch-certificates"})
    )
    workflow = _covenant(registry)
    outcome = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
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
    outcome = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
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
    outcome = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
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
    first = asyncio.run(engine.execute(execute_as(acme), acme, execution_id="exec-1"))
    second = asyncio.run(engine.execute(execute_as(beta), beta, execution_id="exec-1"))
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
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
    )
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
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
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
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
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
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
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
    )
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
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
        engine.resume(resume_as(workflow), workflow, execution_id="no-such", decision="approved")
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
    completed = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(completed, WorkflowCompleted)
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="refreshed")
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
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
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
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="escalated")
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


def _binding(
    product_content_hash: str,
    *,
    subject_id: str = "officer-1",
    verdict: str = "approve",
):
    """One approver's complete D-IMPL-21 binding over what they saw and decided.

    ``verdict`` is a parameter rather than a constant: a helper that pinned one
    verdict could not express an approver who rejected, and
    `enforce_attestation` compares this value against both the submission's
    action and the SIGNED ``action`` claim (`SEC-005`; `D-IMPL-363` E1) — the
    verdict on this binding is the door-minted, UNSIGNED half, which is
    exactly what T13 forges.
    """
    return HumanPrincipalBinding(
        verdict=verdict,
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
        submit_capability(tenant=tenant, principal=subject_id, event_key=event_key),
        event_key=event_key,
        action=action,
        principal=_binding(
            pending.product_content_hash, subject_id=subject_id, verdict=action
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
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
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
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
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
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="escalated")
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
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
    )
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
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


def test_mutating_gate_routes_cannot_route_a_recorded_rejection_to_the_approving_terminal(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """THE SEC-001 RESIDUAL the route compare does not cover: the route map it
    reads is mutable in place, and the hash that would catch the swap is a
    string captured once.

    ``WorkflowDefinition.gate_routes`` is annotated ``Mapping[str, Mapping[str,
    str]]``, which Pydantic v2 validates into a plain ``dict`` of ``dict``s.
    ``CCFContract`` sets ``frozen=True``, which forbids REBINDING the attribute
    and says nothing about mutating the object it already points at. The engine
    reads the route live on every resume, so a mutated map is the map the
    compare consults.

    The hash does not save it. ``Workflow.__init__`` computes
    ``content_hash(definition)`` once and only VERIFIES it against the identity
    it was handed; ``WorkflowEngine.resume`` then compares
    ``record.workflow_definition_hash`` against
    ``workflow.identity.definition_hash`` — two strings, neither re-derived from
    the definition. So a post-construction mutation moves the routing without
    moving the pin. Recomputing ``content_hash`` over the mutated definition
    DOES differ (``gate_routes`` carries ``ccf_hash_transparent: False``, a
    generation boundary, so it is rendered into the hash) — nothing recomputes
    it.

    WHY THIS TEST FAILS ONLY FOR THAT REASON, which is the condition it was
    written under. Each of the other outcomes leaves it GREEN rather than red:
    if the mapping refused mutation, the route is unchanged and the compare
    refuses the resume; if anything re-derived the hash at resume, the
    definition-hash binding refuses it first. Only a mutation that both lands
    and escapes the pin can carry a recorded rejection to the approving
    terminal. The two facts are therefore reported in the failure message
    rather than asserted, so a green result cannot be mistaken for the hole
    being absent for a different reason.

    ``landed`` IS ASSERTED, and that assertion is the point (Dave, 2026-10-03).
    The two outcome assertions alone would be satisfied by whichever guard
    happened to fire — ``resume`` has several that return a
    ``WorkflowResumeRefused`` — so a green on them is the absence of this hole
    only by accident, and a later un-freeze would not necessarily redden this
    file. ``assert not landed`` pins the mechanism directly: the mapping must
    REFUSE the write. The assignment is wrapped so the refusal does not abort
    the test before that assertion is reached, and ``pin_held`` stays reported
    rather than asserted because asserting it would let the test redden for the
    hash instead of for the hole. The two outcome assertions stay as the
    consequence pin: un-freeze the mapping and ``landed`` is true, the engine
    routes the recorded rejection, and they fail too.

    Both the gate and the approving terminal are DERIVED — the gate from the
    state the workflow actually suspended at, the terminal from where the
    artifact routes its own ``approve`` verdict — so no step names a domain
    value this test invented.
    """
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(
        engine.execute(execute_as(workflow), workflow, execution_id="exec-1")
    )
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry, transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
        action="reject", subject_id="officer-2",
    )
    record = registry.state_store.get(
        WORKFLOW_STATE, f"{workflow.definition.tenant}/exec-1"
    )
    assert isinstance(record, WorkflowStateRecord)
    gate = record.current_state

    pinned = workflow.identity.definition_hash
    routes = workflow.definition.gate_routes[gate]
    approving = routes["approve"]
    try:
        routes["reject"] = approving
    except TypeError:
        landed = False
    else:
        landed = routes["reject"] == approving
    pin_held = workflow.identity.definition_hash == pinned
    assert not landed, (
        "the route mapping accepted a write after construction and"
        f" gate_routes[{gate!r}]['reject'] now names the approving terminal"
        f" {approving!r}; definition-hash pin held={pin_held}"
    )

    outcome = asyncio.run(
        engine.resume(
            resume_as(workflow), workflow, execution_id="exec-1", decision=approving
        )
    )
    after = registry.state_store.get(
        WORKFLOW_STATE, f"{workflow.definition.tenant}/exec-1"
    )
    assert isinstance(after, WorkflowStateRecord)
    assert isinstance(outcome, WorkflowResumeRefused), (
        "a recorded rejection reached the approving terminal through an"
        f" in-place mutation of gate_routes[{gate!r}]: mutation landed"
        f"={landed}, definition-hash pin held={pin_held}, resulting status"
        f"={after.status!r} at {after.current_state!r}"
    )
    assert after.current_state != approving, (
        f"the workflow state advanced to the approving terminal {approving!r}"
        f" on a recorded rejection: mutation landed={landed}, definition-hash"
        f" pin held={pin_held}"
    )


def test_a_recorded_rejection_cannot_be_routed_down_the_approving_branch(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001 residual, CLOSED (D-IMPL-357 A3). The artifact declares where
    each verdict goes; the caller's decision must agree with it.

    Replaces ``test_a_rejection_authorizes_resumption_but_does_not_bind_
    the_target``, which asserted the DEFECT: a recorded rejection completing
    the workflow down the ``approved`` branch. That test was written to go
    red the moment a verdict→target binding was declared and enforced, and
    this is that moment.

    The positive assertion on the reason is deliberate. Four other guards in
    ``resume`` also return a ``WorkflowResumeRefused`` whose reason contains
    neither ``reject`` nor ``rejected`` — the definition content-hash
    binding, the no-authority refusal and the declared-target check among
    them — so the two negative assertions alone would pass with the route
    compare never running. Naming the mechanism's own phrase does not
    weaken the no-enumeration property that
    ``test_a_refused_gate_resume_does_not_enumerate_the_declared_targets``
    pins: the phrase names neither the recorded verdict nor the target the
    artifact routes it to.
    """
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry, transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
        action="reject", subject_id="officer-2",
    )
    refused = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(refused, WorkflowResumeRefused)
    assert "does not agree with the route" in refused.reason
    assert "reject" not in refused.reason and "rejected" not in refused.reason
    resumed = [e for e in registry.audit_log.events() if e.action == "workflow_resumed"]
    assert resumed[-1].resolved is False
    # STRENGTHENED, not relaxed (D-IMPL-357 A4). This row used to assert
    # ``actor is None``, which was the defect the A4 review named: every
    # resume refusal audited identically, so "a caller tried to route a
    # recorded rejection down the approving branch" was byte-identical in
    # the log to "a caller mistyped the decision". A refusal caused by a
    # recorded human verdict now names the rule and the approver, and the
    # event class itself distinguishes it.
    assert isinstance(resumed[-1], WorkflowVerdictIntegrityAuditEvent)
    assert resumed[-1].workflow_verdict_integrity == "route_disagreement"
    assert resumed[-1].workflow_recorded_approver == "officer-2"
    assert resumed[-1].actor == "officer-2"
    # The gate is still open, and the declared route for the verdict works.
    record = registry.state_store.get(
        WORKFLOW_STATE, f"{workflow.definition.tenant}/exec-1"
    )
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "suspended"
    assert record.current_state == "credit-officer-approval"
    completed = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="rejected")
    )
    assert isinstance(completed, WorkflowCompleted)
    assert completed.terminal_state == "rejected"
    # RESTORED from the test this one replaced, which asserted
    # ``resumed[0].actor == "officer-2"``: the audit names the human whose
    # REJECTION opened the gate. That is the exact remedy this
    # vulnerability's own fix introduced, and nothing else pins it — one
    # sibling asserts the actor for an APPROVAL, another asserts the
    # rejection's action row rather than the resumption's actor. Dropping it
    # was a weakening, and "rewritten, never weakened" is binding.
    attributed = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed" and event.resolved
    ]
    assert attributed[-1].actor == "officer-2"


def test_a_terminal_gate_with_no_route_map_cannot_be_constructed(
    registry: ControlPlaneRegistry,
) -> None:
    """The one gate shape the boot-time completeness check did not cover is
    now refused at construction, so the engine can never be handed it
    (D-IMPL-357 A2, review round 1, item 7).

    **What this test used to assert, and why it changed.** A2's review found
    that a START node which is both a declared terminal state and a
    ``hitl-gate``-kind step in the resolved task escapes the factory's
    completeness population — ``routable`` subtracts the terminal states, the
    A1 validator then forbids declaring a map for it, and ``execute`` hands
    the start node straight to ``_advance``, which suspends on the step's
    kind before any terminal test. So ``gate_routes`` could legitimately hold
    nothing for the node a resume arrived on, and this test pinned that the
    shape resolved to a typed refusal rather than an exception. A3's review
    then found the mirror shape — the same kind of step listed in
    ``terminal_states`` and reached as a transition target — which COMPLETES
    with no human action at all. Item 7 took one change for both: the factory
    refuses any step whose resolved kind is ``hitl-gate`` and whose name
    appears in ``effective_terminal_states``, because a gate is a place a
    human acts and is never a terminal condition.

    **So the property strengthened rather than weakened: the shape is now
    inexpressible instead of refused late.** Nothing is lost that can still
    be reached — the factory is the only construction path to an executable
    handle (CINV-01c), so no test may manufacture the shape to drive the
    resume path with it.

    **The disclosure that goes with it.** ``resume``'s route lookup is still
    written ``.get(state, {}).get(action)`` rather than an index, and the
    ``route is None`` half of that guard is now structurally unreachable with
    a usable target rather than merely improbable. It stands as
    defense-in-depth, disclosed here and in the method's own comment: no
    behavioral test can distinguish it from a plain index, and no later edit
    of the resume path may reach an unguarded index on a gate's route map.

    Both refusals are pinned at the construction boundary by
    ``tests/workflow/test_factory.py::
    test_a_gate_that_is_the_start_node_and_terminal_is_refused_at_construction``
    and its sibling for the transition-target shape.
    """
    with pytest.raises(WorkflowConstructionError, match="never a terminal condition"):
        _covenant(
            registry,
            name="terminal-gate-workflow",
            start="credit-officer-approval",
            transitions=[],
            terminal_states=["credit-officer-approval"],
            exception_refs={},
            gate_routes={},
        )


def test_another_executions_approval_does_not_open_this_gate(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001. The human action binds to the suspension it was taken
    against — an approval of exec-1 is not an approval of exec-2."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    first = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    second = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-2"))
    assert isinstance(first, WorkflowSuspended)
    assert isinstance(second, WorkflowSuspended)
    _resolve_gate(
        registry,
        transport,
        tenant=workflow.definition.tenant,
        event_key=first.event_key,
    )
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-2", decision="approved")
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
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    transport.submit(
        submit_capability(
            tenant=workflow.definition.tenant,
            principal="impostor",
            event_key=suspended.event_key,
        ),
        submission=HitlActionSubmission(
            event_key=suspended.event_key,
            action="approve",
            principal=_binding("0" * 64, subject_id="impostor"),
        ),
    )
    # It really is on the authority path — the refusal below is the hash
    # binding refusing it, not an empty queue.
    assert len(transport.submissions(tenant=workflow.definition.tenant)) == 1
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
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
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
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
    register_versioned_at_composition(registry, 
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
    # The substitute task calls this step "skill", not "hitl-gate"; a
    # gate_routes entry surviving the copy would trip the D-IMPL-357 A2
    # kind check the substitution is not testing (SEC-001 is resume-time
    # authority, not gate-routing completeness).
    workflow_document["gate_routes"] = {}
    substitute = parse_artifact(workflow_document, WORKFLOW_DEFINITION)
    version = register_versioned_at_composition(registry,
        "attacker/covenant-review", substitute, WORKFLOW_DEFINITION
    )
    handle = WorkflowFactory(control_plane=registry).construct(
        execute_capability(tenant="acme-bank", resource="attacker/covenant-review"),
        definition_version=version,
    )
    # The substitution really is indistinguishable by URI — otherwise this
    # test would be passing on the definition-uri check it exists to get past.
    assert handle.identity.definition_uri == workflow.identity.definition_uri

    outcome = asyncio.run(
        engine.resume(resume_as(handle), handle, execution_id="exec-1", decision="approved")
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
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
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
    version = register_versioned_at_composition(registry, 
        "attacker/covenant-review-routes", substitute, WORKFLOW_DEFINITION
    )
    handle = WorkflowFactory(control_plane=registry).construct(
        execute_capability(
            tenant="acme-bank", resource="attacker/covenant-review-routes"
        ),
        definition_version=version,
    )
    assert handle.identity.definition_uri == workflow.identity.definition_uri
    assert handle.identity.definition_hash != workflow.identity.definition_hash

    outcome = asyncio.run(
        engine.resume(resume_as(handle), handle, execution_id="exec-1", decision="elsewhere")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    record = registry.state_store.get(
        WORKFLOW_STATE, f"{workflow.definition.tenant}/exec-1"
    )
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "suspended"


# --- SEC-001 Tier 0: the exception-routed branch, and which primitive answered
#
# Two holes the first SEC-001 remedy left, found by the follow-up read of
# 2026-09-24:
#
# 1. ``resume``'s exception-routed branch — everything after the
#    ``status == "suspended"`` block — advanced with NO authority check and
#    audited ``resolved=True, actor=None``: the exact signature SEC-001
#    named, one branch over. The engine's own ``_route_exception`` enqueues
#    nothing, so the branch reads as human-free — but
#    :class:`~ccf.hitl.escalation.ExceptionEscalation` IS the shipped
#    primitive for a routed state, and a deployment that composes it really
#    does put a human in the loop that the engine then walked past.
# 2. ``_gate_authority`` never asked WHICH HITL primitive the submission
#    answered, so an action taken against another primitive's event could
#    satisfy an approval-gate check.
#
# The tests below were written first and watched fail against the pre-fix
# engine.


def _escalate(
    registry: ControlPlaneRegistry,
    transport: InMemoryHitlTransport,
    *,
    tenant: str,
    key: str,
    event_key: str,
    product_content_hash: str,
) -> ExceptionEscalation:
    """Compose the shipped ExceptionEscalation over a routed state.

    The composition-root wiring of ``tests/workflow/test_exception_paths.py``
    — the engine returns the routed outcome, the deployment hands that state
    to the primitive on the shared transport. The primitive instance is
    returned because its hand-off trigger is per-instance (WR-01): the
    deployment resolves on the instance that escalated.
    """
    escalation = ExceptionEscalation(
        transport=transport, audit=registry.audit_log, clock=_ticking_clock()
    )
    hand_off = escalation.escalate(
        tenant=tenant,
        event_key=event_key,
        workflow_state_ref=key,
        product_content_hash=product_content_hash,
        policy_ref=None,
        trigger=ExplicitEscalation(
            reason=_load("hitl.yaml")["escalation"]["explicit_reason"]
        ),
    )
    assert isinstance(hand_off, EscalationHandOff)
    return escalation


def _resolve_escalation(
    escalation: ExceptionEscalation,
    *,
    tenant: str,
    event_key: str,
    product_content_hash: str,
    subject_id: str = "duty-officer-9",
) -> None:
    """Put a real human action through the real ExceptionEscalation."""
    resolution = escalation.resolve(
        submit_capability(tenant=tenant, principal=subject_id, event_key=event_key),
        event_key=event_key,
        action="approve",
        principal=_binding(product_content_hash, subject_id=subject_id),
    )
    assert isinstance(resolution, EscalationResolution)


def _route(
    registry: ControlPlaneRegistry, tmp_path: Path, *, execution_id: str
) -> tuple[WorkflowEngine, InMemoryHitlTransport, _Bindings, Workflow, str]:
    """Drive one execution onto the exception-routed branch."""
    engine, transport, bindings = _engine(
        registry, tmp_path, failing=frozenset({"fetch-certificates"})
    )
    workflow = _covenant(registry)
    routed = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id=execution_id))
    assert isinstance(routed, WorkflowExceptionRouted)
    # The retry must be able to succeed, or the resume re-routes and the
    # assertions below would read the second routing rather than the resume.
    bindings.failing = frozenset()
    return (
        engine,
        transport,
        bindings,
        workflow,
        f"{workflow.definition.tenant}/{execution_id}",
    )


def test_a_pending_escalation_holds_the_exception_routed_resume(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001 on the exception-routed branch.

    With an unresolved ``exception-escalation`` bound to this execution on
    the authority path, a human is genuinely in the loop. The engine must
    not walk past them.
    """
    engine, transport, _, workflow, key = _route(
        registry, tmp_path, execution_id="exec-esc"
    )
    tenant = workflow.definition.tenant
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    _escalate(
        registry,
        transport,
        tenant=tenant,
        key=key,
        event_key=f"{key}/fetch-certificates",
        product_content_hash=content_hash(record),
    )
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-esc", decision="retry")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    # The routed state still holds, and the human's question is still open.
    after = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(after, WorkflowStateRecord)
    assert after.status == "exception-routed"
    assert len(transport.pending(tenant=tenant)) == 1
    refusals = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed" and not event.resolved
    ]
    assert len(refusals) == 1


def test_a_resolved_escalation_resumes_and_audits_the_resolver(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001 on the exception-routed branch, the admitting case.

    The resolving human is the audit ``actor`` — the branch used to record
    ``resolved=True, actor=None`` whatever had happened.
    """
    engine, transport, _, workflow, key = _route(
        registry, tmp_path, execution_id="exec-esc"
    )
    tenant = workflow.definition.tenant
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    event_key = f"{key}/fetch-certificates"
    escalation = _escalate(
        registry,
        transport,
        tenant=tenant,
        key=key,
        event_key=event_key,
        product_content_hash=content_hash(record),
    )
    _resolve_escalation(
        escalation,
        tenant=tenant,
        event_key=event_key,
        product_content_hash=content_hash(record),
    )
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-esc", decision="retry")
    )
    assert isinstance(outcome, WorkflowSuspended)  # retried, reached the gate
    resumed = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed"
    ]
    assert len(resumed) == 1
    assert resumed[0].resolved
    assert resumed[0].actor == "duty-officer-9"


def test_an_exception_routed_resume_without_escalation_is_unaffected(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The positive control, and the compatibility claim in one.

    A deployment that composes no escalation has no human in the loop, so
    the routed resume proceeds exactly as before — and states positively
    that no human acted. Without this test the guard above could be
    satisfied by an engine that refused every routed resume.
    """
    engine, transport, _, workflow, key = _route(
        registry, tmp_path, execution_id="exec-esc"
    )
    tenant = workflow.definition.tenant
    assert transport.pending(tenant=tenant) == ()
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-esc", decision="retry")
    )
    assert isinstance(outcome, WorkflowSuspended)
    resumed = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed"
    ]
    assert len(resumed) == 1
    assert resumed[0].resolved and resumed[0].actor is None


def test_another_executions_escalation_does_not_release_this_routing(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The hand-off binds to the execution it was taken against (D-23).

    An open escalation about exec-1 neither holds nor releases exec-2, and
    exec-2's resume must not borrow exec-1's resolver as its actor.
    """
    engine, transport, bindings = _engine(
        registry, tmp_path, failing=frozenset({"fetch-certificates"})
    )
    workflow = _covenant(registry)
    tenant = workflow.definition.tenant
    first = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    second = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-2"))
    assert isinstance(first, WorkflowExceptionRouted)
    assert isinstance(second, WorkflowExceptionRouted)
    bindings.failing = frozenset()
    first_key = f"{tenant}/exec-1"
    first_record = registry.state_store.get(WORKFLOW_STATE, first_key)
    assert isinstance(first_record, WorkflowStateRecord)
    _escalate(
        registry,
        transport,
        tenant=tenant,
        key=first_key,
        event_key=f"{first_key}/fetch-certificates",
        product_content_hash=content_hash(first_record),
    )
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-2", decision="retry")
    )
    assert isinstance(outcome, WorkflowSuspended)
    resumed = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed"
    ]
    assert len(resumed) == 1
    assert resumed[0].actor is None
    # exec-1's question is still open, and exec-1 is still held.
    held = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="retry")
    )
    assert isinstance(held, WorkflowResumeRefused)


def test_an_escalation_resolution_is_not_an_approval_gate_verdict(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The second hole: ``_gate_authority`` never asked which primitive
    answered.

    A deployment may legitimately hand a stuck gate to
    :class:`~ccf.hitl.escalation.ExceptionEscalation` — that is what the
    primitive is for. The duty officer who resolves that escalation has
    not approved the credit, and their ``approve`` must not open the gate.
    Both primitives carry the same two-verdict vocabulary and the same
    suspension hash, so nothing but the answered event class separates
    them.
    """
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    tenant = workflow.definition.tenant
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    key = f"{tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    # The deployment routes the stuck gate to the escalation primitive: the
    # gate's own pending event is consumed and re-posted as an escalation.
    assert (
        transport.remove(tenant=tenant, event_key=suspended.event_key)
        is not None
    )
    escalation = _escalate(
        registry,
        transport,
        tenant=tenant,
        key=key,
        event_key=suspended.event_key,
        product_content_hash=content_hash(record),
    )
    _resolve_escalation(
        escalation,
        tenant=tenant,
        event_key=suspended.event_key,
        product_content_hash=content_hash(record),
    )
    # The submission names this gate, attests to this suspension, and reads
    # ``approve`` — everything the pre-fix check compared.
    (recorded,) = transport.submissions(tenant=tenant)
    assert recorded.event_key == suspended.event_key
    assert recorded.principal.product_content_hash == content_hash(record)
    assert recorded.action in GATE_ACTIONS
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowResumeRefused)


def test_a_bare_submission_needs_this_gate_to_still_be_pending(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The submit-only door's submission joins to a real pending gate event.

    ``POST /hitl/actions`` is submit-only by ruling (D-IMPL-62): it records
    an action and resolves nothing, so the gate's own event is still
    pending when such a submission is the authority. That pending
    approval-gate event is the join. With no pending gate event and no
    primitive having claimed one, nothing on the authority path says this
    submission answered an approval gate at all.
    """
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    tenant = workflow.definition.tenant
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    key = f"{tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    transport.submit(
        submit_capability(
            tenant=tenant, principal="officer-3", event_key=suspended.event_key
        ),
        submission=HitlActionSubmission(
            event_key=suspended.event_key,
            action="approve",
            principal=_binding(content_hash(record), subject_id="officer-3"),
        ),
    )
    # Drained rather than resolved: no primitive claimed it, so no recorded
    # fact says which primitive this submission answered.
    assert transport.dequeue(tenant=tenant) is not None
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowResumeRefused)


# --- D-IMPL-357 A4: which recorded verdict is authoritative -------------------
#
# A3 closed the ROUTING compare: the caller's decision must agree with the
# target the artifact declares for the verdict the authority path recorded.
# Round 1 of review then measured two paths that still reach an approving
# terminal after a rejection was recorded, and neither is a routing defect —
# both attack verdict SELECTION, so the compare faithfully agrees with
# whichever verdict was selected. These tests pin the selection-integrity
# guard: two recorded human verdicts in disagreement on ONE suspension refuse
# the resumption outright, whichever of them selection would have followed.


def _submit_only(
    transport: InMemoryHitlTransport,
    *,
    tenant: str,
    event_key: str,
    product_content_hash: str,
    action: str,
    subject_id: str,
) -> HitlActionSubmission:
    """One verdict through the submit-only action door (D-IMPL-62).

    The door claims nothing through ``remove``, so the transport stamps the
    recorded submission with no answered class — and the gate stays pending,
    which is what keeps such a submission eligible at all.
    """
    return transport.submit(
        submit_capability(
            tenant=tenant, principal=subject_id, event_key=event_key
        ),
        submission=HitlActionSubmission(
            event_key=event_key,
            action=action,
            principal=_binding(product_content_hash, subject_id=subject_id),
        ),
    )


def _suspended_covenant(
    registry: ControlPlaneRegistry, tmp_path: Path, *, execution_id: str
) -> tuple[WorkflowEngine, InMemoryHitlTransport, Workflow, str, str]:
    """A covenant workflow suspended on its gate, with the bound hash."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(
        engine.execute(
            execute_as(workflow), workflow, execution_id=execution_id
        )
    )
    assert isinstance(suspended, WorkflowSuspended)
    tenant = workflow.definition.tenant
    pending = next(
        event
        for event in transport.pending(tenant=tenant)
        if event.event_key == suspended.event_key
    )
    return (
        engine,
        transport,
        workflow,
        suspended.event_key,
        pending.product_content_hash,
    )


def test_a_later_rejection_is_not_discarded_when_an_approval_came_first(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """D-IMPL-357 A4, the measured attack. Selection took the OLDEST
    qualifying submission, so a rejection recorded *after* an approval was
    silently discarded and the approving decision then agreed with the
    approval's declared route. Measured over the served door before this
    guard: HTTP 200, terminal state ``approved``, with the rejection
    standing.

    The order is the load-bearing half of this test: with the approval
    first, A3's routing compare is SATISFIED — the authority is the
    approval, its declared route is the decision the caller named — so no
    earlier guard can produce this refusal, and only the conflict check can.
    """
    engine, transport, workflow, event_key, bound = _suspended_covenant(
        registry, tmp_path, execution_id="exec-1"
    )
    tenant = workflow.definition.tenant
    _submit_only(
        transport, tenant=tenant, event_key=event_key,
        product_content_hash=bound, action="approve", subject_id="officer-1",
    )
    _submit_only(
        transport, tenant=tenant, event_key=event_key,
        product_content_hash=bound, action="reject", subject_id="officer-2",
    )
    outcome = asyncio.run(
        engine.resume(
            resume_as(workflow), workflow, execution_id="exec-1",
            decision="approved",
        )
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    # A distinctive PHRASE from this guard's own refusal, not one common
    # word: four tests in this wave were found able to pass without their
    # subject running, one because the asserted word came from a temp path.
    assert "carries conflicting human verdicts" in outcome.reason
    # Still no enumeration: neither the verdicts nor the targets (remedy 3).
    assert "approve" not in outcome.reason and "reject" not in outcome.reason
    # The gate is untouched: a refusal spends nothing.
    record = registry.state_store.get(WORKFLOW_STATE, f"{tenant}/exec-1")
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "suspended"
    assert record.current_state == "credit-officer-approval"


def test_two_officers_conflicting_verdicts_on_one_suspension_refuse_to_route(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The rejection-first order refuses for the CONFLICT, not by falling back.

    The sibling above records the approval first; this one records the
    rejection first, so between them both arrival orders are pinned. The
    name is the one D-IMPL-357 A4's plan cites.

    With the rejection first, selection would make it the authority and
    A3's routing compare would refuse on its own — so a conflict check
    ordered *after* the compare would leave this shape reported as a
    routing disagreement, which tells the investigator that a caller named
    the wrong transition rather than that two humans disagreed. The
    positive assertion on this guard's own phrase is what pins the
    ordering; the negative assertion is what pins that the routing compare
    did not answer instead.
    """
    engine, transport, workflow, event_key, bound = _suspended_covenant(
        registry, tmp_path, execution_id="exec-1"
    )
    tenant = workflow.definition.tenant
    _submit_only(
        transport, tenant=tenant, event_key=event_key,
        product_content_hash=bound, action="reject", subject_id="officer-2",
    )
    _submit_only(
        transport, tenant=tenant, event_key=event_key,
        product_content_hash=bound, action="approve", subject_id="officer-1",
    )
    outcome = asyncio.run(
        engine.resume(
            resume_as(workflow), workflow, execution_id="exec-1",
            decision="approved",
        )
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    assert "carries conflicting human verdicts" in outcome.reason
    assert "does not agree with the route" not in outcome.reason


def test_agreeing_verdicts_on_one_suspension_still_route(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The control: the refusal is not blanket.

    Two submissions that AGREE carry one distinct verdict, so the conflict
    set has one member and the resumption proceeds exactly as it did
    before. Without this test the guard above could be satisfied by an
    engine that refused every gate resume with more than one submission on
    it — which would break the shipped behavior of a second approver
    (D-23 quorum) recording the same verdict.
    """
    engine, transport, workflow, event_key, bound = _suspended_covenant(
        registry, tmp_path, execution_id="exec-1"
    )
    tenant = workflow.definition.tenant
    for subject in ("officer-1", "officer-2"):
        _submit_only(
            transport, tenant=tenant, event_key=event_key,
            product_content_hash=bound, action="approve", subject_id=subject,
        )
    outcome = asyncio.run(
        engine.resume(
            resume_as(workflow), workflow, execution_id="exec-1",
            decision="approved",
        )
    )
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == "approved"


def test_a_stamped_approval_and_an_unstamped_rejection_refuse_the_resumption(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The stamp race's recorded end state, reproduced deterministically.

    The transport's claim is keyed ``(tenant, event_key)`` and consumed by
    whichever submission for that pair arrives first, so a principal
    holding submit authority can land a verdict in the window an
    ``ApprovalGate`` opens between its ``remove`` and its ``submit``. A
    reviewer raced it for real: **823 of 3000 executions succeeded with
    four attacker threads.** What the race leaves recorded is exactly this
    pair — one STAMPED verdict and one UNSTAMPED opposite verdict bound to
    the same suspension — and that end state is reachable without threads,
    which is why this test has no concurrency in it: resolving through the
    real primitive stamps the approval and consumes the pending event, and
    the rejection submitted afterwards is recorded unstamped.

    **This is the shape the authority predicate cannot see.** The
    unstamped rejection fails the unstamped leg (the gate is no longer
    pending) and so does not qualify at all, leaving a one-member verdict
    set. That is why conflict detection reads a BROADER population than
    authority selection: every gate-action submission bound to this
    suspension, stamped or not, eligible or not.

    No served door can produce a stamped submission — ``POST
    /hitl/actions`` is submit-only by D-IMPL-62 and claims nothing — so the
    stamped leg necessarily comes from the primitive, in process.
    """
    engine, transport, workflow, event_key, bound = _suspended_covenant(
        registry, tmp_path, execution_id="exec-1"
    )
    tenant = workflow.definition.tenant
    _resolve_gate(
        registry, transport, tenant=tenant, event_key=event_key,
        action="approve", subject_id="officer-1",
    )
    recorded = transport.submissions(tenant=tenant)
    assert [s.answered_event_class for s in recorded] == [GATE_EVENT_CLASS]
    assert transport.pending(tenant=tenant) == ()  # the claim is consumed
    _submit_only(
        transport, tenant=tenant, event_key=event_key,
        product_content_hash=bound, action="reject", subject_id="officer-2",
    )
    # The rejection really is the shape the authority predicate drops.
    unstamped = transport.submissions(tenant=tenant)[-1]
    assert unstamped.action == "reject"
    assert unstamped.answered_event_class is None
    outcome = asyncio.run(
        engine.resume(
            resume_as(workflow), workflow, execution_id="exec-1",
            decision="approved",
        )
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    assert "carries conflicting human verdicts" in outcome.reason


def test_a_verdict_bound_to_another_suspension_does_not_freeze_this_gate(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The suspension hash is load-bearing in the conflict predicate too.

    Both populations A4 reads keep ``principal.product_content_hash ==
    content_hash(record)``. Dropping it from the conflict population would
    over-refuse — and not harmlessly: any principal holding submit
    authority for the event could then park a contradicting verdict bound
    to some other content and FREEZE the gate permanently, because nothing
    the legitimate approver does can remove a recorded submission. A
    denial-of-service on approvals is the mirror image of the vulnerability
    this task closes, so the term is pinned rather than assumed.

    The foreign binding here is a real suspension hash — another
    execution's — reached through the same event key, which is what makes
    it the honest analogue of a stale verdict from an earlier suspension of
    this same gate.
    """
    engine, transport, workflow, event_key, bound = _suspended_covenant(
        registry, tmp_path, execution_id="exec-1"
    )
    tenant = workflow.definition.tenant
    other = asyncio.run(
        engine.execute(execute_as(workflow), workflow, execution_id="exec-2")
    )
    assert isinstance(other, WorkflowSuspended)
    foreign = registry.state_store.get(WORKFLOW_STATE, f"{tenant}/exec-2")
    assert isinstance(foreign, WorkflowStateRecord)
    foreign_hash = content_hash(foreign)
    assert foreign_hash != bound  # a suspension's identity is its own
    _submit_only(
        transport, tenant=tenant, event_key=event_key,
        product_content_hash=bound, action="approve", subject_id="officer-1",
    )
    # exec-1's event key, exec-2's suspension: bound to no suspension of
    # this gate, so it is neither eligible nor a conflict.
    _submit_only(
        transport, tenant=tenant, event_key=event_key,
        product_content_hash=foreign_hash, action="reject",
        subject_id="officer-2",
    )
    outcome = asyncio.run(
        engine.resume(
            resume_as(workflow), workflow, execution_id="exec-1",
            decision="approved",
        )
    )
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == "approved"


def test_an_annotation_and_an_override_beside_an_approval_still_route(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The verdict-VOCABULARY term in the conflict predicate is load-bearing.

    ``HITL_ACTIONS`` is ``{approve, reject, override, annotate}`` and only
    the first two are ``GATE_ACTIONS``. Dropping ``action in GATE_ACTIONS``
    from :meth:`_recorded_gate_verdicts` left every test in
    ``tests/workflow`` and ``tests/http_api/test_routes.py`` green, so
    nothing pinned it — measured by review, and this is the control that
    closes that hole.

    The failure direction is why it went unnoticed: without the term an
    annotation or an override bound to this suspension counts as a distinct
    verdict, so the gate REFUSES rather than routing wrongly. That is
    over-refusal, not bypass — and it is still a denial of service on
    approvals, which is the mirror image of the vulnerability A4 closes, and
    the same argument the suspension-hash control rests on.

    Three submissions on one suspension and only one of them a verdict, so
    the conflict set has exactly one member and the resumption proceeds.
    """
    engine, transport, workflow, event_key, bound = _suspended_covenant(
        registry, tmp_path, execution_id="exec-1"
    )
    tenant = workflow.definition.tenant
    _submit_only(
        transport, tenant=tenant, event_key=event_key,
        product_content_hash=bound, action="approve", subject_id="officer-1",
    )
    for action in ("annotate", "override"):
        _submit_only(
            transport, tenant=tenant, event_key=event_key,
            product_content_hash=bound, action=action,
            subject_id="reviewer-1",
        )
    # All three really are recorded against this suspension: the predicate
    # has to discriminate on the ACTION, not on anything else being absent.
    recorded = [
        submission
        for submission in transport.submissions(tenant=tenant)
        if submission.event_key == event_key
        and submission.principal.product_content_hash == bound
    ]
    assert [submission.action for submission in recorded] == [
        "approve",
        "annotate",
        "override",
    ]
    outcome = asyncio.run(
        engine.resume(
            resume_as(workflow), workflow, execution_id="exec-1",
            decision="approved",
        )
    )
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == "approved"


def test_a_conflicting_verdict_refusal_is_a_distinct_audited_record(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """D-IMPL-357 A4. A verdict-integrity refusal is findable in the log.

    Before this, every resume refusal audited identically — same
    ``workflow_resumed`` action, ``resolved=False``, ``actor=None``, no
    reason on the event — so the one refusal a bank's investigator would
    search for was byte-identical to a caller's typo. The refusal PROSE
    still names neither verdict nor target (SEC-001 remedy 3); the audit
    plane is a different reader, and this is where the fact lands.

    The negative half is the load-bearing half: a refusal the caller's own
    request produced must NOT claim a verdict-integrity rule, or the
    distinction the class exists to draw is gone again. Asserted here with
    the undeclared-decision refusal on the same suspension.
    """
    engine, transport, workflow, event_key, bound = _suspended_covenant(
        registry, tmp_path, execution_id="exec-1"
    )
    tenant = workflow.definition.tenant
    _submit_only(
        transport, tenant=tenant, event_key=event_key,
        product_content_hash=bound, action="approve", subject_id="officer-1",
    )
    _submit_only(
        transport, tenant=tenant, event_key=event_key,
        product_content_hash=bound, action="reject", subject_id="officer-2",
    )
    assert isinstance(
        asyncio.run(
            engine.resume(
                resume_as(workflow), workflow, execution_id="exec-1",
                decision="approved",
            )
        ),
        WorkflowResumeRefused,
    )
    refusals = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed" and not event.resolved
    ]
    assert len(refusals) == 1
    recorded = refusals[-1]
    assert isinstance(recorded, WorkflowVerdictIntegrityAuditEvent)
    assert recorded.workflow_verdict_integrity == "conflicting_verdicts"
    # The approver at the head of the eligible verdicts — the actor the
    # resumption would have been attributed to had it proceeded — rather
    # than nothing. Not the only party: by construction another human
    # recorded the contradicting verdict, which the member itself says.
    assert recorded.workflow_recorded_approver == "officer-1"
    assert recorded.actor == "officer-1"
    # A refusal the CALLER produced claims no verdict-integrity rule. On a
    # SECOND execution, because on exec-1 the conflict check is ordered
    # ahead of the declared-target check and answers first — which is
    # itself the ordering the sibling tests pin.
    second = asyncio.run(
        engine.execute(execute_as(workflow), workflow, execution_id="exec-2")
    )
    assert isinstance(second, WorkflowSuspended)
    second_bound = next(
        event
        for event in transport.pending(tenant=tenant)
        if event.event_key == second.event_key
    ).product_content_hash
    _submit_only(
        transport, tenant=tenant, event_key=second.event_key,
        product_content_hash=second_bound, action="approve",
        subject_id="officer-1",
    )
    plain = asyncio.run(
        engine.resume(
            resume_as(workflow), workflow, execution_id="exec-2",
            decision="no-such-transition",
        )
    )
    assert isinstance(plain, WorkflowResumeRefused)
    caller_refusal = [
        event
        for event in registry.audit_log.events()
        if event.action == "workflow_resumed" and not event.resolved
    ][-1]
    assert not isinstance(
        caller_refusal, WorkflowVerdictIntegrityAuditEvent
    )
    assert type(caller_refusal) is AuditEvent
    assert caller_refusal.actor is None

# --- SEC-005: the signed attestation covers the verdict (`D-IMPL-363`) --------

#: This test-as-deployment's own vocabulary (CINV-01): the signing key it
#: writes, the Control Plane key it binds its HITL policy under, the approver
#: whose subject the key is declared for, and the window the pinned policy
#: states. The window values are the deployment's statement, never an SDK
#: default — a required policy that omits them is refused at parse
#: (`D-IMPL-363` E3).
_SIGNING_KID = "hitl-approver-signing-key"
_HITL_POLICY_KEY = "acme-bank/hitl/policy"
_SIGNING_SUBJECT = "officer-2"
_MAX_AGE_SECONDS = 300
_SKEW_SECONDS = 60


def _signed_path(
    registry: ControlPlaneRegistry,
    tmp_path: Path,
    *,
    subject_id: str = _SIGNING_SUBJECT,
) -> tuple[InMemoryHitlTransport, DetachedJwsIdentityProvider, HitlPolicy]:
    """A transport on the SIGNED path — the policy in force requires an attestation.

    Requiredness is a Control Plane value and defaults to false
    (``HitlPolicy.signed_binding_required``), so a deployment that has NOT
    turned signing on gets no signature over anything and SEC-005 says nothing
    about it. This harness turns it ON, which is the only posture in which the
    finding bites: a deployment entitled to believe it obtained
    non-repudiation.

    **The trust source is the pinned policy and nothing else** (`D-IMPL-363`
    E5 / C6(a)): the window and the per-subject ``trusted_keys`` live INSIDE
    the registered :class:`HitlPolicy` document, and the transport takes no
    ``trusted_keys`` argument any more. The policy object is returned because
    the shared verifier judges an attestation against it directly.
    """
    keys = tmp_path / "hitl-keys"
    keys.mkdir()
    key = ECKey.generate_key("P-256", parameters={"kid": _SIGNING_KID})
    (keys / f"{_SIGNING_KID}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    policy = parse_artifact(
        {
            "semver": "1.0.0",
            "signed_binding_required": True,
            "signature_max_age_seconds": _MAX_AGE_SECONDS,
            "permitted_clock_skew_seconds": _SKEW_SECONDS,
            "trusted_keys": {subject_id: {_SIGNING_KID: key.as_dict(private=False)}},
        },
        HITL_POLICY,
    )
    assert isinstance(policy, HitlPolicy)
    register_typed_at_composition(registry, _HITL_POLICY_KEY, policy, HITL_POLICY)
    provider = DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=keys)
    )
    transport = InMemoryHitlTransport(
        control_plane=registry,
        hitl_policy_key=_HITL_POLICY_KEY,
        identity_provider=provider,
    )
    return transport, provider, policy


def test_an_attestation_signed_to_reject_cannot_be_presented_as_an_approval(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-005, closed by `D-IMPL-363`: the signature covers WHAT THEY DECIDED,
    so one valid signature authorizes exactly one verdict.

    The finding this replaces: ``HumanPrincipalBinding`` carries the four
    `D-IMPL-21` fields — approver, authentication, action time, product content
    hash — and the retired ``sign_principal_binding`` signed precisely those.
    The verdict was not among them, so a signature made to REJECT verified
    unchanged beside ``action="approve"``. Under `D-IMPL-363` the signed object
    is :class:`HitlActionClaims`, whose ``action`` IS a signed claim, and
    :func:`enforce_attestation` compares it to both the presented action and
    the door-minted binding's ``verdict`` (E1, C1(a)).

    THE STRONGEST FORGER, not a stub: the attacker swaps BOTH unsigned halves
    — the presented ``action`` and the unsigned binding's ``verdict`` — so the
    only thing still saying ``reject`` is the signed claim set. A verifier that
    compared the two unsigned halves to each other would agree with the forgery.

    WHY THE ROUTE FREEZE DOES NOT REACH THIS. `ece2ae2d` froze ``gate_routes``
    so a write cannot retarget a verdict. Here the map is untouched and the
    VERDICT ITSELF is forged, so the route compare agrees with it and the
    resume would be regular. Wave 1's ``conflicting_verdicts`` cross-check does
    not reach it either: that refuses only when two DISTINCT verdicts are
    recorded against one suspension, and here the genuine rejection is never
    submitted — only the swap is.

    BOTH FACTS ARE GATHERED BEFORE ANYTHING IS ASSERTED, so one failing run
    reports the whole chain rather than stopping at its first link. The
    mechanism assertions come first and pin the signature's scope directly —
    with a POSITIVE CONTROL (the same attestation presented honestly is
    admitted) so the refusal cannot be an attestation that never verified at
    all. The two outcome assertions alone would be satisfied by whichever
    guard in ``resume`` happened to fire; they are kept because they are the
    property the retired test pinned: a swapped verdict never reaches the
    approving terminal.
    """
    transport, provider, policy = _signed_path(registry, tmp_path)
    engine, _, _ = _engine(registry, tmp_path, transport=transport)
    workflow = _covenant(registry)
    tenant = workflow.definition.tenant
    suspended = asyncio.run(
        engine.execute(execute_as(workflow), workflow, execution_id="exec-1")
    )
    assert isinstance(suspended, WorkflowSuspended)

    pending = next(
        event
        for event in transport.pending(tenant=tenant)
        if event.event_key == suspended.event_key
    )
    # What the approver actually stated and signed: a REJECTION of exactly
    # this event, at the instant the door went on to record (`_binding`'s
    # ``action_time`` is fixed, so the freshness window is deterministic and
    # no wall clock is read on this path).
    honest_claims = HitlActionClaims(
        tenant=tenant,
        event_key=suspended.event_key,
        action="reject",
        product_content_hash=pending.product_content_hash,
        subject_id=_SIGNING_SUBJECT,
        issued_at=datetime(2026, 7, 30, 12, tzinfo=UTC),
        nonce="t13-nonce-0001",
    )
    signed = sign_hitl_action(
        honest_claims, provider=provider, key_id=_SIGNING_KID
    )
    capability = submit_capability(
        tenant=tenant,
        principal=_SIGNING_SUBJECT,
        event_key=suspended.event_key,
    )

    def _submission(verdict: str) -> HitlActionSubmission:
        """The submission as a presenter composes it: the attestation verbatim,
        beside an UNSIGNED binding and action the presenter chose."""
        return HitlActionSubmission(
            event_key=suspended.event_key,
            action=verdict,
            principal=_binding(
                pending.product_content_hash,
                subject_id=_SIGNING_SUBJECT,
                verdict=verdict,
            ),
            attestation=signed,
        )

    # POSITIVE CONTROL: presented as signed, the attestation is admitted. The
    # verifier consumes no nonce (`D-IMPL-363` E4), so this leaves the signed
    # path and the pending event untouched for the swap below.
    honest_verified: object
    try:
        honest_verified = enforce_attestation(
            capability,
            _submission("reject"),
            identity_provider=provider,
            policy=policy,
        )
    except PermissionError as refused:
        honest_verified = refused

    # THE SWAP: the approver signed intending to REJECT. Both unsigned halves
    # now say "approve"; the signed claims are untouched.
    record = registry.state_store.get(WORKFLOW_STATE, f"{tenant}/exec-1")
    assert isinstance(record, WorkflowStateRecord)
    gate = record.current_state
    approving = workflow.definition.gate_routes[gate]["approve"]
    swap_refusal: object = None
    try:
        enforce_attestation(
            capability,
            _submission("approve"),
            identity_provider=provider,
            policy=policy,
        )
    except SignedBindingMismatchRefused as refused:
        swap_refusal = refused

    # Wrapped for the reason the null-identity control is wrapped: a regression
    # that starts ADMITTING must not abort before the assertions are reached.
    # The gate invokes the same shared helper, so the refusal surfaces here too
    # and not only at `enforce_attestation`.
    swapped: object
    try:
        swapped = ApprovalGate(
            transport=transport,
            audit=registry.audit_log,
            clock=_ticking_clock(),
            control_plane=registry,
            hitl_policy_key=_HITL_POLICY_KEY,
            identity_provider=provider,
        ).resolve(
            capability,
            event_key=suspended.event_key,
            action="approve",
            principal=_binding(
                pending.product_content_hash,
                subject_id=_SIGNING_SUBJECT,
                verdict="approve",
            ),
            attestation=signed,
        )
    except SignedBindingMismatchRefused as refused:
        swapped = refused
    outcome: object | None = None
    if isinstance(swapped, GateResolution):
        outcome = asyncio.run(
            engine.resume(
                resume_as(workflow),
                workflow,
                execution_id="exec-1",
                decision=approving,
            )
        )
    after = registry.state_store.get(WORKFLOW_STATE, f"{tenant}/exec-1")
    assert isinstance(after, WorkflowStateRecord)

    assert isinstance(honest_verified, HitlActionClaims), (
        "the POSITIVE CONTROL failed: the attestation presented exactly as it"
        " was signed was not admitted"
        f" ({type(honest_verified).__name__}: {honest_verified}), so the"
        " refusal below would prove nothing about the verdict"
    )
    assert honest_verified.action == "reject"
    assert isinstance(swap_refusal, SignedBindingMismatchRefused), (
        "an attestation signed over action='reject' was presented as"
        " action='approve' and `enforce_attestation` did not refuse it as a"
        f" mismatch (got {type(swap_refusal).__name__}), so the signature"
        " authorizes a decision the approver never made; the swapped gate"
        f" resolution was {type(swapped).__name__} and the execution reached"
        f" {after.status!r} at {after.current_state!r}"
    )
    assert isinstance(swapped, SignedBindingMismatchRefused), (
        "`ApprovalGate.resolve` admitted the swapped verdict even though the"
        " shared verifier refuses it; SOMEWHERE on the authority path the"
        " refusal has to surface (the gate's own pre-consumption verification"
        " or the transport's at submit — D-13's idempotent double"
        f" verification, and this composition has both) (got {type(swapped).__name__}).\n"
        " Which of the two fired is pinned separately by"
        " `test_the_approval_gate_verifies_the_attestation_independently_of_the_transport`."
    )
    assert not isinstance(outcome, WorkflowCompleted), (
        "the workflow COMPLETED on a verdict carried by a signature that never"
        f" covered it (terminal {after.current_state!r})"
    )
    assert after.current_state != approving, (
        f"the execution advanced to the approving terminal {approving!r} on a"
        " swapped verdict"
    )
    # The refused resolution consumed nothing: the event is still pending for
    # a genuine rejection to answer (Pitfall 4 doctrine).
    assert suspended.event_key in {
        event.event_key for event in transport.pending(tenant=tenant)
    }
    assert transport.submissions(tenant=tenant) == ()


def test_the_approval_gate_verifies_the_attestation_independently_of_the_transport(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """D-13 / D-IMPL-69: the gate's verification is its OWN, not the transport's.

    T13 above runs with both halves bound, which is the real deployment shape
    — and is exactly why it cannot say WHICH half refused: with the gate's
    binding removed, the transport still refuses at ``submit`` and
    ``resolve`` still raises. Measured: unbinding the gate left T13 green.

    So this control removes the OTHER half. The transport is bound to no
    Control Plane and so verifies nothing; the gate alone holds the policy
    key. If the gate did not verify independently, the swap would be
    admitted, recorded, and returned as a :class:`GateResolution` — no trust
    marker crosses the layer seam in either direction (D-13), so each layer
    has to do the work itself.
    """
    _, provider, policy = _signed_path(registry, tmp_path)
    # Deliberately unbound: this transport resolves no policy and therefore
    # performs no verification of its own.
    unverifying = InMemoryHitlTransport()
    engine, _, _ = _engine(registry, tmp_path, transport=unverifying)
    workflow = _covenant(registry)
    tenant = workflow.definition.tenant
    suspended = asyncio.run(
        engine.execute(execute_as(workflow), workflow, execution_id="exec-1")
    )
    assert isinstance(suspended, WorkflowSuspended)
    pending = next(
        event
        for event in unverifying.pending(tenant=tenant)
        if event.event_key == suspended.event_key
    )
    signed = sign_hitl_action(
        HitlActionClaims(
            tenant=tenant,
            event_key=suspended.event_key,
            action="reject",
            product_content_hash=pending.product_content_hash,
            subject_id=_SIGNING_SUBJECT,
            issued_at=datetime(2026, 7, 30, 12, tzinfo=UTC),
            nonce="t13-independent-nonce-0001",
        ),
        provider=provider,
        key_id=_SIGNING_KID,
    )
    gate = ApprovalGate(
        transport=unverifying,
        audit=registry.audit_log,
        clock=_ticking_clock(),
        control_plane=registry,
        hitl_policy_key=_HITL_POLICY_KEY,
        identity_provider=provider,
    )
    resolved: object
    try:
        resolved = gate.resolve(
            submit_capability(
                tenant=tenant,
                principal=_SIGNING_SUBJECT,
                event_key=suspended.event_key,
            ),
            event_key=suspended.event_key,
            action="approve",
            principal=_binding(
                pending.product_content_hash,
                subject_id=_SIGNING_SUBJECT,
                verdict="approve",
            ),
            attestation=signed,
        )
    except SignedBindingMismatchRefused as refused:
        resolved = refused
    assert isinstance(resolved, SignedBindingMismatchRefused), (
        "the gate admitted a swapped verdict that only IT could have caught:"
        " the transport beneath it is bound to no Control Plane and verifies"
        f" nothing (got {type(resolved).__name__})"
    )
    # Pre-consumption, as D-IMPL-69 requires: nothing was claimed, nothing
    # was recorded, the event is still answerable.
    assert unverifying.submissions(tenant=tenant) == ()
    assert suspended.event_key in {
        event.event_key for event in unverifying.pending(tenant=tenant)
    }
    # The positive side of the same seam: the SAME attestation presented
    # honestly passes the gate's verification, so the refusal above is the
    # verdict and not the wiring.
    honest = gate.resolve(
        submit_capability(
            tenant=tenant,
            principal=_SIGNING_SUBJECT,
            event_key=suspended.event_key,
        ),
        event_key=suspended.event_key,
        action="reject",
        principal=_binding(
            pending.product_content_hash,
            subject_id=_SIGNING_SUBJECT,
            verdict="reject",
        ),
        attestation=signed,
    )
    assert isinstance(honest, GateResolution), honest
    assert honest.outcome.approved is False
    assert honest.record.submission.action == "reject"
    assert honest.record.submission.attestation == signed
