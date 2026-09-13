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
| `materiality_pips` | decimal | overrides the intent's threshold | — |
| `debt_tolerance` | decimal | the caller's ceiling on `D_c` | — |

**`align_clocks` carries the lesson and is kept.** With it `true`, each system's
observation instant is corrected by that system's recorded clock offset before
anything is compared. With it `false`, recorded instants are used as they stand —
which is what conventional reconciliation does, and which is in the surface
precisely so both can be run and the difference measured.

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

**So the product reports one verdict per trade**, naming the divergent system and
carrying the per-system values behind it. Pairwise variance is available beneath
that verdict and **never as the countable unit** (`FXR-G07`, `FXR-G08`).

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

**The clock offset is a fourth kind of time and it has no analogue in rungs 8–11.**
It is not a valid-time, not an observation time and not a supersession: it is a
**correction applied to a recorded instant to recover the true one.** The product
carries the recorded instant, the offset and the corrected instant **separately in
the payload**, so a consumer audits the alignment instead of trusting it
(`FXR-G05`).

### B.5 Context Debt and freshness

| Class | `λ_c` | `decay_basis` | `freshness_over` | Series key |
|---|---|---|---|---|
| `fxr_observation` | **1 hour** | `valid-from` | **`leading-edge`** | **`system_name`** |
| `fxr_trade` | **no decay** (`supersede-only`) | — | — | — |

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
7. **Classify** the verdict: `timing`, `genuine` or `not-evaluable`.

**Step 6 is the honest half of step 5.** A decomposition that always produces a
number produces a wrong one 22 times in 60.

### D.3 The scenarios

**Scenario 1 — the break that inverts.** Measured: **13 of 60 breaks have a raw
variance above the 2-pip threshold and an aligned residual below it.** The
strongest is `BRK-TRD-W12-0235-settlement-risk` (USD/CAD): raw **6.95 pips**,
aligned residual **−0.09**, corrected observation gap **296 s**. Looks like a
genuine error; is the market moving for five minutes.

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
| `CP12-F-01` | **No settlement-instruction, netting, ISO 20022 or CLS-cutoff data exists.** The article's schema names a `SettlementInstruction` entity and `settlesVia` / `netsWith` relationships; measured, both predicates have **zero** edges and no relational table matches. The product is specified without a settlement leg and does not claim one. | ESTATE-LIMITATION |
| `CP12-F-02` | **CFTC Part 43 exists as a DISTRIBUTION PROFILE, not as records.** `part43_profile` holds 44 rows of `(dimension, key, observed_n)` summarising **30,501 real DTCC observations** retrieved 2026-08-22. The trades are *patterned on* it. There is no per-trade public record to join to, so Part 43 is provenance and calibration, never an `E` leg. | ESTATE-LIMITATION |
| `CP12-F-03` | **The estate labels two break classes; the article specifies four.** `break_record.designed_class` holds only `timing` and `genuine`. The article's `amendment-lag` and `revaluation-basis` have no labels. The product classifies into `timing`, `genuine` and `not-evaluable` and **does not invent the two it cannot evidence**. | ESTATE-LIMITATION |
| `CP12-F-04` | **The tick series cannot adjudicate sub-five-minute intervals.** 5-minute spacing against observation gaps frequently below it. Reporting a zero timing component for such an interval misclassifies 22 of 60 breaks. Handled by refusing to decompose rather than by interpolating (TRAP 2). | ESTATE-LIMITATION |
| `CP12-F-05` | **The tick series has a 173,100-second weekend gap.** One break's nearest preceding tick is 20.0 hours old and yields a −72.49-pip residual. Same handling as `CP12-F-04` (TRAP 4). | ESTATE-LIMITATION |
| `CP12-F-06` | **Intraday ticks are `synthetic — engineered`; the daily reference rates are public.** The split is disclosed rather than blurred: the daily series carries a real FRED derivation, the intraday series does not exist publicly at this granularity and is engineered, exactly as rung 9's rate leg was. | NOT-A-GAP |
| `CP12-F-07` | **47 pairwise disagreements above 0.5 pip carry no `break_record` row**, against 47 that do. Measured, they are the *same* underlying divergences seen through the second system pair — which is TRAP 1 stated from the data side. `break_record` is a designated sample, never the population, and the product does not treat it as one. | NOT-A-GAP |
| `CP12-F-08` | **Notionals are banded, never exact.** Part 43 caps large notionals for anonymity. The product reports variance in **pips** throughout and computes nothing requiring a notional. | ESTATE-LIMITATION |

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
| `FXR-G18` | the payload claims no settlement instruction, netting or ISO 20022 content | `CP12-F-01` — a leg the estate does not have |
| `FXR-G19` | the payload carries no second copy of `D_c`, the content address or the policy versions | two copies of one figure |
| `FXR-G20` | an unknown trade refuses distinctly from a trade with no break | request error vs world fact |
| `FXR-G21` | the classification vocabulary is exactly `timing`, `genuine`, `not-evaluable` — the two classes the article names but the estate cannot evidence are absent | `CP12-F-03` — an invented label |

### F.2 Acceptance

Gate 1 is Dave's ruling on §B.3 first — **the unit of analysis** — and the rest
second. Every figure in this document is measured; no SDK gap was found; the two
failed measurement approaches are recorded as TRAP 2 and TRAP 6 rather than
corrected away.
