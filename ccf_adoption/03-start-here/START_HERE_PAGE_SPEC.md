# Start Here Page Contract

## Purpose

This file translates the approved Phase 2 landing-page experience into Phase 3 content and link behavior. It is the contract between the content model and the later site implementation.

The page may evolve visually, but the information hierarchy and link ownership below should remain stable unless a later checkpoint changes the IA.

## Hero

### Product name

`Cognitive Context Fabric`

### Primary message

`From data to better decisions.`

### Supporting message

CCF assembles, contextualizes, and delivers governed Context Products from real-world heterogeneous data estates, with provenance, controls, temporal semantics, and clarity.

### Architecture visual

Use an authoritative or source-faithful L1–L6 visualization:

- L1 — Signal Layer
- L2 — Context Assembly
- L3 — Context Graph
- L4 — Context Operators
- L5 — Context Projection
- L6 — Context Products

Supporting callouts:

- `Real-time assembly`
- `Data products to Context Products`

### Primary actions

| Action | Target | Status |
|---|---|---|
| Get Started | `START_HERE.md` / guided page flow | **LIVE IN PHASE 3 CONTENT** |
| Explore Financial Services | Financial Services catalog | **PLANNED — Phase 6** |

## Resource strip

| Resource | Target | Status |
|---|---|---|
| Watch Overview | `../02-overview/Cognitive_Context_Fabric_Intro.mp4` | **LIVE** |
| Read the Whitepaper | `../01-whitepaper/CCF_Whitepaper_1-2.pdf` | **LIVE** |
| View Architecture | `ARCHITECTURE_AT_A_GLANCE.md` | **LIVE** |
| Why CCF | `WHY_CCF.md` | **LIVE** |
| Context Products | `CONTEXT_PRODUCTS.md` | **LIVE** |
| Browse Resources | `RESOURCES.md` | **LIVE** |

These resources should not be duplicated as another full navigation bar. They are direct content shortcuts.

## Audience entry cards

### For Developers

Purpose: route developers without making them decide whether they are consumers or assemblers from the global navigation alone.

Primary CTA: `Build with CCF`

Destination behavior:

- **Consume Context Products** → Phase 4A
- **Assemble Context Products** → Phase 4B/4C
- SDK Reference → Phase 5

Status in Phase 3: **route placeholder by design; content not yet authored.**

### For Financial Services

Purpose: route from CCF concept to recognizable banking decision problems.

Primary CTA: `View Use Cases`

Destination: Financial Services catalog and domain families.

Status in Phase 3: **route placeholder by design; Phase 6 owns final pages.** Phase 1C evidence already defines the source backbone.

### For Evaluators / Architects / Governance

Purpose: provide a non-coding evaluation path.

Useful Phase 3 live destinations:

- `WHY_CCF.md`
- `ARCHITECTURE_AT_A_GLANCE.md`
- `CONTEXT_PRODUCTS.md`
- released whitepaper

Later destinations:

- Governance & Controls → Phase 8A
- Security & Assurance → Phase 8B/8C
- Adoption Guide → Phase 9A

## Featured Financial Services carousel

The landing-page carousel is an entry catalog, not the full explanation.

Each card should eventually show:

- Context Product / use-case name;
- business-domain label;
- one-line decision problem;
- canonical example identifier;
- optional control/evidence label;
- link to detailed Financial Services page.

Phase 3 should **not** invent finalized public use-case copy. Phase 6 owns that content, grounded in the Phase 1C lineage and governance registers.

Until Phase 6, the site may either:

1. show a clearly labeled preview based on approved CP names; or
2. omit/de-emphasize the carousel in production content builds.

It must not link every card to one generic use-case page as if those pages were complete.

## Lower utility panels

### Latest Updates

Not a Phase 3 priority. Do not fabricate a news feed. Populate only when the project has a defined release/change-log source.

### Popular Resources

Phase 3 can populate this with real targets:

- overview video;
- whitepaper;
- Start Here;
- Architecture at a Glance;
- Context Products;
- Why CCF.

Later add:

- SDK Quickstart — Phase 4;
- API Reference — Phase 5;
- Financial Services examples — Phase 6;
- Data Estate Setup — Phase 7;
- Governance / Security — Phase 8.

### Get Started Today

Primary route depends on persona:

- evaluator → `START_HERE.md` / `WHY_CCF.md`;
- consumer developer → Phase 4A;
- assembler → Phase 4B/4C;
- governance/control → Phase 8A;
- adoption/program lead → Phase 9A.

Until those pages exist, the implementation must not pretend the route is complete.

## Global navigation status by phase

| Primary destination | Content owner | Current status |
|---|---|---|
| Start Here | Phase 3 | **IN BUILD / live content exists** |
| Learn CCF | Phase 3 + later concept expansion | **PARTIAL** |
| Build with CCF | Phase 4 | **NOT YET AUTHORED** |
| Reference | Phase 5 | **NOT YET AUTHORED** |
| Financial Services | Phase 6 | **EVIDENCE READY; PUBLIC PAGES NOT YET AUTHORED** |
| Govern & Operate | Phases 7–8 | **NOT YET AUTHORED** |
| Adopt CCF | Phase 9 | **NOT YET AUTHORED** |

## Link-completeness rule

A missing deep link is acceptable before its owning phase is complete.

A **false link** is not acceptable: no page should imply that a destination is complete when it is still a prototype placeholder.

Each phase should convert its owned placeholders into real links and update this contract or the eventual site link manifest.

## Source / design lineage

- Experience model: Phase 2 Checkpoint 2 (`APPROVED WITH AMENDMENTS`)
- CCF meaning: `drcastillo/ccf@ac81805d0e400da15f860eed8c39a132af3ce945`
- Phase 3 content: `03-start-here/*`
