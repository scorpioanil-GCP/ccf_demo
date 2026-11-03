# Start Here — Visual Asset Plan

## Principle

Phase 2 established the visual language. Phase 3 should now replace directional/generated mock imagery with **authoritative CCF architecture semantics** wherever the visual is explaining the product.

Generated imagery may remain useful for mood/direction, but production diagrams should be sourced from or faithfully reconstructed from `drcastillo/ccf` so that the visual cannot drift away from the architecture.

Source baseline: `drcastillo/ccf@ac81805d0e400da15f860eed8c39a132af3ce945`.

## Hero — six-layer architecture

### Canonical semantic source

`whitepaper/figures/CH07/Fig-CH07-02-layer-model.png`

Supporting source prose / diagram semantics:

`whitepaper/CCF_Chapter_7_CCF_Architecture.md` §7.1.

### Production treatment

Recreate/restyle the L1–L6 concept to fit the approved dark enterprise hero while preserving exactly:

- L1 — Signal Layer
- L2 — Context Assembly
- L3 — Context Graph
- L4 — Context Operators
- L5 — Context Projection (Π)
- L6 — Context Products

Preserve the key architectural note that the layers are **responsibility boundaries, not a simple sequential pipeline**.

Hero callouts:

- `Real-time assembly`
- `Data products to Context Products`

Do not introduce invented layer names or compress the stack to fewer than six layers.

## Context Graph visual

Canonical source:

`whitepaper/figures/CH07/Fig-CH07-03-G-hexagon.png`

Use for:

- Start Here architecture expansion;
- Learn CCF / Context Graph concept page;
- recurring motif for `G(E,R,T,P,Π,L)`.

The six dimensions must remain:

- E — Entities
- R — Relationships
- T — Time / temporal validity
- P — Policy
- Π — Perspective / Projection
- L — Lineage

## Overall architecture visual

Canonical source:

`whitepaper/figures/CH07/Fig-CH07-01-overall-architecture.png`

Use for:

- deeper overview / architecture page;
- evaluator/architect path;
- closed-loop / institutional-memory explanation.

Do not force this complete figure into the landing hero if it creates excessive density. The hero should stay focused on L1–L6.

## Context Product lifecycle

Canonical source:

`whitepaper/figures/CH07/Fig-CH07-13-product-lifecycle.png`

Also use the Chapter 6 Data Product vs Context Product lifecycle Mermaid as source for a simpler adoption-oriented comparison.

Use for:

- `CONTEXT_PRODUCTS.md` enhancement;
- later Build with CCF conceptual introduction.

## Decision Replay

Canonical source:

`whitepaper/figures/CH07/Fig-CH07-26-replay.png`

Use for:

- Governance & Controls;
- architecture evaluator path;
- later assurance material.

The visual must communicate environment/evidence reconstruction, not merely model transcript replay.

## Context Debt / trust

Canonical sources:

- `whitepaper/figures/CH03/Fig-CH03-04-debt-cascade.png`
- `whitepaper/figures/CH07/Fig-CH07-17-trust-triangle.png`

Use after the basic CCF model is understood. Do not overload the initial landing page with these mechanisms.

## Enterprise integration / layering

Source:

- Chapter 8 §8.2–8.3 Mermaid / `Fig-CH08-01` semantics.

Use for:

- `WHY_CCF.md` or architecture expansion;
- Adopt CCF;
- Architecture & Patterns.

The important visual claim is that existing systems remain in place and CCF composes above them.

## Overview video thumbnail

Production treatment should use a modern CCF architectural frame or approved branded frame extracted from the actual video, rather than unrelated scenic photography.

The video itself remains:

`02-overview/Cognitive_Context_Fabric_Intro.mp4`

## Financial Services imagery

Landing-page Financial Services cards may use modern financial/technical imagery for scanning, but images must not imply facts or data values that the example does not prove.

The title, business decision, canonical CP identifier, and evidence/control labels are primary. Decorative imagery is secondary.

## Asset provenance rule

For every production diagram copied or recreated from `ccf`, record:

- source repo;
- source commit;
- source file / figure;
- whether it is `REUSE`, `ADAPT`, or `VISUAL REUSE`;
- any styling-only changes;
- confirmation that architectural semantics were not changed.
