"""A resumption that restores a missing approval request is first recorded as a refused resumption (D-IMPL-378, repair 1.4 (a)).

The hole (the "i" batch panel's seat G2, finding F-G2-2; the findings brief's
§1.4 on the ``dl-378-record`` branch at ``15e79163``). Dave's decision 8 (a), as
built by lane ``378i-d2ext``, made a resumption that finds no approval for a
suspension whose request never reached the queue restore that request
(``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._restore_request``)
and return BEFORE ``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._refuse``.
So the refused resumption's ``workflow_resumed`` row (``resolved=False``) was
never written. The audit log read the original suspension's
``workflow_suspended`` row and then a second ``workflow_suspended`` row, and
nothing in it said that a ``Resume`` holder had asked to pass the gate with no
approval. Measured at ``fe25536c`` with the panel's probe
(``records/2026-10-09-d-impl-378i-panel/fable-G2/probes/p_restore_audit_rows.py``):
rows 37 and 38 are both ``workflow_suspended``; at ``a539c215``, before the
restore existed, row 38 was ``workflow_resumed`` with ``resolved=False``.

Dave's ruling, 2026-10-09 10:54 MST (``D-IMPL-378``), verbatim: *"1.4 (a):
Preserve the refused-resumption audit row, then restore the missing approval
request idempotently."* Option (a) keeps the existing audit vocabulary; no new
audit action. The decision it repairs still binds (06:21): *"Recover the
suspended run by idempotently restoring its missing approval request. Preserve
the original authorization and suspension identity; never manufacture approval
or rerun an effect."*

Each test builds the stuck suspension for real, with lane ``378i-d2ext``'s own
fixtures (a suspension dies at its enqueue), and reads the audit log's events
for the execution's state key, oldest first:

* the first refused resumption appends the refusal row, exactly the row
  ``_refuse`` appends for any refused resumption, and THEN the restore's
  ``workflow_suspended`` row, and the request is pending once;
* a second refused resumption appends one refusal row and nothing else, and
  files no second request;
* the refusal row and the restore are separate writes: a restore that fails
  after the refusal row leaves that row and no request, and the next refused
  resumption is recorded as refused and restores;
* of two processes recovering one suspension at once, each resumption is
  recorded as refused, and one restore's row lands.

RED FIRST: the four tests above the residual section were committed before
the fix, when the restore returned before the refusal row. The residual
measurement after them was added with the fix; it passes before and after it,
and goes red if a later design marks the restore's row, when it must be
rewritten to assert that mark. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ccf.controlplane.audit import AuditEvent
from ccf.workflow.definitions import WORKFLOW_DEFINITION
from ccf_runtime.workflow.engine import (
    ExecutionFenced,
    WorkflowResumeRefused,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WorkflowStateRecord
from tests.workflow.test_approval_gate_limits import SharedBackingStore, StandInRecords
from tests.workflow.test_restore_missing_approval_request import (
    FIRST_GATE,
    NO_APPROVAL,
    DyingTransport,
    Run,
    compose,
    interrupt,
    requests,
    resume,
    start,
    state_of,
    the_request_a_suspension_files,
)
from tests.workflow.test_resume_single_flight import HOLD_SECONDS, Worker

#: A row read for its kind: (event type, action, resolved, actor).
Shape = tuple[str, str, bool, str | None]
#: The row ``WorkflowEngine._refuse`` appends for a refused resumption with no
#: recorded verdict behind the refusal: the log's plain event, no actor.
REFUSAL: Shape = ("AuditEvent", "workflow_resumed", False, None)
#: The row the restore's version-fenced re-write of the unchanged record appends.
RESTORE: Shape = ("AuditEvent", "workflow_suspended", True, None)


def rows_of(run: Run) -> list[AuditEvent]:
    """Every audit event this process's log holds for the execution, oldest first."""
    events = [event for event in run.registry.audit_log.events() if event.key == run.key]
    assert [event.sequence for event in events] == sorted(event.sequence for event in events)
    return events


def appended_since(run: Run, before: list[AuditEvent]) -> list[AuditEvent]:
    """The events appended for the execution after ``before`` was read."""
    seen = {event.sequence for event in before}
    return [event for event in rows_of(run) if event.sequence not in seen]


def shapes(events: list[AuditEvent]) -> list[Shape]:
    return [(type(event).__name__, event.action, event.resolved, event.actor) for event in events]


def comparable(event: AuditEvent) -> dict[str, object]:
    """Every field of a row but the two the log and the clock assign: its sequence and its time."""
    return {"type": type(event).__name__, **event.model_dump(mode="json", exclude={"sequence", "occurred_at"})}


def stuck_at_the_first_gate(run: Run) -> WorkflowStateRecord:
    """The start runs its first step and suspends on ``first-approval``, and its
    process dies at the enqueue: ``suspended``, with no request on the queue."""
    stuck, _ = interrupt(run, "enqueue", lambda: start(run))
    assert (stuck.status, stuck.current_state) == ("suspended", FIRST_GATE)
    assert requests(run, FIRST_GATE) == [], "the interrupted suspension filed no request"
    return stuck


def test_a_resumption_that_restores_a_missing_request_is_recorded_as_refused_before_the_restore(
    tmp_path: Path,
) -> None:
    """R1, the panel's probe as a test. One resumption, no approval, no request on
    the queue: the audit log gains the refusal row and then the restore's row, in
    that order, and the request is pending exactly once."""
    run = compose(tmp_path)
    stuck = stuck_at_the_first_gate(run)
    before = rows_of(run)

    outcome = resume(run)

    appended = appended_since(run, before)
    assert shapes(appended) == [REFUSAL, RESTORE], (
        f"rows the refused resumption appended: {shapes(appended)}"
        f" (outcome {type(outcome).__name__})"
    )
    refusal = appended[0]
    # The refusal row is the one any refused resumption appends: every field but
    # the two the log and the clock assign (its sequence and its time).
    assert type(refusal) is AuditEvent
    assert refusal.model_dump(mode="json", exclude={"sequence", "occurred_at"}) == {
        "action": "workflow_resumed",
        "key": run.key,
        "version": run.workflow.identity.definition_hash,
        "resolved": False,
        "actor": None,
        "artifact_class": WORKFLOW_DEFINITION.class_id,
    }
    # The restore, unchanged (decision 8 (a)): the one request the suspension
    # would have filed, pending once, and the suspension returned.
    assert requests(run, FIRST_GATE) == [the_request_a_suspension_files(run, stuck)]
    assert isinstance(outcome, WorkflowSuspended) and outcome.gate == FIRST_GATE, outcome
    assert state_of(run) == stuck


def test_a_second_refused_resumption_appends_one_refusal_row_and_files_no_second_request(
    tmp_path: Path,
) -> None:
    """R2. A second resumption, the request now pending and still no approval:
    one more refusal row and nothing else, and still one request. From the stuck
    suspension on, the log reads refusal, restore, refusal."""
    run = compose(tmp_path)
    stuck = stuck_at_the_first_gate(run)
    before = rows_of(run)
    first = resume(run)
    after_first = rows_of(run)

    second = resume(run)

    assert isinstance(second, WorkflowResumeRefused), second
    assert NO_APPROVAL in second.reason, second.reason
    assert shapes(appended_since(run, after_first)) == [REFUSAL]
    assert requests(run, FIRST_GATE) == [the_request_a_suspension_files(run, stuck)], (
        "one request after two refused resumptions"
    )
    assert shapes(appended_since(run, before)) == [REFUSAL, RESTORE, REFUSAL], (
        f"first resumption {type(first).__name__}"
    )
    assert state_of(run) == stuck


@pytest.mark.parametrize("death", ["trace-write", "enqueue"])
def test_a_restore_that_fails_after_the_refusal_row_leaves_that_row_and_the_next_refused_resumption_restores(
    tmp_path: Path, death: str
) -> None:
    """The refusal row and the restore are separate writes. The restore dies at
    the same seams a suspension dies at: the artifact store's trace write (before
    the restore's re-write) or the enqueue (after it). The refusal row stays, no
    request is filed, and the next refused resumption is recorded as refused and
    restores the one request."""
    run = compose(tmp_path)
    stuck = stuck_at_the_first_gate(run)
    before = rows_of(run)
    if death == "trace-write":
        run.store.refuse_next_trace_write()
    else:
        run.transport.die_at_next_enqueue()

    with pytest.raises(OSError):
        resume(run)

    failed = [REFUSAL] if death == "trace-write" else [REFUSAL, RESTORE]
    assert shapes(appended_since(run, before)) == failed
    assert requests(run, FIRST_GATE) == []
    after_failure = rows_of(run)

    outcome = resume(run)

    assert isinstance(outcome, WorkflowSuspended), outcome
    assert shapes(appended_since(run, after_failure)) == [REFUSAL, RESTORE]
    assert requests(run, FIRST_GATE) == [the_request_a_suspension_files(run, stuck)]
    assert state_of(run) == stuck


def test_two_processes_recovering_at_once_are_each_recorded_as_refused_and_one_restore_lands(
    tmp_path: Path,
) -> None:
    """Lane ``378i-d2ext``'s race, read in the audit logs. Two processes over one
    durable state store and one shared authority path resume the stuck suspension
    at once; A's restore is held inside its trace write while B's runs to its end.
    Each resumption is recorded as refused in its own process's log; B's restore
    row lands, and A's restore raises :class:`ExecutionFenced` having filed
    nothing."""
    records = StandInRecords()
    transport = DyingTransport()
    transport.scope = "shared"  # type: ignore[misc]
    a = compose(tmp_path / "a", store=SharedBackingStore(records), transport=transport)
    b = compose(tmp_path / "b", store=SharedBackingStore(records), transport=transport)
    stuck = stuck_at_the_first_gate(a)
    a_before, b_before = rows_of(a), rows_of(b)

    a.store.hold_next_trace_write()
    first = Worker(lambda: resume(a)).start()
    try:
        if not a.store.held.wait(HOLD_SECONDS):
            pytest.fail(f"process A's resumption never reached its restore's trace write: {first.join()!r}")
        second = resume(b)
    finally:
        a.store.release.set()

    assert isinstance(second, WorkflowSuspended), second
    with pytest.raises(ExecutionFenced):
        first.join()
    assert shapes(appended_since(a, a_before)) == [REFUSAL], "A: refused, then fenced"
    assert shapes(appended_since(b, b_before)) == [REFUSAL, RESTORE], "B: refused, then restored"
    assert requests(a, FIRST_GATE) == [the_request_a_suspension_files(a, stuck)]


# --- residuals, measured ----------------------------------------------------------
#
# What the restore's row says to an auditor. The engine's own vocabulary has no
# action for a restore (Dave's option (a): no new audit action), so the restore's
# re-write is audited as the suspension write it is.


def test_the_restores_row_is_the_suspensions_own_row_but_for_its_sequence_and_time(
    tmp_path: Path,
) -> None:
    """RESIDUAL. The restore still appends a ``workflow_suspended`` row, and that
    row is the original suspension's row in every field but its sequence and its
    time: nothing in it marks a restore. Read alone, it reads as a second
    suspension at the same gate. (That it follows the refusal row is the first
    test's assertion.)"""
    run = compose(tmp_path)
    stuck_at_the_first_gate(run)
    (original,) = [event for event in rows_of(run) if event.action == "workflow_suspended"]

    resume(run)

    events = rows_of(run)
    suspensions = [event for event in events if event.action == "workflow_suspended"]
    assert len(suspensions) == 2 and suspensions[0] == original, shapes(events)
    restored = suspensions[1]
    assert type(restored) is type(original) is AuditEvent
    assert comparable(restored) == comparable(original)
    assert restored.sequence > original.sequence
