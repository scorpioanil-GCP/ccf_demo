# Financial Services example requirements

## Status

These requirements govern Phase 1C evidence mapping and the later Financial Services Use Cases section. They are product-design constraints for `ccf_adoption`, not optional editorial preferences.

## 1. Personas: add controls and governance explicitly

Financial-services examples must work for more than developers. Each substantial example should identify what each of these readers cares about:

- **Business / domain SME** — the real decision, business consequence, policy or workflow context, and whether the assembled product reflects domain reality.
- **Data engineer / Context Product assembler** — source estate, specification, element-to-source bindings, operator composition, temporal semantics, provenance, policies, tests, and operational limitations.
- **Consumer / agent developer** — how the Context Product is discovered, called, interpreted, refused, and integrated without needing producer internals.
- **Controls / governance persona** — policy binding, entitlements, lineage, evidence, replay, data classification, information barriers, residency, change control, approval boundaries, and what must fail closed.
- **Platform / operations persona** — deployment, observability, source availability, degradation, SLOs, retention, versioning, and production operation.
- **Model-risk persona when Assembly Mode 2 or 3 is used** — model/version pinning, prompt versioning, validation status, substrate-vs-presentation boundary, and smoothing/conflict controls.

Controls and governance are not an appendix. They should appear alongside the business and engineering narrative wherever the example exercises a control-bearing behavior.

## 2. The specification is a primary engineering artifact

The Context Product specification is the bridge from the business problem to implementation.

The intended collaboration model is:

1. **SME and data engineer agree the decision and assembly approach.** They establish what problem is being solved, what context is required, which sources and relationships matter, what temporal/policy conditions apply, and what an acceptable assembled answer looks like.
2. **AI tooling may accelerate specification authoring.** Once the SME and engineer agree the approach, AI can draft the specification, reconcile sections, identify missing fields, generate candidate acceptance tests, and help keep the document internally consistent.
3. **AI is not the authority for a missing term.** It must not invent a source system, threshold, policy rule, data availability claim, ontology binding, or business requirement. Unknowns remain explicit TBCs owned by the responsible source/role.
4. **The spec is reviewed before implementation.** Engineering proceeds from the agreed and approved design, and later build evidence discharges the claims in the spec rather than silently rewriting the design to match what happened to be implemented.

This is consistent with the existing three-owner evidence model in `ccf_code/public/reference/specifications/spec_generation.md`:

- Vault owns **why the Context Product exists**.
- `ccf_dataprep` owns **what data exists and its measured reality**.
- `ccf_code` owns **what the SDK implementation does**.

The adoption portal should teach that collaboration explicitly. The point is not "AI writes the spec." The point is **SME + data engineer settle the design; AI helps turn that settled design into a rigorous, reviewable, falsifiable specification.**

## 3. Every example begins with the business problem, before engineering

A Financial Services example must not open with Python, YAML, graph topology, or an SDK class.

The opening must first establish the real-world problem from which the example was derived. The current CP examples were not invented as technical demonstrations: the Vault extracted real use cases from the CCF whitepaper, shaped them into implementation-independent Context Product requirements, and the SDK examples were then built to solve those problems.

Every substantial example page should therefore begin in this order:

1. **Business problem** — recognizable to a banker, risk/control partner, or domain SME.
2. **Decision being supported** — who is deciding what, and what triggers the decision.
3. **Why the ordinary data/retrieval approach is insufficient** — the concrete counterfactual failure.
4. **Business consequence of getting the context wrong** — risk, client, operational, regulatory, or financial impact.
5. **Context required** — the major signals, relationships, time/policy/perspective requirements.
6. **Control/governance concerns** — what must be policy-bound, evidenced, replayable, or fail closed.
7. **Only then: the Context Product design and SDK implementation.**

This narrative should be sourced primarily from the Vault article and, where useful, the whitepaper passages from which the Vault derived the use case. The engineering material follows the problem narrative; it does not replace it.

## 4. Engineered/public data limitations must be explicit

The examples use public data plus engineered relationships and scenarios. That is a strength for reproducibility, but it creates known limits relative to an actual bank estate.

Some limitations were deliberately accepted because the public data needed to demonstrate the full production condition does not exist. These are often already documented in the CP specification, README, `ccf_dataprep` known-issues material, or the example's gate/findings record.

Each Financial Services example must include a visible **Data Reality & Deliberate Limitations** section that distinguishes:

- what came from public source data;
- what was engineered to create a realistic multi-system decision condition;
- what production data would normally exist but could not be reproduced publicly;
- what simplifications were deliberately taken;
- why the simplification was acceptable for the mechanism being demonstrated;
- what the example **does prove** despite the limitation;
- what the example **does not claim to prove** because of it.

A deliberate data limitation must never be presented as an SDK limitation. Conversely, an actual SDK limitation must not be hidden behind the phrase "engineered data."

Phase 1C must therefore join not only Vault → Dataprep → SDK example, but also the limitation evidence carried in the spec/README/known-issues/gate material.

## 5. Specification/reference templates must be showcased

The approved `ccf_code/main` baseline contains three important public reference artifacts under `public/reference/specifications/`:

### `Context_Product_Specification_Standard_v0-3.md`

Purpose: format contract for a Context Product specification. It defines the seven-section structure (Decision frame, Contract, Data catalog, Assembly recipe, Volatility & materialization, Source binding & readiness, Operate & govern), the four-question build test, placeholder discipline, policy/classification/residency requirements, and the falsifiability posture.

Adoption placement:

- **Using the SDK → Assembler → Design a Context Product** — showcase the section skeleton and explain how an SME and data engineer use it together.
- **Reference Manual / Specifications** — full reference, versioned and pinned.
- **Governance & Controls** — cross-link the policy, classification, residency, replay, model-risk, and second-line portions rather than duplicating them.

### `spec_generation.md`

Purpose: recipe for generating an SDK-level CP spec from the three authorities: Vault (`why`), Dataprep (`what data exists`), and SDK (`what it does`). It also defines the spec-first / approval-before-build sequencing.

Adoption placement:

- **Using the SDK → Assembler → From business problem to approved spec**.
- **Adoption Guide → Team operating model** — useful for explaining SME/data-engineer/AI collaboration and ownership boundaries.
- **Financial Services Use Cases** — link from each example's "How this example was formed" section.

### `example_delivery.md`

Purpose: recipe for everything after specification approval — building, making the example runnable, README/run-block discipline, rendered page mechanics, summary explanations, and validation.

Adoption placement:

- **Using the SDK → Assembler → Build and validate the example**.
- **Financial Services Use Cases → Contributor / reproduction guidance**.
- **Operations / Production** — cross-link validation, environment, and reproducibility practices where appropriate.

### Template publication rule

These reference files are current evidence, but not all are necessarily frozen long-term contracts. Before copying or presenting one as authoritative in `ccf_adoption`, reconcile its version/status against the then-current approved `ccf_code/main` baseline. Prefer a versioned snapshot/provenance model over an unqualified copy.

## 6. Required Financial Services example page shape

The eventual example-page template should contain, at minimum:

1. **Business Problem**
2. **Decision & Personas**
3. **Why Conventional Retrieval/Data Products Are Insufficient**
4. **Business / Risk / Control Consequence**
5. **Context Required**
6. **How This Example Was Formed** — Whitepaper → Vault → spec → Dataprep → SDK example
7. **Data Reality & Deliberate Limitations**
8. **Context Product Specification** — link/snapshot and key design decisions
9. **Assembly Architecture**
10. **Control & Governance View**
11. **Implementation Walkthrough**
12. **Run It / Expected Result**
13. **What the Example Proves**
14. **What It Does Not Prove**
15. **Evidence & Lineage** — source commits/artifacts/tests/gates

The exact visual design can change in Phase 2, but the narrative order is load-bearing: **problem first, specification second, engineering third, evidence throughout.**

## 7. Phase 1C implications

For every CP mapped in Phase 1C, capture at least:

- Vault article / use-case source
- whitepaper origin where traceable
- business problem and decision
- SME/business personas
- controls/governance personas and concerns
- SDK CP spec path
- spec maturity/status
- Dataprep datasets and relationships
- Dataprep known issues / deliberate engineered-data limitations
- SDK example path (canonical path where aliases/retired paths exist)
- example README limitations
- implementation capabilities exercised
- tests/gates proving the behavior
- explicit unresolved/TBC gaps

This is the evidence backbone for Phase 6. It should make it possible to write a Financial Services example without inventing narrative, data reality, or control claims later.
