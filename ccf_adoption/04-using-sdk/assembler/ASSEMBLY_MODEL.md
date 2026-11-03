# The Context Product Assembly Model

## Learn responsibilities before helpers

The assembler should understand **where responsibility lives** before learning individual SDK functions. The CCF SDK mirrors the L1–L6 architectural model closely enough that this is a useful engineering map, not just whitepaper terminology.

## L1 — Signal Layer

**Responsibility:** ingest and normalize observations from heterogeneous sources.

The SDK boundary is `SignalEnvelope` plus `SignalSourceProtocol`. A signal carries provenance and temporal markers with an opaque payload.

**Invariant:** L1 does not interpret.

Examples of source-side work include transactional records, operational events, documents, transcripts, streams, and external feeds. Concrete adapters terminate in normalized envelope emission; they do not receive graph write access.

Assembler question: **What observations enter the fabric, with what source identity and time semantics?**

## L2 — Context Assembly

**Responsibility:** turn signals into governed graph state.

Four concerns converge here:

- semantic resolution;
- temporal stitching;
- policy binding;
- operator invocation.

The current SDK makes Assembly the **sole writer** to L3. That is an architectural invariant, not a style convention.

Assembler question: **How are observations resolved into typed state without losing time, policy, or provenance?**

## L3 — Context Graph

**Responsibility:** persist the typed state the fabric reasons over.

The SDK separates graph read and write Protocols and deliberately keeps the concrete writer private to assembly/boot paths. Other components read.

The graph is not a convenience cache over the source estate. It is CCF-owned computational state that can be queried as-of and replayed under the fabric's invariants.

Assembler question: **What entities, relationships, validity, policy, perspective-relevant state, and lineage must exist for this decision?**

## L4 — Context Operators

**Responsibility:** deterministic, typed computation over graph state.

The current SDK's canonical operator categories are composed into a plan. The package separates mechanism from values: parameter schemas may live in the SDK, but domain thresholds/rates/policy values do not become SDK defaults.

Current planner dependency order is:

**Policy → Similarity → Temporal → Traversal**

Operators are pure/read-only on graph state.

Assembler question: **What computations must run, in what declared composition, and what evidence proves each step actually executed?**

### Important: operator composition is not composite Context Products

L4 composition means composing computation inside the assembly of a Context Product. It is an established part of the current SDK.

CP-14's emerging **composite Context Product** capability is product-level composition across Context Products. It is a separate concern and remains outside the approved 4B contract.

## L5 — Context Projection (Π)

**Responsibility:** shape settled facts into a principal-conditioned decision view.

Projection is a typed transformation, not a post-hoc RBAC filter. The operator plan settles principal-agnostic facts; projection determines their decision significance for a consuming principal.

The same underlying graph state can therefore produce different typed Context Products for different roles without duplicating source truth.

Assembler question: **How should the same governed state be shaped for this role and intent?**

## L6 — Context Products

**Responsibility:** deliver a typed, governed, decision-ready unit of meaning.

The product class owns the request/contract surface, schema, validity/freshness expectations, lineage/replay relationship, entitlement at delivery, and the three validation-gate path that determines what can be served.

A Context Product is callable: subject, temporal boundary, and declared parameters belong to the request rather than being frozen into implementation configuration when they are genuinely caller-owned axes.

Assembler question: **What must the consumer be able to ask, what exactly can be served, and under what conditions must the fabric refuse?**

## Cross-cutting responsibility — Control Plane

The Control Plane carries versioned authored values that parameterize the mechanism:

- policy definitions;
- operator parameters;
- projection requirements;
- half-life rates;
- Context Debt thresholds/weights;
- materialization choices;
- product class declarations and related deployment artifacts.

The important discipline is **no invented defaults**. If the deployment has not declared a required domain value, the SDK should not silently manufacture one.

## Context Half-life and Context Debt

Half-life (`λ_c`) and Context Debt (`D_c`) are operational measures, not decorative metadata.

- Half-life models how decision relevance decays; it is not synonymous with TTL.
- Context Debt measures the gap between context required and context delivered, using versioned deployment calibration.

The assembler owns the evidence and calibration needed to make those measures meaningful for the product. The SDK owns the mechanism.

## Decision Replay

Replay is part of delivery, not an observability add-on.

The current replay model preserves five top-level dimensions and is designed to extend for later HITL, workflow, agent/harness, and model-mode evidence without replacing the baseline.

The assembler should be able to answer:

**Can an independent reviewer reconstruct what the fabric knew, which policy/version applied, which operations ran, what was asked, and what was served or refused?**

## Deployment wiring

`ccf.deployment` is the adopter-facing package for loading/deriving deployment configuration and wiring the fabric. It intentionally stops before taking over the product's validation responsibilities.

The deployment layer may:

- load `ccf_config.yaml` / manifest artifacts;
- resolve artifact classes/pins;
- build operator registries;
- boot dependencies.

It must not collapse authored claims and observed execution into the same value or run the product validation gates on the adopter's behalf.

That separation is what keeps a green gate from becoming tautological.

## A practical mental model

For one Context Product, think in this order:

1. **Decision:** what must be answered safely?
2. **Signals:** what observations exist?
3. **Assembly:** how are they resolved and governed?
4. **Graph:** what state must persist?
5. **Operators:** what deterministic computation is required?
6. **Projection:** what does this principal need to receive?
7. **Product:** what contract/request is served?
8. **Debt/freshness:** how good/current is the context?
9. **Replay:** can the decision substrate be reconstructed?
10. **Gates/refusal:** what prevents an unsafe product from crossing the boundary?

Only after those are explicit should the assembler optimize implementation ergonomics.