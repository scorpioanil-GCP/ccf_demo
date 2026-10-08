"""The approval-gate limits the in-process resumption claim leaves open (D-IMPL-377).

RED BY DESIGN. ``docs/D-IMPL-377-CLOSE-OUT.md`` §4d lists what the
single-flight claim (``runtime/ccf_runtime/workflow/engine.py::_claim_resumption``)
does not cover, and the security page discloses it (SP §4.13). Dave's ruling
on those limits (2026-10-07): *"Disclosure alone does not close them."* Each
test below demonstrates one of them through the shipped engine and transport,
and fails today with the limit's own measures. They are evidence for the
reopening recommendation of lane 378-approval and acceptance tests for a fix
that is not yet ruled. They are NOT integration candidates, and no fix is
here.

* **(a) One approval, two passages, across state-store objects.** The claim
  is keyed by the identity of the Control Plane state-store object. Two
  processes over one durable store each hold their own store object, so their
  claims never meet. SIMULATED IN ONE PROCESS, and said so: two engines, each
  with its own Control Plane registry and its own state-store object, over one
  shared backing store (:class:`SharedBackingStore`, the stand-in for the
  database both processes reach), sharing one HITL transport (the stand-in
  for the shared authority path both processes must reach). That is the
  second clause of limit (a) exactly, and the same mechanism as two real
  processes, whose claim sets are two separate pieces of memory.
* **(b) The outvoted rejection.** A rejection recorded through the transport
  while a resumption is inside its read-decide-commit window is never seen:
  the execution completes at the approving terminal with both verdicts
  standing. Held inside the commit at the storage layer of the stand-in
  durable store (a database write is exactly where real time passes), not by
  wrapping an engine method.
* **(b') The verdict after the passage.** No race: on the submit-only door
  path nothing retires the gate's pending event when the gate is passed, so a
  verdict recorded after the execution completed is recorded as a verdict on
  an OPEN gate, the same end state (b) leaves. Found by this lane.
* **(c) ``execute`` has no single-flight.** Two concurrent starts of one
  execution id both pass the existence check and both run the start node.
* **(d) An attributed row for a passage that never committed.** A resumption
  whose commit fails, or that is cancelled, leaves an attributed
  ``workflow_resumed`` row while the record still says suspended at the gate.

**How these tests assert, and why not by a refusal's name.** No fix is ruled,
so no refusal mechanism exists to name. Each test asserts the hole's own end
state, the measures the close-out recorded, and each is protected from an
accidental green in three ways. (1) The overlap is constructed, not hoped for:
the second actor runs to completion while the first is held inside its window
at a seam, so a serialized run cannot occur. Every hold and every injected
failure sits at the STORAGE LAYER (:class:`StandInRecords`, the stand-in
database's records) or in a deployment binding, never on a store method's
name, so a fix that reads or writes through another method of the store is
still held and still judged. (2) A positive control shows the
same actor admitted when there is no overlap, so a refusal cannot come from a
broken composition. (3) A refusal of the second human's verdict by an identity,
eligibility or attestation guard is re-raised as an error, never counted as a
fix. When a fix is ruled, each test is finalized to also assert that fix's
refusal by name.

Composition reuses the suite's own helpers
(``tests/workflow/test_resume_single_flight.py``,
``tests/workflow/test_engine.py``,
``tests/workflow/test_sec006_engine_controls.py``). Test vocabulary only
(CINV-01).
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from ccf.authz.capability import CapabilityBypassError
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import InMemoryStateStore
from ccf.hitl.transport import (
    ApproverNotEligible,
    HitlActionSubmission,
    InMemoryHitlTransport,
    PrincipalMismatchRefused,
    SignedBindingInvalidRefused,
    SignedBindingMismatchRefused,
    SignedBindingRequiredRefused,
    SignedBindingStaleRefused,
)
from ccf.workflow.factory import Workflow
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowOutcome,
    WorkflowResumeRefused,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from tests.hitl.sec006_harness import execute_as_principal
from tests.workflow import test_engine as eh
from tests.workflow import test_sec006_engine_controls as s6
from tests.workflow.test_resume_single_flight import (
    APPROVER,
    DOWNSTREAM,
    EXECUTION,
    HOLD_SECONDS,
    NEXT_GATE,
    STARTER,
    BlockingOnceBindings,
    Worker,
    approved_suspension,
    engine_over,
    plane,
    resume,
)

#: The two-gate workflow's start node and its first gate.
START = "fetch-certificates"
FIRST_GATE = "first-approval"
#: The covenant workflow's gate, approving terminal, and two eligible officers
#: (``tests/fixtures/banking/approval_policies.yaml``).
COVENANT_GATE = "credit-officer-approval"
APPROVING_TERMINAL = "approved"
OFFICER_1 = "officer-1"
OFFICER_2 = "officer-2"
COVENANT_EXECUTION = "exec-b"

#: Refusals that come from WHO is acting, not from WHEN. A second human's
#: verdict refused by one of these means the test's control is broken, so the
#: tests re-raise them instead of reading them as a concurrency fix.
IDENTITY_REFUSALS: tuple[type[BaseException], ...] = (
    ApproverNotEligible,
    PrincipalMismatchRefused,
    CapabilityBypassError,
    SignedBindingRequiredRefused,
    SignedBindingInvalidRefused,
    SignedBindingMismatchRefused,
    SignedBindingStaleRefused,
)


# --- substrates -----------------------------------------------------------------


class StandInRecords(dict[tuple[str, str], object]):
    """The records of a stand-in durable store, able to hold or fail ONE access.

    A durable store's latency, and its failures, live in its storage, not in
    the names of its client's methods. So the holds and the injected failure
    sit here, under every read and write a reference-store client makes,
    whichever store method makes it:

    * :meth:`arm_read` holds the next read of one key, AFTER reading (a
      thread preempted between its read and its commit);
    * :meth:`arm_write` holds the next write whose value satisfies a
      predicate, BEFORE writing (a commit in flight);
    * :meth:`arm_failure` makes the next such write raise once, writing
      nothing (a store that refuses a commit).
    """

    def __init__(self) -> None:
        super().__init__()
        self._arm_lock = threading.Lock()
        self._read_key: tuple[str, str] | None = None
        self._hold_write: Callable[[tuple[str, str], object], bool] | None = None
        self._fail_write: Callable[[tuple[str, str], object], bool] | None = None
        self.held = threading.Event()
        self.release = threading.Event()

    def arm_read(self, record_class: str, key: str) -> None:
        with self._arm_lock:
            self._read_key = (record_class, key)

    def arm_write(self, predicate: Callable[[tuple[str, str], object], bool]) -> None:
        with self._arm_lock:
            self._hold_write = predicate

    def arm_failure(self, predicate: Callable[[tuple[str, str], object], bool]) -> None:
        with self._arm_lock:
            self._fail_write = predicate

    def _hold(self) -> None:
        self.held.set()
        if not self.release.wait(HOLD_SECONDS):
            raise RuntimeError("the held store access was never released")

    def _read_armed(self, key: object) -> bool:
        with self._arm_lock:
            armed = key == self._read_key
            if armed:
                self._read_key = None
        return armed

    def get(self, key: tuple[str, str], default: object = None) -> object:
        value = super().get(key, default)
        if self._read_armed(key):
            self._hold()
        return value

    def __getitem__(self, key: tuple[str, str]) -> object:
        value = super().__getitem__(key)
        if self._read_armed(key):
            self._hold()
        return value

    def __setitem__(self, key: tuple[str, str], value: object) -> None:
        with self._arm_lock:
            fail = self._fail_write is not None and self._fail_write(key, value)
            if fail:
                self._fail_write = None
            hold = not fail and self._hold_write is not None and self._hold_write(key, value)
            if hold:
                self._hold_write = None
        if fail:
            raise RuntimeError("state store unavailable")
        if hold:
            self._hold()
        super().__setitem__(key, value)


def workflow_write(key: tuple[str, str], value: object) -> bool:
    """Any write of a workflow-state record."""
    return key[0] == WORKFLOW_STATE


def terminal_write(key: tuple[str, str], value: object) -> bool:
    """A write of a workflow-state record whose status is ``terminal``."""
    return key[0] == WORKFLOW_STATE and getattr(value, "status", None) == "terminal"


class SharedBackingStore(InMemoryStateStore):
    """ONE PROCESS'S state-store object over a durable store several share.

    The durable store, a database every replica connects to, is stood in for
    by one :class:`StandInRecords` that every such object reads and writes.
    Each process holds its own client object, so the objects differ in
    identity while the records they return are the same records. That is the
    condition the single-flight claim cannot see, because it is keyed by the
    store object's identity
    (``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume``). Only
    where the records live changes: every proof the reference store runs on
    a write still runs, because every method is the reference store's own.
    """

    def __init__(self, records: StandInRecords) -> None:
        super().__init__()
        self._records = records


class AwaitingStartBindings(eh._Bindings):
    """The suite's node-binding double, except that the START node awaits once,
    as any real I/O-bound first step does. Nothing else differs."""

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        if step_name == START:
            await asyncio.sleep(0)
        return await super().run_skill(tenant=tenant, step_name=step_name, ref=ref)


# --- composition ----------------------------------------------------------------


@dataclass
class Process:
    """One deployment process: its own registry, engine and workflow handle."""

    registry: ControlPlaneRegistry
    engine: WorkflowEngine
    workflow: Workflow


def two_processes(
    tmp_path: Path,
    bindings: eh._Bindings,
    transport: InMemoryHitlTransport,
) -> tuple[Process, Process, StandInRecords]:
    """Two processes over one durable state store and one authority path.

    Each process registers the same two-gate release workflow in its own
    registry, as two replicas of one deployment would, so both handles carry
    the same definition identity. One node-binding double serves both: the
    step after the gate acts on one external system, whichever process runs it.
    """
    records = StandInRecords()
    processes = []
    for name, store in (("a", SharedBackingStore(records)), ("b", SharedBackingStore(records))):
        registry = plane(store)
        workflow = s6._two_gate(registry, eligible=frozenset({STARTER, APPROVER}))
        engine = engine_over(registry, tmp_path / f"process-{name}", bindings, transport)
        processes.append(Process(registry=registry, engine=engine, workflow=workflow))
    a, b = processes
    assert a.workflow.identity.definition_uri == b.workflow.identity.definition_uri
    assert a.workflow.identity.definition_hash == b.workflow.identity.definition_hash
    assert a.registry.state_store is not b.registry.state_store
    return a, b, records


def start_and_approve_once(a: Process, transport: InMemoryHitlTransport) -> str:
    """Start the run in process A and approve its first gate ONCE, through the
    real :class:`~ccf.hitl.approval_gate.ApprovalGate`. Returns the state key."""
    tenant = a.workflow.definition.tenant
    starter = execute_as_principal(
        tenant=tenant, resource=a.workflow.definition_key, principal=STARTER
    )
    suspended = asyncio.run(a.engine.execute(starter, a.workflow, execution_id=EXECUTION))
    assert isinstance(suspended, WorkflowSuspended)
    assert suspended.gate == FIRST_GATE
    eh._resolve_gate(
        a.registry,
        transport,
        tenant=tenant,
        event_key=suspended.event_key,
        action="approve",
        subject_id=APPROVER,
    )
    return f"{tenant}/{EXECUTION}"


def attributed_resumptions(registries: tuple[ControlPlaneRegistry, ...], key: str) -> list[str | None]:
    """Every attributed ``workflow_resumed`` row for ``key``, across processes."""
    return [
        event.actor
        for registry in registries
        for event in registry.audit_log.events()
        if event.key == key
        and event.action == "workflow_resumed"
        and event.resolved
        and event.actor is not None
    ]


def suspension_verdicts(
    transport: InMemoryHitlTransport, *, tenant: str, event_key: str, bound: str
) -> list[tuple[str, str, str | None]]:
    """(action, subject, event_state_at_submit) of every verdict on one suspension."""
    return [
        (s.action, s.principal.approver.subject_id, s.event_state_at_submit)
        for s in transport.submissions(tenant=tenant)
        if s.event_key == event_key and s.principal.product_content_hash == bound
    ]


def suspended_covenant(
    store: InMemoryStateStore | None, tmp_path: Path
) -> tuple[ControlPlaneRegistry, WorkflowEngine, InMemoryHitlTransport, Workflow, str, str]:
    """The covenant workflow suspended on its gate (which routes straight to
    its terminals), over ``store``, approved ONCE by ``officer-1`` through the
    submit-only door shape (D-IMPL-62), as the served action door records it."""
    registry = plane(store)
    engine, transport, workflow, event_key, bound = eh._suspended_covenant(
        registry, tmp_path, execution_id=COVENANT_EXECUTION
    )
    eh._submit_only(
        transport,
        tenant=workflow.definition.tenant,
        event_key=event_key,
        product_content_hash=bound,
        action="approve",
        subject_id=OFFICER_1,
    )
    return registry, engine, transport, workflow, event_key, bound


def resume_covenant(engine: WorkflowEngine, workflow: Workflow) -> WorkflowOutcome:
    return asyncio.run(
        engine.resume(
            eh.resume_as(workflow),
            workflow,
            execution_id=COVENANT_EXECUTION,
            decision=APPROVING_TERMINAL,
        )
    )


def reject_as_officer_2(
    transport: InMemoryHitlTransport, *, tenant: str, event_key: str, bound: str
) -> tuple[HitlActionSubmission | None, BaseException | None]:
    """``officer-2``'s rejection of the same suspension, through the submit-only
    door shape. An identity refusal is re-raised (the control is broken); any
    other refusal is returned, because refusing the verdict is one way a fix
    can close the hole."""
    try:
        return (
            eh._submit_only(
                transport,
                tenant=tenant,
                event_key=event_key,
                product_content_hash=bound,
                action="reject",
                subject_id=OFFICER_2,
            ),
            None,
        )
    except IDENTITY_REFUSALS:
        raise
    except Exception as error:  # a refusal BY A FIX; recorded, never swallowed silently
        return None, error


def state_of(registry: ControlPlaneRegistry, key: str) -> WorkflowStateRecord:
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    return record


# --- (a) one approval, two passages, across state-store objects -----------------


def test_two_state_store_objects_over_one_durable_store_spend_one_approval_once(
    tmp_path: Path,
) -> None:
    """Limit (a). Process A's resumption is held right after its own state read
    (at the storage layer) on another thread; process B's resumption of the same execution runs to its
    end meanwhile; then A is released.

    A and B take two DIFFERENT claims, because their state-store objects
    differ, so neither refuses the other. Today B passes the gate and commits,
    and A, released holding the record it already read, passes again: the step
    after the gate runs twice on ONE human approval, one attributed row lands in
    each process's audit log, and the next gate holds two pending events. The
    in-process control of the same shape is
    ``tests/workflow/test_resume_single_flight.py::test_a_resume_held_inside_its_read_on_another_thread_admits_no_second``,
    green since D-IMPL-377 because there both engines share one store object.
    """
    bindings = eh._Bindings()
    transport = InMemoryHitlTransport()
    a, b, records = two_processes(tmp_path, bindings, transport)
    key = start_and_approve_once(a, transport)
    records.arm_read(WORKFLOW_STATE, key)
    held = Worker(lambda: asyncio.run(resume(a.engine, a.workflow))).start()
    try:
        assert records.held.wait(HOLD_SECONDS), "process A's resume never reached its read"
        second = asyncio.run(resume(b.engine, b.workflow))
    finally:
        records.release.set()
    first = held.join()

    tenant = a.workflow.definition.tenant
    outcomes = [first, second]
    runs = bindings.ran.count(f"skill:{DOWNSTREAM}")
    attributed = attributed_resumptions((a.registry, b.registry), key)
    next_gate = [
        event
        for event in transport.pending(tenant=tenant)
        if event.event_key == f"{key}/{NEXT_GATE}"
    ]
    progressed = [o for o in outcomes if isinstance(o, WorkflowSuspended)]
    refused = [o for o in outcomes if isinstance(o, WorkflowResumeRefused)]
    problems = []
    if runs != 1:
        problems.append(f"the step after the gate ({DOWNSTREAM}) ran {runs} times")
    if attributed != [APPROVER]:
        problems.append(f"attributed workflow_resumed rows across the processes: {attributed}")
    if len(next_gate) != 1:
        problems.append(f"pending events at {NEXT_GATE}: {len(next_gate)}")
    if [o.gate for o in progressed] != [NEXT_GATE] or len(refused) != 1:
        problems.append(f"outcomes: {[type(o).__name__ for o in outcomes]}")
    assert not problems, (
        "LIMIT (a): ONE approval became more than one passage across two"
        " state-store objects over one durable store: " + "; ".join(problems)
    )


@pytest.mark.parametrize("resumer", ["a", "b"], ids=["process-a", "process-b"])
def test_either_process_alone_passes_the_gate_on_the_one_approval(
    tmp_path: Path, resumer: str
) -> None:
    """Positive control for limit (a), green today and after any fix: each
    process ALONE admits the one approval and passes the gate once. So a
    refusal in the red test above can only come from the two resumptions
    meeting, never from a process unable to pass."""
    bindings = eh._Bindings()
    transport = InMemoryHitlTransport()
    a, b, _ = two_processes(tmp_path, bindings, transport)
    start_and_approve_once(a, transport)
    process = a if resumer == "a" else b
    outcome = asyncio.run(resume(process.engine, process.workflow))
    assert isinstance(outcome, WorkflowSuspended), outcome
    assert outcome.gate == NEXT_GATE
    assert bindings.ran.count(f"skill:{DOWNSTREAM}") == 1


# --- (b) the outvoted rejection ----------------------------------------------------


def test_a_rejection_recorded_during_the_resumptions_commit_is_not_outvoted(
    tmp_path: Path,
) -> None:
    """Limit (b), as the close-out words it. ``officer-1`` approves; the
    resumption reads, judges one verdict, decides, and is held inside its
    terminal commit at the storage layer; ``officer-2``, also eligible,
    records a rejection of the SAME suspension; the commit is released.

    Today the execution completes at the APPROVING terminal while the
    rejection stands, recorded against a gate the transport still calls
    pending. Recorded first, the same rejection refuses the resumption for the
    conflict (``tests/workflow/test_engine.py::test_a_later_rejection_is_not_discarded_when_an_approval_came_first``),
    so only its timing decides which outcome a bank gets.
    """
    records = StandInRecords()
    registry, engine, transport, workflow, event_key, bound = suspended_covenant(
        SharedBackingStore(records), tmp_path
    )
    tenant = workflow.definition.tenant
    records.arm_write(terminal_write)
    held = Worker(lambda: resume_covenant(engine, workflow)).start()
    try:
        assert records.held.wait(HOLD_SECONDS), "the resumption never reached its commit"
        rejection, refusal = reject_as_officer_2(
            transport, tenant=tenant, event_key=event_key, bound=bound
        )
    finally:
        records.release.set()
    outcome = held.join()

    if refusal is not None:
        return  # the rejection was refused by a non-identity mechanism: closed
    assert rejection is not None
    passed = (
        isinstance(outcome, WorkflowCompleted)
        and outcome.terminal_state == APPROVING_TERMINAL
    )
    standing = rejection.event_state_at_submit != "missing"
    assert not (passed and standing), (
        "LIMIT (b): officer-2's rejection was recorded on an OPEN gate"
        f" (event_state_at_submit={rejection.event_state_at_submit!r}) during"
        f" the resumption's commit, and the execution completed at"
        f" {APPROVING_TERMINAL!r}: the rejection was outvoted. Verdicts on the"
        f" suspension: {suspension_verdicts(transport, tenant=tenant, event_key=event_key, bound=bound)};"
        f" final state: {state_of(registry, f'{tenant}/{COVENANT_EXECUTION}').status}"
        f"@{state_of(registry, f'{tenant}/{COVENANT_EXECUTION}').current_state}"
    )


# --- (b') the verdict after the passage -----------------------------------------


def test_a_verdict_recorded_after_the_passage_is_not_taken_as_a_verdict_on_an_open_gate(
    tmp_path: Path,
) -> None:
    """Limit (b'), found by this lane; sequential, no race. ``officer-1``
    approves through the submit-only door shape; the execution resumes and
    completes at the approving terminal; THEN ``officer-2`` rejects the same
    suspension.

    Today nothing retires the gate's event when the gate is passed, so the
    queue still offers the passed gate as pending, and the late rejection is
    recorded with ``event_state_at_submit='pending'``. The record then holds
    an approval and a rejection on one suspension of a completed execution,
    indistinguishable from the outvoted rejection of limit (b). Recorded as
    ``missing`` it would say what happened (D-IMPL-366 H2: recorded unjudged,
    never authority).
    """
    registry, engine, transport, workflow, event_key, bound = suspended_covenant(
        None, tmp_path
    )
    tenant = workflow.definition.tenant
    outcome = resume_covenant(engine, workflow)
    assert isinstance(outcome, WorkflowCompleted), outcome
    assert outcome.terminal_state == APPROVING_TERMINAL

    still_offered = any(
        event.event_key == event_key for event in transport.pending(tenant=tenant)
    )
    rejection, refusal = reject_as_officer_2(
        transport, tenant=tenant, event_key=event_key, bound=bound
    )
    problems = []
    if still_offered:
        problems.append(
            "the passed gate's event is still pending in the HITL queue after"
            " the execution completed"
        )
    if refusal is None:
        assert rejection is not None
        if rejection.event_state_at_submit != "missing":
            problems.append(
                "a rejection recorded after the passage was recorded as a verdict"
                f" on an open gate (event_state_at_submit={rejection.event_state_at_submit!r});"
                " verdicts on the passed suspension:"
                f" {suspension_verdicts(transport, tenant=tenant, event_key=event_key, bound=bound)}"
            )
    assert not problems, "LIMIT (b'): " + "; ".join(problems)


# --- (c) execute has no single-flight ----------------------------------------------


@pytest.mark.parametrize(
    "topology", ["one-engine", "two-state-store-objects"], ids=["one-engine", "two-processes"]
)
def test_two_concurrent_starts_of_one_execution_id_run_the_start_node_once(
    tmp_path: Path, topology: str
) -> None:
    """Limit (c). Two ``execute`` calls with ONE execution id on one event loop;
    the start node awaits once. Today both pass the "already exists" check
    before either has written, both run the start node, and the first gate
    holds two pending events, one bound to a record the other overwrote. D-23
    says an execution id is started once."""
    bindings = AwaitingStartBindings()
    transport = InMemoryHitlTransport()
    if topology == "one-engine":
        registry = plane()
        workflow = s6._two_gate(registry, eligible=frozenset({STARTER, APPROVER}))
        engine = engine_over(registry, tmp_path, bindings, transport)
        pairs = [(engine, workflow), (engine, workflow)]
    else:
        a, b, _ = two_processes(tmp_path, bindings, transport)
        pairs = [(a.engine, a.workflow), (b.engine, b.workflow)]
    tenant = pairs[0][1].definition.tenant

    async def both() -> list[WorkflowOutcome]:
        return list(
            await asyncio.gather(
                *(
                    engine.execute(
                        execute_as_principal(
                            tenant=tenant, resource=workflow.definition_key, principal=STARTER
                        ),
                        workflow,
                        execution_id="dup",
                    )
                    for engine, workflow in pairs
                )
            )
        )

    outcomes = asyncio.run(both())
    runs = bindings.ran.count(f"skill:{START}")
    pending_first = [
        event
        for event in transport.pending(tenant=tenant)
        if event.event_key == f"{tenant}/dup/{FIRST_GATE}"
    ]
    refused = [o for o in outcomes if isinstance(o, WorkflowResumeRefused)]
    problems = []
    if runs != 1:
        problems.append(f"the start node ran {runs} times")
    if len(pending_first) != 1:
        problems.append(f"pending events at {FIRST_GATE}: {len(pending_first)}")
    if len(refused) != 1:
        problems.append(f"outcomes: {[type(o).__name__ for o in outcomes]}")
    assert not problems, (
        "LIMIT (c): one execution id was started twice: " + "; ".join(problems)
    )


# --- (d) an attributed row for a passage that never committed ---------------------


@pytest.mark.parametrize("failure", ["commit-fails", "cancelled"])
def test_a_resumption_that_never_commits_leaves_no_attributed_passage_row(
    tmp_path: Path, failure: str
) -> None:
    """Limit (d). The resumption passes every check and appends its attributed
    ``workflow_resumed`` row, then never commits: its state write fails, or it
    is cancelled while the step after the gate runs (the write fails at the
    storage layer, or the step is a deployment binding cancelled in flight).
    The record still says suspended at the gate, and today the audit log still
    says the approver's verdict carried the execution past it, the shape SEC-001 named (*"asserts a
    resolution that never happened"*). A retry then adds a second attributed
    row for the one approval
    (``tests/workflow/test_resume_single_flight.py::test_a_resume_that_raises_gives_the_claim_back``
    measures the retry's re-run)."""
    records = StandInRecords()
    registry = plane(SharedBackingStore(records))
    bindings: eh._Bindings = eh._Bindings() if failure == "commit-fails" else BlockingOnceBindings()
    engine, transport, workflow = approved_suspension(registry, tmp_path, bindings)
    key = f"{workflow.definition.tenant}/{EXECUTION}"

    if failure == "commit-fails":
        records.arm_failure(workflow_write)
        with pytest.raises(RuntimeError, match="state store unavailable"):
            asyncio.run(resume(engine, workflow))
    else:
        assert isinstance(bindings, BlockingOnceBindings)

        async def cancel_inside_the_step() -> None:
            task = asyncio.create_task(resume(engine, workflow))
            for _ in range(10_000):
                if bindings.blocked:
                    break
                await asyncio.sleep(0)
            assert bindings.blocked, "the resume never reached the step after the gate"
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        asyncio.run(cancel_inside_the_step())

    record = state_of(registry, key)
    attributed = attributed_resumptions((registry,), key)
    # Neutral about WHEN a design commits the passage: a passage that never
    # left the gate may carry no attributed row, and one that did carries
    # exactly the one row of the one approval.
    committed = (record.status, record.current_state) != ("suspended", FIRST_GATE)
    expected = [APPROVER] if committed else []
    assert attributed == expected, (
        f"LIMIT (d), {failure}: the audit log carries attributed workflow_resumed"
        f" rows {attributed} while the record is {record.status}@{record.current_state}:"
        f" the passage {'committed' if committed else 'never committed'}"
    )
