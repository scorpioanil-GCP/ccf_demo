---
product: markets.fx-reconciliation.v1
standard: v0-3
sdk_spec: cp-12
tier: 3
cost_band: "×2–4"
assembly_mode: 1
capability_classes: [relational, bitemporal-ledger, graph-traversal, in-memory]
prerequisites: [counterparty-reference-snapshot]
build_order: 12
lifecycle: draft
accountable_owner: markets-operations-product-engineering
review_cadence: at every Control Plane change to the materiality thresholds or the
  recorded clock offsets; and no less than annually
topic: context-products
title: FX Post-Trade Reconciliation — Context Product Specification
generated: '2026-09-12'
---

# FX Post-Trade Reconciliation — Context Product Specification

**`CP-SPEC-012` · Tier 3 · `markets.fx-reconciliation.v1`**
**PostgreSQL for the trades, the system values and the rate series · Fluree for the observation instants, the clock offsets and the amendment chains**

> **Why do two systems disagree about the same trade?**
>
> The answer depends on **whose clock you reconstruct against** — and on not
> counting one disagreement twice.

## 0 · What this document is

A build specification for the engineer who will assemble this Context Product
from the markets data estate. **Every figure below was measured against the live
estate on 2026-09-12 before this document was written**, and the query that
produced it is reproducible.

### 0.1 The governing question

> **Can a Context Product tell a timing artefact from a genuine error, when the
> two are indistinguishable by magnitude — and can it do so without inventing
> breaks that do not exist?**

Measured: the designed timing breaks span **4.08–8.00 pips** and the designed
genuine breaks span **4.01–7.93 pips**. **The ranges overlap almost completely.**
Nothing about the size of a discrepancy says which kind it is. What separates
them is *when each system observed*, corrected for *how wrong each system's clock
is* — and that is the entire product.

### 0.2 Placeholder discipline

No `[TBC]` except the p95 budgets, which cannot exist before code does and close
at Gate 2.

### 0.3 Reads only — no write path anywhere in this product

Both source stores are read. The ledger is append-only, so a write is permanent;
nothing in this product's assembly, its examples or its tests writes to either
(CLAUDE.md §9 — the curated estate is evidence).

### 0.4 No SDK gap

**Every capability this rung needs already exists**, which is worth stating
plainly after two consecutive rungs that did not: as-of pinned graph reads
(`FlureeGraphReader.query_pinned`), `decay: supersede-only` for a closed
reconstruction that does not age, `freshness_over: leading-edge` with a
`series_key_attribute`, the declared product gate seam, and a refusal returned as
data. **Nothing here requires a new SDK mechanism, and nothing here substitutes a
local one.**

---

## A · Decision frame

**The decision.** A middle-office operations analyst working a break, or a
control function asking whether a discrepancy is a timing artefact or a genuine
error.

**The trigger.** A break appears on a reconciliation report.

**Consuming principals.** A single role at this tier.

### A.1 Counterfactual — `latency-poisoned`, disguised as a data-quality problem

Two systems report different values for the same trade. The conventional response
is to declare a data-quality issue and reconcile toward one system as golden.
**Frequently neither is wrong**: the trading system booked at execution, the
settlement system recorded post-affirmation, and the risk system revalued at a
different market snapshot. All three are internally correct **as of their own
observation time**.

A reconciliation built on current state cannot tell the two cases apart, because
it has thrown away the observation times that would separate them.

### A.2 And a second failure this estate makes visible, which the article does not name

**Comparing current state does not only raise false breaks. It also HIDES real
ones.** Measured: **13 of the 60 designed breaks are material at amendment 0 and
immaterial at the latest amendment** — the amendment reconciled the two systems,
and a reconciliation run against current state sees nothing at all.

The break existed. It was worked, or it was not. Current state cannot say which,
because current state has forgotten it happened.

### A.3 The worked case — `TRD-W12-0002`, USD/CAD

Measured. A timing break, and the shape is the product's argument.

| system | amd 0 rate | observed (recorded) | clock offset | **true instant** |
|---|---|---|---|---|
| trading | 1.388337 | 15:26:46 | 0 s | **15:26:46** |
| settlement | 1.388751 | 16:00:18 | +47 s | **15:59:31** |
| risk | 1.388337 | 15:24:54 | −112 s | **15:26:46** |

**Risk and trading observed at the same true instant and agree exactly.**
Settlement observed **33 minutes later** and differs by 4.14 pips — which is what
USD/CAD did in those 33 minutes. Nobody is wrong.

At amendment 1 all three read 1.3927. The break is gone from current state, and
§A.2 is why that matters.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Schema** | `markets.fx-reconciliation` — entities: `Trade`, `SystemObservation`, `ReconciliationBreak`; relationships: `observedIn`, `recordedBySystem`, `amends`; measures: the reconciliation verdict per trade, the divergent system named, timing-attributable and residual variance in **pips** |
| **Freshness SLA** | Intraday for observations |
| **TTL** | 1 hour for a live reconciliation · `ttl_anchor: from_decision` |
| **Policy binding** | Entitlement scope; break-materiality thresholds bound to `intent` |
| **Lineage** | `operators_invoked` = the SDK's own set · `policy_bundle_versions` · `graph_snapshot_at` |
| **Semantic version** | `v1.0.0` |
| **Discovery** | `markets.fx-reconciliation.v1` |
| **Addressability** | `/context-products/markets/fx-reconciliation/{trade-id}` |
| **Assembly mode** | 1 — pure algorithmic. No model in the path |

### B.2 Request parameter surface

The four §6.3 axes are `ProductRequest` **fields** — `subject`, `intent`,
`freshness`, `asked_at`.

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `trades` | list, required | the policy operator's admitted set | — |
| `intent` | **field** | selects the materiality threshold | `break-investigation` |
| `asked_at` | **field** | **the reconstruction point** | — |
| `align_clocks` | bool | **the reconciliation semantics** | `true` |
| `compare_at` | enum | **the comparison instant — `amendment-0` or `latest`** | `amendment-0` |
| `materiality_pips` | decimal | overrides the intent's threshold | — |
| `debt_tolerance` | decimal | the caller's ceiling on `D_c` | — |

**`align_clocks` carries the lesson and is kept.** With it `true`, each system's
observation instant is corrected by that system's recorded clock offset before
anything is compared. With it `false`, recorded instants are used as they stand —
which is what conventional reconciliation does, and which is in the surface
precisely so both can be run and the difference measured.

### B.2a THE COMPARISON INSTANT IS AN EXPLICIT AXIS

**`compare_at` is a request parameter and both states are preserved** (Dave,
2026-09-12). The product does not choose for the caller and **never silently
replaces the requested state with latest**.

| value | what it compares | why it exists |
|---|---|---|
| `amendment-0` | each system's first observation of the trade | **the state in which a break actually occurred.** The hidden-versus-remaining analysis is evaluated here, and only here |
| `latest` | each system's most recent observation at or before `as_of` | what a conventional reconciliation sees |

**The hidden-break analysis is evaluated at `amendment-0`.** Measured: 13 of the
60 designed breaks are material at amendment 0 and immaterial at latest, because
the amendment reconciled the two systems. Asking the question at `latest` cannot
find them — not because they are unimportant but because that state has forgotten
them.

A request that supplies neither `compare_at` nor an explicit acceptance of the
default gets `amendment-0`, because the product's subject is *whether a break
occurred*, and the alternative is the reading §A.2 exists to refuse. The value in
force is carried in the payload (`FXR-G23`).

### B.3 THE UNIT OF ANALYSIS IS THE `(trade, as_of)` RECONCILIATION — NOT THE SYSTEM PAIR

**This is the rung's structural decision and it was measured, not assumed.**

Three systems give three pairwise comparisons per trade. Choosing the pair as the
unit is the obvious reading and it is wrong:

```
over the 60 break trades, at amendment 0:
  pairwise comparisons exceeding 0.5 pip   120
  underlying divergences                    60
  RATIO                                   2.00
```

**Every one of the 60 break trades partitions the same way: two systems agree and
one does not** — measured, 60 of 60, with no other shape present. When settlement
disagrees with trading, it also disagrees with risk. Counting pairs reports that
single fact twice, exactly and systematically.

A middle office told it has 120 breaks when it has 60 staffs for twice the work.
**This is rung 10's lesson arriving from the other side**: there, averaging
*destroyed* a signal; here, pairwise expansion *manufactures* one. Both are the
unit of analysis chosen before the phenomenon was understood.

**THE UNIT OF ANALYSIS IS THE BREAK TRADE. 60 breaks means 60 product
observations.** (Dave, 2026-09-12.) One verdict per trade, naming the divergent
system and carrying the per-system values behind it.

**Pairwise expansion to 120 comparisons is PROHIBITED.** Not discouraged, not
defaulted away from: the payload exposes no countable list of system-pair breaks,
and a consumer cannot arrive at 120 by counting anything the product serves.
Pairwise variance exists beneath a verdict as an explanation of it, never beside
it as a peer (`FXR-G07`, `FXR-G08`, `FXR-G22`).

### B.4 Temporal semantics, enumerated

| Clock | Where it lives | Used for |
|---|---|---|
| **World / execution time** | `fx_trade.execution_ts` (tz-aware), `value_date` | when the trade happened |
| **System observation time** | Fluree `SystemObservation.systemObservedAt`, one per `(trade, system, amendment)` | **the recorded instant — which is not the true one** |
| **Clock offset** | Fluree `clockOffsetSeconds` per system — trading `0`, settlement `+47`, risk `−112` | the systematic skew that turns a recorded instant into a true one |
| **Amendment sequence** | `amendmentSeq` on both legs; 89 `amends` edges onto FX trades | which version of the trade a value belongs to |
| **Fabric-learning time** | `part43_profile.retrieved_at` (2026-08-22), the ledger `t` | provenance only. **Never a comparison basis** |
| **Reference-rate observation** | `fx_intraday_tick.obs_ts` (5-minute), `fx_reference_rate.obs_date` (daily) | revaluation |
| **`as_of`** | `ProductRequest.asked_at`, from the caller | bounds every read; nothing later is knowable |

**THE CLOCK OFFSET IS PRODUCT CONTEXT, NOT A NEW SDK TEMPORAL AXIS** (Dave,
2026-09-12, and the distinction is load-bearing). It is not a valid-time, not an
observation time and not a supersession. It is a **correction this product applies
to a recorded instant in order to compare two systems** — domain knowledge about
three named systems, belonging to the reconciliation and to nothing beneath it.

**The corrected instant is therefore NEVER fed into the fabric's own temporal
machinery.** Specifically it does not reach `valid_from`, `observed_at`,
`_boundary_instant` or any Context Debt term, unless a later specification
explicitly requires it. The λ_c table ages an observation against the instant the
**source recorded**, exactly as `D-IMPL-331` declares, and a corrected instant
entering that path would make the SDK's freshness figure a function of this
product's own alignment model (`FXR-G24`).

The three are carried **separately in the payload** — recorded instant, offset,
corrected instant — so a consumer audits the alignment instead of trusting it,
and so the correction is visibly the product's rather than the fabric's
(`FXR-G05`).

### B.5 Context Debt and freshness

| Class | `λ_c` | `decay_basis` | `freshness_over` | Series key |
|---|---|---|---|---|
| `fxr_observation` | **1 hour** | `valid-from` | **`leading-edge`** | **`system_name`** |
| `fxr_trade` | **no decay** (`supersede-only`) | — | — | — |

**ILLUSTRATIVE CALIBRATION — the demonstration runs at 48 hours, not 1 hour**
(`CP12-F-15`, CLAUDE.md §9, `D-IMPL-323`). One hour is the production figure and
stays declared here. It cannot be demonstrated against this estate: the trade
window is eight days wide, so at a 1-hour half-life every observation has aged to
nothing and `F` is carried almost entirely by the non-decaying `fxr_trade` class.
Measured at `as_of = 2026-08-14`:

| λ_c | `TRD-W12-0002` | `TRD-W12-0424` | spread |
|---|---|---|---|
| 1 hour | F `0.2500` | F `0.2508` | **0.0008** |
| 48 hours | F `0.5151` | F `0.8999` | **0.3848** |

At one hour the term reads the same for a trade booked four days ago and one
booked hours ago — it has stopped measuring its own subject. `ccf_config.yaml`
carries 48 hours with the disclosure beside the value.

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

### B.5a The pip-scale table is a versioned, asserted artifact

**Not a constant inside projection logic** (Dave, 2026-09-12). The scale at which
a currency pair quotes is a market convention this product **asserts**, not a fact
it derives, so it lives in `artifacts/pip-scale.yaml` with its own semver and
provenance — the shape `CP11-F-09`'s SIC mapping arrived at for the same reason.

| pair | pip |
|---|---|
| USD/JPY | **0.01** |
| AUD/USD · EUR/GBP · EUR/USD · GBP/USD · USD/CAD | **0.0001** |

A pair the artifact does not name is **not evaluable**, never defaulted to
`0.0001`: defaulting is how a JPY-quoted pair comes to report a variance a
hundred times too small and passes every threshold (`FXR-G12`, `FXR-G26`).

**`freshness_over: leading-edge` keyed on `system_name`, and the key is a
first-class claim attribute.** Each system's observations of one trade form a
series — one per amendment — and what a reconciliation rests on is **each
system's latest observation at or before `as_of`**, not the average age of its
whole amendment history. `system_name` is promoted out of the payload onto the
claim in the resolution rule's `attribute_keys`, because the scorer reads a series
key off the **claim** and a key buried in a serialized blob resolves to `None` and
collapses every system into one series (`HalfLifeEntry.series_key_attribute`;
`FXR-G14`).

**The trade itself does not decay.** Its identity is superseded by amendment, not
aged, so `supersede-only` — which returns retained relevance `1` and is the
honest statement for a class time does not touch.

---

## C · Data catalog

### C.1 What the estate holds, measured

```
fx_trade                500 rows   6 pairs, exec 2026-08-06 .. 2026-08-13
system_trade_record   1,815 rows   3 systems x 605 records
  by system             605 each   risk / settlement / trading
  amendment_seq 0       1,500      500 trades
  amendment_seq 1         267       89 trades
  amendment_seq 2          33       11 trades
  amendment_seq 3          15        5 trades
break_record             60 rows   40 timing / 20 genuine
fx_intraday_tick     10,368 rows   5-minute, 6 value dates      synthetic — engineered
fx_reference_rate     3,942 rows   daily, 2024-01-02 ..         PUBLIC (FRED DEXUSEU/DEXUSUK)
fx_pip_size               6 rows   0.0001, and 0.01 for USD/JPY
materiality_threshold     3 rows   regulatory-report 1 · break-investigation 2 · control-review 5
part43_profile           44 rows   a DISTRIBUTION over 30,501 real DTCC observations

Fluree
  Trade                   500 nodes, each with three `observedIn` edges
  SystemObservation     1,815 nodes, all carrying systemObservedAt AND recordedBySystem
  ReconciliationBreak      60 nodes
  clockOffsetSeconds        3 values: trading 0, settlement +47, risk −112
  amends                   89 edges onto FX trades
```

**The two legs join on `trade_id`**, and the Fluree observation IRI is
`obs-<trade_id>-<system>-<amendment_seq>`. Verified.

### C.2 Provenance, and what is public

| Element | Provenance |
|---|---|
| Daily FX reference rates | **public** — FRED, with the derivation recorded (`(DEXUSEU) / (DEXUSUK)`) |
| Part 43 distribution profile | **public** — DTCC `pddata.dtcc.com`, retrieved 2026-08-22, over 30,501 observations |
| Intraday tick series | **synthetic — engineered** |
| Trades, system records, observation instants, clock offsets, amendment chains | **synthetic — internal** |
| Both break populations | **synthetic — engineered** |

**The notional is a BAND, never a number** — `fx_trade.notional_band` holds
`1,000,000-5,000,000` and the like. Part 43 caps and bands large notionals to
protect participant anonymity. **This product does not reconstruct a notional from
a band**, and computes nothing that would require one: every variance it reports
is in **pips**, which is a property of the rate and not of the size
(`FXR-G12`).

### C.3 The data traps

**Six, and all six were run during Gate-1 measurement. Two are the author's own
failed readings.**

**TRAP 1 — the pairwise unit doubles the count.** 120 pairwise comparisons over
60 underlying divergences, exactly `2.00×`. §B.3. **Binding:** one verdict per
trade, naming the divergent system.

**TRAP 2 — classifying by residual magnitude after tick revaluation.** The
obvious implementation: revalue each system at its corrected instant from the
tick series, subtract, and call the remainder residual. **Measured at the 2-pip
threshold it misclassifies 22 of 60** — 18 designed-timing breaks read genuine
and 4 designed-genuine read timing. The cause is structural: **the tick series is
5-minute and the observation differences are frequently smaller than that**, so
two instants inside one tick bucket revalue identically and their timing
component reads as zero. **Binding:** a residual computed across an interval
shorter than the tick spacing is **not evaluable** and must be reported as such,
never as zero (`FXR-G10`).

**TRAP 3 — comparing current state.** 13 of 60 designed breaks are material at
amendment 0 and immaterial at the latest amendment. §A.2. **Binding:** the
reconciliation is performed at the requested `as_of` over the observation history,
never over latest state (`FXR-G03`).

**TRAP 4 — the weekend tick.** One break's nearest preceding tick is **20.0 hours**
old, because the series has a 173,100-second gap across the weekend. Revaluing
against it produces a residual of **−72.49 pips** on a raw variance of 7.99 — a
number with no meaning. **Binding:** the same `not-evaluable` rule as TRAP 2, and
the staleness of the tick used is carried in the payload (`FXR-G11`).

**TRAP 5 — comparing rate differences without pip normalisation.** USD/JPY prices
to 0.01 and every other pair to 0.0001. A raw difference of `0.06` is **6 pips**
in USD/JPY and **600 pips** in EUR/USD. Measured after normalisation the two are
comparable — median disagreement 6.00 and 6.40 pips — and without it USD/JPY
breaks vanish beneath any threshold. **Binding:** every variance the product
reports is in pips (`FXR-G12`).

**TRAP 6 — the author's own, and it is recorded because it nearly reached this
document as a finding.** The first classification run compared systems **at their
latest amendment** and reported that *"all 20 genuine breaks show Δt = 0 after
clock correction"* — an apparently perfect discriminator. It is an artifact. Nine
designed-timing breaks also show `Δt = 0` at latest state, **because their
variance at latest state is 0.00 pips**: the amendment reconciled them, so the
two systems trivially agree at the same instant. The measurement was of the wrong
population, and it flattered the mechanism. **Binding:** TRAP 3's, and the reason
§D.2 compares at `as_of` over the observation history rather than at latest state.

---

## D · Assembly recipe

### D.1 Operator step table

| # | Operator | Store | What it does |
|---|---|---|---|
| 1 | `policy.principal-subgraph` | — | admits only the trades the effective request names |
| 2 | `traversal.typed-neighborhood` | Fluree | the observation subgraph: `observedIn`, `recordedBySystem` |
| 3 | Π `FXReconciliationProjection` | in-memory | the alignment, the partition, the verdict, the decomposition |

The deployment authors **no operator set**: the plan factory passes the resolver's
own `required` tuple through, as rungs 9–11 do.

### D.2 The computation

1. **Select each system's observation at or before `as_of`** — the leading edge of
   that system's series for this trade. Never latest state (TRAP 3, TRAP 6).
2. **Correct each recorded instant by that system's `clockOffsetSeconds`** to
   recover the true instant. Where `align_clocks` is `false`, skip this step and
   say so in the payload.
3. **Partition the systems into agreement groups** at the materiality threshold,
   in pips. A trade whose systems all agree has **no break** and is served as
   such, not omitted.
4. **Name the divergent system** where the partition is `(1, 2)`. Where it is
   `(1, 1, 1)` — three-way disagreement — no system is "the odd one out", and the
   payload says so rather than picking one.
5. **Decompose the variance.** Timing-attributable is the market's own move
   between the two corrected instants, taken from the tick at or before each.
   Residual is what is left.
6. **Refuse to decompose where the interval is shorter than the tick spacing, or
   where the nearest tick is stale** — report `not-evaluable` with the reason,
   never a zero (TRAP 2, TRAP 4).
7. **Classify** the verdict. **The vocabulary is exactly `timing`, `genuine`,
   `not-evaluable` and is CLOSED** (Dave, 2026-09-12). The article's
   `amendment-lag` and `revaluation-basis` are not produced, because this estate
   carries no labels for them and a class the product cannot evidence is a label
   it would be inventing (`FXR-G21`).

**Step 6 is the honest half of step 5.** A decomposition that always produces a
number produces a wrong one 22 times in 60.

### D.3 The scenarios

**Scenario 1 — the break that inverts.** `TRD-W12-0472` (EUR/USD): raw **6.01
pips**, timing-attributable **5.79**, residual **0.22**, corrected observation
gap **388 s**, tick staleness **279 s**. Raw variance three times the materiality
threshold; residual an eighth of it. Looks like a genuine error; is the market
moving for six and a half minutes.

> **AMENDED AT GATE 2** (`CP12-F-11`). This scenario originally named
> `BRK-TRD-W12-0235-settlement-risk` — raw 6.95 pips, aligned residual −0.09,
> gap **296 s**. That gap is **below the 300 s tick spacing**, so §D.2 step 6,
> `FXR-G10` and `FXR-G25` all require it to be `not-evaluable`: the −0.09 was
> produced by the residual-magnitude mechanism TRAP 2 refuses. The binding wins
> over the illustration. `TRD-W12-0235` is retained as `FXR-G10`'s subject,
> which is what it actually demonstrates.

**Scenario 2 — the genuine break that survives alignment.**
`BRK-TRD-W12-0004-risk-trading` (GBP/USD): raw **7.82 pips**, corrected
observation gap **0 s** — risk and trading observed at the same true instant —
and settlement agrees with risk to the last digit. Trading is the divergent
system, and no amount of timing explains it.

**Scenario 3 — the break that current state has forgotten.** `TRD-W12-0002`
(§A.3): 4.14 pips at amendment 0, **0.00 at amendment 1**. Asked as of the
execution window it is a break; asked as of today it does not exist.

**Scenario 4 — `align_clocks=false`.** The same question with the correction
disabled. The recorded instants differ by the offsets, so risk appears to have
observed 112 seconds before it did, and the timing attribution changes. Both
answers are served and their content addresses differ.

### D.4 Determinism and replay

**Determinism class: `deterministic`.** `payload_hash` is `sha256` over the
canonical bytes excluding `assembled_at`.

Replay: serve at a pinned `as_of`; re-serve and confirm the hash; re-serve at an
`as_of` **before** an amendment and confirm the pre-amendment values and the
break are present; return to the original and confirm the original hash. If step
three does not differ from step one, `as_of` is not reaching the observation
selection.

### D.5 Validation gates

Six universal — empty-operator guard, lineage strict equality, TTL bounds, debt
gate, suppression silence, classification containment — then the product-specific
set at §G.1, **including variance-decomposition closure**: timing-attributable
plus residual must equal total, or the decomposition must be `not-evaluable`. A
silent gap means a system's observation time was dropped from the alignment.

**Error mapping.** `404` unknown trade · `403` not entitled · `409` debt gate ·
`200` with notices otherwise. **A trade whose systems all agree is `200` with an
explicit `no-break` verdict** — not an empty payload and not an omission.

---

## E · Findings

| id | finding | status |
|---|---|---|
| `CP12-F-01` | **No settlement-instruction, netting, ISO 20022 or CLS-cutoff data exists.** The article's schema names a `SettlementInstruction` entity and `settlesVia` / `netsWith` relationships; **measured, both predicates are ABSENT from this estate's vocabulary — not present with a count of zero** (Dave, 2026-09-12). The distinction is the one this project draws everywhere else: a predicate nothing asserts is not a predicate asserting nothing. No relational table matches either. The product is specified without a settlement leg, does not claim one, and reports the leg as absent rather than as empty (`FXR-G18`). | ESTATE-LIMITATION |
| `CP12-F-02` | **CFTC Part 43 exists as a DISTRIBUTION PROFILE, not as records.** `part43_profile` holds 44 rows of `(dimension, key, observed_n)` summarising **30,501 real DTCC observations** retrieved 2026-08-22. The trades are *patterned on* it. There is no per-trade public record to join to, so Part 43 is provenance and calibration, never an `E` leg. | ESTATE-LIMITATION |
| `CP12-F-03` | **The estate labels two break classes; the article specifies four.** `break_record.designed_class` holds only `timing` and `genuine`. The article's `amendment-lag` and `revaluation-basis` have no labels. The product classifies into `timing`, `genuine` and `not-evaluable` and **does not invent the two it cannot evidence**. | ESTATE-LIMITATION |
| `CP12-F-04` | **The tick series cannot adjudicate sub-five-minute intervals.** 5-minute spacing against observation gaps frequently below it. Reporting a zero timing component for such an interval misclassifies 22 of 60 breaks. Handled by refusing to decompose rather than by interpolating (TRAP 2). | ESTATE-LIMITATION |
| `CP12-F-05` | **The tick series has a 173,100-second weekend gap.** One break's nearest preceding tick is 20.0 hours old and yields a −72.49-pip residual. Same handling as `CP12-F-04` (TRAP 4). | ESTATE-LIMITATION |
| `CP12-F-06` | **Intraday ticks are `synthetic — engineered`; the daily reference rates are public.** The split is disclosed rather than blurred: the daily series carries a real FRED derivation, the intraday series does not exist publicly at this granularity and is engineered, exactly as rung 9's rate leg was. | NOT-A-GAP |
| `CP12-F-07` | **47 pairwise disagreements above 0.5 pip carry no `break_record` row**, against 47 that do. Measured, they are the *same* underlying divergences seen through the second system pair — which is TRAP 1 stated from the data side. `break_record` is a designated sample, never the population, and the product does not treat it as one. | NOT-A-GAP |
| `CP12-F-08` | **Notionals are banded, never exact.** Part 43 caps large notionals for anonymity. The product reports variance in **pips** throughout and computes nothing requiring a notional. | ESTATE-LIMITATION |
| `CP12-F-09` | **The tick series does not reproduce a designed timing move beyond a short interval.** The intraday series and the system values were engineered independently. Measured over the 60 designated breaks: 14 computed `timing`, **all 14 designated timing**; 37 computed `genuine`, of which 20 designated genuine and 17 designated timing — and the disagreement grows monotonically with the observation gap, from ~2 pips at 400 s to 13.73 pips at 10,849 s. Not repaired: `break_record` is a sample and not the truth (`CP12-F-07`), so tuning a cutoff until the two agreed would be the move CLAUDE.md §9 forbids. The payload carries the designation beside the computed verdict, with the gap, the staleness and the full decomposition. | ESTATE-LIMITATION |
| `CP12-F-10` | **A zero observation gap is not TRAP 2.** Applying the sub-tick rule to a zero-length interval returned `not-evaluable` for 29 of 60 breaks and buried the estate's strongest signal: the corrected gap is exactly 0 on **20 of 60**, and those 20 are **exactly** the 20 designated `genuine`, 20 of 20. Two identical instants leave no interval, so the timing component is zero by arithmetic rather than by revaluation — §D.3 scenario 2. `not-evaluable` fell from 29 to 9. | FIXED-gate-2 |
| `CP12-F-11` | **§D.3 scenario 1 named a trade the product's own binding refuses.** See the amendment at §D.3. | FIXED-gate-2 |
| `CP12-F-12` | **The comparison peer was chosen non-deterministically.** `next(iter(set_of_str))` is not stable across interpreters; measured, the same trade compared against `risk` on one run and `trading` on the next, with a different content address. §D.4 declares `deterministic`, which is a property of the code and not a declaration about it. Fixed by ordering on the canonical system tuple. | FIXED-gate-2 |
| `CP12-F-13` | **The three served decomposition figures did not close.** Quantizing independently gave `12.53 + −5.86` against a total of `6.68` on `TRD-W12-0100`, while `closes` read true because it compared unrounded intermediates. The residual is now the remainder of the figures actually served. Found by `FXR-G09` under sabotage. | FIXED-gate-2 |
| `CP12-F-14` | **No three-way disagreement exists anywhere in the estate.** Measured across all 500 trades at 0.01 pip: 440 all-agree, 60 exactly-two-agree, **0 three-way**. In every break the two agreeing systems match to the last digit. `FXR-G08`'s `(1, 1, 1)` limb is `not-required`, and the absence is asserted by the executing test rather than assumed. | ESTATE-LIMITATION |
| `CP12-F-15` | **The declared 1-hour λ_c cannot discriminate across an 8-day snapshot.** See §B.5. Illustrative calibration at 48 hours, disclosed at every site that carries it. | ESTATE-LIMITATION |

---

## F · Gate-2 assertions

### F.1 The declared set

| id | statement | what it catches |
|---|---|---|
| `FXR-G01` | a plan with zero operator steps never serves | empty-operator |
| `FXR-G02` | served lineage equals the plan's typed operator references; `ProductLineage` is exactly three fields | lineage drift |
| `FXR-G03` | the reconciliation is performed at the requested `as_of` over the observation history, and an `as_of` before an amendment sees the pre-amendment values | TRAP 3 / TRAP 6 — current-state comparison |
| `FXR-G04` | `expires_at` derives from the decision instant and respects the ceiling | TTL fabrication |
| `FXR-G05` | every system value carries its **recorded instant, its clock offset and its corrected instant**, separately | an alignment a consumer must trust rather than audit |
| `FXR-G06` | `D_c` above tolerance refuses with the debt block | ungated debt |
| `FXR-G07` | **exactly one verdict per trade**, and the payload exposes no countable pairwise break list | TRAP 1 — the doubled count |
| `FXR-G08` | where the partition is `(1, 2)` the divergent system is named; where it is `(1, 1, 1)` the payload says no system is isolated rather than picking one | a three-way disagreement reported as one system's fault |
| `FXR-G09` | timing-attributable + residual = total variance, **or** the decomposition is `not-evaluable` with a reason | decomposition closure |
| `FXR-G10` | a decomposition across an interval shorter than the tick spacing is `not-evaluable`, never zero | TRAP 2 |
| `FXR-G11` | the staleness of the tick used is carried, and a stale tick yields `not-evaluable` | TRAP 4 — the weekend |
| `FXR-G12` | every variance is expressed in **pips**, and USD/JPY resolves at 0.01 while the others resolve at 0.0001 | TRAP 5 — the scale error |
| `FXR-G13` | `align_clocks=false` produces a different answer **and** a different content address from `align_clocks=true` on the same trade and instant | a parameter that does not reach the computation |
| `FXR-G14` | the λ_c row declares `freshness_over: leading-edge` with `series_key_attribute: system_name`, and that attribute is a **first-class claim attribute** rather than a key inside a serialized blob | every system collapsing into one series |
| `FXR-G15` | a trade whose systems all agree serves with an explicit `no-break` verdict | absence read as an empty answer |
| `FXR-G16` | the four §6.3 axes are `ProductRequest` fields, absent from `parameters` | request identity demoted |
| `FXR-G17` | no notional figure appears anywhere in the payload; the band is carried as a band | `CP12-F-08` — a reconstructed notional |
| `FXR-G18` | the payload claims no settlement, netting or ISO 20022 content, and where it names the leg at all it names it **absent** rather than empty or zero | `CP12-F-01` — an absent leg reported as a measured nothing |
| `FXR-G19` | the payload carries no second copy of `D_c`, the content address or the policy versions | two copies of one figure |
| `FXR-G20` | an unknown trade refuses distinctly from a trade with no break | request error vs world fact |
| `FXR-G21` | the classification vocabulary is exactly `timing`, `genuine`, `not-evaluable` — the two classes the article names but the estate cannot evidence are absent | `CP12-F-03` — an invented label |

### F.1a THE SIX TRAP GATES

**Each measured trap is its own gate and its own Gate-2 sabotage target** (Dave,
2026-09-12). They are listed apart from the behavioral gates above because they
share a demand the others do not:

> **A trap gate must DISTINGUISH the wrong mechanism from the right one.** Two
> answers coinciding is not evidence. Where the correct computation and the
> defective one would agree on the population at hand, the gate must construct or
> select the case where they **diverge**, and assert there.

That rule is not new here. cp-10's `RSM-G23` and cp-11's `EWS-G27` were both
**green under their own sabotage** for exactly this reason — each asserted only
where the two mechanisms happened to produce the same value. Naming it in the
specification makes it a design obligation rather than a lesson relearned.

| id | trap | the gate, and where the two mechanisms DIVERGE |
|---|---|---|
| `FXR-G22` | **TRAP 1 — pairwise expansion** | the product reports **60** observations over the 60 break trades; a pairwise implementation reports **120**. The gate asserts the count AND that no payload field enumerates system-pair breaks countably. Divergence is exact and systematic: `2.00×`, measured |
| `FXR-G23` | **TRAP 3 / TRAP 6 — latest-state comparison** | asserted on the **13 trades that are material at amendment 0 and immaterial at latest**. At `compare_at=amendment-0` the product reports a break; a latest-state implementation reports none. The gate names those trades and requires both answers, so the two mechanisms cannot be confused for one. **It must NOT be asserted on a trade with no amendment**, where both readings agree and the gate would prove nothing |
| `FXR-G24` | **TRAP 6's second half — the corrected instant leaking into the fabric** | the λ_c path ages an observation against the **recorded** instant. The gate asserts the corrected instant reaches no `valid_from`, no `observed_at`, no invalidation boundary and no Context Debt term — and asserts it where the two instants **differ**, i.e. on a `risk` or `settlement` observation, never on `trading`, whose offset is `0` and where the two are identical |
| `FXR-G25` | **TRAP 2 — residual classification on 5-minute ticks** | asserted on a break whose corrected observation gap is **shorter than the tick spacing**. The correct product returns `not-evaluable`; a residual-magnitude implementation returns a confident `timing` or `genuine`. Measured: 22 of 60 differ between the two, so the divergence population is large and nameable |
| `FXR-G26` | **TRAP 5 — missing pip normalisation** | asserted on a **USD/JPY** break, where the pip is `0.01`. Normalised it reports ~6 pips; unnormalised it reports the raw rate difference and reads 100× smaller, passing every threshold. The gate must not be asserted on a `0.0001` pair, where normalised and unnormalised differ by a factor the thresholds may not separate |
| `FXR-G27` | **TRAP 4 — the stale weekend tick** | asserted on the one break whose nearest preceding tick is **20.0 hours** old. The correct product returns `not-evaluable` and carries the staleness; a naive implementation returns a residual of **−72.49 pips** on a raw variance of 7.99. The two answers are not close, which is what makes this gate cheap and decisive |

**Every one of these is a Gate-2 sabotage target**, and the sabotage for each is
the defective mechanism the trap names — reintroduced, and observed producing the
wrong answer on the divergence case the gate selects.

### F.2 Acceptance

**Gate 1 is GO** (Dave, 2026-09-12), with the pre-Gate-2 amendment recorded
above: the break trade as the explicit unit at 60 observations with pairwise
expansion prohibited; the comparison instant as an explicit axis preserving both
states; the pip table as a versioned asserted artifact; the clock offset held as
product context and kept out of the fabric's temporal machinery; the closed
classification vocabulary; `settlesVia` and `netsWith` reported **absent** rather
than zero; and all six measured traps promoted to gates that must distinguish the
wrong mechanism from the right one.

**27 gates, `FXR-G01`–`FXR-G27`.** Every figure in this document is measured; no
SDK gap was found, and none is authorized; the two failed measurement approaches
are recorded as TRAP 2 and TRAP 6 rather than corrected away.
