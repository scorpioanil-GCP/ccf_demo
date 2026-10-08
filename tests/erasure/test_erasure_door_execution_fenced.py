"""A passage the engine fenced reaches the erasure door's caller as a typed refusal (``D-IMPL-378``).

**The hole.** The workflow engine raises
:class:`~ccf_runtime.workflow.engine.ExecutionFenced` when a write that ends a
passage finds the execution's record moved by another writer
(``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._fenced_write``); it
then writes, audits and enqueues nothing more. The erasure door
(``runtime/ccf_runtime/erasure/door.py::ErasureDoor``) drives the engine in
process — ``request`` executes the declared erasure workflow and ``complete``
resumes it — and refuses by name with :class:`~ccf_runtime.erasure.ErasureRefused`
everywhere else, but let ``ExecutionFenced`` escape unmapped. Since lane
378c-finish (Dave's D2 ruling) a retried request or completion can also reach
the fence through the engine's finisher, when another finisher, or the
original passage, writes first.

**The coordinator's instruction (Dave's 21:11 MST order, lane 378c-d3).**
Render it as a typed ``ErasureRefused`` whose reason code matches the workflow
doors' (``execution-fenced``). No HTTP or MCP door serves the erasure door: it
is in process only (``git grep`` over ``src`` and ``runtime``).

The other writer plays as in ``tests/workflow/test_execution_fenced.py``: an
:class:`~ccf.controlplane.state.AuditedStateWriter` over the same state store
writes the execution's record once more, just before the engine's own fenced
write. The erasure workflow runs no step (its first node is its gate, and the
gate's approve route leads straight to ``erased``), so the move is placed at the
store's conditional write, where ``tests/erasure/test_interrupted_erasure_passage.py``
places the engine's death. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.controlplane.audit import AuditEvent
from ccf.controlplane.state import AuditedStateWriter, state_key
from ccf_runtime.erasure import ErasureRefused
from ccf_runtime.workflow.engine import ExecutionFenced
from ccf_runtime.workflow.state import WORKFLOW_STATE
from tests.erasure import composed
from tests.erasure import harness as h
from tests.erasure.test_interrupted_erasure_passage import (
    complete_through,
    die_once_at,
    outcome,
    request_through,
    rows,
    state,
)
from tests.workflow.capabilities import execute_capability

#: The fence's own phrase (``WorkflowEngine._fenced_write``).
FENCED = "was moved by another writer"


def moved_once_before(
    monkeypatch: pytest.MonkeyPatch, plane: h.Plane, *, status: str
) -> list[tuple[object | None, int]]:
    """Just before the engine's next conditional write of a workflow-state
    record with ``status``, another writer writes the execution's record once.
    Returns the record and version that writer left, once it has run."""
    store = plane.registry.state_store
    real = store.put_if
    moved: list[tuple[object | None, int]] = []

    def moving(authorized: Any, record_class: str, record: object, **kwargs: Any) -> int:
        if record_class == WORKFLOW_STATE and getattr(record, "status", None) == status:
            monkeypatch.setattr(store, "put_if", real)
            execution_id = kwargs["record_id"]
            key = state_key(tenant=h.TENANT, record_id=execution_id)
            current, version = store.get_versioned(WORKFLOW_STATE, key)
            AuditedStateWriter(store=store, audit=plane.registry.audit_log).write(
                execute_capability(tenant=h.TENANT, resource=h.WORKFLOW_KEY),
                WORKFLOW_STATE,
                current,
                record_id=execution_id,
                event=AuditEvent(
                    sequence=0,
                    action="state_written",
                    key=key,
                    version=plane.definition_version,
                    resolved=True,
                    occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
                ),
            )
            moved.append(store.get_versioned(WORKFLOW_STATE, key))
            assert moved[0][1] == version + 1
        return real(authorized, record_class, record, **kwargs)  # type: ignore[no-any-return]

    monkeypatch.setattr(store, "put_if", moving)
    return moved


def _assert_refused_execution_fenced(refused: pytest.ExceptionInfo[ErasureRefused]) -> None:
    assert refused.value.reason_code == "execution-fenced", refused.value.reason_code
    assert isinstance(refused.value.__cause__, ExecutionFenced), refused.value.__cause__
    assert FENCED in str(refused.value.__cause__)


def _record_count(plane: h.Plane) -> int:
    prefix = f"{h.TENANT}/{h.ERASURE_RECORD_CLASS}/"
    return sum(1 for key in plane.store._read_index() if key.startswith(prefix))


def test_a_request_whose_first_suspension_is_fenced_is_refused_execution_fenced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``request`` starts the erasure workflow; another writer moves the record
    before its suspension on the approval gate. Refused ``execution-fenced``:
    no approval is offered, no suspension is audited, the other writer's record
    stands."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    moved = moved_once_before(monkeypatch, plane, status="suspended")
    with pytest.raises(ErasureRefused) as refused:
        request_through(plane, request)
    assert moved, "the other writer never ran"
    _assert_refused_execution_fenced(refused)
    assert not plane.transport.pending(tenant=h.TENANT)
    assert rows(plane, request, "workflow_suspended") == []
    key = state_key(tenant=h.TENANT, record_id=request.request_id)
    assert plane.registry.state_store.get_versioned(WORKFLOW_STATE, key) == moved[0]


def test_a_retried_request_whose_finished_start_is_fenced_is_refused_execution_fenced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lane 378c-finish's site: the request's engine dies at its first
    suspension write, so the run is ``running`` at the gate with no step run;
    its retry is FINISHED by the engine (Dave's D2), and another writer moves
    the record before the finisher's suspension write. Refused
    ``execution-fenced``, nothing offered."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    die_once_at(monkeypatch, plane, status="suspended")
    with pytest.raises(OSError, match="died at the suspended state write"):
        request_through(plane, request)
    stuck = state(plane, request)
    assert (stuck.status, stuck.current_state, stuck.trace) == ("running", composed.GATE, ())

    moved = moved_once_before(monkeypatch, plane, status="suspended")
    with pytest.raises(ErasureRefused) as refused:
        request_through(plane, request)
    assert moved, "the other writer never ran"
    _assert_refused_execution_fenced(refused)
    assert not plane.transport.pending(tenant=h.TENANT)
    assert rows(plane, request, "workflow_started") == [None], "the retry finished the start; it never restarted it"
    assert rows(plane, request, "workflow_suspended") == []


def test_a_completion_whose_terminal_write_is_fenced_is_refused_execution_fenced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``complete`` appends the write-ahead index entries and resumes the
    engine past the gate; another writer moves the record before the terminal
    write. Refused ``execution-fenced``: no erasure record is filed, and the
    address stays withheld under its write-ahead entry, ``index-unsupported``."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    suspended = request_through(plane, request)
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    moved = moved_once_before(monkeypatch, plane, status="terminal")
    with pytest.raises(ErasureRefused) as refused:
        complete_through(plane, request, resolution)
    assert moved, "the other writer never ran"
    _assert_refused_execution_fenced(refused)
    assert _record_count(plane) == 0
    assert rows(plane, request, "workflow_completed") == []
    assert outcome(plane) == "unsupported(index-unsupported)"


def test_a_retried_completion_whose_finished_passage_is_fenced_is_refused_execution_fenced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lane 378c-finish's site in ``complete``: the completion's engine dies at
    its terminal write, so the run is ``running`` at ``erased``; its retry is
    finished by the engine, and another writer moves the record before the
    finisher's terminal write. Refused ``execution-fenced``: no record filed,
    the address withheld ``index-unsupported``."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    suspended = request_through(plane, request)
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    die_once_at(monkeypatch, plane, status="terminal")
    with pytest.raises(OSError, match="died at the terminal state write"):
        complete_through(plane, request, resolution)
    stuck = state(plane, request)
    assert (stuck.status, stuck.current_state) == ("running", "erased")

    moved = moved_once_before(monkeypatch, plane, status="terminal")
    with pytest.raises(ErasureRefused) as refused:
        complete_through(plane, request, resolution)
    assert moved, "the other writer never ran"
    _assert_refused_execution_fenced(refused)
    assert _record_count(plane) == 0
    assert rows(plane, request, "workflow_completed") == []
    assert outcome(plane) == "unsupported(index-unsupported)"
