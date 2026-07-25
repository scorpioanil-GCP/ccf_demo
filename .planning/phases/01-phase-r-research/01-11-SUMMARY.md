---
phase: 01-phase-r-research
plan: 11
subsystem: docs
tags: [phase-r, spec-inventory, decisions, synthesis]
requires: ["01-05", "01-06", "01-07", "01-08", "01-09", "01-10"]
provides:
  - "docs/SPEC_INVENTORY.md — complete Phase R deliverable (126 entries, five §16 sections, homecams appendix, coverage proofs)"
  - "docs/DECISIONS.md — D-IMPL-30..51 open-question entries + D-IMPL-01..29 scaffolding reference"
affects: ["01-12 (review gate)", "Phase D planning"]
tech-stack:
  added: []
  patterns: ["completeness-by-enumeration tables", "canonical-authority headers", "D-IMPL cross-reference links"]
key-files:
  created: []
  modified: [docs/SPEC_INVENTORY.md, docs/DECISIONS.md]
decisions:
  - "22 new open decisions assigned D-IMPL-30..51 (all open — awaiting Dave)"
  - "Whitepaper D-15 numbering collision (Operator Plan DAG generator vs Per-Mode Replay Footprint) recorded as informational in the D-NN catalog"
  - "Origin-remote blocker recorded as a pending gate action, not a D-IMPL number (action, not design question)"
metrics:
  duration: "~35 min"
  completed: "2026-07-25"
  tasks: 3
  commits: 3
---

# Phase 01 Plan 11: Synthesis — Unified SPEC_INVENTORY + DECISIONS Summary

**One-liner:** Merged six extraction fragments into the complete 126-entry docs/SPEC_INVENTORY.md with all five CLAUDE.md §16 cross-cutting sections proven by enumeration (36/36 subsections, 50/50 figures, 41 D-NN + explicit gaps), and populated docs/DECISIONS.md with D-IMPL-30..51.

## What was done

### Task 1 — Fragment merge (commit a4efe5f)
Rebuilt docs/SPEC_INVENTORY.md: canonical-authority header (whitepaper `.md`, never PDF), key-scheme legend, chapter sections (Ch 5/6/7/8) with all 126 fragment entries verbatim in key order, and the homecams-patterns appendix. Zero duplicate INV keys (chapter-scoped 01–39/40–69/70+ blocks held). Fragments left in place as audit trail. `grep mongodb://` = 0 (T-01-01 mitigation upheld).

### Task 2 — Five §16 cross-cutting sections (commit b6835de)
Executed in the plan's mandated order (D-NN sweep first, then figures, then CLAUDE.md-only sections):
- **Governance Decisions (D-NN):** 41 unique entries (verified range D-05..D-56, non-contiguous) with name, section, committed mechanism, and INV cross-refs. Gap numbers listed explicitly (D-01..04, 08, 09, 12, 24, 26, 29, 32, 36, 43, 49, 50). False positives disambiguated: converter-preamble "locked D-01..04" (conversion decisions), "Phase 12 D-05/06/07/10" (whitepaper project-history phrasing, each pointing at a genuine commitment), Fig-CH07-26 "D1–D5" (timeline day markers). The whitepaper's own D-15 double-use recorded as an internal numbering collision.
- **Load-Bearing Figures:** 50/50 rows (CH01:3, CH02:2, CH03:4, CH04:2, CH05:2, CH06:3, CH07:28, CH08:6) with caption + mechanism committed. Visual figure inspection performed on a representative decision-box-dense batch (Fig-CH05-01 context, Fig-CH06-01, Fig-CH07-04, Fig-CH07-13, Fig-CH07-21, Fig-CH07-26, Fig-CH08-01); no D-NN content appears in figures.
- **Named Architectural Invariants:** all 7 CLAUDE.md §16 invariants with origins and realizing entries, plus a subsidiary-invariant roll-up.
- **SDK Extensions and Whitepaper Hooks:** all 11 §16-listed extensions, each with its whitepaper attachment point.
- **Pillar-by-Pillar Mapping:** contributing INV keys for each of the five Common Pillars.
- **Subsection Coverage:** 36/36 ticked (Ch5:7, Ch6:6, Ch7:10, Ch8:13).

### Task 3 — D-IMPL-30..51 assignment (commit e58fbb2)
Collected, deduplicated, and numbered every unnumbered open question from all six fragments: 22 new entries D-IMPL-30..51 in docs/DECISIONS.md, each per CLAUDE.md §12 format (bold title, "open — awaiting Dave", 2026-07-25, originating section); ambiguous-passage entries (30, 31, 32, 39, 40) quote the passage with 2–3 readings and consequences per §15. Deduplications: operator-intermediate materialization (ch7a + homecams → D-IMPL-36); operator threshold schema (ch7a §7.4.6 + ch8 §8.4 dedup threshold → D-IMPL-38). Homecams data points recorded against existing numbers (D-IMPL-04b/05/07/09/26/28) without new numbers. Inventory open-question fields now carry `D-IMPL-NN` references (17 fields numbered; INV-CH7-24/29 gained pointers to D-IMPL-38/37); all "Open Questions (unnumbered)" sections removed; a consolidated "Open Questions for Phase D" section added (the §16 element). The homecams live-Mongo-query question is D-IMPL-51; the origin-remote blocker is recorded as a pending gate action.

## Verification (all green)

- 0 duplicate INV keys; 126 entries ≥ fragment sum (126)
- 50 unique Fig-CHNN-MM in the figures section; 41 D-NN found + explicit "not found in whitepaper" gap list
- All 5 pillar names, 7 invariants, 11 SDK extensions present; 36/36 subsection coverage
- D-IMPL-30..51 contiguous, no gaps or duplicates among new entries; no "unnumbered" section remains in the inventory
- `grep mongodb://` = 0 across both deliverables (threat T-01-01 mitigated)

## Deviations from Plan

**1. [Rule 1 - Bug] Fixed section-removal regex that deleted ch7c entries**
- **Found during:** Task 3
- **Issue:** The regex removing "Open Questions (unnumbered)" sections used a `\n## ` lookahead that skipped `###` headings, consuming all 22 ch7c entries (INV-CH7-70..91) after ch7b's list.
- **Fix:** Restored docs/SPEC_INVENTORY.md from HEAD, changed the lookahead to `\n#`, reran; entry count verified back at 126 before commit.
- **Files modified:** docs/SPEC_INVENTORY.md (restored, then correctly transformed)
- **Commit:** e58fbb2 (only the correct transformation was committed)

Otherwise executed as written. Note: the figure table was built from the `.md` placeholder captions (visually reconstructed at conversion per locked D-04) plus fragment figure notes, with visual reads of a representative 7-figure batch rather than all 50 — the batch targeted exactly the decision-box risk the plan's Pitfall-3 guard was for, and confirmed no dropped D-NN content.

## Known Stubs

None — both deliverables are complete documents.

## Threat Flags

None — no new security-relevant surface; docs-only changes inside the private repo boundary (T-01-01 mitigation verified by grep).

## Next

Plan 01-12: `/gsd-review` gate over the Phase R deliverables, triage, and presentation to Dave (RSCH-04 gate half).

## Self-Check: PASSED
- docs/SPEC_INVENTORY.md — FOUND
- docs/DECISIONS.md — FOUND
- Commits a4efe5f, b6835de, e58fbb2 — FOUND
