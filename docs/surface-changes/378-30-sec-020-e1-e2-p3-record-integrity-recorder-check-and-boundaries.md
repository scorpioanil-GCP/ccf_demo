# 378-30 — SEC-020: record integrity on every reader, incompatible recorders refused at construction, and the read-back and child-argument boundaries stated

`D-IMPL-378`, Dave's batch ruling of 2026-10-08 12:29 MST, items E1 (a), E2 (i), E2 (iii) and P3 (a), built on
lane `378e-s020`. **SEC-020 stays OPEN**: Dave did not approve its closure.

- **E1 (a)**, verbatim: *"Approve random per-answer issuance and the named conformance amendments. Preserve record
  content-address integrity. Random references must have indistinguishable distributions; equality is no longer
  the criterion."* A record's reference is its own content address, so its integrity is arithmetic, and the store
  is untrusted infrastructure. The replay engine always re-hashed what it read; two other readers did not.
- **E2 (iii)**, verbatim: *"Approve the recorder keyword change. Detect incompatible recorders at construction,
  rather than on the first refusal."*
- **E2 (i)**, verbatim: *"yes, narrowly: trusted operator/auditor handles holding the underlying store may remain
  unrestricted. Agent-accessible in-process interfaces must still enforce Q12. Document this boundary
  explicitly."* Documentation only, no behavior change: the docstrings of
  `ccf.products.product.OpenedProduct.record_of`, `ccf.replay.engine.replay`, `ccf.replay.engine.replay_refusal`,
  `ccf.replay.engine.resolve_artifact` and `ccf.replay.engine.resolve_artifact_at_uri` now state that each is an
  operator/auditor handle whose caller holds the store, unrestricted by the ruling, and that an agent reads records
  only through the governed evidence reads (measured by `tests/http_api/test_sec020_e2i_operator_boundary.py`).
- **P3 (a)**, verbatim: *"as the API improvement, but not as enforcement proof. Keep the captured-subject
  counterexample in the review. Trusted deployment code is an explicit assumption; caller-controlled mappings
  cannot use this exception."* Documentation only, no behavior change: `ccf.products.child_resolver.ChildArguments`,
  `ccf.products.child_resolver.GrantBoundChildResolver` and `ccf.products.child_resolver.QuestionBoundChildResolver`
  state the trusted-deployment-code assumption, the counterexample it does not cover
  (`tests/products/test_sec020_p3_captured_subject_counterexample.py`), and that no caller input supplies or
  selects a mapping.

**What the tests measure, on test fixtures.** `tests/replay/test_record_content_address_integrity.py`: a record's
name and version are the content address of its stored canonical bytes; an altered record is filed under its own
new name; bytes altered under a reference are refused by the replay engine's read, by `OpenedProduct.record_of`
and by the governed evidence read, before it reads and between its two reads (red before the change at
`record_of` and between the two reads; one severing each turns them red again).
`tests/products/test_sec020_e2iii_recorder_at_construction.py`: a recorder written to the pre-Q12 signature is
refused by name where `GovernedResolver`, `build_governed_resolver`, `create_app`, `build_egress_server`,
`build_experience_server` and `build_artifact_server` are built; a recorder naming the keyword, or taking
`**kwargs`, builds (red before the change on every path; one severing turns them red again).

## ccf.products.resolver.IncompatibleRefusalRecorder

- Surface: ccf.products.resolver.IncompatibleRefusalRecorder
- Public surface: true
- Change type: added
- Before: absent; a recorder whose `record` could not be passed `subject_withholding=` built cleanly and raised `TypeError` at the first refusal the governed resolver recorded.
- After: a `TypeError` raised where a resolver or an entitling door is built, naming the builder and the recorder's type, before anything is minted, registered or answered.
- Why: Dave's E2 (iii) (`D-IMPL-378`): detect incompatible recorders at construction, rather than on the first refusal.
- Migration: give your recorder's `record` the keyword `subject_withholding: str | None = None` (`RefusalRecorderProtocol`), or let it take `**kwargs`. The SDK's `ReplayRefusalRecorder` already does.

## ccf.products.resolver.refuse_incompatible_refusal_recorder

- Surface: ccf.products.resolver.refuse_incompatible_refusal_recorder
- Public surface: true
- Change type: added
- Before: absent.
- After: `refuse_incompatible_refusal_recorder(recorder, *, builder)` reads `record`'s signature, never calling it, and raises `IncompatibleRefusalRecorder` when `record` is missing, its signature cannot be read, or it can be passed `subject_withholding=` neither by name nor through `**kwargs`. Called by `GovernedResolver` and by every entitling door's builder.
- Why: Dave's E2 (iii) (`D-IMPL-378`); one check, stated once, for every path that accepts a recorder.
- Migration: none for a deployment; a door or a composition root that accepts a recorder of its own may call it at construction.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: construction accepted any recorder carrying a `record` attribute.
- After: construction refuses, right after the store-declaration check and before any refusal of the composition, minting or registration, a recorder whose `record` cannot be passed `subject_withholding=` (`IncompatibleRefusalRecorder`). `build_governed_resolver` hands a supplied recorder to it.
- Why: Dave's E2 (iii) (`D-IMPL-378`).
- Migration: as for `IncompatibleRefusalRecorder`.

## ccf.products.resolver.RefusalRecorderProtocol

- Surface: ccf.products.resolver.RefusalRecorderProtocol
- Public surface: true
- Change type: behavior
- Before: conformance was structural, the presence of `record` only; the signature was left to mypy.
- After: every path that accepts a recorder also reads one thing of `record`'s signature at construction: that it can be passed `subject_withholding=`.
- Why: Dave's E2 (iii) (`D-IMPL-378`).
- Migration: as for `IncompatibleRefusalRecorder`.

## ccf_runtime.authz.delivery_boundary.recorded_boundary

- Surface: ccf_runtime.authz.delivery_boundary.recorded_boundary
- Public surface: true
- Change type: behavior
- Before: refused only an absent or non-conforming recorder (`UnrecordableDeliveryBoundaryError`).
- After: also refuses, after that check, a recorder whose `record` cannot be passed `subject_withholding=` (`ccf.products.resolver.IncompatibleRefusalRecorder`), so `create_app`, the product router, `build_egress_server` (and `open_door`, which builds it) and `build_experience_server` refuse it where they are built.
- Why: Dave's E2 (iii) (`D-IMPL-378`).
- Migration: as for `IncompatibleRefusalRecorder`.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: accepted any recorder and called no recorder check at construction.
- After: refuses, first and before anything is composed, a recorder whose `record` cannot be passed `subject_withholding=` (`ccf.products.resolver.IncompatibleRefusalRecorder`).
- Why: Dave's E2 (iii) (`D-IMPL-378`): every path that accepts a refusal recorder.
- Migration: as for `IncompatibleRefusalRecorder`.

## ccf.products.product.OpenedProduct.record_of

- Surface: ccf.products.product.OpenedProduct.record_of
- Public surface: true
- Change type: behavior
- Before: returned whatever the store held at the outcome's address, parsed as a record, without checking that those bytes hash to the address; bytes altered on the substrate came back as the decision's record.
- After: re-hashes the stored bytes against the address the outcome names before parsing them, as the replay engine does (`D-IMPL-89`), and raises `ccf.replay.engine.ReplayDivergence` when they differ. Its docstring also states that it is an operator/auditor handle (Dave's E2 (i)).
- Why: Dave's E1 (a) (`D-IMPL-378`): preserve record content-address integrity.
- Migration: none for intact records. A caller that reads a record through `record_of` may now see `ReplayDivergence` for a record whose bytes were altered after filing.

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: behavior
- Before: re-hashed the bytes of its authorizing read (through `resolve_artifact`) but served, for a byte read, the bytes of its second, erasure-consulted read unchecked; bytes that changed between the two reads were served under the old address.
- After: the second read's bytes are held to the address too; a mismatch is the one evidence-absent refusal, recorded, exactly as bytes that do not hash to their address at the first read always were.
- Why: Dave's E1 (a) (`D-IMPL-378`): preserve record content-address integrity on the read that crosses.
- Migration: none.
