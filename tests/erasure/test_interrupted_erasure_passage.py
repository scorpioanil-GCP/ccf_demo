"""An erasure interrupted where no step runs is FINISHED by its retry, through the shipped door (D-IMPL-378, D2).

The erasure workflow's first node is its approval gate, and the gate's approve
route leads straight to the terminal state ``erased``. Since ``D-IMPL-378`` the
engine records an execution ``running`` at its start before it suspends, and a
passage ``running`` at its decision before its next write. So an engine that
dies at the request's first suspension write, or at the completion's terminal
write, leaves the run ``running`` with no step run. Under Q4's never-retry rule
both retries were refused — measured by two probes on lane ``378b-approval`` at
``7d856fc6``, where the merge base ``b591ff69`` recovered both:

* the request's retry was refused ``workflow-not-suspended``, the run stuck at
  ``running`` on ``erasure-approval``;
* the completion's retry was refused ``approval-not-recorded`` — a name for a
  cause that was not the cause — the run stuck at ``running`` on ``erased``,
  the address withheld ``index-unsupported`` and no erasure record filed.

Dave's D2 ruling (2026-10-07): *"(a) Let the engine finish a stuck run whose
current state is a gate or the end state. No step ran there, so it provably
can't duplicate an effect, which meets your Q4 condition."* Each test below
dies once at the named write and then presents the SAME request through a fresh
:class:`~ccf_runtime.erasure.door.ErasureDoor` over the same plane, as a
restarted door would: the retry finishes the run, never re-runs it, and the
door's contract is otherwise the one ``tests/erasure`` already pins — one
approval row, one completion, the record the write-ahead entries name.

RED FIRST: committed before the finisher existed. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.state import state_key
from ccf_runtime.workflow.engine import WorkflowSuspended
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from tests.erasure import composed
from tests.erasure import harness as h


def die_once_at(monkeypatch: pytest.MonkeyPatch, plane: h.Plane, *, status: str) -> None:
    """The engine's process dies at the next write of a workflow-state record
    with ``status``: that write raises, and nothing is written."""
    store = plane.registry.state_store
    real = store.put_if

    def dying(authorized: Any, record_class: str, record: object, **kwargs: Any) -> int:
        if record_class == WORKFLOW_STATE and getattr(record, "status", None) == status:
            monkeypatch.setattr(store, "put_if", real)
            raise OSError(f"the engine's process died at the {status} state write")
        return real(authorized, record_class, record, **kwargs)  # type: ignore[no-any-return]

    monkeypatch.setattr(store, "put_if", dying)


def state(plane: h.Plane, request: Any) -> WorkflowStateRecord:
    record = plane.registry.state_store.get(
        WORKFLOW_STATE, state_key(tenant=h.TENANT, record_id=request.request_id)
    )
    assert isinstance(record, WorkflowStateRecord)
    return record


def rows(plane: h.Plane, request: Any, action: str) -> list[str | None]:
    """The actor of every resolved ``action`` row for the request's execution."""
    key = state_key(tenant=h.TENANT, record_id=request.request_id)
    return [
        event.actor
        for event in plane.registry.audit_log.events()
        if event.key == key and event.action == action and event.resolved
    ]


def outcome(plane: h.Plane) -> str:
    """How a consult answers the requested address: the record's own reason
    (``supported``), or the reason it withholds it with."""
    consult = h.erasure("compose_erasure_consult")(
        plane.store, index=h.index_of(plane), audit_log=plane.registry.audit_log,
        clock=h.fabric_clock, erasure_trust=h.trust(plane), control_plane=plane.registry, tenant_id=h.TENANT,
    )
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consult.get(content_address=plane.document.content_address)
    return "supported" if refused.value.reason == composed.REASON else f"unsupported({refused.value.reason})"


def request_through(plane: h.Plane, request: Any) -> Any:
    return h.run(
        h.door(plane).request(
            h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)
        )
    )


def complete_through(plane: h.Plane, request: Any, resolution: Any) -> Any:
    return h.run(
        h.door(plane).complete(
            h.resume_cap(), definition_version=plane.definition_version, request=request,
            resolution=resolution, erase=h.erase_cap(request),
        )
    )


def test_an_erasure_request_interrupted_at_its_first_suspension_write_is_finished_by_its_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    die_once_at(monkeypatch, plane, status="suspended")
    with pytest.raises(OSError, match="died at the suspended state write"):
        request_through(plane, request)
    stuck = state(plane, request)
    assert (stuck.status, stuck.current_state, stuck.trace) == ("running", composed.GATE, ())

    suspended = request_through(plane, request)

    assert isinstance(suspended, WorkflowSuspended), suspended
    assert suspended.gate == composed.GATE
    queued = [e for e in plane.transport.pending(tenant=h.TENANT) if e.event_key == suspended.event_key]
    assert len(queued) == 1, queued
    assert rows(plane, request, "workflow_started") == [None]
    assert rows(plane, request, "workflow_suspended") == [None]
    # The finished suspension is the real one: its approval completes the erasure.
    record = complete_through(plane, request, h.approve(plane, queued[0]))
    assert isinstance(record, h.erasure("ErasureRecord")), record
    assert outcome(plane) == "supported"


def test_an_erasure_completion_interrupted_at_its_terminal_write_is_finished_by_its_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    suspended = request_through(plane, request)
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    die_once_at(monkeypatch, plane, status="terminal")
    with pytest.raises(OSError, match="died at the terminal state write"):
        complete_through(plane, request, resolution)
    stuck = state(plane, request)
    assert (stuck.status, stuck.current_state) == ("running", "erased")
    # Withheld meanwhile: the write-ahead entries are in, the record is not.
    assert outcome(plane) == "unsupported(index-unsupported)"

    record = complete_through(plane, request, resolution)

    assert isinstance(record, h.erasure("ErasureRecord")), record
    final = state(plane, request)
    assert (final.status, final.current_state) == ("terminal", "erased")
    assert final.trace == stuck.trace
    entry = h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=plane.document.content_address)
    assert entry is not None and entry.erasure_record_address == content_hash(record)
    assert outcome(plane) == "supported"
    assert rows(plane, request, "workflow_resumed") == [h.APPROVER], "exactly one attributed passage row"
    assert rows(plane, request, "workflow_completed") == [None], "exactly one completion"
