# Wave 12 design — `treasury-liquidity-position` · `fx-post-trade-reconciliation`

**Specs:** `treasury.liquidity-position.v1` · `markets.fx-reconciliation.v1`
Both Tier 3 · Postgres + Fluree, no new store
**Status:** designed 2026-08-21, not yet implemented
**Predecessor:** Wave 11c (consolidation), merged at `c19d126`

Wave 12 pairs the two T3 products that share stores and share nothing else,
except a need for FX reference rates. It is the first wave in the catalog whose
principal risk is **not** fetching wrong.

Every wave through 11c could fail by mis-reading a public source. Wave 12's two
central conditions — an 8bp intraday move and a break that inverts under
`align_clocks` — do not exist in any public source and cannot be fetched at all.
They are engineered, and a wave that hits every count in §F while missing either
one has failed. Neither is catchable by counting rows, so each gets a
recompute-from-loaded-data validator, in the line of `series.py` (Wave 11a) and
`surveillance.py` (Wave 11b).

---

## 0 · Decisions taken

Four were put to the user on 2026-08-21. All four recommendations were accepted.

| # | Decision | Outcome |
|---|---|---|
| D1 | Wave shape | **One branch, three stages** — shared rates, then treasury, then FX recon. The alternative (split 12a/12b) either duplicates the FX rate fetch or makes 12b depend on 12a's tables |
| D2 | Part 43 | **Fetch a real sample.** ~10 trading days of DTCC public SDR FX, used to pattern trade structure and timing. Makes §F's "patterned on real Part 43 records" true rather than asserted |
| D3 | The 8bp move | **Anchor to a real ≥8bp close-to-close day.** The magnitude is observed; only the within-day path is engineered. The provenance label says exactly that |
| D4 | Rate source | **FRED for everything** — SOFR plus percentiles, DGS tenors, H.10 FX. One API, one key already wired, one licensing decision already made in Wave 11a |

**D3 note.** The rejected alternative was injecting a full 8bp into a quiet day.
That would have satisfied §F identically and been materially less honest: both
the size and the timing would be invented, while the §C provenance row would
still read "interpolated from the real daily curve." D3 keeps the interpolation
claim literally true.

---

## 1 · Feasibility, measured before committing

Every number below was measured against live sources on 2026-08-21, before the
design was fixed. Per Wave 11a §1 and Wave 11b §1.

### 1.1 · The FIBO terms are already bound — all of them

Both specs' §C name FIBO classes and say "Bound as of Wave 8." That claim was
checked against `docs/ccf_dataprep_v2.md` rather than trusted:

| Needed by | Terms confirmed present in the binding table |
|---|---|
| FX recon | `Swap`, `SwapLeg`, `SwapConfirmation`, `SwapLifecycleEvent`, `SwapParty`, `SwapTerms`, `UniqueSwapIdentifier`, `hasSwapIdentifier`, `Trade`, `TradeLifecycle`, `TradeLifecycleEvent`, `TradeLifecycleStage`, `SettlementTerms`, `ForeignExchangeRateObservable` |
| Treasury | `ReferenceInterestRate`, `InterestRateBenchmark`, `SpecificProviderInterestRateBenchmark`, `CurrencySpotRate`, `CurrencyForwardRate`, `QuotedExchangeRate`, `ExchangeRateStructure`, `hasQuotedExchangeRate`, `DepositAccount`, `DemandDepositAccount`, `TimeDepositAccount` |

**No new FIBO binding is required by this wave**, and therefore no vault mirror
refresh on the binding table. This is the first wave since 11a that can say so.

> **FALSIFIED 2026-08-22, during Task 9.** This claim was wrong, and the way it
> was wrong is the interesting part. It was checked against **the class names
> the specs' own §C prose mentions** — and every one of those was indeed already
> bound. But the question that matters is not "are the named classes bound", it
> is **"is every type the implementation must assert bound"**, and CLAUDE.md's
> rule 7 (no OWL inference — type explicitly for every role you query against)
> guarantees those two questions have different answers. Typing 200 investment
> positions by instrument required `CommercialPaper`
> (`fibo-sec-dbt-tstd`), `TreasuryBill` (`fibo-sec-dbt-bnd`), and `MutualFund`
> (`fibo-sec-fnd-fnd`) — none named in either spec, all three real, all three
> verified against the EDM Council source and now bound in
> `docs/ccf_dataprep_v2.md`. A fourth term, `ex:RegulatoryPosture`, is a genuine
> non-FIBO extension: FIBO models the instrument and the agreement, not a bank's
> internal jurisdiction/intent posture classification.
>
> The generalisable lesson: **a binding audit run against a spec's prose is not
> a binding audit.** Only the concrete typing the loader performs can answer it,
> which means the honest time to run it is *after* the loader is written, not
> before. §8's definition-of-done item 5 already said the claim must be verified
> at close rather than assumed — this is that verification firing, one task
> earlier than expected and against my own §1.1.
It is also the reason the binding-debt machinery that dominated 11b and 11c is
absent here — but `binding_drift.py`, `orphan_terms.py`, and the confirm script
still run, because "no new terms" is a claim to verify at close, not an
assumption to carry.

`FloatingInterestRate` remains a trap and is already recorded as one in the
binding table's known-bad list: it does not exist in `IND/InterestRates/`. Use
`ReferenceInterestRate`, or `fibo-sec-dbt-bnd:FloatingRateNote` for the
instrument.

### 1.2 · The treasury client set already exists — and it is exactly 15

§F asks for "~15 treasury clients drawn from the anchor obligors." The measured
answer is that Wave 9 already produced them:

```
anchors holding >=1 deposit account:              15
of those, with >=1 XBRL CashAndCashEquivalents fact: 15 / 15
deposit accounts held:                            20, across USD / EUR / GBP / JPY
```

So the treasury client set is **defined, not selected**: it is the set of
anchors that already hold deposits. This is a better outcome than a selection
rule, because it makes the spec's stated prerequisite
(`collateral-and-setoff-coverage`, "deposit accounts") genuinely load-bearing
rather than nominal. Every one of the 15 also carries the XBRL balance-sheet
anchor §C names, so that element joins for all of them, not most.

Cash-fact depth per client runs 22–34 facts; the thinnest client has 22. No
client is short.

### 1.3 · The 8bp condition has seven times the margin it needs

§F asks for **≥ 1** trading day carrying an 8bp intraday move. D3 requires that
day to be a real ≥8bp close-to-close move in the loaded Treasury curve.

Measured across `benchmark_curve` at the 2-year tenor (8,917 rows,
2024-01-02 → 2026-08-18), over every possible 30-consecutive-trading-day window:

```
windows containing >=1 real >=8bp day:   590 of 627
richest 2026 window:  2026-05-11 -> 2026-06-23   7 such days, max 15.0bp
most recent windows:  2026-06-30 -> 2026-08-11   1 such day, exactly 8.0bp
```

**Take the rich window, not the recent one.** The most recent windows satisfy
§F with a single day sitting exactly on the 8.0bp threshold — zero margin, and
one rounding decision away from failing. Wave 11b §D1 is the precedent: an
18-month window met the count and collapsed to one obligor on the condition that
mattered, and the fix was to move the window rather than to accept the margin.

**Selected window: 2026-05-11 → 2026-06-23**, 30 trading days, carrying 7 real
≥8bp days at up to 15bp. The individual days are 2026-05-15 (+9), 05-20 (−9),
05-26 (−12), 06-05 (+12), 06-11 (−8), 06-17 (+15), 06-23 (−8).

**Measured 2026-08-21, after the tick engine was specified — the margin was
needed more than this section claimed.** A day's close-to-close gap does not
guarantee that any *90-minute* window inside it carries 8bp; the bridge has to
put the move there. Simulated over 2,000 seeds per gap size:

```
gap  8bp -> P(max 90-min move >= 8bp) = 47.1%
gap  9bp ->                             65.5%
gap 12bp ->                             94.5%
gap 15bp ->                             99.8%
```

So a window whose only qualifying day sits at exactly 8.0bp — which is what
every recent window offers — satisfies §F **as a coin flip**, not "one rounding
decision away from failing" as this section originally put it. The selected
window's seven days, two of them ≥12bp, give P(all seven miss) = 2.6e-07, and
that ignores the other four tenors contributing ~120 further session-days.

The lesson generalises past this wave: **an `≥ N` floor measured on the input
is not the same as the condition measured on the output.** The gap is real
data; the 90-minute move is a property of the path drawn between the gaps, and
only recomputation from the loaded ticks establishes it. This is precisely why
§6.1 is a recompute gate rather than a row count.

### 1.4 · FRED carries all eleven series

Probed individually, `observation_start=2026-06-01`:

| Series | Role | Obs | Latest |
|---|---|---|---|
| `SOFR` | overnight reference rate | 59 | 3.63 |
| `SOFR1` / `SOFR25` / `SOFR75` / `SOFR99` | published intraday percentiles | 59 each | 3.58 / 3.60 / 3.68 / 3.71 |
| `DEXUSEU` | USD/EUR | 55 | 1.1581 |
| `DEXJPUS` | JPY/USD | 55 | 159.21 |
| `DEXUSUK` | USD/GBP | 55 | 1.3556 |
| `DEXCAUS` | CAD/USD | 55 | 1.3872 |
| `DEXUSAL` | USD/AUD | 55 | 0.7091 |

**H.10 is a WEEKLY release, and that bounds the trade set.** The FX series carry
daily observations but are *published* weekly on Monday, covering through the
prior Friday. Measured 2026-08-21: `fx_reference_rate` extends to 2026-08-14,
which is exactly the correct extent, not a gap. Consequence for
`fx-post-trade-reconciliation`: trade value dates must fall inside the published
window, so the 500 trades span **6 value dates** (2026-08-06 → 08-13) rather
than the 10 days the Part 43 profile was derived from. The profile shapes
*distributions*, not dates, so this costs nothing — but anyone extending the
trade set must move the window rather than assume the rates are simply late.

All eleven live and populated. **`DEXSZUS` was dropped during execution** —
USD/CHF is not one of the six pairs and nothing in the wave consumes it. In its
place, **`EUR/GBP` had to be added and is not fetchable at all**: FRED publishes
no such series (`DEXEUUK` returns "the series does not exist"), so it is derived
as the cross (USD per EUR) / (USD per GBP), provenance `public` with the
derivation recorded per row. Ten series fetched here, five of them FX. Note the FRED convention is inconsistent by
design — `DEXUSEU` is USD-per-EUR while `DEXJPUS` is JPY-per-USD — so the
loader must normalise direction per series explicitly rather than by pattern.
This is the same class of trap as `known-issues.md` §9.6 — the Treasury CSV
header that must be read per file rather than inferred once — and gets the same
treatment: an explicit per-series direction map, not an inferred one.

The SOFR percentiles are fetched but are **reference data, not the tick
anchor** — see §3.1 for why the rejected option C would have mis-used them.

### 1.5 · Part 43 is reachable, and its top-line profile is a finding

DTCC's public SDR requires no auth. Probed for two dates:

```
CFTC_CUMULATIVE_FOREX_2026_08_19.zip   HTTP 200   2,851,343 bytes
CFTC_CUMULATIVE_FOREX_2026_08_18.zip   HTTP 200   2,480,925 bytes
```

Per §8.1's standing lesson — a status code is not evidence of the right content
— the bytes were read, not just the status. The 2026-08-19 file unzips to a
38MB CSV, 69,703 rows, carrying the columns this product needs: `Execution
Timestamp`, `Event timestamp`, `Action type`, `Event type`, `Amendment
indicator`, `Original Dissemination Identifier`, `Notional currency-Leg 1/2`,
`Notional amount-Leg 1/2`.

`Original Dissemination Identifier` is the better-than-expected find: it links a
correction or modification back to the original dissemination, which means the
**amendment-chain shape is observable in real data**, not merely the execution
timing.

Then the top-line pair profile:

```
top pairs: KRW/USD 19,634 · TWD/USD 13,565 · INR/USD 10,236 · BRL/USD 6,447
           IDR/USD 3,621 · PHP/USD 2,917 · CLP/USD 2,107 · COP/USD 1,989
```

**Every one is an NDF pair.** This is structural, not a sampling accident:
CFTC Part 43 covers *swaps*, and deliverable FX forwards and spot are carved out
of the swap definition by Treasury determination. What remains reportable is
non-deliverable forwards, FX options, and currency swaps — which is why the file
is dominated by Asian and Latin American non-deliverable pairs.

The spec's §C describes Part 43 as a source of "publicly disseminated swap and
FX-derivative transactions" and does not note the carve-out. An implementer who
patterns on the whole file gets an all-NDF, Asian-hours dataset that fits no
corporate-treasury narrative and shares no currency with the treasury product's
deposits. **This is a spec-shaped finding and goes to the vault as one**
(§7.3) — it is not a blocker, for the reason in §1.6.

### 1.6 · The majors are in there, and they carry their own profile

The §1.5 top-8 is an aggregate, and this project's standing habit is that
aggregates hide the decision. Whether G10 majors appear *at all* is what picks
the design, and the top-8 cannot answer it. Measured directly:

```
rows carrying a currency pair:  69,273
G10-pair rows:                   3,687  (5.3%)

EUR/USD 1,067 · JPY/USD 661 · AUD/USD 592 · CAD/USD 437
GBP/USD   273 · EUR/GBP 197 · CHF/USD 181 · EUR/JPY 146 · NZD/USD 115 · GBP/JPY 18
```

Not only do the majors appear, the top six are exactly the six §F wants, and the
G10 subset carries its **own** distinct profile — one that the all-pairs
aggregate completely obscures:

| | all pairs | G10 subset |
|---|---|---|
| execution-hour peak (UTC) | 02–05 (Asian) | 10, 14, 15 (London morning, NY open) |
| action mix | NEWT 63,367 · TERM 3,357 · CORR 1,455 · MODI 1,007 · EROR 514 | NEWT 3,039 · TERM 328 · CORR 156 · MODI 108 · EROR 54 |
| amendment links | 6,336 across 6,105 originals | 648 across 593 originals |
| chain lengths | 1×5,914 · 2×171 · 3×10 · 4×8 · 5×1 · 13×1 | 1×560 · 2×26 · 3×1 · 4×5 · 13×1 |

So the design is: **filter to G10, then pattern everything on real records of
the very pairs being generated.** Ten trading days at ~3,700 G10 rows/day gives
roughly 37,000 real records behind 500 generated trades — a ~74:1 backing ratio.

The G10 chain-length distribution also settles §F's amendment condition before
a line is written: §F wants ≥10 trades with chains and ≥3 with two or more. The
real one-day G10 distribution has 593 chained originals of which 33 carry two or
more. Scaled to 500 trades, both floors are comfortably inside the observed
shape rather than imposed on it.

**One caveat carried forward.** `Product name` is present in the schema and
**empty on every one of the 69,703 rows**. Do not build anything on it, and do
not report its emptiness as an absence of products — it is an unpopulated
column, which is a different fact.

### 1.7 · The Wave 9 deposit table is safe to extend

Wave 12 grows `deposit_account` from 20 rows to ~120, which makes it a
two-writer table. §10.5's lesson makes that worth checking rather than assuming.
`loaders/load_collateral_wave9.py` contains **no `DELETE`, no `TRUNCATE`** — it
upserts. Extending the table in place is safe, and Wave 12's own loader keys
idempotency on `account_id` with a distinct prefix.

---

## 2 · Sources and their provenance

### 2.1 · Nothing already loaded is re-fetched

| Asset | Rows | Origin | Wave 12 use |
|---|---|---|---|
| `benchmark_curve` | 8,917 | Treasury.gov daily par yield | Tick-series anchor. **Read-only** |
| `market_oas_series` | 5 series | FRED BAML OAS | Investment-position pricing context. **Read-only** |
| `deposit_account` | 20 | Wave 9 | Extended to ~120, never rewritten |
| `legal_entity` | 50 | Waves 1–6 | 15 become treasury clients; counterparties for FX trades |
| `financial_fact` | — | XBRL companyfacts | Balance-sheet cash anchor, §C `public` |

Per `known-issues.md` §9.6, any further Treasury CSV work reads the header
**per file** — the par curve gained a `1.5 Month` column mid-window in 2025.
Wave 12 only reads the loaded table, so §9.6 does not bind here, but it binds
the moment anyone re-fetches.

### 2.2 · New public fetches — two

**FRED** (`generators/fetch_fred_rates.py`) — the eleven series of §1.4, cached
to `sources/fred/` with retrieval dates. Provenance `public`, source and
retrieval date recorded per row. The Wave 11a FRED licensing decision carries
over unchanged.

**DTCC public SDR** (`generators/fetch_part43.py`) — ten trading days of
`CFTC_CUMULATIVE_FOREX_<date>.zip`, cached to `sources/part43/`. Only the
**derived distributions** are used downstream; individual real trades are never
loaded as trades. Provenance on the derived profile is `public`; every generated
trade is `synthetic — internal` — an invented instance, bank-internal by
nature (§C: "Internal trade records per system"), patterned on the public
shape but not itself deliberately engineered toward a demonstration.

That distinction is the whole point and must survive into the loaded rows: the
*shape* is public and cited, the *instances* are invented (and, per §2.3
below, invented-because-internal rather than invented-toward-a-condition). A
row that blurred either distinction would be exactly the misrepresentation
§C warns about.

### 2.3 · The three provenance classes, per element

| Element | Class | Store |
|---|---|---|
| SOFR, SOFR percentiles, DGS tenors, H.10 FX | `public` | Postgres |
| Treasury par curve (reused) | `public` | Postgres |
| XBRL cash-and-equivalents | `public` | Postgres |
| Part 43 derived distributions (pair mix, hour profile, action mix, chain lengths) | `public` | Postgres |
| Deposit balances, investment positions | `synthetic — internal` | Postgres |
| Concentration limits, permitted-instrument lists, materiality thresholds | `synthetic — internal` | Postgres |
| `heldAt` / `concentratedIn` edges | `synthetic — internal` | Fluree |
| Regulatory posture overlay | `synthetic — internal` | Fluree |
| Internal trade records, system observations | `synthetic — internal` | Postgres |
| `observedIn` / `amends` edges, clock offsets | `synthetic — internal` | Fluree |
| **Intraday tick series** | **`synthetic — engineered`** | Postgres |
| **The stale signal** | **`synthetic — engineered`** | Postgres |
| **Timing-artefact breaks** | **`synthetic — engineered`** | Fluree |
| **Genuine breaks** | **`synthetic — engineered`** | Postgres |

---

## 3 · The engineered conditions

Four conditions in this wave cannot be counted into existence. Each is stated
here with the mechanism that produces it and the recomputation that proves it.

### 3.1 · The intraday tick series, and the 8bp move

**Mechanism.** For each of the 30 trading days in the §1.3 window, the day's
path opens at the prior session's published close and terminates at that day's
published close, both taken from `benchmark_curve` unmodified. Between them, a
Brownian bridge at 5-minute granularity over a 6.5-hour session — 78 ticks per
day, per series. The bridge is seeded deterministically so reloads reproduce.

Because both endpoints are real, the day-over-day move is real. On the seven
§1.3 days the endpoint gap is already ≥8bp, so a path connecting them **must**
traverse ≥8bp within the session. The condition is produced by the real data's
own geometry rather than injected.

**Why not the SOFR percentiles.** The rejected option would have shaped
within-day dispersion from SOFR's published 1st/25th/75th/99th percentiles.
Those are real intraday dispersion — but of the overnight repo rate, not of the
Treasury par curve this product quotes. Using them would have imported real
numbers into the wrong instrument, which is a subtler error than inventing and
harder to spot later. The percentiles are still loaded, as reference data.

**What the validator recomputes.** Not "is there a day flagged 8bp." The spec's
counterfactual is specific — *"the market has moved eight basis points in the
last ninety minutes"* — so the check is a **maximum 90-minute rolling move
computed from the loaded ticks**, asserted ≥8bp on at least one day. It also
asserts tick spacing is exactly 5 minutes with no gaps, and that every day's
first and last tick equal the published values in `benchmark_curve`. That last
check is what stops the series drifting off its anchor and quietly becoming
fiction.

### 3.2 · The concentration breach

**Mechanism.** ≥2 clients are positioned so that a naively optimal allocation —
all available cash into the highest-yielding permitted counterparty — exceeds
their `concentration_limit`. The limit is not set after the fact to make the
breach true; positions and limits are generated independently and the breach is
then confirmed by computation.

**What the validator recomputes.** It builds the naive allocation itself from
loaded positions, permitted-instrument lists, and limits, and asserts ≥2 clients
breach. A stored `breaches=true` flag proves nothing and is not consulted.

### 3.3 · The stale signal

**Mechanism.** One contributing signal carries an observation timestamp
deliberately older than the 15-minute `max_staleness` bound, so a consumer's
staleness gate fires and fail-closed is observed rather than described.

**What the validator recomputes.** Asserts ≥1 loaded signal whose observation
timestamp is older than the bound, and — the part that matters — that the
signal is otherwise **complete and well-formed**. A stale signal that is also
malformed would fail the gate for the wrong reason and prove nothing about
staleness.

### 3.4 · The break that inverts under `align_clocks`

This is the product's entire argument and the single hardest thing in the wave.

**Mechanism.** Three systems — trading, settlement, risk — each carry a recorded
clock offset. At least one trade is constructed so that:

- compared on **raw current values**, the variance between two systems exceeds
  the materiality threshold and classifies as `genuine`;
- projected to a **common as-of point** using each system's recorded offset and
  its amendment chain, the variance collapses below threshold and reclassifies
  as `timing`.

And at least one *other* break is constructed to survive alignment as genuine,
so the product is not merely explaining everything away.

**What the validator recomputes.** It performs both computations from loaded
data — raw comparison and clock-aligned comparison — and asserts the flip
occurs for ≥1 break and does *not* occur for ≥1 other. It additionally asserts
the spec's own §D gate: **variance decomposition closure**, timing-attributable
plus residual equals total. A gap there means a system's observation time was
dropped from the alignment, which is precisely the defect that would make the
inversion accidental rather than constructed.

---

## 4 · Data model

### 4.1 · Store partition

Single-writer discipline per CLAUDE.md. Fluree nodes carry `lei`/identifier plus
a display label; all attributes resolve from Postgres.

**Postgres — new tables**

| Table | Owns | Approx rows |
|---|---|---|
| `reference_rate` | SOFR + percentiles + DGS tenors | 10,539 (measured) |
| `fx_reference_rate` | H.10 pairs (5 fetched + EUR/GBP derived), every value date | 3,942 (measured) |
| `treasury_client` | the 15, with mandate reference | 15 |
| `investment_position` | MMF / CP / T-bill, laddered maturities | ~200 |
| `concentration_limit` | per client, per counterparty | ~60 |
| `permitted_instrument` | per client mandate | ~75 |
| `intraday_tick` | 5-min ticks, 30 days | ~11,700 |
| `fx_trade` | the 500, 6 pairs | 500 |
| `system_trade_record` | per-system value per trade | ~1,500 |
| `break_record` | ~60, classified | ~60 |
| `materiality_threshold` | ops policy | ~6 |
| `part43_profile` | derived public distributions | ~50 |

All rate spans match `benchmark_curve` (2024-01-02 onward, ~665 trading days),
so the three rate tables share one calendar rather than three. `reference_rate`
is 16 series — SOFR, 4 percentiles, 11 DGS tenors — at ~659 dates;
`fx_reference_rate` is 6 pairs at the same dates.

**Corrected 2026-08-21 during execution.** This read "19 series — SOFR, 4
percentiles, **14** DGS tenors". 14 is `benchmark_curve`'s tenor count
(Treasury.gov publishes 1.5-month, 2-month, and 4-month points); FRED's DGS
constant-maturity family has **11**. Conflating the two produced both the wrong
series count and the wrong row estimate. Measured actuals after loading: 10,539
rate observations across 16 series, 3,942 FX across 6 pairs.

**Postgres — extended**

`deposit_account` 20 → ~120, distinct `account_id` prefix, upsert-keyed.

**Fluree — new assertions**

`heldAt`, `concentratedIn` (position → counterparty); regulatory posture overlay,
time-versioned; `observedIn` (trade → system observation); `amends` (amendment
chains); system observation timestamps and clock offsets; the timing-artefact
break assertions.

### 4.2 · Explicit typing, no inference

Per CLAUDE.md rule 7, Fluree runs without reasoning. Every entity is typed
explicitly for every role it must be queried against — a `Swap` that must also
answer a `Trade` query carries both types, asserted, not inferred.

### 4.3 · Correlation keys

Treasury joins on `LEI` (client) and instrument identifier (position). FX recon
joins on `trade_id` internally, counterparty `LEI`, and currency-pair plus value
date for netting. Every FX value date must have a row in `fx_reference_rate` —
§F states this as a condition and it is checked, not assumed.

**Pair naming.** Part 43 emits legs unordered, so the probe's sorted form reads
`JPY/USD` where market convention is `USD/JPY`. Normalisation to market
convention happens once, at the fetch boundary, and the convention is recorded
in `docs/ccf_dataprep_v2.md`. A convention applied in two places eventually
disagrees with itself.

---

## 5 · Pipeline

Load order per CLAUDE.md: ontology → crosswalk → entities → relationships →
temporal → documents → departmental. Wave 12 touches entities, relationships,
and temporal.

**Stage 1 — shared**
1. `generators/fetch_fred_rates.py` → `sources/fred/`
2. `loaders/load_rates_wave12.py` → `reference_rate`, `fx_reference_rate`

**Stage 2 — treasury**
3. `generators/generate_treasury.py` → clients, deposits, positions, limits, mandates
4. `generators/generate_ticks.py` → the interpolated series
5. `loaders/load_postgres_wave12_treasury.py`
6. `loaders/load_fluree_wave12_treasury.py` → `heldAt`, `concentratedIn`, posture overlay

**Stage 3 — FX recon**
7. `generators/fetch_part43.py` → `sources/part43/`, derived profile
8. `generators/generate_fx_trades.py` → trades, system records, offsets, breaks, chains
9. `loaders/load_postgres_wave12_fx.py`
10. `loaders/load_fluree_wave12_fx.py` → `observedIn`, `amends`, offsets, timing breaks

All loaders idempotent and re-runnable. Every Fluree reconcile scopes retraction
**by subject, never by predicate** — §10.5, non-negotiable.

---

## 6 · Validation

### 6.1 · `validators/intraday.py` — new gate

Recomputes from loaded data, never from a generator's flag:

| Check | Asserts |
|---|---|
| Rolling 90-minute move | ≥8bp on ≥1 day, computed from `intraday_tick` |
| Anchor fidelity | every day's first/last tick equals `benchmark_curve` |
| Tick spacing | exactly 5 minutes, no gaps, 78 ticks/session |
| Naive allocation | ≥2 clients breach their limit, allocation recomputed |
| Staleness | ≥1 signal older than 15m, otherwise well-formed |

### 6.2 · `validators/reconcile.py` — new gate

| Check | Asserts |
|---|---|
| Inversion | ≥1 break classifies `genuine` raw and `timing` aligned |
| Survivor | ≥1 break classifies `genuine` under both |
| Decomposition closure | timing + residual = total variance, per break |
| Break mix | ~⅔ timing / ⅓ genuine across ~60 |
| Chain shape | ≥10 trades chained, ≥3 with two or more |
| Rate coverage | every value date has an `fx_reference_rate` row |

### 6.3 · Existing gates, all re-run at close

`partition.py` · `conditions.py` (extended with both §F sets) ·
`orphan_terms.py` · `binding_drift.py` · `artifact_reproduces_store.py` ·
`series.py` and `surveillance.py` (regression — Waves 11a/11b must not move).

`orphan_terms.py` is new in 11c and easy to skip. It catches Fluree predicates
whose writer was deleted, which `artifact_reproduces_store.py` structurally
cannot. Run it.

---

## 7 · Risks carried into implementation

### 7.1 · The dormant predicate-scoped reconcile in `load_fluree_wave10.py`

§10.5 records that Wave 11b turned `load_fluree_wave11a.py --reconcile` into a
silent data-loss hazard by asserting more edges on a predicate that loader
believed it owned outright. The same pattern is **still present, dormant**, in
`load_fluree_wave10.py` across six predicates.

Wave 12 writes new predicates, so it should not fire. "Should not" is how Wave
11b's hazard read the day before it did. Verify explicitly during
implementation; do not carry the assumption.

### 7.2 · Two writers on `deposit_account`

§1.7 measured this safe — Wave 9 upserts and never deletes. The risk is not
today's code but tomorrow's: anyone adding a reconcile to
`load_collateral_wave9.py` would silently delete Wave 12's 100 rows. Record the
two-writer fact in `docs/ccf_dataprep_v2.md` so the next author sees it before
writing the DELETE, not after.

### 7.3 · The Part 43 NDF carve-out is a vault punch-list item

§1.5's finding — that Part 43 structurally cannot supply deliverable major-pair
FX, because deliverable FX is carved out of the swap definition — belongs in the
spec, whose §C presents Part 43 without the caveat. Same shape as Wave 11a's
TRACE finding.

Goes out through `~/.agent-exchange/ccf-dataprep/outbox/`, timestamp with
**hyphens, never colons**. Four punch lists (Waves 10, 11a, 11b, 11c) are
already uncollected — **do not re-send them**; this is a fifth, not a resend.

### 7.4 · FRED's inconsistent rate direction

§1.4: `DEXUSEU` is USD-per-EUR, `DEXJPUS` is JPY-per-USD. An inferred direction
map would be right for some series and silently inverted for others, producing
FX revaluations wrong by a reciprocal — large, plausible, and not obviously
wrong at a glance. Explicit per-series map, unit-tested against a known value.

### 7.5 · The inversion is constructible and still easy to get wrong

§3.4's break must invert for the *right reason*. A break that flips because the
materiality threshold happens to sit between two arbitrary numbers is not the
product's argument; it is a coincidence wearing its costume. The decomposition
closure check in §6.2 is what distinguishes them, which is why it is a gate
rather than a diagnostic.

---

## 8 · Definition of done

Per CLAUDE.md, all five must hold, for both products:

1. Every §C element exists, in the store the catalog names, with its provenance
   class recorded.
2. Every correlation key the catalog implies actually joins.
3. Every §F `≥ N` condition is satisfiable by a real query against loaded data —
   including the four of §3, each proven by recomputation rather than count.
4. Single-writer discipline holds; no element duplicated into a store that does
   not own it.
5. No new FIBO term is introduced unbound. §1.1 expects zero new terms; that is
   a claim to verify at close, not an assumption to carry.
