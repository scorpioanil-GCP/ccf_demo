---
product: cib.opportunity-synthesis.v1
standard: v0-3
owner: vault
sdk_spec: cp-18
tier: 5
cost_band: "×8–15 — one departmental SQLite read, five PostgreSQL reads, one MongoDB read, one bounded Fluree read; four operator categories plus an in-memory rank; no LLM"
assembly_mode: 1
capability_classes: [relational, bitemporal-ledger, graph-traversal, document-passage, in-memory]
prerequisites: [client-360-coverage-graph, mnpi-wall-enforcement, rating-and-spread-migration, credit-surveillance-early-warning]
topic: context-products
title: IB Opportunity Synthesis — Context Product Specification
generated: '2026-09-21'
---

# IB Opportunity Synthesis — Context Product Specification

**`CP-SPEC-018` · rung 18 · `cib.opportunity-synthesis` @ `1.0.0` · Gate 1 — written before any code exists, on Dave's GO of 2026-09-21 (*"GO on CP-18 IB Gate 1 only… Stop with the spec, estate evidence, intended gates, and any genuinely new capability question"*)**
**Departmental SQLite `departmental.sqlite` for banker-local prospect notes and the control-room restricted list · PostgreSQL `ccf_v2` for bankers, coverage, perspectives, projection plans, the weight vectors, mandates and every structured signal source · MongoDB `fibo_v2` for proxy and registration passages · Fluree `fibo-v2` for the ledger instant — every read read-only, every write to a per-request scratch fabric**

> **The only product in the catalog anchored on the consumer rather than on
> the subject.** A banker asks what to work on; the coverage portfolio decides
> which prospects are candidates and the verified perspective decides what the
> ranking optimizes for. Three bankers receive three different orderings of
> the same governed signals — not three sorts of one list — because Π is a
> dimension of the product rather than of the presentation layer. The weight
> vector that produced an ordering is pinned in the record, so a ranking
> entered months ago replays under the weights that were in force then.

---

> ## READ THIS BEFORE YOU READ A NUMBER
>
> **These examples teach METHOD — how to engineer and construct a Context
> Product with the CCF SDK — not the figures.**
>
> Every count and date in this document is here to show how a specification
> binds to a real store, and for no other reason. Measured read-only on
> 2026-09-21 against the live estate: `ccf_v2.banker` 40 rows,
> `coverage_assignment` 1,000, `ib_perspective` 3, `ib_projection_plan` 3,
> `perspective_weight` 66 (two versions × three perspectives × eleven signal
> types), `ib_signal_class` 11, `mandate` 40, `deal` 32 (11 MNPI-bearing),
> `interaction` 2,050 — all `synthetic — internal`; the departmental
> `prospect_note` 50 rows over 37 prospects and `restricted_list` 4 rows. The
> 50 covered prospects are real legal entities (`ccf_v2.legal_entity`,
> `provenance = 'public'`), and so are the 8-K, 13F, GDELT and
> government-award rows attached to them; **every banker, coverage
> assignment, perspective, weight, mandate, local note and restriction is
> invented.**
>
> **No number here is a fact about any real company, any real banker, or any
> real coverage portfolio.**

---

## 0 · What this document is

Gate 1 for rung 18, written to the Context Product Specification Standard
v0.3 before any code exists. Dave rules on it; nothing is built until he does.

**This rung deliberately reuses the MNPI and AML deployment shape.** The
paved producer road (`D-IMPL-343`), the credential-derived policy envelope at
the acquisition seam, the standard door with its three typed overrides, and
the SDK's Similarity operator are all **settled mechanism** and are adopted
here unchanged. The newly published adopter page
(`public/how-to/condition-acquisition-on-the-verified-credential.md`) is the
guidance this rung is written against.

### 0.1 What this rung is NOT allowed to reopen

Recorded first, because the temptation is structural: IB expresses these
three mechanisms differently from MNPI and AML, and *expressing a settled
mechanism differently is not evidence that the mechanism is wrong.*

| settled | why IB looks different | the ruling that stands |
|---|---|---|
| the credential-derived policy envelope | IB's envelope selects a **weight vector** rather than a class vocabulary | `D-GATE-cp-19` closed A2 at **B**: adopter documentation, no abstraction. Measured again here, **not reconsidered**, unless it exceeds the thresholds set there |
| the multi-principal standard door | 40 bankers rather than 3 or 4 principals | `open_door` plus three typed overrides, exactly as CP-17 and CP-19 wire it. A larger principal population is a count, not a new mechanism |
| the Similarity machinery | IB ranks candidates, and Similarity ranks passages | These are different operations. Similarity selects the evidence corpus; the **Rank step is the deployment's own arithmetic** and is not a Similarity variant. No change to `SimilaritySelectParameters` is sought |

**A redesign of any of the three is out of scope for this rung**, and a Gate-1
review finding that proposes one should be rejected on that ground alone
unless it produces a measured defect rather than a preference.

### 0.2 The five questions this Gate 1 exists to answer

Dave's own framing, and the spine of everything below.

1. **Perspective-conditioned projection and ranking from the same governed
   signals** — §A.2, §D.3 step 5, `IBO-G01`–`IBO-G04`.
2. **A pinned, policy-versioned weight vector so replay reproduces the
   historical ranking** — §B.4, §D.5, `IBO-G05`–`IBO-G07`.
3. **MNPI and wall state consumed as governed context rather than
   reconstructed** — §D.3 step 2 and **§F.4, the one genuinely new capability
   question this rung raises**.
4. **Banker-local notes as evidence that moves a ranking** — §C.1, §D.3
   step 6, `IBO-G10`, `IBO-G11`.
5. **A2 measured again on the same seven dimensions** — §G.2.

### 0.3 Placeholder discipline

Every `[TBC]` in this document carries an owner and a resolution route in
§F.2. No `[TBC]` is resolved by assumption at build time; one that cannot be
resolved becomes a finding.

### 0.4 The four-question test

- **Is the answer assembled rather than retrieved?** Yes. No store holds a
  ranked opportunity list; the ranking is composed from eleven signal classes
  across four stores under a perspective-selected weight vector.
- **Does it need governance before use?** Yes. A restricted prospect must
  leave the candidate space before anything is ranked, and the banker's
  coverage portfolio bounds the candidate set.
- **Does the answer decay?** Yes, and at eleven different rates — one day for
  spread trajectory, 180 days for government-revenue concentration.
- **Must a past answer be reproducible?** Yes, and this is the rung's sharpest
  obligation: a weight change reorders every list ever produced, so a ranking
  is defensible only if the weights that produced it are pinned.

---

## A · Decision frame

**Decision and trigger.** A coverage or product banker asking what to work on
this week, against the portfolio of prospects assigned to them.

**The consuming principals — three, with genuinely different dimensional
needs.** Read from `ccf_v2.ib_perspective` rather than restated:

| perspective | ranks on |
|---|---|
| `PSP-MA` — M&A originator | strategic catalyst, sponsor activity, sector consolidation |
| `PSP-DCM` — DCM banker | maturity walls, refinancing windows, rate sensitivity |
| `PSP-SECTOR` — sector strategist | thematic movement across the sector |

### A.1 Counterfactuals — Perspective Flat and Content Static

**Perspective Flat.** The synthesis returns "top 20 prospects" irrespective of
whether the reader originates M&A, places debt, or covers a sector. The signal
was in the estate; the frame that shapes it per role was not.

**Content Static.** Every banker sees one ranked list, and the presentation
layer filters it by portfolio. Filtering a shared ranking changes *which rows
appear*; it cannot change *what the ranking optimized for*. A maturity wall is
the DCM banker's top signal and near-noise to the M&A originator, and no
filter over a shared ordering can express that.

### A.2 The counterfactual acceptance test — measured, and it holds

The test this rung must pass is the vault specification's own: **one prospect
that ranks top-3 for the M&A originator and outside the top-20 for the DCM
banker, from identical underlying signals.**

Simulated read-only on 2026-09-21 over the 46 unrestricted candidates, with
the estate's own `perspective_weight` v1 vectors and `ib_signal_class`
half-lives against a decision instant of 2026-08-25:

| prospect | M&A rank | DCM rank | gap |
|---|---|---|---|
| `549300TMDIT8WREDOF45` (MASTEC INC) | **2** | **34** | 32 |
| `549300FHJQTDPPN41627` | 17 | 37 | 20 |
| `529900VN48L8QCMVPV36` | 25 | 10 | 15 |
| `529900L7KB2N9KXCDI76` | 21 | 6 | 15 |
| `5493000Q1S5TJIDIQH89` | 19 | 4 | 15 |

**The asked case exists**, and it inverts in both directions: three prospects
rank materially higher for DCM than for M&A. The three perspectives produced
three different top-fives. *This simulation is evidence that the estate can
carry the claim; it is not the product, and the product's own arithmetic is
specified in §D.3 step 7.*

### A.3 A refusal is an answer

A banker with no coverage assignment receives a governed refusal, not an empty
list. A banker whose perspective the estate holds no projection plan for is
refused by name. A question whose assessed Context Debt exceeds the caller's
tolerance is withheld with a replay reference. None of these is a failure of
the rung.

---

## B · Contract

### B.1 The nine elements

| element | value |
|---|---|
| **class** | `cib.opportunity-synthesis` |
| **lane** | `1.0.0` |
| **subject** | a `banker_id` — **the consumer, not the subject entity** |
| **intent** | `weekly-planning` |
| **freshness** | `event-driven` |
| **TTL** | `product_ttl_seconds: 14400` (4 h), `ttl_anchor: from_decision` |
| **assembly mode** | 1 — algorithmic throughout; **no LLM on any path** |
| **operators** | `policy.principal-subgraph`, `similarity.corpus-select`, `temporal.as-of-boundary`, `traversal.typed-neighborhood` |
| **declared gate** | `cp-18.ranking-holds` |

### B.2 Classification and residency

Classification vocabulary: `public`, `internal`, `banker-local`. Signals drawn
from filings and public news are `public`; coverage, mandates, deals and
weights are `internal`; a `prospect_note` is `banker-local` and is admitted
only for the banker who wrote it (§D.3 step 6). No residency constraint
applies: every prospect in the covered set is a US filer.

### B.3 Model-risk annotation

Not applicable — assembly mode 1. **The ranking is arithmetic over a
policy-versioned weight vector**, which is what makes it replayable and
defensible; a scored recommendation nobody can justify is a recommendation
nobody will action.

### B.4 Request parameter surface

The rule this surface is designed against is the one published at
`public/how-to/condition-acquisition-on-the-verified-credential.md`: *if
changing the value could give the caller more than its credential permits, it
is envelope input; if it can only ask for less, it can be a request
parameter.*

| parameter | type | what it moves | default | why it is here |
|---|---|---|---|---|
| `as_of` | ISO-8601 instant | the decision instant and the `T` cut | `asked_at` | narrows or moves the window; cannot admit a prospect the portfolio excludes |
| `since` | ISO-8601 instant | the signal window's lower bound | `as_of − 90d` | can only shrink the evidence |
| `limit` | number, ≤ 50 | how many ranked rows are served | 20 | can only ask for fewer |
| `signal_types` | list | narrows within the perspective's permitted set | the plan's full set | **bounded by the plan** — a type outside it is refused, not silently dropped |
| `debt_tolerance` | number, 0..1 | the caller's ceiling on assessed debt | class default | the standard tolerance surface |

**Not on the request, and refused if named:**

- **`perspective`** — it is the door's, derived from the verified credential.
  A request naming one is refused as an undeclared parameter. This is the
  CP-17 and CP-19 ruling preserved, unchanged.
- **`banker_id` as anything other than the subject** — the subject *is* the
  banker, and the entitlement check holds the caller to its own id (§D.3
  step 1).
- **`weight_version`** — and this is the load-bearing exclusion. A caller
  choosing which weight vector ranks its book could choose the one that ranks
  its book most favourably, which is strictly *more* than its credential
  permits. The version in force is resolved from the Control Plane at the
  decision instant and **pinned in the record**; replay reproduces it from the
  pin (§D.5). A historical ranking is re-read by replaying its record, never
  by asking for an old version.
- **`include_evidence` / `explain_ranking`** — the vault specification offers
  both as request parameters. **This specification declines both**, and names
  the reason as a correction rather than an omission: the payload's member set
  must be a function of the perspective and never of the request, or an empty
  member becomes informative about the subject (the property `ATM-G07` and
  `ATM-G08` established at rung 19). Evidence and the ranking explanation are
  always served to a perspective whose plan carries them.

### B.5 Prerequisites, consumers and scope boundary

**Prerequisites.** `client-360-coverage-graph` (the coverage graph),
`mnpi-wall-enforcement` (the wall state — see §F.4),
`rating-and-spread-migration` and `credit-surveillance-early-warning` (spread
trajectory and signal cadence).

**Out of scope, named:** deal execution, fee forecasting, client outreach
drafting, any generative narrative over the ranking, and any scheduler that
decides *when* a banker is asked. The product ends when the banker holds a
ranked, evidenced, replayable list.

---

## C · Data catalog

### C.1 Element table

Every row measured read-only on 2026-09-21 over the 50 covered prospects.

| element | store | table / collection | volumetrics over the covered set | class |
|---|---|---|---|---|
| banker roster | PostgreSQL | `banker` | 40 rows; 5 desks; roles coverage/credit/product | internal |
| coverage portfolio | PostgreSQL | `coverage_assignment` | 1,000 rows; **25 prospects per banker, exactly**; all 50 prospects covered by more than one banker | internal |
| perspectives | PostgreSQL | `ib_perspective` | 3 rows | internal |
| projection plans | PostgreSQL | `ib_projection_plan` | 3 rows, `plan_version` v1 | internal |
| **ranking weights** | PostgreSQL | `perspective_weight` | **66 rows = 3 perspectives × 11 signal types × 2 versions** (`v1`, `v2`) | internal |
| signal half-lives | PostgreSQL | `ib_signal_class` | 11 rows, 1–180 days | internal |
| M&A events | PostgreSQL | `signal_event` where `signal_type='8k_event'` | 534 rows over 49 prospects | public |
| sector news | PostgreSQL | `gdelt_mention` | 951 rows over 30 prospects | public |
| maturity ladder | PostgreSQL | `debt_instrument` | 96 rows over 48 prospects | public |
| spread trajectory | PostgreSQL | `spread_observation` via `debt_instrument` | 47,849 rows, keyed on `instrument_id` | public |
| institutional positioning | PostgreSQL | `institutional_holder` | 22,476 rows over 49 prospects | public |
| government-revenue concentration | PostgreSQL | `gov_contract_concentration` | 104 rows over **8** prospects | public |
| insider activity | PostgreSQL | `person_role` | 817 rows over 50 prospects | public |
| mandates and appetite | PostgreSQL | `mandate` | 40 rows, all over covered prospects; appetite in {deleveraging, acquisitive, opportunistic, no-appetite, null} | internal |
| proxy and registration passages | MongoDB | `passage`, `document` | 37,865 passages; 249 documents | public |
| **banker-local notes** | **SQLite** | `prospect_note` | **50 rows over 37 prospects**, 6 flagged rank-changing, carrying `banker_id`, `signal_type`, `materiality` | banker-local |
| restricted list | SQLite | `restricted_list` | **4 rows, all four covered, none removed** | internal |
| ledger instant | Fluree | `fibo-v2` | the `t` watermark, for `graph_snapshot_at` | — |

### C.2 Capability decomposition

`relational` (six reads), `document-passage` (one), `bitemporal-ledger` (the
watermark), `in-memory` (the rank). **No vector index** — see §C.4 trap 4.

### C.3 Correlation key and single-writer discipline

`banker_id` anchors the question; `lei` correlates every signal, note and
restriction to a prospect; `instrument_id` joins spread observations to their
issuer. Every claim enters the per-request fabric through L2's single writer,
edges before attributed nodes.

### C.4 The data traps, each with the binding chosen and what it costs

**Trap 1 — the signal-type vocabulary is a deployment mapping, not an estate
column.** `perspective_weight` and `ib_signal_class` name eleven signal types.
**No table stores a signal under those names.** `signal_event` uses an
entirely different vocabulary (`adverse_media`, `8k_event`, `trend_delta`,
`spread_widening`, `warn_notice` — CP-11's), and the remaining nine types are
derived from six other tables and one SQLite table. *The map from signal type
to source is this deployment's, declared in
`artifacts/source-vocabulary.yaml`, and no estate row is invented to hold it.*
Binding chosen: declare the map; cost: a reader must consult one artifact to
know where `maturity_wall` comes from.

**Trap 2 — the three projection plans permit identical signal types.** All
three `ib_projection_plan` rows carry the same eleven-element
`permitted_signal_types`. **The plan is therefore not the discriminator**;
the *weight vector* is. An implementation that keyed the perspective's shape
on `permitted_signal_types` would find the three perspectives
indistinguishable and the counterfactual would silently stop being
demonstrated. Binding chosen: the plan bounds **which signal types may be
admitted at all**, and `perspective_weight` decides **what the ranking
optimizes for**; §D.7's `IBO-G03` holds the two apart.

**Trap 3 — no banker maps to a perspective anywhere in the estate.**
`banker` carries `desk` (M&A Advisory 14, Leveraged Finance 11, CIB Coverage
6, Treasury Services 5, Credit Risk 4) and `role`
(coverage/credit/product), and `ccf_v2.principal` holds CP-17's four
principals whose `perspective` values are `coverage-banker`,
`research-analyst`, `trader` and `kyc-analyst` — **none of the three IB
perspectives, and no `banker_id` column.** This is the same shape as rung
19's `ATM-F-03`. Binding chosen: the credential → perspective half of the
mapping is **declared by this deployment** in `ccf_environment.yaml`; the
perspective → plan and perspective → weights halves are the **estate's** and
are read from it. `[TBC-1]`, §F.2.

**Trap 4 — no passage carries an embedding.** As at rung 19, the corpus is
ranked lexically by the SDK's reference index over passage text, the index
version is pinned, and the vector path is disclosed as out of scope rather
than worked around. A floor will need the same illustrative calibration rung
19 recorded (`ATM-F-05`), measured before it is declared. `[TBC-2]`.

**Trap 5 — government-revenue concentration reaches 8 of 50 prospects.** One
of the eleven signal types is near-empty over the covered set. That is honest
thin data, disclosed; it is *not* a reason to reweight the vector, and the
gates must not pin a count that hides it.

**Trap 6 — the estate records which banker met which prospect, and never
which banker was in the room when it mattered.**
`interaction_participant.party_key` **does** join to `banker.banker_id`:
4,000 rows, 37 of the 40 bankers, 150 distinct banker-prospect pairs. But of
the **18 MNPI-bearing interactions, not one carries a participant of any
kind** — every one of those 4,000 banker participations sits on a non-MNPI
interaction, and `deal` has no banker column at all. So the estate can say
*this banker met this prospect* and cannot say *this banker crossed the wall
on this prospect*. Wall state here is a property of the **prospect**, not of
the banker-prospect pair. This is the fact that shapes §F.4, and it was
measured after a first probe asserted the weaker and wrong claim that the
join itself was missing.

---

## D · Assembly recipe

### D.1 Client call

```
make -s example-cp-18 BANKER=--banker=BKR006
make -s example-cp-18 BANKER=--banker=BKR006 PERSPECTIVE_VIA_CREDENTIAL   # the door decides
```

### D.2 Operator step table

| # | step | category | store | emits |
|---|---|---|---|---|
| 1 | the banker, the portfolio and the envelope | — | PostgreSQL + SQLite | the candidate set and the perspective's plan |
| 2 | wall and restricted-list bound | — | SQLite (+ §F.4) | the permitted candidate set |
| 3 | the weight vector in force at `as_of` | — | Control Plane | the pinned `weight_version` |
| 4 | Policy | `policy.principal-subgraph` | — | the classification-contained view |
| 5 | Similarity | `similarity.corpus-select` | MongoDB | the supporting passages |
| 6 | Temporal | `temporal.as-of-boundary` | — | the valid-time cut at `as_of` |
| 7 | Traversal | `traversal.typed-neighborhood` | — | the signal neighborhood from each candidate |
| 8 | Rank | in-memory, the deployment's own | — | the ordering, with contributing signals |

**Policy runs before Similarity**, as at rungs 17 and 19, and the order is
read off the served product rather than off the configuration.

### D.3 Step detail

**1. The banker, the portfolio and the envelope — the credential first.**
The verified `banker_id` arrives as `AcquisitionContext.perspective`; the
request's subject must equal it. The coverage portfolio (25 prospects) is the
candidate set. The perspective's `ib_projection_plan` row bounds which signal
types may be admitted at all. *This is the A2 seam, written exactly as the
adopter page specifies, and it is measured in §G.2 — not redesigned.*

**2. The wall and restricted-list bound — before anything is ranked.** A
restricted prospect is **removed from the candidate space**, never marked as
restricted in the output: a suppressed row with a marker tells the banker
exactly what the wall exists to hide. Four of the fifty covered prospects are
on the list and none has been removed, so a banker covering all four loses
four candidates and is told nothing. **How the wall determination itself is
obtained is the open question of §F.4.**

**3. The weight vector in force.** Resolved from the Control Plane policy
bundle at the decision instant, never from the request. The version is pinned
into `policy_bundle_versions` and therefore into replay dimension 2.

**4–7. The four operator categories**, composed in `CATEGORY_ORDER`.

**6 (the acquisition half). Banker-local notes.** The departmental
`prospect_note` rows **for this banker only** are admitted as claims of class
`banker-local`. Fifty notes span 37 prospects and six are flagged
rank-changing. A fabric that cannot reach the banker's own notebook produces
a ranking the banker distrusts, because it omits what they already know.

**8. Rank — the deployment's arithmetic, and deliberately not an operator.**
For each permitted candidate, each admitted signal contributes its weight
decayed by its own half-life against `as_of`; the contributions are summed,
mandate appetite is applied, and the ordering is truncated to `limit`.
Deterministic, no inference. The served payload carries, per ranked row, the
contributing signals with their weights, their ages and their evidence
anchors. **The Rank step is not a Similarity variant and seeks no change to
the Similarity operator** (§0.1).

### D.4 Determinism class and payload hash

Class 1 — fully deterministic. The same banker, instant, perspective and
weight version hash to the same bytes.

### D.5 Replay statement and replay test

**The rung's sharpest obligation.** A ranking served under weight version
`v1` must replay to its served bytes after the Control Plane has moved to
`v2`. The record pins the version; replay resolves the pinned version and
never "latest". The negative control is the same record replayed against `v2`
deliberately, which must **diverge** rather than quietly agree — the shape
rung 19 used for its posture sabotage.

Measured support for the test: moving `PSP-MA` from `v1` to `v2` changes the
position of **28 of 46 candidates**, so the two orderings are observably
different rather than nominally so.

### D.6 Emitted contract

Payload members, all fixed per perspective: `perspective`, `as_of`,
`weight_version`, `banker`, `portfolio_size`, `candidates_considered`,
`ranked_opportunities` (each with its contributing signals, weights, ages and
evidence anchors), `signal_types_admitted`, `entities_in_view`,
`edge_types_served`. Whether the evidence trail and the local-note attribution
are members of every perspective or of some is `[TBC-3]`.

### D.7 Validation gates

Empty-operator guard, lineage strict equality, TTL bounds — the SDK's three —
plus the declared gate `cp-18.ranking-holds`, whose predicates are:
candidate containment (no restricted prospect, no prospect outside the
portfolio), weight-version presence (the served product names the version
that ranked it), signal-type containment (every contributing signal's type is
in the perspective's permitted set), shape by perspective, and
explanation completeness (every ranked row carries at least one contributing
signal).

---

## E · Volatility, debt and materialization

### E.1 Half-life table

Read from `ccf_v2.ib_signal_class`, not restated as policy: spread trajectory
1 day; sector news 7; insider activity and 8-K events 14; registrations,
proxies and activist stakes 30; **banker-local note 60**; maturity wall and
institutional positioning 90; government-revenue concentration 180. Whether
any of these needs an illustrative calibration against the snapshot is
`[TBC-4]`, to be measured before it is declared, on rung 19's terms.

### E.2 Debt model

`D_c = 1 − F·C·S`. Completeness is over the signal classes the perspective's
plan requires and the portfolio can supply — with government-revenue
concentration reaching 8 of 50 prospects, a *correct* reading of this estate
carries real debt, and that is a result rather than a defect.
`CP17-F-12`'s scorer semantics apply unchanged: F is a mean over every
observation in the view.

### E.3 Materialization posture

Derived on demand, per banker. The candidate set is portfolio-specific and the
ranking is perspective-specific, so materialization would need one cached
product per banker per perspective, refreshed at the fastest signal's cadence.

### E.4 Supersession triggers

A new 8-K or activist filing on a covered prospect; a restricted-list update;
a coverage reassignment; **a weight-vector version change**, which reorders
every list ever produced.

---

## F · Source binding and readiness

### F.1 Element readiness

Every element in §C.1 is present and measured. **No element is missing.** The
readiness risks are the six traps of §C.4, and none of them blocks the build.

### F.2 Every `[TBC]`, with an owner and a route

| id | question | owner | route |
|---|---|---|---|
| `TBC-1` | Which credential maps to which perspective, given that no estate row says? | this deployment | declare in `ccf_environment.yaml`, exactly as rung 19 resolved `ATM-F-03`; read the perspective → plan and → weights halves from the estate |
| `TBC-2` | The Similarity floor over the passage corpus | build | measure the score distribution first, then declare the smallest floor that still discriminates, with the measurement at the declaration site |
| `TBC-3` | Do all three perspectives carry the evidence trail and the local-note attribution, or only some? | Dave, at Gate 2 | the member set must be fixed per perspective either way |
| `TBC-4` | Does any half-life need an illustrative calibration against the snapshot? | build | measure; declare only if the term cannot be shown discriminating |
| `TBC-5` | **How the wall determination is obtained** | **Dave, at this Gate** | §F.4 |

### F.3 Access path

The four stores rung 19 already reads, under `CCF_CP_18_*` names declared in
`ccf_environment.yaml`, every one read-only. No new substrate.

### F.4 The one genuinely new capability question

**Everything else in this rung is a second or third writing of settled
mechanism. This is not, and it is the only question this Gate 1 asks Dave to
rule.**

**The requirement.** IB must consume MNPI and wall state as governed context
rather than reconstruct it. CP-17 (`cib.mnpi-wall`) is the product that
determines it, and it is **anchored per issuer**: one question, one issuer,
one answer.

**The arithmetic that makes this a question.** IB's candidate set is a
banker's coverage portfolio — **25 prospects, measured, for every one of the
40 bankers.** Composing CP-17 as a governed child at the candidate-set grain
is therefore **25 child questions per IB question**, and the SDK's supported
path is one parameterized `mcp_product` call per question. Asking one producer
many questions is named in `docs/EXAMPLE-EVALUATION-CRITERIA.md` §F as an
explicitly **post-launch** capability ("fan-out helpers that ask one producer
many questions"), so the supported path today is the twenty-five calls.

**What the estate says about how much of CP-17 is actually needed.** Measured
(§C.4 trap 6): the banker-to-interaction join **exists** — 4,000 rows over 37
bankers — but **none of the 18 MNPI-bearing interactions carries a participant
of any kind**, and `deal` names no banker. **This estate therefore cannot
express a per-banker wall crossing**, however much it can express a banker's
ordinary contact history. The bound IB needs at step 2 is consequently *is
this prospect restricted or MNPI-bearing at this instant*, which is one row of
the control room's restricted list plus `deal.mnpi_bearing` — and the control
room is a system of record **both** products read, not an output either owns.
Were the estate to attach bankers to MNPI interactions later, the per-banker
crossing would become expressible and route B's full fan-out would become the
honest answer; that is the condition under which this ruling should be
revisited.

**The distinction that matters, stated plainly.** Reading the restricted list
is not reconstructing CP-17's determination; CP-17 reads it too. What IB must
not do is recompute CP-17's *crossing-based, two-clock wall determination* —
the part that combines the restricted list with crossings valid at one instant
and asserted by another. The question is whether IB needs that determination
at all, or only the restricted-list bound.

**Three routes, with what each costs. Dave to rule; nothing is
pre-authorized.**

| route | what it does | cost | what it proves |
|---|---|---|---|
| **A — restricted-list bound only** | IB reads the control room directly for the candidate bound, and composes no child | one SQLite read; no composition | the bound, and nothing about composition. Risks reading as "IB reconstructs MNPI state" even though the control room is a shared system of record |
| **B — CP-17 as a governed child, full fan-out** | 25 child questions per IB question, one per candidate | 25 `mcp_product` calls per question; the fan-out §F names as post-launch | composition at full grain, at a cost the criteria already classify as backlog-shaped |
| **C — bound first, compose a demonstration subset** *(recommended)* | the restricted-list bound removes candidates before ranking; CP-17 is then composed as a governed child for the **MNPI-bearing prospects only** — measured at **10 of 50** | one SQLite read plus a bounded number of child calls | both halves: the bound is governed, and the composition boundary is genuinely exercised, without writing a fan-out helper the criteria say not to write |

**The recommendation is C**, and the reason is the rung's own evidence: the
estate cannot express the per-banker crossing that would make full fan-out
necessary, and the criteria explicitly reject building the fan-out helper
inside the example that surfaces the need. **If Dave rules B**, the fan-out
cost becomes a measured backlog record rather than a helper. **If Dave rules
A**, §D.3 step 2 loses its composition claim and says so.

**No SDK change is sought by any of the three routes.**

---

## G · Operate and govern

Accountable owner: the SDK examples maintainer (role). Degradation contract:
the control room is **mandatory** (unreachable ⇒ refused, source class named);
a banker with no coverage assignment is refused by name; a perspective with no
plan is refused by name; every other class degrades with debt. Lifecycle:
`draft` at this Gate; nothing further until Dave's ruling.

### G.1 Intended product gates

The acceptance authority for every gate is **this clause** (`D-IMPL-326`).
Each id will be claimed by exactly one executing test. **Every gate below is
directional, structural or relational; none pins a count or a date.**

| id | property |
|---|---|
| `IBO-G01` | the served operator plan names Policy before Similarity, read off the product |
| `IBO-G02` | three perspectives, one banker, one instant → three orderings and three content addresses |
| `IBO-G03` | the ordering differs while the admitted signal-type set does not — the weight vector is the discriminator, not the plan (§C.4 trap 2) |
| `IBO-G04` | the counterfactual case: a prospect ranked top-3 by one perspective and outside the top-20 by another, from identical signals |
| `IBO-G05` | the served product names the weight version that ranked it |
| `IBO-G06` | a ranking served under `v1` replays to its served bytes after the Control Plane has moved to `v2` |
| `IBO-G07` | the same record replayed against the wrong weight version **diverges** |
| `IBO-G08` | no restricted prospect appears in any served ranking, and no member, count or marker indicates that one was removed |
| `IBO-G09` | no prospect outside the banker's own portfolio appears in any served ranking |
| `IBO-G10` | a banker's local notes reach that banker's ranking and no other banker's |
| `IBO-G11` | at least one ranked row's position depends on a local note — removing it moves the row |
| `IBO-G12` | the payload's member set is a function of the perspective and never of the banker or the request |
| `IBO-G13` | every ranked row carries at least one contributing signal with its weight, age and evidence anchor |
| `IBO-G14` | a `signal_types` value outside the perspective's plan is refused, not silently dropped |
| `IBO-G15` | a banker with no coverage assignment is refused by name, as data, with a replay reference |
| `IBO-G16` | a banker id that exists nowhere is indistinguishable from one whose candidates Policy removed entirely |

Sixteen intended gates. Each will carry a named sabotage and be watched to go
red, or be recorded `unavailable` with its guard named — rung 19's discipline,
including the rule that **a sabotage which cannot redden its gate is a defect
in the proof machinery and is recorded as one.**

### G.2 The A2 measurement, and its standing instruction

A2 is **measured again here on the same seven dimensions** — domain-policy
LOC, generic plumbing LOC, concepts absent from public docs, hand-built
runtime objects, duplicated authority, structural similarity, and
AI-generatability — against cp-13-canonical, cp-17 and cp-19.

**It is not reconsidered.** `D-GATE-cp-19` closed A2 at B, and the thresholds
for reopening are fixed: *the generic seam grows materially beyond ~15 lines*,
or *a later rung requires a fifth undocumented SDK concept*. A measurement
inside those thresholds is recorded and the decision stands. One additional
datum this rung can supply that its predecessors could not: whether the
newly published adopter page **removes** the private-knowledge cost — the seam
here is to be written against the page rather than against the prior trees'
source, and whether that was sufficient is itself worth recording.

---

## Gate 1 summary

**Built on:** the MNPI and AML deployment shape, unchanged.
**New mechanism sought from the SDK:** none.
**Open question for Dave:** one — §F.4, how the wall determination is
obtained, with three routes and a recommendation.
**Estate:** complete. Every element measured, every claim in §A.2 confirmed
against live data, no missing source.
**Stop:** here. No implementation, no SDK work, no gates written until Dave
rules.
