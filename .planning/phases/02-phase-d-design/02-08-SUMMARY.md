---
phase: 02-phase-d-design
plan: 08
subsystem: design-docs
tags: [orchestration, hitl, diagrams, phase-d]
requires: [02-04]
provides:
  - fragments/design-orch-hitl.md (Orchestration + HITL pillar sections for DESIGN.md synthesis)
  - docs/diagrams/pillar-orchestration.mmd
  - docs/diagrams/pillar-hitl.mmd
  - docs/diagrams/seq-hitl-suspend-resume.mmd
affects: [02-10 synthesis, docs/DESIGN.md]
tech-stack:
  added: []
  patterns: [PATTERNS bolded-field component template, standalone .mmd convention]
key-files:
  created:
    - .planning/phases/02-phase-d-design/fragments/design-orch-hitl.md
    - docs/diagrams/pillar-orchestration.mmd
    - docs/diagrams/pillar-hitl.mmd
    - docs/diagrams/seq-hitl-suspend-resume.mmd
  modified: []
decisions:
  - "Audit-by-construction shown structurally: replay write is a precondition of the gate state transition; queue is sole action ingress; HumanPrincipalBinding is a required schema field"
  - "INV-CH8-19 (Supervision Quality) mapped as deferred per D-IMPL-48 ruling, with reason recorded for Appendix A"
  - "D-IMPL-49 swarm-level intent decomposition documented as orchestration-layer concern and named post-v0 extension (ruling obligation discharged)"
metrics:
  duration: ~35 min
  completed: 2026-07-25
---

# Phase 2 Plan 08: Orchestration + HITL Pillars Summary

Orchestration Layer and HITL pillars designed at contract altitude: state-machine Workflow primitive with D-IMPL-18 Control Plane persistence and the D-IMPL-17 LangGraph two-seam boundary, plus four HITL primitives whose only completion path emits a replay write (D-IMPL-20 typed-queue transport, D-IMPL-21 HumanPrincipalBinding), rendered in three Mermaid diagrams.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Draft design-orch-hitl.md | 1aa332d | fragments/design-orch-hitl.md (128 lines) |
| 2 | Author three .mmd diagrams | 9a07eed | docs/diagrams/pillar-orchestration.mmd, pillar-hitl.mmd, seq-hitl-suspend-resume.mmd |

## Verification

- Owned-entry loop check: all 16 INV keys on `design-orch-hitl` lines of entry-ownership.md present in the fragment (11 owned + 5 see-also) — PASS.
- All four primitive names (ApprovalGate, ExceptionEscalation, OverrideBoundary, ReviewQueue) and `OrchestrationProtocol` appear; audit-by-construction section names concrete design constructs (single queue ingress, required binding field, replay-write-before-transition ordering).
- `grep -cE 'D-IMPL-(17|18|20|21)'` = 13 (>= 4); zero fenced code blocks (no-code criterion, T-02-24).
- All three diagrams render via mmdc; pillar-hitl.mmd has a bold `==audit by construction==>` edge from each of the four primitives to the Replay node (T-02-22 total edges); seq diagram contains explicit suspend and resume steps.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree branch behind expected base**
- **Found during:** startup worktree branch check
- **Issue:** HEAD was at 1891b40 (main merge) instead of the expected base 5ce1c7f; plan files absent
- **Fix:** fast-forward-only merge to 5ce1c7f (HEAD was a strict ancestor; no commits lost)
- **Commit:** n/a (ff merge)

**2. [Rule 3 - Blocking] mmdc could not launch a browser**
- **Found during:** Task 2 render check
- **Issue:** all puppeteer-cached Chrome binaries are x86-64 on an aarch64 host (Google ships no linux-arm64 chrome-for-testing); snap Chromium works but cannot read the mmdc HTML under hidden `~/.nvm`
- **Fix:** copied mermaid-cli to a temporary non-hidden home path, rendered with `PUPPETEER_EXECUTABLE_PATH=/snap/bin/chromium`, removed the temp copy afterward
- **Files modified:** none (tooling only)
- **Note for later plans:** other diagram plans in this wave will hit the same issue; same workaround applies.

## Threat Flags

None — no new security surface; T-02-22/23/24 mitigations applied per plan.

## Known Stubs

None.

## Self-Check: PASSED

- fragments/design-orch-hitl.md — FOUND
- docs/diagrams/pillar-orchestration.mmd — FOUND
- docs/diagrams/pillar-hitl.mmd — FOUND
- docs/diagrams/seq-hitl-suspend-resume.mmd — FOUND
- commits 1aa332d, 9a07eed — FOUND
