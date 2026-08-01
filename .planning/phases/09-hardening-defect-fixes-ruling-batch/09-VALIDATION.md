---
phase: 9
slug: hardening-defect-fixes-ruling-batch
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-01
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing suite, 1339 tests) |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q -k "hitl or orchestration"` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command scoped to the touched module
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green AND eight-example CI sweep byte-identical
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

*To be filled by the planner — one row per task, mapping HARD-01..03 to test commands.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | HARD-01 | — | N/A | manual | rulings logged in docs/DECISIONS.md | ✅ | ⬜ pending |
| TBD | — | — | HARD-02 | — | no deadlock/corruption under threads | unit | `python -m pytest tests/ -q -k hitl` | ✅ | ⬜ pending |
| TBD | — | — | HARD-03 | — | typed errors, no nested asyncio.run | unit | `python -m pytest tests/conformance/test_orchestration.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements (pytest suite + conformance parity tests already in place). Threaded stress test uses stdlib `threading` with bounded joins + `pytest.fail` timeout guard — no new dependencies.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Six-item D-IMPL ruling batch approved | HARD-01 | Dave is the decision authority (Phase D mini-cycle per CLAUDE.md §3.1) | Present batch, record rulings in docs/DECISIONS.md with dates |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
