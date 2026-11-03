# Wave 11a design — `rating-and-spread-migration`

**Written:** 2026-08-19 · **Status:** approved, not yet implemented
**Spec:** `credit-risk.rating-migration.v1`, tier 3 · **Stores:** Postgres + Fluree

> Re-read from the vault on 2026-08-19, per the standing rule that specs are
> patched in place.

---

## 0 · Decisions taken

| # | Question | Decision |
|---|---|---|
| 1 | Per-CUSIP TRACE history is licensed and unreachable. How is the spread leg built? | **Real index base + engineered idiosyncratic spread** |
| 2 | Wave 11 carries two dependent products. One wave or two? | **Split.** 11a is this product; 11b is `credit-surveillance-early-warning` |

**On the split.** `credit-surveillance-early-warning` names this product as a
prerequisite and inherits its spread series, so the two are sequential rather
than parallel and splitting costs no wall-clock. Wave 10 was one product and ran
11 tasks, 21 commits, two fix rounds and a whole-branch review; both of these
together would be visibly larger, and a ~20-task plan is where Wave 10's
thirteen reference-code defects would have compounded rather than being caught
one task at a time. The split also lets 11b's plan be written against 11a's
**actually loaded data** rather than against predictions about it.

---

## 1 · Feasibility, measured before committing

Wave 9 established the pattern and Wave 10 reinforced it: probe the named
source, and if it does not support the §C row, say so and take a sanctioned
fallback. Everything below was probed on 2026-08-19.

### 1.1 · FINRA TRACE is NOT reachable — the §C row cannot be satisfied as written

§C names FINRA TRACE for "corporate bond transaction prices and yields",
described as "publicly disseminated (delayed)". That description is true and
misleading in the same breath. Dissemination means prints hit the tape for
anyone with a terminal. It does not mean the historical series is downloadable
in bulk without a licence — and §F needs 60 instruments × 24 months, which is
bulk history.

Probed FINRA's free Query API:

| Endpoint | Result |
|---|---|
| `api.finra.org/data/group/{otcMarket,fixedIncomeMarket,traceMarket,...}` | **404** on every group root |
| `.../otcMarket/name/{traceCorporateBond,corporateBond,traceBond}` | **404** |
| `.../otcMarket/name/weeklySummary` | **200** — and it is **equity ATS volume** |

The one endpoint that returns data carries rows like `BRKR, Bruker Corporation
Common Stock, JPBX, ... totalWeeklyTradeCount, totalWeeklyShareQuantity`. Equity
symbols, share counts, no prices, no yields, no bonds.

**Bond-level TRACE history is FINRA's licensed product.** This is the UCC-1
situation from Wave 9 repeating: a §C row naming a source that is real, correct
in principle, and not freely obtainable in the form the envelope requires.

**Worth sending to the vault as a spec finding.** §C already contains exactly
the right reasoning for licensed data — it names agency ratings from S&P,
Moody's and Fitch as licensed, instructs treating an "agency rating feed" as
unavailable rather than an integration to build, and offers three substitute
legs. That reasoning is sound and simply pointed at the wrong source. TRACE
needs the same treatment.

### 1.2 · XBRL cannot substitute for instrument reference data

§C's fallback for instrument reference is "TRACE reference data; EDGAR
debt-security registrations". Probed `companyfacts` for the four anchors with
the largest filing histories:

| CIK | us-gaap tags | Debt-instrument tags present |
|---|---|---|
| 1059262 | 452 | none |
| 1091667 | 504 | `DebtInstrumentFaceAmount` — **121 facts** |
| 1094831 | 696 | `DebtInstrumentInterestRate{Effective,Stated}Percentage` — **1 fact, 2012** |
| 1632970 | 410 | `DebtInstrumentInterestRateEffectivePercentage` — **1 fact, 2016** |

Two problems, either of which is disqualifying. The coverage is wildly uneven —
121 facts for one filer, a single 2012 fact for another. And **`companyfacts`
flattens away the dimensional context**: XBRL debt-instrument facts are
qualified by an axis identifying *which* instrument, and the flattened API drops
it. So Charter's 121 face-amount facts cannot be attributed to individual
instruments at all.

Instrument reference is therefore **engineered**, not fetched.

### 1.3 · What IS reachable, and verified

| Source | Status |
|---|---|
| **Treasury par yield curve** | ✅ free CSV, daily, full tenor grid (1 Mo → 30 Yr) |
| **FRED ICE BofA OAS by rating band** | ✅ five series verified, **794 daily rows each**, current to 2026-08-18 |
| **8-K Item 2.03** debt issuance | ✅ **all 50 anchors** have at least one; 790 filings total |
| **8-K rating actions** | ✅ **5 anchors, 14 filings** — see §1.4 |
| Obligors with reported long-term debt | ✅ **48 of 50** in XBRL |

The five verified FRED series, with their values on 2026-08-18 — note they form
a real credit curve, monotonic by rating, which is the point:

| Series | Band | OAS |
|---|---|---|
| `BAMLC0A2CAA` | AA | 0.60 |
| `BAMLC0A3CA` | A | 0.69 |
| `BAMLC0A4CBBB` | BBB | 1.00 |
| `BAMLH0A1HYBB` | BB | 1.63 |
| `BAMLH0A2HYB` | B | 2.94 |

AAA is deliberately excluded: this cast is mid-market and leveraged, and no
anchor in it would price at AAA. (`BAMLC0A1CAAAEY` was also probed and works,
but it is the effective-**yield** variant rather than OAS — mixing the two would
be a units error.)

### 1.4 · The one condition that was not obviously satisfiable — and a lesson

§F wants **≥ 1 obligor with a rating action disclosed in a real 8-K**. Unlike
Item 2.04, rating actions surface as Item 8.01 prose with no metadata flag to
select on, so this was flagged at design time as unproven.

EDGAR full-text search, **first page only**, found **1** anchor. That would have
committed this spec to a zero-margin condition.

The same sweep **with paging** found **5 anchors across 14 filings**:

| Obligor | Filings |
|---|---|
| AVIS BUDGET GROUP | 5 |
| INDEPENDENCE REALTY TRUST | 5 |
| Peakstone Realty Trust | 2 |
| Vertiv Holdings | 1 |
| GRIFFON CORP | 1 |

The floor is cleared five times over. **The lesson is the gap between the two
numbers**: 1 versus 5 was an artifact of pagination, not of the data, and a
probe that stops at the first page produces a confident wrong answer. The plan
must page.

---

## 2 · The three-leg spread model

With TRACE unavailable, spread is composed rather than fetched:

```
yield(instrument, t) = benchmark(tenor, t)            Treasury par curve   [public]
                     + oas(rating_band, t)            FRED ICE BofA        [public]
                     + idiosyncratic(instrument, t)   engineered           [engineered]

spread(instrument, t) = yield(instrument, t) - benchmark(tenor, t)
```

**The market factor is genuinely public and genuinely moves.** The 2024–2026
credit cycle appears in the data because it is the real index, not a curve
someone drew. Only the instrument-specific level is invented.

**Provenance splits per element, not per row.** `spread_observation` stores the
market and idiosyncratic components in separate columns so the public and
engineered parts stay separable by query — a consumer can always ask what was
observed and what was built. The estate already does this for collateral, where
existence may be `public` while every valuation is `synthetic — internal`.

**KNOWN SIMPLIFICATION — `rating_band` is fixed at generation and never
follows a grade migration.** `oas(rating_band, t)` above reads
`debt_instrument.rating_band`, assigned once when the instrument is generated.
`generate_grades.py` then lets an obligor's grade drift across band boundaries
over the same window. Both files implement this design faithfully; the design
itself is what does not close the loop. Measured on the loaded data — 3 of 30
obligors, 6 of 60 instruments:

| LEI | market band pinned at | grade band reached | duration off-band | unreflected OAS gap |
|---|---|---|---|---|
| `5493003QENHHS261UR94` | BB | B | 182 days | ~122 bp |
| `5493004HBTOTE9DI9P12` | BBB | BB | 145 days | ~75 bp |
| `549300EQD0ZXRSMG3549` | B | BB | 92 days | ~122 bp |

**Ruled: document, do not reprice.** Re-banding on the migration date would step
the market leg ~122bp discontinuously — an unlabelled artifact as bad as the one
it replaces, since real repricing is gradual and anticipatory. Gliding between
the two band curves is the honest fix, but a glided value is neither index: it is
a synthetic interpolation between two real series, which breaks this section's
own "provenance splits per element" rule and needs either a fourth column or a
provenance downgrade during transition windows. That is a design decision for
Wave 11b, whose subject is spread-versus-grade signal — not a patch on 11a.
Carried as **the first open question for Wave 11b planning**; see
`docs/known-issues.md` §9.10.

**Benchmark matching is by tenor, never by calendar proximity**, per §D step 4.
An instrument with 4.2 years to maturity is matched against the interpolated
4-to-5-year point on that day's curve, not against whichever tenor happens to be
nearest in the file.

---

## 3 · Data model

Per §C: Postgres owns observations and policy (`E`, `P`); Fluree owns the event
and assertion history (`R`, `T`).

### 3.1 · New Postgres tables

| Table | Provenance | Holds |
|---|---|---|
| `debt_instrument` | `synthetic — engineered` | instrument id, issuer LEI, coupon, maturity, face amount, rating band, seniority; issuance date anchored to a real Item 2.03 filing where one exists |
| `spread_observation` | **split** | instrument, date, `benchmark_bp` (public), `market_oas_bp` (public), `idiosyncratic_bp` (engineered), `spread_bp` (computed), `yield_bp` (computed) |
| `benchmark_curve` | `public` | date × tenor → par yield, from Treasury |
| `market_oas_series` | `public` | date × rating band → OAS, from FRED, with the series id recorded |
| `rating_scale` | `synthetic — internal` | internal grade ↔ notch mapping, **policy-versioned** |
| `divergence_threshold` | `synthetic — internal` | by sector, policy-versioned |

`rating_scale` carrying a `policy_version` is not decoration. §D step 2 is
explicit that a recalibration changes every notch-equivalent figure the product
has ever produced, so lineage must record which mapping applied.

**Instrument identifiers are engineered and must look it.** Format:
`syn-i-<6 hex>`, mirroring Wave 10's `syn-p-` person keys. A real CUSIP is nine
alphanumeric characters with a check digit; this shares no property with one and
cannot be looked up anywhere. Per the settled rule that synthetic identifiers
take a visibly distinct format, a reader must never be able to mistake one for a
real security identifier.

### 3.2 · Fluree — events and the assertion history

Node types, **all bound in Wave 8**, no new bindings required:

| Term | IRI |
|---|---|
| `DebtInstrument` | `fibo-fbc-fi-fi:DebtInstrument` |
| `CorporateBond` | `fibo-sec-dbt-bnd:CorporateBond` |
| `Bond` | `fibo-sec-dbt-bnd:Bond` |
| `FloatingRateNote` | `fibo-sec-dbt-bnd:FloatingRateNote` |
| `isSubordinated` / `isSubordinatedTo` | `fibo-sec-dbt-dbti:` |

**Terms still to verify** against the EDM Council source before anything
generates against them: `issuedBy` (§B names it; no FIBO binding exists in the
contract yet), and whether FIBO carries classes for a credit grade or a market
observation. Bind upstream, verify, generate, then flag the vault mirror — the
project rule exists because generating against an invented local name validates
cleanly here and cannot be consumed downstream.

### 3.3 · The grade history is a supersession chain, and Wave 5 already built the vocabulary

§D step 3 is the reason this product needs a ledger: *"the migration IS the
supersession chain, which is why this product needs a ledger rather than a
current-state table."*

Wave 5's bitemporal vocabulary is already in the estate and partly used:

| Predicate | Current assertions |
|---|---|
| `ex:validFrom` | 223 |
| `ex:assertedAt` | 29 |
| `ex:supersededBy` | **0 — declared, never populated** |

`ex:supersededBy` is a declared-but-empty predicate, the same shape as
`fibo-fnd-rel-rel:controls` before Wave 10's follow-up closed it. Wave 11a
populates it as a matter of course: every rerating supersedes the grade it
replaces, and the chain is the product's output.

**Grades are a step function.** Each assertion carries an exact `validFrom`, and
the superseded assertion is retained rather than overwritten. §D step 5's
instruction — *resample, do not interpolate across a rating action* — is an
assembly-time rule, but it is only satisfiable if the data carries exact
effective dates rather than smoothed ones, which is a manufacture requirement.

---

## 4 · Pipeline

Each step is a separate, re-runnable, `--dry-run`-capable script.

| # | Script | Does |
|---|---|---|
| 1 | `generators/fetch_treasury_curve.py` | Treasury par yield curve, 24 months, all tenors |
| 2 | `generators/fetch_market_oas.py` | the five FRED OAS series, recording series ids |
| 3 | `generators/fetch_rating_actions.py` | **paged** EDGAR FTS sweep for rating-action 8-Ks, then fetch the matches |
| 4 | `generators/fetch_debt_issuance.py` | Item 2.03 filings by `items` metadata — free selection, machinery exists from Wave 10 |
| 5 | `generators/generate_instruments.py` | ~60 instruments, laddered, anchored to real issuance dates |
| 6 | `generators/generate_spreads.py` | compose the three legs; place the divergence cases and the sparse series |
| 7 | `generators/generate_grades.py` | quarterly history + ≥4 off-cycle reratings, as a supersession chain |
| 8 | `loaders/load_postgres_wave11a.py` | six tables |
| 9 | `loaders/load_fluree_wave11a.py` | instrument nodes, `issuedBy`, grade assertions, events — **with `--reconcile` from the start**, per Wave 10's lesson |

---

## 5 · The §F conditions, and how each is created

| # | Condition | Mechanism | Class |
|---|---|---|---|
| 1 | ~30 obligors with publicly traded debt | **the 30 largest by most-recent reported `LongTermDebt` in XBRL**, restricted to obligors that also have >= 1 Item 2.03 8-K. Deterministic, public, and it puts the obligors with the most debt in the product about debt. Ties broken by LEI ascending. The 5 rating-action anchors are force-included regardless of rank, so condition 6 cannot be lost to a ranking change | `public` selection |
| 2 | ~60 instruments, laddered by maturity | generated | `synthetic — engineered` |
| 3 | 24 months observations + matched curve | real Treasury + real FRED, daily | `public` |
| 4 | Quarterly grades, **≥ 4 off-cycle reratings** | generated, so the series is not mechanically regular | `synthetic — internal` |
| 5 | **≥ 3 divergence cases, ≥ 1 confirmed later** | engineered into the idiosyncratic component | `synthetic — engineered` |
| 6 | ≥ 1 rating action in a real 8-K | **5 anchors, 14 filings available** | `public` |
| 7 | **≥ 2 thin instruments with observation gaps** | real gaps, deliberately not filled | `synthetic — engineered` |

### 5.1 · The two conditions counting cannot fake

**#5 — divergence.** The product's central claim is that the market anticipates
the grade. A divergence case is a period where the spread widens materially
while the internal grade does not move, and the ≥ 1 "confirmed later" case is
one where the grade subsequently moves in the direction the spread already
indicated. Neither is a row count: both are relationships between two series
over time, and the validator must compute them from the loaded data rather than
read a flag the generator set.

**#7 — sparse series.** Thin instruments must have genuine **gaps**, not
interpolated values. A validator that counts observations would pass a fully
interpolated series; the check must assert that observation dates are actually
missing for those instruments, and that nothing filled them.

---

## 6 · Validation gates

- **`validators/partition.py`** — new `ex:` types registered; instrument and
  grade attributes must not leak into Fluree.
- **`validators/conditions.py`** — a `rating-and-spread-migration` section with
  the seven §F checks, of which #5 and #7 are computed from the series.
- **New `validators/series.py`** — the divergence and sparsity proofs, computed
  from loaded data. Named separately because they are the two the count would
  fake, exactly as `traversal.py` was split out in Wave 10.
- **`validators/artifact_reproduces_store.py`** — extended to the new artifacts.
  This validator found a real divergence on its first run in Wave 10; every new
  artifact belongs in it.
- **Full suite must stay green.** `conditions.py` reached 72 passed / 0 failed
  for the first time on 2026-08-19. A new red check means a real regression now,
  which is the property that made closing the control-edge gap worth doing.

---

## 7 · Risks carried into implementation

1. **The idiosyncratic component must not swamp the market factor.** If the
   engineered spread dominates, the public index becomes decoration and the
   product's claim rests on invented data after all. Made measurable: across all
   observations **outside** an engineered divergence window, the median
   `|idiosyncratic_bp|` must be **no more than 40% of the median `market_oas_bp`**.
   Inside a divergence window it may exceed that — widening the idiosyncratic
   component *is* how a divergence is manufactured — so the check excludes those
   windows by date rather than being relaxed. `validators/series.py` asserts the
   ratio rather than the generator claiming it.
2. **Tenor matching is easy to get subtly wrong.** Matching by calendar
   proximity instead of tenor is explicitly forbidden by §D and would produce
   plausible, wrong spreads — the silent class of defect this project keeps
   finding.
3. **`issuedBy` and the grade/observation classes are unbound.** Verify against
   the EDM Council source first; mint `ex:` only where FIBO genuinely lacks a
   term, and record which.
4. **Rating-action extraction is prose.** The paged FTS sweep finds the
   *filings*; identifying the action within them is a bounded search, and
   candidates that cannot be confirmed drop to `context_debt` rather than being
   forced.
5. **Vault drift.** The TRACE finding, any new `ex:` terms, and
   `supersededBy` moving from declared to materialized all go out through the
   exchange when the wave lands.

---

## 8 · Out of scope for Wave 11a

- **`credit-surveillance-early-warning`** — Wave 11b, planned separately against
  this wave's loaded data.
- **Assembly-time behaviour from §D** — resampling, notch-equivalent
  computation, series-cadence disclosure, the empty-operator guard. Read to
  learn what the data must support, never implemented.
- **Agency ratings.** Licensed and not redistributable. §C is explicit and this
  design does not attempt a workaround.
