---
phase: 4
slug: phase-i-1-fabric-core
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-25
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + hypothesis 6.x (property tests) + testcontainers 4.x (Postgres conformance) |
| **Config file** | none — Wave 0 installs (`pyproject.toml` with pytest config) |
| **Quick run command** | `pytest tests/ -x -q -m "not conformance"` |
| **Full suite command** | `pytest tests/ -q && python -m ccf_lint --all` (CINV lints) |
| **Estimated runtime** | ~60 seconds quick / ~300 seconds full (containers) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q -m "not conformance"`
- **After every plan wave:** Run full suite including Postgres conformance and CINV lints
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | FABR-01..09, CINV-01..04 | — | — | unit/property/conformance/lint | — | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — package + pytest + mypy config, venv bootstrap (PEP-668 host)
- [ ] `tests/conftest.py` — shared fixtures (SQLite graph store, config artifacts, canonical-serialization helpers)
- [ ] `tests/test_smoke.py` — import/smoke stubs for the fabric package
- [ ] CINV lint harness scaffold (`ccf_lint` runnable, not-yet-applicable checks explicitly marked)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| D-GATE review presentation to Dave | — | Approval authority is Dave's (CLAUDE.md §3.1) | Present deliverables + review report + triage |

*All other phase behaviors have automated verification per FEASIBILITY.md §11.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
