"""An interrupted passage that ran no step is FINISHED, never re-run (D-IMPL-378, Dave's D2).

Dave's Q4 ruling on ``D-IMPL-378`` admitted a retry only with *"a durable claim
identifying the original passage"* that *"prevent[s] duplicate effects; 'same
engine' alone is insufficient. If that cannot be proved, use (b)"* — never retry
an interrupted passage. His D2 ruling (2026-10-07), on the runs that rule left
stuck: *"(a) Let the engine finish a stuck run whose current state is a gate or
the end state. No step ran there, so it provably can't duplicate an effect,
which meets your Q4 condition."*

A passage commits its record ``running`` at its decision BEFORE the step after
the gate runs (``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume``),
and an execution commits ``running`` at its start node before its first node
runs (``::WorkflowEngine.execute``). When that node is a gate or a terminal
state, no step lies between the commit and the passage's next write: what is
left is the engine's own version-fenced write and, at a gate, its one queue
event. Each test below interrupts exactly there — the stand-in durable store
refuses that next write once — and presents the passage again:

* a gate routed straight to a terminal state, finished by ANOTHER process: it
  completes, no step callable is invoked, one attributed row, one completion;
* an execution whose first node is a gate, finished by its starter's retried
  start or by a resumption: it suspends, no step callable is invoked, one
  queue event;
* a finisher racing the live original passage: one write lands, and the loser
  raises :class:`~ccf_runtime.workflow.engine.ExecutionFenced` in process (its
  rendering at the doors is lane 378c-d3's);
* a passage no durable claim names — or one its claim decided otherwise —
  is not finished;
* a start is finished for its own starter only, and only when its first node
  is a gate: a start at a step, which ran, is never finished.

Every other ``running`` record — one at a step, which may have run — stays
never-retried
(``tests/workflow/test_approval_gate_limits.py::test_an_interrupted_passage_is_never_retried_by_any_process``).

RED FIRST: the first six tests were committed before the finisher existed,
when every retry met the never-retried refusal; the last three guard the
finisher's own conditions, and their red is the lane's severings. Test
vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.authz.capability import Authorized
from ccf.controlplane.audit import AuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import AuditedStateWriter, StateWriteToken
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.workflow.factory import Workflow
from ccf_runtime.workflow.engine import (
    ExecutionFenced,
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowOutcome,
    WorkflowResumeRefused,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from tests.hitl.sec006_harness import execute_as_principal
from tests.workflow import test_engine as eh
from tests.workflow.test_approval_gate_limits import (
    ALREADY_EXISTS,
    APPROVING_TERMINAL,
    COVENANT_GATE,
    OFFICER_1,
    SharedBackingStore,
    StandInRecords,
    terminal_write,
)
from tests.workflow.test_resume_single_flight import (
    HOLD_SECONDS,
    INTERRUPTED,
    RUNNING,
    Worker,
    plane,
)

EXECUTION = "exec-finish"
#: The refusal a ``running`` record meets when it ran no step but no durable
#: claim on the HITL authority path names its passage
#: (``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume``).
NO_CLAIM = "no durable claim on the HITL authority path names it"


def suspended_write(key: tuple[str, str], value: object) -> bool:
    """A write of a workflow-state record whose status is ``suspended``."""
    return key[0] == WORKFLOW_STATE and getattr(value, "status", None) == "suspended"


def gate_start_covenant(registry: ControlPlaneRegistry) -> Workflow:
    """The covenant workflow, started AT its gate: no step precedes it, and
    the gate routes straight to its terminal states."""
    return eh._covenant(
        registry,
        start=COVENANT_GATE,
        transitions=[
            {"source": COVENANT_GATE, "target": APPROVING_TERMINAL},
            {"source": COVENANT_GATE, "target": "rejected"},
        ],
        exception_refs={},
    )


@dataclass
class Process:
    """One deployment process: its registry, engine, handle and node bindings."""

    registry: ControlPlaneRegistry
    engine: WorkflowEngine
    workflow: Workflow
    bindings: eh._Bindings


def covenant_processes(
    tmp_path: Path, stores: tuple[SharedBackingStore, SharedBackingStore]
) -> tuple[Process, Process, InMemoryHitlTransport]:
    """Two processes over one durable store and one shared authority path,
    each with its own registry, store object, engine and node bindings."""
    transport = InMemoryHitlTransport()
    transport.scope = "shared"  # type: ignore[misc]
    processes = []
    for name, store in zip(("a", "b"), stores, strict=True):
        registry = plane(store)
        engine, used, bindings = eh._engine(registry, tmp_path / f"process-{name}", transport=transport)
        assert used is transport
        processes.append(Process(registry, engine, eh._covenant(registry), bindings))
    a, b = processes
    assert a.workflow.identity.definition_hash == b.workflow.identity.definition_hash
    assert a.registry.state_store is not b.registry.state_store
    return a, b, transport


def suspend_and_approve(process: Process, transport: InMemoryHitlTransport) -> str:
    """Execute to the covenant gate in ``process`` and record ONE approval by
    ``officer-1`` through the submit-only door shape. Returns the state key."""
    workflow = process.workflow
    suspended = asyncio.run(
        process.engine.execute(eh.execute_as(workflow), workflow, execution_id=EXECUTION)
    )
    assert isinstance(suspended, WorkflowSuspended) and suspended.gate == COVENANT_GATE
    tenant = workflow.definition.tenant
    bound = next(
        e.product_content_hash for e in transport.pending(tenant=tenant) if e.event_key == suspended.event_key
    )
    eh._submit_only(
        transport, tenant=tenant, event_key=suspended.event_key, product_content_hash=bound,
        action="approve", subject_id=OFFICER_1,
    )
    return f"{tenant}/{EXECUTION}"


def resume(process: Process) -> WorkflowOutcome:
    return asyncio.run(
        process.engine.resume(
            eh.resume_as(process.workflow), process.workflow,
            execution_id=EXECUTION, decision=APPROVING_TERMINAL,
        )
    )


def state_of(registry: ControlPlaneRegistry, key: str) -> WorkflowStateRecord:
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    return record


def rows(registries: tuple[ControlPlaneRegistry, ...], key: str, action: str) -> list[str | None]:
    """The actor of every RESOLVED ``action`` row for ``key``, across processes."""
    return [
        event.actor
        for registry in registries
        for event in registry.audit_log.events()
        if event.key == key and event.action == action and event.resolved
    ]


def test_a_gate_routed_straight_to_a_terminal_is_finished_by_another_process_not_rerun(
    tmp_path: Path,
) -> None:
    """Process A commits the passage past the covenant gate and the store
    refuses its terminal write, so the record stays ``running`` at the
    terminal state. Process B — another engine, another store object — presents
    the resumption again and FINISHES the passage under the gate's closure,
    which names it by what it decided: it completes, invoking no step callable,
    with the one attributed row A committed and one completion row."""
    records = StandInRecords()
    a, b, transport = covenant_processes(tmp_path, (SharedBackingStore(records), SharedBackingStore(records)))
    key = suspend_and_approve(a, transport)
    tenant = a.workflow.definition.tenant
    records.arm_failure(terminal_write)
    with pytest.raises(RuntimeError, match="state store unavailable"):
        resume(a)
    stuck = state_of(a.registry, key)
    assert (stuck.status, stuck.current_state) == ("running", APPROVING_TERMINAL)
    ran_before = list(a.bindings.ran)
    claims = transport.closures(tenant=tenant)
    assert len(claims) == 1, claims

    outcome = resume(b)

    assert isinstance(outcome, WorkflowCompleted), outcome
    assert outcome.terminal_state == APPROVING_TERMINAL
    # No step callable was invoked by the finisher, in either process.
    assert b.bindings.ran == [] and a.bindings.ran == ran_before
    final = state_of(b.registry, key)
    assert (final.status, final.current_state) == ("terminal", APPROVING_TERMINAL)
    assert final.trace == stuck.trace
    both = (a.registry, b.registry)
    assert rows(both, key, "workflow_resumed") == [OFFICER_1], "exactly one attributed passage row"
    assert rows(both, key, "workflow_completed") == [None], "exactly one completion"
    assert transport.closures(tenant=tenant) == claims, "the passage's own claim, not a second"


@pytest.mark.parametrize("retry", ["execute", "resume"])
def test_an_execution_whose_first_node_is_a_gate_is_finished_not_restarted(
    tmp_path: Path, retry: str
) -> None:
    """The execution's start commit lands, and the store refuses its first
    suspension write: the record stays ``running`` at the gate with no step
    run and no event queued. The starter's retried start — or a resumption —
    FINISHES it: it suspends on the gate with exactly one queue event and one
    start row, invoking no step callable."""
    records = StandInRecords()
    registry = plane(SharedBackingStore(records, scope="process"))
    engine, transport, bindings = eh._engine(registry, tmp_path)
    workflow = gate_start_covenant(registry)
    tenant = workflow.definition.tenant
    key = f"{tenant}/{EXECUTION}"
    event_key = f"{key}/{COVENANT_GATE}"
    records.arm_failure(suspended_write)
    with pytest.raises(RuntimeError, match="state store unavailable"):
        asyncio.run(engine.execute(eh.execute_as(workflow), workflow, execution_id=EXECUTION))
    stuck = state_of(registry, key)
    assert (stuck.status, stuck.current_state, stuck.trace) == ("running", COVENANT_GATE, ())
    assert not [e for e in transport.pending(tenant=tenant) if e.event_key == event_key]

    if retry == "execute":
        outcome = asyncio.run(engine.execute(eh.execute_as(workflow), workflow, execution_id=EXECUTION))
    else:
        outcome = asyncio.run(
            engine.resume(eh.resume_as(workflow), workflow, execution_id=EXECUTION, decision=APPROVING_TERMINAL)
        )

    assert isinstance(outcome, WorkflowSuspended), outcome
    assert outcome.gate == COVENANT_GATE
    assert bindings.ran == [], "no step callable was invoked"
    queued = [e for e in transport.pending(tenant=tenant) if e.event_key == event_key]
    assert len(queued) == 1, queued
    assert rows((registry,), key, "workflow_started") == [None]
    assert rows((registry,), key, "workflow_suspended") == [None]
    final = state_of(registry, key)
    assert (final.status, final.current_state) == ("suspended", COVENANT_GATE)
    # The finished suspension is a real one: its one approval carries the run on.
    eh._submit_only(
        transport, tenant=tenant, event_key=event_key, product_content_hash=queued[0].product_content_hash,
        action="approve", subject_id=OFFICER_1,
    )
    done = asyncio.run(
        engine.resume(eh.resume_as(workflow), workflow, execution_id=EXECUTION, decision=APPROVING_TERMINAL)
    )
    assert isinstance(done, WorkflowCompleted) and done.terminal_state == APPROVING_TERMINAL
    assert rows((registry,), key, "workflow_resumed") == [OFFICER_1]


class PausingBackingStore(SharedBackingStore):
    """One process's store object that can pause BEFORE its next terminal write,
    outside the durable store's write lock: a process preempted between its
    passage commit and the write that ends the passage."""

    def __init__(self, records: StandInRecords) -> None:
        super().__init__(records)
        self._pause_armed = False
        self._pause_lock = threading.Lock()
        self.paused = threading.Event()
        self.resume_write = threading.Event()

    def pause_before_terminal_write(self) -> None:
        with self._pause_lock:
            self._pause_armed = True

    def put_if(
        self,
        authorized: Authorized[Any],
        record_class: str,
        record: object,
        *,
        record_id: str,
        token: StateWriteToken,
        expected_version: int,
    ) -> int:
        with self._pause_lock:
            pause = self._pause_armed and terminal_write((record_class, record_id), record)
            if pause:
                self._pause_armed = False
        if pause:
            self.paused.set()
            if not self.resume_write.wait(HOLD_SECONDS):
                raise RuntimeError("the paused terminal write was never released")
        return super().put_if(  # type: ignore[no-any-return]
            authorized, record_class, record, record_id=record_id, token=token,
            expected_version=expected_version,
        )


@pytest.mark.parametrize("winner", ["finisher", "original"])
def test_a_finisher_racing_the_live_original_passage_writes_once_and_the_loser_is_fenced(
    tmp_path: Path, winner: str
) -> None:
    """Process A's passage has committed and A is paused before its terminal
    write when process B, seeing the record ``running`` at the terminal state,
    finishes it. Exactly one terminal write lands — whichever comes first — and
    the other raises :class:`ExecutionFenced` having written nothing: one
    completion row, one attributed row, no step callable invoked by B."""
    records = StandInRecords()
    store_a, store_b = PausingBackingStore(records), PausingBackingStore(records)
    a, b, transport = covenant_processes(tmp_path, (store_a, store_b))
    key = suspend_and_approve(a, transport)
    store_a.pause_before_terminal_write()
    original = Worker(lambda: resume(a)).start()
    try:
        assert store_a.paused.wait(HOLD_SECONDS), "the original passage never reached its terminal write"
        stuck = state_of(b.registry, key)
        assert (stuck.status, stuck.current_state) == ("running", APPROVING_TERMINAL)
        if winner == "finisher":
            finished = resume(b)
            assert isinstance(finished, WorkflowCompleted), finished
        else:
            store_b.pause_before_terminal_write()
            finisher = Worker(lambda: resume(b)).start()
            try:
                if not store_b.paused.wait(HOLD_SECONDS):
                    pytest.fail(f"the finisher never reached its terminal write: {finisher.join()!r}")
            finally:
                store_a.resume_write.set()
            completed = original.join()
            assert isinstance(completed, WorkflowCompleted), completed
            store_b.resume_write.set()
            with pytest.raises(ExecutionFenced):
                finisher.join()
    finally:
        store_a.resume_write.set()
        store_b.resume_write.set()
    if winner == "finisher":
        with pytest.raises(ExecutionFenced):
            original.join()

    both = (a.registry, b.registry)
    assert rows(both, key, "workflow_completed") == [None], "exactly one terminal write landed"
    assert rows(both, key, "workflow_resumed") == [OFFICER_1]
    assert b.bindings.ran == []
    final = state_of(a.registry, key)
    assert (final.status, final.current_state) == ("terminal", APPROVING_TERMINAL)


def test_a_passage_no_durable_claim_names_is_never_finished(tmp_path: Path) -> None:
    """The record is ``running`` at a terminal state, so no step can have run —
    but the engine presenting it again reaches an authority path holding no
    closure for its passage. The durable claim is what identifies the passage
    (Dave's Q4 condition), so without it the passage is not finished: refused,
    typed, by name, with nothing written and no step callable invoked."""
    records = StandInRecords()
    registry = plane(SharedBackingStore(records, scope="process"))
    engine, transport, bindings = eh._engine(registry, tmp_path / "first")
    workflow = eh._covenant(registry)
    process = Process(registry, engine, workflow, bindings)
    key = suspend_and_approve(process, transport)
    records.arm_failure(terminal_write)
    with pytest.raises(RuntimeError, match="state store unavailable"):
        resume(process)
    stuck = state_of(registry, key)
    assert (stuck.status, stuck.current_state) == ("running", APPROVING_TERMINAL)

    # Another engine over the same Control Plane, whose transport holds no
    # closure — the authority path that decided this passage is not the one
    # it reaches.
    other, other_transport, other_bindings = eh._engine(
        registry, tmp_path / "second", transport=InMemoryHitlTransport()
    )
    assert other_transport.closures(tenant=workflow.definition.tenant) == ()
    outcome = resume(Process(registry, other, workflow, other_bindings))

    assert isinstance(outcome, WorkflowResumeRefused), outcome
    assert NO_CLAIM in outcome.reason, outcome.reason
    assert RUNNING in outcome.reason and INTERRUPTED in outcome.reason, outcome.reason
    assert other_bindings.ran == []
    assert state_of(registry, key) == stuck


def test_another_principals_start_does_not_finish_an_interrupted_start(tmp_path: Path) -> None:
    """The start's durable claim is the create-if-absent record, stamped with
    its starter. Another principal presenting the same execution id is a
    second start, refused as one (D-23), and finishes nothing; the starter's
    own retry then does."""
    records = StandInRecords()
    registry = plane(SharedBackingStore(records, scope="process"))
    engine, transport, bindings = eh._engine(registry, tmp_path)
    workflow = gate_start_covenant(registry)
    tenant = workflow.definition.tenant
    key = f"{tenant}/{EXECUTION}"
    records.arm_failure(suspended_write)
    with pytest.raises(RuntimeError, match="state store unavailable"):
        asyncio.run(engine.execute(eh.execute_as(workflow), workflow, execution_id=EXECUTION))
    stuck = state_of(registry, key)

    other = execute_as_principal(tenant=tenant, resource=workflow.definition_key, principal="officer-z")
    refused = asyncio.run(engine.execute(other, workflow, execution_id=EXECUTION))

    assert isinstance(refused, WorkflowResumeRefused), refused
    assert ALREADY_EXISTS in refused.reason, refused.reason
    assert state_of(registry, key) == stuck
    assert not transport.pending(tenant=tenant)
    # Positive control: the starter's own retry finishes it.
    finished = asyncio.run(engine.execute(eh.execute_as(workflow), workflow, execution_id=EXECUTION))
    assert isinstance(finished, WorkflowSuspended), finished
    assert bindings.ran == []


def test_an_interrupted_start_at_a_step_is_never_finished(tmp_path: Path) -> None:
    """The covenant workflow starts at a step. Its start commit lands, its
    steps run, and the store refuses the suspension write at its gate: the
    record still says ``running`` at the START node, which is a step that
    ran. Neither the starter's retry nor a resumption finishes it, and no
    step runs a second time."""
    records = StandInRecords()
    registry = plane(SharedBackingStore(records, scope="process"))
    engine, transport, bindings = eh._engine(registry, tmp_path)
    workflow = eh._covenant(registry)
    tenant = workflow.definition.tenant
    key = f"{tenant}/{EXECUTION}"
    records.arm_failure(suspended_write)
    with pytest.raises(RuntimeError, match="state store unavailable"):
        asyncio.run(engine.execute(eh.execute_as(workflow), workflow, execution_id=EXECUTION))
    stuck = state_of(registry, key)
    assert (stuck.status, stuck.current_state, stuck.trace) == ("running", workflow.definition.start, ())
    ran = list(bindings.ran)
    assert ran, "the start's steps ran before the suspension write failed"

    again = asyncio.run(engine.execute(eh.execute_as(workflow), workflow, execution_id=EXECUTION))
    resumed = asyncio.run(
        engine.resume(eh.resume_as(workflow), workflow, execution_id=EXECUTION, decision=APPROVING_TERMINAL)
    )

    assert isinstance(again, WorkflowResumeRefused) and ALREADY_EXISTS in again.reason, again
    assert isinstance(resumed, WorkflowResumeRefused), resumed
    assert RUNNING in resumed.reason and INTERRUPTED in resumed.reason, resumed.reason
    assert NO_CLAIM not in resumed.reason, "a step that ran is never treated as unclaimed-but-finishable"
    assert bindings.ran == ran, "no step ran a second time"
    assert state_of(registry, key) == stuck
    assert not transport.pending(tenant=tenant)


def test_a_passage_its_claim_decided_otherwise_is_never_finished(tmp_path: Path) -> None:
    """The gate's closure decided a REJECTION, and the passage committed
    ``running`` at ``rejected`` before its terminal write failed. A writer
    outside the engine then rewrites the record to say ``running`` at
    ``approved``, leaving the suspension it names unchanged. The closure is
    found, but its decided verdict routes to ``rejected``, not to the record's
    state: the claim does not name this passage, so it is not finished."""
    records = StandInRecords()
    registry = plane(SharedBackingStore(records, scope="process"))
    engine, transport, bindings = eh._engine(registry, tmp_path)
    workflow = eh._covenant(registry)
    tenant = workflow.definition.tenant
    suspended = asyncio.run(engine.execute(eh.execute_as(workflow), workflow, execution_id=EXECUTION))
    assert isinstance(suspended, WorkflowSuspended)
    bound = next(e.product_content_hash for e in transport.pending(tenant=tenant) if e.event_key == suspended.event_key)
    eh._submit_only(
        transport, tenant=tenant, event_key=suspended.event_key, product_content_hash=bound,
        action="reject", subject_id=OFFICER_1,
    )
    records.arm_failure(terminal_write)
    with pytest.raises(RuntimeError, match="state store unavailable"):
        asyncio.run(engine.resume(eh.resume_as(workflow), workflow, execution_id=EXECUTION, decision="rejected"))
    key = f"{tenant}/{EXECUTION}"
    stuck = state_of(registry, key)
    assert (stuck.status, stuck.current_state) == ("running", "rejected")
    last = stuck.trace[-1]
    rewritten = stuck.model_copy(
        update={
            "current_state": APPROVING_TERMINAL,
            "trace": stuck.trace[:-1] + (last.model_copy(update={"target": APPROVING_TERMINAL}),),
        }
    )
    AuditedStateWriter(store=registry.state_store, audit=registry.audit_log).write(
        eh.execute_as(workflow), WORKFLOW_STATE, rewritten, record_id=EXECUTION,
        event=AuditEvent(
            sequence=0, action="state_written", key=key, version=workflow.identity.definition_hash,
            resolved=True, occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
        ),
    )
    ran = list(bindings.ran)

    outcome = asyncio.run(
        engine.resume(eh.resume_as(workflow), workflow, execution_id=EXECUTION, decision=APPROVING_TERMINAL)
    )

    assert isinstance(outcome, WorkflowResumeRefused), outcome
    assert NO_CLAIM in outcome.reason, outcome.reason
    assert state_of(registry, key) == rewritten
    assert rows((registry,), key, "workflow_completed") == []
    assert bindings.ran == ran
