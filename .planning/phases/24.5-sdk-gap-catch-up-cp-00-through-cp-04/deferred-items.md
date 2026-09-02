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
