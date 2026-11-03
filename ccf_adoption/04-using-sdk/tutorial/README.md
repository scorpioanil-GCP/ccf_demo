# Phase 4C — Progressive assembler tutorial

> **Source and execution:** dated snippets below retain their original source baseline. For current SDK `v1.0.2@5f85b389`, use [setup and configuration](../../examples/CONFIGURATION.md) and the [current developer guide](../../05-reference/README.md).

> **Historical tutorial baseline.** This tutorial intentionally preserves the pre-CP-14 CP-01 learning snapshot. Current `ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178` has additional product, demonstration-time, entitlement, integrity and workflow controls. Use the current technical reference when adapting the tutorial into new code.

## Tutorial anchor

The first end-to-end assembler tutorial uses:

**CP-01 — Counterparty Reference Snapshot**

Pinned implementation baseline:

- `drcastillo/ccf_code@374a36007bb2fda3e968a83c2ead7d84993c0b23`
- example: `examples/cp-01-counterparty-reference-snapshot/`

Pinned data-estate baseline:

- `drcastillo/ccf_dataprep@fcf7dddf79c7f443300d745e90bf39510ef12ab7`
- portable estate: `portable/`

## Why CP-01

CP-01 is the first rung of the approved Context Product ladder and is small enough to understand end to end while still demonstrating real CCF behavior:

- a real financial-services decision frame;
- two identity authorities behind one anchor;
- a load-bearing Policy step;
- entity-anchored TTL/freshness;
- Context Debt;
- governed refusal;
- content addressing;
- Decision Replay;
- explicit assembler identity;
- Control Plane values separated from implementation code.

It uses a relational source estate and does not depend on CP-14 composite Context Products.

## Learning sequence

Read `CP01_PROGRESSIVE_TUTORIAL.md` top to bottom.

The tutorial deliberately progresses through these stages:

1. Restore and verify the real demonstration estate.
2. Understand the business decision before reading code.
3. Read the approved SDK-level specification.
4. Inspect the Control Plane and backend boundary.
5. Read the three implementation seams: caller, assembler, spine.
6. Run the default served path.
7. Run a governed Policy refusal.
8. Inspect Debt, expiry, content identity and replay evidence.
9. Run the correctness tests and understand what they prove.
10. Identify the example's deliberate limitations and known findings.

## Boundary

This is a tutorial for assembling **one Context Product** on the approved pre-CP-14 SDK surface.

It does not teach composite Context Products. Operator composition inside L4 remains part of ordinary assembly; product-level composition is a separate capability under active CP-14 development.
