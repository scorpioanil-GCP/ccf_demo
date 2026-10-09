"""A run left ``suspended`` with no pending approval request gets that request back (D-IMPL-378, Dave's decision 8 (a)).

The hole (the final panel's seat F2, finding F2-01). A suspension is three
acts: the version-fenced write of the ``suspended`` record, the write-through
of its trace artifact, and the enqueue of its one approval request
(``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._suspend``). A
process that dies, or an artifact store that fails, after the first act and
before the last leaves the run ``suspended`` at its gate with no request on the
HITL transport. Measured at ``a539c215``: the starter's retried start is
refused "already exists", a resumption is refused for want of an approval, and
an approval recorded meanwhile is recorded ``event_state_at_submit='missing'``
and never counts, so nothing in the SDK could move the run again
(``records/2026-10-09-d-impl-378-final-panel/fable-F2/probes/probe_suspended_without_event.py``
on the ``dl-378-record`` branch).

Dave's decision 8 (2026-10-09 06:06, confirmed 06:21 "8a"): *"(a). Recover the
suspended run by idempotently restoring its missing approval request. Preserve
the original authorization and suspension identity; never manufacture approval
or rerun an effect."* Option (a) extends D2, *"Let the engine finish a stuck
run whose current state is a gate or the end state"*, so the recovery runs on
D2's own two triggers: the starter's retried start and a resumption.

Each test builds the stuck state for real. The failure is injected where an
outage lives, in the artifact store's write of the trace or in the transport's
enqueue, never on an engine method, so a recovery written any other way is
still judged. Then the recovery runs, and the test asserts the ruling's words:

* (i) exactly ONE pending approval request results, equal field by field to the
  request a suspension files (an uninterrupted control shows the same
  description fits an ordinary suspension's request);
* (ii) running the recovery again files nothing more;
* (iii) an approval recorded while the request was missing still does not
  count: the gate opens only on a fresh approval of the restored request;
* (iv) no step runs during the recovery;
* (v) after a genuine approval the run passes the gate exactly once;
* (vi) the suspension's identity is unchanged: the record's content hash, which
  the request, every verdict and the gate's closure are bound to, and the trace
  artifact's address, which is the address the interrupted suspension meant to
  file.

The two-gate release workflow is used because the step after its first gate
(``archive-certificates``) is a real node, so a passage can be counted.

RED FIRST: committed before the recovery existed, when every retry met the
refusals above. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef, DerivedWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import InMemoryStateStore
from ccf.hitl.approval_gate import GATE_EVENT_CLASS
from ccf.hitl.transport import (
    HitlActionSubmission,
    HitlGateClosed,
    InMemoryHitlTransport,
    PendingHitlEvent,
)
from ccf.workflow.factory import Workflow
from ccf_runtime.workflow.engine import (
    WORKFLOW_TRACE_ARTIFACT_CLASS,
    ExecutionFenced,
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowOutcome,
    WorkflowResumeRefused,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from http_api.composition_authority import deployment_write_kinds
from tests.hitl.sec006_harness import execute_as_principal
from tests.workflow import test_engine as eh
from tests.workflow import test_sec006_engine_controls as s6
from tests.workflow.test_approval_gate_limits import ALREADY_EXISTS, SharedBackingStore, StandInRecords
from tests.workflow.test_resume_single_flight import (
    APPROVER,
    DOWNSTREAM,
    HOLD_SECONDS,
    NEXT_GATE,
    STARTER,
    Worker,
    plane,
)

EXECUTION = "exec-restore"
#: The two-gate workflow's first gate, and the terminal its second gate's
#: approval routes to (``tests/fixtures/banking/workflows/two_gate_release_workflow.yaml``).
FIRST_GATE = "first-approval"
RELEASED = "released"
#: The refusal a resumption meets at a gate no recorded approval opens
#: (``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume``).
NO_APPROVAL = "no approval for this suspension has returned through the HITL authority path"


# --- substrates -----------------------------------------------------------------


class TraceStore(FileArtifactStore):
    """The deployment's file store, able to refuse or hold its NEXT trace write, once.

    The refusal and the hold sit in the store's own ``put``, where an artifact
    store outage or a slow artifact store lives. ``refused`` keeps the trace a
    refused write carried, and ``filed`` the reference of every trace write that
    landed, so a test can name the address an interrupted suspension meant to
    file.
    """

    def __init__(self, root: Path) -> None:
        super().__init__(root=root, write_kinds=deployment_write_kinds(workflow_traces=True))
        self._arm_lock = threading.Lock()
        self._refuse_next = False
        self._hold_next = False
        self.held = threading.Event()
        self.release = threading.Event()
        self.refused: list[object] = []
        self.filed: list[ArtifactRef] = []

    def refuse_next_trace_write(self) -> None:
        with self._arm_lock:
            self._refuse_next = True

    def hold_next_trace_write(self) -> None:
        with self._arm_lock:
            self._hold_next = True

    def put(self, authorized: Any, artifact: object) -> ArtifactRef:
        trace = isinstance(artifact, DerivedWrite) and artifact.artifact_class == WORKFLOW_TRACE_ARTIFACT_CLASS
        with self._arm_lock:
            refuse = trace and self._refuse_next
            if refuse:
                self._refuse_next = False
            hold = trace and not refuse and self._hold_next
            if hold:
                self._hold_next = False
        if refuse:
            assert isinstance(artifact, DerivedWrite)
            self.refused.append(artifact.artifact)
            raise OSError("the artifact store refused the trace write")
        if hold:
            self.held.set()
            if not self.release.wait(HOLD_SECONDS):
                raise RuntimeError("the held trace write was never released")
        ref = super().put(authorized, artifact)
        if trace:
            self.filed.append(ref)
        return ref


class DyingTransport(InMemoryHitlTransport):
    """The reference transport, whose caller's process dies at, or is held before, its NEXT enqueue.

    A death raises once and queues nothing; a hold blocks that one enqueue (or,
    armed separately, the next submit) before it records anything and outside
    the transport's own lock, until :attr:`release` is set. Every other call is
    the reference transport's own.
    """

    def __init__(self) -> None:
        super().__init__()
        self._death_lock = threading.Lock()
        self._die_next = False
        self._hold_next = False
        self._hold_submit = False
        self.held = threading.Event()
        self.release = threading.Event()

    def die_at_next_enqueue(self) -> None:
        with self._death_lock:
            self._die_next = True

    def hold_next_enqueue(self) -> None:
        with self._death_lock:
            self._hold_next = True

    def hold_next_submit(self) -> None:
        with self._death_lock:
            self._hold_submit = True

    def submit(self, authorized: Any, *, submission: HitlActionSubmission) -> HitlActionSubmission:
        with self._death_lock:
            hold, self._hold_submit = self._hold_submit, False
        if hold:
            self.held.set()
            if not self.release.wait(HOLD_SECONDS):
                raise RuntimeError("the held submit was never released")
        return super().submit(authorized, submission=submission)

    def enqueue(self, *, event: PendingHitlEvent) -> None:
        with self._death_lock:
            die, self._die_next = self._die_next, False
            hold = not die and self._hold_next
            if hold:
                self._hold_next = False
        if die:
            raise OSError("the process died before its enqueue")
        if hold:
            self.held.set()
            if not self.release.wait(HOLD_SECONDS):
                raise RuntimeError("the held enqueue was never released")
        super().enqueue(event=event)


# --- composition ----------------------------------------------------------------


@dataclass
class Run:
    """One deployment process running the two-gate workflow under ``EXECUTION``."""

    registry: ControlPlaneRegistry
    engine: WorkflowEngine
    transport: DyingTransport
    store: TraceStore
    bindings: eh._Bindings
    workflow: Workflow

    @property
    def tenant(self) -> str:
        return self.workflow.definition.tenant

    @property
    def key(self) -> str:
        return f"{self.tenant}/{EXECUTION}"

    def event_key(self, gate: str) -> str:
        return f"{self.key}/{gate}"


def compose(
    root: Path,
    *,
    store: InMemoryStateStore | None = None,
    transport: DyingTransport | None = None,
) -> Run:
    """One process: its registry over ``store``, the two-gate workflow (``officer-a``
    and ``officer-b`` eligible), its own artifact store, and the transport."""
    registry = plane(store)
    workflow = s6._two_gate(registry, eligible=frozenset({STARTER, APPROVER}))
    transport = DyingTransport() if transport is None else transport
    bindings = eh._Bindings()
    artifacts = TraceStore(root / "artifacts")
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=artifacts,
        hitl_transport=transport,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=eh._ticking_clock(),
        debt_binding=eh._PermissiveDebt(),
    )
    return Run(registry, engine, transport, artifacts, bindings, workflow)


def start(run: Run) -> WorkflowOutcome:
    """``officer-a`` starts the execution (or retries the start)."""
    starter = execute_as_principal(tenant=run.tenant, resource=run.workflow.definition_key, principal=STARTER)
    return asyncio.run(run.engine.execute(starter, run.workflow, execution_id=EXECUTION))


def resume(run: Run, decision: str = DOWNSTREAM) -> WorkflowOutcome:
    return asyncio.run(
        run.engine.resume(eh.resume_as(run.workflow), run.workflow, execution_id=EXECUTION, decision=decision)
    )


def recover(run: Run, trigger: str) -> WorkflowOutcome:
    """D2's two triggers: the starter's retried start, or a resumption."""
    return start(run) if trigger == "execute" else resume(run)


def state_of(run: Run) -> WorkflowStateRecord:
    record = run.registry.state_store.get(WORKFLOW_STATE, run.key)
    assert isinstance(record, WorkflowStateRecord)
    return record


def requests(run: Run, gate: str) -> list[PendingHitlEvent]:
    """The approval requests pending at ``gate`` of this execution."""
    return [e for e in run.transport.pending(tenant=run.tenant) if e.event_key == run.event_key(gate)]


def the_request_a_suspension_files(run: Run, record: WorkflowStateRecord) -> PendingHitlEvent:
    """The approval request a suspension of ``record`` files: its gate's event key
    and class, the execution's state key, the record's own content hash, the
    gate's pinned approval policy, and the starter as requester."""
    gate = record.current_state
    return PendingHitlEvent(
        event_key=run.event_key(gate),
        event_class=GATE_EVENT_CLASS,
        tenant=run.tenant,
        workflow_state_ref=run.key,
        product_content_hash=content_hash(record),
        policy_ref=run.workflow.definition.gate_policies[gate],
        requested_by=record.started_by,
    )


def rows(registries: tuple[ControlPlaneRegistry, ...], key: str, action: str) -> list[str | None]:
    """The actor of every RESOLVED ``action`` row for ``key``, across processes."""
    return [
        event.actor
        for registry in registries
        for event in registry.audit_log.events()
        if event.key == key and event.action == action and event.resolved
    ]


def interrupt(run: Run, death: str, act: Callable[[], WorkflowOutcome]) -> tuple[WorkflowStateRecord, str]:
    """Run ``act`` with ``death`` armed. Returns the stuck record and the address
    of the trace the interrupted suspension meant to file."""
    if death == "trace-write":
        run.store.refuse_next_trace_write()
    else:
        run.transport.die_at_next_enqueue()
    with pytest.raises(OSError):
        act()
    stuck = state_of(run)
    meant = content_hash(run.store.refused[-1]) if death == "trace-write" else run.store.filed[-1].content_address
    return stuck, meant


# --- the hole, as the ruling words it -------------------------------------------


@pytest.mark.parametrize("trigger", ["execute", "resume"])
@pytest.mark.parametrize("death", ["trace-write", "enqueue"])
def test_a_suspension_whose_request_never_reached_the_queue_gets_exactly_that_request_back(
    tmp_path: Path, death: str, trigger: str
) -> None:
    """The start runs its first step and suspends on ``first-approval``, and the
    trace write or the enqueue dies. The recovery, by the starter's retried start
    or by a resumption, files exactly the one request that suspension would have
    filed and nothing else. The gate then opens once, on a fresh approval."""
    control = compose(tmp_path / "control")
    assert isinstance(start(control), WorkflowSuspended)
    assert requests(control, FIRST_GATE) == [the_request_a_suspension_files(control, state_of(control))], (
        "an ordinary suspension's request is the request this test describes"
    )

    run = compose(tmp_path / "run")
    stuck, meant = interrupt(run, death, lambda: start(run))
    assert (stuck.status, stuck.current_state) == ("suspended", FIRST_GATE)
    assert requests(run, FIRST_GATE) == [], "the interrupted suspension filed no request"
    missing = eh._submit_only(
        run.transport, tenant=run.tenant, event_key=run.event_key(FIRST_GATE),
        product_content_hash=content_hash(stuck), action="approve", subject_id=APPROVER,
    )
    assert missing.event_state_at_submit == "missing"
    ran = list(run.bindings.ran)
    assert ran == ["skill:fetch-certificates"], ran
    suspended_rows = rows((run.registry,), run.key, "workflow_suspended")
    verdicts = run.transport.submissions(tenant=run.tenant)

    outcome = recover(run, trigger)

    # (i) exactly ONE request: the one the suspension would have filed.
    expected = the_request_a_suspension_files(run, stuck)
    assert requests(run, FIRST_GATE) == [expected], (
        f"pending requests at {FIRST_GATE} after the recovery ({type(outcome).__name__}:"
        f" {getattr(outcome, 'reason', '')[:120]})"
    )
    assert isinstance(outcome, WorkflowSuspended), outcome
    assert (outcome.gate, outcome.event_key) == (FIRST_GATE, expected.event_key)
    # (vi) the suspension's identity: the record, and so its content hash, and the
    # trace artifact's address, which is the one the suspension meant to file.
    assert state_of(run) == stuck
    assert outcome.trace_artifact.content_address == meant == content_hash(stuck.trace)
    assert run.store.get(content_address=meant) == canonical_bytes(stuck.trace)
    # (iv) no step ran; and no verdict was recorded and no gate closed.
    assert run.bindings.ran == ran
    assert run.transport.submissions(tenant=run.tenant) == verdicts
    assert run.transport.closures(tenant=run.tenant) == ()
    # The recovery is audited, by one row.
    assert rows((run.registry,), run.key, "workflow_suspended") == suspended_rows + [None]

    # (ii) the recovery again files nothing more.
    again = recover(run, trigger)
    assert isinstance(again, WorkflowResumeRefused), again
    assert requests(run, FIRST_GATE) == [expected]
    assert rows((run.registry,), run.key, "workflow_suspended") == suspended_rows + [None]
    assert state_of(run) == stuck
    assert run.bindings.ran == ran

    # (iii) the approval recorded while the request was missing does not open the gate.
    refused = resume(run)
    assert isinstance(refused, WorkflowResumeRefused), refused
    assert NO_APPROVAL in refused.reason, refused.reason
    assert run.bindings.ran == ran

    # (v) a fresh approval of the restored request passes the gate exactly once.
    eh._resolve_gate(
        run.registry, run.transport, tenant=run.tenant, event_key=expected.event_key,
        action="approve", subject_id=APPROVER,
    )
    passed = resume(run)
    assert isinstance(passed, WorkflowSuspended) and passed.gate == NEXT_GATE, passed
    assert isinstance(resume(run), WorkflowResumeRefused)
    assert run.bindings.ran == ran + [f"skill:{DOWNSTREAM}"]
    assert [a for a in rows((run.registry,), run.key, "workflow_resumed") if a is not None] == [APPROVER]


def test_a_suspension_a_passage_left_without_its_request_gets_it_back_from_the_resumers_retry(
    tmp_path: Path,
) -> None:
    """The run passes ``first-approval`` on a real approval, runs the step after
    it, and suspends on ``second-approval``, where the enqueue dies. The
    resumer's retry files that gate's one request, the step that ran is not run
    again, and the run then completes once on that gate's approval."""
    run = compose(tmp_path)
    first = start(run)
    assert isinstance(first, WorkflowSuspended)
    eh._resolve_gate(
        run.registry, run.transport, tenant=run.tenant, event_key=first.event_key,
        action="approve", subject_id=APPROVER,
    )
    stuck, meant = interrupt(run, "enqueue", lambda: resume(run))
    assert (stuck.status, stuck.current_state) == ("suspended", NEXT_GATE)
    assert requests(run, NEXT_GATE) == []
    ran = list(run.bindings.ran)
    assert ran.count(f"skill:{DOWNSTREAM}") == 1, ran

    outcome = resume(run)

    expected = the_request_a_suspension_files(run, stuck)
    assert requests(run, NEXT_GATE) == [expected], (
        f"pending requests at {NEXT_GATE} after the retry ({type(outcome).__name__}:"
        f" {getattr(outcome, 'reason', '')[:120]})"
    )
    assert isinstance(outcome, WorkflowSuspended) and outcome.gate == NEXT_GATE, outcome
    assert outcome.trace_artifact.content_address == meant
    assert state_of(run) == stuck
    assert run.bindings.ran == ran, "no step ran again"

    eh._resolve_gate(
        run.registry, run.transport, tenant=run.tenant, event_key=expected.event_key,
        action="approve", subject_id=APPROVER,
    )
    done = resume(run, decision=RELEASED)
    assert isinstance(done, WorkflowCompleted) and done.terminal_state == RELEASED, done
    assert run.bindings.ran == ran
    assert rows((run.registry,), run.key, "workflow_completed") == [None]


def test_two_processes_recovering_one_suspension_at_once_file_one_request(tmp_path: Path) -> None:
    """Two processes over one durable state store and one shared authority path
    recover the same stuck suspension at once. Process A's recovery is held
    inside its trace write (a slow artifact store, at the storage layer) while
    process B's runs to its end. One request is filed, by B, and A's recovery,
    finding the record moved since it read it, raises :class:`ExecutionFenced`
    having filed nothing."""
    records = StandInRecords()
    transport = DyingTransport()
    transport.scope = "shared"  # type: ignore[misc]
    a = compose(tmp_path / "a", store=SharedBackingStore(records), transport=transport)
    b = compose(tmp_path / "b", store=SharedBackingStore(records), transport=transport)
    stuck, _ = interrupt(a, "enqueue", lambda: start(a))
    assert (stuck.status, stuck.current_state) == ("suspended", FIRST_GATE)

    a.store.hold_next_trace_write()
    first = Worker(lambda: resume(a)).start()
    try:
        if not a.store.held.wait(HOLD_SECONDS):
            pytest.fail(f"process A's recovery never reached its trace write: {first.join()!r}")
        second = resume(b)
    finally:
        a.store.release.set()

    assert isinstance(second, WorkflowSuspended), second
    with pytest.raises(ExecutionFenced):
        first.join()
    assert requests(a, FIRST_GATE) == [the_request_a_suspension_files(a, stuck)]
    assert rows((a.registry, b.registry), a.key, "workflow_suspended") == [None, None], (
        "the suspension's own row and ONE recovery"
    )
    assert a.bindings.ran == ["skill:fetch-certificates"] and b.bindings.ran == []


# --- what the recovery must never do ---------------------------------------------


def test_a_request_the_approval_gate_resolved_is_never_filed_again(tmp_path: Path) -> None:
    """The run suspends normally and its request is RESOLVED through the real
    :class:`~ccf.hitl.approval_gate.ApprovalGate`, which claims the request off
    the queue before it records the approval. The run is now ``suspended`` with
    no pending request, and nothing is missing: a verdict recorded against the
    pending request is on the authority path. The starter's retried start must
    not file the request again, which would reopen a decided gate to more
    verdicts. It is refused "already exists" and files nothing, and the recorded
    approval still carries the run past the gate once."""
    run = compose(tmp_path)
    first = start(run)
    assert isinstance(first, WorkflowSuspended)
    eh._resolve_gate(
        run.registry, run.transport, tenant=run.tenant, event_key=first.event_key,
        action="approve", subject_id=APPROVER,
    )
    assert requests(run, FIRST_GATE) == []
    before = state_of(run)
    suspended_rows = rows((run.registry,), run.key, "workflow_suspended")

    again = start(run)

    assert isinstance(again, WorkflowResumeRefused), again
    assert ALREADY_EXISTS in again.reason, again.reason
    assert requests(run, FIRST_GATE) == [], "a resolved request was filed again"
    assert state_of(run) == before
    assert rows((run.registry,), run.key, "workflow_suspended") == suspended_rows
    passed = resume(run)
    assert isinstance(passed, WorkflowSuspended) and passed.gate == NEXT_GATE, passed
    assert run.bindings.ran.count(f"skill:{DOWNSTREAM}") == 1


# --- residuals, measured ----------------------------------------------------------
#
# Each test below pins what the recovery does NOT prevent, so the disclosure in
# ``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._restore_request``
# rests on a measurement. Each goes red if the residual is ever closed, and must
# then be rewritten to assert the closing mechanism.


@pytest.mark.parametrize("overlap", ["a slow suspension", "a recovery held at its enqueue"])
def test_an_overlapping_recovery_can_file_a_second_identical_request_and_the_gate_still_opens_once(
    tmp_path: Path, overlap: str
) -> None:
    """RESIDUAL. The conditional write orders recoveries that read the same
    version, not one that reads the record after another write landed and before
    that write's enqueue. Process A is held there, either inside its suspension's
    trace write (the suspension is alive but slow, after its suspension write
    landed) or inside a recovery's enqueue (after that recovery's write landed),
    while process B's resumption runs to its end. Both file the request: two
    identical requests for the one suspension. One approval then opens the gate
    exactly once, the gate's closure retires both requests, and a later verdict
    on the suspension is refused ``hitl-gate-closed``."""
    records = StandInRecords()
    transport = DyingTransport()
    transport.scope = "shared"  # type: ignore[misc]
    a = compose(tmp_path / "a", store=SharedBackingStore(records), transport=transport)
    b = compose(tmp_path / "b", store=SharedBackingStore(records), transport=transport)
    if overlap == "a slow suspension":
        a.store.hold_next_trace_write()
        held, release = a.store.held, a.store.release
        first = Worker(lambda: start(a)).start()
    else:
        interrupt(a, "enqueue", lambda: start(a))
        transport.hold_next_enqueue()
        held, release = transport.held, transport.release
        first = Worker(lambda: resume(a)).start()
    try:
        if not held.wait(HOLD_SECONDS):
            pytest.fail(f"process A was never held: {first.join()!r}")
        second = resume(b)
    finally:
        release.set()
    assert isinstance(second, WorkflowSuspended), second
    assert isinstance(first.join(), WorkflowSuspended)
    stuck = state_of(a)
    expected = the_request_a_suspension_files(a, stuck)
    assert requests(a, FIRST_GATE) == [expected, expected], "the residual: two identical requests"

    eh._resolve_gate(
        a.registry, transport, tenant=a.tenant, event_key=expected.event_key,
        action="approve", subject_id=APPROVER,
    )
    passed = resume(a)
    assert isinstance(passed, WorkflowSuspended) and passed.gate == NEXT_GATE, passed
    assert requests(a, FIRST_GATE) == [], "the gate's closure retired both requests"
    with pytest.raises(HitlGateClosed):
        eh._submit_only(
            transport, tenant=a.tenant, event_key=expected.event_key,
            product_content_hash=expected.product_content_hash, action="reject", subject_id=APPROVER,
        )
    assert isinstance(resume(b), WorkflowResumeRefused)
    assert a.bindings.ran.count(f"skill:{DOWNSTREAM}") == 1 and b.bindings.ran == []


def test_with_two_transports_over_one_state_store_a_recovery_files_on_its_own_transport(
    tmp_path: Path,
) -> None:
    """RESIDUAL: the deployment condition. Two engines over ONE state store,
    each with its own HITL transport, which is outside the posture SP §4.13
    requires (one shared HITL transport wherever one state store is resumed
    from). Engine A suspends normally, so the request is pending on A's
    transport. A resumption through engine B finds no approval and no request on
    B's transport, and files the request there: the suspension's request is
    pending on both, and each transport's verdicts are judged only by its own
    engine. The recovery cannot tell a request filed on another transport from
    one never filed, because nothing in the suspension names its transport."""
    store = InMemoryStateStore()
    a = compose(tmp_path / "a", store=store)
    b = compose(tmp_path / "b", store=store)
    assert a.transport is not b.transport and a.registry.state_store is b.registry.state_store
    first = start(a)
    assert isinstance(first, WorkflowSuspended)
    expected = the_request_a_suspension_files(a, state_of(a))
    assert requests(a, FIRST_GATE) == [expected] and requests(b, FIRST_GATE) == []

    outcome = resume(b)

    assert isinstance(outcome, WorkflowSuspended), outcome
    assert requests(a, FIRST_GATE) == [expected]
    assert requests(b, FIRST_GATE) == [expected], "the residual: filed again on B's transport"
    assert a.bindings.ran == ["skill:fetch-certificates"] and b.bindings.ran == []


def test_a_request_claimed_and_not_yet_answered_is_filed_again_and_its_verdict_still_counts_once(
    tmp_path: Path,
) -> None:
    """RESIDUAL. The real :class:`~ccf.hitl.approval_gate.ApprovalGate` claims
    the pending request (it removes it from the queue) and is held before the
    transport records its verdict. A claim is not visible through the transport
    Protocol, so a resumption then finds no request, no verdict and no closure,
    and files the request again; the transport's enqueue discards the
    outstanding claim, as its Protocol documents. The gate's verdict is then
    recorded against the restored request, unstamped (``pending``), and it
    carries the run past the gate exactly once."""
    run = compose(tmp_path)
    first = start(run)
    assert isinstance(first, WorkflowSuspended)
    run.transport.hold_next_submit()
    resolving = Worker(
        lambda: eh._resolve_gate(
            run.registry, run.transport, tenant=run.tenant, event_key=first.event_key,
            action="approve", subject_id=APPROVER,
        )
    ).start()
    try:
        if not run.transport.held.wait(HOLD_SECONDS):
            pytest.fail(f"the gate's submit was never held: {resolving.join()!r}")
        assert requests(run, FIRST_GATE) == [], "the gate claimed the request"
        restored = resume(run)
    finally:
        run.transport.release.set()
    resolving.join()

    assert isinstance(restored, WorkflowSuspended), restored
    (recorded,) = run.transport.submissions(tenant=run.tenant)
    assert (recorded.event_state_at_submit, recorded.answered_event_class) == ("pending", None)
    assert requests(run, FIRST_GATE) == [the_request_a_suspension_files(run, state_of(run))]
    passed = resume(run)
    assert isinstance(passed, WorkflowSuspended) and passed.gate == NEXT_GATE, passed
    assert requests(run, FIRST_GATE) == []
    assert run.bindings.ran.count(f"skill:{DOWNSTREAM}") == 1
