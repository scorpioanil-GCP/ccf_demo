# Phase 2: Phase D — Design - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-25
**Phase:** 2-Phase D — Design
**Areas discussed:** D-IMPL resolution workflow, DESIGN.md structure, Diagram format & tooling, Invariant proof format

---

## D-IMPL resolution workflow

**Q1 — How should the ~49 open D-IMPL decisions reach Dave?**

| Option | Description | Selected |
|--------|-------------|----------|
| Batched interactive sessions | Themed batches via AskUserQuestion, rulings logged immediately | ✓ |
| Recommendations doc, async review | Proposals doc reviewed on Dave's own time | |
| Design first, decide after | Draft against provisional assumptions, rule with design in hand | |

**Q2 — Presentation style per decision?**

| Option | Description | Selected |
|--------|-------------|----------|
| Recommendation-first | Claude's recommended option first with rationale, alternatives with consequences (CLAUDE.md §15) | ✓ |
| Neutral options only | All readings equal weight | |
| Recommendation + Homecams data point | Recommendation plus explicit Homecams triangulation display | |

**Q3 — Timing vs drafting?**

| Option | Description | Selected |
|--------|-------------|----------|
| Gating decisions first, rest interleaved | (Claude's recommendation) | |
| All decisions before any drafting | Full decision marathon precedes DESIGN.md drafting | ✓ |
| Draft-driven ordering | Decisions surface as drafting hits them | |

**Notes:** Dave overrode the interleaved recommendation — the marathon completes first.

**Q4 — Handling of deferred rulings?**

| Option | Description | Selected |
|--------|-------------|----------|
| Provisional + flagged | Claude's recommendation adopted provisionally, marked, confirmed at gate | ✓ |
| Hard-flag as gating, design around it | Explicit deferral, design holes remain | |
| No deferrals allowed | Marathon runs until every ruling lands | |

---

## DESIGN.md structure

**Q1 — Top-level organization?**

| Option | Description | Selected |
|--------|-------------|----------|
| By pillar, fabric layers inside | Five Common Pillar sections, L1–L6 inside Data & Context pillar | ✓ |
| By fabric layer, pillars as overlay | L1–L6 spine first | |
| Mirror the inventory chapters | Whitepaper chapter keyed | |

**Q2 — Inventory→design traceability?**

| Option | Description | Selected |
|--------|-------------|----------|
| Inline citations + matrix appendix | Inline INV-CHx-NN cites plus full 126-entry appendix table | ✓ |
| Matrix appendix only | One table at the end | |
| Inline citations only | Coverage by grep | |

**Q3 — Component altitude?**

| Option | Description | Selected |
|--------|-------------|----------|
| Contract-level | Responsibility, Protocol/type signatures, seams, D-IMPL rulings embodied | ✓ |
| Module-level blueprint | Adds package layout, class diagrams, schemas | |
| Conceptual architecture | Prose + diagrams, signatures deferred | |

**Notes:** Confirmed via free-text "contract move" (contract-level, move on).

---

## Diagram format & tooling

**Q1 — Format?**

| Option | Description | Selected |
|--------|-------------|----------|
| Mermaid source in-repo | GitHub-native, matches rebuilt whitepaper figures | ✓ |
| Mermaid + exported PNG/SVG | Source plus committed renders | |
| PlantUML / draw.io | Richer layout, extra toolchain | |

**Q2 — Sequence diagrams beyond the required 7?**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, for load-bearing flows | L2 single-writer path, A2A admission, HITL suspend/resume, replay resolution | ✓ |
| Only the required 7 | Flows in prose | |
| Claude decides per section | Ad hoc | |

**Q3 — Naming/C4/detail depth:** deferred to Claude's discretion (user chose "Next area").

---

## Invariant proof format

**Q1 — How to demonstrate preserved-by-construction?**

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated chapter + enforcement table | Per-invariant structural argument, enforcement point, diagram ref, review-checkable table | ✓ |
| Embedded in each component section | Arguments live with mechanism only | |
| Both: embedded + summary chapter | Cross-reference index | |

**Q2 — Pre-specify CI enforcement design?**

| Option | Description | Selected |
|--------|-------------|----------|
| Specify CI enforcement design | Name concrete lints/test shapes for Phase F/I to implement against | ✓ |
| Structural argument only | Defer CI mechanism to Phase F | |

---

## Claude's Discretion

- Decision-batch grouping/ordering within the marathon (gating list prominent)
- Diagram naming convention, C4 layering, per-diagram detail depth
- DECISIONS.md ruling entry format on resolution

## Deferred Ideas

None — discussion stayed within phase scope.
