---
product: credit-risk.early-warning.v1
standard: v0-3
sdk_spec: cp-11
tier: 3
cost_band: "×2–4"
assembly_mode: 1
capability_classes: [relational, bitemporal-ledger, graph-traversal, in-memory]
prerequisites: [corporate-family-tree, credit-exposure-rollup, rating-and-spread-migration, covenant-in-force-as-of]
build_order: 11
lifecycle: draft
accountable_owner: credit-risk-product-engineering
review_cadence: at every Control Plane change to the signal weights, the escalation
  thresholds or the λ_c table; and no less than annually
topic: context-products
title: Credit Surveillance / Early Warning — Context Product Specification
generated: '2026-09-12'
---

# Credit Surveillance / Early Warning — Context Product Specification

**`CP-SPEC-011` · Tier 3 · `credit-risk.early-warning.v1`**
**PostgreSQL for the dated signal stream, the weights and the thresholds · Fluree for the supersession chain and the prior-observation anchors**

> **What changed on this name since we last looked — and does it matter?**
>
> Five signal classes on five decay regimes, where one of them does not decay at
> all and is bounded by **supersession** instead.

## 0 · What this document is

A build specification for the engineer who will assemble this Context Product
from the credit data estate. **Every figure below was measured against the live
estate on 2026-09-12 before this document was written**, and the query that
produced it is reproducible.

### 0.1 The governing question

> **Can a Context Product answer "what changed, and does it matter" without
> either drowning the answer in everything that ever happened, or losing the
> signal that a fact has stopped being relevant without becoming old?**

Rung 10 established that freshness reads the leading edge of a series rather
than its history. This rung asks the harder version: what governs a class that
**never decays**? An acceleration filing is as true a year later as the day it
landed. Time does not make it irrelevant — a **later filing that supersedes it**
does.

### 0.2 Placeholder discipline

No `[TBC]` except the p95 budgets, which cannot exist before code does and close
at Gate 2. Where a value is a demonstration choice rather than a production
recommendation, §0.4 and §E.1 name it.

### 0.3 Reads only — no write path anywhere in this product

Both source stores are read. The ledger is append-only, so a write is permanent;
nothing in this product's assembly, its examples or its tests writes to either
(CLAUDE.md §9 — the curated estate is evidence).

### 0.4 THE VAULT ARTICLE'S CENTRAL MECHANISM IS NOT BUILDABLE ON TODAY'S SDK

**This section is first because it is the Gate-1 decision.**

The canonical article names step 7 — emitting a supersession event that makes
the Control Plane **cascade cache invalidation to every downstream Context
Product whose `operators_invoked` touched the affected entity** — and says of
it: *"Step 7 is why this product is in the catalog."*

**Measured against `src/` and `runtime/` on 2026-09-12, none of its four parts
exists.** This was verified directly, not inferred:

| The article's claim | What the SDK has |
|---|---|
| "supersession is a **Policy event**" | It is a graph write-path column. `src/ccf/graph/_writer.py::_restitch_chain` sets `superseded_by` / `superseded_at`; backend SQL filters on them at as-of read time. It never reaches the Control Plane. |
| "**the Control Plane propagates**" | There is no event bus, subscriber registry, watcher or notify path for supersession anywhere in `src/` or `runtime/`. The one `notify()` is `ccf/hitl/webhook.py`, for human-approval events. |
| "invalidation **cascades to downstream products**" | **There is no product cache to invalidate.** The only cache in the SDK is `ccf/operators/planner.py::IntermediateCache`, a per-execution memo of operator intermediates whose own docstring rules the longer-lived case out: *"A longer-lived cache needs the invalidation story `D-IMPL-36` defers, and a cache without one is a replay defect waiting for a write."* |
| "whose **`operators_invoked`** touched the affected entity" | Nothing reads `operators_invoked` for invalidation. Every reference in the tree is construction, set-union on composition, or gate validation. No reverse index from entity to the products that touched it exists. |

Two further facts complete the picture. `decay: supersede-only` — the name that
sounds like the mechanism — is **purely a half-life mode**: its entire behavior
is `ccf/halflife/decay.py::freshness` returning `Decimal(1)`. It triggers
nothing. And `ArtifactStoreProtocol` offers `put` / `get` / `exists` /
`resolve_uri` and **no delete, by design** (`artifacts/protocol.py`: *"must never
offer an update or delete operation… what makes the tampering threat structural
rather than procedural"*) — so there is nothing to evict even in principle.

**The SDK's actual staleness posture is pull-based and per-request.** A product
carries `expires_at`, the TTL-bounds gate checks it at serve time, and the graph
excludes superseded claims at as-of read time. **A consumer learns a product is
stale by asking again, never by being told.**

**What this specification therefore builds, and what it does not.** It builds
steps 1–6 in full, and it replaces step 7 with the honest demonstration the same
machinery supports:

> **Re-derivation on next request, not a cascade.** Ingest a superseding claim,
> re-ask the same question, and observe that the answer changes because the
> as-of read now excludes the superseded claim — with the two content addresses
> differing to prove it. This is a real property and it is worth demonstrating.
> **It is not the cascade, and this document does not call it one.**

`CP11-F-01` records the gap. **Whether rung 11 ships on that basis, or waits for
an SDK cycle that builds the cascade, is Dave's ruling at Gate 1** — it is not a
decision this document takes.

### 0.5 What is real, what is engineered, and three things this product does NOT consume

| Element | Provenance |
|---|---|
| 8-K filing events, by item | **public** — SEC EDGAR, with accession and primary document |
| State WARN Act notices | **public** — state WARN registries |
| Adverse media mentions | **public** — GDELT Project |
| XBRL period-over-period deltas | **public** — SEC `companyfacts` |
| Issuer-specific spread widening | **synthetic — engineered** (inherited from rung 10's decomposition) |
| Signal weights by type and sector | **synthetic — internal** |
| Escalation thresholds by intent | **synthetic — internal** |
| Prior-observation anchor points | **synthetic — internal** |
| Supersession chain over 8-K signals | **synthetic — internal** (the chain; the filings it links are public) |

**Three things the article assumes that this estate does not carry**, each
verified rather than presumed:

- **No FINRA TRACE.** Inherited from `CP10-F-01`: the spread leg is a
  decomposition, not an observed trade. This document does not call it TRACE.
- **No per-mention media sentiment.** `gdelt_mention.tone` **looks like a
  sentiment score and is not one**: measured, all 951 rows carry the identical
  literal string `<-5`, which is the GDELT *query filter* that selected them.
  Tone-weighting per mention is not computable here, and this product does not
  claim it (`CP11-F-04`).
- **No Item 4.02 non-reliance events.** `filing_profile` records two obligors
  with a lifetime 4.02 count; **zero** appear as dated events in the window. The
  auditor leg is Item 4.01 only, 6 events across 5 obligors (`CP11-F-05`).

> **Illustrative calibration.** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the governed
> behavior observable in that snapshot. They demonstrate how the SDK applies
> these controls and should not be interpreted as recommended production
> coverage-policy thresholds.

### 0.6 The four-question test

- **Is the answer assembled rather than stored?** Yes. No store holds *"what
  changed on this name since the last review, weighted by class, with the
  superseded facts removed rather than aged out."*
- **Does more than one consumer need it?** Yes — the surveillance sweep, the
  credit officer preparing a review, and the control function asking why a name
  did or did not escalate.
- **Does it carry a governed freshness claim?** Yes, and a **180-fold spread**
  across the decaying classes, plus one class that does not decay at all.
- **Would a `SELECT` do?** No, and §C.4 records **five** naive readings that
  were actually run during Gate-1 measurement. Each returned a confidently wrong
  answer.

---

## A · Decision frame

**The decision.** A portfolio surveillance function running a scheduled sweep,
or a credit officer asking what moved on a name since last review.

**The trigger.** A sweep, or a name that has started to look different.

**Consuming principals.** A single role at this tier.

### A.1 Counterfactual — `context-starved`, compounded by an accumulating score

Two failures compose.

**First, the classic one.** The signals live in separate systems and nobody
joins them at decision time. A layoff notice, a spread widening and a trend
reversal each look unremarkable alone and are alarming together. Measured:
**18 of the 50 anchor obligors carry three or more distinct signal classes
inside a single 30-day window**, and no source system composes them.

**Second, and specific to this rung: a score that only ever goes up.** The 8-K
class carries **no decay by declaration** — `signal_weight.decay_days` is `NULL`
for every one of its nine sector rows. Read naively, that means every 8-K ever
filed contributes at full weight forever. Measured at `as_of` 2026-08-19 over
the two-year window:

```
naive accumulation      max 3.1415   median 0.9726
                        48/50 over the sweep threshold
                        39/50 over credit-committee
                        30/50 over board-risk
```

**A control that fires on 60% of the book is not a control.** The routine
filings — 220 Item 1.01 material-agreement events, 184 Item 5.02 officer
changes — swamp the four Item 2.04 accelerations that actually matter.

### A.2 What "no decay" actually means, and it is the rung's whole point

An acceleration filing does not become *less true* with age. What ends its
relevance is **a later filing that supersedes it** — and the estate models that
directly: **538 `WarningSignal` nodes, 486 carrying `supersededBy`, 52 with an
open end**, approximately one current signal per obligor.

Applying it changes the answer completely. Same instant, same weights, same
decay curves — the only difference is that a superseded 8-K contributes nothing:

```
supersession applied    max 0.3694   median 0.1458
                        3/50 over the sweep threshold
                        0/50 over credit-committee
                        0/50 over board-risk
```

**Neither reading is usable as declared**, and that is a finding rather than an
embarrassment (`CP11-F-02`). The mechanism is right and the *thresholds* were
calibrated against the wrong one. §E.2 declares recalibrated demonstration
values under the `D-IMPL-323` conditions, with this measurement as the reason.

### A.3 The worked case — Tupperware Brands `G8NWFN4YP7CR6FOP4886`

Measured. A high-severity filing, a heavy media footprint, and **no financial
trend evidence at all** — three signals that do not agree about how much is
known.

| when | what | source |
|---|---|---|
| **2024-09-18** | **8-K Item 2.04** — acceleration or triggering event. Severity **1.0**, the only item class that carries it | EDGAR `0001008654-24-000068` |
| across the window | **23 adverse-media mentions**, the heaviest concentration on any Item 2.04 carrier | GDELT |
| across the window | **0 XBRL trend deltas** — the filer stopped producing comparable period facts | `companyfacts` |

**What a reader must not conclude.** The absence of trend deltas is not
evidence that the financials are stable. It is an **absence**, and the payload
says so rather than scoring it as zero — the standing rule from rung 9, arriving
here on a new axis.

### A.4 The contrast case — Murphy Oil `QBKYQD0ODE7DC7PDIN91`

**Two** Item 2.04 events in the window (2024-12-06 and 2026-01-08), **13** 8-K
events in total, **7** media mentions and **11** trend deltas. Every class is
populated and they broadly agree. This is what a well-evidenced name looks like,
and it is in the specification so the Tupperware case has something to be
contrasted against.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Schema** | `credit-risk.early-warning` — entities: `LegalEntity`, `WarningSignal`, `SignalSource`, `PriorObservation`; relationships: `signalAbout`, `triggeredBy`, `supersededBy`; measures: composite warning score, contributing signals with class, weight, age, decayed contribution and source |
| **Freshness SLA** | Event-driven; sweep cadence daily |
| **TTL** | 6 hours · `ttl_anchor: from_decision` |
| **Policy binding** | Entitlement scope; signal weights and escalation thresholds bound to `intent` |
| **Lineage** | `operators_invoked` = the SDK's own set · `policy_bundle_versions` · `graph_snapshot_at` |
| **Semantic version** | `v1.0.0` |
| **Discovery** | `credit-risk.early-warning.v1` |
| **Addressability** | `/context-products/credit-risk/early-warning/{lei}` |
| **Assembly mode** | 1 — pure algorithmic. No model in the path |

### B.2 Request parameter surface

The four §6.3 axes are `ProductRequest` **fields** — `subject`, `intent`,
`freshness`, `asked_at`. Everything else rides in `parameters`.

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `obligors` | list, required | the policy operator's admitted set | — |
| `intent` | **field** | selects the weight and threshold set | `daily-sweep` |
| `since` | date | the delta's left edge | the obligor's prior-observation anchor |
| `signal_types` | list | filter | all five |
| `min_contribution` | decimal | filter on decayed contribution | `0` |
| `explain` | bool | payload shape | `true` |
| `debt_tolerance` | decimal | the caller's ceiling on `D_c` | — |

**`since` defaults to the prior-observation anchor, not to a fixed lookback**,
because the product is a delta and a delta needs a prior. **Measured limitation:
all 50 anchors carry `validFrom 2024-08-19`** — one seeded cold-start point, not
a per-obligor sweep history. So the default delta is the full window for every
obligor, and a shorter delta must be asked for explicitly (`CP11-F-03`).

### B.3 THE DELTA IS ON VALID TIME, NOT ON LEDGER `t`

The article specifies step 3 as *"a delta query against two ledger points, not a
lookback window."* **That is not available on this estate, and the substitution
is declared here rather than made silently.**

Measured: the ledger head is `t = 5729`. Pinned reads at successive `t` give the
`WarningSignal` population as **0 before `t = 421`, all 538 by `t = 491`, and
538 at every point thereafter** — the entire signal population arrives in one
bulk load and nothing is ever added. Its siblings land in the same band:
`SignalSource` complete by `t = 421`, `PriorObservation` by `t = 422`.

**A ledger-point delta over this estate returns everything or nothing.** It
cannot express the product.

**What does work is the world clock.** `signal_event.observed_at` spans
**2024-08-19 → 2026-08-19** and the anchors sit at 2024-08-19. So the delta is
defined as:

> the signals whose **source observation date** falls in
> `(since, asked_at]` — a valid-time interval, evaluated as of the decision
> instant.

This is the rung-9 discipline (`D-IMPL-331`/`332`) applied to a delta rather
than to a decay: **the question is about the world, so it is asked against the
world's clock.** `CP11-F-06` records that the ledger axis was measured and
rejected, so a later reader does not assume it was never considered.

### B.4 Time semantics, enumerated

| Clock | Where it lives | Used for |
|---|---|---|
| **World / source valid-time** | `signal_event.observed_at` (a `date`), `SignalSource.validFrom` | the delta bound, and the decay basis for every decaying class |
| **Fabric-learning time** | `filing_profile.retrieved_at` — **a single value, 2026-08-16, for all 50 rows** | provenance only. Never a decay basis |
| **Assertion / booked time** | Fluree `assertedAt` exists (7,232 assertions) but **not on `WarningSignal`** | not available for signals; absent rather than substituted |
| **Supersession / effectivity** | `supersededBy` on 486 of 538 `WarningSignal` nodes | ends a non-decaying signal's relevance |
| **Reporting-period time** | `trend_delta.period_end` / `prior_period_end` | the trend class's own subject; never confused with when it was observed |
| **`as_of`** | `ProductRequest.asked_at`, from the caller | bounds every read. Nothing later is knowable |

**A measured shape worth stating plainly: the Fluree `WarningSignal` node
carries no timestamp at all.** Its predicates are `rdf:type`, `rdfs:label`,
`provenance`, `signalAbout`, `triggeredBy` and `supersededBy` — the date appears
only inside the label *string* (`"8-K item 1.01 signal — … (2025-03-05)"`).
**The dated leg is PostgreSQL.** The graph carries identity, attribution and the
supersession chain; the relational store carries the clock. Parsing a date out
of a label is forbidden by `CP11-F-07`.

---

## C · Data catalog

### C.1 Element table

| Element | Provenance | Class | Store | `G` |
|---|---|---|---|---|
| 8-K events by item (1.01 · 2.03 · 2.04 · 4.01 · 5.02) | public | `8k_event` | Postgres `signal_event` | `E`,`T` |
| 8-K signal identity and supersession chain | synthetic — internal | `WarningSignal` | **Fluree** | `E`,`R`,`T` |
| Filing that triggered a signal | public | `SignalSource` | **Fluree** | `E`,`R`,`T` |
| Adverse media mentions | public | `adverse_media` | Postgres | `E`,`T` |
| WARN Act notices and their matches | public | `warn_notice` | Postgres | `E`,`T` |
| Issuer-specific spread widening | synthetic — engineered | `spread_widening` | Postgres | `E`,`T` |
| XBRL period-over-period deltas | public | `trend_delta` | Postgres | `E` |
| Signal weights and decay, by type × sector | synthetic — internal | policy | Postgres | `P` |
| Escalation thresholds by intent | synthetic — internal | policy | Postgres | `P` |
| Prior-observation anchors | synthetic — internal | `PriorObservation` | **Fluree** | `T` |

### C.2 The population, measured 2026-09-12

```
anchor obligors                      50   (legal_entity.is_anchor)
signal_event                      1,603   2024-08-19 .. 2026-08-19
  8k_event                          534   49 obligors
  adverse_media                     654   30 obligors
  trend_delta                       383   47 obligors
  spread_widening                    27   ~15 obligors
  warn_notice                         5    4 obligors
8-K items, dated:  1.01 220 · 5.02 184 · 2.03 120 · 4.01 6 · 2.04 4
signal_weight        45 rows = 5 classes × 9 sectors
escalation_threshold  6 rows, 3 intents
Fluree WarningSignal   538  (486 superseded, 52 current)
Fluree SignalSource    409
Fluree PriorObservation 50  (all validFrom 2024-08-19)
warn_notice          3,514   warn_match 36  (32 ambiguous, 4 resolved)
gdelt_mention          951   30 obligors; 49 carry a down-weight factor
```

**The two stores join on `signal_id`**: `signal_event.signal_id` is the local
part of the `WarningSignal` IRI (`sig-8k-02a95d9e9460`). Verified.

**The supersession chain covers `8k_event` and nothing else** — 534 of 534
mirrored into Fluree. The three non-8-K nodes in the graph are the engineered
composite-case seeds. This is not an oversight: **the 8-K class is the one with
no decay, and supersession is what bounds it.**

### C.3 Correlation key and identity authority

`LEI` → `CIK` for filings, through `filing_profile`. Entity **name matching**
for WARN notices and GDELT, which is lossy — and §C.4 TRAP 4 measures exactly
how lossy.

### C.4 The data traps

Five, and **all five were run during Gate-1 measurement**. Two of them are the
author's own failed readings, recorded rather than quietly corrected.

**TRAP 1 — "no decay" read as "accumulates forever".**
`signal_weight.decay_days` is `NULL` for all nine `8k_event` rows. Summing every
8-K at full weight puts **30 of 50 obligors over the board-risk threshold and 48
of 50 over the sweep threshold**. The routine 220 Item 1.01 and 184 Item 5.02
filings drown the 4 Item 2.04 accelerations. *No decay* means *time does not end
its relevance*; it does not mean *nothing ends its relevance*. **Binding:**
supersession bounds the 8-K class, and `RSM`-style leading-edge selection is how
(§E.1).

**TRAP 2 — supersession applied to a threshold calibrated without it.** The
corrected reading drops the maximum composite from 3.1415 to 0.3694, and **no
obligor reaches the credit-committee threshold of 0.55 or the board threshold of
0.85**. A control that never fires demonstrates as little as one that always
does. **Binding:** §E.2 declares recalibrated illustrative thresholds under
`D-IMPL-323`, labeled at every site.

**TRAP 3 — the lifetime census read as the actionable population.**
`filing_profile.count_8k_item_2_04` says **16 obligors** carry an acceleration
filing, with Murphy Oil at 10. Only **3 obligors have one inside the two-year
window**, and only **4 dated events exist in total**. The profile counts a
company's whole EDGAR history; `signal_event` carries the window. The ratio is
stable across item types — **1.01: 13.5% · 2.03: 15.2% · 2.04: 9.1%** — which is
what proves it is a window effect rather than a load defect. **Binding:** the
product reads dated events. A count is never a population.

**TRAP 4 — accepting an ambiguous name match.** `warn_match` holds 36 rows:
**32 `ambiguous` and 4 `resolved`.** The ambiguous ones are wrong, and
visibly so at score ≈ 0.71:

| anchor | matched employer | score |
|---|---|---|
| TransDigm Group INC | **Transdev** | 0.7059 |
| B&G Foods, Inc. | **US Foods, Inc.** | 0.7059 |
| SP Plus Corp | **Lamps Plus** | 0.7059 |
| MUELLER INDUSTRIES INC | **Pride Industries** | 0.7059 |
| Caesars Entertainment, Inc. | **Sony Pictures Entertainment** | 0.7083 |

Accepting them attributes other companies' layoffs to these obligors.
**Measured: only the 4 resolved matches became signals**, which is the estate
already holding the right line. **Binding:** the product consumes `resolved`
matches only, and the payload publishes the ambiguous count so the reader can
see what was withheld and why — an absence with a reason, not a silence.

**TRAP 5 — a field that looks like a measurement and is a query.**
`gdelt_mention.tone` reads like a sentiment score. **All 951 rows carry the
identical literal string `<-5`** — the GDELT query filter that selected the
corpus. Weighting a mention by its "tone" would be weighting every mention by a
constant while appearing to discriminate. **Binding:** the product does not
consume `tone`. Media weight comes from the class weight and the count, with the
49 down-weighted mentions honored at their declared factor.

---

## D · Assembly recipe

### D.1 The unit of analysis is the OBLIGOR, and unlike rung 10 that is the source's own unit

`signal_event` carries `lei` and no facility, instrument or account key. That is
not a limitation to work around — it is what the signals **are**: an 8-K is
filed by a company, a WARN notice names an employer, a media mention names a
company, an XBRL delta is a company's own period-over-period change.

**The one class that reaches further is `spread_widening`**, whose `source_ref`
carries `instrument_ids` on 26 rows — inherited from rung 10, where the bond is
the unit. **It is carried through, never averaged into the obligor figure
before detection** (rung 10's `CP10-F-06`, arriving here as an inherited
discipline): where a spread signal names instruments, the payload names them.

**`include_family` is deliberately NOT in this product's parameter surface.**
The article offers it, and summing a composite score across a corporate family
is exactly the aggregation that rung 10 established destroys the phenomenon: a
family total cannot say *which member moved*. Family scope is
`corporate-family-tree`'s answer, and composing the two is a Tier-5 question.

### D.2 Operator step table

| # | Operator | Store | What it does |
|---|---|---|---|
| 1 | `policy.principal-subgraph` | — | admits only the obligors the effective request names |
| 2 | `traversal.typed-neighborhood` | Fluree | the signal subgraph: `signalAbout`, `triggeredBy`, `supersededBy` |
| 3 | Π `CreditSurveillanceProjection` | in-memory | the delta, the supersession filter, the decayed contributions, the composite and the escalation band |

The deployment authors **no operator set**: the plan factory passes the
resolver's own `required` tuple through, as rungs 9 and 10 do.

### D.3 The computation

1. **Bound the delta.** Signals whose `observed_at` is in `(since, asked_at]`.
   `since` defaults to the obligor's `PriorObservation.validFrom`.
2. **Apply supersession to the non-decaying class.** An `8k_event` whose
   `WarningSignal` carries `supersededBy` contributes **nothing** — it has not
   aged, it has been replaced. Every other class carries its full history into
   the decay curve.
3. **Decay each remaining signal** against its own class λ_c and the
   **source observation date**, never the ingestion instant.
4. **Weight** by `(signal_type, sector)` from the policy-versioned table.
5. **Sum** the decayed contributions into the composite.
6. **Band** against the `intent`'s escalation threshold.
7. **Explain.** Every contributing signal with its class, weight, age, decayed
   contribution and source — and every signal that was *excluded*, with the
   reason: superseded, out of delta, out of severity, or an ambiguous match.

**Step 7's exclusion list is load-bearing.** A composite that reports only what
counted cannot be audited; the question *"why did this name not escalate"* is
answered by what was left out.

### D.4 The scenarios

**Scenario 1 — the accumulating score.** Any obligor, full window, supersession
**off**: the composite reaches 3.1415 at the top and 30 of 50 breach the board
threshold. Supersession **on**: the maximum is 0.3694. The same instant, the
same weights, the same curves. Only the *set* changed.

**Scenario 2 — the thinly-evidenced name.** Tupperware `G8NWFN4YP7CR6FOP4886`:
an Item 2.04 at severity 1.0, 23 media mentions, **0 trend deltas**. The payload
reports the trend class as **absent**, not as zero.

**Scenario 3 — the well-evidenced contrast.** Murphy Oil
`QBKYQD0ODE7DC7PDIN91`: 2 Item 2.04s, 13 8-K events, 7 mentions, 11 trend
deltas. Every class populated.

**Scenario 4 — the composite.** Measured: **18 obligors carry ≥3 distinct
signal classes inside one 30-day window**, 24 at 60 days, 25 at 90. The
product's core argument — that individually unremarkable signals compose — has
18 real instances and needs no engineering.

**Scenario 5 — re-derivation, which is what replaces the cascade.** Ask, ingest
a superseding claim, ask again at the same `as_of`, and observe the composite
change and the content address differ. **This demonstrates that the answer is
re-derived from a graph that honors supersession. It does not demonstrate a
cascade, and §0.4 says why.**

### D.5 Determinism and replay

**Determinism class: `deterministic`.** `payload_hash` is `sha256` over the
canonical bytes excluding `assembled_at`.

Replay: serve at a pinned `as_of`, re-serve at the same instant and confirm the
hash; re-serve at an `as_of` **before** a superseding filing and confirm the
superseded signal is **present and current** at that instant; return to the
original and confirm the original hash. If the third step does not differ from
the first, `as_of` is not reaching the supersession filter.

### D.6 Validation gates

Six universal — empty-operator guard, lineage strict equality, TTL bounds, debt
gate, suppression silence, classification containment — then the
product-specific set at §G.1.

**Error mapping.** `404` unknown obligor · `403` not entitled, no detail ·
`409` debt gate · `503` a mandatory source class unavailable, named · `200` with
notices otherwise. An obligor with **no signals in the delta** is `200` with a
composite of zero and an explicit `no-change` finding — **not** an error, and
not an empty payload.

---

## E · Volatility, debt and materialization

### E.1 Half-life table

> **Illustrative calibration.** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the governed
> behavior observable in that snapshot. They demonstrate how the SDK applies
> these controls and should not be interpreted as recommended production
> coverage-policy thresholds.

| Signal class | `λ_c` | `decay_basis` | `freshness_over` | Series key | Basis | Ends when |
|---|---|---|---|---|---|---|
| `spread_widening` | **1 day** | `valid-from` | `leading-edge` | the **instrument** | measured — inherited from rung 10 | next observation |
| `adverse_media` | **7 days** | `valid-from` | `series-mean` | — | measured — `signal_weight.decay_days` | decay only |
| `trend_delta` | **90 days** | `valid-from` | `series-mean` | — | measured | next reporting period |
| `warn_notice` | **180 days** | `valid-from` | `series-mean` | — | measured | decay only |
| `8k_event` | **no decay** | `valid-from` | **`leading-edge`** | the **obligor** | measured — `decay_days IS NULL` | **supersession** |

**The `8k_event` row is the rung.** It declares `decay: supersede-only` *and*
`freshness_over: leading-edge` keyed on the obligor, and the pair is what makes
"a fact that never becomes false but can stop being relevant" expressible at
all. `supersede-only` alone would return freshness `1.0` for every one of the
534 filings — rung 10 measured exactly that shape and rejected it
(`CP10-F-07`). Leading-edge alone would decay a fact that does not decay.

**The series key is a first-class claim attribute.** For `8k_event` it is the
obligor identifier, which is a top-level claim attribute and not buried in a
serialized payload — the seam documented in `HalfLifeEntry.series_key_attribute`
and measured on rung 10. For `spread_widening` it is `instrument_id`, carried
forward from rung 10's resolution rules unchanged.

**A 180-fold spread across the decaying classes, plus one class outside the
curve entirely.** Rung 9 had four kinds of time; rung 10 had a ninety-fold
spread; this rung has both, and a class that answers to neither.

### E.2 Debt and the recalibrated thresholds

`D_c = 1 − (F · C · S)`, multiplicative.

- **F — freshness.** Over the **leading edge of each series** for the two
  leading-edge classes, and over the participating observations for the three
  `series-mean` classes, each against its own λ_c and the **source** clock.
- **C — completeness.** Two live terms: how many of the five signal classes the
  obligor has *any* evidence in, and whether the obligor's prior-observation
  anchor resolves. Tupperware exercises the first — it is missing a class.
- **S — semantic consistency.** Whether every consumed signal resolves to a
  source: an 8-K to its accession, a WARN notice to a **resolved** match. An
  ambiguous match is a consistency *finding*, not a silent drop.

**THE ESCALATION THRESHOLDS ARE RECALIBRATED, AND THE MEASUREMENT THAT FORCED IT
IS §C.4 TRAP 2.** The estate declares 0.30 / 0.55 / 0.85, which were calibrated
against the accumulating reading. Under the correct reading the maximum
composite over the full window is **0.3694**, so the upper two bands are
unreachable. The product declares, as demonstration values:

| Band | Declared in estate | **This product** | Obligors reached (measured, full window) |
|---|---|---|---|
| `daily-sweep` | 0.30 | **0.15** | **25** of 50 |
| `credit-committee-referral` | 0.55 | **0.25** | **8** of 50 |
| `board-risk-report` | 0.85 | **0.35** | **2** of 50 |

The full measured curve, so a later reader can see why these three and not
others — and can re-derive them rather than trusting the table:

```
threshold   0.05  0.10  0.15  0.20  0.25  0.30  0.35  0.40
obligors      48    45    25    14     8     3     2     0
                          ^sweep     ^committee  ^board
```

`0.10` was the first value tried for the sweep band and it was **wrong** — it
reaches 45 of 50, which is the TRAP-1 failure arriving at a lower number. The
band has to leave something out to mean anything.

**All three fire, and they discriminate** — roughly half the book, then a sixth,
then two names. The four conditions of `D-IMPL-323`
are met: the mechanism is observable, the calculation is untouched — only the
declared threshold moves, never a timestamp or an `asked_at` — the term is shown
ordering two real subjects, and the value is disclosed here, in the artifact
that declares it, and in the README. **Gate `EWS-G12` asserts the ORDERING and
the BAND COUNTS being non-degenerate, never the numbers**, so the estate may
grow without making the gate wrong.

### E.3 Materialization and TTL

**Derived on demand.** The product *is* a delta; a materialized delta is a
contradiction — and §0.4 is the harder version of the same point: there is no
product cache in the SDK to materialize into.

TTL 6 hours, `ttl_anchor: from_decision`, ceiling one day. A request pinned to a
past `as_of` is a forensic reconstruction and does not decay.

### E.4 What invalidates a served answer

**Nothing, actively — and that is the honest statement.** A served answer stops
being current when a superseding filing lands, and **the fabric has no way to
tell a holder of that answer.** The holder learns by asking again. §0.4 is the
mechanism; this row is its consequence stated where a consumer will hit it.

---

## F · Findings

| id | finding | status |
|---|---|---|
| `CP11-F-01` | **The article's central mechanism — supersession-driven cache-invalidation cascade — does not exist in the SDK.** Verified across `src/` and `runtime/`: no product cache (only a per-execution operator memo whose docstring defers the invalidation story to `D-IMPL-36`), no Control Plane event propagation, no reverse index from entity to the products that touched it, and an ArtifactStore with no delete by design. `decay: supersede-only` is purely a half-life mode returning `Decimal(1)`. The product is specified without step 7, and §D.4 scenario 5 substitutes **re-derivation on next request**, named as such. | **OPEN — SDK GAP** |
| `CP11-F-02` | **Both readings of the composite are unusable as the estate declares them.** Naive accumulation: 30/50 over board-risk. Supersession applied: 0/50 over credit-committee. The mechanism is right; the thresholds were calibrated against the wrong reading. §E.2 recalibrates under `D-IMPL-323`. | FIXED-gate-1 |
| `CP11-F-03` | **All 50 prior-observation anchors carry the same `validFrom` (2024-08-19).** The estate seeds one cold-start point per obligor, not a sweep history, so the default delta is the full window for every obligor. A shorter delta must be requested. | ESTATE-LIMITATION |
| `CP11-F-04` | **`gdelt_mention.tone` is a query filter, not a measurement.** All 951 rows carry the identical string `<-5`. Per-mention tone weighting is not computable and the product does not claim it. | ESTATE-LIMITATION |
| `CP11-F-05` | **No Item 4.02 non-reliance events.** Two obligors carry a lifetime 4.02 count; zero dated events exist in the window. The auditor leg is Item 4.01 only — 6 events, 5 obligors. | ESTATE-LIMITATION |
| `CP11-F-06` | **The ledger `t` axis carries no delta.** Measured by pinned read: 0 `WarningSignal` before `t=421`, all 538 by `t=491`, 538 at every point to the head at `t=5729`. The article's "delta between two ledger points" would return everything or nothing. The delta is defined on **valid time** instead, and §B.3 declares the substitution rather than making it silently. | ESTATE-LIMITATION |
| `CP11-F-07` | **The Fluree `WarningSignal` node carries no timestamp**; the date appears only inside its `rdfs:label` string. The dated leg is PostgreSQL and the graph carries identity, attribution and the supersession chain. Parsing a date out of a label is forbidden — a label is prose, not a clock. | ESTATE-LIMITATION |
| `CP11-F-08` | **32 of 36 WARN name matches are wrong and visibly so** (TransDigm→Transdev, B&G Foods→US Foods, SP Plus→Lamps Plus, at score ≈0.71). Only the 4 `resolved` matches became signals — the estate already holds the line. The product consumes `resolved` only and publishes the ambiguous count. | NOT-A-GAP |

---

## G · Gates

### G.1 The declared set

| id | statement | what it catches |
|---|---|---|
| `EWS-G01` | a plan with zero operator steps never serves | empty-operator |
| `EWS-G02` | served lineage equals the plan's typed operator references; `ProductLineage` is exactly three fields | lineage drift |
| `EWS-G03` | `expires_at` derives from the decision instant and respects the ceiling | TTL fabrication |
| `EWS-G04` | `D_c` above tolerance refuses with the debt block | ungated debt |
| `EWS-G05` | a non-admitted obligor leaves no name, count or marker in the payload | disclosure by marker |
| `EWS-G06` | payload classification is the highest contributing | classification leak |
| `EWS-G07` | a **superseded** `8k_event` contributes **zero** to the composite, and appears in the exclusion list with reason `superseded` | TRAP 1 — no decay read as accumulation |
| `EWS-G08` | a superseded signal is **not** reported as stale or aged; its exclusion reason is supersession and its age is reported unchanged | conflating supersession with decay |
| `EWS-G09` | every decaying class decays against the **source observation date**, never ingestion | the `D-IMPL-331` defect, reintroduced |
| `EWS-G10` | the delta's bounds are `(since, asked_at]` on **valid time**, and no signal dated after `asked_at` enters the payload | look-ahead |
| `EWS-G11` | an obligor with no signal in the delta returns `200` with an explicit `no-change` finding, never an empty payload or an error | absence read as failure |
| `EWS-G12` | the three escalation bands are each reachable and strictly ordered, and the band populations are non-degenerate | TRAP 2 — a control that never fires |
| `EWS-G13` | a signal class in which the obligor has **no evidence** is reported **absent**, never scored as zero | absence read as a measurement |
| `EWS-G14` | only `resolved` WARN matches contribute; the ambiguous count is published with its reason | TRAP 4 — a false attribution |
| `EWS-G15` | no `gdelt_mention.tone` value reaches any weight, score or payload field | TRAP 5 — a query filter read as a measurement |
| `EWS-G16` | the payload never presents a `filing_profile` lifetime count as a population of actionable events | TRAP 3 |
| `EWS-G17` | every contributing signal names its class, weight, age, decayed contribution and source | an unexplainable composite |
| `EWS-G18` | the exclusion list is served whenever `explain`, and names a reason per excluded signal | "why did this not escalate" unanswerable |
| `EWS-G19` | the four §6.3 axes are `ProductRequest` fields, absent from `parameters` | request identity demoted |
| `EWS-G20` | no date is ever parsed out of an `rdfs:label`; every instant comes from a typed field | `CP11-F-07` |
| `EWS-G21` | the payload carries no second copy of `D_c`, the content address or the policy versions | two copies of one figure |
| `EWS-G22` | the payload never claims that any downstream product was invalidated, evicted or notified | `CP11-F-01` — the gap asserted as a gate |
| `EWS-G23` | re-serving at an `as_of` before a superseding filing reports the superseded signal as **current** at that instant | `as_of` not reaching the supersession filter |
| `EWS-G24` | a `spread_widening` signal naming instruments carries them into the payload rather than collapsing to the obligor | rung 10's `CP10-F-06`, inherited |

### G.2 Acceptance

Gate 1 is Dave's ruling on §0.4 first and the rest second. **If the cascade is
required for rung 11 to count, this specification does not deliver it and says
so.** If re-derivation is an acceptable substitute, the remainder is buildable
against measured estate facts throughout.
