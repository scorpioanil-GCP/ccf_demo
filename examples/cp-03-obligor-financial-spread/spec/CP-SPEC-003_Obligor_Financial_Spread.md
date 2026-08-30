# Obligor Financial Spread — Context Product Specification

**`CP-SPEC-003` · rung 03 of the vault's ladder · Tier 1**
**PostgreSQL `ccf_v2` for every attribute · Fluree `fibo-v2` for the policy binding**
**Gate 2 builds the Postgres half; the Fluree binding is staged — §C.6.1**
**Registry name `credit-risk.spread.v1` · cost band ×1 (baseline)**

> Standardized financial spreads for a single obligor, with peer comparison at
> identical periods. **Teaches attribute-level temporal validity before any graph
> or ledger is involved** — every figure carries a period end, a filing date and
> a retrieval date, and the three are not the same thing.

| | |
|---|---|
| **Source article** | `wiki/context-products/content/obligor-financial-spread.md`, vault-owned, **`standard: q019`** |
| **Authored to** | `Context_Product_Specification_Standard_v0-3.md` — the article is on the older Q019 form and is *raised* to v0.3 here, per `spec_generation.md` §4 |
| **Gate 1 status** | **APPROVED — Dave, 2026-08-29.** Authored 2026-08-29; approved on a full read of the specification |
| **Gate 2 status** | **not started.** Nothing is implemented |
| **Estate** | probed 2026-08-29 against `parkavedb` schema `ccf_v2` on `192.168.4.76`, read-only. **This product was `unprobed` before this document** |
| **Stores** | **TWO** (Dave, 2026-08-29). **PostgreSQL `ccf_v2`** supplies every attribute; **Fluree `fibo-v2`** supplies the **policy-version binding** and nothing else — the §7.8 Control/Data-plane split, which Q019 §3 assigns to exactly these two stores. MongoDB, SQLite and Neo4j were each queried and each excluded. Reasoning at §C.2, per-store verdict at §F.3. **A deviation from the vault article's `capability_classes: [relational]` — `[TBC — vault]`, §F.2 row 24. STAGED: Gate 2 builds the Postgres half only; the Fluree binding lands at a later gate — §C.6.1** |

---

## 0 · What this document is

A specification a competent engineer can build from **without a further design
conversation**, and which a reviewer can *falsify* rather than merely agree with.
Every figure in it was measured against the estate on 2026-08-29 and the query
that produced it is recoverable from §F.3. Where a value is not yet known it is
marked `[TBC — <owner>]` and registered at §F.2.

**This document is the whole of Gate 1.** Nothing below is implemented. The
build discharges it at Gate 2 and clears the `[TBC — this build]` rows then.

### 0.1 Do you need a Context Product? — the four-question test

The vault article for this product is on the **older Q019 form**, which has no
four-question section. The result is therefore `[TBC — vault]` and is **not
invented here**. What can be said from the article's own text is recorded, and
the verdict is left to the owner of the test:

| Question | What the article supports | Verdict |
|---|---|---|
| Is the answer assembled from more than one source? | Yes — XBRL company facts, XBRL frames, an internal spreading convention, internal ratio definitions | leans yes |
| Does the answer decay? | Yes, and **at different rates per attribute** — annual ~365d, quarterly ~90d, restatement event-driven | leans yes |
| Is the answer policy-conditioned? | Weakly. Public-filing data carries **no MNPI constraint** — the article says so deliberately | leans **no** |
| Would a wrong answer cause harm a log would not catch? | Yes — a stale leverage ratio sizes a facility wrongly and the log records a correct query | leans yes |
| **Result** | | **`[TBC — vault]`** |

> One leaning-no is not a failure. `counterparty-reference-snapshot` was admitted
> to this catalog with *"one no, one partial, admitted on stated basis."* The
> weak policy leg is **this product's teaching point**, not its defect — §B.2.

### 0.2 Placeholder discipline

Every unresolved item carries `[TBC — <owner>]` and appears again at **§F.2**
with that owner and the gate that clears it.

- `[TBC — this build, phase Pn]` — a value only the build can supply. **Cleared
  at Gate 2.**
- `[TBC — <agent>]` — a term belonging to another agent under
  `spec_generation.md`. Cleared when that agent rules, never by this document.

**An unmarked assumption is a worse defect than a marked gap.** No `[TBC]` in
this document is a guess wearing a marker: each names a measurement nobody has
taken or a term nobody has ruled.

### 0.3 Section skeleton

`A` decision frame · `B` contract · `C` data catalog · `D` assembly recipe ·
`E` volatility, debt and materialization · `F` source binding and readiness ·
`G` operate and govern. The order is the standard's and is not rearranged.

### 0.4 Front matter

| Field | Value |
|---|---|
| Registry name | `credit-risk.spread.v1` |
| Tier | 1 |
| **Assembly Mode** | **1 — pure algorithmic.** No LLM is invoked on any path. The article leaves `assembly_mode: null`; Mode 1 is **derived here** from §D having no semantic stage, and is `[TBC — vault]` for confirmation |
| Cost band | ×1 (the baseline) |
| Lifecycle state | **approved-not-built** — Gate 1 approved by Dave 2026-08-29; **no code, artifacts or tests exist** |
| Accountable owner | product: Credit Risk · data steward: credit analysis / spreading · policy: identity and access |
| Last review | 2026-08-29 (this authoring) |
| What it resolves | One obligor to a **typed, period-aligned financial spread** in which every figure names the period it describes, the filing that asserted it, and whether a later filing changed it |
| Four-question build test | `[TBC — vault]` — §0.1 |
| Build order | **Third on the vault's ladder, and last of Tier 1.** Depends on `counterparty-reference-snapshot` for the LEI→CIK crosswalk; supplies spread figures to `credit-exposure-rollup`, `credit-memo-context` and `rating-and-spread-migration` |
| Prerequisites | `counterparty-reference-snapshot` (rung 01) — **satisfied**: 50 of 50 obligors resolve through `ccf_v2.crosswalk`, 0 orphans (§C.3) |
| `out_of_scope` in the article | **`null` — NOT STATED**, which per the vault's frontmatter notice of 2026-08-29 never means *nothing*. The scope boundary at §B.5 is therefore **proposed by this document**, not quoted, and is `[TBC — vault]` |

---

## Section A — Decision frame

**Decision and trigger.** A credit officer is sizing a facility or preparing a
rerating and needs spread financials — leverage, coverage, margins — with peer
context at comparable periods.

**Consuming principals.** Single role at this tier. The estate carries four
principals (§C.1 element 8); the perspective axis is present but **near-inert
here by design**, and §B.2 says why that is the lesson rather than the gap.

### A.1 The counterfactual — Latency Poisoned, in its simplest form

The article states the failure and this document adopts it verbatim as the
counterfactual this product exists to prevent:

> Every figure in this product carries *three* different dates that are
> routinely conflated: the **period end** the figure describes, the **filing
> date** on which it became public, and the **retrieval date** on which the
> agent read it. A dashboard shows one number and implies one date. An agent
> reasoning over a FY-end leverage ratio filed nine months ago, as though it
> described the borrower's position today, has made a correct inference from a
> stale frame.

And the generalization, which is the sentence the whole rung is built to earn:

> **Temporal validity is an attribute-level property, not a product-level one.**
> A product does not have *a* freshness; each of its claims does.

**Why that sentence is load-bearing against rungs 01 and 02.** The ladder has
been moving the TTL anchor one step further from the request at each rung, and
this rung is where a single anchor stops being sufficient:

| Rung | Anchor | What it proved |
|---|---|---|
| 01 `counterparty-reference-snapshot` | the legal entity's own refresh date | the contract fires; identity authority hierarchy |
| 02 `facility-terms-snapshot` | the instrument's own `effective_date` | an expiry that **does not move when the question moves** |
| **03 this product** | **the filing that asserted each figure** | **one expiry per product is not enough** — the anchor becomes per-attribute |

**Closed-taxonomy mode for the counterfactual.** The Standard's counterfactual
taxonomy is a closed list. `Latency Poisoned` is the article's own term and is
adopted. Whether an attribute-level latency failure is a **mode** of
`Latency Poisoned` or a distinct member is `[TBC — vault]`; a reading is
proposed — *it is the same mode observed at finer granularity* — and is **not
asserted**.

### A.2 Fixture `OFS-F01` — the counterfactual, made falsifiable

The counterfactual is a claim, so it gets a fixture that can fail:

- Take one obligor with a **material** restatement (§E.5 — 33 obligors qualify).
- Ask for the affected period twice: once at `basis=as-reported`, once at
  `basis=latest-restated`.
- **The two answers must differ**, and each must name the accession that
  asserted it.
- A build in which they agree has not implemented the product; it has
  implemented a dashboard with a parameter on it.

`[TBC — this build, phase P7]` — the two calls and their outputs.

---

## Section B — Contract

### B.1 The nine elements

| # | Element | Value |
|---|---|---|
| 1 | **Schema** | `obligor_financial_spread` — entity `LegalEntity`; attributes: revenue, EBITDA components, total debt, cash, interest expense, and the derived leverage / coverage ratios. **No relationships.** Every attribute carries `period_end`, `period_start`, `unit`, `filed_date`, `accession`, `basis`. Machine-readable artifact `[TBC — this build, phase P6]` at `docs/schemas/obligor_financial_spread.v1.json` |
| 2 | **Freshness SLA** | **Quarterly — bounded by the filer's reporting cadence, not by a clock.** A product whose SLA promised anything faster would be promising something the SEC does not supply |
| 3 | **TTL** | **30 days**, `ttl_anchor: from_entity_freshness`, measured from **the `filed_date` of the latest fact admitted to the payload** — §B.1.1 |
| 4 | **Policy Binding** | Entitlement scope, **plus the versioned policy binding resolved from Fluree `ex:PolicyVersion` at `asked_at`** (§C.6) — the Control-plane half of the Q019 §3 split. **Public-filing data carries no MNPI constraint**, stated deliberately because `mnpi-wall-enforcement` (rung 17) depends on the reader knowing which corpora *do* — §B.2 |
| 5 | **Lineage** | `operators_invoked` · `graph_snapshot_at` · `policy_version` · **`accession` per attribute, not per product** — §D.6 |
| 6 | **Semantic Version** | `v1.0.0` |
| 7 | **Discovery** | `credit-risk.spread.v1` |
| 8 | **Addressability** | `/context-products/credit-risk/spread/{lei}` |
| 9 | **Assembly Mode** | **1 — pure algorithmic**, derived at §0.4, `[TBC — vault]` |

#### B.1.1 Element 3, and the one thing this anchor must be tested for

`from_entity_freshness` here means the expiry is a function of **the filings the
payload actually consumed**, not of the request and not of a wall clock. A
payload assembled from a 10-K filed 2024-02-28 expires 30 days after
**2024-02-28**, whichever instant it was asked at.

That is rung 02's lesson inherited. What is **new** at this rung is that the
anchor is chosen **per payload from a set of per-attribute filing dates**, and
choosing it is a real decision with a measured consequence:

- **latest `filed_date` in the payload** — the payload is as fresh as its
  freshest claim. Optimistic: a spread carrying one current quarter and four
  stale annuals looks fresh.
- **earliest `filed_date` in the payload** — the payload is as fresh as its
  stalest claim. Pessimistic, and refuses far more.

**This document declares the latest**, and records the consequence rather than
hiding it: **gate `OFS-G09` asserts the shipped behavior and is written to turn
RED if the declaration is later changed to the earliest.** That redness is the
signal to reopen §F.4 finding 4 — the same tripwire pattern rung 02 used for its
TTL basis. The measured refusal counts for both readings are
`[TBC — this build, phase P6]`.

**THE VAULT HAS SINCE SET THE TEST THIS ANCHOR MUST PASS, and it passes.**
Ruling of 2026-08-30, on rung 02's TTL finding:

> A freshness anchor has to be an **observation timestamp that moves**… An
> origination date is fixed for the life of the agreement. So
> `effective_date + 90d` is **not a refresh cadence — it is permanent expiry
> that re-derivation cannot clear.** That is a category error in the anchor,
> not a tight window.

`filed_date` **moves**: filers file quarterly, so re-derivation clears the
expiry. The measured contrast is the evidence — rung 02 refuses 50 of 60
*permanently*, while this product serves **23 of 50** and its 27 refusals clear
as filers file. A refusal here is the product working, not a finding awaiting a
ruling. **Confirmation of that reading is requested in the §11 return of
2026-08-30**; it is not assumed closed.

> **The 30-day window itself is the vault's value and is untouched here.**
> Whether it should widen is a separate question from which date it is measured
> from, and conflating the two would hide one behind the other.

### B.2 Classification, residency, and the policy leg that is deliberately weak

| Aspect | Value |
|---|---|
| **Payload classification** | `public`. Measured: `provenance` on `ccf_v2.financial_fact` is **`public` for all 15,055 rows** — there is no internal-classified fact in this estate |
| **MNPI** | **None.** The corpus is filed public data. `principal.sees_mnpi` exists in the estate and **does not gate this product** |
| **Residency constraints** | `[TBC — identity and access]` |
| **Cross-border serving** | `[TBC — identity and access]` |

**The weak policy leg is the lesson.** Rungs 01 and 02 both had entitlement
doing visible work — jurisdiction grants and need-to-know suppressed rows. Here
the same machinery runs and **suppresses nothing**, because the data is public.
That is worth building rather than skipping, for two reasons:

1. It proves the Policy step is **not conditional on having something to
   suppress**. `policy_version` is still emitted, still lands in replay, and the
   operator still runs before anything reads state. A product that skipped
   Policy when it had no restrictions would be a product whose audit trail
   silently changed shape with its data.
2. It is the **negative control** for `mnpi-wall-enforcement` at rung 17. A
   reader who has seen entitlement do nothing here can see it do everything
   there, and tell the difference.

`[TBC — identity and access]` — whether a residency constraint applies to
*derived* figures computed from public inputs, which is not obviously the same
question as whether it applies to the inputs.

### B.3 Model-risk annotation

**Not applicable — Assembly Mode 1.** The Standard requires this section for
Modes 2 and 3 only. **No LLM is invoked on any path in §D**, and gate `OFS-G07`
asserts it.

### B.4 Request parameter surface

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `lei` | string(20), required | **A** — the anchor | — |
| `intent` | enum, required | **P** — selects the policy envelope and the bound ratio definitions | — |
| `periods` | int 1–12 | **T** — the window | `4` |
| `basis` | enum `as-reported` \| `latest-restated` | **T** — semantics, not window | `as-reported` |
| `include_peers` | bool | payload shape | `false` |
| `peer_basis` | enum `sic` \| `sic-and-size` | peer set | `sic` |
| `debt_tolerance` | float | **P** — the ceiling above which assembly refuses | `0.25` provisional, `[TBC — this build, phase P8]` |
| `as_of` | — | **ABSENT.** See §B.5 | — |

**`basis` is the parameter this rung exists for.** The article states it
exactly, and the estate backs it:

> `as-reported` returns the figure as it was filed for that period.
> `latest-restated` returns the figure as most recently amended. **These are
> different numbers for the same period**, and which one is correct depends
> entirely on the decision: a covenant test asks what was reported at the time;
> a trend analysis asks for the restated series. **One parameter, two legitimate
> truths.**

**Measured backing: 321 fact-cells across 37 of the 50 obligors genuinely
change value between filings** (§C.4 trap 1). The article's manufacture envelope
asked for *"~3 obligors carrying a genuine restatement... without a restatement
the `basis` parameter has nothing to demonstrate."* **There are 37.** Nothing
needs engineering, and §F.1 records the element as satisfied on that basis.

### B.5 Prerequisites, consumers and scope boundary

**Prerequisite — satisfied, measured.** `counterparty-reference-snapshot`
supplies LEI→CIK. **50 of 50 obligors resolve, 0 orphans.**

**Downstream consumers.** `credit-exposure-rollup` (rung 05),
`rating-and-spread-migration` (rung 10), `credit-memo-context` (rung 14).

**Scope boundary — PROPOSED, not quoted.** The article's `out_of_scope` is
`null`, which the vault's own notice says means *not stated*, never *nothing*.
The following is therefore this document's proposal and is `[TBC — vault]`:

| Out of scope | Why | Belongs to |
|---|---|---|
| **`as_of` — reconstructing the spread as it stood on a past date** | Requires ledger time-travel, which arrives at Tier 3 | `covenant-in-force-as-of` (rung 08) |
| Exposure aggregated across a family | a rollup, not a spread | `credit-exposure-rollup` |
| Rating actions and market spreads | different signal entirely — and note `ccf_v2.spread_observation` is **that** product's table, not this one (§C.4 trap 4) | `rating-and-spread-migration` |
| Covenant compliance computed from these figures | needs the covenant text | `covenant-cross-reference` (rung 13) |

**`as_of` is declared-but-inert and must fail loudly**, returning **`400
not_supported_at_tier`** — the tier boundary doing its job rather than a gap.
Gate `OFS-G06` asserts the refusal.

> **Known SDK limitation, carried forward from rung 02.**
> `ProductRequestViolation.reason` is a closed `Literal` with no
> `not_supported_at_tier` member. Rung 02 recorded this as its §F.4 finding 2
> and it is **still open**. §F.4 finding 5 restates it; the build will need the
> same workaround rung 02 used, and it is not invented here.

---

## Section C — Data catalog

**Everything below was measured on 2026-08-29** against `parkavedb` schema
`ccf_v2`, read-only. This product was recorded as **`unprobed`** in
`CONTEXT-PRODUCT-LADDER-AND-ESTATE.md` before this document; the caveat there
was explicit that what the survey listed was *"what the tables hold, not a
verdict on the specs."* This section is the verdict.

> **Column presence is a weaker test than element satisfaction.** Rung 01 was
> declared *"fully backed"* on column presence and reported **three real gaps**
> once its elements were checked one by one. Every row below is checked as an
> element.

### C.1 Element table

One row per element, not per column. The system of record names the store, the
schema and the table.

| # | Element | System of record | Provenance class | Classification | Capability class | `G` | Ontology IRI | Satisfied? |
|---|---|---|---|---|---|---|---|---|
| 1 | Tagged financial facts — revenue, EBITDA components, debt, cash, interest expense | SEC XBRL `companyfacts` → **PostgreSQL** `ccf_v2.financial_fact` | `public-filing` | `public` | `relational` | **E** | **`[TBC — ccf_dataprep]`** — §C.1.1 | **yes** — 15,055 rows, 50 obligors, 21 tags |
| 2 | `period_end` · `period_start` · `filed_date` · `accession` · `form` · `unit` per fact | XBRL companyfacts → same table, carried natively | `public-filing` | `public` | `relational` | **T** · **L** | **`[TBC — ccf_dataprep]`** — §C.1.1 | **yes** — six columns, non-derived, on every row |
| 3 | Restatement chain — same fact, multiple accessions, **different value** | XBRL companyfacts ordered by `filed_date` | `public-filing` | `public` | `relational` | **T** | **`[TBC — ccf_dataprep]`** — §C.1.1 | **yes — 321 cells, 37 of 50 obligors.** §C.4 trap 1 |
| 4 | Peer facts at identical period | SEC XBRL `frames` → **PostgreSQL** `ccf_v2.peer_fact` | `public-filing` | `public` | `relational` | **E** | **`[TBC — ccf_dataprep]`** | **yes** — 22,494 rows; 22,083 match on `(period_end, tag)` |
| 5 | SIC / cohort for peer-set construction | EDGAR submissions → **PostgreSQL** `ccf_v2.peer_entity`, `.peer_cohort` | `public-filing` | `public` | `relational` | **E** | **`[TBC — ccf_dataprep]`** | **yes** — 1,678 entities, 324 cohorts |
| 6 | **US-GAAP tag → spread-line mapping** | internal spreading convention → **deployment artifact** | `internal-SOR` | `internal` | `relational` | schema | n/a — a mapping, not an entity | **NO in estate — by design.** §C.4 trap 3 |
| 7 | **Derived ratio definitions** — leverage, coverage, fixed-charge | internal credit policy → **deployment artifact**, Policy-loaded | `internal-SOR` | `internal` | `relational` | schema | n/a | **NO in estate — by design.** §C.4 trap 3 |
| 8 | **Internal adjustments** — addbacks, pro-forma EBITDA | internal credit analysis → **deployment artifact** | `internal-SOR` | `internal` | `relational` | **E** | **`[TBC — ccf_dataprep]`** | **NO in estate — by design.** §C.4 trap 3 |
| 9 | Entitlement scope | entitlement service → **PostgreSQL** `ccf_v2.principal`, `.principal_jurisdiction` | `internal-SOR` | `internal` | `relational` | **P** | `[TBC — ccf_dataprep]` | **yes** — 4 principals; **suppresses nothing**, §B.2 |
| 10 | **Item 4.02 non-reliance filing counts** | EDGAR 8-K item counts → **PostgreSQL** `ccf_v2.filing_profile` | `public-filing` | `public` | `relational` | **T** | **`[TBC — ccf_dataprep]`** — §C.1.1 | **yes — 11 of 50 obligors**, 15 filings. §C.4 trap 2 |
| 11 | **Policy-version binding** — which `PolicyVersion` was in force at `asked_at`, its validity window, and its `supersededBy` link | credit policy → **Fluree `fibo-v2`**, `ex:PolicyVersion` | `internal-SOR` | `internal` | `relational` (a **lookup by IRI, not a traversal** — §C.2) | **P** · **T** | `ex:PolicyVersion` — **bound**, unlike rows 1–10 | **yes — 17 instances**, 2 carrying `supersededBy`, `validFrom` on all 17. **Estate-ready; STAGED out of Gate 2** — §C.6.1 |

> **Element 10 is not in the article.** It was found while probing and is
> **added** here: SEC 8-K **Item 4.02 is *Non-Reliance on Previously Issued
> Financial Statements*** — the filer's own formal declaration that a prior
> figure should not be relied on. That is the restatement *event*, natively
> sourced rather than inferred. Its coverage is the subject of §C.4 trap 2 and
> it is **not** sufficient on its own.

**Three of ten elements are NOT satisfied by the estate** (6, 7, 8). See §C.4
trap 3 for the resolution, which is **not** "ask `ccf_dataprep` for tables.

> **The provenance column uses the Standard's closed list**, not the estate's
> labels. §3.1 fixes it at `internal-SOR · vendor · public-filing · derived ·
> inherited`. The estate's own `provenance_values` — `public`,
> `synthetic — internal`, `synthetic — engineered`, `derived` — are **estate
> properties describing how the demonstration data was produced**, and
> [[estate-data-catalog]] says plainly that they *"do not belong in a §C
> provenance column."* A draft of this table used them; it is corrected here.
>
> **This product has no `synthetic — engineered` element at all** — nothing was
> planted to make a condition the public data would not supply. The vault's
> envelope anticipated engineering a restatement; **321 real ones made that
> unnecessary.** That is worth stating, because the engineered class is where a
> demonstration is most open to challenge.

#### C.1.1 The ontology column is empty for this product, and the reason is structural

**Every attribute row above carries `[TBC — ccf_dataprep]`.** That is not this
document declining to look it up. The binding article
(`wiki/context-products/content/fibo-iri-binding.md`) was searched on
2026-08-29:

| Term | Occurrences in the binding article |
|---|---:|
| `obligor-financial-spread` | **0** |
| `XBRL` · `companyfacts` | **0** |
| `FinancialReport` · `Revenue` · `MonetaryAmount` | **0** |
| `LegalEntity` | 19 |

The article carries product-named vocabulary sections for **eleven** other
products — `kyc-refresh-beneficial-ownership`, `client-360-coverage-graph`,
`collateral-and-setoff-coverage`, `treasury-liquidity-position`,
`rating-and-spread-migration`, `fx-post-trade-reconciliation`,
`abs-securitization-surveillance`, `credit-exposure-rollup`,
`credit-surveillance-early-warning`, `ib-opportunity-synthesis`, and the
covenant work — **and none for this one.**

**The entity is bound; the attributes are not.** This product's *anchor* is a
`LegalEntity`, and rung 01 established the seven-class Commons/FIBO typing chain
that every product inherits — gate `CPR-G06` there asserts its completeness
because *"a partial chain propagates catalog-wide."* This product anchors on the
same LEI and inherits that chain unchanged.

What has no binding is the **payload**: a tagged financial fact, its period, its
filing, its accession.

**And that is a boundary rather than an omission.** FIBO and Commons are an
ontology of **entities and relationships** — which is precisely what `fibo-v2`
carries as the semantic layer (§C.2). **This is the first product on the ladder
whose payload is almost entirely *attributes and time* rather than entities and
edges**, so the vocabulary has nothing to say about it. From rung 04 the
products become edge-shaped, and the semantic layer begins to carry them.

**Two consequences, both recorded rather than resolved here:**

1. The binding article's own description states that *"coverage is closed
   against every spec in this catalog as of the Wave 8 binding; the next gap
   will come from a new spec."* **It is not closed for this spec, and this spec
   is not new** — it is rung 03 of the original 21. Recorded as §F.4 finding 8
   and returned to the vault under §11.
2. **Nothing here blocks the build.** This product does not write to `fibo-v2`
   and asserts no types (§C.2, gate `OFS-G05`). The binding matters at rung 05,
   where `credit-exposure-rollup` traverses the family tree and needs these
   figures attached to entities the graph already types. **The gap should be
   closed before rung 05, not before Gate 2 here.**"

### C.2 Capability decomposition

| Capability class | Used for | Store |
|---|---|---|
| `relational` | every step in §D without exception | PostgreSQL |
| `graph-traversal` | **none.** Fluree is read, but by **IRI lookup** — no edge is walked, no depth is taken. Traversal arrives at rung 04 | — |
| `vector-index` | **none** | — |
| `bitemporal-ledger` | **not used** — though one **exists** in `fibo-v2` (1,107 `supersededBy`). Deliberately untouched; that is the point of the rung | Fluree, unused |

**The ledger is not absent from the estate. It is absent from this product.**
This is the sharper statement and it is the teaching content. `fibo-v2` carries
**3,022 `validFrom` and 1,107 `supersededBy`** assertions — a working bitemporal
ledger, one store away. This product handles a **changing past** — 321 figures
that were restated — using nothing but `filed_date` ordering within a relational
table, **while that ledger sits unused.**

Rung 08 (`covenant-in-force-as-of`) therefore does not *introduce* time-travel;
it **turns on a capability already present**. A reader who has seen the
relational version first can see exactly what the ledger buys, because the
alternative was available the whole time and was not taken.

**The estate's division of labor, per Q019 §3 — this is the frame the rest of
this section argues inside.**

| Store | Owns | Relevance here |
|---|---|---|
| **Postgres `ccf_v2`** | **`E`, policy reference** | **every element of this product** |
| Fluree `fibo-v2` | `R`, `T`, lineage, **policy binding** | **the policy binding, and only that** — §C.6, **staged out of Gate 2** per §C.6.1. Its `R` and its ledger stay untouched either way |
| MongoDB `fibo_v2` | passage-level lineage | nothing — no document text is read (§C.4 trap 3 of rung 02's kind) |
| SQLite departmental | departmental | nothing |
| Neo4j | optional | nothing — v1 hello-world sample, not v2 data |

> **A tension worth naming rather than smoothing.** Fluree owns `T`, yet three
> of this product's elements are marked `T` (rows 2, 3, 10) and all of them live
> in Postgres. That is not a violation; it is **the definition of this rung.**
> The temporal axis here is *attribute-level and filing-derived* —
> `period_end`, `filed_date`, `accession` carried on the fact itself — not the
> graph's bitemporal axis of `validFrom` / `supersededBy`. **A product can carry
> time without carrying the ledger's time**, and this is the one that shows it.

**Fluree carries exactly one thing for this product — the policy binding — and
carries none of its payload. The reason is structural as well as measured.**

**Structural — the division of labor.** Per Q019 §3, `fibo-v2` owns **`R`, `T`,
lineage and policy binding**: the typed edge graph — ownership, control,
guarantee, cross-default, syndicate, collateral, set-off — over the FIBO
ontology. **Its nodes carry LEI and label only; every attribute resolves
elsewhere.** Elements 1–10 of §C.1 are `E`, `T` or schema and **not one is `R`**,
so Fluree could not supply them without abandoning the split that makes it
useful — *"no store duplicates another's authority"* (Q019 §7).

**Element 11 is the exception, and it is an exception on principle.** Q019 §3
assigns policy **binding** to Fluree and policy **values** to Postgres — the
§7.8 Control-plane / Data-plane split. A product that read its `policy_version`
from Postgres would collapse that split silently. §C.6 is where this product
does not.

**Measured — the ledger was queried anyway**, on 2026-08-29, because a store
assignment is a claim rather than evidence. `fibo-v2` holds **87,162 triples
over 11,906 subjects, **171 predicates** and 91 classes, with 449 `ex:lei` nodes**
— and **not one tagged financial fact.** No XBRL-shaped entity, nothing carrying
`period_end`, `filed_date` or `accession`, nothing within two orders of
magnitude of this product's 15,055 facts. The three classes whose names invite
the mistake were each opened:

| Class | Instances | What it is | Belongs to |
|---|---:|---|---|
| `PriorObservation` | 50 | a synthetic **credit-rating / signal** observation — `signalAbout` → a `Corporation`, `validFrom` a date | rung 10 |
| `MeasurementPeriod` | 11 | **document passage offsets** — `documentId`, `startOffset` | rung 13 |
| `FilingPosture` | 2 | a policy posture with an effective date | policy / regime |
| `Report` | **0** | a declared class with no instances | — |

**A store assignment is not evidence that the other stores are empty of
relevant material.** This one is, and the check is recorded so the next author
does not have to repeat it — or, worse, skip it.

> **A counting trap met while doing this, worth carrying.** A first pass
> reported *"17,697 typed subjects"* — which is the count of subject-**type
> pairs**, not subjects. A subject carrying `LegalEntity`, `Organization` and
> `FormalOrganization` is counted three times, and the tell was visible in the
> output: those three classes each read exactly **854**. The subject count is
> **11,906**. Same error class as §C.4 trap 1, in a different store: **a count
> is only a count of what its key actually is.**

### C.3 Correlation key, single-writer discipline, and identity authority

**Correlation key.** `LEI → CIK`, via `ccf_v2.crosswalk` from rung 01.
**Measured: 50 of 50, 0 orphans.**

**A convenience that must not become the contract.** `ccf_v2.financial_fact`
carries **both** `lei` and `cik` on every row, so this product *could* resolve
without the crosswalk. **It must not.** The `cik` on the fact table is a
denormalized convenience of this estate; the authority for LEI→CIK is rung 01's
crosswalk, and a product that read the local column would silently stop
depending on its declared prerequisite — and would keep working right up until
an estate without that column. Gate `OFS-G02` asserts resolution **goes through
the crosswalk**.

**`peer_fact` has no `lei` — only `cik`.** Peer identity is therefore CIK-native
and peers are **not** resolved to LEIs. This is correct at this tier: peers are
a comparison cohort, not counterparties, and giving them counterparty identity
would imply an entitlement surface they do not have.

**Single writer.** Nothing in §D writes. All reads are `SELECT`. Entry to `L3`,
were any to occur, is through `L2` only.

### C.4 The traps — what the data does not support cleanly

Five, each with the binding chosen and what it costs.

#### Trap 1 — accession multiplicity is not restatement, and the key decides it

**The single most important measurement in this document**, because the naive
form of it is what a competent engineer would write first.

Grouping facts and counting *accessions* suggests restatements everywhere.
Counting *distinct values* on the **correct key** finds a twelfth as many:

| Measure, on key `(lei, tag, unit, period_end, fiscal_period)` | Cells |
|---|---:|
| total fact-cells | 11,118 |
| with **more than one accession** | 3,547 |
| with more than one accession but **identical value** — the trap | **3,226** |
| **with more than one distinct VALUE — genuine restatements** | **321** |

3,226 of the 3,547 are the same figure re-reported as a **prior-period
comparative**: a 10-K reports FY2021, and the next three 10-Qs and the following
10-K all carry FY2021 again, unchanged. Five accessions, one number.

**And the key itself invents restatements if it is short.** Measured:

| Grouping key | Cells reported as "restated" | What the excess is |
|---|---:|---|
| `(lei, tag, period_end)` | **410** | — |
| `+ unit` | 407 | **3 currency artifacts** |
| `+ unit, period_start` | 392 | 15 duration artifacts |
| **`+ unit, fiscal_period` — the estate's own key** | **321** | **a further 71**: `period_start` and `fiscal_period` cut differently, and 125 `(period_end, fiscal_period)` groups span more than one `period_start` |
| `+ unit, period_start, fiscal_period` | 317 | 4 more, and **too strict** — see below |

**Why the estate's key and not this document's.** `period_start` was *invented
here*; `fiscal_period` is what `ccf_v2.financial_fact` **declares**:

```
PRIMARY KEY (cik, tag, unit, period_end, fiscal_period, accession)
```

Strip `accession` — the filing, which is exactly what a restatement varies — and
what remains is the store's own statement of what makes a fact *the same fact*.
`lei` substitutes for `cik` because the two are **1:1 across all 50 obligors**,
measured. Adding `period_start` on top drops four further cells, but a filer who
restates a **period boundary** has restated the fact; treating that as a
different fact hides a real correction. **The estate's identity is the binding,
and a self-authored key is an assumption that counts.**

- **Currency.** Accession `0000050725-19-000077` reports
  `RevenueFromContractWithCustomerIncludingAssessedTax` for period-end
  2019-09-30 as **CAD 3,500,000** *and* **USD 2,209,289,000**. One filing, one
  tag, one period, two units. Not a restatement.
- **Duration.** A Q3-only figure and a nine-month year-to-date figure both carry
  `period_end = 2019-09-30` and differ only in `period_start`. Collapsing them
  reads a **duration difference as a restatement** — the same error the article
  warns about across peers (*"comparing a Q3 figure to a peer's Q2"*), except it
  bites inside a single obligor, where it is harder to see.

**Binding.** The restatement key is
**`(lei, tag, unit, period_end, fiscal_period)`** — the estate's own primary key minus `accession` and is declared in the recipe
artifact, not in code. Gate `OFS-G03` asserts that a shorter key is not in use,
by requiring the census the build reports to equal **321** — and not 392, 410 or 3,547.

> **What this costs.** Nothing in capability; it costs the build a temptation.
> An engineer who "fixes" a low restatement count by relaxing the key will make
> the number go up and the product go wrong, and `OFS-G03` is written to catch
> exactly that direction of change.

#### Trap 2 — the native restatement signal exists and covers less than a quarter

Element 10 gives a filer's own **Item 4.02** declaration. It should be the
signal. Measured against the 39 obligors whose values actually change:

| | has Item 4.02 | no Item 4.02 | total |
|---|---:|---:|---:|
| **value genuinely changed** | **9** | **28** | 37 |
| no value change | 2 | 11 | 13 |
| total | 11 | 39 | 50 |

**Only 9 of 37 real restatements carry a formal non-reliance filing**, and 2 of
the 11 filings correspond to no value change in this estate.

**Binding.** Item 4.02 is used as **corroboration when present and never as the
detector.** Detection is value comparison on the trap-1 key; a payload whose
period carries an Item 4.02 additionally sets a `formally_restated` marker. A
build that detected restatement *from* Item 4.02 would miss 28 of 37; a build
that detected it from accession count would report 3,547. Gate `OFS-G04`
asserts both directions.

#### Trap 3 — three elements are absent from the estate, and that is correct

Elements 6, 7 and 8 — the tag→spread-line mapping, the ratio definitions, the
internal adjustments — **do not exist in `ccf_v2`**, and `provenance` on
`financial_fact` is `public` for all 15,055 rows, so no internal-classified fact
exists to carry them.

**This is not a gap to be filled by `ccf_dataprep`.** All three are
**Control Plane artifacts of the deployment**, not estate rows:

- The article itself says the ratio definitions are *"versioned policy rather
  than code"* and that the Policy step *"load[s] the internal ratio definitions
  bound to `intent`"*. A definition loaded by Policy and emitted as
  `policy_version` **is** a Control Plane artifact by construction.
- Putting them in the estate would make a **domain value** into fabric state,
  which the No-Hardcoding Rule forbids just as firmly as putting them in code.

**Binding.** Elements 6, 7 and 8 ship as versioned artifacts under the example's
`artifacts/`, are referenced by URI from the deployment, and are **never**
literals in a `.py` file. §F.1 marks them **satisfied-by-artifact**, which is a
different verdict from *satisfied by the estate* and is recorded as such.

#### Trap 4 — `spread_observation` is a different product's table

`ccf_v2.spread_observation` (47,849 rows) carries `spread_bp`, `market_oas_bp`,
`benchmark_bp`, `yield_bp`, `years_to_maturity`, keyed by `instrument_id`.

**That is a credit spread in basis points. This product is a financial spread —
a spreadsheet of standardized financials.** The word is overloaded and the
tables are one `ILIKE '%spread%'` apart. `spread_observation` belongs to
`rating-and-spread-migration` (rung 10).

**The collision occurs twice, in two different stores.** Fluree's
`PriorObservation` (50 instances) is the same rung-10 signal, and it is keyed by
**the same obligor LEIs as this product's facts** — `prior-obs-` plus the LEI.
The obligor whose `NetIncomeLoss` restated by 428% (§E.5) has a
`PriorObservation` too, about something else entirely. A build that reached for
"the observation about this obligor" would find a rating signal and serve it as
a financial fact, and both stores would have answered correctly.

**Binding.** This product does not read `spread_observation`. Gate `OFS-G05`
asserts the table is absent from the executed query set — a cheap assertion that
prevents an expensive confusion.

#### Trap 5 — one revenue line, four tags, and one obligor with none

A "revenue" figure is not one tag. Measured, by obligors carrying each:

| Tag | Obligors |
|---|---:|
| `Revenues` | 39 |
| `RevenueFromContractWithCustomerExcludingAssessedTax` | 37 |
| `SalesRevenueNet` | 25 |
| `RevenueFromContractWithCustomerIncludingAssessedTax` | 10 |
| **carrying none of the four** | **1** |

The four overlap — an obligor commonly carries two or three across its history
as US-GAAP tagging changed. This is element 6's mapping doing real work, not a
formality, and it is why the mapping is a versioned artifact with a precedence
order rather than a lookup.

**Binding.** The mapping artifact declares the precedence. **One obligor cannot
be spread for revenue at all** and its revenue line is served
`NOT_EVALUABLE` — **never `0`**, which reads as a company with no sales. Gate
`OFS-G08` asserts the refusal shape.

### C.5 Instant and duration facts are both in scope

**`period_start` is NULL on instant facts and populated on duration facts.**
Measured:

| Kind | `period_start` | Facts | Example tags |
|---|---|---:|---|
| **instant** (balance sheet) | **NULL** | **8,088** | `Assets`, `CashAndCashEquivalentsAtCarryingValue`, `StockholdersEquity`, `LongTermDebt` |
| **duration** (income statement) | populated | **6,967** | `Revenues`, `NetIncomeLoss`, `OperatingIncomeLoss`, `InterestExpense` |

**Instant facts are the majority — 8,088 of 15,055 — and a duration-only
analysis is a defect, not a simplification.** Leverage needs `LongTermDebt`
(instant) over EBITDA (duration); a spread built from duration facts alone
cannot compute a leverage ratio at all.

**This is a live hazard, not a hypothetical.** During the estate probe for this
document, a `JOIN ... USING (period_start)` silently dropped **every instant
fact**, because in SQL `NULL` never equals `NULL`. The join returned a clean,
plausible, internally consistent restatement profile covering **280 of the 392 then counted
cells** and announced no error. The corrected census — via a single `GROUP BY`,
where NULLs group together — is **321** on the estate's key.

**Binding.**
- Any grouping or joining on `period_start` uses `IS NOT DISTINCT FROM`, or a
  single `GROUP BY`, and **never** `JOIN ... USING`.
- The payload carries instant and duration facts and marks which each is.
- **Gate `OFS-G01`** asserts the served payload contains **at least one instant
  and at least one duration fact**, and that the restatement census equals the
  full-key figure. A duration-only payload fails it.

> The general shape, worth naming because it recurs: **a join that silently
> drops NULLs produces an answer with no error attached to it.** The defect
> presents as a smaller number, and a smaller number looks like a cleaner
> dataset. §F.4 finding 1.

### C.6 The second store — the policy binding, and why it is not decoration

**Ruled by Dave, 2026-08-29: this product is comprised of content from two
sources.** The binding below is what makes that true on principle rather than by
adding a join.

**What a naive Fluree join would have bought: nothing defensible.** All 50
obligors are present as `ex:lei` nodes (449 in the ledger, sampled and
confirmed), so a join *works* — and returns the obligor's **display label**,
which `ccf_v2.legal_entity` already owns. That is a duplicated authority, which
Q019 §7 forbids outright. **"Two stores" is not a goal that justifies a join.**

**What Fluree genuinely owns here.** `ex:PolicyVersion` — **17 instances,
`validFrom` on all 17, `validTo` on 3, `supersededBy` on 2.** Two families:

| Family | Members | Carries |
|---|---|---|
| **credit policy** | `credit-policy-v1.0` (2023-08-13 → 2025-06-23), `credit-policy-v1.1` (2025-06-24 →) | identity and validity window — **the binding** |
| credit-memo policy | `credit-memo-policy-v1` (2024-01-01 → 2025-06-30, `supersededBy` → v2), `credit-memo-policy-v2` (2025-07-01 →) | **values**: `debtToleranceDefault`, `creditLimitEnvelopeUsd`, `regOInsiderThresholdUsd` |
| posture | 13, jurisdiction × intent | `postureIntent`, `postureJurisdiction`, `postureLevel` — **rung 09's**, not read here |

**The binding this product takes** is the *credit policy* version in force at
`asked_at`: its IRI, its `validFrom`/`validTo`, and its `supersededBy` where one
exists. It is emitted as `policy_version` in lineage (§D.6). It is a **lookup by
IRI with a validity predicate — not a traversal**; no edge is walked and no depth
is taken, which is why this product remains a `relational`-capability product
while reading two stores. **Multi-store and Tier 2 are different claims**, and
only the second is about capability.

**Why this fits *this* product rather than any product.** The subject of rung 03
is *which value was true when, and when did we learn it*. A policy version with a
validity window is that same question asked about the **rule** instead of the
**fact**. The product therefore carries **two independent supersession axes**:

| Axis | Instances | Pins |
|---|---:|---|
| the fact restates | **321** cells, 37 obligors | which `accession` asserted the figure |
| the policy version supersedes | 2 `supersededBy` links | which rule was in force at the decision |

A replay must pin **both** — §D.5. Neither rung 01 nor rung 02 could ask that.

#### C.6.1 Staged — specified here, built at a later gate

**Ruled by Dave, 2026-08-29.** The two-store design above **stands as the
specification**. What is staged is the **build**, not the decision.

**Gate 2 builds the Postgres half only.** `policy_version` is emitted from the
Control Plane artifact, §D.3 says so explicitly, and no Fluree connection is
opened — which is why `OFS-G05` at Gate 2 asserts *no store but Postgres*, and
its Fluree clause activates later with the binding.

**Why staged rather than built now.** Credit spreading is specified Tier 1 with a
single prerequisite (LEI→CIK). The Fluree binding adds a second store and a second
failure mode, and Gate 2's subject is whether **the census was measured honestly**
— 321 not 392, instant included, accession multiplicity not mistaken for
restatement. Mixing *"did we count restatements correctly"* with *"does the policy
binding resolve across a supersession"* would let either failure be read as the
other.

**What defers with it, as one unit:** §C.1 element 11, the Fluree half of §C.2's
verdict, §F.3's Fluree row, and gate **`OFS-G14`**. **What does NOT defer:** the
Policy **operator** itself, which is the only operator in the plan — an empty
operator plan fails `empty-operator-guard` and the product cannot serve at all.
**The operator is mandatory; only its binding source is staged.**

**A finding rather than a binding.** `credit-memo-policy-v1` → `v2` moves
`debtToleranceDefault` from **`0.3` to `0.25`** across 2025-07-01. The same
obligor with the same facts can therefore **refuse under one policy and serve
under the other**, because the debt gate's threshold itself moved. This
product's `debt_tolerance` default of `0.25` (§B.4) matches v2 — so the value is
**not a guess**, but the artifact carrying it is named for `credit-memo-context`
(rung 14), and binding rung 03's threshold to another product's policy artifact
would be a stretch this document does not make. **Recorded as §F.4 finding 12;
the `[TBC — product owner]` at §F.2 row 8 now has a candidate source rather than
a blank.**

---

## Section D — Assembly recipe

### D.1 Client call

```
GET /context-products/credit-risk/spread/5493001KJTIIGC8Y1R12
      ?intent=annual-review&periods=8&basis=as-reported&include_peers=true
```

### D.2 Step table — and the operator question this rung does not decide

| # | Step | Layer | Is it an operator? | Reads | Emits | Fails |
|---|---|---|---|---|---|---|
| 1 | **Resolve** | **L2** | **no** | `lei` | obligor row, `cik` via crosswalk | fail closed → **404** |
| 2 | **Policy** | **L4** | **YES — the only one** | resolved obligor; principal; `intent`; **`asked_at`** | `policy_version` (**at Gate 2: the Control Plane artifact** — §C.6.1); entitlement set and ratio definitions (Postgres/artifact); permitted set | **403**; source unreachable → **503**, never a permissive default |
| 3 | **Attribute batch-select** | **L2** | **no** — see below | permitted obligor, `periods`, `basis` | fact set, instant **and** duration | **404** if the obligor has no facts |
| 4 | **Peer batch-select** *(conditional)* | **L2** | **no** | period set from step 3, `peer_basis` | peer facts at **identical `period_end`** | degrade, never fail |
| 5 | **Derivation** | in-memory | **no** | steps 3–4 + step 2's definitions | ratios, each naming its inputs | `NOT_EVALUABLE` per line |
| 6 | **Contract assembly** | **L6** | **no** | all above | `ServableProduct`, `expires_at`, `payload_hash`, `context_debt` | **503** on gate refusal; **409** debt |

**One operator. That is the whole of the operator plan** —
`operators_invoked: ["policy.<key>"]`, key `[TBC — this build, phase P6]`.

#### D.2.1 Why the batch-select is L2 assembly and not an `Enrich` operator

**Ruled by Dave, 2026-08-29.** This document does **not** decide the operator
vocabulary question, and records the mismatch rather than resolving it.

The vault article declares `operators_invoked: [Resolve, Policy, Enrich]`, and
the Standard's **§10.2 closed operator vocabulary** has eight members including
`Enrich` — *"resolve nodes to attributes. Always batched."* The shipped SDK has
**four operator categories** — `PolicyFilter`, `SimilaritySelect`,
`TemporalAsOf`, `TraversalNeighborhood` — and **`Enrich` appears 0 times in all
of `src/`**, verified against a positive control.

Three facts decided the binding:

1. **The `D-59` seam permits a deployment operator, but the registry reads a
   *category* off it.** `build_operator_registry(..., deployment_operators=)`
   documents that *"which operators exist is per-deployment policy"* — the key
   is the deployment's, the **category** is one of the canonical four. A batched
   attribute fan-out over Postgres **before any graph exists** is not Traversal,
   not Temporal, not Policy and not Similarity. Registering it under one of them
   would be **a fake mapping** that made the lineage record say something untrue.
2. **Rung 02 already set the shape.** `CP-SPEC-002` treats `Resolve` as not an
   operator (it is `L2` entity resolution under `AssemblyWorker`) and contract
   assembly as not an operator (Standard §10.2 retires `Compose`). One of its
   three steps was an operator. This is the same shape with one more step.
3. **Nothing is lost.** The fan-out still happens, still batched, still one
   query per source per step (§D.3). What changes is only whether it is *named*
   as an L4 operator in lineage.

**The mismatch is recorded, not resolved: `[TBC — Dave]`, §F.2 row 1.** Rung 03
is **evidence for** the later four-versus-eight ruling, not the place to make it.

**And it carries a tripwire.** **Gate `OFS-G10`** asserts that
`operators_invoked` contains **exactly one** entry and that no operator whose
key or category is `Enrich` is registered. **If the vocabulary question is later
ruled in favor of the Standard's eight and an `Enrich` operator is added, this
gate turns RED** — and that redness is the signal to reopen §F.2 row 1, not a
regression. This is the same pattern rung 02 used to hold its TTL finding open.

### D.3 Step detail

**Step 1 — Resolve (L2).** `lei` → `ccf_v2.crosswalk` → `cik` → obligor row.
Through the crosswalk, never the denormalized `financial_fact.cik` (§C.3).
Witness: the crosswalk row consumed. **The witness is not `lei`** — that is the
caller's own input, and a witness the input alone satisfies is not a witness.

**Step 2 — Policy (L4, the operator).** The only operator in the plan, and the
step whose source is **staged** — §C.6.1.

- **Postgres `ccf_v2`** — the entitlement envelope from `principal`; the
  `intent`-bound ratio definitions from the deployment artifact. These are the
  policy **values**, and they are Gate 2's.
- **`policy_version` — AT GATE 2, from the Control Plane artifact**, and this
  document says so rather than implying otherwise. The Fluree `ex:PolicyVersion`
  binding specified at §C.6 is **not built at Gate 2**; when it lands, this
  bullet and `OFS-G14` activate together and nothing else in §D moves.

Runs **before** any fact is read, per composition invariant 1, even though it
suppresses nothing here (§B.2).

**Fails closed on its one source.** Entitlement unreachable → **`503`**, never a
permissive default. When the Fluree binding lands, a second failure mode joins
it — no `PolicyVersion` covering `asked_at` → **`503`**, never a fallback to the
newest version, because serving under a rule that was not in force is the failure
this product exists to make visible. Gate `OFS-G14`, deferred with it.

**Step 3 — Attribute batch-select (L2).** **One query for all periods and all
tags** — not one per period. §7.4 N+1 avoidance, and the article is explicit
that batching is mandatory rather than a variant.

- `basis=as-reported` → the **earliest** accession per fact-cell.
- `basis=latest-restated` → the **latest**.
- The fact-cell key is **`(lei, tag, unit, period_end, fiscal_period)`** — the estate's own primary key minus `accession` — §C.4
  trap 1. Grouping is by `GROUP BY`, or `IS NOT DISTINCT FROM`; **never**
  `JOIN ... USING (period_start)`, which drops all 8,088 instant facts (§C.5).

**Step 4 — Peer batch-select (L2, conditional).** Peers matched on
**`period_end`, never on `filed_date`**. The article: *"comparing a Q3 figure to
a peer's Q2 because they filed the same week is the classic spreading error, and
the operator forecloses it."* Foreclosed here by the join key.

**Step 5 — Derivation (in-memory, algorithmic).** Ratios from the
policy-versioned definitions. **No LLM.** Each derived figure records the
fact-cells it consumed — §D.6.

**Step 6 — Contract assembly (L6).** Not an operator.

**Budget:** per-step and total `[TBC — this build, phase P6]` against a declared
p95 envelope of `[TBC — this build, phase P6]`.

### D.4 Determinism class and payload hash

**Deterministic.** Same `(lei, intent, periods, basis, include_peers,
peer_basis, asked_at)` over the same estate → byte-identical payload.

`payload_hash` = sha256 over the canonical bytes of the served product.
Value for the pinned run: `[TBC — this build, phase P6]`.

**The `basis` parameter must change the content address** for an obligor with a
restatement, and must **not** change it for one without. Gate `OFS-G11`.

### D.5 Replay statement and replay test

Replay resolves the **exact** artifact versions — graph pin, policy bundle,
ratio-definition artifact, mapping artifact, prompt artifacts (none, Mode 1) —
never "latest."

`OFS-R01` — the three hashes `[TBC — this build, phase P6]`.

**The restatement makes replay falsifiable in a way rungs 01 and 02 could not.**
A replayed decision over a since-restated period must reproduce **the figure as
it stood at decision time**, not today's. The data condition this needs — a
mutable attribute plus a retained snapshot — **exists natively here**: that is
what a restatement *is*. Rung 02 had to record the same fixture as needing an
estate condition nobody had supplied; this rung has 321 of them.

### D.6 Emitted contract

`ObligorFinancialSpreadContract@v1.0.0`, `extra=forbid`.

Per-attribute, **not per product**:

| Field | Why |
|---|---|
| `period_start` (nullable), `period_end` | instant versus duration is visible, §C.5 |
| `unit` | the CAD/USD case, §C.4 trap 1 |
| `filed_date`, `accession` | which filing asserted **this** figure |
| `basis_applied` | which of the two truths this figure is |
| `policy_version` *(product-level)* | **at Gate 2** the Control Plane artifact's version; **after §C.6.1** the Fluree binding in force at `asked_at`, with its validity window. The field is the same either way — only its source moves |
| `restated` | the value changed across filings on the full key |
| `restatement_class` | **`precision` \| `material`**, §E.5 |
| `formally_restated` | an Item 4.02 exists — corroboration, §C.4 trap 2 |
| `inputs` (derived lines only) | the fact-cells this ratio consumed, §D.7.1 |

> **Lineage is carried per attribute because the question is asked per
> attribute.** *"The lineage record must survive a question about one figure,
> not just about the product as a whole."*

### D.7 Validation gates

**The SDK's shipped gates run unchanged, and no gate is added to the SDK.**
Ruled by Dave, 2026-08-29 (`D-IMPL-102` limb 3).

| Gate | Source | Applies here |
|---|---|---|
| `empty-operator-guard` | SDK | yes — one operator, non-empty |
| `lineage-strict-equality` | SDK | yes |
| `ttl-bounds` | SDK | yes — §B.1.1 |
| `source-attestation` | SDK | n/a — no A2A at this tier |
| `lineage-attributability` | SDK | n/a — **A2A peer attestation** (`D-IMPL-57`), *not* per-attribute lineage. §D.7.1 |

#### D.7.1 Per-attribute lineage completeness — example-local, and an unclosed SDK gap

The article asks for a fourth gate: *"per-attribute lineage completeness — a
derived ratio must name every input fact it consumed."*

**No such gate exists in the SDK, and none is added.** The similarly-named
`lineage-attributability` is A2A peer attestation and does **not** discharge it.

**The binding, per Dave's ruling:** the property is proven **example-locally** —
asserted in the recipe artifact and tested in `tests/examples/`, with
**nothing reusable added to `src/`**. The same bound as Phase 24.1's criteria 2
versus 18.

**Can it be proven at all without new SDK types?** Yes, at this tier, and the
reason is worth stating rather than assuming: the derived lines are computed in
**step 5, in-memory, from fact-cells the product already carries in the
payload**. The check is therefore *"every `inputs` entry on a derived line
resolves to a fact-cell present in this same payload, and every derived line has
a non-empty `inputs`"* — closed over the payload, needing no SDK type the
contract does not already have. **Gate `OFS-G12`** asserts it, example-locally.

**What the SDK genuinely lacks** is a *general* per-attribute lineage
obligation: nothing in `src/` requires any product to carry attribute-granular
lineage, so a product that dropped `inputs` would fail only this example's test
and no fabric invariant. **Recorded as §F.4 finding 2, unclosed**, owner Dave.

### D.8 The snapshot the printed run reproduces

Per `D-IMPL-218`. The demonstrated run assembles **over a named pin**, and the
loaders stay **off the demonstrated path** — *"run the loader, then observe the
product"* must not appear as a reproduction recipe.

- **Pin:** `asked_at` pinned to a stated instant; obligor, `intent`, `periods`,
  `basis` all stated; estate identified by schema and probe date. Exact values
  `[TBC — this build, phase P6]`.
- **Reproduction bar:** *same question → same answer*, not correspondence with
  the live world. A reader whose numbers differ has **re-derived, not replayed**.
- **The restatement facts are already in the estate** — 321 of them — so nothing
  needs loading to demonstrate `basis`, and no `load_*` step is part of the demo.

---

## Section E — Volatility, debt and materialization

### E.1 Half-life table

| Signal class | `λ_c` | Basis |
|---|---|---|
| Annual facts (10-K) | ~365 days | superseded by the next annual filing |
| Quarterly facts (10-Q) | ~90 days | superseded by the next quarterly filing |
| **Restatement** | **event-driven** | rewrites a closed period — **the earliest supersession case in the catalog** |
| Peer set composition | ~180 days | drifts as filers change SIC or exit |

**These are the vault's values and are not recalibrated here.** `λ_c` measured
against actual read frequency is `[TBC — this build, phase P8]`.

**The half-life is per signal class, not per product** — which is §A.1's
sentence expressed as a table. A payload mixing a 10-K annual with a current
10-Q carries two decay rates simultaneously, and a single product-level `λ_c`
could not express it.

### E.2 Debt model and per-component debt table

`D_c` combines freshness `F` and completeness `S`.

| Component | Contributes to | Weight |
|---|---|---|
| Fact staleness, **per attribute against its own class `λ_c`** | `F` | `[TBC — this build, phase P8]` |
| Missing revenue line (1 of 50 obligors) | `S` | `[TBC — this build, phase P8]` |
| Missing peer cohort | `S` | `[TBC — this build, phase P8]` |
| Ratio inputs incomplete → `NOT_EVALUABLE` | `S` | `[TBC — this build, phase P8]` |
| **Restatement pending** — Item 4.02 present, value not yet changed (2 obligors) | `F` | `[TBC — this build, phase P8]` |

> The last row is a real state this estate contains: **2 obligors filed a
> non-reliance notice and the corrected figure has not landed.** The right
> posture is elevated debt, not refusal — the figure is known to be wrong and
> the correction is known to be coming.

`debt_tolerance` default `0.25`, provisional, `[TBC — this build, phase P8]`.
Breach → **`409` with the debt block**, *not* a `200` with a warning.

### E.3 Materialization posture

**Materialized.** The article's reasoning is adopted: slow decay, high read
frequency, deterministic derivation.

Confirmed against the estate: 15,055 facts over 50 obligors and 262 period-ends
is a small, slow corpus, and the derivation is pure. **Restatement is the
invalidation trigger**, and §E.4 says how it is detected — which is the reason a
materialized posture is safe here rather than merely cheap.

### E.4 Supersession triggers

| Trigger | Detection | Cascade |
|---|---|---|
| New 10-K or 10-Q accession for the CIK | new `accession` on the fact key | refresh; **not** necessarily a restatement (§C.4 trap 1) |
| **Restatement** — value changed on the full key | **value comparison**, §C.4 trap 1 | invalidate the affected period for this product **and** downstream |
| **Item 4.02 non-reliance filing** | `filing_profile.count_8k_item_4_02` | **corroboration; covers 9 of 37** (§C.4 trap 2) |
| Peer cohort drift | SIC change or filer exit | refresh peer set only |

**Downstream cascade order** when a restatement lands: `credit-exposure-rollup`
(rung 05) and `credit-memo-context` (rung 14) both consume spread figures, and
`rating-and-spread-migration` (rung 10) consumes the trend.

### E.5 The two restatement classes — material and precision

**Ruled by Dave, 2026-08-29: `basis` must not treat a 5.3× change in
NetIncomeLoss and a $15,000 rounding of SalesRevenueNet as the same event.**

Both are in the estate, from the same obligor:

| Tag | Period | First filed | Later filed | Change | Class |
|---|---|---:|---:|---:|---|
| `NetIncomeLoss` | FY2017 | 7,800,000 | **41,200,000** | **+428%** | **material** |
| `SalesRevenueNet` | Q2 2015 | 405,615,000 | 405,600,000 | −0.004% | **precision** |

A credit officer cares enormously about the first and not at all about the
second. A `basis` parameter that surfaced both identically would be technically
correct and practically useless.

**The measured distribution across all 321 genuine restatement cells:**

| Band | Cells | Obligors | of which instant |
|---|---:|---:|---:|
| `< 1%` — precision | **100** | 23 | 38 |
| `1–5%` | 46 | 15 | 6 |
| `≥ 5%` — material | **175** | 32 | 22 |
| **total** | **321** | **37** | **66** |

**There is no natural gap in this distribution.** It is continuous from
rounding to restatement, with a substantial middle band. That is itself the
finding: **the threshold cannot be discovered in the data and must be a declared
policy value** — which is precisely why it lives in an artifact rather than in
code. A build that hard-coded `0.01` would be encoding a credit-policy judgment
as a constant.

**Binding.**
- `restatement_class ∈ {precision, material}`, computed as
  `|last − first| / |first|` against a threshold **declared in the artifact**
  (`artifacts/restatement.yaml`), **never a code constant**.
- The threshold's **default is proposed at `0.01`** and is
  `[TBC — product owner]` — the proposal is this document's, the ruling is the
  credit-policy owner's.
- `first_v = 0` or NULL → **`NOT_EVALUABLE`**, never a division and never a
  `material` default.
- Gate `OFS-G13` asserts the class is read from the artifact: changing the
  artifact's threshold must move cells between classes, and a build in which it
  does not has hard-coded it.

---

## Section F — Source binding and readiness

### F.1 Element readiness

| # | Element | Ready? | Note |
|---|---|---|---|
| 1 | Tagged financial facts | **yes** | 15,055 rows, 50 obligors, 21 tags |
| 2 | Per-fact temporal metadata | **yes** | six columns, native, no derivation |
| 3 | Restatement chain | **yes** | **321 cells / 37 obligors** — vault asked for ~3 |
| 4 | Peer facts | **yes** | 22,083 of 22,494 match on `(period_end, tag)` |
| 5 | SIC / cohort | **yes** | 1,678 entities, 324 cohorts |
| 6 | Tag → spread-line mapping | **satisfied by artifact** | absent from estate **by design**, §C.4 trap 3 |
| 7 | Ratio definitions | **satisfied by artifact** | as above; Policy-loaded, versioned |
| 8 | Internal adjustments | **satisfied by artifact** | as above |
| 9 | Entitlement scope | **yes** | 4 principals; suppresses nothing, §B.2 |
| 10 | Item 4.02 counts | **yes** | 11 of 50 obligors, 15 filings |

**No element is a build blocker.** Three are satisfied by artifact rather than
by estate, which is a **different verdict** and is recorded as one.

### F.2 Every `[TBC]` in this document, with an owner

**Built by enumerating every marker and mapping each to a row**, not by
comparing totals — rung 01's *"a count is not a roster."*

| # | Marker | Section | Owner | Cleared at |
|---|---|---|---|---|
| 1 | **`Enrich` / §10.2 four-versus-eight operator vocabulary** — the article and Standard declare `Enrich`; the SDK has four categories and no `Enrich` | §D.2.1 | **Dave** | a later vocabulary ruling — **not this rung** |
| 2 | Four-question build-test result — article is on the Q019 form | §0.1, §0.4 | **vault** | — |
| 3 | Assembly Mode confirmation (Mode 1 derived here) | §0.4, §B.1 | **vault** | — |
| 4 | Closed-taxonomy mode for the counterfactual | §A.1 | **vault** | — |
| 5 | Scope boundary — `out_of_scope` is `null` = not stated | §B.5 | **vault** | — |
| 6 | Residency constraints; derived-figure residency | §B.2 | identity and access | — |
| 7 | Cross-border serving condition | §B.2 | identity and access | — |
| 8 | **Restatement threshold** default `0.01` proposed | §E.5 | **product owner** | certification |
| 9 | `debt_tolerance` calibration (provisional `0.25`) | §B.4, §E.2 | product owner | P8 |
| 10 | Schema artifact `obligor_financial_spread.v1.json` | §B.1 | this build | **P6** |
| 11 | p95 budget — per step, total, envelope | §D.2 | this build | **P6** |
| 12 | `payload_hash` for the pinned run | §D.4 | this build | **P6** |
| 13 | Replay fixture `OFS-R01`, three hashes | §D.5 | this build | **P6** |
| 14 | Policy operator key | §D.2 | this build | **P6** |
| 15 | Pin values for the demonstrated run | §D.8 | this build | **P6** |
| 16 | TTL-anchor refusal counts, latest versus earliest | §B.1.1 | this build | **P6** |
| 17 | Sabotage result for each of the **fourteen** gates | §D.7, §G.2 | this build | **P7** |
| 18 | Counterfactual fixture `OFS-F01` — the two-`basis` comparison | §A.2 | this build | **P7** |
| 19 | `λ_c` measured against read frequency | §E.1 | this build | **P8** |
| 20 | Per-component `D_c` contributions — 5 rows | §E.2 | this build | **P8** |
| 21 | A coverage manifest in `spec_coverage.py` — currently `[UNMAP]` | §C preamble | `ccf_dataprep` | — |
| 22 | **Ontology IRI — the seven attribute rows of §C.1** (1, 2, 3, 4, 5, 8, 9, 10). The binding article has **no vocabulary for this product at all** and claims closed coverage | §C.1, §C.1.1 | `ccf_dataprep` | **before rung 05**, not before Gate 2 |
| 23 | **Catalog currency.** Every §C and §E figure is dated 2026-08-29 against a **live** estate; [[estate-data-catalog]] is stamped 2026-08-30T01:56:48Z at commit `5206155`. Neither is a stability promise | §F.3 | `ccf_dataprep` — regeneration on request | re-confirmed at **Gate 2** |
| 24 | **Two-store deviation.** The vault article declares `capability_classes: [relational]` and the ladder puts the first multi-store product at rung 04. This product reads **Fluree for the policy binding** on Dave's ruling of 2026-08-29, **staged out of Gate 2** (§C.6.1) so the vault's term is not overtaken by a build. Tier and build order are the **vault's** under the §1 ownership table | §0.4, §C.6.1 | **vault** | — |
| 25 | **Which `PolicyVersion` family binds this product** — `credit-policy-v*` carries the window but no values; `credit-memo-policy-v*` carries `debtToleranceDefault` and is named for rung 14 | §C.6, §F.4 finding 12 | **product owner** + `ccf_dataprep` | certification |

**Twelve are `this build` and clear at Gate 2. Five are the vault's. Two are
identity and access's. Three are the product owner's. Three are `ccf_dataprep`'s.
One is Dave's. Twenty-five in total.** (Row 25 is shared and counted once, to the
product owner.)

> **Rows, not markers.** the raw `[TBC]` occurrences map to these 23 rows: row 22
> alone covers nine markers in the §C.1 table, several rows are cited twice
> across sections, and four occurrences in §0.2 are the placeholder *classes*
> being defined rather than markers. **A count is not a roster** — rung 01's
> rule, and this document has now violated the underlying discipline twice
> (§C.4 trap 1, §F.4 finding 9), so the register is built by enumerating
> markers and mapping each to a row rather than by reconciling totals.

> **Row 1 is the one to watch.** It is the only marker whose resolution could
> change §D's shape, and it is deliberately **not** blocking: the build proceeds
> on the L2 binding, and `OFS-G10` turns red if the ruling later goes the other
> way.

### F.3 Access path, identifiers, history, volumetrics

**Estate binding — all five stores, with the verdict for each.** A reader asking
*"which stores does this product touch?"* should get the whole answer here rather
than an answer about the one it uses. Every store was checked on 2026-08-29;
§C.2 carries the reasoning, this table carries the result.

| Store | Owns (Q019 §3) | Checked | Verdict for this product |
|---|---|---|---|
| **PostgreSQL `ccf_v2`** @ `192.168.4.76:5432`, db `parkavedb`, read-only | **`E`, policy reference** | yes | **THE ONLY STORE READ.** All ten §C.1 elements |
| **Fluree `fibo-v2`** @ `:8090` | `R`, `T`, lineage, **policy binding** | **yes** | **SPECIFIED, staged out of Gate 2 (§C.6.1)** — then the policy binding only (`ex:PolicyVersion`, 17 instances), by IRI lookup. **Zero tagged financial facts**; nodes carry LEI and label only, so none of the payload comes from here. §C.6 |
| **MongoDB `fibo_v2`** @ `:27017` | passage-level lineage | yes | **not read.** Filing *text* and passages; this product reads filing *facts*. Passage lineage arrives at rung 13 |
| **SQLite** `data/departmental.sqlite` | departmental | yes | **not read.** 148 rows total; nothing financial-reporting |
| **Neo4j** @ `:7687` | optional | yes | **not read.** 14 nodes — the v1 hello-world sample, not v2 data |

**Two stores read, three excluded — a measured verdict, not a tier convention.**
Gate `OFS-G05` asserts the negative half of this table at runtime: MongoDB,
SQLite and Neo4j are never opened, and **the only Fluree read is the
`ex:PolicyVersion` lookup** — no edge traversal, and no attribute sourced from
the ledger.

| Table | Rows | Columns | Key facts |
|---|---:|---:|---|
| `financial_fact` | 15,055 | 16 | 50 obligors · 50 CIKs · 262 period-ends · 2008-06-30 → 2026-07-04 · `provenance` `public` on 100% |
| `peer_fact` | 22,494 | 15 | **`cik` only, no `lei`** · carries `frame` |
| `peer_entity` | 1,678 | 6 | |
| `peer_cohort` | 324 | 10 | |
| `filing_profile` | 50 | 10 | `count_8k_item_4_02` — element 10 |
| `crosswalk` | **83** | 7 | **50 of 50 obligors resolve, 0 orphans** |
| `principal` | 4 | 8 | `sees_mnpi`, `sees_need_to_know`, `perspective` |
| `principal_jurisdiction` | 17 | 3 | not used by this product — §B.2 |
| `legal_entity` | 156 | 24 | rung 01's table; anchor identity |

> **One figure in this table was wrong until it was measured.** A draft of this
> section carried `crosswalk = 53`, taken from
> `CONTEXT-PRODUCT-LADDER-AND-ESTATE.md` (28 Aug) rather than from the database.
> The measured value on 2026-08-29 is **83**. The document that repeatedly warns
> against counting the wrong thing had **inherited a count instead of taking
> one** — recorded here rather than quietly corrected, because the failure is
> the lesson. §F.4 finding 9.

**History depth.** 18 years. **Fiscal year ends: 16 of 50 obligors are
non-December** (Dec 34, Mar 4, Jun 4, Sep 3, Jan/Apr/May/Aug/Oct 1 each; sums to
50). The article's envelope asked for ~2. **Period alignment is a real
operation**, not a formality, and `peer_basis=sic` cohorts will straddle fiscal
calendars.

**Connection.** `CCF_CP_03_POSTGRES_DSN`, built from `ccf_dataprep`'s
`ccf.config.PG`. **`ccf_dataprep` is read-only to this repository.**

**Two catalogs were consulted, and both are dated.**

| Source | Stamp | Used for |
|---|---|---|
| Direct query of `ccf_v2` and `fibo-v2` | **2026-08-29** | every figure in §C and §E |
| [[estate-data-catalog]] — mirror of `ccf_dataprep/docs/store-catalog.md` | **generated 2026-08-30T01:56:48Z**, upstream commit `5206155` | the store partition, the **declared primary key** of §C.4 trap 1, the 171-predicate correction, the closed provenance vocabulary |

**Citing the stamp is the catalog's own requirement**, not a courtesy: it says
plainly that it is *"a snapshot, not a stability promise."* Where the two
disagree the repository wins, and `store-catalog.json` — which **MCP cannot
serve** — is read from the `ccf_dataprep` working copy directly.

**One number was taken from the catalog and then verified against the store**:
the 171 predicates. The catalog records that the ledger answers *"how many
predicates"* three ways — `COUNT(DISTINCT ?p)` → 178, `GROUP BY ?p` → 198,
`SELECT DISTINCT ?p` → **171, correct** — and that the aggregate forms invent 27
phantoms which return **zero rows**, one of which (`ex:AdministrativeAgent`) is a
**class, not a predicate**. A draft of §C.2 carried **178**. See §F.4 finding 11.

### F.4 Recorded findings — not `[TBC]`, because none needs a decision to build

1. **A `JOIN ... USING` on a nullable column silently drops the majority of a
   corpus.** Probing this estate, a join on `period_start` dropped all 8,088
   instant facts and returned a clean restatement profile over **280 of 392 on the key then in use**
   cells with no error. **The defect presents as a smaller, tidier number.**
   Bound at §C.5 and asserted by `OFS-G01`.
2. **The SDK has no general per-attribute lineage obligation.** Nothing in
   `src/` requires attribute-granular lineage; a product dropping `inputs` would
   fail only this example's test. Proven example-locally per Dave's ruling;
   **the SDK gap is recorded and left open**, owner Dave. §D.7.1.
3. **`lineage-attributability` is not what its name suggests.** It is A2A peer
   attestation (`D-IMPL-57`), not per-attribute lineage. Two readers of this
   catalog have now had to check. Naming finding only; no change requested.
4. **The TTL anchor's basis is a real choice with a measured consequence.**
   Latest-`filed_date` versus earliest changes the refusal population. Declared
   as latest; `OFS-G09` asserts it and turns red if changed. §B.1.1.
5. **`ProductRequestViolation.reason` still cannot encode a tier refusal.**
   Carried forward from rung 02 §F.4 finding 2, **still open**. §B.5.
6. **The estate exceeds its own manufacture envelope on three counts** —
   restatements 37 obligors versus ~3 asked, non-December fiscal years 16 versus
   ~2, peers 1,678 versus ~150. Recorded so a later reader does not "correct"
   the envelope to match the article.
13. **The vault article omits `debt_tolerance` and `as_of`, and this is the
   THIRD of three.** Both are universal under Standard §2.4; this article's
   request surface declares neither (`lei`, `intent`, `periods`, `basis`,
   `include_peers`, `peer_basis`). The vault ruled on rung 02, 2026-08-30:
   *"two of two is a pattern… **Do not wait for the vault on it** — both are
   universal under Standard §2.4, so add them at your level and record the vault
   article's omission as a finding."* That instruction is applied rather than
   re-asked: both are added at §B.4 and §B.5 — `debt_tolerance` with a `409`
   debt block, `as_of` declared-and-inert and refused
   `400 not_supported_at_tier` under `OFS-G06` — and the omission is recorded
   here rather than held as a `[TBC]`. **Three of three is no longer a pattern
   in the articles; it is a property of the q019 form**, and belongs to the
   vault's sweep rather than to any one product.

12. **A policy threshold is versioned, superseding, and changes value — and this
   product's own default matches the later version.** `credit-memo-policy-v1`
   (`validFrom` 2024-01-01, `validTo` 2025-06-30, `supersededBy` → v2) carries
   `debtToleranceDefault` **0.3**; `credit-memo-policy-v2` (2025-07-01 →)
   carries **0.25**. §B.4's provisional `0.25` is therefore **v2's actual
   value**, not an invention — but the artifact is named for `credit-memo-context`
   (rung 14), so this document **records the source without binding to it**
   (§F.2 row 25). The consequence worth naming: the same obligor with the same
   facts can **refuse under one policy and serve under the other**, because the
   debt gate's threshold moved rather than the data.

10. **The estate declares the identity of a fact, and this document invented one
   instead.** `ccf_v2.financial_fact` carries
   `PRIMARY KEY (cik, tag, unit, period_end, fiscal_period, accession)`. A draft
   keyed restatements on a self-authored `(lei, tag, unit, period_start,
   period_end)` and counted **392 across 39 obligors**; the estate's own identity
   minus `accession` gives **321 across 37**. The invented key over-counted by
   **71 cells and 2 obligors** — `period_start` and `fiscal_period` cut
   differently, and 125 `(period_end, fiscal_period)` groups span more than one
   `period_start`. **Read the declared key before writing one** (§C.4 trap 1).

11. **A store can answer the same question three ways and be wrong twice.**
   Fluree reports 178 / 198 / **171** predicates depending on the query form;
   the aggregate forms invent 27 phantoms that return zero rows, and an empty
   traversal reads as *"this estate has no such entities"* rather than *"this
   predicate is not real."* This product reads no Fluree, so nothing here is
   affected — recorded because §C.2's class census was taken by **enumeration**
   for exactly this reason, and a later rung will be tempted to aggregate.
   `ccf_dataprep` known-issues §56.

9. **A figure was inherited rather than measured, inside this document.**
   §F.3 carried `crosswalk = 53` from a planning document dated 28 Aug; the
   measured value is **83**. Caught only because the estate was summarized
   independently. **The rule that survives: a spec that says "measured" must
   have run the query, and a number copied from a sibling document is an
   inherited claim wearing a measurement's clothes.** Fixed; recorded because
   the class recurs.

8. **The FIBO binding has no vocabulary for this product, and claims closed
   coverage.** Zero occurrences of `obligor-financial-spread`, `XBRL`,
   `companyfacts`, `FinancialReport`, `Revenue` or `MonetaryAmount`, against
   product-named sections for eleven other products. The entity is bound and the
   attributes are not — a **structural boundary** of an entity-relationship
   ontology, not an oversight (§C.1.1). **Owner `ccf_dataprep`; needed before
   rung 05, not before Gate 2 here.**

7. **`spread_observation` is a naming collision waiting to happen** — 47,849
   rows of credit spreads one `ILIKE '%spread%'` away from this product.
   `OFS-G05` asserts it is never read. §C.4 trap 4.

---

## Section G — Operate and govern

### G.1 The attribute-level obligation, restated where an operator will look

| Field | Value |
|---|---|
| **Accountable owner** | product: Credit Risk · data steward: credit analysis / spreading · policy owner: identity and access — **roles, not individuals** |
| **Service objectives** | p50 / p95 assembly latency, volume, concurrency ceiling, payload bound, per-call cost: `[TBC — this build, phase P6]` |
| **Degradation contract** | **Mandatory** (fail closed): `lei` resolution, `cik` crosswalk, entitlement scope → `404` / `503`. **Non-mandatory** (serve with elevated `D_c` + notice): peer set, any individual ratio line, internal adjustments, debt-reconciliation context |
| **Debt model** | §E.2. `debt_tolerance` default `0.25`, provisional |
| **Observability** | per-step latency · `D_c` distribution · **gate-failure counts by gate, all fourteen** · **restatement-class split served (`precision` vs `material`)** · `NOT_EVALUABLE` rate by ratio line · **`basis` parameter usage split** · TTL refusal rate |
| **Retention and record of record** | The **filing** is record of record, identified by `accession`. The fabric references it and does not replace it. Replay-record retention tier: `[TBC — this build, phase P8]` |
| **Test fixtures** | `OFS-F01` counterfactual · `OFS-G01`…`OFS-G14` one per gate · `OFS-D01` degradation branch · `OFS-R01` replay hash assertion |
| **Lifecycle** | **`approved-not-built`** — Gate 1 authored and **approved by Dave, 2026-08-29**. Certification additionally requires every §F.2 row closed or accepted by a named owner |

**The obligation an operator must not lose.** Every served figure names the
period it describes, the filing that asserted it, and whether a later filing
changed it. **A payload that carries a number without those three is not a
degraded product; it is a different product** — the dashboard this rung exists
to contrast with.

### G.2 Acceptance criteria — each phrased so it can fail

| Gate | Assertion | Evidence |
|---|---|---|
| **`OFS-G01`** | The payload carries **at least one instant and at least one duration** fact, and the restatement census equals the **full-key** figure. A duration-only payload fails | §C.5 · 8,088 instant / 6,967 duration |
| **`OFS-G02`** | Resolution goes **through `crosswalk`**; `financial_fact.cik` is never the resolution path | §C.3 · 50 of 50, 0 orphans |
| **`OFS-G03`** | The restatement key is the estate's declared identity `(lei, tag, unit, period_end, fiscal_period)`; the census is **321** — not 392, not 410, not 3,547 | §C.4 trap 1 |
| **`OFS-G04`** | Item 4.02 is **corroboration, never the detector** — a restatement without a 4.02 is still detected (28 of 37), and a 4.02 without a value change is not reported as restated (2 of 11) | §C.4 trap 2 |
| **`OFS-G05`** | `spread_observation` is never read. **At Gate 2: no store but Postgres is opened at all.** After §C.6.1: the only Fluree read is the `ex:PolicyVersion` lookup — never `PriorObservation`, no edge traversal, no payload attribute from the ledger | §C.6.1, §C.4 trap 4 |
| **`OFS-G06`** | `as_of` is refused **`400 not_supported_at_tier`**, never silently honored | §B.5 |
| **`OFS-G07`** | **No LLM client is reachable** from any §D step — Assembly Mode 1 | §B.3 |
| **`OFS-G08`** | The obligor with no revenue tag serves `NOT_EVALUABLE`, **never `0`** | §C.4 trap 5 · 1 of 50 |
| **`OFS-G09`** | `expires_at` is 30 days from the **latest `filed_date` in the payload**, and does **not** move with `asked_at`. **Turns RED if the basis is changed to earliest** | §B.1.1 |
| **`OFS-G10`** | `operators_invoked` has **exactly one** entry and **no `Enrich` operator is registered**. **Turns RED if the §10.2 vocabulary is later adopted** — that redness reopens §F.2 row 1 | §D.2.1 |
| **`OFS-G11`** | `basis` **changes the content address** for a restated obligor and **does not** for an unrestated one | §D.4 |
| **`OFS-G12`** | Every derived line has a non-empty `inputs`, and every entry resolves to a fact-cell in the **same payload**. Example-local; nothing added to `src/` | §D.7.1 |
| **`OFS-G13`** | `restatement_class` is read from `artifacts/restatement.yaml` — **changing the artifact's threshold moves cells between classes** | §E.5 |
| **`OFS-G14`** *(DEFERRED — §C.6.1)* | `policy_version` names the **Fluree** binding whose validity window contains `asked_at`. Asking either side of a `supersededBy` boundary yields **different** `policy_version` values; a request whose instant no `PolicyVersion` covers is refused **`503`** and **never falls back to the newest** | §C.6, §D.3 |

**Every gate must be made to fail deliberately once.** `[TBC — this build,
phase P7]` — the sabotage applied to each and the observed result. **A gate that
has never been observed red is not evidence that it runs.**

**Two gates are written to go RED when something is later corrected** —
`OFS-G09` (TTL basis) and `OFS-G10` (operator vocabulary). Their redness is a
**signal, not a regression**, and each names the register row it reopens.

### G.3 Catalog contribution

What this rung adds that rungs 01 and 02 could not:

- **Attribute-level temporal validity.** The first product where one `λ_c` per
  product is insufficient and the payload says so per figure.
- **A past that changes.** 321 genuine restatements — the earliest supersession
  case in the catalog, handled **with no bitemporal ledger**, which is what
  makes rung 08's ledger legible when it arrives.
- **One parameter, two legitimate truths.** `basis` is the catalog's first
  parameter where both settings are correct and the decision picks.
- **A negative control for entitlement.** Policy runs and suppresses nothing —
  the contrast rung 17 needs.
- **Two stores, each doing only what it owns.** Postgres every attribute, Fluree
  the policy binding and nothing else — the §7.8 Control/Data-plane split made
  executable rather than described, **without a traversal and without a
  duplicated authority**. The first product in the catalog to read two stores,
  and it does so at `relational` capability.
- **Two independent supersession axes in one product** — the fact restates (321
  cells) and the policy version supersedes (2 links). Replay must pin both.
- **The measurement disciplines**, which generalize past this product: a count
  on the wrong key invents data (trap 1), a native signal can be real and
  insufficient (trap 2), an absent element can be correctly absent (trap 3), and
  **a NULL-dropping join reports a tidy number and no error** (§C.5).

---

## Gate 1 — status

**This specification is complete except for its `[TBC]` register at §F.2**, and
is submitted for Gate 1 review.

- **Nothing is implemented.** No code, no artifacts, no tests exist for this
  product. The example directory contains this document and nothing else.
- **Every figure was measured**, read-only, on 2026-08-29, against `ccf_v2` on
  `192.168.4.76`. The product was **`unprobed`** before this document.
- **Twelve `[TBC — this build]` rows clear at Gate 2.** Nine belong to other
  owners and are named rather than invented.
- **Two rulings from Dave, 2026-08-29, are recorded rather than re-litigated:**
  the batch-select is **L2 assembly, not an `Enrich` operator** (§D.2.1), and
  **no fourth gate is added to the SDK** (§D.7.1).
- **Three corrections are on the record, all of one class.** (1) An earlier count
  of `10,769` groups with multiple accessions was a summing error. (2) A
  restatement census of `410` used a key too short to exclude currency and
  duration artifacts. (3) The replacement key — `period_start` — was **this
  document's invention**, and reading `ccf_v2.financial_fact`'s **declared
  primary key** showed the estate's own identity uses `fiscal_period` instead;
  that moved the census from `392` to **321** and the population from 39
  obligors to **37**.
  **The measured figures are 11,118 fact-cells, 3,547 with more than one
  accession, 3,226 re-reported identically, and 321 genuine restatements across
  37 of 50 obligors.** Every figure in this document is derived from that census.
  **The general rule earned here: bind the identity of a fact to the store's
  declared key before inventing one**, because a self-authored key is an
  assumption that counts.

**Gate 1 is CLOSED — approved by Dave, 2026-08-29.** Gate 2 may begin. The twelve
`[TBC — this build]` rows at §F.2 clear when it does; the thirteen belonging to the
vault, `ccf_dataprep`, identity-and-access and the product owner do not, and are
not this build's to invent.
