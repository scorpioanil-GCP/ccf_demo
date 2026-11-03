# Assemble Context Products

**Running examples:** [current setup, Fluree 4.2.4 and connection configuration](../../examples/CONFIGURATION.md).

**New: [Context Skills](../../05-reference/05-technical-reference/CONTEXT_SKILLS.md)** — how a bank agent is granted authority to ask a Context Product, with the SK-01 implementation and SME/Information Architect analysis. Current Fluree requirement: **4.2.4**.

> **Historical learning snapshot.** This Phase 4B path is pinned to its recorded pre-CP-14 baseline. Product-level composition and other capabilities described here as future work have since landed. For current implementation behavior, read [SDK Update Status](../../SDK_UPDATE_STATUS.md) and the [current technical reference](../../05-reference/05-technical-reference/README.md) before copying code.

## Purpose

This is the producer-side learning path for engineers who need to **construct** a governed Context Product. It is intentionally separate from the consumer path.

A consumer asks a product a question. An assembler owns the much harder problem of making that answer trustworthy.

## The assembler's job

An assembler turns a business decision into a reproducible, governed Context Product by connecting five responsibilities:

1. **Decision and contract** — establish what decision the product supports, who consumes it, what must be true for the answer to be safe, and what the product must refuse.
2. **Data reality** — identify what data actually exists, where it lives, what is public vs internal vs engineered, how current it is, and where the estate is incomplete.
3. **Specification** — bind the decision to the implementation through a reviewable SDK-level Context Product specification.
4. **Assembly** — acquire signals, resolve and persist graph state, apply operators, project for a principal, measure freshness / Context Debt, and build the typed product.
5. **Evidence and delivery** — validate the product, record replay, expose it through a supported door/binding, and prove the documented behavior through tests and gates.

The assembler does **not** begin with Python. The assembler begins with the decision.

## Recommended path

### 1. Prepare the demonstration data estate

Read `DATA_ESTATE_SETUP.md`.

The canonical full learning environment is the `ccf_dataprep` portable estate: two fabrics across five datastore technologies, restored locally and verified before SDK assembly exercises begin.

### 2. Move from business decision to approved specification

Read `DECISION_TO_SPEC.md`.

The operating model is:

**SME + data engineer settle the design; AI helps turn the settled design into a rigorous, falsifiable specification.**

The three authorities remain distinct:

- Vault — **why the Context Product exists**
- Dataprep — **what data exists**
- `ccf_code` — **what the implementation does**

Missing owner terms stay explicit TBCs. They are never guessed.

### 3. Learn the L1–L6 assembly responsibilities

Read `ASSEMBLY_MODEL.md`.

The assembler should understand responsibility boundaries before learning individual helper functions:

- L1 Signal — normalize observations; do not interpret
- L2 Assembly — semantic resolution, temporal stitching, policy binding, operator invocation; sole writer
- L3 Graph — persisted typed state; normal components read
- L4 Operators — pure/read-only computation over graph state
- L5 Projection — principal-conditioned typed interpretation, not RBAC filtering
- L6 Context Product — typed, governed, decision-ready delivery

### 4. Wire, validate, record, serve

Read `VALIDATE_AND_SERVE.md`.

Deployment helpers assemble configuration and dependencies; they deliberately do **not** run product gates for the adopter. The separation between authored claims and independently observed execution must stay load-bearing.

## What this path does not teach yet

### Composite Context Products

The original Phase 4B baseline predated CP-14. Current SDK main includes CP-14 and composite replay. Continue with the [CP-14 runbook](../../05-reference/02-context-product-producer/examples/CP14_CREDIT_MEMO_CONTEXT.md) and [current Context Product reference](../../05-reference/05-technical-reference/CONTEXT_PRODUCTS.md) for child admission, aggregate debt, lineage, expiry and refusal behavior.

Do not confuse:

- **operator composition** — the established L4 algebra for composing computation over a graph; with
- **composite Context Products** — governed admission and combination of child product contracts, demonstrated by CP-14 and SK-01.

See the archived [Phase 4 SDK change watch](../../archive/project/phase-4/SDK_CHANGE_WATCH.md).

### Assembly Modes 2 and 3

The approved CP ladder through the current baseline is predominantly the algorithmic foundation. Model/agent assembly, model-risk controls, prompt/version governance, and semantic-stage behavior are advanced material and remain evidence-gated.

## Evidence baseline

Assembler documentation is pinned to:

- `ccf_code/main@374a36007bb2fda3e968a83c2ead7d84993c0b23` — CP-13 approved; CP-14 work excluded
- `ccf_dataprep/main@fcf7dddf79c7f443300d745e90bf39510ef12ab7`

See `ASSEMBLER_SOURCE_MANIFEST.yaml` for the exact source paths used.
