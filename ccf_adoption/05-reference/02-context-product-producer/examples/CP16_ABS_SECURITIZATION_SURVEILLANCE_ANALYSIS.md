> **Current operations:** use [the refreshed implementation walkthrough](CP16_ABS_SECURITIZATION_SURVEILLANCE.md) and Fluree **4.2.4** where required. The embedded specification remains historical evidence at its stated pin.

> **Reading copy:** [HTML edition](CP16_ABS_SECURITIZATION_SURVEILLANCE_ANALYSIS.html), with rendered tables and sources included in this file.

# CP-16 — ABS / Securitization Surveillance — Analysis

**Audience:** banking SME and Information Architect. **Purpose:** reconstruct the journey from the business problem to this example’s final specification.

**Final specification:** `examples/cp-16-abs-securitization-surveillance/spec/CP-SPEC-016_ABS_Securitization_Surveillance.md`, read directly from `drcastillo/ccf_code` at `37ac3055fd64ed64d78c6fd5555d79e451859153`. [Open the included final spec](#source-spec). Its recorded decisions, corrections, findings and placeholders are the destination of this walkthrough. The [Standard v0.3](#source-standard) supplies the template and the [generation recipe](#source-recipe) explains the ownership and evidence sequence.

The figures below are the final spec’s teaching-estate measurements or declared design values. They are not new runtime measurements. Once the design journey is understood, continue with the [implementation walkthrough](#source-implementation).

## Start with trigger proximity and the cost of detail

A structured-finance desk or risk function asks how a securitization is performing and whether a trigger may change its waterfall. A delinquency percentage alone does not answer that question: the applicable trigger definition and units must accompany it. Asking for every loan can also make a correct answer economically impractical.

The estate contains **1,322,453 loan-period rows**; one deal-period contains 35,814. The SME and Information Architect therefore make granularity three things at once: a meaningful request choice, a payload-and-cost choice and a credential-bounded entitlement. The desk may ask at loan level, credit risk at cohort level and client reporting at deal level.

The hardest evidence issue is the only amended trigger. SDART-2022-6 moves from **24.00% to 13.50%**, effective **1 November 2025**. The amendment is engineered and has no filed passage. The final ruling is to serve it explicitly **unanchored**, with synthetic provenance and a finding, so the temporal demonstration remains visible without invented prospectus text.

## Declare the shape and the two kinds of bound — Standard §0–§B → final §0–§B

| Element | Value |
|---|---|
| **Class** | `cib.abs-surveillance` |
| **Lane** | `v1.0.0` |
| **Schema** | `abs_surveillance` |
| **Request surface** | §B.4 — seven parameters |
| **TTL** | 24 h · `ttl_anchor: from_entity_freshness`, anchored on the servicer report's period end (§E.1) |
| **Obligations** | Risk-retention and disclosure bound to `intent`; loan-level privacy bound to `perspective_role` |
| **Assembly mode** | Governed assembly from three stores; aggregate at the effective granularity |
| **Lineage** | `operators_invoked` as the SDK's served plan; `graph_snapshot_at` as ledger `t`; `policy_version`; passage-level `L` on every structural claim |
| **Declared gates** | §G.1 — **21 gates**, `ABS-G01`..`ABS-G21` plus `ABS-G07` |

The contract table retains an older gate-count description; the final §G and Gate-1 summary declare **22 gates**. Its reference to request §B.4 likewise points to the surface actually located at §B.3. Those are source-document inconsistencies, not new product behavior.

| Parameter | Type | Domain | Default | Moves |
|---|---|---|---|---|
| `deal_id` | string, required | the 3 deals in `ccf_v2.abs_deal` | — | anchor |
| `intent` | enum, required | `trigger-monitoring` \| `holdings-review` \| `client-reporting` | — | policy envelope; **priced, never defaulted** |
| `as_of` | date | the 12 periods `2025-07`..`2026-06` | latest | `T` — reporting period **and the decision instant** (§F.4.1) |
| `granularity` | enum | `ArgumentDomain.members = (deal, tranche, cohort, loan)` | `tranche` | **payload shape and cost band**, bounded by the role ceiling |
| `cohorts` | list | the 4 cohorts per deal-period | all | `R` filter |
| `trigger_proximity` | bool | — | `true` | payload shape |
| `loan_sample` | int | `minimum: 0` | `0` | **cost bound** — stratified across cohorts, never a prefix |

`ArgumentDomain.members` defines which granularities are meaningful. A role-applicable `PolicyConstraint.allowed_set` defines which meaningful values this caller may request. Outside-domain and above-ceiling requests are distinct refusals. A client-reporting caller asking for loan detail receives `not-in-allowed-set` with the bound; it is not silently downgraded.

The served product states effective granularity **and the ceiling actually resolved**. This positive assertion replaces the source article's vacuous “if policy lowered it” rule: policy never lowers it in this SDK path. The Control Plane is the enforced authority; estate entitlement rows are evidence against which drift is checked.

`as_of` bounds acquisition at the decision instant and selects the report period. Reading current rows and merely labelling them September would answer the wrong question. A requested loan sample is stratified across cohorts, not a prefix of a file whose order may be unrepresentative.

## Assess source fitness before asserting structure — Standard §C → final §C

The three-store evidence includes deal structure, tranches, trigger definitions, pool measurements, passages, entitlements and stamped cost measurements. The amendment is reached through the existing two-hop path: deal `specifiesTrigger` original, then original `supersededBy` amendment. There is no direct deal-to-amendment edge to pretend exists.

Other findings shape the payload. ABS-15G repurchase filings are depositor-scoped and carry no deal IDs; the product serves that scope and explicitly states that per-deal attribution is unavailable. One yield-supplement trigger has a unit and passage but no numeric value or component, so proximity is an explained uncomputable finding. Two overcollateralization triggers have two threshold components; both remain visible with the binding component identified.

All 1,882 ABS passages have embeddings, but the source records that the SDK's ready path is lexical. The analysis must not attribute the limitation to missing estate vectors. Some FIBO terms are provisional and absent from the single-file Release load; a zero result from that load does not prove the estate lacks the relationship. Other vocabulary bindings remain provisionally `ex:` and are recorded for resolution rather than asserted as absent from FIBO.

## Resolve the missing anchor without falsifying it — Standard §D → final §D and §F.4

| # | Step | Store | SDK operator category |
|---|---|---|---|
| 1 | Resolve the deal and its reporting period for `as_of` | Postgres | — (acquisition) |
| 2 | Bind entitlement, intent obligations and the **granularity ceiling** | Control Plane + estate evidence | Policy |
| 3 | Walk `specifiesTrigger` / `isSubordinatedTo` / `isCollateralizedBy` at the ledger point for `as_of`, **following `supersededBy` to the definition in force** | Fluree | Traversal + Temporal |
| 4 | Retrieve prospectus and servicer passages supporting each structural claim, within the step-2 allowlist | MongoDB | Similarity |
| 5 | Resolve pool performance **at the effective granularity**, aggregating or sampling *in acquisition* | Postgres | — (acquisition) |
| 6 | Compute pool performance, tranche coverage, trigger proximity, benchmark comparison | in-process | — (Π) |
| 7 | Assemble, govern, assess, gate | — | — |

The original threshold applies at **30 September 2025**; the amended threshold at **30 June 2026**. The amendment's assertion date, **11 January 2026**, is separate from its November effective date. The final spec explains the knowledge-time distinction as well, but the seven-parameter surface above does not add a caller `known_as_of` parameter. The analyst must distinguish that semantic example from an invented API option.

Route B splits the anchor promise into two independently testable invariants. Every **publicly sourced** threshold has a rehashable prospectus anchor. Every threshold without a public anchor states `anchored: false`, synthetic/engineered source classification and a finding naming the missing public anchor. No empty anchor object, null passage ID or placeholder document is allowed to imply filed text exists. Neither refusing the engineered amendment nor minting a passage follows the final ruling.

The source acquisition must do the aggregation or sampling before it emits signal envelopes. Deal, tranche and cohort use pre-aggregated rows; loan detail is streamed and sampled without materializing the full pool. The gate measures records and blocks at that seam, because merely saying “streaming” cannot prove bounded work.

## Let cost evidence govern the design, not the stopwatch — Standard §E–§F → final §A.2 and §E–§F

The 24 measured runs show stable block counts of **2, 4, 2 and 1,763** for deal, tranche, cohort and loan respectively. Wall-clock time is unstable: cohort's measured range spans about 1,391× and its worst timing exceeds a loan run. The final cost rule therefore uses **blocks, never timing as a gate**.

Those counts are stamped evidence, not permanent constants. The invariant is relational: aggregate levels are close in block cost, while loan detail is orders of magnitude more expensive. The product reports the current and next-detail cost bands so a consuming agent can understand its request's consequence.

Monthly loan/tranche performance uses roughly 30-day half-lives, vintage benchmarks roughly 90 days, and trigger/prospectus standing state is non-decaying and superseded. Debt is **1 − F×C×S** over required classes; a privacy-excluded required class still affects completeness under this spec's explicit rule. The materialization split is monthly aggregate levels versus on-demand loan detail.

The declared TTL is 24 hours anchored on the servicer report period end. The spec identifies the mismatch with the static monthly estate and calls for disclosed illustrative calibration, but does not give a replacement value here. Older TBC rows and the earlier “ruling owed” sentence must be read with the later Route B approval. The final summary records 22 executing gates, 21 observed red under sabotage and one unavailable because operator ordering is structurally fixed.

## Hand over the exact acceptance boundary — Standard §G → final §G

| id | What it asserts | Red when |
|---|---|---|
| `ABS-G01` | The served operator plan runs Policy before Similarity | the categories are reordered |
| `ABS-G02` | The deal, its 6 tranches and their `seniority_rank` ordering are served from the graph, not from a constant | the ordering is hard-coded |
| `ABS-G03` | At `as_of 2025-09-30` the in-force delinquency threshold is the **original**; at `2026-06-30` it is the **amendment** | the ledger point is ignored |
| `ABS-G04` | The amendment is reached by `specifiesTrigger` then `supersededBy` — never by a name-match join | a string join is substituted |
| `ABS-G05` | Acquisition is bounded at the **decision instant**: a question at `2025-09-30` acquires no `2026` loan period | the bound is dropped (residual 341-1) |
| `ABS-G06` | **Anchoring invariant 1** — every **publicly sourced** threshold resolves to a passage whose stored `sha256` re-hashes | an anchor is broken or a hash drifts |
| `ABS-G07` | **Anchoring invariant 2** — every threshold **without** a public anchor is named in the product as `anchored: false`, classified `synthetic`/engineered, with a finding naming the missing public anchor; and **nothing in the payload implies a passage exists** | the amendment is served as anchored, silently dropped, or given a blank/placeholder anchor |
| `ABS-G08` | A granularity outside `ArgumentDomain.members` is a **request-validity** refusal | the domain is widened |
| `ABS-G09` | A granularity inside the domain but above the role ceiling is refused **`not-in-allowed-set` with the bound attached** | the ceiling is dropped, or the value is silently lowered |
| `ABS-G10` | **Positively**: the ceiling **stated in the payload** equals the `PolicyConstraint` actually resolved for that principal — asserted for all three principals, so it cannot pass by coincidence | the stated ceiling is hard-coded, or derived from anything but the resolved constraint (§F.4.2) |
| `ABS-G11` | The enforced ceiling equals the estate's declared ceiling for that principal | the three authorities drift (trap 5) |
| `ABS-G12` | Three principals, one door, three different effective granularities from the same question | one principal's answer is served to another |
| `ABS-G13` | **Load-bearing.** The complete source population is never materialized: **records scanned** and **blocks scanned** are measured at the acquisition seam, and the acquired record count tracks the *answer*, not the *population* — at `loan` it is bounded by the sample, at the aggregate rungs by the cohort count | the acquired count tracks the population, or the aggregation moves out of acquisition |
| `ABS-G14` | `loan_sample` draws **stratified across cohorts**, not a prefix | a prefix is taken |
| `ABS-G15` | Cost is served as a **relational** fact keyed on blocks — the three aggregate rungs indistinguishable and all ≪ `loan` — with the measured counts carried as stamped evidence rather than as product constants. **Timing is never a gate.** | a time-keyed assertion is substituted, or a measured count becomes a threshold (§A.2) |
| `ABS-G16` | The yield-supplement trigger is served as a **finding naming why proximity is uncomputable** | it is served as `0` or dropped (trap 3) |
| `ABS-G17` | A two-component threshold carries both components and names which bound the test | one component is silently discarded (trap 4) |
| `ABS-G18` | Repurchase activity is **depositor-scoped with a stated absence** of per-deal attribution | a deal↔filing join is invented (trap 2) |
| `ABS-G19` | **Two observation types.** The standing classes (deal, tranche, trigger, anchor) are minted `supersede-only` and carry no observed time; the dated ones (cohort, loan, benchmark, repurchase) declare `decay_basis: valid-from` and carry their day — so an undated claim in a *dated* class is refused, which is what `D-IMPL-332` actually says | a dated class's basis is moved off `valid-from`, collapsing the distinction |
| `ABS-G20` | TTL is anchored on the servicer report's period end, not on request time | the anchor moves to `asked_at` |
| `ABS-G21` | Replay reconstructs the served product from the record and the stores with no second producer call | any input is re-derived rather than resolved |
| `ABS-G22` | **Existence is not an oracle.** A deal that does not exist and a real deal with no reporting period at the instant are refused *indistinguishably*; a subject with evidence is served, so the gate is not vacuous | the two refusals differ by subject |

The unavailable gate is `ABS-G01`, with `CATEGORY_ORDER` named as its guard; it is not silently counted as a successful sabotage. The remaining contract makes trigger effectivity, honest anchoring, bounded acquisition, cost and role ceiling inspectable together. The SME can assess proximity to the actual threshold while the architect can bound both disclosure and the cost of constructing the answer.


## Included source snapshots

Exact retrieved source texts, with their original historical statuses and internal links retained as source text. Tables quoted within the walkthrough come directly from the final spec; Markdown pipe escaping is normalized for display.

<a id="source-spec"></a>

<details>
<summary>Final example specification — ccf_code@37ac3055</summary>

Path: `examples/cp-16-abs-securitization-surveillance/spec/CP-SPEC-016_ABS_Securitization_Surveillance.md`

``````text
<!--
  CP-SPEC-016 — ABS / Securitization Surveillance.
  Authored at Gate 1 to Context Product Specification Standard v0.3
  (vault `context-products/spec-standard-v0-3`) before any code exists, per
  `D-IMPL-319` and the memory rule *specs come before code*.

  Source specification: vault `context-products/abs-securitization-surveillance`
  (`cib.abs-surveillance.v1`, standard q019, generated 2026-08-15, corrected
  2026-08-23 and 2026-08-24). Where this document departs from that one, the
  departure is stated and reasoned at the point of departure — never silently.

  GATE 2 GRANTED 2026-09-21 with §F.4 ruled Route B. The ruling was folded
  into this document BEFORE any implementation, per Dave's instruction.
-->

# ABS / Securitization Surveillance — Context Product Specification

**Rung 16 · Tier 4 · Postgres + Fluree + MongoDB · `cib.abs-surveillance.v1`**

**Status: GATE 2 — §F.4 RULED (Route B), 2026-09-21. Build authorized, minimal,
on the existing SDK. No SDK work.**

---

## 0 · What this document is

This is the specification for rung 16 of the Context Product ladder, authored
at Gate 1 to answer one question before a line of code was written, and carrying
Dave's Gate-2 ruling folded in at §F.4:

> **What does ABS surveillance require that CP-01 through CP-19 have not
> already proven?**

Everything else in here is in service of that question. §0.1 records what is
reused unchanged and is explicitly **not** reopened. §0.2 records what is
genuinely new. §0.3 records the data traps, each measured against the live
estate on 2026-09-21, with the binding this specification proposes. §F.4 was
the single question owed at Gate 1; it is **ruled**, and the ruling governs the
build.

### 0.1 Already proven — reused unchanged, and NOT reopened

Nine mechanisms this rung consumes exactly as earlier rungs left them. None is
reopened, re-measured, or improved for this rung's convenience.

| # | Mechanism | Proven at | Reused here as |
|---|---|---|---|
| 1 | The paved producer road — `open_product(config_root, scratch, acquire, project, assess, gate, environ)` with `--8<--` boot/answer regions and a **named** `plan_factory` | `D-IMPL-343`; cp-04-canonical; rungs 13, 15, 17, 18, 19 | The whole producer spine. Seventh tree on the road. |
| 2 | The standard door — `open_door` plus three typed overrides (token source, perspective resolver, tenant entitlement policy **registered after**, latest-wins) | `D-IMPL-324`; cp-17, cp-18, cp-19, cp-15 | Three credentialed principals at one door (§B.4). The ordering rule is private knowledge and is carried as friction, not repaired here (batch A1). |
| 3 | The credential-derived policy envelope at the acquisition seam — `AcquisitionContext.perspective`, the envelope/parameter rule | `D-GATE-cp-19` closed **A2 at B**; `public/how-to/condition-acquisition-on-the-verified-credential.md` | Followed as published. **A2 is closed. This rung opens no envelope SDK phase and takes on no new A2 measurement obligation.** |
| 4 | Policy before Similarity, made inexpressible otherwise by the SDK's `CATEGORY_ORDER` (policy → similarity → temporal → traversal) | cp-19 (`ATM` gates); whitepaper §7.4(c) | Step 2 bounds the corpus before step 4 retrieves from it. |
| 5 | Passage-level lineage with a re-hashable span — `PassageAnchor` (`src/ccf/contracts/claims.py::PassageAnchor`) over stored `sha256` | cp-13-canonical; cp-19 | Every trigger threshold anchored to filed prospectus text (§D.7). |
| 6 | Evidence-anchored TTL — `from_entity_freshness` resolved by `src/ccf/products/expiry.py::resolve_ttl_anchor` | cp-02; cp-15 | Expiry rides the servicer report's own period, never request time. |
| 7 | As-of evaluation over a bitemporal ledger, with the assertion clock kept distinct from the validity clock | cp-08 (*booking lag is not supersession*); cp-13-canonical | Trigger definitions **as they stood in the period** (§D.3 step 3). |
| 8 | A governed refusal returned by name, as data, with a replay reference — never a raise | cp-05 onward | The granularity ceiling (§F.4). |
| 9 | `PolicyConstraint` with `ConstraintApplicability.perspective_role` and an `allowed_set` fold | `src/ccf/controlplane/artifacts.py::PolicyConstraint`; cp-17, cp-19 | The ceiling artifact itself. |

### 0.2 Genuinely new — three shapes, none needing a new SDK symbol

**This is the answer to the question in §0.** Three things here are not proven
by the first nineteen rungs. Two are demonstrations rather than mechanisms; one
is a request-surface shape the ladder has never carried.

**(a) A request parameter that is simultaneously a shape lever, a cost lever,
and the thing a role ceiling bounds.** Every prior rung's role-bounded value
was a *value*: cp-15's ownership threshold, cp-17's permitted classes,
cp-19's corpus scope. `granularity` is different in kind — the same parameter
decides the payload's shape, the assembly's cost band, and is the parameter the
caller's credential is allowed to bound. The SDK carries both halves already
(`src/ccf/products/request.py::ArgumentDomain` for the domain, `PolicyConstraint`
+ `perspective_role` + `allowed_set` for the ceiling), and nothing new is
needed — but no rung has yet put a *shape-and-cost* selector under a role
ceiling, and the interaction is where this rung's evidence is.

**(b) Assembly that must not materialize the population it reads.** The loan
leg carries **1,322,453 rows** (`ccf_v2.abs_loan_period`, measured 2026-09-21);
one deal-period alone is 35,814. Every prior rung materialized everything it
acquired, because everything it acquired was small. Here the aggregation or the
sample must happen **in acquisition, before signal envelopes are emitted**, or
the fabric ingests a million rows to answer a question about four cohorts. No
new SDK symbol is implicated; what is new is that the fan-out is real rather
than notional, which is precisely why the source specification calls this rung
the catalog's cost stress test.

**RULED 2026-09-21 — this is a LOAD-BEARING property of the rung.** The loan
and deal-period legs **must not materialize their complete source populations
merely to assemble the product**, and the proof is a measurement rather than an
assertion: **records scanned and blocks scanned** are captured at the
acquisition seam and gated (`ABS-G13`). A rung that merely *says* it streams has
proved nothing; the gate reddens when the acquired record count tracks the
population rather than the answer.

**(c) The cost of the caller's own question, stated back to the caller as a
governed fact.** The estate carries `ccf_v2.abs_cost_measurement` — 24 timed
runs made by `ccf-dataprep` on 2026-08-23. A product that tells an agent what
its question costs is a pattern the ladder has not demonstrated, and it is the
direct answer to the source specification's own framing: *an agent that cannot
see cost will always choose maximum detail.*

**Residual `341-1` goes live for the first time.** Acquisition must be bounded
at the decision instant rather than at request time. Gate 0 records this as *a
rule stated nowhere public*. This rung is where it is first exercised, and the
absence of a public statement of the rule is carried as friction.

**No genuinely new SDK capability is identified.** That is a claim, not an
assumption: it was checked symbol by symbol against `src/` on 2026-09-21, and
every mechanism §0.1 and §0.2 name resolves to a real definition site (§F.3).

### 0.3 The counterfactual that has no data, surfaced first

The source specification asks for **≥ 1 trigger definition amendment, so as-of
evaluation matters**. The estate has exactly one, and it is the sharpest fact
in this document — see §F.4. It is surfaced here, before the contract, because
it determines whether this rung's headline claim is serveable at all.

### 0.4 The four-question build test (Standard v0.3)

| Question | Answer |
|---|---|
| Can an engineer build this without a further design conversation? | **No — one ruling is owed** (§F.4). Everything else is settled here. |
| Is every source named, with its store, its provenance and its scale? | **Yes** — §C, every figure measured 2026-09-21 against `.76`. |
| Is every parameter's domain, default and effect stated? | **Yes** — §B.4. |
| Is every gate expressible as a test that can go red? | **Yes, with one named risk** — §G.1, and the vacuity risk on `ABS-G10` is stated rather than discovered later. |

---

## A · Decision frame

**Decision and trigger.** A structured-finance desk monitoring a deal it
arranged or holds, or a risk function testing whether a trigger is
approaching. The question is *how is this securitization performing, and how
close is it to a trigger that changes the waterfall*.

**Consuming principals.** **Three**, and the estate holds all three
(`ccf_v2.abs_granularity_entitlement`, measured 2026-09-21). The source
specification says "single role at this tier"; this document departs from it,
because the estate that was built for it carries three roles with three
different granularity ceilings, and the ceiling is the mechanism this rung
exists to demonstrate. A single role would make the ceiling unobservable.

| Principal | Ceiling | The estate's own rationale |
|---|---|---|
| `structured-finance-desk` | `loan` | arranges and holds these deals; needs loan-level detail |
| `credit-risk` | `cohort` | monitors trigger proximity; cohort detail is sufficient |
| `client-reporting` | `deal` | external-facing; loan-level borrower attributes are not disclosable |

### A.1 Counterfactuals

**Increased Analytical Depth as a multiplier on noise** (whitepaper §2.3). An
agent that ingests loan-level detail without the deal's structure produces
confident aggregates answering no question anyone asked. *Delinquency rose
40bp — does that approach a trigger?* Only the structure knows, and the
structure lives in a prospectus. This rung's answer: the trigger threshold and
the pool measure are served **together**, each anchored, and proximity is
computed in the unit the trigger is defined in.

**Cost blindness.** The second failure, specific to this tier: naive assembly
here is not slow but economically unviable. The counterfactual is a product
that meets its contract and blows its budget.

### A.2 The counterfactual acceptance test — measured, and it holds

The cost counterfactual is only demonstrable if the cost difference is real and
reproducible. Measured across the estate's own 24 timed runs (`ccf_v2.abs_cost_measurement`,
six runs per granularity, 2026-08-23, basis 1,322,453 rows):

| Granularity | Rows | Shared blocks | Distinct block values across 6 runs | median ms range |
|---|---:|---:|---:|---|
| `deal` | 1 | 2 | **1** | 0.260 – 0.724 |
| `tranche` | 6 | 4 | **1** | 0.297 – 0.963 |
| `cohort` | 4 | 2 | **1** | 0.148 – **205.871** |
| `loan` | 35,814 | 1,763 | **1** | 39.040 – 43.193 |

**The block count is perfectly stable; the wall clock is not.** Every
granularity returns exactly one distinct block value across all six runs, while
`cohort`'s median time spans a **1,391× range** — and `cohort`'s worst run
(205.871 ms) is **4.9× slower than `loan`'s best** (39.040 ms). A cost gate
keyed on milliseconds would therefore invert the very ordering this rung
exists to teach. This is `ccf-dataprep`'s own caveat, re-measured here rather
than inherited.

**RULED 2026-09-21.** Cost evidence is **block count, never wall-clock
runtime**; **timing is not a gate**. The measured structural counts — 2, 2, 4,
1,763 — are evidence for the shape-and-cost relationship, **but estate-specific
counts are not to become product constants where a relational assertion is
sufficient.** So the gates assert the *relationships*, which hold at any pool
size:

- the three aggregate rungs are **indistinguishable in block terms** from one
  another and separated from `loan` by orders of magnitude — `blocks(deal) ≈
  blocks(tranche) ≈ blocks(cohort) ≪ blocks(loan)`;
- descending from `cohort` to `loan` is the **only** step that changes cost
  materially, and it is the same step the privacy ceiling sits on;
- the product carries enough governed cost information for **an agent to reason
  about the consequence of asking for greater detail** — the band it is in, the
  band the next level down would be in, and that the two are not comparable.

The four measured numbers appear in the product as **evidence with their
measurement stamp**, not as thresholds anything is compared against.

### A.3 A refusal is an answer

A `client-reporting` principal asking for `granularity=loan` gets a governed
refusal naming `not-in-allowed-set` with the bound attached — not a quietly
downgraded product. §F.4 is where that is ruled.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Class** | `cib.abs-surveillance` |
| **Lane** | `v1.0.0` |
| **Schema** | `abs_surveillance` |
| **Request surface** | §B.4 — seven parameters |
| **TTL** | 24 h · `ttl_anchor: from_entity_freshness`, anchored on the servicer report's period end (§E.1) |
| **Obligations** | Risk-retention and disclosure bound to `intent`; loan-level privacy bound to `perspective_role` |
| **Assembly mode** | Governed assembly from three stores; aggregate at the effective granularity |
| **Lineage** | `operators_invoked` as the SDK's served plan; `graph_snapshot_at` as ledger `t`; `policy_version`; passage-level `L` on every structural claim |
| **Declared gates** | §G.1 — **21 gates**, `ABS-G01`..`ABS-G21` plus `ABS-G07` |

### B.2 Departures from the source specification, each reasoned

| Source says | This document says | Why |
|---|---|---|
| "Single role at this tier" | Three roles | The estate carries three ceilings; one role makes the ceiling unobservable (§A). |
| `operators_invoked: [Resolve, Policy, TemporalTraversal, Similarity, Enrich, Aggregate]` — six | The SDK's **served** operator plan, three keys | Six spec operators map to three SDK operator keys; the served plan is the fact, the spec's list is vocabulary. Recorded as friction, not repaired (Gate 0). |
| "if policy lowered the granularity, say so" | A request above the ceiling is **refused by name**; a served product states its effective granularity **and the ceiling in force**, and `ABS-G10` proves that stated ceiling equals the resolved constraint | The constraint layer refuses out-of-bound values and never narrows them (`D-IMPL-251`); a vacuous assertion is refused by ruling. §F.4.2. |
| `Waterfall`, `Servicer`, `servicedBy`, `SourceDocument` | `ex:` terms, provisionally, raised upstream | No FIBO term exists / the binding pass has not reached them. **Absence from the binding table is not evidence of absence from FIBO** — a wrong module guess is indistinguishable from a missing term. |

### B.3 Request parameter surface

| Parameter | Type | Domain | Default | Moves |
|---|---|---|---|---|
| `deal_id` | string, required | the 3 deals in `ccf_v2.abs_deal` | — | anchor |
| `intent` | enum, required | `trigger-monitoring` \| `holdings-review` \| `client-reporting` | — | policy envelope; **priced, never defaulted** |
| `as_of` | date | the 12 periods `2025-07`..`2026-06` | latest | `T` — reporting period **and the decision instant** (§F.4.1) |
| `granularity` | enum | `ArgumentDomain.members = (deal, tranche, cohort, loan)` | `tranche` | **payload shape and cost band**, bounded by the role ceiling |
| `cohorts` | list | the 4 cohorts per deal-period | all | `R` filter |
| `trigger_proximity` | bool | — | `true` | payload shape |
| `loan_sample` | int | `minimum: 0` | `0` | **cost bound** — stratified across cohorts, never a prefix |

**RULED 2026-09-21.** `granularity` is treated as **all three things
simultaneously** — a caller request parameter, a product-shape and cost lever,
and a role-bounded policy value — realized on the existing mechanisms only:
`ArgumentDomain.members`, `PolicyConstraint`, `ConstraintApplicability.perspective_role`,
and the `allowed_set` fold. **No new SDK abstraction.** `ABS-G10` must
**positively** prove that the ceiling the product states equals the policy
constraint actually resolved for that principal; a vacuous *"if policy lowered
it"* assertion is explicitly refused (§F.4.2).

**`granularity` carries two different bounds and they are different kinds of
thing.** `ArgumentDomain.members` says which values are *meaningful questions
of this class* — request-contract vocabulary, no artifact pin, no authority.
The role ceiling says which of those meaningful values *this caller may ask* —
a `PolicyConstraint` with a pin and an authority. `D-IMPL-259` is explicit that
the first must not be turned into the second. A value outside the domain is a
request-validity refusal; a value inside the domain but above the ceiling is a
policy refusal carrying the bound. **They are separate gates** (`ABS-G08`,
`ABS-G09`).

### B.4 Prerequisites and scope boundary

The source specification names two prerequisites: `counterparty-reference-snapshot`
and `covenant-cross-reference`. Neither is required as a **child product**:
cp-01 is a frozen specimen (`D-IMPL-261`) and cp-13-canonical's passage
machinery is a *pattern* this rung reuses, not a product it composes. **This
rung declares no children.** It is a single-class producer, exactly as rungs
15, 17, 18 and 19 were — composition is CP-20's and CP-21's business.

---

## C · Data catalog

### C.1 Element table — every figure measured against `.76` on 2026-09-21

| Element | Store | Object | Scale | Provenance |
|---|---|---|---|---|
| Deals | Postgres `ccf_v2` | `abs_deal` | **3** (SDART-2022-6, TAOT-2022-B, SDART-2024-1) | public — ABS-EE EX-102 |
| Tranches | Postgres | `abs_tranche` | **18** (6/6/6), `seniority_rank` 0..5 | public — 424B5 |
| Loan-level performance | Postgres | `abs_loan_period` | **1,322,453** rows; 12 periods per deal, `2025-07`..`2026-06` | public — ABS-EE |
| Cohort aggregates | Postgres | `abs_cohort_performance` | **132** (4 cohorts × 12 periods × ~3 deals) | derived |
| Servicer reports | Postgres | `abs_servicer_report` | **36** (12 per deal) | public — 10-D |
| Vintage benchmarks | Postgres | `abs_vintage_benchmark` | **24** | derived across loaded deals |
| Repurchase filings | Postgres | `abs_repurchase` | **8**, all `deal_id = NULL` (§C.3 trap 2) | public — ABS-15G |
| Internal holdings | Postgres | `abs_holding` | **6**, 2 of them `is_risk_retention` | synthetic — internal |
| Granularity ceilings | Postgres | `abs_granularity_entitlement` | **3** principals | synthetic — internal |
| Materialization posture | Postgres | `abs_materialization_policy` | **4** (deal/tranche/cohort materialized; loan on-demand) | synthetic — internal |
| Measured cost curve | Postgres | `abs_cost_measurement` | **24** timed runs | measured by `ccf-dataprep` 2026-08-23 |
| Deal / tranche / trigger structure | Fluree `fibo-v2` | `AssetBackedSecurity` 3, `PoolBackedSecurity` 3, `Tranche` 18, `TriggerEvent` **11** | — | public |
| Structural edges | Fluree | `specifiesTrigger` **10**, `isSubordinatedTo` **16**, `isCollateralizedBy` **95**, `isCollateralizationOf` **18**, `ex:servicedBy` **3** | — | public |
| Loan-level privacy constraints | Fluree | `ex:LoanLevelPrivacyConstraint` **4**, each `minimumGranularity: cohort` | — | synthetic — internal |
| Prospectus + servicer documents | MongoDB `fibo_v2` | `document` where `document_id ^abs-` | **39** (3 prospectuses + 36 servicer reports) | public |
| Passages | MongoDB | `passage` where `passage_id ^abs-` | **1,882**, each with `sha256`, offsets, and a **1536-dim `text-embedding-3-small` embedding** | public/derived |
| Trigger passage anchors | MongoDB | `trigger_anchor` | **10** — with quoted filed text and offsets | public |

**Departmental SQLite holds nothing for this rung** (checked: `covenant_tracker`,
`large_exposure_limit_workbook`, `prospect_note`, `restricted_list`,
`risk_limit_workbook`, `sar_classification`, `syndicate_desk_tracker`). ABS is a
**three-store** product, not four.

### C.2 Correlation key

`deal_id` → CIK and depositor CIK; loans key to `(deal_id, period)`; tranches
key to `tranche_id` with `cusip` present on only 4 of 18; triggers key to
`abs-trigger-{deal_id}-{kind}`; anchors key `trigger_id` → `passage_id` →
`document_id`.

### C.3 The data traps, each with the binding chosen

**Trap 1 — the amended trigger is the one threshold with no passage anchor.**
The full statement, and the ruling it needs, is §F.4.

**Trap 2 — ABS-15G is a depositor-level filing, and this is load-bearing.**
All 8 rows in `abs_repurchase` carry `deal_id = NULL`; the two depositor CIKs
(1383094 Santander, 1131131 Toyota) each filed for the whole shelf. **A deal
with no repurchases has no filing of its own to be absent** — it is simply not
named in a filing that exists. **Binding: no join from deal to repurchase is
invented.** Repurchase activity is served as a depositor-scoped member with
its filings named and an explicit statement that per-deal attribution is not
available from the filing. This is the same discipline CP-15 applied to the
LEI-keyed refresh register: *a stated absence, never a dropped member, never an
invented join.*

**Trap 3 — one trigger has a unit but no value.**
`abs-trigger-TAOT-2022-B-yield_supplement` carries `thresholdUnit: amount`,
a label, a `validFrom` and a passage anchor, and **no `thresholdValue` and no
`thresholdComponent`**. Its threshold is a formula in the prospectus, not a
number. **Binding: proximity is uncomputable for it and is served as a finding
naming why, never as `0` and never dropped.** A finding is not an absence.

**Trap 4 — two triggers carry two threshold components.**
`SDART-2022-6-overcollateralization` has components `1.50` and `22.80` with
`thresholdValue 22.80`; `SDART-2024-1-overcollateralization` has `15.20` and
`2.00` with `thresholdValue 15.20`. The threshold is the greater of two tests.
**Binding: components are carried; the product does not silently reduce a
two-component test to one number without saying which it used.**

**Trap 5 — three authorities can state the ceiling and they must not drift.**
The ceiling exists in Postgres (`abs_granularity_entitlement`, per principal),
in Fluree (`ex:LoanLevelPrivacyConstraint`, per *field*, all at
`minimumGranularity: cohort`), and will exist in the Control Plane as the
`PolicyConstraint` the SDK actually enforces. **Binding: the Control Plane
artifact is the single authority the product enforces; the estate rows are
read as evidence and the product states which authority bound it.** A gate
asserts the enforced ceiling equals the estate's declared ceiling for that
principal, so drift is a red build rather than a silent divergence.

**Trap 6 — the estate's vector half is ready and the SDK's is not.**
All **1,882** ABS passages carry a 1536-dimension `text-embedding-3-small`
embedding. This is the **first rung where the estate can support the vector
path** — cp-19's 72 advisory passages carried none, and the blocker there was
recorded as the estate. Here the blocker is entirely the SDK side: no embedder
ships and the builder wires no vector substrate. **Binding: the lexical
operator is used, as at cp-19, and the existing backlog item is updated with
this second and differently-shaped piece of evidence.** No SDK work is proposed
for it here.

**Trap 7 — monthly data against a 24-hour TTL.** Servicer reporting is monthly;
the 12 periods end `2026-06`. A 24 h TTL at any demonstration instant after
`2026-07` reads every product as expired. **Binding: an illustrative
calibration under `D-IMPL-323`, disclosed in the artifact that declares it, in
the README and here** — with the standing wording, and with the decay and the
decision instant left real.

**Trap 8 — provisional FIBO modules.** `TriggerEvent`, `specifiesTrigger` and
`TrancheType` live in modules carrying `hasMaturityLevel = Provisional` and are
**excluded from FIBO's single-file Release load**. A consumer who loads
QuickFIBOProd and queries these IRIs gets **zero rows and no error**. The
estate has them materialized (11 `TriggerEvent`, 10 `specifiesTrigger`), so this
does not block the rung; it is disclosed because the silent-zero failure mode is
exactly the kind this project refuses to leave undocumented.

---

## D · Assembly recipe

### D.1 Client call

```
GET /context-products/cib/abs-surveillance/SDART-2022-6
      ?intent=trigger-monitoring&granularity=cohort&trigger_proximity=true&as_of=2026-06-30
```

### D.2 Operator step table

| # | Step | Store | SDK operator category |
|---|---|---|---|
| 1 | Resolve the deal and its reporting period for `as_of` | Postgres | — (acquisition) |
| 2 | Bind entitlement, intent obligations and the **granularity ceiling** | Control Plane + estate evidence | Policy |
| 3 | Walk `specifiesTrigger` / `isSubordinatedTo` / `isCollateralizedBy` at the ledger point for `as_of`, **following `supersededBy` to the definition in force** | Fluree | Traversal + Temporal |
| 4 | Retrieve prospectus and servicer passages supporting each structural claim, within the step-2 allowlist | MongoDB | Similarity |
| 5 | Resolve pool performance **at the effective granularity**, aggregating or sampling *in acquisition* | Postgres | — (acquisition) |
| 6 | Compute pool performance, tranche coverage, trigger proximity, benchmark comparison | in-process | — (Π) |
| 7 | Assemble, govern, assess, gate | — | — |

Six spec operators map to three SDK operator keys. The **served** plan is the
fact of record.

### D.3 Step detail — where the new things sit

**Step 2 is where the rung's headline lives.** The ceiling is resolved from a
`PolicyConstraint` whose `ConstraintApplicability.perspective_role` selects it
for the caller's role and whose `allowed_set` folds to membership. A requested
granularity above that set is refused `not-in-allowed-set` with the bound
attached (`src/ccf/products/constraints.py`, `ConstraintRefusal.reason`).

**Step 3 is where the amendment decides the answer.** SDART-2022-6's delinquency
trigger was asserted `2022-09-14` at **24.00 %** and superseded by an amendment
valid from **2025-11-01** at **13.50 %**. The amendment is reachable in exactly
one way — `specifiesTrigger` from the deal to the original, then `supersededBy`
from the original to the amendment. There is no direct edge from the deal to the
amendment (verified: the amendment node has exactly **one** incoming triple, the
`supersededBy`). **No join is invented; the two-hop walk is the estate's own
structure.**

Two instants make this observable, both real periods:

| Instant | In force | Why |
|---|---|---|
| `2025-09-30` | **24.00 %** (original) | before the amendment's `validFrom` |
| `2026-06-30` | **13.50 %** (amendment) | after it |

And the assertion clock is separately observable: the amendment was **asserted**
`2026-01-11` but is **valid from** `2025-11-01`. A question about period
`2025-11` asked *as the bank knew it on 2025-12-01* yields 24.00; the same
question asked today yields 13.50. That is cp-08's two clocks, on a second
rung.

**Step 5 is the fan-out boundary.** At `deal`, `tranche` or `cohort` the
pre-aggregated rows are read — 1, 6 or 4 rows, 2–4 shared blocks. At `loan` the
rows are streamed and **the full pool is never materialized**; where
`loan_sample` is given the sample is stratified across cohorts, because ABS-EE
files are ordered in ways that make a prefix unrepresentative.

### D.4 Determinism class

Fully algorithmic. No LLM inference anywhere in the path. Proximity, coverage
and benchmark comparison are arithmetic over acquired claims.

### D.5 Replay statement

The product replays from its record and the stores with no second producer
call: `graph_snapshot_at` fixes the ledger `t` that selected the trigger
definition, `policy_version` fixes the ceiling that bounded the granularity,
and the effective request fixes `as_of`, `granularity` and `loan_sample`.

### D.6 Validation gates (contract level)

Empty-operator guard · lineage strict equality · TTL bounds · **passage
resolvability** — every anchor's `passage_id` resolves and its stored `sha256`
re-hashes · **trigger anchoring** — the two invariants of §F.4.0, separately · **granularity disclosure** — the
served product states its effective granularity *and* the ceiling in force.

---

## E · Volatility, debt and materialization

### E.1 Half-life

| Signal class | `λ_c` | Basis |
|---|---|---|
| Loan-level performance | ~30 days | monthly servicer cadence |
| Tranche balances | ~30 days | |
| Trigger definitions | **no decay — supersede-only** | fixed at issuance unless amended |
| Prospectus text | **no decay — supersede-only** | immutable once filed |
| Vintage benchmarks | ~90 days | recomputed as peer deals report |

**`D-IMPL-332` applies and must be respected**: a class declaring
`decay_basis: valid-from` **refuses** an undated claim. Trigger definitions and
prospectus text are *standing state*, not dated events, and take a
`supersede-only` decay exactly as cp-18's `maturity_wall` did. Getting this
wrong is a refusal at serve time, not a silent staleness.

### E.2 Debt

`D_c = 1 − F·C·S` over what was assembled. Completeness counts the required
classes; a class the privacy ceiling excluded is **still required**, because the
product genuinely is less complete for a principal who may not see it — saying
otherwise hides the cost of the entitlement rather than measuring it (cp-15's
rule, reused).

### E.3 Materialization

The estate states the posture: `deal`, `tranche`, `cohort` **materialized** on a
30-day refresh; `loan` **on-demand**, never materialized. The split *is* the
cost strategy.

### E.4 Supersession

New 10-D distribution report; ABS-15G repurchase activity; trigger-definition
amendment; monthly ABS-EE filing.

---

## F · Source binding and readiness

### F.1 Element readiness

Every element in §C.1 is present and measured. **No element is missing.** The
one shortfall is not a missing element but a missing *attribute* on one node,
and it is §F.4.

### F.2 Every `[TBC]`, with an owner

| # | Item | Owner |
|---|---|---|
| 1 | **The unanchored amendment** (§F.4) | **Dave** — blocking |
| 2 | Three principals rather than the source spec's one | Dave — recommended yes; costs no new mechanism |
| 3 | The demonstration instants `2025-09-30` / `2026-06-30` | Dave — recommended as stated |
| 4 | The illustrative TTL calibration (trap 7) | Dave — under `D-IMPL-323` |
| 5 | `Servicer` / `servicedBy` / `SourceDocument` IRIs | `ccf-dataprep`, non-blocking; `ex:` provisionally |

### F.3 Symbols named in this document, verified against `src/` on 2026-09-21

`src/ccf/products/request.py::ArgumentDomain` (with `members`) ·
`src/ccf/controlplane/artifacts.py::PolicyConstraint` ·
`src/ccf/controlplane/artifacts.py::ConstraintApplicability` (with
`perspective_role`) · `src/ccf/controlplane/artifacts.py::RequestBoundParameter` ·
`src/ccf/products/constraints.py` (the `allowed_set` → membership fold and the
`not-in-allowed-set` refusal reason) · `src/ccf/products/expiry.py::resolve_ttl_anchor` ·
`src/ccf/contracts/claims.py::PassageAnchor` · `src/ccf/products/resolver.py`
(`decision_instant_parameter`). Every one resolves. None is invented.

### F.4 — RULED 2026-09-21: ROUTE B. The amended trigger is served, marked unanchored

> **Dave's ruling, verbatim in substance.** *Accept §F.4 Route B.* The engineered
> amended threshold **remains part of the served product**, represented
> explicitly as `anchored: false`, with provenance/source classification
> `synthetic` / engineered, and **a finding naming the missing public anchor**.
> *Do not imply that a prospectus passage exists.* The anchoring invariant is
> **split in two**: (1) every publicly sourced threshold has a prospectus
> passage anchor; (2) every threshold without a public anchor is explicitly
> named as unanchored in the product. *The amended SDART-2022-6 threshold must
> remain observable at the appropriate `as_of`; do not refuse it merely because
> the engineered amendment has no filed passage.* **No minted prospectus text.**

**What this settles, and what it forecloses.** Route A (refuse) and Route C
(mint a passage) are both closed. The product serves the amended threshold, and
the honesty is carried by the marking and the finding rather than by a refusal.
The two invariants are separately gated — `ABS-G06` and `ABS-G07` — precisely
so that neither can be satisfied by the other: an implementation that anchored
everything would fail `ABS-G07` for having nothing to name, and one that
named everything unanchored would fail `ABS-G06`.

**The measurement that forced the ruling follows.**

**The measurement.** Of the estate's 11 `TriggerEvent` nodes, **10 carry a
`passageAnchor` and one does not**: `abs-trigger-SDART-2022-6-delinquency-amendment`.
MongoDB's `trigger_anchor` collection confirms it from the other side — it holds
exactly **10** documents. The unanchored node is also the only one whose
provenance is `synthetic — engineered` rather than `public`, and the reason is
honest: the amendment was engineered so that as-of evaluation would matter, and
**there is no filed prospectus text behind an amendment that was never filed.**

**Why this is the whole rung and not a detail.** The source specification's
validation gate says *every trigger threshold must carry a prospectus passage
anchor* — because *a threshold asserted without a passage anchor is a number
nobody can defend to a committee*. But the amendment is the only thing that
makes the as-of question real. So at `as_of ≥ 2025-11-01` on SDART-2022-6, the
in-force delinquency threshold is **13.50 %** and it has no passage behind it.
The anchoring gate as written would refuse the product **exactly when the
rung's headline capability becomes observable.**

**The three routes, with consequences.**

| | Route | What the product does | Cost |
|---|---|---|---|
| **A** | **Refuse the unanchored threshold by name** | `as_of ≥ 2025-11-01` on this deal yields a governed refusal naming the unanchored trigger | The rung's headline as-of demonstration becomes a refusal, not a served comparison. Honest, and a governed refusal *is* a successful SDK demonstration — but it makes the amendment unobservable in a served payload. |
| **B** | **Serve it, marked** *(recommended)* | The amended threshold is served with `anchored: false`, its provenance `synthetic — engineered`, and a finding naming that it carries no filed text; the anchoring gate is recast to *every **publicly-sourced** threshold carries an anchor, and every unanchored threshold is named as a finding* | The gate stops being "all anchored" and becomes two assertions. Keeps the as-of comparison observable and keeps the evidence honest. Same shape as cp-15's *a finding is not an absence*. |
| **C** | Ask `ccf-dataprep` to mint a passage for the amendment | Everything anchors | **Rejected in this document**: it would manufacture filed text for an event that was never filed. That is inventing evidence, which is worse than the gap. |

**RULED: B**, 2026-09-21. The recommendation stood. Routes A and C are closed.

**What must not happen**: the amendment must not be quietly treated as
anchored, and **no passage may be minted for it**.

#### F.4.0 The two anchoring invariants, as ruled

| | Invariant | Gate |
|---|---|---|
| **1** | Every **publicly sourced** threshold has a prospectus passage anchor whose stored `sha256` re-hashes | `ABS-G06` |
| **2** | Every threshold **without** a public anchor is explicitly named as unanchored **in the product** | `ABS-G07` |

The served representation of an unanchored threshold carries, together:
`anchored: false`; a source classification of `synthetic` / engineered; and a
finding naming the missing public anchor. **Nothing in the payload may imply a
prospectus passage exists** — no empty anchor object, no null `passage_id`, no
placeholder document reference. The absence is stated, not encoded as a blank.

### F.4.1 The decision instant — residual `341-1`, live for the first time

`as_of` is both the reporting period and the **decision instant**. Acquisition
must be bounded at that instant rather than at request time, or a product asked
about `2025-09` acquires `2026-06` rows and computes a proximity nobody asked
for. The rule is real and is **stated nowhere public** — Gate 0 records exactly
that. It is carried here as friction and as gate `ABS-G05`, and no SDK work is
proposed for it.

### F.4.2 The vacuity risk on the disclosure gate, stated before it bites

Under route A or B, **nothing ever lowers a granularity** — a request above the
ceiling is refused, not narrowed. So the source specification's gate *"if policy
lowered the granularity, say so"* would be **vacuously true forever**, which is
the shape cp-08 taught us to refuse (*config nobody reads is documentation, not
control*). The recast gate is therefore a **positive** assertion: the served
product states the ceiling in force, and `ABS-G10` asserts that stated ceiling
equals the constraint the SDK actually resolved — so a sabotage that hard-codes
the ceiling reddens it. Stated here so it is designed, not discovered at close.

---

## G · Operate and govern

### G.1 Product gates — 22 (Route B splits the anchoring invariant into `ABS-G06`/`ABS-G07`)

| id | What it asserts | Red when |
|---|---|---|
| `ABS-G01` | The served operator plan runs Policy before Similarity | the categories are reordered |
| `ABS-G02` | The deal, its 6 tranches and their `seniority_rank` ordering are served from the graph, not from a constant | the ordering is hard-coded |
| `ABS-G03` | At `as_of 2025-09-30` the in-force delinquency threshold is the **original**; at `2026-06-30` it is the **amendment** | the ledger point is ignored |
| `ABS-G04` | The amendment is reached by `specifiesTrigger` then `supersededBy` — never by a name-match join | a string join is substituted |
| `ABS-G05` | Acquisition is bounded at the **decision instant**: a question at `2025-09-30` acquires no `2026` loan period | the bound is dropped (residual 341-1) |
| `ABS-G06` | **Anchoring invariant 1** — every **publicly sourced** threshold resolves to a passage whose stored `sha256` re-hashes | an anchor is broken or a hash drifts |
| `ABS-G07` | **Anchoring invariant 2** — every threshold **without** a public anchor is named in the product as `anchored: false`, classified `synthetic`/engineered, with a finding naming the missing public anchor; and **nothing in the payload implies a passage exists** | the amendment is served as anchored, silently dropped, or given a blank/placeholder anchor |
| `ABS-G08` | A granularity outside `ArgumentDomain.members` is a **request-validity** refusal | the domain is widened |
| `ABS-G09` | A granularity inside the domain but above the role ceiling is refused **`not-in-allowed-set` with the bound attached** | the ceiling is dropped, or the value is silently lowered |
| `ABS-G10` | **Positively**: the ceiling **stated in the payload** equals the `PolicyConstraint` actually resolved for that principal — asserted for all three principals, so it cannot pass by coincidence | the stated ceiling is hard-coded, or derived from anything but the resolved constraint (§F.4.2) |
| `ABS-G11` | The enforced ceiling equals the estate's declared ceiling for that principal | the three authorities drift (trap 5) |
| `ABS-G12` | Three principals, one door, three different effective granularities from the same question | one principal's answer is served to another |
| `ABS-G13` | **Load-bearing.** The complete source population is never materialized: **records scanned** and **blocks scanned** are measured at the acquisition seam, and the acquired record count tracks the *answer*, not the *population* — at `loan` it is bounded by the sample, at the aggregate rungs by the cohort count | the acquired count tracks the population, or the aggregation moves out of acquisition |
| `ABS-G14` | `loan_sample` draws **stratified across cohorts**, not a prefix | a prefix is taken |
| `ABS-G15` | Cost is served as a **relational** fact keyed on blocks — the three aggregate rungs indistinguishable and all ≪ `loan` — with the measured counts carried as stamped evidence rather than as product constants. **Timing is never a gate.** | a time-keyed assertion is substituted, or a measured count becomes a threshold (§A.2) |
| `ABS-G16` | The yield-supplement trigger is served as a **finding naming why proximity is uncomputable** | it is served as `0` or dropped (trap 3) |
| `ABS-G17` | A two-component threshold carries both components and names which bound the test | one component is silently discarded (trap 4) |
| `ABS-G18` | Repurchase activity is **depositor-scoped with a stated absence** of per-deal attribution | a deal↔filing join is invented (trap 2) |
| `ABS-G19` | **Two observation types.** The standing classes (deal, tranche, trigger, anchor) are minted `supersede-only` and carry no observed time; the dated ones (cohort, loan, benchmark, repurchase) declare `decay_basis: valid-from` and carry their day — so an undated claim in a *dated* class is refused, which is what `D-IMPL-332` actually says | a dated class's basis is moved off `valid-from`, collapsing the distinction |
| `ABS-G20` | TTL is anchored on the servicer report's period end, not on request time | the anchor moves to `asked_at` |
| `ABS-G21` | Replay reconstructs the served product from the record and the stores with no second producer call | any input is re-derived rather than resolved |
| `ABS-G22` | **Existence is not an oracle.** A deal that does not exist and a real deal with no reporting period at the instant are refused *indistinguishably*; a subject with evidence is served, so the gate is not vacuous | the two refusals differ by subject |

**Two of these are at risk of being unavailable** and are named now rather than
discovered at close: `ABS-G01` may be **inexpressible** because `CATEGORY_ORDER`
fixes the executed order in the SDK's planner (it was unavailable on rungs 15
and 19 for exactly that reason), and `ABS-G13` depends on the acquisition seam
exposing an envelope count the test can read. Both will be reported as
`unavailable` with their guard named if they cannot be reddened — never quietly
swapped for something easier.

### G.2 What this rung measures for the backlog

The A2 envelope review is **closed at B** and is not reopened. What this rung
measures instead: the block-keyed cost assertion (new); the granularity-ceiling
plumbing as a *second* instance of a role-applicable `allowed_set` (the first
was predicted at this rung by Gate 0, so this is the first live one); the
undocumented decision-instant rule (341-1); and the vector-path evidence from
trap 6.

---

## Gate 1 summary

- **Genuinely new:** three shapes (§0.2) — a shape-and-cost parameter under a
  role ceiling; assembly that must not materialize its population; cost stated
  back to the caller. **No new SDK capability is required**, verified symbol by
  symbol.
- **Estate:** ready on all three stores; 1,322,453 loan rows, 11 triggers, 10
  anchors, 1,882 passages, 3 principals with 3 ceilings. Eight traps recorded
  with bindings.
- **Gates:** 22 declared and executing; **21 observed RED** under their own
  sabotage, **1 `unavailable`** with its guard named (`ABS-G01` — `CATEGORY_ORDER`
  fixes the executed order, so the forbidden ordering is inexpressible).
- **Ruled:** §F.4 — **Route B**, 2026-09-21. The amendment is served marked
  `anchored: false` with a finding; the anchoring invariant is split in two
  (`ABS-G06`, `ABS-G07`); no prospectus text is minted.
- **Authorized:** Gate 2, minimal build on the existing SDK. No new SDK
  abstraction, no `D-IMPL` id spent.

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

Path: `05-reference/02-context-product-producer/examples/CP16_ABS_SECURITIZATION_SURVEILLANCE.md`

``````text
# CP-16 — ABS / Securitization Surveillance

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-16-abs-securitization-surveillance/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP16_ABS_SECURITIZATION_SURVEILLANCE_ANALYSIS.md) · [HTML reading edition](CP16_ABS_SECURITIZATION_SURVEILLANCE_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-16-abs-securitization-surveillance/README.md`  
**Qualified specification:** `examples/cp-16-abs-securitization-surveillance/spec/CP-SPEC-016_ABS_Securitization_Surveillance.md`  
**Qualified source:** `examples/cp-16-abs-securitization-surveillance`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-16-abs-securitization-surveillance/spec/CP-SPEC-016_ABS_Securitization_Surveillance.md`

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

Introduces population-scale acquisition where a request parameter (`granularity`) changes payload shape, cost, and the caller's permitted ceiling. It proves that large loan populations must be bounded during acquisition—not materialized first and trimmed later.

## The question

> What surveillance context should be assembled for this securitization at the requested granularity, and is that granularity permitted and affordable for this principal?

## What to understand before you run it

- `granularity` is simultaneously a semantic shape lever, a cost lever and a governed entitlement ceiling.
- Loan-level scale makes acquisition pushdown mandatory.
- Cost is expressed in deterministic work units/records, not wall-clock timing.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
export CCF_CP_16_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_16_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_16_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_16_FLUREE_LEDGER='fibo-v2'
export CCF_CP_16_MONGO_URI='mongodb://<read-only-user>:<password>@<host>:<port>/?authSource=<auth-database>'
export CCF_CP_16_MONGO_DB='fibo_v2'
export CCF_CP_16_TOKEN_DESK='<credential>'
export CCF_CP_16_TOKEN_RISK='<credential>'
export CCF_CP_16_TOKEN_REPORTING='<credential>'
export CCF_CP_16_TOKEN_UNGRANTED='<credential>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-16-abs-securitization-surveillance/spec/` | Granularity/cost/role-ceiling contract and source limits. |
| `examples/cp-16-abs-securitization-surveillance/ccf_config.yaml` | Request domains, product/role constraints and Debt settings. |
| `examples/cp-16-abs-securitization-surveillance/ccf_environment.yaml` | Source and credential variable names. |
| `examples/cp-16-abs-securitization-surveillance/artifacts/` | Source vocabulary, perspectives, question and gates. |
| `examples/cp-16-abs-securitization-surveillance/acquisition.py` | Population-scale bounded reads/aggregation. |
| `examples/cp-16-abs-securitization-surveillance/projection.py` | Granularity-dependent payload. |
| `examples/cp-16-abs-securitization-surveillance/deployment.py` | Assessment and request/policy bindings. |
| `examples/cp-16-abs-securitization-surveillance/produce.py` | Paved-road product. |
| `examples/cp-16-abs-securitization-surveillance/run.py` | Granularity/principal variations. |

## Run it

```bash
make venv
make -s example-cp-16
make -s example-cp-16 GRANULARITY="--granularity cohort" PRINCIPAL="--principal PRIN-CRR-002"
make -s example-cp-16 GRANULARITY="--granularity loan" LOAN_SAMPLE="--loan-sample 300"
make -s example-cp-16 AS_OF="--as-of 2025-09-30T00:00:00+00:00" ASKED_AT="--asked-at 2025-09-30T00:00:00+00:00"
.venv/bin/python examples/cp-16-abs-securitization-surveillance/run.py --door
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- Different principals/granularities receive materially different product shapes.
- A request above the principal's granularity ceiling is refused by name rather than silently reduced.
- Loan-level path samples/aggregates during acquisition, before claims are minted.
- The product reports the deterministic cost of the caller's chosen question.

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
| Cohort view | `make -s example-cp-16 GRANULARITY="--granularity cohort" PRINCIPAL="--principal PRIN-CRR-002"` | Role-conditioned coarser product. |
| Loan sample | `make -s example-cp-16 GRANULARITY="--granularity loan" LOAN_SAMPLE="--loan-sample 300"` | Loan-level shape and higher deterministic cost. |
| Historical instant | `make -s example-cp-16 AS_OF="--as-of 2025-09-30T00:00:00+00:00" ASKED_AT="--asked-at 2025-09-30T00:00:00+00:00"` | Decision-time bounded acquisition changes evidence. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_16_granularity.py tests/examples/test_cp_16_surveillance.py tests/examples/test_cp_16_sabotage.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- Request shape/cost/entitlement can be the same governed axis.
- Large populations can be bounded before materialization.
- Cost disclosure can be deterministic and product-visible.

## What it does not prove

- Production securitization surveillance thresholds or cost bands.
- That all loan-level data can be materialized safely in memory.

## Spec → code lesson for Cowork

Use CP-16 when a request parameter controls data volume/shape. Cowork must implement the bound at acquisition and enforce the caller's ceiling before expensive work, not post-filter a fully materialized population.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.
``````

</details>

