---
phase: 05-phase-i-2-agent-specialization-framework
plan: 07
subsystem: gate
tags: [gate, d-gate-i2, d-17, verification, handoff]
requires: [05-06]
provides:
  - docs/PHASE_I2_GATE.md — verification evidence, 14-row D-17 per-invariant checklist, success-criteria evidence map (AGNT-01/02/03), discretionary implementation notes, I.3/I.4 handoff
  - clean full verification run recorded (568 passed / exactly 2 skips, mypy --strict 63 files, tools.lints exit 0, no allowlist entries this phase)
  - ROADMAP Phase 5 marked 7/7 plans executed
affects: [phase-6, phase-7]
tech-stack:
  added: []
  patterns:
    - gate package follows the I.1 D-17 format exactly (PHASE_I1_GATE.md) so review tooling and Dave read the same shape
key-files:
  created:
    - docs/PHASE_I2_GATE.md
  modified:
    - .planning/ROADMAP.md
decisions:
  - "No new D-IMPL entries: the three discretionary items (NotYetBound-as-exception, exact-match prompt-parameter rule, frozenset grant-set) were Claude's-discretion choices inside ruled space, recorded as implementation notes in the gate doc per the plan"
  - "docs/DECISIONS.md untouched — D-GATE-I.2 is written only after Dave approves, per §3.1 (T-05-21 mitigation)"
metrics:
  duration: ~8 min
  completed: 2026-07-26
  tasks: 2
  tests: 568 passed, 2 skipped
---

# Phase 5 Plan 07: Gate Wave — Verification Sweep, Checklist, Handoff Summary

Phase I.2 is gate-ready: docs/PHASE_I2_GATE.md carries the full verification evidence (all legs green on first run, exactly 2 I.4 CINV-04 skips per D-10), a 14-row D-17 per-invariant checklist where every row names a test file::function or lint rule id, the four ROADMAP success criteria mapped to concrete evidence across AGNT-01/02/03, and the I.3/I.4 handoff notes (Jinja2 SSTI verbatim, NotYetBound transports, ApprovalSink, task execution). Awaiting `/gsd-review --phase "Phase I.2" --all` → triage → Dave → D-GATE-I.2 → merge, per §3.1.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Full verification sweep | 69e2b11 |
| 2 | Per-invariant checklist + evidence map + I.3 handoff | a26f752 |

## What was verified (Task 1)

- `.venv/bin/pytest tests/ -q` → **568 passed, 2 skipped** (exit 0)
- `.venv/bin/pytest tests/invariants/ -rs -q` → 15 passed, 2 skipped — the only skips: `hitl-action-capture` and `workflow-trace-capture`, both phase-tagged **I.4**
- `.venv/bin/mypy --strict src` → clean, 63 source files
- `.venv/bin/python -m tools.lints` → exit 0; `git log -- tools/lints/allowlist.yaml` shows last touch in Phase 4 (ab7b7eb) — **no cinv01c allowlisting this phase**
- Open Question 4 (RESOLVED): `grep -rn "task" src/ccf/replay/record.py` empty — D-11 shipped schema + construction only, no task-execution replay capture invented
- Boundary spot-checks all empty: domain grep (`covenant|banking|kyc`) over `src/ccf/agents` + `src/ccf/skills`; `.render(` over `src/ccf`; harness-import grep over `src/`
- D-04 wave conformance recorded: (a) 05-02/05-03 → (b) 05-04 → (c) 05-05/05-06 → (d) 05-07

Nothing was fixed silently; every leg passed on first run — no blocking findings arose during the sweep.

## What was assembled (Task 2)

- **§2 Per-invariant checklist (14 rows):** CINV-01a/b/c (with the behavioral fixture suite `tests/lints/test_cinv01c_behavioral.py`), CINV-02, CINV-03, CINV-04 skill-set-capture (active; owning test `tests/integration/test_agent_slice.py::test_a_granted_decision_captures_the_grant_set_hash_in_dimension_4`), audit-by-construction for grants, tier-1 non-waivable check, single-writer across the agent boundary (consumption-discipline tests), D-05 version discipline, D-07 grant-set determinism, six-axis version matrix, D-IMPL-19 composition rules, ApprovalSink conformance. Every row names a concrete path.
- **§3 Success-criteria evidence map:** all four ROADMAP Phase 5 criteria mapped (criterion 1 → archetypes/composition/consumption + domain grep; 2 → factory tests + cinv01c fixture; 3 → catalog/grants/dispatch/CINV-04; 4 → six-axis matrix + dimension-4 assertions), all three AGNT ids referenced.
- **§4 Discretionary notes:** NotYetBound-as-exception, exact-match prompt-parameter rule, frozenset grant-set — recorded with rationale, NOT as D-IMPL entries.
- **§5 Handoff:** I.3 — Jinja2 rendering + SSTI surface (RESEARCH threat-register note carried verbatim), MCP/A2A dispatch NotYetBound → transports, prompt-artifact pinning consumed by the adapter context-injection seam, I.1 advisory carry-forwards A-1/A-7. I.4 — ApprovalSink real ApprovalGate (D-09, conformance suite joins unchanged, D-IMPL-21 identity binding), task execution + the two remaining CINV-04 deferrals.
- **ROADMAP:** 05-07 checkbox ticked, Plans count 7/7.
- **DECISIONS.md:** confirmed to contain no D-GATE-I.2 entry (`grep` verified) — approval not yet given.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None introduced by this plan. Carried deferrals (mcp/a2a NotYetBound dispatch, synchronous ApprovalSink) are documented in the gate doc's §5 handoff with receiving phases.

## Threat Flags

None — both plan threats mitigated as specified: T-05-20 (every checklist row names test/lint evidence; command outputs recorded in §1), T-05-21 (no D-GATE-I.2 entry written; explicit AWAITING REVIEW status banner in the gate doc).

## Self-Check: PASSED

- docs/PHASE_I2_GATE.md exists; .planning/ROADMAP.md shows 7/7 and 05-07 ticked
- Commits 69e2b11 and a26f752 present on `phase-i2`
- Gate-doc verify: `grep skill-set-capture`, `grep -i handoff`, AGNT count ≥ 3 — all pass
