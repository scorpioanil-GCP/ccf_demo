# 380-01 (rulings 1 (a), 3 and 4 (a)) — two writers derive their reference before the store holds what they wrote; a special file or an oversized file at a deployment marker's path is refused, never replaced

`D-IMPL-380`, the dated amendment of 2026-10-10 05:34 MST, Dave, verbatim: *"Hash before put in both writers. Compare
the store's answer to that precomputed reference. Do not hash the object again after the store has held it."*;
*"Refuse pipes, sockets, and devices without opening or replacing them. Do not weaken the page."*; *"Cap the read at
the longest marker the SDK writes. Refuse "oversized" by name. Do not replace the file. Count the bytes actually
read."* Built in lane `380-repair`, red test first. **SEC-020 stays OPEN**; nothing here changes a SEC row. The
cp-03 fixture lock and the removal of `CASCADE` from cp-03's setup script, built in the same lane, are example-only
changes to the example setup scripts and their test harness, not SDK changes, and carry no entry here.

Fragment `378-69` said that each writer derives the reference of what it filed; for the admission gate and the
workflow engine it was derived after `put` returned, from the object the store had held. Fragment `378-70-c` said
that anything at a stale marker's path that is neither a regular file nor a symbolic link (a FIFO, a socket, a device)
is replaced as before. Neither holds now. `378-69` and `378-70-c` are left as written; this fragment corrects them.

**What the tests measure, on test fixtures.** `tests/peering/test_admission_record_writer_hashes_before_put.py` (2
cases) and `tests/workflow/test_trace_writer_hashes_before_put.py` (3 cases), red on `2d8b0692` before the fix: a
store that alters the admission record while holding it (a key written into its echoed parameters, which validate to
a plain `dict`, or a field forced with `object.__setattr__`) and answers the altered record's genuine reference had
the crossing admitted with a `peering_admitted` verdict naming the altered record; a store that rewrites the trace's
first entry with `object.__setattr__` had the engine hand out the rewritten trace's reference on the completed,
suspended and exception-routed outcomes. Now each is refused by the existing mismatch type, with no verdict
appended and no `trace_artifact` returned. `tests/products/test_deployment_marker_special_file_refused.py` (2 cases,
red on `31a2a7fb`): a FIFO and a socket at the marker's path with no store were replaced and the boot booted
`"verified"`; now refused `"unreadable"`, the same inode left. `tests/products/test_deployment_marker_oversized_refused.py`
(2 cases, red on `fcc2c5f7`): a sparse 1 GiB marker was read whole (2 GiB read with no store beside it, 1 GiB beside
one); now refused `"oversized"`, at most the longest marker's length plus one byte read, the file untouched.

## ccf.peering.admission.PeeringAdmissionGate

- Surface: ccf.peering.admission.PeeringAdmissionGate
- Public surface: true
- Change type: behavior
- Before: `admit` derived the admission record's reference after the store's `put` returned, from the record object the store had held, so a store that altered the record while holding it and answered the altered record's own reference passed the check and the verdict named the altered record.
- After: the record's reference is derived from the record as built, before `put` is called, and the store's answer is held to it field for field; such a store is refused `AdmissionRecordReferenceMismatch`, and no `peering_admitted` verdict is appended.
- Why: `D-IMPL-380` ruling 1 (a), 2026-10-10 05:34 MST. Red test: `tests/peering/test_admission_record_writer_hashes_before_put.py::test_a_store_that_alters_the_record_while_it_holds_it_is_refused_and_no_verdict_is_written`.
- Migration: none for a store that does not change what it is handed.

## ccf.peering.admission.AdmissionRecordReferenceMismatch

- Surface: ccf.peering.admission.AdmissionRecordReferenceMismatch
- Public surface: true
- Change type: behavior
- Before: raised when the store's answer was not the reference of the record object as it stood after `put` returned.
- After: raised when the store's answer is not the reference of the record as the gate built it, derived before `put`; this includes a store that altered the record while holding it.
- Why: `D-IMPL-380` ruling 1 (a). Red test: as for `ccf.peering.admission.PeeringAdmissionGate`.
- Migration: none.

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: the execution trace's reference was derived after the store's `put` returned, from the trace the store had held, so a store that rewrote the trace while holding it and answered the rewritten trace's own reference had that reference handed out as `trace_artifact`.
- After: the trace's reference is derived from the trace as built, before `put` is called; such a store is refused `WorkflowTraceReferenceMismatch`, and no outcome carrying a `trace_artifact` is returned.
- Why: `D-IMPL-380` ruling 1 (a). Red test: `tests/workflow/test_trace_writer_hashes_before_put.py::test_a_store_that_rewrites_the_trace_while_it_holds_it_is_refused_and_no_trace_reference_is_handed_out`.
- Migration: none for a store that does not change what it is handed.

## ccf_runtime.workflow.engine.WorkflowTraceReferenceMismatch

- Surface: ccf_runtime.workflow.engine.WorkflowTraceReferenceMismatch
- Public surface: true
- Change type: behavior
- Before: raised when the store's answer was not the reference of the trace as it stood after `put` returned.
- After: raised when the store's answer is not the reference of the trace as the engine built it, derived before `put`; this includes a store that rewrote the trace while holding it.
- Why: `D-IMPL-380` ruling 1 (a). Red test: as for `ccf_runtime.workflow.engine.WorkflowEngine`.
- Migration: none.

## ccf.deployment.manifest.DeploymentStoreNotVerified

- Surface: ccf.deployment.manifest.DeploymentStoreNotVerified
- Public surface: true
- Change type: reshaped
- Before: `reason` was one of `"pending"`, `"unreadable"`, `"claimed"`, `"lock-unavailable"`, `"lock-held"`; a FIFO, a socket or a device at the marker's path with no store beside it was replaced; a regular-file marker was read to its full size, and one longer than any marker the SDK writes was refused `"unreadable"` beside a store and replaced with none.
- After: `reason` may also be `"oversized"`: a regular file at the marker's path, with or without a store beside it, longer than the longest marker the SDK writes. The boot reads at most one byte past that length and neither compares nor replaces the file; the text names the marker and says an operator resolves it. Anything at the marker's path that is neither a regular file nor a symbolic link (a FIFO, a socket, a character or block device, a directory) is refused `"unreadable"` before anything is created, decided from its `lstat` type, never opened and never replaced.
- Why: `D-IMPL-380` rulings 3 and 4 (a), 2026-10-10 05:34 MST. Red tests: `tests/products/test_deployment_marker_special_file_refused.py::test_380_3_a_special_file_at_the_marker_path_with_no_store_is_refused_unreadable_and_left` and `tests/products/test_deployment_marker_oversized_refused.py::test_380_4_a_sparse_1_gib_marker_is_refused_oversized_read_at_most_the_bound_and_left`.
- Migration: a caller that branches on `reason` meets a sixth value. For `"oversized"` or a special file refused `"unreadable"`, find what wrote it at the marker's path, then remove it (and the store, if one stands there) so that a boot creates and verifies a new store (the security how-to, section 4.12).

## ccf.deployment.DeploymentStoreNotVerified

- Surface: ccf.deployment.DeploymentStoreNotVerified
- Public surface: true
- Change type: reshaped
- Before: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.
- After: as `ccf.deployment.manifest.DeploymentStoreNotVerified`; the package-level spelling of the same class.
- Why: `D-IMPL-380` rulings 3 and 4 (a).
- Migration: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: a plain boot replaced a FIFO, a socket or a device standing at the marker's path with no store beside it, and read a regular-file marker to its full size.
- After: it is refused `DeploymentStoreNotVerified`, `"unreadable"` for such a special file and `"oversized"` for a regular file longer than any marker the SDK writes; neither is replaced.
- Why: `D-IMPL-380` rulings 3 and 4 (a). Measured as for `ccf.deployment.manifest.DeploymentStoreNotVerified`.
- Migration: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: as `load_and_boot`.
- After: as `load_and_boot`; both doors share one boot spine.
- Why: `D-IMPL-380` rulings 3 and 4 (a).
- Migration: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.
