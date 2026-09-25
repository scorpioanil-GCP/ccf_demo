"""Workflow exception paths routed into ``ExceptionEscalation`` (07-08).

Written before the implementation per the TDD discipline. The claim: a
workflow node whose exception ref targets an escalation binding routes
there as a first-class recorded transition — the routed transition appears
in the execution trace, in the audit log, and (after the execution reaches
terminal) in the dimension-5 step-sequence block — and the escalation's
resolution is a bound human action landing on dimension 2.

The wiring is composition-root shape (CLAUDE.md §8.1): the engine returns a
typed :class:`WorkflowExceptionRouted` naming the artifact-declared handler
ref; the deployment hands that routed state to the escalation primitive on
the shared HITL transport. `/src` never imports `/runtime`, so the seam is
data — the routed outcome's fields — not an import.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    TASK_DEFINITION,
    AgentDefinition,
    TaskDefinition,
)
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.approval_gate import ApprovalGate, GateResolution
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
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from ccf.workflow.factory import Workflow, WorkflowFactory
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowExceptionRouted,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord


from tests.workflow.capabilities import (
    execute_as,
    execute_capability,
    resume_as,
)
from tests.workflow.test_engine import _PermissiveDebt

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


def _registry() -> ControlPlaneRegistry:
    plane = ControlPlaneRegistry(clock=_ticking_clock())
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
    return plane


def _covenant(registry: ControlPlaneRegistry) -> Workflow:
    fixture = _load("workflows/covenant_review_workflow.yaml")
    definition = parse_artifact(
        fixture["workflow_definition"], WORKFLOW_DEFINITION
    )
    assert isinstance(definition, WorkflowDefinition)
    key = fixture["keys"]["workflow_definition"]
    version = registry.register_versioned(key, definition, WORKFLOW_DEFINITION)
    assert isinstance(version, str)
    return WorkflowFactory(control_plane=registry).construct(
        execute_capability(tenant=definition.tenant, resource=key),
        definition_version=version,
    )


class _Bindings:
    """Injected node bindings failing once per named step, then succeeding."""

    def __init__(self, failing: set[str]) -> None:
        self.failing = failing

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        if step_name in self.failing:
            self.failing.discard(step_name)
            raise RuntimeError(f"skill {step_name!r} failed")
        return {"step": step_name}

    async def run_agent(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        if step_name in self.failing:
            self.failing.discard(step_name)
            raise RuntimeError(f"agent {step_name!r} failed")
        return {"step": step_name}


def _principal(*, product_content_hash: str) -> HumanPrincipalBinding:
    approver = _load("hitl.yaml")["approvers"]["credit_officer"]
    return HumanPrincipalBinding(
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=product_content_hash,
    )


def test_an_exception_ref_routes_into_an_escalation_end_to_end(
    tmp_path: Path,
) -> None:
    """Routed transition in trace + audit + dim-5; resolution on dim 2."""
    registry = _registry()
    transport = InMemoryHitlTransport()
    bindings = _Bindings(failing={"fetch-certificates"})
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=FileArtifactStore(root=tmp_path / "artifacts"),
        hitl_transport=transport,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=_ticking_clock(),
        debt_binding=_PermissiveDebt(),
    )
    workflow = _covenant(registry)
    tenant = workflow.definition.tenant

    # 1. The failing node routes to its artifact-declared handler ref — a
    #    first-class recorded transition (D-13).
    routed = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-esc"))
    assert isinstance(routed, WorkflowExceptionRouted)
    key = f"{tenant}/exec-esc"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    assert record.trace[-1].kind == "exception"
    assert record.trace[-1].target == routed.handler_ref

    # 2. The deployment hands the routed state to the escalation primitive
    #    (composition-root wiring; the routing artifact is the policy_ref).
    escalation = ExceptionEscalation(
        transport=transport, audit=registry.audit_log, clock=_ticking_clock()
    )
    state_hash = content_hash(record)
    hand_off = escalation.escalate(
        tenant=tenant,
        event_key=f"{key}/{routed.node}",
        workflow_state_ref=key,
        product_content_hash=state_hash,
        policy_ref=routed.handler_ref,
        trigger=ExplicitEscalation(
            reason=_load("hitl.yaml")["escalation"]["explicit_reason"]
        ),
    )
    assert isinstance(hand_off, EscalationHandOff)
    (pending,) = transport.pending(tenant=tenant)
    assert pending.event_class == "exception-escalation"
    assert pending.workflow_state_ref == key

    # 3. Resolution is a bound human action landing on dimension 2.
    resolution = escalation.resolve(
        tenant=tenant,
        event_key=f"{key}/{routed.node}",
        action="approve",
        principal=_principal(product_content_hash=state_hash),
    )
    assert isinstance(resolution, EscalationResolution)
    assert resolution.hitl_actions_block

    # 4. Resume retries the routed-from node; execution reaches the gate,
    #    the gate resolves, and the terminal step sequence (dimension 5)
    #    carries the exception transition verbatim.
    suspended = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-esc", decision="retry")
    )
    assert isinstance(suspended, WorkflowSuspended)
    gate = ApprovalGate(
        transport=transport, audit=registry.audit_log, clock=_ticking_clock()
    )
    (gate_event,) = transport.pending(tenant=tenant)
    gate_resolution = gate.resolve(
        tenant=tenant,
        event_key=suspended.event_key,
        action="approve",
        principal=_principal(
            product_content_hash=gate_event.product_content_hash
        ),
    )
    assert isinstance(gate_resolution, GateResolution)
    completed = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-esc", decision="approved")
    )
    assert isinstance(completed, WorkflowCompleted)
    assert '"kind":"exception"' in completed.step_sequence_block
    assert routed.handler_ref in completed.step_sequence_block

    # 5. Audit: the routed transition and both human actions are recorded.
    actions = [event.action for event in registry.audit_log.events()]
    assert "workflow_exception" in actions
    assert actions.count("hitl_action") >= 2
