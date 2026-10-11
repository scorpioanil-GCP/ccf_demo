# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""An erasure request whose approval request never reached the queue gets it back from its retry (D-IMPL-378, decision 8 (a)).

The erasure workflow's first node is its approval gate, so a request suspends
there at once. When the door's process dies, or its artifact store fails, after
the engine's suspension write and before its enqueue, the run is ``suspended``
with no approval request on the HITL transport. Measured at ``a539c215`` by the
final panel's seat F2 (finding F2-01): the request's retry was refused
``workflow-not-suspended`` and no approver could act on it, so the request id
was stuck for good.

Dave's decision 8 (a), 2026-10-09: *"Recover the suspended run by idempotently
restoring its missing approval request. Preserve the original authorization and
suspension identity; never manufacture approval or rerun an effect."* Each test
below dies once at the named seam, never on an engine method, and then presents
the SAME request through the shipped
:class:`~ccf_runtime.erasure.door.ErasureDoor` again, as a restarted door would:
the retry returns the suspension with exactly one approval request, bound to the
unchanged suspension, and that request's signed approval completes the erasure
once, filing the record its index entries name.

RED FIRST: committed before the recovery existed. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import DerivedWrite
from ccf.contracts.canonical import content_hash
from ccf_runtime.workflow.engine import WORKFLOW_TRACE_ARTIFACT_CLASS, WorkflowSuspended
from tests.erasure import composed
from tests.erasure import harness as h
from tests.erasure.test_interrupted_erasure_passage import (
    complete_through,
    outcome,
    request_through,
    rows,
    state,
)


def die_once_before_the_enqueue(monkeypatch: pytest.MonkeyPatch, plane: h.Plane, *, death: str) -> None:
    """The door's next suspension dies after its state write: at the artifact
    store's write of the trace (an outage), or at the transport's enqueue (the
    process dies). Either raises once, filing nothing."""
    if death == "enqueue":
        real_enqueue = plane.transport.enqueue

        def dying(**kwargs: Any) -> None:
            monkeypatch.setattr(plane.transport, "enqueue", real_enqueue)
            raise OSError("the door's process died before its enqueue")

        monkeypatch.setattr(plane.transport, "enqueue", dying)
        return
    real_put = plane.store.put

    def refusing(authorized: Any, artifact: object) -> Any:
        if isinstance(artifact, DerivedWrite) and artifact.artifact_class == WORKFLOW_TRACE_ARTIFACT_CLASS:
            monkeypatch.setattr(plane.store, "put", real_put)
            raise OSError("the artifact store refused the trace write")
        return real_put(authorized, artifact)

    monkeypatch.setattr(plane.store, "put", refusing)


@pytest.mark.parametrize("death", ["trace-write", "enqueue"])
def test_an_erasure_request_whose_approval_request_never_reached_the_queue_is_restored_by_its_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, death: str
) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    die_once_before_the_enqueue(monkeypatch, plane, death=death)
    with pytest.raises(OSError):
        request_through(plane, request)
    stuck = state(plane, request)
    assert (stuck.status, stuck.current_state) == ("suspended", composed.GATE)
    assert list(plane.transport.pending(tenant=h.TENANT)) == [], "no approval request was filed"

    suspended = request_through(plane, request)

    assert isinstance(suspended, WorkflowSuspended), suspended
    assert suspended.gate == composed.GATE
    queued = [e for e in plane.transport.pending(tenant=h.TENANT) if e.event_key == suspended.event_key]
    assert len(queued) == 1, queued
    assert queued[0].product_content_hash == content_hash(stuck), "bound to the unchanged suspension"
    assert queued[0].requested_by == h.REQUESTER
    assert state(plane, request) == stuck
    # The restored request is a real one: its signed approval completes the erasure, once.
    record = complete_through(plane, request, h.approve(plane, queued[0]))
    assert isinstance(record, h.erasure("ErasureRecord")), record
    assert outcome(plane) == "supported"
    assert rows(plane, request, "workflow_resumed") == [h.APPROVER], "exactly one attributed passage row"
    assert rows(plane, request, "workflow_completed") == [None], "exactly one completion"
