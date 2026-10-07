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
