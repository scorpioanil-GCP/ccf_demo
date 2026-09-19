---
product: credit-risk.covenant-in-force.v1
standard: v0-3
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

**`CP-SPEC-008` · Tier 3 · `credit-risk.covenant-in-force.v1`**
**Fluree for covenants, amendments and both time axes · PostgreSQL for facilities, drawdowns and the breach-threshold register**

> **Which amendments bound this facility on the drawdown date, and which of them
> had the institution actually booked by then?**
>
> One question, on two clocks.

## 0 · What this document is

A build specification for the engineer who will assemble this Context Product
from the credit data estate. It states the decision the product serves, the
contract it publishes, which store each element comes from, the assembly
recipe, and the gates the finished product is held to.

Every figure below was measured against the estate before this document was
written, and the query that produced it is reproducible.

### 0.1 Placeholder discipline

No `[TBC]`. Where a value is a demonstration choice rather than a production
recommendation, §0.3 names it and says why.

### 0.2 Reads only — no write path anywhere in this product

Both source stores are read with `SELECT`. The ledger is append-only, so a
write is permanent; nothing in this product's assembly, its examples or its
tests writes to either store. The fabric's own graph is per-run scratch and is
discarded when the run exits.

This matters to the recipe and not only to operations: §D.6's replay
demonstration is designed to need no write, because a product that had to
mutate its sources to demonstrate itself would be demonstrating the mutation.

### 0.3 What is real in this estate, and what was engineered

The estate is built to resemble a financial-services credit data estate. Some
of it is public filing data; some is synthetic, because the real equivalent is
internal to a bank and is not published anywhere. An engineer reading this
specification should know which is which, and where a parameter was chosen to
make a control observable rather than to recommend a production value.

| Element | Provenance |
|---|---|
| Covenant terms — type, threshold, test frequency | **public** — EDGAR EX-10 credit agreements, parsed |
| Amendment events and effective dates | **public** — 8-K Item 1.01, amended-and-restated EX-10 exhibits |
| Facility reference data, drawdowns | **synthetic** — internal loan-system records have no public equivalent |
| **Amendment booking dates (assertion time)** | **synthetic, deliberately engineered** — see below |
| Breach-threshold register and its versions | **synthetic** — internal credit policy |

**The booking lag is the one engineered element this product depends on, and it
is engineered because it cannot be sourced.** When a bank *booked* an amendment
is internal to that bank; no filing discloses it. Without a deliberate gap
between an amendment's effective date and its booking date — with a drawdown
falling inside that gap — `as_of` and `known_as_of` return identical answers
for every query and the bitemporal model looks like redundant machinery. Three
such gaps exist in the estate, each with a drawdown inside it, and §A.2 works
one of them through.

**Two further disclosures, both about the demonstration data rather than about
the design.**

- **Covenant terms are not versioned in this estate.** The amendment history is
  complete and dated on both axes; the covenant *terms* those amendments
  produced are carried at their current values, with no per-version history.
  The product therefore serves current terms and **labels them unversioned**
  (§D.4, `CIF-G12`) rather than implying they were reconstructed for `as_of`.
  A production estate that versions covenant terms would extend this product's
  answer without changing its shape: the same two-axis cut would then apply to
  the terms as well as to the amendments.
- **Half-lives are illustrative.** The estate is a point-in-time snapshot
  rather than a continuously refreshed feed, so freshness parameters are chosen
  to make the governed behavior observable in that snapshot. §E.1 carries the
  standing wording.

### 0.4 The four-question test

- **Is the answer assembled rather than stored?** Yes. No store holds *"the
  amendments in force on 2025-09-09 as known on 2025-09-09"*; it is a two-axis
  cut over assertions in one store, anchored on a facility in another.
- **Does more than one consumer need it?** Yes — credit, workout, audit and
  counsel, and the four want different instants on different axes.
- **Does it carry a governed freshness claim?** Yes, and an unusual one: an
  answer about a settled past date does not decay (§E.3).
- **Would a `SELECT` do?** No, and this is the tier where that stops being a
  matter of convenience. A `SELECT` against current state returns today's
  amendments with full confidence and no signal that it answered a different
  question than the one asked.

---

## A · Decision frame

**The decision.** *Which amendments bound this facility on this date, and which
of them had the institution actually booked by then?*

**The trigger, in three forms that are not the same question.**

1. **Live** — a credit officer testing a drawdown request against current terms.
   `as_of` = today, `known_as_of` = today.
2. **Forensic** — a workout team or supervisor asking what bound a drawdown
   that happened months ago. `as_of` = the drawdown date, `known_as_of` = today.
   *What was true?*
3. **Dispute** — counsel asking what the institution **knew** was true on that
   date. `as_of` = `known_as_of` = the drawdown date. *What did you know, and
   when?*

Forms 2 and 3 differ in one parameter and **return different answers**. That
difference is this product's subject.

### A.1 Counterfactual — `temporally-incoherent`

A loan system that stores amendments as current state answers forms 2 and 3
identically, and answers both with today's position. The answer is not
approximate; it is an answer to a question nobody asked, returned with the same
confidence as a correct one. The failure surfaces under supervisory examination
— after the institution has already relied on it.

### A.2 The worked case — `FAC-01BB3F`

| fact | value |
|---|---|
| Amendment | `AMD-01BB3F-2`, amendment 2 to the facility |
| Effective (`validFrom`) — **valid time** | **2025-08-14** |
| Booked (`assertedAt`) — **assertion time** | **2025-10-05** |
| Gap | **52 days** |
| Drawdown inside the gap | `DRW-01BB3F-0000`, **2025-09-09**, USD 4,500,000 |

On **2025-09-09** the amendment was legally in force and had not yet been
booked. A drawdown was taken that day. Asked about that date:

- **form 2** (`as_of=2025-09-09`, `known_as_of=today`) **admits** the amendment
  — it was in force, and we know that now;
- **form 3** (`as_of=known_as_of=2025-09-09`) **excludes** it — the institution
  had not booked it, and acted in good faith on the facility as it then stood.

**Two answers, one facility, one `as_of`, differing only in what was known.**

Two further engineered gaps — 44 and 45 days, each with a drawdown inside —
serve as controls, so the behavior is not demonstrated on a single row.

### A.3 Scope boundary

Out of scope, and stated before the contract so the boundary is visible:

- **Breach and headroom evaluation.** Whether a covenant was breached needs
  period-appropriate financials against period-appropriate thresholds. That is
  a distinct product; `evaluate_headroom` is declared and always refused (§B.2).
- **Policy analysis.** The breach-threshold register is read to pin which
  version was in force at `as_of`. It is not a second product here.
- **Historical covenant terms.** §0.3 — the estate carries no per-version
  covenant history, so terms are served at current values and labelled.

---

## B · Contract

### B.1 The nine elements

| # | Element | Value |
|---|---|---|
| 1 | **Name** | `credit-risk.covenant-in-force` |
| 2 | **Version** | `1.0.0` |
| 3 | **Subject** | one `facility_id` |
| 4 | **Payload** | the amendment set admitted at the two declared instants; every amendment excluded, with **which axis excluded it**; the covenants the facility carries, labelled unversioned; the drawdowns in the window |
| 5 | **Lineage** | both legs, plus `as_of`, `known_as_of`, and the ledger transaction point the read was bounded at |
| 6 | **Policy** | the breach-threshold register version effective at `as_of` |
| 7 | **Debt** | the platform's reference assessment — this product declares no metric of its own (§E.2) |
| 8 | **TTL** | anchored on the latest assertion in the SCORED observation set (§E.3, corrected 2026-09-18) |
| 9 | **Determinism** | class 1, pure algorithmic — no model call anywhere in §D |

### B.2 Request parameter surface — bitemporal

| Parameter | Type | Moves | Default | Expected effect |
|---|---|---|---|---|
| `facility_id` | string, **required** | anchor | — | unresolvable ⇒ refusal, never an empty answer |
| `principal_scope` | array, **required** | `P` envelope | — | the admitted set the policy step reads |
| `as_of` | string (ISO date) | **`T` — valid time** | the request's own instant | which amendments were in force |
| `known_as_of` | string (ISO date) | **`T` — assertion time** | the request's own instant | which of them had been booked |
| `include_superseded` | bool | payload shape | — | **declared and always refused** |
| `evaluate_headroom` | bool | payload shape | — | **declared and always refused** |

**The two time parameters are the heart of this product, and conflating them is
the most common modelling error in this domain.**

- **`as_of` is valid time** — when was this amendment in force? An amendment
  effective 2025-08-14 bound the facility on 2025-09-09 regardless of when it
  was recorded.
- **`known_as_of` is assertion time** — when did the institution know? If an
  amendment effective 2025-08-14 was not booked until 2025-10-05, then on
  2025-09-09 the institution was operating against the prior terms, in good
  faith, having not yet learned of the new ones.

Litigation and supervision ask different questions of these two axes. *"What was
true?"* is `as_of`. *"What did you know, and when?"* is `known_as_of`.
**Dropping either filter answers a different question**, and §D.7's coherence
gate refuses a set where one was dropped.

**Both defaults are declared RELATIVE to the request's own instant, not as
dates.** A literal date written into the contract means one window on the day it
is written and a different one a year later, with nothing saying it drifted. The
class declares an offset of zero against the request instant, so *today* and
*now* stay *today* and *now* on every day the product is asked:

```yaml
relative_defaults:
  as_of:        {offset_seconds: 0, render: date}
  known_as_of:  {offset_seconds: 0, render: date}
```

Computing the date in deployment code would be the equivalent mistake one layer
over: the parameter whose entire subject is *which instant governed this
decision* would take its value from somewhere nothing records.

**Why two parameters are declared and always refused.** Both are part of the
uniform request surface, and a parameter that is silently absent reads as
*unsupported by oversight* rather than *unsupported by decision*. Declaring and
refusing them by name, with the reason, makes the boundary explicit:
`include_superseded` because this estate carries no per-version covenant history
(§0.3), and `evaluate_headroom` because breach evaluation is a different product
(§A.3).

---

## C · Data catalog

### C.1 Element table

| Element | Store | `G` |
|---|---|---|
| Facility, borrower, facility terms | PostgreSQL | `E` |
| Covenant — type, threshold, unit | Fluree | `R` |
| Amendment, effective date, sequence | Fluree | **`T` — valid time** |
| Amendment booking date | Fluree | **`T` — assertion time** |
| Drawdown events | PostgreSQL | `T` |
| Breach-threshold register and its versions | PostgreSQL | `P`, `T` |

Every predicate IRI, table and column this product reads is declared in
`artifacts/source-vocabulary.yaml` — one document an engineer edits to point the
product at a different estate, without touching any code.

### C.2 The population, measured

| population | measured |
|---|---|
| Covenant nodes | 180, across 45 facilities |
| Covenant types | `leverage` 85 · `interest_coverage` 63 · `fixed_charge_coverage` 58 · `minimum_liquidity` 42 · `secured_leverage` 20 · `net_capital` 2 |
| **Amendments to credit facilities — this product's slice** | **25, across 18 facilities** |
| **Of those, carrying both an effective date and a booking date** | **25 — every one** |
| Engineered booking lags, each with a drawdown inside | 3 |
| Drawdowns | 151 |
| Breach-threshold register versions | 2, with distinct effective dates |

**Scope the amendment count to the facilities.** The estate also carries
amendment events against trades, trade lifecycle events and syndicated loans —
112 further `amends` edges that this product does not read. A count taken across
all of them describes the ledger, not this product; the 25 above is the figure a
build plans against.

### C.3 Correlation key and single-writer discipline

`facility_id` correlates the two legs. Fluree is authoritative for covenants,
amendments and both temporal axes; PostgreSQL for facilities, drawdowns and the
register. Within the fabric, one component holds the write handle to graph
state, and this product writes to neither source.

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
`AMD-01BB3F-2` appears. That pair is the product's proof.

### D.2 Step table

| # | Layer | Step | Store | Emits |
|---|---|---|---|---|
| 1 | L1/L2 | acquisition | PostgreSQL + Fluree | facility, amendments, covenants, drawdowns in window |
| 2 | L4 | policy — principal subgraph | over graph state | the admitted facility subgraph |
| 3 | L4 | traversal — typed neighborhood | over graph state | amendments and covenants reachable from the facility |
| 4 | L5 | projection — the two-axis cut | in memory | the answer, and the exclusion record |

The temporal cut is a **projection**, not a traversal: it selects and shapes
truth that has already been admitted, rather than reaching for more of it.

### D.3 Acquisition (step 1)

The facility, its drawdowns and the register version are read from PostgreSQL.
The amendments and covenants are read from Fluree, bounded at the transaction
point the run records, so the answer is reproducible.

**`as_of` is applied in the read.** The amendment query filters on the effective
date at the source rather than reading every amendment and discarding later.

**`known_as_of` is deliberately NOT applied in the read**, and this is the one
place the recipe will look wrong to a reader optimising it. The projection has
to report *which axis* excluded each omitted amendment (§D.4). A read that had
already dropped the un-booked amendments would leave only survivors, and the
exclusion record would be unfillable — or would have to be rebuilt from a second
query, which is two sources of truth for one answer. **One cut, in the
projection, over a view that still contains the candidate.**

An unresolvable `facility_id` **raises rather than returning an empty set**: an
unknown facility is a claim about the request, an empty answer a claim about the
world, and they mean opposite things.

### D.4 The two-axis cut (step 4)

For each amendment reachable from the facility:

```
admitted  ⟺  validFrom ≤ as_of
             AND (validTo is open OR as_of < validTo)     ← valid time
             AND assertedAt is present
             AND assertedAt ≤ known_as_of                 ← assertion time
```

**An amendment with no booking date is not assumed booked.** Every amendment in
this product's slice carries one, so the branch is not exercised here — but
defaulting a missing booking date to the effective date would make every booking
lag vanish, which is the one thing this product exists to make visible.

**The exclusion record is part of the payload, not a log line.** For every
amendment excluded, the payload names **which axis excluded it**. An amendment
absent because it was not yet in force and an amendment absent because the
institution had not yet learned of it are different facts, and a consumer that
cannot tell them apart has the single-timeline problem back in a new place.

**The covenants the facility carries are served alongside, labelled
unversioned** (§0.3). The payload states this as a field rather than in prose:
serving current terms beside a historical amendment answer is the one place a
consumer could read more history into the answer than it contains.

### D.5 Determinism and the emitted contract

Class 1. Two serves of one question at one instant reach one content address.
The ledger transaction point is recorded as **execution provenance** — where the
evidence lived, not what the answer says — and is not part of product identity.

### D.6 Replay

1. Serve, and record the transaction point from lineage.
2. **Re-serve at that recorded point after the ledger has advanced** and the
   identical content address returns.
3. **Vary `known_as_of` alone across a booking gap**, `as_of` held, and the
   admitted amendment set changes.

Neither demonstration writes to any store (§0.2).

### D.7 Validation gates

The platform's three universal delivery gates apply unchanged. This product
declares a **fourth**, and it is the reason the tier exists:

> **Temporal coherence.** Every admitted amendment satisfies
> `validFrom ≤ as_of` **and** `assertedAt ≤ known_as_of`. An admitted amendment
> violating either means one of the two filters was dropped, and the product
> refuses rather than serving an answer to a question nobody asked.

---

## E · Volatility and materialization

### E.1 Half-life table

| Signal class | `λ_c` | Note |
|---|---|---|
| Amendment structure | ~180 days | amendment-driven |
| Covenant terms | ~365 days | rarely amended independently |
| Facility reference data | ~90 days | loan-system refresh cadence |
| **An answer about a closed past date** | **∞** | the past does not change |

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the
> platform applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

### E.2 Debt

This product declares **no Context Debt metric of its own**. The platform's
reference assessment applies.

A debt figure exists to report a shortfall in the answer — evidence the product
served without being able to vouch for. Every amendment in this product's slice
carries both an effective date and a booking date (§C.2), so there is no
shortfall of that kind to report, and a figure that read the same on every
answer would be decorative rather than informative.

An estate whose facility amendments lack a booking date — the shape the trade
amendments already have — would give this product a real shortfall to measure,
and a product-specific metric would then be specified against that measured
population.

### E.3 Materialization and TTL

Derived per request; never materialized. **TTL is anchored on the latest
assertion in the SCORED OBSERVATION SET — the same selected set the freshness
factor is scored over — never on request time.**

**Corrected 2026-09-18 (Dave's ruling under `D-IMPL-341`).** This clause read
"among the SERVED set", and the mechanism does not read the served set: the
anchor comes from the same selected observations the freshness factor scores,
before the projection decides what to display. Deriving an expiry from the
finished payload would be a second selection algorithm reading a rendered
answer, which is exactly what the ruling forbids; the correction is to this
sentence, not to the code.

The difference is visible on a closed question and is a real consequence rather
than a rounding of words. Asked with `as_of` and `known_as_of` at the drawdown,
this product serves `AMD-01BB3F-1` alone and excludes `AMD-01BB3F-2` on the
assertion-time axis — yet `-2` is in the scored set, so the anchor is `-2`'s
booking date. **What the anchor identifies is the freshness of the evidence
this answer was selected from; it does not claim that every amendment shown was
refreshed at that instant, and it does not claim the excluded one was served.**

Two regimes follow from the two clocks, and they are a genuine consequence of
ledger-backed temporality rather than a convenience:

- **live** (`as_of` at the request's own instant) — short, because the answer
  moves when the next amendment is booked;
- **closed** (`as_of` naming a settled past date, with `known_as_of` also
  closed) — long, because neither what was true nor what was known can change.

**The dual regime is specified and not yet implemented.** Where *closed* ends
and *live* begins is a policy decision an operator makes; see §G.3.

### E.4 What invalidates a served answer

A new amendment being **booked** — an `assertedAt` later than a served
`known_as_of` appearing — changes the answer to a live query and leaves a closed
one untouched. That asymmetry is the dual regime's whole justification.

---

## F · Source binding and readiness

### F.1 Readiness

| requirement | measured | verdict |
|---|---|---|
| Facilities carrying covenants | 45 | **met** |
| Facilities with at least one amendment | 18 | **met** |
| Facilities with two or more sequential amendments | present; the engineered cases are amendments 2, 3 and 3 | **met** |
| **At least one engineered booking lag with a drawdown inside** | **3** | **met** |
| Four or more covenant types per facility | 6 types estate-wide; the worked case carries 4 | **met** |
| Two or more register versions with distinct effective dates | 2 | **met** |

### F.2 Access path

Connection material — host, port, credentials — comes from the environment, and
`backends.yaml` names the variables rather than the values. **The namespaces are
declared separately from the connection settings**; deriving them from
connection material alone points the run at the wrong generation of the estate.

---

## G · Operate and govern

### G.1 Product gates

| Gate | Asserts |
|---|---|
| `CIF-G01` | a later `as_of` admits no fewer amendments than an earlier one, `known_as_of` held |
| `CIF-G02` | a later `known_as_of` admits no fewer amendments than an earlier one, `as_of` held |
| `CIF-G03` | **across a booking gap, `as_of` held and `known_as_of` varied admits DIFFERENT amendment sets** — the two-clock claim |
| `CIF-G04` | every admitted amendment satisfies **both** filters — the temporal-coherence gate |
| `CIF-G05` | a set whose coherence is violated is refused, observed failing under a one-line filter removal |
| `CIF-G06` | the exclusion record names **which axis** excluded each omitted amendment |
| `CIF-G08` | re-serving at a recorded transaction point reproduces the content address |
| `CIF-G09` | the transaction point is lineage, **not** product identity |
| `CIF-G10` | `include_superseded` and `evaluate_headroom` are refused by name with their declared reasons |
| `CIF-G11` | an unresolvable `facility_id` refuses; it does not return an empty set |
| `CIF-G12` | the served covenants are **labelled unversioned**, so no consumer reads them as reconstructed for `as_of` |
| `CIF-G16` | every policy bundle the product cites is carried by the decision record, and it cites at least one |
| `CIF-G15` | a closed as-of answer carries the long TTL and a live one the short TTL — **specified, not yet implemented** (§G.3) |

**All directional or structural. No population figure is pinned in a gate** —
`CIF-G03` names the booking-gap *relationship*, not the three amendment ids, so
a fourth engineered lag does not break it, and the counts in §C.2 are
measurements a reader reproduces rather than assertions a test holds.

**`CIF-G07`, `CIF-G13` and `CIF-G14` are gaps in this numbering and are not
reused.** `CIF-G07` and `CIF-G14` were specified against a population this
estate does not contain — an amendment missing a booking date, and a debt ratio
derived from it. `CIF-G13` asserted the same replay property `CIF-G16` now
carries, but read the citation from an attribute the lineage contract does not
have, so its left-hand set was always empty and its subset test could not fail;
the obligation is restated under a new id rather than repaired in place, because
a gate that once reported coverage it did not provide should not keep its name.
In all three cases the id is left empty so a later obligation does not inherit a
name that meant something else.

### G.2 Acceptance criteria

1. The two axes are separately parameterised and separately filterable, and
   varying either alone changes the admitted amendment set.
2. The booking-gap divergence is demonstrated on estate data, with a drawdown
   inside the gap.
3. Every omitted amendment is accounted for **by axis**.
4. The served covenants are labelled unversioned, and no claim is made that
   their terms were reconstructed for `as_of`.
5. The product writes to neither source store.
6. A recorded transaction point reproduces its answer after the ledger advances.

### G.3 Not yet built

**`CIF-G15` — the dual TTL.** §E.3 specifies a long TTL for an answer about a
closed past date and a short one for a live query. Where *closed* ends and
*live* begins is an operator's policy decision rather than one this
specification settles, so the gate is declared and visibly unimplemented rather
than dropped or counted as running.
