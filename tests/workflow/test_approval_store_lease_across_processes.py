# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A single-process approval store refuses a second process (SEC-001; D-IMPL-391, ruling 2(a)).

Dave's ruling 2(a) of 2026-10-17 13:27 MST: *"Stores labeled single-process get
the graph store's lock. A second process is refused by name."* His criterion A
of 11:28 asks that a second process be unable to submit a verdict or read
in-flight state, refused with a named, recorded error; his answers of 15:25 MST
read "recorded" as *"Logged by the refused process only"* and extend the lock to
the approval queue (*"Cover the queue as well."*).

The SDK ships no approval store a second process can reach, so the criterion is
proved on the path-backed stand-in pair of
``tests/support/path_backed_approval_pair.py`` — a ``"process"`` state store at
``P/state/`` and a ``"process"`` HITL transport at ``P/queue/``, each taking the
graph store's ``LockFileWriterLease`` inside its own directory when it is
OPENED — in real OS processes (``multiprocessing``, spawn):

* **A.** Process 1 opens ``P``, suspends a run and records a verdict. While it
  lives, process 2's attempt to open the store and its attempt to open the
  queue are each refused with ``WriterLeaseHeld``, naming the lock and the rule,
  and process 2 logs one record saying so: it can neither submit a verdict nor
  read process 1's in-flight state. After process 1 exits cleanly, process 3
  opens ``P`` and the run passes its gate on process 1's verdict, because both
  halves are durable.
* **B4.** Process 3's store has process 1's identity, and the suspension
  process 1 wrote carries it (new with design 1.4).
* **D1.** Two processes on distinct paths both succeed (a guard).
* **D2.** A holder killed with SIGKILL does not leave ``P`` locked; the positive
  control is that process 2 is refused while process 1 lives.
* **The in-process control.** In one process the pair at ``P`` admits itself; a
  second live object at ``P`` is refused; dropping and collecting the first
  pair frees ``P``.

Children report outcomes over a queue (exception class name and message:
exceptions do not pickle reliably across spawn) and never sleep to synchronize.
Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
import gc
import logging
import multiprocessing as mp
import os
import signal
from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import WriterLeaseHeld
from ccf_runtime.workflow.state import WORKFLOW_STATE
from tests.support.path_backed_approval_pair import (
    LEASE_LOG,
    LOCK_FILENAME,
    SINGLE_PROCESS_RULE,
    PathBackedHitlTransport,
    PathBackedStateStore,
    open_pair,
)

_TIMEOUT = 120.0
NEXT_GATE = "second-approval"


def _compose(root: Path, store: Any, transport: Any) -> dict[str, Any]:
    """The suite's two-gate composition over the pair at ``root``."""
    from tests.hitl.sec006_harness import execute_as_principal
    from tests.workflow import test_engine as eh
    from tests.workflow import test_sec006_engine_controls as s6
    from tests.workflow.test_resume_single_flight import (
        APPROVER,
        EXECUTION,
        STARTER,
        engine_over,
        plane,
        resume,
    )

    registry = plane(store)
    workflow = s6._two_gate(registry, eligible=frozenset({STARTER, APPROVER}))
    bindings = eh._Bindings()
    engine = engine_over(registry, root, bindings, transport)
    tenant = workflow.definition.tenant

    def start() -> Any:
        starter = execute_as_principal(
            tenant=tenant, resource=workflow.definition_key, principal=STARTER
        )
        return asyncio.run(engine.execute(starter, workflow, execution_id=EXECUTION))

    def approve(event_key: str) -> None:
        eh._resolve_gate(
            registry, transport, tenant=tenant, event_key=event_key,
            action="approve", subject_id=APPROVER,
        )

    return {
        "registry": registry,
        "engine": engine,
        "workflow": workflow,
        "bindings": bindings,
        "tenant": tenant,
        "key": f"{tenant}/{EXECUTION}",
        "start": start,
        "approve": approve,
        "resume": lambda: asyncio.run(resume(engine, workflow)),
    }


def _holder(root: str, reports: Any, release: Any) -> None:
    """Process 1: open P, suspend a run, record a verdict, report, hold until released."""
    try:
        store, transport = open_pair(root)
        deployment = _compose(Path(root), store, transport)
        suspended = deployment["start"]()
        deployment["approve"](suspended.event_key)
        record = store.get(WORKFLOW_STATE, deployment["key"])
        reports.put(
            (
                "HELD",
                {
                    "identity": getattr(store, "identity", None),
                    "record_identity": getattr(record, "state_store_identity", None),
                    "suspension": content_hash(record),
                    "submissions": len(transport.submissions(tenant=deployment["tenant"])),
                },
            )
        )
    except BaseException as exc:
        reports.put(("ERROR", {"error": f"{type(exc).__name__}: {exc}"}))
        return
    if not release.wait(_TIMEOUT):
        return
    store.close()
    transport.close()
    reports.put(("CLOSED", {}))


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _intruder(root: str, reports: Any) -> None:
    """Process 2: try to open the store, then the queue, at P; report each outcome and the logs."""
    handler = _Records()
    LEASE_LOG.addHandler(handler)
    LEASE_LOG.setLevel(logging.INFO)
    outcomes: dict[str, tuple[str, str, str]] = {}
    for half, opener in (
        ("store", lambda: PathBackedStateStore(Path(root) / "state")),
        ("queue", lambda: PathBackedHitlTransport(Path(root) / "queue")),
    ):
        try:
            opened = opener()
        except BaseException as exc:
            outcomes[half] = ("REFUSED", type(exc).__name__, str(exc))
        else:
            if half == "store":
                held = len(getattr(opened, "_records", {}))
                outcomes[half] = ("OPENED", "", f"read {held} records")
            else:
                outcomes[half] = ("OPENED", "", "read the queue")
            opened.close()
    reports.put(("INTRUDER", {"outcomes": outcomes, "logs": handler.messages}))


def _resumer(root: str, reports: Any) -> None:
    """Process 3: open P after the holder is gone and resume the suspended run."""
    try:
        store, transport = open_pair(root)
        deployment = _compose(Path(root), store, transport)
        outcome = deployment["resume"]()
        reports.put(
            (
                "RESUMED",
                {
                    "outcome": type(outcome).__name__,
                    "gate": getattr(outcome, "gate", None),
                    "identity": getattr(store, "identity", None),
                    "downstream_runs": len(deployment["bindings"].ran),
                },
            )
        )
        store.close()
        transport.close()
    except BaseException as exc:
        reports.put(("ERROR", {"error": f"{type(exc).__name__}: {exc}"}))


def _spawn(target: Any, *args: Any) -> tuple[Any, Any]:
    ctx = mp.get_context("spawn")
    reports = ctx.Queue()
    process = ctx.Process(target=target, args=(*args, reports), daemon=True)
    process.start()
    return process, reports


def _report(reports: Any, expected: str) -> dict[str, Any]:
    kind, body = reports.get(timeout=_TIMEOUT)
    assert kind == expected, (kind, body)
    result: dict[str, Any] = body
    return result


def _hold(root: Path) -> tuple[Any, Any, Any, dict[str, Any]]:
    ctx = mp.get_context("spawn")
    reports = ctx.Queue()
    release = ctx.Event()
    process = ctx.Process(target=_holder, args=(str(root), reports, release), daemon=True)
    process.start()
    return process, reports, release, _report(reports, "HELD")


def _intrude(root: Path) -> dict[str, Any]:
    process, reports = _spawn(_intruder, str(root))
    try:
        return _report(reports, "INTRUDER")
    finally:
        process.join(_TIMEOUT)


def _resume(root: Path) -> dict[str, Any]:
    process, reports = _spawn(_resumer, str(root))
    try:
        return _report(reports, "RESUMED")
    finally:
        process.join(_TIMEOUT)


def _assert_refused_by_name(intrusion: dict[str, Any], root: Path) -> None:
    for half, directory in (("store", root / "state"), ("queue", root / "queue")):
        status, name, message = intrusion["outcomes"][half]
        assert (status, name) == ("REFUSED", "WriterLeaseHeld"), (
            f"process 2 opened the {half} at P while process 1 held it: {message}"
        )
        assert str(directory / LOCK_FILENAME) in message and SINGLE_PROCESS_RULE in message, message
        assert any(
            str(directory / LOCK_FILENAME) in line and SINGLE_PROCESS_RULE in line
            for line in intrusion["logs"]
        ), f"the refused process logged no record naming the {half}'s lock and the rule"


def test_a_a_second_process_can_neither_open_the_store_nor_the_queue(tmp_path: Path) -> None:
    """Criterion A and B4: refused by name while process 1 holds P; after a clean
    exit, a new process opens P and the run passes on process 1's verdict, under
    process 1's store identity."""
    root = tmp_path / "P"
    holder, reports, release, held = _hold(root)
    try:
        intrusion = _intrude(root)
    finally:
        release.set()
        _report(reports, "CLOSED")
        holder.join(_TIMEOUT)
    _assert_refused_by_name(intrusion, root)
    assert held["submissions"] == 1

    resumed = _resume(root)

    assert (resumed["outcome"], resumed["gate"]) == ("WorkflowSuspended", NEXT_GATE), resumed
    assert resumed["downstream_runs"] == 1
    assert held["identity"] is not None and resumed["identity"] == held["identity"], (
        "the reopened store does not keep its identity"
    )
    assert held["record_identity"] == held["identity"], (
        "the suspension process 1 wrote does not name its store"
    )


def test_d1_two_processes_on_distinct_paths_both_succeed(tmp_path: Path) -> None:
    holders = [_hold(tmp_path / name) for name in ("Pa", "Pb")]
    for process, reports, release, _held in holders:
        release.set()
        _report(reports, "CLOSED")
        process.join(_TIMEOUT)
    for name in ("Pa", "Pb"):
        resumed = _resume(tmp_path / name)
        assert (resumed["outcome"], resumed["gate"]) == ("WorkflowSuspended", NEXT_GATE), resumed


def test_d2_a_holder_killed_with_sigkill_does_not_leave_p_locked(tmp_path: Path) -> None:
    root = tmp_path / "P"
    holder, _reports, _release, _held = _hold(root)
    # The positive control: while process 1 lives, process 2 is refused.
    intrusion = _intrude(root)
    # Killed while waiting on its release event; the event is never touched
    # again, since a process killed inside a wait can leave its condition's
    # internal count for a later ``set`` to block on.
    os.kill(holder.pid, signal.SIGKILL)
    holder.join(_TIMEOUT)
    assert holder.exitcode == -signal.SIGKILL
    _assert_refused_by_name(intrusion, root)
    resumed = _resume(root)
    assert (resumed["outcome"], resumed["gate"]) == ("WorkflowSuspended", NEXT_GATE), resumed


def test_the_in_process_lease_control(tmp_path: Path) -> None:
    """One process admits its own pair; a second live object at P is refused;
    dropping and collecting the first pair frees P."""
    root = tmp_path / "P"
    store, transport = open_pair(root)
    deployment = _compose(root, store, transport)
    assert deployment["engine"] is not None
    with pytest.raises(WriterLeaseHeld, match="is held"):
        PathBackedStateStore(root / "state")
    with pytest.raises(WriterLeaseHeld, match="is held"):
        PathBackedHitlTransport(root / "queue")

    del store, transport, deployment
    gc.collect()

    try:
        again_store, again_transport = open_pair(root)
    except WriterLeaseHeld as exc:
        pytest.fail(f"P stayed locked after its pair was dropped and collected: {exc}")
    assert again_store.writer_lease().scope == "cross-process"
    again_store.close()
    again_transport.close()
