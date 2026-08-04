# 15-03 — the Criterion 1 surface audit baseline (ERGO-03)

Both entries are `Public surface: false`. `tools/dump_surface.py` walks only
`/src` and `/runtime` modules that define `__all__`, so neither a module under
`tools/` nor a Make target can ever appear in the manifest diff. Confirmed
empirically: `tools/dump_surface.py --report` reports `added (0)`,
`removed (0)`, `reshaped (0)` for this plan.

## tools/measure_examples.py

- Surface: tools/measure_examples.py
- Public surface: false
- Change type: added
- Before: absent — the examples tree's mechanical line counts existed only as
  a narrative table in `15-RESEARCH.md`, itself a correction of a ROADMAP
  estimate that was wrong in both directions
- After: an AST measurement tool with an exported `serialize()` and a
  `--check` mode, writing one JSON fragment per example module to
  `docs/surface/examples/before/`; `removable` (mechanical wiring, which
  rewrites delete) and `relocatable` (assertions and prints, which D-09 merely
  moves to `tests/`) are separate keys that are never summed
- Why: D-11 makes the surface audit a phase-close report and D-12 forbids a
  numeric target, so the audit's honesty rests entirely on the phase-close
  figure being a re-measurement by the same code that produced the phase-start
  figure, and on relocation being reported apart from removal — D-12's stated
  risk is a target hit by moving lines rather than by removing work
- Migration: none — this is a repository tool, not part of the installed SDK.
  Plans that rewrite an example write an `after/` fragment beside the
  `before/` one; the `before/` baseline is written once, by this plan, and is
  never regenerated

## make measure-examples

- Surface: make measure-examples
- Public surface: false
- Change type: added
- Before: absent
- After: regenerates the per-file baseline fragments under
  `docs/surface/examples/before/`; declared after the `surface:` target with
  its own `.PHONY` entry
- Why: the one documented command for the measurement (D-10), so the audit is
  reproducible by a name rather than by an invocation someone has to recall
- Migration: none. The target is deliberately not wired into `ci` — the
  assertion half lives in the always-on `test` job as
  `tests/examples/test_surface_audit.py`, the same arrangement `openapi` and
  `surface` use
