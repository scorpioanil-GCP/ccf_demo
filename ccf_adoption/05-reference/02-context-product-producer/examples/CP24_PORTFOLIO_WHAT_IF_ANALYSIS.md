> **Current operations:** use [the refreshed implementation walkthrough](CP24_PORTFOLIO_WHAT_IF.md) and Fluree **4.2.4** where required. The embedded specification remains historical evidence at its stated pin.

> **Reading copy:** [HTML edition](CP24_PORTFOLIO_WHAT_IF_ANALYSIS.html), with rendered tables and sources included in this file.

# CP-24 — Portfolio What-If / Stress — Analysis

**Audience:** banking SME and Information Architect. **Purpose:** reconstruct the journey from the business problem to this example’s final specification.

**Final specification:** `examples/cp-24-portfolio-what-if/spec/CP-SPEC-024_Portfolio_What_If_Stress.md`, read directly from `drcastillo/ccf_code` at `37ac3055fd64ed64d78c6fd5555d79e451859153`. [Open the included final spec](#source-spec). Its recorded decisions, corrections, findings and placeholders are the destination of this walkthrough. The [Standard v0.3](#source-standard) supplies the template and the [generation recipe](#source-recipe) explains the ownership and evidence sequence.

The figures below are the final spec’s teaching-estate measurements or declared design values. They are not new runtime measurements. Once the design journey is understood, continue with the [implementation walkthrough](#source-implementation).

## Start with “what if?” while keeping observed facts intact

A portfolio manager asks what happens to the book if rates rise and real-property collateral falls. The final spec uses the same **`BKR019`** 25-member population as CP23 and a demonstration scenario of **SOFR +150 basis points**, **real-property values −10%** and a 12-month horizon.

The originating business question mentions DSCR. The final product deliberately narrows its scope to three arithmetic limbs: incremental interest/headroom, secured coverage and a roll-up of members crossing a coverage floor. It does not claim to build a DSCR forecast, rating model, expected-loss model or digital-twin application merely because those are plausible extensions of the question.

The central SME requirement is that a stressed ratio must never be mistaken for the observed ratio. The architect therefore keeps three things distinct: source evidence, caller assumptions and scenario-derived values. Those distinctions must survive governance, payload display, identity and replay.

## Make the assumption a closed request object — Standard §0–§B → final §0–§B

| Element | Value |
|---|---|
| **Class** | `cib.portfolio-what-if` |
| **Lane** | `v1.0.0` |
| **Schema** | `portfolio_what_if` |
| **Request surface** | §B.3 — a closed `scenario` object plus five scalars |
| **TTL** | 24 h · `ttl_anchor: from_decision` (rung 23's reasoning, unchanged: a book's evidence has many ages) |
| **Obligations** | the sensitivity artifact and the scenario domain bound to `intent`; the impact set bound to the role |
| **Assembly mode** | governed assembly of the observed population, then deterministic Π arithmetic under the bound assumptions |
| **Lineage** | observed claims carry source `L`; **assumptions carry none, and that is the separation** |
| **Declared gates** | §G.1 — **17 gates**, `WIF-G01`..`WIF-G17` |

| Limb | Observed input | Scenario input | Impact |
|---|---|---|---|
| **Interest cost and headroom** | drawn balance, commitment (rung 23's utilization) | `rate_shift_bp` | incremental annual interest at the shifted rate; headroom after it |
| **Secured coverage** | collateral valuation and haircut by category | `collateral_shift_bp`, by asset class | stressed collateral value; secured coverage against drawn |
| **Book roll-up** | the population | both | how many members cross a declared coverage floor, and which |

| Parameter | Type | Domain | Default | Moves |
|---|---|---|---|---|
| `book` | — | — | — | the **subject**; not a parameter |
| `intent` | enum, required | `stress-test` \| `credit-review` \| `what-if` | — | policy envelope; **priced, never defaulted** |
| `as_of` | date-time | — | `asked_at` | the decision instant; bounds acquisition of the OBSERVED state |
| **`scenario`** | **object, required** | one closed level (§B.4) | — | **the hypothetical** |
| `members` | array | subset of the book | whole book | narrows; canonicalized by the deployment (rung 23's `Q2`) |
| `coverage_floor_bp` | integer | 0..20000 | from the artifact | the floor the roll-up counts crossings against; may be RAISED only |
| `debt_tolerance` | number | 0..1 | class default | the caller's ceiling on assessed debt |

The exact `scenario` members are `rate_shift_bp`, `collateral_shift_bp`, `collateral_class` and `horizon_months`; only `rate_shift_bp` is listed as required in the schema. The object has one declared level. Undeclared members and deeper structures refuse rather than creating an open-ended scenario language.

Rate and collateral magnitudes use **integer basis points**: `150` means +1.50 percentage points; `-1000` means −10%. `horizon_months` is an integer month count, not basis points. `collateral_class` names the category the shift applies to, such as `real_property`. The final specification's abbreviated demonstration object omits that category even though class-specific application is required; a review of the fully bound question must retain the category explicitly rather than apply the shift to all assets.

Bare JSON fractions such as `0.015` are noncanonical floats and are refused, never coerced or rounded. Although decimal strings can canonicalize in the underlying system, the final Q1 decision chooses the integer domain for this product. Domain arithmetic can convert to Decimal internally. The request boundary itself does not gain a float-to-Decimal repair path.

Membership narrowing inherits CP23's deployment-owned set normalization. Coverage floor can only rise above the artifact's value, and the caller's debt tolerance governs whether the observed evidence is sufficient to use.

## Assess the estate the scenario will stress — Standard §C → final §C

The source contains observed SOFR, facilities, drawdowns, collateral valuations and haircuts. The demonstration book has 60 collateral assets: 28 real-property, 15 marketable-securities, 15 receivables and two inventory assets. The measured average haircuts are 35%, 15%, 25% and 50% respectively; they come from the estate rather than being invented as scenario assumptions.

Average valuation ages differ substantially: 177 days for real property, 144 for securities, 91 for receivables and **320 for inventory**. Applying a stress to stale inventory creates a **stressed stale valuation**. It does not create a fresh appraisal.

Only 12 members have collateral and 14 facilities. Members with neither remain in the population, and impacted counts are stated against that population. No source value is manufactured to make every member stressable. The CP21 boundary remains: regulatory capital, limit definitions and connected-group derivation are outside this example.

The sensitivity artifact is explicitly illustrative. The analyst records that calibration separately from measured input values, which remain the source's observations at the real decision instant.

## Keep assumptions outside graph evidence — Standard §D → final §D

| # | Step | Store | Operator category |
|---|---|---|---|
| 1 | Resolve the book, the caller's role and the bound scenario | Postgres + Control Plane | — (acquisition) |
| 2 | Bind entitlement, the impact set, the sensitivity artifact and the scenario domain | Control Plane | Policy |
| 3 | Acquire the OBSERVED state: members, facilities and drawdowns, collateral, the base rate | Postgres | — (acquisition) |
| 4 | Cut every dated claim at the decision instant | — | Temporal |
| 5 | Walk the book's members from the book anchor | — | Traversal |
| 6 | Apply the assumptions: stressed rate, stressed collateral, coverage roll-up | in-process | — (Π) |
| 7 | Assemble, govern, assess, gate | — | — |

Acquisition emits only observed claims, bounded at `as_of`. Policy selects permitted impacts, sensitivity authority and the scenario domain. Temporal and Traversal operate on the observed book. Projection receives the canonical effective request and applies its assumptions; there is no ranked corpus and no Similarity operator.

The scenario is **never minted as a `SignalEnvelope` or graph claim**. Observed values carry source lineage. Assumptions live in the recorded effective request on replay dimensions 2 and 5 and carry no invented source lineage. Derived values are payload arithmetic, labelled `basis: scenario` and naming the assumption used.

For a rate result, the observed base rate, assumed shift and derived shifted rate are all visible. For collateral, the observed and stressed values are paired, and only the named asset class moves. The book roll-up identifies which members cross the floor, not merely how many. A reader can therefore trace the arithmetic without treating its conditional result as an observation.

The three role renderings—coverage, credit and product—change which impacts are visible, not the underlying arithmetic. Many scenarios are many requests; this spec builds neither a scenario scheduler nor an interactive application.

## Prove that a scenario cannot improve evidence quality — Standard §E–§F → final §E–§F

The governing rule is exact: **observed evidence determines Context Debt; assumptions determine scenario outputs**. Two different scenarios over the same instant and population must have identical debt. A more severe stress can worsen coverage without making the evidence less complete; a mild stress cannot make an old appraisal fresher.

Every stressed figure preserves its observed input's timestamp and age. No derived claim receives a new `observed_at` or `valid_from`, because no derived graph claim is created. Freshness, TTL and debt are not reset merely because arithmetic ran.

TTL is **24 hours from decision**. The declared illustrative half-lives extend the portfolio treatment with roughly seven days for reference rates and 180 for collateral; standing book, member and facility facts are superseded rather than aged. A scenario has no half-life: it is a condition of the question, not evidence about the world.

Final Q2 selects a **sibling producer over authoritative sources**, reusing CP23's population shape. It does not compose CP23 as a child. The duplicated population reader is recorded as a second instance of friction, with no abstraction pre-authorized. The earlier “questions owed” roster must be read with both final rulings: integer canonical units and sibling construction. Illustrative sensitivity and demonstration details remain visible in the source's owned calibration entries.

## Test identity and separation independently — Standard §G → final §G

| id | What it asserts | Red when |
|---|---|---|
| `WIF-G01` | the served operator set is the class's declaration and the executed plan runs Policy first | a key is dropped or reordered |
| `WIF-G02` | the `scenario` is a CLOSED object: an undeclared member is refused, and a structure deeper than the one declared level is not representable | the object is opened, or nesting is admitted |
| `WIF-G03` | a magnitude outside its declared domain is refused by name, as a request-contract violation rather than a policy one | the domain is widened |
| `WIF-G04` | **a noncanonical fractional form is REFUSED, never coerced or rounded** — the float path never yields an address | a float is coerced, or reaches canonicalization and succeeds |
| `WIF-G05` | the scenario crosses a DOOR and the product served over it is byte-identical to the in-process one | the door drops or mangles a scenario member |
| `WIF-G06` | **no claim in the served view carries a scenario magnitude** — the assumptions never entered the fabric, and no hypothetical carries source lineage pretending it was observed | a scenario value is minted as a claim |
| `WIF-G07` | every scenario-derived measure is labelled `basis: scenario` and **names the assumption that produced it** | a derived measure is served unlabelled or unattributed |
| `WIF-G08` | every stressed figure is served beside the OBSERVED figure it came from; the observed one carries source lineage and the assumption carries none | a stressed figure is served alone, or the two provenances become indistinguishable |
| `WIF-G09` | the base rate is an observed claim at `as_of`, the shift is an assumption, and the shifted rate is derived from both — all three served | the shifted rate is served as if observed |
| `WIF-G10` | the collateral shift applies ONLY to the named asset class; other classes are unchanged | the shift leaks across classes |
| `WIF-G11` | **LOAD-BEARING: a scenario does not refresh its factual inputs.** Every stressed figure carries its observation's `observed_at` and age, and a stressed stale valuation is still stale | the observed instant or age is dropped from the derived result |
| `WIF-G12` | **and nothing is RESET by arithmetic**: no derived value carries a fresher instant than its observation, and the TTL anchor and `D_c` are computed from the observed evidence alone | `observed_at`, `valid_from`, freshness, TTL or debt moves because a calculation ran |
| `WIF-G13` | **THE GOVERNING RULE, PROVED DIRECTLY: `D_c` is identical for two different scenarios over the same instant and population.** Observed evidence determines debt; assumptions never do | the assumptions move the debt |
| `WIF-G14` | the coverage roll-up names WHICH members cross the floor, not only how many | the roll-up is a bare count |
| `WIF-G15` | the same canonical assumptions at the same instant replay to the same effective request and the same content address | any input is re-derived rather than resolved |
| `WIF-G16` | a CHANGED assumption is a CHANGED determination — so `WIF-G15` cannot be met by ignoring the scenario | the scenario stops reaching the address |
| `WIF-G17` | CP-21's regulatory inputs are named nowhere in the tree | `limit_definition`, `bank_capital` or `connection_basis` appears |

The 17 intended gates include three independent identity tests: the same canonical scenario replays to the same address; a changed assumption changes the determination; an equivalent-looking noncanonical float refuses. Door and in-process results must match, so the proof includes the closed object crossing the actual product boundary.

Final gate numbering governs where older prose references differ: named floor-crossing members are `WIF-G14`, and the CP21 scope boundary is `G17`. The ordering sabotage may be unavailable under fixed SDK category order, with the guard named. The completed journey gives the SME a conditional answer whose assumptions are explicit and gives the architect a structural separation between evidence and arithmetic that can be tested directly.


## Included source snapshots

Exact retrieved source texts, with their original historical statuses and internal links retained as source text. Tables quoted within the walkthrough come directly from the final spec; Markdown pipe escaping is normalized for display.

<a id="source-spec"></a>

<details>
<summary>Final example specification — ccf_code@37ac3055</summary>

Path: `examples/cp-24-portfolio-what-if/spec/CP-SPEC-024_Portfolio_What_If_Stress.md`

``````text
<!--
  CP-SPEC-024 — Portfolio What-If / Stress Context.
  Gate 1 ONLY. Authored to Context Product Specification Standard v0.3 before
  any code exists, per `D-IMPL-319` and the rule *specs come before code*.

  Source: `references/cbcib-portfolio-management-CLAUDE.md` (Dave's `cbcib`
  Portfolio Management POC requirements, supplied 2026-09-20) and the CP-24
  definition derived from it in `docs/GATE-0-COVERAGE-CP15-24.md` §4.2.

  GATE 2 GRANTED 2026-09-21: both recommendations accepted. The rulings were
  folded into this document BEFORE any implementation, per the instruction.
-->

# Portfolio What-If / Stress — Context Product Specification

**Rung 24 · Postgres (+ the graph watermark) · `cib.portfolio-what-if`**

**Status: GATE 2 — `Q1` and `Q2` RULED, 2026-09-21. Build authorized, minimal,
on the paved road as a SIBLING product. No SDK work, no `D-IMPL` id spent.**

---

## 0 · What this document is

> **CP-24 is not a forecasting or modeling platform** (Dave, 2026-09-21). The
> scenario assumptions are **explicit inputs**. CCF's job is to govern the
> current context, bind the assumptions, produce the scenario-conditioned
> Context Product, and preserve enough lineage to **distinguish facts from
> hypotheticals** and **replay the determination**. No model is fitted, no
> probability is estimated, and nothing is predicted.

The question this document exists to answer:

> **What does portfolio what-if require that CP-01 through CP-23 have not
> already proven?**

### 0.1 Already proven — reused unchanged, and NOT reopened

| # | Mechanism | Proven at | Reused here as |
|---|---|---|---|
| 1 | The paved producer road, `open_product(...)` with a named `plan_factory` | `D-IMPL-343`; rungs 13–19, 23 | the producer spine. **Ninth tree on the road.** |
| 2 | **A POPULATION as the assembly unit** — the book, its members, batched per limb | **`D-GATE-cp-23`** | the observed current state this rung conditions |
| 3 | Population debt by the SDK's `compose_debt_factors`, per-factor minimum | `D-GATE-cp-23`, `D-IMPL-104` | unchanged; the scenario does not touch how debt composes |
| 4 | Deployment-owned canonicalization of a member set | `D-GATE-cp-23` (`Q2`) | unchanged; `produce.book_question`'s shape is reused |
| 5 | The standard door + three typed overrides; three roles from the estate's own vocabulary | `D-IMPL-324`; rung 23 | the same three roles see different impact sets |
| 6 | Π as deterministic arithmetic over a Control Plane artifact (values, never code) | cp-18's weight vector; rung 23's severity tiers | the **sensitivity artifact** |
| 7 | An illustrative calibration, disclosed where a reader meets it | `D-IMPL-323` | the sensitivities and the demonstration scenario |
| 8 | A governed refusal by name, as data, with a replay reference | cp-05 onward | an unpriced intent, an out-of-domain scenario magnitude |
| 9 | Content addressing: the same question is the same bytes | every rung | **the same scenario replays to the same address** |

### 0.2 Genuinely new — three things

**(a) A determination that depends on EXPLICIT HYPOTHETICALS.** Every rung so
far served observed facts about the world. CP-24's answer is *conditional*: it
is true **given** assumptions the caller supplied and the world did not. The
product must therefore keep two kinds of content apart — what was observed,
which carries source lineage through `L`, and what was assumed, which is the
recorded effective request. **The separation exists by construction** (§D.3),
and the payload additionally *labels* every scenario-derived measure so a
consumer cannot mistake one for the other.

**(b) The first CLOSED object request parameter — and the first object
parameter to cross a door.** `SkillArgumentProperty.properties` admits one
declared level of members and `SkillArgumentMember` carries **no `properties`
and no `items`**, so a third level is not expressible by construction. **This
corrects Gate 0's claim that an object parameter has crossed no shipped door:**
cp-09 ships one — but as an **open mapping** with no declared `properties`,
and cp-09 ships **no door at all** (measured 2026-09-21). What is unproven is
the *closed* shape and the *door crossing*, and CP-24 is where both happen.

**(c) Replay of a hypothetical.** `replay` re-feeds the recorded request, so
the same scenario over the same instant reconstructs to the same content
address — and a *different* scenario over identical observed facts is a
different determination. Nothing before this rung replayed an assumption.

**No genuinely new SDK capability is identified.** Checked symbol by symbol and
by execution against `src/` on 2026-09-21 (§F.2, §F.4).

### 0.3 Deliberately OUT of scope — the probe's boundary

| Left out | Why |
|---|---|
| **Any fitted model, probability, or prediction** | the scenario is an input, not an inference. Dave's discipline, 2026-09-21. |
| The interactive sandbox / Digital Credit Twin UI | harness- and UX-owned by standing ruling |
| A scenario scheduler or sweep | **many scenarios are many requests**, by standing ruling — per-request assembly |
| Expected-loss and RWA models | a capital model is not a context product; the impacts served here are arithmetic over declared sensitivities |
| Regulatory large-exposure arithmetic | CP-21's, and the CP-23 boundary is preserved (§C.3 trap 4) |
| Composing CP-23's product as a CHILD | see `Q2` (§F.4) — recommended against for this rung |

### 0.4 The four-question build test (Standard v0.3)

| Question | Answer |
|---|---|
| Buildable without a further design conversation? | **No — one capability question and one scope decision are owed** (§F.4). |
| Every source named, with store, provenance and scale? | **Yes** — §C, measured 2026-09-21. |
| Every parameter's domain, default and effect stated? | **Yes** — §B.3. |
| Every gate expressible as a test that can go red? | **Yes, with one named risk** — §G.1. |

---

## A · Decision frame

**Decision and trigger.** A portfolio manager or credit officer asking *what
happens to this book if rates rise and collateral values fall* — the
requirements' Digital Credit Twin, reduced to the part CCF actually owns.

**Subject.** The same **coverage book** rung 23 established: `BKR019`, 25
members, named by its banker.

**Consuming principals.** The same three estate roles — `coverage`, `credit`,
`product` — differing in **which impacts each sees**, not in the arithmetic.

**The demonstration scenario**, from the requirements' own words:

> *"How does a 150 bps rise in SOFR impact the DSCR of our commercial real
> estate sub-portfolio?"*

expressed as `{rate_shift_bp: 150, collateral_shift_bp: -1000, horizon_months: 12}`
— SOFR **+150 bps** and real-property collateral **−10 %**.

**Counterfactual — a hypothetical mistaken for a fact.** The failure this rung
exists to prevent is a consumer reading a stressed coverage ratio as the
*observed* one. Three things prevent it: observed claims carry source lineage
and scenario values do not; the assumptions are the recorded effective request
on replay dimensions 2 and 5; and **every scenario-derived measure in the
payload is labelled as such** (`WIF-G07`).

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Class** | `cib.portfolio-what-if` |
| **Lane** | `v1.0.0` |
| **Schema** | `portfolio_what_if` |
| **Request surface** | §B.3 — a closed `scenario` object plus five scalars |
| **TTL** | 24 h · `ttl_anchor: from_decision` (rung 23's reasoning, unchanged: a book's evidence has many ages) |
| **Obligations** | the sensitivity artifact and the scenario domain bound to `intent`; the impact set bound to the role |
| **Assembly mode** | governed assembly of the observed population, then deterministic Π arithmetic under the bound assumptions |
| **Lineage** | observed claims carry source `L`; **assumptions carry none, and that is the separation** |
| **Declared gates** | §G.1 — **17 gates**, `WIF-G01`..`WIF-G17` |

### B.2 The three impact limbs — the smallest set that proves the shape

| Limb | Observed input | Scenario input | Impact |
|---|---|---|---|
| **Interest cost and headroom** | drawn balance, commitment (rung 23's utilization) | `rate_shift_bp` | incremental annual interest at the shifted rate; headroom after it |
| **Secured coverage** | collateral valuation and haircut by category | `collateral_shift_bp`, by asset class | stressed collateral value; secured coverage against drawn |
| **Book roll-up** | the population | both | how many members cross a declared coverage floor, and which |

Nothing else. Rating migration, liquidity and covenant projection are
*forecasts*, and forecasts are out of scope (§0.3).

### B.3 Request parameter surface

| Parameter | Type | Domain | Default | Moves |
|---|---|---|---|---|
| `book` | — | — | — | the **subject**; not a parameter |
| `intent` | enum, required | `stress-test` \| `credit-review` \| `what-if` | — | policy envelope; **priced, never defaulted** |
| `as_of` | date-time | — | `asked_at` | the decision instant; bounds acquisition of the OBSERVED state |
| **`scenario`** | **object, required** | one closed level (§B.4) | — | **the hypothetical** |
| `members` | array | subset of the book | whole book | narrows; canonicalized by the deployment (rung 23's `Q2`) |
| `coverage_floor_bp` | integer | 0..20000 | from the artifact | the floor the roll-up counts crossings against; may be RAISED only |
| `debt_tolerance` | number | 0..1 | class default | the caller's ceiling on assessed debt |

### B.4 The `scenario` object — closed, and integral

```yaml
scenario:
  type: object
  properties:
    rate_shift_bp:        {type: integer}   # +150 = SOFR up 1.50%
    collateral_shift_bp:  {type: integer}   # -1000 = values down 10.00%
    collateral_class:     {type: string}    # which asset category the shift applies to
    horizon_months:       {type: integer}
  required: [rate_shift_bp]
```

**EVERY MAGNITUDE IS AN INTEGER IN CANONICAL UNITS — basis points — BY RULING
(`Q1`, 2026-09-21), and the ruling rests on a measurement rather than a style
choice.** The request surface **rejects undeclared members, structures deeper
than the one declared level, and noncanonical fractional forms**; a float is
**refused, never coerced**. `SkillArgumentMember` is **not widened** and no
recursive request schema is introduced for this rung. Measured 2026-09-21: a
JSON fraction such as `0.015` parses to a Python `float`, and the SDK's
canonicalizer **refuses a float outright** — *"float is not canonically
encodable (not bit-stable across platforms)"*. Integers and decimal *strings*
both canonicalize exactly. Basis points remove the fraction from the wire
entirely, so a scenario is exactly addressable with no encoding convention for
a caller to get wrong. The Decimals live in the sensitivity artifact, where
they are never on a wire.

### B.5 Prerequisites

**None as children.** This rung declares no composite requirement — see `Q2`
(§F.4). It re-assembles the observed population using **rung 23's shape**,
which is what Dave's instruction asks for.

---

## C · Data catalog — every figure measured against `.76` on 2026-09-21

### C.1 Element table

| Element | Store | Object | Scale | Provenance |
|---|---|---|---|---|
| Book membership and members | Postgres `ccf_v2` | `coverage_assignment`, `banker`, `legal_entity` | 1,000 / 40 / 156 | rung 23's sources, unchanged |
| Facilities and drawdowns | Postgres | `facility`, `drawdown` | 60 over 22 borrowers; 151 | public |
| **Reference rates** | Postgres | `reference_rate` | **10,539** rows; **SOFR at 3.63 % on 2026-08-20**, plus Treasury constant maturities | public — FRED |
| Benchmark curve | Postgres | `benchmark_curve` | **8,917** rows, `curve_date` × `tenor_years` × `par_yield_pct` | public |
| **Collateral and haircuts** | Postgres | `collateral_asset`, `haircut_schedule` | **60 assets in `BKR019`'s book**, 4 categories | public / synthetic |
| Graph watermark | Fluree `fibo-v2` | ledger `t` | — | — |

### C.2 The collateral the scenario shifts — `BKR019`'s book

| category | assets | avg haircut | valuation age (avg days) |
|---|---:|---:|---:|
| `real_property` | **28** | 0.3500 | 177 |
| `marketable_securities` | 15 | 0.1500 | 144 |
| `receivables` | 15 | 0.2500 | 91 |
| `inventory` | 2 | 0.5000 | 320 |

**`real_property` is the requirements' "commercial real estate sub-portfolio"**
and is the largest category, so the demonstration shift lands on real evidence
rather than a thin corner. The haircuts are the estate's, not this product's.

### C.3 The data traps, each with the binding chosen

**Trap 1 — a shifted rate is not an observed rate.** The scenario names a
*shift*; the base is `reference_rate.SOFR` at `as_of`. **Binding:** the base is
an observed claim carrying source lineage, the shift is an assumption carrying
none, and the shifted rate is a **derived** value labelled as
scenario-conditioned. All three are served, so a reader can see the arithmetic
rather than a single number of unclear provenance.

**Trap 2 — STALE EVIDENCE UNDER STRESS. Ruled 2026-09-21, and load-bearing.**
An `inventory` valuation averaging **320 days** is stale evidence, and stressing
it yields **a stressed stale valuation** — not a fresh one.

> **A scenario does not refresh its factual inputs.** Carry the original
> observation's age and freshness into the derived result. **Do not reset
> `observed_at`, `valid_from`, freshness, TTL or Context Debt merely because
> arithmetic was applied.** Make it visible in the product and load-bearing in
> a gate.

**Binding:** every stressed figure carries the observed input's `observed_at`
and its age in days; the derived value is minted as **no claim at all**, so
there is no second `observed_at` to drift; the TTL anchor and `D_c` are
computed from the observed evidence alone. `WIF-G11` proves it, and
`WIF-G12` proves the negative — that no derived value carries a fresher
instant than the observation it came from. **No fresher collateral observation
is manufactured to make the stress result cleaner** (§C.3 trap 5).

**Trap 3 — not every member has collateral or a facility.** 12 of 25 members
have collateral and 14 have a facility. **Binding:** rung 23's rule, unchanged
— a member with neither remains a member, and the impacted counts are stated
against the population rather than implied.

**Trap 4 — the CP-21 boundary still holds.** `limit_definition`,
`bank_capital` and `connection_basis` are CP-21's regulatory inputs.
**Binding:** they are named nowhere in this tree either, and `WIF-G14` reads
them out of the modules and declared tables exactly as `PEW-G18` does.

**Trap 5 — the estate is a snapshot and the sensitivities are illustrative.**
**Binding:** an illustrative calibration under `D-IMPL-323`, disclosed in the
artifact that declares it, in the README and here. The *observed* values, the
decay and the decision instant remain the estate's and the SDK's.

---

## D · Assembly recipe

### D.1 Client call

```
GET /context-products/cib/portfolio-what-if/BKR019
      ?intent=stress-test&as_of=2026-08-25
      &scenario={"rate_shift_bp":150,"collateral_shift_bp":-1000,"collateral_class":"real_property"}
```

### D.2 Operator step table

| # | Step | Store | Operator category |
|---|---|---|---|
| 1 | Resolve the book, the caller's role and the bound scenario | Postgres + Control Plane | — (acquisition) |
| 2 | Bind entitlement, the impact set, the sensitivity artifact and the scenario domain | Control Plane | Policy |
| 3 | Acquire the OBSERVED state: members, facilities and drawdowns, collateral, the base rate | Postgres | — (acquisition) |
| 4 | Cut every dated claim at the decision instant | — | Temporal |
| 5 | Walk the book's members from the book anchor | — | Traversal |
| 6 | Apply the assumptions: stressed rate, stressed collateral, coverage roll-up | in-process | — (Π) |
| 7 | Assemble, govern, assess, gate | — | — |

Three operator keys, as rung 23 — there is no ranked corpus.

### D.3 THE GOVERNING FACT/HYPOTHETICAL RULE — load-bearing, ruled 2026-09-21

> **Observed evidence determines Context Debt. Scenario assumptions determine
> scenario-derived outputs. Scenario assumptions are NEVER evidence.**

Six consequences, each gated:

| # | Consequence | Gate |
|---|---|---|
| 1 | scenario magnitudes **never become graph claims** | `WIF-G06` |
| 2 | assumptions live in the **canonical effective request / replay evidence** | `WIF-G15` |
| 3 | derived values **explicitly identify which assumption produced them** | `WIF-G07` |
| 4 | observed **source lineage remains attached to the factual input** | `WIF-G08` |
| 5 | hypothetical inputs **carry no source lineage pretending they were observed** | `WIF-G06`, `WIF-G08` |
| 6 | **`D_c` is unchanged when only scenario assumptions change** | **`WIF-G13`, which proves the rule directly** |

### D.3.1 Where the separation lives, and why it is structural

**The assumptions never become claims.** Nothing in the scenario is minted as a
`SignalEnvelope`; it reaches Π as the effective request, not as graph content.
So:

- every **observed** value in the payload traces to a claim with source
  lineage in `L`;
- every **assumed** value is in the recorded effective request — replay
  dimension 2 (policy bindings and effective request) and dimension 5 (the
  request on the content-generation path);
- no observed claim can carry a scenario value, because the scenario never
  entered the fabric.

That is the separation *by construction*. `WIF-G06` proves the negative — the
scenario's magnitudes appear in **no** claim in the served view — and
`WIF-G07` proves the positive: every derived measure is labelled
`basis: scenario` and names the assumption it used.

### D.4 Determinism class

Fully algorithmic. No LLM inference and **no fitted model**: each impact is
arithmetic over an observed value, a declared sensitivity and a stated
assumption.

### D.5 Replay statement

The determination replays with no second producer call. **The scenario is part
of the effective request**, so re-feeding the record reproduces the same
address; a different scenario over identical observed facts is a different
determination (`WIF-G15`, `WIF-G16`).

### D.6 Validation gates (contract level)

Empty-operator guard · lineage strict equality · TTL bounds · **assumption
containment** (no scenario value in any claim) · **impact labelling** (every
derived measure names its basis and its assumption) · **observed/derived
pairing** (no stressed figure without the observed figure it came from).

---

## E · Volatility, debt and materialization

### E.1 Half-life

Rung 23's table, extended by the two classes this rung adds:

| Class | `λ_c` | Basis |
|---|---|---|
| book, member, facility | supersede-only | standing state |
| `reference_rate` | ~7 days | `valid-from` — a daily series |
| `collateral` | ~180 days | `valid-from` — an appraisal date |
| the signal classes | as rung 23 | unchanged |

All **illustrative** under `D-IMPL-323`.

**A scenario has no half-life.** It is not an observation and does not decay;
it is a condition of the question. Recorded because it is the kind of thing a
later reader would otherwise try to give one.

### E.2 Debt

Unchanged from rung 23: `D_c` over the observed population, by the SDK's
per-factor minimum. **The scenario does not improve or worsen `D_c`** — debt
measures the evidence, and the assumptions are not evidence. A stressed book
with stale collateral is *both* highly impacted and poorly evidenced, and the
two numbers say different things.

### E.3 Materialization

Per request. **Many scenarios are many requests**, by standing ruling.

---

## F · Source binding and readiness

### F.1 Element readiness

Every element is present and measured. Nothing is missing.

### F.2 Symbols named, verified against `src/` on 2026-09-21

`src/ccf/products/product.py::open_product` ·
`src/ccf/skills/catalog.py::SkillArgumentProperty` (with `properties`) ·
`src/ccf/skills/catalog.py::SkillArgumentMember` (no `properties`, no `items` —
the one-level ceiling) · `src/ccf/products/request.py::ProductRequest` ·
`src/ccf/contracts/canonical.py` (the float refusal) ·
`src/ccf/halflife/debt.py::compose_debt_factors` ·
`src/ccf/products/expiry.py::resolve_ttl_anchor`. Every one resolves.

### F.3 Every `[TBC]`, with an owner

| # | Item | Owner |
|---|---|---|
| 1 | **`Q1` — the scenario's wire form** (§F.4) | **Dave** |
| 2 | **`Q2` — child of CP-23, or sibling over the same shape?** (§F.4) | **Dave** |
| 3 | The demonstration scenario and instant | Dave — recommended as stated |
| 4 | The illustrative sensitivity values | Dave — under `D-IMPL-323` |

### F.4 — THE QUESTIONS OWED

#### `Q1` — RULED 2026-09-21: INTEGER CANONICAL UNITS

> **Dave's ruling.** Scenario magnitudes crossing a CCF boundary use **integer
> canonical units**. For CP-24: SOFR **+150 bps → `150`**; CRE **−10 % →
> `-1000`**. **Do not accept bare JSON fractional values and do not add
> float→Decimal coercion** — the existing refusal of floating-point values as
> non-bit-stable is **correct behavior**. Domain calculations may convert the
> canonical integer assumption to `Decimal` internally. **Gate the identity
> property:** same canonical assumptions → same effective-request identity;
> changed assumption → changed identity; **equivalent-looking but noncanonical
> float input → governed refusal, not coercion.** **No SDK parsing change.**

**What this settles.** Route A stands; B and C are closed. Three gates carry
it and none can satisfy another: `WIF-G15` (same → same), `WIF-G16` (changed →
changed) and `WIF-G04` (a noncanonical float is **refused**, never coerced or
rounded). The `Decimal` conversion happens *inside* the arithmetic, never on a
wire and never in a request.

**The original question, for the record.**

**Measured 2026-09-21, by execution rather than by reading:**

| form | canonicalizes? | what a JSON body yields |
|---|---|---|
| integer basis points (`150`) | **yes, exactly** | `int` |
| decimal string (`"0.015"`) | **yes, exactly** | `str` |
| `Decimal("0.015")` in-process | yes, exactly → `"0.015"` | n/a |
| **JSON fraction (`0.015`)** | **NO — refused** | `float` |

The canonicalizer refuses a float by name: *"float is not canonically
encodable (not bit-stable across platforms)"*. That is **correct and valuable
SDK behavior** — an unstable address would be far worse than a refusal — but it
means a scenario carrying `-0.10` over a door is refused unless the deployment
chooses a form.

| | Route | Consequence |
|---|---|---|
| **A** | **Integers in basis points everywhere** *(recommended)* | no fraction ever reaches the wire; exact addressing; the caller cannot get the encoding wrong. `-10 %` is `-1000`. Cost: the caller thinks in bps, which is the domain's own unit anyway. |
| **B** | Decimal strings (`"-0.10"`) | also exact, but the JSON schema says `string` for a number, and a caller who sends `-0.10` unquoted is refused at serve time rather than at boot |
| **C** | Ask the SDK to coerce JSON floats to `Decimal` at the door | **not proposed.** It would change how every product's request is parsed, and float→Decimal coercion re-introduces exactly the platform instability the refusal exists to prevent |

**Recommendation: A.** Route C is explicitly not recommended.

#### `Q2` — RULED 2026-09-21: SIBLING, NOT CHILD

> **Dave's ruling.** Build CP-24 as a **sibling portfolio product** using the
> authoritative underlying sources and the population shape proven by CP-23.
> **Do not compose CP-23 as a child** — the new capability under test is
> explicit hypotheticals, not product composition. **Record duplicated
> population-reader plumbing as a friction measurement. This is the SECOND
> instance only.** If a later rung produces a third substantially identical
> population reader, **measure all three before considering documentation or an
> SDK abstraction. No abstraction is pre-authorized.**

**What this settles.** Route A stands; B is closed. The duplicated reader is
measured in `FINDINGS.md` §2 as `WIF-F-01`, counted as instance two of two, and
nothing is abstracted.

**The original question, for the record.**

Gate 0 allows either: *"CP-23's book context **or its sources**"*. Dave's
instruction says *reuse CP-23's portfolio population shape*.

| | Route | Consequence |
|---|---|---|
| **A** | **A sibling producer over the same sources, reusing rung 23's shape** *(recommended)* | no child resolution, no producer registration, no composite admission. The rung stays a probe of *hypotheticals*, which is what is genuinely new. Cost: rung 23's population reader is written a second time — a real DX cost, and the **second** instance, so it is a measurement rather than a trigger. |
| **B** | Declare `requires: cib.portfolio-early-warning` and admit CP-23 as a child | proves composition over a *population* product, which nothing has. But it pulls in the whole cp-14 child chain and would make composition — not hypotheticals — the rung's dominant new thing, against the stated discipline. |

**Recommendation: A**, with the duplicated population reader recorded as a
friction measurement. **If Dave prefers B, that is a materially larger rung and
should be said so plainly.**

---

## G · Operate and govern

### G.1 Product gates — 17 (the two standing rules of 2026-09-21 add two)

| id | What it asserts | Red when |
|---|---|---|
| `WIF-G01` | the served operator set is the class's declaration and the executed plan runs Policy first | a key is dropped or reordered |
| `WIF-G02` | the `scenario` is a CLOSED object: an undeclared member is refused, and a structure deeper than the one declared level is not representable | the object is opened, or nesting is admitted |
| `WIF-G03` | a magnitude outside its declared domain is refused by name, as a request-contract violation rather than a policy one | the domain is widened |
| `WIF-G04` | **a noncanonical fractional form is REFUSED, never coerced or rounded** — the float path never yields an address | a float is coerced, or reaches canonicalization and succeeds |
| `WIF-G05` | the scenario crosses a DOOR and the product served over it is byte-identical to the in-process one | the door drops or mangles a scenario member |
| `WIF-G06` | **no claim in the served view carries a scenario magnitude** — the assumptions never entered the fabric, and no hypothetical carries source lineage pretending it was observed | a scenario value is minted as a claim |
| `WIF-G07` | every scenario-derived measure is labelled `basis: scenario` and **names the assumption that produced it** | a derived measure is served unlabelled or unattributed |
| `WIF-G08` | every stressed figure is served beside the OBSERVED figure it came from; the observed one carries source lineage and the assumption carries none | a stressed figure is served alone, or the two provenances become indistinguishable |
| `WIF-G09` | the base rate is an observed claim at `as_of`, the shift is an assumption, and the shifted rate is derived from both — all three served | the shifted rate is served as if observed |
| `WIF-G10` | the collateral shift applies ONLY to the named asset class; other classes are unchanged | the shift leaks across classes |
| `WIF-G11` | **LOAD-BEARING: a scenario does not refresh its factual inputs.** Every stressed figure carries its observation's `observed_at` and age, and a stressed stale valuation is still stale | the observed instant or age is dropped from the derived result |
| `WIF-G12` | **and nothing is RESET by arithmetic**: no derived value carries a fresher instant than its observation, and the TTL anchor and `D_c` are computed from the observed evidence alone | `observed_at`, `valid_from`, freshness, TTL or debt moves because a calculation ran |
| `WIF-G13` | **THE GOVERNING RULE, PROVED DIRECTLY: `D_c` is identical for two different scenarios over the same instant and population.** Observed evidence determines debt; assumptions never do | the assumptions move the debt |
| `WIF-G14` | the coverage roll-up names WHICH members cross the floor, not only how many | the roll-up is a bare count |
| `WIF-G15` | the same canonical assumptions at the same instant replay to the same effective request and the same content address | any input is re-derived rather than resolved |
| `WIF-G16` | a CHANGED assumption is a CHANGED determination — so `WIF-G15` cannot be met by ignoring the scenario | the scenario stops reaching the address |
| `WIF-G17` | CP-21's regulatory inputs are named nowhere in the tree | `limit_definition`, `bank_capital` or `connection_basis` appears |

**One is at risk of coming back `unavailable`**, named now: `WIF-G01`'s
ordering limb, because `CATEGORY_ORDER` has made the forbidden order
inexpressible on rungs 15, 16, 19 and 23. If a predicted sabotage proves
impossible because the SDK makes the bad state unreachable, it will be marked
`unavailable` with its guard named — **the mechanism will not be weakened to
manufacture a red**.

### G.2 What this rung measures for the backlog

The **second** instance of the population reader (`Q2` route A) — a
measurement, not yet the third that triggers an abstraction review; the closed
object parameter's ergonomics at a door; and whether labelling
scenario-derived measures is enough for a consumer to keep facts and
hypotheticals apart.

---

## Gate 1 summary

- **Genuinely new:** three things (§0.2) — a determination depending on
  **explicit hypotheticals**, the first **closed** object parameter and the
  first to cross a **door**, and **replay of a hypothetical**. **No new SDK
  capability required.**
- **Gate 0's B7 claim is corrected** (§0.2b, `Q1`): an object parameter *has*
  shipped (cp-09, open mapping, no door), and a fractional magnitude *does*
  have an exact wire form — integers in basis points, or decimal strings. A
  bare JSON fraction is refused, correctly and by name.
- **Estate:** ready. SOFR at 3.63 %, an 8,917-row curve, and 60 collateral
  assets in the demonstration book across four categories with real haircuts.
  Five traps recorded with bindings.
- **Scope held to a probe** (§0.3): three impact limbs, no model, no
  prediction, no sandbox, no sweep.
- **Intended gates:** 17, one flagged as at risk of `unavailable`; if a
  predicted sabotage is structurally impossible the guard is named and the
  mechanism is NOT weakened to manufacture a red.
- **Ruled 2026-09-21:** `Q1` — integer canonical units (basis points); a
  noncanonical float is refused, never coerced; no SDK parsing change. `Q2` —
  **sibling, not child**; the duplicated population reader is a friction
  measurement, **second instance only**, and no abstraction is pre-authorized.
- **Two standing rules made load-bearing:** the governing fact/hypothetical
  rule (§D.3) and stale-evidence-under-stress (§C.3 trap 2).
- **Authorized:** Gate 2, minimal build on the paved road. No SDK work, no
  `D-IMPL` id spent.

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

Path: `05-reference/02-context-product-producer/examples/CP24_PORTFOLIO_WHAT_IF.md`

``````text
# CP-24 — Portfolio What-If / Stress

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-24-portfolio-what-if/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP24_PORTFOLIO_WHAT_IF_ANALYSIS.md) · [HTML reading edition](CP24_PORTFOLIO_WHAT_IF_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-24-portfolio-what-if/README.md`  
**Qualified specification:** `examples/cp-24-portfolio-what-if/spec/CP-SPEC-024_Portfolio_What_If_Stress.md`  
**Qualified source:** `examples/cp-24-portfolio-what-if`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-24-portfolio-what-if/spec/CP-SPEC-024_Portfolio_What_If_Stress.md`

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

First explicitly conditional Context Product. It governs factual context and binds caller-supplied hypothetical assumptions while keeping assumptions separate from evidence, lineage freshness and Context Debt.

## The question

> Given the current governed portfolio evidence, what deterministic outputs follow under this explicit scenario, without pretending the scenario itself was observed?

## What to understand before you run it

- Scenario assumptions are request state, not evidence.
- Changing only the scenario must not refresh or improve Context Debt.
- Hypothetical outputs must name the assumption that produced them.
- Scenario magnitudes use canonical integer units for bit-stable requests.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
export CCF_CP_24_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_24_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_24_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_24_FLUREE_LEDGER='fibo-v2'
export CCF_CP_24_TOKEN_COVERAGE='<credential>'
export CCF_CP_24_TOKEN_CREDIT='<credential>'
export CCF_CP_24_TOKEN_PRODUCT='<credential>'
export CCF_CP_24_TOKEN_UNGRANTED='<credential>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-24-portfolio-what-if/spec/` | Conditional/hypothetical product contract. |
| `examples/cp-24-portfolio-what-if/ccf_config.yaml` | Closed scenario request schema and product/operator declarations. |
| `examples/cp-24-portfolio-what-if/ccf_environment.yaml` | Source/credential names. |
| `examples/cp-24-portfolio-what-if/artifacts/source-vocabulary.yaml` | Observed source mappings. |
| `examples/cp-24-portfolio-what-if/artifacts/sensitivities.yaml` | Illustrative sensitivities as declared values. |
| `examples/cp-24-portfolio-what-if/artifacts/question.yaml` | Demonstration population/instant/scenario. |
| `examples/cp-24-portfolio-what-if/acquisition.py` | Observed factual input acquisition. |
| `examples/cp-24-portfolio-what-if/projection.py` | Deterministic scenario arithmetic. |
| `examples/cp-24-portfolio-what-if/artifacts/gates.yaml` | 17 gates including assumption/evidence separation. |

## Run it

```bash
make venv
make -s example-cp-24
make -s example-cp-24 PRINCIPAL="--principal PRIN-CO-002" INTENT="--intent credit-review"
make -s example-cp-24 SCENARIO='--scenario {"rate_shift_bp":300,"collateral_shift_bp":-2000,"collateral_class":"real_property"}'
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- Scenario is recorded as a closed request object; undeclared members/types refuse.
- Derived interest/headroom/collateral outputs identify the assumptions used.
- Stale observed inputs remain stale after stress arithmetic; scenario does not reset observed_at, freshness, TTL or Debt.
- Changing scenario while holding evidence constant leaves Context Debt unchanged.
- The product remains deterministic what-if arithmetic, not a forecast/probability model.

For exact byte-for-byte output, content addresses or measured figures, use the qualified SDK tree's committed tests/transcripts. This guide describes the invariant behavior a reproducer should see.

## How the example works

```
qualified source estate
  ↓
acquisition
  ↓
SignalEnvelope / governed source evidence
  ↓
L2/L3 context state
  ↓
L4 operators + policy/temporal bounds
  ↓
L5 projection
  ↓
L6 gates / Debt fulfillment / composition where applicable
  ↓
served product OR governed refusal
```

## Variations to try

| Purpose | Command | Expected semantic change |
|---|---|---|
| Credit role | `make -s example-cp-24 PRINCIPAL="--principal PRIN-CO-002" INTENT="--intent credit-review"` | Different role-conditioned product. |
| More severe scenario | `make -s example-cp-24 SCENARIO='--scenario {"rate_shift_bp":300,"collateral_shift_bp":-2000,"collateral_class":"real_property"}'` | Scenario-derived outputs change; factual Debt should not. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_24_whatif.py tests/examples/test_cp_24_sabotage.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- Facts and hypotheticals can coexist without conflating their provenance.
- Scenario assumptions can be governed, hashed and replayable as request state.
- Changing assumptions need not change Context Debt when factual evidence is unchanged.

## What it does not prove

- Forecast accuracy or probabilities.
- Recommended stress/sensitivity calibration.
- That CP-24 is a composite over CP-23—it deliberately reads authoritative sources as a sibling product.

## Spec → code lesson for Cowork

Use CP-24 when the spec is explicitly conditional. Cowork must keep observed evidence and assumptions in different structures and tests should assert scenario-only changes do not alter factual Debt.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.
``````

</details>

