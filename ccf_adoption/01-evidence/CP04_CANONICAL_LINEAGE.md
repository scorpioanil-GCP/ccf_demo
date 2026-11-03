# CP-04 Canonical — Corporate Family Tree lineage exemplar

## Status

- **Adoption role:** Phase 1C.1 exemplar
- **Canonical SDK example:** `examples/cp-04-canonical-corporate-family-tree`
- **Historical/non-canonical example:** `examples/cp-04-corporate-family-tree`
- **Approved SDK baseline:** `ccf_code/main@1a04e565504f712350b51777cfe398be46d5e157`
- **Product:** `reference.corporate-family` at implementation major lane `2.0.0`
- **Tier:** T2
- **Assembly Mode:** 1 / pure algorithmic in the canonical SDK specification

This record demonstrates the Phase 1C lineage model. It is not the eventual public use-case page.

---

## 1. Business problem — why this exists

### Decision

A credit decision cannot reliably set or test family-level concentration by looking only at the legal borrower named on a facility. The relevant decision frame is the corporate family: parent, subsidiaries, control/ownership relationships and the ultimate parent that may connect apparently unrelated borrowers.

### Counterfactual failure

The Vault specification frames the failure as **Context Starved**: a conventional data product can return the immediate parent recorded in a CRM and still miss a shared ultimate parent several hops away. The concentration calculation can therefore look complete while using the wrong group boundary.

This is not primarily a model-quality problem. If the relationship was never assembled into the decision frame, a more capable model cannot recover it.

### Business personas

- credit officer / credit-risk user evaluating family-level exposure
- KYC analyst consuming the same corporate structure for a different downstream purpose
- downstream Context Products, especially exposure rollup

### Engineering persona

The data engineer / Context Product assembler must join graph relationships with relational entity attributes without pretending either source is complete by itself.

### Controls & governance persona

A controls/governance reviewer should be able to examine:

- the admitted family/policy envelope
- which source relationships were public vs engineered
- bounded traversal and technical refusal behavior
- measured Context Debt rather than implied completeness
- source lineage and store provenance
- replay evidence and content identity
- specification/version/change discipline

---

## 2. Whitepaper / Vault lineage

### Implementation-independent source

`obsidian-vault/wiki/context-products/content/corporate-family-tree.md`

The Vault defines the business problem and implementation-independent product shape: multi-hop family traversal, direct vs ultimate parent, cross-shareholding cycles as findings, and a multi-store requirement.

Important limitations already surfaced by the Vault include:

- GLEIF/API acquisition did not initially carry relationship valid-time even though the upstream golden copy did; that is a fetch/deferred-data issue, not proof that the source lacks valid time.
- consolidation basis requires a reified relationship representation rather than a bare edge.
- Exhibit 21 is not a complete ownership register and does not reliably provide ownership percentage; it is also legally materiality-filtered.
- an intent-bound ownership-materiality threshold was not present in the public/engineered estate described by the Vault spec.
- non-LEI subsidiary stubs require a visibly synthetic bridging identifier scheme.
- cross-shareholding cycles must be deliberately engineered and labeled if the public sample does not naturally contain them.

### Source-state caveat

The pinned Vault article still carries older frontmatter (`standard: q019`, `sdk_spec: null`, `owner: vault`) even though a canonical SDK implementation specification now exists. That is a source-state divergence to preserve, not silently normalize. The Vault remains authoritative for the business/implementation-independent term; the canonical SDK spec is authoritative for the current implementation term.

---

## 3. Dataprep lineage — what the estate actually provides

### Acquisition wave

Dataprep Wave 3 created the ownership graph:

- FIBO / OMG Commons ontology bindings
- GLEIF RR-CDF Level 2 parent/control relationships
- EDGAR Exhibit 21 subsidiary information
- relational identity/attribute spine in Postgres
- graph relationships in Fluree

### Public observed data

Representative public sources include:

- GLEIF Level 1 identity/attributes
- GLEIF RR-CDF Level 2 relationships
- FIBO / OMG Commons ontology terms
- EDGAR Exhibit 21 subsidiary disclosures where used in the engineered estate

### Engineered / synthetic data

Dataprep explicitly records an engineered cross-shareholding cycle in the ownership wave, labeled `synthetic — engineered`. Where public depth is too shallow, the acquisition plan also permits engineered depth padding, which must remain visible as engineered rather than implied observed structure.

### Data-reality lessons that must survive into adoption content

- **Fetch, extraction and engineering are different risk classes.** A fetch usually fails loudly; extraction can silently produce the wrong meaning; engineering is legitimate only when labeled.
- The public corporate-family estate is not a production bank master-data estate.
- Empty results can mean *not materialized/fetched*, not *does not exist*.
- Ontology bindings are themselves correctness-critical; an internally consistent graph can still be externally wrong if it uses invalid semantic bindings.
- Public filings can be disclosure-limited by regulation, so absence from Exhibit 21 is not proof of absence from the legal family.

### Not an SDK limitation

These public-source gaps and engineered conditions are estate limitations or demonstration choices. They must not be presented as defects in the CCF SDK unless executable SDK evidence independently demonstrates a defect.

---

## 4. SDK specification lineage

### Canonical implementation specification

`examples/cp-04-canonical-corporate-family-tree/spec/CP-SPEC-004C_Corporate_Family_Tree_Canonical.md`

The canonical specification is a **retrospective specification**, and it says so explicitly. The implementation predated this spec; it was added later to restore the rule that every example has its own specification and every gate traces to that specification.

That disclosure matters to the adoption portal because the normal method we want to teach is **spec first, approved, then build**. CP-04 canonical is useful precisely because it lets us teach both the preferred rule and an honestly disclosed historical exception.

### Current implementation focus

The canonical spec intentionally does not re-derive the whole corporate-family domain. It teaches the current producer shape:

- `boot / acquire / govern`
- bounded acquisition
- caller `max_depth` vs backend `depth_limit`
- thin edges before attributed nodes
- store pin as execution provenance, not product identity
- canonical producer shape detectable structurally

### Concrete source bindings

- Fluree `fibo-v2`: family edges, class chain and graph labels/identifiers
- PostgreSQL `ccf_v2`: GLEIF Level 1 attributes

Connection material is external to the specification; backend configuration carries variable names rather than credentials.

---

## 5. Executable behavior on the approved baseline

The canonical README and specification report that, at the demonstration's default governed depth, the served family contains 49 entities and 119 typed edges, with 29 entities resolved through the relational attribute leg. The example computes `D_c = 0.408163` on that answer.

At `max_depth=1`, it serves a smaller family and the debt changes to `0.555556`. A request beyond the backend depth ceiling is refused with technical authority rather than silently clipped.

These figures are **reproducible demonstration measurements**, not permanent product truths and should not be hard-coded as conceptual claims in the adoption portal.

The implementation also preserves corporate ownership circuits as findings rather than treating cycles as runtime errors.

---

## 6. Controls & governance lens

### Policy / entitlement

The request carries an admitted family set. The example distinguishes policy scope from technical backend capability rather than collapsing them into one bound.

### Temporal / freshness honesty

TTL is tied to source assertion state rather than a hidden request-time default. Where public source validity is not available, the adoption narrative must distinguish that limitation from transaction/assertion-time provenance.

### Context Debt

Debt is computed from the answer actually served. A governance reviewer can therefore see that a thinner answer has a different debt state rather than receiving one decorative global completeness score.

### Refusal posture

An unresolvable anchor or a request beyond the backend's governed ceiling produces a refusal rather than a plausible empty or clipped answer.

### Provenance and replay

The store transaction-time head is execution provenance and is not allowed to redefine product identity. Replay is richer than product lineage and preserves the governed context needed to reconstruct the serve.

### Separation of duties / source protection

The example reads both source systems read-only. Source acquisition logic is separate from the fabric's governed runtime, and connection secrets do not belong in the product specification.

### Model risk

Not applicable to the canonical CP-04 trust path: Assembly Mode 1 is pure algorithmic and invokes no model.

---

## 7. What CP-04 canonical proves

It demonstrates that the current SDK can:

- assemble one product from multiple source systems without pre-joining them
- traverse a governed graph at a request-dependent bound
- enrich graph results from a separate relational source
- surface partial attribute coverage as measured Context Debt
- preserve cycles as meaningful findings
- distinguish request governance from backend technical limits
- refuse unsupported requests rather than silently approximate
- carry source/runtime provenance and Decision Replay
- expose the current canonical producer pattern rather than the frozen historical shape

---

## 8. What it does not prove

It does **not** establish that:

- the public demonstration estate is a complete corporate-ownership master
- Exhibit 21 represents every subsidiary or ownership percentage
- every relationship has real-world valid-time available in the current loaded estate
- the engineered cycle is naturally observed public-company behavior
- the demonstration's entity/edge counts are stable production targets
- the current two-store demo covers all systems a bank would need in production
- a Mode 2/3 model-based assembly path has been validated by this example

Those boundaries should be visible near the example, not hidden in implementation notes.

---

## 9. Adoption-page implication

The eventual public example page should open with the concentration-risk business problem, not with Fluree, Postgres, Python or operator code. The specification should then show how the SME/data-engineer agreement becomes a buildable product design. Only after that should the page explain the engineered estate and implementation.

Recommended narrative order:

1. Business problem and decision
2. Why a flat/CRM answer fails
3. Personas, including controls/governance
4. What context must be assembled
5. Data reality and deliberate limitations
6. Specification and assembly approach
7. Current SDK implementation
8. Run it
9. Controls/governance evidence
10. What it proves / does not prove
11. Source lineage
