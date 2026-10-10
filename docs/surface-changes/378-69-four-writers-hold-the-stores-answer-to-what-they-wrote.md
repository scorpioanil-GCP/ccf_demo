# 378-69 (decision 5 (a), extended) — four more writers hold the store's answer to what they wrote

`D-IMPL-378` decision 5, ruled by Dave on 2026-10-09 at 16:38 MST, adopting Grok's recommendation, verbatim: *"(a) Fix
the four writers in one small lane."* The option he ruled on extends decision 5 (a) (06:06 MST, confirmed at 06:21
MST), *"Verify the returned record address against the record actually written."*, built for the record writer in
fragment `378-53-a`, to four neighbor writers that the lane `378i-small` reported. Built in lane `378j-writers`. SEC-020
stays open; nothing here changes a SEC row.

**What was measured before the change**, on `dl-378-integ` @ `6cd6023e`, with stores that file the bytes faithfully
and answer another artifact's reference, or the right reference with one field (content address, URI, name, tenant or
class) changed or carried in a `str` subclass that claims equality:

- `QueryPinWriter.write_query_bytes` returned the store's answers: a store answering every write with the first query's
  reference made it return query 1's reference for query 2. The governed `serve()` discards these references, so none
  of them left a serve; the product was delivered and its record appended.
- `QuestionBoundChildResolver` held the content address of the parent store's answer for a child question (with `!=`,
  which the `str` subclass passes) and recorded its URI unchecked as `ChildResolution.child_question_ref`: a store
  answering the question's own address and another question's URI had that URI recorded, and replay's audit read of the
  row then raised `ReplayDivergence`. A changed name, tenant or class was accepted.
- `PeeringAdmissionGate` used the store's answer for the admission record unchecked: with another crossing's record
  reference answered, the crossing was admitted and its `peering_admitted` verdict's key and version named the other
  crossing's record; a changed URI, tenant or class was accepted.
- `WorkflowEngine` handed the store's answer for the execution trace to callers as `trace_artifact` on the suspended,
  exception-routed and completed outcomes: another execution's trace reference was handed out for this one.

**What holds now**, in `tests/replay/test_query_pin_writer_checks_the_returned_reference.py`,
`tests/products/test_child_question_retention_checks_the_returned_reference.py`,
`tests/peering/test_admission_record_writer_checks_the_returned_reference.py` and
`tests/workflow/test_trace_writer_checks_the_returned_reference.py` (53 tests written before the change: 47 failed
before it, the 6 controls passed before and after; plus two cases pinning what a crossing refused at its record
keeps, added after it, below). Each writer derives the reference of what it filed under `D-IMPL-26` (the content
address is the content hash of what was written, the URI's version is that address, the name and class are the
writer's own, the tenant is its capability's) and holds every field of the store's answer to it as an exact string,
with the record writer's comparison (`ccf.replay.serve._same_string`). A difference raises the writer's own
`ArtifactStoreError` subclass, after `put` returns and before any reference leaves the writer or is recorded; the text
names the differing fields and no value the store answered. The reference handed out or recorded is the one the
writer derived, which the store's answer equals. Each check was severed (the store's answer handed out again) and the
same tests reddened; weakening the shared comparison to `==` reddened exactly the 20 claimed-equality tests.

**What it does not check.** The bytes the store holds: each writer reads the store's answer, not the store. A store
that answers the right reference while holding other bytes under it is found by the readers that re-hash what they
fetch before use (`ccf.replay.engine.resolve_artifact`, `ccf.replay.engine.retained_child_question`).

**Not changed, and measured.** At the MCP egress door these four refusals, like `ReplayReferenceMismatch`, are not
among the types the door wraps into the opaque `ccf-runtime-failure:<id>` (it wraps `ValueError`, `TypeError`,
`LookupError` and `OSError`), so a client that triggers one behind the door receives its text: the fixed prose and the
differing field names, no value and no type name.

## ccf.replay.serve.QueryPinReferenceMismatch

- Surface: ccf.replay.serve.QueryPinReferenceMismatch
- Public surface: true
- Change type: added
- Before: absent; the query-pin writer returned whatever references the store answered.
- After: an `ArtifactStoreError` raised by `QueryPinWriter.write_query_bytes` when any field of the reference the store's `put` answered for a query (content address, URI, tenant, class, name) is not, as an exact string, the query's own. It carries `fields`, the names of the differing fields; its text names those fields and no value the store answered.
- Why: `D-IMPL-378` decision 5 (a), extended by decision 5. Red test: `tests/replay/test_query_pin_writer_checks_the_returned_reference.py::test_a_store_answering_the_first_querys_reference_for_every_write_is_refused_by_name`.
- Migration: none; additive. A handler for `ArtifactStoreError` also catches it.

## ccf.products.child_resolver.ChildQuestionReferenceMismatch

- Surface: ccf.products.child_resolver.ChildQuestionReferenceMismatch
- Public surface: true
- Change type: added
- Before: absent; the question-bound resolver raised a plain `RuntimeError` when the parent store's answer for a child question carried another content address (compared with `!=`) and recorded the answer's URI unchecked.
- After: an `ArtifactStoreError` that is also a `RuntimeError`, raised when any field of the parent store's answer for a child question (content address, URI, tenant, class, name) is not, as an exact string, the question's own, after `put` returns and before the producer is asked. It carries `fields`; its text names those fields and no value the store answered. It replaces the address-only `RuntimeError`, whose text named both addresses.
- Why: `D-IMPL-378` decision 5 (a), extended by decision 5. Red test: `tests/products/test_child_question_retention_checks_the_returned_reference.py::test_a_parent_store_answering_another_questions_uri_is_refused_by_name`.
- Migration: none for a handler of `RuntimeError` or `ArtifactStoreError`. A product class that declared `builtins.RuntimeError` as a seam refusal no longer matches it, because seam refusals match the exact type.

## ccf.peering.admission.AdmissionRecordReferenceMismatch

- Surface: ccf.peering.admission.AdmissionRecordReferenceMismatch
- Public surface: true
- Change type: added
- Before: absent; the admission gate pointed its verdict at whatever reference the store answered for the admission record.
- After: an `ArtifactStoreError` raised by `PeeringAdmissionGate.admit` when any field of the store's answer for the admission record (content address, URI, tenant, class, name) is not, as an exact string, the record's own, after `put` returns and before the `peering_admitted` verdict is appended. It is not an `AdmissionNotRecorded`: the store answered. It carries `fields`; its text names those fields and no value the store answered.
- Why: `D-IMPL-378` decision 5 (a), extended by decision 5. Red test: `tests/peering/test_admission_record_writer_checks_the_returned_reference.py::test_a_store_answering_another_crossings_record_reference_is_refused_by_name`.
- Migration: none; additive. A handler for `ArtifactStoreError` also catches it.

## ccf_runtime.workflow.engine.WorkflowTraceReferenceMismatch

- Surface: ccf_runtime.workflow.engine.WorkflowTraceReferenceMismatch
- Public surface: true
- Change type: added
- Before: absent; the engine handed callers whatever reference the store answered for the execution trace.
- After: an `ArtifactStoreError` raised by `WorkflowEngine.execute` and `WorkflowEngine.resume` when any field of the store's answer for the trace (content address, URI, tenant, class, name) is not, as an exact string, the trace's own, after `put` returns, so no outcome carrying it is returned. It carries `fields`; its text names those fields and no value the store answered.
- Why: `D-IMPL-378` decision 5 (a), extended by decision 5. Red test: `tests/workflow/test_trace_writer_checks_the_returned_reference.py::test_a_store_answering_another_executions_trace_reference_is_refused_by_name`.
- Migration: none; additive. A handler for `ArtifactStoreError` also catches it.

## ccf.replay.serve.QueryPinWriter

- Surface: ccf.replay.serve.QueryPinWriter
- Public surface: true
- Change type: behavior
- Before: `write_query_bytes` returned whatever references the store's `put` answered, one per query.
- After: `write_query_bytes` derives each query's own reference and raises `QueryPinReferenceMismatch` unless the store's answer equals it field for field; the references returned are the derived ones. Queries filed before the mismatched one in the same call stay filed.
- Why: `D-IMPL-378` decision 5 (a), extended by decision 5. Red test: `tests/replay/test_query_pin_writer_checks_the_returned_reference.py::test_a_reference_with_any_field_not_the_querys_own_is_refused_by_name`.
- Migration: none for a store conforming to `D-IMPL-26`; a store answering any other reference for a query is refused.

## ccf.replay.serve.serve

- Surface: ccf.replay.serve.serve
- Public surface: true
- Change type: behavior
- Before: with a query-pin writer, discarded the references the pin store answered, then appended the record and delivered.
- After: raises `QueryPinReferenceMismatch`, through the pin writer, when the pin store's answer for an executed query is not that query's own reference; the record is not appended and nothing is delivered.
- Why: `D-IMPL-378` decision 5 (a), extended by decision 5. Red test: `tests/replay/test_query_pin_writer_checks_the_returned_reference.py::test_the_governed_serve_delivers_nothing_when_the_pin_store_answers_another_querys_reference`.
- Migration: none for a conforming store.

## ccf.products.child_resolver.QuestionBoundChildResolver

- Surface: ccf.products.child_resolver.QuestionBoundChildResolver
- Public surface: true
- Change type: behavior
- Before: `resolve_for` recorded the URI the parent store answered for each child question as the row's `child_question_ref`, checking only the answer's content address.
- After: `resolve_for` raises `ChildQuestionReferenceMismatch` before the producer is asked when the parent store's answer is not the question's own reference; the URI recorded is the derived one, which the store's answer equals. Through a governed resolver it propagates unless the product class declares it a seam refusal, so the composition records and answers nothing.
- Why: `D-IMPL-378` decision 5 (a), extended by decision 5. Red test: `tests/products/test_child_question_retention_checks_the_returned_reference.py::test_a_reference_with_any_field_not_the_questions_own_is_refused_by_name`.
- Migration: none for a conforming store.

## ccf.peering.admission.PeeringAdmissionGate

- Surface: ccf.peering.admission.PeeringAdmissionGate
- Public surface: true
- Change type: behavior
- Before: `admit` appended the `peering_admitted` verdict with the key and version of whatever reference the store answered for the admission record.
- After: `admit` raises `AdmissionRecordReferenceMismatch` when the store's answer is not the record's own reference; no verdict is appended and no `AdmittedProduct` exists. The issuance nonce is spent, as when the record is not persisted (`AdmissionNotRecorded`): the same envelope presented again is refused `replayed` (`tests/peering/test_admission_record_writer_checks_the_returned_reference.py::test_a_crossing_refused_at_its_record_has_spent_its_nonce`, both cases; SP §1.1a's nonce sentence now says so).
- Why: `D-IMPL-378` decision 5 (a), extended by decision 5. Red test: `tests/peering/test_admission_record_writer_checks_the_returned_reference.py::test_a_reference_with_any_field_not_the_records_own_is_refused_by_name`.
- Migration: none for a conforming store.

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: the suspended, exception-routed and completed outcomes carried, as `trace_artifact`, whatever reference the store answered for the execution trace.
- After: those outcomes carry the trace's own reference, and the engine raises `WorkflowTraceReferenceMismatch` instead of returning one when the store's answer is not it. The trace is written after the transition it describes is persisted, so that transition and its audit row stand, and at a suspension the approval request has not been enqueued, as with a store failure at that point.
- Why: `D-IMPL-378` decision 5 (a), extended by decision 5. Red test: `tests/workflow/test_trace_writer_checks_the_returned_reference.py::test_a_reference_with_any_field_not_the_traces_own_is_refused_by_name`.
- Migration: none for a conforming store.
