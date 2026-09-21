# CP-SPEC-019 — AML Typology Match

**Product class:** `compliance.aml-typology` · **lane** `1.0.0` · **tier 5**
**Status:** Gate 1 — authored before any implementation, presented for Dave's
ruling. Nothing in `examples/cp-19-aml-typology-match/` exists beyond this
document and the artifacts it declares.
**Vault source:** `wiki/context-products/content/aml-typology-match.md`
(`compliance.aml-typology.v1`, standard q019). **Gate-0 row:** CP-19 in
`docs/GATE-0-COVERAGE-CP15-24.md` — 40 rows, 29 supported, 5 friction, 5
estate, **0 missing capability, 0 incorrect behavior**, 1 later.
**Predecessor:** CP-17 (`D-GATE-cp-17`), whose paved road, door composition
and credential-derived envelope this rung reuses and is measured against.

---

## 0 · What this document is

The specification for rung 19, written before its code, to the Context Product
Specification Standard v0.3. Every number in it was measured read-only against
the live `.76` estate on 2026-09-20 and is cited where it is used. Nothing here
asks for data to be added.

### 0.1 What this product intends to prove

| # | Claim | Realized by | Gate |
|---|---|---|---|
| 1 | **Policy runs before Similarity, and the order is a served fact.** The permitted document set is computed before any ranking, so no residency- or confidentiality-restricted passage enters the candidate space. The operator plan the product serves names the order; it is not a comment in code. | The four-operator composition of Whitepaper §7.4(c); the SDK's `policy.principal-subgraph` and `similarity.corpus-select` in one declared plan, Policy first | `ATM-G01`, `ATM-G02` |
| 2 | **A disposition the posture forbids is never generated as a candidate.** Not generated and then filtered — never constructed. The permitted-disposition set bounds the payload's candidate list by construction. | `DispositionRule` per (posture, typology, disposition) read at the Policy step; the declared product gate refuses a payload carrying a candidate outside it | `ATM-G03`, `ATM-G04` |
| 3 | **The posture in force at `as_of` governs, not the posture in force now.** The same alert, asked at two instants, yields two different permitted sets, and the earlier answer is not reconstructible from the later one by any means except asking as of the earlier instant. | Two `FilingPosture` nodes with distinct effective dates; `temporal.as-of-boundary` on the posture read | `ATM-G05`, `ATM-G06` |
| 4 | **Three perspectives differ in what is assembled, not in what is displayed.** The member set of the served payload is a function of the perspective's plan, and a member absent from a plan is absent from the product. | `ccf_v2.aml_projection_plan`, three rows, keyed by perspective; Π branches on the role | `ATM-G07`, `ATM-G08` |
| 5 | **The existence of a SAR is itself restricted.** A perspective not named in a SAR's visibility set receives no indication that one exists — no count, no marker, no placeholder, no member. | `sar_classification` in the departmental SQLite, read at the Policy step **before any enterprise source runs** | `ATM-G09`, `ATM-G10` |
| 6 | **Residency is an entitlement, not a filter applied afterwards.** Party data for a resident of a constrained jurisdiction is admitted only to a principal holding the declared entitlement. | `ResidencyConstraint` requiring `sees_eu_person_data`; the principal register carries the flag | `ATM-G11` |
| 7 | **Every typology claim is anchored to an advisory passage.** A match with no resolvable passage is not served. | 72 FinCEN/FATF advisory passages in MongoDB, each carrying `advisory_number` and `typology` | `ATM-G12` |
| 8 | **An examiner reconstructs the posture that governed.** Replay resolves which posture was in force, which plan applied, which operators composed and which passages each claim rested on. | The five-dimension record; dimension 2 pins the posture version | `ATM-G13` |

### 0.2 What this product deliberately does not prove

- **A per-alert Similarity query.** `SimilaritySelectParameters.query` is an
  artifact literal with no request-bound arm. Dave ruled (2026-09-20):
  class-level lexical Similarity is acceptable for the initial release and the
  per-alert query remains backlog. This rung ranks a **class-level typology
  vocabulary** and carries the per-alert match on the `matchesTypology`
  traversal. Recorded, not worked around.
- **The vector path.** Measured: all 72 advisory passages carry neither an
  embedding nor a `sha256`, and no embedder ships with the SDK. The corpus is
  ranked lexically over passage text. This is an estate limitation, disclosed
  here and at the artifact that declares the index.
- **A SAR narrative.** Drafting is a downstream semantic stage. This product
  is algorithmic throughout (§7.6 alternation).
- **New SDK mechanism.** Nothing here asks for one. If the build surfaces a
  missing capability, incorrect behavior or a governance defect, it stops.

### 0.3 The four-question test

1. *Could a `SELECT` answer this?* No. The permitted-disposition set depends on
   a posture effective at a past instant, held in a bitemporal ledger, and the
   candidate space is bounded before ranking.
2. *Does the answer change by who asks?* Yes, in what is **assembled**: three
   plans, three member sets, and a SAR whose existence is invisible to `l1`.
3. *Does the answer change by when it is asked as of?* Yes. `TYP-STRUCT` /
   `close-no-action` is permitted under the 2025 posture and forbidden under
   the 2026 one.
4. *Is a refusal an answer?* Yes. A perspective with no plan is refused by
   name; an alert with no admissible content is served computed-empty on the
   same path a nonexistent alert takes, so neither reveals the other.

---

## A · Decision frame

**Trigger.** A transaction-monitoring alert requiring adjudication.

**Consumers — three, one escalation path.** `l1` analyst (action-ready triage),
`l2` reviewer (investigative history and counterparty graph), `examiner`
(defensibility: reasoning trail, policy-version attribution, evidence chain).

### A.1 Counterfactual — Policy Blind, in its consequential form

The agent proposes a closure the analyst is *authorized to enter* but which
the filing posture in force forbids for that pattern. Access control said yes.
A wrongly-closed alert is a filing failure, not a workflow error.

**The estate makes this exactly measurable.** `TYP-STRUCT` under posture
`POST-2025-01` (effective 2025-03-01) permits `close-no-action` and forbids
`escalate-l2`. Under `POST-2026-01` (effective 2026-01-15) the two invert.
One alert, two `as_of` values, two permitted sets, measured — not asserted.

### A.2 Counterfactual — Perspective Flat

One artifact for three audiences. The `l1` analyst drowns in investigative
history it cannot action; the examiner receives a disposition recommendation
with no policy-version attribution. Measured: the three plans differ in member
count (4, 6, 10) and `l1`'s does not contain `sar_filing_history` at all.

### A.3 A refusal is an answer

A principal whose perspective has no plan is refused with minimal disclosure
through the one recorder. An alert whose admissible content the Policy step
removes entirely is **served computed-empty**, identically to an alert id that
does not exist — the A6 posture CP-17 established and this rung inherits
(`ATM-G14`).

---

## B · Contract

### B.1 The elements

| Element | Value |
|---|---|
| Schema | `compliance.aml-typology` @ `1.0.0` |
| Subject | `alert_id` — the alert under adjudication |
| Freshness | intraday for transactions; ~1 day for sanctions |
| TTL | 3600 s · `ttl_anchor: from_decision` (per-alert, per-perspective, under a live sanctions obligation — nothing here is cacheable) |
| Policy binding | entitlement scope; the **filing posture effective at `as_of`**; disposition rules by posture; **SAR confidentiality from the departmental store**; residency constraint by entitlement |
| Lineage | `operators_invoked` naming all four; `graph_snapshot_at` as ledger `t`; `policy_bundle_versions`; passage-level anchors on every typology claim |
| Discovery intent | `alert-adjudication` |

### B.2 Request parameter surface — two parameters, both load-bearing

| Parameter | Type | Default | Moves | Why it is on the surface |
|---|---|---|---|---|
| `as_of` | string, zoned instant | a relative default rendered at request time | `T` — which posture governs | Claim 3 cannot be demonstrated without it |
| `network_depth` | number, 1–4 | `2` | `R` — traversal scope | Claim 1's permitted-party bound is visible only when the traversal can exceed it; the estate holds 21 alerts whose own trigger text names a subject sitting **3 ownership hops deep**, invisible at the default 2 |

**Outside the request surface, by the CP-17 ruling this rung preserves:**
`perspective` (derived from the verified credential, never a caller's claim),
`corpus_scope`, and `sections`. A caller states no perspective; the door
decides it.

### B.3 Classification and residency

The permitted sets are **bounds on admission**, computed at the Policy step
from three sources that are read before any enterprise source runs:

| Bound | Source | Store |
|---|---|---|
| permitted disposition set | `DispositionRule` for (posture at `as_of`, typology) | Fluree |
| SAR visibility | `sar_classification.visible_to_perspectives` | **SQLite, departmental** |
| residency entitlement | `ResidencyConstraint.requiresEntitlement` against the principal register | Fluree + Postgres |

### B.4 Prerequisites and scope boundary

Prerequisite products (`kyc-refresh-beneficial-ownership`,
`credit-surveillance-early-warning`) are **not built** and are not composed.
This rung reads the estate directly, as CP-17 did. No composite, no child
product, no second estate.

---

## C · Data catalog

### C.1 Element table — every row measured 2026-09-20

| Element | Provenance | Store | Measured | `G` |
|---|---|---|---|---|
| Alerts | synthetic — internal | Postgres `ccf_v2.aml_alert` | **150** rows, 106 distinct subject parties | `E`,`T` |
| Prior-alert links | synthetic — internal | `ccf_v2.aml_alert_link` | **50** | `R` |
| Parties | synthetic — engineered | `ccf_v2.aml_party` | **201**; jurisdictions USA 22, NLD 21, GBR 19, FRA 15, SGP 13, DEU 11 | `E` |
| Transactions | synthetic — engineered | `ccf_v2.aml_transaction` | **4 358** | `E` |
| Sanctions entries | public (OFAC) | `ccf_v2.sanctions_entry` | **19 730** | `E` |
| Screening results | synthetic — internal | `ccf_v2.sanctions_screening_result` | **19** | `E` |
| OFAC near-match | synthetic — engineered | `aml_party.ofac_near_match` | **1** party | `E` |
| `transactedWith` edges | synthetic — internal | Fluree `fibo-v2` | **1 291 912** assertions | `R` |
| `matchesTypology` | derived | Fluree | **4 008** | `R` |
| Typologies | public (FinCEN/FATF derived) | Fluree `Typology` | **4**: `TYP-FUNNEL`, `TYP-SHELL`, `TYP-STRUCT`, `TYP-TBML` | `R` |
| Typology patterns | derived | Fluree `TypologyPattern` | **4** | `R` |
| Filing postures | synthetic — internal | Fluree `FilingPosture` | **2**: `POST-2025-01` (from 2025-03-01), `POST-2026-01` (from 2026-01-15) | `P`,`T` |
| Disposition rules | synthetic — internal | Fluree `DispositionRule` | **16** = 2 postures × 4 typologies × 2 dispositions | `P`,`T` |
| Residency constraint | public rule, synthetic binding | Fluree `ResidencyConstraint` | **1**, 27 EU/EEA countries, requires `sees_eu_person_data` | `P` |
| Advisory passages | public (FinCEN/FATF) | MongoDB `fibo_v2.passage` | **72** carrying `advisory_number` and `typology` | `L` |
| **SAR classification** | synthetic — internal | **SQLite departmental** `sar_classification` | **12** rows; 9 `restricted` (`l2`,`examiner`), 3 `confidential` (`examiner` only) | `P` |
| Projection plans | synthetic — internal | `ccf_v2.aml_projection_plan` | **3**, keyed by perspective; members 4 / 6 / 10 | `Π` |
| Principal register | synthetic — internal | `ccf_v2.principal` | 4 rows, carrying `sees_eu_person_data` | `P` |

### C.2 The data traps, each with the binding chosen

1. **The advisory corpus carries no embedding and no `sha256`** (measured: 0 of
   72). Binding: lexical ranking over passage text with a pinned index version;
   the vector path is out of scope and disclosed at the artifact. Anchoring
   uses `passage_id` with `start_offset`/`length`, not a content hash.
2. **The residency constraint names countries in full (`Austria`, `Belgium`);
   parties carry ISO3 (`USA`, `NLD`)**; the principal register's jurisdiction
   prefixes are ISO2 (`AT`, `NL`). Three vocabularies for one concept.
   Binding: the constraint is evaluated on the **declared entitlement**
   (`requiresEntitlement: sees_eu_person_data`) against the principal's own
   flag, which is a single boolean in the register — no country mapping is
   invented, and the country list is carried as evidence only. Recorded as a
   finding, not repaired.
3. **The estate holds no AML principal.** `ccf_v2.principal` has four rows and
   none carries an `l1`, `l2` or `examiner` perspective; `aml_projection_plan`
   is keyed by perspective with no principal column. Binding: **[TBC-1]** —
   see §F.2. The rung cannot derive a perspective from a credential without
   one of the two answers there.
4. **`aml_projection_plan` carries `elements`, not permitted sets.** Unlike
   CP-17's `projection_plan` (keyed by `principal_id`, carrying
   `permitted_edge_types` / `permitted_classifications` /
   `permitted_document_types`), AML's plan says what is *assembled* and the
   *bounds* come from three other sources. Consequence recorded for the A2
   measurement: **this rung's envelope is not the same shape as CP-17's**, and
   whether its plumbing is nonetheless substantially identical is the
   question the third instance exists to answer — measured after the build,
   never predicted here.
5. **`matchesTypology` is dense** (4 008 assertions over 201 parties). Binding:
   the traversal is bounded by `network_depth` and by the permitted party set;
   the match set is filtered to the subject's own parties.

---

## D · Assembly recipe

### D.1 Client call

```
GET /product/{tenant}/compliance.aml-typology/1.0.0
      ?subject=ALT-000005&intent=alert-adjudication&freshness=event-driven
      &asked_at=...&parameters={"as_of":"2026-02-01T00:00:00+00:00","network_depth":"3"}
```

### D.2 Operator step table

| # | Step | Operator | Sources | Emits |
|---|---|---|---|---|
| 1 | Resolve | *(none — the acquisition seam)* | SQLite → Postgres → Fluree → MongoDB, **in that order** | one `SignalEnvelope` per admissible claim, edges first |
| 2 | Policy | `policy.principal-subgraph` | — | the permitted set, class-level vocabulary |
| 3 | Temporal | `temporal.as-of-boundary` | — | the valid-time cut at `as_of` |
| 4 | Traversal | `traversal.typed-neighborhood` | — | the party network to `network_depth` |
| 5 | Similarity | `similarity.corpus-select` | — | the ranked advisory passages, **from the permitted set only** |
| 6 | Π | `MnpiWall`-shaped projection | — | the payload, member set a function of the perspective |
| 7 | Assess | the SDK scorer | — | `D_c` |
| 8 | Gate | `cp-19.dispositions-hold` | — | containment of candidates, members and anchors |

**The ordering in the served plan is claim 1.** `CATEGORY_ORDER` places Policy
before Similarity; the product's `lineage.operators_invoked` carries all four,
and `ATM-G01` reads the order off the *served* product rather than off the
configuration.

### D.3 Step detail — what the acquisition seam does, in order

1. **SAR confidentiality first, from the departmental store.** Before any
   enterprise source is opened, `sar_classification` is read for the alert. A
   SAR whose `visible_to_perspectives` does not name the asking perspective
   contributes **no claim of any kind** — the `sar_filing_history` member is
   absent for `l1` because no SAR claim was ever minted, not because Π dropped
   it.
2. **The posture at `as_of`.** The `FilingPosture` with the greatest
   `postureEffectiveFrom` ≤ `as_of` governs. Its `DispositionRule` set for
   each matched typology is the **permitted disposition set**.
3. **The residency entitlement.** If the constraint applies and the principal's
   `sees_eu_person_data` is false, party detail for constrained residents is
   not minted.
4. **The alert, its parties, its transactions**, then the typology matches and
   the network to `network_depth`, then the advisory passages for the matched
   typologies.
5. **Nothing restricted is minted for anyone.** The posture, the rule set and
   the SAR classification are consumed at this seam as *envelope inputs* and
   are not emitted as claims (the CP-17 §D.3 step 1.7 discipline, preserved).
   The permitted disposition set **is** emitted, on the alert claim, because
   the principal is entitled to know what it may propose and the gate reads it
   off the view.

### D.4 Emitted contract

```
payload: {
  perspective, as_of, posture: {posture_id, effective_from},
  alert: {alert_id, subject_party, raised_at, trigger, case_id},
  typology_matches: [{typology_id, confidence, advisory: {passage_id, advisory_number, document_id}}],
  permitted_dispositions: [...],                 # the bound, not the proposal
  disposition_candidates: [...],                 # l1, examiner — a subset of the above, always
  typology_pattern_summary: [...],               # all three
  counterparty_network: [...],                   # l2, examiner
  ownership_chain: [...],                        # l2, examiner
  prior_alert_lineage: [...],                    # l2, examiner
  sanctions_screening_result: [...],             # l1, examiner
  sar_filing_history: [...],                     # l2, examiner — ABSENT for l1
  policy_version_attribution: {...},             # examiner
  reasoning_trail: [...],                        # examiner
  entities_in_view, edge_types_served
}
```

`lineage_inputs_at`: `perspective`, `as_of`.

### D.5 Validation gates

Empty-operator guard · lineage strict equality · TTL bounds · **disposition
containment** (every candidate inside the permitted set) · **member
containment** (the member set equals the perspective's declared plan) ·
**typology anchoring** (every match carries a resolvable passage) · **SAR
silence** (no member, count or marker indicating a SAR the perspective may not
see).

---

## E · Volatility, debt and materialization

### E.1 Half-life table

| Class | Basis | λ_c | Note |
|---|---|---|---|
| `sanctions_entry` | supersede-only | — | never cached; the obligation is live |
| `transaction` | valid-from | **3 600 s** | **illustrative calibration** (see below) |
| `typology` | supersede-only | — | advisory-driven |
| `filing_posture` | supersede-only | — | changes on new guidance |
| `alert` | supersede-only | — | event-driven |

> **Illustrative calibration:** this example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

The estate's newest transaction value date is **2026-08-24**; a one-hour
half-life read at a 2026 `asked_at` would make every alert fail closed, so the
decision instant is pinned to the estate's own window and the calibration is
disclosed here, in the artifact and in the README.

### E.2 Debt

`F` from the SDK scorer over the view; `C` = the perspective's own required
element classes present ÷ required, read off the alert claim's plan; `S` = 1.
**Carried forward from CP-17 without re-litigation:** `F` is a mean over every
observation in the view, so supersede-only classes dilute a curve class
(`CP17-F-12`). It is disclosed, not re-charged.

### E.3 Materialization

Derived on demand, always. Per-alert, per-perspective, under a live sanctions
obligation.

---

## F · Source binding and readiness

### F.1 Readiness

Every element of §C.1 is present and measured. No element is `[TBC]` for
existence.

### F.2 Every `[TBC]`, with an owner

| # | Question | Owner | Blocks | Options |
|---|---|---|---|---|
| **TBC-1** | **The estate holds no AML principal.** `ccf_v2.principal` carries four principals whose perspectives are CP-17's (`coverage-banker`, `research-analyst`, `trader`, `kyc-analyst`); `aml_projection_plan` is keyed by `l1` / `l2` / `examiner` with no principal column. How does a verified credential become an AML perspective? | **Dave**, with ccf-dataprep for option (b) | The build. Without it there is no credential-derived envelope to measure, which is the A2 instance this rung exists to provide | **(a)** The rung declares its own three credentials in `ccf_environment.yaml` and maps them to the three perspectives in its own artifact — deployment identity is environment, the mapping is the deployment's, no estate row is invented, and it is the same shape CP-17's door uses. **(b)** Ask ccf-dataprep whether AML principals are intended in `ccf_v2.principal`, and wait. **Recommended: (a)**, because the perspective→plan mapping already exists in the estate and only the credential→perspective half is a deployment concern; (b) costs a round trip for a row the deployment would still have to name. |

Nothing else is `[TBC]`. The four data traps of §C.2 are bindings already
chosen, not open questions.

### F.3 Recorded findings — measured at Gate 1, needing no decision to build

| id | Finding | Category |
|---|---|---|
| `ATM-F-01` | 0 of 72 advisory passages carry an embedding or a `sha256`; the vector path is unreachable and anchoring uses offsets | estate limitation |
| `ATM-F-02` | Three vocabularies for jurisdiction: constraint names countries, parties carry ISO3, principals carry ISO2 prefixes | estate limitation |
| `ATM-F-03` | `aml_projection_plan` carries assembled elements, not permitted sets — a different envelope shape from CP-17's per-principal plan | example decision, **A2 input** |
| `ATM-F-04` | `CP17-F-12`'s scorer semantics apply here unchanged | disclosed, carried |

---

## G · Operate and govern

### G.1 Product gates

| id | Gate | Kind |
|---|---|---|
| `ATM-G01` | The **served** product's operator plan names Policy before Similarity | directional |
| `ATM-G02` | No passage outside the permitted document set appears in any ranked result | containment |
| `ATM-G03` | Every disposition candidate is inside the permitted set | containment |
| `ATM-G04` | A candidate outside the permitted set refuses the product by name | sabotage |
| `ATM-G05` | One alert at two `as_of` values yields two permitted sets, and `TYP-STRUCT`/`close-no-action` is in the earlier and not the later | directional |
| `ATM-G06` | The posture pinned in the record is the one effective at `as_of`, not the latest | equality |
| `ATM-G07` | Each perspective's member set equals its declared plan, for every alert | equality |
| `ATM-G08` | The member set is a function of the perspective and never of the alert | equality |
| `ATM-G09` | `l1` receives no member, count or marker indicating a SAR exists | absence |
| `ATM-G10` | A `confidential` SAR is invisible to `l2` and visible to `examiner` | directional |
| `ATM-G11` | Constrained-resident party detail requires `sees_eu_person_data` | containment |
| `ATM-G12` | Every typology match carries a resolvable advisory passage | containment |
| `ATM-G13` | Replay reconstructs the posture, the plan and the passages | replay |
| `ATM-G14` | An alert whose admissible content Policy removes entirely is indistinguishable from a nonexistent alert id, at both measured tolerances | A6, inherited |

### G.2 Acceptance

Every gate above executes against the live estate. At least twelve of the
fourteen are observed **red** under deliberate sabotage before the rung closes.

### G.3 Lifecycle

Lane `1.0.0`. Built once, on Dave's GO, after `TBC-1` is ruled.

---

## H · What this rung measures about the SDK

The Gate-0 row predicts **0 missing capabilities and 0 incorrect behaviors**.
What it predicts instead is friction, and this rung is the scheduled third
instance of the measurement:

- **A2 — the credential-derived policy envelope, third writing.** Measured
  after the build against CP-17 and cp-13-canonical: domain-policy LOC,
  generic plumbing LOC, concepts absent from public documentation, hand-built
  runtime objects, duplicated authority, structural similarity, and whether an
  AI agent could generate it from the spec plus the public surface alone.
  CP-17's measurement was ≈70 domain lines, ≈25 plumbing lines, four
  undocumented concepts. **`ATM-F-03` already records that this rung's
  envelope has a different shape**, which is evidence the review must weigh
  rather than a conclusion it may assume.
- **A1 — several principals through one door**, third writing; the latest-wins
  registration ordering measured again.
- **A3 — policy before similarity over a corpus**, second writing with the
  SDK operator.

No SDK change is pre-authorized. The A2 classification (leave alone /
documentation / small ergonomics) is brought to Dave with its measurements
before anything is implemented.
