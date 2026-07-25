# Phase 3: Phase F — Feasibility & Scoping - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-25
**Phase:** 3-phase-f-feasibility-scoping
**Areas discussed:** Component granularity, v0.1 surface definition, Test strategy shape, Advisory disposition

---

## Component granularity

| Option | Description | Selected |
|--------|-------------|----------|
| DESIGN.md components | One verdict per named design component/Protocol (~30–50), appendix matrix maps all 126 inventory entries | ✓ |
| All 126 inventory entries | Verdict per SPEC_INVENTORY entry — duplicative | |
| Pillar-level | Five coarse verdicts — fails FEAS-01 bar | |

**User's choice:** DESIGN.md components (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| New D-IMPL + gate flag | Log new D-IMPL-NN, mark "needs design choice", present at D-GATE-F | ✓ |
| Resolve inline during Phase F | Mini decision session mid-phase | |
| You decide | | |

**User's choice:** New D-IMPL + gate flag (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Verdict + rationale + risk | 2–4 sentence rationale + low/med/high risk feeding milestone sizing | ✓ |
| Verdict + one-line rationale | Minimal | |
| Full effort estimates | Per-component sizing — speculative | |

**User's choice:** Verdict + rationale + risk (recommended)

---

## v0.1 surface definition

| Option | Description | Selected |
|--------|-------------|----------|
| Example-driven | v0.1 = what runs examples 00–01 end-to-end on reference backends | ✓ |
| Pillar-driven | Data and Context Layer complete, rest deferred | |
| Vertical slice | Thin path through all five pillars | |

**User's choice:** Example-driven (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Align 1:1 with I.1–I.5 | docs/ROADMAP.md milestones = GSD implementation phases, D-GATE gated | ✓ |
| Independent user-facing milestones | Release-version milestones mapped to phases | |
| You decide | | |

**User's choice:** Align 1:1 with I.1–I.5 (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Named deferral register | Table: item, source, reason, earliest re-entry milestone | ✓ |
| Prose deferral section | Paragraph summary | |
| You decide | | |

**User's choice:** Named deferral register (recommended)

---

## Test strategy shape

| Option | Description | Selected |
|--------|-------------|----------|
| Per-invariant spec table | FEASIBILITY.md chapter: mechanism, CI job, pass criterion, DESIGN.md section | ✓ |
| Standalone TEST_STRATEGY.md | Separate full test-plan doc | |
| You decide | | |

**User's choice:** Per-invariant spec table (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Both, explicitly | Algebraic operator-pair equality + staged-execution equivalence | ✓ |
| Algebraic only | | |
| Staged-execution only | | |

**User's choice:** Both, explicitly (recommended) — closes Codex/Cursor composition-preservation advisory

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, as test-strategy row | ReHydrationRecipe replay must match pinned content hashes (D-IMPL-26) | ✓ |
| Note only, defer spec to Phase I | | |
| You decide | | |

**User's choice:** Yes, as test-strategy row (recommended) — closes Gemini re-hydration advisory

---

## Advisory disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Honest verdict, no re-litigation | Per-harness sizing/risk analysis; high risk → staging recommendation to Dave at gate | ✓ |
| Treat ruling as fixed, no analysis | | |
| Reopen D-IMPL-24 now | | |

**User's choice:** Honest verdict, no re-litigation (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Advisory closure appendix | All 7 items with disposition; wording fixes applied to DESIGN.md in-place | ✓ |
| Fold silently into content | | |
| You decide | | |

**User's choice:** Advisory closure appendix (recommended)

## Claude's Discretion

- FEASIBILITY.md / ROADMAP.md chapter ordering and formatting
- Component enumeration extracted from DESIGN.md
- Risk-rating rubric definitions
- Presentation of the Phase I gate-list check

## Deferred Ideas

None — discussion stayed within phase scope.
