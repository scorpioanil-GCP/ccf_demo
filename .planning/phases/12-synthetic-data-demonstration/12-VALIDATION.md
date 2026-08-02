---
phase: 12
slug: synthetic-data-demonstration
status: final
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-01
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, 1479 tests) |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/examples/ -x -q` |
| **Full suite command** | `make examples && python -m pytest -q` |
| **Estimated runtime** | ~330 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/examples/ -x -q`
- **After every plan wave:** Run `make examples && python -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01/T1-T2 | 12-01 | 1 | DEMO-01 | T-12-01 | deterministic generation (pinned checksums + ring signature) | unit | `PYTHONPATH=src:runtime python -m pytest tests/examples/test_demo_generator.py -x -q` | ✅ | ✅ green |
| 12-02/T1-T3 | 12-02 | 2 | DEMO-02 | T-12-04 | end-to-end example run + executed baseline contrast (0 raw / 1 governed, byte-compared narration) | integration | `make example-08` | ✅ | ✅ green |
| 12-03/T1-T2 | 12-03 | 3 | DEMO-03 | T-12-07 | CI single-command run, deterministic (nine-example aggregate; walkthrough includes resolve) | integration | `make examples` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Test stubs for the new example (checksum pin, end-to-end run) — `tests/examples/test_demo_generator.py` (12-01) + `make example-08` byte-compare (12-02)
- [x] Existing pytest infrastructure covers framework needs (no installs)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Walkthrough doc reads correctly / narration quality | DEMO-03 | Prose quality is human judgment | Read the walkthrough doc end-to-end; verify literal-includes resolve |

---

## Validation Audit 2026-08-02

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Post-fix re-audit after review fixes WR-01..WR-05 (commits 1df8b69..d281efa): DEMO-01 re-verified via `pytest tests/examples/` (4 passed, WR-05 pins regenerated), DEMO-02 via `make example-08` (exit 0, byte-identical consecutive runs), DEMO-03 unchanged (fixes touched only example-08 files). `nyquist_compliant: true` stands. One manual-only row (walkthrough prose quality) tracked in 12-HUMAN-UAT.md.
