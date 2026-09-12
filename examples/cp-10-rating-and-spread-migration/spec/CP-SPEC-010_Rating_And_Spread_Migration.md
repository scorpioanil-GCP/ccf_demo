---
product: credit-risk.rating-migration.v1
standard: v0-3
sdk_spec: cp-10
tier: 3
cost_band: "×2–4"
assembly_mode: 1
capability_classes: [relational, bitemporal-ledger, in-memory]
prerequisites: [counterparty-reference-snapshot, obligor-financial-spread]
build_order: 10
lifecycle: draft
accountable_owner: credit-risk-product-engineering
review_cadence: at every Control Plane change to the rating scale, the divergence
  thresholds or the λ_c table; and no less than annually
topic: context-products
title: Rating & Spread Migration — Context Product Specification
generated: '2026-09-12'
---

# Rating & Spread Migration — Context Product Specification

**`CP-SPEC-010` · Tier 3 · `credit-risk.rating-migration.v1`**
**Fluree for the bitemporal internal-grade history · PostgreSQL for the spread decomposition, the instrument reference and the policy tables**

> **Has this obligor deteriorated — and does the market think so before the
> credit file does?**
>
> Three signals, three clocks, and the answer lives in their disagreement.

## 0 · What this document is

A build specification for the engineer who will assemble this Context Product
from the credit data estate. Every figure below was measured against the live
estate on 2026-09-12 before this document was written, and the query that
produced it is reproducible.

### 0.1 The governing question

Ruled by Dave at Gate 1, and it is what the rung exists to answer:

> **Can the Context Product distinguish market-wide movement, issuer-specific
> deterioration, and internal credit assessment, preserve their different
> clocks, and identify when they disagree?**

Rung 9 proved that one `as_of` can govern four *kinds* of time without
flattening them. This rung is the next question: three signals that are all
"credit quality", moving at different rates, where **the interesting fact is
the divergence** and any average destroys it.

### 0.2 Placeholder discipline

No `[TBC]` except the p95 budgets, which cannot exist before code does and
close at Gate 2. Where a value is a demonstration choice rather than a
production recommendation, §0.4 names it.

### 0.3 Reads only — no write path anywhere in this product

Both source stores are read. The ledger is append-only, so a write is
permanent; nothing in this product's assembly, its examples or its tests writes
to either (CLAUDE.md §9 — the curated estate is evidence).

### 0.4 What is real, what is engineered, and two things this product does NOT consume

**THIS PRODUCT CONSUMES NO AGENCY RATINGS AND NO TRACE DATA.** Both statements
are load-bearing and both were verified rather than assumed:

- **No agency ratings.** S&P, Moody's and Fitch ratings are licensed and not
  redistributable. Measured: no agency column exists in any of the estate's 118
  tables, and the internal scale is `synthetic — internal`. An SDK example
  ships with the SDK and is copied by adopters, so committing licensed values
  into one is redistribution exactly as it would be in a product. The three
  legal legs the vault names are what this product uses, minus the one the
  estate does not hold.
- **No TRACE.** The vault's §C assumes FINRA TRACE for the spread leg.
  **Measured: the estate holds none.** Instrument identifiers are `syn-i-*` and
  the spread is *decomposed*, not observed. This specification does not call
  the spread leg TRACE, and the payload does not either.

| Element | Provenance |
|---|---|
| Treasury benchmark yield | **public** — Treasury.gov / FRED |
| Market OAS by rating band | **public** — ICE BofA option-adjusted spread series on FRED (`BAMLH0A1HYBB` and four siblings) |
| **Issuer-specific (idiosyncratic) spread** | **synthetic — engineered** — the residual after the two public components; the primary signal of this product |
| Instrument reference — coupon, maturity, seniority, band | **synthetic — engineered** |
| Internal risk-grade history | **synthetic — internal** — bitemporal, with off-cycle reviews |
| Internal rating scale and notch mapping | **synthetic — internal** |

**Illustrative calibration.** This example runs against a point-in-time
demonstration estate rather than continuously refreshed production data.
Freshness half-lives and related thresholds are calibrated to make the governed
behavior observable in that snapshot. They demonstrate how the SDK applies
these controls and should not be interpreted as recommended production
coverage-policy thresholds.

### 0.5 The four-question test

- **Is the answer assembled rather than stored?** Yes. No store holds *"the
  issuer-specific spread move, net of the market, against the grade that was in
  force at the time."* It is a decomposition in one store cut against a
  bitemporal history in another.
- **Does more than one consumer need it?** Yes — the portfolio manager
  screening for deterioration, the credit officer preparing a rerating, and the
  control function asking why a grade did not move when the market did.
- **Does it carry a governed freshness claim?** Yes, and a **ninety-fold
  asymmetry**: the spread legs move daily and the internal grade quarterly. A
  single product-level freshness figure over both would be actively misleading,
  which is why each series carries its own.
- **Would a `SELECT` do?** No, and this rung is where that becomes measurable
  rather than arguable. §C.4 records **two** naive aggregations that were
  actually run during Gate 1 and each returned a confidently wrong answer.

---

## A · Decision frame

**The decision.** A portfolio manager reviewing deterioration across a book, or
a credit officer preparing a rerating and needing the trajectory rather than
the point.

**The trigger.** A screen, or a name that has started to look different.

**Consuming principals.** A single role at this tier.

### A.1 Counterfactual — `temporally-incoherent`, by aggregation

Internal grades are reviewed quarterly. Spreads move daily. A product
presenting both as "current credit quality" implies they carry equal currency,
when a grade set eleven weeks ago and a spread observed this morning describe
different moments.

**Worse, the signal IS the divergence.** A spread that widened while the grade
did not move is the early warning. Averaging the two into one quality score
destroys exactly the information the product exists to surface.

And there is a second aggregation that destroys it just as thoroughly:
collapsing a *time series* into its endpoints. §C.4 records both, because both
were run here.

### A.2 The worked case — Celanese Corp, `549300FHJQTDPPN41627`

Measured. The market moved first; the credit file followed 95 days later, and
said so in its own words.

| when | what | source |
|---|---|---|
| **2024-12-12** | issuer-specific spread peaks at **131.1 bp** — **4.5×** this issuer's own 29.4 bp median, with the market component already netted out | `spread_observation` |
| 2025-02-17 | quarterly review. Grade **unchanged at BB** | ledger |
| **2025-03-17** | grade moves **BB → BB-**, trigger: *"ad hoc credit review following sustained spread widening in the obligor's traded debt"* | ledger |
| 2025-03-21 | that assertion is **booked** — four days after it took effect | ledger `assertedAt` |

**The acceptance test, as a procedure that can fail:**

1. Serve the product for this obligor over the full window.
2. Assert the payload reports the peak idiosyncratic move **and** the grade in
   force on that date, and that the grade in force was **BB**.
3. Assert the next grade change is **later than the peak**, is a **downgrade**,
   and is **off-cycle**.
4. Assert the lag between them is reported as a figure rather than left for a
   reader to subtract.

A product that averaged the series, or that compared the peak to the *current*
grade instead of the grade **in force at the time**, fails step 2 or 3.

### A.3 The five cases where the market moved and the grade never did

The other half of the demonstration, and the larger half. Measured over the
same window, market component netted out, each against **that issuer's own**
median:

| obligor | peak idiosyncratic | multiple of own median | grade |
|---|---|---|---|
| `529900VKCYZW8GZ4WW58` | 162.9 bp | **4.2×** | never moved |
| `254900HM1ABRDJ7T5718` | 113.5 bp | **5.4×** | never moved |
| `5493004Q1NNH6JXCSI52` | 98.3 bp | **6.5×** | never moved |
| `5493004HBTOTE9DI9P12` | 82.7 bp | **4.5×** | never moved |
| `5493003QENHHS261UR94` | 68.0 bp | **2.9×** | never moved |

**These are not errors in the credit file and the product does not call them
errors.** It reports that two independent assessments of one obligor disagree,
by how much, and for how long. What to do about that is the credit officer's.

### A.4 Scope boundary

Held at §B.8.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Schema** | `rating_spread_migration` — entities `cmns-org:LegalEntity`, `fibo-fbc-fi-fi:DebtInstrument`, `fibo-sec-dbt-bnd:CorporateBond`, `fibo-fbc-dae-cr:OrganizationCreditRating`; relationships `fibo-fbc-dae-cr:concernsParty`, `ex:supersededBy`; measures — grade migration series, three-component spread series, divergence episodes. Machine-readable at `schemas/rating_spread_migration.v1.json` |
| **Freshness SLA** | **Per series, and the series do not share a clock** (§B.6). Market OAS and both spread components daily; internal grade quarterly with off-cycle reviews; scale mapping and thresholds versioned, not decaying |
| **TTL** | 4 hours · `ttl_anchor: from_decision`. Ceiling 1 day — the fastest series' own cadence. A request pinned to a past `as_of` is a forensic reconstruction and does not decay |
| **Policy Binding** | Entitlement scope · the rating scale and its notch mapping, versioned — a recalibration changes every notch-equivalent figure the product has ever produced, so `policy_bundle_versions` must record which mapping applied · divergence thresholds |
| **Lineage** | **`ProductLineage` exactly** — `operators_invoked`, `policy_bundle_versions`, `graph_snapshot_at`. Everything else lives on its own surface (§B.7) |
| **Semantic Version** | `v1.0.0` |
| **Discovery** | `credit-risk.rating-migration.v1` |
| **Addressability** | `/context-products/credit-risk/rating-migration/{lei}` |
| **Assembly Mode** | **1 — no model in the trust path.** Resampling, differencing and threshold comparison. A generative stage could reconcile a disagreement the substrate deliberately surfaced, which is the one thing this product must not do |

`extra=forbid` on every payload model, validated at the boundary.

### B.2 Classification, residency and cross-border serving

**Data classification: `internal`** — the highest of any §C element. The grade
history, the scale and the thresholds are internal; the benchmark and the
market OAS series are public.

**Information barrier.** None crosses this product. It reads no MNPI-bearing
source. **The licensing boundary is the analogous constraint here**, and it is
absolute rather than graded: no agency rating enters the payload, the
transcript, or the published page.

**Residency and cross-border.** Entity-level; the obligor's own jurisdiction
governs. No element is replicated across a border by this product.

**The suppression rule.** Where policy excludes an obligor the payload carries
**no count, marker or placeholder**.

### B.3 Model-risk annotation

**Not applicable — no model in the trust path.** Assembly Mode 1.

### B.4 Request parameter surface

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `lei` | string(20), required | `E` anchor | — |
| `intent` | enum, required | `P` — selects the scale mapping and threshold set | — |
| `as_of` | datetime, required | **`T` — the decision instant; the window's right edge** | — |
| `freshness` | string, required | `T` — the currency the caller requires | — |
| `window` | duration | `T` — how far back the series runs | `730d` |
| `granularity` | enum `daily` \| `weekly` \| `monthly` | `T` resolution | `weekly` |
| `series` | list `grade` \| `spread` \| `divergence` | `R` scope | all |
| `divergence_multiple` | decimal | `P` — the episode threshold, as a multiple of the obligor's own median | class default |
| `debt_tolerance` | decimal | `P` — debt gate | class default |
| `include_superseded_grades` | bool | payload shape | `true` |

### B.5 How the request maps onto the SDK

**The four §6.3 axes are `ProductRequest` FIELDS, not parameters** — they
establish which question was asked and are what the content address and the
replay record resolve against (`TLP`-equivalent gate `RSM-G19`):

| The caller supplies | Lands on |
|---|---|
| the `{lei}` path segment | **`ProductRequest.subject`** |
| `intent` | **`ProductRequest.intent`** |
| `as_of` | **`ProductRequest.asked_at`** |
| the freshness requirement | **`ProductRequest.freshness`** |
| `window`, `granularity`, `series`, `divergence_multiple`, `debt_tolerance`, `include_superseded_grades` | **`ProductRequest.parameters`** |

`debt_tolerance` and `divergence_multiple` are `Decimal`, never float: the
canonicalizer refuses floats as not bit-stable, and both ride the request's
content address.

### B.6 Three signals, three clocks — and the ninety-fold spread

| Signal | Cadence in this estate | Clock it is measured on | Can it refuse? |
|---|---|---|---|
| Market OAS by rating band | **daily**, 786 dates | observation date | yes — a mandatory input |
| Issuer-specific (idiosyncratic) spread | **daily**, 499 dates per instrument | observation date | yes — the primary signal |
| Internal grade | **quarterly**, ~8–9 per obligor over 24 months, plus off-cycle | **effective date**, with a separate booked date | no — a grade is in force or it is not |

**A single product-level freshness figure over these would be actively
misleading.** The contract therefore carries a window and a native cadence
**per series**, and `RSM-G14` fails if any series omits one.

**The grade's two dates are both carried and are not the same claim.**
`validFrom` is when the grade took effect; `assertedAt` is when it was booked.
Measured on the anchor: a **four-day** lag. This product **serves both and
reconstructs on `validFrom`** — rung 8 owns the question of reconstructing on
the booking axis, and duplicating it here would be two products answering one
question differently.

### B.7 Where the governance evidence lives

`ProductLineage` is `operators_invoked`, `policy_bundle_versions`,
`graph_snapshot_at`, and this product extends none of it. Per-series windows
and cadences are **payload** — they are the answer, not its provenance. `D_c`
is on the debt assessment; the content address on the governed product; the
plan and perspective in the replay record. `RSM-G21` asserts the payload
carries no second copy.

### B.8 Prerequisites, consumers and scope boundary

**Prerequisites:** `counterparty-reference-snapshot` (rung 1) for obligor
identity; `obligor-financial-spread` (rung 3) for the financial context a
rerating is argued from.

**Consumers, named individually:**

| Consumer | What it takes | Notified on |
|---|---|---|
| `credit-surveillance-early-warning` (rung 11) | the divergence episodes as a trigger | MAJOR; and on any scale recalibration |
| `credit-memo-context` (rung 14) | the migration trajectory and its citations | MAJOR |
| `large-exposure-rwa-concentration` (rung 21) | grade in force, for risk weighting | MAJOR |

**Scope boundary — the vault's frame, narrowed by measurement:** how credit
quality has moved, and how the market anticipated it.

- **No agency ratings and no TRACE** (§0.4). Not a deferral — a statement about
  what this product consumes.
- **No sparse-series handling.** The vault's §F asks for thinly-traded
  instruments with observation gaps. **Measured: coverage is 468–499 of 499
  dates per instrument.** The requirement is **removed from this rung** rather
  than simulated, on Dave's ruling: *"The estate cannot demonstrate it; do not
  simulate it just to satisfy the vault description."*
- **No rating-action events from 8-K.** The estate's grade history is internal;
  no public rating-action event is carried, and the product does not imply one.
- **No forecast.** The product reports what moved and when. It does not predict
  the next rating action.

---

## C · Data catalog

### C.1 Element table

| Element | System of record | Provenance | Classification | Capability | `G` | Ontology IRI |
|---|---|---|---|---|---|---|
| Obligor identity | PostgreSQL `ccf_v2.legal_entity` | vendor (GLEIF) | public | relational | `E` | `cmns-org:LegalEntity` |
| Debt instrument reference | PostgreSQL `ccf_v2.debt_instrument` | derived (engineered) | internal | relational | `E` | `fibo-fbc-fi-fi:DebtInstrument` |
| Treasury benchmark component | PostgreSQL `ccf_v2.spread_observation.benchmark_bp` | public-filing | public | relational | `E`, `T` | `fibo-ind-ir-ir:InterestRateBenchmark` |
| Market OAS by rating band | PostgreSQL `ccf_v2.market_oas_series` | public-filing (ICE BofA via FRED) | public | relational | `E`, `T` | `fibo-ind-ir-ir:ReferenceInterestRate` |
| **Issuer-specific spread** | PostgreSQL `ccf_v2.spread_observation.idiosyncratic_bp` | derived (engineered) | internal | relational | `E`, `T` | `ex:IdiosyncraticSpread` |
| Internal grade history | Fluree `fibo-v2` | internal-SOR (synthetic) | internal | **bitemporal-ledger** | `T`, `R` | `fibo-fbc-dae-cr:OrganizationCreditRating` |
| Grade supersession chain | Fluree `fibo-v2` | internal-SOR (synthetic) | internal | bitemporal-ledger | `T` | `ex:supersededBy` |
| Rating scale and notch mapping | PostgreSQL `ccf_v2.rating_scale` | internal-SOR (synthetic) | internal | relational | `P` | `ex:RatingScale` |

**`ex:IdiosyncraticSpread` and `ex:RatingScale` are deliberately unbound.** No
FIBO or Commons term covers "the residual after netting a public market series
out of a spread", and inventing a `spec.edmcouncil.org` IRI would make the
binding mirror disagree with FIBO. The debt and rating classes above are the
vault's Wave-8 mirror.

Deployment detail — host, port, credential — appears nowhere in this
specification or the example tree.

### C.2 The population, measured 2026-09-12

| | measured |
|---|---|
| Spread observations | **47,849** over **96 instruments** · 499 dates · **2024-08-19 → 2026-08-18**, exactly 24 months |
| Coverage per instrument | **468–499 of 499** dates — near-complete, no material gaps |
| Issuers with spreads | **48**, exactly **2 instruments each** |
| Market OAS series | **3,930** rows · 5 rating bands (`AA`, `A`, `BBB`, `BB`, `B`) · 786 dates · ICE BofA on FRED |
| Internal grades | **245** assertions over **30 obligors**, 8–9 each |
| Bitemporal fields | `validFrom` 245 · `validTo` 215 · `assertedAt` 245 · `supersededBy` **215** |
| Triggers | 210 quarterly review · 30 initial · **5 off-cycle**, each with a narrative cause |
| Obligors whose grade changed | **21 of 30** |
| **Rated ∩ spread-observed** | **30 of 30** — every rated obligor has spreads |
| Divergence episodes (peak ≥ 2× own median) | **6** — five with no grade move, one confirmed 95 days later |

### C.3 Correlation key, single-writer, identity authority

**Key.** `LEI` end to end: `legal_entity.lei` → `debt_instrument.lei` →
`spread_observation.instrument_id`; in the ledger the rated party carries
`ex:lei`. **Measured: all 30 rated obligors resolve and all 30 have spreads.**
No crosswalk is needed and none is synthesized.

**Identity authority.** GLEIF for the obligor; the internal credit system for
the grade. Different authorities, different freshness ceilings, not averaged.

**Single writer.** Nothing here writes. Both legs are read through L2 into the
per-run fabric graph.

### C.4 The data traps

**Two of these were not found by inspection. They were found by running a naive
analysis and getting a confidently wrong answer — twice, during Gate 1
measurement of this very specification.** Both are recorded because they are
the product's own counterfactual, committed by its own author.

- **TRAP 1 — endpoint aggregation reports ZERO divergence.** The first
  measurement compared each obligor's mean idiosyncratic spread over the first
  20 days against the last 20 days, and looked for cases where the spread
  widened while the grade held. It found **none**. The episodes are *transient*:
  `529900VKCYZW8GZ4WW58` peaks at 162.9 bp against a 38.7 bp median and returns
  to 38.0 bp by the window's end, so its endpoint delta is **−4.3 bp**. A
  start-versus-end comparison does not merely understate the signal, it
  **inverts** it. **Binding:** episodes are detected against the obligor's own
  median over the window, never against its endpoints. **Cost:** a threshold
  that is per-obligor rather than absolute, which is the right shape anyway —
  a 100 bp move means different things at AA and at B.
- **TRAP 2 — temporal proximity is not confirmation.** The second measurement
  asked whether a grade changed within 45 days of the spread peak and found
  **6 of 6** — apparently every episode confirmed. But quarterly reviews land
  every ~90 days, so *some* review is near *any* date; the test was detecting
  the existence of a review, not a change. Checking **direction and ordering**
  showed **none** of the six moved within 45 days, and exactly **one** — the
  anchor — moved at all, 95 days later and off-cycle. **Binding:** a
  confirmation requires a grade change that is **after** the peak, is a
  **downgrade**, and is **off-cycle**; all three are asserted separately.
  **Cost:** the confirmation count drops from six to one, which is the true
  figure.
- **TRAP 3 — the spread is not observed, it is decomposed.** There is no TRACE
  in this estate. `spread_bp = market_oas_bp + idiosyncratic_bp`, and
  `yield_bp = benchmark_bp + spread_bp`. **Binding:** the payload serves the
  three components separately and labels the issuer-specific one as
  `synthetic — engineered`. **Cost:** the product cannot claim an observed
  market price, and does not.
- **TRAP 4 — the rating band is an instrument attribute, not a time series.**
  `debt_instrument.rating_band` selects which market OAS series applies and is
  **static**. An obligor whose grade migrates does not migrate bands in the
  market leg. **Binding:** stated in the payload, so a reader knows the market
  component is the band the instrument was issued into. **Cost:** the market
  netting is approximate for an obligor that has moved several notches, and the
  product says so rather than implying precision it does not have.
- **TRAP 5 — the internal scale uses agency-style letters.** `AA+` through
  `B-`, 15 notches. These are **the internal scale**, `synthetic — internal`,
  and are not an agency's opinion. **Binding:** every grade in the payload
  carries its scale id and its provenance. **Cost:** none, but the labelling is
  not optional — a demo grade mistaken for a rating is the licensing boundary
  failing by presentation rather than by ingestion.

### C.5 What this data is

Restated beside the figures: public benchmark and public market OAS; engineered
issuer-specific spread; synthetic internal grade history. No agency rating and
no TRACE.

---

## D · Assembly recipe

### D.1 Client call

```
GET /context-products/credit-risk/rating-migration/549300FHJQTDPPN41627
      ?intent=portfolio-review
      &as_of=2026-08-18T00:00:00Z
      &window=730d&granularity=weekly&series=grade,spread,divergence
```

As a `ProductRequest`, so the §B.5 mapping is concrete:

```
ProductRequest(
    schema_name="credit-risk.rating-migration.v1",
    schema_version="1.0.0",
    subject="549300FHJQTDPPN41627",
    intent="portfolio-review",
    asked_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
    freshness="daily",
    parameters={
        "window": "P730D",
        "granularity": "weekly",
        "series": ["grade", "spread", "divergence"],
        "divergence_multiple": Decimal("2"),
    },
)
```

### D.2 Operator step table

| # | Operator | Capability | Inputs | Emits | Failure behavior | p95 budget |
|---|---|---|---|---|---|---|
| 1 | `Resolve` | relational | `lei` | obligor, its instruments and their bands | `404` on unknown obligor | `[TBC — ccf_code, phase P6]` |
| 2 | `Policy` | relational | `intent` | scale mapping, notch table, divergence thresholds; emits `policy_bundle_versions` | `503` if unresolvable | `[TBC — ccf_code, phase P6]` |
| 3 | `Traversal` | bitemporal-ledger | obligor URI, window, `as_of` | the full grade assertion history with both dates and the supersession chain | `503` if the ledger is unreachable | `[TBC — ccf_code, phase P6]` |
| 4 | `Enrich` | relational | instrument set, window | the three spread components per instrument per date | `503` naming the absent source class | `[TBC — ccf_code, phase P6]` |
| 5 | `Evaluate` | in-memory | everything above | resampled series, divergence episodes, notch-equivalent figures | — | `[TBC — ccf_code, phase P6]` |
| 6 | `Projection` | in-memory | evaluated series | the principal's view | — | `[TBC — ccf_code, phase P6]` |
| 7 | — | in-memory | all of the above | contract assembly, `payload_hash`, `D_c`, TTL | `409` on debt gate | `[TBC — ccf_code, phase P6]` |

**Policy runs before anything is measured** — the notch mapping is versioned,
and a recalibration changes every notch-equivalent figure this product has ever
produced. Which mapping applied must be in lineage, not inferred.

### D.3 The three-signal decomposition — this rung's mechanism

Every figure the product reports about "spread" is one of three, and they are
never added into one number for the reader:

```
yield_bp  =  benchmark_bp  +  market_oas_bp  +  idiosyncratic_bp
             └── public ──┘   └── public ──┘   └─ issuer-specific ─┘
                                                  THE PRIMARY SIGNAL
```

- **`benchmark_bp`** — the risk-free level. Moves for reasons that have nothing
  to do with this obligor.
- **`market_oas_bp`** — what the *whole rating band* is paying. A widening here
  is a market move, not a deterioration.
- **`idiosyncratic_bp`** — what is left. **This is the only component that is
  evidence about this obligor**, and it is what every divergence figure in this
  specification is computed on.

**Resample; do not interpolate across a grade change.** A grade is a step
function, and smoothing it invents intermediate states that never existed
(`RSM-G12`).

**An episode is measured against the obligor's own median**, not an absolute
threshold — TRAP 1's binding, and the right shape independently: 100 bp means
different things at `AA` and at `B`.

### D.4 The scenarios

**Scenario 1 — the confirmation.** `549300FHJQTDPPN41627`, full window. The
peak at 131.1 bp on 2024-12-12 with **BB** in force; the downgrade to **BB-** on
2025-03-17, off-cycle, 95 days later; the four-day booking lag. The product
reports the lag as a figure.

**Scenario 2 — a standing disagreement.** `529900VKCYZW8GZ4WW58`. Peak 162.9 bp,
**4.2× its own median**, grade **B** throughout and still **B** at the window's
end. Two assessments of one obligor that never reconciled.

**Scenario 3 — the market move that is not a deterioration.** Any obligor over
a period where `market_oas_bp` rises and `idiosyncratic_bp` does not. The
headline spread widens; the product reports **no episode**, because the
widening was not about this obligor. This is the scenario a naive product gets
wrong in the *opposite* direction from scenarios 1 and 2.

### D.5 Determinism and the emitted contract

**Determinism class: `deterministic`.** `payload_hash` is `sha256` over the
canonical bytes excluding `assembled_at`.

The payload carries: obligor identity; the grade series with `validFrom`,
`assertedAt`, trigger, scale id and supersession pointer per assertion; the
spread series as **three labelled components** with the band the market leg was
taken from; the divergence episodes with peak, date, multiple of own median,
grade in force at the peak, and — where one exists — the confirming change with
its lag in days; and **a per-series register carrying each series' native
cadence, its resampled cadence and its window**.

### D.6 Replay

1. Serve at a pinned `as_of`; record `payload_hash` and `policy_bundle_versions`.
2. Re-serve at the same `as_of`; confirm the hash is unchanged.
3. Re-serve at an `as_of` **before** the anchor's downgrade; confirm the grade
   in force is **BB** and the confirming change is **absent** — not merely
   flagged differently, absent.
4. Re-serve at the original instant; confirm the original hash returns.

If step 4 returns step 3's value, `as_of` is not reaching the plan.

### D.7 Validation gates

Six universal — empty-operator guard, lineage strict equality, TTL bounds, debt
gate, suppression silence, classification containment. Then the
product-specific set, tabulated at §G.1.

**Error mapping.** `404` unknown obligor · `403` not entitled, no detail ·
`400 not_supported_at_tier` for a declared-inert parameter · `409` debt gate ·
`503` a mandatory source class unavailable, named · `200` with notices
otherwise. An obligor with grades but no spreads is `200` with the spread
series `NOT_EVALUABLE` — not an error, and not a silent omission.

---

## E · Volatility, debt and materialization

### E.1 Half-life table

> **Illustrative calibration.** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

| Signal class | `λ_c` | `decay_basis` | Basis | Supersession event |
|---|---|---|---|---|
| Market OAS | **1 day** | `valid-from` | illustrative | next publication |
| Issuer-specific spread | **1 day** | `valid-from` | illustrative | next observation |
| Benchmark | **1 day** | `valid-from` | illustrative | next publication |
| Internal grade | **90 days** | `valid-from` | expert — the review cycle, measured at ~91 days between quarterly assertions | next assertion, on-cycle or off |
| Rating scale mapping | **no decay** | — | measured | recalibration |
| Divergence thresholds | **no decay** | — | measured | policy revision |

**`decay_basis: valid-from` on all four moving classes, and it is load-bearing
here** (`D-IMPL-331`, `D-IMPL-332`). Every one of these sources carries a real
observation or effective date, so decaying against ingestion time would report
a two-year-old spread observation as perfectly fresh. Rung 9 is where that
defect was found; this rung is the first authored after the fix and declares
the basis from the start.

**A ninety-fold spread between the fastest and slowest class inside one
product.** That is the point, not an awkwardness.

### E.2 Debt

`D_c = 1 − (F · C · S)`, multiplicative.

- **F — freshness.** Over the **participating** classes, each against its own
  λ_c and its own basis. A grade 80 days old is near its half-life; a spread
  observation from the same date is long dead. Averaging them into one
  freshness figure is the counterfactual at §A.1 arriving through the debt
  model, so it is normalized per class and folded, never pooled.
- **C — completeness.** Two live terms: spread coverage over the requested
  window (measured 468–499 of 499 dates), and whether the obligor is rated at
  all (30 of 30 here, so it contributes nothing and the payload says so).
- **S — semantic consistency.** Whether every instrument's band resolves to a
  market OAS series. A band with no series is a consistency failure, not a
  silent skip.

| Component | May be absent? | `D_c` contribution | Behavior when absent |
|---|---|---|---|
| Market OAS for a band | no | — | `503` — the market component cannot be netted out, so no figure is defensible |
| Issuer-specific spread | no | — | `503` — this is the primary signal |
| Internal grade history | yes | 0.20 | grade and divergence series `NOT_EVALUABLE`; the spread series still serves |
| Scale mapping | yes | 0.10 | notch-equivalent figures omitted; raw grades still serve |

### E.3 Materialization and TTL

**Posture: `split`.** History does not change once observed; only the leading
edge moves. The historical series is materializable; the trailing window is
derived on demand. The mechanical test: the fastest λ_c is one day, so a cache
window longer than that is wrong for the leading edge and harmless for the
settled past.

**Cache key:** tenant · schema version · plan id · `graph_snapshot_at` ·
`as_of` · `window` · `granularity` · `series` · `divergence_multiple` ·
principal binding · `debt_tolerance`.

**TTL** `expires_at = decision_instant + 4h`, ceiling 1 day. A pinned past
`as_of` is a forensic reconstruction and does not decay.

### E.4 What invalidates a served answer

- A new spread observation — **local**, invalidates the leading edge.
- A new grade assertion, on-cycle or off — **local**, and it may create or
  confirm an episode.
- A scale recalibration — **cascading**, to every notch-equivalent figure and
  to every downstream consumer named at §B.8.

Re-derivation is lazy.

---

## F · Source binding and readiness

### F.1 Readiness

| Element | Available today | Blocker |
|---|---|---|
| Obligor identity | **yes** — 30 of 30 resolve | — |
| Instrument reference | **yes** — 96, 2 per issuer | — |
| Benchmark and market OAS | **yes** — public, 5 bands, 786 dates | — |
| Issuer-specific spread | **yes** — 47,849 rows, 24 months | engineered; `CP10-F-01` |
| Internal grade history | **yes** — 245 assertions, bitemporal | — |
| Off-cycle reviews | **yes** — 5 | — |
| Divergence episodes | **yes** — 6 (5 standing, 1 confirmed) | — |
| **TRACE observations** | **no** | `CP10-F-01`; scope narrowed, not simulated |
| **Sparse / thinly-traded series** | **no** | `CP10-F-02`; requirement removed by ruling |
| **Agency ratings** | **deliberately not consumed** | `CP10-F-03` |

### F.2 Open `[TBC]` register

Seven p95 budgets, all owned by `ccf_code`, all closing at phase P6 — the same
seven §D.2 carries. **A budget is not guessed at Gate 1:** a plausible number
that survives review becomes a figure somebody plans against.

No `[TBC]` is owed by the vault or by `ccf_dataprep`.

### F.3 Recorded findings — no decision needed to build

| id | finding | status |
|---|---|---|
| `CP10-F-01` | **The estate holds no FINRA TRACE data.** The spread leg is a decomposition — public Treasury benchmark, public ICE BofA OAS by band, and an engineered issuer-specific residual. The vault's §C assumes TRACE; dataprep's own digest flagged coverage as unconfirmed. Confirmed absent. The product does not claim TRACE. | ESTATE-LIMITATION |
| `CP10-F-02` | **No thinly-traded instruments with observation gaps.** Coverage is 468–499 of 499 dates per instrument. The vault's §F requirement is removed from this rung by ruling rather than simulated. | ESTATE-LIMITATION |
| `CP10-F-03` | **No agency ratings anywhere in the estate**, verified across 118 tables. The licensing boundary is satisfied by construction, not by a filter. The internal scale's agency-style letters are labelled as internal at every site. | NOT-A-GAP |
| `CP10-F-04` | **The market leg's rating band is static per instrument.** An obligor that migrates several notches is still netted against its issue band, so the market netting is approximate for exactly the obligors the product is most interested in. Stated in the payload. | ESTATE-LIMITATION |
| `CP10-F-05` | **Two naive aggregations produced confidently wrong answers during Gate 1 measurement** — endpoint differencing reported zero divergence and inverted the sign; temporal proximity reported six confirmations where there is one. Both are recorded at §C.4 as the product's own counterfactual, committed by its own author. | NOT-A-GAP |

### F.4 Access path

Read-only credentials. PostgreSQL `ccf_v2`; Fluree `fibo-v2` over the SPARQL
query route. Environment-variable names in `backends.yaml`; nothing this
example runs writes to either store.

---

## G · Operate and govern

**Accountable owner — roles, never individuals.** Credit-risk product
engineering owns assembly; the credit policy function owns the scale, the notch
mapping and the divergence thresholds; market data operations owns the
benchmark and OAS feeds; the internal credit system owns the grade history.

**Lifecycle: `draft` at Gate 1 → `in-build` → `certified` at Gate 2.**

**Service objectives.** `[TBC — ccf_code, phase P6]` per §F.2.

**Degradation contract.** Mandatory: obligor resolution, market OAS for every
band in scope, issuer-specific spread. Non-mandatory: grade history, scale
mapping — each degrades to `NOT_EVALUABLE` with a debt contribution.

**Observability.** Per-operator latency; `D_c` by component; gate failures by
id; episode counts by obligor; the distribution of confirmation lags — that
last one is the evidence base that would move the 90-day grade λ_c from
`expert` to `measured`.

### G.1 Product gates

| id | asserts | detects |
|---|---|---|
| `RSM-G01` | a plan with zero operator steps never serves | empty-operator |
| `RSM-G02` | served lineage equals the plan's typed operator references; `ProductLineage` is three fields | lineage drift |
| `RSM-G03` | `expires_at` derives from the decision instant and respects the ceiling | TTL fabrication |
| `RSM-G04` | `D_c` above tolerance returns `409` with the debt block | ungated debt |
| `RSM-G05` | a withheld obligor leaves no count or marker | disclosure by marker |
| `RSM-G06` | payload classification is the highest contributing | classification leak |
| `RSM-G07` | the three spread components are served separately and never pre-summed | the aggregation at §A.1 |
| `RSM-G08` | every divergence figure is computed on `idiosyncratic_bp`, not on `spread_bp` | a market move reported as a deterioration |
| `RSM-G09` | an episode is detected against the obligor's own median, not an absolute threshold | TRAP 1 |
| `RSM-G10` | the anchor's peak reports the grade **in force on that date**, not the current grade | comparing a past move to a present grade |
| `RSM-G11` | a confirmation requires a change that is later, a downgrade, and off-cycle — all three asserted separately | TRAP 2 |
| `RSM-G12` | the grade series is resampled, never interpolated across a change | invented intermediate grades |
| `RSM-G13` | `validFrom` and `assertedAt` are both served and are distinguishable | collapsing the two clocks |
| `RSM-G14` | every series declares its native cadence, its resampled cadence and its window | one freshness over a ninety-fold spread |
| `RSM-G15` | each series decays against its own λ_c and `valid-from` basis | the `D-IMPL-331` defect, reintroduced |
| `RSM-G16` | the supersession chain is served and every superseded grade points forward | a history served as a set |
| `RSM-G17` | an unknown obligor refuses distinctly from one with no spreads | request-error vs world-fact |
| `RSM-G18` | the payload labels the issuer-specific component `synthetic — engineered` and names no TRACE | `CP10-F-01` misrepresented |
| `RSM-G19` | the four axes are `ProductRequest` fields, absent from `parameters` | request identity demoted |
| `RSM-G20` | every grade carries its scale id and provenance; no agency name appears anywhere in the payload | the licensing boundary failing by presentation |
| `RSM-G21` | the payload carries no second copy of `D_c`, the content address or the policy versions | two copies of one figure |
| `RSM-G22` | a market-wide widening with flat idiosyncratic spread produces **no** episode | scenario 3 |

Every gate is made to fail deliberately at least once before Gate 2, and each
sabotage is recorded with its state — `passed`, `unavailable` or
`not-required` — on the vocabulary ruled at rung 9.

### G.2 Acceptance criteria

1. The anchor's peak is reported with the grade in force on that date, and that
   grade is `BB`.
2. The confirming change is later, a downgrade, and off-cycle — each asserted
   separately, and the lag reported as a figure.
3. The five standing-disagreement obligors each report an episode with no
   confirming change.
4. A market-wide widening with flat idiosyncratic spread produces no episode.
5. Every series in the payload declares its native cadence and its window.
6. `validFrom` and `assertedAt` are both present and differ for at least one
   assertion.
7. No agency name and no reference to TRACE appears anywhere in the payload.
8. Replay at a pinned `as_of` reproduces `payload_hash` exactly, and an earlier
   `as_of` omits the confirming change entirely.
9. All 22 gates execute, each with a docstring naming its id, and each has been
   observed failing or recorded as `unavailable` with the upstream guard named.

**Open decisions blocking build: none.**

### G.3 What this rung proves, and what it does not

**Proves, and nothing below it did:** that one product can carry three
assessments of the same obligor moving at a ninety-fold difference in cadence,
keep them separate, net the market out of the one that is supposed to be about
the obligor, and report a disagreement as a first-class finding rather than
averaging it away. Rung 9 proved four *kinds* of time could coexist under one
`as_of`; this proves three *series* of genuinely different cadence can, and that
the product's most valuable output is the one an aggregate destroys.

**Does not prove:** anything about observed market prices (`CP10-F-01`), sparse
series (`CP10-F-02`), agency opinion (`CP10-F-03`), band migration in the market
leg (`CP10-F-04`), or forecasting the next rating action.
