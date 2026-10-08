# 378-09 — one approval, one passage: the gate's closure and the conditional state write

Dave's ruling on 2026-10-07 (`D-IMPL-378`, his Q4), verbatim: *"(a), conditional.
Approve the atomic gate close and conditional state write. Unsupported third-party
implementations must fail at construction. Retry must use a durable claim identifying
the original passage and prevent duplicate effects; 'same engine' alone is
insufficient. If that cannot be proved, use (b) [never retry an interrupted passage]
for interrupted passages."*

What was measured before this change, each as a red test committed first
(`lane-378-approval`, `52f78691` to `ca0330e1`):

- **One approval, two passages.** Two resumptions through two state-store objects
  over one durable store, or through two processes' doors, both passed the gate. The
  step after the gate ran twice, and two attributed rows named the one approver.
- **The outvoted rejection.** A rejection recorded inside a resumption's
  read-decide-commit window was never judged, and the execution left the gate on the
  approving route with both verdicts standing. This was measured three ways: right
  after the resumption read the verdicts; during its terminal commit; and through the
  served action door while the step after the gate ran.
- **The verdict after the passage.** A passed gate's event stayed pending, so a later
  rejection was recorded as a verdict on an open gate.
- **One execution id started twice.**
- **An attributed row for a passage that never committed.**

What holds now is in `tests/workflow/test_approval_gate_limits.py` and
`tests/http_api/test_approval_gate_limits_door.py`. Every test there asserts the
limit's end state and then the refusing mechanism by name.

**What this does NOT do.**
- **A conflicted gate still stays suspended for good** (`D-GATE-357` (2)). There is
  still no primitive that reopens it.
- **An interrupted passage stays `running` for good** (the ruling's (b)). There is no
  primitive that reconciles it; an operator does that outside the fabric.
- **The transport's stamp race is unchanged** (residual (1) of
  `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._gate_authority`).
- **A gate passed before this change keeps its pending event.** Only a closure
  retires an event, and no closure exists for those gates.
- **The guarantees are the store's and the transport's.** The engine refuses an
  implementation without the members, but it cannot see whether a third-party
  implementation keeps the atomicity it declares.
  `tests/conformance/test_gate_closure_and_conditional_write.py` is the suite such an
  implementation must pass.

## ccf.controlplane.state.ConditionalStateStore

- Surface: ccf.controlplane.state.ConditionalStateStore
- Public surface: true
- Change type: added
- Before: absent — `ControlPlaneStateStore.put` replaced a record unconditionally, so two writers that read one record could both commit over it
- After: a runtime-checkable Protocol extending `ControlPlaneStateStore` with `scope` (`"process"` or `"shared"`), `get_versioned(record_class, key) -> (record | None, version)` and `put_if(authorized, record_class, record, *, record_id, token, expected_version) -> new version`. Every write of a key, conditional or not, increments the key's version; version `0` means absent; `put_if` runs `put`'s proofs and writes only if the key is still at `expected_version`, atomically against every other writer of the same durable store, else raises `StateConflict` and writes nothing
- Why: Dave's ruling of 2026-10-07 approved the conditional state write (`D-IMPL-378`). Red tests: `tests/workflow/test_approval_gate_limits.py::test_two_state_store_objects_over_one_durable_store_spend_one_approval_once`, `::test_two_concurrent_starts_of_one_execution_id_run_the_start_node_once`; conformance: `tests/conformance/test_gate_closure_and_conditional_write.py`
- Migration: a deployment-supplied state store implements `get_versioned`, `put_if` and `scope` — an optimistic version column, or a row lock in one transaction — and runs `tests/conformance/test_gate_closure_and_conditional_write.py` against itself; the workflow engine refuses at construction a store that does not (see `WorkflowEngine` below)

## ccf.controlplane.state.StateConflict

- Surface: ccf.controlplane.state.StateConflict
- Public surface: true
- Change type: added
- Before: absent
- After: a `RuntimeError` raised by `put_if` when the key's version is not the one its writer read; nothing was written. Placed in `ccf.products.refusal.NON_VALUE_VIOLATIONS`: an exception the store raises, never a determination a consumer receives
- Why: `D-IMPL-378`; the workflow engine turns it into its own typed resumption refusal
- Migration: none for callers of the SDK's doors; a deployment's own store raises it from `put_if`

## ccf.controlplane.state.InMemoryStateStore

- Surface: ccf.controlplane.state.InMemoryStateStore
- Public surface: true
- Change type: behavior
- Before: a dict of records; `put` replaced a record unconditionally
- After: a `ConditionalStateStore` of scope `"process"`: every write increments the key's version under one lock, `put_if` compares and writes inside that lock, and `get_versioned` reads the version before the record, so a torn read can only make a later `put_if` conflict
- Why: `D-IMPL-378`, the reference implementation of the conditional write
- Migration: none; `put`, `get` and `items` answer as before

## ccf.controlplane.state.AuditedStateWriter

- Surface: ccf.controlplane.state.AuditedStateWriter
- Public surface: true
- Change type: behavior
- Before: `write` only
- After: also `write_if(authorized, record_class, record, *, record_id, event, expected_version) -> (event, version)`: the store's `put_if` first, then the event, so a refused write appends nothing; a store that is not a `ConditionalStateStore` raises `TypeError`
- Why: `D-IMPL-378`; the workflow engine's passage commit and its attributed audit row are one write
- Migration: none

## ccf.controlplane.audit.AuditAction

- Surface: ccf.controlplane.audit.AuditAction
- Public surface: true
- Change type: behavior
- Before: no action recorded an execution's start
- After: `"workflow_started"` joins the vocabulary: the workflow engine records an execution as started, with a create-if-absent write, before its first node runs
- Why: `D-IMPL-378`; an execution id is started once (D-23), measured by `tests/workflow/test_approval_gate_limits.py::test_two_concurrent_starts_of_one_execution_id_run_the_start_node_once`
- Migration: a consumer that enumerates audit actions adds `workflow_started`

## ccf.hitl.transport.GateClosure

- Surface: ccf.hitl.transport.GateClosure
- Public surface: true
- Change type: added
- Before: absent
- After: a `CCFContract` naming one suspension's decided gate — `tenant`, `event_key`, `product_content_hash`, `passage` (the suspension, the authority submission and the verdict, never the engine), `decided_action`, `decided_by`, `observed_submissions`, `authorizing_decision_id` — written by `close_gate`; it is also the durable claim a retried passage presents
- Why: `D-IMPL-378`, the atomic gate close
- Migration: none

## ccf.hitl.transport.GateAlreadyClosed

- Surface: ccf.hitl.transport.GateAlreadyClosed
- Public surface: true
- Change type: added
- Before: absent
- After: a `PermissionError` `close_gate` raises when another passage already closed the suspension's gate; nothing changed
- Why: `D-IMPL-378`; conformance: `tests/conformance/test_gate_closure_and_conditional_write.py::test_racing_closures_by_different_passages_admit_exactly_one`
- Migration: none

## ccf.hitl.transport.GateVerdictsChanged

- Surface: ccf.hitl.transport.GateVerdictsChanged
- Public surface: true
- Change type: added
- Before: absent
- After: a `PermissionError` `close_gate` raises when the number of submissions recorded on the suspension is not the number the caller judged; nothing changed and the gate stays open
- Why: `D-IMPL-378`; red test `tests/workflow/test_approval_gate_limits.py::test_a_rejection_recorded_right_after_the_resumptions_verdict_read_is_not_outvoted`
- Migration: none

## ccf.hitl.transport.HitlGateClosed

- Surface: ccf.hitl.transport.HitlGateClosed
- Public surface: true
- Change type: added
- Before: absent — a verdict on a suspension whose gate had been passed was recorded, as `pending` on the submit-only door path
- After: a `PermissionError` `submit` raises, before any nonce is consumed or anything recorded, when the suspension the verdict names was already decided; the HTTP and MCP doors answer it with `hitl-gate-closed` (HTTP 409)
- Why: `D-IMPL-378`. Red tests: `tests/workflow/test_approval_gate_limits.py::test_a_rejection_recorded_during_the_resumptions_commit_is_not_outvoted` and `::test_a_verdict_recorded_after_the_passage_is_not_taken_as_a_verdict_on_an_open_gate`; `tests/http_api/test_approval_gate_limits_door.py::test_a_rejection_posted_while_the_step_after_the_gate_runs_is_not_outvoted`, `::test_a_rejection_posted_during_the_terminal_commit_is_not_outvoted_at_the_door` and `::test_a_passed_gate_is_neither_offered_nor_accepted_as_pending_at_the_doors`; the MCP door: `tests/mcp/test_hitl_gate_closed_mcp.py::test_a_verdict_on_a_decided_gate_is_refused_at_the_mcp_door`
- Migration: a client that presents a verdict after the gate was passed now receives a refusal instead of a receipt; the verdict did not count before either

## ccf.hitl.transport.HITLTransportProtocol

- Surface: ccf.hitl.transport.HITLTransportProtocol
- Public surface: true
- Change type: behavior
- Before: no member decided a gate; a verdict on a passed gate was recorded
- After: three members join: `scope` (`"process"` or `"shared"`); `close_gate(authorized: Authorized[Resume], *, event_key, product_content_hash, passage, decided_action, decided_by, observed_submissions) -> GateClosure`, one atomic step with `submit` and `remove` that returns an existing closure of the same passage, refuses another passage's (`GateAlreadyClosed`) and a changed count (`GateVerdictsChanged`), and otherwise records the closure, removes the suspension's event from `pending` and discards a claim on it; and `closures(*, tenant)`. `submit` refuses a verdict on a decided suspension (`HitlGateClosed`). A conforming implementation keeps closures exactly as durable as its submissions
- Why: Dave's ruling of 2026-10-07 approved the atomic gate close (`D-IMPL-378`)
- Migration: a deployment-supplied transport implements the three members and the refusal in `submit`, atomically with its recording, and runs `tests/conformance/test_gate_closure_and_conditional_write.py`; the workflow engine refuses at construction a transport that does not offer the whole Protocol

## ccf.hitl.transport.InMemoryHitlTransport

- Surface: ccf.hitl.transport.InMemoryHitlTransport
- Public surface: true
- Change type: behavior
- Before: a verdict on a passed gate's suspension was recorded; a passed gate's event stayed in `pending` on the submit-only door path
- After: scope `"process"`; `close_gate` and `closures` under the transport's one lock; `submit` refuses a decided suspension's verdict inside the step that records, before the revalidation and the nonce
- Why: `D-IMPL-378`, the reference implementation of the gate close
- Migration: none

## ccf_runtime.workflow.engine.ExecutionFenced

- Surface: ccf_runtime.workflow.engine.ExecutionFenced
- Public surface: true
- Change type: added
- Before: absent
- After: a `RuntimeError` a passage's later write raises when a writer other than that passage moved the execution's record while the passage ran; nothing was written
- Why: `D-IMPL-378`; every write after a passage commit is conditional on the version that passage wrote
- Migration: none on a conforming store: the engine's own refusals leave no second writer

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: construction accepted any state store and transport. `execute` checked for a record and then ran nodes, and wrote at the first suspension. `resume` took the in-process claim, read the record and the verdicts (twice), and appended its attributed `workflow_resumed` row. Only then did it run the step after the gate and write at the next suspension or terminal. A retry after a failed write ran the step after the gate again
- After: construction refuses, typed (`WorkflowWiringError`) and by name: a state store that is not a `ConditionalStateStore` declaring scope `"process"` or `"shared"`; a transport that does not offer the whole `HITLTransportProtocol` with such a scope; and a `"shared"` store paired with a transport that is not `"shared"`. `execute` writes a `running` record at the start node with a create-if-absent write (`workflow_started`) before any node runs; a second start of the id is refused "already exists" (409 at the door). `resume` keeps the in-process claim and reads the verdicts once. After every check it closes the gate on the verdicts it judged: refused if a verdict arrived since its read, or if another passage holds the closure. It then commits the passage — the record `running` at the decision, and the attributed `workflow_resumed` row, in one write conditional on the version it read — BEFORE the step after the gate runs; a lost commit is refused. A resumption that finds a `running` record is refused: "An interrupted passage is never retried". A passage whose commit never landed is still `suspended`: presenting the resumption again re-takes the same closure, and the step runs once. A later write of a passage is fenced by version (`ExecutionFenced`)
- Why: `D-IMPL-378` (Dave, 2026-10-07). Red tests: `tests/workflow/test_approval_gate_limits.py` and `tests/http_api/test_approval_gate_limits_door.py`. The two halves of the retry ruling: `tests/workflow/test_approval_gate_limits.py::test_a_passage_whose_commit_never_landed_is_retried_once_on_its_own_closure` and `::test_an_interrupted_passage_is_never_retried_by_any_process`. Construction: `tests/workflow/test_engine_refuses_unsupported_seams.py`. The two single-flight tests the ruling changed: `tests/workflow/test_resume_single_flight.py::test_a_resume_that_raises_gives_the_claim_back` (the retry now runs the step once) and `::test_a_cancelled_resume_gives_the_claim_back` (the later resume is now refused as an interrupted passage)
- Migration: a deployment over its own state store or transport implements the new members (above) or is refused at construction. A deployment where several processes resume no longer needs its own per-execution lock in front of the door; it needs a `"shared"` store and a `"shared"` transport. `GET /workflow/execution` can now answer `status: "running"` — between a passage's commit and its next suspension or terminal, and for good after an interrupted passage, which an operator reconciles outside the fabric (the gate's closure, `HITLTransportProtocol.closures`, names the passage). A retry after a failed resumption runs the step after the gate again only if its commit never landed; one interrupted after its commit is refused. Audit readers see one `workflow_started` row per execution; the attributed `workflow_resumed` row is now written with the passage's state write. An execution suspended before the upgrade resumes normally once the deployment's store reports a version for the records it held before the upgrade (a version column initialized for existing rows); the SDK's in-memory store keeps nothing across a restart

## ccf_runtime.http_api.errors.ERROR_HITL_GATE_CLOSED

- Surface: ccf_runtime.http_api.errors.ERROR_HITL_GATE_CLOSED
- Public surface: true
- Change type: added
- Before: absent
- After: `"hitl-gate-closed"`, the code `POST /hitl/actions` answers with 409 and the MCP door's `submit_hitl_action` raises in its refusal body, when the suspension the verdict names was already decided
- Why: `D-IMPL-378`
- Migration: a client branching on refusal codes adds this one; nothing was recorded

## ccf_runtime.http_api.routes.hitl.build_router

- Surface: ccf_runtime.http_api.routes.hitl.build_router
- Public surface: true
- Change type: behavior
- Before: `POST /hitl/actions` answered 200 for a verdict on a passed gate's suspension, with `event_pending: true` on the submit-only path, and `GET /hitl/queue` kept listing the passed gate's event
- After: such a verdict is answered 409 with `error_code` `hitl-gate-closed` and nothing is recorded; the queue no longer lists a decided gate's event
- Why: `D-IMPL-378`; `tests/http_api/test_approval_gate_limits_door.py::test_a_passed_gate_is_neither_offered_nor_accepted_as_pending_at_the_doors`
- Migration: as for `ERROR_HITL_GATE_CLOSED`

## ccf_runtime.mcp.hitl_server.build_hitl_server

- Surface: ccf_runtime.mcp.hitl_server.build_hitl_server
- Public surface: true
- Change type: behavior
- Before: `submit_hitl_action` had no refusal for a decided gate
- After: it raises the refusal body with `error_code` `hitl-gate-closed` when the transport refuses a verdict on a decided suspension
- Why: `D-IMPL-378`; `tests/mcp/test_hitl_gate_closed_mcp.py::test_a_verdict_on_a_decided_gate_is_refused_at_the_mcp_door`
- Migration: as for `ERROR_HITL_GATE_CLOSED`

## ccf.products.refusal.NON_VALUE_VIOLATIONS

- Surface: ccf.products.refusal.NON_VALUE_VIOLATIONS
- Public surface: true
- Change type: behavior
- Before: seven exception-family names
- After: `StateConflict` joins with its reason: an exception a state store raises, never a determination a consumer receives
- Why: the structural walk places every `…Conflict` class (`tests/products/test_refusal_envelope.py::test_the_refusal_vocabulary_is_closed_by_set_equality`)
- Migration: none
