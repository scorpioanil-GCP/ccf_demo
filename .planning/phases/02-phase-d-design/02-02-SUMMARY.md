---
phase: 02-phase-d-design
plan: 02
subsystem: decision-log
tags: [decision-log, decision-marathon]
requires:
  - phase-d branch + DECISIONS.md hygiene (02-01)
provides:
  - 16 batch-1 rulings RESOLVED in docs/DECISIONS.md (D-IMPL-01,02,03,04,05,07,08,09,33,34,35,37,38,39,40,41)
  - fragments/marathon-batch-1.md — 16 recommendation-first briefs (Wave-5 design input)
  - Five Phase I gate items resolved (D-IMPL-01..05); language target fixed at Python 3.12+
affects: [all downstream signature-level design (Wave 5), 02-03..02-11, Phase I gate list]
tech-stack:
  added: []
  patterns: [recommendation-first ruling sessions (D-02); mechanism-declares-schema / Control-Plane-supplies-values (D-IMPL-38/39/40 shared shape)]
key-files:
  created:
    - .planning/phases/02-phase-d-design/fragments/marathon-batch-1.md
  modified:
    - docs/DECISIONS.md
decisions:
  - "D-IMPL-01: Python 3.12+ sole v0 target, Pydantic v2 extra=forbid, Protocol seams"
  - "D-IMPL-02: GraphStore Protocol + Postgres + SQLite-for-dev references"
  - "D-IMPL-03: SimilarityIndex Protocol + sqlite-vec reference (Chroma if budget)"
  - "D-IMPL-04: two packages ccf + ccf-runtime; async-first runtime, sync fabric core"
  - "D-IMPL-05: multi-tenant first-class; single-tenant = degenerate case"
  - "D-IMPL-07: EmbedderProtocol + API and local-deterministic reference adapters"
  - "D-IMPL-08: Pattern 5 stage Protocols + one opinionated reference pipeline"
  - "D-IMPL-09: LLMClientProtocol; Anthropic reference adapter with Citations"
  - "D-IMPL-33: typed SignalEnvelope minimal-superset, extra=forbid"
  - "D-IMPL-34: Protocol requires six invariant semantics; layout backend-internal; reader/writer split"
  - "D-IMPL-35: EntityResolutionStrategy Protocol + deterministic reference strategy; attributes are user config"
  - "D-IMPL-37: explicit boot-time register() API, fail-fast duplicates"
  - "D-IMPL-38: typed versioned OperatorParameterSet; no silent defaults"
  - "D-IMPL-39: MAX_TTL per product class in Control Plane, required, no default"
  - "D-IMPL-40: threat scale + D_c thresholds are Control Plane config; SDK ships routing only"
  - "D-IMPL-41: four-layer single-writer enforcement stack (Protocol split, DI-at-boot, mypy+import lint CI gate, boot-token backstop)"
metrics:
  duration: ~1 session (briefs + interactive ruling session + logging)
  completed: 2026-07-25
---

# Phase 2 Plan 02: Decision Marathon Batch 1 Summary

**One-liner:** All 16 fabric-and-runtime-fundamentals decisions (D-IMPL-01..09 gating set plus 33..41 ambiguity entries) ruled by Dave AS RECOMMENDED and logged RESOLVED in docs/DECISIONS.md — zero provisionals, zero deferrals.

## What was done

### Task 1 — Recommendation briefs (commit a79c809)
- `fragments/marathon-batch-1.md`: 16 recommendation-first briefs per locked D-02, D-IMPL-01 first (it gates 02/03/07/09/41 and all signature-level design). Rationales cite INV-CHx-NN entries and whitepaper sections; every alternative carries consequences; Homecams observations phrased only as data points, never defaults.

### Task 2 — Interactive ruling session + logging (commit 280ba23)
- Session held with Dave via the orchestrator checkpoint. Every decision ruled AS RECOMMENDED (Approver: Dave, 2026-07-25). No deferrals — zero PROVISIONAL entries in this batch.
- D-IMPL-01..09 logged as status-note bullets in the existing status-notes list (D-IMPL-10 precedent format); D-IMPL-33..41 logged by appending RESOLVED tokens to their existing entries with original ambiguous-passage text retained (D-IMPL-51 precedent).
- Ruling-of-record note captured for D-IMPL-34: Dave initially mis-clicked the thinner-Protocol alternative and immediately corrected to the recommendation; the six-semantics surface is the ruling of record.
- The "All other D-IMPL-01..29 open" umbrella bullet updated to enumerate the remaining open numbers (11..29 minus 10-provisional).
- Phase I gate impact: D-IMPL-01 through 05 now resolved; remaining gate items 11, 14, 17, 20, 24, 26, 28.

## Verification

- Plan's automated check passed: all 16 IDs carry `RESOLVED` in docs/DECISIONS.md, dated 2026-07-25, "Approver: Dave".
- Original entry text of D-IMPL-33..41 retained (5 "Ambiguous passage" quotations still present; each appended entry carries "Originally: Open — awaiting Dave").
- Rulings commit 280ba23 touches only docs/DECISIONS.md.

## Deviations from Plan

None - plan executed exactly as written (the checkpoint session was mediated by the orchestrator; rulings transcribed verbatim from Dave's answers, no invented rulings).

## Known Stubs

None.

## Threat Flags

None — T-02-04 (every RESOLVED names Approver: Dave), T-02-05 (no provisionals to mark), T-02-06 (original entry text retained, verified) all satisfied.

## Self-Check: PASSED

- `.planning/phases/02-phase-d-design/fragments/marathon-batch-1.md` — FOUND
- 16/16 RESOLVED tokens in docs/DECISIONS.md — FOUND
- Commits a79c809, 280ba23 on phase-d — FOUND
