---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 01
subsystem: decisions
tags: [decision-log, orchestration, workflow, dependencies, fastapi, httpx]
requires: []
provides:
  - "D-IMPL-60 entry in docs/DECISIONS.md (three OrchestrationProtocol driver legs)"
  - "D-IMPL-61 entry in docs/DECISIONS.md (absent exception ref = propagate-to-terminal)"
  - "phase-i4 branch off main"
  - "fastapi==0.140.0 and httpx==0.28.1 direct pins with stated reasons"
affects:
  - "07-04 (WorkflowDefinition schema — D-IMPL-61 gates its exception-routing validator)"
  - "front-door plans (HTTP API skeleton, CLI — depend on the new pins)"
tech-stack:
  added: [fastapi==0.140.0, httpx==0.28.1]
  patterns: ["stated-reason dependency comments", "new-number-not-amend decision discipline"]
key-files:
  created: []
  modified: [docs/DECISIONS.md, pyproject.toml]
decisions:
  - "D-IMPL-60 (Dave, 2026-07-29): all three v0 SDKs get real OrchestrationProtocol drivers under runtime/ccf_runtime/orchestration/<sdk>/; D-IMPL-17 cross-referenced, not edited"
  - "D-IMPL-61 (Dave, 2026-07-30): option-a propagate-to-terminal — absent per-node exception ref is a defined, audited transition to terminal failed state, recorded in trace"
metrics:
  duration: "~15 min (continuation after decision checkpoint)"
  completed: "2026-07-30"
---

# Phase 7 Plan 01: Phase Opening — Decisions and Pins Summary

**One-liner:** D-IMPL-60 (three orchestrator driver legs) and D-IMPL-61 (absent exception ref = propagate-to-terminal, Dave 2026-07-30) recorded; fastapi/httpx pinned with stated reasons; baseline suite unchanged at 987 passed / 2 skipped.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Create phase-i4 branch and record D-IMPL-60 | af2d09d | docs/DECISIONS.md |
| 2 | D-IMPL-61 ruling (checkpoint:decision, resumed) | 0d8aee3 | docs/DECISIONS.md |
| 3 | Dependency pins with stated reasons | c057f92 | pyproject.toml |

## What Was Done

- **Task 1 (prior session):** Branch `phase-i4` created off `main`. D-IMPL-60 written per the D-IMPL-24 consequence-enumeration template: three driver legs under `runtime/ccf_runtime/orchestration/<sdk>/` (never under `adapters/`, with a bidirectional import ban), three conformance legs in one factory-parametrized suite, CINV-02 carve-out re-examination under the D-IMPL-53 negative-test discipline, and the "one deep, then two" staging explicitly declined. D-IMPL-17 cross-referenced, not edited (verified: `git diff main -- docs/DECISIONS.md` touches no D-IMPL-17 text).
- **Task 2 (checkpoint resolved):** Dave ruled **option-a, propagate-to-terminal** (2026-07-30). Recorded as D-IMPL-61: a node with no per-node exception ref validates; when its exception path fires, the workflow takes a defined, explicit, audited transition to a terminal `failed` state, recorded in the trace as a first-class state transition per CLAUDE.md §8.1. Cites D-13 (the residual this closes) and D-16 (the declined forcing-function reading). The accepted consequence — an author can omit a handler silently — is mitigated by the trace making every propagate-to-terminal transition visible. Plan 07-04's exception-routing validator is unblocked.
- **Task 3:** Added `fastapi==0.140.0` (stated reason: D-IMPL-23 OpenAPI generated from existing `extra=forbid` Pydantic contracts; ADK's `fastapi>=0.133` constraint interaction recorded for the gate) and `httpx==0.28.1` (promoted from transitive-via-mcp to direct because first-party CLI code imports it) to `[project] dependencies`. Updated the now-stale uvicorn comment that claimed httpx was unpinned-transitive. No click/typer added — CLI is stdlib argparse per research. Editable reinstall performed.

## Verification

- `grep -c "D-IMPL-60" docs/DECISIONS.md` → 1; `grep -c "D-IMPL-61" docs/DECISIONS.md` → 1
- `.venv/bin/python -c "import fastapi, httpx; ..."` → `0.140.0 0.28.1`
- Baseline suite (recorded verbatim, per plan instruction not to hardcode counts):
  - **Before pin change:** `987 passed, 2 skipped, 104 warnings in 77.25s`
  - **After pin change + editable reinstall:** `987 passed, 2 skipped, 104 warnings in 78.72s`
  - Identical pass/skip counts, zero failures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale transitive-dependency comment in pyproject.toml**
- **Found during:** Task 3
- **Issue:** The uvicorn stated-reason comment asserted "`httpx` and `starlette` arrive transitively and are not pinned directly" — false once httpx became a direct pin, exactly the class of untrue-comment defect the D-21 mypy-override note documents.
- **Fix:** Comment updated to name starlette alone as transitive and point at the new httpx pin.
- **Files modified:** pyproject.toml
- **Commit:** c057f92

No other deviations — plan executed as written.

## Known Stubs

None.

## Threat Flags

None — both new dependencies were pre-audited in the 07-RESEARCH Package Legitimacy Audit (T-07-01 mitigation applied: exact-version pins, slopcheck [OK], mature PyPI repos).

## Self-Check: PASSED

- docs/DECISIONS.md contains D-IMPL-60 and D-IMPL-61 — FOUND
- pyproject.toml contains fastapi==0.140.0 and httpx==0.28.1 — FOUND
- Commits af2d09d, 0d8aee3, c057f92 present on phase-i4 — FOUND
