---
product: treasury.liquidity-position.v1
standard: v0-3
sdk_spec: cp-09
tier: 3
cost_band: "×2–4 (derived on demand)"
assembly_mode: 1
capability_classes: [relational, bitemporal-ledger, graph-traversal, in-memory]
prerequisites: [counterparty-reference-snapshot, collateral-and-setoff-coverage]
topic: context-products
title: Treasury Liquidity Position — Context Product Specification
generated: '2026-09-11'
---

# Treasury Liquidity Position — Context Product Specification

**`CP-SPEC-009` · Tier 3 · `treasury.liquidity-position.v1`**
**PostgreSQL for balances, positions, rates and limits · Fluree for the position graph and the time-versioned regulatory posture**

> **What is this client's cash and rate posture at this instant, what may they
> do with it, and how old is each thing I just told you?**
>
> One question, over four kinds of time.

## 0 · What this document is

A build specification for the engineer who will assemble this Context Product
from the treasury data estate. It states the decision the product serves, the
contract it publishes, which store each element comes from, the assembly
recipe, and the gates the finished product is held to.

Every figure below was measured against the live estate on 2026-09-11 before
this document was written, and the query that produced it is reproducible.

### 0.1 The governing principle

Ruled by Dave at Gate 1, and it is the spine of every section that follows:

> **Different context elements have different temporal semantics. `as_of`
> governs the determination, but it does not turn reporting-period dates,
> market observations, policy effectivity and timeless holdings into the same
> kind of timestamp.**

Rungs 1 through 8 each carried one clock, or two of the same kind. This rung
carries **four kinds at once**, and the product's job is to keep them apart in
the payload rather than averaging them into a single freshness claim. §D.3 is
where that becomes mechanism.

### 0.2 Placeholder discipline

No `[TBC]`. Where a value is a demonstration choice rather than a production
recommendation, §0.4 names it and says why.

### 0.3 Reads only — no write path anywhere in this product

Both source stores are read. The ledger is append-only, so a write is
permanent; nothing in this product's assembly, its examples or its tests writes
to either store. The fabric's own graph is per-run scratch and is discarded
when the run exits.

This matters to the recipe and not only to operations: §D.6's replay
demonstration and §D.4's three scenarios are all reachable by moving one
request parameter, so no scenario needs the estate mutated to produce it.

### 0.4 What is real in this estate, and what was engineered

| Element | Provenance |
|---|---|
| Daily Treasury constant-maturity and SOFR series | **public** — FRED (`DGS3MO`…`DGS30`, `SOFR`, percentiles) |
| Daily par yield curve | **public** — Treasury.gov |
| FX daily reference rates | **public** — FRED (`DEXUSEU` and siblings) |
| **Intraday rate tick series** | **synthetic, deliberately engineered** — see below |
| **Intraday FX tick series** | **synthetic, deliberately engineered** |
| **`stale_signal` fixture** | **synthetic, deliberately engineered** — the `max_staleness` case |
| Client reported cash and its period end | **public** — XBRL `companyfacts` balance-sheet anchor |
| Deposit balances, investment positions | **synthetic** — internal treasury records have no public equivalent |
| Concentration limits, permitted-instrument lists, mandates | **synthetic** — internal treasury policy |
| Regulatory posture overlay and its versions | **synthetic** — internal, time-versioned in the ledger |

**The intraday tick series is the one engineered element this product depends
on, and it is engineered because it cannot be sourced.** Treasury.gov, FRED and
the NY Fed all publish **daily**. This product's entire premise is a signal that
moves within the day. Presenting interpolated ticks as observed market data
would misrepresent the source, so every tick row carries
`provenance = 'synthetic — engineered'` and the payload repeats it.

**Measured:** 11,700 tick rows · 30 trading days 2026-05-11 → 2026-06-23 ·
5 tenors (0.25, 1, 2, 5, 10 years) · 5-minute granularity · 13:30–19:55 UTC
(09:30–15:55 ET) · 78 ticks per tenor per day · 150 distinct (day, tenor) pairs.
The vault's manufacture envelope asked for at least one day carrying an 8 bp
intraday move; the largest measured is **24.33 bp** (2-year, 2026-05-26).

**Illustrative calibration.** This example runs against a point-in-time
demonstration estate rather than continuously refreshed production data.
Freshness half-lives and related thresholds are calibrated to make the governed
behavior observable in that snapshot. They demonstrate how the SDK applies
these controls and should not be interpreted as recommended production
coverage-policy thresholds. §E.1 carries the table; §D.4 carries the decision
instants and how each was chosen.

### 0.5 The four-question test

- **Is the answer assembled rather than stored?** Yes. No store holds *"this
  client's liquidity posture at 18:05 on 2026-06-17, under the regulatory
  posture then in force."* It is a rate observation from one table, holdings
  from two more, limits from a fourth, a currency conversion from a fifth, and
  a policy version reconstructed from a ledger — with four different temporal
  semantics that must survive into the payload.
- **Does more than one consumer need it?** Yes — the treasury specialist
  advising the client, the credit officer who owns the concentration limits,
  and the control function that has to show which policy version authorized a
  position. They want the same numbers with different envelopes.
- **Does it carry a governed freshness claim?** Yes, and an asymmetric one:
  15 minutes on the rate leg, 90 days on the filing leg, a step function on the
  policy leg, and — measured — **nothing at all on the holdings leg**, because
  the estate never recorded when a balance was observed. Publishing that
  absence is part of the claim.
- **Would a `SELECT` do?** No. A `SELECT` joining balances to the most recent
  published daily curve returns a confident number that is **23.60 bp** away
  from the market at the decision instant (§A.2), reports the client compliant
  when three of its seven counterparty exposures have no limit to check against
  (§A.3), and attaches one freshness to all of it.

---

## A · Decision frame

**The decision.** A treasury specialist advising a corporate client on cash
positioning or short-duration investment — intraday, while the client waits.

**The trigger.** The client asks a question whose answer moves within the hour.

**Consuming principals.** A single role at this tier. The conversational
advisory rendering is deferred to Tier 5.

### A.1 Counterfactuals — two, and they live at two instants

The vault names two failure modes. Measurement shows they **cannot both be
demonstrated in one run**, because the estate engineered them at different
decision instants. That is a property of the data, recorded here rather than
papered over, and it is why §D.4 defines three scenarios.

**`temporally-incoherent` — Latency Poisoned.** The rate-curve refresh is
daily. The frame is *correct against its pipeline contract* and *wrong against
the decision at hand*. Nothing is broken; the pipeline delivered exactly what
it promised, and the promise was the wrong one. Every system reports healthy.

**`policy-blind` — the limit that was never checked.** The agent reports a
client's concentration as compliant. Access control said yes. But three of the
client's seven counterparty exposures have **no concentration limit on file**,
and one of those three is larger than two of the limits that do exist. The
naive answer and the governed answer differ not in the numbers they compute but
in **what they admit they could not check**.

### A.2 The worked case — Latency Poisoned, measured

Anchor: `2549004GGE2APGNT6O92` (American Healthcare REIT, Inc.), the one
treasury client holding US-NY deposits under a `reserve-buffer` mandate.

Decision instant: **2026-06-17T18:05:00Z** (14:05 ET).

| | value | source |
|---|---|---|
| 2-year rate the product serves | **4.285995 %** | `intraday_tick`, `obs_ts = 2026-06-17T18:05Z` |
| 2-year rate the daily pipeline serves | **4.05 %** | `reference_rate`, `DGS2`, most recent *published* `obs_date = 2026-06-16` |
| **gap** | **23.60 bp** | measured |

The acceptance test, as a procedure that can fail:

1. Serve the product at `as_of = 2026-06-17T18:05:00Z`.
2. Read the 2-year rate the payload carries and its `observed_at`.
3. Independently read the most recent `reference_rate` row for `DGS2` with
   `obs_date < 2026-06-17`.
4. **Assert the two differ by at least 8 bp, and assert the served value is the
   tick.** If they agree, the product is reading the daily series and the
   intraday leg is decorative.

This is `TLP-G11`.

### A.3 The worked case — Policy Blind, measured

Same anchor, same instant. Fourteen positions, 2,630,266,766.99 in notional
across **seven** counterparties, against **four** concentration limits.

| counterparty | share of notional | limit | verdict |
|---|---|---|---|
| `JJAX4X60DE65EYFOTY73` | 30.21 % | 30.2 % | **breach** |
| `549300EZQXWQI2YL1T80` | 17.08 % | — | **limit-unknown** |
| `0IDE18EMH1CUKQCUYE69` | 16.73 % | 18.7 % | within-limit |
| `529900E95812SYWMCE44` | 12.55 % | — | **limit-unknown** |
| `549300DUOO1KXOHPM605` | 11.87 % | 15.7 % | within-limit |
| `549300EC266625K12S42` | 11.52 % | 24 % | within-limit |
| `5493004PFHUPOR1PWN79` | 0.03 % | — | **limit-unknown** |

**The second-largest exposure this client holds has no limit to check it
against, and it is larger than two of the limits that exist.** A product with
two verdicts — breach and within-limit — reports six of seven as fine. A
product with three verdicts reports one breach, three within limit, and **three
it could not evaluate**, and publishes the coverage figure: **4 of 7
counterparties** here, **60 of 103 (holder, counterparty) pairs** estate-wide.

The acceptance test:

1. Serve the product for the anchor.
2. **Assert the payload distinguishes three verdicts, and that the count in
   each is 1 / 3 / 3.**
3. **Assert the payload publishes limit coverage as a ratio.**
4. Sabotage: collapse `limit-unknown` into `within-limit` and confirm the gate
   turns red.

This is `TLP-G12` and `TLP-G13`. No allocation optimizer is built — ruled at
Gate 1 (Q2 a). The demonstration uses the client's **real holdings**, so no
business logic is invented in example code.

### A.4 Scope boundary

**From the vault, verbatim:** a corporate client's cash, rate, and concentration
posture right now.

Checked against this specification's §C and payload, three boundaries are drawn
explicitly:

- **No allocation proposals.** The vault's parameter surface carries
  `include_proposals`. It is declared and **refuses with
  `not_supported_at_tier`** (§B.2) rather than silently returning nothing.
  Generating candidate allocations requires an optimization policy that is
  domain configuration, not SDK mechanism.
- **No FX exposure product.** Currency conversion happens so liquidity can be
  expressed in one currency; the FX *position* question is rung 12's.
- **No collateral or set-off computation.** `deposit_account` carries
  `setoff_contractual` and `setoff_enforceable`, and 73 of 120 deposits carry a
  `nettedUnder` edge. That is rung 6's subject. This product reads the flags
  through and does not net.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Schema** | `treasury_liquidity_position` — entities `cmns-org:LegalEntity`, `fibo-fbc-pas-caa:DepositAccount`, `fibo-fbc-pas-caa:InvestmentAccount`, `fibo-sec-dbt-bnd:TreasuryBill`, `fibo-sec-fun-fun:MutualFund`, `fibo-sec-dbt-tsd:CommercialPaper`; relationships `ex:heldAt`, `ex:concentratedIn`, `ex:setOffAgainst`; policy `ex:RegulatoryPosture`. Machine-readable at `schemas/treasury_liquidity_position.v1.json` |
| **Freshness SLA** | **Per signal class, four classes, never one figure** — §D.3. Intraday rate 15 min · FX 1 day · policy effectivity a step function · holdings **unobserved** |
| **TTL** | 15 minutes · `ttl_anchor: from_decision`. `expires_at = decision_instant + 15m`. A request pinned to a past `as_of` is a forensic reconstruction and **does not decay**; the payload says so rather than publishing a window that misdescribes it (§E.3) |
| **Policy Binding** | Entitlement scope · counterparty concentration limits · permitted-instrument list by mandate · **regulatory posture resolved at the decision instant from the ledger**, emitting `policy_version` |
| **Lineage** | `operators_invoked[]` as typed references · `graph_snapshot_at` (ledger `t`) · `policy_version` · `projection_plan_id` · **per-signal `observed_at` with its `temporal_class`** · `context_debt` · `payload_hash` · `model_record` |
| **Semantic Version** | `v1.0.0` |
| **Discovery** | `treasury.liquidity-position.v1` |
| **Addressability** | `/context-products/treasury/liquidity-position/{lei}` |
| **Assembly Mode** | **1 — no model in the trust path.** Every figure is arithmetic over typed inputs. Chosen for determinism: a product whose whole claim is *how old is each number* cannot have a generative stage that could smooth two ages into one sentence |

`extra=forbid` on every payload model, validated at the boundary.

### B.2 Request parameter surface

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `lei` | string(20), required | `E` anchor | — |
| `intent` | enum `operating-liquidity` \| `reserve-buffer` \| `short-term-investment`, required | `P` — selects the limit regime and the posture row | — |
| `as_of` | datetime | **`T` — the decision instant** | request time |
| `max_staleness` | duration | **`T` — the fail-closed bound** | `15m` |
| `currencies` | list | `R` scope | all held |
| `debt_tolerance` | float | `P` — debt gate | `0.25` |
| `horizon` | enum `intraday` \| `t+1` \| `t+30` | `T` window | `intraday` |
| `include_proposals` | bool | — | **inert — refuses `not_supported_at_tier`** |

**`as_of` is the product's defining parameter and it governs four things at
once**: which tick is read, which posture version is in force, which FX
observation applies, and what the mandate tenor bound is measured from. It does
**not** move the holdings, which carry no observation time — and it does not
relabel `cash_fact_asof`, which is a period end (§D.3).

**`max_staleness` is the second.** If any *freshness-bearing* signal is older
than the bound, the product **fails closed** — an error naming the stale signal
and its age. It does not serve a partial product and it does not substitute the
last good value. A treasury product that quietly substitutes yesterday's curve
is more dangerous than one that refuses, because the substitution is invisible
and the refusal is not.

---

## C · Data catalog

### C.1 Element table

| Element | System of record | Provenance | Classification | Capability | `G` | Ontology IRI |
|---|---|---|---|---|---|---|
| Client treasury registration, intent, mandate | PostgreSQL `ccf_v2.treasury_client` | internal-SOR (synthetic) | internal | relational | `E`, `P` | `cmns-org:LegalEntity` |
| Reported cash and its period end | PostgreSQL `ccf_v2.treasury_client` | public-filing | public | relational | `E`, `T` | `fibo-fnd-acc-cur:CashInstrument` |
| Deposit balances, currency, jurisdiction | PostgreSQL `ccf_v2.deposit_account` | internal-SOR (synthetic) | internal | relational | `E` | `fibo-fbc-pas-caa:DepositAccount` |
| Investment positions, notional, maturity | PostgreSQL `ccf_v2.investment_position` | internal-SOR (synthetic) | internal | relational | `E` | `fibo-fbc-pas-caa:InvestmentAccount` |
| Intraday rate tick series | PostgreSQL `ccf_v2.intraday_tick` | derived (engineered) | public | relational | `E`, `T` | `fibo-ind-ir-ir:ReferenceInterestRate` |
| Daily reference rate series | PostgreSQL `ccf_v2.reference_rate` | public-filing | public | relational | `E`, `T` | `fibo-ind-ir-ir:InterestRateBenchmark` |
| FX daily reference rates | PostgreSQL `ccf_v2.fx_reference_rate` | public-filing | public | relational | `E`, `T` | `fibo-fbc-fi-fi:ExchangeRate` |
| Deliberately stale signal fixture | PostgreSQL `ccf_v2.stale_signal` | derived (engineered) | public | relational | `T` | `fibo-ind-ir-ir:ReferenceInterestRate` |
| Counterparty concentration limits | PostgreSQL `ccf_v2.concentration_limit` | internal-SOR (synthetic) | internal | relational | `P` | `ex:ConcentrationLimit` |
| Permitted-instrument list by mandate | PostgreSQL `ccf_v2.permitted_instrument` | internal-SOR (synthetic) | internal | relational | `P` | `ex:PermittedInstrument` |
| Position graph — `heldAt`, `concentratedIn` | Fluree `fibo-v2` | internal-SOR (synthetic) | internal | graph-traversal | `R` | `ex:heldAt`, `ex:concentratedIn` |
| Deposit graph — `setOffAgainst`, `nettedUnder` | Fluree `fibo-v2` | internal-SOR (synthetic) | internal | graph-traversal | `R` | `ex:setOffAgainst` |
| **Regulatory posture, time-versioned** | Fluree `fibo-v2` | internal-SOR (synthetic) | internal | **bitemporal-ledger** | `P`, `T` | `ex:RegulatoryPosture` |
| Counterparty identity | Fluree `fibo-v2` + PostgreSQL `ccf_v2.legal_entity` | vendor (GLEIF) | public | graph-traversal, relational | `E` | `cmns-org:LegalEntity` |

Deployment detail — host, port, credential — appears nowhere in this
specification, in the example tree, or in any artifact. `backends.yaml` carries
environment-variable **names** only.

### C.2 The population, measured 2026-09-11

| | measured |
|---|---|
| Treasury clients | **15**, all resolving in `ccf_v2.legal_entity` |
| Intents | 5 each of `operating-liquidity`, `reserve-buffer`, `short-term-investment` |
| Deposit accounts | **120** · 4 currencies (JPY 32, GBP 30, EUR 29, USD 29) · 8 jurisdictions · 7–9 per client |
| Investment positions | **200** · 3 kinds (T-bill 70, MMF 68, CP 62) · 13–14 per client · 45 counterparties, **45 of 45 resolving** |
| Concentration limits | **60** · exactly 4 per client · every limit row matches a real position pair · **60 of 103 position pairs covered** |
| Permitted-instrument rows | **45** — all 15 mandates permit all 3 kinds at **365 days** |
| Intraday ticks | **11,700** · 30 days · 5 tenors · 5-minute |
| Daily reference rates | **10,539** · 16 series · 659 dates · 2024-01-02 → 2026-08-20 |
| FX daily | **3,942** · 6 pairs → 2026-08-14 · FX intraday **10,368** · 2026-08-06 → 08-13 only |
| `stale_signal` | **4** rows, own `as_of` 2026-08-21T16:00Z · ages 45.0 / 2.5 / 1.28 / 1.55 min |
| Regulatory postures | **13** nodes over **12** occurring (jurisdiction, intent) pairs |
| **Posture versions** | **exactly one pair is versioned** — `US-NY / reserve-buffer`: `standard` from 2024-01-02, `enhanced-scrutiny` from **2026-06-16** |
| Concentration breaches on real holdings | **10 pairs across 9 clients** |
| Mandate tenor exceedances at 2026-06-17 | **34 of 200 positions** |

### C.3 Correlation key, single-writer, identity authority

**Key.** `LEI` end to end. Client → `treasury_client.lei` → `deposit_account.holder_lei`
→ `investment_position.holder_lei` → `investment_position.counterparty_lei` →
`legal_entity.lei`. In the ledger, counterparty nodes carry `ex:lei`, so the
graph and relational legs join on the same authority with no crosswalk.
**Measured coverage: 15 of 15 clients and 45 of 45 counterparties resolve.**

**Identity authority.** GLEIF for counterparty identity; the internal treasury
register for client registration and mandate. These are different authorities
with different freshness ceilings and the payload does not average them.

**Single writer.** Nothing here writes. Both legs are read through L2 into the
per-run fabric graph; the ArtifactStore holds the served product and its replay
record. No harness and no operator acquires a write handle.

### C.4 The data traps

Six, each with the binding chosen and what the choice costs.

- **`heldAt` and `concentratedIn` are the same edge, twice.** Both exist on all
  200 `InvestmentAccount` nodes, and **0 of 200 diverge**. The vault's design
  treats them as two relationship types; the estate materializes one relation
  under two names. **Binding:** read `ex:concentratedIn` for the concentration
  question, record which predicate answered, and do **not** compose the two as
  if they carried different information. **Cost:** the traversal is one hop, not
  two, and the product says so (`TLP-G18`).
- **Holdings carry no observation time.** `deposit_account` and
  `investment_position` have no timestamp column at all. **Binding:** a fourth
  temporal class, `unobserved-holding`, with no `observed_at` and no
  contribution to the freshness term. **Cost:** the product cannot make a
  freshness claim about the client's own balances, and it publishes that
  absence rather than inheriting the request time (`TLP-G15`). This is the
  sharpest finding in the estate and it contradicts the vault's "deposit
  balances ~1 hour" row, which assumed a timestamp that is not there.
- **`cash_fact_asof` is a reporting-period end, not an observation instant.**
  Measured values are 2022-12-31, 2025-09-30, 2026-03-31 (×3), 2026-06-27,
  2026-06-30 (×9) — quarter ends from XBRL `companyfacts`. **Binding:**
  `temporal_class: reporting-period-end`, its own slow λ_c, never decayed as a
  market observation. **Cost:** one client's reported cash is 3.5 years old, and
  the payload shows that beside a 15-minute rate — which is the asymmetry the
  rung exists to make visible.
- **The permitted-instrument *kind* check is vacuous; the *tenor* check is
  not.** All 15 mandates permit all 3 instrument kinds, so no position is ever
  refused on kind. The 365-day maximum tenor does bite: **34 of 200** positions
  exceed it at 2026-06-17, including 2 of the anchor's 14. **Binding:** run both
  checks and report them separately, so a reader can see which one discriminated.
  **Cost:** honesty about a control that never fires in this estate.
- **The intraday series, the FX intraday series, the daily series, the stale
  fixture and the filing dates occupy five different time universes.** Latest
  tick 2026-06-23; FX intraday 2026-08-06→08-13; FX daily → 2026-08-14; daily
  rates → 2026-08-20; the stale fixture pinned at 2026-08-21. **Binding:** three
  pinned scenarios (§D.4), each chosen from a measurement. **Cost:** there is no
  single instant at which the whole product is live, and pretending otherwise
  would make every answer `fail_closed` — the cp-07 failure, avoided by ruling
  rather than by luck.
- **Concentration limits cover 58 % of exposure pairs.** 60 of 103. **Binding:**
  a third verdict, `limit-unknown`, and a published coverage ratio. **Cost:**
  the product cannot say "compliant"; it says "1 breach, 3 within limit, 3 not
  evaluable, coverage 4/7."

---

## D · Assembly recipe

### D.1 Client call

The forensic case, because it exercises the most surface:

```
GET /context-products/treasury/liquidity-position/2549004GGE2APGNT6O92
      ?intent=reserve-buffer
      &as_of=2026-06-17T18:05:00Z
      &max_staleness=15m
      &debt_tolerance=0.25
```

### D.2 Step table

| # | Operator | Capability | Inputs | Emits | Failure behavior | p95 budget |
|---|---|---|---|---|---|---|
| 1 | `Resolve` | relational | `lei`, `intent` | client registration, mandate, home currency, filing-period cash | `404` on unknown anchor | `[TBC — this build]` |
| 2 | `Policy` | bitemporal-ledger | client jurisdictions, `intent`, `as_of` | posture in force per (jurisdiction, intent) + `policy_version` | `503` if the ledger is unreachable | `[TBC — this build]` |
| 3 | `Traversal` | graph-traversal | client URI, `as_of` | position graph — `concentratedIn` to counterparties | `503` if the ledger is unreachable | `[TBC — this build]` |
| 4 | `Enrich` | relational | position graph, `as_of`, currency set | balances, notionals, the rate tick at `as_of`, the FX observation, **each with its own `observed_at` and `temporal_class`** | `503` naming the absent source class | `[TBC — this build]` |
| 5 | `Evaluate` | in-memory | everything above, `max_staleness` | **staleness gate**, then liquidity by currency and in home currency, weighted duration, concentration verdicts, mandate checks | **fail closed** naming the stale signal and its age | `[TBC — this build]` |
| 6 | `Projection` | in-memory | evaluated measures, posture | the principal's view | — | `[TBC — this build]` |
| 7 | — | in-memory | all of the above | contract assembly, `payload_hash`, `D_c`, TTL | `409` on debt gate | `[TBC — this build]` |

Operators come from the closed vocabulary. The staleness gate is **inside step
5**, not a step of its own — it is an `Evaluate` precondition, and making it a
step would put an operator in the plan that emits nothing.

**Policy runs before traversal and before enrichment.** At this tier the
posture does not remove edges, but it must be *resolved at the decision
instant* before any measure is computed, so that the answer and the authority
for the answer come from the same moment. Mirroring this into `artifacts/assembly-recipe.yaml`
with a WITNESS per step is a Gate 2 obligation.

### D.3 The four temporal classes — this rung's mechanism

Every element the payload carries declares a `temporal_class`. The classes are
not interchangeable and the product's arithmetic treats them differently.

| class | example | what the timestamp means | how `as_of` acts on it | decays? |
|---|---|---|---|---|
| `market-observation` | `intraday_tick.obs_ts`, `fx_reference_rate.obs_date` | an instant at which a value was observed | **selects** the observation at or before `as_of` | **yes** — λ_c, and subject to `max_staleness` |
| `policy-effectivity` | `RegulatoryPosture.validFrom` | the instant from which a rule is in force | **selects** the version in force at `as_of` | **no** — a step function. A policy is not stale; it is either in force or it is not |
| `reporting-period-end` | `treasury_client.cash_fact_asof` | the closing label of a reporting window | **bounds** it — a period ending after `as_of` is not yet knowable | slowly, on filing cadence — never on market cadence |
| `unobserved-holding` | `deposit_account.balance`, `investment_position.notional` | **nothing — no observation time was recorded** | **does not act on it at all** | **undefined**, and the payload says so |

Three consequences that the gates enforce:

- A `reporting-period-end` never enters the freshness term (`TLP-G14`).
- An `unobserved-holding` never receives a synthesized `observed_at` from the
  request time (`TLP-G15`). Inheriting `asked_at` would manufacture a freshness
  claim out of the act of asking.
- `policy-effectivity` is resolved by comparing `validFrom` to `as_of`, not by
  reading the ledger head (`TLP-G10`).

### D.4 The three scenarios, and how each instant was chosen

Ruled at Gate 1 (Q1 a). Every instant below comes from a measurement, not a
preference.

**Scenario 1 — the headline run. `as_of = 2026-06-17T18:05:00Z`.**
Chosen because it is the **largest measured gap between the intraday tick and
the most recent published daily close, anywhere in the post-flip window**:
2-year tick 4.285995 % against `DGS2` 4.05 % published 2026-06-16 — **23.60 bp**.
The posture flip of 2026-06-16 is in force, so `US-NY / reserve-buffer` reads
`enhanced-scrutiny`. Carries the Latency-Poisoned counterfactual (`TLP-G11`),
the three concentration verdicts (`TLP-G12`), and 2 mandate tenor exceedances.

**Scenario 2 — policy time-travel. `as_of = 2026-06-15T18:05:00Z`.**
Same client, same question, same parameters, **two days earlier and one posture
version back.** `US-NY / reserve-buffer` reads `standard`, and `policy_version`
differs. Chosen as the last trading day before the flip. The assertion is that
the two runs **disagree** — if they agree, the effectivity filter was dropped
and `as_of` is not reaching the policy leg (`TLP-G09`).

**Scenario 3 — fail closed. `as_of = 2026-08-21T16:00:00Z`, `max_staleness=15m`.**
The `stale_signal` fixture's own instant. Four signals: `SIG-000` at **45.0
minutes**, and three at 2.5, 1.28 and 1.55 minutes. The product refuses, names
`SIG-000` and its age, and **carries no liquidity figure at all** (`TLP-G07`,
`TLP-G08`). A product that returned three-quarters of an answer with a warning
would pass a "did it warn?" test and fail this one.

### D.5 Determinism and the emitted contract

**Determinism class: `deterministic`.** No model in the trust path. Given the
same `as_of`, the same ledger `t` and the same Control Plane state, the product
returns byte-identical bytes. `payload_hash` is `sha256` over the canonical
bytes excluding `assembled_at`.

The envelope is the §8 response envelope, populated with types, with a payload
carrying: client identity and mandate; liquidity by currency and in home
currency with the FX observation used for each conversion; weighted duration
against the tick curve; per-counterparty concentration with its three-valued
verdict and the coverage ratio; the mandate kind and tenor checks reported
separately; the posture in force with its `validFrom` and version; filing-period
cash with its period end; and **a signal register listing every element with its
`observed_at`, its `temporal_class` and its age at the decision instant**.

### D.6 Replay

1. Serve at `as_of = 2026-06-17T18:05:00Z`; record `payload_hash`,
   `graph_snapshot_at`, `policy_version`.
2. Re-serve at the same `as_of` without pinning the snapshot; confirm the hash
   is unchanged — the estate is static, so this proves reproducibility, not
   time-travel.
3. Re-serve at `as_of = 2026-06-15T18:05:00Z`; confirm the posture and
   `policy_version` **differ**, and that the hash differs.
4. Re-serve at `2026-06-17T18:05:00Z` again and confirm the **original** hash
   returns. If step 4 returns step 3's value, `as_of` is not reaching the plan
   and `graph_snapshot_at` is decorative.

Two axes, tested separately: the rate axis (`TLP-G11`) and the policy axis
(`TLP-G09`). **Agreement between them under a constructed case means a filter
was dropped.**

### D.7 Validation gates

Six universal, without re-argument: empty-operator guard · lineage strict
equality · TTL bounds · debt gate · suppression silence · classification
containment. These are `TLP-G01` … `TLP-G06`. The product-specific gates are
`TLP-G07` … `TLP-G18` and are tabulated in §G.1.

**Error mapping.**

| condition | raising step | response |
|---|---|---|
| `lei` has no `treasury_client` row | 1 | `404` — distinct from a client with no positions, which is `200` with an empty holdings block |
| principal not entitled to the client | 2 | `403`, no detail on what exists |
| `include_proposals=true` | 0 (validation) | `400 not_supported_at_tier` |
| a freshness-bearing signal exceeds `max_staleness` | 5 | **refusal** naming the signal and its age, **no partial payload** |
| `D_c` exceeds `debt_tolerance` | 7 | `409` with the debt block |
| ledger or relational leg unreachable | 2, 3, 4 | `503` naming the source class |
| concentration limits absent for some counterparties | 5 | `200` with `limit-unknown` verdicts and the coverage ratio — **not** a silent pass |

**Silence is not a negative answer.** A counterparty with no limit row is not a
counterparty within its limit, and the payload never lets the two read the same.

---

## E · Volatility, debt and materialization

### E.1 Half-life table

> **Illustrative calibration.** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

| Signal class | `λ_c` | Basis | Decay driver | Supersession event |
|---|---|---|---|---|
| Intraday rate tick | **15 min** | illustrative | market movement | next tick |
| FX reference rate | **1 day** | illustrative | daily publication | next publication |
| Reported cash (filing) | **90 days** | expert | quarterly filing cadence | next filing |
| Concentration limit | **90 days** | illustrative | treasury policy review | limit change |
| Permitted-instrument list | **90 days** | illustrative | IPS review | mandate amendment |
| Regulatory posture | **no decay — step function** | **measured** (`validFrom`) | — | posture amendment |
| Deposit balance, investment position | **none — unobserved** | **measured (absence)** | — | — |

**λ_c is a half-life, not a refresh cadence.** The 15 minutes on the tick row is
a decay rate chosen so the control is observable; it is not a claim that the
estate refreshes every 15 minutes, and §D.4's instants are pinned precisely so
that the decay is computed against a real observation rather than against a
snapshot's age.

**The last two rows are the rung's teaching point.** One class does not decay
because decay is the wrong model for it. One class has no λ_c because the estate
recorded no observation time, and inventing one would be the defect.

### E.2 Debt

`D_c = 1 − (F · C · S)`, multiplicative, so a collapsed dimension forces
escalation rather than averaging away.

- **F — freshness.** Normalized over the **required freshness-bearing classes**
  — intraday rate, FX, and the filing figure — **not** over classes present.
  `unobserved-holding` and `policy-effectivity` are **excluded from both
  numerator and denominator**, because including a class with no observation
  time would let the absence of a timestamp improve the score.
- **C — completeness.** `resolved / served`. Two live terms in this product:
  concentration-limit coverage (4 of 7 for the anchor, 60 of 103 estate-wide)
  and counterparty identity resolution (45 of 45, so it contributes nothing
  here — and the payload says so rather than omitting it).
- **S — semantic consistency.** Currency coherence: every balance converted
  carries an FX observation for the decision day, and a conversion with no rate
  is a consistency failure rather than a silent skip.

| Component | May be absent? | `D_c` contribution | Behavior when absent |
|---|---|---|---|
| Intraday rate tick at `as_of` | no | — | **fail closed** — refusal, not debt |
| FX observation for a held currency | yes | 0.15 | that currency's balance is `NOT_EVALUABLE`; others serve |
| Concentration limit for a counterparty | yes | 0.10 per uncovered pair, capped 0.20 | verdict `limit-unknown`, coverage published |
| Filing-period cash | yes | 0.08 | filing block omitted; liquidity unaffected |
| Regulatory posture for a (jurisdiction, intent) | no | — | `503` — the product will not serve an unauthorized view |
| Permitted-instrument list | yes | 0.05 | mandate check reported `NOT_EVALUABLE` |

**Checked against the 0.25 default tolerance:** no single optional component
exceeds it, so no optional absence alone forces a refusal. The uncovered-limit
term caps at 0.20 deliberately — uncovered limits are the estate's normal
condition (58 % coverage), and a product that refused to serve because of it
would refuse on almost every client, which would demonstrate nothing.

**Debt decomposes per claim.** A missing FX rate for JPY returns the USD, EUR
and GBP liquidity evaluated and the JPY figure `NOT_EVALUABLE` — not a
product-level failure.

### E.3 Materialization and TTL

**Posture: `derived-on-demand`, always.** The mechanical test: if the
fastest-moving input's λ_c is shorter than the intended cache window,
materialization is wrong. The fastest input's λ_c is **15 minutes**, so a
materialized product would expire before it was read twice. This is the
catalog's clearest on-demand case and the deliberate counterpoint to rung 1.

**Cache key**, for the cache that is nonetheless correct to keep for the
duration of a TTL window: `tenant · schema version · plan id ·
graph_snapshot_at · as_of · max_staleness · currencies · intent · principal
binding · debt_tolerance`. Dropping `as_of` or `max_staleness` from the key is a
correctness defect that presents as an intermittent one.

**TTL.** `expires_at = decision_instant + 15m`, ceiling 15 minutes; a request
for a longer window refuses with authority `technical`. **A request pinned to a
past `as_of` is a forensic reconstruction and does not decay** — the payload
declares it non-decaying rather than publishing a 15-minute window that would
misdescribe a settled past instant. This mirrors rung 8's finding and is the
same mechanism reaching the opposite conclusion because the subject differs.

### E.4 What invalidates a served answer

- A tick beyond the movement threshold — **local**, invalidates the rate leg.
- A deposit or position movement — **local**, but unobservable in this estate
  (no timestamp), so invalidation is by TTL expiry only. Recorded as a
  limitation, not designed around.
- A concentration-limit change — **local**.
- A regulatory-posture amendment — **cascading**, to any downstream product
  whose answer was authorized by the superseded version.

Re-derivation is **lazy**: invalidate for the next request, never re-materialize
eagerly.

---

## F · Source binding and readiness

### F.1 Readiness

| Element | Available today | Gap owner | Blocker |
|---|---|---|---|
| Clients, mandates, intents | **yes** — 15 | — | — |
| Deposit balances | **partial** — values yes, **observation time no** | ccf_dataprep | recorded as `CP09-F-01`; the product handles it, it is not a blocker |
| Investment positions | **partial** — same | ccf_dataprep | as above |
| Intraday ticks | **yes** — 30 days, 5 tenors | — | window ends 2026-06-23; scenarios pinned inside it |
| Daily rates, FX | **yes** | — | — |
| Concentration limits | **partial** — 60 of 103 pairs | ccf_dataprep | by design; the product publishes coverage |
| Permitted instruments | **partial** — kind check vacuous | ccf_dataprep | recorded as `CP09-F-02` |
| Position graph | **yes** — 200 edges each | — | `heldAt` ≡ `concentratedIn`, `CP09-F-03` |
| Regulatory posture | **yes** — 13 nodes, 1 versioned pair | — | one version pair; sufficient for `TLP-G09` |
| `stale_signal` fixture | **yes** — 4 rows, 1 breaching | — | — |

### F.2 Open `[TBC]` register

**Empty.** Every element above was measured against the live estate on
2026-09-11. The `[TBC — this build]` markers in §D.2 are p95 budgets, which
cannot exist before code does and close at Gate 2.

### F.3 Recorded findings — no decision needed to build

| id | finding | status |
|---|---|---|
| `CP09-F-01` | Deposit balances and investment positions carry **no observation timestamp**, so the vault's "deposit balances ~1 hour λ_c" cannot be computed. The product adds a fourth temporal class rather than synthesizing a time. | ESTATE-LIMITATION |
| `CP09-F-02` | The permitted-instrument **kind** check is vacuous — all 15 mandates permit all 3 kinds. The **tenor** check is live (34 of 200 positions exceed 365 days at 2026-06-17). Both are run and reported separately. | ESTATE-LIMITATION |
| `CP09-F-03` | `ex:heldAt` and `ex:concentratedIn` are identical on all 200 positions (**0 divergence**). Two declared relationship types carry one relation. The product reads one and records which. | NOT-A-GAP |
| `CP09-F-04` | The vault's §C assigns the intraday series, limits and mandates to Postgres and the posture to Fluree. **Confirmed against the estate** — no reassignment needed. | NOT-A-GAP |
| `CP09-F-05` | The estate's five time universes have no common live instant. Three pinned scenarios were ruled at Gate 1 rather than choosing a single "now" that would fail closed on everything. | ESTATE-LIMITATION |

### F.4 Access path

Read-only credentials. PostgreSQL `ccf_v2` schema; Fluree `fibo-v2` ledger over
the SPARQL query route. Environment-variable names in `backends.yaml`;
**nothing this example runs writes to either store**, and a role that could
write would make that a promise rather than a guarantee.

---

## G · Operate and govern

**Accountable owner.** Treasury product engineering owns assembly; the treasury
policy function owns limits, mandates and the posture overlay; market data
operations owns the rate and FX feeds. Roles, not individuals.

**Lifecycle.** `draft` at Gate 1 → `in-build` → `certified` at Gate 2.

### G.1 Product gates

| id | asserts | detects |
|---|---|---|
| `TLP-G01` | a plan with zero operator steps never serves | empty-operator |
| `TLP-G02` | served lineage equals the plan's typed operator references exactly | lineage drift |
| `TLP-G03` | `expires_at` derives from the decision instant and never exceeds the 15-minute ceiling | TTL fabrication |
| `TLP-G04` | `D_c` above `debt_tolerance` returns `409` with the debt block | ungated debt |
| `TLP-G05` | a withheld element leaves no count, marker or placeholder | disclosure by marker |
| `TLP-G06` | payload classification is the highest of any contributing element | classification leak |
| `TLP-G07` | at `2026-08-21T16:00Z` with `15m`, the product refuses and names `SIG-000` at 45.0 min | staleness gate inert |
| `TLP-G08` | that refusal carries **no** liquidity figure | partial serve dressed as a warning |
| `TLP-G09` | `2026-06-15T18:05Z` and `2026-06-17T18:05Z` return `standard` / `enhanced-scrutiny` and different `policy_version` | `as_of` not reaching the policy leg |
| `TLP-G10` | a pre-flip request does not see the 2026-06-16 version though it is the ledger head | reading head instead of effectivity |
| `TLP-G11` | the served 2-year rate at `2026-06-17T18:05Z` is the tick (4.285995), not the published daily close (4.05), differing by ≥ 8 bp | Latency Poisoned |
| `TLP-G12` | the anchor returns exactly 1 breach, 3 within-limit, 3 limit-unknown | collapsing three verdicts into two |
| `TLP-G13` | the payload publishes limit coverage as a ratio (4/7) | unstated completeness |
| `TLP-G14` | every payload element carries a `temporal_class`, and `reported_cash` is never `market-observation` | flattening four clocks into one |
| `TLP-G15` | holdings carry no `observed_at` and none is synthesized from `asked_at` | manufactured freshness |
| `TLP-G16` | at `2026-06-17T18:05Z` the anchor reports 2 positions exceeding the 365-day mandate tenor (`POS-00025` at 378 d, `POS-00028` at 368 d) | inert mandate check |
| `TLP-G17` | an LEI with no `treasury_client` row returns `404`, distinct from a client with no positions | request-error vs world-fact confusion |
| `TLP-G18` | the product reads one of `heldAt` / `concentratedIn` and records which | claiming information the estate does not carry |

Every gate is made to fail deliberately at least once before Gate 2, and each
sabotage is recorded.

### G.2 Acceptance criteria

1. The product serves scenario 1 and the payload's 2-year rate is the tick at
   `2026-06-17T18:05Z`, at least 8 bp from the most recent published daily close.
2. Scenarios 1 and 2 return different `policy_version` values and different
   `payload_hash` values, from identical requests differing only in `as_of`.
3. Scenario 3 refuses, names `SIG-000` and its age, and carries no liquidity
   figure.
4. The anchor's concentration block carries three distinct verdicts in the
   counts 1 / 3 / 3, plus a published coverage ratio.
5. Every payload element carries a `temporal_class` from the closed set of four,
   and no `unobserved-holding` carries an `observed_at`.
6. Replay at a pinned `as_of` reproduces `payload_hash` exactly.
7. `D_c` is computed over freshness-bearing classes only, and removing a
   concentration limit **raises** it.
8. All 18 gates execute, each with a docstring naming its id, and each has been
   observed failing.

**Open decisions blocking build: none.** §F.2 is empty.

### G.3 What this rung proves, and what it does not

**Proves, and nothing below it did:** that one `as_of` can govern a
determination without flattening four different kinds of time into one
freshness claim; that a policy version is selected by effectivity rather than
read from the head; that a fast-λ_c product refuses rather than substituting;
and that a completeness gap is reported as a third verdict rather than
disappearing into a pass.

**Does not prove:** allocation proposals under a policy envelope (no optimizer,
ruled at Gate 1); FX exposure as a subject (rung 12); set-off and netting
(rung 6); any freshness claim about client holdings, which this estate cannot
support (`CP09-F-01`).
