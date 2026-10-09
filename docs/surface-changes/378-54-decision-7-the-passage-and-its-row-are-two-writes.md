# 378-54 — decision 7: the passage commit and its audit row are two writes, not one, and what the window between them leaves is disclosed

`D-IMPL-378`, lane `378i-docs`, decision 7 of the final panel (G-ONEWRITE). Dave ruled on 2026-10-09 at 06:06 MST and
confirmed at 06:21 (recorded on `main` at `d429dcfa`), verbatim: *"(b), with the documentation correction now. Make a
committed transition without its audit row detectable and recoverable. Do not claim atomicity that does not exist."*
This entry is the documentation correction. The design half, making such a transition detectable and recoverable, is
not built here. No SEC row changes here.

**What was claimed, and what was measured.** The security page's §4.13, a row of the controls register and the
docstring of `WorkflowEngine.resume` said the passage (the execution leaving its gate) and its attributed
`workflow_resumed` row are one write. `ccf.controlplane.state.AuditedStateWriter.write_if` makes them two: the state
store's conditional write, then the audit log's append. When the append ran, the record had already moved, and after
the append failed the record stays moved with no event
(`tests/controlplane/test_audited_write_is_two_writes.py::test_limit_an_append_that_fails_after_the_conditional_write_leaves_the_record_moved_with_no_event`).
Through the engine, a `workflow_resumed` append that fails after the passage commit leaves the record `running` one
version on, past its gate, with no attributed row; the gate's closure on the HITL transport still names the approver
and the queue no longer offers the gate. When the state after the gate is a step, the step has not run and every later
resumption is refused as an interrupted passage
(`tests/workflow/test_passage_commit_two_writes_limits.py::test_limit_a_failed_row_append_leaves_the_execution_past_its_gate_with_no_resumed_row`).
When it is a terminal state, a later resumption completes the execution, and the completed record still has no
`workflow_resumed` row
(`tests/workflow/test_passage_commit_two_writes_limits.py::test_limit_a_terminal_reached_through_the_window_completes_later_with_no_resumed_row`).
Each of these asserts the window as it stands, so the design that closes it turns them red.

Documentation only, no behavior change. The manifest `make surface` writes is unchanged, because it records signatures
rather than docstring text, and no signature changed. The correction of the published pages is held by
`tests/workflow/test_passage_commit_two_writes_limits.py::test_the_published_pages_no_longer_claim_the_passage_and_its_row_are_one_write`,
which failed before it.

## ccf.controlplane.state.AuditedStateWriter

- Surface: ccf.controlplane.state.AuditedStateWriter
- Public surface: true
- Change type: behavior
- Before: the docstring of `write_if` said the store's conditional write comes first and the event after it, so a refused write appends nothing; it did not say what an append that fails after the write landed leaves.
- After: documentation only; the behavior is unchanged. The docstring of `write_if` adds that these are two writes, not one atomic step: an append that fails after `put_if` landed leaves the record moved with no event for the transition, and the append's error propagates to the caller. Making such a transition detectable and recoverable is being designed (`D-IMPL-378`, decision 7 (b)), not built.
- Why: Dave's ruling on decision 7 (`D-IMPL-378`, 2026-10-09): "Do not claim atomicity that does not exist."
- Migration: none in code. A reader who takes the audit log as the complete history of Control Plane state writes allows for a write whose event append failed, which has no event.

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: the docstring of `resume` said the passage is committed "together with its attributed `workflow_resumed` row, in ONE audited write".
- After: documentation only; the behavior is unchanged. The docstring of `resume` says the passage is committed conditionally before the step after the gate runs and its row is appended after the commit lands: two writes, not one. An append that fails after the commit leaves the execution past its gate with no `workflow_resumed` row, and the security page's §4.13 states what an operator then finds. Detecting and recovering such a passage is being designed (`D-IMPL-378`, decision 7 (b)), not built.
- Why: Dave's ruling on decision 7 (`D-IMPL-378`, 2026-10-09): "Do not claim atomicity that does not exist."
- Migration: none in code. An operator who reconciles executions against the audit log reads a `running` execution past its gate with no `workflow_resumed` row as a passage whose row append failed; the approver is named by the gate's closure on the HITL transport (`decided_by`).
