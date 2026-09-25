"""The `OrchestrationProtocol` conformance suite — the bar for every driver.

D-IMPL-60 (three driver legs, one factory-parametrized suite) and D-IMPL-17
(identical replay obligations for external orchestrators). The doctrine this
suite enforces structurally, quoted from the Protocol module: the isinstance
target is drivers and the in-SDK reference adapter, never the bare engine —
the engine is the authority the Protocol drives, not a third peer harness.

The shape mirrors ``test_harness_adapter.py`` deliberately: a per-leg
NamedTuple bundling a factory plus leg-specific drivers, so shared test
bodies never name an SDK type; skips are visible and self-explaining, naming
the SDK and the extra that enables it; and ``CCF_REQUIRE_HARNESSES=1`` turns
an absent-SDK skip into a failure. 07-13 adds the ADK and Claude legs as
params without changing a single test body — the constraint every assertion
here is written under.

Everything domain-specific — the payment-release workflow, its task, its
gate policy, the approvers — comes from ``tests/fixtures/banking``. This
module holds mechanism only (CLAUDE.md §6.4).

**The capability crosses the seam (D-IMPL-353 §1.2).** Every leg's
``start_execution``/``resume_execution`` takes the ``Authorized`` for its own
verb and hands it to the engine, which verifies it; the leg mints nothing
and holds it in no field. The shared bodies here mint through the real
``mint`` (``tests.workflow.capabilities``) and pass it through, and two
tests assert the negative space: a wrong-kind capability reaches no engine
state through any leg, and no driver retains a capability after a drive.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

import pytest
import yaml
from _pytest.outcomes import Failed, Skipped

from ccf.agents.definitions import TASK_DEFINITION, TaskDefinition
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.approval_gate import ApprovalGate, GateResolution
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.orchestration.protocol import OrchestrationProtocol
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from ccf.workflow.factory import Workflow, WorkflowFactory
from ccf_runtime.orchestration import SegmentNotExecutedError
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from conftest import HARNESS_REQUIRED_ENV, harness_unavailable

from ccf.authz.capability import Authorized, CapabilityBypassError, Execute
from tests.workflow.capabilities import (
    execute_as,
    execute_capability,
    resume_as,
)

pytestmark = [pytest.mark.conformance]

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"

#: A module name no extra installs, driving the skip mechanism's real code
#: path — the same discipline as the harness suite's ``ABSENT_HARNESS``.
ABSENT_SDK = "ccf_no_such_orchestrator_sdk"


def _load(relative: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((FIXTURES / relative).read_text())
    return loaded


def _ticking_clock() -> Callable[[], datetime]:
    """Deterministic injected clock — replay equivalence depends on it."""
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


class World:
    """One Control Plane, one engine, one real gate — a fresh world per leg.

    Fresh worlds with identical injected clocks are what make the
    replay-equivalence comparison canonical-bytes-based rather than
    modulo-anything: two legs driving the same engine surface consume the
    same ticks, so equal obligations produce equal bytes.
    """

    def __init__(self, tmp_path: Path) -> None:
        self.registry = ControlPlaneRegistry(clock=_ticking_clock())
        task_fixture = _load("tasks/payment_release_task.yaml")
        _register_declared(self.registry, task_fixture["referenced_artifacts"])
        task = parse_artifact(task_fixture["task_definition"], TASK_DEFINITION)
        assert isinstance(task, TaskDefinition)
        workflow_fixture = _load("workflows/payment_release_workflow.yaml")
        self.registry.register_versioned(
            workflow_fixture["keys"]["task_definition"], task, TASK_DEFINITION
        )
        _register_declared(
            self.registry, workflow_fixture["referenced_artifacts"]
        )
        self.transport = InMemoryHitlTransport()
        self.bindings = _Bindings()
        self.engine = WorkflowEngine(
            control_plane=self.registry,
            artifact_store=FileArtifactStore(root=tmp_path / "artifacts"),
            hitl_transport=self.transport,
            skill_binding=self.bindings,
            agent_binding=self.bindings,
            clock=_ticking_clock(),
        )
        self.gate = ApprovalGate(
            transport=self.transport,
            audit=self.registry.audit_log,
            clock=_ticking_clock(),
        )

    def workflow(self, **mutations: Any) -> Workflow:
        fixture = _load("workflows/payment_release_workflow.yaml")
        document = fixture["workflow_definition"]
        document.update(mutations)
        definition = parse_artifact(document, WORKFLOW_DEFINITION)
        assert isinstance(definition, WorkflowDefinition)
        key = fixture["keys"]["workflow_definition"]
        if mutations:
            key = f"{definition.tenant}/workflows/{definition.name}"
        version = self.registry.register_versioned(
            key, definition, WORKFLOW_DEFINITION
        )
        assert isinstance(version, str)
        return WorkflowFactory(control_plane=self.registry).construct(
            execute_capability(tenant=definition.tenant, resource=key),
            definition_version=version,
        )

    def approve(self, suspended: WorkflowSuspended) -> GateResolution:
        """The human action, through the REAL gate — outside the driver.

        The driver's business is driving the engine; the approval is the
        HITL pillar's, and it travels the same gate whichever leg drove the
        suspension. That equality is part of "identical replay obligations".
        """
        (pending,) = [
            event
            for event in self.transport.pending(tenant=suspended.tenant)
            if event.event_key == suspended.event_key
        ]
        approver = _load("hitl.yaml")["approvers"]["credit_officer"]
        resolution = self.gate.resolve(
            tenant=suspended.tenant,
            event_key=suspended.event_key,
            action="approve",
            principal=HumanPrincipalBinding(
                approver=ApproverIdentity(**approver["identity"]),
                authentication=AuthenticationContext(
                    **approver["authentication"]
                ),
                action_time=datetime.fromisoformat(approver["action_time"]),
                product_content_hash=pending.product_content_hash,
            ),
        )
        assert isinstance(resolution, GateResolution)
        return resolution


# --- the parametrized leg -----------------------------------------------------

#: Builds the driver under test over the world's engine. The engine is an
#: argument, never something the leg constructs: the CCF engine stays the
#: authority for state and audit, and the driver merely drives it.
DriverFactory = Callable[[WorkflowEngine], OrchestrationProtocol]

#: Leg-specific introspection of the orchestrator's own persisted position
#: for one execution — ``(driver, tenant, execution_id)``, the tenant being
#: the capability's, which is the engine's key (§1.3) — or ``None`` for a
#: leg with no external position to hold (the in-SDK reference adapter).
#: Returns every value the orchestrator persisted, so the shared body can
#: assert that none of it is CCF workflow state — the checkpointer holds
#: graph position only (T-07-30).
PositionProbe = Callable[[OrchestrationProtocol, str, str], tuple[object, ...]]


class OrchestrationLeg(NamedTuple):
    """One orchestrator SDK's entry into the suite (D-IMPL-60)."""

    leg_id: str
    driver: DriverFactory
    positions: PositionProbe | None


#: Every driver leg, reference first. 07-13 appended "adk" and "claude-agent".
ORCHESTRATION_PARAMS = ("in-sdk", "langgraph", "adk", "claude-agent")


def build_orchestration_leg(param: str) -> OrchestrationLeg:
    if param == "in-sdk":
        from ccf_runtime.orchestration.reference import (
            WorkflowEngineOrchestrationAdapter,
        )

        return OrchestrationLeg(
            leg_id=param,
            driver=lambda engine: WorkflowEngineOrchestrationAdapter(
                engine=engine
            ),
            positions=None,
        )
    if param == "langgraph":
        harness_unavailable("langgraph", param)

        from ccf_runtime.orchestration.langgraph.driver import (
            LangGraphWorkflowDriver,
        )

        def positions(
            driver: OrchestrationProtocol, tenant: str, execution_id: str
        ) -> tuple[object, ...]:
            assert isinstance(driver, LangGraphWorkflowDriver)
            return driver.checkpointed_values(
                tenant=tenant, execution_id=execution_id
            )

        return OrchestrationLeg(
            leg_id=param,
            driver=lambda engine: LangGraphWorkflowDriver(engine=engine),
            positions=positions,
        )
    if param == "adk":
        harness_unavailable("google.adk", param)

        from ccf_runtime.orchestration.adk.driver import AdkWorkflowDriver

        def adk_positions(
            driver: OrchestrationProtocol, tenant: str, execution_id: str
        ) -> tuple[object, ...]:
            assert isinstance(driver, AdkWorkflowDriver)
            return driver.persisted_state(
                tenant=tenant, execution_id=execution_id
            )

        return OrchestrationLeg(
            leg_id=param,
            driver=lambda engine: AdkWorkflowDriver(engine=engine),
            positions=adk_positions,
        )
    if param == "claude-agent":
        harness_unavailable("claude_agent_sdk", param)

        from ccf_runtime.orchestration.claude_agent.driver import (
            ClaudeAgentWorkflowDriver,
        )

        def claude_positions(
            driver: OrchestrationProtocol, tenant: str, execution_id: str
        ) -> tuple[object, ...]:
            assert isinstance(driver, ClaudeAgentWorkflowDriver)
            return driver.session_transcript(
                tenant=tenant, execution_id=execution_id
            )

        return OrchestrationLeg(
            leg_id=param,
            driver=lambda engine: ClaudeAgentWorkflowDriver(engine=engine),
            positions=claude_positions,
        )
    raise NotImplementedError(param)


@pytest.fixture(params=ORCHESTRATION_PARAMS)
def leg(request: pytest.FixtureRequest) -> OrchestrationLeg:
    return build_orchestration_leg(request.param)


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


# --- the suite's own guarantees ----------------------------------------------


def test_an_absent_orchestrator_sdk_skips_with_an_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The skip names the SDK and the extra that enables it — visibly."""
    monkeypatch.delenv(HARNESS_REQUIRED_ENV, raising=False)
    with pytest.raises(Skipped) as skipped:
        harness_unavailable(ABSENT_SDK, ABSENT_SDK)
    message = str(skipped.value)
    assert ABSENT_SDK in message
    assert "pip install -e" in message


def test_an_absent_orchestrator_sdk_fails_when_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CCF_REQUIRE_HARNESSES=1 machinery, reused rather than reinvented."""
    monkeypatch.setenv(HARNESS_REQUIRED_ENV, "1")
    with pytest.raises(Failed) as failed:
        harness_unavailable(ABSENT_SDK, ABSENT_SDK)
    assert HARNESS_REQUIRED_ENV in str(failed.value)
    assert not isinstance(failed.value, Skipped)


# --- structural conformance (Task 1) ------------------------------------------


def test_the_driver_conforms_to_the_protocol_structurally(
    leg: OrchestrationLeg, world: World
) -> None:
    """The isinstance target is the driver — never the bare engine."""
    assert isinstance(leg.driver(world.engine), OrchestrationProtocol)


def test_the_bare_engine_is_not_the_isinstance_target(world: World) -> None:
    """The doctrine sentence, made structural: the engine is the authority
    the Protocol drives, not a third peer harness — and it does not satisfy
    the Protocol, so no composition root can wire it in as one."""
    assert not isinstance(world.engine, OrchestrationProtocol)


def test_the_doctrine_sentence_is_written_down() -> None:
    import ccf.orchestration.protocol as module

    assert module.__doc__ is not None
    assert "not a third peer harness" in module.__doc__


def test_the_protocol_methods_are_keyword_only_and_typed() -> None:
    """Factory-built handle in, typed outcomes out, keyword-only throughout."""
    import inspect

    for name in ("start_execution", "resume_execution"):
        signature = inspect.signature(getattr(OrchestrationProtocol, name))
        parameters = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.name != "self"
        ]
        assert parameters, name
        for parameter in parameters:
            assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, name
            assert parameter.annotation is not inspect.Parameter.empty, name
        workflow_parameter = signature.parameters["workflow"]
        assert workflow_parameter.annotation in (Workflow, "Workflow")
        assert signature.return_annotation in (CCFContract, "CCFContract")
        # D-IMPL-353 §1.2: the capability is a parameter of both verbs, typed
        # for that verb's own kind and with no default (§4 refuses one).
        authorized = signature.parameters["authorized"]
        assert authorized.default is inspect.Parameter.empty
        expected = "Authorized[Execute]" if name == "start_execution" else "Authorized[Resume]"
        assert str(authorized.annotation).endswith(expected)


# --- the shared end-to-end body (Task 3) --------------------------------------


def _drive_to_terminal(
    leg: OrchestrationLeg, world: World, workflow: Workflow, execution_id: str
) -> tuple[WorkflowSuspended, WorkflowCompleted]:
    """Suspend on the real gate, approve, resume to terminal — via the leg."""
    driver = leg.driver(world.engine)
    suspended = asyncio.run(
        driver.start_execution(
            authorized=execute_as(workflow),
            workflow=workflow,
            execution_id=execution_id,
        )
    )
    assert isinstance(suspended, WorkflowSuspended)
    world.approve(suspended)
    outcome = asyncio.run(
        driver.resume_execution(
            authorized=resume_as(workflow),
            workflow=workflow,
            execution_id=execution_id,
            decision="released",
        )
    )
    assert isinstance(outcome, WorkflowCompleted)
    return suspended, outcome


def test_the_leg_drives_the_workflow_end_to_end(
    leg: OrchestrationLeg, world: World
) -> None:
    workflow = world.workflow()
    suspended, outcome = _drive_to_terminal(leg, world, workflow, "exec-1")
    assert world.bindings.ran == ["skill:verify-payment"]
    assert suspended.gate == "treasury-approval"
    assert outcome.terminal_state == "released"
    assert outcome.trace_artifact.content_address


def test_the_replay_record_is_equivalent_to_the_reference_legs(
    leg: OrchestrationLeg, tmp_path: Path
) -> None:
    """Identical replay obligations, proven — not asserted (T-07-32).

    Two fresh worlds with identical injected clocks, the same workflow, the
    same execution id: the leg's terminal outcome and the in-SDK reference
    leg's must agree byte-for-byte on everything replay records — the
    dimension-5 step-sequence block, the dimension-4 delegation chain, and
    the terminal state. Canonical-bytes comparison, no modulo needed,
    because nothing nondeterministic is left to differ.
    """
    reference_world = World(tmp_path / "reference")
    _, reference = _drive_to_terminal(
        build_orchestration_leg("in-sdk"),
        reference_world,
        reference_world.workflow(),
        "exec-1",
    )
    leg_world = World(tmp_path / "leg")
    _, outcome = _drive_to_terminal(
        leg, leg_world, leg_world.workflow(), "exec-1"
    )
    assert canonical_bytes(outcome.step_sequence_block) == canonical_bytes(
        reference.step_sequence_block
    )
    assert canonical_bytes(outcome.delegation_chain) == canonical_bytes(
        reference.delegation_chain
    )
    assert outcome.terminal_state == reference.terminal_state
    assert (
        outcome.trace_artifact.content_address
        == reference.trace_artifact.content_address
    )


def test_the_ccf_engine_stays_authoritative_for_suspended_state(
    leg: OrchestrationLeg, world: World
) -> None:
    """T-07-30: the suspended WorkflowStateRecord is on the Control Plane
    store; whatever position the orchestrator persisted holds no CCF
    workflow state — graph position only."""
    workflow = world.workflow()
    driver = leg.driver(world.engine)
    suspended = asyncio.run(
        driver.start_execution(
            authorized=execute_as(workflow), workflow=workflow, execution_id="exec-1"
        )
    )
    assert isinstance(suspended, WorkflowSuspended)
    key = f"{suspended.tenant}/exec-1"  # the capability's tenant (§1.3)
    record = world.registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "suspended"
    if leg.positions is not None:
        persisted = leg.positions(driver, suspended.tenant, "exec-1")
        assert persisted  # the orchestrator did persist a position
        for value in persisted:
            assert not isinstance(value, (WorkflowStateRecord, CCFContract)), (
                "the orchestrator's checkpoint carries CCF workflow state;"
                " the CCF engine is authoritative and the checkpointer holds"
                " graph position only (T-07-30)"
            )
            assert isinstance(value, (str, bool, int)), value


def test_a_never_executed_segment_raises_the_same_typed_error_on_every_leg(
    leg: OrchestrationLeg, world: World
) -> None:
    """D-13(b), WR-03: asking a driver for the outcome of an execution it
    never ran raises :class:`SegmentNotExecutedError` — the SAME type on
    every driver leg, never a bare ``KeyError``. The in-SDK reference
    adapter holds no outcome store of its own (``positions is None``), so
    the assertion runs where a driver actually holds ``_outcomes``."""
    if leg.positions is None:
        pytest.skip("in-sdk reference adapter holds no outcome store")
    driver = leg.driver(world.engine)
    tenant = execute_as(world.workflow()).tenant
    with pytest.raises(SegmentNotExecutedError) as raised:
        driver._outcome(tenant, "never-ran")  # type: ignore[attr-defined]
    assert not isinstance(raised.value, KeyError)
    assert "never-ran" in str(raised.value)
    assert tenant in str(raised.value)


def test_the_introspection_seam_is_loop_safe(
    leg: OrchestrationLeg, world: World
) -> None:
    """D-13(c), WR-03: each leg's sync introspection seam works both from a
    plain sync context and from inside ``asyncio.run``-hosted coroutine
    code — no nested-run ``RuntimeError`` — and returns equivalent state
    (exercising the ADK session service's cross-loop read, A1)."""
    if leg.positions is None:
        pytest.skip("in-sdk reference adapter holds no outcome store")
    workflow = world.workflow()
    driver = leg.driver(world.engine)
    suspended = asyncio.run(
        driver.start_execution(
            authorized=execute_as(workflow), workflow=workflow, execution_id="exec-1"
        )
    )
    assert isinstance(suspended, WorkflowSuspended)
    probe = leg.positions
    from_sync = probe(driver, suspended.tenant, "exec-1")

    async def hosted() -> tuple[object, ...]:
        # The probe call happens while THIS loop runs in THIS thread —
        # exactly the WR-03 defect scenario the fix removes.
        return probe(driver, suspended.tenant, "exec-1")

    from_inside_a_loop = asyncio.run(hosted())
    assert from_sync  # the orchestrator did persist a position
    assert from_inside_a_loop == from_sync


def test_two_tenants_do_not_collide_through_the_leg(
    leg: OrchestrationLeg, world: World
) -> None:
    """(tenant, execution_id) keying holds across the driver seam (D-23)."""
    driver = leg.driver(world.engine)
    acme = world.workflow()
    beta = world.workflow(tenant="beta-bank", artifact_version="1.1.0")
    first = asyncio.run(
        driver.start_execution(
            authorized=execute_as(acme), workflow=acme, execution_id="exec-1"
        )
    )
    second = asyncio.run(
        driver.start_execution(
            authorized=execute_as(beta), workflow=beta, execution_id="exec-1"
        )
    )
    assert isinstance(first, WorkflowSuspended)
    assert isinstance(second, WorkflowSuspended)
    acme_record = world.registry.state_store.get(
        WORKFLOW_STATE, "acme-bank/exec-1"
    )
    beta_record = world.registry.state_store.get(
        WORKFLOW_STATE, "beta-bank/exec-1"
    )
    assert isinstance(acme_record, WorkflowStateRecord)
    assert isinstance(beta_record, WorkflowStateRecord)
    assert acme_record.tenant == "acme-bank"
    assert beta_record.tenant == "beta-bank"


# --- D-IMPL-353: the capability crosses the seam, and only the capability ----


def _holds_a_capability(value: object) -> bool:
    if isinstance(value, Authorized):
        return True
    if isinstance(value, dict):
        return any(_holds_a_capability(v) for v in value.values())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_holds_a_capability(v) for v in value)
    return False


def test_a_wrong_kind_capability_reaches_no_engine_state_through_the_leg(
    leg: OrchestrationLeg, world: World
) -> None:
    """§1.5 across the seam: a genuine ``Resume`` handed to ``start_execution``
    is the wrong kind for the engine's ``execute``. Every leg surfaces the
    engine's own typed refusal VERBATIM — the LangGraph and ADK topologies
    propagate node exceptions natively, and the Claude leg re-raises the
    exception its guarded tool kept — and the observable is the same on every
    leg: no state under the tenant, nothing on the queue, no node ran."""
    driver = leg.driver(world.engine)
    workflow = world.workflow()
    wrong = resume_as(workflow)
    with pytest.raises(CapabilityBypassError, match="kind"):
        asyncio.run(
            driver.start_execution(
                authorized=wrong,  # type: ignore[arg-type]
                workflow=workflow,
                execution_id="exec-wk",
            )
        )
    assert (
        world.registry.state_store.get(WORKFLOW_STATE, f"{wrong.tenant}/exec-wk")
        is None
    )
    assert world.transport.pending(tenant=wrong.tenant) == ()
    assert world.bindings.ran == []


def test_the_driver_retains_no_capability_after_a_drive(
    leg: OrchestrationLeg, world: World
) -> None:
    """The capability lives in the closure of the call that received it and
    dies with it (§1.2): after a full drive no attribute of the driver — nor
    anything a dict/list attribute holds — is an ``Authorized``."""
    driver = leg.driver(world.engine)
    workflow = world.workflow()
    _drive_to_terminal(leg, world, workflow, "exec-1")
    retained = {
        name: value
        for name, value in vars(driver).items()
        if _holds_a_capability(value)
    }
    assert retained == {}
    # And the positive control: a capability IS an Authorized, so the walk
    # would have found one had the driver kept it.
    assert _holds_a_capability({"k": [execute_as(workflow)]})


def test_the_engine_files_under_the_capabilitys_tenant_through_the_leg(
    leg: OrchestrationLeg, world: World
) -> None:
    """§1.3 across the seam: the state key, the suspend handle and the HITL
    event carry the capability's tenant. The handle is acme-bank's; the run
    is under a beta-bank capability for the same key; everything lands under
    beta-bank and nothing under acme-bank."""
    driver = leg.driver(world.engine)
    workflow = world.workflow()
    as_beta: Authorized[Execute] = execute_capability(
        tenant="beta-bank", resource=workflow.definition_key
    )
    suspended = asyncio.run(
        driver.start_execution(
            authorized=as_beta, workflow=workflow, execution_id="exec-b"
        )
    )
    assert isinstance(suspended, WorkflowSuspended)
    assert suspended.tenant == "beta-bank"
    assert world.registry.state_store.get(WORKFLOW_STATE, "acme-bank/exec-b") is None
    record = world.registry.state_store.get(WORKFLOW_STATE, "beta-bank/exec-b")
    assert isinstance(record, WorkflowStateRecord)
    assert record.tenant == "beta-bank"
    assert world.transport.pending(tenant="acme-bank") == ()
    (pending,) = world.transport.pending(tenant="beta-bank")
    assert pending.tenant == "beta-bank"
    if leg.positions is not None:
        assert leg.positions(driver, "beta-bank", "exec-b")
