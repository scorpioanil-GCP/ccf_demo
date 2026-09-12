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

### A.2 The worked case — Celanese Corp `549300FHJQTDPPN41627`, bond `syn-i-b23153`

**The unit is the BOND** (§D.3, amended at Gate 1 on 2026-09-12). A bond is what
trades; the obligor-level figure is a convenience, and §C.4 TRAP 6 records what
that convenience costs here.

Measured. The market moved first; the credit file followed 96 days later, and
said so in its own words.

| when | what | source |
|---|---|---|
| **2024-12-11** | on the **5-year** bond `syn-i-b23153`, the issuer-specific spread peaks at **233.2 bp** — **8.0×** that bond's own 29.0 bp median, with the market component already netted out | `spread_observation` |
| same day | the **25-year** bond `syn-i-f87e69` reaches **28.9 bp** — **1.3×** its own median. **No episode.** The concern is entirely at the short end | `spread_observation` |
| 2025-02-17 | quarterly review. Grade **unchanged at BB** | ledger |
| **2025-03-17** | grade moves **BB → BB-**, trigger: *"ad hoc credit review following sustained spread widening in the obligor's traded debt"* | ledger |
| 2025-03-21 | that assertion is **booked** — four days after it took effect | ledger `assertedAt` |

**This is the only episode in the estate whose grade change is both a downgrade
and off-cycle.** Measured across all 96 bonds: 15 episodes, 5 followed by some
grade change, and **exactly one** where that change is a downgrade *and*
off-cycle. The other four are on-cycle reviews, three of them upgrades — near
in time and opposite in meaning, which is TRAP 2 restated at bond level.

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

### A.3 The cases where the market moved and the grade never did

The other half of the demonstration, and the larger half. **Measured per bond**,
market component netted out, each against **that bond's own** median. Ten of the
fifteen episodes are followed by no grade change at all; the six largest:

| obligor | bond | tenor | peak idiosyncratic | multiple of **that bond's** median | grade |
|---|---|---|---|---|---|
| `5493004Q1NNH6JXCSI52` | `syn-i-991bbc` | 10y | 178.8 bp | **14.2×** | never moved |
| `254900HM1ABRDJ7T5718` | `syn-i-6e26db` | 7y | 201.7 bp | **9.4×** | never moved |
| `529900VKCYZW8GZ4WW58` | `syn-i-4d322a` | 25y | 282.6 bp | **7.0×** | never moved |
| `5493004HBTOTE9DI9P12` | `syn-i-5c7d89` | 2y | 83.8 bp | **5.0×** | never moved |
| `5493004HBTOTE9DI9P12` | `syn-i-b2c3fe` | 18y | 81.6 bp | **4.1×** | never moved |
| `5493003QENHHS261UR94` | `syn-i-b20157` | 10y | 72.5 bp | **2.6×** | no *downgrade* |

**Bond-level detection finds more, and finds it sharper.** The obligor-level
pass this table replaced reported six episodes at 2.9×–6.5×; the bond-level pass
reports fifteen at up to 14.2×. The obligor-level multiples were not wrong
arithmetic — they were the right arithmetic on the wrong unit.

**`5493004HBTOTE9DI9P12` appears twice, and that is information.** Both its
bonds — a 2-year and an 18-year — episode on the same day. A concern visible
across the whole curve is a different credit story from one confined to the
short end, and an obligor-level average cannot tell them apart.

**These are not errors in the credit file and the product does not call them
errors.** It reports that two independent assessments disagree, by how much, on
which bond, and for how long. What to do about that is the credit officer's.

### A.4 Scope boundary

Held at §B.8.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Schema** | `rating_spread_migration` — entities `cmns-org:LegalEntity`, `fibo-fbc-fi-fi:DebtInstrument`, `fibo-sec-dbt-bnd:CorporateBond`, `fibo-fbc-dae-cr:OrganizationCreditRating`; relationships `fibo-fbc-dae-cr:concernsParty`, `ex:supersededBy`; measures — grade migration series, three-component spread series, divergence episodes. Machine-readable at `schemas/rating_spread_migration.v1.json` |
| **Benchmark basis** | **`static_issue_band`** — the market component is the OAS of the band the instrument was ISSUED into, and that band does not migrate with the obligor's grade (§C.4 TRAP 4, `CP10-F-04`). Named in the payload on every spread figure |
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
  measurement compared each series' mean idiosyncratic spread over the first 20
  days against the last 20 days, and looked for cases where the spread widened
  while the grade held. It found **none**.

  The episodes are *transient*, and restated at the corrected unit (TRAP 6) the
  inversion is starker still:

  | bond | start | end | **endpoint Δ** | median | peak | multiple |
  |---|---|---|---|---|---|---|
  | `syn-i-4d322a` | 42.1 | 40.8 | **−1.2 bp** | 40.3 | 282.6 | **7.0×** |
  | `syn-i-b23153` | 28.5 | 23.7 | **−4.9 bp** | 29.0 | 233.2 | **8.0×** |

  **The anchor's own bond — the product's headline case — looks like a 4.9 bp
  IMPROVEMENT under endpoint differencing**, while it in fact reached eight
  times its normal level and drew an off-cycle downgrade. A start-versus-end
  comparison does not merely understate the signal, it **inverts the sign**.

  **Binding:** episodes are detected against the series' own **median** over the
  window, never against its endpoints. **Cost:** a threshold that is per-series
  rather than absolute, which is the right shape anyway — a 100 bp move means
  different things at `AA` and at `B`.
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
- **TRAP 6 — cross-instrument averaging hides and inverts credit signals, exactly
  as time averaging does.** Found at Gate 2 build, against the Gate-1 spec's own
  headline number, and the amendment is `D-GATE-cp-10` Gate 1 reopened on
  2026-09-12.

  **The measurement.** Celanese has two bonds whose idiosyncratic spreads are
  normally indistinguishable — medians **29.0** and **29.5 bp**. On 2024-12-11
  they read **233.2** and **28.9 bp**:

  | bond | tenor | matures | median | peak | multiple |
  |---|---|---|---|---|---|
  | `syn-i-b23153` | 5y | 2031-08-04 | 29.0 bp | **233.2 bp** | **8.0×** — an episode |
  | `syn-i-f87e69` | 25y | 2050-12-17 | 29.5 bp | 37.4 bp | 1.3× — **no episode** |

  Averaging them gives 131.1 bp against a blended 29.4 bp median — **4.5×**. So
  the average **halves the peak, halves the multiple, and erases the fact that
  the concern is entirely at the short end.** A term-structure signal becomes a
  smaller undifferentiated one.

  **Not a Celanese quirk.** Measured across the estate: **5,267 (obligor, date)
  pairs** where one bond's idiosyncratic spread is more than twice the other's;
  the worst obligor reaches **231.6×** at its widest and averages **5.3×** every
  day; one obligor carries a negative residual on one leg while the other is
  positive, so their average describes a bond that does not exist.

  **Binding:** the **instrument is the primary observation unit** for spread and
  for episode detection. **Instruments are never averaged before detection**
  (`RSM-G09`, `RSM-G24`). An obligor-level spread figure is a **derived summary**
  and is served only with its dispersion beside it.

  **Cost:** more episodes to report — fifteen rather than six — and a payload
  that is a series per bond rather than one per obligor. That is the shape of
  the evidence.

  **Why it is recorded as a trap and not a correction.** The Gate-1 spec was
  internally consistent and implementable exactly as written; building it would
  have reproduced 131.1 bp faithfully. The number was not wrong, it was **the
  right arithmetic on the wrong unit** — and it is the product's own thesis,
  committed by its own author, for the third time in this document.

- **TRAP 3 — the spread is not observed, it is decomposed.** There is no TRACE
  in this estate. `spread_bp = market_oas_bp + idiosyncratic_bp`, and
  `yield_bp = benchmark_bp + spread_bp`. **Binding:** the payload serves the
  three components separately and labels the issuer-specific one as
  `synthetic — engineered`. **Cost:** the product cannot claim an observed
  market price, and does not.
- **TRAP 4 — the benchmark basis is `static_issue_band`, and it does not
  migrate with the obligor.** `debt_instrument.rating_band` selects which market
  OAS series is netted out, and it is **fixed at issue**. An obligor whose grade
  migrates keeps being netted against the band it was issued into.

  **Measured, so the imprecision is bounded rather than hand-waved:** at the
  window's start all 30 rated obligors sat in their issue band; by its end
  **2 of 30 had migrated out of it** — `5493004HBTOTE9DI9P12` (`BBB` at issue,
  `BB+` now) and `549300EQD0ZXRSMG3549` (`B` at issue, `BB-` now, an upgrade).

  **And the direction of the error is knowable, which matters more than its
  size.** The first of those two is also one of §A.3's divergence cases. It is
  netted against the `BBB` series while its grade says `BB+`, and the `BB` band
  trades far wider than `BBB` — measured over the §D.4 event window, `BB` ran
  156 → 306 bp against `BBB` at 98 → 149 bp. Netting a `BB+` obligor against
  `BBB` therefore **understates the market component and overstates the
  residual**: the very obligors this product is most interested in are the ones
  whose `idiosyncratic_bp` is least trustworthy, and it is biased *toward*
  reporting deterioration.

  **Binding, in four parts** (Dave, 2026-09-12):
  1. the basis is **named** in the contract and on every spread figure as
     `static_issue_band`;
  2. the payload **states** that `idiosyncratic_bp` loses precision as issuer
     quality migrates away from the issue band, and flags the obligors for which
     it has;
  3. the product **does not infer a new band from the internal grade** — that
     would substitute one assessment for another and quietly make the market leg
     a function of the very grade the divergence is measured against;
  4. the residual is **never presented as unqualified "pure issuer
     deterioration"** (`RSM-G23`).

  **Cost:** the product's headline signal carries a qualifier it cannot remove
  with this estate. That is the honest position, and naming it is cheaper than a
  precision it does not have.
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

**THE INSTRUMENT IS THE PRIMARY OBSERVATION UNIT.** A bond is what trades and
what carries a spread; an obligor-level spread is an average over instruments
that may be pricing different things. **Episodes are detected per bond, against
that bond's own median**, and **instruments are never averaged before
detection** (§C.4 TRAP 6, `RSM-G09`, `RSM-G24`).

**An obligor-level spread figure is a DERIVED SUMMARY, and never travels
alone.** Where an obligor has more than one instrument the payload carries the
summary **with its dispersion** — at minimum the per-bond values it was computed
from — so a reader can see whether it describes a bond or no bond. Measured:
5,267 (obligor, date) pairs in this estate have one bond more than twice the
other.

**The grade comparison stays at obligor level, and that asymmetry is
deliberate.** The internal grade is an assessment of the *obligor*; the spread
is a price on a *bond*. The product compares bond-market signals against
obligor-level internal credit assessment, and does not invent a per-bond grade
to make the two units match.

**The median is per bond**, not absolute — TRAP 1's binding at the corrected
unit, and the right shape independently: 100 bp means different things at `AA`
and at `B`, and different things on a 2-year and a 25-year.

**The market leg is netted on `static_issue_band`, and the product says so
rather than correcting for it.** The band is the instrument's at issue and does
not follow the obligor's grade (`CP10-F-04`). **The product must not infer a
band from the internal grade to improve the netting**: that would make the
market component a function of the grade, and the whole subject of this rung is
whether the market and the grade agree. A residual computed from a grade-derived
band could not disagree with the grade. So `idiosyncratic_bp` is served as **the
residual on a stated basis**, qualified where the obligor has migrated out of
its issue band, and never as unqualified "pure issuer deterioration"
(`RSM-G23`).

### D.4 The scenarios

**Scenario 1 — the confirmation.** `549300FHJQTDPPN41627`, bond
**`syn-i-b23153`** (5y), full window. Peak **233.2 bp** on 2024-12-11 —
**8.0×** that bond's own median — with the obligor's grade **BB** in force; the
downgrade to **BB-** on 2025-03-17, **off-cycle**, **96 days** later; the
four-day booking lag. The product reports the lag as a figure.

**The sibling bond is part of the scenario, not a footnote.** `syn-i-f87e69`
(25y) reaches 1.3× its own median on the same day and produces **no episode**.
The two bonds' medians are 29.0 and 29.5 bp — normally indistinguishable — so
the divergence is the signal and the average is what hides it (§C.4 TRAP 6).

**Scenario 2 — a standing disagreement.** `529900VKCYZW8GZ4WW58` (Sabre Corp),
bond **`syn-i-4d322a`** (25y). Peak **282.6 bp**, **7.0× that bond's own
median**, on 2026-01-23; grade **B** throughout and still **B** at the window's
end. Two assessments that never reconciled.

**Scenario 3 — the market move that is not a deterioration. `549300TRW1LZMDJZAQ78`
(B&G Foods, Inc.), `2025-02-18 → 2025-04-07`.** Measured, not asserted:

| | measured |
|---|---|
| the event | **every band widens together** — `B` +165.0 bp, `BB` +150.5, `BBB` +51.2, `A` +36.0, `AA` +28.9. A market-wide risk-off move |
| this obligor's **headline** spread | **+166.6 bp** |
| this obligor's **issuer-specific** spread | **+1.5 bp** — range 33.3–46.1 bp across the whole window |
| this obligor's grade | **`B` throughout**, including a quarterly review on 2025-02-17, inside the run-up |

**All three signals agree that nothing happened to this obligor**, and a product
reading the headline reports a 167 bp deterioration. The product reports **no
episode** and says why: the widening belonged to the band.

This is the scenario a naive product gets wrong in the *opposite* direction from
scenarios 1 and 2 — and it is the more common error, because 22 of the 30 rated
obligors show the same pattern over this window.

### D.5 Determinism and the emitted contract

**Determinism class: `deterministic`.** `payload_hash` is `sha256` over the
canonical bytes excluding `assembled_at`.

The payload carries: obligor identity; the grade series with `validFrom`,
`assertedAt`, trigger, scale id and supersession pointer per assertion; the
spread series as **three labeled components** with the band the market leg was
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

| Signal class | `λ_c` | `decay_basis` | `freshness_over` | Series | Basis | Supersession event |
|---|---|---|---|---|---|---|
| Market OAS | **1 day** | `valid-from` | `leading-edge` | the **bond** | illustrative | next publication |
| Issuer-specific spread | **1 day** | `valid-from` | `leading-edge` | the **bond** | illustrative | next observation |
| Benchmark | **1 day** | `valid-from` | `leading-edge` | the **bond** | illustrative | next publication |
| Internal grade | **90 days** | `valid-from` | `leading-edge` | the **obligor** | expert — the review cycle, measured at ~91 days between quarterly assertions | next assertion, on-cycle or off |
| Rating scale mapping | **no decay** | — | `series-mean` | — | measured | recalibration |
| Divergence thresholds | **no decay** | — | `series-mean` | — | measured | policy revision |

**`decay_basis: valid-from` on all four moving classes, and it is load-bearing
here** (`D-IMPL-331`, `D-IMPL-332`). Every one of these sources carries a real
observation or effective date, so decaying against ingestion time would report
a two-year-old spread observation as perfectly fresh. Rung 9 is where that
defect was found; this rung is the first authored after the fix and declares
the basis from the start.

**A ninety-fold spread between the fastest and slowest class inside one
product.** That is the point, not an awkwardness.

#### E.1.1 `freshness_over: leading-edge` — CORRECTION, 2026-09-12 (`D-IMPL-333`)

**§E.1 and §E.2 were reopened for this and nothing else** (Dave, 2026-09-12).
The rest of the specification stands as amended at Gate 1.

**What the approved spec got wrong.** It declared the two half-lives and their
bases and said nothing about *which observations* constitute the thing being
aged. The SDK's reference scorer answered that question by default: it took the
**mean** freshness over every observation in the view. This product's view is
years of daily quotes by construction — that history is how a migration is
detected at all — so the default drove `F` to approximately zero and `D_c` to
`fail_closed` on a serve whose newest quote was two days old.

**Measured on the anchor, `549300FHJQTDPPN41627` at `as_of` 2026-08-20:**

```
observations in the view   rsm_spread 996 · rsm_grade 9 · rsm_instrument 2 · rsm_obligor 1
observations entering F    rsm_spread   2 · rsm_grade 1 · rsm_instrument 2 · rsm_obligor 1

  rsm_spread   syn-i-b23153   valid_from 2026-08-18   F = 0.250000
  rsm_spread   syn-i-f87e69   valid_from 2026-08-18   F = 0.250000
  rsm_grade    549300FHJQTDPPN41627  valid_from 2026-05-18   F = 0.484832
  rsm_instrument / rsm_obligor  (supersede-only)      F = 1.000000

F over the leading edge   0.664139      F over every observation   0.004750
D_c 0.3651, signal OK                   D_c 0.9955, fail_closed

C = 0.9559 measured, S = 1.0000 measured, in both columns. The right-hand
D_c is the same product of the same three terms with the same C and S — only
F differs — and it is derived here rather than served, because the left-hand
column is what the SDK now produces.
```

**The rule, in Dave's words:** *"Freshness applies to the leading edge of each
logical series as of the decision instant, not to its historical members."*

Concretely: `F` reads the **latest spread observation per bond at or before
`as_of`**, and the **grade in force at `as_of`**. Everything older is historical
evidence — it is what the episode detection at §D.3 runs on, and it is *better*
to have than not to have. A freshness term that counts it as staleness has
stopped measuring what the caller asked about.

**Four things this does NOT do.**

- **It is not wall-clock latest.** The edge is relative to the requested
  `as_of`. A request pinned to 2025-03-01 sees the series as it stood then, and
  a later quote is not yet knowable. §E.3's forensic-reconstruction reading is
  unchanged and now has a freshness term that agrees with it.
- **It does not shorten the series.** Every one of the 996 spread observations
  still reaches the projection. §D.3 detects episodes across the full history;
  only the debt term reduces.
- **It does not split the classes.** The obvious alternative — declare
  `rsm_spread_current` and `rsm_spread_history` so the scorer sees only the
  first — was refused (Dave: *"Do not split into artificial current/history
  classes unless the SDK forces us to"*). An entity class names the kind of
  thing observed; it must not encode this product's reading of its own data.
  The series key does the partitioning in the λ_c row, where it belongs.
- **It is not `supersede-only` under another name.** That was checked before
  the SDK was changed, because Dave required it: over nine observations one day
  apart, read at the newest, `supersede-only` gives `F` per observation
  `[1, 1, 1, 1, 1, 1, 1, 1, 1]`, mean `1.000000`. It means *this class does not
  decay* — every historical point still enters `F`, now each reading as
  perfectly fresh. Curve-mean understates freshness by counting history as
  stale; `supersede-only` overstates it by declaring history evergreen. Neither
  says *"the newest quote for this bond is two days old."*

**What the series key reaches.** `series_key_attribute` is read off the
**claim**, so `instrument_id` is promoted out of `payload_json` and onto the
spread node's attributes in `ccf_config.yaml`. Without that promotion the key
resolves to `None` and every bond's history collapses into a single series —
which reads as a working configuration and is not one.

### E.2 Debt

`D_c = 1 − (F · C · S)`, multiplicative.

- **F — freshness.** Over the **leading edge of each series** in each
  participating class, each against its own λ_c and its own basis
  (§E.1.1, `D-IMPL-333`). A grade 80 days old is near its half-life; a spread
  observation from the same date is long dead. Averaging them into one
  freshness figure is the counterfactual at §A.1 arriving through the debt
  model, so it is normalized per class and folded, never pooled. **And the
  members of one class are not pooled across time either** — a bond's series
  contributes the quote the answer rests on, not the average age of everything
  kept about it. Measured on the anchor: 996 spread observations in the view,
  **two** entering `F`, one per bond.
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
| `CP10-F-03` | **No agency ratings anywhere in the estate**, verified across 118 tables. The licensing boundary is satisfied by construction, not by a filter. The internal scale's agency-style letters are labeled as internal at every site. | NOT-A-GAP |
| `CP10-F-04` | **The benchmark basis is `static_issue_band`.** The market component is the OAS of the band the instrument was issued into, and it does not migrate with the obligor. Measured: all 30 rated obligors were in their issue band at the window's start; **2 of 30 had left it by the end**, one of them a §A.3 divergence case netted against `BBB` while graded `BB+`. Because `BB` trades far wider than `BBB` (156→306 vs 98→149 bp over the §D.4 window), the error is **directional**: the market component is understated and the residual overstated, precisely for the obligors the product cares most about. Four bindings at §C.4 TRAP 4; enforced by `RSM-G23`. **No band is inferred from the internal grade** — that would make the market leg a function of the grade the divergence is measured against. | ESTATE-LIMITATION |
| `CP10-F-06` | **Cross-instrument averaging halved the anchor's peak and its multiple, and erased a term-structure signal.** Found at Gate 2 build against the Gate-1 spec's own headline figure; **Gate 1 was reopened for this amendment alone** (Dave, 2026-09-12). The instrument is now the primary observation unit; obligor-level spread is a derived summary that never travels without its dispersion. Measured: 5,267 (obligor, date) pairs carry one bond at more than twice the other. | FIXED-gate-1-amendment |
| `CP10-F-07` | **Historical-series freshness cannot be computed across the full archive.** The original §E.1/§E.2 treatment averaged freshness across all historical observations, driving `F` from the intended current-state measure to an archive-length measure. On the anchor case, `F` moved from **0.004750** to **0.664139** after adopting leading-edge freshness by logical series. `supersede-only` was tested and rejected because it makes every historical observation fully fresh rather than selecting the current edge. Fixed by `D-IMPL-333`; §E.1/§E.2 reopened for the correction and nothing else (§E.1.1). | FIXED-gate-2 |
| `CP10-F-08` | **The confirmation test could not distinguish "not rated at the peak" from "rated and never moved".** Found running §D.4 scenario 2 at Gate 2: `_confirmation` returned `None` for both, so the product reported Sabre — rated `B` at the peak and still `B` through two later reviews — as though the obligor carried no grade. **Scenario 2 is precisely the second state**, so the product could not express the case its own specification declares. Now three outcomes: `changed` (with the three tests of `RSM-G11` reported separately), `unchanged` (with the grade in force and the count of later reviews that left it alone), and `not-evaluable`. An absence of evidence and a standing disagreement are different answers. | FIXED-gate-2 |
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
| `RSM-G09` | an episode is detected **per bond**, against **that bond's own** median, never against an absolute threshold and never on an inter-instrument average | TRAP 1 and TRAP 6 |
| `RSM-G10` | a bond's peak reports the **obligor's** grade in force on that date, not the current grade — the units are deliberately different (§D.3) | comparing a past move to a present grade |
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
| `RSM-G22` | a market-wide widening with flat idiosyncratic spread produces **no** episode — asserted on `549300TRW1LZMDJZAQ78` over `2025-02-18 → 2025-04-07`, where the headline moved +166.6 bp and the residual +1.5 bp | scenario 3 |
| `RSM-G24` | an obligor-level spread figure never travels without its dispersion; the per-bond values it summarizes are carried beside it | TRAP 6 — a summary read as an observation |
| `RSM-G23` | every spread figure names its basis as `static_issue_band`; an obligor whose grade has migrated out of its issue band is FLAGGED; the payload never calls the residual unqualified "pure issuer deterioration"; and no band is ever derived from the internal grade | `CP10-F-04` presented as precision it does not have |

Every gate is made to fail deliberately at least once before Gate 2, and each
sabotage is recorded with its state — `passed`, `unavailable` or
`not-required` — on the vocabulary ruled at rung 9.

### G.2 Acceptance criteria

1. The anchor bond `syn-i-b23153` reports a peak of 233.2 bp at **8.0×** its own
   median, with the obligor's grade in force on that date reported as `BB` —
   and the sibling bond `syn-i-f87e69` reports **no episode** on the same day.
2. The confirming change is later, a downgrade, and off-cycle — each asserted
   separately, and the lag reported as a figure.
3. Ten bond-level episodes are followed by no grade change, and the six largest
   are reported with their tenor. No episode is detected on an average of two
   instruments.
4. A market-wide widening with flat idiosyncratic spread produces no episode.
5. Every series in the payload declares its native cadence and its window.
6. `validFrom` and `assertedAt` are both present and differ for at least one
   assertion.
7. No agency name and no reference to TRACE appears anywhere in the payload.
8. Replay at a pinned `as_of` reproduces `payload_hash` exactly, and an earlier
   `as_of` omits the confirming change entirely.
9. Every spread figure names `static_issue_band`, the two migrated obligors are
   flagged, and no band is derived from a grade.
10. An obligor-level spread figure, wherever one is served, carries the per-bond
    values it was computed from.
11. All 24 gates execute, each with a docstring naming its id, and each has been
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
