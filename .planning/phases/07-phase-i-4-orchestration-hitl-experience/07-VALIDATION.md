---
phase: 7
slug: phase-i-4-orchestration-hitl-experience
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-30
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing suite, 987 tests green as of Phase I.3 close) |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q --no-header -k "<phase-relevant selector>"` |
| **Full suite command** | `python -m pytest tests/ -q && python -m mypy --strict src runtime` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command scoped to the touched module's tests
- **After every plan wave:** Run the full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | ORCH-01, ORCH-02, HITL-01, EXPR-01, EXPR-02, EXPR-03 | — | — | unit/integration | pytest | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test stubs for workflow state machine, HITL primitives, OrchestrationProtocol, CLI, HTTP API, MCP egress extensions (per plan task map)
- [ ] Shared fixtures reuse existing `tests/conftest.py` patterns (factory-constructed agents from fixture artifacts)

*Existing pytest + mypy strict infrastructure covers the framework; Wave 0 adds phase-specific test stubs only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None expected | — | CI-verifiable invariants mandated (audit-by-construction lint, replay checks) | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
