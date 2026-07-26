# Phase I.2 — Agent Specialization Framework: Gate Package

**Phase:** 5 (Phase I.2 — Agent Specialization Framework) · **Branch:** `phase-i2` · **Assembled:** 2026-07-26
**Protocol:** CLAUDE.md §3.1 (self-review → triage → present to Dave → `D-GATE-I.2` → merge)
**Gate bar:** D-17 pattern carried from I.1 — the per-invariant checklist green, each named
invariant mapping to a *named passing* test or lint. No numeric coverage gate.

> **Status: AWAITING REVIEW.** This package is the plan 05-07 deliverable. The
> `/gsd-review --phase "Phase I.2" --all` run, triage, Dave's approval, the `D-GATE-I.2`
> entry, and the merge of `phase-i2` to `main` all happen through the §3.1 protocol
> *after* this document — none of them is performed here, and `docs/DECISIONS.md`
> deliberately contains no `D-GATE-I.2` entry yet.

---

## 1. Verification Evidence — Execution Record

All legs executed on `phase-i2` in the project `.venv` (Python 3.12), 2026-07-26.

| Leg | Command | Result |
|-----|---------|--------|
| Full suite | `.venv/bin/pytest tests/ -q` | **568 passed, 2 skipped** (exit 0) |
| Invariant registry, skip detail | `.venv/bin/pytest tests/invariants/ -rs -q` | **15 passed, 2 skipped** — the only skips in the whole suite, both CINV-04 deferrals (below) |
| Strict typing | `.venv/bin/mypy --strict src` | **Success: no issues found in 63 source files** |
| Invariant lints (CINV-01a/b/c, CINV-02, CINV-03) | `.venv/bin/python -m tools.lints` | **exit 0, zero findings** |
| Allowlist discipline | `git log --oneline -- tools/lints/allowlist.yaml` | last touched `ab7b7eb` (Phase 4, plan 04-02) — **no cinv01c allowlisting occurred this phase** |

**The 2 skips are deliberate and load-bearing (D-10).** I.1 ended with 3 phase-tagged
CINV-04 skips; I.2 activated `skill-set-capture`, leaving exactly the two I.4 deferrals:

| Skipped check | Activating phase | Reason string emitted |
|---------------|------------------|------------------------|
| `hitl-action-capture` | **Phase I.4** | every HITL action lands in replay dimension 2 by construction (CLAUDE.md §8.2) |
| `workflow-trace-capture` | **Phase I.4** | every workflow execution trace lands in replay dimensions 4 and 5 by construction (CLAUDE.md §8.1) |

### RESEARCH Open Question 4 verification (RESOLVED as ruled)

D-11 ships the task **schema + construction only** — no task-execution replay capture is
invented in I.2. Verified two ways:

- `grep -rn "task" src/ccf/replay/record.py` → **empty** (no TaskDefinition or
  task-execution capture field exists in the replay record).
- `tests/agents/test_factory.py::test_no_replay_capture_is_invented_for_tasks` asserts it
  behaviorally, so the boundary cannot regress silently.

### Fixture-only boundary spot-checks (all must be, and are, empty)

| Spot check | Command | Result |
|------------|---------|--------|
| No domain values in the agent/skill mechanism | `grep -rin "covenant\|banking\|kyc" src/ccf/agents src/ccf/skills` | **empty** (exit 1) |
| No template rendering in I.2 (D-13: parse-only) | `grep -rn "\.render(" src/ccf` | **empty** (exit 1) |
| No harness imports anywhere in `/src` | `grep -rn "import adk\|langgraph\|claude_agent" src/` | **empty** (exit 1) — corroborating the CINV-02 lint's zero findings |

Every agent instance, prompt, threshold, half-life value, skill grant, and policy scope in
this phase lives under `tests/fixtures/banking/` (agents/, prompts/, tasks/, skills/) —
never in `/src`. Nothing was fixed silently to produce these results; every leg passed on
first run.
