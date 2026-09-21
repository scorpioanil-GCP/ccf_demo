<!--
  CP-SPEC-021 — Large Exposure / RWA Concentration.
  Gate 1 ONLY. Authored to Context Product Specification Standard v0.3 before
  any code exists, per `D-IMPL-319` and the rule *specs come before code*.

  Source: vault `context-products/large-exposure-rwa-concentration`
  (`risk.large-exposure.v1`, standard q019, generated 2026-08-15) and
  `docs/GATE-0-COVERAGE-CP15-24.md` §4.1/§4.2 row CP-21.

  NOTHING HERE IS AUTHORIZED TO BE BUILT. Gate 2 is Dave's.
-->

# Large Exposure / Concentration — Context Product Specification

**Rung 21 · Postgres + Fluree + MongoDB + departmental SQLite · `risk.large-exposure`**

**Status: GATE 1 — awaiting Dave's ruling. No implementation, no SDK work, no
`D-IMPL` id spent.**

---

## 0 · What this document is

> **CP-21 owns the regulatory arithmetic CP-23 deliberately excluded.** Rung 23
> fenced it off with `PEW-G18`, which fails if `limit_definition`,
> `bank_capital` or `connection_basis` is touched. This rung is where that
> capability is tested **independently**, so the portfolio early-warning product
> is not contaminated by it and the two can be judged separately.

The question this document exists to answer:

> **What does regulatory large-exposure calculation require that CP-01 through
> CP-24 have not already proven?**

### 0.1 Already proven — reused unchanged, and NOT reopened

| # | Mechanism | Proven at | Reused here as |
|---|---|---|---|
| 1 | The paved producer road, `open_product(...)` with a named `plan_factory` | `D-IMPL-343`; rungs 13–19, 23, 24 | the producer spine. **Tenth tree on the road.** |
| 2 | A **population** as the assembly unit, with debt by the SDK's `compose_debt_factors` | `D-GATE-cp-23` | the connected group is a population — but a **derived** one (§0.2a) |
| 3 | Deterministic Π arithmetic over a Control Plane artifact (values, never code) | rungs 18, 23, 24 | the limit set and the counting rules |
| 4 | An **object-valued** request parameter, closed, in integer canonical units | **`D-GATE-cp-24`** (`Q1`) | the `proposal`, tested with and without |
| 5 | Observed evidence versus explicit hypothetical, kept apart | **`D-GATE-cp-24`** | the `proposal` is an assumption and never evidence |
| 6 | As-of evaluation over a bitemporal ledger, two clocks kept distinct | cp-08, cp-13-canonical, cp-16 | the regime in force at `as_of` (§0.2b) |
| 7 | Passage-level lineage to filed text | cp-13-canonical, cp-16, cp-19 | every limit anchored to a published provision |
| 8 | The departmental SQLite source, read first | cp-17, cp-19 | the risk department's limit workbook |
| 9 | Three credentialed principals at one standard door, three role-conditioned views | `D-IMPL-324`; rungs 15–19, 23, 24 | credit officer / committee / examiner |
| 10 | A governed refusal by name, as data, with a replay reference | cp-05 onward | an unpriced intent, an unknown regime, a debt breach |

### 0.2 Genuinely new — three things, established from the spec and the estate

**(a) A population whose MEMBERSHIP IS DERIVED, and whose derivation is a
request parameter.** Rung 23's book was a *roster* — 25 rows read from a table.
A connected group is **computed from edges**, and `connection_basis` selects
*which* edges: `control` alone, `economic-dependency` alone, or `both`. **The
same anchor yields different groups, therefore different exposure, therefore a
different compliance answer.** Nothing on the ladder has had a population the
caller can redefine. The estate supports it: **184 `connectedTo` edges** and
**4 `economicallyDependentOn` edges**, each carrying a stated `dependencyBasis`
(three supplier concentrations and one shared-funding case).

**(b) THE RULE ITSELF IS VERSIONED, SELECTED AND ANCHORED.** Every earlier rung
as-of'd *data*. Here the **regime** — the rule that decides the limit — is a
first-class artifact with effective dates, and which one applies is a request
parameter. Measured: **3 `RegimeVersion` nodes** — `crr-2014-2021`,
`pra-2022` (effective 2022-01-01, 25 % of capital) and `reg-o` (effective
2026-01-01). Two consequences neither the ladder nor this estate has met
before:

- **a limit need not be a percentage.** Regulation O is an **absolute**
  `limitAbsoluteUsd` of **$500,000**, beside PRA's `limitPctOfCapital` of
  **25.0**. A product that assumes "limit = pct × capital" cannot express it.
- **the rule cites published text.** `citesProvision` resolves into **464
  regime passages across 31 documents**, and all three cited provisions
  resolve to real rulebook language — CRR Article 395(1), the PRA exclusions,
  and 12 CFR 215.4(b).

**(c) A FRESHNESS ASYMMETRY THE PRODUCT MUST DISCLOSE RATHER THAN RESOLVE.**
Exposure moves intraday; the capital base is **quarterly** (`bank_capital`, 12
rows, latest 2026-03-31). The source specification is explicit that this is
*unavoidable rather than a modelling flaw* and that the obligation is to
**disclose the asymmetry** — which is why capital-base date coherence is a
validation gate and not a computation. Rung 24 proved a scenario cannot refresh
evidence; this rung proves a *denominator* cannot be silently aged into a
numerator's clock.

**What is NOT new, though it was expected to be.** Group-grain aggregation
(cp-05 rolled up a corporate family), limits and headroom (cp-05, rung 23),
three role-conditioned views (rungs 18, 23, 24), an object-valued hypothetical
(rung 24) and departmental-SQLite-first (cp-17, cp-19) are all proven. **The
capstone's value is that the ladder holds together, not that it adds
mechanism** — the source specification says so itself: *"less a new capability
than a demonstration that the ladder holds together."*

### 0.3 Deliberately OUT of scope

| Left out | Why |
|---|---|
| **RWA modelling / advanced approaches** | FFIEC 101 was never fetched and there is no FR Y-9C base (Gate 0). A capital model is not a context product. |
| A jurisdiction engine | `regime` is selected by parameter and entitlement, not inferred from a domicile graph |
| The supervisory workflow | an examiner *rendering* is in scope; a supervisory case management system is not |
| Re-deriving CP-23's early-warning signals | that product exists; this one answers *are we within limits* |

### 0.4 The four-question build test (Standard v0.3)

| Question | Answer |
|---|---|
| Buildable without a further design conversation? | **No — two questions are owed** (§F.4). |
| Every source named, with store, provenance and scale? | **Yes** — §C, measured 2026-09-21. |
| Every parameter's domain, default and effect stated? | **Yes** — §B.3. |
| Every gate expressible as a test that can go red? | **Yes, with one named risk** — §G.1. |

---

## A · Decision frame

**Decision and trigger.** A facility approaching approval, a periodic limit
review, or a supervisory request to demonstrate compliance.

**Three renderings of ONE calculation**, from the source specification:

| Principal | Needs |
|---|---|
| **credit officer** | headroom for a specific proposal; what would breach |
| **committee** | concentration and limit utilisation across the book |
| **examiner** | methodology attribution, policy-version binding, evidence chain, replay anchor |

**The counterfactual is four failures composing** — *Context Starved* (group
computed from legal entity rather than control and economic dependency),
*Latency Poisoned* (exposure measured against a quarter-end capital base),
*Policy Blind* (one jurisdiction's regime applied to another's group),
*Perspective Flat* (the examiner gets the committee's dashboard). Each is
survivable alone; together they are a regulatory finding.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Class** | `risk.large-exposure` |
| **Lane** | `v1.0.0` |
| **Schema** | `large_exposure_concentration` |
| **Request surface** | §B.3 |
| **TTL** | 4 h · `ttl_anchor: from_decision` (the source specification's, and rung 23's reasoning: a group's evidence has many ages) |
| **Obligations** | regime and limit set bound to `intent` and `regime`; the rendering bound to the role |
| **Assembly mode** | derive the group, then governed assembly over its members, then deterministic evaluation |
| **Lineage** | `graph_snapshot_at` as ledger `t`; `policy_version`; passage-level `L` on every regime claim |
| **Declared gates** | §G.1 — 20 gates, `LEX-G01`..`LEX-G20` |

### B.2 The measures

Exposure by group as a percentage of eligible capital **and** against any
absolute limit; limit utilisation; headroom; which limit **binds first**;
mitigation effect; the position **with and without** a proposal.

### B.3 Request parameter surface

| Parameter | Type | Domain | Default | Moves |
|---|---|---|---|---|
| `lei` | — | — | — | the **subject**; resolves to its connected group |
| `intent` | enum, required | `limit-test` \| `committee-review` \| `supervisory-request` | — | policy envelope; **priced, never defaulted** |
| `regime` | enum | `pra-2022` \| `crr-2014-2021` \| `reg-o` \| `internal` | per entitlement | **which rules apply** |
| `connection_basis` | enum | `control` \| `economic-dependency` \| `both` | **`both`** | **the group definition — and therefore the answer** |
| `as_of` | date-time | — | `asked_at` | the decision instant; selects the regime **in force** |
| `proposal` | object, closed | `{facility_type, commitment_usd, obligor_lei}` | none | the hypothetical, in integer canonical units (rung 24's `Q1`) |
| `apply_mitigation` | boolean | — | `true` | whether eligible mitigation is counted |
| `debt_tolerance` | number | 0..1 | class default | fail-closed bound |

**`connection_basis` defaults to `both`, and that is the conservative
posture.** A product exposing only control-based grouping computes a
compliant-looking number against an incomplete group. `LEX-G04` proves the
basis actually moves the membership on this estate.

### B.4 Prerequisites

The source specification names six. **Whether they are composed as CHILDREN or
re-assembled as a sibling is `Q1` (§F.4)** — the one genuinely structural
question this rung asks.

---

## C · Data catalog — every figure measured against `.76` on 2026-09-21

### C.1 Element table

| Element | Store | Object | Scale | Provenance |
|---|---|---|---|---|
| Bank capital base | Postgres `ccf_v2` | `bank_capital` | **12** quarters, RSSD 852218, latest 2026-03-31 | public — FFIEC Call Report |
| The reporting bank | Postgres | `reporting_bank` | **2** — JPMorgan Chase Bank NA under its holding company | public — FDIC |
| Limit definitions | Postgres | `limit_definition` | **3** intents with `counts_guarantees`, `counts_undrawn`, `connection_basis` | synthetic — internal |
| Exposure by facility | Postgres | `facility`, `drawdown` | 60 over 22 borrowers; 151 | public |
| Guarantees | Postgres | `guarantee_terms` | **28** | synthetic |
| Hypothetical proposals | Postgres | `exposure_proposal` | **2** — one `breaches`, one `fits_after_mitigation` | synthetic |
| Control edges | Fluree `fibo-v2` | `ex:connectedTo` | **184** | public |
| **Economic-dependency edges** | Fluree | `ex:economicallyDependentOn` + `ex:dependencyBasis` | **4**, each with a stated basis | **synthetic — internal** |
| Ultimate parents | Fluree | `hasGlobalUltimateParent` 103, `hasDomesticUltimateParent` 36, `controls` 3 | — | public |
| **Regime versions** | Fluree | `ex:RegimeVersion` | **3** — CRR 2014-2021, PRA 2022, Reg O | public |
| Internal limit envelope | Fluree | `ex:LimitEnvelope` | **1** — 5.0 % of capital, effective 2026-01-01 | synthetic — internal |
| Reg O insider designation | Fluree | `ex:InsiderDesignation` | **1** | public-derived |
| **Regime rule text** | MongoDB `fibo_v2` | `document` / `passage` where id ~ `crr|pra|reg-o` | **31 documents, 464 passages** | public — CRR, PRA Rulebook, 12 CFR 215 |
| Risk-department limit workbook | departmental SQLite | `risk_limit_workbook` | **16** obligor-scoped single-name limits with utilisation | synthetic — internal |

**Four stores, as the source specification requires** — and the fourth is the
departmental SQLite, read first, on the cp-17 pattern.

### C.2 The regime versions, measured

| node | label | effective from | limit |
|---|---|---|---|
| `regime-version-crr-2014-2021` | (CRR, superseded) | — | — |
| `regime-version-pra-2022` | PRA Large Exposures Part | **2022-01-01** | `limitPctOfCapital` **25.0** |
| `regime-version-reg-o` | Regulation O (12 CFR 215.4(b)) | **2026-01-01** | `limitAbsoluteUsd` **500,000** |

`pra-2022` cites **two** provisions — `crr-art-395-2021-12-31` and
`pra-large-exposures-01-01-2022` — and all three cited provisions resolve to
real rulebook text.

### C.3 The data traps, each with the binding chosen

**Trap 1 — THE UNITS TRAP, and it is the sharpest on the ladder.**
`bank_capital` is denominated in **thousands of dollars** (the FFIEC Call
Report convention); `facility.commitment_amount` is in **dollars**. Read as
dollars, JPMorgan Chase Bank NA would have **$0.30 bn** of Tier 1 capital and
**$4.02 bn** of total assets — absurd for a bank whose Call Report shows
**$4.0 trillion**. Read as thousands, Tier 1 is **$295.8 bn** and the figures
are correct.

**The consequence of getting it wrong is catastrophic and silent:** a 25 %
limit computed on the unscaled figure is **$73.9 million**, and **42 of the
estate's 60 facilities would breach it single-handedly**. The product would
report a bank in total breach of everything, confidently.

**The estate contains its own positive control.** The two engineered proposals
are calibrated against the *correct* limit: **$75.0 bn** is labelled
`breaches` and **$59.4 bn** `fits_after_mitigation`, against 25 % of $295.8 bn
= **$73.94 bn**. Both labels are only true under the thousands reading.
**Binding:** the capital base is normalised **at the acquisition seam**, the
scaling factor is a **declared** value in the source vocabulary rather than a
literal in code, the normalised and raw figures are **both served**, and
`LEX-G06` asserts the estate's own proposal outcomes come out as labelled —
which no unscaled implementation can satisfy.

**Trap 2 — two authorities disagree about the internal limit.**
`ccf_v2.limit_definition` prices `internal-appetite` at **0.15** (15 % of
capital); Fluree's `ex:LimitEnvelope` declares **5.0 %**. **Binding:** the
Control Plane artifact is the single authority the product enforces, both
values are served with their source named, and `LEX-G09` asserts the enforced
figure equals the declared one — rung 23's trap 5, a second time, and this time
the two genuinely differ.

**Trap 3 — regime passages carry no `sha256`.** All 464 resolve by
`passage_id` and carry text, but **none stores a hash** (for contrast, ABS's
1,882 passages all do). **Binding:** regime anchoring is proved by
**resolvability and quoted text**, not by re-hash, and the absence is stated
rather than worked around. `LEX-G07` asserts every limit cites a provision that
resolves; a re-hash limb is **not** claimed.

**Trap 4 — economic dependency is only four edges, and that is the point.**
The source specification says this relationship *"is not derivable from public
filings"* and is *"exactly the kind of edge that lives in an analyst's head."*
Four edges is thin, but it is enough to change a group. **Binding:** the
demonstration anchor is chosen so that `connection_basis` demonstrably moves
the membership (`LEX-G04`); each edge's `dependencyBasis` and its synthetic
provenance travel with it, so a reader can see that this part of the group is a
judgment rather than a filing.

**Trap 5 — no connected-group registry exists.** Groups are **derived
components**, not rows (Gate 0). **Binding:** the group is computed per request
from the edges at the ledger point, its composition is served, and the product
does not pretend to a stable group identifier the estate does not have.

**Trap 6 — the capital base is a quarter old.** Latest `bank_capital` is
**2026-03-31**; a decision instant later than that measures today's exposure
against last quarter's capital. **Binding:** §0.2c — the asymmetry is
**disclosed**, not resolved. The capital base's own `report_date` and its age
in days travel with every ratio, and `LEX-G12` refuses a payload that serves a
ratio without them.

---

## D · Assembly recipe

### D.1 Client call

```
GET /context-products/risk/large-exposure/B3BS7ACMDUWISF18KY76
      ?intent=limit-test&regime=pra-2022&connection_basis=both&apply_mitigation=true
      &proposal={"facility_type":"revolver","commitment_usd":75000000000,"obligor_lei":"B3BS..."}
```

### D.2 Operator step table

| # | Step | Store | Category |
|---|---|---|---|
| 1 | Resolve the anchor and the caller's rendering | Postgres | — |
| 2 | Bind entitlement; select the **regime in force at `as_of`**; read the departmental limit workbook; emit `policy_version` | Fluree + SQLite + Control Plane | Policy |
| 3 | **Derive the group** by walking `connectedTo` and, where the basis includes it, `economicallyDependentOn`, at the ledger point | Fluree | Traversal + Temporal |
| 4 | Retrieve the regime provisions supporting each limit | MongoDB | Similarity |
| 5 | Acquire exposure, guarantees and mitigation for every group member | Postgres | — |
| 6 | Resolve and **normalise** the capital base | Postgres | — |
| 7 | Aggregate under the regime's counting rules; apply the proposal with and without | in-process | Π |
| 8 | Evaluate against every applicable limit; identify which **binds first**; fail closed beyond tolerance | in-process | Π |

### D.3 Determinism class

Fully algorithmic. No LLM inference, no fitted model.

### D.4 Validation gates (contract level)

Empty-operator guard · lineage strict equality · TTL bounds · **regime
anchoring** (every limit cites a provision that resolves) · **capital-base date
coherence** (the base's date and age travel with every ratio) · **group-basis
disclosure** (the payload states which basis produced the group) · **debt
tolerance**.

---

## E · Volatility and debt

| Class | `λ_c` | Basis |
|---|---|---|
| exposure | ~4 hours | inherited from cp-05 |
| capital base | ~90 days | quarterly reporting |
| regime rules | ~730 days | slow, high-impact |
| internal limits | ~180 days | |
| group composition | ~180 days | |
| economic-dependency edges | ~365 days | judgment, reviewed periodically |

All **illustrative** under `D-IMPL-323`. Debt is the SDK's per-factor minimum
across group members, unchanged from rung 23 — and, as rung 24 established,
**the proposal is an assumption and cannot move it** (`LEX-G17`).

---

## F · Source binding and readiness

### F.1 Element readiness

Every element is present and measured. **Nothing required by §B is missing**,
and the two genuine absences — RWA/FFIEC 101 and a group registry — are out of
scope by §0.3 and trap 5 respectively.

### F.2 Symbols to be used, verified against `src/` on 2026-09-21

`open_product` · `ProductRequest` (opaque subject) · `SkillArgumentProperty`
with `properties` and `SkillArgumentMember` (the one-level ceiling, rung 24) ·
`compose_debt_factors` · `PolicyConstraint` + `ConstraintApplicability` ·
`resolve_ttl_anchor` · `run_gates`. Every one resolves; none is invented.

### F.3 Every `[TBC]`, with an owner

| # | Item | Owner |
|---|---|---|
| 1 | **`Q1` — composite over children, or a single-class producer?** | **Dave** |
| 2 | **`Q2` — the capital-units normalisation** | **Dave** (a binding is recommended) |
| 3 | The demonstration anchor, regime and instant | Dave — recommended as stated |
| 4 | The illustrative `λ_c` values | Dave — under `D-IMPL-323` |

### F.4 — THE QUESTIONS OWED

#### `Q1` — is CP-21 a COMPOSITE over group-scoped children, or a single-class producer? **(structural)**

Gate 0 calls group-scoped children *"the ruled path"* (`Q13`) and notes it
*"needs 1–2 **new** group-scoped producer trees"* — *"example work to authorize
at Gate 1"*. That is the single largest scope decision on this rung.

| | Route | Consequence |
|---|---|---|
| **A** | **Single-class producer over the derived group** *(recommended)* | one tree. The group is derived, its members' exposure is acquired directly, and the arithmetic is this rung's. **Precedent is strong and recent:** rung 24 was ruled a *sibling* of rung 23 for exactly this reason — the capability under test should dominate the rung. Here that capability is the **derived group, the versioned regime and the disclosed asymmetry**, none of which is composition. Cost: the capstone does not demonstrate composition, and `compose_expiry` / `CompositeAdmissionGate` stay unexercised at group grain. |
| **B** | **Composite over 1–2 new group-scoped child producers** | proves composition over a *derived* population, which nothing has — genuinely valuable, and the source specification's own step 6 describes it. Cost: **two or three new trees** rather than one, the cp-14 child chain throughout, and composition becomes the rung's dominant new thing. Gate 0 also records that *a composite behind a door is unproven*. |

**Recommendation: A**, with the composition gap recorded explicitly as the one
thing the capstone does **not** demonstrate — so the ladder's coverage claim
stays honest. **If Dave prefers B, that is a materially larger rung** and the
extra producer trees are the authorisation being requested.

#### `Q2` — how is the capital-units mismatch handled? **(binding, with a recommendation)**

Not a question about SDK capability — a question about how the product stays
honest about a 1000× unit difference that silently turns a compliant bank into
a catastrophically breaching one (trap 1).

| | Route | Consequence |
|---|---|---|
| **A** | **Normalise at the acquisition seam, with the factor DECLARED and both figures served** *(recommended)* | the scaling lives in `artifacts/source-vocabulary.yaml` as a declared value, never a literal in code; the payload carries the raw Call Report figure, its unit, the factor and the normalised base; and `LEX-G06` asserts the estate's own proposal labels come out right, which no unscaled implementation can satisfy |
| **B** | Normalise in Π | the fabric would carry a claim whose units differ from the estate's, and the raw figure would be lost |
| **C** | Ask `ccf-dataprep` to restate the table in dollars | changes a curated estate to suit one consumer; the FFIEC convention is correct as it stands |

**Recommendation: A.** Route C is explicitly not recommended.

---

## G · Operate and govern

### G.1 Intended product gates — 20

| id | What it asserts | Red when |
|---|---|---|
| `LEX-G01` | the served operator set is the class's declaration and the executed plan runs Policy first | a key is dropped or reordered |
| `LEX-G02` | the group is **DERIVED** from edges at the ledger point, not read from a registry | a stored group id is substituted |
| `LEX-G03` | the payload states which `connection_basis` produced the group | the basis is not disclosed |
| `LEX-G04` | **`connection_basis` MOVES the membership**: `control` and `both` give different groups on the demonstration anchor, and therefore different exposure | the basis stops reaching the traversal |
| `LEX-G05` | the regime **in force at `as_of`** is selected, and an earlier instant selects an earlier version | the regime is fixed regardless of instant |
| `LEX-G06` | **THE UNITS GATE**: the capital base is normalised by a DECLARED factor, and the estate's own two proposals evaluate to `breaches` and `fits_after_mitigation` as labelled | the raw figure is used, or the factor becomes a code literal |
| `LEX-G07` | every applicable limit **cites a provision that resolves** to rulebook text, with the quoted words served | a limit is served with no provision, or a citation that does not resolve |
| `LEX-G08` | an **absolute** limit (Reg O, $500,000) and a **percentage** limit are both expressible, and the product says which kind each is | a limit is assumed to be a percentage |
| `LEX-G09` | the enforced internal limit equals the declared one, and both disagreeing sources are served with their origin named | the two authorities drift silently |
| `LEX-G10` | the product identifies which limit **binds first**, not merely that some limit binds | only a pass/fail is served |
| `LEX-G11` | headroom and utilisation are computed against the **eligible** capital base under the regime's counting rules (`counts_guarantees`, `counts_undrawn`) | a counting rule is ignored |
| `LEX-G12` | **the freshness asymmetry is DISCLOSED**: every ratio carries the capital base's `report_date` and its age in days | a ratio is served without its denominator's date |
| `LEX-G13` | `apply_mitigation` is load-bearing: the same group evaluates differently with and without it | mitigation stops reaching the arithmetic |
| `LEX-G14` | the `proposal` is computed **with and without**, and both positions are served | only the post-proposal position is served |
| `LEX-G15` | the `proposal` is a closed object in integer canonical units; a noncanonical form is refused, never coerced | rung 24's `Q1` is weakened |
| `LEX-G16` | the **examiner** rendering carries methodology, `policy_version` and the replay anchor that the committee rendering does not | the three renderings collapse |
| `LEX-G17` | **a proposal is an assumption and cannot move `D_c`** — two proposals over one instant and group give identical debt | the hypothetical becomes evidence (rung 24's rule) |
| `LEX-G18` | economic-dependency edges carry their stated `dependencyBasis` and synthetic provenance, so judgment is distinguishable from filing | the provenance is lost |
| `LEX-G19` | debt beyond `debt_tolerance` **fails closed** — a limit calculation on incomplete exposure is withheld, not served | the tolerance stops binding |
| `LEX-G20` | replay reconstructs the determination; the same anchor, regime, basis, instant and proposal hash to the same bytes, and a changed regime or basis does not | any input is re-derived |

**One is at risk of coming back `unavailable`** — `LEX-G01`'s ordering limb,
because `CATEGORY_ORDER` has made the forbidden order inexpressible on rungs
15, 16, 19, 23 and 24. If a predicted sabotage proves structurally impossible
the guard is named and **the mechanism is not weakened to manufacture a red**.

### G.2 What this rung measures for the backlog

Whether a **third** substantially identical population reader appears (rung 23
was the first, rung 24 the second — `D-GATE-cp-24` ruled that a third triggers
measuring all three before any remedy is chosen); the limit-and-headroom
arithmetic at its **third** site (cp-05, rung 23, here), which
`docs/GATE-0-COVERAGE-CP15-24.md` §5.0 names as the abstraction-review trigger;
and the cost of four stores in one product.

---

## Gate 1 summary

- **Genuinely new:** three things (§0.2) — a population whose **membership is
  derived and caller-redefinable**; **the rule itself versioned, selected and
  anchored to published text**, including a limit that is an absolute amount
  rather than a percentage; and **a freshness asymmetry the product must
  disclose rather than resolve**. **No new SDK capability is identified.**
- **What is NOT new, though expected to be:** group-grain aggregation, limits
  and headroom, three renderings, the object-valued hypothetical and
  departmental-SQLite-first are all already proven. The capstone's value is
  that the ladder holds together.
- **Estate: ready, and richer than expected.** 184 control edges, 4
  economic-dependency edges with stated bases, 3 regime versions, 464 regime
  passages resolving to real rulebook text, a 16-row departmental workbook, and
  two engineered proposals that act as a positive control on the units trap.
- **Six traps recorded**, one of them severe: reading the capital base in the
  wrong unit makes **42 of 60 facilities breach single-handedly**.
- **Intended gates:** 20, one flagged as at risk of `unavailable`.
- **Owed:** **`Q1`** (composite over new group-scoped children, or a
  single-class producer — recommend **single-class**, and record the
  composition gap honestly) and **`Q2`** (the capital-units normalisation —
  recommend normalising at the acquisition seam with a declared factor).
- **Not started:** no implementation, no SDK work, no `D-IMPL` id spent.
