---
phase: 11-performance-battery
verified: 2026-08-01T00:00:00Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Manually dispatch .github/workflows/perf.yml (suite=all) on GitHub, download perf/results artifact, and record the first perf/baselines/gh-ubuntu-24.04.json via the six-step ritual in perf/README.md with Dave's D-IMPL-70 approval logged in docs/DECISIONS.md"
    expected: "A committed, Dave-approved runner-class-keyed baseline file; subsequent dispatches gate against it instead of printing 'NO BASELINE — NOT GATED'"
    why_human: "D-13/D-IMPL-70 forbid auto-recording baselines — the first baseline is a deliberate Dave-approved act requiring a live GitHub Actions dispatch, which cannot be performed programmatically here"
---

# Phase 11: Performance Battery Verification Report

**Phase Goal:** Adopters and CI can measure the hardened SDK reproducibly, with committed baselines and relative regression gates that catch real slowdowns without runner-variance flake
**Verified:** 2026-08-01
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `make perf` runs the micro suite locally and reports p50/p95/p99 reproducibly | ✓ VERIFIED | Makefile `perf` composes perf-micro/scale/xproc/replay, each piping pytest-benchmark JSON through `perf/gate.py`; gate.py computes nearest-rank p50/p95/p99 + median (lines 100–121); 13 micro benchmarks (operators 7 incl. composed-vs-sequential, gates 3, factory 2, run_coroutine_sync 1) — within the ~10–15 target |
| 2 | Fabric scale curves from deterministic, domain-neutral generator built only through L2/factory paths | ✓ VERIFIED | `perf/synth/generator.py` (305 lines, seeded PERF_SEED=20260801); ingest exclusively via `handle.worker.ingest` (perf/conftest.py:111); neutral YAML artifacts under perf/synth/artifacts/; `tests/perf_synth/test_determinism.py` pins shapes + sha256 checksums — 24 gate+determinism tests pass in 40.5s; scale suite runs rungs (500, 1_000) in pedantic mode (documented D-07 flex, rationale in perf/suites/scale/conftest.py) |
| 3 | Cross-process latency + replay-at-scale suites empirically support year-scale replay claim | ✓ VERIFIED | Real-subprocess READY-handshake fixture (perf/suites/crossproc/conftest.py:137) with warm-up round-trips; MCP egress + peering benchmarks; replay ladder parametrized with byte-exact assert via canonical_bytes and fitted-exponent bound b <= 1.0 + EPS written to results JSON (test_replay_scale.py); 100k rung sourced from decision_stream(100_000) with deterministic replication (documented deviation, consistent with plan intent) |
| 4 | Opt-in perf.yml compares against committed runner-class-keyed baselines via thresholds.toml; re-baseline ritual documented | ✓ VERIFIED (mechanism) | perf.yml: workflow_dispatch-only, pinned ubuntu-24.04, CCF_PERF_RUNNER_CLASS=gh-ubuntu-24.04, uploads perf/results; thresholds.toml suite defaults 10/10/25/15% with loosen-only override rule enforced in gate.py; perf/README.md (167 lines) documents six-step Dave-gated ritual, runner-class keys, seed, speed-up policy. First baseline file itself awaits the manual dispatch — see Human Verification |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `perf/gate.py` | Report + gate pipeline, min 80 lines | ✓ VERIFIED | 310 lines; NO BASELINE — NOT GATED notice, D-10 runner-class key with unknown-key report-only, D-12 median-only baseline schema, D-13 no auto-record, exit 0/nonzero contract |
| `perf/thresholds.toml` | Suite defaults + loosen-only overrides | ✓ VERIFIED | micro 0.10 / scale 0.10 / crossproc 0.25 / replay 0.15; loosen-only rule documented and rejected in code (typed load error) |
| `tests/perf_gate/test_gate.py` | Deterministic gate unit tests, min 60 lines | ✓ VERIFIED | 280 lines, passing |
| `perf/synth/generator.py` | Seeded topology + decision stream, min 120 lines | ✓ VERIFIED | 305 lines; hub-heavy topology, decision_stream, importable for Phase 12 |
| `perf/synth/artifacts/ontology.yaml` | Neutral ontology, contains entity_rules | ✓ VERIFIED | Present with sibling controlplane/agent/task/prompt/workflow artifacts |
| `perf/conftest.py` | Session-scoped rung fixtures via boot + ingest | ✓ VERIFIED | 138 lines; fabric_1k/10k/100k fixtures, worker.ingest single-writer path |
| `tests/perf_synth/test_determinism.py` | Pinned shape + checksum per rung | ✓ VERIFIED | 126 lines, passing |
| `perf/suites/micro/*` | Operator/factory/gates/dispatch benchmarks | ✓ VERIFIED | 13 benchmarks; composed-vs-sequential as two named benchmarks (test_composed_ab / test_sequential_ab) |
| `perf/suites/scale/*` | Assembly + projection curves, pedantic | ✓ VERIFIED | benchmark.pedantic with explicit rounds; rungs (500, 1_000) |
| `perf/suites/crossproc/conftest.py` | Subprocess fixture, handshake + warm-up, min 50 lines | ✓ VERIFIED | 238 lines; READY handshake, terminate→wait→kill, no sleep-based spawn |
| `perf/suites/replay/test_replay_scale.py` | Ladder + byte-exact + curve-shape | ✓ VERIFIED | 157 lines; exponent in results JSON for Phase 14 |
| `tests/perf_smoke/test_smoke.py` | Bitrot smoke via --benchmark-disable | ✓ VERIFIED | 82 lines; runs every suite; joins `make test` → `ci-core` → `ci` |
| `.github/workflows/perf.yml` | Opt-in perf CI job | ✓ VERIFIED | 70 lines; workflow_dispatch, per-suite input, artifact upload |
| `perf/README.md` | Ritual + keys + seed + budgets, min 60 lines | ✓ VERIFIED | 167 lines; ritual, runner-class keys, speed-up policy, seed/checksum docs |
| `perf/baselines/` | Baseline directory | ✓ VERIFIED (empty by design) | .gitkeep committed; empty per D-13 — first baseline is a Dave-gated manual act |

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| Makefile perf-* targets | perf/gate.py | gate invoked after each pytest-benchmark run | ✓ WIRED |
| perf/gate.py | perf/thresholds.toml | tomllib load + loosen-only validation | ✓ WIRED |
| perf/synth/generator.py | artifacts/*.yaml | yaml.safe_load | ✓ WIRED |
| perf/conftest.py | ccf.boot / handle.worker.ingest | single-writer ingest loop | ✓ WIRED |
| scale suites | rung fixtures | pedantic mode with fresh-graph setup | ✓ WIRED |
| micro/test_dispatch.py | ccf_runtime.orchestration.common | run_coroutine_sync import | ✓ WIRED |
| crossproc/conftest.py | real server child | READY-handshake subprocess spawn | ✓ WIRED |
| replay suite | generator decision_stream | ladder input (D-30) | ✓ WIRED |
| tests/perf_smoke | perf/suites | subprocess pytest --benchmark-disable | ✓ WIRED |
| perf.yml | Makefile | make perf* with CCF_PERF_RUNNER_CLASS=gh-ubuntu-24.04 | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Gate logic + generator determinism | `pytest tests/perf_gate tests/perf_synth` | 24 passed in 40.5s | ✓ PASS |
| pytest-benchmark pinned in perf extra | pyproject `perf = ["pytest-benchmark==5.2.3"]` | Present | ✓ PASS |
| perf/results gitignored, perf not in ci | .gitignore line 18; `ci: ci-core examples` (no perf) | Confirmed | ✓ PASS |
| Full battery + smoke in always-on CI | Post-merge gate: make lint/typecheck/test green, 1479 passed / 2 skipped (includes perf_smoke) | Confirmed by merged-tree gate | ✓ PASS |
| Full `make perf` ~10-min budget | Not re-run (5+ min); 11-05 SUMMARY records 5m28s exit-0 calibration run | Accepted executor evidence, within D-17 budget | ? SKIP (accepted) |

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
| --- | --- | --- | --- |
| PERF-01 | 11-01, 11-03, 11-05 | ✓ SATISFIED | make perf pipeline + 13 micro benchmarks + p50/p95/p99 reporting + smoke bitrot guard |
| PERF-02 | 11-02, 11-03 | ✓ SATISFIED | Deterministic seeded generator, L2-only ingest, assembly/projection curves over rung ladder |
| PERF-03 | 11-04 | ✓ SATISFIED | Real-subprocess MCP/A2A round-trips + replay ladder with byte-exact and exponent-bound asserts |
| PERF-04 | 11-01, 11-05 | ✓ SATISFIED (mechanism) | Runner-class-keyed baseline schema + relative-median gating + loosen-only thresholds + opt-in perf.yml + documented ritual; first baseline file is the pending human step below |

No orphaned requirements: REQUIREMENTS.md maps exactly PERF-01..04 to Phase 11, all claimed by plans.

### Anti-Patterns Found

None. No TBD/FIXME/XXX in the perf tree or its tests; no absolute-time assertions in benchmarks (gate.py is the sole timing judge); no harness imports; ingest goes only through the single-writer path.

### Human Verification Required

### 1. First gh-ubuntu-24.04 baseline recording

**Test:** Dispatch `.github/workflows/perf.yml` (suite=all) on GitHub, download the `perf/results` artifact, and follow the six-step re-baseline ritual in `perf/README.md` to write `perf/baselines/gh-ubuntu-24.04.json`, with Dave's approval logged in `docs/DECISIONS.md`.
**Expected:** Committed baseline; subsequent dispatches gate at relative-median thresholds instead of report-only "NO BASELINE — NOT GATED".
**Why human:** D-13/D-IMPL-70 make baseline recording a deliberate Dave-approved act, and it requires a live GitHub Actions run.

### Gaps Summary

No gaps. All four roadmap success criteria are structurally verified in the codebase, all plan must-haves hold, all key links are wired, and the perf-specific tests pass independently. The two documented deviations (scale rungs flexed to 500/1000 with generator-constraint rationale; replay 100k rung via deterministic replication of decision_stream) are consistent with plan intent and D-07/D-30. The only outstanding item is the intrinsically manual first-baseline recording, surfaced as a human verification step.

---

_Verified: 2026-08-01_
_Verifier: Claude (gsd-verifier)_
