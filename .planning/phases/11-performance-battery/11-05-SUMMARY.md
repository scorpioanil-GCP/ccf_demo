---
phase: 11-performance-battery
plan: 05
subsystem: perf
tags: [smoke-test, ci-workflow, governance-docs, calibration]
requires: [11-01, 11-02, 11-03, 11-04]
provides:
  - tests/perf_smoke — always-on bitrot smoke running every suite via --benchmark-disable (D-04)
  - .github/workflows/perf.yml — workflow_dispatch-only opt-in perf job (D-IMPL-70)
  - perf/README.md — re-baseline ritual, runner-class keys, thresholds rules, seed/ladder docs (D-14)
  - CCF_PERF_SMOKE=1 smallest-rung knob in the scale and replay suites
affects: [phase-12, phase-14]
tech-stack:
  added: []
  patterns:
    - subprocess-per-suite smoke with hard timeout (T-11-14)
    - env-knob ladder collapse for untimed smoke runs
key-files:
  created:
    - tests/perf_smoke/__init__.py
    - tests/perf_smoke/test_smoke.py
    - .github/workflows/perf.yml
    - perf/README.md
  modified:
    - perf/suites/scale/conftest.py
    - perf/suites/replay/test_replay_scale.py
decisions:
  - "A3 confirmed: pytest-benchmark 5.2.3 --benchmark-disable runs each benchmarked callable exactly once as a plain test (verified via pytest --help); no fallback needed"
  - "CCF_PERF_SMOKE=1 collapses scale ladder to (500,) and replay ladder to (1_000,); rung IDs unchanged so baseline keys are unaffected; curve-fit test skips under smoke"
  - "No calibration changes: full battery measured 5m28s vs the ~10-min D-17 target — rounds/rungs left exactly as waves 2 set them"
metrics:
  duration: "~45 min"
  completed: "2026-08-02"
  tasks: 2
---

# Phase 11 Plan 05: Smoke, CI Workflow & Governance Docs Summary

Always-on bitrot smoke (4 subprocess tests, --benchmark-disable, never
timed), workflow_dispatch-only perf.yml pinned to ubuntu-24.04, and the
D-14 perf/README.md governance doc — with phase-gate evidence: a full
`make perf` calibration run at **5 m 28 s total, exit 0 report-only**.

## Phase-gate evidence: full-battery wall times (D-17/D-25)

Measured `make perf` (runner class `local`, /usr/bin/time, 2026-08-02):

| Suite | D-25 budget | Measured |
| --- | --- | --- |
| micro | ~2 min | 52.4 s |
| scale | ~3 min | 206.8 s (3:26) |
| crossproc | ~2 min | 2.4 s |
| replay | ~3 min | 64.5 s |
| **total** | **~10 min (D-17)** | **5 m 28 s, exit 0** |

Within budget with headroom — **no calibration changes applied**; rounds
and rungs stay exactly as waves 2 set them (recorded in perf/README.md).

## Smoke-test runtime

`pytest tests/perf_smoke -q`: **4 passed in 136 s** (~2.3 min), well
under the 300 s per-suite subprocess timeout. Full always-on
`pytest tests/ -q` with smoke included: **1479 passed, 2 skipped, 4 m 27 s**.
`make lint typecheck` green (perf/ remains outside both scopes, documented
in the README per the 11-01 observation).

## What was built

- **Task 1 (ac9f074):** `tests/perf_smoke/test_smoke.py` — one
  parametrized test per suite, `sys.executable -m pytest
  perf/suites/<suite> -q --benchmark-disable -x` via subprocess with
  `PYTHONPATH=src:runtime:perf:<root>` and `CCF_PERF_SMOKE=1`, hard
  300 s timeout, full stdout/stderr on failure. A3 verified against the
  installed pytest-benchmark 5.2.3. `.github/workflows/perf.yml`:
  workflow_dispatch-only (yaml-asserted single trigger), `suite` choice
  input (all/micro/scale/crossproc/replay) mapped to Makefile targets,
  `runs-on: ubuntu-24.04` pinned (zero `ubuntu-latest` occurrences),
  `CCF_PERF_RUNNER_CLASS: gh-ubuntu-24.04`, explicit `.venv` provisioning
  (Makefile hardcodes it, mirroring live-legs.yml), `timeout-minutes: 30`,
  `upload-artifact@v4` of `perf/results/` with `if: always()`.
- **Task 2 (2067c59):** `perf/README.md` (167 lines) covering all eight
  D-14 items: run surface + measured budgets; runner-class key list
  (`gh-ubuntu-24.04`, `local`, custom charset rule, unknown→report-only);
  the six-step Dave-gated re-baseline ritual with the D-12 schema and the
  never-auto-record rule (D-13); loosen-only thresholds 10/10/25/15
  (D-19..D-22); seed `20260801`, D-07 ladder flexes in force, checksum-pin
  update discipline (D-08); speed-up WARN policy; lint/typecheck scope
  note; Phase 14 PERFORMANCE.md pointer.

## Deviations from Plan

**1. [Rule 3 - Blocking] Worktree had no `.venv`** — symlinked the main
repo's venv (same resolution as 11-01/11-04).

**2. [Planned knob, new code] `CCF_PERF_SMOKE` added to suite code**
- The suites did not previously respect a smoke knob; per the plan's
  explicit instruction one was added: `perf/suites/scale/conftest.py`
  collapses `SCALE_RUNGS` to `(500,)` and
  `perf/suites/replay/test_replay_scale.py` collapses `LADDER` to
  `(1_000,)` under `CCF_PERF_SMOKE=1`, each with a `#:` doc constant.
- **Companion fixes required by --benchmark-disable:** the replay test's
  `benchmark.stats.stats.median` access is now guarded (`stats` is None
  when disabled), and `test_curve_shape` skips when the ladder is
  collapsed or no medians were recorded (it needs all three rungs timed).
- Commit: ac9f074.

**3. [Minor] perf.yml comment reworded** — the acceptance gate requires
zero `ubuntu-latest` occurrences; the explanatory comment now says
"never a floating image tag" instead of naming it.

## First gh-ubuntu-24.04 baseline: manual phase-gate step

`perf/baselines/` remains empty by design. The first
`gh-ubuntu-24.04` baseline awaits a manual `perf.yml` dispatch, results
review, and Dave's approval per D-IMPL-70 — a post-review human ritual
(documented step-by-step in perf/README.md), not code in this phase.

## Verification

- `pytest tests/perf_smoke -q`: 4 passed (136 s); full `pytest tests/ -q`
  1479 passed, 2 skipped
- perf.yml: yaml.safe_load asserts `workflow_dispatch` is the ONLY
  trigger; grep gates — workflow_dispatch 1, ubuntu-24.04 4,
  ubuntu-latest 0, gh-ubuntu-24.04 2, upload-artifact 1
- perf/README.md: 167 lines (min 60); re-baseline 3 hits,
  gh-ubuntu-24.04 1, D-IMPL-70 3, literal seed 20260801 present
- `make perf` exit 0 report-only, 5 m 28 s; `make lint typecheck` green

## Known Stubs

None.

## Threat Flags

None — T-11-12 (workflow_dispatch-only, yaml-asserted), T-11-13 (ritual
documented as manual + Dave-approved; gate.py has no baseline write
path), T-11-14 (300 s subprocess timeouts + smallest-rung smoke knob)
all implemented per the plan's threat register.

## Commits

| Task | Commit | Description |
| --- | --- | --- |
| 1 | ac9f074 | smoke test + CCF_PERF_SMOKE knob + perf.yml |
| 2 | 2067c59 | perf/README.md + full-battery calibration evidence |

## Self-Check: PASSED

- tests/perf_smoke/{__init__.py,test_smoke.py}, .github/workflows/perf.yml,
  perf/README.md all exist
- Commits ac9f074 and 2067c59 present in log
- Smoke 4/4 green; full suite 1479 passed; battery exit 0 within budget
