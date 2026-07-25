---
phase: 02-phase-d-design
plan: 09
subsystem: design-docs
tags: [experience, seams, mcp, a2a, harness-adapter, artifact-store, diagrams]
requirements: [DSGN-01, DSGN-03]
dependency-graph:
  requires: [02-04 (marathon rulings D-IMPL-13..27)]
  provides: [design-experience-seams fragment, both DSGN-03 seam diagrams, pillar-experience diagram, A2A admission sequence]
  affects: [02-10 (DESIGN.md synthesis), Phase I.3/I.4]
key-files:
  created:
    - .planning/phases/02-phase-d-design/fragments/design-experience-seams.md
    - docs/diagrams/pillar-experience.mmd
    - docs/diagrams/seam-harness-adapter.mmd
    - docs/diagrams/seam-artifact-store.mmd
    - docs/diagrams/seq-a2a-admission.mmd
  modified: []
decisions: []
metrics:
  duration: ~35m
  completed: 2026-07-25
---

# Phase 2 Plan 09: Experience Pillar + Cross-Process Seams Summary

**One-liner:** Contract-altitude design of the three v0 front doors (MCP egress, `ccf` noun-verb CLI, HTTP skeleton) and all four cross-process seams (five-edge MCP role allocation, LF-A2A federation with verify-everything admission and set-union lineage, four-seam HarnessAdapterProtocol with three v0 targets, hybrid-addressed ArtifactStore with mutability-split substrate), plus the two DSGN-03-mandated seam diagrams and the D-09 A2A admission sequence.

## What Was Built

- **`fragments/design-experience-seams.md` (152 lines):** Experience pillar sections (MCP server per D-IMPL-13, CLI per D-IMPL-22 with the full noun-verb table, HTTP API per D-IMPL-23 with the no-L1-ingestion rule, non-goals incl. the INV-CH8-21 out-of-scope disposition and INV-CH8-24 coexistence posture); Seams chapter (MCP role-allocation table with distinct modules/trust postures; A2A per D-IMPL-14/15/16 with L2-only admission and set-union lineage continuity; HarnessAdapterProtocol per D-IMPL-24/25 with the four seams named and the LangGraph two-seam disambiguation; ArtifactStore per D-IMPL-26/27 with never-a-second-writer). Coverage table for all six owned INV entries; threat dispositions T-02-25/26/27 addressed by design.
- **Four diagrams**, all render-verified: `pillar-experience.mmd`, `seam-harness-adapter.mmd` (four labeled seam edges, no harness node in core, effects routed through L2), `seam-artifact-store.mmd` (no store→L3 edge; store edges terminate at L2/Control Plane mechanism), `seq-a2a-admission.mmd` (signing, verification step, reject branch, set-union write).

## Verification Results

- Owned-entry loop check: all INV keys grepped from entry-ownership rows citing design-experience-seams present in the fragment — PASS.
- `D-IMPL-(13|14|15|16|22|23|24|25|26|27)` citations: 33 (>= 10) — PASS. No code blocks in fragment. "set-union" present.
- All four diagrams render (mermaid parse + render): PASS. seam diagram greps (inject/skill/effect/replay; verif/reject) — PASS.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree branch was behind the expected base commit**
- **Found during:** Startup branch check
- **Issue:** `worktree-agent-a6a1ab95ba700329f` sat at old main (1891b40), missing the entire `02-phase-d-design` phase directory; expected base 5ce1c7f.
- **Fix:** Fast-forward merge (`git merge --ff-only 5ce1c7f`) — no history rewrite.

**2. [Rule 3 - Blocking] mmdc render-check unusable on this host**
- **Found during:** Task 2 verification
- **Issue:** puppeteer's cached chrome/chrome-headless-shell binaries are x86-64 on an ARM host (exec format failure); snap chromium cannot read the mermaid-cli install under the hidden `~/.nvm` path (ERR_ACCESS_DENIED).
- **Fix:** Equivalent render verification via system chromium headless + the same bundled mermaid parser (`mermaid.parse` + `mermaid.render` for all four files) from a temp dir inside the worktree, removed afterward. This caught and fixed a real syntax error (semicolon-in-message in `seq-a2a-admission.mmd`). Recommend fixing the puppeteer cache (ARM chrome build) before the phase-gate review; logged for awareness.
- **Files modified:** docs/diagrams/seq-a2a-admission.mmd (line 15 semicolon → dash)
- **Commit:** 937e9c9

Also removed a stray control-character-named crash artifact the headless chromium run left at the worktree root (never staged).

## Known Stubs

None — design documents, no runtime stubs.

## Threat Flags

None — no new surface beyond the plan's threat model; T-02-25/26/27 dispositions embodied in the fragment and enforced visually in the diagrams.

## Commits

- 0278eab — docs(phase-02): Experience pillar + seams chapter draft
- 937e9c9 — docs(phase-02): experience pillar + seam + A2A diagrams
