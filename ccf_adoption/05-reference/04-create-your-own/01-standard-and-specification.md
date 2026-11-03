# Context Product Specifications

**Qualified source package:** `ccf_code/public/reference/specifications/` at `015be95f…`

Primary source documents:

- `Context_Product_Specification_Standard_v0-3.md`
- `spec_generation.md`
- `example_delivery.md`

## Qualified-source notes

Two source-document caveats are intentionally recorded rather than silently rewritten here:

1. The Standard v0.3 header still states a whitepaper v1.1 basis while the current published whitepaper is v1.2. Treat the Standard as the qualified specification-format source at this SDK baseline; reconcile the header in its owning source through the normal change path rather than editing the rule in adoption documentation.
2. `spec_generation.md` records several stale numeric cross-references inside the Standard. When those occur, resolve the cited section **by heading/semantic name**, not by a stale number.

This page is the adopter-facing map of those rules. It does not replace the Standard.

## Two specification levels

### Business / implementation-independent product definition

Answers **what the product is and why it exists**.

It owns:

- decision frame;
- trigger;
- consuming principals;
- counterfactual;
- build-test rationale;
- scope boundary;
- prerequisites/consumers;
- business intent.

### SDK implementation specification

Answers **how this product is implemented against a specific estate with this SDK**.

It adds:

- actual store/schema/table bindings;
- measured source readiness/coverage;
- ontology bindings;
- concrete request contract;
- operator composition;
- TTL/half-life/Debt design;
- validation gates;
- materialization posture;
- implementation acceptance criteria.

It names the store/schema/table needed by the implementation, but never deployment host/port/credential values.

## Standard structure

The v0.3 standard uses seven sections:

| Section | Purpose |
|---|---|
| A | Decision frame |
| B | Contract |
| C | Data catalog |
| D | Assembly recipe |
| E | Volatility and materialization |
| F | Source binding and readiness |
| G | Operate and govern |

Unresolved authority-owned terms remain explicit `[TBC — owner]`.

## Four-question admission test

Before building a Context Product, test whether the decision actually requires one.

The Standard asks whether the answer:

1. changes materially with who is asking;
2. has a validity window;
3. must be reconstructible with historical policy/freshness state;
4. is composed at runtime from sources no schema author pre-joined.

Qualified/partial answers are allowed when stated honestly.

## Gate 1 — design approval

Before implementation, the implementation spec contains all knowable design terms and explicitly marks build-measured terms TBC.

Gate 1 approves:

- scope;
- decision;
- request/product contract;
- source bindings;
- operator/assembly design;
- temporal/policy/debt design;
- intended gates/acceptance.

**No implementation code before Gate 1.**

## Gate 2 — evidence close-out

After implementation/run:

- fill measured budgets;
- hashes/addresses;
- witnesses;
- sabotage/gate observations;
- final materialization/operations values;
- close every `[TBC — this build]`.

A build that disproves a Gate-1 design term creates a deviation. Do not edit the design silently until it matches the code.

## Authority split for AI-assisted authoring

| Term | Authority |
|---|---|
| why / decision / business scope | SME / business product definition |
| what data really exists | data engineering / source-estate evidence |
| what the SDK implementation does | qualified SDK + canonical examples + tests |
| drafting, transformation, consistency checks | AI assistant |

Rule:

> **AI may draft an authority-owned term from supplied evidence. It may not invent a missing authority-owned term.**

## Recommended template

The qualified generation recipe identifies CP-SPEC-000 as the current document-shape template for specification authoring.

Do not use a later, more complex CP as the blank template merely because it is newer; use later canonical examples to learn current **implementation** patterns.

## From spec to code

Once Gate 1 is approved, the AI assistant should generate against the stabilized paved-road shape:

- `ccf_config.yaml`
- `ccf_environment.yaml`
- `acquisition.py`
- `projection.py`
- `deployment.py`
- thin `produce.py`
- `run.py`
- server/door where required
- artifacts/tests/docs required by the example-delivery rules

See [Cowork Spec-to-Code Workflow](07-end-to-end-cowork-workflow.md).
