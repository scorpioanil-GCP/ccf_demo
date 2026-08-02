---
phase: 11
slug: performance-battery
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-01
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) + pytest-benchmark 5.2.3 (new dep) |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/ -x -q` (with `--benchmark-disable` for perf smoke) |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T-11-01-* | 11-01 | 1 | PERF-04 | T-11-01/02/03 | loosen-only thresholds, traversal-safe keys, no baseline writes | unit | `pytest tests/perf_gate -q` | ✅ | ✅ green |
| T-11-02-* | 11-02 | 1 | PERF-02 | T-11-04/05 | safe_load + typed contracts, single-writer ingest | unit | `pytest tests/perf_synth -q` | ✅ | ✅ green |
| T-11-03-* | 11-03 | 2 | PERF-01, PERF-02 | T-11-07/08 | sanity asserts in every benchmark | smoke + opt-in bench | `pytest tests/perf_smoke -q` (micro/scale legs) | ✅ | ✅ green |
| T-11-04-* | 11-04 | 2 | PERF-03 | T-11-09/10/11 | 127.0.0.1-only, process-group teardown, byte-exact before timing | smoke + opt-in bench | `pytest tests/perf_smoke -q` (crossproc/replay legs) | ✅ | ✅ green |
| T-11-05-* | 11-05 | 3 | PERF-04 | T-11-12/13/14 | workflow_dispatch-only, timeouts, smoke knob | smoke | `pytest tests/perf_smoke -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Verify pytest-benchmark 5.2.3 × installed pytest compatibility (RESEARCH.md assumption A1)
- [x] Bitrot smoke wiring: perf benchmarks runnable via `--benchmark-disable` in `/tests`

*Existing pytest infrastructure covers standard phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI `perf.yml` opt-in job behavior on GitHub runners | PERF-04 | Requires actual CI runner execution | Trigger workflow_dispatch on a branch; confirm gate compares against runner-class-keyed baseline and missing-baseline is loud report-only |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-08-01 (post-execution audit)

---

## Validation Audit 2026-08-01

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All four PERF requirements carry automated always-on coverage (28 dedicated tests: 18 gate + 6 determinism + 4 smoke legs) plus opt-in benchmark suites gated by `perf/gate.py`. Full suite at audit time: 1479 passed, 2 skipped. Manual-only: live `perf.yml` dispatch (tracked in 11-HUMAN-UAT.md).
