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

**The tenant is the capability's (D-IMPL-353 §1.3).** ``execute`` and
``resume`` each require the :class:`~ccf.authz.capability.Authorized` for
their own action — ``Execute`` and ``Resume`` respectively — and
:func:`~ccf.authz.capability.verify` it against the handle's definition key
before anything else. From that line on the only tenant in the engine is
``authorized.tenant``: the state key is derived from it and the execution
id, every state-store and trace-store write carries the capability and that
derived key (the §1.2 derived-writes rule), and the HITL pending event is
filed under it. Nothing here reads the tenant the artifact declares; the
factory compared it with the capability once, at construction, and that is
the whole of the tenant check. A capability for tenant B therefore cannot
produce state under tenant A — not because a comparison refuses it, but
because no expression of the engine files anywhere but under
``authorized.tenant`` (§2 P2).

**Refusal doctrine (I.1 line).** Expected outcomes — gate suspension,
exception-path routing, a resume of a terminal or unknown execution, an
undeclared decision — are typed returned values, audited (refusals as
``resolved=False``). Broken wiring — a handle that is not a factory
product, a step ref the Control Plane cannot resolve, a foreign state
record, ambiguous nominal routing — raises.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Protocol, Union, runtime_checkable

from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol, DerivedWrite
from ccf.authz.capability import Authorized, Execute, Resume, verify
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.audit import (
    AuditAction,
    AuditEvent,
    AuditLog,
    WorkflowVerdictIntegrityFailure,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.resolution import resolve_pinned
from ccf.controlplane.state import (
    AuditedStateWriter,
    ConditionalStateStore,
    StateConflict,
    state_key,
)
from ccf.halflife.debt import DebtAssessment, DebtSignal
from ccf.hitl.approval_gate import GATE_ACTIONS, GATE_EVENT_CLASS
from ccf.hitl.escalation import ESCALATION_EVENT_CLASS
from ccf.hitl.transport import (
    ApproverNotEligible,
    GateAlreadyClosed,
    GateVerdictsChanged,
    check_approver_eligibility,
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
    "ExecutionFenced",
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

#: Executions with a resumption in flight IN THIS PROCESS (D-IMPL-377), each
#: as ``(id(state_store), state_key)``: the Control Plane state store the
#: execution's record lives in, and the key it lives under. Module-level and
#: not per engine, because two engines over one Control Plane read and write
#: the same record and must be refused against each other. Membership IS the
#: claim; the lock guards only the test-and-set and the discard, and is never
#: held across an ``await``.
_RESUMPTIONS_IN_FLIGHT: set[tuple[int, str]] = set()
_RESUMPTIONS_IN_FLIGHT_LOCK = threading.Lock()

#: The two sharing scopes a Control Plane state store and a HITL transport
#: declare (``D-IMPL-378``): ``process`` — no other process reaches them — and
#: ``shared`` — a durable implementation several processes reach. Mechanism
#: vocabulary, read by the construction checks; no deployment value.
_SCOPES: frozenset[str] = frozenset({"process", "shared"})


def _claim_resumption(claim: tuple[int, str]) -> bool:
    """Take one execution's single-flight claim, or report it already taken.

    A test-and-set that returns at once either way (D-IMPL-377): the caller
    refuses rather than waits, so no thread blocks on another resumption and
    no event loop blocks on itself.
    """
    with _RESUMPTIONS_IN_FLIGHT_LOCK:
        if claim in _RESUMPTIONS_IN_FLIGHT:
            return False
        _RESUMPTIONS_IN_FLIGHT.add(claim)
        return True


def _release_resumption(claim: tuple[int, str]) -> None:
    """Give one execution's single-flight claim back (D-IMPL-377)."""
    with _RESUMPTIONS_IN_FLIGHT_LOCK:
        _RESUMPTIONS_IN_FLIGHT.discard(claim)


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


class ExecutionFenced(RuntimeError):
    """A later write of a passage found the record moved by another writer.

    SDK-defined (``D-IMPL-378``). Every write after a passage commit is
    conditional on the version that passage wrote. A conflict means a writer
    other than this passage moved the execution's record while the passage
    ran — which the engine's own refusals make impossible on a conforming
    store, since a ``running`` execution is never resumed or restarted — so the
    engine fails closed rather than overwrite what it never saw.
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
        # D-IMPL-378 (Dave: "Unsupported third-party implementations must fail
        # at construction"): a store or transport that cannot make a gate's
        # passage exactly-once is refused here, by name, before any execution
        # runs — never discovered at the first resumption.
        store = control_plane.state_store
        store_scope = getattr(store, "scope", None)
        if not isinstance(store, ConditionalStateStore) or store_scope not in _SCOPES:
            raise WorkflowWiringError(
                f"the Control Plane state store {type(store).__name__} is not a"
                " ConditionalStateStore declaring a scope of 'process' or"
                " 'shared' (get_versioned, put_if, scope); without a conditional"
                " write, two resumptions of one suspension, or two starts of one"
                " execution id, can both commit (D-IMPL-378; SEC-001)"
            )
        transport_scope = getattr(hitl_transport, "scope", None)
        if (
            not isinstance(hitl_transport, HITLTransportProtocol)
            or transport_scope not in _SCOPES
        ):
            raise WorkflowWiringError(
                f"the HITL transport {type(hitl_transport).__name__} does not"
                " offer the whole HITLTransportProtocol (close_gate, closures,"
                " scope among it) with a scope of 'process' or 'shared'; without"
                " close_gate, a verdict recorded while a gate is being decided"
                " is never judged (D-IMPL-378; SEC-001)"
            )
        if store_scope == "shared" and transport_scope != "shared":
            raise WorkflowWiringError(
                "the Control Plane state store is shared between processes but"
                " the HITL transport is not: a verdict recorded through another"
                " process would never be judged here, and that process's gate"
                " closures would never be seen (D-IMPL-378; SEC-001)"
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
        self,
        authorized: Authorized[Execute],
        workflow: Workflow,
        *,
        execution_id: str,
    ) -> WorkflowOutcome:
        """Run one execution from its start node.

        Args:
            authorized: The ``Execute`` capability the gate minted for this
                handle's definition key (D-IMPL-353 §1.2). Verified first;
                its tenant is the tenant the execution is filed under.
            workflow: A WorkflowFactory-built handle — the ONLY accepted
                input type (ORCH-01).
            execution_id: Caller-supplied execution identity; state is keyed
                ``(authorized.tenant, execution_id)`` (D-23; §1.3).

        Raises:
            WorkflowExecutionTypeError: ``workflow`` is not a factory-built
                handle.
            CapabilityBypassError: ``authorized`` is fabricated, retargeted,
                not an ``Execute``, or minted for another definition key.
            WorkflowWiringError: a step ref resolves to nothing, or nominal
                routing is ambiguous.
        """
        self._require_handle(workflow)
        verify(authorized, kind=Execute, resource=workflow.definition_key)
        tenant = authorized.tenant
        key = self._key(tenant, execution_id)
        # D-IMPL-378: the execution is recorded as started BEFORE its first
        # node runs, by a create-if-absent write, so a second start of the same
        # id is refused before it runs anything — in this process or any other
        # over the same store (D-23: an execution id is started once).
        try:
            version = self._write_state(
                authorized,
                workflow,
                key,
                self._record(
                    workflow,
                    tenant=tenant,
                    execution_id=execution_id,
                    current_state=workflow.definition.start,
                    status="running",
                    trace=(),
                    started_by=authorized.principal,
                ),
                action="workflow_started",
                actor=None,
                expected_version=0,
            )
        except StateConflict:
            return self._refuse(
                authorized,
                workflow,
                execution_id=execution_id,
                reason=(
                    f"execution {key!r} already exists; an execution id is"
                    " started once and thereafter resumed (D-23)"
                ),
            )
        return await self._advance(
            authorized,
            workflow,
            execution_id=execution_id,
            state=workflow.definition.start,
            trace=(),
            # SEC-006 (D-IMPL-366 G1 (a)): the REQUESTER of every gate this
            # execution reaches is the starter — the Execute capability's
            # principal — stamped once here and carried on every record.
            started_by=authorized.principal,
            version=version,
        )

    async def resume(
        self,
        authorized: Authorized[Resume],
        workflow: Workflow,
        *,
        execution_id: str,
        decision: str,
    ) -> WorkflowOutcome:
        """Continue a suspended execution under ``decision``.

        ``authorized`` is the ``Resume`` capability — its own kind, never
        ``Execute``: a deployment that granted *start a workflow* has not
        granted *carry a human decision past its gate* (D-IMPL-353 §1.5).
        Verified first against the handle's definition key; the state key
        is derived from ``authorized.tenant`` and ``execution_id``, so a
        capability for another tenant reads and writes nothing of this one.

        ``decision`` must name a transition target the artifact declares
        from the suspended node (CINV-01 — routing is the artifact's
        statement; the engine interprets, never decides).

        **One approval, one passage, however many processes resume**
        (``D-IMPL-378``; ``SEC-001``). Three mechanisms stand between one
        human approval and a second passage, and each is measured on its own:

        * **The in-process claim** (``D-IMPL-377``). Before the state record
          is read, the resumption takes a single-flight claim on the
          execution, keyed by the Control Plane state store the record lives
          in and by its state key, and shared by every engine in this process
          over that store. While it is held, a second resumption of the same
          execution is REFUSED, never queued: a typed
          :class:`WorkflowResumeRefused`, audited ``resolved=False``, which the
          HTTP door answers with the same 409 as the sequential refusal. It is
          released on every exit — completion, refusal, exception and
          cancellation — and its lock guards only the test-and-set, never an
          ``await``.
        * **The gate's closure on the authority path.** After every check has
          passed and before anything is written, the resumption asks the HITL
          transport to close the gate on exactly the verdicts it judged
          (:meth:`~ccf.hitl.transport.HITLTransportProtocol.close_gate`). A
          verdict recorded after the resumption read the verdicts makes the
          closure fail, and the resumption is refused ("present the resumption
          again"); a verdict arriving after the closure is refused at every
          door with ``hitl-gate-closed``, so it never stands beside a decision
          it can no longer reach, and the queue stops offering the gate.
        * **The conditional passage commit.** The passage — the record leaving
          the gate, together with its attributed ``workflow_resumed`` row, in
          ONE audited write — is committed conditionally on the version the
          resumption read, BEFORE the step after the gate runs. Of two
          resumptions in two processes, or through two state-store objects
          over one durable store, exactly one commit lands; the other is
          refused before it runs anything.

        **An interrupted passage is never retried** (Dave's ruling on
        ``D-IMPL-378``). A passage whose commit never landed leaves the record
        ``suspended`` with no step started, so presenting the resumption again
        re-takes the same closure (it names the passage, not the engine) and
        exactly one commit can land. A passage whose commit landed is
        ``running`` until it suspends or completes; a resumption that finds it
        ``running`` is refused, typed, because the step after the gate may
        already have had effects no engine can see, and an operator reconciles
        the execution outside the fabric.

        Measured by ``tests/workflow/test_approval_gate_limits.py``,
        ``tests/http_api/test_approval_gate_limits_door.py`` and
        ``tests/workflow/test_resume_single_flight.py``.

        Raises:
            WorkflowExecutionTypeError: ``workflow`` is not a factory-built
                handle.
            CapabilityBypassError: ``authorized`` is fabricated, retargeted,
                not a ``Resume``, or minted for another definition key.
            ForeignStateRecordError: the state store returned a record this
                machine did not write.
            ExecutionFenced: a writer other than this passage moved the
                execution's record while the passage ran.
        """
        self._require_handle(workflow)
        verify(authorized, kind=Resume, resource=workflow.definition_key)
        tenant = authorized.tenant
        key = self._key(tenant, execution_id)
        # D-IMPL-377: taken BEFORE the record is read, so no second
        # resumption can read what this one has not yet committed over.
        claim = (id(self._control_plane.state_store), key)
        if not _claim_resumption(claim):
            return self._refuse(
                authorized,
                workflow,
                execution_id=execution_id,
                reason=(
                    f"execution {key!r} already has a resumption in flight in"
                    " this process; a suspended execution is resumed by one"
                    " request at a time, so this one is refused rather than"
                    " queued — present it again once the other has returned"
                    " (D-IMPL-377; CLAUDE.md §8.1)"
                ),
            )
        try:
            return await self._resume_claimed(
                authorized,
                workflow,
                execution_id=execution_id,
                decision=decision,
                key=key,
            )
        finally:
            _release_resumption(claim)

    async def _resume_claimed(
        self,
        authorized: Authorized[Resume],
        workflow: Workflow,
        *,
        execution_id: str,
        decision: str,
        key: str,
    ) -> WorkflowOutcome:
        """:meth:`resume`'s body, run only while its single-flight claim is held."""
        tenant = authorized.tenant
        record, version = self._read_versioned(key)
        if record is None:
            return self._refuse(
                authorized,
                workflow,
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
                authorized,
                workflow,
                execution_id=execution_id,
                reason=(
                    f"execution {key!r} is terminal; a terminal execution"
                    " never transitions again (CLAUDE.md §8.1)"
                ),
            )
        if (
            record.workflow_definition_uri != workflow.identity.definition_uri
            or record.workflow_definition_hash
            != workflow.identity.definition_hash
        ):
            return self._refuse(
                authorized,
                workflow,
                execution_id=execution_id,
                reason=(
                    f"execution {key!r} was started under"
                    f" {record.workflow_definition_uri!r} at content"
                    f" {record.workflow_definition_hash!r}, not"
                    f" {workflow.identity.definition_uri!r} at"
                    f" {workflow.identity.definition_hash!r}; an execution"
                    " continues only under the definition it was started"
                    " with, matched by content because the URI is the"
                    " artifact's statement about itself (D-IMPL-26;"
                    " SEC-001)"
                ),
            )
        if record.status == "running":
            # D-IMPL-378, Dave's Q4 ruling: an interrupted passage is never
            # retried. A ``running`` record is a passage whose commit LANDED, so
            # the step after its gate may have started, and what that step did
            # is outside anything this engine can see: no retry of it can be
            # shown not to repeat an effect. So it is refused, typed, whoever
            # asks, until an operator reconciles the execution outside the
            # fabric. (A passage whose commit never landed is still
            # ``suspended`` and IS retried below: its step never started, its
            # gate's closure names it, and only one commit can land.)
            return self._refuse(
                authorized,
                workflow,
                execution_id=execution_id,
                reason=(
                    f"execution {key!r} has a committed passage that has not"
                    " finished: it is running in another process, or it was"
                    " interrupted after its step began. An interrupted passage"
                    " is never retried, because the effects its step may"
                    " already have had cannot be shown not to repeat; an"
                    " operator reconciles it outside the fabric (D-IMPL-378;"
                    " SEC-001)"
                ),
            )
        if record.status == "suspended":
            # SEC-001: a gate opens on a human action returned through the
            # HITL authority path, never on the caller's decision string.
            # The authority is bound to THIS suspension, so one approval
            # authorizes exactly the passage it was taken against
            # (CLAUDE.md §8.2 audit-by-construction).
            #
            # The check is UNCONDITIONAL on the suspended branch, and that
            # is the whole of its integrity. ``status == "suspended"`` is
            # written in exactly one place — :meth:`_suspend`, reachable
            # only from a ``hitl-gate`` step — so a suspended record IS a
            # gate suspension, as a fact the fabric recorded about itself.
            # The first version of this fix asked
            # ``_is_gate(workflow, record.current_state)`` instead, reading
            # the kind out of the CALLER'S handle. That was walk-around-able
            # and was demonstrated: ``definition_uri`` is built from the
            # artifact's own declared tenant, name and artifact_version, so
            # a second definition registered under a different key carries
            # the same URI, and one whose task calls the gate node an
            # ordinary step skipped this block entirely and completed the
            # workflow with the approval still pending and
            # ``resolved=True, actor=None`` in the audit — the exact
            # signature SEC-001 named. Never ask the caller what kind of
            # node the fabric is waiting on.
            # D-IMPL-378: ONE read of the recorded verdicts, from which the
            # authority, the conflict population and the count the gate's
            # closure is judged against are all derived.
            snapshot = self._hitl_transport.submissions(tenant=tenant)
            qualifying = self._gate_authority(
                tenant=tenant,
                key=key,
                gate=record.current_state,
                record=record,
                workflow=workflow,
                snapshot=snapshot,
            )
            if not qualifying:
                return self._refuse(
                    authorized,
                    workflow,
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
            # Selection is UNCHANGED (D-IMPL-357 A4): the head of the
            # eligible tuple is the submission the single-submission form
            # returned, because ``submissions`` is oldest-first. What changed
            # is that selection no longer runs alone — the verdicts recorded
            # against this suspension must not disagree before one of them is
            # allowed to route.
            authority = qualifying[0]
            actor: str | None = authority.principal.approver.subject_id
            recorded = self._recorded_gate_verdicts(
                tenant=tenant,
                key=key,
                gate=record.current_state,
                record=record,
                snapshot=snapshot,
            )
            if len({submission.action for submission in recorded}) > 1:
                # D-IMPL-357 A4: two distinct human verdicts on ONE
                # suspension. Ordered ahead of the declared-target and route
                # compares deliberately — with the contradicting verdict at
                # the head of the eligible tuple the route compare would
                # refuse on its own, and the record would then say a caller
                # named the wrong transition rather than that two humans
                # disagreed. Names NEITHER verdict and NEITHER target
                # (SEC-001 remedy 3); the audit event carries the rule and
                # the approver selection reached, for the reader who is
                # entitled to them.
                return self._refuse(
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    reason=(
                        f"execution {key!r} carries conflicting human"
                        f" verdicts on gate {record.current_state!r}; a gate"
                        " routes on one recorded verdict and the fabric will"
                        " not choose between two, and it offers no primitive"
                        " for reconciling a conflicted suspension, so this"
                        " gate stays suspended until the disagreement is"
                        " settled operationally, outside the fabric"
                        " (D-IMPL-357 A4; CLAUDE.md §8.2)"
                    ),
                    verdict_integrity="conflicting_verdicts",
                    recorded_approver=actor,
                )
            targets = self._targets(workflow, record.current_state)
            if decision not in targets:
                return self._refuse(
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    reason=(
                        f"decision {decision!r} names no declared transition"
                        f" target from {record.current_state!r}; routing is"
                        " interpreted from the artifact only (CINV-01;"
                        " CLAUDE.md §8.1)"
                    ),
                )
            route = workflow.definition.gate_routes.get(record.current_state, {}).get(
                authority.action
            )
            if route is None or decision != route:
                # D-IMPL-357 A3/A4: the artifact declares where the recorded
                # verdict goes; the caller's decision is a double-entry that
                # must agree. Names NEITHER the verdict nor the route (remedy 3:
                # the refusal never answers the caller's question for them).
                #
                # ``.get(..., {}).get(...)`` and not an index, deliberately
                # — now as disclosed defense-in-depth rather than as live
                # coverage. The shape that motivated it was a gate which is
                # both the start node and a declared terminal state: the
                # factory's completeness population subtracts terminal
                # states, so no route map was required, the A1 validator
                # forbade declaring one, and ``_advance`` suspends on the
                # step's kind before any terminal test — so such a gate
                # could hold a resume, and an unguarded index would raise
                # where a typed refusal is owed. D-IMPL-357 A2 (review round
                # 1, item 7) now REFUSES that construction outright, in
                # either position, so ``route is None`` is structurally
                # unreachable with a usable target rather than merely
                # improbable. No behavioral test can distinguish this from a
                # plain index; it stands so that no later edit of this path
                # reaches an unguarded one.
                return self._refuse(
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    reason=(
                        f"decision {decision!r} does not agree with the route"
                        " the workflow definition declares for the verdict"
                        " the HITL authority path recorded on"
                        f" {record.current_state!r}; routing is interpreted"
                        " from the artifact only (CINV-01; D-IMPL-357)"
                    ),
                    verdict_integrity="route_disagreement",
                    recorded_approver=actor,
                )
            # D-IMPL-378: decide the gate ONCE, on exactly the verdicts judged
            # above, in the authority path's own atomic step. A verdict recorded
            # since the read changes the count and the decision fails; one
            # arriving after it is refused by name at every door; another
            # passage cannot take the closure.
            event_key = self._event_key(key, record.current_state)
            suspension = content_hash(record)
            observed = sum(
                1
                for submission in snapshot
                if submission.event_key == event_key
                and submission.principal.product_content_hash == suspension
            )
            # The passage is named by WHAT it decides — this suspension, this
            # authority submission, this verdict — never by who decides it. A
            # retry of a passage whose commit never landed re-presents the same
            # name, so the gate's closure (the durable claim on the authority
            # path) is re-taken idempotently, and the conditional passage
            # commit below lets exactly one attempt land (D-IMPL-378, Q4).
            passage = content_hash(
                {
                    "suspension": suspension,
                    "authority": content_hash(authority),
                    "action": authority.action,
                }
            )
            try:
                self._hitl_transport.close_gate(
                    authorized,
                    event_key=event_key,
                    product_content_hash=suspension,
                    passage=passage,
                    decided_action=authority.action,
                    decided_by=authority.principal.approver.subject_id,
                    observed_submissions=observed,
                )
            except GateAlreadyClosed:
                return self._refuse(
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    reason=(
                        f"the gate {record.current_state!r} of execution"
                        f" {key!r} was already decided by another passage; one"
                        " approval authorizes one passage (D-IMPL-378; SEC-001)"
                    ),
                )
            except GateVerdictsChanged:
                return self._refuse(
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    reason=(
                        f"a verdict on gate {record.current_state!r} of"
                        f" execution {key!r} was recorded while this resumption"
                        " was deciding, so nothing was decided; present the"
                        " resumption again and it judges the verdicts that now"
                        " stand (D-IMPL-378; D-IMPL-357 A4)"
                    ),
                )
            trace = record.trace + (
                self._entry(
                    record.trace, record.current_state, decision, "resume"
                ),
            )
            # D-IMPL-378: the passage — the record leaving the gate — and its
            # attributed row are ONE audited write, committed conditionally on
            # the version read, BEFORE the step after the gate runs. Of two
            # resumptions anywhere, exactly one commit lands; a refused or
            # failed commit appends no row.
            try:
                version = self._write_state(
                    authorized,
                    workflow,
                    key,
                    self._record(
                        workflow,
                        tenant=tenant,
                        execution_id=execution_id,
                        current_state=decision,
                        status="running",
                        trace=trace,
                        started_by=record.started_by,
                    ),
                    action="workflow_resumed",
                    actor=actor,
                    expected_version=version,
                )
            except StateConflict:
                return self._refuse(
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    reason=(
                        f"execution {key!r} moved while this resumption decided"
                        " its gate; the passage that moved it stands, and one"
                        " approval authorizes one passage (D-IMPL-378; SEC-001)"
                    ),
                )
            if decision in workflow.definition.effective_terminal_states:
                return self._complete(
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    terminal_state=decision,
                    trace=trace,
                    started_by=record.started_by,
                    version=version,
                )
            return await self._advance(
                authorized,
                workflow,
                execution_id=execution_id,
                state=decision,
                trace=trace,
                started_by=record.started_by,
                version=version,
            )
        # exception-routed: the handler handed the state back — retry the
        # node it was routed from.
        #
        # SEC-001, one branch over. This path used to advance with NO
        # authority check at all and audit ``resolved=True, actor=None`` —
        # the exact signature the finding named — on the reading that an
        # exception path "crosses no gate, so it acquires no approver".
        # :meth:`_route_exception` really does enqueue nothing, but
        # :class:`~ccf.hitl.escalation.ExceptionEscalation` is the shipped
        # primitive FOR a routed state (CLAUDE.md §8.2), and a deployment
        # that composes it puts a human in the loop that the engine then
        # walked straight past.
        #
        # Applicability is the fabric's recorded fact, never the caller's:
        # an escalation is in force iff the transport HOLDS a pending
        # ``exception-escalation`` event bound to this execution's own
        # state key. The resume caller supplies nothing that decides
        # whether this runs — the key is derived from the record the state
        # store returned — and a deployment that composes no escalation
        # has no such event and is unaffected.
        if self._escalation_pending(tenant=tenant, key=key):
            return self._refuse(
                authorized,
                workflow,
                execution_id=execution_id,
                reason=(
                    f"execution {key!r} was routed to an exception path and"
                    " an escalation of this state is still open on the HITL"
                    " authority path; the designated role has not acted, and"
                    " retrying the node would spend their decision before"
                    " they made it (CLAUDE.md §8.2; D-IMPL-20)"
                ),
            )
        resolution = self._escalation_authority(
            tenant=tenant, key=key, record=record
        )
        # D-IMPL-378: the retry of the routed node is a passage too, committed
        # conditionally before the node runs, so two resumptions of one
        # exception-routed execution cannot both re-run it.
        try:
            version = self._write_state(
                authorized,
                workflow,
                key,
                self._record(
                    workflow,
                    tenant=tenant,
                    execution_id=execution_id,
                    current_state=record.current_state,
                    status="running",
                    trace=record.trace,
                    started_by=record.started_by,
                ),
                action="workflow_resumed",
                actor=(
                    None
                    if resolution is None
                    else resolution.principal.approver.subject_id
                ),
                expected_version=version,
            )
        except StateConflict:
            return self._refuse(
                authorized,
                workflow,
                execution_id=execution_id,
                reason=(
                    f"execution {key!r} moved while this resumption decided its"
                    " retry; the passage that moved it stands (D-IMPL-378;"
                    " SEC-001)"
                ),
            )
        return await self._advance(
            authorized,
            workflow,
            execution_id=execution_id,
            state=record.current_state,
            trace=record.trace,
            started_by=record.started_by,
            version=version,
        )

    # -- the machine ----------------------------------------------------------

    async def _advance(
        self,
        authorized: Authorized[Execute] | Authorized[Resume],
        workflow: Workflow,
        *,
        execution_id: str,
        state: str,
        trace: tuple[TraceEntry, ...],
        started_by: str | None,
        version: int,
    ) -> WorkflowOutcome:
        """Drive the machine from ``state`` until suspend or terminal.

        ``version`` is the state record's version this passage wrote
        (``D-IMPL-378``); the one write this drive ends in is conditional on
        it.

        ``started_by`` is the starter recorded for this execution (SEC-006;
        `D-IMPL-366` G1 (a)), threaded unchanged into every record and every
        gate event this drive produces.

        The tenant is read from the capability and nowhere else (§1.3).
        """
        tenant = authorized.tenant
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
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    gate=state,
                    trace=trace,
                    started_by=started_by,
                    version=version,
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
                        authorized,
                        workflow,
                        execution_id=execution_id,
                        node=state,
                        trace=trace,
                        started_by=started_by,
                        version=version,
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
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    node=state,
                    trace=trace,
                    started_by=started_by,
                    version=version,
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
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    terminal_state=target,
                    trace=trace,
                    started_by=started_by,
                    version=version,
                )
            state = target

    def _suspend(
        self,
        authorized: Authorized[Execute] | Authorized[Resume],
        workflow: Workflow,
        *,
        execution_id: str,
        gate: str,
        trace: tuple[TraceEntry, ...],
        started_by: str | None,
        version: int,
    ) -> WorkflowSuspended:
        """Suspend on a hitl-gate: persist, enqueue, return a typed handle.

        The record, the state key, the trace artifact and the pending HITL
        event are all filed under ``authorized.tenant`` (§1.3).
        """
        tenant = authorized.tenant
        key = self._key(tenant, execution_id)
        trace = trace + (self._entry(trace, gate, gate, "suspend"),)
        record = self._record(
            workflow,
            tenant=tenant,
            execution_id=execution_id,
            current_state=gate,
            status="suspended",
            trace=trace,
            started_by=started_by,
        )
        self._fenced_write(
            authorized, workflow, key, record, action="workflow_suspended", version=version
        )
        trace_artifact = self._write_trace(authorized, key, execution_id, trace)
        event_key = self._event_key(key, gate)
        self._hitl_transport.enqueue(
            event=PendingHitlEvent(
                event_key=event_key,
                event_class=GATE_EVENT_CLASS,
                tenant=tenant,
                workflow_state_ref=key,
                product_content_hash=content_hash(record),
                policy_ref=workflow.definition.gate_policies.get(gate),
                # SEC-006 (D-IMPL-366 G1 (a)): the requester is the starter.
                requested_by=started_by,
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
        authorized: Authorized[Execute] | Authorized[Resume],
        workflow: Workflow,
        *,
        execution_id: str,
        node: str,
        trace: tuple[TraceEntry, ...],
        started_by: str | None,
        version: int,
    ) -> WorkflowOutcome:
        """Take ``node``'s exception path (D-13; D-IMPL-61 option-a)."""
        tenant = authorized.tenant
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
                started_by=started_by,
            )
            self._fenced_write(
                authorized, workflow, key, record, action="workflow_exception", version=version
            )
            trace_artifact = self._write_trace(
                authorized, key, execution_id, trace
            )
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
            authorized,
            workflow,
            execution_id=execution_id,
            terminal_state=WORKFLOW_FAILED_STATE,
            trace=trace,
            started_by=started_by,
            version=version,
        )

    def _complete(
        self,
        authorized: Authorized[Execute] | Authorized[Resume],
        workflow: Workflow,
        *,
        execution_id: str,
        terminal_state: str,
        trace: tuple[TraceEntry, ...],
        started_by: str | None,
        version: int,
    ) -> WorkflowCompleted:
        """Reach a terminal condition: persist, write through, hand to replay."""
        tenant = authorized.tenant
        key = self._key(tenant, execution_id)
        record = self._record(
            workflow,
            tenant=tenant,
            execution_id=execution_id,
            current_state=terminal_state,
            status="terminal",
            trace=trace,
            started_by=started_by,
        )
        self._fenced_write(
            authorized, workflow, key, record, action="workflow_completed", version=version
        )
        trace_artifact = self._write_trace(authorized, key, execution_id, trace)
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
        """The state key an execution lives under — the seam's own derivation.

        :func:`~ccf.controlplane.state.state_key` rather than a local
        f-string (D-IMPL-353 §1.3): the state store derives the key it writes
        under from the capability's tenant and the record id, and the engine's
        reads must derive the same key the same way or a suspended execution
        could be written under one key and looked for under another. Every
        caller passes ``authorized.tenant``; the injectivity rules (a tenant
        may not carry the separator) are the seam's, stated once.
        """
        return state_key(tenant=tenant, record_id=execution_id)

    @staticmethod
    def _event_key(key: str, gate: str) -> str:
        """The pending-event key a gate suspension enqueues under."""
        return f"{key}/{gate}"

    def _gate_authority(
        self,
        *,
        tenant: str,
        key: str,
        gate: str,
        record: WorkflowStateRecord,
        workflow: Workflow,
        snapshot: tuple[HitlActionSubmission, ...],
    ) -> tuple[HitlActionSubmission, ...]:
        """Every recorded human verdict ELIGIBLE to authorize passage past ``gate``.

        SEC-001. Reads the HITL transport's authority path — the only
        surface a human action returns through (D-IMPL-20) — and returns
        the submissions that may authorize THIS suspension, oldest first, or
        an empty tuple.

        **Eligibility only; it decides nothing about agreement**
        (D-IMPL-357 A4). The caller selects the authority from the head of
        this tuple, exactly as the single-submission form selected it, and
        asks :meth:`_recorded_gate_verdicts` — a deliberately BROADER
        population — whether the verdicts recorded against this suspension
        disagree. The two questions cannot share one predicate: the rules
        below are what make a verdict *routable*, and a verdict that is not
        routable can still be a recorded human decision that contradicts
        the one that is. Reading agreement off this tuple would leave the
        transport's stamp race wide open, because the racing officer's
        rejection is recorded unstamped and fails the unstamped leg.

        Three conditions, all necessary:

        * the submission names this gate's pending event. **A backstop,
          not the load-bearing check** — two suspensions differ in at
          least ``execution_id`` or ``current_state``, so the hash below
          already separates them and severing this line reddens nothing.
          Kept because it is what a reader expects to see, and stated so
          nobody mistakes it for the guard that is doing the work;
        * **(load-bearing)** its principal echoes ``content_hash(record)``
          — the suspension's
          own identity, which is what the pending event bound at suspend
          time and what :class:`~ccf.hitl.approval_gate.ApprovalGate`
          already makes the approver attest to (T-07-39). A suspension's
          trace is unique to it, so an approval cannot be replayed onto
          another execution, another tenant, or a later suspension of the
          same gate. This is what refuses a submission made through the
          submit-only action door (D-IMPL-62), which compares no hashes of
          its own;
        * the action is an approval-gate verdict. Both verdicts authorize
          the engine to leave the gate — a rejection routes to whichever
          target the artifact declares for it, which is why the check is
          ``in GATE_ACTIONS`` and not ``== GATE_APPROVE``;
        * **(added by the 2026-09-24 follow-up read)** an approval gate is
          what the action answered. A submission carries the same two
          verdicts as
          :data:`~ccf.hitl.escalation.ESCALATION_ACTIONS`, so before this
          the three conditions above could all be met by a human action
          taken against a *different* primitive's event that happened to
          name this event key — a reachable composition, because handing a
          stuck gate to
          :class:`~ccf.hitl.escalation.ExceptionEscalation` is what that
          primitive is for, and the duty officer who takes the hand-off has
          not approved the credit.

        **Why the answered-class test has two legs, and what decides which
        one runs.** Not the caller: the submission's own
        ``answered_event_class`` does, and the transport — not the
        submitter — writes it (see
        :class:`~ccf.hitl.transport.HitlActionSubmission`).

        * **Stamped.** Some primitive claimed an event through
          :meth:`~ccf.hitl.transport.HITLTransportProtocol.remove` before
          submitting. The class it claimed must be
          :data:`~ccf.hitl.approval_gate.GATE_EVENT_CLASS` and the claimed
          event must have been bound to this execution's state key. This is
          the leg that refuses the escalation-answered action above.
          :meth:`~ccf.hitl.approval_gate.ApprovalGate.resolve` consumes the
          pending event, so by resume time this is the ONLY leg a
          gate-resolved approval can take — which is why the class cannot
          simply be read off the pending queue.
        * **Unstamped.** Nothing was claimed: the shape the submit-only
          action door produces (D-IMPL-62 — it records and resolves
          nothing). Then the join is to the gate's own event, which is
          still pending precisely because nothing resolved it, and its
          class must be ``GATE_EVENT_CLASS``. Both terms are the engine's
          own: the event key is minted by :meth:`_event_key` and the class
          was written by :meth:`_suspend`.

        **The residual that leaves, stated so it is not read as closed.**
        The unstamped leg accepts an action that the ApprovalGate primitive
        never resolved — so the gate's TOCTOU guard and its signed-binding
        enforcement did not run, only the transport's own D-16 leg did.
        That path is not anonymous (the door derives the principal from a
        verified token grant, D-IMPL-67, and the hash binding above still
        holds), but it is weaker than a gate resolution, and closing it
        means giving the door a *resolve* route rather than a submit-only
        one — a change to D-IMPL-62's ruled contract and to
        ``runtime/ccf_runtime/http_api/routes/hitl.py``, not something this
        module may decide alone.

        **The verdict→target binding, and exactly how far it closes.**
        Declared on the artifact as ``gate_routes`` (D-IMPL-357 A1) and
        enforced in :meth:`resume` after the declared-target check, pinned
        by ``tests/workflow/test_engine.py::
        test_a_recorded_rejection_cannot_be_routed_down_the_approving_branch``.
        Given one recorded human action, the caller's decision must agree
        with the target the artifact declares for the verdict that action
        carries.

        **No verdict recorded on this suspension is outvoted by a passage**
        (``D-IMPL-378``). A verdict recorded before the resumption reads the
        verdicts is in the population judged here and refuses the resumption if
        it disagrees (``D-IMPL-357`` A3 + A4); one recorded after that read and
        before the decision makes the gate's closure fail, and the resumption
        is refused; one arriving after the closure is refused at the door
        (``hitl-gate-closed``). Routing is the compare in :meth:`resume`;
        selection integrity is the conflict refusal over
        :meth:`_recorded_gate_verdicts`; timing integrity is the closure. The
        paths A3's review measured are shut, and each was measured again going
        red:

        * **Two distinct verdicts on one suspension** no longer resolve to
          the oldest and route on it. They refuse, in either arrival order,
          and the refusal is ordered ahead of the route compare so the
          record says two humans disagreed rather than that a caller named
          the wrong transition. Pinned in process and through the served
          doors.
        * **The transport's stamp race** no longer decides a verdict. Its
          recorded end state — one stamped verdict and one unstamped
          opposite verdict on the same suspension — is precisely what
          :meth:`_recorded_gate_verdicts` refuses, which is why that
          population is deliberately unfiltered by eligibility.

        **What remains OPEN, stated here because this docstring is the
        residual ledger a close panel, an adopter and the next maintainer
        read.**

        * **(1) The stamp race itself is still there, in the transport.**
          A claim is keyed ``(tenant, event_key)`` and consumed by whichever
          submission for that pair arrives first, so an attacker holding
          submit authority can still cause an officer's verdict to be
          recorded unstamped. What changed is the consequence: the pair now
          REFUSES and demands human reconciliation instead of routing on
          the attacker's verdict. So the race has become an availability
          problem — anyone with submit authority for the event can park a
          contradicting verdict and hold the gate until a human
          reconciles — rather than an integrity one. Closing it means
          ``remove`` minting an opaque claim token that ``submit``
          requires, a :class:`~ccf.hitl.transport.HITLTransportProtocol`
          signature change that belongs with the D-IMPL-62 door ruling.
        * **(2) A conflicted gate stays suspended for good** (``D-GATE-357``
          (2)). The fabric offers no primitive that reopens it; a human settles
          the disagreement outside the fabric.
        * **(3) An interrupted passage stays ``running`` for good.** It is
          never retried (Dave's ruling on ``D-IMPL-378``), and the fabric
          offers no primitive that reconciles it; an operator reads the gate's
          closure (:meth:`~ccf.hitl.transport.HITLTransportProtocol.closures`)
          and the audit row, and reconciles outside the fabric.
        * **(4) The guarantees are the store's and the transport's.** They
          hold over a :class:`~ccf.controlplane.state.ConditionalStateStore`
          and a transport whose ``close_gate`` and ``submit`` are atomic with
          respect to each other, as the reference implementations are. The
          engine refuses at construction an implementation that offers neither
          the methods nor a declared scope; it cannot see whether a
          third-party implementation keeps the atomicity it declares —
          ``tests/conformance/test_gate_closure_and_conditional_write.py`` is
          the suite a deployment runs against its own.

        **What the closure replaced, carried so it is not re-derived.**
        Before ``D-IMPL-378`` the read-decide-commit was atomic only against
        other resumptions in one process. Measured on 2026-10-07: two
        resumptions through two state-store objects over one durable store
        both passed the gate on one approval; a rejection recorded right
        after the resumption's last read of the verdicts was outvoted
        (15 of 15 forced-timing runs), and so was one recorded through the
        served action door while the step after the gate ran. A second read
        before the commit was rejected as a fix: it narrows the window and
        invites a reader to think the class is handled, and when the step
        after the gate has already run there is nothing left to refuse.

        The bound on the claim above is deliberate, because this project
        has already paid once for stating it wider: an earlier fix on this
        same vulnerability was reported complete, and the close panel on
        the follow-on work reproduced the CRITICAL finding with that fix
        in place.

        Note the direction of trust: the engine *reads* the authority path
        and never writes a verdict to it. The one thing it records there is
        the gate's closure (``D-IMPL-378``), which decides no verdict: it
        freezes the verdicts the engine judged. Resolution stays the gate
        primitive's act (CLAUDE.md §8.2).
        """
        event_key = self._event_key(key, gate)
        suspension = content_hash(record)
        gate_still_pending = any(
            event.event_key == event_key
            and event.event_class == GATE_EVENT_CLASS
            for event in self._hitl_transport.pending(tenant=tenant)
        )
        # SEC-006 (D-IMPL-366 §4 (4)): the engine site is the BACKSTOP for
        # every path — eligibility judged inside the per-submission predicate,
        # before the conflict count in `resume`, against the definition's
        # pinned gate policy and the RECORD's starter (the engine holds no
        # event here). The engine's Control Plane is always bound, so a gate
        # with no policy, an unresolvable or wrong-class policy, or a record
        # with no starter (an in-flight pre-change suspension, G5 (a)) admits
        # nothing: fail-closed by ruling.
        policy_ref = workflow.definition.gate_policies.get(gate)

        def eligible(submission: HitlActionSubmission) -> bool:
            try:
                check_approver_eligibility(
                    policy_ref=policy_ref,
                    requested_by=record.started_by,
                    subject_id=submission.principal.approver.subject_id,
                    control_plane=self._control_plane,
                )
            except ApproverNotEligible:
                return False
            return True

        return tuple(
            submission
            for submission in snapshot
            if submission.event_key == event_key
            and submission.principal.product_content_hash == suspension
            and submission.action in GATE_ACTIONS
            # D-IMPL-366 H2 (RULED): a submission recorded while NO event was
            # under its key is never authority — whatever is pending now.
            and submission.event_state_at_submit != "missing"
            and (
                submission.answered_event_class == GATE_EVENT_CLASS
                and submission.answered_workflow_state_ref == key
                if submission.answered_event_class is not None
                # The unstamped leg: a door submission recorded against a
                # PENDING event keeps today's semantics, and so does a
                # pre-change record (None) — the fixture rule.
                else submission.event_state_at_submit in (None, "pending")
                and gate_still_pending
            )
            and eligible(submission)
        )

    def _recorded_gate_verdicts(
        self,
        *,
        tenant: str,
        key: str,
        gate: str,
        record: WorkflowStateRecord,
        snapshot: tuple[HitlActionSubmission, ...],
    ) -> tuple[HitlActionSubmission, ...]:
        """Every gate verdict RECORDED against this suspension, oldest first.

        D-IMPL-357 A4, and the population is broader than
        :meth:`_gate_authority`'s on purpose: every submission naming this
        gate's pending event, bound to this suspension's own content hash,
        carrying a :data:`~ccf.hitl.approval_gate.GATE_ACTIONS` verdict —
        **stamped or not, eligible to be the authority or not.** The caller
        refuses the resumption when the distinct verdicts here number more
        than one.

        **Why eligibility is deliberately not applied.** Round 1 of A4's
        review measured the sequence that walks straight through a
        predicate that does apply it. A credit officer resolves the gate
        ``reject``, which REMOVES the pending claim and then submits; an
        attacker holding submit authority for the same event lands
        ``approve`` in that window; the transport stamps whichever submit
        arrives first (documented at
        :meth:`~ccf.hitl.transport.HITLTransportProtocol.submit`), so the
        attacker's verdict takes the stamp and the officer's is recorded
        UNSTAMPED. The gate is no longer pending, so the officer's
        rejection fails the unstamped leg and is not eligible at all — and
        an eligibility-filtered verdict set then has exactly one member,
        detects no conflict, and the routing compare faithfully agrees with
        the attacker. Raced for real: **823 of 3000 executions succeeded
        with four attacker threads.** Filtering nothing here is what closes
        it, without weakening what selection requires of an authority.

        **The suspension hash stays in the predicate**, and it is what
        keeps this from over-refusing: a verdict recorded against an
        EARLIER suspension of the same gate — a loop, an exception route
        and a re-suspension — carries that suspension's content hash and is
        correctly invisible here. Dropping it would let a resolved
        disagreement poison every later suspension of the same node
        forever.

        **The event-key term is a BACKSTOP, not the load-bearing check** —
        the same disclosure :meth:`_gate_authority` carries for its own copy
        of this term, restated here so this predicate's reader does not have
        to infer it. Two suspensions differ in at least ``execution_id`` or
        ``current_state``, so the suspension hash above already separates
        them, and dropping this line reddens nothing across
        ``tests/workflow`` and ``tests/http_api/test_routes.py``. Measured,
        not assumed. Kept because it is what a reader expects to see, and
        stated so nobody mistakes it for the guard doing the work.

        **The verdict-vocabulary term, by contrast, IS load-bearing and is
        pinned** — by ``tests/workflow/test_engine.py::
        test_an_annotation_and_an_override_beside_an_approval_still_route``.
        :data:`~ccf.hitl.transport.HITL_ACTIONS` carries ``override`` and
        ``annotate`` alongside the two gate verdicts, so without ``action in
        GATE_ACTIONS`` either of those bound to this suspension would count
        as a distinct verdict and wedge the gate. That failure direction is
        over-refusal rather than bypass, which is exactly why it could sit
        here unpinned — and it is still a denial of service on approvals,
        the mirror image of the vulnerability this task closes.

        **What it costs, stated rather than assumed.** Agreeing submissions
        carry one distinct verdict, so nothing that previously proceeded on
        agreement now refuses — a second approver recording the same
        verdict (D-23 quorum) is unaffected. The one real behavior change
        is the intended one: where a verdict was recorded that never became
        the authority and the opposite verdict was then recorded, the
        resumption previously proceeded on whichever one selection reached
        and now refuses. A bank's answer to *two humans recorded opposite
        verdicts on one decision* is to stop and require reconciliation,
        not to resolve silently in favor of whichever one won a race.

        A verdict recorded against a DIFFERENT primitive's event that
        happens to name this event key and this suspension hash — the
        escalation composition :meth:`_gate_authority` describes — counts
        here even though it can never be the authority. That is the same
        ruling applied consistently: it is a recorded human decision about
        this suspension, and if it contradicts the routable one the fabric
        does not get to pick.
        """
        event_key = self._event_key(key, gate)
        suspension = content_hash(record)
        return tuple(
            submission
            for submission in snapshot
            if submission.event_key == event_key
            and submission.principal.product_content_hash == suspension
            and submission.action in GATE_ACTIONS
        )

    def _escalation_pending(self, *, tenant: str, key: str) -> bool:
        """Whether an unanswered escalation of ``key`` is on the transport.

        SEC-001 Tier 0, the exception-routed branch's applicability test
        (CLAUDE.md §8.2; D-IMPL-20). True iff the HITL transport HOLDS a
        pending :data:`~ccf.hitl.escalation.ESCALATION_EVENT_CLASS` event
        whose ``workflow_state_ref`` is this execution's own state key.

        Every term is a fact the fabric recorded about itself. ``key`` is
        derived from the tenant the artifact declares and the execution id
        the state store answered under; the event class and the state ref
        were written by
        :meth:`~ccf.hitl.escalation.ExceptionEscalation.escalate` at
        hand-off. The resume caller declares, sends and omits nothing that
        reaches this test — which is the lesson the first SEC-001 fix
        taught at cost (a guard whose applicability the caller decides is
        not a guard).

        Pending is the right state to read because resolution *consumes*
        the event: every shipped primitive claims through
        :meth:`~ccf.hitl.transport.HITLTransportProtocol.remove` before it
        submits, so an event that is still pending is an unanswered one. A
        deployment that composes no escalation holds no such event and is
        unaffected — pinned by ``test_an_exception_routed_resume_without_
        escalation_is_unaffected``.

        **The escalation leg's OWN remaining gap — no longer the gate's**
        (D-IMPL-357 A4). The gate's verdict→target residual is closed to
        the bound :meth:`_gate_authority`'s ledger states — read it there
        rather than inferring an unconditional close from this sentence:
        ``gate_routes`` declares where each verdict goes (A1), the route
        compare enforces it (A3), and conflicting verdicts recorded before
        the resumption's own read refuse (A4). None of that reaches here,
        because
        ``gate_routes`` is keyed by the two
        :data:`~ccf.hitl.approval_gate.GATE_ACTIONS` verdicts on a gate
        NODE, and an escalation is a hold on an exception-routed state
        rather than a gate. So for this leg it remains true that either
        :data:`~ccf.hitl.escalation.ESCALATION_ACTIONS` verdict releases
        the hold: a declined hand-off is still a recorded human decision
        about this state, and nothing a
        :class:`~ccf.workflow.definitions.WorkflowDefinition` carries maps
        an escalation verdict to a route. What the SEC-001 work did change
        here is that some human must have acted on this routing at all, and
        the audit names them.

        This is stated rather than deleted because it is a distinct open
        question with a distinct answer: declaring escalation routes would
        be a new generation of the workflow contract (the shape A1 took for
        gates), and whether a declined hand-off should route somewhere
        other than a retry of the same node is a ruling nobody has made.
        """
        return any(
            event.event_class == ESCALATION_EVENT_CLASS
            and event.workflow_state_ref == key
            for event in self._hitl_transport.pending(tenant=tenant)
        )

    def _escalation_authority(
        self, *, tenant: str, key: str, record: WorkflowStateRecord
    ) -> HitlActionSubmission | None:
        """The recorded human action that released this routed state.

        SEC-001 Tier 0. The attribution half of the exception-routed
        branch: :meth:`_escalation_pending` decides whether the resume may
        proceed, this decides whose name the audit carries. ``None`` is the
        honest answer for a deployment that composed no escalation — the
        audit then states positively that no human acted, which
        :meth:`_append`'s defaultless ``actor`` keyword forces every call
        site to do.

        Three conditions, all read off recorded facts:

        * the transport stamped the submission as answering an
          ``exception-escalation`` — its own observation of which event was
          claimed, overwritten on every submit and therefore not something
          a submitter can assert about itself (the submit-only action door,
          D-IMPL-62, claims nothing and is stamped ``None``);
        * the claimed event was bound to THIS execution's state key, which
          the escalating deployment stated at hand-off and the engine
          re-derives here — so one execution's escalation never attributes
          another's resume;
        * **(binding to the specific routing)** the resolver's principal
          echoes ``content_hash(record)``, the routed state's own identity,
          exactly as :meth:`_gate_authority` binds an approval to its
          suspension. A later routing of the same execution has a different
          trace and therefore a different hash.

        **Known residual, stated rather than implied.** The third condition
        holds only when the deployment hands
        :meth:`~ccf.hitl.escalation.ExceptionEscalation.escalate` the
        content hash of the routed :class:`WorkflowStateRecord` — the
        composition its own ``product_content_hash`` docstring describes
        ("the content hash of the state the human will review") and the one
        ``tests/workflow/test_exception_paths.py`` exercises. A deployment
        that binds some other hash still cannot resume past an OPEN
        escalation — that is :meth:`_escalation_pending`, which compares no
        hashes — but its resolver will not be named in the audit. Losing an
        attribution is not the same defect as losing the control, and the
        alternative (naming whoever last answered any escalation about this
        execution) would put a human's name against a decision that may not
        be theirs.
        """
        routing = content_hash(record)
        return next(
            (
                submission
                for submission in self._hitl_transport.submissions(
                    tenant=tenant
                )
                if submission.answered_event_class == ESCALATION_EVENT_CLASS
                and submission.answered_workflow_state_ref == key
                and submission.principal.product_content_hash == routing
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
        started_by: str | None,
    ) -> WorkflowStateRecord:
        return WorkflowStateRecord(
            tenant=tenant,
            execution_id=execution_id,
            current_state=current_state,
            status=status,
            trace=trace,
            workflow_definition_uri=workflow.identity.definition_uri,
            workflow_definition_hash=workflow.identity.definition_hash,
            started_by=started_by,
        )

    def _read_versioned(self, key: str) -> tuple[object | None, int]:
        """The execution's record and its version (``D-IMPL-378``)."""
        store = self._control_plane.state_store
        assert isinstance(store, ConditionalStateStore)  # refused at construction otherwise
        return store.get_versioned(WORKFLOW_STATE, key)

    def _write_state(
        self,
        authorized: Authorized[Execute] | Authorized[Resume],
        workflow: Workflow,
        key: str,
        record: WorkflowStateRecord,
        *,
        action: AuditAction,
        actor: str | None,
        expected_version: int,
    ) -> int:
        """Write state through the audited surface, conditionally — one write, one event.

        A DERIVED write (D-IMPL-353 §1.2, derived-writes rule): the state
        store derives the key it writes under from ``authorized.tenant`` and
        the execution id — the engine hands it the record id and the
        capability that authorized the run, and names no key and no tenant.
        ``key`` here is the engine's own reading of that same derivation
        (:meth:`_key`), used for the audit event and asserted equal to what
        the store derives, so the two cannot drift apart silently.

        The write is conditional on ``expected_version`` and the event is
        appended only when it lands (``D-IMPL-378``), so the audit log never
        records a transition the store did not take.

        Raises:
            StateConflict: the record moved since ``expected_version`` was read.
        """
        execution_id = key[len(authorized.tenant) + 1 :]
        assert self._key(authorized.tenant, execution_id) == key
        _, version = self._writer.write_if(
            authorized,
            WORKFLOW_STATE,
            record,
            record_id=execution_id,
            event=AuditEvent(
                sequence=0,  # reassigned by the log; sequencing is its own
                action=action,
                key=key,
                version=workflow.identity.definition_hash,
                resolved=True,
                occurred_at=self._clock(),
                actor=actor,
                artifact_class=WORKFLOW_DEFINITION.class_id,
            ),
            expected_version=expected_version,
        )
        return version

    def _fenced_write(
        self,
        authorized: Authorized[Execute] | Authorized[Resume],
        workflow: Workflow,
        key: str,
        record: WorkflowStateRecord,
        *,
        action: AuditAction,
        version: int,
    ) -> int:
        """A write that ends a passage, conditional on the version the passage wrote.

        ``D-IMPL-378``. A conflict here means a writer other than this passage
        moved the execution's record while the passage ran; fail closed
        (:class:`ExecutionFenced`).
        """
        try:
            return self._write_state(
                authorized,
                workflow,
                key,
                record,
                action=action,
                actor=None,
                expected_version=version,
            )
        except StateConflict as error:
            raise ExecutionFenced(
                f"execution {key!r} was moved by another writer while this"
                " passage ran; nothing was written (D-IMPL-378)"
            ) from error

    def _append(
        self,
        workflow: Workflow,
        key: str,
        *,
        action: AuditAction,
        resolved: bool,
        actor: str | None,
        verdict_integrity: WorkflowVerdictIntegrityFailure | None = None,
        recorded_approver: str | None = None,
    ) -> None:
        """Audit one transition that changes no persisted state.

        ``actor`` carries no default (SEC-001 remedy 2): every call site
        states who acted, or states positively that no human did. A default
        would let a gate resolution be audited with the approver silently
        omitted — the shape that let the pre-fix engine record
        ``resolved=True`` for an approval that never happened.

        ``verdict_integrity`` and ``recorded_approver`` DO default, because
        their absence is the ordinary case and the log's default event class
        is the honest record of it (D-IMPL-357 A4). Supplying the member
        makes the appended event a
        :class:`~ccf.controlplane.audit.WorkflowVerdictIntegrityAuditEvent`,
        which is how a refusal caused by a recorded human verdict stops
        being byte-identical to a caller's typo. They travel as a pair:
        every site that names a rule also names the approver it reached.
        """
        self._audit.append(
            action=action,
            key=key,
            version=workflow.identity.definition_hash,
            resolved=resolved,
            occurred_at=self._clock(),
            actor=actor,
            artifact_class=WORKFLOW_DEFINITION.class_id,
            workflow_verdict_integrity=verdict_integrity,
            workflow_recorded_approver=recorded_approver,
        )

    def _refuse(
        self,
        authorized: Authorized[Execute] | Authorized[Resume],
        workflow: Workflow,
        *,
        execution_id: str,
        reason: str,
        verdict_integrity: WorkflowVerdictIntegrityFailure | None = None,
        recorded_approver: str | None = None,
    ) -> WorkflowResumeRefused:
        """Return a typed refusal, audited ``resolved=False``.

        A refusal the caller's own request produced — no execution, a
        terminal one, a definition mismatch, no authority, an undeclared
        decision — audits with no actor, because no human's recorded
        verdict is what refused it.

        The two verdict-integrity refusals are different in kind and now
        different in the record (D-IMPL-357 A4): they refuse BECAUSE a
        human's verdict was recorded, so they name the rule and the
        approver, and the appended event is a
        :class:`~ccf.controlplane.audit.WorkflowVerdictIntegrityAuditEvent`.
        ``actor`` carries the same approver: the refusal row is not an
        attributed passage — ``resolved`` is ``False`` — but it IS about a
        human action, and an investigator filtering the log by actor must
        find it.
        """
        tenant = authorized.tenant
        self._append(
            workflow,
            self._key(tenant, execution_id),
            action="workflow_resumed",
            resolved=False,
            actor=recorded_approver,
            verdict_integrity=verdict_integrity,
            recorded_approver=recorded_approver,
        )
        return WorkflowResumeRefused(
            tenant=tenant, execution_id=execution_id, reason=reason
        )

    def _write_trace(
        self,
        authorized: Authorized[Execute] | Authorized[Resume],
        key: str,
        execution_id: str,
        trace: tuple[TraceEntry, ...],
    ) -> ArtifactRef:
        """Write the trace through to the ArtifactStore (D-IMPL-18).

        A DERIVED write (D-IMPL-353 §1.2): the engine names the record it
        produced — the trace class and the execution id — in a
        :class:`~ccf.artifacts.protocol.DerivedWrite`, presents the capability
        that authorized the run, and the store files it under
        ``authorized.tenant`` after verifying the capability against the kinds
        the deployment declared for the trace class. **The deployment must
        declare** :data:`WORKFLOW_TRACE_ARTIFACT_CLASS` **under**
        ``(Execute, Resume)`` in the store's
        :class:`~ccf.artifacts.protocol.WriteKinds`: a store that has not makes
        the class the client lane, and the engine's ``Execute``/``Resume``
        capability dies at the store's ``verify_any`` on the first trace write
        — fail closed, nothing filed, no execution reported as run.
        """
        del key  # the state key; the trace is named by the execution id alone
        return self._artifact_store.put(
            authorized,
            DerivedWrite(
                artifact_class=WORKFLOW_TRACE_ARTIFACT_CLASS,
                name=execution_id,
                artifact=trace,
            ),
        )
