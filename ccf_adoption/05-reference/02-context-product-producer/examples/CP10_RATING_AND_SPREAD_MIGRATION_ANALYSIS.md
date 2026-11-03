> **Current operations:** use [the refreshed implementation walkthrough](CP10_RATING_AND_SPREAD_MIGRATION.md) and Fluree **4.2.4** where required. The embedded specification remains historical evidence at its stated pin.

> **Reading copy:** [HTML edition](CP10_RATING_AND_SPREAD_MIGRATION_ANALYSIS.html), with rendered tables and sources included in this file.

# CP-10 — Rating & Spread Migration — Analysis

**Audience:** banking SME and Information Architect. **Purpose:** reconstruct the journey from the business problem to this example’s final specification.

**Final specification:** `examples/cp-10-rating-and-spread-migration/spec/CP-SPEC-010_Rating_And_Spread_Migration.md`, read directly from `drcastillo/ccf_code` at `37ac3055fd64ed64d78c6fd5555d79e451859153`. [Open the included final spec](#source-spec). Its recorded decisions, corrections, findings and placeholders are the destination of this walkthrough. The [Standard v0.3](#source-standard) supplies the template and the [generation recipe](#source-recipe) explains the ownership and evidence sequence.

The figures below are the final spec’s teaching-estate measurements or declared design values. They are not new runtime measurements. Once the design journey is understood, continue with the [implementation walkthrough](#source-implementation).

## Start with a disagreement the product must preserve

A portfolio manager sees a bond's spread widen while the bank's internal grade remains unchanged. The credit officer needs to know whether the move reflects the market, a particular instrument, a subsequent grade action or an unresolved disagreement. An averaged trajectory that makes those signals agree defeats the question.

The final spec's corrected unit is **the bond**, not the obligor's average. For Celanese (`549300FHJQTDPPN41627`), the five-year bond `syn-i-b23153` peaks on **11 December 2024** at **233.2 bp** idiosyncratic spread, **8.0×** its own 29.0 bp median. The 25-year sibling `syn-i-f87e69` is at 28.9 bp, only 1.3× its median, and does not episode. This is a short-end concern, not an interchangeable issuer-wide signal.

The grade in force is **BB**. The 17 February review leaves it unchanged. The downgrade to **BB−** on **17 March 2025** is off-cycle, **96 days after the peak**, and is booked four days later. The product must report that lag and qualify the confirmation: later than the peak, a downgrade and off-cycle. Proximity to any review does not suffice.

Across 96 measured bonds the final bond-level analysis finds **15 episodes**, ten followed by no grade change. Disagreement is information for the credit officer; it is not automatically an error in the credit file.

## Make the unit and clock explicit in the contract — Standard §0–§B → final §0–§B

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

The extra benchmark-basis row is material: `static_issue_band` names the band into which the instrument was issued. It does not migrate when the obligor's internal grade changes. Reconstructing a benchmark from that grade would make the two supposedly independent signals circular and could net away the disagreement being studied.

The contract is internal because internal grades, scales and thresholds govern the highest classification. Licensed agency ratings are outside the payload, transcript and published page. No TRACE observations are available in this engineered decomposition. The companion therefore explains the final synthetic teaching case without suggesting that it supplies licensed market or agency data.

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

The four identity axes map to `ProductRequest.subject`, `intent`, `asked_at` and `freshness`. Window defaults to 730 days; output granularity defaults to weekly. Choosing weekly output does not authorize detecting episodes on an obligor-level average.

**Read the table with the final correction:** its threshold description retains “obligor's own median,” while corrected §A.2–A.3 and the final acceptance criteria require **each bond's own median**. Those later, explicit unit corrections govern the walkthrough. Recording the inconsistency is more accurate than silently rewriting the quoted source table or reproducing the earlier six-episode result.

## Inspect the three clocks and their source limits — Standard §C → final §C

Market OAS is daily, the engineered idiosyncratic component is daily per instrument, and internal grades change on quarterly or off-cycle review. The grade is a step function: it remains in force until replaced. It must not decay as if a quarterly review were a missed daily observation.

The architect retains effective and assertion dates on grades, but this product reconstructs the grade in force using `validFrom`. It does not duplicate CP08's separate knowledge-time query. That boundary keeps a four-day booking lag visible without quietly changing the requested temporal model.

Several measurements force changes to an initially plausible design:

- Comparing only the first and last 20-day means misses intervening episodes and can report improvement for the Celanese case despite the 8× peak.
- Averaging the short and long bonds reduces a sharp 233.2-versus-28.9 bp contrast to a 131.1 bp midpoint, concealing where the concern sits on the curve.
- A review near a peak is not necessarily a confirming downgrade; direction, ordering and off-cycle status need separate evidence.
- The residual after subtracting a static issue-band market component is explicitly qualified. It is not a pure causal estimate of issuer deterioration.

These findings belong in Standard §C's fitness assessment. They explain why the final contract has a unit, basis and cadence for each figure rather than only a convenient timeseries schema.

## Build the recipe around aligned evidence, not reconciliation — Standard §D → final §D

The declared decomposition is **yield = benchmark + market OAS + idiosyncratic component**. The recipe retains the daily spread components, represents grade history as an in-force step function and detects divergence per bond against that bond's own history. An obligor grade can contextualize multiple bonds; it does not become a newly invented rating for each bond.

Projection may summarize an obligor only with dispersion and the underlying bond members retained. It must still be possible to distinguish a whole-curve event from a short-end event. The market-wide scenario provides a control: a widening market component with a flat idiosyncratic component must not be labelled an issuer-specific episode merely because total spread grew.

Replay moves the right edge of the requested window. Before the March downgrade, the later confirmation cannot appear. At the same pinned instant, source basis and policy versions, the content address must reproduce. Mode 1 keeps resampling, differencing and threshold comparison deterministic; a generative stage is unnecessary to the promised answer.

## Define quality at the correct edge of each series — Standard §E–§F → final §E–§F

Debt is **1 − F×C×S**. Freshness is assessed at the leading edge of each selected series under its declared validity basis, not by treating every historical quote in the window as stale evidence. The final correction gives the useful example: a 996-quote view may require two latest per-bond observations for freshness assessment while retaining all the historical rows for coverage and trajectory.

Completeness measures coverage of the requested history; the measured idiosyncratic series supply 468–499 observations against 499 possible, with grade coverage for all 30 obligors. Coherence respects each instrument's declared band and market series. Missing mandatory OAS or idiosyncratic input produces the specified 503 refusal. Missing optional grade evidence adds 0.2 and leaves grade/divergence unevaluable while spread can remain available. Missing mapping adds 0.1 and omits notch equivalents while retaining raw grades.

The design materializes history and derives the requested trailing window on demand. TTL is four hours from decision with a one-day ceiling; a pinned past reconstruction does not decay. The completed spec records no open build blocker. These are handoff decisions and source findings, not claims that this documentation run executed the SDK's runtime suite.

## Make the corrected unit an acceptance condition — Standard §G → final §G

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

The final eleven acceptance criteria require the corrected 233.2 bp/8× short-bond peak with grade BB, the non-episoding sibling, the three confirmation conditions and explicit lag, the ten episodes with no grade change, preserved cadence and dates, replay before confirmation, declared static issue-band basis and bond-preserving summaries. All 24 gates must execute; an unavailable case must name its upstream guard as specified. That closes the SME's question with a precise, testable account of disagreement rather than a smoothed story of deterioration.


## Included source snapshots

Exact retrieved source texts, with their original historical statuses and internal links retained as source text. Tables quoted within the walkthrough come directly from the final spec; Markdown pipe escaping is normalized for display.

<a id="source-spec"></a>

<details>
<summary>Final example specification — ccf_code@37ac3055</summary>

Path: `examples/cp-10-rating-and-spread-migration/spec/CP-SPEC-010_Rating_And_Spread_Migration.md`

``````text
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

``````

</details>

<a id="source-standard"></a>

<details>
<summary>Specification Standard v0.3 — ccf_code@37ac3055</summary>

Path: `public/reference/specifications/Context_Product_Specification_Standard_v0-3.md`

``````text
# Context Product Specification Standard

**v0.3** — authoring standard for CB/CIB Context Products

**Status:** draft for Data Engineering review · **Basis:** CCF Whitepaper
v1.1, Ch 6 §§6.2–6.5 and Ch 7 §§7.4–7.10 · **Supersedes:** v0.2
(seven-section skeleton retained; twelve additions listed at §16)

Table of contents (updates when the document opens)

---

## 0 · What this document is

This is the **format contract** for a Context Product specification — not a
specification of any one product. A spec written to this standard is complete
enough that a data engineer can identify the source systems, build the
assembly path, register the product, and operate it without a further design
conversation.

Five rules govern the whole document.

- **A Context Product is not a dataset.** It is a unit of meaning — typed,
  governed, and fit to act on — assembled at request time for one intent, one
  perspective, one moment and one policy envelope.
- **The contract is nine elements, not eight.** Schema, Freshness SLA, TTL,
  Policy Binding, Lineage, Semantic Version, Discovery, Addressability,
  Assembly Mode.
- **Assembly is a composition of named operators over capability classes.**
  A spec describing bespoke logic instead of an operator composition has
  moved cost from the platform to the product, which is the failure mode
  this architecture exists to prevent.
- **The wire format is part of the standard.** Every product returns the
  same response envelope (§10). A consumer that must special-case a
  product's response shape does not have a contract, it has an integration.
- **Every claim in a spec is falsifiable or it is decoration.** *(new in
  v0.3)* A counterfactual, a replay guarantee, a determinism class and a
  validation gate are each stated as a test someone can run and watch fail.
  A spec whose assertions cannot be disproved has documented an intention,
  not a design.

### 0.1 Do you need a Context Product? — the four-question test

Build one only if the answer to **all four** is yes. If any is no, build the
data product and move on; the fabric is expensive precisely because it
carries guarantees a data product does not.

| # | Question | If no |
| --- | --- | --- |
| 1 | Does the answer change with who is asking, beyond formatting? | Build a view |
| 2 | Does the answer have a validity window after which acting on it is wrong? | Build a table with a refresh schedule |
| 3 | Must the answer be reconstructible after the fact, with the policy and freshness state that produced it? | Build a report and archive the output |
| 4 | Is it composed at runtime from sources no schema author pre-joined? | Build the join |

A qualified yes is a legitimate answer, but it must be written down as one.
A product admitted on two clear yeses and two partials is admitted on a
stated basis that a reviewer can challenge.

### 0.2 Placeholder discipline (new in v0.3)

Every unresolved item carries an explicit marker — `[TBC]` — and every
marker appears again in §F with a named owner. **A spec with honest gaps is
buildable; a spec with invented system names is not.** Reviewers should
treat an unmarked assumption as the more serious defect, because a marked
gap gets closed and an invented one gets built.

### 0.3 Section skeleton

| § | Section | Answers | Primary audience |
| --- | --- | --- | --- |
| A | Decision frame | What decision, for whom, and what breaks without it | Product owner, business sponsor |
| B | Contract | The nine elements and the request parameter surface | Consuming agent teams |
| C | Data catalog | Every element, its system of record, and where it lands in G | Data engineering |
| D | Assembly recipe | The operator composition, step by step, with emits, budgets and gates | Data engineering |
| E | Volatility & materialization | Per-signal half-life, debt model, supersession, caching posture | Platform, FinOps |
| F | Source binding & readiness | What exists today, what does not, who owns the gap | Data engineering, source owners |
| G | Operate & govern | Owner, SLOs, degradation, observability, retention, lifecycle | Platform, second line |

The seven sections appear in order, always. A product with nothing to say in
a section writes one line explaining why, rather than omitting the heading —
an absent section reads as an oversight and a short one reads as a decision.

### 0.4 Front matter (new in v0.3)

Before §A, every spec carries: registry name · tier · Assembly Mode · cost
band · lifecycle state · accountable owner · last review date · a
two-sentence statement of what the product resolves · the four-question
build test result · build-order note.

**Capability gate.** Where a product cannot be built at all without a
capability the estate may not have, that fact is stated **above §A**, not
discovered in §C. This is a scheduling decision, not a build detail: a spec
whose blocking dependency is buried is a spec that gets scheduled and then
stalls.

---

## 1 · Section A — Decision frame

**Decision & trigger.** The decision, the role taking it, and the event that
triggers the request, in language a business sponsor recognizes. Where a
product serves several distinct triggers that ask genuinely different
questions, tabulate them and name which axis each exercises — the forensic
and the live case are not the same request wearing different parameters.

**Consuming principals.** Every role that will call the product, and whether
each receives **materially different assembled content** — not different
formatting. Different content means a projection plan (§13.2); different
formatting belongs to the consuming application.

**Counterfactual failure.** What a conventional data product returns for
this decision and why it is wrong. Name the failure mode from the closed
taxonomy: **context-starved · temporally-incoherent · perspective-flat ·
policy-blind · evidence-free**. If you cannot write a counterfactual a
skeptical engineer accepts, the product does not belong in the catalog yet.

**Counterfactual acceptance test** *(new in v0.3)*. The counterfactual is
written as an executable test, not a narrative. State the query, the two
answers, and the condition under which they must differ. Where they agree,
the product is not doing the work the counterfactual claims for it — and
this is exactly the check a reviewer should be able to run on the built
product rather than accept on assertion.

**Primitive taught** *(optional, catalog coherence)*. Where the product is
the clearest instance of one architectural primitive, name it — the catalog
is also a teaching sequence, and a product that teaches nothing new is a
candidate for merger with its neighbour.

**Contrast pointer** *(optional)*. Where a sibling product makes the
opposite design choice on the same axis, name it and the axis. Two products
with opposite `ttl_anchor` values teach the anchor better than either does
alone.

---

## 2 · Section B — Contract

### 2.1 The nine elements

| Element | What to write | Common error |
| --- | --- | --- |
| Schema | Named payload type; entities, relationships, attributes and measures, each bound to an ontology IRI. Link the machine-readable schema artifact. | Prose in a table cell with no artifact. Prose is not a contract. |
| Freshness SLA | Per signal class, not one value for the product. | One "intraday" over a payload mixing intraday and annual signals. |
| TTL | Duration plus ttl_anchor: from_decision or from_entity_freshness. Where the product carries a dual TTL, state both branches and the condition that selects them. | Anchoring by habit rather than by decision shape. |
| Policy Binding | Every regime and internal policy constraining construction, each with a resolvable version id; entitlement scope bound to the actual entitlement service; data classification and residency constraints (§2.2). Where policy must be pinned to a past date, say so here and enforce it in §D. | Asserting "entitlement scope" with nothing behind it. |
| Lineage | operators_invoked[] · graph_snapshot_at · policy_version · projection_plan_id · passage anchors where any claim rests on text · context_debt · payload_hash · model_record for Mode 2/3. | Omitting context_debt; it is an output of every assembly. |
| Semantic Version | vMAJOR.MINOR.PATCH, prior supported version, migration window, and the change class rules at §14. | A version with no stated migration window. |
| Discovery | domain.product.vN. | Registering before §G is complete. |
| Addressability | URL pattern with a resolvable anchor identifier. | Anchoring on an internal surrogate key. |
| Assembly Mode | 1 pure algorithmic · 2 algorithmic with LLM packaging · 3 algorithmic orchestration with agent-swarm assembly, with a one-sentence cost/quality/determinism rationale. Modes 2 and 3 additionally require the model-risk annotation at §2.3. | Omitted entirely. |

**Assembly Mode is a registration-time commitment.** The product owner settles
it, with a stated rationale, when the product class is registered. **It is not
something the assembling agent works out for itself, and it cannot vary between
calls.** Changing it is a MAJOR change (§14).

### 2.2 Classification and residency

State, inside Policy Binding:

| Field | Values |
| --- | --- |
| Data classification | public · internal · confidential · restricted — highest classification of any element in §C |
| Information barrier | none · control-room restricted · MNPI-bearing |
| Residency constraints | Jurisdictions whose data may not leave, and the effect on assembly |
| Cross-border serving | May this product be served to a principal outside the data's jurisdiction, and under what condition |

**The suppression rule.** Where policy excludes content, the payload must
carry **no count, marker, or placeholder** indicating that anything was
withheld. Restricted content is never materialized and filtered — a "3 items
hidden" marker is itself a disclosure, and on an information-barrier product
it is a reportable one.

### 2.3 Model-risk annotation — Mode 2 and Mode 3 only

An LLM in the delivery path is a model, and model governance applies.
Record:

- Model identifier and version, pinned; temperature pinned; prompt template
  versioned and logged
- Model-risk registration reference and validation status
- **The substrate/presentation boundary** — which fields are algorithmic
  artifact-of-record and which are model-rendered presentation
- **The smoothing control** — how the design prevents the model reconciling
  a conflict the substrate deliberately surfaced. A product whose substrate
  reports two sources disagreeing and whose narrative reads as settled has
  failed, and this is the failure mode Mode 2 is most prone to

Mode 1 products state "not applicable — no model in the trust path," which
is the reason to prefer Mode 1 wherever the decision does not need
narrative.

### 2.4 Request parameter surface

A table of every parameter with a **"Moves"** column naming which dimension
it moves: E anchor, R scope, T reconstruction, P envelope, Π perspective, or
a measure. A parameter that moves nothing is a formatting flag; push it to
the consumer.

Required on every product: an anchor identifier, `intent` (from the intent
registry, §13.1), and `debt_tolerance`.

**Declared-but-inert parameters** *(new in v0.3)*. Where a parameter is part
of the uniform surface but unsupported at this product's tier, declare it
and have it **fail explicitly** — `not_supported_at_tier`. It must never
silently succeed against current state. A parameter that appears to work and
does not is worse than an absent one: it will be relied on in a dispute.

### 2.5 Prerequisites, consumers and scope boundary

- **Prerequisites** — products this one composes over, by registry name.
  This is the build order.
- **Consumers** — products and applications that depend on this one.
  Required because §E supersession cascades need a reverse dependency list,
  and because a MAJOR version change needs a notification list.
- **Deliberately out of scope** — capabilities a reader will expect and not
  find, and which product carries them. Flag these to consumers as *coming
  next*, not as gaps.

---

## 3 · Section C — Data catalog

### 3.1 Element table

One row per data element:

| Column | Content | Rule |
| --- | --- | --- |
| Element | The fact or signal, in business language | One row per element, not per table |
| System of record | The authoritative source system | A named system; "internal" is not a system |
| Provenance class | internal-SOR · vendor · public-filing · derived · inherited | derived requires the derivation to appear in §D |
| Classification | public · internal · confidential · restricted | Drives §2.2 |
| Capability class | The store capability required (§11.1) | Never a product name |
| G dimension | E · R · T · P · Π · L · schema | Every element lands somewhere in the graph or it is not context |
| Ontology IRI | Bound class or property from the shared ontology contract | Unbound elements block registration |

### 3.2 Capability decomposition (new in v0.3)

Where a product depends on a capability the estate may not have, **decompose
the capability into its separable properties** and state what is deliverable
if each is absent. An estate rarely fails a capability wholesale; it
satisfies two of four properties and fails the rest, and that is the finding
worth having.

| Column | Content |
| --- | --- |
| Property | The separable sub-capability |
| Common estate answer | Widely available · sometimes · rare |
| If absent | Blocking · degrades to a named partial · workaround with a stated cost |

Where the decomposition yields a partial, name the **interim posture** —
which triggers are deliverable, what the unsupported parameter returns, and
what version string the partial ships under. Shipping a partial as though it
were complete is the failure this section exists to prevent.

### 3.3 Correlation key and single-writer discipline

Close with the **correlation key** — the identifier(s) every element joins
on, where the crosswalk lives, and its **measured coverage**. An unmeasured
crosswalk is a stated risk, not a footnote.

**Single-writer discipline.** One system is authoritative per element; no
element is written by two. Where an element exists today in two systems,
name the authority and make the other a read replica. This is a prerequisite
to build, not a follow-up.

**Identity authority hierarchy** *(new in v0.3)*. Where an anchor identifier
does not exist for every entity the product must serve, tabulate the entity
classes, the identity authority for each, the source of record-status for
each, and the **freshness ceiling each class implies**. An anchor that
silently excludes a population is inherited by every downstream product, and
the asymmetry belongs in the payload rather than averaged into a single
freshness claim.

---

## 4 · Section D — Assembly recipe

### 4.1 Client call

The literal request with parameters populated. Where the product has a
forensic and a live case, show the forensic one — it exercises more of the
surface.

### 4.2 Operator step table (expanded in v0.3)

Numbered, **one operator per step**, as a table:

| Column | Content |
| --- | --- |
| # | Step order |
| Operator | One name from the closed vocabulary (§11.2) |
| Capability class | From §11.1 — never a product name |
| Inputs | What the step consumes |
| Emits | What the step produces, named as it appears in lineage |
| Failure behavior | fail closed → HTTP code · degrade with debt · skip |
| p95 budget | Milliseconds, summing to a stated total against the tier envelope |

The final step is always contract assembly. **State the budget total and the
envelope it is measured against.** A total at 97% of the envelope is a
design finding, not a rounding detail — say which step dominates and what
the first optimisation would be.

### 4.3 Step detail

Below the table, prose for any step carrying a non-obvious discipline. This
is where an engineer learns *why* an ordering exists, and it is the part
that prevents a well-meaning optimisation from removing a load-bearing step.

Two disciplines recur and should be written out wherever they apply:

- **Policy that appears to do nothing still runs first.** At Tier 1 the
  step is an entitlement check; at Tier 5 the same step is what makes a
  restricted edge structurally absent. The ordering is learned from the
  first product or retrofitted painfully later.
- **Two filters on two axes are two filters.** Where a product reconstructs
  both what was true and what was known, both filters are separately
  parameterised and separately testable. Applying one silently answers a
  different question, and the silence is the defect.

### 4.4 Determinism class and payload hash

| Class | Meaning | Applies to |
| --- | --- | --- |
| deterministic | Same anchor + as_of + policy_version + graph snapshot → byte-identical payload | Mode 1 |
| substrate-deterministic | Algorithmic substrate byte-identical; presentation reproducible only under pinned model, temperature and prompt | Mode 2, Mode 3 |

Every product publishes a **payload hash** over the deterministic portion,
excluding `assembled_at`. **Replay asserts hash equality, not similarity.**

### 4.5 Replay statement and replay test

**Replay statement.** What exactly the replay engine re-executes to return
the identical product. "A similar product" is a defect recorded in §G, not a
caveat.

**Falsifiable replay test** *(new in v0.3)*. A numbered procedure a reviewer
can run against the built product, ending in an assertion that can fail. The
pattern: serve and record the snapshot · mutate the underlying state ·
re-derive live and confirm the new value · re-derive at the recorded
snapshot and confirm the **original** value returns. If the final step
returns the new value, the snapshot is not load-bearing and
`graph_snapshot_at` is decorative.

Where the product carries two time axes, add a second test asserting the
axes **disagree** under a case constructed to separate them. Agreement means
a filter was dropped.

### 4.6 Emitted contract

The response envelope of §10, populated with this product's payload schema,
**with types**. This is what the consuming agent team codes against and what
CI validates. Prose describing a payload is not a payload.

`extra=forbid` is enforced as a build-time CI invariant: a per-product
subclass cannot quietly introduce a field absent from the base declaration, and
a pull request carrying a drifted contract fails before it reaches a deployment
surface.

### 4.7 Validation gates

**Universal**, applying to every product without re-argument:

- **Empty-operator guard** — no operator returns an empty set silently;
  empty is fail-closed or an explicit debt contribution
- **Lineage strict equality** — operators_invoked equals the operators
  executed
- **TTL bounds** — expires_at consistent with the declared TTL and anchor;
  where the TTL is dual, the branch matches the condition
- **Debt gate** — assembly halts and returns the debt signal where D_c
  exceeds debt_tolerance
- **Suppression silence** — payload carries no marker of withheld content
  (§2.2)
- **Classification containment** — no element above the declared
  classification appears in the payload

Then **product-specific gates**, each a testable assertion naming the defect
it detects, cross-referenced to a fixture ID:

> "reconciliation guard — gross exposure must be ≥ guarantee-adjusted
> exposure; a violation means the dedup logic double-subtracted. → fixture
> EXP-G01"

---

## 5 · Section E — Volatility, debt & materialization

### 5.1 Half-life table

One row per signal class: λ_c · **calibration basis** · decay driver ·
supersession event · owner.

λ_c is **Control Plane configuration per observation type**, not a
per-document attribute; conflicts between two specs resolve centrally. The
table in a spec is an **initial calibration proposal**, and saying so is the
difference between a value an engineer can challenge and a number they
assume was measured.

**Calibration basis** is one of: **illustrative** (a starting assumption) ·
**expert** (business judgment, named function) · **measured** (observed
decision-reversal or restatement data). A catalog whose λ_c values are all
illustrative is not calibrated, and stating that plainly is more useful than
implying otherwise. Review cadence: annually, or on any
supersession-pattern change.

### 5.2 Debt model and per-component debt table (expanded in v0.3)

`D_c = 1 − (F · C · S)` — **multiplicative**, so a collapsed dimension
forces escalation rather than being averaged away. **Normalize F over
required signal classes, not over the classes actually present**, or losing
a source improves the freshness score.

Beyond the model, every spec carries a **per-component debt table**:

| Column | Content |
| --- | --- |
| Component | The input or claim |
| May be absent? | yes · no |
| D_c contribution | The weight |
| Behavior when absent | Fail closed · serve with flag · mark the affected claim NOT_EVALUABLE |

**Debt is decomposed per claim, never only per product.** A product with
four claims where one input is missing returns three evaluated claims and
one marked unusable — not a product-level failure, and never a
silently-omitted fourth. The gap is captured **before** the decision is
taken and shapes it directly: it is a decision input, not a log line.

### 5.3 Materialization posture

`materialized` · `derived-on-demand` · `split` (state which fields and
why). The test is mechanical: **if the fastest-moving input's λ_c is shorter
than the intended cache window, materialization is wrong.**

State the **cache key** explicitly — tenant, schema name, plan id, snapshot,
any time-axis parameters, and principal binding. A cache key missing a
parameter that changes the payload is a correctness defect that presents as
an intermittent one.

### 5.4 Supersession triggers

Each event marked **local** or **cascading**, and for cascading, the named
downstream products from §2.5. Invalidation cascades to every product whose
`operators_invoked` touched the superseded entity, not only those named for
it.

Re-derivation is **lazy** — invalidate for next request; do not
re-materialize eagerly, or a routine upstream publication becomes a
thundering-herd event across the catalog.

---

## 6 · Section F — Source binding & readiness

| Element | System of record | Interface & cadence | Available today | Gap owner | Blocker |
| --- | --- | --- | --- | --- | --- |

**Available today** is yes · partial (name the fields) · no. Every partial
or no carries a named gap owner and a stated blocker. Close with:

- **Access path** — existing feed, CDC, API, event stream, or new build
- **Identifier reality** — does the correlation key exist end to end; who
  owns the crosswalk; measured coverage
- **History depth** — how far back the source reconstructs, which bounds
  any as_of the contract advertises. Where the source publishes snapshots
  without history, **start retaining deltas now**; history not captured
  cannot be reconstructed later
- **Text-source boundary** — build-time extraction or runtime operator. A
  spec reaching into a document at runtime has changed capability class and
  cost band
- **First-build volumetrics** *(new in v0.3)* — the population the first
  build must contain for every gate and counterfactual to have something to
  act on. Where a required case does not occur naturally in the sample,
  **widen the sample until it does** rather than proceeding without it; a
  demonstrable primitive with no instance in the data reads to reviewers as
  machinery without a purpose

**No spec passes review with an unowned gap.** "Does not exist yet" is a
valid state; unattributed is not.

---

## 7 · Section G — Operate & govern

| Entry | Content |
| --- | --- |
| Accountable owner | Product owner, data steward, policy owner — roles, not individuals |
| Service objectives | p50 / p95 assembly latency, expected volume, concurrency ceiling, payload bound, absolute per-call cost estimate alongside the relative band |
| Degradation contract | Per input class: partial payload with elevated D_c, or fail closed. Mandatory classes named explicitly |
| Debt model | Which inputs drive F, C and S; debt_tolerance default and its basis (§5.2) |
| Observability | Per-operator latency · D_c distribution · gate-failure counts by gate · cache hit rate · entitlement denials · degradation-branch frequency · supersession-triggered invalidations. This is also the evidence base for moving λ_c and debt_tolerance from illustrative to measured |
| Retention & record of record | Which system is the record of record for each element; the fabric references it and does not replace it. Replay-record retention tier — full-fidelity, compressed, or tombstoned — and the severity rule that assigns it |
| Test fixtures | Named fixtures for the happy path, each gate, each degradation branch, and a replay hash assertion |
| Lifecycle | draft · in-build · certified · deprecated, with date and reviewer. Deprecation requires: consumer notification from §2.5, a sunset date at least one migration window out, and a named successor or an explicit statement that none exists |

### 7.1 Acceptance criteria (new in v0.3)

Every spec closes with a checklist of assertions **specific to this
product**, each independently verifiable, each phrased so it can fail. The
universal definition of done is at §15; §7.1 is what this product must
additionally prove. Close with the **open decisions blocking build**, named
by their §F row.

### 7.2 Catalog contribution (new in v0.3, optional)

Where the catalog is also a teaching sequence: what this product proves that
no earlier product proved, and what it deliberately does not prove. A
product that proves nothing new is a merge candidate; a product whose
exclusions are unstated invites a reviewer to read a tier boundary as an
oversight.

---

## 8 · Response envelope

Every product returns the same envelope. This is a wire contract, not a
style guide.

```json
{
  "product": "credit-risk.exposure-rollup",
  "semantic_version": "1.0.0",
  "payload": { },
  "contract": {
    "assembled_at": "...",
    "expires_at": "...",
    "ttl_anchor": "from_decision",
    "ttl_basis": "...",
    "assembly_mode": 1,
    "determinism_class": "deterministic",
    "freshness": [
      { "signal_class": "...", "observed_at": "...",
        "lambda_c_hours": 4, "relevance": 0.87 }
    ]
  },
  "lineage": {
    "operators_invoked": [ ],
    "graph_snapshot_at": "...",
    "policy_version": "...",
    "projection_plan_id": "...",
    "model_record": null,
    "payload_hash": "..."
  },
  "context_debt": {
    "F": 0.91, "C": 1.0, "S": 1.0, "D_c": 0.09,
    "contributions": [ ]
  },
  "notices": [
    { "type": "degraded-input", "signal_class": "...", "effect": "..." }
  ]
}
```

Rules:

- `payload` is never returned without `contract`, `lineage` and
  `context_debt`. A consumer that receives context with no debt signal
  cannot know what it is trusting.
- `notices` **is for degradation the consumer must see**, not for logging.
  Anything policy suppressed never appears here (§2.2).

---

## 9 · Error semantics

Every product returns one of these, and §D names which step raises which.

| Condition | Response | Notes |
| --- | --- | --- |
| Anchor unresolvable | 404 | Never an empty payload |
| Principal not entitled | 403, no detail on what exists | Existence is itself disclosure |
| Parameter unsupported at tier | 400 not_supported_at_tier | Never a silent success against current state |
| Debt gate exceeded | 409 with the debt block | Not a 200 with a warning |
| Mandatory input unavailable | 503 with the failed source class named | Silence is not a negative answer — an unretrieved screening source is not a clean screen |
| Non-mandatory input unavailable | 200 with notices and elevated D_c | The degradation contract in §G governs which inputs are which |

---

## 10 · Operators and capability classes

### 10.1 Capability classes

| Class | Capability required | Typical use |
| --- | --- | --- |
| relational | Set-based query over structured records at scale | Resolve, Enrich, reference lookup |
| bitemporal-ledger | Append-only state with valid-time and observed-time, queryable at a past point | Traversal mode temporal, supersession chains |
| graph-traversal | Multi-hop typed edge traversal with predicate filters | Ownership, guarantee, cross-default |
| document-passage | Document storage with passage-level addressing | Passage lineage, evidence chains |
| vector-index | Similarity retrieval over embeddings | Typology and pattern matching |
| federated-external | Contract-bounded request outside the institution's trust boundary | Cross-organizational products |
| in-memory | Deterministic computation over assembled state | Evaluate in all modes |

Estate binding lives in one artifact owned by the platform team. **Product
specs never name a database.**

### 10.2 Closed operator vocabulary

| Operator | Purpose | Reads | Emits | Cost driver |
| --- | --- | --- | --- | --- |
| Resolve | Anchor to canonical entity | relational | canonical entity, principal perspective | O(1) |
| Policy | Load the envelope in force; compute permitted sets | relational, bitemporal-ledger | policy_version, permitted party / document / action sets | O(1); gates everything downstream |
| Projection | Resolve and apply the Π plan | relational | projection_plan_id, projection shape | O(1) |
| Traversal | Walk typed edges. Modes: current · temporal | graph-traversal, bitemporal-ledger | node set, edge set, graph_snapshot_at | fan-out × depth — dominant cost |
| Enrich | Resolve nodes to attributes. Always batched | relational, document-passage | attribute sets, passage spans | entity × attribute fan-out |
| Similarity | Rank candidates within the permitted set | vector-index | ranked candidates with scores | candidate-set size |
| Evaluate | Deterministic computation. Modes: aggregate · score · reconcile · rank | in-memory | measures, scores, variances | negligible |
| Federate | Contract-bounded request to an external fabric | federated-external | remote attested payload, attestation record | network + negotiation |

Retired names: Batch Enrich (batch is mandatory, not a variant), Temporal
Traversal (a Traversal mode), Aggregate / Score / Reconcile / Rank (Evaluate
modes), Compose (contract assembly, not an operator).

### 10.3 Composition invariants

1. **Policy before anything that reads graph state.** Impermissible content
   is never materialized, not filtered afterwards.
2. **Resolve before Traversal.** Traversal from an unresolved anchor
   answers plausibly about the wrong entity.
3. **Enrich is batched, always.** One query per source per step.
4. **Algorithmic substrate before any semantic stage.** Every LLM
   invocation reads only the typed substrate a preceding algorithmic
   operator produced, and the substrate remains artifact-of-record.

### 10.4 Cost estimation

Cost bands are relative multiples of the Tier-1 baseline and are
placeholders until measured. Estimate before building:

```
est_cost = baseline
         × (1 + traversal_fanout^depth / fanout_reference)
         × (1 + enrich_sources)
         × mode_multiplier          # Mode 1 = 1 · Mode 2 ≈ 3–5 · Mode 3 ≈ 15
         × materialization_factor   # materialized = 1/hit_rate · on-demand = 1
```

Record the assumed fan-out, depth and hit rate. The commonest cost surprise
is a traversal whose fan-out was estimated on the median entity and paid on
the tail — **state the p95 fan-out, not the mean**.

---

## 11 · Shared contracts

Six artifacts referenced by every spec. Only the first exists today; the
rest block certification, not build.

| Artifact | Owner | Purpose | State |
| --- | --- | --- | --- |
| Ontology / IRI binding | Data architecture | Class and property IRIs every schema binds to | exists |
| Intent registry | Product owners + second line | Enumerated intent values and the envelope each selects | missing |
| Projection plan registry | Product owners | Named Π plans and what each assembles differently | missing |
| Policy version registry | Second line / compliance | Versioned envelopes with effective dates, resolvable at replay | missing |
| Half-life calibration table | Platform | λ_c per observation type with calibration basis | missing |
| Capability binding | Platform | Capability class to estate system, per environment | missing |

**Extension namespace** *(new in v0.3)*. Where a schema needs a class or
property the shared ontology does not carry, it is minted in the `ex:`
extension namespace — **registered centrally with an owner, once**, not ad
hoc per product. Three products minting their own covenant model
independently is three incompatible covenant models, and the divergence is
discovered at integration rather than at design.

### 11.1 Intent registry record

`intent` is required on every product and selects the policy envelope, which
makes it a governed object. Each record carries: intent id · plain-language
decision · the policy envelope selected · permitted principals · products
accepting it · owner · effective date and version · deprecation status.

### 11.2 Projection plan record

Each plan carries: plan id · principal(s) · **what is assembled
differently** (not displayed differently) · entitlement precondition ·
suppression behavior confirming the silence rule · owner · version. A plan
whose difference is presentational is rejected — that is a consumer concern.

---

## 12 · Naming, versioning and change classes

| Convention | Rule |
| --- | --- |
| Registry name | domain.product.vN — domain from the approved list, product in kebab-case, N = MAJOR only |
| Address | /context-products/{domain}/{product}/{anchor-id} |
| Schema artifact | schemas/{payload_type}.v{MAJOR}.json |
| Fixture id | {PREFIX}-{F/G/D/R}{nn} — happy path, gate, degradation, replay |
| Spec document id | CP-SPEC-{nnn} — stable across versions of the same product |

Change classes:

| Class | Examples | Consumer impact |
| --- | --- | --- |
| PATCH | Gate added, telemetry added, documentation | None |
| MINOR | Additive payload field, new optional parameter, new projection plan, λ_c recalibration | Backward compatible; notify consumers |
| MAJOR | Field removed or retyped, parameter default changed, ttl_anchor changed, Assembly Mode changed, policy envelope semantics changed | Migration window required; both versions served |

A λ_c or debt_tolerance change is **MINOR by type and material by effect** —
it changes outputs without changing shape. Announce these to consumers
explicitly rather than letting them surface as unexplained behavior change.

---

## 13 · Tiers, review and certification

| Tier | Capability classes | Cost band | Required review |
| --- | --- | --- | --- |
| 1 | relational | ×1 baseline | Product owner |
| 2 | + graph-traversal | ×1–2 | Product owner + platform |
| 3 | + bitemporal-ledger | ×2–4 | + second line where P is regulatory |
| 4 | + document-passage, vector-index | ×3–5 materialized, ×8–15 on demand | + second line, evidence-chain review |
| 5 | + federated-external, multi-principal Π | ×8–15 | + legal / control room |

Tiers describe assembly complexity, not maturity, and **not build order** —
build order comes from the prerequisite graph.

**Certification evidence.** Moving to certified requires, on file: schema
artifact published; all fixtures passing including the replay hash
assertion; measured p95 latency and per-call cost; debt_tolerance justified
against observed data; every §F gap closed or accepted by a named owner;
and, for Mode 2/3, model-risk registration complete.

---

## 14 · Review checklist for the reviewer (new in v0.3)

A reviewer reads for six things, in this order. The first three reject a
spec; the last three return it with comments.

- **Is the counterfactual falsifiable?** Can I run the test in §A and watch
  it fail? If not, the product's reason to exist is an assertion.
- **Is every capability stated as a capability, not a product?** A named
  database in §C means the spec is bound to a platform decision that has
  not been made.
- **Does every gap have an owner?** An unowned [TBC] is an unassigned risk
  that will surface during build.
- **Does each §D step name one operator from the closed vocabulary?**
  Bespoke logic in a step means cost moved from platform to product.
- **Is debt decomposed per claim?** A single product-level D_c forces
  all-or-nothing escalation and wastes the primitive.
- **Does the payload carry types?** Prose describing a payload is not a
  payload.

---

## 15 · Definition of done

- All seven sections present, in order, with front matter and capability
  gate
- Four-question build test answered, including honest partials
- Nine contract elements populated, including Assembly Mode with rationale
- Classification, residency and information-barrier fields complete
- Model-risk annotation complete for Mode 2/3, or "not applicable" for
  Mode 1
- Every §C element has a system of record, provenance class,
  classification, capability class, G dimension and ontology IRI
- Capability decomposition present where the estate answer is unknown, with
  interim posture named
- Correlation key stated with measured coverage, or the measurement named
  as a §F gap
- Every §D step names one operator from the closed vocabulary, its
  capability class, its emits, its failure behavior and its budget
- The four composition invariants hold
- Determinism class stated and a payload hash defined
- Replay statement plus a numbered, falsifiable replay test
- Emitted contract shown with types, conformant to the §8 envelope; error
  taxonomy mapped to steps
- Product-specific gates written as testable assertions with fixture IDs
- Half-life table carries a calibration basis and an owner per row
- Per-component debt table present, with behavior-when-absent per
  component
- Every no or partial in §F has a named gap owner; first-build volumetrics
  stated
- §G complete, including degradation contract, debt model, observability,
  retention and lifecycle
- Consumers list populated and cascading supersession targets named
- Acceptance criteria written as failable assertions; open blocking
  decisions named

---

## 16 · What changed from v0.2

| # | Addition | Why |
| --- | --- | --- |
| 1 | Rule 5 — every claim falsifiable | v0.2 required a counterfactual and a replay statement but allowed both to be narrative; a reviewer had no test to run |
| 2 | §0.2 placeholder discipline | An invented system name is a more serious defect than a marked gap, and v0.2 had no convention for marking one |
| 3 | §0.4 front matter and the capability gate | A blocking platform dependency discovered in §C is discovered after scheduling |
| 4 | §1 counterfactual acceptance test | Turns the counterfactual from a rationale into an executable check on the built product |
| 5 | §2.4 declared-but-inert parameters | A parameter that appears to work and does not will be relied on in a dispute |
| 6 | §3.2 capability decomposition and interim posture | Estates fail capabilities partially, not wholesale; the partial is the useful finding |
| 7 | §3.3 identity authority hierarchy | An anchor that silently excludes a population propagates the exclusion catalog-wide |
| 8 | §4.2 operator step table with emits and budgets | v0.2 prescribed prose steps; engineers need inputs, outputs and a latency budget per step |
| 9 | §4.5 falsifiable replay test | v0.2 defined hash equality but gave no procedure to demonstrate it |
| 10 | §4.6 emitted contract with types | The largest remaining gap between an architecture document and a buildable one |
| 11 | §5.2 per-component debt table | Product-level D_c forces all-or-nothing escalation; per-claim decomposition is what makes the primitive useful |
| 12 | §7.1–7.2 acceptance criteria and catalog contribution; §14 reviewer checklist | v0.2 could be written but not reviewed consistently |

Two v0.2 disciplines were reinforced rather than changed: λ_c remains
Control Plane configuration that a spec proposes rather than fixes, and the
suppression silence rule is now also a universal validation gate rather than
a prose rule.

``````

</details>

<a id="source-recipe"></a>

<details>
<summary>Specification generation recipe — ccf_code@37ac3055</summary>

Path: `public/reference/specifications/spec_generation.md`

``````text
# Generating a Context Product Specification — recipe for SDK Claude

**Audience:** the Claude session working in `ccf_code`.
**Output of this recipe:** one `CP-SPEC-NNN_<Product_Name>.md` in
**`examples/cp-NN-<slug>/spec/`** — inside the example it governs, never in a
docs folder (§7.1) — authored as the **first step** of that example project,
**approved by Dave before any implementation**, and closed out against a build
that proves it.
**Status:** authoring instruction, not a specification. Written 2026-08-29 by
the vault Claude at Dave's direction.

**Owner: the vault.** Proposed by `ccf-sdk` and sent through the §11 return path
2026-08-29; reverse it here if the vault rules otherwise. The reason is this
document's own §1 — most of what follows states **what the vault and
`ccf_dataprep` owe `ccf_code`**, and an agent that owns the document stating its
own entitlements is writing another agent's term, which is the failure §0
records. So: **`ccf_code` proposes changes here through the return path rather than
editing freely** — with one narrow exception, and a test for it.

**§7 describes `ccf_code`'s own tree**, so `ccf_code` may edit §7 directly and
report back when the edit **records what the tree already is**: a path, a
filename, a directory that exists, a layout the examples already follow. That
is what happened to §7.2 on 2026-08-29 — the diagram predated `page/` and
`summary_explanations.md`, and a session following it would have built an
example missing both.

**The test: could this edit be wrong tomorrow without any file moving?** If it
could, it is a rule and not an observation, and it goes through the §11 return
path — even when it sits inside §7, even when the tree already disagrees with
it, and even when every example already does what the edit says. A requirement
that something be published, a gate ordering, an approval, any *shall* or
*must* or *never*: rules. Observing that no CP-SPEC is published is an
observation. **Deleting the requirement to publish one is a rule change.**

Recorded rather than implied: §7.1's publication requirement was deleted
directly at `a9c4e28b` on 2026-09-12 and reported through `contrib/ccf-sdk/`.
**The vault ruled the outcome correct and the route wrong.** The edit stands and
is not precedent for the next one. The report was complete and honest, which is
why this is a wording change here rather than a reversal there.

**The companion document is `ccf_code`'s.**
[How an example is delivered](example_delivery.md) covers everything after the
spec is approved — the `make` target, the venv, the README run block, the
documentation page mechanics, the banker-facing summary, the verbatim-output
discipline and a delivery definition of done. Nothing in it is another agent's
term, so it is owned, edited and gated by `ccf_code` without a return path.
**Where the two documents disagree about `ccf_code`'s tree, the companion
wins**; where they disagree about what a specification must contain, this one
does.

---

## 0 · What this document is

There are 21 Context Products described in the obsidian vault. None of them has
an SDK specification yet except `counterparty-reference-snapshot`, and that one
is on the older CP-SPEC-001 form. This document is the recipe for producing the
rest.

A Context Product specification here is assembled from **three inputs owned by
three different agents**, it is **the first step in building a Context Product
example**, and **it does not proceed to implementation until Dave has approved
it** (§2).

The single most important rule in this document is that **you may not write
another agent's term.**

That rule exists because it has already failed once. The vault wrote a scope
sentence — *"identity only — no exposure, no grade, no relationship"* —
with no implementation to check it against. `ccf_dataprep` read it, correctly
treated the vault as the requirements authority, and generated an estate with
**no risk grade and no coverage assignment**. Meanwhile CP-SPEC-001's emitted
contract declares `internal_risk_grade`, `coverage_rm_id`, `coverage_team` and
`coverage_lob`, and its §E.2 assigns the absent overlay a **0.30 `D_c`
contribution against a 0.25 `debt_tolerance`** — which trips the debt gate and
returns `409`. Three agents, no malice, one unservable product.

Everything below is designed so that cannot happen twenty more times.

---

## 1 · The law: three owners, one term each

| Term of the equation | Owner | Authoritative for | Published as |
|---|---|---|---|
| **why it exists** | **vault**<br>`obsidian-vault/wiki/context-products/content/` | Decision frame · trigger · consuming principals · counterfactual and its closed-taxonomy failure mode · four-question build test result *with honest partials* · tier · build order · prerequisites · **scope boundary** · primitive taught · contrast pointer · the seven-class Commons/FIBO typing chain | The vault article, prose. §A and the front matter of your spec derive from it |
| **what data exists** | **ccf_dataprep**<br>`/home/parkave/ccf_dataprep` | §C element rows — system of record · provenance class · classification · capability class · `G` dimension · **ontology IRI** · §F readiness and *measured* coverage · §E calibration evidence · first-build volumetrics · every count, threshold and match rate | Their repo: `docs/spec-digest.md`, `docs/data-acquisition-plan.md`, `docs/known-issues.md`, `validators/spec_coverage.py`, `ontology/`, and the live `ccf_v2.*` schema |
| **what it does** | **ccf_code (you)** | §B.1 element values the runtime enforces · parameter surface · §D operator steps, budgets and witnesses · determinism class · replay test · emitted contract · validation gates and fixtures · error mapping · §E materialization and debt · §G operations — **and the merge itself** | `examples/cp-NN-<slug>/` — spec, artifacts and code together |

**The rule.** When a term you need is missing from its owner, you write
`[TBC — <owner>]` and name what you asked for. **You never guess it.** A guessed
term is indistinguishable from an authoritative one once it is written down, and
that is precisely how the grade/coverage break happened.

This is the standard's own placeholder discipline (§0.2) applied *across* agents
rather than within a document: *"a marked gap gets closed and an invented one
gets built."*

### 1.1 · Two levels of specification — and you are writing the second

**Ruled by Dave, 2026-08-29:**

> *"We must distinguish between the specification at the vault level versus the
> SDK level. The vault level is an **implementation independent** product
> specification whereas the SDK is a **specific implementation artifact** for
> developing the context product."*

Both documents are legitimately called `CP-SPEC-001`. They are different
artifact classes answering different questions, and **neither supersedes the
other.**

| | **Vault level** | **SDK level — what you write** |
|---|---|---|
| Document | `wiki/context-products/content/<slug>.md` | `examples/cp-NN-<slug>/spec/CP-SPEC-NNN_….md` |
| Answers | **what the product is** | **how it is built** |
| Posture | implementation-independent | a specific implementation artifact, bound to one estate |
| **Names a store** | **no** | **yes — or a table reference means nothing** |

**The Standard's §10.1 — *"product specs never name a database"* — is written
for the vault level.** Applying it to an implementation artifact strips out the
one thing a developer needs: *"As a context product developer how do I know
where the data being referenced lives?"* (Dave). In a five-store estate
`ccf_v2.legal_entity` does not say whether that is the relational store, the
graph ledger, the document store or the departmental file.

**Three levels. Only the middle one moves:**

| Level | Example | Vault level | SDK level |
|---|---|---|---|
| Capability class — what the store must *do* | `relational` | yes | yes |
| **Store · schema · table — where the element *is*** | `PostgreSQL ccf_v2.legal_entity` | **no** | **yes** |
| Deployment — host, port, credential, instance | — | **never** | **never** |

**Deployment never appears in a specification of either kind.** It lives in
`backends.yaml` as an environment-variable *name*. A sweep of `examples/`,
`public/`, `src/` and `runtime/` for the estate's host address must return
nothing, and no credential enters the tree.

> **This distinction cost a working session before it was written down, and it
> produced two errors in opposite directions.** Read side by side without it,
> the vault article and the repo's `CP-SPEC-001` look like rival drafts of one
> document — 11 §C rows against 4 — and the apparent task is to adjudicate which
> wins. There was no conflict. Then the same gap, applied the other way, stripped
> store identification out of an implementation spec on the literal reading of a
> rule written for the other level. Carry the frame, not just the rules.

---

## 2 · The sequencing law: spec first, approved, then build

**Every specification must be approved by Dave, and the approved specification
is the first step in creating a Context Product example.** Nothing is
implemented before that approval. There are two gates.

### Gate 1 — the authored spec (blocking)

A CP-SPEC is **not** written for the whole catalog in advance. It is written as
**step one of one example project**, when that product comes up the ladder. At
Gate 1 you author everything knowable before code exists:

- §0 and the data banner · front matter · capability gate
- §A in full, including the counterfactual acceptance test as a procedure
- §B.1–B.5 — the nine elements, parameter surface, scope boundary
- §C in full — every element bound to a real table and IRI, coverage measured,
  traps named
- §D.1–D.3 — client call, the operator step table, step detail
- §D.7 gates and §G.2 acceptance criteria, **as intentions phrased so they can
  fail**
- §E.1–E.5 and §F.1–F.4 — with measured data reality from `ccf_dataprep`
- Everything not yet measurable marked **`[TBC — this build, phase Pn]`**

**Send it to Dave. Do not write implementation code until he approves it.** He
is approving the *design*: scope, decision frame, contract elements, operator
composition, and what the product will be held to. That is the cheapest moment
to catch a wrong product, and the grade/coverage break in §10.1 is what an
unreviewed scope boundary costs downstream.

### Gate 2 — the completed spec (close-out)

During and after the build, the measurable terms land: p95 budgets, payload
hashes, witnesses, replay results, gate-failure observations, final
materialization posture. You fill them in and clear every `[TBC — this build]`.

Gate 2 is **not** a second design review. It is a close-out: the approved design
is now discharged by something that runs.

**Nothing at Gate 2 may silently change a Gate-1 decision.** If the build
disproves an approved term — a λ_c, an operator step, a scope boundary — that is
a **deviation**: stop, state it, and take it back to Dave. Do not edit the
approved design to match what you built.

### An approved spec IS editable — classify the edit, not the document

**Ruled by Dave, 2026-08-29.** Approval does not freeze the file. It freezes
**what was approved**, which is not the same thing. Three classes:

| Class | Examples | What to do |
|---|---|---|
| **Editorial** | spelling, a heading brought into line with the Standard, formatting, a broken link, a typo | **Just edit it.** No notice, no approval. Name it in the commit message |
| **Corrective** | a factual error in something approved — a wrong table name, a miscounted row, a stale path | **Edit it, then say what changed and why.** No re-approval; visibility is the obligation |
| **Substantive** | a contract element value · scope boundary · operator step · λ_c · a gate · a parameter · anything that changes what the approval was *about* | **Still a deviation.** Stop, state it, take it back. Unchanged by this ruling |

The test is not *"is the document approved?"* — it always is. The test is
**"would Dave's approval have been different if the document had said this
originally?"** If no, edit. If yes, escalate.

Regenerating a published page after an editorial edit is part of the edit, not a
separate approval.

### Why the claims must still be discharged by a run

Approval makes the design binding; it does not make the claims true. That is
what `examples/cp-00-institutional-holders/artifacts/assembly-recipe.yaml`
holds you to:

> *"**THE §D OPERATOR STEP TABLE, AS DATA** — so that criterion 2 is discharged
> by a test rather than by a reading... **A prose table cannot be held against a
> run.** This document declares the same steps with, per step, a WITNESS — a fact
> a completed run either produced or did not... **a step nothing executes is
> RED.**"*

So: the spec is approved first and proven second. A section whose content cannot
be known before the build is `[TBC — this build]` at Gate 1, never a plausible
guess — a guessed budget that survives review becomes a number someone plans
against.

## 3 · Build order: the ladder is the vault's, not yours

Priority is **increasing complexity**, and the vault establishes it. Do not
reorder for convenience. Each rung teaches a primitive the next rung assumes,
and the catalog is a teaching sequence as much as an inventory.

`cp-00-institutional-holders` sits below the ladder as your own warm-up rung and
is already built. The vault's 21 follow:

| Rung | Tier | Product | What it exists to prove |
|---|---|---|---|
| 01 | **T1** | `counterparty-reference-snapshot` | The contract fires. Identity authority hierarchy. The replay harness itself |
| 02 | T1 | `facility-terms-snapshot` | Anchoring on something other than a legal entity; `from_entity_freshness` against a document-dated source |
| 03 | T1 | `obligor-financial-spread` | Attribute-level temporal validity before any graph exists |
| 04 | **T2** | `corporate-family-tree` | First multi-store product. Multi-hop traversal, cross-shareholding cycles as findings |
| 05 | T2 | `credit-exposure-rollup` | Traversal + aggregation; the concentration denominator a flat product gets wrong |
| 06 | T2 | `collateral-and-setoff-coverage` | Typed edge vocabulary; coverage as a graph question |
| 07 | T2 | `client-360-coverage-graph` | High fan-out; where traversal cost becomes a design constraint |
| 08 | **T3** | `covenant-in-force-as-of` | **Flagship.** Ledger time-travel, supersession preserved |
| 09 | T3 | `treasury-liquidity-position` | Fast `λ_c` forcing on-demand derivation |
| 10 | T3 | `rating-and-spread-migration` | Per-signal decay curves |
| 11 | T3 | `credit-surveillance-early-warning` | Supersession cascading across downstream products |
| 12 | T3 | `fx-post-trade-reconciliation` | Two time axes that must be separately parameterised |
| 13 | **T4** | `covenant-cross-reference` | Passage-level lineage across documents |
| 14 | T4 | `credit-memo-context` | Algorithmic/semantic stage alternation; debt across a multi-agent handoff |
| 15 | T4 | `kyc-refresh-beneficial-ownership` | Entity resolution; ownership to person level |
| 16 | T4 | `abs-securitization-surveillance` | Loan-level fan-out; forces the materialization decision |
| 17 | **T5** | `mnpi-wall-enforcement` | Entitlement as formative constraint — the edge never materializes |
| 18 | T5 | `ib-opportunity-synthesis` | Projection `Π` across three principals |
| 19 | T5 | `aml-typology-match` | Policy-before-Similarity. **Synthetic obligor only, never a named real company** |
| 20 | T5 | `syndicated-lending-co-lender` | Cross-organizational federation under a negotiated envelope |
| 21 | T5 | `large-exposure-rwa-concentration` | Composes every primitive below it |

**Tier is not build order within a tier** — the vault's index order above is.
Where a product's `Prerequisites` name another product, that dependency
overrides the list.

---

## 4 · Phase 0 — gather, before you write a line *(Gate 1)*

For product `<slug>`:

**4.1 Read the vault article in full.**
`/home/parkave/obsidian-vault/wiki/context-products/content/<slug>.md`
Or `get_article("context-products", "<slug>")` over MCP.

Extract and hold separately — these are the vault's terms and you will not
alter them:
- decision & trigger, consuming principals
- counterfactual failure + which closed-taxonomy mode it names
  (`context-starved · temporally-incoherent · perspective-flat · policy-blind · evidence-free`)
- the four-question test result, **including partials and nos**
- tier, build order note, prerequisites, consumers
- **scope boundary** — record it verbatim; see §10 warning
- primitive taught, contrast pointer

> ⚠️ **Twenty of the 21 vault articles are on the older Q019 form**, where **§F
> means *Manufacture envelope*, not *Source binding & readiness*.** Only
> `counterparty-reference-snapshot` is on v0.3. Resolve vault sections **by
> heading name, never by letter.**

**4.2 Pull the data reality from ccf_dataprep.**

| Need | Where |
|---|---|
| §C rows as dataprep holds them | `validators/spec_coverage.py` — `read_catalog()` and the per-product manifests |
| §C/§F as dataprep read the vault | `docs/spec-digest.md` |
| Obligor cast, waves, acquisition decisions | `docs/data-acquisition-plan.md` |
| Known defects and limits | `docs/known-issues.md` |
| Ontology IRI bindings | `ontology/`, plus the vault's `fibo-iri-binding` mirror |
| Anchor-cast satisfaction | `validators/cast_audit.py` |
| Live estate | the `ccf_v2.*` schema |

**Measure, do not assume.** Every count, coverage figure and match rate in your
spec must come from a query you ran or a dataprep artifact you can cite.
`bound is not the same as materialized` — an IRI documented in the binding
mirror does not mean rows exist against it.

**4.3 Re-read the Standard.**
`public/reference/specifications/Context_Product_Specification_Standard_v0-3.md`

Known errata — the document's own cross-references are stale in six places, so
resolve by heading, not by the number cited: response envelope is **§8** (cited
as §10, twice); intent registry **§11.1** (cited §13.1); projection plans
**§11.2** (cited §13.2); change classes **§12** (cited §14, twice); capability
classes and operator vocabulary **§10.1/§10.2** (cited §11.1/§11.2).

**4.4 Use CP-SPEC-000 as your template, not CP-SPEC-001.**
`examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`

CP-SPEC-001 predates the current form. CP-SPEC-000 carries the embedded §0, the
B.1–B.5 / C.1–C.5 / D.1–D.7 / **E.1–E.5** / F.1–F.4 / G.1–G.3 structure, the
`[TBC]`-with-owner register at F.2, and the mandatory data banner. Match it.

---

## 5 · Phase map — Gate 1, then build, then Gate 2

| Phase | Gate | What you do | Spec sections |
|---|---|---|---|
| **P1 · Frame** | 1 | Read vault article; confirm the product is real and belongs | §0, banner, front matter, §A, §B.5 |
| **P2 · Bind** | 1 | Map every element to a real table/column and IRI; measure coverage | §C.1–C.3, §F.1, §F.3 |
| **P3 · Trap** | 1 | Find what the data does *not* support cleanly; choose bindings, record their cost | **§C.4**, §C.2, §F.4 |
| **P4 · Design** | 1 | Contract elements, parameter surface, operator composition, intended gates and criteria | §B.1–B.4, §D.1–D.3, §D.7, §E.1–E.5, §G.2 *(budgets and measured values `[TBC — this build]`)* |
| **▶ GATE 1** | — | **Send to Dave. Stop. No implementation until approved.** | Spec complete except `[TBC — this build]` |
| **P5 · Assemble** | 2 | `assembler.py`, `produce.py`, `deployment.py`, `ccf_config.yaml`, `backends.yaml` | code; `artifacts/*.yaml` |
| **P6 · Run** | 2 | Execute; capture budgets, hashes, witnesses | §D.2 budgets, §D.4, §D.5, §D.6 |
| **P7 · Gate** | 2 | Fixtures; make each gate fail deliberately once | §D.7 fixture IDs, §G.2 results |
| **P8 · Operate** | 2 | Measure decay against read frequency; confirm posture | §E.1 basis, §E.3 posture, §G.1, §G.3 |
| **▶ GATE 2** | — | Clear every `[TBC — this build]`; file returns to vault and dataprep | §F.2 register closed |

A Gate-1 section written from imagination is the failure this map exists to
prevent. A Gate-2 value that contradicts an approved Gate-1 decision is a
**deviation** — see §2.

## 6 · Section-by-section recipe

Throughout: **SOURCE** = whose term it is · **NEVER INVENT** = the failure mode
· **DISCHARGED BY** = what proves it.

### §0 · What this document is

Restate the standard's five rules, the four-question test, placeholder
discipline, the section skeleton and front matter — as CP-SPEC-000 does. This is
deliberate duplication so the spec is readable standalone.

**Then the banner. It is mandatory and it is not boilerplate.**

CP-SPEC-000 opens with `READ THIS BEFORE YOU READ A NUMBER`, stating that the
examples **teach method, not figures**, with that product's own *measured*
provenance counts. Reproduce this with **your product's measured numbers**, and
follow CP-SPEC-000's discipline of repeating the statement **beside each figure
cluster** rather than leaving it as a header a reader scrolls past.

For `aml-typology-match` (rung 19) the vault adds a hard constraint: **synthetic
obligor only, never a named real company.** Carry it into the banner.

### Front matter

**SOURCE:** vault (registry name, tier, build order, what it resolves) ·
you (Assembly Mode, cost band, lifecycle).

Registry name is `domain.product.vN`. **Assembly Mode is a registration-time
commitment** — a documented decision with a one-sentence cost/quality/determinism
rationale, not a description of how you happened to build it. Modes 2 and 3
require §B.3.

**Capability gate above §A** where the product cannot be built without a
capability the estate may not have. This is a scheduling statement.

### §A · Decision frame

**SOURCE: vault, entirely.**
**NEVER INVENT:** the counterfactual, the failure-taxonomy mode, or the
four-question result. If the vault's four-question result carries a `no` or a
`partial`, **carry it through unchanged** — `counterparty-reference-snapshot` is
admitted on one no and one partial, stated openly, and that honesty is the
standard working.

**You add one thing:** the **counterfactual acceptance test** — the vault's
narrative counterfactual rewritten as a numbered procedure ending in an
assertion that can fail. State the query, both answers, and the condition under
which they must differ.

**DISCHARGED BY:** a test in the example that runs the counterfactual and fails
if the two answers agree.

### §B · Contract

**B.1 — the nine elements.** Schema · Freshness SLA · TTL · Policy Binding ·
Lineage · Semantic Version · Discovery · Addressability · **Assembly Mode**.

**SOURCE: you.** The vault's element values are theoretical and have been
measurably wrong — its `counterparty-reference-snapshot` set `λ_c ≈ 24h` where
the real half-life is ~365 days, having substituted publication cadence for
decay. Take element *intent* from the vault; take *values* from your runtime.

Rules that are not negotiable:
- **Schema** binds every entity, relationship, attribute and measure to an
  **ontology IRI**, and links a machine-readable artifact at
  `schemas/{payload_type}.v{MAJOR}.json`. *Prose in a table cell is not a
  contract.*
- **Freshness SLA** is **per signal class**, never one value over a mixed payload.
- **TTL** carries `ttl_anchor` **and states how `expires_at` is computed.** For
  `from_entity_freshness` that is source publication time, not request time —
  *a 23:00 request against an 06:00 file gets 7 hours of validity, not 24.*
  **Nine vault specs declare this anchor and none define the computation.** You
  must.
- **Lineage** is the full list: `operators_invoked[]` · `graph_snapshot_at` ·
  `policy_version` · `projection_plan_id` · passage anchors where a claim rests
  on text · `context_debt` · `payload_hash` · `model_record`. Plus any
  product-specific authority field. `operators_invoked` carries **typed operator
  references** — `ResolveOperator@entity-master.v1.0` — **not bare names**,
  because lineage strict equality compares them.
- **Discovery** is registered only after §G is complete.

**B.2 — classification and residency.** Data classification (highest of any §C
element) · information barrier · residency · cross-border serving. **The
suppression rule:** where policy excludes content the payload carries **no
count, marker or placeholder**. A "3 items hidden" marker is itself a
disclosure.

**B.3 — model-risk annotation.** Modes 2/3 only: pinned model and version,
pinned temperature, versioned prompt, model-risk registration, the
**substrate/presentation boundary**, and the **smoothing control** — how the
design stops the model reconciling a conflict the substrate deliberately
surfaced. Mode 1 states *"not applicable — no model in the trust path."*

**B.4 — request parameter surface.** Every parameter with a **Moves** column
naming which dimension it moves (`E` anchor · `R` scope · `T` reconstruction ·
`P` envelope · `Π` perspective · a measure). A parameter that moves nothing is a
formatting flag — push it to the consumer.

Required on every product: an anchor identifier, `intent`, `debt_tolerance`.

**Declared-but-inert parameters** must be declared and **fail explicitly** with
`not_supported_at_tier`, never silently succeed. This keeps the request surface
uniform so consumers do not learn a second calling convention at a higher tier.

**B.5 — prerequisites, consumers, scope boundary.**
**SOURCE: vault** for prerequisites and consumers (it owns build order).
Consumers must be **named individually** — supersession cascades and MAJOR
version notification both need a reverse dependency list, and *"every other
product"* cannot serve as one.

> ⚠️ **Scope boundary — treat with suspicion.** This is the field that broke.
> Copy the vault's sentence verbatim, then **check it against your §C and your
> payload.** If your payload declares a field the vault's scope excludes, you
> have found a live conflict: **do not silently resolve it.** Record it, raise
> it (§11), and mark the field `[TBC — ruling]` until it is settled.

### §C · Data catalog

**SOURCE: ccf_dataprep, entirely.**

**C.1 — element table.** One row per element, *not per table*:

`Element · System of record · Provenance class · Classification · Capability class · G dimension · Ontology IRI`

- **Provenance class** is the closed list: `internal-SOR · vendor ·
  public-filing · derived · inherited`. `synthetic` is **not** a provenance
  class — it is a property of the estate and belongs in the §0 banner or its own
  column. The vault conflates these; do not copy that.
- **Capability class** — never a product name. `relational ·
  bitemporal-ledger · graph-traversal · document-passage · vector-index ·
  federated-external · in-memory`. This column says what the store must *do*.
- **Store · schema · table — name it.** Per §1.1 you are writing the
  implementation artifact, so §C.1 carries a store column alongside capability
  class, and §F.3 states the estate binding collectively — including **which
  stores this product does not read, and why.** The vault article's store
  assignment is a **proposal** to confirm against the real estate, not residue
  to discard and not an authority to copy. **Deployment detail — host, port,
  credential — never appears.**
- **G dimension** — every element lands in `E · R · T · P · Π · L · schema`, or
  it is not context.
- **Ontology IRI** — unbound elements block registration. Foundational party
  terms are in **OMG Commons** (`cmns-org:`), not FIBO; only `Corporation` stays
  as `fibo-be-le-cb:Corporation`. A validator asserting every IRI begins
  `spec.edmcouncil.org` will reject correct data.

**C.2 — capability decomposition.** Decompose each required capability into
separable properties with `Widely available · sometimes · rare` and what is
deliverable if each is absent. State the **interim posture** where the answer is
partial. Estates fail capabilities partially, and the partial is the finding.

**C.3 — correlation key, single-writer, identity authority.** The join key,
where the crosswalk lives, its **measured** coverage. One authoritative writer
per element. Where an anchor does not exist for every entity the product serves,
tabulate entity classes, identity authority, and the **freshness ceiling each
implies** — an anchor that silently excludes a population propagates the
exclusion catalog-wide.

**C.4 — the data traps.** CP-SPEC-000's most valuable section and the one with
no vault equivalent. **Where the data does not cleanly support what the spec
wants, name the trap, the binding you chose, and what that choice costs.**
CP-SPEC-000 records ~22.5% weak issuer matching **by design** rather than as a
defect. A spec with no traps section has either a perfect estate or an
unexamined one.

**C.5 — what this data is.** Restate the synthetic/engineered posture beside the
figures, per the banner discipline.

### §D · Assembly recipe

**SOURCE: you, entirely. This section is code before it is prose.**

**D.1 — client call.** The literal request, parameters populated. Where the
product has a forensic and a live case, show the **forensic** one — it exercises
more surface.

**D.2 — operator step table.** One operator per step:

`# · Operator · Capability class · Inputs · Emits · Failure behavior · p95 budget`

Operators come from the closed vocabulary only: **Resolve · Policy · Projection
· Traversal · Enrich · Similarity · Evaluate · Federate**. Retired names —
Batch Enrich, Temporal Traversal, Aggregate/Score/Reconcile/Rank, Compose — are
not operators. Final step is always contract assembly.

**State the budget total and the envelope it is measured against.** A total at
97% of envelope is a design finding: say which step dominates and what the first
optimization would be.

**Mirror this table into `artifacts/assembly-recipe.yaml` with a WITNESS per
step.** A step nothing executes is RED.

**D.3 — step detail.** Prose only where a step carries a non-obvious discipline.
Two recur and must be written wherever they apply:
- **Policy runs first even when it appears to do nothing.** At T1 it is an
  entitlement check; at T5 it is what makes a restricted edge structurally
  absent. Learned from the first product or retrofitted painfully.
- **Two filters on two axes are two filters.** Separately parameterised,
  separately testable. Applying one silently answers a different question.

**D.4 — determinism class and payload hash.** `deterministic` (Mode 1) or
`substrate-deterministic` (Modes 2/3) — those exact enum strings; they ship in
the envelope. Publish a hash over the deterministic portion excluding
`assembled_at`. **Replay asserts hash equality, not similarity.**

**D.5 — replay statement and falsifiable replay test.** A numbered procedure
ending in an assertion that can fail: serve and record · mutate state ·
re-derive live and confirm the new value · re-derive at the recorded snapshot
and confirm the **original** returns. If the last step returns the new value,
`graph_snapshot_at` is decorative.

Two time axes ⇒ a second test asserting the axes **disagree** under a
constructed case. Agreement means a filter was dropped.

**D.6 — emitted contract.** The §8 envelope populated **with types**. This is
what consuming teams code against and what CI validates. `extra=forbid` is a
build-time invariant. *Prose describing a payload is not a payload.*

**D.7 — validation gates.** Six universal, without re-argument: empty-operator
guard · lineage strict equality · TTL bounds · debt gate · suppression silence ·
classification containment. Then **product-specific gates**, each a testable
assertion naming the defect it detects, cross-referenced to a fixture ID.

**Error mapping** — condition → raising step → response. `404` unresolvable ·
`403` not entitled, no detail on what exists · `400 not_supported_at_tier` ·
`409` debt gate with the debt block · `503` mandatory input unavailable, source
class named · `200` with notices for non-mandatory. **Silence is not a negative
answer** — an unretrieved screening source is not a clean screen.

### §E · Volatility, debt & materialization

**SOURCE: dataprep for calibration evidence, you for the model and posture.**

**E.1 — half-life table.** Per signal class: `λ_c` · **calibration basis** ·
decay driver · supersession event · owner.

> **λ_c is a half-life, not a refresh cadence.** A daily file does not make a
> legal name decay daily. This is the single most consequential error in the
> vault's version and it must not propagate.

Calibration basis is `illustrative · expert · measured`. **State plainly where
no row is measured.** λ_c is Control Plane configuration; your table is a
proposal.

**E.2 — debt model and per-component debt.** `D_c = 1 − (F · C · S)`,
multiplicative so a collapsed dimension forces escalation. **Normalize F over
required signal classes, not over classes present**, or losing a source improves
the score.

Then the per-component table: `Component · May be absent? · D_c contribution ·
Behavior when absent`. **Debt decomposes per claim, never only per product** —
four claims with one input missing returns three evaluated and one
`NOT_EVALUABLE`, not a product-level failure.

Check your contributions against `debt_tolerance`. A single optional component
contributing more than the default tolerance means the product refuses to serve
whenever it is absent — that is a design finding, not an accident.

**E.3 — materialization posture.** `materialized · derived-on-demand · split`.
The test is mechanical: **if the fastest-moving input's λ_c is shorter than the
intended cache window, materialization is wrong.** Feed it a real λ_c — fed a
cadence, it returns the wrong architecture while looking correctly applied.

State the **cache key** explicitly: tenant · schema · plan id · snapshot · time
parameters · principal binding · every parameter that changes the payload. A
missing key parameter is a correctness defect presenting as an intermittent one.

**E.4 — supersession triggers.** Each **local** or **cascading**; for cascading,
the named downstream products. Re-derivation is **lazy** — invalidate for next
request, never re-materialize eagerly.

**E.5 — the expiry and its refusals.** Per CP-SPEC-000: state what expiry
actually produces at the delivery boundary and which refusals it can raise.

### §F · Source binding & readiness

**SOURCE: dataprep, entirely.**

**F.1** — per element: system of record · interface & cadence · **available
today** (`yes · partial (name the fields) · no`) · gap owner · blocker.

**F.2** — **every `[TBC]` in the document, with an owner.** This is the register
that makes the cross-agent discipline auditable. Each row names the term, the
owning agent, and what was asked. **No spec passes review with an unowned gap.**
*"Does not exist yet" is a valid state; unattributed is not.*

**F.3** — access path · **identifier reality** (does the key exist end to end,
who owns the crosswalk, measured coverage) · **history depth** (where the source
publishes snapshots without history, say *start retaining deltas now* — history
not captured cannot be reconstructed later) · text-source boundary ·
**first-build volumetrics**: the population the first build needs for every gate
and counterfactual to have something to act on. Where a required case does not
occur naturally, **widen the sample until it does**.

**F.4** — **recorded findings that are not `[TBC]`**, because they need no
decision to build. Keep this distinct from F.2; conflating a finding with a
blocker inflates the blocker list and hides the real ones.

### §G · Operate & govern

**SOURCE: you.**

Accountable owner (roles, not individuals) · service objectives (p50/p95,
volume, concurrency, payload bound, **absolute** per-call cost alongside the
relative band) · degradation contract per input class with **mandatory classes
named** · debt model · observability (per-operator latency, `D_c` distribution,
gate failures by gate, cache hit rate, entitlement denials, degradation-branch
frequency, supersession invalidations — this is the evidence base that moves
λ_c from illustrative to measured) · retention and record of record · test
fixtures · lifecycle (`draft · in-build · certified · deprecated`).

**G.1** — restate the expiry obligation where an operator will look for it.

**G.2 — acceptance criteria.** Assertions **specific to this product**, each
independently verifiable, each phrased so it can fail. Close with the **open
decisions blocking build**, named by their §F.2 row.

**G.3 — catalog contribution.** What this product proves that nothing earlier
proved, and what it deliberately does not prove. The vault's *primitive taught*
is your input. A product that proves nothing new is a merge candidate; a product
whose exclusions are unstated invites a reviewer to read a tier boundary as an
oversight.

---

## 7 · Where the spec lives, and the artifacts around it

### 7.1 · The spec lives in the example, not in the docs tree

**A product spec belongs at `examples/cp-NN-<slug>/spec/CP-SPEC-NNN_<Name>.md`,
and is created there at Gate 1.** It is never authored in
`public/reference/specifications/`.

This follows from §2 rather than from filing preference. A spec whose §D steps
are discharged by witnesses in `artifacts/assembly-recipe.yaml`, and whose
emitted contract is validated by CI against code in the same directory, has to
be **versioned with the thing that proves it**. Move it into a documentation
tree and the claims and their evidence can drift in separate commits — which is
the entire failure this recipe exists to prevent.

The two trees have different jobs:

| Path | Holds | Example |
|---|---|---|
| `examples/cp-NN-<slug>/spec/` | **product specifications** — one per example, co-versioned with the code that discharges them | `CP-SPEC-000-institutional-holders.md` |
| `public/reference/specifications/` | **reference documents** — things that govern specs but describe no product | `Context_Product_Specification_Standard_v0-3.md`, this recipe |

**ONE CANONICAL SPEC, AND NO SECOND COPY THAT CAN DRIFT.** A product
specification lives in its example's `spec/` directory and **is not duplicated
into `public/`**. There is no second location and no per-spec nav entry.

| | Where |
|---|---|
| **Canonical, and the only copy** | `examples/cp-NN-<slug>/spec/`, from Gate 1 onward — versioned with the artifacts and code that discharge it |
| **`public/reference/specifications/`** | reference documents that **govern** specs and describe no product: the authoring standard, this recipe, the delivery companion |

Public documentation **may reference or summarize** a CP-SPEC — link to it,
quote a clause, explain what a rung proves. It must not create a second copy of
the document.

**This corrects what this section used to say, and the correction is a
documentation-rule fix rather than any product's deviation** (Dave,
2026-09-12). The previous text directed a copy into
`public/reference/specifications/` with a nav entry after Gate 2, and cited
`mkdocs.yml` for it. `mkdocs.yml` says the opposite, in a ruling of the same
author dated 2026-08-29:

> *"Individual CP-SPECs do NOT live here. A specification lives in its own
> example's `spec/` directory, beside the artifacts and code it governs.
> `CP-SPEC-001` sat here only to bootstrap the authoring process and was deleted
> at `59831ea5` once it had served that purpose — by then it had drifted to 640
> lines against a 1,355-line canonical source, silently dropping every section
> that recorded an open question."*

**The precedent is unanimous and was measured before this edit: no CP-SPEC for
`cp-00` through `cp-08` is published under `public/` at all.** Eight gates
closed without it. The surviving instruction here was stale, and it was caught
at rung 9's Gate 2 by an executor who stopped rather than following it.

**Why the deleted copy is the argument.** A specification is proven by the
artifacts and tests beside it; a copy somewhere else is proven by nothing, and
the first thing it loses is the sections recording open questions — which is
exactly what happened, and it happened silently, because a stale copy renders
perfectly well.

> ⚠️ `public/` has a strict docs build. **Any file you add under `public/`
> without a nav entry fails `mkdocs build --strict`.** That still holds for the
> reference documents this directory does carry.

> **`CP-SPEC-001_Counterparty_Reference_Snapshot.md` is a deliberately placed
> exemplar — *"what a spec would look like for counterparty reference"* (Dave,
> 2026-08-29) — and it is a **control, not a source.**
>
> The plan for rung 01 is that you author the spec **fresh from this recipe**,
> and Dave then compares your output against that file **by hand**. That
> comparison is a test of the recipe as much as of your spec, and it only works
> if you have not read CP-SPEC-001 as an input. **Deltas are expected and are
> the point.** Where your spec differs, the difference is the finding.
>
> So: author at `examples/cp-01-counterparty-reference-snapshot/spec/`. Do not
> copy from CP-SPEC-001, do not reconcile against it, and do not treat its
> values as authoritative — it predates the example-based structure, has no
> `artifacts/`, no witnesses, and the error classes cataloged in §10.2.

### 7.2 · The example layout

The spec is one file in a runnable example. Match `cp-01`'s layout:

```
examples/cp-NN-<slug>/
├── spec/CP-SPEC-NNN_<Product_Name>.md
├── artifacts/
│   ├── assembly-recipe.yaml   ← §D.2 as data, with a WITNESS per step
│   ├── expected.yaml          ← what the served product should contain
│   ├── question.yaml          ← the caller's vocabulary, read-side
│   └── ttl.yaml               ← the class TTL and its ceiling
├── assembler.py  produce.py  run.py  deployment.py
├── backends.yaml  ccf_config.yaml
├── page/                      ← build_page.py + template.html committed, render is not
├── README.md
└── summary_explanations.md    ← the banker-facing document
```

**The `page/` directory and `summary_explanations.md` are not optional**, and
what goes in them, plus the `example-cp-NN` target, the venv discipline and
the validation pass, are governed by
[How an example is delivered](example_delivery.md) — which is authoritative for
everything downstream of this section. This diagram is the summary; that
document is the recipe.

All `artifacts/*.yaml` validate against
`docs/schemas/ccf.declared-artifact.json`.

Follow `cp-00`'s `expected.yaml` discipline: **it derives nothing from a run.**
When artifacts change, run the suite, review the failure, and deliberately edit
the file in the same commit — so an expected-output change is an edit to a
reviewed artifact rather than a refreshed transcript.

---

## 8 · Definition of done — the specification

Ship when all of these hold. This is the standard's §15, plus what this pipeline
adds.

**These are the SPECIFICATION's conditions and they are half the deliverable.**
The example's conditions — the `make` target, the venv, the README run block,
the documentation page, the banker summary, the verbatim-output check and the
validation pass — are [How an example is delivered](example_delivery.md) §11.
Both lists must hold before anything is presented to Dave.

- **The spec was approved by Dave at Gate 1 before any implementation code was
  written**, and every Gate-2 deviation from the approved design was taken back
  to him rather than absorbed
- All seven sections present in order, with §0, front matter, capability gate
  and the data banner
- Four-question result carried from the vault **including partials**
- Nine contract elements populated, Assembly Mode with rationale
- Classification, residency, information-barrier complete; model-risk complete
  for Modes 2/3 or "not applicable" for Mode 1
- Every §C element has SOR, provenance class, classification, capability class,
  G dimension and ontology IRI — and **no §C row names a database**
- Capability decomposition present where the estate answer is unknown, with
  interim posture
- Correlation key stated with **measured** coverage, or the measurement named as
  an F.2 gap
- Every §D step names one closed-vocabulary operator with capability class,
  emits, failure behavior and budget — **and has a witness in
  `assembly-recipe.yaml`**
- The four composition invariants hold: Policy before any graph read · Resolve
  before Traversal · Enrich always batched · algorithmic substrate before any
  semantic stage
- Determinism class stated with an enum value; payload hash defined
- Replay statement plus a numbered falsifiable replay test that has been **run
  and observed to fail** when the snapshot is bypassed
- Emitted contract shown with types, conformant to the §8 envelope, passing
  `extra=forbid` in CI; error taxonomy mapped to steps
- Six universal gates plus product-specific gates with fixture IDs, **each made
  to fail deliberately at least once**
- Half-life table carries calibration basis and owner per row, and **no λ_c is a
  publication cadence**
- Per-component debt table present; contributions checked against
  `debt_tolerance`
- Materialization posture derived from measured λ_c against read frequency;
  cache key complete
- Every `no` or `partial` in §F has a named gap owner; volumetrics stated
- §G complete; consumers named individually; cascading supersession targets named
- **F.2 register complete — every `[TBC]` carries an owning agent**
- Acceptance criteria are failable assertions; blocking decisions named

---

## 9 · Cross-agent placeholder discipline

| Situation | Write |
|---|---|
| Vault has not framed something you need | `[TBC — vault]` + what you asked |
| Data reality unknown or unmeasured | `[TBC — ccf_dataprep]` + the measurement needed |
| Vault framing and build evidence conflict | `[TBC — ruling]` + both readings, verbatim |
| You have not built it yet | `[TBC — this build, phase Pn]` |

Never `[TBC]` bare. An unowned marker is an unassigned risk, and the F.2
register is what makes it collectable.

---

## 10 · Known conflicts — do not resolve these silently

**10.1 · `counterparty-reference-snapshot` grade and coverage — NOT blocking.
Author to the vault.**

The vault's scope boundary says *"identity only — no exposure, **no grade**, no
relationship."* CP-SPEC-001's payload declares `internal_risk_grade`,
`coverage_rm_id`, `coverage_team`, `coverage_lob` and an `internal_risk_grade`
freshness class. `ccf_dataprep` built to the vault's reading and carries **none**
of those fields.

**This is not a conflict between two authorities.** Scope boundary is the
**vault's term** under §1, and CP-SPEC-001 is an exemplar for later comparison
(§7.1), not a source. So:

- **Author to the vault's scope.** No internal overlay in rung 01.
- The overlay is then **not a debt component at all**, so CP-SPEC-001's
  0.30-against-0.25 `debt_tolerance` collision — and the `409` it implies —
  **does not arise.** That failure exists only under a per-component table
  counting a field the spec does not carry.
- **`ccf_dataprep` is already aligned.** Nothing needs regenerating.

If your build disproves the vault's scope, that is a §11 return, not a reason to
stop.

> **A ruling that was inferred rather than made.** On 2026-08-29 Dave pasted
> **both** documents — the vault's `counterparty-reference-snapshot` article at
> 03:23 MST with *"this is the one we need to build to"*, and the authoring
> Standard nine minutes later. Together that is the framing input and the
> structural basis: **the direction was unambiguous.**
>
> What it was not is a decision on the grade/coverage conflict, which §10.1 had
> marked blocking. **A document handover settles what you build to; it does not
> close a named conflict.** Those are closed by an explicit decision, named, or
> not at all — so **ask for one by name and wait.** Declining to close it alone
> was correct, and the inference pointed the right way.

**10.2 · Vault articles carry theoretical values that have been measurably
wrong.** Documented cases in `counterparty-reference-snapshot`: λ_c set to
publication cadence (24h vs ~365d); materialization posture inverted as a
consequence; `operators_invoked` as bare names; missing `payload_hash`,
`model_record` and the per-attribute authority field; a parameter surface
missing `debt_tolerance` and the inert `as_of`. **Assume the same class of error
in the other twenty.** Take framing from the vault; take values from your build.

**10.3 · The `references/` copies are history, not sources.**
`references/CP-SPEC-001_..._v2.md` and
`references/CP-SPEC-001_..._v0-3-restructure.md` are prior drafts. Read them for
audit history; author nothing from them. Same standing as CP-SPEC-001 itself
(§7.1).

**10.4 · Twenty vault articles are on the Q019 form** where §F means
*Manufacture envelope*. Resolve by heading name.

**10.5 · The vault's catalog count is stale** — it says 22 product specs in two
places; the measured figure is **21**, of which **20** declare no Assembly Mode.

---

## 11 · The return path

When your build contradicts an input, **send it back** — the failure this
pipeline exists to prevent is a correction that stalls at the boundary.

- **To the vault:** write into `~/.agent-exchange/<your-agent-id>/outbox/` as
  `<YYYY-MM-DDTHH-MM-SSZ>-<slug>.tmp/` containing `message.md` plus attachments,
  **then rename to drop `.tmp`** — the rename is what publishes it. A message
  left as `.tmp` never arrives, and this has already happened once: dataprep's
  2026-08-28 consumer signal sat unpublished until it was found by hand. State
  what your document **removes**, not only what it adds.
- **To ccf_dataprep:** same channel, their box is `ccf-dataprep`.
- **Your box is `ccf-sdk`** — `/home/parkave/.agent-exchange/ccf-sdk/`, with
  `inbox/`, `outbox/` and `_archive/`. Use that id, not a new one: a duplicate
  under a different id splits you into two agents.

Send back at minimum: any scope-boundary conflict, any λ_c the build disproves,
any element the vault names that the estate cannot supply, and any capability
the estate fails.

---

## 12 · Summary

1. Read the vault article — take **framing**, never values.
2. Pull the data reality from `ccf_dataprep` — **measure**, never assume.
3. Structure to the **Standard v0.3**, templated on **CP-SPEC-000**.
4. **Author the spec first, at `examples/cp-NN-<slug>/spec/`** — it is step one
   of the example project, and it lives with the code that will prove it. Mark
   what only the build can know as `[TBC — this build]`.
5. **▶ Send it to Dave. Stop. Nothing is implemented until he approves it.**
6. Build the example; fill the measured terms; clear every `[TBC]`. A build that
   disproves an approved term is a **deviation** — take it back, do not absorb it.
7. Never write another agent's term. `[TBC — owner]` instead.
8. Every claim discharged by something that runs; every gate made to fail once.
9. Send contradictions back, and **remember the rename**.
10. Work the ladder in order. Complexity is the vault's call, not yours.

``````

</details>

<a id="source-implementation"></a>

<details>
<summary>Implementation walkthrough — refreshed 18 October 2026, SDK v1.0.2</summary>

Path: `05-reference/02-context-product-producer/examples/CP10_RATING_AND_SPREAD_MIGRATION.md`

``````text
# CP-10 — Rating & Spread Migration

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-10-rating-and-spread-migration/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP10_RATING_AND_SPREAD_MIGRATION_ANALYSIS.md) · [HTML reading edition](CP10_RATING_AND_SPREAD_MIGRATION_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-10-rating-and-spread-migration/README.md`  
**Qualified specification:** `examples/cp-10-rating-and-spread-migration/spec/CP-SPEC-010_Rating_And_Spread_Migration.md`  
**Qualified source:** `examples/cp-10-rating-and-spread-migration`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-10-rating-and-spread-migration/spec/CP-SPEC-010_Rating_And_Spread_Migration.md`

Read it before the Python:

| Spec section | What to learn | Where it lands |
|---|---|---|
| §A | decision, consumer, counterfactual, scope | README + acceptance tests |
| §B | contract, request, TTL, policy/perspective | `ccf_config.yaml` + payload |
| §C | sources, identity, ontology, data traps | acquisition + environment/source declarations |
| §D | operators, projection, gates | `acquisition.py`, `deployment.py`, `projection.py`, `produce.py` |
| §E | half-life, Context Debt, materialization | config + assessment code |
| §F | source readiness and limitations | environment/source artifacts + findings |
| §G | acceptance and operational evidence | tests, gates, run evidence |

As you read the code, ask: **which approved spec term is this implementing?**

## Why this example exists

Demonstrates disagreement as useful context: market spread components, instrument-level behavior and internal grades can move differently. It also shows why freshness should read the leading edge of a retained time series rather than average the age of history.

## The question

> Is the observed spread movement issuer-specific deterioration, market-wide movement, or a disagreement that should remain visible beside the internal rating?

## What to understand before you run it

- Serve benchmark, band spread and issuer-specific residual separately; do not flatten them into a headline total.
- The instrument—not the obligor average—is the observation unit for traded spread behavior.
- Different signal classes can have radically different half-lives inside one product.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

Use the qualified/restored demonstration estate and read-only source credentials. This adoption guide uses placeholders even when the source README names a local development host.

```bash
export CCF_CP_10_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_10_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_10_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_10_FLUREE_LEDGER='fibo-v2'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-10-rating-and-spread-migration/spec/` | Migration question, bond-level correction and Gate-1/Gate-2 deviations. |
| `examples/cp-10-rating-and-spread-migration/artifacts/` | Scenarios, source vocabulary and gates. |
| `examples/cp-10-rating-and-spread-migration/acquisition.py` | Bond/rating/market reads and leading-edge selection. |
| `examples/cp-10-rating-and-spread-migration/deployment.py` | Per-class freshness and Debt. |
| `examples/cp-10-rating-and-spread-migration/projection.py` | Three-component spread decomposition. |
| `examples/cp-10-rating-and-spread-migration/run.py` | Three measured scenarios. |

## Run it

```bash
make venv
make -s example-cp-10
make -s example-cp-10 LEI=529900VKCYZW8GZ4WW58
make -s example-cp-10 LEI=549300TRW1LZMDJZAQ78 AS_OF=2025-04-07T00:00:00+00:00 WINDOW_DAYS=48 GRANULARITY=daily
make -s example-cp-10 DEBT_TOLERANCE=0.10
```

An intentional governed refusal may produce a non-zero example process exit. Read the reported refusal before treating non-zero as a broken deployment.

## What you should observe

- Default case shows a market move followed later by a rating action.
- A second obligor shows large bond-specific movement with no rating change.
- A market-wide widening can produce a large headline move but tiny issuer-specific residual and therefore not mean deterioration.
- Lower debt tolerance can govern/withhold the answer.

Exact content addresses, replay references, timestamps and measured figures should be checked against the qualified example's committed tests/transcripts rather than copied from memory.

## How the example works

```
source evidence
  ↓ acquisition
SignalEnvelope(s)
  ↓ governed assembly / L3
GraphView
  ↓ L4 operators
admitted/computed context
  ↓ Π
candidate product
  ↓ L6 gates + Debt fulfillment
served product OR governed refusal
```

This rung's distinctive behavior is described above; the listed source files show the implementation seam where it enters.

## Variations to try

| Purpose | Command | Expected semantic change |
|---|---|---|
| Standing disagreement | `make -s example-cp-10 LEI=529900VKCYZW8GZ4WW58` | Instrument move remains visible beside unchanged grade. |
| Market-wide widening | `make -s example-cp-10 LEI=549300TRW1LZMDJZAQ78 AS_OF=2025-04-07T00:00:00+00:00 WINDOW_DAYS=48 GRANULARITY=daily` | Headline and residual tell different stories. |
| Tighter tolerance | `make -s example-cp-10 DEBT_TOLERANCE=0.10` | Fulfillment/refusal changes. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_10_output.py -q
```

Do not stop at the happy path. The qualified SDK example's gate/sabotage tests are the evidence that the behavior is load-bearing.

## What this example proves

- Instrument-level aggregation can preserve signals obligor averages erase.
- Disagreement between market and rating evidence can be the answer.
- Freshness scoring should use decision-relevant leading observations.

## What it does not prove

- That synthetic/engineered ratings are licensed agency ratings.
- That the example is TRACE data.
- Production market/rating thresholds.

## Spec → code lesson for Cowork

Use CP-10 when a product must preserve competing signal explanations. Cowork should not 'reconcile' disagreement away unless the approved spec defines that reconciliation.

Product-specific values, thresholds, source names and policy must come from the **new approved spec/evidence**, never from this demonstration by convenience.
``````

</details>

