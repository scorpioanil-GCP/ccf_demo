# 380-02 (second round, rulings 1 (a) and 2 (a)) — two writers hand the store a deep copy and keep their own; a deployment marker's type is checked from `lstat` before any open

`D-IMPL-380`, the dated amendment of 2026-10-10 07:39 MST, Dave, verbatim: *"`lstat` first in
`_read_deployment_marker`, so both beside-store reads and the boot's own re-reads are covered. The test counts opens
and must see zero. State the swap race."*; *"Each writer gives the store a deep copy made before the save and keeps
its own. The caller and the replay record, including the workflow resume path, get the untouched copy. The test
alters the record and then answers with the original fingerprint. The saved-bytes limit stays disclosed."* Built in
lane `380b-repair`, red test first. **SEC-020 stays OPEN**; nothing here changes a SEC row. The example write lock's
naming of a rule dependent, built in the same lane, is an example-only change to the example setup scripts and their
test harness, not an SDK change, and carries no entry here.

Fragment `380-01` said that each writer derives its reference before the store holds what it wrote; it did not say
that the object the store held was the writer's own, which the caller and the replay record go on to use. That
still holds, and this fragment adds to it.

**What the tests measure, on test fixtures.** `tests/peering/test_admission_record_store_holds_a_copy.py` (2 cases)
and `tests/workflow/test_trace_store_holds_a_copy.py` (4 cases), red on `9f5cea23` before the fix: a store that
alters what it is handed (a key written into the admission record's echoed parameters, a field forced with
`object.__setattr__` into the record's issuance or into the trace's first entry), files it, and answers the reference
of the object as handed had the crossing admitted with `AdmittedProduct.issuance` carrying the alteration, and had the
completed outcome's `step_sequence_block`, the state record read back after a completed, suspended or
exception-routed run, and the state record a recovering resumption wrote carry the rewrite. Now each carries the
object as built. `tests/products/test_deployment_marker_special_file_refused.py` (8 cases, red on `87fc9a56` and
`490b1645`): a FIFO and a socket at the marker's path beside a store were opened once before their type was checked;
now opened zero times, with the outcomes unchanged.

## ccf.peering.admission.PeeringAdmissionGate

- Surface: ccf.peering.admission.PeeringAdmissionGate
- Public surface: true
- Change type: behavior
- Before: `admit` handed the store its own admission record, whose `issuance` is the instance it returns in `AdmittedProduct`, so a store that altered the record while holding it and answered the record's original reference had its alteration returned to the caller.
- After: the store is handed a deep copy of the record taken before `put`; the gate keeps its own, so `AdmittedProduct.issuance` is the issuance as built. The bytes the store files are still not re-read: such a store files altered bytes under the original's address, and a reader that re-hashes what it fetches finds the difference.
- Why: `D-IMPL-380` second round, ruling 2 (a), 2026-10-10 07:39 MST. Red test: `tests/peering/test_admission_record_store_holds_a_copy.py::test_a_store_that_alters_the_record_and_answers_the_original_reference_leaves_the_admitted_issuance_as_built`.
- Migration: none for a store that does not change what it is handed.

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: the store was handed the engine's own trace entries, the ones behind `step_sequence_block` and inside the state record, so a store that rewrote the trace while holding it and answered the trace's original reference had its rewrite reach the outcome, the state record and the record a recovering resumption wrote.
- After: the store is handed deep copies of the entries taken before `put`; the engine keeps its own, so the outcome, the state record and the recovery path carry the trace as built. The bytes the store files are still not re-read, as for `ccf.peering.admission.PeeringAdmissionGate`.
- Why: `D-IMPL-380` second round, ruling 2 (a). Red test: `tests/workflow/test_trace_store_holds_a_copy.py`.
- Migration: none for a store that does not change what it is handed.

## ccf.deployment.manifest.DeploymentStoreNotVerified

- Surface: ccf.deployment.manifest.DeploymentStoreNotVerified
- Public surface: true
- Change type: behavior
- Before: beside a store, a FIFO, a socket or a device at the marker's path was opened (without blocking and without following a link) before its type was checked, and then refused `"unreadable"`.
- After: the marker's type is checked from `lstat` before any open, beside a store too, so such a file is refused `"unreadable"` without being opened. The `lstat` narrows, and does not close, one race: a special file swapped in for a regular one between the `lstat` and the open is opened and then refused from its descriptor's type.
- Why: `D-IMPL-380` second round, ruling 1 (a). Red test: `tests/products/test_deployment_marker_special_file_refused.py`.
- Migration: none; the refusals are unchanged.
