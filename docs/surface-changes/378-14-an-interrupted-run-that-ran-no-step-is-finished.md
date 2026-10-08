# 378-14 — an interrupted run that ran no step is finished, never re-run

Dave's ruling on 2026-10-07 (`D-IMPL-378`, his D2 = (a)), on the question as it was put
to him: *"Let the engine finish a stuck run whose current state is a gate or the end
state. No step ran there, so it provably can't duplicate an effect, which meets your
Q4 condition."* His Q4 condition still governs everything else: *"Retry must use a
durable claim identifying the original passage and prevent duplicate effects; 'same
engine' alone is insufficient. If that cannot be proved, use (b)"* — never retry an
interrupted passage.

What was measured before this change, each as a red test committed first:

- **A gate routed straight to a terminal state.** A passage that committed and whose
  terminal write then failed stayed `running` at the terminal state, and every later
  resumption was refused as interrupted.
- **An execution whose first node is a gate.** A start that committed and whose first
  suspension write failed stayed `running` at the gate. The starter's retry was refused
  as a second start, and a resumption was refused as interrupted.
- **The erasure door.** An erasure request interrupted that way was refused on retry
  `workflow-not-suspended`. An erasure completion interrupted at its terminal write was
  refused on retry `approval-not-recorded`, which misnames the cause, and its address
  stayed withheld (`index-unsupported`) with no erasure record filed.

What holds now is in `tests/workflow/test_finish_interrupted_passage.py` and
`tests/erasure/test_interrupted_erasure_passage.py`.

**What this does NOT do.**
- **A `running` record at a step stays `running` for good.** The step may have run, so
  the ruling's (b) applies unchanged; an operator reconciles it outside the fabric.
- **A finisher racing the original passage still costs the loser an exception.** One
  fenced write lands and the other raises `ExecutionFenced`. How the workflow doors
  render that is lane 378c-d3's change, not this one.
- **A passage whose durable claim is missing is not finished.** That happens when the
  engine reaches an authority path holding no closure for it, or when a writer outside
  the engine changed the record's state. It is refused, typed, and an operator
  reconciles it.

## ccf_runtime.workflow.state.suspension_left_by

- Surface: ccf_runtime.workflow.state.suspension_left_by
- Public surface: true
- Change type: added
- Before: absent
- After: `suspension_left_by(record) -> WorkflowStateRecord | None` rebuilds, exactly, the suspension a `running` record's passage past a gate left: the gate as its state, `suspended` as its status, the trace without its last `resume` entry, every other field unchanged. Its content hash is the one the gate's closure and every verdict on that suspension name. It returns `None` when the record is not `running`, or when its last trace entry is not a `resume` into its current state
- Why: `D-IMPL-378`, Dave's D2 ruling. It is how a finisher, or the erasure door, finds the durable claim that identifies an interrupted passage, without asking which engine wrote the record
- Migration: none

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: `resume` refused every `running` record: "An interrupted passage is never retried". `execute` refused every existing execution id as a second start
- After: `resume` FINISHES a `running` record whose state is a `hitl-gate` or a terminal state. It makes the version-fenced suspension or completion write and, at a gate, its one queue event; it invokes no step callable and adds no attributed row. It finishes only when the passage's durable claim names it. For a passage past a gate, the claim is the gate's closure, found by the suspension the passage left, and its decided verdict must route to the record's state. For an execution's start, the claim is the create-if-absent record. When no step can have run but no claim names the passage, `resume` refuses: "no durable claim on the HITL authority path names it". A `running` record at a step is still refused as interrupted. `execute` finishes a start for its own starter when the start node is a `hitl-gate` and the record is still `running` there with an empty trace; any other existing id is still refused "already exists". A finisher that loses the fenced write to the original passage, or the original that loses it to a finisher, raises `ExecutionFenced` and writes nothing
- Why: `D-IMPL-378`, Dave's D2 ruling under his Q4 condition. Red tests: `tests/workflow/test_finish_interrupted_passage.py::test_a_gate_routed_straight_to_a_terminal_is_finished_by_another_process_not_rerun`, `::test_an_execution_whose_first_node_is_a_gate_is_finished_not_restarted`, `::test_a_finisher_racing_the_live_original_passage_writes_once_and_the_loser_is_fenced`, `::test_a_passage_no_durable_claim_names_is_never_finished`
- Migration: a caller that treated the never-retried refusal of a `running` record at a gate or a terminal state as final may now present the resumption again and receive the finished outcome. A `running` record at a step is unchanged

## ccf_runtime.erasure.door.ErasureDoor

- Surface: ccf_runtime.erasure.door.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: `complete` refused an execution in `running` with `approval-not-recorded`, a name for a cause that was not the cause, so a completion interrupted after its passage committed could never complete. `request` passed on the engine's "already exists" refusal of a start interrupted before it suspended, as `workflow-not-suspended`
- After: `complete` holds the recorded approval to the suspension the running passage left, rebuilt by `suspension_left_by`, and resumes the engine, which finishes the passage when no step can have run (`erased` follows the gate directly) and otherwise refuses it, as `workflow-refused`. The record it files is the one the interrupted attempt's write-ahead entries name. `request` receives the finished suspension from the engine when the same requester retries
- Why: `D-IMPL-378`, Dave's D2 ruling. Red tests: `tests/erasure/test_interrupted_erasure_passage.py::test_an_erasure_request_interrupted_at_its_first_suspension_write_is_finished_by_its_retry`, `::test_an_erasure_completion_interrupted_at_its_terminal_write_is_finished_by_its_retry`
- Migration: none; SEC-009's door contract is otherwise unchanged
