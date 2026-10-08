"""A fenced passage reaches the workflow doors' callers as a typed refusal, never a 500 (``D-IMPL-378``; Dave, 2026-10-07 21:11 MST).

**The hole, as measured by lane 378b-approval.** A passage's closing write is
conditional on the version the passage wrote
(``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._fenced_write``). When a
writer outside the engine, or a store that does not keep its own conditional
write, moves the execution's record under a passage, that write raises
:class:`~ccf_runtime.workflow.engine.ExecutionFenced` and writes, appends and
enqueues nothing. The engine RAISES it rather than returning a refusal, and the
workflow doors (``runtime/ccf_runtime/http_api/routes/workflow.py::build_router``)
mapped only the refusals the engine returns, so it escaped them unmapped: an HTTP
caller got an opaque ``500 Internal Server Error``.

**Dave's ruling (21:11 MST, "yes fix both now").** Map it to a typed refusal at
every door that drives workflows: HTTP 409 with its own error code,
``execution-fenced`` (``ccf_runtime.http_api.errors.ERROR_EXECUTION_FENCED``).

**The doors.** ``git grep`` over ``src`` and ``runtime`` finds the engine's
``execute`` and ``resume`` called by the two HTTP workflow routes,
``POST /workflow/invocations`` and ``POST /workflow/resumptions`` (the CLI's
``workflow invoke`` and ``workflow resume`` reach the same routes); by the
in-process orchestration drivers, which hand the engine's own exception back to
their caller by name; and by the in-process erasure door. No MCP door executes or
resumes a workflow.

Each door is driven as a caller drives it, over the suite's governed application
(``tests/http_api/test_approval_gate_limits_door.py``). The other writer plays as
it does in the approval lane's in-process fence test
(``tests/workflow/test_execution_fenced.py``): while the step runs, an
:class:`~ccf.controlplane.state.AuditedStateWriter` over the same state store
writes the execution's record. The client does not raise the application's
exceptions, so each test sees the status a caller over the network sees. Each red
test has a positive control: the same request with no other writer answers 200.
Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from ccf.controlplane.audit import AuditEvent
from ccf.controlplane.state import AuditedStateWriter
from ccf_runtime.workflow.state import WORKFLOW_STATE
from http_api.test_approval_gate_limits_door import (
    APPROVER,
    EXECUTION,
    STARTER,
    Door,
    act,
    bound_hash,
    fabric_at,
    open_door,
    resume_at,
)
from tests.workflow import test_engine as eh
from tests.workflow.capabilities import execute_capability
from tests.workflow.test_approval_gate_limits import FIRST_GATE, START
from tests.workflow.test_resume_single_flight import DOWNSTREAM, NEXT_GATE

#: The fence's own phrase (``WorkflowEngine._fenced_write``).
FENCED = "was moved by another writer"


class MovingBindings(eh._Bindings):
    """The suite's node-binding double, except that while ``step`` runs, ``move``
    runs once: the writer outside the engine."""

    def __init__(self, step: str) -> None:
        super().__init__()
        self._step = step
        self.move: Callable[[], None] | None = None

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        if step_name == self._step and self.move is not None:
            move, self.move = self.move, None
            move()
        return await super().run_skill(tenant=tenant, step_name=step_name, ref=ref)


def _execution_fenced_code() -> str:
    """The named constant the wire code must equal; reported if absent."""
    from ccf_runtime.http_api import errors

    code = getattr(errors, "ERROR_EXECUTION_FENCED", None)
    assert code == "execution-fenced", (
        f"MISSING CONTRACT: ccf_runtime.http_api.errors.ERROR_EXECUTION_FENCED is {code!r}"
    )
    return code


def _unraised(door: Door) -> httpx.AsyncClient:
    """A client that, like a caller over the network, gets the application's
    error STATUS instead of its exception."""
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=door.app, raise_app_exceptions=False),
        base_url="http://fabric.invalid",
    )


def _other_writer(door: Door, tenant: str, moved: list[tuple[object | None, int]]) -> Callable[[], None]:
    """Write the execution's record once more, as a writer outside the engine
    over the same state store — the shape ``tests/workflow/test_execution_fenced.py`` plays."""
    store = door.fabric.registry.state_store
    key = f"{tenant}/{EXECUTION}"

    def move() -> None:
        record, version = store.get_versioned(WORKFLOW_STATE, key)
        assert getattr(record, "status", None) == "running", record
        AuditedStateWriter(store=store, audit=door.fabric.registry.audit_log).write(
            execute_capability(tenant=tenant, resource=door.key),
            WORKFLOW_STATE,
            record,
            record_id=EXECUTION,
            event=AuditEvent(
                sequence=0,
                action="state_written",
                key=key,
                version=door.version,
                resolved=True,
                occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
            ),
        )
        moved.append(store.get_versioned(WORKFLOW_STATE, key))
        assert moved[0][1] == version + 1

    return move


def _suspensions_audited(door: Door, key: str) -> list[AuditEvent]:
    return [
        event
        for event in door.fabric.registry.audit_log.events()
        if event.key == key and event.action == "workflow_suspended"
    ]


def _pending_at(door: Door, tenant: str, gate: str) -> list[Any]:
    return [
        event
        for event in door.fabric.hitl.pending(tenant=tenant)
        if event.event_key == f"{tenant}/{EXECUTION}/{gate}"
    ]


def _drive(
    tmp_path: Path, which: str, *, other_writer: bool
) -> tuple[httpx.Response, Door, str, list[tuple[object | None, int]], MovingBindings]:
    """One request at ``which`` door — the invocation, or the resumption after an
    approval — with the other writer moving the record while the step runs, or not."""
    bindings = MovingBindings(START if which == "invocation" else DOWNSTREAM)
    fabric, key, version = fabric_at(tmp_path / "fabric", two_gate=True)
    door = open_door(fabric, key, version, tmp_path / "gate", bindings)
    tenant = str(fabric.product_address.tenant)
    moved: list[tuple[object | None, int]] = []
    if which == "invocation" and other_writer:
        bindings.move = _other_writer(door, tenant, moved)

    async def flow() -> httpx.Response:
        async with _unraised(door) as c:
            invocation = {"definition_key": key, "definition_version": version, "execution_id": EXECUTION}
            invoked = await c.post("/workflow/invocations", json=invocation, headers=STARTER)
            if which == "invocation":
                return invoked
            assert invoked.status_code == 200, invoked.text
            event_key = invoked.json()["event_key"]
            approved = await act(
                c, event_key=event_key, bound=bound_hash(door, tenant, event_key), action="approve", headers=APPROVER
            )
            assert approved.status_code == 200, approved.text
            if other_writer:
                bindings.move = _other_writer(door, tenant, moved)
            return await resume_at(c, door, DOWNSTREAM)

    return asyncio.run(flow()), door, tenant, moved, bindings


def _assert_refused_execution_fenced(response: httpx.Response) -> None:
    assert response.status_code == 409, (
        f"the fenced passage reached the caller as {response.status_code}, not a typed 409:"
        f" {response.text[:300]!r}"
    )
    detail = response.json()["detail"]
    assert detail["error_code"] == _execution_fenced_code(), detail
    assert FENCED in detail["message"], detail


def test_a_passage_fenced_at_the_resumption_door_is_refused_409_execution_fenced(tmp_path: Path) -> None:
    """``credit-officer-11`` approves at the action door; the resumption passes
    the gate, and while the step after it runs, the other writer moves the
    execution's record. The passage's next write, its suspension at the next
    gate, is fenced. Before the ruling the resumption door answered 500."""
    response, door, tenant, moved, bindings = _drive(tmp_path, "resumption", other_writer=True)
    key = f"{tenant}/{EXECUTION}"
    assert moved, "the other writer never ran"
    assert bindings.ran.count(f"skill:{DOWNSTREAM}") == 1
    _assert_refused_execution_fenced(response)
    # The fence's own guarantees, through the door: the other writer's record
    # stands, no suspension at the next gate was audited, and it is not offered.
    assert door.fabric.registry.state_store.get_versioned(WORKFLOW_STATE, key) == moved[0]
    assert len(_suspensions_audited(door, key)) == 1, "only the first gate's suspension is audited"
    assert not _pending_at(door, tenant, NEXT_GATE)


def test_a_passage_fenced_at_the_invocation_door_is_refused_409_execution_fenced(tmp_path: Path) -> None:
    """The invocation records the execution ``running`` before its start node
    runs; while that node runs, the other writer moves the record. The
    suspension at the first gate is fenced. Before the ruling the invocation door
    answered 500."""
    response, door, tenant, moved, bindings = _drive(tmp_path, "invocation", other_writer=True)
    key = f"{tenant}/{EXECUTION}"
    assert moved, "the other writer never ran"
    assert bindings.ran.count(f"skill:{START}") == 1
    _assert_refused_execution_fenced(response)
    assert door.fabric.registry.state_store.get_versioned(WORKFLOW_STATE, key) == moved[0]
    assert not _suspensions_audited(door, key)
    assert not _pending_at(door, tenant, FIRST_GATE)


@pytest.mark.parametrize("which", ["invocation", "resumption"])
def test_the_same_request_with_no_other_writer_answers_200(tmp_path: Path, which: str) -> None:
    """Positive control: no writer outside the engine, so the fence never fires
    and the door answers 200 with the suspension at the next gate."""
    response, door, tenant, moved, _bindings = _drive(tmp_path, which, other_writer=False)
    assert not moved
    assert response.status_code == 200, response.text
    gate = FIRST_GATE if which == "invocation" else NEXT_GATE
    assert response.json()["gate"] == gate
    assert len(_pending_at(door, tenant, gate)) == 1
