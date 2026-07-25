---
phase: 01-phase-r-research
plan: 07
subsystem: research
tags: [spec-inventory, whitepaper, projection, context-products, context-debt, half-life]
requires: ["01-04"]
provides:
  - "fragments/inventory-ch7b.md — §7.5–§7.7 seven-field inventory entries INV-CH7-40..68"
affects: ["01-11 synthesis merge"]
tech-stack:
  added: []
  patterns: [seven-field inventory entry, chapter-scoped keys, unnumbered open questions]
key-files:
  created:
    - .planning/phases/01-phase-r-research/fragments/inventory-ch7b.md
  modified: []
decisions:
  - "Key allocation within the 40–69 block: §7.5 → 40–44, §7.6 → 45–56 (three validation gates as three distinct entries 46–48), §7.7 → 57–68"
  - "MAX_TTL configuration locus and CAR threat-level/threshold source emitted as unnumbered open questions for synthesis"
metrics:
  duration: "~15 min"
  completed: "2026-07-25"
  tasks: 2
  commits: 2
---

# Phase 1 Plan 07: §7.5–§7.7 Inventory Extraction Summary

Extracted every commitment in whitepaper §7.5 (Projection Π), §7.6 (Context Products), and §7.7 (Debt & Half-life) into 29 seven-field entries (INV-CH7-40..68) in fragments/inventory-ch7b.md, with formulas and gate conditions verbatim.

## What Was Done

- **Task 1 (commit 1c6dc19):** INV-CH7-40..56 covering §7.5 (Π substitution vs RBAC, ProjectionPlan `required_operators()` + `invoke()` structural interface, two-stage execution, role-shaped views/runtime conditioning, output stability layer) and §7.6 (ContextProductContract base with `extra=forbid` verbatim; the three validation gates — empty-operator guard, lineage strict equality, TTL bounds — as three distinct entries with gate conditions in Invariants; per-product independent semver lanes; SLO envelope; materialization/cache coherency; derivation paths; per-class cost bands; Algorithmic ⇄ Semantic Alternation citing §7.6.6 with the CLAUDE.md §11 CI-lint enforcement hook noted in Dependencies; three assembly modes; per-mode replay footprint + five disciplines).
- **Task 2 (commit 14edad0):** INV-CH7-57..68 covering §7.7: λ_c decay formula verbatim (`R(t) = R₀ × (1/2)^((t − t₀) / λ_c)`) with the values-live-in-Control-Plane-config-never-code invariant; λ_c table shape; supersession as Policy event; D_c formulas verbatim (`D_c = 1 − (C_available / C_required)`, `D_c = 1 − (F · C · S)`, rejected `D_c_alt`); multiplicative-conjunctive defense; three debt components; CAR four-state routing (Forced LLM as distinct behavior); Trust Triangle debt-mapping; Fail-Closed conservative bias; multi-agent debt cascade.

## Verification

- All Task 1/Task 2 automated greps pass: `required_operators` ×2, `extra=forbid` ×6, all three gates present, `§7.7` ×18, `λ_c` ×24, `fail-closed` ×6.
- Zero PDF citations in the fragment (locked D-01 honored).
- 29 `### INV-CH7-` entries, keys in the 40–69 block; `## Open Questions (unnumbered)` section present with 2 entries.

## Deviations from Plan

None - plan executed exactly as written.

## Open Questions Emitted (unnumbered, for synthesis)

1. MAX_TTL configuration locus (INV-CH7-48, §7.6.1/§7.6.4).
2. CAR threat-level scale and class-specific D_c threshold source (INV-CH7-65, §7.7.7).

## Self-Check: PASSED

- fragments/inventory-ch7b.md exists: FOUND
- Commits 1c6dc19, 14edad0 exist on worktree branch: FOUND
