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
