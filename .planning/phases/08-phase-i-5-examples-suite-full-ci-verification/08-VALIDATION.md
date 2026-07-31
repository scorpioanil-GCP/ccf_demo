---
phase: 8
slug: phase-i-5-examples-suite-full-ci-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-30
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — 1315 tests green at Phase 7 close) |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=120 -k "<touched area>"` |
| **Full suite command** | `python -m pytest tests/ -q && python -m mypy --strict src runtime` |
| **Estimated runtime** | ~90 seconds full suite |

---

## Sampling Rate

- **After every task commit:** Run quick command scoped to touched area
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green, all 8 examples run end-to-end via their documented commands
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

*(Filled by planner — one row per task; example commands (`make example-NN` or documented single command per example) count as automated verification.)*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| — | — | — | EXAM-01..09 | — | — | e2e/unit | — | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `Makefile` (or documented per-example run commands) — examples runner targets
- [ ] `tests/examples/` harness — CI-invocable end-to-end runs of examples 00–07
- [ ] CI `examples` job in `.github/workflows/ci.yml`

*Existing pytest infrastructure covers unit/invariant requirements; examples e2e harness is net-new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Ollama harness legs on GH Actions | EXAM (03 live legs) | Local model availability differs from runners; opt-in workflow | Run opt-in workflow / local `make example-03-live` with Ollama serving |
| GH Actions green evidence | EXAM-09 | Push authorization gated (flagged for Dave) | Push branch once authorized; observe Actions run |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
