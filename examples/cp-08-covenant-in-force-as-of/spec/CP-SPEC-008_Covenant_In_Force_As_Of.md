---
product: credit-risk.covenant-in-force.v1
standard: v0-3
owner: vault
sdk_spec: cp-08
tier: 3
cost_band: "×2–4"
assembly_mode: 1
capability_classes: [relational, graph-traversal, in-memory]
prerequisites: [facility-terms-snapshot, corporate-family-tree, obligor-financial-spread]
topic: context-products
title: Covenant-in-Force As-Of — Context Product Specification
generated: '2026-09-11'
---

# Covenant-in-Force As-Of — Context Product Specification

**`CP-SPEC-008` · rung 08 · Tier 3 · FLAGSHIP · `credit-risk.covenant-in-force.v1`**
**Fluree `fibo-v2` for covenants, amendments and both time axes · PostgreSQL `ccf_v2` for facilities, drawdowns and the breach-threshold policy register**

> **Which covenants were in force on the drawdown date?**
>
> One question. Not *were they breached*, not *what does policy say now* — **what
> bound this facility on that day, and what did the bank know then.**

## 0 · What this document is

**Gate 1. No implementation code exists.** Nothing under
`examples/cp-08-covenant-in-force-as-of/` but this specification. The rung
returns to Gate 1 first, per the discipline `CP-SPEC-007` restored.

Every figure below was **measured against the curated `.76` estate on
2026-09-11** before this document was written. Where a figure is a population
count it is reported as evidence a reader can reproduce, **never as a test
fixture** — the estate grows, and a spec that pinned `45 facilities` would make
its own tests wrong on the day another facility lands.

### 0.1 Placeholder discipline

No `[TBC]` in this document. Two properties the vault article assumes are
**measured absent** from the estate; they are named in §0.5 and the assembly is
designed around them rather than written as though they were there.

### 0.2 The estate is read-only, and that is a design constraint

`.76` is the curated evidence estate. **Nothing in this product's assembly, its
examples, or its tests may write or amend the live Fluree ledger.** The ledger
is append-only, so a seeded assertion is permanent; and a product that had to
mutate the estate to demonstrate itself would be demonstrating the mutation.

This has a sharp consequence for the flagship claim, and §D.6 states it: the
"amend a covenant and re-read at the old `t`" demonstration the vault describes
**cannot be run against `.76`**. What replaces it is stronger, not weaker.

### 0.3 Capability gate — above §A because it schedules the build

| Capability | Needed for | Present? |
|---|---|---|
| Valid-time interval on covenant assertions | `as_of` filtering | **yes** — `ex:validFrom` on every covenant |
| Assertion-time stamp on amendments | `known_as_of` filtering | **yes** — `ex:assertedAt` |
| An engineered gap between the two | the whole bitemporal demonstration | **yes** — three, with a drawdown inside each |
| Ledger transaction-time pin | reproducible re-read | **yes** — `FlureeGraphStore.post_query_pinned` |
| Covenant-level supersession markers | superseded-set return | **NO** — see §0.5 |
| Ledger `t` ↔ calendar date mapping | the vault's literal step 3 | **NO** — see §0.5 |

### 0.4 The four-question test

- **Is the answer assembled rather than stored?** Yes. No store holds
  *"the covenants in force on 2025-09-09 as known on 2025-09-09"*; it is a
  two-axis cut over assertions that live in one store and facilities that live
  in another.
- **Does more than one consumer need it?** Yes — credit, workout, audit and
  counsel, and the three want *different instants on different axes*.
- **Does it carry a governed freshness claim?** Yes, and an unusual one: a
  closed as-of answer does not decay (§E).
- **Would a `SELECT` do?** **No, and this is the rung where that stops being a
  matter of convenience.** A `SELECT` against current state returns today's
  covenants with full confidence and no signal that it answered a different
  question than the one asked.

### 0.5 Two measured absences, and what the spec does about them

The vault article is on the older Q019 form and predates the loaded estate.
Read by **heading name** rather than section letter, per the recipe. Two of its
assumptions do not hold, and both were measured rather than inferred.

**(1) Covenants carry no supersession marker.** The vault's *Decision frame*
says an amended covenant *"writes the new terms while preserving the
pre-amendment terms in force, with a supersession marker."* Measured on
`fibo-v2`: **180 `ex:Covenant` nodes, of which 0 carry `ex:supersededBy` and 2
carry `ex:validTo`.** The 1,107 `supersededBy` assertions in the ledger sit on
`WarningSignal` (486), `OpportunitySignal` (354), `CreditRating` (215),
`IssuanceEvent` (111), `PriorObservation` (49), `BreachOfCovenant` (4) and
`PolicyVersion` (2) — every class except the one this product reads.

*What the spec does:* `include_superseded` is **declared and inert** at this
tier (§B.2). The product does not fabricate a superseded set it cannot source,
and does not silently return an empty one — it refuses the parameter by name
with the declared reason, which is the `CP-SPEC-007` §B.2 discipline applied to
a capability rather than a tier.

**(2) The ledger's `t` axis is load order, not booking chronology.** The vault's
*Assembly Recipe* step 3 says to *"query the ledger at the block corresponding
to `known_as_of`."* There is no such block. `src/ccf/graph/backends/fluree.py`
records the ruling this rests on (`D-IMPL-240` (2), ledger row `24.5-L-01`):
Fluree's `t` *"is a commit counter that advances on a data no-op and orders
writes, not observations,"* and **substituting `t` for `as_of` is the
transaction-time-for-observation-time error the ruling forbids.** The estate
was loaded in waves, so its `t` ordering encodes when `ccf_dataprep` wrote rows
— not when a bank booked an amendment.

*What the spec does:* **both clocks are read from DATA, and the ledger pin keeps
the role the SDK already gives it.** `as_of` cuts on `ex:validFrom`/`ex:validTo`;
`known_as_of` cuts on `ex:assertedAt`. The pinned read (`t`) bounds the STORE so
the answer is reproducible, and enters lineage as **execution provenance**
(`D-IMPL-309`), never as a temporal cut. This is not a weakening of the vault's
design — it is the vault's design with the two axes put on the axis the estate
actually models them on.

### 0.6 The store's data model is NOT the SDK's, and nothing below changes that

Every vocabulary term in this document — `ex:Covenant`, `ex:validFrom`,
`ex:validTo`, `ex:assertedAt`, `ex:amends`, `ex:bookingLagDays`,
`covenant_policy`, `drawdown` — belongs to **the estate and this deployment**,
never to the SDK.

**The SDK ships adapters that reach a backend. It ships no opinion about what
the backend holds.** `FlureeGraphStore` knows how to issue a pinned read and
what a transaction counter is; it does not know what a covenant is, that
`validFrom` is a valid-time axis, or that a booking lag exists. Those are facts
this example declares in its own `artifacts/source-vocabulary.yaml` and reads
through the same mechanism every other rung uses (CLAUDE.md §11, *mechanism,
not values*).

Concretely, and this is the line a reader should hold the Gate-2 build against:

- **In the SDK:** the graph-store Protocol and its Fluree adapter; the pinned
  read; the four operator categories; `Π` as a typed transformation; the
  request contract, its relative defaults and its resolution; the validation
  gates; the replay record.
- **In this example:** that covenants have two time axes, what the predicates
  are called, which store holds which leg, and the two-axis cut itself.

**If the Gate-2 build finds itself wanting a covenant-shaped, amendment-shaped
or bitemporal-shaped concept inside `/src`, that is the defect** — the same
defect class as a half-life table in library code. The temporal cut in §D.4 is
this deployment's `Π`, and the SDK's contribution is that `Π` is a declared,
replayable transformation over a graph it does not interpret.

The one SDK-side fact §0.5 (2) leans on is **not** an exception: the ruling that
Fluree's `t` is transaction time and may not stand in for `as_of` is a statement
about the *adapter's* contract with its substrate, not about covenants. It would
read identically if this product were about shipping manifests.

---

---

## A · Decision frame

**The decision.** *Which covenants bound this facility on this date, and which
of them had the bank actually learned by then?*

**The trigger, in three forms that are not the same question.**

1. **Live** — a credit officer testing a drawdown request against current
   covenants. `as_of` = now, `known_as_of` = now.
2. **Forensic** — a workout team or supervisor asking what bound a drawdown that
   happened months ago. `as_of` = the drawdown date, `known_as_of` = now. *What
   was true?*
3. **Dispute** — counsel asking what the bank **knew** was true on that date.
   `as_of` = `known_as_of` = the drawdown date. *What did you know, and when?*

Forms 2 and 3 differ only in one parameter and **return different covenant
sets**. That difference is this product's subject.

### A.1 Counterfactual — `temporally-incoherent`

The closed-taxonomy mode is *temporally incoherent*, and the failure is silent.

A loan system that stores covenants as current state answers form 2 and form 3
identically, and answers both with today's terms. It is not that the answer is
approximate: it is an answer to a question nobody asked, returned with the same
confidence as a correct one. The failure surfaces under supervisory examination
— after the institution has already relied on it.

### A.2 The measured exhibit — `FAC-01BB3F`

The estate carries a facility where the three forms genuinely diverge.

| fact | value |
|---|---|
| Amendment | `AMD-01BB3F-2`, *"Amendment 2 to FAC-01BB3F"* |
| Effective (`ex:validFrom`) — **valid time** | **2025-08-14** |
| Booked (`ex:assertedAt`) — **assertion time** | **2025-10-05** |
| `ex:bookingLagDays` | **52** |
| `ex:isEngineeredBookingLag` | `true` |
| Drawdown inside the gap | `DRW-01BB3F-0000`, **2025-09-09**, USD 4,500,000 |
| `ccf_v2.drawdown.falls_in_booking_gap` | `true` |

On **2025-09-09** the amendment **was legally in force** and the bank **had not
yet booked it**. A drawdown was taken that day. Asked about that date:

- **form 2** (`as_of=2025-09-09`, `known_as_of=today`) returns the amended terms
  — what was true;
- **form 3** (`as_of=known_as_of=2025-09-09`) returns the pre-amendment terms —
  what the bank could see, and what it acted on in good faith.

A single-timeline store returns one answer to both and signals nothing.

**Two further engineered cases** exist and are the directional controls, so the
demonstration is not one lucky row: `AMD-2A2C38-3` (44-day gap, **2** drawdowns
inside) and `AMD-405B7A-3` (45-day gap, 1 drawdown inside, USD 99,000,000).

### A.3 What this product is not

Out of scope at this rung, stated here so the boundary is visible before §B:

- **Breach scoring.** Whether a covenant was *breached* needs period-appropriate
  financials against period-appropriate thresholds; that is a distinct product.
  `evaluate_headroom` is declared and inert (§B.2).
- **Policy analysis.** Policy versions are read to pin which register was in
  force; the policy register is not a second product here.
- **Any write path.** §0.2.

---

## B · Contract

### B.1 The nine elements

| # | Element | Value |
|---|---|---|
| 1 | **Name** | `credit-risk.covenant-in-force` |
| 2 | **Version** | `1.0.0` |
| 3 | **Subject** | one `facility_id` |
| 4 | **Payload** | the covenant set in force at the two declared instants, each with its type, threshold, validity interval and the amendment that produced it; the amendments admitted and those excluded **by which axis**; the drawdowns in the window |
| 5 | **Lineage** | both legs, plus `as_of`, `known_as_of` and the ledger `t` as execution provenance |
| 6 | **Policy** | the breach-threshold register version effective at `as_of` |
| 7 | **Debt** | `D_c` from covenants whose amendment chain resolved ÷ covenants served |
| 8 | **TTL** | dual — see §E.3 |
| 9 | **Determinism** | class 1, pure algorithmic. No model call anywhere in §D |

### B.2 Request parameter surface — bitemporal

| Parameter | Type | Moves | Default | Expected effect |
|---|---|---|---|---|
| `facility_id` | string, **required** | anchor | — | unresolvable ⇒ refusal, never an empty covenant set |
| `principal_scope` | array, **required** | `P` envelope | — | the admitted set the policy step reads |
| `as_of` | string (ISO date) | **`T` — valid time** | **relative, offset 0** | which covenants were in force |
| `known_as_of` | string (ISO date) | **`T` — assertion time** | **relative, offset 0** | which of them the bank had booked |
| `include_superseded` | bool | payload shape | — | **declared and inert** (§0.5) |
| `evaluate_headroom` | bool | payload shape | — | **declared and inert** (§A.3) |

**Both defaults are declared RELATIVE, and that is a requirement rather than a
preference** (`D-IMPL-325`). The vault article gives `as_of` a default of
*"today"* and `known_as_of` a default of *"now"*. Neither may be authored as a
literal date: `CP07-F-03` measured what happens when a temporal default is
written as a literal — it means one window the day it is written and a different
one a year later, with nothing anywhere saying it drifted. The class declares:

```yaml
relative_defaults:
  as_of:
    offset_seconds: 0
    render: date
  known_as_of:
    offset_seconds: 0
    render: date
```

> **An offset of `0` is refused by the SDK** — `RelativeDefault` requires a
> negative offset, because a window reaches into what has happened, and `0` is
> `asked_at` itself, which `defaults` already expresses. **This is a genuine
> conflict between the mechanism and this product's need, and it is recorded as
> `CP08-F-01` rather than worked around.** Both readings are live at Gate 1:
> either the mechanism widens to admit `0` as *"the request's own instant,
> rendered"* — which is what *today* and *now* mean — or the class declares no
> default and the door supplies `asked_at`, which puts a governance value back
> in deployment code and is the shape `D-IMPL-315` keeps out. **This needs a
> ruling before Gate 2**, and the spec does not choose one.

**`as_of` and `known_as_of` are two filters and dropping either answers a
different question.** The validation gate in §D.7 holds both, and it is the gate
this rung exists to add.

**Why `include_superseded` and `evaluate_headroom` are declared at all.** Both
are part of the uniform request surface the Standard §2.4 describes, and a
parameter that is silently absent reads as *unsupported by oversight* rather
than *unsupported by decision*. Declared-and-inert refuses them by name with the
declared reason, exactly as `CP-SPEC-007` declared `as_of` at Tier 2 and this
rung makes it real.

---

## C · Data catalog

### C.1 Element table

| Element | Provenance | Class | Store | `G` |
|---|---|---|---|---|
| Facility, borrower, facility terms | internal loan system | synthetic — internal | **PostgreSQL** `ccf_v2.facility` | `E` |
| Covenant — type, threshold, unit | EDGAR **EX-10**, parsed | public where parsed; synthetic where templated | **Fluree** `fibo-v2` | `R`, `T` |
| Covenant validity interval | derived at load | mixed | **Fluree** | **`T` — valid time** |
| Amendment, effective date, sequence | **8-K Item 1.01**; amended-and-restated EX-10 | public | **Fluree** | `T` |
| **Amendment booking date** | internal loan-ops workflow | **synthetic — engineered** | **Fluree** | **`T` — assertion time** |
| Covenant definitions | EX-10 defined-terms | public | **Fluree** | `R` |
| Drawdown events | internal loan system | synthetic — internal | **PostgreSQL** `ccf_v2.drawdown` | `T` |
| Breach-threshold register | internal credit policy | synthetic — internal | **PostgreSQL** `ccf_v2.covenant_policy` | `P`, `T` |

### C.2 What is measured, and it is evidence rather than a fixture

Measured 2026-09-11 against `fibo-v2` and `ccf_v2`. **No test may pin these
numbers**; they are here so a reader can reproduce the shape of the estate.

| population | measured |
|---|---|
| `ex:Covenant` nodes | 180 |
| Facilities carrying ≥1 covenant | 45 |
| Covenant types | `leverage` 85 · `interest_coverage` 63 · `fixed_charge_coverage` 58 · `minimum_liquidity` 42 · `secured_leverage` 20 · `net_capital` 2 |
| Amendments (`ex:amends`) | 137 across 135 facilities |
| **Amendments carrying `assertedAt` AND `bookingLagDays`** | **25** |
| **Engineered booking lags** | **3** |
| Drawdowns | 151, of which **3** carry `falls_in_booking_gap` |
| Policy versions with supersession | 2 |

**The bitemporal subset is 25 of 137 amendments, and that is the honest
denominator for this product's Context Debt** (§E.2). An amendment with no
`assertedAt` cannot be placed on the assertion axis at all; the product serves it
with that stated rather than assuming it was booked on its effective date.

### C.3 Correlation key and single-writer discipline

`facility_id` correlates the two legs. Fluree is authoritative for covenants,
amendments and both temporal axes; PostgreSQL for facilities, drawdowns and the
policy register. **Neither leg is written by this product** (§0.2), and within
the fabric L2 remains the only writer to L3.

---

## D · Assembly recipe

### D.1 Client call — the dispute case

```
GET /context-products/credit-risk/covenant-in-force/FAC-01BB3F
      ?principal_scope=FAC-01BB3F
      &as_of=2025-09-09
      &known_as_of=2025-09-09
```

The drawdown date on both axes. Change `known_as_of` to today and the same
facility returns a different covenant set; that pair is the product's proof.

### D.2 Step table

| # | Layer | Operator | Store | Emits |
|---|---|---|---|---|
| 1 | L1/L2 | *(acquisition)* | PostgreSQL | facility, borrower, drawdowns in window |
| 2 | L4 | `policy.principal-subgraph` | — (over L3) | the admitted facility set |
| 3 | L4 | `traversal.typed-neighborhood` | — (over L3) | covenants, definitions and amendments reachable from the facility |
| 4 | L5 | `Π` covenant-in-force | in-memory | the two-axis cut, and the exclusion record |

**Two registered operators, not five verbs.** The vault's recipe names Resolve,
Policy, TemporalTraversal, Enrich and Evaluate. Those are *stages of the
reasoning*, and the SDK's operator vocabulary is closed at four categories
(`D-IMPL-223`). Resolve and Enrich are **acquisition**, which happens before L2
and registers no operator; Evaluate is out of scope (§A.3); and the temporal cut
is **`Π`**, not a traversal, because it selects and shapes truth rather than
reaching for more of it.

### D.3 Step detail — acquisition (step 1)

The facility and its drawdowns are read from PostgreSQL **at the bound
governance resolved**, never read wide and filtered afterwards. The covenant and
amendment assertions are read from Fluree through the **pinned** read
(`FlureeGraphStore.post_query_pinned`), so the store is bounded and the answer
reproducible.

Both legs are `SELECT`-only. An unresolvable `facility_id` **raises rather than
returning an empty covenant set**: an empty set is a claim about the world and
an unknown facility is a claim about the request.

### D.4 Step detail — the two-axis cut (step 4)

For each covenant assertion reachable from the facility:

```
admitted  ⟺  validFrom ≤ as_of
             AND (validTo is absent OR as_of < validTo)      ← valid time
             AND assertedAt ≤ known_as_of                    ← assertion time
```

**An amendment with no `assertedAt` is not assumed booked.** It is excluded from
the assertion-time filter and **recorded as unplaceable**, which is what drives
Context Debt (§E.2). Assuming `assertedAt = validFrom` would manufacture the very
coincidence the product exists to disprove.

**The exclusion record is part of the payload, not a log line.** For every
assertion excluded, the payload says **which axis excluded it**. A covenant
absent because it was not yet in force and a covenant absent because the bank had
not yet learned of it are different facts, and a consumer that cannot tell them
apart has the single-timeline problem back in a new place.

### D.5 Determinism and the emitted contract

Class 1. Two serves of one question at one instant reach one content address.
`CovenantInForceContract@v1.0.0` carries both instants as first-class lineage
fields and the ledger `t` as execution provenance (`D-IMPL-309`) — **`t` is not
part of product identity**, because where the evidence lives is not what the
answer says.

### D.6 Replay, and the demonstration that replaces the vault's

The vault proposes: *"run the query, note the `t`, amend a covenant, re-run at
the original `t`, and get the original answer back."* **That cannot be run
here** — it amends the curated ledger (§0.2).

What replaces it is available, repeatable, and tests the same property:

1. Serve at `(as_of, known_as_of)` and record the ledger `t` from lineage.
2. **Re-serve at the recorded `t` after any later ledger activity** — the
   estate advances on its own as `ccf_dataprep` loads — and get the identical
   content address back.
3. **Vary `known_as_of` alone across a booking gap** and watch the covenant set
   change while `as_of` is held. The historical state is reconstructed from data
   the product did not have to mutate to observe.

Step 2 is the *substrate remembers* claim. Step 3 is the *two clocks are two
questions* claim. Neither requires a write.

### D.7 Validation gates

The SDK's three universal L6 gates apply unchanged. This product declares a
**fourth**, and it is the reason the rung exists:

> **Temporal coherence.** Every assertion in the served set satisfies
> `validFrom ≤ as_of < validTo` (where `validTo` is present) **and**
> `assertedAt ≤ known_as_of`. A served assertion violating either means one of
> the two filters was dropped, and the product refuses rather than serving an
> answer to a question nobody asked.

The gate is declared as data and identified in the replay record, per
`D-IMPL-282`. **Its sabotage is a one-line filter removal**, and the gate must be
observed red under it before it is recorded as passing.

---

## E · Volatility, debt and materialization

### E.1 Half-life table

| Signal class | `λ_c` | Note |
|---|---|---|
| Covenant structure | ~180 days | amendment-driven |
| Covenant definitions | ~365 days | rarely amended independently |
| Breach-threshold register | ~180 days | policy review cycle |
| **A closed as-of answer** | **∞** | the past does not change |

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

### E.2 Debt model

`D_c` on this product is **not** a freshness score, and that is the point. It is
the fraction of the covenant set whose **amendment chain could be placed on the
assertion axis**:

```
D_c = 1 − (assertions with a resolvable assertedAt ÷ assertions served)
```

Measured shape: **25 of 137 amendments carry `assertedAt`**, so on a facility
whose amendments are outside that subset the product serves the covenants and
says, in the debt signal, that it could not tell you what the bank knew. That is
a real property of the answer and the consumer needs it.

### E.3 Materialization and the dual TTL

Derived per request; never materialized. **TTL is anchored on the latest
assertion among the served set, never on request time** — and the product
carries two regimes:

- **live** (`as_of` = the request's own instant) — short, because the answer
  moves when the next amendment is booked;
- **closed** (`as_of` names a settled past date **and** `known_as_of` is also
  closed) — long, because neither what was true nor what was known can now
  change.

The same endpoint carrying two TTLs from one parameter pair is a consequence of
ledger-backed temporality worth showing, and it is the reason `ttl_anchor` is
`from_entity_freshness` rather than `from_decision`.

### E.4 Supersession triggers

8-K Item 1.01 amendment · 8-K Item 2.04 acceleration · internal amendment
booking · policy-version change. Each **appends**; none overwrites. No trigger
destroys the prior answer, which is what makes a closed as-of answer permanent.

---

## F · Source binding and readiness

*(The current Standard's section; the vault article's corresponding heading is
**Manufacture envelope**, on the older Q019 lettering — resolved by heading, per
the recipe.)*

### F.1 Readiness against the vault's envelope

| the vault asks for | measured | verdict |
|---|---|---|
| ~40 facilities | 60 in `ccf_v2.facility`; 45 carry covenants | **met** |
| ~12 facilities with ≥1 amendment | 135 facilities carry amendments | **met** |
| ≥3 facilities with 2+ sequential amendments | `amendmentSeq` present; the three lag cases are amendments 2, 3 and 3 | **met** |
| **≥1 amendment with an engineered booking lag, drawdown inside the gap** | **3**, each with ≥1 in-gap drawdown | **met** |
| ≥4 covenant types per facility | 6 types estate-wide; `FAC-01BB3F` carries 4 | **met** |
| ≥2 policy versions with distinct effective dates | 2, with `effective_from`/`effective_to` | **met** |
| ≥1 covenant in breach at a past date but compliant today | 2 `BreachOfCovenant` nodes, both superseded | **met, and out of scope** (§A.3) |
| Covenant supersession markers | **0 of 180** | **NOT met** — §0.5 (1) |
| Ledger `t` ↔ booking date | **absent by construction** | **NOT met** — §0.5 (2) |

### F.2 Access path

Connection material from the estate's own environment; **the namespaces do
not** — `.env` names the v1 estate and this product reads **v2**
(`fibo-v2`, `ccf_v2`). Deriving namespaces from `.env` points the run at v1.

### F.3 Known limits, carried as findings

- **`CP08-F-01`** — the relative-default mechanism refuses an offset of `0`,
  and `as_of`/`known_as_of` need exactly that. **Gates the request contract**
  (§B.2).
- **`CP08-F-02`** — covenant supersession is unmarked in the estate, so
  `include_superseded` is inert. Recorded, not designed around silently.
- **`CP08-F-03`** — 112 of 137 amendments carry no `assertedAt` and cannot be
  placed on the assertion axis. This is the debt signal's subject (§E.2), not a
  defect to repair.

---

## G · Operate and govern

### G.1 Product gates

The acceptance authority for every gate is **this clause** (`D-IMPL-326`).

| Gate | Asserts |
|---|---|
| `CIF-G01` | a later `as_of` admits no fewer covenants than an earlier one, `known_as_of` held |
| `CIF-G02` | a later `known_as_of` admits no fewer covenants than an earlier one, `as_of` held |
| `CIF-G03` | **across a booking gap, `as_of` held and `known_as_of` varied returns DIFFERENT covenant sets** |
| `CIF-G04` | every served assertion satisfies both filters — the temporal-coherence gate |
| `CIF-G05` | a served set whose coherence is violated is refused, observed under sabotage |
| `CIF-G06` | the exclusion record names **which axis** excluded each omitted assertion |
| `CIF-G07` | an amendment with no `assertedAt` is excluded and counted, never assumed booked |
| `CIF-G08` | `include_superseded` and `evaluate_headroom` are refused by name with their declared reasons |
| `CIF-G09` | an unresolvable `facility_id` refuses; it does not return an empty covenant set |
| `CIF-G10` | re-serving at a recorded ledger `t` reproduces the content address |
| `CIF-G11` | the ledger `t` is in lineage as execution provenance and **not** in product identity |
| `CIF-G12` | replay dimension 2 is a superset of product policy lineage |
| `CIF-G13` | `D_c` moves with the resolvable-assertion ratio, not with the estate |
| `CIF-G14` | a closed as-of answer carries the long TTL and a live one the short TTL |

**All directional or structural. No estate population is pinned** — `CIF-G03`
names the booking-gap *relationship*, not the three amendment ids, so the gate
survives a fourth engineered lag being added.

### G.2 Acceptance criteria

1. The two axes are separately parameterised and separately filterable, and
   varying either alone changes the answer.
2. The booking-gap divergence is demonstrated on real estate data, with a
   drawdown inside the gap.
3. Every omitted assertion is accounted for by axis.
4. The product writes to neither source store.
5. A recorded ledger `t` reproduces its answer after later ledger activity.
6. `D_c` reports the assertion-axis resolvability of the served set.

### G.3 What Gate 2 must resolve before any code

- **`CP08-F-01`** — the `offset_seconds: 0` question. The request contract
  cannot be authored until it is ruled.
- Whether `include_superseded` stays inert at this tier or the rung is deferred
  until the estate marks covenant supersession.
