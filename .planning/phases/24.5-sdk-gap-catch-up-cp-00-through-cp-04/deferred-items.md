# Phase 24.5 — deferred items

Out-of-fence discoveries logged by executors. Not fixed in the plan that found them
(the fence is the plan's `ledger_ids`); carried for the phase close.

## Found by 24.5-03 (2026-09-02)

- **`tests/test_surface_completeness.py::test_every_diff_line_has_a_matching_public_log_entry`
  is RED at the Wave-2 base `4614e6e`, before and independent of plan 03's fragment.**
  The manifest diff reports `reshaped: ccf.halflife.decay.HalfLifeEntry — NO ENTRY`. Plan
  `24.5-11` (`24.5-L-22`; commits `633da39`, `64e3a50`) reshaped `HalfLifeEntry`, and its
  fragment `docs/surface-changes/24.5-11-a-supersede-only-half-life-class.md` claims the name
  as `ccf.controlplane.artifacts.HalfLifeEntry` only; the re-export
  `ccf.halflife.decay.HalfLifeEntry` is a second manifest line with no entry. Repair belongs
  to `L-22`'s owner (one more seven-field section, or a `reshaped` entry for the re-export
  name); plan 03 does not touch it. `tests/test_surface_drift.py` is GREEN; 19 of the 20
  cases in the two surface gates pass.

Out-of-scope discoveries logged by executors under the deviation rules' scope
boundary: found while working one ledger row, not caused by that row's edit,
and not fixed inside that row's fence.

## 1. `ccf.halflife.decay.HalfLifeEntry` has no surface-log claim (found by plan 24.5-04)

- **Found during:** plan `24.5-04` Task 3, running `tests/test_surface_completeness.py`
  after adding the `24.5-04` fragment.
- **What:** `tests/test_surface_completeness.py::test_every_diff_line_has_a_matching_public_log_entry`
  is RED at the Wave-2 base (`4614e6e`) on
  `reshaped: ccf.halflife.decay.HalfLifeEntry — NO ENTRY`. The name is the
  `ccf.halflife.decay` re-export of `ccf.controlplane.artifacts.HalfLifeEntry`,
  which ledger row `24.5-L-22` (plan `24.5-11`) reshaped.
  `docs/surface-changes/24.5-11-a-supersede-only-half-life-class.md` claims
  `ccf.controlplane.artifacts.HalfLifeEntry` (`reshaped`) and mentions the
  `ccf.halflife.decay.HalfLifeEntry` re-export only in prose — the gate matches
  `Surface:` fields, not prose.
- **Not mine to fix:** the fragment belongs to `24.5-L-22`; plan `24.5-04`'s
  fence is `24.5-L-05` only (criterion 1). The fix is one `Surface:` section
  for `ccf.halflife.decay.HalfLifeEntry` (`reshaped`) in the `24.5-11`
  fragment, then `tools/assemble_surface_changes.py`.
- **Owner:** whichever plan next touches the `24.5-11` fragment, or the phase
  close (`24.5-18`), before the surface manifest is regenerated.
- **Plan 24.5-04's own entries** (`TraversalSpec`, both
  `TraversalNeighborhoodParameters` paths, the artifact class, and
  `TraversalNeighborhood` as `behavior`) pass
  `test_every_public_log_entry_has_a_matching_diff_line`.

## 2. `OperatorParametersArtifact`'s "no default in this hierarchy" sentence is stale (found by plan 24.5-05)

- **Found during:** plan `24.5-05` Task 2, reading
  `src/ccf/controlplane/artifacts.py::OperatorParametersArtifact` to mirror the
  neighborhood artifact's shape for the descendants sibling.
- **What:** the marker base's docstring says "**No field in this hierarchy
  carries a default.**" Since ledger row `24.5-L-05` (plan `24.5-04`) both
  `TraversalNeighborhoodParametersArtifact` and now
  `TraversalDescendantsParametersArtifact` inherit
  `admitted_entity_classes: frozenset[str] | None = None` — a named positive
  sentinel, not a chosen number (the `ccf.operators.params` module docstring
  already says so). Doc-only; no behavior is wrong.
- **Not mine to fix:** the sentence is `L-05`'s (the field that made it stale);
  plan `24.5-05`'s fence is `24.5-L-06` only (criterion 1). Plan `24.5-04`'s
  out-of-scope item 3 logged the sibling sentence on the neighborhood artifact.
- **Owner:** the return trip, or whichever plan next edits that docstring —
  one sentence in the `params.py` voice ("no NUMERIC default; the `None` is a
  positive sentinel").

## 3. hw1's `consume.py` prints `— None` for a gate refusal's key (found by plan 24.5-15)

- **Found during:** plan `24.5-15` Task 1, measuring the ladder flip on
  `tests/examples/test_hw1_two_transports.py::test_both_documented_transports_return_the_same_answer`.
- **What:** `examples/hw1-companies-over-revenue/consume.py` prints
  `f"refused: {result.refusal.reason} — {result.refusal.key}"` on any refusal.
  A gate refusal names no parameter, so `key` is `None` and the line reads
  `refused: empty-operator-result — None`. Cosmetic; the typed refusal is
  correct. Before `24.5-L-24` no gate refusal reached this line on a clean
  checkout (the empty fabric served "0 of 0 assembled"), so the shape was
  never printed.
- **Not mine to fix:** `examples/` is closed in 24.5 (`.continue-here.md`);
  a README/consume change is `24.5.1`. The flip itself is recorded in
  `24.5-15-SUMMARY.md` for plan `24.5-16`'s re-measure.
- **Owner:** `24.5.1`, alongside whatever ruling plan `24.5-16` reaches on
  the hw1 flip (a clean checkout's hello-world is now refused by name rather
  than served empty).

## 24.5-FIX-01 — out-of-scope observations (not fixed here)

### `tools/docs_tests/test_requirement_ledger.py::test_the_uat_roster_matches_the_records_on_disk` is red before this fix

- **Observed:** `make gate-tools`'s docs leg: the frozen `human_verification`
  roster lacks `.planning/phases/24.5-sdk-gap-catch-up-cp-00-through-cp-04/24.5-VERIFICATION.md`,
  which `ceab40fd` (the phase verification report, before `24.5-FIX-01`)
  put on disk. Pre-existing at `b232ff29`; not caused by CR-01's fix and not
  touched by it.
- **Owner:** the 24.5 close (the roster is a phase-close artifact).

### `tests/replay/test_store_snapshot_pin_fluree.py::test_a_product_served_at_pin_n_is_not_reproducible_from_pin_n_plus_1` failed ONCE in a full Fluree leg

- **Observed:** first full leg (`CCF_REQUIRE_FLUREE=1 CCF_TEST_FLUREE_URL=http://localhost:8090 … -m fluree`):
  `TypeError: the JSON object must be str, bytes or bytearray, not NoneType`
  from `src/ccf/graph/reader.py::_entity_records` under
  `src/ccf/graph/backends/fluree.py::query_pinned` — a pinned read returning a
  row with no attributes column. Not reproduced: the module alone passed twice,
  and the second full leg passed it (284 passed, only `CFT-G16` red, which is
  the measured consequence recorded in `24.5-FIX-01-SUMMARY.md`). No file in
  the failing path was edited by this fix.
- **Owner:** the Fluree leg's state-accumulation posture (`D-03`, one
  CCF-owned ledger across a job); an order-dependent read, to be reproduced
  before it is believed.
