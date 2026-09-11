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

**`CP-SPEC-008` · rung 08 · Tier 3 · `credit-risk.covenant-in-force.v1`**
**Fluree `fibo-v2` for covenants and amendments · PostgreSQL `ccf_v2` for facilities, drawdowns and the breach-threshold register**

> **Which amendments bound this facility on the drawdown date, and which of them
> had the bank actually booked by then?**
>
> One question, on two clocks. Not *were the covenants breached*, not *what does
> policy say now*, and — after Gate 1's measurement — **not** *what did a
> superseded covenant say*: the estate has no superseded covenant, and §0.5
> records why this specification does not claim one.

> **SCOPE NARROWED AT GATE 1 (Option B, Dave, 2026-09-11).** The vault frames
> rung 08 as a flagship demonstrating *"ledger time-travel with supersession
> preserved rather than overwritten."* **The supersession half is withdrawn**,
> on measurement rather than on preference: no covenant in this estate is ever
> superseded, and a product may not teach a property its data does not have.
> What remains — two clocks, a real booking lag, and a reproducible pinned read
> — is measured, demonstrable, and smaller. `spec/MEASUREMENT-NOTE.md` carries
> the evidence.

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

This has a sharp consequence, and §D.6 states it: the *"amend a covenant and
re-read at the old `t`"* demonstration the vault describes **cannot be run
against `.76`**. It would need a write — and, as Gate 1 went on to measure, it
would also need a superseded covenant, which the estate does not hold.

### 0.3 Capability gate — above §A because it schedules the build

| Capability | Needed for | Present? |
|---|---|---|
| Valid-time interval on amendments | `as_of` filtering | **yes** — `ex:validFrom` |
| Assertion-time stamp on amendments | `known_as_of` filtering | **yes** — `ex:assertedAt`, on 25 |
| An engineered gap between the two | the bitemporal demonstration | **yes** — three, with a drawdown inside each |
| Ledger transaction-time pin | reproducible re-read | **yes**, and measured — §0.5 |
| Assertion time **on covenants** | covenant-level `known_as_of` | **NO** — 0 of 180; §0.5 (1) |
| Covenant supersession | superseded-set return | **NO** — 0 of 180, at every ledger point; §0.5 (2) |
| Ledger `t` ↔ calendar date | the vault's literal step 3 | **NO** — §0.5 (3) |

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

### 0.5 What Gate 1 measured, and what it withdrew

The vault article is on the older Q019 form and predates the loaded estate.
Read by **heading name** rather than section letter, per the recipe. Three of
its assumptions were measured against `.76`, read-only. One holds, two do not.

**The instruction that shaped the measurement, and it is the right one:
a booking lag is not proof of supersession.** The two claims were measured
apart.

#### (1) Two clocks — HOLDS, on amendments rather than on covenants

*What would prove it:* the same subject, with `as_of` inside its validity
interval, where moving `known_as_of` from before to after `assertedAt` **changes
the answer**.

Measured: **`assertedAt` appears on ZERO covenants** — on the three booking-lag
facilities and across the whole ledger at every point sampled. It lives on the
**amendment** nodes. So nothing on a covenant can be filtered by `known_as_of`,
and the covenant set is identical on both sides of a booking gap.

It holds one level up and genuinely: `AMD-01BB3F-2` carries
`validFrom 2025-08-14` and `assertedAt 2025-10-05`, so it is excluded at
`known_as_of=2025-09-09` and admitted after. **The product's bitemporal subject
is therefore the amendment slice**, and §B.2 says so rather than implying the
covenants move.

#### (2) Supersession preserved — WITHDRAWN

*What would prove it:* a later amendment replacing a covenant assertion, where
querying the ledger at the original `t` still returns the prior one.

Measured three ways, all negative. Covenant thresholds are **unchanged across
the entire ledger** — 180 at `t:1500` through head `t:5591`, zero changed and
zero added at every point. **No covenant interval is ever closed** (`validTo`
constant at 2) and **no covenant ever gains a marker** (`supersededBy` 0 at
every point). And the ledger's 1,107 supersession markers belong to
`WarningSignal`, `CreditRating`, `IssuanceEvent`, `PolicyVersion` and others —
**not to the covenant slice this product reads**, so per the instruction they do
not count.

The ledger's covenant history is a single staged load, not an amendment
lifecycle. **There is nothing for time-travel to reconstruct**, so the claim is
removed from the title, the gates and the teaching text rather than softened.

#### (3) The ledger cannot carry `known_as_of` — and was never going to

The vault's step 3 says to *"query the ledger at the block corresponding to
`known_as_of`."* There is no such block. `src/ccf/graph/backends/fluree.py`
records the ruling (`D-IMPL-240` (2), ledger row `24.5-L-01`): Fluree's `t`
*"orders writes, not observations,"* and **substituting `t` for `as_of` is the
transaction-time-for-observation-time error the ruling forbids.** The estate was
loaded in waves, so its `t` encodes when `ccf_dataprep` wrote rows.

*What the spec does:* **both clocks are read from DATA** — `as_of` cuts on
`validFrom`/`validTo`, `known_as_of` on `assertedAt` — and the pinned read keeps
the role the SDK already gives it: it bounds the STORE and enters lineage as
execution provenance (`D-IMPL-309`), never as a temporal cut.

#### What the pinned read DOES give, measured

The one property of the substrate this product still leans on was verified
rather than assumed. A pinned read genuinely reconstructs a ledger point: all
typed subjects read **0 → 17,230 → 17,871** at `t:1`, `t:2000` and head, and a
pin past head returns `408 err:db/ReadAfterWriteTimeout`.

That measurement began as a suspected substrate defect — `covenantOf` read 182
at `t:1` while all typed subjects read 0, which cannot both be true of one
ledger state. The control settled it: the load wrote thin `covenantOf` edges
first and attributed nodes later, which is this repository's own documented
ingestion order. **The pin is honest**, and `CIF-G08` rests on it.

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

**The decision.** *Which amendments bound this facility on this date, and which
of them had the bank actually booked by then?*

**Amendments, not covenants, and the difference is the whole of §0.5 (1).** The
covenants a facility carries are served as context — they are what the
amendments govern — but the estate versions neither their terms nor their
assertion time, so they do not move with either clock. **What moves, and what
this product is about, is the amendment set.**

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

- **form 2** (`as_of=2025-09-09`, `known_as_of=today`) **admits** the amendment
  — it was in force on that date, and we know it now;
- **form 3** (`as_of=known_as_of=2025-09-09`) **excludes** it — the bank had not
  booked it, and acted in good faith on the facility as it then stood.

**Two answers, from one facility, at one `as_of`, differing only in what was
known.** A single-timeline store returns one answer to both and signals nothing.

What the product does **not** say is that the covenant *terms* differed between
those two answers. They do not, in this estate, and §0.5 (1) is why.

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
- **Supersession.** Withdrawn at Gate 1 on measurement (§0.5 (2)). A superseded
  covenant set is not served, not gated and not taught, because the estate holds
  none.
- **Any write path.** §0.2.

---

## B · Contract

### B.1 The nine elements

| # | Element | Value |
|---|---|---|
| 1 | **Name** | `credit-risk.covenant-in-force` |
| 2 | **Version** | `1.0.0` |
| 3 | **Subject** | one `facility_id` |
| 4 | **Payload** | the **amendment set** admitted at the two declared instants; every amendment excluded, with **which axis excluded it**; the covenants the facility carries, served as context with their terms stated as unversioned; the drawdowns in the window |
| 5 | **Lineage** | both legs, plus `as_of`, `known_as_of` and the ledger `t` as execution provenance |
| 6 | **Policy** | the breach-threshold register version effective at `as_of` |
| 7 | **Debt** | `D_c` from amendments placeable on the assertion axis ÷ amendments served |
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

> **`CP08-F-01` is RESOLVED — `D-IMPL-328` (Dave, 2026-09-11).** An offset of
> `0` was refused until this rung asked for it: `RelativeDefault` required a
> negative offset on the reading that `0` *"is not a relative default at all but
> `asked_at` itself, which `defaults` already expresses."* The first clause is
> right and the second is not — a literal date written into `defaults` is a date
> that **ages**, which is the defect `CP07-F-03` measured. The mechanism now
> admits `0` as the **identity offset**, meaning the request's own instant
> unchanged, and it is ordinary in every other respect: same resolution branch,
> same authority `default`, same contract pin, and the resolved **literal** in
> replay rather than the rule. A positive offset is still refused.
>
> **No `asked_at` is injected in deployment code.** That was the alternative and
> it was declined: it would put a governance value back in the spine for the one
> parameter whose entire subject is *which instant governed this decision*
> (`D-IMPL-315`).

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
facility, at the same `as_of`, returns a **different admitted amendment set** —
`AMD-01BB3F-2` appears. That pair is the product's proof, and it is the
amendment set that moves, never the covenant terms (§0.5 (1)).

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

For each **amendment** reachable from the facility:

```
admitted  ⟺  validFrom ≤ as_of                               ← valid time
             AND assertedAt ≤ known_as_of                    ← assertion time
```

The covenants the facility carries are served alongside, **with their terms
stated as unversioned** — the payload says so rather than implying the terms
were reconstructed for `as_of`, because in this estate they were not (§0.5 (1)).

**An amendment with no `assertedAt` is not assumed booked.** 112 of 137 carry
none. Such an amendment is **recorded as unplaceable on the assertion axis**
rather than admitted or dropped, and that is what drives Context Debt (§E.2).
Assuming `assertedAt = validFrom` would manufacture the very coincidence the
product exists to disprove — it would make every booking lag vanish.

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

### D.6 Replay, and the two demonstrations that survive measurement

The vault proposes: *"run the query, note the `t`, amend a covenant, re-run at
the original `t`, and get the original answer back."* **Neither half is
available.** The amendment writes the curated ledger (§0.2), and there is no
superseded covenant for the re-read to recover (§0.5 (2)).

What replaces it needs no write and was measured at Gate 1:

1. **The pinned read reconstructs a ledger point.** Serve, record the `t` from
   lineage, and re-serve at that `t` after the ledger has advanced — the estate
   advances on its own as `ccf_dataprep` loads. The identical content address
   returns. Verified: all typed subjects read 0 → 17,230 → 17,871 across
   `t:1`, `t:2000` and head, and a pin past head returns
   `408 err:db/ReadAfterWriteTimeout`.
2. **Varying `known_as_of` alone across a booking gap changes the admitted
   amendment set**, with `as_of` held. This is the two-clock claim, and it is
   the one the estate supports.

**What is NOT claimed.** That the substrate preserves a superseded covenant. It
would, in a ledger that had one; this one does not, and a specification that
taught the property anyway would be teaching it from the documentation rather
than from the data.

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
the fraction of the served amendment set that could be **placed on the assertion
axis at all**:

```
D_c = 1 − (amendments with a resolvable assertedAt ÷ amendments served)
```

Measured shape: **25 of 137 amendments carry `assertedAt`**, so `D_c` on most
facilities is high and says something true — *this answer cannot tell you what
the bank knew*. On the three engineered facilities it is low and the answer
carries the second clock. **A debt signal that read the same on both would be
decorative**; this one distinguishes exactly the facilities the product can
answer the dispute question for.

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

### E.4 What would invalidate a served answer

A new amendment being **booked** — that is, an `assertedAt` later than a served
`known_as_of` appearing — changes the answer to a live query and leaves a closed
one untouched. That asymmetry is the dual TTL's whole justification.

**This section deliberately does not list supersession triggers.** The vault's
version does, and in a ledger carrying superseded covenants it would be right.
Measured, this estate has none (§0.5 (2)), so a trigger list here would describe
events the product cannot observe.

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
| ≥1 covenant in breach at a past date but compliant today | 2 `BreachOfCovenant` nodes | **met, and out of scope** (§A.3) |
| **Assertion time on covenants** | **0 of 180**, at every ledger point | **NOT met** — scope narrowed to amendments, §0.5 (1) |
| **Covenant supersession** | **0 of 180**; thresholds unchanged `t:1500`→head | **NOT met** — claim withdrawn, §0.5 (2) |
| Ledger `t` ↔ booking date | absent by construction | **NOT met** — both clocks read from data, §0.5 (3) |

### F.2 Access path

Connection material from the estate's own environment; **the namespaces do
not** — `.env` names the v1 estate and this product reads **v2**
(`fibo-v2`, `ccf_v2`). Deriving namespaces from `.env` points the run at v1.

### F.3 Known limits, carried as findings

- **`CP08-F-01` — RESOLVED** by `D-IMPL-328` (2026-09-11). The relative-default
  mechanism refused an offset of `0`; it now admits it as the identity offset,
  meaning the request's own instant unchanged, with authority, provenance and
  replay identical to any other offset. No `asked_at` is injected in deployment
  code.
- **`CP08-F-02` — CLOSED AS A SCOPE DECISION.** Covenant supersession is absent
  from the estate: 0 of 180 covenants carry `supersededBy`, thresholds are
  unchanged from `t:1500` to head, and no interval is ever closed. The product
  **withdraws the claim** rather than serving an empty superseded set;
  `include_superseded` stays declared-and-inert. The ledger's 1,107 supersession
  markers belong to other classes and do not count.
- **`CP08-F-03` — OPEN, and it is the debt signal's subject.** 112 of 137
  amendments carry no `assertedAt` and cannot be placed on the assertion axis.
  Not a defect to repair: the product serves those facilities and says, in
  `D_c`, that it cannot tell you what the bank knew.
- **`CP08-F-04` — OPEN, and it is not this product's to fix.** Covenants carry no
  assertion time at all, so the *covenant terms* a facility bore on a past date
  cannot be reconstructed. The product serves the current terms and labels them
  unversioned. A future estate wave that versions covenant terms would restore
  the vault's original scope.

---

## G · Operate and govern

### G.1 Product gates

The acceptance authority for every gate is **this clause** (`D-IMPL-326`).

| Gate | Asserts |
|---|---|
| `CIF-G01` | a later `as_of` admits no fewer **amendments** than an earlier one, `known_as_of` held |
| `CIF-G02` | a later `known_as_of` admits no fewer amendments than an earlier one, `as_of` held |
| `CIF-G03` | **across a booking gap, `as_of` held and `known_as_of` varied admits DIFFERENT amendment sets** — the two-clock claim |
| `CIF-G04` | every admitted amendment satisfies **both** filters — the temporal-coherence gate |
| `CIF-G05` | a set whose coherence is violated is refused, observed red under a one-line filter removal |
| `CIF-G06` | the exclusion record names **which axis** excluded each omitted amendment |
| `CIF-G07` | an amendment with no `assertedAt` is recorded unplaceable, never assumed booked |
| `CIF-G08` | re-serving at a recorded ledger `t` reproduces the content address |
| `CIF-G09` | the ledger `t` is in lineage as execution provenance and **not** in product identity |
| `CIF-G10` | `include_superseded` and `evaluate_headroom` are refused by name with their declared reasons |
| `CIF-G11` | an unresolvable `facility_id` refuses; it does not return an empty set |
| `CIF-G12` | the served covenants are **labelled unversioned**, so no consumer reads them as reconstructed for `as_of` |
| `CIF-G13` | replay dimension 2 is a superset of product policy lineage |
| `CIF-G14` | `D_c` moves with the placeable-amendment ratio, not with the estate |
| `CIF-G15` | a closed as-of answer carries the long TTL and a live one the short TTL |

**Two gates were REMOVED at Gate 1 rather than weakened**, and this is recorded
so a reader comparing drafts sees a withdrawal rather than a gap: a superseded-set
return gate, and a gate asserting that covenant *terms* differ across a booking
gap. The estate supports neither (§0.5), and a gate that cannot fail is worse
than no gate.

**`CIF-G12` is the gate this narrowing earns.** Serving current covenant terms
beside a historical amendment answer is the one place a consumer could mistake
this product for the one the vault described. The label is not prose in a README
— it is a payload field, held by a gate.

**All directional or structural. No estate population is pinned** — `CIF-G03`
names the booking-gap *relationship*, not the three amendment ids, so a fourth
engineered lag does not break it.

### G.2 Acceptance criteria

1. The two axes are separately parameterised and separately filterable, and
   varying either alone changes the admitted amendment set.
2. The booking-gap divergence is demonstrated on real estate data, with a
   drawdown inside the gap.
3. Every omitted amendment is accounted for **by axis**.
4. The served covenants are labelled unversioned and no claim is made that their
   terms were reconstructed for `as_of`.
5. The product writes to neither source store.
6. A recorded ledger `t` reproduces its answer after later ledger activity.
7. `D_c` reports the assertion-axis placeability of the served amendment set.

### G.3 What Gate 2 inherits

`CP08-F-01` is resolved and the request contract can now be authored.
`CP08-F-02` is closed as a scope decision. What Gate 2 carries forward:

- **`CP08-F-03`** — most amendments are unplaceable on the assertion axis. It is
  the debt signal's subject, and Gate 2 must show `D_c` distinguishing the
  facilities the dispute question can be answered for from those it cannot.
- **`CP08-F-04`** — covenants carry no assertion time, so their terms are served
  unversioned and labelled. A later estate wave that versions covenant terms
  would restore the vault's original scope, and **this specification is the
  record of why it was not available in 2026-09**.
