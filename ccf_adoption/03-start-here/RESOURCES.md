# CCF Resources

Use this page as the short path to the material behind the Start Here experience.

## Overview video

**Cognitive Context Fabric — Intro**

[Watch the overview video](../02-overview/Cognitive_Context_Fabric_Intro.mp4)

Use this when you want the fastest narrative introduction before reading the architecture or SDK material.

## Released whitepaper

**Cognitive Context Fabric Whitepaper v1.2**

[Read the released whitepaper](../01-whitepaper/CCF_Whitepaper_1-2.pdf)

The PDF is the released distribution artifact. The adoption portal uses the structured whitepaper Markdown and source diagrams as the authority for architectural terminology and as the reusable source for portal explanations.

## Start Here pages

- [Cognitive Context Fabric — From data to better decisions](START_HERE.md)
- [Why CCF](WHY_CCF.md)
- [Architecture at a Glance](ARCHITECTURE_AT_A_GLANCE.md)
- [Context Products](CONTEXT_PRODUCTS.md)

## Architecture concepts to explore next

The deeper **Learn CCF** section will expand these concepts individually:

- Context as the operating environment
- Systems of Record → Signal Generation → Cognition
- Context Graph `G(E,R,T,P,Π,L)`
- Dynamic Context vs Dynamic Content
- L1–L6 architecture
- Context Operators
- Context Projection (Π)
- Context Half-life
- Context Debt
- Control Plane / Data Plane
- Decision Replay
- Assembly Mode
- Layering, not replatforming

## Build with CCF

Two different audiences should take different paths.

### Consume

For agent/application developers who want to discover, call, and interpret existing Context Products without learning how the products are assembled.

Planned early topics:

- `ProductClient`
- `Result`
- governed refusal
- in-process binding
- MCP
- A2A / harness integration
- lineage, debt, and replay from the consumer view

### Assemble

For engineers responsible for constructing Context Products from enterprise data estates.

The path begins with:

1. business decision and SME collaboration;
2. Context Product specification;
3. data-estate readiness;
4. source binding and assembly design;
5. graph/operators/projection;
6. policy, temporal semantics, provenance, and Context Debt;
7. validation and serving.

The canonical demonstration environment is the portable estate from `ccf_dataprep`.

## Financial Services

The Financial Services catalog will provide business-first examples backed by the evidence chain:

`whitepaper / business problem → Vault requirement → Dataprep estate → SDK specification → executable example → adoption explanation`

The approved implementation evidence currently runs through CP-12 on the pinned `ccf_code/main` baseline.

## Governance & Controls

Controls are not a separate afterthought. The portal will include dedicated material for:

- provenance and lineage;
- entitlements and suppression;
- temporal correctness;
- policy binding;
- Context Debt;
- Decision Replay;
- dependency invalidation;
- information barriers;
- change control;
- control evidence and second-line review.

Mechanism evidence must not be confused with production certification or security assurance.

## Security & Assurance

Security claims will be tied to a named assessed SDK release/commit. The CP example ladder demonstrates control mechanisms but is **not** itself a threat model, vulnerability assessment, penetration test, or secure-deployment certification.

## Source baselines for this release of Start Here

- CCF / whitepaper source: `drcastillo/ccf@ac81805d0e400da15f860eed8c39a132af3ce945`
- Vault: `drcastillo/obsidian-vault@e10add2edc85efe8e355844edfecc492bcf9fa65`
- Dataprep: `drcastillo/ccf_dataprep@fcf7dddf79c7f443300d745e90bf39510ef12ab7`
- SDK approved evidence: `drcastillo/ccf_code@1a04e565504f712350b51777cfe398be46d5e157`

Later phases will advance these pins deliberately when the source repositories move and the adoption evidence is reconciled.
