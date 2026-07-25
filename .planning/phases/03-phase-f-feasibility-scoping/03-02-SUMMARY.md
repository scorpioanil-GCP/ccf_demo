---
phase: 03-phase-f-feasibility-scoping
plan: 02
subsystem: docs
tags: [roadmap, phase-f, v0.1-surface, deferral-register]
requires: [docs/FEASIBILITY.md, .planning/ROADMAP.md, docs/DECISIONS.md]
provides:
  - docs/ROADMAP.md (milestones I.1-I.5, v0.1 surface, deferral register)
affects: [03-03 (test-strategy chapter cross-references this file), 03-04 (gate review)]
tech-stack:
  added: []
  patterns: [two-roadmap preamble pattern, Appendix-B-style deferral register table]
key-files:
  created: [docs/ROADMAP.md]
  modified: []
decisions:
  - "v0.1 IdentityProvider assessment (D-11 advisory 7): NOT required for v0.1 — examples 00-01 are in-process, no A2A boundary crossed; dev/mock IdentityProvider enters as the first deliverable of I.3's A2A work"
  - "Deferral register extended beyond the five mandatory rows with two verified candidates: Chroma second SimilarityIndex impl (D-IMPL-03 'if budget allows') and remote Control Plane implementation (CLAUDE.md §13 extension point)"
  - "LangGraph staging within I.3 carried verbatim from FEASIBILITY.md as a recommendation for Dave at D-GATE-F, explicitly marked not-a-scope-change; no harness adapter row appears in the deferral register (D-IMPL-24 stands)"
metrics:
  duration: "~12 min"
  completed: 2026-07-25
---

# Phase 3 Plan 02: docs/ROADMAP.md — Milestones, v0.1 Surface, Deferral Register Summary

**One-liner:** docs/ROADMAP.md created (186 lines) with five D-GATE-I.n-gated milestones mirroring .planning/ROADMAP.md phases 4-8 1:1, an example-driven v0.1 surface table (examples 00-01 cut incl. IdentityProvider not-needed assessment), and a seven-row deferral register.

## What was built

- **Task 1 (`1aa52b2`):** `docs/ROADMAP.md` —
  - **Preamble** stating the two-roadmap relationship: `.planning/ROADMAP.md` is the sequencing source of truth; `docs/ROADMAP.md` is the deliverable view, 1:1 aligned; CLAUDE.md rev 4 canonical. D-IMPL-10 status quoted verbatim from DESIGN.md Appendix C (Pitfall 1 avoided).
  - **§1 Milestones** (D-05): I.1 Fabric Core, I.2 Agent Specialization Framework, I.3 Cross-Process & Harness Adapters, I.4 Orchestration/HITL/Experience, I.5 Examples Suite & Full CI Verification — each with its `.planning/ROADMAP.md` phase mapping, `D-GATE-I.n` gate, requirement IDs, and per-milestone risk highlights from FEASIBILITY.md (high risk concentrated in I.3 per D-10: MCP client, A2A, ADK adapter, LangGraph adapter; Claude Agent SDK med). LangGraph stage-later-within-I.3 phrased strictly as a recommendation for Dave.
  - **§2 v0.1 surface** (D-04): explicit example-driven table — fabric core L1-L6, three validation gates (verbatim gate naming), Control Plane registry, Decision Replay, SQLite graph store, sqlite-vec, file-backed ArtifactStore, Agent & Task Factory, `AnalyticsInsightsAgent` only, CINV scaffolding — plus the dev/mock IdentityProvider line item assessed as not needed for v0.1 with rationale (D-IMPL-15 identity is first exercised at I.3).
  - **§3 Deferral register** (D-06): mandatory five rows (Homecams rebuild, D-IMPL-10 adapter split, D-IMPL-49 swarm intent decomposition, D-IMPL-48 Supervision Quality, Conversational Reporting Layer §8.10) + Chroma (D-IMPL-03) + remote Control Plane; explicit "Not deferred" note that all three harness adapters ship v0.

## Verification

- All plan `<verify>` greps pass: milestone names, gate IDs D-GATE-I.1..I.5 (5/5 found), deferral mentions ≥ 5, `AnalyticsInsightsAgent`, `.planning/ROADMAP.md` literal path, "Deferral Register", FEASIBILITY link
- 186 lines ≥ 80 min_lines; no harness-adapter deferral row
- `.planning/STATE.md` and `.planning/ROADMAP.md` untouched

## Deviations from Plan

**1. [Rule 3 - Blocking] Worktree branch handling**
- **Found during:** startup
- **Issue:** Plan says "On branch `phase-f`"; executor runs in an isolated worktree.
- **Fix:** Stayed on `worktree-agent-ac1d907cb27d3959b` per orchestrator instructions; worktree base reset to expected commit `71d503d`.
- **Commit:** n/a (process deviation)

No content deviations — executed as planned.

## Known Stubs

None. §4 of docs/ROADMAP.md notes the FEAS-03 test-strategy chapter is added by plan 03-03 — an intentional forward reference per the phase plan structure, not a stub.

## Threat Flags

None — docs-only change; only docs/ROADMAP.md committed (T-03-02 mitigations honored).

## Self-Check: PASSED

- docs/ROADMAP.md exists: FOUND
- Commit 1aa52b2: FOUND
