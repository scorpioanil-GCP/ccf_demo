---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 01
subsystem: tooling
tags: [surface-manifest, drift-gate, d-15, ergo-01, ergo-17]
requires: []
provides:
  - tools.dump_surface.serialize
  - tools.dump_surface.diff_surfaces
  - tools.dump_surface.build_surface
  - docs/surface/v0.2-surface.json
  - docs/surface/v0.2-surface-baseline.json
  - docs/surface-changes/ fragment contract
  - make surface
affects:
  - Makefile
tech-stack:
  added: []
  patterns:
    - "committed-artifact + regenerator + drift-gate triad (15-PATTERNS §5)"
    - "single-owner regeneration for whole-tree artifacts under parallel waves"
key-files:
  created:
    - tools/dump_surface.py
    - docs/surface/v0.2-surface.json
    - docs/surface/v0.2-surface-baseline.json
    - tests/test_surface_drift.py
    - docs/surface-changes/README.md
  modified:
    - Makefile
decisions:
  - "The unqualified path docs/surface/v0.2-surface.json is the LIVE manifest; the frozen phase-start copy carries the qualified -baseline suffix, so a stale read is impossible by naming"
  - "The standing drift gate is documented-drift, not bytes-equality, so it survives eleven waves of surface-changing plans instead of being switched off"
  - "Fragment claims are matched by literal substring at fully-qualified-name granularity with a dotted-module fallback — no Markdown parsing, so the gate cannot rot against a reformat"
metrics:
  duration: ~35m
  completed: 2026-08-04
  tasks: 3
  commits: 3
---

# Phase 15 Plan 01: Surface Baseline and Drift Gate Summary

Captured the phase-start public surface of all 140 `__all__`-bearing modules under
`/src` and `/runtime` as a committed JSON manifest, stood up a documented-drift CI
gate over it, and created the conflict-free per-plan home for the D-15 curated
surface-change log.

## What Was Built

**`tools/dump_surface.py`** — the regenerator, structurally mirroring
`tools/dump_openapi.py`. `REPO_ROOT` from `__file__` (never `cwd`); an exported
`serialize()` the drift test imports rather than restating; a `--check` phase-gate
mode; and a `--report` in-flight mode that writes nothing and always exits 0.
`diff_surfaces(before, after)` returns `added` / `removed` / `reshaped` as sorted
lists of fully-qualified `<dotted.module>.<name>` strings — name granularity, because
15-21's completeness cross-check cannot tell an addition from a removal inside a module
that both gained and lost exports.

The manifest records, per module, the sorted `__all__` plus a per-name `kind`
(`class` / `contract` / `function` / `constant`) and `shape` (signature for callables,
`{field: annotation}` for `CCFContract` subclasses, type name otherwise). Docstrings are
deliberately not recorded: a reworded docstring is not a surface change.

**`docs/surface/v0.2-surface.json`** (live, 140 modules) and
**`docs/surface/v0.2-surface-baseline.json`** (frozen byte-for-byte copy). `main()`
writes only the former; the baseline is written once, here, and never again.

**`tests/test_surface_drift.py`** — five tests: the documented-drift gate (bytes-equality
when nothing moved, otherwise every drifting name must be claimed by a
`docs/surface-changes/15-*.md` fragment), a meta-test that the failure message names
`make surface`, `v0.2-surface.json`, and `docs/surface-changes/`, a non-vacuity test
(≥50 modules, plus `ccf.controlplane.artifacts` / `ccf.boot` / `ccf.products.gates`
present), a fragment-claim rule test on hand-built manifests, and a frozen-baseline
existence test.

**`docs/surface-changes/README.md`** — the fragment contract: `15-NN-<slug>.md` naming,
the seven-field entry shape, the `Public surface` boolean and why it exists, the
`Surface`-token rules split by classification, the four `Change type` values including
`behavior`, and the two-file naming scheme with the single-owner regeneration rule.

**`make surface`** — added beside `openapi:` with its `##` help comment and `.PHONY` entry.

## Key Decisions

**Qualify the frozen file, not the live one.** The obvious alternative would leave every
future contributor and Phase 16 reaching for "the surface manifest", finding
`v0.2-surface.json`, and getting the stale snapshot. Naming it the other way means no tool
and no test is ever re-pointed mid-phase or at phase close.

**Documented-drift, not bytes-equality.** Eleven waves of plans each change the surface
while the live manifest has a single owner at each end of the phase. A gate demanding
bytes-equality throughout would be red for the whole phase and would therefore be
switched off. The gate's known limitation — module-granular and direction-blind, since
fragments are read as an accumulating union — is stated plainly in its docstring, along
with the pairing: `tests/test_surface_completeness.py` (plan 15-21) supplies the exact,
name-level, both-directions guarantee at phase close. Neither is sufficient alone.

**Literal substring matching over fragment parsing.** The `Surface` field is contractually
a single literal token, so a substring match is sufficient and cannot rot against a
Markdown reformat.

## Verification Performed

| Check | Result |
| --- | --- |
| `tools/dump_surface.py --check` | exits 0 |
| `pytest tests/test_surface_drift.py -q` | 5 passed |
| `cmp` live vs. baseline manifest | identical (exit 0) |
| `python -m tools.lints --all` | clean |
| `mypy` | Success, 161 source files |
| `grep "^surface:" Makefile` | line 177; `surface` in `.PHONY` |
| `diff_surfaces` on two hand-built dicts | returns fully-qualified names under `added`/`removed`/`reshaped` |

**Documented-drift proven end to end, not asserted.** Removing `boot` from
`src/ccf/boot.py`'s `__all__` made the gate fail naming `ccf.boot.boot`, `--check` exit 1,
and `--report` still exit 0 listing the removal. Adding
`docs/surface-changes/15-99-tmp.md` naming that same symbol made the gate pass again.
Both temporaries were then reverted and the tree reverified clean — this is what proves
the gate is documented-drift rather than a merely weakened bytes check.

`docs/SURFACE-CHANGES.md` confirmed absent — assembly is 15-21's job.

## Deviations from Plan

**1. [Rule 3 - Blocking] Symlinked `.venv` into the worktree**

- **Found during:** Task 1 verification
- **Issue:** every verify command in the plan invokes `.venv/bin/python`, and the git
  worktree has no `.venv` — the venv lives in the main checkout and is gitignored.
- **Fix:** `ln -s /home/parkave/ccf_code/.venv <worktree>/.venv`. Confirmed with
  `ccf.__file__` / `ccf_runtime.__file__` that `PYTHONPATH=src:runtime` still resolves the
  **worktree's** sources, not the main checkout's editable install, so every verification
  above ran against the code under review.
- **Files modified:** none tracked (the symlink is gitignored and not committed)
- **Commit:** n/a

Otherwise the plan executed exactly as written.

## Notes for Future Plans

- **Do not run `make surface` and do not list either manifest in `files_modified`.** Run
  `tools/dump_surface.py --report` and write a `docs/surface-changes/15-NN-<slug>.md`
  fragment instead. The live manifest's next and last writer in this phase is 15-21.
- The drift gate is satisfied by naming the drifting **module** as well as the exact name,
  so a fragment cannot accidentally fail to claim its own change — but 15-21's cross-check
  requires the fully-qualified name and a `Change type` matching the diff direction.
  Write fragments to the stricter contract from the start.
- `--report` compares against the *committed* manifest, so mid-phase it accumulates the
  changes of every merged plan, not just the current one.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, or trust-boundary schema. The manifest records
signatures only — no docstrings and no constant values (T-15-01-04, accepted). No package
installs (T-15-01-SC).
