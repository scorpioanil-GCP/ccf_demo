"""``WorkflowEngine`` — the async-first in-SDK workflow state machine.

SDK-defined (CLAUDE.md §8.1 — an extension beyond the whitepaper, and it
says so); ORCH-01; D-IMPL-17/18/27/61. The execution half of the Workflow
primitive: it interprets WorkflowFactory-built handles
(:mod:`ccf.workflow.factory`) as state machines with explicit states,
transitions, and terminal conditions, suspends on hitl-gate nodes with
typed state persisted at the Control Plane boundary through the audited
write surface only, and resumes later.

**Placement (Open Question 2, resolved in writing).** The workflow
*contracts* are synchronous ``/src`` surface (07-04); this engine and its
state record are ``/runtime`` per D-14 and the state seam's
record-next-to-the-machine doctrine — the machine runs here, so the record
lives beside it (:mod:`ccf_runtime.workflow.state`).

**Factory handles only (ORCH-01).** ``execute`` and ``resume`` accept the
:class:`~ccf.workflow.factory.Workflow` handle and nothing else; a raw
``WorkflowDefinition`` is refused with a typed error. "Via the Task
Factory" holds at the execution boundary, not only at construction.

**Harness-neutral at every node (CLAUDE.md §8.1).** Node execution travels
two injected Protocol seams — :class:`SkillNodeBinding` and
:class:`AgentNodeBinding` — that the composition root binds: skill nodes
onto the existing skill dispatch (:mod:`ccf.skills.dispatch`), agent nodes
onto an Agent-Factory-constructed agent under a
:class:`~ccf.harness.protocol.HarnessAdapterProtocol` binding (§7.3). This
module names no harness and imports none; which harness executes an agent
node is resolved through the adapter binding, never through the workflow.

**Routing is the artifact's statement (CINV-01).** Transitions, terminals,
exception refs, and gate policies are interpreted from the factory-resolved
definition content only; no routing value exists in this module. A resume
decision must name a transition target the artifact declares.

**Persistence follows the D-IMPL-18/27 mutability split.** Live suspended
state is a :class:`~ccf_runtime.workflow.state.WorkflowStateRecord` on the
native Control Plane state seam, written exclusively through
:class:`~ccf.controlplane.audit.AuditLog`-bearing
:class:`~ccf.controlplane.state.AuditedStateWriter` writes. The immutable
execution trace writes through to the injected ArtifactStore at each
suspend and at terminal as content-addressed canonical bytes.

**Refusal doctrine (I.1 line).** Expected outcomes — gate suspension,
exception-path routing, a resume of a terminal or unknown execution, an
undeclared decision — are typed returned values, audited (refusals as
``resolved=False``). Broken wiring — a handle that is not a factory
product, a step ref the Control Plane cannot resolve, a foreign state
record, ambiguous nominal routing — raises.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Protocol, Union, runtime_checkable

from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.audit import AuditAction, AuditEvent, AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.resolution import resolve_pinned
from ccf.controlplane.state import AuditedStateWriter
from ccf.halflife.debt import DebtAssessment, DebtSignal
from ccf.hitl.approval_gate import GATE_ACTIONS
from ccf.hitl.transport import (
    HITLTransportProtocol,
    HitlActionSubmission,
    PendingHitlEvent,
)
from ccf.skills.grants import SplitAuditPlaneError
from ccf.workflow.definitions import (
    WORKFLOW_DEFINITION,
    WORKFLOW_FAILED_STATE,
)
from ccf.workflow.factory import Workflow
from ccf_runtime.workflow.state import (
    WORKFLOW_STATE,
    TraceEntry,
    WorkflowStateRecord,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "WORKFLOW_TRACE_ARTIFACT_CLASS",
    "AgentNodeBinding",
    "DebtAssessmentBinding",
    "ForeignStateRecordError",
    "SkillNodeBinding",
    "UnboundDebtAssessmentError",
    "WorkflowCompleted",
    "WorkflowEngine",
    "WorkflowExceptionRouted",
    "WorkflowExecutionTypeError",
    "WorkflowOutcome",
    "WorkflowResumeRefused",
    "WorkflowSuspended",
    "WorkflowWiringError",
]

#: The artifact class execution traces write through under (D-IMPL-18). A
#: mechanism identifier: it names the engine's own trace artifacts, exactly
#: as ``WORKFLOW_STATE`` names its state records.
WORKFLOW_TRACE_ARTIFACT_CLASS = "ccf.workflow-trace"


class WorkflowExecutionTypeError(TypeError):
    """The execute surface was handed something other than a factory handle.

    ORCH-01's "via the Task Factory", enforced at the execution boundary: a
    raw ``WorkflowDefinition`` — or anything else that is not the
    WorkflowFactory-built :class:`~ccf.workflow.factory.Workflow` — is not
    an accepted input type (CINV-01c, one level further up).
    """


class WorkflowWiringError(RuntimeError):
    """Broken wiring between the handle and this engine's Control Plane.

    A step ref that resolves to nothing, or nominal routing the artifact
    leaves ambiguous — a raised exception on the I.1 line, never a returned
    refusal: this is a broken deployment, not an expected outcome.
    """


class UnboundDebtAssessmentError(WorkflowWiringError):
    """An agent-node handoff was attempted with no bound debt assessment.

    D-IMPL-65's committed engine refusal, delivered in the 7.1 gap cycle
    per D-IMPL-66(b): DESIGN.md §4 names per-handoff ``D_c`` recomputation
    with fail-closed routing as a Workflow-primitive invariant
    (INV-CH7-68), so an engine asked to hand off to an agent node without a
    :class:`DebtAssessmentBinding` is a broken deployment — a raised
    exception on the I.1 line, never a returned refusal.
    """


class ForeignStateRecordError(TypeError):
    """The state store returned a record this machine did not write.

    The ``GrantStateRecord`` isinstance discipline applied to workflows: the
    :data:`~ccf_runtime.workflow.state.WORKFLOW_STATE` record class is the
    workflow machine's alone (D-IMPL-18/27).
    """


@runtime_checkable
class SkillNodeBinding(Protocol):
    """The seam a ``skill`` node executes through (CLAUDE.md §8.1).

    The composition root binds this onto the existing skill dispatch
    (:mod:`ccf.skills.dispatch`); the engine holds only the Protocol, so no
    dispatch target — and no transport behind one — is named here.
    """

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        """Invoke the skill the step's pinned ref names."""
        ...


@runtime_checkable
class AgentNodeBinding(Protocol):
    """The seam an ``agent`` node executes through (CLAUDE.md §7.3/§8.1).

    The composition root binds this onto an Agent-Factory-constructed agent
    running under a :class:`~ccf.harness.protocol.HarnessAdapterProtocol`
    adapter. Which harness executes is the binding's business — the engine
    never names one, which is what "harness-neutral at every node" means.
    """

    async def run_agent(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        """Invoke the agent the step's pinned definition ref names."""
        ...


@runtime_checkable
class DebtAssessmentBinding(Protocol):
    """The seam a ``D_c`` assessment travels before every agent handoff.

    INV-CH7-68 (debt cascades across multi-agent handoffs), D-IMPL-65's
    named next-phase commitment, accelerated by D-IMPL-66(b). The
    composition root binds this onto :func:`ccf.halflife.debt.assess_debt`
    against the Control Plane's resolved debt-profile artifact
    (``ccf.controlplane.artifacts``) for the decision class. The engine
    holds no profile and no threshold (CINV-01):
    it consumes only the :class:`~ccf.halflife.debt.DebtSignal` band the
    assessment already carries — the artifact's statement, never a value of
    this module's.
    """

    async def assess(
        self, *, tenant: str, step_name: str, ref: str
    ) -> DebtAssessment:
        """Assess ``D_c`` for the handoff to the agent ``ref`` names."""
        ...


class WorkflowSuspended(CCFContract):
    """A typed suspended handle — suspension is a value, not an exception.

    Returned when execution reaches a hitl-gate node (CLAUDE.md §8.1). The
    gate interaction in 07-06 goes through the injected HITL transport stub
    only; the real ApprovalGate (07-07) owns gate semantics.
    """

    tenant: str
    execution_id: str
    gate: str
    event_key: str
    trace_artifact: ArtifactRef


class WorkflowCompleted(CCFContract):
    """A terminal outcome, with the replay handoff the engine serialized.

    ``step_sequence_block`` is the canonical serialization of the execution
    trace — serialized once, here, and passed verbatim to replay dimension 5
    (07-05 keyword); ``delegation_chain`` extends dimension 4 with the
    workflow execution id followed by the agent-definition identities the
    execution invoked, in declaration order (CLAUDE.md §8.1).
    """

    tenant: str
    execution_id: str
    terminal_state: str
    step_sequence_block: str
    delegation_chain: tuple[str, ...]
    trace_artifact: ArtifactRef


class WorkflowExceptionRouted(CCFContract):
    """An exception path taken to its ref'd handler — an expected outcome.

    First-class recorded transition (D-13; CLAUDE.md §8.1): the node's
    exception ref resolved and the execution's state was handed to it. A
    node with *no* ref never produces this — absence propagates to the
    reserved ``failed`` terminal instead (D-IMPL-61 option-a).
    """

    tenant: str
    execution_id: str
    node: str
    handler_ref: str
    trace_artifact: ArtifactRef


class WorkflowResumeRefused(CCFContract):
    """A resume the engine refuses — typed value, audited ``resolved=False``.

    Unknown execution, already-terminal execution, a handle that does not
    describe the suspended execution, or a decision the artifact declares no
    transition for. All expected outcomes on the I.1 line.
    """

    tenant: str
    execution_id: str
    reason: str


WorkflowOutcome = Union[
    WorkflowSuspended,
    WorkflowCompleted,
    WorkflowExceptionRouted,
    WorkflowResumeRefused,
]


class WorkflowEngine:
    """The async-first workflow state machine (CLAUDE.md §8.1; D-IMPL-04/17).

    Everything is injected — Control Plane, artifact store, HITL transport,
    node bindings, clock — in the constructor-injection discipline of every
    Control Plane service: the engine holds no routing, no vocabulary of the
    deployment's, and no wall clock of its own.

    Args:
        control_plane: The registry the engine resolves step refs through
            and whose state seam and audit plane it writes (D-IMPL-18).
        artifact_store: Where execution traces write through at suspend and
            terminal (D-IMPL-18; content-addressed, D-IMPL-26).
        hitl_transport: The typed HITL queue hitl-gate suspensions enqueue
            into (D-IMPL-20). In 07-06 this is the gate interaction in its
            entirety; the ApprovalGate primitive (07-07) owns the rest.
        skill_binding: The ``skill``-node execution seam.
        agent_binding: The ``agent``-node execution seam (§7.3 — resolved
            through a harness adapter at the composition root).
        clock: Time source for trace and audit timestamps. Injected, never
            read from the wall.
        debt_binding: The per-agent-handoff ``D_c`` assessment seam
            (INV-CH7-68; D-IMPL-65/66(b)). Optional at construction so a
            skill-and-gate-only deployment carries no obligation it never
            exercises — but an *agent-node* handoff on an engine with no
            binding raises :class:`UnboundDebtAssessmentError`.
        audit: Optional explicitness affordance, constrained exactly as the
            grant ledger's: the Control Plane is the audit plane and there
            is one of it (INV-CH7-71), so this defaults to — and may only
            be — ``control_plane.audit_log``.

    Raises:
        SplitAuditPlaneError: ``audit`` is a log other than
            ``control_plane.audit_log``.
    """

    def __init__(
        self,
        *,
        control_plane: ControlPlaneRegistry,
        artifact_store: ArtifactStoreProtocol,
        hitl_transport: HITLTransportProtocol,
        skill_binding: SkillNodeBinding,
        agent_binding: AgentNodeBinding,
        clock: Callable[[], datetime],
        audit: AuditLog | None = None,
        debt_binding: DebtAssessmentBinding | None = None,
    ) -> None:
        if audit is not None and audit is not control_plane.audit_log:
            raise SplitAuditPlaneError(
                "the engine's audit log is not the log its Control Plane"
                " records into; workflow transitions would land in two"
                " partial journals and no complete one. Omit `audit` (it"
                " defaults to `control_plane.audit_log`) or pass that same"
                " log (INV-CH7-71; CLAUDE.md §10)"
            )
        self._control_plane = control_plane
        self._artifact_store = artifact_store
        self._hitl_transport = hitl_transport
        self._skill_binding = skill_binding
        self._agent_binding = agent_binding
        self._clock = clock
        self._debt_binding = debt_binding
        self._audit = control_plane.audit_log if audit is None else audit
        self._writer = AuditedStateWriter(
            store=control_plane.state_store, audit=self._audit
        )

    @property
    def artifact_store(self) -> ArtifactStoreProtocol:
        """The injected trace write-through substrate (D-IMPL-18)."""
        return self._artifact_store

    # -- the execution surfaces (factory handles only, ORCH-01) --------------

    async def execute(
        self, workflow: Workflow, *, execution_id: str
    ) -> WorkflowOutcome:
        """Run one execution from its start node.

        Args:
            workflow: A WorkflowFactory-built handle — the ONLY accepted
                input type (ORCH-01).
            execution_id: Caller-supplied execution identity; state is keyed
                ``(tenant, execution_id)`` (D-23).

        Raises:
            WorkflowExecutionTypeError: ``workflow`` is not a factory-built
                handle.
            WorkflowWiringError: a step ref resolves to nothing, or nominal
                routing is ambiguous.
        """
        self._require_handle(workflow)
        tenant = workflow.definition.tenant
        key = self._key(tenant, execution_id)
        if self._control_plane.state_store.get(WORKFLOW_STATE, key) is not None:
            return self._refuse(
                workflow,
                tenant=tenant,
                execution_id=execution_id,
                reason=(
                    f"execution {key!r} already exists; an execution id is"
                    " started once and thereafter resumed (D-23)"
                ),
            )
        return await self._advance(
            workflow,
            tenant=tenant,
            execution_id=execution_id,
            state=workflow.definition.start,
            trace=(),
        )

    async def resume(
        self, workflow: Workflow, *, execution_id: str, decision: str
    ) -> WorkflowOutcome:
        """Continue a suspended execution under ``decision``.

        ``decision`` must name a transition target the artifact declares
        from the suspended node (CINV-01 — routing is the artifact's
        statement; the engine interprets, never decides).

        Raises:
            WorkflowExecutionTypeError: ``workflow`` is not a factory-built
                handle.
            ForeignStateRecordError: the state store returned a record this
                machine did not write.
        """
        self._require_handle(workflow)
        tenant = workflow.definition.tenant
        key = self._key(tenant, execution_id)
        record = self._control_plane.state_store.get(WORKFLOW_STATE, key)
        if record is None:
            return self._refuse(
                workflow,
                tenant=tenant,
                execution_id=execution_id,
                reason=f"no execution exists under {key!r}",
            )
        if not isinstance(record, WorkflowStateRecord):
            raise ForeignStateRecordError(
                f"the Control Plane state store returned a"
                f" {type(record).__name__} under workflow state key"
                f" {key!r}, not a WorkflowStateRecord; the"
                f" {WORKFLOW_STATE!r} record class is the workflow"
                " machine's alone (D-IMPL-18/27)"
            )
        if record.status == "terminal":
            return self._refuse(
                workflow,
                tenant=tenant,
                execution_id=execution_id,
                reason=(
                    f"execution {key!r} is terminal; a terminal execution"
                    " never transitions again (CLAUDE.md §8.1)"
                ),
            )
        if record.workflow_definition_uri != workflow.identity.definition_uri:
            return self._refuse(
                workflow,
                tenant=tenant,
                execution_id=execution_id,
                reason=(
                    f"execution {key!r} was started under"
                    f" {record.workflow_definition_uri!r}, not"
                    f" {workflow.identity.definition_uri!r}; an execution"
                    " continues only under the definition it was started"
                    " with (D-IMPL-26)"
                ),
            )
        if record.status == "suspended":
            actor: str | None = None
            if self._is_gate(workflow, record.current_state):
                # SEC-001: a gate opens on a human action returned through
                # the HITL authority path, never on the caller's decision
                # string. The authority is bound to THIS suspension, so one
                # approval authorizes exactly the passage it was taken
                # against (CLAUDE.md §8.2 audit-by-construction).
                authority = self._gate_authority(
                    tenant=tenant, key=key, gate=record.current_state,
                    record=record,
                )
                if authority is None:
                    return self._refuse(
                        workflow,
                        tenant=tenant,
                        execution_id=execution_id,
                        reason=(
                            f"execution {key!r} is suspended on HITL gate"
                            f" {record.current_state!r} and no approval for"
                            " this suspension has returned through the HITL"
                            " authority path; a gate is opened by a recorded"
                            " human action, never by naming a transition"
                            " (CLAUDE.md §8.2; D-IMPL-20)"
                        ),
                    )
                actor = authority.principal.approver.subject_id
            targets = self._targets(workflow, record.current_state)
            if decision not in targets:
                return self._refuse(
                    workflow,
                    tenant=tenant,
                    execution_id=execution_id,
                    reason=(
                        f"decision {decision!r} names no declared transition"
                        f" target from {record.current_state!r}; routing is"
                        " interpreted from the artifact only (CINV-01;"
                        " CLAUDE.md §8.1)"
                    ),
                )
            trace = record.trace + (
                self._entry(
                    record.trace, record.current_state, decision, "resume"
                ),
            )
            self._append(
                workflow,
                key,
                action="workflow_resumed",
                resolved=True,
                actor=actor,
            )
            if decision in workflow.definition.effective_terminal_states:
                return self._complete(
                    workflow,
                    tenant=tenant,
                    execution_id=execution_id,
                    terminal_state=decision,
                    trace=trace,
                )
            return await self._advance(
                workflow,
                tenant=tenant,
                execution_id=execution_id,
                state=decision,
                trace=trace,
            )
        # exception-routed: the handler handed the state back — retry the
        # node it was routed from. No gate, and so no human actor.
        self._append(
            workflow,
            key,
            action="workflow_resumed",
            resolved=True,
            actor=None,
        )
        return await self._advance(
            workflow,
            tenant=tenant,
            execution_id=execution_id,
            state=record.current_state,
            trace=record.trace,
        )

    # -- the machine ----------------------------------------------------------

    async def _advance(
        self,
        workflow: Workflow,
        *,
        tenant: str,
        execution_id: str,
        state: str,
        trace: tuple[TraceEntry, ...],
    ) -> WorkflowOutcome:
        """Drive the machine from ``state`` until suspend or terminal."""
        key = self._key(tenant, execution_id)
        step_kinds = {
            step.name: step for step in workflow.task_definition.steps
        }
        while True:
            step = step_kinds.get(state)
            if step is None:
                raise WorkflowWiringError(
                    f"node {state!r} names no step in the resolved task"
                    " definition; the factory's semantic layer should have"
                    " refused this handle (D-12)"
                )
            if step.kind == "hitl-gate":
                return self._suspend(
                    workflow,
                    tenant=tenant,
                    execution_id=execution_id,
                    gate=state,
                    trace=trace,
                )
            assert step.ref is not None  # non-gate steps carry refs by schema
            if resolve_pinned(self._control_plane, step.ref) is None:
                raise WorkflowWiringError(
                    f"step {state!r} references {step.ref!r}, which resolves"
                    " to nothing this engine's Control Plane has registered;"
                    " broken wiring raises (I.1 line; DESIGN.md §3.5)"
                )
            if step.kind == "agent":
                # INV-CH7-68 debt cascade: D_c is assessed BEFORE every
                # agent handoff, outside the try/except so a fail-closed
                # route is a deliberate transition, never an accident
                # (D-IMPL-65; D-IMPL-66(b)).
                if self._debt_binding is None:
                    raise UnboundDebtAssessmentError(
                        f"agent node {state!r} was reached on an engine"
                        " with no bound DebtAssessmentBinding; INV-CH7-68"
                        " requires D_c recomputed at every agent handoff"
                        " (D-IMPL-65). Bind `debt_binding=` at the"
                        " composition root onto ccf.halflife.debt"
                        ".assess_debt against the class's debt profile"
                    )
                assessment = await self._debt_binding.assess(
                    tenant=tenant, step_name=state, ref=step.ref
                )
                if assessment.signal is DebtSignal.FAIL_CLOSED:
                    # The fabric does not know enough to support the
                    # handoff: route the node's exception path without
                    # ever invoking the agent (fail-closed, DESIGN.md §4).
                    return self._route_exception(
                        workflow,
                        tenant=tenant,
                        execution_id=execution_id,
                        node=state,
                        trace=trace,
                    )
            try:
                if step.kind == "skill":
                    await self._skill_binding.run_skill(
                        tenant=tenant, step_name=state, ref=step.ref
                    )
                else:
                    await self._agent_binding.run_agent(
                        tenant=tenant, step_name=state, ref=step.ref
                    )
            except Exception:
                return self._route_exception(
                    workflow,
                    tenant=tenant,
                    execution_id=execution_id,
                    node=state,
                    trace=trace,
                )
            targets = self._targets(workflow, state)
            if len(targets) != 1:
                raise WorkflowWiringError(
                    f"node {state!r} declares {len(targets)} outgoing"
                    " transitions; a non-gate node's nominal path must"
                    " declare exactly one successor for the engine to"
                    " interpret (CLAUDE.md §8.1; CINV-01)"
                )
            (target,) = targets
            trace = trace + (self._entry(trace, state, target, "transition"),)
            self._append(
                workflow,
                key,
                action="workflow_transition",
                resolved=True,
                actor=None,
            )
            if target in workflow.definition.effective_terminal_states:
                return self._complete(
                    workflow,
                    tenant=tenant,
                    execution_id=execution_id,
                    terminal_state=target,
                    trace=trace,
                )
            state = target

    def _suspend(
        self,
        workflow: Workflow,
        *,
        tenant: str,
        execution_id: str,
        gate: str,
        trace: tuple[TraceEntry, ...],
    ) -> WorkflowSuspended:
        """Suspend on a hitl-gate: persist, enqueue, return a typed handle."""
        key = self._key(tenant, execution_id)
        trace = trace + (self._entry(trace, gate, gate, "suspend"),)
        record = self._record(
            workflow,
            tenant=tenant,
            execution_id=execution_id,
            current_state=gate,
            status="suspended",
            trace=trace,
        )
        self._persist(workflow, key, record, action="workflow_suspended")
        trace_artifact = self._write_trace(tenant, execution_id, trace)
        event_key = self._event_key(key, gate)
        self._hitl_transport.enqueue(
            event=PendingHitlEvent(
                event_key=event_key,
                event_class="approval-gate",
                tenant=tenant,
                workflow_state_ref=key,
                product_content_hash=content_hash(record),
                policy_ref=workflow.definition.gate_policies.get(gate),
            )
        )
        return WorkflowSuspended(
            tenant=tenant,
            execution_id=execution_id,
            gate=gate,
            event_key=event_key,
            trace_artifact=trace_artifact,
        )

    def _route_exception(
        self,
        workflow: Workflow,
        *,
        tenant: str,
        execution_id: str,
        node: str,
        trace: tuple[TraceEntry, ...],
    ) -> WorkflowOutcome:
        """Take ``node``'s exception path (D-13; D-IMPL-61 option-a)."""
        key = self._key(tenant, execution_id)
        handler_ref = workflow.definition.exception_refs.get(node)
        if handler_ref is not None:
            trace = trace + (
                self._entry(trace, node, handler_ref, "exception"),
            )
            record = self._record(
                workflow,
                tenant=tenant,
                execution_id=execution_id,
                current_state=node,
                status="exception-routed",
                trace=trace,
            )
            self._persist(workflow, key, record, action="workflow_exception")
            trace_artifact = self._write_trace(tenant, execution_id, trace)
            return WorkflowExceptionRouted(
                tenant=tenant,
                execution_id=execution_id,
                node=node,
                handler_ref=handler_ref,
                trace_artifact=trace_artifact,
            )
        # Absent ref: a defined, audited transition to the reserved terminal
        # (D-IMPL-61) — a positive recorded event, never a fall-through.
        trace = trace + (
            self._entry(trace, node, WORKFLOW_FAILED_STATE, "exception"),
        )
        self._append(
            workflow,
            key,
            action="workflow_exception",
            resolved=True,
            actor=None,
        )
        return self._complete(
            workflow,
            tenant=tenant,
            execution_id=execution_id,
            terminal_state=WORKFLOW_FAILED_STATE,
            trace=trace,
        )

    def _complete(
        self,
        workflow: Workflow,
        *,
        tenant: str,
        execution_id: str,
        terminal_state: str,
        trace: tuple[TraceEntry, ...],
    ) -> WorkflowCompleted:
        """Reach a terminal condition: persist, write through, hand to replay."""
        key = self._key(tenant, execution_id)
        record = self._record(
            workflow,
            tenant=tenant,
            execution_id=execution_id,
            current_state=terminal_state,
            status="terminal",
            trace=trace,
        )
        self._persist(workflow, key, record, action="workflow_completed")
        trace_artifact = self._write_trace(tenant, execution_id, trace)
        visited = {entry.source for entry in trace} | {
            entry.target for entry in trace
        }
        delegation_chain = (f"workflow:{key}",) + tuple(
            step.ref
            for step in workflow.task_definition.steps
            if step.kind == "agent"
            and step.name in visited
            and step.ref is not None
        )
        return WorkflowCompleted(
            tenant=tenant,
            execution_id=execution_id,
            terminal_state=terminal_state,
            step_sequence_block=canonical_bytes(trace).decode("utf-8"),
            delegation_chain=delegation_chain,
            trace_artifact=trace_artifact,
        )

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _require_handle(workflow: object) -> None:
        if not isinstance(workflow, Workflow):
            raise WorkflowExecutionTypeError(
                f"the engine executes WorkflowFactory-built handles only;"
                f" got {type(workflow).__name__}. Construct through"
                " ccf.workflow.factory.WorkflowFactory — ORCH-01's 'via the"
                " Task Factory' holds at the execution boundary (CINV-01c)"
            )

    @staticmethod
    def _key(tenant: str, execution_id: str) -> str:
        return f"{tenant}/{execution_id}"

    @staticmethod
    def _event_key(key: str, gate: str) -> str:
        """The pending-event key a gate suspension enqueues under."""
        return f"{key}/{gate}"

    @staticmethod
    def _is_gate(workflow: Workflow, state: str) -> bool:
        """Whether ``state`` names a hitl-gate step in the resolved task."""
        return any(
            step.name == state and step.kind == "hitl-gate"
            for step in workflow.task_definition.steps
        )

    def _gate_authority(
        self,
        *,
        tenant: str,
        key: str,
        gate: str,
        record: WorkflowStateRecord,
    ) -> HitlActionSubmission | None:
        """The recorded human approval authorizing passage past ``gate``.

        SEC-001. Reads the HITL transport's authority path — the only
        surface a human action returns through (D-IMPL-20) — and returns
        the submission that authorizes THIS suspension, or ``None``.

        Three conditions, all necessary:

        * the submission names this gate's pending event, so an approval of
          one gate is not an approval of another;
        * its principal echoes ``content_hash(record)`` — the suspension's
          own identity, which is what the pending event bound at suspend
          time and what :class:`~ccf.hitl.approval_gate.ApprovalGate`
          already makes the approver attest to (T-07-39). A suspension's
          trace is unique to it, so an approval cannot be replayed onto
          another execution, another tenant, or a later suspension of the
          same gate;
        * the action is an approval-gate verdict. Both verdicts authorize
          the engine to leave the gate — a rejection routes to whichever
          target the artifact declares for it, which is why the check is
          ``in GATE_ACTIONS`` and not ``== GATE_APPROVE``.

        **Known residual (D-IMPL-350).** The verdict does not bind WHICH
        declared target the resume may take, because no artifact declares
        that mapping: a :class:`~ccf.workflow.definitions.WorkflowDefinition`
        carries ``transitions`` (source→target) and nothing verdict-shaped.
        Deriving one in code would put domain routing values in ``/src``
        (No-Hardcoding, CLAUDE.md §6.4), so the mapping must be declared
        before it can be enforced. Until then a recorded rejection can be
        routed down the approving branch. Pinned by
        ``tests/workflow/test_engine.py::
        test_a_rejection_authorizes_resumption_but_does_not_bind_the_target``.

        Note the direction of trust: the engine *reads* the authority path
        and never writes a verdict to it. Resolution stays the gate
        primitive's act (CLAUDE.md §8.2).
        """
        event_key = self._event_key(key, gate)
        suspension = content_hash(record)
        return next(
            (
                submission
                for submission in self._hitl_transport.submissions(
                    tenant=tenant
                )
                if submission.event_key == event_key
                and submission.tenant == tenant
                and submission.principal.product_content_hash == suspension
                and submission.action in GATE_ACTIONS
            ),
            None,
        )

    @staticmethod
    def _targets(workflow: Workflow, source: str) -> frozenset[str]:
        return frozenset(
            transition.target
            for transition in workflow.definition.transitions
            if transition.source == source
        )

    def _entry(
        self,
        trace: tuple[TraceEntry, ...],
        source: str,
        target: str,
        kind: str,
    ) -> TraceEntry:
        return TraceEntry(
            sequence=len(trace),
            source=source,
            target=target,
            kind=kind,
            occurred_at=self._clock(),
        )

    def _record(
        self,
        workflow: Workflow,
        *,
        tenant: str,
        execution_id: str,
        current_state: str,
        status: str,
        trace: tuple[TraceEntry, ...],
    ) -> WorkflowStateRecord:
        return WorkflowStateRecord(
            tenant=tenant,
            execution_id=execution_id,
            current_state=current_state,
            status=status,
            trace=trace,
            workflow_definition_uri=workflow.identity.definition_uri,
        )

    def _persist(
        self,
        workflow: Workflow,
        key: str,
        record: WorkflowStateRecord,
        *,
        action: AuditAction,
    ) -> None:
        """Write state through the audited surface — one write, one event."""
        self._writer.write(
            WORKFLOW_STATE,
            key,
            record,
            event=AuditEvent(
                sequence=0,  # reassigned by the log; sequencing is its own
                action=action,
                key=key,
                version=workflow.identity.definition_hash,
                resolved=True,
                occurred_at=self._clock(),
                actor=None,
                artifact_class=WORKFLOW_DEFINITION.class_id,
            ),
        )

    def _append(
        self,
        workflow: Workflow,
        key: str,
        *,
        action: AuditAction,
        resolved: bool,
        actor: str | None,
    ) -> None:
        """Audit one transition that changes no persisted state.

        ``actor`` carries no default (SEC-001 remedy 2): every call site
        states who acted, or states positively that no human did. A default
        would let a gate resolution be audited with the approver silently
        omitted — the shape that let the pre-fix engine record
        ``resolved=True`` for an approval that never happened.
        """
        self._audit.append(
            action=action,
            key=key,
            version=workflow.identity.definition_hash,
            resolved=resolved,
            occurred_at=self._clock(),
            actor=actor,
            artifact_class=WORKFLOW_DEFINITION.class_id,
        )

    def _refuse(
        self,
        workflow: Workflow,
        *,
        tenant: str,
        execution_id: str,
        reason: str,
    ) -> WorkflowResumeRefused:
        """Return a typed refusal, audited ``resolved=False``."""
        self._append(
            workflow,
            self._key(tenant, execution_id),
            action="workflow_resumed",
            resolved=False,
            actor=None,
        )
        return WorkflowResumeRefused(
            tenant=tenant, execution_id=execution_id, reason=reason
        )

    def _write_trace(
        self,
        tenant: str,
        execution_id: str,
        trace: tuple[TraceEntry, ...],
    ) -> ArtifactRef:
        """Write the trace through to the ArtifactStore (D-IMPL-18)."""
        return self._artifact_store.put(
            tenant_id=tenant,
            artifact_class=WORKFLOW_TRACE_ARTIFACT_CLASS,
            name=execution_id,
            artifact=trace,
        )
