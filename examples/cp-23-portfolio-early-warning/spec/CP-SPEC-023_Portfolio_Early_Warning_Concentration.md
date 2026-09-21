<!--
  CP-SPEC-023 — Portfolio Early-Warning / Concentration Context.
  Gate 1 ONLY. Authored to Context Product Specification Standard v0.3 before
  any code exists, per `D-IMPL-319` and the rule *specs come before code*.

  Source: `references/cbcib-portfolio-management-CLAUDE.md` — the requirements
  of Dave's `cbcib` Portfolio Management POC, supplied 2026-09-20, and the
  CP-23 definition derived from it in `docs/GATE-0-COVERAGE-CP15-24.md` §4.2.

  NOTHING HERE IS AUTHORIZED TO BE BUILT. Gate 2 is Dave's.
-->

# Portfolio Early-Warning / Concentration — Context Product Specification

**Rung 23 · Postgres (+ the graph watermark) · `cib.portfolio-early-warning`**

**Status: GATE 1 — awaiting Dave's ruling. No implementation, no SDK work, no
`D-IMPL` id spent.**

---

## 0 · What this document is

> **This is a coverage probe, not a Portfolio Management application.**
> Dave's instruction, 2026-09-21: *the smallest honest product that
> demonstrates portfolio-level aggregation, multi-signal early warning,
> policy-conditioned portfolio views, freshness/debt propagation, and
> concentration — not every PM feature in the requirements.* §0.3 records
> what is deliberately **left out**, so the omissions are a decision rather
> than an oversight.

The question this document exists to answer:

> **What does portfolio early warning require that CP-01 through CP-19 have
> not already proven?**

### 0.1 Already proven — reused unchanged, and NOT reopened

| # | Mechanism | Proven at | Reused here as |
|---|---|---|---|
| 1 | The paved producer road — `open_product(...)` with a named `plan_factory` | `D-IMPL-343`; rungs 13, 15, 16, 17, 18, 19 | the whole producer spine. **Eighth tree on the road, and see §F.1 — the low road Gate 0 predicted is not needed.** |
| 2 | The standard door + three typed overrides, tenant policy registered AFTER | `D-IMPL-324`; rungs 15–19 | three credentialed principals at one door |
| 3 | An **opaque** `ProductRequest.subject` that is not an entity URI | cp-18 (a banker as subject) | the subject is a **book**, named by its banker |
| 4 | Π as a dimension of the product — one `plan_id`, a role branch | cp-18 | three role-conditioned views of one class |
| 5 | The credential-derived envelope at the acquisition seam | `D-GATE-cp-19` (A2 closed at **B**) | followed as published; **no envelope SDK phase is opened** |
| 6 | Per-signal-class `λ_c` and a decaying freshness factor | cp-09, cp-10, cp-11 | five signal classes with genuinely different staleness |
| 7 | Two observation types — `supersede-only` vs `decay_basis: valid-from` | `D-IMPL-332`, `D-GATE-cp-18` | standing book membership vs dated signals |
| 8 | Limit-and-headroom arithmetic over committed exposure | cp-05 | **second instance**; `docs/GATE-0-COVERAGE-CP15-24.md` §5.0 names the third as the review trigger |
| 9 | A governed refusal by name, as data, with a replay reference | cp-05 onward | an unpriced intent, an ungranted role, an empty book |
| 10 | Cost/shape discipline: measure, never assert | `D-GATE-cp-16` | the member count and what acquisition materialized are served facts |

### 0.2 Genuinely new — three things, and none needs a new SDK symbol

**(a) One governed product whose subject is a POPULATION, not an entity.**
Every rung so far has anchored on one thing — an entity, a deal, a facility, a
banker's own ranked list. Here the *members are the answer's population*: 25
clients aggregate into one product, and the payload's measures are properties
of the set. cp-18 proved an opaque subject; it did not prove a subject whose
members are themselves the unit of assembly.

**(b) Context Debt as a property of a POPULATION.** `D_c` has always described
one subject's evidence. Over a book it must answer *how impaired is the worst
member's evidence, per factor*. The SDK already implements exactly that rule —
`src/ccf/halflife/debt.py::compose_debt_factors` is per-factor minimum strength
(worst factor wins, never `max(child D_c)`) — but its contract is written for
**admitted children**, and this product has none. Whether calling it with
*members* is legitimate reuse or a naming stretch is **Q1** (§F.4).

**(c) Multi-class signal freshness aggregated across many members.** Five
signal classes in the demonstration book carry genuinely different staleness —
measured 12, 14, 51, 52 and 53 days at the pinned instant — so one book's
freshness is a *distribution*, not a number. Per-class `λ_c` is proven at
cp-09/10/11 for one anchor; aggregating it across a population is not.

**No genuinely new SDK capability is identified.** Checked symbol by symbol
against `src/` on 2026-09-21 (§F.2).

### 0.3 Deliberately OUT of scope — the probe's boundary

| Left out | Why |
|---|---|
| Collateral deterioration, liquidity/treasury, rating migration as separate limbs | each is proven per-anchor at cp-06 / cp-09 / cp-10; adding them multiplies the tree without adding a *mechanism*. The four limbs in §B.3 already exercise all five of Dave's demonstrations. |
| **Regulatory large-exposure arithmetic** (`limit_definition`, `bank_capital`, `connection_basis`) | that is **CP-21's** product. CP-23 computes *book concentration against a declared threshold*, which is a different question — deliberately, so the two rungs do not solve the same problem twice. |
| The continuous-monitoring loop, ML alert clustering, the narrative layer | harness- and agent-owned by standing ruling; the product is assembled when invoked. |
| Behavioral velocity, seasonality calibration, headroom *projections* | forecasting is a model, not a context product. Utilization and headroom are served as measured facts. |
| The eleven banking skills, the UX pillars | the requirements' POC scope, not the SDK's (CLAUDE.md §13). |

### 0.4 The four-question build test (Standard v0.3)

| Question | Answer |
|---|---|
| Buildable without a further design conversation? | **No — two questions are owed** (§F.4). Everything else is settled here. |
| Every source named, with store, provenance and scale? | **Yes** — §C, measured 2026-09-21. |
| Every parameter's domain, default and effect stated? | **Yes** — §B.4. |
| Every gate expressible as a test that can go red? | **Yes, with two named risks** (§G.1). |

---

## A · Decision frame

**Decision and trigger.** A portfolio manager, credit officer or relationship
manager asking *what in my book needs attention, and where is it concentrated*
— the requirements' rejection of "dashboard-and-wait" in favor of surfacing
risk before it becomes a breach.

**Subject.** A **coverage book**, named by its banker. `ccf_v2.coverage_assignment`
carries 1,000 rows over 40 bankers — every book is 25 clients.

**Consuming principals — three, from the estate's OWN role vocabulary.**
`ccf_v2.banker.role` holds exactly three values: `coverage` (14), `credit` (13)
and `product` (13). The product uses those names rather than inventing
PM/CO/RM, on the cp-15 discipline: **do not declare what the estate already
says.**

| Role | What the book looks like to it |
|---|---|
| `coverage` | every member, utilization and headroom, client-facing signals |
| `credit` | every member, plus covenant pressure and the concentration view |
| `product` | members with facilities only; no covenant or concentration members |

**Counterfactual — *Increased Analytical Depth as a multiplier on noise*
(whitepaper §2.3).** A book of 25 clients carrying 866 signal observations will
produce a confident aggregate that answers nothing unless each signal's class,
severity and *age* travel with it. The answer here is that severity tiers are a
Control Plane artifact, each signal class decays on its own `λ_c`, and the
book's debt is the worst member's per factor — so a stale corner of the book
cannot be averaged away by a fresh one.

### A.1 The demonstration book, chosen on evidence

**`BKR019`** (Mei Nkosi, role `product`, desk M&A Advisory) — selected because
its book is the only one carrying **all ten** signal families, measured
2026-09-21:

| family | members covered (of 25) |
|---|---|
| early-warning signals | **25** |
| trend deltas | 25 |
| under a concentration limit | 21 |
| adverse media | 15 |
| facilities | **14** |
| collateral | 12 |
| deposits | 9 |
| drawdowns | 9 |
| WARN notices | 6 |
| covenant breaches | **2** |

**The book's own role is `product` while the asking principal's role is
independent of it** — a `credit` officer may ask about a `product` banker's
book. The subject is the book; the perspective is the caller's.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Class** | `cib.portfolio-early-warning` |
| **Lane** | `v1.0.0` |
| **Schema** | `portfolio_early_warning` |
| **Request surface** | §B.4 — six parameters |
| **TTL** | 24 h · `ttl_anchor: from_decision` (§E.1 — **not** evidence-anchored; the reason is stated there) |
| **Obligations** | severity tiers and the concentration threshold bound to `intent`; the member set bounded by the caller's role |
| **Assembly mode** | governed assembly at book grain; per-member acquisition, aggregated before Π |
| **Lineage** | the SDK's served operator plan; `graph_snapshot_at`; `policy_version`; one lineage entry per member |
| **Declared gates** | §G.1 — 18 gates, `PEW-G01`..`PEW-G18` |

### B.2 The four limbs, and what each demonstrates

| Limb | Source | Dave's demonstration it serves |
|---|---|---|
| **Utilization and headroom** | `facility` + `drawdown` | portfolio-level aggregation |
| **Early-warning signals** | `signal_event` (5 classes) | multi-signal early warning; freshness propagation |
| **Covenant pressure** | `covenant_breach` | *a finding is not an absence* (§C.3 trap 2) |
| **Concentration** | `legal_entity.sic` + committed exposure | concentration |

Policy-conditioned views and worst-factor debt cut across all four.

### B.3 Request parameter surface

| Parameter | Type | Domain | Default | Moves |
|---|---|---|---|---|
| `book` | — | — | — | the **subject**, a `banker_id`; not a parameter |
| `intent` | enum, required | `portfolio-review` \| `credit-review` \| `concentration-review` | — | policy envelope; **priced, never defaulted** |
| `as_of` | date-time | — | `asked_at` | `T`, and the decision instant that bounds acquisition |
| `members` | array of string | subset of the book | empty = the whole book | narrows the population. **Can only ask for FEWER.** See `Q2` (§F.4). |
| `signal_classes` | array of string | the five declared classes | empty = all | narrows which signal classes are read |
| `severity_floor` | number | `minimum: 0`, `maximum: 1` | from the tier artifact | raises the floor only; a floor below the artifact's is refused |
| `debt_tolerance` | number | 0..1 | class default | the caller's ceiling on assessed debt |

**`members` narrows and never widens.** A member not in the caller's book is
refused by name (`not-in-book`) rather than silently dropped — the cp-16
discipline that a bound refuses rather than narrows.

### B.4 Prerequisites

**None as children.** This rung declares no composite requirement: it is a
single-class producer over many anchors. Composition is CP-21's and CP-24's
business. CP-24 consumes this product's *current-state* answer as its observed
input, which is why CP-23 is built first.

---

## C · Data catalog — every figure measured against `.76` on 2026-09-21

### C.1 Element table

| Element | Store | Object | Scale | Provenance |
|---|---|---|---|---|
| Book membership | Postgres `ccf_v2` | `coverage_assignment` | **1,000** rows, 40 bankers × 25 clients | synthetic — internal |
| Banker identity and role | Postgres | `banker` | **40**; roles `coverage` 14 / `credit` 13 / `product` 13 | synthetic — internal |
| Member reference | Postgres | `legal_entity` | **156**, carrying `sic` and `sic_description` | public — GLEIF |
| Facilities | Postgres | `facility` | **60** over 22 borrowers; `commitment_amount`, `maturity_date` | public |
| Drawdowns | Postgres | `drawdown` | **151** over 14 borrowers | public |
| Early-warning signals | Postgres | `signal_event` | **1,603** over 50 LEIs; `signal_type`, `severity`, `observed_at` | public/derived |
| Covenant breaches | Postgres | `covenant_breach` | **2** estate-wide, both in `BKR019`'s book | public |
| Graph watermark | Fluree `fibo-v2` | ledger `t` | — | — |

### C.2 The five signal classes, with their measured staleness

Measured in `BKR019`'s book at the pinned instant `2026-08-25`:

| class | observations | members | newest | days stale |
|---|---:|---:|---|---:|
| `adverse_media` | 332 | 15 | 2026-08-13 | **12** |
| `8k_event` | 318 | 25 | 2026-08-11 | **14** |
| `trend_delta` | 201 | 24 | 2026-07-04 | **52** |
| `spread_widening` | 15 | 8 | 2026-07-05 | **51** |
| `warn_notice` | 2 | 1 | 2026-07-03 | **53** |

**The spread is the point.** A per-class `λ_c` table makes these five decay at
different rates, so the book's freshness factor is driven by *which* classes a
member has — and `PEW-G09` asserts that two members with different class mixes
get different freshness, never a book-wide average.

### C.3 The data traps, each with the binding chosen

**Trap 1 — `coverage_assignment` is not a bitemporal membership record.** It
carries `assigned_date` and no end date, so a book is *as it stands*, not *as
it stood*. **Binding:** membership is a **standing state** (`decay:
supersede-only`, `D-IMPL-332`) and the product states that the book is the
current roster; it does not claim to reconstruct a historical book. Gate 0's
Q16 resolution — membership as an **entity attribute on the member claim**, not
an edge, so per-member supersession reaches the invalidation register — is
adopted unchanged.

**Trap 2 — the estate's only two covenant breaches are both CURED.**
`compliant_today = True` on both; breach dates 2025-04-15 and 2025-05-27, cured
2025-06-06 and 2025-07-18. So **active covenant pressure in this book is
genuinely zero**, and the two historical breaches are real evidence of past
stress. **Binding:** the member is present and states both — zero active, two
historical-and-cured, each named — rather than being omitted. An empty member
would read as *this book has no covenant history*, which is false. This is
rung 15's *a finding is not an absence*, and rung 16's cycle member, a third
time.

**Trap 3 — utilization has no `outstanding` column.** Utilization is
`sum(drawdown.amount) / facility.commitment_amount`, computed from 151 drawdown
rows. Measured for `BKR019`: 14 borrowers between **34.19 %** and **67.31 %**.
**Binding:** the arithmetic is the deployment's and is disclosed as such; no
outstanding balance is invented, and a facility with no drawdown row is served
at zero utilization *with its drawdown count*, so zero-because-undrawn and
zero-because-unobserved are distinguishable.

**Trap 4 — 11 of 25 members have no facility at all.** **Binding:** they remain
members and carry their signal and concentration measures; the product states
the facility-covered count. Dropping them would make the book's utilization
look like the whole book's.

**Trap 5 — `concentration_limit` is a TREASURY limit, not a credit one.** Its
intents are `reserve-buffer` and `short-term-investment` and it is keyed
holder → counterparty; that is cp-09's deposit concentration. **Binding:**
CP-23's concentration limb is **book concentration by SIC sector and by
single-name share of committed exposure, against a declared threshold
artifact** — and it does **not** touch `limit_definition`, `bank_capital` or
`connection_basis`, which are CP-21's regulatory arithmetic. Stated here so the
two rungs demonstrably do not solve the same problem twice.

**Trap 6 — the book is a snapshot and the signals are up to 53 days old.** At
any demonstration instant later than the data window, a short `λ_c` reads every
member stale. **Binding:** an **illustrative calibration** under `D-IMPL-323`,
disclosed in the artifact that declares it, in the README and here, with the
decay and the decision instant left real.

---

## D · Assembly recipe

### D.1 Client call

```
GET /context-products/cib/portfolio-early-warning/BKR019
      ?intent=portfolio-review&as_of=2026-08-25&severity_floor=0.5
```

### D.2 Operator step table

| # | Step | Store | SDK operator category |
|---|---|---|---|
| 1 | Resolve the book and the caller's role; bound the member set | Postgres + Control Plane | — (acquisition) |
| 2 | Bind entitlement, intent obligations, severity tiers, the concentration threshold | Control Plane | Policy |
| 3 | Per member: facilities and drawdowns, signals by class, covenant history, sector | Postgres | — (acquisition) |
| 4 | Cut every dated claim at the decision instant | — | Temporal |
| 5 | Walk the book's members from the book anchor | — | Traversal |
| 6 | Aggregate: utilization, tiered signals, concentration, worst-factor debt | in-process | — (Π) |
| 7 | Assemble, govern, assess, gate | — | — |

**Similarity is not in this product's plan.** There is no ranked corpus: the
signals are typed rows, not passages. The class declares three operator keys,
not four, and `PEW-G01` asserts the served plan against the declaration rather
than against a fixed four.

### D.3 Where the new things sit

**Step 3 is the fan-out.** 25 members × four limbs. The member reads are
batched per limb rather than looped per member, and what acquisition
materialized is a served fact (`PEW-G13`) — the cp-16 discipline, reused.

**Step 6 carries (b).** Each member yields its own `DebtFactors`; the book's
are the **per-factor minimum** across members. The SDK's own composition rule
is exactly that; whether it may be *called* here is `Q1`.

### D.4 Determinism class

Fully algorithmic. No LLM inference. Every measure is arithmetic over acquired
claims.

### D.5 Replay statement

The product replays from its record with no second producer call: `as_of` fixes
the instant, the effective request fixes the member set and the floors,
`policy_version` fixes the tiers and the concentration threshold, and
`graph_snapshot_at` fixes the ledger point.

### D.6 Validation gates (contract level)

Empty-operator guard · lineage strict equality · TTL bounds · **member
containment** (no served member outside the book) · **tier provenance** (every
tiered signal names the artifact version that tiered it) · **debt
attribution** (the book's weakest factor names the member it came from).

---

## E · Volatility, debt and materialization

### E.1 Half-life, and why the TTL anchor is `from_decision`

| Class | `λ_c` | Basis |
|---|---|---|
| book membership | **supersede-only** | standing state; no event date |
| facility, sector | **supersede-only** | standing state |
| `adverse_media` | ~14 days | `decay_basis: valid-from` |
| `8k_event` | ~30 days | `valid-from` |
| `trend_delta` | ~90 days | `valid-from` — quarterly |
| `spread_widening` | ~30 days | `valid-from` |
| `warn_notice` | ~90 days | `valid-from` |
| drawdown, covenant breach | ~90 days | `valid-from` |

All values **illustrative** under `D-IMPL-323`.

**The TTL anchor is `from_decision`, and that is a departure worth stating.**
Rung 16 anchored expiry on its evidence's own freshness, and that was right
there because one deal-period is one piece of evidence. A book's evidence is
25 members' worth with staleness from 12 to 53 days, so *whose* freshness would
anchor it is not answerable — and rung 16 measured what happens when an
evidence anchor has nothing to anchor on: a `ttl-anchor-unresolvable` refusal
(`ABS-F-10`). **Binding:** expiry is anchored on the decision, and the
*evidence's* age is carried where it belongs, in the per-class freshness and
in `D_c`. `PEW-G10` asserts the two are not confused.

### E.2 Debt

`D_c = 1 − F·C·S` per member; the book's factors are the per-factor minimum
across members. **Completeness counts a member the role excluded as still
required** — the book genuinely is less complete for a role that may not see
part of it, and saying otherwise hides the cost of the entitlement (rungs 15
and 16, reused).

### E.3 Materialization

Nothing is precomputed. The product is assembled per request; the
continuous-monitoring loop is harness-owned by standing ruling.

### E.4 Supersession

A new signal observation; a drawdown; a covenant breach or cure; a coverage
reassignment. Per-member invalidation reaches the register because membership
is an entity attribute (trap 1).

---

## F · Source binding and readiness

### F.1 The low road is NOT needed — Gate 0's prediction is refuted

`docs/GATE-0-COVERAGE-CP15-24.md` §4.1 predicts CP-23 as *"the first low-road
rung"*, measured against cp-05's 2,382 lines over five files, and names **A10**
— `run_gates(touched_entities=None)` passing with no signal — as what it would
measure. **Read against the tree on 2026-09-21, that does not hold:**

- `src/ccf/projection/engine.py::ExecutionResult.touched_entities` returns
  **every entity URI in the composed view, sorted** — for a 25-member book,
  every member the view touched;
- `src/ccf/products/resolver.py` passes `touched_entities=execution.touched_entities()`
  into the gate sequence on the governed path, so on the paved road the
  argument is **never `None`**;
- `ProductRequest.subject` is opaque (proven at cp-18), so a book id is a legal
  subject and `open_product` needs no widening.

**Therefore CP-23 is a paved-road rung, A10 does not arise from it, and the
`Q12(b)` guard question is not triggered here.** A10 remains open for a
genuinely hand-built low-road caller; this rung is not one. **This is a Gate-1
finding and it makes the rung materially cheaper than predicted** — the
prediction is corrected rather than inherited, and the *proof* is the build.

### F.2 Symbols named, verified against `src/` on 2026-09-21

`src/ccf/products/product.py::open_product` · `src/ccf/products/request.py::ProductRequest`
(opaque `subject`) · `src/ccf/products/request.py::ArgumentDomain` ·
`src/ccf/halflife/debt.py::compose_debt_factors` · `src/ccf/products/gates.py::run_gates`
(with `touched_entities`) · `src/ccf/projection/engine.py::ExecutionResult`
· `src/ccf/controlplane/artifacts.py::PolicyConstraint` and
`ConstraintApplicability` · `src/ccf/products/expiry.py::resolve_ttl_anchor`.
Every one resolves. None is invented.

### F.3 Every `[TBC]`, with an owner

| # | Item | Owner |
|---|---|---|
| 1 | **`Q1` — debt over members** (§F.4) | **Dave** |
| 2 | **`Q2` — member-set order as identity** (§F.4) | **Dave** |
| 3 | The demonstration book `BKR019` and instant `2026-08-25` | Dave — recommended as stated |
| 4 | The illustrative `λ_c` values and severity tiers | Dave — under `D-IMPL-323` |
| 5 | Three roles from the estate's own vocabulary | Dave — recommended yes |

### F.4 — THE TWO GENUINELY NEW CAPABILITY QUESTIONS

#### `Q1` — may `compose_debt_factors` be called with MEMBERS rather than children?

**The measurement.** `src/ccf/halflife/debt.py::compose_debt_factors(own, children)`
takes `children: Sequence[DebtFactors]` and returns the **per-factor minimum
strength** — precisely the worst-factor rule this rung needs, and explicitly
*not* `max(child D_c)`, for the reason its own docstring gives: collapsing each
constituent to one number loses which factor each was weak on.

**The tension.** The function's contract is written for **admitted children of
a composite** (`D-IMPL-104`, `D-IMPL-336`). CP-23 has no children — it has
members of a population. The arithmetic is identical; the vocabulary is not.

| | Route | Consequence |
|---|---|---|
| **A** | **Call it, with members as the sequence** *(recommended)* | zero new SDK surface, and the ruled rule is applied once rather than re-implemented. Cost: a function whose docstring says *children* is called with members, so the naming and the docstring would need a later widening to stay honest. |
| **B** | The deployment re-implements per-factor minimum | ~5 lines, no SDK question — but it is the **third** site of an SDK-ruled composition rule, and the next rung would make a fourth. Re-implementing a *ruled* rule is how the rule drifts. |
| **C** | Widen the SDK contract now | out of scope: Gate 1 authorizes no SDK change. |

**Recommendation: A**, with the naming recorded as a friction finding rather
than repaired in this rung.

#### `Q2` — is a member set's ORDER part of the determination's identity?

**The measurement.** Array parameter order **is** identity today: a
`ProductRequest` carrying `members: ["A","B","C"]` and one carrying
`["C","B","A"]` produce **different canonical bytes**, hence different content
addresses. Verified in-process 2026-09-21.

**The tension.** A book is a *set*. The same 25 clients asked in two orders are
the same question and should be the same determination — but today they are
two, and an agent that builds the list from an unordered source will get a
different address each call.

| | Route | Consequence |
|---|---|---|
| **A** | **The deployment canonicalizes — sort `members` before it becomes the effective request** *(recommended)* | one question, one address. The caller's order is not evidence and is not preserved. Needs a gate proving two orderings agree, and a note that the *effective request* differs from the literal request. |
| **B** | Leave order as identity | two orderings of one book are two products with two replay records. Defensible — the effective request is what was asked — but it makes the address unstable for any caller that does not sort. |
| **C** | Ask the SDK to canonicalize array parameters | an SDK change; **not proposed**, and it would change every existing product's addressing. |

**Recommendation: A.** It is a deployment decision, costs nothing, and the
alternative is an address that changes for reasons the caller did not intend.
**Route C is explicitly not recommended** — the SDK's current behavior is
defensible and changing it reaches every rung.

---

## G · Operate and govern

### G.1 Intended product gates — 18

| id | What it asserts | Red when |
|---|---|---|
| `PEW-G01` | the SERVED operator plan matches the class's declaration and runs Policy first | the categories are reordered or a key is dropped |
| `PEW-G02` | every served member belongs to the subject's book; a member outside it is refused `not-in-book`, never dropped | a foreign member is served or silently removed |
| `PEW-G03` | the book is served at **population grain** — the member count is a served fact and the measures are set properties | a single-member answer would satisfy the payload |
| `PEW-G04` | `members` narrows and never widens; the effective population is the intersection with the book | the parameter can add a member |
| `PEW-G05` | **two orderings of the same member set are ONE determination** (per `Q2` route A) | the canonicalization is removed |
| `PEW-G06` | three roles over one book give three different member sets or measure sets from the same question | one role's answer is served to another |
| `PEW-G07` | the severity tier of every signal names the Control Plane artifact version that assigned it | a tier is hard-coded |
| `PEW-G08` | `severity_floor` may only be RAISED above the artifact's; a lower floor is refused by name | the floor can be lowered |
| `PEW-G09` | two members with different signal-class mixes get different freshness — the book is not an average | freshness is computed book-wide |
| `PEW-G10` | expiry is anchored on the DECISION and the evidence's age lives in `D_c`, not in the TTL | the TTL is re-anchored on evidence |
| `PEW-G11` | the book's debt is the **per-factor minimum** across members and names the member each weak factor came from | `max(member D_c)` is substituted |
| `PEW-G12` | a member the role excluded still counts against completeness | the entitlement is made to look free |
| `PEW-G13` | what acquisition materialized is a served fact and tracks the member count, not the estate | the count tracks the population |
| `PEW-G14` | utilization is computed from observed drawdowns; a facility with no drawdown is zero **with its drawdown count** | undrawn and unobserved become indistinguishable |
| `PEW-G15` | members with no facility remain members, and the facility-covered count is stated | they are dropped from the book |
| `PEW-G16` | covenant pressure states zero active AND two historical-and-cured; the member is never omitted | the member is dropped when empty |
| `PEW-G17` | concentration is computed against the declared threshold artifact and touches no regulatory large-exposure input | `limit_definition` or `bank_capital` is read |
| `PEW-G18` | replay reconstructs the determination with no second producer call; the same book, instant and role hash to the same bytes | any input is re-derived |

**Two are at risk of coming back `unavailable`**, named now rather than
discovered at close: `PEW-G01`, because `CATEGORY_ORDER` may again make the bad
ordering inexpressible (rungs 15, 16 and 19 all found it so); and `PEW-G05`,
which is only reddenable if the canonicalization is the deployment's — under
`Q2` route B it would have nothing to assert.

### G.2 What this rung measures for the backlog

The second instance of limit-and-headroom arithmetic (the third triggers the
review, `docs/GATE-0-COVERAGE-CP15-24.md` §5.0); the `compose_debt_factors`
naming question; whether the paved road carries a population subject as
cleanly as §F.1 predicts; and the member-count/acquisition-cost relation at
book grain.

---

## Gate 1 summary

- **Genuinely new:** three shapes (§0.2) — a **population** as subject, debt as
  a property of a population, and multi-class freshness aggregated across
  members. **No new SDK capability required**, verified symbol by symbol.
- **Gate 0's low-road prediction is refuted** (§F.1): `touched_entities` is
  threaded automatically on the paved road, so **A10 does not arise from this
  rung** and the tree is materially cheaper than predicted.
- **Estate:** ready. `BKR019`'s book carries all ten signal families; five
  signal classes with staleness from 12 to 53 days; six traps recorded with
  bindings.
- **Scope held to a probe** (§0.3): four limbs, not the requirements' six
  pillars; no regulatory large-exposure arithmetic, which is CP-21's.
- **Intended gates:** 18, two flagged as at risk of `unavailable`.
- **Owed:** **two rulings** — `Q1` (may `compose_debt_factors` take members;
  recommend **A**, call it) and `Q2` (is member order identity; recommend
  **A**, the deployment sorts).
- **Not started:** no implementation, no SDK work, no `D-IMPL` id spent.
