<!--
  CP-SPEC-020 — Syndicated Lending Co-Lender.
  Authored to Context Product Specification Standard v0.3 before any code
  exists, per `D-IMPL-319` and the rule *specs come before code*.

  Source: vault `context-products/syndicated-lending-co-lender`
  (`cb.syndicate-co-lender.v1`, standard q019, generated 2026-08-15) and
  `docs/GATE-0-COVERAGE-CP15-24.md` §4.1/§4.2 row CP-20.

  Peer estate: vault `contrib/ccf-dataprep/co-lender-peer-estate-as-measured`
  (measurement, ccf-dataprep, 2026-09-19), independently re-measured live
  against both fabrics on 2026-09-22 and reproduced exactly.

  GATE 1 ACCEPTED 2026-09-22 AS BUCKET 1. Dave's rulings on `Q1`, `Q2` and the
  three `Q3` amendments are folded into this document BEFORE any
  implementation, per the instruction. One question remains owed (§F.4 `Q4`).
-->

# Syndicated Lending Co-Lender — Context Product Specification

**Rung 20 · Postgres + Fluree + a second organization's fabric · `cb.syndicate-co-lender`**

**Status: GATE 1 ACCEPTED — BUCKET 1, 2026-09-22. No SDK or runtime capability
is missing. `D-IMPL-346` remains unspent. Build is NOT yet authorized: `Q4`
(§F.4) is owed before Gate 2.**

---

## 0 · What this document is

The question this document exists to answer:

> **What does cross-organizational federation require that CP-01 through
> CP-24 have not already proven?**

**The measured answer is: nothing.** CP-20 is a **bucket-1** rung under the
six-bucket rule (`docs/DECISIONS.md`, Dave, 2026-09-19). *"Another
organization"* is domain framing over cross-tenant governed child admission
that `D-IMPL-340` shipped and rung 14 proved. **CP-20's contribution is an
estate that makes federation properties observable — not a new SDK
mechanism.**

### 0.1 Already proven — reused unchanged, and NOT reopened

| # | Mechanism | Proven at | Reused here as |
|---|---|---|---|
| 1 | The paved producer road, `open_product(...)` with a named `plan_factory` | `D-IMPL-343`; rungs 13–19, 21, 23, 24 | both the peer producer and the local composite |
| 2 | **A composite admitting a child governed under ANOTHER TENANT**, held to the consumer's own registration | **`D-IMPL-340`**, `D-GATE-340`; rung 14 | the federated co-lender child. Measured precedent: `examples/cp-14-credit-memo-context/ccf_config.yaml` declares `tenant_id: cp-14-demo` and registers producers under `cp-03-canonical-demo`, `cp-04-canonical-demo` and `cp-05-demo` |
| 3 | The **TTL floor** as a property of the shipped path — `composite.py` calls `compose_expiry(constituent_validities=[child.expires_at …])` | `D-IMPL-31`, `D-IMPL-104` | the composite is never labeled fresher than an admitted peer child (§G.1 `CLD-G05`) |
| 4 | **Provenance separation already carried** — `eligibility_basis` as a closed three-value vocabulary (`local-register` · `producer-attested` · `provider-controls`) on the replay record's child rows, beside `producer_id`, `producer_tenant`, `question_ref`, `producer_replay_ref` | `D-IMPL-336` Am. 5, `D-IMPL-337`, `D-IMPL-342` | every claim's local-reconstructible / remote-attested marking is **derived** from it (§G.1 `CLD-G15`) |
| 5 | A **governed refusal** by name, as data, with a replay reference — never a raise, never a product | cp-05 onward | the unattested peer declaration (§G.1 `CLD-G06`) |
| 6 | **Optional means optional ABSENCE, not optional governance** — a refused child refuses the composite even in an optional slot | **`D-IMPL-336` F1** | `CLD-G07`, and it is load-bearing |
| 7 | The **zero-admitted-children** outcome is legal: the parent's own terms stand, `expires_at` is `None`, lineage is the parent's own | `D-IMPL-336` Am. 5 (`composite.py`, the `if not admitted_children` branch) | `include_federated=false` needs **no** second local child (§F.4 note 2) |
| 8 | Credential-derived policy envelope at the acquisition seam | A2 **closed at B** by `D-GATE-cp-19`; rungs 13, 15, 17, 18, 19 | the bilateral disclosure envelope. **Not reopened** |
| 9 | Several credentialed principals at one standard door, role-conditioned views | `D-IMPL-324`; rungs 15–19, 21, 23, 24 | `agent` / `participant` / `prospective` |
| 10 | Passage-level lineage to filed text | cp-13-canonical, cp-16, cp-19 | the amendment consent threshold, anchored to its EX-10 span |
| 11 | **Acquisition is not an operator** — source retrieval belongs at the acquisition seam, before any operator runs | **`LEX-F-03`** (rung 21, recorded rather than papered over) | the precedent that settles `Q3.3` (§0.5) |

### 0.2 What CP-20 actually adds

Not capability — **observability**. Three properties of federation that the
SDK has always implemented but no rung has ever been able to *watch*, because
no rung until now had a second fabric belonging to a second institution:

**(a) A negotiated envelope whose request and disclosure scopes genuinely
differ.** Two `DisclosureEnvelope` nodes exist and they are asymmetric in both
directions (§C.2). Until now every policy envelope on the ladder governed one
institution's view of its own material. This one governs *what one institution
may ask another for*, which is a different question and is refused in a
different place — before dispatch, not after admission.

**(b) Attestation as an admission condition on real data.** One of the three
peer declarations carries `attestation = NULL`. The SDK's answer is a governed
refusal; §A of `docs/EXAMPLE-EVALUATION-CRITERIA.md` names that a success.

**(c) Declared, not controlled, freshness and latency.** The peer states a TTL
and a latency the local fabric neither sets nor verifies, only honors. The
comparison is against a *declaration in the peer's data*, never a synthetic
network timeout.

### 0.3 Deliberately OUT of scope

- **The reverse direction** — the peer's agent at our door. Ruled out of the
  first proof (Dave, 2026-09-22). Several credentialed principals at one door
  is in any case proven by rung 17.
- **Route B peering.** `PeeringAdmissionGate` and the `LfA2AWire` path are not
  declarable on the paved config; Route A is the governed spine.
- **Any A2A requirement inherited from CP-22.** Rung 22 established
  agent-internal assembly and has **no bearing** on whether Context Products
  federate here.
- **`require_attestation` in any form.** See `Q3.1` (§0.5).
- **Minting an SDK operator.** See `Q3.3` (§0.5).
- **Retuning the peer estate** to make a refused child admissible.

### 0.4 The four-question build test (Standard v0.3)

| # | Question | Answer |
|---|---|---|
| 1 | Is the decision recurrent and consequential? | Yes — amendment consent, participation, workout. A wrong syndicate picture misprices a vote. |
| 2 | Does it need governed context no single store holds? | Yes, and **no single institution** holds it. The local fabric holds composition and our own position; the peer holds its own. |
| 3 | Would a `SELECT` do? | No. The answer's value is inseparable from *which* claims are ours and reconstructible and which are the peer's and merely attested. |
| 4 | Is the governance real? | Yes — a bilateral envelope, competition-law constraints, and an attestation condition that actually refuses. |

### 0.5 The Gate-1 rulings of 2026-09-22, folded

**`Q1` — RULED (b): SCOPES NAME PRODUCT CLASSES, NOT PAYLOAD FIELDS.**

> **Dave's ruling.** `requestScope` and `discloseScope` name product classes,
> not payload fields. **Therefore Citibank's `co-lender-position` product is
> not requestable under its current envelope. Do not retune the estate to make
> the Citi band admissible. The envelope refusal IS the demonstration.**

Consequence, stated once and honored throughout: **exactly one peer child is
ever admitted in this rung** — Bank of America's, on the facility `Q2` names.
Citibank's position is observable as estate evidence and is never a child.

**`G13` RECAST (same ruling).** There is no admitted Citi band child. The old
*"an admitted band member is represented without implying precision"* is
replaced by:

> **No served payload may contain a point estimate derived from a band
> declaration.** The band declaration may be observed as estate evidence; the
> product must never manufacture a dollar point estimate from it.

`CLD-G10` owns the Citi out-of-envelope request and its refusal. `CLD-G13`
owns precision honesty. **Citi's position is not to be made requestable merely
to give `CLD-G13` a positive payload fixture.**

**`Q2` — RULED: SPLIT THE FACILITIES.**

> **Dave's ruling.** Do not force one anchor to prove both an admitted peer
> observation and an unattested governed refusal. **`FAC-A4A5EE`** — unattested
> remote declaration, the `CLD-G06`/`CLD-G07` governed-refusal path.
> **`FAC-6F4065`** — attested peer facility, the amendment-consent /
> admitted-peer path. Two separate asks against two facilities. **The
> unattested facility must remain refused. Do not weaken attestation to expose
> the vote.**

**`Q3.1` — `require_attestation` IS REMOVED.** It does not appear in the
request surface (§B.3), in the SDK, or in the example. It is not a valid
escape hatch and `D-IMPL-16` makes it unexpressible in any case.

**`Q3.2` — AN UNATTESTED REMOTE CHILD IS A REFUSAL, NEVER DEBT.** The vault
spec's *"an unattested remote claim is recorded as Context Debt rather than
admitted"* is **struck**. It contradicts `D-IMPL-336` F1. The outcome is a
governed refusal, and `CLD-G07` keeps it load-bearing: the refusal refuses the
composite **even in an optional slot**. Missing attestation is never converted
into a debt factor.

**`Q3.3` — `Federate` AND `Enrich` DO NOT APPEAR IN `operators_invoked`.**
The vault spec's `operators_invoked: [Resolve, Policy, Projection,
TemporalTraversal, Federate, Enrich, Compose]` is **struck and remapped**.

The two vocabularies are kept apart, deliberately:

| Vocabulary | Where it is legitimate | Members |
|---|---|---|
| **Standard v0.3 §10.2** — specification language | §D.2's step table, as *architecture* | Resolve · Policy · Projection · Traversal · Enrich · Similarity · Evaluate · **Federate** |
| **The runtime's closed categories** — what the SDK actually executes | **`lineage.operators_invoked`, and nowhere else** | `policy` · `similarity` · `temporal` · `traversal` (`src/ccf/operators/base.py`, `CATEGORY_ORDER`) |

**Lineage contains only operators the SDK actually executes.** The precedent
is `LEX-F-03`, recorded on rung 21 for exactly this reason: a §D step assigned
to Similarity was wrong because *"by the time an operator runs, acquisition is
over and the graph exists."* Federation is acquisition. It happens at the
acquisition seam, before any operator runs, and it is **not** an operator
invocation. No new SDK operator is minted.

---

## A · Decision frame

**Decision and trigger.** A syndicate amendment requiring lender consent. The
credit officer must know whether the consent threshold in the filed agreement
is reachable — which cannot be answered from our own share alone.

**Consuming principals.** The bank's own credit officer, under three
renderings: `agent` (administrative agent — documentation and waterfall
detail), `participant` (an existing lender), `prospective` (a candidate
assignee, who receives materially less).

**Counterfactual failure — Context Starved across an organizational
boundary.** Each syndicate member holds a partial view. No member holds the
whole picture, and today's mechanism is a phone call or a spreadsheet emailed
between agents. The failure is not that data is missing; it is that **there is
no interface**. A contract-bound product with a negotiated envelope carries
TTL, lineage and a policy envelope both institutions can audit — which a
data-sharing agreement does not.

**The hard part is the envelope, not the wire.** Two institutions must agree
what each may see, and each must enforce the other's constraints on material
it never controls.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Schema** | `syndicate_co_lender_position` — entities: `SyndicatedFacility`, `SyndicateMember`, `SyndicateParticipation`, `Amendment`, `AmendmentThreshold`, `DisclosureEnvelope`, `Passage`; relationships: `participationIn`, `participationOf`, `amends`, `thresholdGoverns`; measures: syndicate composition, own position, the admitted peer position, consent-threshold reachability, divergence where both sides are exact. |
| **Classification / residency** | `internal`; single jurisdiction; the peer's material never leaves the record it was admitted into. |
| **Assembly Mode** | **Mode 1 — pure algorithmic.** No LLM anywhere. |
| **Freshness SLA** | Daily for positions; event-driven for amendments. |
| **TTL** | **4 hours** · `ttl_anchor: from_decision` · floored by any admitted child's own expiry (§E). **`Q4` is owed on this value — see §F.4.** |
| **Policy Binding** | Entitlement scope; **the bilateral disclosure envelope per counterparty**, request scope and disclosure scope held as two distinct sets; competition-law constraints (`CLR-001`–`CLR-004`); the credit agreement's confidentiality provisions. |
| **Lineage** | `operators_invoked` — **runtime categories only**: `policy.principal-subgraph`, `temporal.as-of-boundary`, `traversal.typed-neighborhood`. Plus `graph_snapshot_at` (ledger `t`), `policy_version`, `projection_plan_id`, and the **admitted child's own lineage by set-union** (`D-IMPL-31`). Federation appears in replay dimension 2 as the child row's `producer_id` / `producer_tenant` / `question_ref` / `producer_replay_ref` / `eligibility_basis` — **not** as an operator. |
| **Semantic Version** | `v1.0.0` |
| **Discovery** | `cb.syndicate-co-lender` |
| **Addressability** | `/context-products/cb/syndicate/{facility_id}/co-lender-position` |

### B.2 The measures

Syndicate composition at the ledger point · our own share and rating · the
admitted peer's share **at its declared precision** · the consent threshold in
force with its filed provision · whether the threshold is reachable from the
positions actually held · divergence, **only where both sides are exact**.

### B.3 Request parameter surface

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `facility_id` | string, required | anchor | — |
| `intent` | enum, required | selects the envelope and policy | — |
| `perspective` | enum `agent` \| `participant` \| `prospective` | **Π** | derived from the credential |
| `include_federated` | bool | acquisition scope | **`false`** |
| `counterparties` | list | federation scope | per envelope |
| `as_of` | date | `T` | today |

**`require_attestation` is absent by ruling (`Q3.1`).** Attestation is a
condition of admission, not a caller-selectable bound.

`include_federated` defaults to **`false`**. Reaching across an organizational
boundary is a deliberate act with legal consequences and must never happen
because a default made it happen. The switch is expressed through the public
`build_children=` hatch on `open_product` — the only supported way a *request*
parameter reaches the child-resolution seam, since the `optional-absent`
branch keys on grants, which are a deployment property. **The glue is measured
before it is called a DX issue** (`CLD-G08`, and §G.2).

### B.4 Prerequisites

`facility-terms-snapshot` (cp-02) · `credit-exposure-rollup` (cp-05) ·
`covenant-in-force-as-of` (cp-08) · `mnpi-wall-enforcement` (cp-17).
**Conceptual prerequisites only** — all four are frozen specimens under
`D-IMPL-261` and none is composed as a child here.

---

## C · Data catalog — every figure measured live on 2026-09-22

Both fabrics were read read-only. ccf-dataprep's 2026-09-19 measurement
reproduced **exactly**; where this document and the wave documents disagree,
the measurement wins.

### C.1 The two fabrics

| | Primary (ours — JPMorgan Chase Bank, N.A.) | Peer (Bank of America, N.A.) |
|---|---|---|
| Fluree | `:8090`, ledger `fibo-v2` | `:8091`, ledger `bofa/syndicate` |
| Postgres | schema `ccf_v2` in `parkavedb` | schema `colender` in `bofa_syndicated` |
| MongoDB | `fibo_v2` | `bofa_syndicated` — **empty by design** |

Connection material for both comes from the environment. **The peer's variables
live in `~/.bashrc`, which returns early for non-interactive shells, so every
peer read runs under `bash -ic`** — and `.env.example` documents a peer at
`192.168.4.77` that does not exist. Neither fact reaches the example's code: no
address and no credential appears in the tree (`CLD-G20`).

### C.2 The two disclosure envelopes — genuinely asymmetric

| Counterparty | `requestScope` (what we may ask them for) | `discloseScope` (what we may tell them) |
|---|---|---|
| **Bank of America** (`SYNM-9d3fd0fd`) | `member_commitment`, `own_position` | `syndicate_composition`, `amendment_vote_posture` |
| **Citibank** (`SYNM-8e5427c6`) | `amendment_vote_posture` | `syndicate_composition` |

Both `envelopeVersion: v1`, `validFrom: 2026-08-26`, provenance
`synthetic — internal`.

**Under `Q1`(b) this table is the whole federation-scope story.** BofA's
`own_position` class is requestable, so its `co-lender-position` product can be
admitted. **Citibank's cannot** — `amendment_vote_posture` is the only class we
may request from Citibank, and the peer fabric holds no such product. The one
Citibank row that exists is a *position*, which is precisely what the envelope
does not permit us to ask for.

### C.3 What the peer holds

`colender.peer_position` — **7 rows**. `colender.peer_product_declaration` —
**3 rows**. Fluree `bofa/syndicate` — **2 typed `FinanceSyndicateMember`
nodes**, `ex:disclosurePrecision` `exact` (BofA) and `band` (Citibank).

| facility | declaration | declared TTL | declared latency | attestation | peer position |
|---|---|---|---|---|---|
| **`FAC-6F4065`** | `PDEC-4BEB7CE1F8` | 21600 s (6 h) | 650 ms | bilateral signed digest | BofA **exact** $187,000,000 |
| `FAC-405B7A` | `PDEC-AC14CC0870` | 10800 s (3 h) | **7200 ms** | bilateral signed digest | Citibank **band** $20 m–$140 m |
| **`FAC-A4A5EE`** | `PDEC-14A62D69A5` | 7200 s (2 h) | 900 ms | **NULL** | BofA **exact** $182,000,000 |

All six peer `facility_id` values resolve in `ccf_v2.facility` with
`syndicated = true`. That join — `(LEI, facility_id)` — is the whole negotiated
interface.

### C.4 What the primary holds

| Element | Store | Measured |
|---|---|---|
| `syndicate_member` | Postgres | 45 rows, real LEI and RSSD |
| `own_position` | Postgres | 5 rows — `FAC-6F4065` **$61,500,000** `BBB-` performing; `FAC-A4A5EE` $84,000,000 |
| `syndicate_projection_plan` | Postgres | 3 — `agent`, `participant`, `prospective` |
| `competition_law_rule` | Postgres | 4 — `CLR-001`–`CLR-004` (US ×3, EU ×1) |
| `divergence_threshold` | Postgres | 9, by sector, with `policy_version` |
| `member_call_report` / `reporting_bank` | Postgres | 16 / 2 |
| `SyndicateParticipation` | Fluree | 97 total; **18 on `FAC-6F4065`** |
| `AmendmentThreshold` | Fluree | 16; the pair governing `FAC-6F4065` is below |
| `Amendment` / `AmendmentEvent` / `AmendmentVote` | Fluree | 25 / 6 / **1** |
| `DisclosureEnvelope` | Fluree | 2 (§C.2) |

**The consent threshold, from filed text.** `AmendmentThreshold`
`…/1046102_0001104659-25-031884_tm2511351d1_ex10-1.htm/required-lenders`:
`consentStandard` **"Required Lenders"**, `consentPercent` **50**,
`sourcePassage` `…#offset=165132-165234`, `thresholdGoverns` both `FAC-6F4065`
and `FAC-A4A5EE`. A companion `each-affected-lender` threshold governs the same
pair. The `AmendmentEvent` on that document has `effectiveDate` **2025-04-03**
and amends both facilities; `AMD-6F4065-1` is the amendment itself.

**This is what makes the peer child causally necessary.** Our own share on
`FAC-6F4065` is $61.5 m. The 50 % Required-Lenders threshold is not reachable
from our position alone, and whether it is reachable *at all* depends on the
admitted peer's $187 m. A sabotage that drops the child changes the answer.

### C.5 The traps, each with a binding chosen

| # | Trap | Binding |
|---|---|---|
| 1 | The two fabrics **share a host**; Postgres shares host *and* port and differs only by database and role. Isolation is software-only. | Every peer read goes through the registered door (`CLD-G20`). The example holds no peer DB handle at all, so the shared host is unreachable from it by construction. |
| 2 | `pytest validators/test_fabric_isolation.py` in `ccf_dataprep` **collects zero tests and reports success**. | Recorded, not inherited. This rung's gates are declared in `artifacts/gates.yaml` and resolved against a real `pytest --collect-only`, per `D-IMPL-224`. |
| 3 | Summed `commitmentUsd` over the 18 participations on `FAC-6F4065` is **$950,000,000**; `ccf_v2.facility.commitment_amount` for `FAC-6F4065` is **$500,000,000**. The EX-10 covers `FAC-6F4065` **and** `FAC-A4A5EE` ($300 m), which still does not reconcile to $950 m. | **`[TBC-1]`** — bind at Gate 2. The product must state which denominator the consent arithmetic uses and why, and must not silently pick one. Whichever is chosen, the other is served beside it, as rung 21 did for conflicting capital authorities. |
| 4 | The peer's positions carry `as_of = 2026-08-26`, ~27 days before the demonstration instant. | The peer producer anchors **`from_decision`**, not `from_entity_freshness`: it answers about its current position and its declared TTL is a duration. An entity-freshness anchor would expire every child before serve and make the rung unobservable — the cp-07 trap `D-IMPL-323` exists for. |
| 5 | The peer's Mongo helper refuses to write the peer's own database (`PROTECTED_MONGO_DBS`). | Irrelevant here — this rung writes nothing anywhere, and the peer Mongo is empty by design. |

### C.6 Correlation key and single-writer discipline

`facility_id`, and member `LEI`/`RSSD`. The peer's material enters through
**L2 only**, after `CompositeAdmissionGate` holds it to the local
registration. The peer fabric never acquires a write handle to our graph and
we never acquire one to theirs.

---

## D · Assembly recipe

### D.1 Client call

```
GET /context-products/cb/syndicate/FAC-6F4065/co-lender-position
      ?intent=amendment-consent&perspective=participant
      &include_federated=true&counterparties=B4TYDEB6GKMZO031MB27
      &as_of=2026-09-22
```

### D.2 Operator step table

The **Category** column names what the runtime executes. A step whose category
is `—` is acquisition or contract assembly and **contributes nothing to
`operators_invoked`** (`Q3.3`, and `LEX-F-03`).

| # | Step | Store | Standard §10.2 name | Runtime category |
|---|---|---|---|---|
| 1 | Resolve the facility anchor and the caller's rendering from the credential | Postgres | Resolve | — (acquisition) |
| 2 | Bind entitlement; load the bilateral envelope for each named counterparty; compute the **request** set and the **disclosure** set as two distinct sets; load the competition-law rules; emit `policy_version` | Fluree + Postgres | Policy | **`policy.principal-subgraph`** |
| 3 | Bound the graph at `as_of` | Fluree | Traversal (temporal mode) | **`temporal.as-of-boundary`** |
| 4 | Walk `participationIn` / `participationOf` / `amends` / `thresholdGoverns` from the facility; emit the syndicate graph and ledger `t` | Fluree | Traversal (current mode) | **`traversal.typed-neighborhood`** |
| 5 | **Envelope containment.** Refuse any counterparty whose requested class is outside its `requestScope` — **before dispatch** | in-process | — | — |
| 6 | **Federated acquisition.** Where `include_federated`, ask each permitted peer its question through its registered `mcp_product` producer; hold every answer to the registration; compare the peer's `declared_latency_ms` against the deployment's bound; admit or refuse | peer fabric, via the registered door | Federate | — (acquisition) |
| 7 | Resolve our own position, rating and posture; resolve passage spans for the consent provision | Postgres + MongoDB | Enrich | — (acquisition) |
| 8 | Compose composition, positions at each member's declared precision, consent reachability and divergence; floor the expiry; union the lineage | in-process | Evaluate / Compose | Π |

### D.3 Determinism class

Fully algorithmic, Mode 1. No LLM inference, no fitted model. The same
question at the same instant hashes to the same bytes.

### D.4 Validation gates (contract level)

Empty-operator guard · lineage strict equality · TTL bounds · **envelope
containment** (no request exceeds the negotiated scope) · **attestation as an
admission condition** · **provenance separation** (every claim local-
reconstructible or remote-attested, derived from `eligibility_basis`) · **TTL
floor** (the composite never outlives an admitted child).

---

## E · Volatility and debt

| Signal class | `λ_c` | Basis |
|---|---|---|
| Syndicate composition | ~180 days | changes on assignment |
| Commitments | ~365 days | amendment-driven |
| Own position and posture | ~1 day | |
| **Remote positions** | **peer-declared** | the local fabric neither sets nor verifies it, only honors it |
| Disclosure envelopes | ~365 days | renegotiated periodically |
| Amendment state | event-driven | moves hourly during a live consent solicitation |

All values **illustrative** under `D-IMPL-323` and disclosed where a reader
meets them. Debt is the SDK's per-factor aggregation, unchanged. **Missing
attestation is never a debt factor** (`Q3.2`).

**Materialization posture: local structure materialized; federated components
never cached.** Caching a remote product beyond its declared TTL breaches the
envelope it was released under — a contractual matter, not a performance one.

**Supersession triggers.** Assignment or transfer; amendment; peer-declared
invalidation; envelope renegotiation.

---

## F · Source binding and readiness

### F.1 Element readiness

**Every element §B requires is present and measured on one of the two
fabrics.** Nothing is missing. The absences that exist are deliberate (peer
MongoDB) or out of scope (§0.3).

### F.2 Symbols to be used, verified against `src/` on 2026-09-22

`open_product` with `build_children=` · `McpProducerRegistration` ·
`QuestionBoundChildResolver` · `CompositeAdmissionGate` · `ChildRequirement`
(`required=false` + `absence_treatment`) · `compose_expiry` ·
`compose_lineage` · `compose_debt_factors` · `PolicyConstraint` +
`ConstraintApplicability` · `resolve_ttl_anchor` · `run_gates` ·
`build_egress_server`. Every one resolves; none is invented. **No symbol is
added and none is changed.**

### F.3 Every `[TBC]`, with an owner

| # | Item | Owner |
|---|---|---|
| `[TBC-1]` | The consent-arithmetic denominator (§C.5 trap 3) | Dave — bind at Gate 2; both figures served either way |
| `[TBC-2]` | **`Q4` — the class TTL, and whether `CLD-G04` has a carrier** | **Dave — owed before Gate 2 (§F.4)** |
| `[TBC-3]` | The illustrative `λ_c` values | Dave — under `D-IMPL-323` |
| `[TBC-4]` | The deployment's federation latency bound (§G.1 `CLD-G12`) | Dave — recommended at 5 s, the vault spec's value |

### F.4 — THE QUESTION OWED

#### `Q4` — `CLD-G04` and `CLD-G05` cannot both be carried against this estate

**This is a conflict between the locked gate boundaries and the `Q1`/`Q2`
rulings, surfaced rather than resolved.** The locked boundary reads: *"G04/G05
— peer child expiry binds on one facility; composite ceiling binds on
another."* Measured against the estate, that is not satisfiable.

The arithmetic, with the class TTL at the vault spec's 4 h and
`ttl_anchor: from_decision`:

| facility | child TTL | vs 4 h ceiling | admissible under `Q1`/`Q2`? | carries |
|---|---|---|---|---|
| `FAC-6F4065` | 6 h | ceiling is lower → **ceiling binds** | **yes** (attested, in envelope) | `CLD-G05` |
| `FAC-405B7A` | 3 h | **child would bind** | **no** — Citibank out of envelope (`Q1`b) | nothing |
| `FAC-A4A5EE` | 2 h | **child would bind** | **no** — unattested, refused (`Q2`) | nothing |

**The only two declarations short enough to floor the composite are precisely
the two that are governed-refused.** Bank of America holds positions on six
facilities but product declarations on only two, so there is no fourth
candidate. An admitted child whose expiry floors the composite is therefore
**unreachable from this estate without weakening a governed refusal**, which
`Q1` and `Q2` both forbid.

Three ways forward. None may be taken without a ruling:

1. **Declare `CLD-G04` `unavailable`, with its guard named** — the rulings and
   the estate jointly make the arm unreachable. Precedent: `ABS-G01` at
   `D-GATE-cp-16`, where a structurally impossible sabotage was named rather
   than manufactured. **Recommended.** It is the honest statement, it costs
   nothing, and `CLD-G05` still proves the floor formula positively.
2. **Raise the class TTL above 6 h** as an illustrative calibration under
   `D-IMPL-323`, so the attested child's 6 h binds. This buys `CLD-G04` and
   **loses `CLD-G05`** — no declaration exceeds any ceiling above 6 h — so it
   trades one arm for the other rather than carrying both.
3. **Retune the estate.** Explicitly forbidden by `Q1` and by CLAUDE.md §9.
   Listed only to record that it was considered and refused.

**A consequence worth stating plainly: residual `341-4` does not become live
on CP-20.** Gate 0 predicted this rung would be its first live carrier, and my
own Gate-1 report repeated that prediction. Measured against the estate under
the `Q1`/`Q2` rulings, it is wrong — the binding-child case is exactly the
case those rulings refuse. `341-4` remains a carried residual.

**Two notes that need no ruling, recorded because they change what would
otherwise have been asked:**

1. **`include_federated=false` needs no second local child.** `compose_expiry`
   is not reached when nothing is admitted: `composite.py`'s `if not
   admitted_children` branch returns `expires_at=None` with the parent's own
   lineage, which `D-IMPL-336` Amendment 5 calls *"a legal outcome"*. No local
   child requirement is invented to keep the composite well-formed.
2. **The single open `AmendmentVote` is on `FAC-A4A5EE`**, the refusal
   facility — so the `voteState: open` flag is not observable on the
   admitted-peer facility. It is not needed and nothing is seeded to create
   one. `FAC-6F4065` carries the stronger material: an amendment in force
   (`AMD-6F4065-1`), a filed 50 % Required-Lenders threshold with a resolvable
   passage, and a consent question that **cannot be answered without the peer
   child**. Recorded as an estate limitation (§B.4 of
   `docs/EXAMPLE-EVALUATION-CRITERIA.md`), disclosed in the README.

---

## G · Operate and govern

### G.1 Product gates — 20

| id | What it asserts | Red when |
|---|---|---|
| `CLD-G01` | the admitted child is governed under the **producer's** tenant, and the composite's own tenant is neither compared to it nor set equal to it | the child is admitted only by claiming our tenant |
| `CLD-G02` | a child whose `tenant_id` disagrees with the registration is refused **`producer-tenant-mismatch`**, by name, as data | the mismatch is tolerated or raised |
| `CLD-G03` | a child whose `producer_id` disagrees with the registration is refused **`producer-mismatch`** — a **distinct** reason from `CLD-G02` | the two refusals collapse into one |
| `CLD-G04` | **the admitted child's expiry floors the composite** — `expires_at` equals the child's when the child is the lower term | the child term is dropped from the minimum. **Carrier owed — see `Q4` (§F.4)** |
| `CLD-G05` | **the class ceiling floors the composite** when it is the lower term, on `FAC-6F4065` (6 h child against a 4 h ceiling), computed from the live declared value | the ceiling term is dropped, or the value is hard-coded |
| `CLD-G06` | the unattested declaration on **`FAC-A4A5EE`** produces a **governed refusal** — as data, with a replay reference, never a raise and never a product | the child is admitted, or the refusal escapes as an exception |
| `CLD-G07` | **that refusal refuses the composite even though the federated slot is optional.** Optional means optional *absence*, not optional governance (`D-IMPL-336` F1) | an optional slot swallows a refused child |
| `CLD-G08` | `include_federated=false` serves, admitting no child, recording the row as `optional-absent` and applying the declared absence treatment to debt | the flag is ignored, or absence is priced as zero |
| `CLD-G09` | the two `include_federated` values on one anchor produce **different content addresses** — the flag is part of the question's identity | the flag does not reach the address |
| `CLD-G10` | a request for Citibank's `co-lender-position` is refused **before dispatch**, and **no peer call is made** — proved by a dispatch counter, not by the absence of a result | the request reaches the wire, or is refused only after admission |
| `CLD-G11` | `requestScope` and `discloseScope` are read as **two different sets** from the same envelope node, for both counterparties | one set is used for both purposes |
| `CLD-G12` | a peer whose **declared** `declared_latency_ms` exceeds the deployment's bound is refused by name — a **declaration comparison**, never a synthetic network timeout | a timeout is simulated, or the declaration is ignored |
| `CLD-G13` | **no served payload contains a point estimate derived from a band declaration**, under any perspective. The band may be observed as estate evidence; a dollar point estimate must never be manufactured from it | a midpoint, a bound, or any single figure is derived from `band_low`/`band_high` |
| `CLD-G14` | divergence is computed **only where both sides are exact**; a band-declared member yields no divergence number | a divergence is reported against a band |
| `CLD-G15` | every claim is marked local-reconstructible or remote-attested, and the marking is **derived from the admission result's `eligibility_basis`** rather than authored | the marking is hard-coded, or a remote claim is presented as reconstructible |
| `CLD-G16` | replay dimension 2 is a **superset** of the product's lineage, and the child row names `producer_id`, `producer_tenant`, `question_ref` and `producer_replay_ref` | any of the four is absent from an admitted or refused row |
| `CLD-G17` | the composite's lineage is the **set-union** of its own and the admitted child's (`D-IMPL-31`), and is **not** used to prove provenance separation — `lineage.operators_invoked` is a `frozenset` and carries no order and no federation marker | the union is not taken, or `Federate`/`Enrich` appears in `operators_invoked` |
| `CLD-G18` | three perspectives serve **structurally different** products from one class through one door | the three renderings collapse |
| `CLD-G19` | `prospective` receives strictly less than `participant`, which receives strictly less than `agent` — an **ordering**, asserted as containment, never as a count | the ordering inverts, or the gate pins a number |
| `CLD-G20` | **the example holds no peer database handle.** The peer fabric is reachable only through the registered producer; no peer address or credential appears in the tree | any module opens a connection to the peer's Postgres, Fluree or MongoDB |

**`CLD-G04` is the one at risk of `unavailable`,** for the reason §F.4 gives.
If the ruling makes the arm unreachable the guard is named and **the mechanism
is not weakened to manufacture a red** — the standing rule from `D-GATE-cp-16`.

### G.2 What this rung measures for the backlog

The **`build_children=` glue for a request-scoped optional child**, counted in
lines before it is called a DX issue (Dave, 2026-09-22) — this is its first
instance on the ladder. The **credential-envelope seam at its next instance**,
recorded only; A2 is closed at **B** by `D-GATE-cp-19` and is **not reopened
absent materially new evidence**. And the cost of a second producer tree over a
foreign fabric, against the cp-04-canonical baseline of 1,165 Python and 784
YAML lines.

---

## Gate 1 summary

**Bucket 1. No SDK or runtime capability is missing; none is added.** The
genuinely new capability count is **zero**. `D-IMPL-346` remains unspent. The
active issue cap for this rung is **0 of 3** — `AIA-F-01` was charged on rung
22 and does not carry here, because nothing in CP-20 depends on or reactivates
it.

**Owed before Gate 2:** `Q4` (§F.4) — whether `CLD-G04` is declared
`unavailable` with its guard named (recommended), or the class TTL is
recalibrated to carry `CLD-G04` at the cost of `CLD-G05`.
