---
phase: 02-phase-d-design
plan: 07
subsystem: design-docs
tags: [design-docs, agent-framework, diagrams]
requires: [02-04]
provides:
  - "Core Agent Types pillar design fragment (design-agent-types.md)"
  - "Core Agent Types pillar component diagram (pillar-agent-types.mmd)"
affects: [02-10]
tech-stack:
  added: []
  patterns: ["PATTERNS bolded-field component template", "standalone .mmd diagram sources"]
key-files:
  created:
    - .planning/phases/02-phase-d-design/fragments/design-agent-types.md
    - docs/diagrams/pillar-agent-types.mmd
  modified: []
decisions:
  - "Fragment embodies RESOLVED rulings D-IMPL-11, 12, 19, 28, 29 exactly; zero provisional flags needed (provisional register confirms 0 provisionals)"
  - "mmdc render-check replaced by equivalent mermaid.min.js render via puppeteer-core + snap chromium (Rule 3 tooling workaround on aarch64)"
metrics:
  duration: "~15 min"
  completed: 2026-07-25
---

# Phase 2 Plan 07: Core Agent Types Pillar Summary

**One-liner:** Core Agent Types pillar designed at contract altitude — single-`Agent`-class + Protocol archetype bundles (D-IMPL-11/19), Agent & Task Factory over YAML/Pydantic artifacts (D-IMPL-28), and two-tier governed skilling (D-IMPL-12/29) — with a factory-only-construction pillar diagram.

## What Was Built

**Task 1 — `fragments/design-agent-types.md`** (153 lines, commit 85fc530)
- Unified `Agent` base per the D-IMPL-11 ruling: single concrete class, no subclassing, archetypes as Protocol-typed `ArchetypeComponent` bundles; no reasoning loop (harness-neutral by construction, CLAUDE.md §6.5).
- All six archetypes with per-archetype Responsibility / Invariants / Seams field blocks plus a fabric-interaction/replay-obligation table.
- Archetype composition per D-IMPL-19 (ordered list, dedup, declaration-order defaults with factory warning, hard-contradiction construction error).
- Agent & Task Factory per D-IMPL-28 (YAML + Pydantic v2 `extra=forbid` + exported JSON Schema; Jinja2 prompt artifacts by versioned URI; independent semver lanes) with the No-Hardcoding Rule as structural design (lint design cross-referenced to the Invariant Preservation chapter).
- Channel 1 (all six specialization axes named) and Channel 2 (dynamic catalog per D-IMPL-12, four skill types, two-tier governance per D-IMPL-29, replay capture of skill-set in force).
- Whitepaper-owned entries integrated: INV-CH7-32 (swarm-realized operators via ContextAssemblyAgent), INV-CH8-12 (alternating derivation bound into archetype pipelines), INV-CH8-22 (platform/domain split as the mechanism/values boundary), INV-CH6-05/07/08 (consumption discipline, loop discipline, trust-gated action), INV-CH7-84 (mechanical dimension-4 capture).
- D-IMPL-49 swarm intent-decomposition obligation noted with cross-reference to design-orch-hitl.md.

**Task 2 — `docs/diagrams/pillar-agent-types.mmd`** (commit 101c731)
- `flowchart TD` with two subgraphs: "SDK mechanism (/src)" (Agent base, six archetypes, Factory, tier-1 compatibility check) vs "Control Plane artifacts" (agent/task definitions, prompt artifacts, skill catalog, grants).
- Archetype→agent path passes through the Factory only (no direct edge, per threat T-02-19); skilling grant path routes through the policy-compatibility check; replay node receives agent version + skill-set in force.

## Verification

- Owned-entry loop check: all 14 INV keys on `design-agent-types` lines of entry-ownership.md (7 owned + 7 see-also) present in the fragment — PASS.
- Six archetype names, six specialization axes, both channels: present.
- `grep -cE 'D-IMPL-(11|12|19|28|29)'` = 17 (>= 5); zero code blocks.
- Diagram renders (SVG produced); Factory node and both subgraphs present.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] mmdc render-check unusable on this host**
- **Found during:** Task 2 verification
- **Issue:** mmdc's puppeteer-managed chrome binaries are x86-64 while the host is aarch64 (corrupt/unrunnable); snap chromium cannot read mmdc's install under hidden `~/.nvm` (snap confinement).
- **Fix:** rendered with the exact same `mermaid.min.js` bundle mmdc ships, injected over CDP into snap chromium via puppeteer-core (script in session scratchpad). Equivalent render verification; SVG produced successfully.
- **Files modified:** none (scratchpad-only script)
- **Commit:** 101c731 (workaround noted in commit message)

## Threat Model Dispositions

- T-02-19 (archetype/agent boundary blur): mitigated — subgraph separation + factory-only edge in the diagram; fragment states the boundary structurally.
- T-02-20 (unflagged provisional bases): mitigated — all five governing rulings verified RESOLVED against `provisional-register.md` (0 provisionals); fragment states this explicitly.
- T-02-21 (phase-boundary code): mitigated — zero code blocks in the fragment (verified by grep).

## Known Stubs

None.

## Self-Check: PASSED

- `.planning/phases/02-phase-d-design/fragments/design-agent-types.md` — FOUND
- `docs/diagrams/pillar-agent-types.mmd` — FOUND
- Commit 85fc530 — FOUND
- Commit 101c731 — FOUND
