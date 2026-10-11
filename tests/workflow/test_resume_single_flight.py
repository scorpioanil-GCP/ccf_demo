"""One resumption per execution at a time, in one process (D-IMPL-377; CLAUDE.md §8.1/§8.2).

RED FIRST. The residual ledger in
``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._gate_authority``,
item (2)(a): nothing made a resumption's read-decide-commit atomic, so two
concurrent resumes of ONE suspension, carrying ONE human approval, both
passed the authority read and the conflict check, ran the downstream node
twice, and wrote two attributed ``workflow_resumed`` rows. One human decision
became two passages. Measured on 2026-10-07 against 34a1f6bf: 5 of 5 on one
event loop with a downstream skill that awaits once, 5 of 5 with two OS
threads (one engine, and two engines over one Control Plane), and 3 of 3
through the served door (``tests/http_api/test_resume_single_flight_door.py``).

The controls here, each red before the single-flight claim existed:

* **one event loop**: ``asyncio.gather`` of two resumes. The downstream skill
  awaits ``asyncio.sleep(0)``, the smallest yield any I/O-bound skill makes,
  and no engine method is wrapped;
* **two OS threads**: the first resume is held inside its state read by a
  state store that pauses one armed read (the
  :class:`~ccf.controlplane.state.ControlPlaneStateStore` seam, not an engine
  internal), and the second resume runs while it is held. This runs once with
  one engine and once with two engines over one Control Plane, because the
  claim must hold for the process and not only for one engine instance.

Each control asserts what the hole did: the downstream node's run count, the
attributed rows and the pending events at the next gate. Each also asserts
that the second resume is refused BY THE CLAIM, identified by the claim's own
phrase.

Composition reuses the suite's own helpers (``tests/workflow/test_engine.py``
and ``tests/workflow/test_sec006_engine_controls.py``): the SEC-006 two-gate
release workflow, because its first gate's approve route leads to a real node
(``archive-certificates``) rather than straight to a terminal. Test vocabulary
only (CINV-01).
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import InMemoryStateStore
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.workflow.factory import Workflow
from ccf_runtime.workflow.engine import (
    WorkflowEngine,
    WorkflowOutcome,
    WorkflowResumeRefused,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE
from http_api.composition_authority import deployment_store
from tests.hitl.sec006_harness import execute_as_principal
from tests.workflow import test_engine as eh
from tests.workflow import test_sec006_engine_controls as s6

#: The claim's own phrase, from the refusal
#: ``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume`` returns
#: while another resumption of the same execution is in flight.
IN_FLIGHT = "already has a resumption in flight"
#: The refusal a resumption meets when the execution's passage has committed
#: and not finished (``D-IMPL-378``): :data:`RUNNING` names the record's state,
#: :data:`INTERRUPTED` the rule Dave's Q4 ruling set — an interrupted passage is
#: never retried. From the same engine refusal.
RUNNING = "has a committed passage that has not finished"
INTERRUPTED = "An interrupted passage is never retried"
#: The node the first gate's approve route leads to, and the decision naming it.
DOWNSTREAM = "archive-certificates"
NEXT_GATE = "second-approval"
STARTER = "officer-a"
APPROVER = "officer-b"
EXECUTION = "exec"
HOLD_SECONDS = 10.0


class AwaitingBindings(eh._Bindings):
    """The suite's node-binding double, except that the downstream step awaits
    once, as any real I/O-bound skill does. Nothing else differs."""

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        if step_name == DOWNSTREAM:
            await asyncio.sleep(0)
        return await super().run_skill(tenant=tenant, step_name=step_name, ref=ref)


class PausingStateStore(InMemoryStateStore):
    """The reference state store, holding ONE armed workflow-state read open.

    Once armed for a key, the first read of that key returns the record and
    then blocks its thread until :attr:`release` is set. This is the shape a
    thread preempted between its read and its commit takes. Every other read
    is the reference store's own.
    """

    def __init__(self) -> None:
        super().__init__()
        self._arm_lock = threading.Lock()
        self._armed: str | None = None
        self.held = threading.Event()
        self.release = threading.Event()

    def arm(self, key: str) -> None:
        with self._arm_lock:
            self._armed = key

    def get(self, record_class: str, key: str) -> object | None:
        record = super().get(record_class, key)
        with self._arm_lock:
            hold = record_class == WORKFLOW_STATE and key == self._armed
            if hold:
                self._armed = None
        if hold:
            self.held.set()
            if not self.release.wait(HOLD_SECONDS):
                raise RuntimeError("the held state read was never released")
        return record

    def get_versioned(self, record_class: str, key: str) -> tuple[object | None, int]:
        """The versioned read the engine makes since ``D-IMPL-378``, held the same way."""
        record, version = super().get_versioned(record_class, key)  # type: ignore[misc]
        with self._arm_lock:
            hold = record_class == WORKFLOW_STATE and key == self._armed
            if hold:
                self._armed = None
        if hold:
            self.held.set()
            if not self.release.wait(HOLD_SECONDS):
                raise RuntimeError("the held state read was never released")
        return record, version


class Worker:
    """One real OS thread running one call; its outcome or exception kept."""

    def __init__(self, call: Callable[[], Any]) -> None:
        self._box: dict[str, Any] = {}

        def target() -> None:
            try:
                self._box["outcome"] = call()
            except BaseException as error:  # re-raised in join()
                self._box["error"] = error

        self._thread = threading.Thread(target=target, daemon=True)

    def start(self) -> Worker:
        self._thread.start()
        return self

    def join(self) -> Any:
        self._thread.join(HOLD_SECONDS * 2)
        assert not self._thread.is_alive(), "the worker thread never finished"
        if "error" in self._box:
            raise self._box["error"]
        return self._box["outcome"]


def plane(store: InMemoryStateStore | None = None) -> ControlPlaneRegistry:
    """The ``registry`` fixture body of test_engine.py, over ``store`` when given."""
    registry = ControlPlaneRegistry(clock=eh._ticking_clock(), state_store=store)
    eh._register_covenant_closure(registry)
    eh._register_refresh_closure(registry)
    return registry


def engine_over(
    registry: ControlPlaneRegistry,
    tmp_path: Path,
    bindings: eh._Bindings,
    transport: InMemoryHitlTransport,
) -> WorkflowEngine:
    """``tests/workflow/test_engine.py::_engine``'s body, with ``bindings``."""
    return WorkflowEngine(
        control_plane=registry,
        artifact_store=deployment_store(tmp_path / "artifacts", workflow_traces=True),
        hitl_transport=transport,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=eh._ticking_clock(),
        debt_binding=eh._PermissiveDebt(),
    )


def approved_suspension(
    registry: ControlPlaneRegistry, tmp_path: Path, bindings: eh._Bindings
) -> tuple[WorkflowEngine, InMemoryHitlTransport, Workflow]:
    """The two-gate workflow suspended on ``first-approval``, approved ONCE.

    ``officer-a`` starts it and ``officer-b``, who is eligible and is not the
    starter, approves through the real
    :class:`~ccf.hitl.approval_gate.ApprovalGate`.
    """
    workflow = s6._two_gate(registry, eligible=frozenset({STARTER, APPROVER}))
    transport = InMemoryHitlTransport()
    engine = engine_over(registry, tmp_path, bindings, transport)
    tenant = workflow.definition.tenant
    starter = execute_as_principal(
        tenant=tenant, resource=workflow.definition_key, principal=STARTER
    )
    suspended = asyncio.run(engine.execute(starter, workflow, execution_id=EXECUTION))
    assert isinstance(suspended, WorkflowSuspended)
    assert suspended.gate == "first-approval"
    eh._resolve_gate(
        registry,
        transport,
        tenant=tenant,
        event_key=suspended.event_key,
        action="approve",
        subject_id=APPROVER,
    )
    return engine, transport, workflow


async def resume(engine: WorkflowEngine, workflow: Workflow) -> WorkflowOutcome:
    return await engine.resume(
        eh.resume_as(workflow), workflow, execution_id=EXECUTION, decision=DOWNSTREAM
    )


def assert_one_passage(
    registry: ControlPlaneRegistry,
    transport: InMemoryHitlTransport,
    workflow: Workflow,
    bindings: eh._Bindings,
    outcomes: list[WorkflowOutcome],
) -> None:
    """One human approval, one passage: the hole's three measures, then the
    refusal of the second resume by the claim's own phrase."""
    tenant = workflow.definition.tenant
    key = f"{tenant}/{EXECUTION}"
    runs = bindings.ran.count(f"skill:{DOWNSTREAM}")
    assert runs == 1, f"the downstream node ran {runs} times on one approval"
    attributed = [
        event.actor
        for event in registry.audit_log.events()
        if event.key == key
        and event.action == "workflow_resumed"
        and event.resolved
        and event.actor is not None
    ]
    assert attributed == [APPROVER], (
        f"attributed workflow_resumed rows on one approval: {attributed}"
    )
    next_gate = [
        event
        for event in transport.pending(tenant=tenant)
        if event.event_key == f"{key}/{NEXT_GATE}"
    ]
    assert len(next_gate) == 1, f"pending events at {NEXT_GATE}: {len(next_gate)}"
    progressed = [o for o in outcomes if isinstance(o, WorkflowSuspended)]
    refused = [o for o in outcomes if isinstance(o, WorkflowResumeRefused)]
    assert [o.gate for o in progressed] == [NEXT_GATE], outcomes
    assert len(refused) == 1, outcomes
    assert IN_FLIGHT in refused[0].reason, refused[0].reason
    # The refusal is audited as one, with no human named: nobody's verdict refused it.
    refusal_rows = [
        event
        for event in registry.audit_log.events()
        if event.key == key and event.action == "workflow_resumed" and not event.resolved
    ]
    assert [event.actor for event in refusal_rows] == [None], refusal_rows


def test_two_resumes_of_one_approval_on_one_event_loop_pass_the_gate_once(
    tmp_path: Path,
) -> None:
    """One event loop, no engine wrap: ``asyncio.gather`` of two resumes.

    Before the claim, the first resume yielded inside the downstream node, and
    the second read a state record nothing had committed over yet. It passed
    every check, and the node ran twice.
    """
    registry = plane()
    bindings = AwaitingBindings()
    engine, transport, workflow = approved_suspension(registry, tmp_path, bindings)

    async def both() -> list[WorkflowOutcome]:
        return list(await asyncio.gather(resume(engine, workflow), resume(engine, workflow)))

    outcomes = asyncio.run(both())
    assert_one_passage(registry, transport, workflow, bindings, outcomes)


@pytest.mark.parametrize(
    "engines", [1, 2], ids=["one-engine", "two-engines-one-control-plane"]
)
def test_a_resume_held_inside_its_read_on_another_thread_admits_no_second(
    tmp_path: Path, engines: int
) -> None:
    """Two OS threads. The first resume is held inside its own state read, and
    the second resume runs to its end while it is held.

    Before the claim, the second resume passed and committed. The first was
    then released holding the record it had already read, passed every check
    on that stale record, and ran the node again. With two engines over one
    Control Plane the shape is identical, so a claim scoped to one engine
    instance would leave this case red.
    """
    store = PausingStateStore()
    registry = plane(store)
    bindings = eh._Bindings()
    engine, transport, workflow = approved_suspension(registry, tmp_path, bindings)
    other = engine if engines == 1 else engine_over(registry, tmp_path, bindings, transport)
    store.arm(f"{workflow.definition.tenant}/{EXECUTION}")
    held = Worker(lambda: asyncio.run(resume(engine, workflow))).start()
    try:
        assert store.held.wait(HOLD_SECONDS), "the first resume never reached its read"
        second = asyncio.run(resume(other, workflow))
    finally:
        store.release.set()
    first = held.join()
    assert_one_passage(registry, transport, workflow, bindings, [first, second])


# --- the claim is given back on every exit ------------------------------------
#
# Green before the claim existed (nothing was ever taken) and green after; what
# they pin is the RELEASE. A claim kept past any one of these exits would refuse
# every later resumption of the execution as "in flight" for the life of the
# process, which is a permanent denial of service on that approval.


class FailingOnceStateStore(InMemoryStateStore):
    """The reference state store, failing its next workflow-state write once."""

    def __init__(self) -> None:
        super().__init__()
        self.fail_next_write = False

    def put(
        self,
        authorized: Any,
        record_class: str,
        record: object,
        *,
        record_id: str,
        token: Any,
    ) -> None:
        if self.fail_next_write and record_class == WORKFLOW_STATE:
            self.fail_next_write = False
            raise RuntimeError("state store unavailable")
        super().put(authorized, record_class, record, record_id=record_id, token=token)

    def put_if(
        self,
        authorized: Any,
        record_class: str,
        record: object,
        *,
        record_id: str,
        token: Any,
        expected_version: int,
    ) -> int:
        """The conditional write the engine makes since ``D-IMPL-378``, failing the same way."""
        if self.fail_next_write and record_class == WORKFLOW_STATE:
            self.fail_next_write = False
            raise RuntimeError("state store unavailable")
        return super().put_if(  # type: ignore[misc, no-any-return]
            authorized,
            record_class,
            record,
            record_id=record_id,
            token=token,
            expected_version=expected_version,
        )


class BlockingOnceBindings(eh._Bindings):
    """The downstream step's FIRST call never returns on its own; only
    cancellation ends it. Later calls are the suite's double."""

    def __init__(self) -> None:
        super().__init__()
        self.blocked = False

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        if step_name == DOWNSTREAM and not self.blocked:
            self.blocked = True
            await asyncio.Event().wait()
        return await super().run_skill(tenant=tenant, step_name=step_name, ref=ref)


def assert_not_held(outcome: WorkflowOutcome) -> None:
    """The later resumption passed: the claim had been given back."""
    if isinstance(outcome, WorkflowResumeRefused):
        assert IN_FLIGHT not in outcome.reason, "the claim was never released"
    assert isinstance(outcome, WorkflowSuspended), outcome
    assert outcome.gate == NEXT_GATE


def test_a_completed_resume_gives_the_claim_back(tmp_path: Path) -> None:
    """Completion: the next resumption is judged on its own authority, at the
    next gate, and the claim never answers it."""
    registry = plane()
    bindings = eh._Bindings()
    engine, transport, workflow = approved_suspension(registry, tmp_path, bindings)
    first = asyncio.run(resume(engine, workflow))
    assert isinstance(first, WorkflowSuspended) and first.gate == NEXT_GATE
    second = asyncio.run(resume(engine, workflow))
    assert isinstance(second, WorkflowResumeRefused)
    assert "no approval for this suspension" in second.reason
    assert IN_FLIGHT not in second.reason


def test_a_resume_refused_for_its_authority_gives_the_claim_back(tmp_path: Path) -> None:
    """Refusal: a resume refused before any approval is recorded returns the
    claim, so the resume after the approval passes."""
    registry = plane()
    bindings = eh._Bindings()
    workflow = s6._two_gate(registry, eligible=frozenset({STARTER, APPROVER}))
    transport = InMemoryHitlTransport()
    engine = engine_over(registry, tmp_path, bindings, transport)
    tenant = workflow.definition.tenant
    starter = execute_as_principal(
        tenant=tenant, resource=workflow.definition_key, principal=STARTER
    )
    suspended = asyncio.run(engine.execute(starter, workflow, execution_id=EXECUTION))
    assert isinstance(suspended, WorkflowSuspended)
    refused = asyncio.run(resume(engine, workflow))
    assert isinstance(refused, WorkflowResumeRefused)
    assert "no approval for this suspension" in refused.reason
    eh._resolve_gate(
        registry,
        transport,
        tenant=tenant,
        event_key=suspended.event_key,
        action="approve",
        subject_id=APPROVER,
    )
    assert_not_held(asyncio.run(resume(engine, workflow)))


def test_a_resume_that_raises_gives_the_claim_back(tmp_path: Path) -> None:
    """Exception: the state store fails the resume's commit, and the error
    propagates. The claim goes back with it, so the retry passes.

    Changed by Dave's Q4 ruling (``D-IMPL-378``), and only as far as it
    requires. Since the ruling, the first write a resumption makes is its
    passage commit, which comes BEFORE the step after the gate, so this
    failure lands before any step has run. The ruling admits a retry only with
    a durable claim naming the original passage and a proof that no effect can
    repeat. Here both hold: the gate's closure names the passage (by what it
    decides, not by who decides it) and the retry re-takes that one closure
    rather than a second; and the step had not run, and only one passage commit
    can land. So the retry runs the step ONCE. At ``7bf069cc`` the failing
    write came after the step, and the retry ran the step a second time — the
    repeated effect the ruling forbids.
    """
    store = FailingOnceStateStore()
    registry = plane(store)
    bindings = eh._Bindings()
    engine, transport, workflow = approved_suspension(registry, tmp_path, bindings)
    tenant = workflow.definition.tenant
    store.fail_next_write = True
    with pytest.raises(RuntimeError, match="state store unavailable"):
        asyncio.run(resume(engine, workflow))
    taken = transport.closures(tenant=tenant)
    assert len(taken) == 1, taken
    assert_not_held(asyncio.run(resume(engine, workflow)))
    # The retry re-took the SAME closure: one durable claim, one passage.
    assert transport.closures(tenant=tenant) == taken
    # The failed commit ran nothing; the retry ran the step once.
    assert bindings.ran.count(f"skill:{DOWNSTREAM}") == 1


def test_a_cancelled_resume_gives_the_claim_back(tmp_path: Path) -> None:
    """Cancellation: the resume is cancelled while the step after the gate
    awaits. The claim goes back with the cancellation: a later resume is not
    refused as in flight.

    Changed by Dave's Q4 ruling (``D-IMPL-378``), and only as far as it
    requires. The cancelled passage's commit had landed before its step began,
    so its step may already have had effects the engine cannot see, and no
    retry can be shown not to repeat them. The ruling's answer is (b): an
    interrupted passage is never retried. So the later resume is refused,
    typed, with the never-retried refusal — not with the in-flight one, which
    is the claim's release this test exists to pin — and the step does not run
    again. Before the ruling, the later resume passed and re-ran the step.
    """
    registry = plane()
    bindings = BlockingOnceBindings()
    engine, transport, workflow = approved_suspension(registry, tmp_path, bindings)

    async def cancel_then_resume() -> WorkflowOutcome:
        first = asyncio.create_task(resume(engine, workflow))
        for _ in range(10_000):
            if bindings.blocked:
                break
            await asyncio.sleep(0)
        assert bindings.blocked, "the first resume never reached the downstream node"
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        return await resume(engine, workflow)

    outcome = asyncio.run(cancel_then_resume())
    assert isinstance(outcome, WorkflowResumeRefused), outcome
    assert IN_FLIGHT not in outcome.reason, "the claim was never released"
    assert INTERRUPTED in outcome.reason, outcome.reason
    assert RUNNING in outcome.reason, outcome.reason
    # The cancelled first call never finished, and nothing re-ran the step.
    assert bindings.ran.count(f"skill:{DOWNSTREAM}") == 0
