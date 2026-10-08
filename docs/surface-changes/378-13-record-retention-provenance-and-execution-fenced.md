# 378-13 — record retention for the records the fabric filed; a fenced passage refused 409 at the workflow doors

Two fixes Dave ordered on 2026-10-07 at 21:11 MST (`D-IMPL-378`, "yes fix both
now"). Each was measured red before anything changed.

- **The erasure door applied record retention to anything shaped like a
  record.** Lane 378-provenance measured that
  `runtime/ccf_runtime/erasure/door.py::ErasureDoor._verify_addresses` refused
  `replay-input` for ANY stored bytes carrying the subject in a replay-input
  field, a principal's own client-lane filing included. So a tenant could make
  its own client file un-erasable by shaping it like a Decision Replay record,
  and `tests/erasure/test_sec009_address_verification.py` pinned that as if it
  were intended. Dave's ruling: apply record-retention rules only to records the
  fabric itself filed, using the one provenance check,
  `src/ccf/replay/provenance.py::filed_by_record_writer`.
- **`ExecutionFenced` reached HTTP callers as a 500.** Lane 378b-approval
  measured that the workflow doors let it escape unmapped. Dave's ruling: a typed
  refusal at every door that drives workflows. Those doors are
  `POST /workflow/invocations` and `POST /workflow/resumptions`, and, in process,
  the erasure door (`git grep` over `src` and `runtime`: the engine's `execute`
  and `resume` are otherwise called only by the in-process orchestration
  drivers, which hand the engine's exception back by name). No MCP door executes
  or resumes a workflow, and no HTTP or MCP door serves the erasure door. On the
  coordinator's instruction this lane merged lane 378c-finish (Dave's D2), whose
  finisher adds `ExecutionFenced` raise sites: a retried start the engine
  finishes (`WorkflowEngine._finish_start`), and the erasure door's retried
  request and completion.

## ccf_runtime.erasure.ErasureDoor

- Surface: ccf_runtime.erasure.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: `request` and `complete` refused an address `replay-input` whenever the subject appeared in a replay-input field (`ccf.erasure.REPLAY_INPUT_PATHS`) of its stored bytes, whoever filed them. A door over an erasure-consulting composition whose store answers no `names_at` raised an unmapped `AttributeError`. An `ExecutionFenced` the engine raised under `request` or `complete` escaped the door unmapped.
- After: the `replay-input` refusal applies only where the store's naming shows the address filed by the fabric's record writer, under a class its `WriteKinds` declares under `ReplayMint`, under the requesting tenant. `src/ccf/replay/provenance.py::filed_by_record_writer` decides it, asked only for an address whose subject is in a replay-input field. Any other filing, a record-shaped client-lane filing included, is erased like any client artifact. A store that declares no `WriteKinds` cannot say who filed such an address, so the door refuses `class-unverifiable`, with `UnattributableRecordStore` as the cause; a naming read that fails when that question is asked is refused the same way. A door over an erasure-consulting composition whose store answers no `names_at` is refused `class-unverifiable` for any address, as `ErasureConsultingStore.names_at` documents. The `ccf.erasure` package docstring states the narrowed rule. A passage the engine fenced (`ExecutionFenced`) is refused `ErasureRefused` with reason code `execution-fenced` and the fence as the cause: at `request`, no approval is requested; at `complete`'s last passage, after the write-ahead append, no erasure record is filed and the address stays withheld (`index-unsupported`) under the appended entries; at a further gate's passage, nothing is erased (code reading; no fixture erasure workflow has a second gate).
- Why: `D-IMPL-378` (Dave, 2026-10-07 21:11 MST). The `execution-fenced` refusal: `tests/erasure/test_erasure_door_execution_fenced.py` (four red tests: a request's start fenced, directly and through the engine's finisher, and a completion's last passage fenced, directly and through the finisher). The replay-input rule's red tests: `tests/erasure/test_sec009_address_verification.py::test_a_client_filing_with_the_subject_in_a_replay_input_field_is_erased_like_any_client_artifact` (renamed from `::test_a_subject_in_a_replay_input_field_refuses_replay_input`, which asserted the defect); `tests/erasure/test_replay_input_retention_provenance.py::test_a_record_shaped_client_filing_is_erased_like_any_client_artifact`, `::test_a_store_that_declares_no_write_kinds_refuses_rather_than_judge_a_record_shaped_filing` (raw and composed), `::test_an_erasure_consulting_store_over_a_substrate_with_no_naming_refuses_class_unverifiable` and `::test_over_the_mcp_backed_store_a_client_filing_with_the_subject_in_a_replay_input_field_is_erasable`; added after the fix, `::test_a_naming_read_that_fails_when_provenance_is_asked_refuses_class_unverifiable`. Control: `::test_a_record_the_fabrics_record_writer_filed_still_refuses_replay_input`.
- Migration: a caller of the erasure door that handled `ExecutionFenced` by name now receives `ErasureRefused` with reason code `execution-fenced`, the fence chained as its cause. An erasure request naming a client artifact with the subject in a replay-input field is now admitted and erased; a record the record writer filed is refused `replay-input` as before. Over the MCP-backed store, a request naming a client filing the record validator accepts is still refused `subject-unverifiable`, because the artifact server does not serve those bytes on the client lane. That is a residual, kept as the strict expected failure `tests/erasure/test_replay_input_retention_provenance.py::test_over_the_mcp_backed_store_a_record_shaped_client_filing_is_erased_like_any_client_artifact`. A door over a third-party store that declares no `WriteKinds` is refused `class-unverifiable` where it was refused `replay-input`; declare the store's `WriteKinds`.

## ccf_runtime.erasure.door.ErasureDoor

- Surface: ccf_runtime.erasure.door.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: as for `ccf_runtime.erasure.ErasureDoor`
- After: as for `ccf_runtime.erasure.ErasureDoor`
- Why: as for `ccf_runtime.erasure.ErasureDoor`
- Migration: as for `ccf_runtime.erasure.ErasureDoor`

## ccf_runtime.http_api.errors.ERROR_EXECUTION_FENCED

- Surface: ccf_runtime.http_api.errors.ERROR_EXECUTION_FENCED
- Public surface: true
- Change type: added
- Before: absent
- After: `"execution-fenced"`, the code `POST /workflow/invocations` and `POST /workflow/resumptions` answer with 409 when the engine fenced a write that ends a passage because another writer moved the execution's record (`ExecutionFenced`)
- Why: `D-IMPL-378` (Dave, 2026-10-07 21:11 MST)
- Migration: a client branching on refusal codes adds this one. The engine wrote, audited and enqueued nothing, and a resumption presented again is refused as an interrupted passage (`tests/http_api/test_execution_fenced_door.py::test_after_a_fenced_passage_a_resumption_presented_again_is_refused_as_an_interrupted_passage`)

## ccf_runtime.http_api.routes.workflow.build_router

- Surface: ccf_runtime.http_api.routes.workflow.build_router
- Public surface: true
- Change type: behavior
- Before: an `ExecutionFenced` raised by the engine's `execute` or `resume` escaped both routes unmapped, and the caller got an opaque `500 Internal Server Error`
- After: both routes answer it 409 with the shared refusal body, `error_code` `execution-fenced` and the fence's message. That includes the invocation of a retried start the engine finishes (lane 378c-finish), whose suspension write loses to another writer
- Why: `D-IMPL-378`. Red tests: `tests/http_api/test_execution_fenced_door.py::test_a_passage_fenced_at_the_resumption_door_is_refused_409_execution_fenced` and `::test_a_passage_fenced_at_the_invocation_door_is_refused_409_execution_fenced`; positive controls `::test_the_same_request_with_no_other_writer_answers_200`. The finisher's site: `::test_a_finished_start_fenced_at_the_invocation_door_is_refused_409_execution_fenced` (red on lane 378c-finish's tree, which has no mapping), control `::test_the_same_finished_start_with_no_other_writer_answers_200`
- Migration: as for `ERROR_EXECUTION_FENCED`. No MCP door executes or resumes a workflow, so no MCP rendering changes
