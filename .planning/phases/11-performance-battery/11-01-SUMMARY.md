---
phase: 11-performance-battery
plan: 01
subsystem: perf-infra
tags: [pytest-benchmark, gating, thresholds, makefile]
requires: []
provides:
  - perf/gate.py report+gate pipeline (D-02/D-03, D-IMPL-70 repo-owned)
  - perf/thresholds.toml suite defaults + loosen-only override schema
  - Makefile perf/perf-micro/perf-scale/perf-xproc/perf-replay targets
  - pytest-benchmark==5.2.3 perf extra (A1 resolved)
  - perf/baselines/ directory (empty; baselines are Dave-gated)
affects: [11-02, 11-03, 11-04, 11-05]
tech-stack:
  added: [pytest-benchmark==5.2.3]
  patterns: [stdlib-only gate script, pure-function gate logic tested on fixtures]
key-files:
  created:
    - perf/gate.py
    - perf/thresholds.toml
    - perf/baselines/.gitkeep
    - tests/perf_gate/__init__.py
    - tests/perf_gate/test_gate.py
  modified:
    - pyproject.toml
    - .gitignore
    - Makefile
decisions:
  - "Speed-ups beyond threshold WARN, never fail (RESEARCH Open Question 1 recommendation, documented in gate.py docstring)"
  - "Percentiles via nearest-rank on sorted raw timings; median via statistics.median matching pytest-benchmark's reported number (D-03)"
  - "Runner-class key charset-restricted to [A-Za-z0-9._-]+ before path join (T-11-02)"
metrics:
  duration: ~25 min
  completed: 2026-08-01
  tasks: 2
  tests-added: 18
---

# Phase 11 Plan 01: Perf Battery Foundation Summary

One-liner: pytest-benchmark 5.2.3 harness + stdlib-only `perf/gate.py`
report+gate pipeline with loosen-only thresholds.toml and 18 deterministic
unit tests, wired into `make perf-*` targets that never join `ci`.

## What was built

- **Task 1 (ff1f71b):** `perf = ["pytest-benchmark==5.2.3"]` extra folded
  into `dev`; `perf/results/` gitignored; Makefile `perf`,
  `perf-{micro,scale,xproc,replay}` targets with `ENV_PERF` (PYTHONPATH
  includes `perf`, `CCF_PERF_RUNNER_CLASS ?= local`), each suite target
  running pytest-benchmark then `perf/gate.py`. `make -n ci` contains no
  perf token; `ci` target untouched.
- **Task 2 (a456054 RED, d371293 GREEN):** `perf/gate.py` (pure functions
  `compute_percentiles`, `resolve_threshold`, `sanitize_runner_class`,
  `evaluate` + thin `main()`), `perf/thresholds.toml` (defaults
  0.10/0.10/0.25/0.15 for micro/scale/crossproc/replay, D-19..D-21;
  loosen-only override schema, D-22), `perf/baselines/.gitkeep`, and
  `tests/perf_gate/test_gate.py` (18 tests, all deterministic, in always-on
  CI collection via existing `testpaths = ["tests"]`).

## A1 resolution evidence (RESEARCH Pitfall 2)

pytest-benchmark 5.2.3 is compatible with the project's `pytest==9.1.1` pin.
A throwaway trivial benchmark in the scratchpad ran green under pytest 9.1.1
with `--benchmark-json`; the export contained `benchmarks[0].stats.data` with
**187,125 raw timings** (rounds = 187,125). No pin adjustment needed.

## Lint/typecheck scope observation for perf/ (for plan 11-05 docs)

- `tools.lints` `LINTED_TREES = ("src", "runtime", "examples")` — **`perf/`
  is NOT in lint scope** (and `tests/` never was). Not extended in this plan
  per the plan's explicit instruction.
- `[tool.mypy] files = ["src", "runtime"]` — **`perf/gate.py` and
  `tests/perf_gate/` are NOT type-checked** by `make typecheck`.
- `make lint typecheck` and the full suite (1469 passed, 2 skipped) stay
  green.

## Deviations from Plan

**1. [Rule 3 - Blocking] Worktree has no `.venv`**
- **Found during:** Task 1 install step
- **Issue:** `.venv/bin/pip` absent in the worktree (venvs are gitignored)
- **Fix:** symlinked the main repo's `.venv` into the worktree and installed
  `pytest-benchmark==5.2.3` into it directly (additive; no editable-install
  repoint). Also changed the `.gitignore` `.venv/` entry to `.venv` so the
  symlink form is ignored too.
- **Commit:** ff1f71b

**2. [Rule 1 - Bug] Test loader dataclass AttributeError**
- **Found during:** Task 2 GREEN
- **Issue:** loading `gate.py` via `spec_from_file_location` without
  registering the module in `sys.modules` broke `@dataclass` resolution
- **Fix:** register module in `sys.modules` before `exec_module`
- **Commit:** d371293

## Expected follow-ups (not defects)

- `make perf-*` targets will fail until `perf/suites/<suite>/` directories
  exist (wave 2 plans) — anticipated by the plan.
- `perf/baselines/` is empty by design; the first baseline is recorded via a
  `perf.yml` dispatch + Dave approval (D-IMPL-70).

## Known Stubs

None — no placeholder values or unwired data paths.

## Threat Flags

None — all new surface is covered by the plan's threat model (T-11-01/02/03
mitigations implemented; T-11-SC accepted per RESEARCH audit).

## Commits

| Commit | Type | Description |
| --- | --- | --- |
| ff1f71b | chore | perf extra, Makefile targets, gitignore |
| a456054 | test | failing deterministic gate tests (RED) |
| d371293 | feat | gate.py + thresholds.toml + .gitkeep (GREEN) |

## TDD Gate Compliance

RED (a456054, tests fail on missing gate.py) → GREEN (d371293, 18/18 pass).
No refactor commit needed.

## Self-Check: PASSED

- perf/gate.py, perf/thresholds.toml, perf/baselines/.gitkeep,
  tests/perf_gate/test_gate.py all exist
- Commits ff1f71b, a456054, d371293 present in log
- `pytest tests/perf_gate -q`: 18 passed; full suite 1469 passed
- `make -n perf` shows 4 gate.py invocations; `make -n ci` has no perf token
