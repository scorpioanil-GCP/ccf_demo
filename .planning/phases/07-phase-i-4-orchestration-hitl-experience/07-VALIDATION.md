---
phase: 7
slug: phase-i-4-orchestration-hitl-experience
status: complete
nyquist_compliant: true
wave_0_complete: true
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
| workflow-engine | 07-01..06 | 1–5 | ORCH-01 | — | state-machine suspend/resume, replay trace capture | unit/integration | `pytest tests/workflow` | ✅ | ✅ green |
| orchestration-protocol | 07-12/13 | 8–9 | ORCH-02 | — | 3-driver conformance (LangGraph/ADK/Claude), engine refusal | integration | `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance/test_orchestration.py tests/conformance/test_harness_portability.py` | ✅ | ✅ green |
| hitl-primitives | 07-07/08, 07-15..20 | 5–7 | HITL-01 | — | audit-by-construction, identity binding, signed-binding authority, replay e2e | unit/integration | `pytest tests/hitl` (12 files, incl. test_replay_e2e.py) | ✅ | ✅ green |
| mcp-egress | 07-09 | 6 | EXPR-01 | — | HITL transport doors, principal binding refusals | integration | `pytest tests/hitl/test_transport.py tests/http_api/test_hitl_door_identity.py` | ✅ | ✅ green |
| cli | 07-11 | 7 | EXPR-02 | — | ccf CLI verbs incl. hitl submit, skill import | unit | `pytest tests/cli` | ✅ | ✅ green |
| http-api | 07-10, 07-16 | 7 | EXPR-03 | — | 8 ruled nouns, OpenAPI 3.1.0, BearerAuth, typed refusals | integration | `pytest tests/http_api` | ✅ | ✅ green |

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

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** retroactive audit passed (validate-phase, 2026-07-31)

## Validation Audit 2026-07-31

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 (all 6 requirements already COVERED by green tests) |
| Escalated | 0 |

Retroactive audit: the draft per-task map was never populated during execution; all six
requirements (ORCH-01/02, HITL-01, EXPR-01/02/03) were cross-referenced to existing suites
and executed fresh — 177 passed (tests/hitl, tests/cli, tests/http_api) + 330 passed
(tests/workflow, tests/conformance, tests/replay under CCF_REQUIRE_HARNESSES=1).
