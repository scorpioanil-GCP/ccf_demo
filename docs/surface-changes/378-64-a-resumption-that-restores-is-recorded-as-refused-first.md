# 378-64 — a resumption that restores a missing approval request is recorded as refused first

Dave's ruling of 2026-10-09 at 10:54 MST (`D-IMPL-378`, repair 1.4 (a)), verbatim: *"Preserve the refused-resumption
audit row, then restore the missing approval request idempotently."* Option (a) of the findings brief's §1.4 keeps the
existing audit vocabulary: no new audit action. It repairs decision 8 (a) as built (fragment `378-51`). No SEC row
changes here.

What was measured before this change, by the "i" batch panel's seat G2 (finding F-G2-2) and again as red tests
committed first. A resumption that found no approval for a suspension whose request never reached the queue restored
the request and returned before its refusal row was appended. The audit log read the suspension's `workflow_suspended`
row and then a second `workflow_suspended` row, and nothing in it said that a resumption had been refused. Before the
restore existed (`a539c215`), the same resumption appended `workflow_resumed` with `resolved=False`.

What holds now is in `tests/workflow/test_restore_keeps_the_refused_resumption_row.py`. The first refused resumption's
row is byte-identical, sequence and time included, to the row `a539c215` appended at the same point (measured with the
lane's probe over the same fixtures).

**What this does NOT do.**
- **It does not mark the restore.** The restore's re-write of the unchanged record still appends a `workflow_suspended`
  row, and that row is the suspension's own row in every field but its sequence and time. Read alone, it reads as a
  second suspension at the same gate (measured,
  `tests/workflow/test_restore_keeps_the_refused_resumption_row.py::test_the_restores_row_is_the_suspensions_own_row_but_for_its_sequence_and_time`).
- **It does not change the starter's retried start.** The ruling names the refused resumption. The starter's retry
  that restores the request appends the restore's row alone, as Dave's D2 finish of an interrupted start does (measured,
  `tests/workflow/test_restore_keeps_the_refused_resumption_row.py::test_the_starters_retried_start_that_restores_appends_the_restores_row_alone`).
- **It does not make the refusal row and the restore one write.** A restore that fails after the row (at its trace write,
  or at its enqueue after its re-write landed) leaves the row and no request, and the next resumption that finds no
  approval is recorded as refused and restores (measured).
- **It does not change what `resume` returns.** A resumption that restores still returns the suspension as
  `WorkflowSuspended`, and one that finds the request pending still returns the refusal.

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: `resume`, finding no approval for a suspension whose request never reached the queue, restored the request and returned the suspension without appending its refusal row. The audit log read the suspension's `workflow_suspended` row and then a second one, and recorded no refused resumption
- After: `resume` appends its refusal row first (`workflow_resumed`, `resolved=False`, no actor, the row any refused resumption appends), then restores the request as before and returns the suspension. A restore that fails after the row leaves the row and no request. A second refused resumption appends one more refusal row and files no second request. Of two processes resuming at once, each resumption is recorded as refused in its own log, and the one whose restore loses raises `ExecutionFenced` having filed nothing. The docstring of `resume` says so
- Why: `D-IMPL-378`, Dave's repair 1.4 (a) of 2026-10-09. Red tests: `tests/workflow/test_restore_keeps_the_refused_resumption_row.py::test_a_resumption_that_restores_a_missing_request_is_recorded_as_refused_before_the_restore`, `::test_a_second_refused_resumption_appends_one_refusal_row_and_files_no_second_request`, `::test_a_restore_that_fails_after_the_refusal_row_leaves_that_row_and_the_next_refused_resumption_restores`, `::test_two_processes_recovering_at_once_are_each_recorded_as_refused_and_one_restore_lands`
- Migration: none in code. An operator reading the audit log for a suspension restored by a resumption finds, after the suspension's own `workflow_suspended` row, the refused resumption's `workflow_resumed` row (`resolved=False`, no actor) and then the restore's `workflow_suspended` row, which is the suspension's own row but for its sequence and time. A suspension restored by the starter's retried start shows the restore's row alone
