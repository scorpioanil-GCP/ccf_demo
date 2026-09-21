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
acquisition seam and gated (`ABS-G12`). A rung that merely *says* it streams has
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
| Is every gate expressible as a test that can go red? | **Yes, with one named risk** — §G.1, and the vacuity risk on `ABS-G09` is stated rather than discovered later. |

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
| **Declared gates** | §G.1 — **21 gates**, `ABS-G01`..`ABS-G20` plus `ABS-G06b` |

### B.2 Departures from the source specification, each reasoned

| Source says | This document says | Why |
|---|---|---|
| "Single role at this tier" | Three roles | The estate carries three ceilings; one role makes the ceiling unobservable (§A). |
| `operators_invoked: [Resolve, Policy, TemporalTraversal, Similarity, Enrich, Aggregate]` — six | The SDK's **served** operator plan, three keys | Six spec operators map to three SDK operator keys; the served plan is the fact, the spec's list is vocabulary. Recorded as friction, not repaired (Gate 0). |
| "if policy lowered the granularity, say so" | A request above the ceiling is **refused by name**; a served product states its effective granularity **and the ceiling in force**, and `ABS-G09` proves that stated ceiling equals the resolved constraint | The constraint layer refuses out-of-bound values and never narrows them (`D-IMPL-251`); a vacuous assertion is refused by ruling. §F.4.2. |
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
and the `allowed_set` fold. **No new SDK abstraction.** `ABS-G09` must
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
policy refusal carrying the bound. **They are separate gates** (`ABS-G07`,
`ABS-G08`).

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
The two invariants are separately gated — `ABS-G06` and `ABS-G06b` — precisely
so that neither can be satisfied by the other: an implementation that anchored
everything would fail `ABS-G06b` for having nothing to name, and one that
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
| **2** | Every threshold **without** a public anchor is explicitly named as unanchored **in the product** | `ABS-G06b` |

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
product states the ceiling in force, and `ABS-G09` asserts that stated ceiling
equals the constraint the SDK actually resolved — so a sabotage that hard-codes
the ceiling reddens it. Stated here so it is designed, not discovered at close.

---

## G · Operate and govern

### G.1 Intended product gates — 21 (Route B splits the anchoring invariant)

| id | What it asserts | Red when |
|---|---|---|
| `ABS-G01` | The served operator plan runs Policy before Similarity | the categories are reordered |
| `ABS-G02` | The deal, its 6 tranches and their `seniority_rank` ordering are served from the graph, not from a constant | the ordering is hard-coded |
| `ABS-G03` | At `as_of 2025-09-30` the in-force delinquency threshold is the **original**; at `2026-06-30` it is the **amendment** | the ledger point is ignored |
| `ABS-G04` | The amendment is reached by `specifiesTrigger` then `supersededBy` — never by a name-match join | a string join is substituted |
| `ABS-G05` | Acquisition is bounded at the **decision instant**: a question at `2025-09-30` acquires no `2026` loan period | the bound is dropped (residual 341-1) |
| `ABS-G06` | **Anchoring invariant 1** — every **publicly sourced** threshold resolves to a passage whose stored `sha256` re-hashes | an anchor is broken or a hash drifts |
| `ABS-G06b` | **Anchoring invariant 2** — every threshold **without** a public anchor is named in the product as `anchored: false`, classified `synthetic`/engineered, with a finding naming the missing public anchor; and **nothing in the payload implies a passage exists** | the amendment is served as anchored, silently dropped, or given a blank/placeholder anchor |
| `ABS-G07` | A granularity outside `ArgumentDomain.members` is a **request-validity** refusal | the domain is widened |
| `ABS-G08` | A granularity inside the domain but above the role ceiling is refused **`not-in-allowed-set` with the bound attached** | the ceiling is dropped, or the value is silently lowered |
| `ABS-G09` | **Positively**: the ceiling **stated in the payload** equals the `PolicyConstraint` actually resolved for that principal — asserted for all three principals, so it cannot pass by coincidence | the stated ceiling is hard-coded, or derived from anything but the resolved constraint (§F.4.2) |
| `ABS-G10` | The enforced ceiling equals the estate's declared ceiling for that principal | the three authorities drift (trap 5) |
| `ABS-G11` | Three principals, one door, three different effective granularities from the same question | one principal's answer is served to another |
| `ABS-G12` | **Load-bearing.** The complete source population is never materialized: **records scanned** and **blocks scanned** are measured at the acquisition seam, and the acquired record count tracks the *answer*, not the *population* — at `loan` it is bounded by the sample, at the aggregate rungs by the cohort count | the acquired count tracks the population, or the aggregation moves out of acquisition |
| `ABS-G13` | `loan_sample` draws **stratified across cohorts**, not a prefix | a prefix is taken |
| `ABS-G14` | Cost is served as a **relational** fact keyed on blocks — the three aggregate rungs indistinguishable and all ≪ `loan` — with the measured counts carried as stamped evidence rather than as product constants. **Timing is never a gate.** | a time-keyed assertion is substituted, or a measured count becomes a threshold (§A.2) |
| `ABS-G15` | The yield-supplement trigger is served as a **finding naming why proximity is uncomputable** | it is served as `0` or dropped (trap 3) |
| `ABS-G16` | A two-component threshold carries both components and names which bound the test | one component is silently discarded (trap 4) |
| `ABS-G17` | Repurchase activity is **depositor-scoped with a stated absence** of per-deal attribution | a deal↔filing join is invented (trap 2) |
| `ABS-G18` | Trigger definitions and prospectus text are minted `supersede-only`; an undated claim in those classes is refused `MissingDecayInstant` | a decaying basis is declared (`D-IMPL-332`) |
| `ABS-G19` | TTL is anchored on the servicer report's period end, not on request time | the anchor moves to `asked_at` |
| `ABS-G20` | Replay reconstructs the served product from the record and the stores with no second producer call | any input is re-derived rather than resolved |

**Two of these are at risk of being unavailable** and are named now rather than
discovered at close: `ABS-G01` may be **inexpressible** because `CATEGORY_ORDER`
fixes the executed order in the SDK's planner (it was unavailable on rungs 15
and 19 for exactly that reason), and `ABS-G12` depends on the acquisition seam
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
- **Intended gates:** 21, two flagged as at risk of `unavailable` with their
  guards named.
- **Ruled:** §F.4 — **Route B**, 2026-09-21. The amendment is served marked
  `anchored: false` with a finding; the anchoring invariant is split in two
  (`ABS-G06`, `ABS-G06b`); no prospectus text is minted.
- **Authorized:** Gate 2, minimal build on the existing SDK. No new SDK
  abstraction, no `D-IMPL` id spent.
