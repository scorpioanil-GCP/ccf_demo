# 378-51 — a run left suspended with no approval request gets that request back

Dave's decision 8 of 2026-10-09 (`D-IMPL-378`; 06:06, confirmed at 06:21 as "8a"): *"(a). Recover
the suspended run by idempotently restoring its missing approval request. Preserve the original
authorization and suspension identity; never manufacture approval or rerun an effect."* Option (a)
extends his D2 ruling (fragment `378-14`), so the recovery runs on D2's own triggers: the starter's
retried start and a resumption.

What was measured before this change, by the final panel and again as red tests committed first. A
suspension writes its `suspended` record, then its trace artifact, then its one approval request. A
process that died, or an artifact store that failed, after the record write left the execution
`suspended` at its gate with no request. The starter's retried start was refused "already exists", a
resumption was refused for want of an approval, an approval recorded meanwhile was recorded
`event_state_at_submit="missing"` and never counted, and the erasure door's retried request was
refused `workflow-not-suspended`. Nothing in the SDK could move the execution again.

What holds now is in `tests/workflow/test_restore_missing_approval_request.py` and
`tests/erasure/test_erasure_request_restored.py`.

**What this does NOT do.**
- **It does not file at most one request in every overlap.** When the suspension's own passage, or
  another recovery, has written the record and not yet queued the request, a recovery in that window
  files a second identical request. The gate still opens once on one approval, and its closure retires
  both (measured). Filing at most one would take an enqueue that is atomic with its own absence check,
  which is a change to `HITLTransportProtocol`.
- **It does not see a gate primitive's claim.** A request that the approval gate has claimed and not
  yet answered is filed again. The enqueue discards the claim, so that verdict is recorded against the
  restored request without the primitive's stamp, and it still opens the gate once (measured).
- **It does not know which transport the suspension used.** It files the request on the recovering
  engine's own HITL transport. With two transports over one Control Plane state store, a request
  pending on one is filed again on the other (measured). Run one HITL transport per state store.
- **It does not reopen a gate.** A suspension whose request is pending, was answered, or whose gate
  was closed is never filed again.

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: an execution left `suspended` with no pending approval request could never move. `execute` refused the starter's retry "already exists", `resume` refused with "no approval for this suspension has returned through the HITL authority path", and a verdict recorded meanwhile was recorded `missing` and never counted
- After: `execute`, for the execution's own starter under the definition it was started with, and `resume`, when it finds no approval, restore that one request when the HITL transport holds no pending request, no closure and no verdict for the suspension other than ones recorded while no request was pending. The restore re-files the trace artifact from the record's own trace, at the same content address; re-writes the record unchanged, conditionally on the version read, which adds one `workflow_suspended` row, and of two recoveries that read the same version one write lands and the other raises `ExecutionFenced`; enqueues the request the suspension would have filed (the same event key and class, the record's own content hash, the gate's pinned approval policy, the starter as requester); and returns the suspension as `WorkflowSuspended`. No step runs, no verdict is recorded and no gate is closed, and a verdict recorded while the request was missing is never authority. With the request pending, a later `execute` or `resume` is refused as before. The erasure door's retried request reaches this path
- Why: `D-IMPL-378`, Dave's decision 8 (a). Red tests: `tests/workflow/test_restore_missing_approval_request.py::test_a_suspension_whose_request_never_reached_the_queue_gets_exactly_that_request_back`, `::test_a_suspension_a_passage_left_without_its_request_gets_it_back_from_the_resumers_retry`, `::test_two_processes_recovering_one_suspension_at_once_file_one_request`, `tests/erasure/test_erasure_request_restored.py::test_an_erasure_request_whose_approval_request_never_reached_the_queue_is_restored_by_its_retry`
- Migration: a caller that treated "already exists", or the no-approval refusal, of such an execution as final may present it again and receive the suspension. An operator reading the audit log finds a second `workflow_suspended` row for a restored suspension, with the record and its trace unchanged
