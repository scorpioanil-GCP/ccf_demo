# 15-03 — the Criterion 1 surface audit baseline (ERGO-03)

Both entries are `Public surface: false`. `tools/dump_surface.py` walks only
`/src` and `/runtime` modules that define `__all__`, so neither a module under
`tools/` nor a Make target can ever appear in the manifest diff. Confirmed
empirically: `tools/dump_surface.py --report` reports `added (0)`,
`removed (0)`, `reshaped (0)` for this plan.

## Carry-forward ruling for plan 15-04 (not a surface change)

Dave approved the Task 4 checkpoint on 2026-08-04. The widened No-Hardcoding
lint over `tests/` produces **3 findings** — under threshold, so D-IMPL-78
lands in plan 15-04 as scoped and needs no re-surfacing.

Two of the three are prose-diagnostic false positives of
`cinv01a-prompt-shape`: `tests/http_api/test_openapi.py:38` (the `make openapi`
drift message) and `tests/test_surface_drift.py:78` (the `make surface` drift
message). **Dave's explicit ruling: resolve these by RULE REFINEMENT, not by
allowlist entries.** Two allowlist entries today becomes friction on every
future diagnostic message, and this phase's own conventions actively encourage
multi-sentence diagnostics that name their own fix (15-01 ships a test
asserting exactly that). The distinction is mechanically detectable — a prompt
is a string sent to a model; a diagnostic is a string shown to a developer.
`cinv01a-prompt-shape` currently detects "long English string literal," which
is a proxy for the wrong thing.

The third finding, `tests/agents/test_agent.py:93`
(`cinv01c-factory-bypass`, a direct `Agent(**values)` call), is **genuine** per
CLAUDE.md §6.4 and must keep firing after the refinement.

Plan 15-03 records this ruling only; the refinement itself is 15-04's work and
`tools/lints/__main__.py` is unmodified by this plan.

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
