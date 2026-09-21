<!--
  CP-SPEC-024 — Portfolio What-If / Stress Context.
  Gate 1 ONLY. Authored to Context Product Specification Standard v0.3 before
  any code exists, per `D-IMPL-319` and the rule *specs come before code*.

  Source: `references/cbcib-portfolio-management-CLAUDE.md` (Dave's `cbcib`
  Portfolio Management POC requirements, supplied 2026-09-20) and the CP-24
  definition derived from it in `docs/GATE-0-COVERAGE-CP15-24.md` §4.2.

  NOTHING HERE IS AUTHORIZED TO BE BUILT. Gate 2 is Dave's.
-->

# Portfolio What-If / Stress — Context Product Specification

**Rung 24 · Postgres (+ the graph watermark) · `cib.portfolio-what-if`**

**Status: GATE 1 — awaiting Dave's ruling. No implementation, no SDK work, no
`D-IMPL` id spent.**

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
| **Declared gates** | §G.1 — 16 gates, `WIF-G01`..`WIF-G16` |

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

**EVERY MAGNITUDE IS AN INTEGER IN BASIS POINTS, and that is a measured
requirement rather than a style choice** (`Q1`, §F.4). Measured 2026-09-21: a
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

**Trap 2 — collateral valuations are up to 320 days old.** An `inventory`
valuation averaging 320 days is stale evidence, and stressing a stale value
compounds the staleness. **Binding:** the valuation age travels with every
stressed figure, and the observed valuation's own freshness continues to drive
`D_c` exactly as rung 23 established. The scenario does not refresh anything.

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

### D.3 Where the separation lives, and why it is structural

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

#### `Q1` — how does a fractional magnitude cross the wire? **(capability)**

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

#### `Q2` — does CP-24 COMPOSE CP-23, or re-assemble the same shape? **(scope)**

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

### G.1 Intended product gates — 16

| id | What it asserts | Red when |
|---|---|---|
| `WIF-G01` | the served operator set is the class's declaration and the executed plan runs Policy first | a key is dropped or reordered |
| `WIF-G02` | the `scenario` is a CLOSED object: an undeclared member is refused, and a third level is not expressible | the object is opened, or nesting is admitted |
| `WIF-G03` | a magnitude outside its declared domain is refused by name; the refusal is a request-contract violation, not a policy one | the domain is widened |
| `WIF-G04` | **a JSON fraction is refused** rather than silently rounded — the float path never yields an address | a float reaches canonicalization and succeeds |
| `WIF-G05` | the scenario crosses a DOOR and the product served over it is byte-identical to the in-process one | the door drops or mangles a scenario member |
| `WIF-G06` | **no claim in the served view carries a scenario magnitude** — the assumptions never entered the fabric | a scenario value is minted as a claim |
| `WIF-G07` | every scenario-derived measure is labelled `basis: scenario` and names the assumption it used | a derived measure is served unlabelled |
| `WIF-G08` | every stressed figure is served beside the OBSERVED figure it came from, and the observed one carries source lineage | a stressed figure is served alone |
| `WIF-G09` | the base rate is an observed claim at `as_of`, and the shifted rate is derived from it and the shift — all three served | the shifted rate is served as if observed |
| `WIF-G10` | the collateral shift applies only to the named asset class; other classes are unchanged | the shift leaks across classes |
| `WIF-G11` | a stressed collateral figure carries its valuation age | the staleness of the observed input is lost |
| `WIF-G12` | the coverage roll-up names WHICH members cross the floor, not only how many | the roll-up is a bare count |
| `WIF-G13` | `D_c` measures the OBSERVED evidence and is unchanged by the scenario — two scenarios over one instant give identical debt | the assumptions move the debt |
| `WIF-G14` | CP-21's regulatory inputs are named nowhere in the tree | `limit_definition`, `bank_capital` or `connection_basis` appears |
| `WIF-G15` | the same scenario at the same instant replays to the same content address | any input is re-derived rather than resolved |
| `WIF-G16` | a DIFFERENT scenario over identical observed facts is a DIFFERENT determination — so `WIF-G15` cannot be met by ignoring the scenario | the scenario stops reaching the address |

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
- **Intended gates:** 16, one flagged as at risk of `unavailable`.
- **Owed:** **one capability question** (`Q1`, the wire form — recommend
  integers in basis points; explicitly do *not* change SDK parsing) and **one
  scope decision** (`Q2`, sibling or child — recommend sibling, and say plainly
  that the child route is a materially larger rung).
- **Not started:** no implementation, no SDK work, no `D-IMPL` id spent.
