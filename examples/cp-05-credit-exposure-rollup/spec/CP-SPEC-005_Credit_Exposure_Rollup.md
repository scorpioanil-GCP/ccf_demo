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

9. **`assembly_mode`, `out_of_scope` and `sdk_spec` are `null` in the vault
   article's front matter.** This specification supplies all three; the vault
   article should be updated on the return path (`spec_generation.md` §11).

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
