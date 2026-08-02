---
phase: 11
slug: performance-battery
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| (filled by planner) | | | PERF-01..04 | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Verify pytest-benchmark 5.2.3 × installed pytest compatibility (RESEARCH.md assumption A1)
- [ ] Bitrot smoke wiring: perf benchmarks runnable via `--benchmark-disable` in `/tests`

*Existing pytest infrastructure covers standard phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI `perf.yml` opt-in job behavior on GitHub runners | PERF-04 | Requires actual CI runner execution | Trigger workflow_dispatch on a branch; confirm gate compares against runner-class-keyed baseline and missing-baseline is loud report-only |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
