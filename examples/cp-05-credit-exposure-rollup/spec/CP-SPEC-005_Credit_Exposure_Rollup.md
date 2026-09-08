---
product: credit-risk.exposure-rollup.v1
spec_version: v1.0.0
standard: v0-3
vault_article: credit-exposure-rollup
vault_standard: q019
owner: sdk
tier: 2
cost_band: "×1–2"
assembly_mode: derived-on-demand
capability_classes: [relational, graph-traversal, in-memory]
stores: [postgres, fluree]
prerequisites: [corporate-family-tree, facility-terms-snapshot]
ladder_rung: 5
authored: 2026-09-07
status: AUTHORED — awaiting Dave's Gate 1 review
---

# Credit Exposure Rollup — Context Product Specification

**Tier 2** · Postgres + Fluree · `credit-risk.exposure-rollup.v1` · cost band ×1–2
**Rung 5 of the ladder.** Prerequisites `corporate-family-tree` (rung 4) and
`facility-terms-snapshot` (rung 2), both built.

> Aggregates committed and outstanding exposure across a corporate family,
> following guarantee and cross-default edges rather than legal-entity
> boundaries. Traversal plus arithmetic — and the arithmetic is where the
> architecture earns its keep.

---

## 0 · What this document is

This is the **SDK specification** for one Context Product: the buildable
second-level document that turns the vault's product article into something a
`ccf_code` session can implement without inventing a term. The vault owns the
product's *meaning*; this document owns its *construction*. Where the two could
diverge, the vault wins and the divergence is recorded rather than resolved
silently (`spec_generation.md` §1, §10).

**The vault article is on the q019 form.** Its `§F` heading is *Manufacture
envelope*, not *Source binding & readiness*. This specification is on **v0.3**,
where §F is *Source binding & readiness*. Vault sections are therefore resolved
**by heading name, never by letter**, and the vault's manufacture-envelope
conditions appear here in **F.1** and **F.3**.

**Every number in this document was measured against the live estate on
2026-09-07**, not carried from the vault or estimated. `bound is not the same as
materialized`: an IRI in the binding mirror does not mean rows exist against it.
Where a count appears, the query that produced it is stated with it.

### 0.1 Do you need a Context Product? — the four-question test

> ⚠ **The vault article carries no four-question test result**, which
> `spec_generation.md` §4.1 lists among the items to extract *"including
> partials and nos."* Measured: `grep -c "four-question"` over the article reads
> **0**. The test below is **SDK-authored against the estate**, not transcribed
> from the vault, and is registered for vault confirmation in F.2.

| Question | Answer | Consequence |
|---|---|---|
| **Does the answer require more than one system of record?** | **Yes.** Ownership, guarantee and cross-default edges live in Fluree; commitments, balances, limit definitions and the reconciliation live in Postgres. | Two stores, one contract. A flat query against either alone is structurally unable to answer. |
| **Does the answer depend on graph structure rather than a key?** | **Yes.** Exposure follows guarantee and cross-default edges, which cross legal-entity boundaries. Four entities in this estate sit in a cross-default chain while holding no facility of their own. | A borrower-keyed sum cannot find them. This is the product's reason to exist. |
| **Does the answer change with who is asking, or under which policy?** | **Yes.** The group-limit definition is versioned policy bound to `intent`. Measured: `internal-appetite` sets `counts_guarantees=false` and `counts_undrawn=false`; `group-limit-test` sets both `true`. | The same anchor yields a different number under a different intent, by data rather than by code. |
| **Is the answer time-sensitive in a way a cached table would get wrong?** | **Yes.** Outstanding balances move intraday (`λ_c` ≈ 4 h) while structure moves annually. | Materialization is the **wrong** posture here — see E.3. This is the first rung where that is true. |

Four yes. The product is warranted.

### 0.2 Placeholder discipline

Every `[TBC]` in this document carries a named owner and appears again in **F.2**
with that owner and what unblocks it. A spec with honest gaps is buildable; a
spec with hidden gaps is not. There are **no** `[TBC]` markers gating the build
of this product — F.2 records the two that exist and why neither blocks.

### 0.3 Section skeleton

`A` decision frame · `B` contract (B.1–B.5) · `C` data catalog (C.1–C.5) ·
`D` assembly recipe (D.1–D.7) · `E` volatility, debt & materialization (E.1–E.5) ·
`F` source binding & readiness (F.1–F.4) · `G` operate & govern (G.1–G.3).

### 0.4 Front matter

**Registry name** `credit-risk.exposure-rollup.v1` · **tier** 2 ·
**Assembly Mode** derived on demand · **cost band** ×1–2 ·
**capability classes** relational, graph-traversal, in-memory ·
**stores** Postgres (`ccf_v2`) + Fluree (`fibo-v2`).

**What it resolves, in two sentences.** Given one anchor obligor and a stated
intent, it returns total committed and outstanding exposure across that
obligor's corporate family, following guarantee and cross-default edges and
deduplicating exposure that a guarantee has already captured at the parent. It
emits both gross and guarantee-adjusted measures so the consumer can see what
the adjustment did, rather than being handed one number and asked to trust it.

**A capability the estate may not have.** None. Every element in C.1 was
measured present on 2026-09-07 and the counts are in F.1. This product is
buildable today.

---

## Section A — Decision frame

**Decision & trigger.** A credit officer or portfolio manager is testing a
proposed facility against a group limit, or answering *"what do we actually have
on this name?"* ahead of a committee.

**Consuming principals.** Single role at this tier. Perspective conditioning is
not exercised here; it arrives at rung 18.

**Counterfactual failure — Context Starved, compounding.**

Taken verbatim from the vault, because it is the product's whole argument:

> Exposure is not additive across a legal-entity list. A guarantee from the
> parent means the subsidiary's exposure is *also* the parent's. A cross-default
> clause means a breach at one entity accelerates obligations at another. A data
> product that sums facility balances by borrower LEI produces a number that is
> confidently wrong in both directions: it double-counts where a guarantee
> already captured the risk, and it under-counts where a cross-default binds an
> entity that holds no facility at all. The error is invisible in the output — a
> number is returned, it looks like an exposure, and nothing signals that the
> graph structure it should have respected was never traversed.

**Both directions of that error are live in this estate, measured:**

- **Double-counting.** `ccf_v2.guarantee_terms` carries **4 rows** of
  `kind = 'downstream-dedup'` — cases where a parent's guarantee already
  captures a subsidiary's exposure, so a naive sum counts it twice.
- **Under-counting.** Of the **20** distinct entities reachable across the
  **15** `crossDefaultsWith` edges, **4 hold no facility of their own**. A
  borrower-keyed sum cannot reach them at any depth, because it never looks at
  an edge.

**Why the failure is silent.** Neither error raises. The naive number is
well-formed, plausibly sized, and wrong. That is what makes this a Context
Product rather than a query: the correction is structural, and a consumer has no
way to detect its absence from the output alone. This product therefore emits
**gross and adjusted side by side** (D.6) and refuses to emit only the adjusted
figure — the difference *is* the evidence.

**Primitive taught.** Traversal composed with algorithmic aggregation, under a
policy regime that decides what counts. Contrast pointer: `corporate-family-tree`
uses the same traversal machinery and takes the **opposite** materialization
posture (E.3).

---

## Section B — Contract

### B.1 The nine elements

| # | Element | Value |
| --- | --- | --- |
| 1 | **Schema** | Payload type `credit_exposure_rollup`. Entities: **LegalEntity** (the anchor and every entity reached) and **CreditFacility**. Relationships carried into the payload: `owns` / `isUltimatelyConsolidatedBy` (ownership), `isGuarantorOf` (guarantee), `crossDefaultsWith` (cross-default), `hasBorrower` (facility → obligor). Measures, each emitted **twice — gross and guarantee-adjusted**: committed, outstanding, undrawn. Reported **by entity and by group**. |
| 2 | **Freshness SLA** | **Per signal class, not one value for the product.** Outstanding balances **intraday**; guarantee and cross-default structure **daily**; ownership edges **daily**; group-limit definition **on policy review**. The per-class shape is the point: a single product-level SLA would either over-promise on structure or under-promise on balances. |
| 3 | **TTL** | **4 hours · `ttl_anchor: from_decision`.** The anchor **flips** from `facility-terms-snapshot`'s `from_entity_freshness`. Exposure is meaningful only for the duration of the decision taken against it; there is no underlying entity whose validity period governs it. Two products, two anchors, and the difference is a property of *the decision*, not of the data. `expires_at` = request time + 4 h. |
| 4 | **Policy Binding** | Regime: **internal credit policy**, versioned in `ccf_v2.limit_definition` and bound to the request's `intent`. Measured — three intents, and they genuinely differ: `group-limit-test` (`counts_guarantees=true`, `counts_undrawn=true`, `connection_basis=control`, limit 25% of capital); `regulatory-large-exposure` (`true`, `true`, `both`, 25%); `internal-appetite` (**`false`, `false`**, `control`, 15%). Entitlement scope bound to the entitlement service. Data classification **confidential** (B.2). Because the limit definition is versioned policy rather than code, a change to it changes every rollup, and the lineage record shows which definition produced which number. |
| 5 | **Lineage** | `operators_invoked: [Resolve, Policy, Traversal, Enrich, Aggregate]` · `graph_snapshot_at` — the Fluree ledger `t` at which the traversal read · `policy_version` — the `limit_definition` row version in force · plus source accession for each Postgres element. Lineage strict equality is a validation gate (D.7), not a debug aid. |
| 6 | **Semantic Version** | **v1.0.0.** First supported version; no migration window. |
| 7 | **Discovery** | `credit-risk.exposure-rollup.v1`. |
| 8 | **Addressability** | `/context-products/credit-risk/exposure-rollup/{lei}` — anchored on the **obligor LEI**. |
| 9 | **Assembly Mode** | **2 — algorithmic with a graph traversal.** Rationale in one sentence: every step is deterministic arithmetic or a typed graph walk, and no semantic stage is invoked at any point, so the product is fully replayable from the graph snapshot plus the policy version. |

> **A note on the figures in this document, required and meant.**
>
> These examples teach **method** — how to engineer and construct a Context
> Product with the CCF SDK — not the figures.
>
> **Entity identities are real.** The anchor used throughout is
> `5493000Q1S5TJIDIQH89` — **Regis Corporation**, a real LEI, a real
> jurisdiction (`US-MN`) and a real SIC code (7200), as filed.
>
> **The bank's book is engineered.** Every facility, commitment, outstanding
> balance, undrawn availability, guarantee edge, cross-default edge and
> group-limit definition is **synthetic — internal**. No bank lends to Regis
> Corporation on these terms, because the lender does not exist. The topology
> was engineered so the product's failure modes are demonstrable rather than
> hypothetical, and it is calibrated against public reality: committed exposure
> reconciles to **49.4%** of the obligor's XBRL-reported total debt, which
> `ccf_v2.debt_reconciliation` flags `plausible = true`.
>
> **No number here is a claim about any real company's borrowings.**

### B.2 Classification and residency

**Data classification: `confidential`** — the highest classification of any
element in C.1. Ownership, guarantee and cross-default topology derived from
EDGAR are `public`; facility commitments, outstanding balances, undrawn
availability, borrower-of edges and limit definitions are `synthetic — internal`
standing in for material non-public bank book data, and are classified as the
real thing would be.

**Residency.** Single jurisdiction, US. No cross-border transfer constraint is
exercised at this rung; it arrives at rung 20 with A2A.

**Consequence for delivery.** A `confidential` payload may not be served to an
unentitled principal, and the entitlement check is a Policy-operator step
(D.3 step 2) rather than a filter applied to a computed answer. The distinction
matters: computing an exposure and then withholding it still computed it.

### B.3 Model-risk annotation

**No model.** No LLM, no scoring function, no estimator participates in
construction. Every emitted figure is a sum, a difference, or a filter over
rows and edges the estate holds. SR 11-7 model-risk treatment therefore does
not attach to this product's *construction*.

It does attach to the **group-limit definition** (`ccf_v2.limit_definition`),
which is a policy artifact with its own owner and review cycle. This product
consumes that definition by version and records which version it consumed; it
does not interpret, extend or default it. Where a limit definition is absent
for a requested `intent`, the product **refuses** (E.5) rather than falling back
to a default — a silently defaulted limit definition is the failure this
annotation exists to prevent.

### B.4 Request parameter surface

| Parameter | Type | Moves | Default | Notes |
|---|---|---|---|---|
| `lei` | string(20), **required** | anchor | — | Must resolve through `ccf_v2.legal_entity`; an unresolvable LEI refuses rather than returning an empty rollup. |
| `intent` | enum, **required** | selects limit definition and policy envelope | — | One of the three measured values. **No default** — see B.3. |
| `depth` | int 1–5 | `R` scope | **3** | Ownership walk depth. |
| `materiality` | decimal 0–1 | `R` filter | **0.05** | **The caller's decision tolerance, not a fact about the family.** Entities below this share of group exposure are aggregated into a residual rather than enumerated; it does NOT apply to zero-exposure entities reached by cross-default (§C.4 trap 2). **See B.4.1 — 5% is the product DEFAULT, not the product TRUTH.** |
| `follow_guarantees` | bool | `R` scope | **true** | |
| `follow_cross_default` | bool | `R` scope | **true** | |
| `basis` | enum `committed` \| `outstanding` \| `both` | measure | **both** | |

#### B.4.1 The effective threshold is resolved at request time

**5% is the product default. It is not the product truth.** The truth is:
*return family exposures above the **effective** materiality threshold* — and
that threshold is resolved per request under the authority model the SDK already
defines (`ccf.products.provenance::Authority`, the literal
`['default', 'caller', 'policy', 'technical']`):

> **policy boundary > caller value > product default**, with `technical`
> bounding all three.

Three clients wanting 2%, 5% and 10% are **three parameterizations of one
product**, not three products. The author defines the parameter and its domain;
the caller may override inside it; policy may constrain it further; and the
**effective value together with its authority is recorded on the answer**, so
replay reconstructs the question rather than only the numbers.

Measured on the demonstrated anchor:

| Caller | Effective | Authority | Material entities |
|---|---|---|---|
| supplies nothing | `0.05` | `default` | 4 |
| asks `0.10` | `0.10` | `caller` | 3 — RB Global drops out at 7.9% of the family |
| asks `0.02` | `0.02` | `caller` | 4 |
| asks `0.01` | `0.01` | `caller` | **5 — the anchor itself comes into view** |
| asks `0.10` under `internal-appetite` | — | **refused** | *"exceeds the applicable maximum 0.05 established by authority 'policy'; the request is refused rather than narrowed, because a narrowed request answers a question nobody asked"* |

Each threshold produces a **different content address**: one product, one
assembler, three governed projections.

**This resolves what an earlier draft recorded as a defect.** F.4 noted the
anchor falls below its own materiality floor and is filtered from the enumerated
entities of its own rollup. That is not a defect to special-case — it is a
parameterization, and at `0.01` the anchor appears. Exempting it would have
hard-coded one consumer's tolerance into the product.

**The implementation resolves nothing itself.** `deployment.py::effective_request`
assembles four inputs and hands them to
`ccf.products.constraints::resolve_effective_request`; the precedence, the bounds
and the refusals are the SDK's.

**`follow_guarantees` and `follow_cross_default` are separable on purpose**, and
this is a contract commitment rather than a convenience. Different limit regimes
count them differently, and a product that hard-codes one interpretation cannot
serve two regimes. The estate proves the need: `internal-appetite` sets
`counts_guarantees = false` while `group-limit-test` sets it `true`.

**The two flags and the policy regime can disagree, and the resolution is
ruled here:** the **policy regime wins**, and the disagreement is reported as a
finding on the product rather than resolved silently. A caller who sets
`follow_guarantees=true` under an intent whose definition says
`counts_guarantees=false` gets the guarantee edges **traversed** (so the family
is complete) and **not counted** in the adjusted measure (so the limit test is
correct), with a finding naming the conflict. Traversal scope and measurement
policy are different questions and the contract keeps them apart.

### B.5 Prerequisites, consumers and scope boundary

**Prerequisites.** `corporate-family-tree` (rung 4) — supplies the ownership
traversal pattern and the cycle-as-finding discipline. `facility-terms-snapshot`
(rung 2) — supplies facility commitment and terms.

**Consumers.** Credit officers and portfolio managers, through a single role at
this tier. Downstream on the ladder, `large-exposure-rwa-concentration`
(rung 21) composes this product.

**Scope boundary — ⚠ THE VAULT ARTICLE CARRIES NONE. What follows is
SDK-supplied and needs vault confirmation (F.2).**

`spec_generation.md` §4.1 requires the scope boundary to be recorded *verbatim*
from the vault. **It cannot be, because the vault article has no scope-boundary
section** — measured: `grep -c "scope boundary"` over the article reads **0**,
and the MCP copy is byte-identical to the copy on disk, so this is an absence in
the article rather than a read failure.

The boundary below is therefore **derived by the SDK** from the article's tier-2
framing and from `corporate-family-tree`'s precedent, and is flagged for the
vault to confirm or replace:

> *(SDK-supplied, pending vault confirmation)* Single institution. No external
> fabric is reached.

**What that excludes, stated so no one has to infer it:** no A2A, no second
CCF instance, no co-lender view, no netting against another bank's book. Those
arrive at rung 20 (`syndicated-lending-co-lender`). This product's MCP door
(G.1) is an egress surface for consumers **inside** the tenant boundary.

**An earlier draft of this section presented that sentence as a verbatim vault
quotation. It was not one** — the wording was carried from
`examples/cp-04-corporate-family-tree/artifacts/assembly-recipe.yaml`, a
different product's artifact, and mis-attributed. Corrected here, and recorded
rather than quietly amended because a fabricated citation is the defect class
this project treats most seriously.

---

## Section C — Data catalog

### C.1 Element table

`G` is the CCF dimension the element serves: `R` relationship · `E` entity
attribute · `P` policy. Counts measured 2026-09-07 against Postgres `ccf_v2` and
Fluree ledger `fibo-v2`.

| Element | Provenance | Class | Store | `G` | Measured |
|---|---|---|---|---|---|
| Ownership edges | inherited from `corporate-family-tree` | public | **Fluree** | `R` | `owns` **636**; `isUltimatelyConsolidatedBy` **140**; `isDirectlyConsolidatedBy` **140** |
| Guarantee edges — guarantor → obligor | EDGAR EX-10 guarantor schedules and subsidiary guarantees | public topology, engineered coverage | **Fluree** | `R` | `isGuarantorOf` **27** |
| Cross-default edges | EX-10 cross-default clauses; 10-K debt footnote | public topology, engineered | **Fluree** | `R` | `crossDefaultsWith` **15**, reaching **20** distinct entities |
| Borrower-of edges — facility → obligor | internal loan system | **synthetic — internal** | **Fluree** | `R` | `hasBorrower` **45** |
| Facility commitment and terms | inherited from `facility-terms-snapshot` | **synthetic — internal** | Postgres | `E` | `facility` **60** rows across **22** distinct borrowers |
| Outstanding balance · undrawn availability | internal loan system | **synthetic — internal** | Postgres | `E` | columns `outstanding_balance`, `undrawn_availability` on all 60 |
| Aggregate reported debt (reconciliation check) | XBRL `companyfacts` — total debt | public | Postgres | `E` | `debt_reconciliation` **14** rows |
| Group-limit definition by intent | internal credit policy | **synthetic — internal** | Postgres | `P` | `limit_definition` **3** intents |
| Guarantee coverage percentage and caps | EX-10 guarantee terms where stated; otherwise internal | mixed | Postgres | `E` | `guarantee_terms` **28** — `upstream` **24**, `downstream-dedup` **4** |
| Entity identity | GLEIF / EDGAR | public | Postgres | `E` | `legal_entity` **156** |

**The reconciliation the public data makes possible, and its one honest miss.**
Total synthetic facility commitments for a public anchor can be sanity-checked
against XBRL-reported total debt. They will not match — the bank holds only part
of the borrower's debt — but the synthetic figure should be a *plausible share*
of the real one. Measured: **13 of 14** obligors carry `plausible = true`;
**one does not**. That row is not hidden and not repaired here (F.4); a spec
that reported 14 of 14 would be describing a different estate.

### C.2 Capability decomposition

| Capability class | Where it is exercised | Store |
|---|---|---|
| **relational** | Resolve (anchor → canonical obligor), Policy (limit definition by intent), Batch Enrich (entities → facilities and balances), reconciliation read | Postgres |
| **graph-traversal** | one walk over ownership, guarantee and cross-default predicates | Fluree |
| **in-memory** | Aggregate: sum by entity, sum by group, guarantee-path deduplication, materiality filter, gross-vs-adjusted emission | none — algorithmic |

**No similarity, no semantic stage, no model.** The Algorithmic ⇄ Semantic
Alternation is satisfied trivially at this rung: every stage is algorithmic, and
no LLM client may be imported by any module implementing this product.

### C.3 Correlation key, single-writer discipline, and identity authority

**Correlation key.** `LEI` for entities; `facility_id` for facilities. Both
resolve through `ccf_v2.crosswalk` (**83** rows, mapping
`internal_client_id ↔ lei ↔ cik ↔ ticker`).

**Identity authority.** GLEIF's LEI is authoritative for entity identity. The
internal client id is *not* an identity — it is a bank-side handle that the
crosswalk maps to one. Where the two disagree, the LEI wins and the
disagreement is a finding.

**A join hazard, recorded because it caught the author.** Fluree subjects are
addressed by **entity slug** (`…/RegisCorporation`), while Postgres keys on
**LEI**. Joining slugs to LEIs directly yields a 100% miss rate that looks like
a finding rather than a defect. The ledger's own `lei` predicate is the bridge,
and every cross-store join in the implementation **must** go through it or
through the crosswalk. An implementation that appears to discover that no
entity holds a facility has made this mistake.

**Single-writer.** This product **writes nothing**. It is a read-only assembly
over two systems of record; L2 remains the only writer to the graph, and
nothing in this product acquires a write handle to either store.

### C.4 The three data traps, each with the binding chosen and what it costs

**Trap 1 — the guarantee double-count.** A parent guarantees a subsidiary that
holds its own facility. Summing facility balances by borrower counts that
exposure twice: once at the subsidiary as borrower, once at the parent as
guarantor. **Binding chosen:** deduplicate at the guarantee edge — where a
guarantee already captures a subsidiary's exposure at the parent, count it
once, and emit the gross figure alongside so the adjustment is visible.
**What it costs:** the adjusted figure is no longer reproducible by a consumer
with a spreadsheet, which is precisely why gross must ship beside it.
**Live in this estate:** `guarantee_terms.kind = 'downstream-dedup'`, 4 rows.

**Trap 2 — the cross-default blind spot.** A cross-default clause binds an
entity that holds no facility at all. A borrower-keyed sum cannot reach it,
because it never examines an edge. **Binding chosen:** traverse
`crossDefaultsWith` as a first-class predicate in the same walk, and include
reached entities in the family even when they contribute zero facility
exposure — their presence is the finding. **What it costs:** the family is
larger than a facility list suggests, and the materiality filter must not
silently drop a zero-exposure entity that a cross-default reached; such an
entity is reported as connected-with-no-exposure rather than aggregated into
the residual. **Live in this estate:** **4** of the 20 entities in cross-default
chains hold no facility.

**Trap 3 — the policy-shaped number.** "Total exposure" is not a property of the
data; it is a property of the limit definition in force. Undrawn commitments
count under one regime and not another. **Binding chosen:** the limit definition
is read from `ccf_v2.limit_definition` by `intent`, its version is recorded in
lineage, and the product never defaults it. **What it costs:** a caller must
state an intent, and there is no "just give me the number" path. That is
deliberate — the number without the intent is the confidently-wrong figure §A
describes. **Live in this estate:** `internal-appetite` counts neither
guarantees nor undrawn, against `group-limit-test` which counts both.

### C.5 What this data is — stated once more, because it is the point

The entity layer is real: 156 legal entities with real LEIs, jurisdictions and
SIC codes, and an ownership graph derived from public filings. The **bank's
book is engineered** — facilities, balances, guarantee coverage, cross-default
topology and limit definitions are synthetic, standing in for data no public
source carries.

The engineering is not arbitrary. The topology was built so that both halves of
§A's counterfactual are demonstrable — 4 dedup cases and 4 cross-default-only
entities — and the book is calibrated so committed exposure is a plausible
share of publicly reported debt in 13 of 14 cases. **That calibration is what
makes the demonstration honest**: a product that produced correct arithmetic
over an implausible book would prove the arithmetic and nothing else.

---

## Section D — Assembly recipe

### D.1 Client call

```
GET /context-products/credit-risk/exposure-rollup/5493000Q1S5TJIDIQH89
      ?intent=group-limit-test
      &depth=3
      &materiality=0.05
      &follow_guarantees=true
      &follow_cross_default=true
      &basis=both
```

**The anchor is `5493000Q1S5TJIDIQH89` — Regis Corporation** — chosen because it
exercises every step rather than because it is the largest book. Measured:
**4 facilities** (Term Loan 70,000,000 · Revolving Credit Facility 35,000,000 ·
Term Loan A 25,000,000 · Term Loan B 15,000,000 = **145,000,000 committed**;
**111,497,463 outstanding**; **31,447,787 undrawn**), it **gives 5 guarantees**,
one of which is a `downstream-dedup` case, and its committed exposure is
**49.4%** of XBRL-reported total debt with `plausible = true`.

An anchor with facilities but no guarantees would let a naive implementation
pass. This one will not.

### D.2 Operator step table

| # | Operator | Store | Reads | Emits | May be empty? |
|---|---|---|---|---|---|
| 1 | **Resolve** | Postgres | `legal_entity`, `crosswalk` | canonical obligor | **No** — an unresolvable anchor refuses |
| 2 | **Policy** | Postgres | `limit_definition` by `intent`; entitlement service | policy envelope, `policy_version` | **No** — a missing definition refuses (B.3) |
| 3 | **Traversal** | Fluree | `owns`, `isUltimatelyConsolidatedBy`, `isGuarantorOf`, `crossDefaultsWith`, `hasBorrower` | node set, edge set, ledger `t` | **No** — the anchor is always in the node set |
| 4 | **Batch Enrich** | Postgres | `facility`, `guarantee_terms`, `debt_reconciliation` | facilities and balances per entity | **Yes** — a family may hold no facilities |
| 5 | **Aggregate** | in-memory | steps 3 + 4 | gross and adjusted measures, findings | **No** |
| 6 | **Contract assembly** | — | all above | `CreditExposureRollupContract@v1.0.0` | **No** |

### D.3 Step detail

**Step 1 · Resolve — Postgres.** `lei` → canonical obligor via
`ccf_v2.legal_entity`. An LEI that does not resolve **refuses**; it does not
return an empty rollup. A zero-exposure answer for a real obligor and a
"no such obligor" answer are different facts, and the contract keeps them apart.

**Step 2 · Policy — Postgres.** Entitlement scope is checked **before** any
exposure is computed (B.2). The group-limit definition bound to `intent` is
loaded from `ccf_v2.limit_definition`: `counts_guarantees`, `counts_undrawn`,
`connection_basis`, `limit_pct_of_capital`. Emits `policy_version`. If the
caller's `follow_*` flags disagree with the definition, the definition governs
the **measure** and the flags govern the **traversal scope**, with a finding
recording the conflict (B.4).

**Step 3 · Traversal — and the distinction this rung exists to teach.**

> **Acquisition may use backend-specific logic; decision logic must execute
> through the declared fabric mechanisms.**

Reading the source estate over SPARQL is **acquisition**. It is backend-specific
by nature, has no SDK surface today (F.4, `D-IMPL-277`), and it **populates L3
without answering anything**. Deciding which entities constitute the family is
**decision logic**, and it runs through the operator the Control Plane
registered — `traversal.typed-neighborhood` — over a `GraphView` of L3 bounded
at the request's own instant, seeded from the entity class `ccf_config.yaml`
declares.

An earlier draft answered the question from the acquisition walk directly. It
produced the same 77 entities and **was not a Context Product**: the Control
Plane permitted a traversal that never ran, and a hand-rolled walk ran one it
never saw. The two agreeing at 77 is what licensed the demotion, not what
excused it.

**Step 3a · Acquisition — Fluree. One walk, several predicate types.** Walk
ownership to `depth`, and extend across `isGuarantorOf` and `crossDefaultsWith`
where the corresponding flags are set.

> **Do not issue one traversal per edge type.** This is the step where a naive
> implementation quietly becomes three round trips and a merge, and where the
> traversal's own `t` stops being a single snapshot. One walk, one ledger `t`,
> one node set. `corporate-family-tree` established the pattern; this product is
> where it starts to pay, because the predicate count rises from one to four.

Emits the node set, the edge set, and `graph_snapshot_at` = the ledger `t`.
Cycles are returned as **findings, not errors**, per the prerequisite product.

**Step 4 · Batch Enrich — Postgres. One query, not N.** A single query resolves
every returned entity to its facilities, balances and guarantee terms.

> Fan-out here is **entity × facility**, so the N+1 penalty is *multiplicative*
> rather than linear — the batch pattern matters more than it did at
> `corporate-family-tree`, where fan-out was entity-only. An implementation that
> issues one query per entity is not slow; it is wrong at scale, and the
> difference shows up as a latency cliff rather than an error.

Entities with no facility are retained with zero exposure — their presence is
the cross-default finding (C.4 trap 2).

**Step 5 · Aggregate — in-memory, algorithmic.**

1. Sum by entity, then by group.
2. **Deduplicate guarantee paths.** Where a guarantee edge already captures a
   subsidiary's exposure at the parent, count it **once**, honoring
   `guarantee_terms.covered_pct` and `cap_amount`. *This is the step that makes
   the product correct and the naive sum wrong, and it is worth a comment in
   the example code.*
3. Apply `materiality` — **except** to zero-exposure entities reached only by
   cross-default, which are reported rather than absorbed into the residual.
4. Emit **both** gross and guarantee-adjusted measures.

**Step 6 · Contract assembly.** Build `CreditExposureRollupContract@v1.0.0`
with `graph_snapshot_at` = the ledger `t` from step 3 and `expires_at` =
request time + 4 hours per `from_decision`.

### D.4 Determinism class and payload hash

**Determinism class: deterministic given (graph snapshot `t`, policy version,
request parameters).** No clock is read during construction except to stamp
`expires_at`, and no random or model-derived value participates.

**Payload hash** covers the measures, the entity and edge sets, the findings and
the lineage — and **excludes** `expires_at`, which is a function of request time
rather than of the answer. Two runs at the same `t` under the same policy
version with the same parameters **must** produce the identical payload hash;
a difference is a defect in construction, not drift in the estate.

### D.5 Replay statement and replay test

**Replay statement.** Given `graph_snapshot_at`, `policy_version` and the
request parameters recorded in lineage, the product reconstructs byte-identical
measures. The Fluree ledger `t` makes the graph side replayable; the policy
version makes the measurement side replayable; the Postgres side is replayable
because facility rows are append-only with logical supersession.

**Replay test.** Produce a rollup, record its lineage, then re-produce from the
recorded lineage alone and compare payload hashes. The test must also
**demonstrate the negative**: re-produce at a *different* `policy_version` and
show the hash changes, proving the policy version is load-bearing rather than
decorative. A replay test that only shows equality cannot distinguish a working
replay from one that ignores its inputs.

### D.6 Emitted contract

`CreditExposureRollupContract@v1.0.0`, Pydantic with `extra=forbid`.

| Field | Type | Notes |
|---|---|---|
| `anchor` | `LegalEntityRef` | resolved obligor |
| `intent` | `str` | echoed from the request |
| `policy_version` | `str` | the `limit_definition` version in force |
| `graph_snapshot_at` | `str` | Fluree ledger `t` |
| `entities` | `list[EntityExposure]` | per entity: committed, outstanding, undrawn — **gross and adjusted** |
| `group` | `GroupExposure` | committed, outstanding, undrawn — **gross and adjusted** |
| `residual` | `GroupExposure` | entities below `materiality`, aggregated |
| `connected_without_exposure` | `list[LegalEntityRef]` | reached by cross-default, holding no facility |
| `findings` | `list[Finding]` | cycles, flag/policy conflicts, reconciliation observations |
| `reconciliation` | `ReconciliationNote \| None` | committed vs XBRL-reported debt, with `plausible` |
| `expires_at` | `datetime` | request time + 4 h |
| `lineage` | `Lineage` | operators invoked, snapshot, policy version, source accessions |

**Gross and adjusted are both required fields.** A consumer must never receive
only the adjusted figure: the difference between them is the evidence that the
graph was traversed, and a single number is indistinguishable from the naive sum
§A warns about.

### D.7 Validation gates

Four gates. The first three are the SDK's standard set; the fourth is this
product's own.

| Gate | Assertion | Failure means |
|---|---|---|
| **Empty-operator guard** | No operator in D.2 marked "may be empty: No" returned empty | A step silently produced nothing and the product would have shipped a well-formed wrong answer |
| **Lineage strict equality** | Lineage names exactly the operators invoked — no more, no fewer | The record does not describe the run |
| **TTL bounds** | `expires_at` = request time + 4 h, within bounds | The `from_decision` anchor was not applied |
| **Reconciliation guard** | **gross ≥ guarantee-adjusted**, per entity and per group | The dedup logic **double-subtracted**. Adjusted exposure exceeding gross is arithmetically impossible; if it happens, step 5.2 removed the same exposure twice |

**The reconciliation guard is the one that earns its place.** The other three
catch a broken pipeline. This one catches a *plausible wrong answer* — the
failure mode §A says is invisible in the output. It must be observed firing on a
deliberately double-subtracting implementation before it is trusted, not merely
observed passing.

---

### D.8 The fulfillment determination — the step after the gates

The gates decide whether a product **exists**. This step decides whether the
fabric is **willing to attest** that the product it built is fit for this
consumer to act on. They are different questions and they are answered by
different code, in this order:

```
assembly -> projection -> Debt assessment -> effective Debt tolerance
         -> fulfillment determination -> replay -> disclosure
```

**Context Debt does not refuse the request.** `D_c` is a *measurement* of the
fabric's confidence in what it assembled, taken from evidence (E.2) and
identical for every consumer of the same determination. Governance uses that
measurement to decide whether fulfillment is permitted. Two consumers may ask
the same business question with different fitness requirements, and the same
assembled determination may legitimately be fulfilled for one and refused for
the other.

**The mechanism.** `ccf.products.gates::refuse_over_tolerance` takes a
`ServableProduct` — which is not constructible outside `run_gates` — and one
resolved `EffectiveParameter`. The sequencing is therefore structural rather
than documented: a caller who has not run the gates has nothing to pass, so
*withheld* can only ever be said about a product that exists.

**The tolerance is a resolved parameter, never a number.** The three debt
authorities — the class's `debt_tolerance` default of `0.25`, the caller's
declared bar, and any applicable policy constraint — are folded exactly once,
upstream, by `resolve_effective_request`. The fulfillment check performs no
fold of its own; a second fold is where a product would quietly re-acquire the
power to overrule its own governance.

**The one narrowing case, and why it is not an inconsistency.** This deployment
registers two policy constraints with the same `maximum` operator, and they
behave differently:

| Constraint | Parameter | Caller asks | Outcome |
|---|---|---|---|
| `materiality-ceiling/internal-appetite` | `materiality` | `0.10` over a `0.05` ceiling | **REFUSED by name**, before assembly. A narrowed request answers a question nobody asked (`D-IMPL-251` C5) |
| `debt-tolerance-ceiling/regulatory-large-exposure` | `debt_tolerance` | `1.0` over a `0.10` ceiling | **NARROWED to `0.10`** with authority `policy`; the product is assembled and then withheld against that bar |

`DEBT_TOLERANCE_PARAMETER` is the SDK's **only** parameter-name-keyed branch,
and it keys on the SDK's own mechanism token rather than on any deployment's
vocabulary. The asymmetry is deliberate: **a fitness bar cannot be refused
before fitness has been measured.** Materiality shapes the answer, so a
disallowed value can be refused at the boundary; debt tolerance *judges* the
answer, so the comparison must wait until the observation exists. Both
behaviors are visible in the scenario set (E.6).

**What withholding does not do.** It does not withdraw the determination. The
$10,125,000,000 gross and $9,325,000,000 guarantee-adjusted figures are the
assembled truth and are printed on a withheld run. The fabric may know what it
calculated without being willing to attest that the calculation is fit to serve;
disclosure decides what the caller sees, and it discloses both the number and
the reason it is not attested.

---

### D.9 Decision replay — written before the response is released

`D-IMPL-256`: *"Every governed determination that crosses a CCF delivery
boundary — fulfilled or refused, tool or resource, authorized or denied — must
reach the replay writer before the response is released."*

**One writer, one store, one record class for both outcomes.** `D-IMPL-253` Q13
(Dave): *"Refusal is itself a decision and deserves the same five-dimensional
replay model. Do not create second-class replay."* A separate artifact class for
withheld determinations would be that second class. Measured on this product,
the **withheld record is larger than the served one** — 20,639 bytes against
17,157 — because it additionally carries the refusal envelope, its evidence and
the debt breakdown.

| Dimension | Served | Withheld |
|---|---|---|
| 1 · Context fabric | boundary `2026-09-07T12:00:00+00:00`, 77 touched entities | **identical** — the same state was read |
| 2 · Policy bindings | the Control Plane bundle pin **and** `limit_definition/group-limit-test` | identical |
| 2 · Effective request | present | present |
| 3 · Model version | `assembly_mode=algorithmic`, `model=none` | identical |
| 4 · Perspective | `PRIN-CRO-001 / credit-officer` | identical |
| 5 · Content path | product content address, `refusal_recorded: false` | `no-product-address`, `refusal_recorded: true` |
| 5 · Debt | `1.000` | `1.000`, arriving through the refusal envelope's own permitted evidence |

**What replay re-asks is the EFFECTIVE question, never the caller's.**
`resolution` carries one parameter per name with the authority that established
it, so a reader sees `debt_tolerance 0.10 [policy]` rather than the `1.0` the
Regulated Consumer typed. Under a narrowing constraint those are different
questions and only one of them was answered.

**Two policy bindings, because two versioned policies governed the answer.** The
Control Plane bundle is the fabric's own, pinned at boot. The limit definition is
credit policy read from the amounts store, and it is what decided whether
guarantees net and whether undrawn commitments count (§D.3 step 2). Recording
only the first would leave a reader unable to tell which definition produced
which number.

**Ordering is structural rather than conventional.** A served product is what a
successful append *returns* (INV-CH7-79): there is no branch through `serve`
that hands back a product whose record failed to write, because the product
comes out of the same call that wrote it. On the withheld branch `record_refusal`
returns the artifact reference rather than a delivery capability — a refusal has
no product for a capability to authorize, and what the caller needs is the
address the refusal envelope's `replay_reference` points at.

**The store is per-run, and that is a demonstration choice rather than a
deployment one** (`artifacts/replay.yaml`). What is demonstrated is the ordering,
which is observable inside one run. The record is read back out of the store and
its content address compared against the record the run built before the
directory is discarded, so the reported address is a fact about a persisted
artifact rather than about an object that was never written.

---

---

### D.10 The MCP door — and the two questions it was built to answer

The door is `server/serve.py` over `server/door.yaml`. It exposes the governed
path of §D.8–§D.9 as an MCP tool, authenticated, entitled, and recording every
denial as a decision. It re-implements no part of the assembly, the gates, the
debt assessment, the tolerance comparison or the replay record.

#### Question 1 — does the governed door reconcile declared behavior against observed execution?

**No. It proves a record EXISTS; it does not read what the record says.**
Measured directly:

```
product payload claims family = 77
replay record observed touched = 77

--- door check on a product whose payload disagrees with its record ---
door_refusal  -> None (no refusal)
served_answer -> ACCEPTED. payload family = 9999 | record says 77
```

A `ServedProduct` whose payload claims 9,999 family members, wrapping a replay
record whose dimension 1 observed 77, crosses the delivery boundary unremarked.

What the boundary *does* enforce is real and is not nothing.
`ccf.products.door::served_answer` refuses anything that is not a
`ServedProduct` — a bare `ServableProduct` is named as *"admitted by the gates,
recorded by nothing"* — and `D-IMPL-260` P-A requires *"a typed/provable
governed result proving determination, replay and disclosure completed."* That
is a **shape** proof: something was recorded. It is not a **content**
reconciliation: nobody compares what was recorded against what is being served.

**Both operands are in the door's hand.** `ServedProduct.product` carries the
payload; `ServedProduct.replay_ref` addresses the record. Reading dimension 1
and comparing it against the payload is one store fetch away. The ingredients
are present and the comparison is not made — which is the same sentence
findings 8, 12 and 14 each produced about a different mechanism.

#### Question 2 — is MCP exposure binding, or another application?

Measured in executable lines (blank lines, comments and docstrings excluded):

| | total | executable |
|---|---|---|
| cp-04's door (`compose.py` + `serve.py`) | 733 | **260** |
| cp-05's door (`serve.py`) | 334 | **204** |

cp-05 came to this with its governed path already built, and still spent 204
lines. The reduction is 22%, not the order of magnitude one would expect if the
door were binding. Breaking cp-05's 204 down:

| Part | exec | Kind |
|---|---|---|
| `door()` — entitlement registration, per-boot credential, `build_egress_server(...)` | 60 | **binding and configuration** |
| imports | 30 | plumbing — 8 SDK modules plus three MCP auth internals |
| `door_values`, `Door`, `serve`, module-level | 28 | plumbing |
| `build_resolver` — the `ProductResolverProtocol` adapter | 41 | **application** |
| `_wrong_address`, `_no_standing_answer`, `_refused`, `_text` | 31 | **application** |

**Roughly half is binding and half is a small application.** The application
half is not arbitrary — it is parameter translation, the wrong-address refusal,
the no-standing-answer refusal for a parameterized class read as a resource, and
the `refuse_request` call the door explicitly delegates. Each is a real decision
a deployment must make. But each also has to be *written*, and three of the four
mint a `ProductRequestViolation` by hand because the SDK ships no constructor
for "this door was addressed for the wrong class."

**The honest verdict: exposure is binding plus a thin application, and the thin
application is where a deployment can still get governance wrong.**
`ProductResolverProtocol` names the risk in its own docstring — *"a resolver
that does not call `refuse_request` serves against an unchecked request"* — and
that is a ruling (`D-IMPL-113`), not an oversight: the door never holds the
`RegisteredProductClass` both comparisons need. cp-05 discharges
`refuse_request`; it does **not** call `refuse_bound_payload`, because this class
declares no `payload_schema_key` and there would be nothing to compare against.
That absence is stated in `server/serve.py` rather than left to be inferred.

#### The finding behind both answers

**The SDK already ships the entire governed path cp-05 hand-built.**
`ccf.products.resolver::GovernedResolver`, reached through
`build_governed_resolver`, performs — in this order —
`refuse_intent` → `resolve_effective_request` → `GraphView` at the boundary →
`build_operator_registry` → `ProjectionEngine.execute(plan_factory(...))` →
`register_product_class` → the candidate contract with lineage, payload, debt and
`computed_empty` → `run_gates` → `refuse_over_tolerance` → `build_replay_record`
→ `serve` or a recorded refusal. That is §D.8 and §D.9 of this document,
composed, shipped and tested.

cp-05 did not use it. It was built by hand across steps 4 and 5 of this rung's
rebuild, and the reason is the one this specification has now recorded four
times: **the machinery is present and correct, and the easiest path for an
author walks past it.** What cp-05 would need to adopt it is a `plan_factory`
carrying the Postgres enrichment and the aggregation, an
`AssemblyDebtScorerProtocol` override (its debt comes from `balance_as_of` dates
and reconciliation rows, not from the `GraphView`), a home for the
product-specific reconciliation guard, and an answer to `D-IMPL-277` for the
acquisition step `GovernedResolver` assumes has already happened. None of those
is a blocker; all four are unstated.

---

## Section E — Volatility, debt & materialization

### E.1 Half-life table

| Signal class | `λ_c` | Why |
|---|---|---|
| Outstanding balances | **~4 hours** | Drawdowns and repayments land intraday |
| Guarantee and cross-default structure | **~365 days** | Amendment-driven |
| Ownership edges | **~180 days** | Inherited from `corporate-family-tree` |
| Group-limit definition | **~180 days** | Policy review cycle |

**The spread is the design constraint.** The fastest class moves ~2,190× faster
than the slowest. A product-level half-life would have to be set to the fastest —
4 hours — which would declare a stable ownership graph stale every four hours,
or to something longer, which would serve a balance figure hours after it stopped
being true. Per-class `λ_c` is not a refinement here; it is the only correct
shape.

### E.2 Debt model and per-component debt table

Context Debt `D_c` accrues per component against its own `λ_c`.

| Component | `λ_c` | Debt at threshold | Behavior at breach |
|---|---|---|---|
| Outstanding balances | 4 h | freshness shortfall vs the 4 h SLA | **Fail-closed** — refuse rather than serve a stale balance as current |
| Guarantee / cross-default structure | 365 d | staleness of the amendment feed | **Finding** — serve, and name the staleness |
| Ownership edges | 180 d | staleness inherited from rung 4 | **Finding** |
| Group-limit definition | 180 d | policy past review date | **Finding** — the definition is still the definition until replaced |

**Only the balance component fails closed.** A stale ownership edge produces an
answer that is slightly out of date; a stale balance produces an answer that is
*wrong about money* while looking current. The asymmetry is deliberate and is
the debt model's whole content at this rung.

### E.3 Materialization posture

**Derived on demand. Materialization is the wrong answer here, and this is the
first rung where that is true.**

The fastest input moves on a ~4 hour half-life, so a materialized rollup would
be stale inside its own `λ_c` window — the cache would spend most of its life
serving a number the estate had already superseded. The cost of recomputation
is bounded (one traversal, one batch query, in-memory arithmetic); the cost of
serving a stale exposure to a limit test is not.

**The contrast with `corporate-family-tree` is the point.** Same traversal
machinery, same stores, **opposite posture** — that product's inputs move on a
180-day half-life and materializing is correct. A reader who takes "traversal
products should be materialized" from rung 4 and applies it here gets a
plausible, stale, wrong number. The posture is a property of the *volatility
profile*, never of the shape of the query.

### E.4 Supersession triggers

- Drawdown or repayment event — supersedes the balance component
- Amendment changing guarantee or cross-default structure
- Any supersession cascading from `corporate-family-tree`
- Replacement of a `limit_definition` row — supersedes **every** rollup taken
  under the prior version, which is why the version is in lineage

### E.5 The expiry, and the two refusals it can produce

`expires_at` is request time + 4 hours, anchored `from_decision`.

**Refusal 1 — expired product.** A rollup read after `expires_at` is refused,
not served with a warning. The decision it was assembled for has either been
taken or has gone stale; either way the number is no longer the number.

**Refusal 2 — balance debt at threshold.** If the outstanding-balance component
breaches its freshness SLA at construction time, the product **fails closed**
(E.2) rather than emitting an exposure built on a stale balance. The refusal
names the component and its measured staleness.

**Both refusals are refusals of fulfillment, not of response.** The caller
receives a typed refusal carrying the reason, the component and the measurement
— never a silent empty payload, and never a partial rollup presented as whole.

### E.6 The demonstrated run, measured — and the eight consumers

**The demonstrated run is a governed refusal, and nothing was calibrated to
avoid that.** Measured against the estate at the pinned instant
`2026-09-07T12:00:00+00:00`:

| Factor | Value | Evidence |
|---|---|---|
| freshness | `0` | 15 real `balance_as_of` dates, 324–396 hours old, scored against the declared 4-hour `λ_c` |
| completeness | `0.2467` | 19 of 77 family members carry an LEI and can be checked for exposure at all |
| semantic_consistency | `1` | 5 reconciliations among the obligors this determination used; none disagrees |
| **`D_c = 1 − min(F, C, S)`** | **`1.000`** | the weakest link bounds confidence; signal `fail_closed` |

Against the class's own `0.25` default tolerance, fulfillment is **withheld**.
This is E.2's asymmetry firing exactly as designed: the balance component is the
one that fails closed, and it is stale. The correct response is to record it,
not to widen `λ_c` until the demonstration serves — a four-hour half-life
recalibrated to fit old demo data would make every later run of this product
lie about how current its money figures are.

**Eight named consumers, one estate, one instant.** `run.py --scenarios` runs
the set declared in `artifacts/scenarios.yaml`; `page/scenario-transcript.txt`
is its output.

| Consumer | Requested | Effective (authority) | Projected | Fulfillment |
|---|---|---|---|---|
| Default | *nothing* | `materiality 0.05` (default) · `debt_tolerance 0.25` (default) | 4 material, residual 145,000,000 | **WITHHELD** (default) |
| Detailed | `materiality 0.02` | `0.02` (caller) · `0.25` (default) | 4 material, residual 145,000,000 | **WITHHELD** (default) |
| Material-Only | `materiality 0.10` | `0.10` (caller) · `0.25` (default) | 3 material, residual 945,000,000 | **WITHHELD** (default) |
| Strict-Fitness | `debt_tolerance 0.05` | `0.05` (caller) | 4 material | **WITHHELD** (caller) |
| Exploratory | `debt_tolerance 1.0` | `1.0` (caller) | 4 material | **SERVED** |
| Regulated | `intent regulatory-large-exposure`, `debt_tolerance 1.0` | **`0.10` (policy)** — narrowed | 4 material | **WITHHELD** (policy) |
| Appetite | `intent internal-appetite`, `materiality 0.10` | — | — | **REFUSED at the request boundary** |
| As-Of | `as_of 2026-06-30` | — | — | **REFUSED at the request boundary** |

**The invariant this table exists to prove.** Family **77**, gross
**10,125,000,000**, adjusted **9,325,000,000** and `D_c` **1.000** are
byte-identical across every consumer that reached assembly. The fabric does not
revise what it knows to suit who is asking. What varies is (a) which slice of
that truth is projected, and (b) whether the fabric will attest that it is fit
to act on.

**Two measurements worth stating because they were not the expected result.**

1. **The Detailed Consumer's finer threshold changes nothing.** Dropping the
   floor from 506,250,000 to 202,500,000 selects the same four entities,
   because this family's book is concentrated: five entities hold facilities
   and the smallest material one commits 800,000,000. The projection moves only
   at 10%, where the 800,000,000 obligor falls into the residual. A threshold
   that *can* move the answer is not a threshold that *does*, and a
   demonstration that only showed the moving case would teach the wrong lesson
   about what materiality is for.
2. **A different tolerance produces a different content address.** The address
   spans the effective request — including the resolved `debt_tolerance` and
   the authority that set it — so the Exploratory and Default consumers address
   differently while their determinations are byte-equal. That is correct:
   *"give me this if you are confident enough"* is not the same question as
   *"give me this whatever your confidence."* The served-or-withheld outcome is
   deliberately **not** hashed in, because it is a pure function of the
   tolerance and the Debt the address already covers.

---

## Section F — Source binding & readiness

### F.1 Element readiness

All measured 2026-09-07. The vault's manufacture-envelope conditions (its
q019 `§F`) are reproduced here with what the estate actually holds.

| Vault condition | Required | Measured | Status |
|---|---|---|---|
| Facilities | ~40 | **60** | **Met** |
| Anchor obligors | ~50 | **22 distinct borrowers** | **Divergent — recorded (F.4)** |
| Guarantee edges | ~25 | **27** | **Met** |
| — of which upstream | ≥ 3 | **24** (`guarantee_terms.kind='upstream'`) | **Met** |
| Cross-default edges | ~15 | **15** | **Met** |
| — reaching an entity holding no facility | ≥ 2 | **4** of 20 entities reached | **Met** |
| Families where naive ≠ guarantee-adjusted | ≥ 3 | **4** (`kind='downstream-dedup'`) | **Met** |
| Balances reconciling to a plausible share of XBRL debt | all | **13 of 14** | **Divergent — recorded (F.4)** |

**Verdict: buildable today.** Every element in C.1 exists and is populated. The
two divergences are recorded rather than repaired, and neither blocks
construction.

### F.2 Every `[TBC]` in this document, with an owner

| `[TBC]` | Owner | What unblocks it | Blocks build? |
|---|---|---|---|
| Entitlement service binding — the concrete service this product calls for entitlement scope at D.3 step 2 | SDK | The example may bind the reference entitlement surface; a production deployment binds its own | **No** — the step is specified, only the endpoint is deployment-local |
| `limit_pct_of_capital` denominator — whose capital, measured how | Vault / credit policy | Needed only when the product **tests** a limit rather than **reporting** exposure against one; this version reports | **No** — out of scope at v1.0.0, and named so it is not silently assumed |

| **Vault: four-question test result** — absent from the article (§0.1) | Vault | Vault authors it, or ratifies the SDK-authored version | **No** |
| **Vault: scope boundary** — absent from the article (B.5) | Vault | Vault authors it, or ratifies the SDK-supplied wording | **No** |
| **Vault: primitive taught / build-order note** — absent from the article | Vault | Vault authors them | **No** |
| **Vault front matter: `sdk_spec`, `assembly_mode`, `out_of_scope` are `null`; `sources` is `unknown`** | Vault | This specification supplies the first three; return path (`spec_generation.md` §11) | **No** |

**No `[TBC]` gates the build.** All are recorded so a later reader does not
mistake an absence for an oversight.

**Four of the six are absences in the vault article, not in this
specification.** They are listed here because §4.1 requires those items to be
*extracted from the vault*, and they could not be — the article does not carry
them. Every SDK-supplied substitute is labeled as such at the point of use
(§0.1, B.5) rather than presented as the vault's.

### F.3 Access path, identifiers, history, text and volumetrics

**Access path.** Postgres `ccf_v2` on the estate host, read-only credentials.
Fluree 4.1.4 read endpoint `/v1/fluree/query`, SPARQL dialect, **explicit
`FROM <fibo-v2>` on every query** — the server answers HTTP 500 without one, so
the ledger name is not optional and is never defaulted.

**Identifiers.** LEI (20 char) for entities; `facility_id` for facilities; the
Fluree entity slug bridged to LEI through the ledger's `lei` predicate or
`ccf_v2.crosswalk` — never by string similarity (C.3).

**History.** Fluree carries ledger `t` for point-in-time reads. Postgres facility
rows are append-only with logical supersession. Both are required for D.5.

**Text.** None. This product reads no unstructured content; passage-level
lineage arrives at rung 13.

**Volumetrics, measured.** 156 legal entities · 60 facilities · 916 ownership
edges (`owns` 636 + `isUltimatelyConsolidatedBy` 140 + `isDirectlyConsolidatedBy`
140) · 27 guarantee edges · 15 cross-default edges · 45 borrower-of edges. At
`depth=3` from the worked anchor the node set is small; the scale question this
product raises is answered at rung 16, not here.

### F.4 Recorded findings — not `[TBC]`, because none needs a decision to build

1. **22 distinct borrowers against the vault's ~50 anchors.** The estate exceeds
   the facility count (60 vs ~40) while concentrating them across fewer
   borrowers. The uneven distribution the vault asks for is present — some
   families hold several facilities, some none — so the product's behavior is
   demonstrable. Recorded because the number differs from the vault's, not
   because it is wrong.
2. **One of 14 reconciliations is `plausible = false`.** One obligor's synthetic
   commitments are not a plausible share of its XBRL-reported debt. Left as-is:
   it exercises the `reconciliation` field's negative path, which an all-true
   estate could not.
3. **RESOLVED, not carried — the anchor below its own materiality floor.** An
   earlier draft recorded it as a finding that the anchor is filtered from the
   enumerated entities of its own rollup at the 5% default. It is not a defect:
   the threshold is the CALLER's decision tolerance (B.4.1), and a caller asking
   `0.01` sees the anchor. Recorded because the first reading was wrong and the
   correction is architectural rather than a patch.
4. **The slug↔LEI join hazard** (C.3). Recorded as a finding because it produced
   a false measurement during authoring, and any implementation will meet it.
5. **The vault article's own worked anchor does not exist in the estate.** Its
   §D client call uses `5493001KJTIIGC8Y1R12`; measured, that LEI is **absent
   from `ccf_v2.legal_entity` and holds zero facilities**, beside a positive
   control confirming the query resolves `5493000Q1S5TJIDIQH89` to `REGIS CORP`.
   This specification substitutes a real, exercising anchor (D.1) and records
   the substitution here rather than making it silently. The vault's example
   call should be repointed on the return path.
6. **API/documentation friction — the envelope payload is FLAT, not nested.**
   `AssemblyWorker`'s resolver treats `match_key` as a presence flag and reads
   every identity and attribute key from the TOP LEVEL of `raw_payload`, as
   siblings. Nesting them under the match key resolves the rule and then refuses
   — *"matched rule for 'exposure_member' but lacks identity keys
   ['entity_uri']; the fabric refuses to mint a URI from partial identity."*
   **The SDK is behaving correctly**; refusing to mint from partial identity is
   right. The declaration simply does not make the required payload shape
   obvious. Adoption ergonomics, not a semantic defect.

7. **CANDIDATE SDK VALIDATION GAP — operator seed classes and
   resolution-produced entity classes can be compositionally incompatible with
   no boot-time refusal.** The traversal operator's `seed_entity_classes` names
   a class the resolution spec must mint. Each document is valid alone; the
   COMBINATION can yield a silently empty traversal over a fully populated
   graph. **Measured, both ways:** seeding on `exposure_nonesuch` — a class
   nothing mints — the fabric **boots clean**, and the product then refuses at
   the empty-operator guard: *"the declared traversal operator returned no
   entities over an L3 holding 77 ingested nodes and 100 relationship claims."*
   **NOT FIXED.** Recorded as a candidate; cp-05 continues, and whether this
   deserves a general compatibility check is decided after seeing whether the
   same class of mismatch appears elsewhere.

8. **Guard placement is load-bearing, and this is where it was learned.** The
   empty-operator guard originally watched the ACQUISITION walk. Under the
   sabotage above that walk returns 77 and the guard **passes**, while the
   served family is empty. The guard now watches the OPERATOR's output, which is
   what the product serves. A guard over the wrong step is not a weaker guard —
   it is a guard that reports on something nobody is served.

9. **API friction, minor and recorded — `ProjectionPlan.invoke` receives no
   request.** Its four arguments are `view`, `operator_outputs`, `perspective`
   and `temporal_boundary`. A caller-selectable *projection* parameter — this
   product's materiality threshold — therefore has no declared channel into
   `invoke` and arrives through the plan's constructor, the plan being built per
   request. **`ProjectionEngine.execute` itself required no adaptation**, so
   this is a discoverability cost rather than a capability gap: an author has to
   work out that the plan, not the call, is where a per-request projection
   parameter lives. Arguably correct as designed — a projection conditioned on
   `perspective` and bounded by time, with everything else fixed at
   construction, is a defensible contract.

10. **`assembly_mode`, `out_of_scope` and `sdk_spec` are `null` in the vault
   article's front matter.** This specification supplies all three; the vault
   article should be updated on the return path (`spec_generation.md` §11).

11. **NOT A GAP — the `debt_tolerance` narrowing is deliberate, and the source
    says so.** A `maximum` policy constraint on `materiality` refuses; the same
    operator on `debt_tolerance` narrows. That looked like an inconsistency
    until it was measured against `src/ccf/products/constraints.py`, which
    documents it as *"the one exception to 'nothing is clamped'"* and gives the
    reason: the comparison that can still refuse — observed Debt against that
    tolerance — happens after assembly, where the observation exists. Recorded
    as a **confirmed SDK behavior**, not a finding, because a reader meeting
    the asymmetry for the first time will reach for the same wrong conclusion.
    `DEBT_TOLERANCE_PARAMETER` is the SDK's only parameter-name-keyed branch
    and it keys on the SDK's own mechanism token, never on this deployment's
    vocabulary.

12. **The fulfillment path was present, complete and NOT the obvious path.**
    `run_gates` -> `ServableProduct` -> `refuse_over_tolerance` required no SDK
    change and no adaptation: the class registration, the gates, the debt field
    on the contract and the tolerance check all composed as specified. What it
    required was *knowing to look for it*. An earlier draft of this product
    computed Context Debt, printed it, and served the answer anyway — the debt
    figure was an ornament on a product nothing governed. Nothing in the SDK
    stopped that, because a producer that never calls `refuse_over_tolerance`
    is indistinguishable from one whose tolerance was met. **The same shape as
    finding 8**: the machinery is present and correct, and the easiest path for
    an author still walks past it.

13. **Two self-inflicted documentation defects, recorded rather than amended.**
    (a) `summary_explanations.md` quoted a depth-refusal message no run ever
    produced — invented from the shape of the argument rather than copied from
    output. The two real messages differ from it and from each other, and are
    better teaching: depth 6 is refused by the CLASS's declared domain, depth 9
    by the SUBSTRATE's capability, and a caller told which is which knows
    whether to ask for a different product or to stop asking. (b)
    `artifacts/assembly-recipe.yaml` did not parse as YAML — an unquoted
    `` `may_be_empty: false` `` inside a scalar — while claiming to be "§D.2 as
    data." Nothing reads the file, which is why it went unnoticed for the whole
    build. Both are the same class as finding 5: a plausible artifact nobody
    executed. **The rule that catches this class is to run the thing, not to
    read it**, and both were found by running it.

14. **DEFECT, FOUND BY THE REPLAY RECORD — the declared policy operator was
    invoked and its output discarded.** The product answered 77 family members
    from a traversal that never passed through `policy.principal-subgraph`,
    while its lineage declared that operator among the ones invoked. The cause
    was one argument: `registry.resolve("traversal.typed-neighborhood").apply(
    ..., upstream=())`, which registers the policy operator and then walks the
    raw view.

    **Nothing caught it for the whole build.** Lineage strict equality passed —
    the engine *did* invoke both operators. The empty-operator guard passed —
    the traversal returned 77. Every gate passed. What found it was building
    dimension 1 of the replay record: `touched_entities: 0` for a determination
    over 77 members, because the `ProjectionEngine`'s **chained** pipeline was
    correctly returning nothing (an empty `permitted_classifications` admits
    nothing — *"the fabric does not admit state it cannot prove is
    admissible"*) while the served answer came from somewhere else entirely.

    **The config was right from the start; two halves of it were never
    implemented.** `ccf_config.yaml` already declared `family_id` as an
    attribute key on both entity rules, and `permitted_classifications: []`
    deliberately empty. What was missing was the envelope carrying a `family_id`
    value, and the request-time binding of the permitted set — both of which
    rung 4 had already ruled and built (`D-IMPL-229`, Dave: *"If PolicyFilter
    can only key off a claim attribute, that attribute is membership, minted
    when the node is admitted to the walk."*).

    **Fixed, and sabotage-verified in both directions.** Policy now runs first
    and the traversal chains from its provenance;
    `deployment.py::refuse_unbound_family_scope` refuses an unbound set and a
    set naming another family, by name, and both refusals were observed firing.
    Minting the family under a value the request does not name now returns an
    empty traversal, caught by the empty-operator guard — *"the declared
    traversal operator returned no entities over an L3 holding 77 ingested nodes
    and 100 relationship claims"* — against a positive control of 77. The answer
    is unchanged at 77 members and $9.325B; what changed is that it now passes
    through the envelope it always claimed to.

    **The SDK observation this leaves.** Every SDK mechanism behaved correctly.
    `PolicyFilter` excluded state it could not prove admissible; the engine
    chained correctly; the gates checked what they are specified to check. What
    no mechanism did was notice that a product's *served answer* and its own
    *engine's execution* disagreed about how many entities existed. This is the
    same shape as findings 8 and 12: **the machinery is present and correct, and
    the easiest path for an author walks past it.**

15. **A float in the payload, caught only on the served path.** The payload
    carried `request.materiality` as a Python float.
    `ccf.contracts.canonical` refuses one outright — *"float is not canonically
    encodable (not bit-stable across platforms); use int or decimal.Decimal"* —
    which is exactly right. But the refusal fires only when the product payload
    is content-hashed, and **only the served path does that**: a withheld
    determination's record never hashes the payload, so the same defect had been
    riding silently through every refused run. Fixed by carrying the `Decimal`
    into the projection (exact arithmetic on a money floor) and its string form
    on the wire — which also preserves the caller's lexical form, so `0.10` stays
    `0.10` rather than normalizing to `0.1`.

16. **The Control Plane document has no slot for a deployment's own replay
    binding.** Adding a `replay:` section to `ccf_config.yaml` is refused by
    name, and the refusal is right — a Control Plane document that accepted
    arbitrary sections would let a deployment smuggle unaudited state into the
    audit plane — and its message names every recognized alternative. But the
    artifact class names a deployment writes its decision records under have
    nowhere declared to live. Rung 4 put them in `deployment.py` as module
    constants; this rung puts them in `artifacts/replay.yaml`. Neither is the
    Control Plane. Minor, and recorded because every example will meet it.

17. **THE SDK SHIPS THE WHOLE GOVERNED SPINE AND cp-05 REBUILT IT BY HAND.**
    `ccf.products.resolver::GovernedResolver`, reached through
    `build_governed_resolver`, composes `refuse_intent` →
    `resolve_effective_request` → `GraphView` → `build_operator_registry` →
    `ProjectionEngine.execute` → `register_product_class` → candidate contract
    → `run_gates` → `refuse_over_tolerance` → `build_replay_record` → `serve`
    or a recorded refusal. That is §D.8 and §D.9 of this document, shipped.
    cp-05 built all of it by hand across steps 4 and 5 of this rung's rebuild
    and discovered the shipped version only while building the MCP door.

    **This is the fourth instance of one pattern**, and at a larger scale than
    the other three: findings 8 (acquisition), 12 (fulfillment) and 14 (policy
    composition) each said *the machinery is present and correct, and the
    easiest path for an author walks past it*. This one says it about the
    entire governed path at once.

    What cp-05 would need to adopt `GovernedResolver`: a `plan_factory` carrying
    the Postgres enrichment and the aggregation; an
    `AssemblyDebtScorerProtocol` override, because this product's debt comes
    from `balance_as_of` dates and reconciliation rows rather than from the
    `GraphView`; a home for the product-specific reconciliation guard, which
    `run_gates` does not run; and a ruling on `D-IMPL-277` for the acquisition
    step `GovernedResolver` assumes has already happened. Each is tractable and
    none is documented as the path.

18. **The delivery boundary proves a record EXISTS and does not read it**
    (§D.10 question 1). A `ServedProduct` whose payload claims 9,999 family
    members, wrapping a replay record whose dimension 1 observed 77, crosses
    unremarked — measured, not argued. Both operands are in the door's hand:
    the payload on `ServedProduct.product`, the record at
    `ServedProduct.replay_ref`. This is the reconciliation findings 8, 12 and 14
    each imply and no layer performs.

19. **`GovernedResolver` does not call `refuse_request` or
    `refuse_bound_payload` either.** The door's own docstring puts the
    obligation on the resolver (`D-IMPL-113`, extended by `D-IMPL-121`),
    and the SDK's *reference* resolver calls `refuse_intent` and neither of
    those two. So a deployment adopting `build_governed_resolver` in good faith
    inherits an unchecked request surface unless it wraps the result. Recorded
    as measured rather than as a criticism: the ruling's reason — the door does
    not hold the `RegisteredProductClass` — applies to the door, and
    `GovernedResolver` registers the class itself, so the second operand is in
    its hand.

---

## Section G — Operate & govern

### G.1 The expiry obligation, restated where an operator will look for it

A `credit_exposure_rollup` expires **4 hours after the request that produced
it**. It is not refreshed in place and it is not served past expiry (E.5). An
operator seeing an expired product in a queue should expect a refusal on read,
not a stale payload — and the refusal is the correct behavior, not an incident.

### G.2 Acceptance criteria

The specification is discharged when a run demonstrates, on the live estate:

1. The worked call at **D.1** returns a `CreditExposureRollupContract@v1.0.0`
   with gross **and** adjusted measures populated.
2. **Gross ≠ adjusted** for the anchor — proving the dedup step is load-bearing
   rather than a no-op on this data.
3. `connected_without_exposure` is **non-empty** across the estate — proving the
   cross-default traversal reached what a borrower-keyed sum cannot.
4. The **same anchor under `internal-appetite`** returns a different adjusted
   figure than under `group-limit-test` — proving the limit definition is
   consumed rather than hard-coded.
5. All **four validation gates** pass, and the **reconciliation guard is
   observed firing** on a deliberately double-subtracting variant.
6. **Replay** from recorded lineage reproduces the payload hash, and a replay at
   a different `policy_version` produces a different one (D.5).
7. The traversal issues **one** walk, not one per predicate — evidenced by a
   single ledger `t` in lineage.
8. The product is reachable **over MCP** as well as in-process, serving the same
   payload from the same assembler with no business logic reimplemented.

### G.3 Catalog contribution

**Registered as** `credit-risk.exposure-rollup.v1`.

**Delivery surfaces.** In-process adapter **and an MCP door** — MCP is mandatory
for this and every subsequent rung. **A2A is deferred**, not dropped; it arrives
with rung 20 (`syndicated-lending-co-lender`) where the scope boundary opens
beyond a single institution.

**What this rung contributes to the ladder.** The first product where
materialization is the wrong posture (E.3); the first multi-predicate traversal
(D.3 step 3); the first multiplicative batch-enrich fan-out (D.3 step 4); the
first product-specific validation gate (D.7); and the first place where a
versioned policy artifact changes the answer rather than merely permitting it
(C.4 trap 3).

**Contrast pointer for the next reader.** `corporate-family-tree` — same
machinery, opposite materialization posture. Read them together or the posture
looks arbitrary.

---

*End of specification. Authored 2026-09-07 against `spec_generation.md` and
`Context_Product_Specification_Standard_v0-3.md`. Every count measured on the
live estate; no figure carried from the vault unverified. Awaiting Gate 1
review.*
