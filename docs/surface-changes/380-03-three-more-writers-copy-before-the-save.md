# 380-03 (third round, ruling 2 (a)) — three more writers hand the store a deep copy and keep their own; the erasure door checks both answers and returns its own record

`D-IMPL-380`, the dated amendment of 2026-10-10 09:18 MST, Dave, verbatim: *"Fix all three the same way. Copy before
the save. The erasure door also checks the store's answer and does not return the object the store held. The child
contracts are built from the copy the writer kept. The workflow state store is not trusted because it is the Control
Plane. That is the same hole as the artifact store, one writer over."* And at 09:23 MST: *"The reading stands. Both
saves get the copy and the answer check."* *"Each of the three writers copies before the save and keeps its own. The
erasure door checks both answers and returns its own record. The parent is built from contracts the store never held.
The state-store change is in the one function every state write uses, and the saved-bytes limit is written down."*
Built in lane `380c-repair`, red test first. **SEC-020 stays OPEN**; nothing here changes a SEC row.

Fragment `380-02` made two writers hand the store a deep copy. This fragment applies the same rule to three more:
the erasure door's two saves, the composite's child-contract retention, and the workflow engine's Control Plane state
writes. The saved-bytes limit stays disclosed for each: a store that alters its copy files (or saves) altered bytes,
and nothing here re-reads what it filed.

**What the tests measure, on test fixtures.** `tests/erasure/test_erasure_record_store_holds_a_copy.py` (4 cases, 3
of them red on `e00e9c2f`; the fourth, an approval altered and its original reference answered, is a guard that was
green before the fix too, because the door uses nothing of its approval after that save but the address it derived
before it): a store that rewrote the erasure record inside `put` and answered the original reference had its rewrite
returned by `complete`; a store that answered its altered address, for the record or the approval, was not refused.
`tests/products/test_child_contract_store_holds_a_copy.py` (1 case, red on `2128cc2a`): a store that wrote a key into
an admitted child contract's payload and answered the right address had its key reach the parent's child view.
`tests/workflow/test_state_store_holds_a_copy.py` (3 cases, red on `466516f6`): a state store that rewrote a trace
entry of the record it was handed had its rewrite reach the trace artifact and its reference, the completed outcome's
`step_sequence_block`, and the suspension's approval binding. Now each carries the object as built.

## ccf_runtime.erasure.ErasureDoor

- Surface: ccf_runtime.erasure.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: `complete` handed the store its own recorded approval and its own erasure record, discarded both answers, and returned the record the store had held, so a store that altered the record while holding it had its alteration returned to the caller under write-ahead index entries naming the record as built.
- After: both saves hand the store a deep copy taken before the save, and the door keeps its own object. Each answer is held, field for field as exact strings, to the reference the door derived before the save (content address, versioned URI, tenant, class, name). A mismatch is refused `ErasureRefused` by name after the store returns: `approval-reference-mismatch` before the write-ahead append, so no index entry is appended; `record-reference-mismatch` after it, with the address withheld under the appended entries, as on every other failed completion. `complete` returns the door's own record. The bytes the store files are still not re-read: the consult re-hashes what it fetches and fails closed on altered bytes.
- Why: `D-IMPL-380` third round, ruling 2 (a), 2026-10-10 09:18 and 09:23 MST. Red tests: `tests/erasure/test_erasure_record_store_holds_a_copy.py`.
- Migration: none for a store that does not change what it is handed and answers the reference of what it filed. A caller that branches on `ErasureRefused.reason_code` meets two new values.

## ccf_runtime.erasure.door.ErasureDoor

- Surface: ccf_runtime.erasure.door.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: as for `ccf_runtime.erasure.ErasureDoor`
- After: as for `ccf_runtime.erasure.ErasureDoor`
- Why: as for `ccf_runtime.erasure.ErasureDoor`
- Migration: as for `ccf_runtime.erasure.ErasureDoor`

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: a composite's child-contract retention handed the store each admitted child's own contract, the object from which the parent's child view is then built, and `ContextProductContract.payload` validates to a live `dict`, so a store that wrote into that mapping and answered the right address had its alteration reach the parent.
- After: the store is handed a deep copy of each contract taken before the save; the resolver keeps its own, so the parent's child view is built from contracts the store never held. The content-address check on the store's answer is unchanged. The bytes the store files are still not re-read; replay re-hashes what it fetches.
- Why: `D-IMPL-380` third round, ruling 2 (a). Red test: `tests/products/test_child_contract_store_holds_a_copy.py`.
- Migration: none for a store that does not change what it is handed.

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: every Control Plane state write handed the state store the engine's own state record, whose trace entries are the engine's own; in every passage but `_restore_request`, which writes the trace first (from a record read back from the store), the state write comes before `_write_trace`, so a state store that rewrote the record while holding it had its rewrite reach the trace artifact, a completed outcome's `step_sequence_block` and a suspension's approval binding.
- After: the one function every state write uses hands the state store a deep copy taken before the save; the engine keeps its own record, and the trace artifact, the outcome and the approval binding are built from it. The saved-bytes limit, state-store form: the state store saves its copy, and a later passage that reads the record back (a resume, a retry, the recovery path) reads what the store saved.
- Why: `D-IMPL-380` third round, ruling 2 (a). Red tests: `tests/workflow/test_state_store_holds_a_copy.py`.
- Migration: none for a state store that does not change what it is handed.
