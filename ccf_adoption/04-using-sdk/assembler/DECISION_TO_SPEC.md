# From Business Decision to Approved Context Product Specification

## Start with the decision, not the SDK

A Context Product exists to support a decision. The first assembler task is therefore not to pick a backend, write Python, or choose an operator. It is to make the decision frame explicit enough that an SME, data engineer, controls partner, and implementer agree on what the product must mean.

The implementation specification is the bridge from that agreed design to code.

## The collaboration model

The preferred operating model is:

**SME + data engineer settle the design; AI helps turn the settled design into a rigorous, reviewable, falsifiable specification.**

AI can accelerate drafting, reconciliation, acceptance-test formulation, and consistency checks. It is not the authority for a missing business rule, source system, threshold, policy, ontology binding, or data-availability claim.

Unknowns remain explicit TBCs owned by the responsible source or role.

## Three authorities, three questions

The current specification-generation recipe separates authority deliberately:

| Question | Authority | What it owns |
|---|---|---|
| **Why does this product exist?** | Vault / domain specification | decision, trigger, principals, counterfactual failure, scope, tier, prerequisites |
| **What data actually exists?** | `ccf_dataprep` | systems of record, provenance, classification, capability, ontology binding, measured coverage, data traps and limitations |
| **What does this implementation do?** | `ccf_code` | emitted contract, request/parameter surface, operator composition, budgets/witnesses, replay, debt/materialization behavior, gates, tests and runtime behavior |

An implementation spec must not silently take ownership of a term that belongs to another authority.

## Two specification levels

### Implementation-independent product specification

The Vault-level specification answers **what the Context Product is** without binding it to a specific database deployment.

It should be readable by a domain SME and architect without knowing whether the eventual implementation uses PostgreSQL, Fluree, MongoDB, Neo4j, a lakehouse, or another source.

### SDK implementation specification

The SDK-level specification answers **how this specific implementation is built** against one known estate.

It therefore names the source store / schema / table or equivalent implementation binding needed by the data engineer. It still does **not** contain hostnames, ports, credentials, or environment-specific deployment details; those belong in deployment configuration.

Neither specification supersedes the other.

## Gate 1 — approve the design before code

The SDK recipe requires the specification to be the first implementation artifact for a Context Product example.

At Gate 1, author everything knowable before implementation, including:

- decision and trigger;
- consuming principals/personas;
- counterfactual failure;
- contract elements and request parameters;
- scope boundaries and explicit exclusions;
- data catalog / element-to-source bindings;
- provenance/classification and measured readiness;
- proposed operator recipe and witnesses;
- temporal and materialization posture;
- Context Debt / half-life evidence where applicable;
- intended validation / refusal behavior;
- operate-and-govern responsibilities;
- `[TBC — owner]` for anything not yet authoritative or measurable.

Then stop for approval. Implementation begins only after the design is accepted.

## Gate 2 — prove the design

After implementation, measurable terms are closed out from actual execution:

- p95 or other declared budgets;
- witnessed operator steps;
- hashes / content addresses where relevant;
- replay outcomes;
- observed refusal/gate behavior;
- final materialization posture;
- remaining or cleared TBCs.

Gate 2 is not permission to rewrite Gate 1 silently. If the build disproves an approved design term, that is a deviation and must be surfaced.

## The specification page shape

The current Standard uses seven sections in a fixed order:

1. **A — Decision frame**
2. **B — Contract**
3. **C — Data catalog**
4. **D — Assembly recipe**
5. **E — Volatility & materialization**
6. **F — Source binding & readiness**
7. **G — Operate & govern**

This ordering is useful to adoption because it keeps the product business-first while still producing an implementation artifact detailed enough for engineering and second-line review.

## A practical assembler conversation

Before writing the spec, the SME and data engineer should be able to answer:

- What decision is being made, by whom, and when?
- What would a context-starved or stale answer get wrong?
- Which relationships/time/policy/perspective dimensions change the answer?
- Which data exists publicly, which exists only inside the institution, and which condition must be engineered for the demonstration?
- What must fail closed rather than degrade silently?
- What evidence must travel with the answer so a reviewer can reconstruct it later?
- What is explicitly outside the product's scope?

Only after those are settled should implementation details be committed.

## Composition boundary — CP-14

The current approved documentation baseline covers specification of an individual Context Product. **Do not design the composite Context Product contract from the pre-CP-14 partial implementation.**

CP-14 is now available on current main. Use its [current implementation walkthrough](../../05-reference/02-context-product-producer/examples/CP14_CREDIT_MEMO_CONTEXT.md) and the [Context Product reference](../../05-reference/05-technical-reference/CONTEXT_PRODUCTS.md) when specifying:

- how constituent products are named and versioned;
- how dependency/request contracts compose;
- aggregate Context Debt semantics;
- aggregate lineage/replay semantics;
- TTL/freshness interactions;
- mixing/refusal policy;
- entitlement/perspective interactions;
- whether composite products add new specification elements or reuse the current seven-section contract.

These questions are addressed by the current composite contract and CP-14 evidence. The earlier source pin below records this guide's original specification-method provenance.

## Source references

Pinned Phase 4B sources:

- `public/reference/specifications/Context_Product_Specification_Standard_v0-3.md`
- `public/reference/specifications/spec_generation.md`
- `public/reference/specifications/example_delivery.md`

from `ccf_code/main@374a36007bb2fda3e968a83c2ead7d84993c0b23`.
