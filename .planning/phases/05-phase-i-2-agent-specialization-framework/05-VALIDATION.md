---
phase: 5
slug: phase-i-2-agent-specialization-framework
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-26
revised: 2026-07-26
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + hypothesis 6.161.5 + mypy `--strict` (pinned since Phase I.1) |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`, testpaths=tests) |
| **Quick run command** | `.venv/bin/pytest tests/agents tests/skills -x -q` (or targeted file) |
| **Full suite command** | `.venv/bin/pytest tests/ -q && .venv/bin/python -m tools.lints && .venv/bin/mypy --strict src` |
| **Estimated runtime** | ~60–90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/pytest tests/ -x -q`
- **After every plan wave:** Run the full suite command (pytest + tools.lints + mypy --strict)
- **Before `/gsd:verify-work`:** Full suite must be green with exactly 2 invariant skips (D-10)
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-T1 | 05-01 | 1 | AGNT-02 | T-05-02 | six-axis schema, extra=forbid, no silent defaults | unit | `.venv/bin/pytest tests/agents/test_definitions.py -x -q` | ❌ created in task (TDD) | ⬜ pending |
| 05-01-T2 | 05-01 | 1 | AGNT-02 | T-05-03 | parse-only Jinja2 validation, no render surface | unit | `.venv/bin/pytest tests/agents/test_prompts.py -x -q && ! grep -rn "\.render(" src/ccf/agents/` | ❌ created in task (TDD) | ⬜ pending |
| 05-01-T3 | 05-01 | 1 | AGNT-02 | T-05-01, T-05-04 | D-05 hash-verified bump, audited refusals; dimension-4 (incl. delegation_chain) done once | unit + full suite | `.venv/bin/pytest tests/controlplane/test_hash_verified_bump.py tests/ -x -q && .venv/bin/mypy --strict src && .venv/bin/python -m tools.lints` | ❌ created in task (TDD) | ⬜ pending |
| 05-02-T1 | 05-02 | 2 | AGNT-01 | — | Agent has no loop, no construction token | unit | `.venv/bin/pytest tests/agents/ -x -q && .venv/bin/mypy --strict src` | ❌ created in task (TDD) | ⬜ pending |
| 05-02-T2 | 05-02 | 2 | AGNT-02 | T-05-05..07 | factory-only construction; bad bindings fail | unit + lint | `.venv/bin/pytest tests/agents/test_factory.py -x -q && .venv/bin/python -m tools.lints` | ❌ created in task (TDD) | ⬜ pending |
| 05-02-T3 | 05-02 | 2 | AGNT-01, AGNT-02 | — | harness double in /tests only; dimension-4 slice assertions | integration | `.venv/bin/pytest tests/integration/test_agent_slice.py tests/agents/ -x -q && .venv/bin/pytest tests/ -q` | ❌ created in task (TDD) | ⬜ pending |
| 05-03-T1 | 05-03 | 3 | AGNT-01 | — | six archetypes, no domain values in /src | unit | `.venv/bin/pytest tests/agents/test_archetypes.py -x -q && .venv/bin/mypy --strict src` | ❌ created in task (TDD) | ⬜ pending |
| 05-03-T2 | 05-03 | 3 | AGNT-01 | — | D-IMPL-19 dedupe/order-warn/error composition | unit | `.venv/bin/pytest tests/agents/test_composition.py tests/agents/test_factory.py -x -q` | ❌ created in task (TDD) | ⬜ pending |
| 05-03-T3 | 05-03 | 3 | AGNT-01 | — | no Agent path to L1–L5 (negative) | unit (negative) | `.venv/bin/pytest tests/agents/test_consumption_discipline.py -x -q && .venv/bin/pytest tests/ -q && .venv/bin/python -m tools.lints` | ❌ created in task (TDD) | ⬜ pending |
| 05-04-T1 | 05-04 | 4 | AGNT-02 | — | TaskFactory construction only, no execution (D-11) | unit | `.venv/bin/pytest tests/agents/test_factory.py -x -q && .venv/bin/python -m tools.lints` | ❌ created in task (TDD) | ⬜ pending |
| 05-04-T2 | 05-04 | 4 | AGNT-02 | — | CINV-01c fires on factory bypass (behavioral, D-12) | lint (behavioral) | `.venv/bin/pytest tests/lints/test_cinv01c_behavioral.py -x -q && .venv/bin/python -m tools.lints` | ❌ created in task (TDD) | ⬜ pending |
| 05-04-T3 | 05-04 | 4 | AGNT-02 | — | axis-change ⇒ new version; JSON Schema export | unit | `.venv/bin/pytest tests/agents/test_schema_export.py tests/agents/test_factory.py -x -q && .venv/bin/pytest tests/ -q` | ❌ created in task (TDD) | ⬜ pending |
| 05-05-T1 | 05-05 | 5 | AGNT-03 | T-05-14, T-05-18 | 4-type catalog via versioned Control Plane path; opaque requirement ids | unit | `.venv/bin/pytest tests/skills/test_catalog.py tests/agents/test_schema_export.py -x -q && .venv/bin/mypy --strict src && .venv/bin/python -m tools.lints` | ❌ created in task (TDD) | ⬜ pending |
| 05-06-T1 | 05-06 | 6 | AGNT-03 | T-05-15..17, T-05-19 | non-waivable tier-1; audited state machine behind ApprovalSink; D-07 hash | unit + conformance | `.venv/bin/pytest tests/skills/test_grants.py tests/conformance/test_approval_sink.py -x -q` | ❌ created in task (TDD) | ⬜ pending |
| 05-06-T2 | 05-06 | 6 | AGNT-03 | T-05-16, T-05-18 | dispatch governed by grants; NotYetBound for mcp/a2a; CINV-04 active (2 skips) | integration + invariant | `.venv/bin/pytest tests/skills tests/integration/test_agent_slice.py -x -q && .venv/bin/pytest tests/invariants/test_replay_by_construction.py -rs -x && .venv/bin/pytest tests/ -q \| tail -1` | ✅ invariant registry exists (check skipped) | ⬜ pending |
| 05-07-T1 | 05-07 | 7 | AGNT-01..03 | T-05-20 | full battery + boundary spot-check greps recorded | full suite | `.venv/bin/pytest tests/ -q && .venv/bin/mypy --strict src && .venv/bin/python -m tools.lints && test -f docs/PHASE_I2_GATE.md` | ✅ battery exists | ⬜ pending |
| 05-07-T2 | 05-07 | 7 | AGNT-01..03 | T-05-20, T-05-21 | evidence-mapped gate checklist; no premature D-GATE | doc check | `grep -q "skill-set-capture" docs/PHASE_I2_GATE.md && grep -qi "handoff" docs/PHASE_I2_GATE.md` | ❌ created in task | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers phase test scaffolding (pytest + CI + lints + invariant check registry from I.1). All new test modules are created inside their TDD tasks (test-first), so no separate Wave 0 stub plan is required; the only pre-existing file mutated is `tests/invariants/test_replay_by_construction.py` (CINV-04 flip, 05-06-T2), which already exists.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none — TDD tasks create their own test files)
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner sign-off 2026-07-26 (revision per checker feedback)
