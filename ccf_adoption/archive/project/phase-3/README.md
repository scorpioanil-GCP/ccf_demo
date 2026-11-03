# Phase 3 — Start Here / CCF Story

## Status

**READY FOR CHECKPOINT 3 REVIEW**

Branch: `phase-3-start-here`

## Purpose

Build the front door into CCF so a technically sophisticated newcomer can understand:

- what CCF is;
- why a cognition/context layer is needed for agentic systems;
- how CCF relates to existing data architecture;
- what a Context Product is;
- how the L1–L6 architecture fits together;
- what governance/replay/debt add;
- where to go next based on role and intent.

## Artifacts

Content lives under `03-start-here/`:

- `START_HERE.md` — primary front-door narrative and persona routing.
- `WHY_CCF.md` — architectural problem framing and layering-not-replatforming posture.
- `ARCHITECTURE_AT_A_GLANCE.md` — Systems of Record → Signal Generation → Cognition, six-tuple, L1–L6, planes, half-life/debt, replay.
- `CONTEXT_PRODUCTS.md` — Data Products → Context Products and the consumer contract at conceptual level.
- `RESOURCES.md` — live overview-video / whitepaper links and routes into later sections.
- `START_HERE_PAGE_SPEC.md` — landing-page content/link contract and phase ownership for placeholders.
- `VISUAL_ASSET_PLAN.md` — authoritative CCF figure sources for production visuals.
- `SOURCE_MAP.yaml` — machine-readable source and terminology map.

## Source baseline

Architectural meaning is grounded in:

`drcastillo/ccf@ac81805d0e400da15f860eed8c39a132af3ce945`

Primary source chapters:

- Executive Summary
- Chapter 3 — Agent Anatomy / Context as the Operating Environment
- Chapter 5 — CCF Conceptual Model
- Chapter 6 — Context as a Product
- Chapter 7 — System Architecture
- Chapter 8 — Enterprise Integration

Existing adoption assets used directly:

- `01-whitepaper/CCF_Whitepaper_1-2.pdf`
- `02-overview/Cognitive_Context_Fabric_Intro.mp4`

## Key decisions preserved

1. Context is taught as the agent's operating environment, not merely another input.
2. CCF is positioned above the governed enterprise data estate and below agent runtimes.
3. Existing warehouses, lakehouses, Data Mesh, semantic layers, graphs, documents, and streams remain valuable substrate.
4. Enterprise posture is **layering, not replatforming**.
5. Canonical Context Graph vocabulary remains `G(E,R,T,P,Π,L)`.
6. Canonical layers remain L1 Signal, L2 Assembly, L3 Graph, L4 Operators, L5 Projection, L6 Context Products.
7. L1–L6 are responsibility boundaries, not merely a sequential pipeline.
8. Data Products and Context Products are composition partners.
9. Context Products are introduced as typed, governed, decision-ready outputs rather than generic query results.
10. SDK signatures/defaults remain outside Phase 3 and must come from `ccf_code` in Phases 4–5.
11. Security/production certification claims are not inferred from architecture prose.

## Link posture

Phase 3 converts these prototype destinations to real repository targets:

- overview video;
- released whitepaper;
- Why CCF;
- Architecture at a Glance;
- Context Products;
- resource index.

Links owned by later phases remain explicitly labeled as planned rather than falsely presented as complete. `START_HERE_PAGE_SPEC.md` records ownership and status.

## Visual posture

The approved Phase 2 dark enterprise visual remains the design target. Production explanatory visuals should prefer authoritative CCF figures or source-faithful restyling:

- L1–L6: `Fig-CH07-02-layer-model.png`
- Context Graph six-tuple: `Fig-CH07-03-G-hexagon.png`
- overall architecture: `Fig-CH07-01-overall-architecture.png`
- Context Product lifecycle: `Fig-CH07-13-product-lifecycle.png`
- replay: `Fig-CH07-26-replay.png`

Generated Phase 2 imagery remains directional rather than architectural authority.

## Checkpoint 3 approval test

Approve if a technically sophisticated newcomer can now answer:

1. What is CCF?
2. Why does agentic reasoning require a context/cognition responsibility beyond ordinary data access?
3. Where does CCF sit relative to existing enterprise data architecture?
4. What is a Context Graph?
5. What is a Context Product?
6. What are L1–L6?
7. Why do policy, time, perspective, lineage, Context Debt, and Decision Replay matter?
8. Where should I go next as an evaluator, developer, assembler, architect, or governance/control reader?

## After approval

Phase 4 begins **Using the SDK**, starting with the consumer path before the assembler path, and uses the verified Dataprep portable estate where full assembly is required.
