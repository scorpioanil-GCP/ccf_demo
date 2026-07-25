---
phase: 02-phase-d-design
plan: 01
subsystem: design-docs
tags: [design-docs, decision-log, setup]
requires: []
provides:
  - phase-d branch cut from main (tracking origin)
  - docs/DECISIONS.md hygiene-clean (stale blocker + duplicated Gate Log heading removed)
  - fragments/entry-ownership.md — 126-row INV-key ownership table for Wave-5 drafting
affects: [02-02..02-11 (all Phase D plans execute on phase-d), 02-10 synthesis (Appendix A source)]
tech-stack:
  added: []
  patterns: [single-owner + see-also entry assignment derived from pillar mapping]
key-files:
  created:
    - .planning/phases/02-phase-d-design/fragments/entry-ownership.md
  modified:
    - docs/DECISIONS.md
decisions:
  - "Ownership derived from SPEC_INVENTORY.md Pillar-by-Pillar Mapping; dual-pillar entries get one primary owner + See-also, never two owners"
  - "Fragment totals: data-context-a 41, data-context-b 61, agent-types 7, orch-hitl 11, experience-seams 6 = 126"
metrics:
  duration: ~10 min
  completed: 2026-07-25
---

# Phase 2 Plan 01: Phase D Setup Summary

**One-liner:** phase-d branch cut from main, DECISIONS.md gate-log hygiene fix applied, and all 126 inventory entries pre-assigned to exactly one of five Wave-5 drafting fragments via the pillar mapping.

## What was done

### Task 1 — Branch + DECISIONS.md hygiene (commit 19edd64)
- `phase-d` created off `main` (not phase-r HEAD — Pitfall 6), pushed tracking `origin/phase-d`. `git merge-base --is-ancestor origin/main phase-d` passes.
- Removed the stale "BLOCKER (Dave): create the private repo…" line, the duplicated `## Gate Log (D-GATE)` heading, and the "(No gates logged yet.)" placeholder flagged in 01-VERIFICATION.md (lines 63–71 of main's copy). The fix is byte-identical to the fix Dave already approved on phase-r (commit 84ef58a). D-GATE-R entry untouched; diff vs main touches only the hygiene lines (1 insertion, 5 deletions).

### Task 2 — Entry ownership table (commit b0cb640)
- `fragments/entry-ownership.md`: 146 lines, 126 table rows, columns `INV key | Owning fragment | See-also`.
- Verified: 126 unique INV keys; set-equality with `grep -oE 'INV-CH[0-9]+-[0-9]+' docs/SPEC_INVENTORY.md | sort -u` (diff empty); zero duplicate keys in column 1; owning-fragment values are exactly the five named fragments.
- Header states the invariant: every INV key appears in exactly one Owning-fragment cell; synthesis (02-10) builds Appendix A from this table.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Phase 2 planning docs existed only on phase-r**
- **Found during:** Task 1
- **Issue:** All Phase 2 planning artifacts (11 plans, CONTEXT, RESEARCH, PATTERNS, VALIDATION, 01-VERIFICATION.md) were committed on phase-r after the D-GATE merge; cutting phase-d from main would have removed them from the working tree, blocking every subsequent Phase D plan.
- **Fix:** Committed pending working-tree planning files on phase-r first (108e9fd), then after cutting phase-d, carried `.planning/` over via `git checkout phase-r -- .planning` in a dedicated commit (54ba361). No design or code content carried — planning metadata only.
- **Files modified:** `.planning/**`
- **Commits:** 108e9fd (phase-r), 54ba361 (phase-d)

**2. [Note] `grep -c 'D-GATE-R'` acceptance criterion**
- The count went 2 → 1 because the removed stale placeholder line itself contained the string `D-GATE-R`. The actual D-GATE-R gate entry is untouched (verified by diff). The criterion's intent — gate log unaltered — holds; the literal count invariance was impossible while removing the flagged placeholder. Identical to the already-approved phase-r fix.

## Known Stubs

None.

## Threat Flags

None — T-02-01/02/03 mitigations from the plan's threat model all verified (diff-scoped hygiene fix, merge-base ancestry check, 126-key set-equality check).

## Self-Check: PASSED

- `.planning/phases/02-phase-d-design/fragments/entry-ownership.md` — FOUND
- `docs/DECISIONS.md` clean (0 matches for "No gates logged"; single Gate Log heading) — FOUND
- Commits 19edd64, b0cb640, 54ba361 on phase-d — FOUND
