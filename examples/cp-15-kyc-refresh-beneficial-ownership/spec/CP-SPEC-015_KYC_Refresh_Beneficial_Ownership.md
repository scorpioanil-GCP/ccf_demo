---
product: compliance.beneficial-ownership.v1
standard: v0-3
owner: vault
sdk_spec: cp-15
tier: 4
cost_band: "×3–5 — four PostgreSQL reads, one MongoDB read, one bounded Fluree read; four operator categories plus an in-memory evaluate; no LLM"
assembly_mode: 1
capability_classes: [relational, bitemporal-ledger, graph-traversal, document-passage, in-memory]
prerequisites: [corporate-family-tree, counterparty-reference-snapshot]
topic: context-products
title: KYC Refresh / Beneficial Ownership — Context Product Specification
generated: '2026-09-21'
---

# KYC Refresh / Beneficial Ownership — Context Product Specification

**`CP-SPEC-015` · rung 15 · `compliance.beneficial-ownership` @ `1.0.0` · Gate 1 — written before any code exists, on Dave's GO of 2026-09-21 (*"authorize KYC Gate 1 next… Gate 1 only first, identify what is genuinely new versus already proven, and don't build until we rule on that delta"*)**
**PostgreSQL `ccf_v2` for chains, persons, name variants, crosswalks, sanctions, thresholds and refresh state · MongoDB `fibo_v2` for KYC documents and their passages · Fluree `fibo-v2` for the ledger instant · the departmental store is not read by this rung — every read read-only, every write to a per-request scratch fabric**

> **Who are the natural persons behind this entity — and what do you do with
> the ones you are not sure about?** Ownership walked to person level across
> jurisdictions, with a resolution confidence carried per person, and the
> findings that fall *below* a reporting threshold or *below* a confidence
> floor kept **inside** the product and handed to the SDK's review queue
> rather than dropped out of it. A low-confidence match is a finding, not an
> absence.

---

> ## READ THIS BEFORE YOU READ A NUMBER
>
> **These examples teach METHOD — how to engineer and construct a Context
> Product with the CCF SDK — not the figures.**
>
> Measured read-only on 2026-09-21 against the live estate: `ccf_v2.bo_chain`
> 50 rows over 50 anchor entities and 46 persons, `bo_chain_hop` 169,
> `psc_person` 210 (35 EU nationals), `person_name_variant` 997,
> `person_crosswalk` 1,815 (75 in the `false_positive` band),
> `sanctions_screening_result` 19 (all in the review band),
> `sanctions_entry` 19,730, `bo_threshold` 18, `resolution_policy` 3,
> `kyc_refresh_state` 50 (19 overdue), `principal` 4; MongoDB `kyc_document`
> 32. The anchor entities are real legal entities
> (`ccf_v2.legal_entity`, `provenance = 'public'`); **every person, chain,
> variant, crosswalk, screening result, threshold and KYC document attached to
> them is invented, and the person records are pseudonymized by
> construction.**
>
> **No number here is a fact about any real person or any real ownership
> structure.**

---

## 0 · What this document is

Gate 1 for rung 15, written to the Context Product Specification Standard
v0.3 before any code exists. Dave rules on it; nothing is built until he does.

Dave's framing for this Gate is narrower than a full specification:
*identify what is genuinely new versus already proven, and do not build until
we rule on that delta.* §0.1 and §0.2 are therefore the spine, and everything
after them is the evidence for them.

### 0.1 Already proven — reused unchanged, and NOT reopened

| mechanism | proven at | how this rung uses it |
|---|---|---|
| the paved producer road | `D-IMPL-343`, rungs 13c/14/17/19/18 | `open_product` with the same five verbs; no new seam |
| the credential-derived policy envelope | A2, closed at **B** by `D-GATE-cp-18` | residency entitlement decides which person records materialize; **measured again, not reconsidered** (§G.2) |
| the multi-principal standard door | rungs 17, 19, 18 | four principals, three typed overrides |
| Policy before Similarity over a corpus | rungs 17, 19, 18 | residency-excluded persons leave the candidate space before matching runs |
| an evidence-anchored TTL | rung 1, `from_entity_freshness` | the anchor is the sanctions publish date rather than a filing date — a new *source*, not a new mechanism |
| a governed refusal at the acquisition seam | rungs 17, 19, 18 | four typed refusals |
| a declared product gate with several predicates | rungs 17, 19, 18 | one slot, five predicates |

**A redesign of any of these is out of scope for this rung.** IB expressed
them differently and that was not evidence they were wrong; KYC will too.

### 0.2 Genuinely new — one coverage shape, ruled 2026-09-21

**Dave's words, and the scope of this rung:** *"The one new coverage shape is
a governed Context Product handed to an existing HITL workflow primitive."*
**No new SDK mechanism is authorized.**

**A HITL primitive composed with a PRODUCT.** `ReviewQueue.submit_for_review`,
its transport, its two delivery surfaces and its replay landing are unit-,
workflow- and cross-process proven in `tests/hitl/`, but **no active example
composes a HITL primitive with a Context Product.** Verified 2026-09-21: a
search of `examples/` for `ReviewQueue`, `submit_for_review`, `ApprovalGate`
or `hitl` returns **nothing**. The only example that ever composed one is
`archive/examples/05-workflow-hitl`, which is archived and which binds the
queue to a **workflow** rather than to a product — and that difference is
exactly what leaves `workflow_state_ref` undefined for this case (§F.4).
This rung would be the first.

Everything else on the list the vault specification implies is either already
proven (§0.1), or is an attribute rather than a mechanism (a resolution
confidence carried per person is a claim attribute, which `RelationshipClaim`
and `EntityClaim` already hold), or has no data (§0.3).

**The one convention to rule is `Q14`**, and §F.4 is where it is asked.

### 0.3 The counterfactual that has no data, surfaced first

The vault specification's **first** counterfactual is *Context Starved by
cycle*: entity A owns B owns C owns A, and a recursive query without cycle
handling loops, truncates, or computes a confidently wrong percentage.

**There are no ownership cycles in this estate.** Measured two ways on
2026-09-21: no chain in `bo_chain_hop` revisits an owner, and no hop's
`owned_id` equals an earlier hop's `owner_id` in the same chain. Zero, on both
tests.

This is the same shape as rung 18's missing SC 13D filings: the specification's
headline case is priced and unsupplied. **It is surfaced here rather than
simulated**, and §F.4.2 asks Dave what to do about it. The rung's *second*
counterfactual — *Context Starved by name* — is supplied in abundance (§A.2)
and is strong enough to carry the product on its own.

### 0.4 The four-question test

- **Assembled rather than retrieved?** Yes — the chain, the resolution, the
  screening and the threshold test compose across three stores.
- **Needs governance before use?** Yes — a person record outside the
  principal's residency entitlement must never materialize.
- **Decays?** Yes, and at very different rates: sanctions daily, the register
  monthly, the refresh cycle in years.
- **Must a past answer be reproducible?** Yes — a KYC determination is the
  record a regulator asks about.

---

## A · Decision frame

**Decision and trigger.** A periodic KYC refresh falling due, an onboarding, or
an analyst needing the ownership chain behind a counterparty. Measured: 19 of
the 50 clients in `kyc_refresh_state` are **overdue**.

**Consuming principals.** Four are registered, and — unlike rungs 17 and 19 —
**the estate already distinguishes them on exactly the axis this product
needs**: `principal.sees_eu_person_data` is true for `PRIN-KYC-004` (the KYC
analyst) and false for the other three. This rung therefore has a **real
entitled/unentitled pair** and does not have to declare one (contrast
`ATM-F-03`).

### A.1 Counterfactuals

**Context Starved by name** — supplied, and the product's spine.
The same natural person appears differently across sources; a system keyed on
exact match sees several people, and one keyed on fuzzy match without
provenance merges two who are genuinely different. In a sanctions context the
merge is the more dangerous error.

**Context Starved by cycle** — **not supplied** (§0.3, `F.4.2`).

### A.2 The counterfactual acceptance test — measured, and it holds

| evidence the test needs | measured 2026-09-21 |
|---|---|
| persons with name variants across sources | 997 variant rows over the person population |
| a genuine false-positive pair — two different people who fuzzy-match strongly | **75** crosswalk rows in the `false_positive` band with `is_true_match = false`, scoring **0.9091 to 1.0000**; 23 of them on persons who appear in a chain |
| a person crossing a sanctions list below certainty | **19** screening results, **every one** in the review band, scoring **0.7097 to 0.8364**; 6 of those persons appear in a chain, across 7 anchors |
| a declared confidence policy | `resolution_policy`: `auto_clear` 0.95, `merge_threshold` 0.90, `review_floor` 0.70, at `policy_version` `kyc-resolution-v1` |

**Without the false positive, `min_confidence` looks like overhead.** The
estate supplies it 75 times over, at scores high enough that an exact-match
system and a naive fuzzy-match system fail in opposite directions on the same
data. That is the demonstration.

### A.3 A refusal is an answer

An entity with no chain is served computed-empty, never refused. A principal
without the residency entitlement receives a product with the EU-resident
persons absent — and that absence is **not** disclosed as a count, because a
count of what was withheld is itself disclosure. A question above the caller's
debt tolerance is withheld with a replay reference.

---

## B · Contract

### B.1 The nine elements

| element | value |
|---|---|
| **class** | `compliance.beneficial-ownership` |
| **lane** | `1.0.0` |
| **subject** | an entity `lei` |
| **intent** | `kyc-refresh`, `onboarding`, `enhanced-due-diligence` — and the intent **selects the threshold** (§B.4) |
| **freshness** | `event-driven` |
| **TTL** | 24 h, `ttl_anchor: from_entity_freshness` anchored on the sanctions publish date |
| **assembly mode** | 1 — algorithmic throughout; **no LLM on any path** |
| **operators** | `policy.principal-subgraph`, `similarity.corpus-select`, `temporal.as-of-boundary`, `traversal.typed-neighborhood` |
| **declared gate** | `cp-15.ownership-holds` |

### B.2 Classification and residency

Vocabulary: `public`, `internal`, `person-restricted`. A person record whose
subject is an EU resident carries `person-restricted`, and it is admitted only
for a principal whose `sees_eu_person_data` is true — **the estate's own
column, not a declaration of this deployment's**.

### B.3 Model-risk annotation

Not applicable — assembly mode 1. Resolution confidence is carried, never
computed by inference: the estate's `person_crosswalk.match_score` and
`sanctions_screening_result.score` are read as evidence. Whether they are
carried or recomputed is part of `Q14` (§F.4).

### B.4 Request parameter surface

Designed against the rule published at
`public/how-to/condition-acquisition-on-the-verified-credential.md`: *if
changing the value could give the caller more than its credential permits, it
is envelope input; if it can only ask for less, it can be a request
parameter.*

| parameter | type | what it moves | default | why |
|---|---|---|---|---|
| `as_of` | ISO-8601 instant | the decision instant and the valid-time cut | `asked_at` | narrows; cannot admit a person the entitlement excludes |
| `threshold` | number | the reporting threshold, 0..100 | **per `intent`, from the estate** | see below |
| `max_depth` | number | how deep the ownership walk goes, 1..10 | 6 | can only ask for less |
| `min_confidence` | number | the resolution floor, 0..1 | `resolution_policy.review_floor` | see below |
| `debt_tolerance` | number | the caller's ceiling on assessed debt | class default | the standard surface |

**Not on the request, and refused if named:** `jurisdictions`. The vault
specification offers it as a request parameter defaulting *per entitlement*.
**This specification declines it**, and the rule decides: a caller naming a
jurisdiction set could name one wider than its entitlement, which is strictly
more than the credential permits. The permitted jurisdiction set is envelope
input, derived at the acquisition seam from
`principal_jurisdiction` and `principal.sees_eu_person_data`.

**`threshold` and `min_confidence` are request parameters that can only narrow
*upward*.** Raising a threshold reports fewer persons; raising a confidence
floor clears fewer matches. Lowering either would report *more*, which is why
both are **floored by the estate's own declared value** and a request below
the floor is refused by name rather than honored — the same shape as rung 18's
`signal_types` bound. This is the one place the published rule needed a
second reading, and it is recorded as such.

**`include_cycles` and `screen_sanctions` are declined**, for rung 18's
reason: a payload whose shape the caller chooses makes an empty member
informative about the subject. Cycles and screening results are always served
to a perspective whose plan carries them.

### B.5 Prerequisites and scope boundary

**Prerequisites.** `corporate-family-tree` and `counterparty-reference-snapshot`.
Neither has a canonical producer to require — cp-01 is a frozen specimen — so
**this rung reads the reference rows itself** and records that as an
example-scope decision rather than a composition.

**Out of scope, named:** the human's decision itself (the queue is exercised;
a person releasing or rejecting is a test, not a product feature), any
generative narrative, the sanctions list's own curation, and any
recommendation about whether to onboard.

---

## C · Data catalog

### C.1 Element table

Measured read-only 2026-09-21.

| element | store | table / collection | volumetrics | class |
|---|---|---|---|---|
| ownership chains to person level | PostgreSQL | `bo_chain` | 50 rows, 50 anchors, 46 persons; depth 2–6; effective ownership 1.86 %–67.23 % | internal |
| the hops behind each chain | PostgreSQL | `bo_chain_hop` | 169 rows | internal |
| person records | PostgreSQL | `psc_person`, `person` | 210 PSC persons (35 EU nationals), 954 person rows | person-restricted / internal |
| name variants | PostgreSQL | `person_name_variant` | 997 rows | internal |
| cross-source resolution | PostgreSQL | `person_crosswalk` | 1,815 rows; bands `exact` 992, `strong` 521, `review` 177, `weak` 50, **`false_positive` 75** | internal |
| the confidence policy | PostgreSQL | `resolution_policy` | 3 thresholds at one `policy_version` | internal |
| sanctions screening | PostgreSQL | `sanctions_screening_result` | **19, all in the review band**, 0.7097–0.8364 | internal |
| sanctions lists | PostgreSQL | `sanctions_entry`, `sanctions_name` | 19,730 / 45,511 | public |
| thresholds by jurisdiction **and intent** | PostgreSQL | `bo_threshold` | 18 rows; GB `onboarding` 25 %, GB `enhanced_due_diligence` **10 %**, `sanctions_screening` 0 % | internal |
| refresh state | PostgreSQL | `kyc_refresh_state` | 50 clients, **19 overdue** | internal |
| residency entitlement | PostgreSQL | `principal`, `principal_jurisdiction` | 4 principals, **1 with `sees_eu_person_data`**; 17 jurisdiction grants | internal |
| KYC documents and passages | MongoDB | `kyc_document`, `passage` | 32 documents in five kinds | internal |
| the ledger instant | Fluree | `fibo-v2` | the `t` watermark | — |

### C.2 Capability decomposition

`relational` (six reads), `document-passage` (one), `bitemporal-ledger` (the
watermark), `in-memory` (the threshold and confidence evaluation). **No vector
index.**

### C.3 Correlation key

`lei` anchors the question; `person_key` correlates chains, variants,
crosswalks and screening. **Person identity across sources is the unresolved
join, and that is the point** — `person_crosswalk` is the estate's record of
how well it resolved, not an assertion that it did.

### C.4 The data traps, each with the binding chosen

**Trap 1 — there are no ownership cycles.** §0.3. The vault specification's
headline counterfactual has zero supporting rows. Binding: surfaced to Dave at
§F.4.2, never simulated.

**Trap 2 — one chain per anchor.** 50 chains over 50 anchors: every entity has
**exactly one** beneficial-ownership chain and one terminal person. So a
threshold test yields at most one reportable person per entity, and no anchor
has both an above- and a below-threshold owner (measured: zero). The product
is honest about this — it serves *the* chain and its finding, not a set — and
`IBO`-style set assertions would be vacuous. Binding: the gates assert the
relationship between the chain and the threshold, never a count of owners.

**Trap 3 — 33 of the 50 chains fall BELOW the 25 % reporting threshold**, and
17 of those are between 10 % and 25 %, which is exactly the band GB's
`enhanced_due_diligence` threshold reaches and `onboarding` does not. So the
intent genuinely changes the answer on real data, and the sub-threshold
population — the review-queue case — is the majority of the estate rather than
a contrived corner.

**Trap 4 — every sanctions screening result is in the review band.** All 19
score between 0.71 and 0.84, none clears `auto_clear` (0.95) and none falls
below `review_floor` (0.70). The estate supplies **no** auto-cleared and **no**
auto-rejected screening. Binding: the product's screening member is therefore
*always* a review finding; the gate asserts the disposition follows the policy
thresholds rather than asserting a mix that does not exist.

**Trap 5 — three KYC documents contradict the computed chain.** One declares
7.24 % where the chain computes 48.97 %. Binding: the declaration is served as
a *document claim* beside the computed figure, never reconciled into it; the
contradiction is the finding.

**Trap 6 — `controls` has zero assertions in the graph** (recorded in the
vault specification and unchanged). An ownership traversal matching only
`controls` returns empty on data `owns` resolves. Binding: the chain is read
from the relational `bo_chain` tables, which is where this estate materialized
it; the Fluree read is the watermark only.

---

## D · Assembly recipe

### D.1 Client call

```
make -s example-cp-15 LEI=--lei=<an anchor entity>
make -s example-cp-15 INTENT=--intent=enhanced-due-diligence   # a 10% threshold, not 25%
```

### D.2 Operator step table

| # | step | category | store | emits |
|---|---|---|---|---|
| 1 | the entity, the refresh state and the envelope | — | PostgreSQL | the permitted jurisdiction set and the residency entitlement |
| 2 | the threshold in force for this intent and jurisdiction | — | PostgreSQL | the applicable threshold |
| 3 | Policy | `policy.principal-subgraph` | — | the classification-contained view |
| 4 | Similarity | `similarity.corpus-select` | MongoDB | the supporting KYC passages |
| 5 | Temporal | `temporal.as-of-boundary` | — | the valid-time cut |
| 6 | Traversal | `traversal.typed-neighborhood` | — | the ownership neighborhood |
| 7 | Evaluate | in-memory, the deployment's own | — | the threshold test, the confidence test, the findings |
| 8 | **Review submission** | — | the SDK's `ReviewQueue` | one pending event per finding (§F.4) |

### D.3 Step detail — and where the new thing sits

**1. The envelope, from the credential.** The verified principal's
`sees_eu_person_data` and its `principal_jurisdiction` rows decide which person
records may be materialized at all. A person the envelope excludes is **never
minted**, so nothing downstream can serve it by mistake. *This is the A2 seam,
written against the adopter page, measured in §G.2 and not redesigned.*

**2. The threshold.** `bo_threshold` is keyed by jurisdiction **and intent**,
so the same entity under `onboarding` and under `enhanced_due_diligence` gets
different reportable sets. The caller may raise the threshold and may not
lower it below the estate's floor.

**3–6. The four operator categories**, composed in `CATEGORY_ORDER`.

**7. Evaluate.** Persons at or above the threshold are *reportable*. Persons
below it, and resolutions below `min_confidence`, become **findings kept
inside the product** — the vault specification's own words: *a low-confidence
match is a finding, not an absence.*

**8. Review submission — the genuinely new step.** Each finding is submitted
to `ReviewQueue.submit_for_review` with the served product's content address
bound to it. The convention this needs is `Q14`, §F.4.

### D.4 Determinism class

Class 1 — fully deterministic. The same entity, instant, intent and principal
hash to the same bytes.

### D.5 Replay statement

The determination replays from its own record. **The product's own record
carries `NO_HITL_ACTIONS` by construction** — submission is the producing
agent's side, not a human action — and a human verdict lands on a *second*
record linked by the content hash. That two-record shape is `Q14`'s second
half.

### D.6 Emitted contract

Members, fixed per perspective: `principal`, `as_of`, `entity`,
`applicable_threshold`, `intent`, `ownership_chain`, `reportable_owners`,
`sub_threshold_findings`, `resolution_findings`, `sanctions_findings`,
`cycle_findings`, `document_declarations`, `review_submissions`,
`refresh_state`, `entities_in_view`, `edge_types_served`.

`cycle_findings` is **present and empty** for every entity in this estate
(§0.3) — present because the shape must not vary with the subject, empty
because there are no cycles, and the emptiness is disclosed in the README and
the findings rather than read as *"no cycle here"*.

### D.7 Validation gates

The SDK's three, plus the declared gate `cp-15.ownership-holds`: residency
containment, confidence disclosure (every person carries one), threshold
correctness (every reportable owner is at or above the applicable threshold
and every sub-threshold finding is below it), review linkage (every finding
has a submission and every submission names the served content address), and
shape by perspective.

---

## E · Volatility, debt and materialization

### E.1 Half-life

Sanctions ~1 day — *"a same-day addition is the highest-severity supersession
in the catalog"*. The PSC register ~30 days. Crosswalks and chains
`supersede-only`. The KYC document `supersede-only`. **Whether any of these
needs an illustrative calibration is `[TBC-2]`**, measured before declared.

**A standing state is its own observation type** (`D-GATE-cp-18`): a chain's
effective percentage is true *as of now* and carries no event date, while a
sanctions publication and a PSC filing happened on a day. They go in different
classes with different decay, and a `valid-from` class will refuse an undated
claim rather than anchor it silently.

### E.2 Debt

`D_c = 1 − F·C·S`. `CP17-F-12`'s scorer semantics apply unchanged.

### E.3 Materialization

Derived on demand. **Sanctions screening is never cached** — the whole
obligation is same-day.

### E.4 Supersession

An OFAC daily delta; a PSC filing; a refresh falling due. Note the recorded
SDK fact: an ownership *change* reaches the invalidation register only when the
reified ownership node is an **entity** claim, because relationship
supersession never calls the sink.

---

## F · Source binding and readiness

### F.1 Element readiness

Every element in §C.1 is present and measured, **except ownership cycles,
which are absent entirely** (§0.3).

### F.2 Every `[TBC]`, with an owner

| id | question | owner | route |
|---|---|---|---|
| `TBC-1` | Which credential maps to which principal? | this deployment | the estate registers four principals **with the residency axis already on them**, so only the credential → principal half is declared |
| `TBC-2` | Does any half-life need an illustrative calibration? | build | measure first, declare only if the term cannot be shown discriminating |
| `TBC-3` | Does the product carry the estate's stored confidence, or recompute it? | **Dave, at this Gate** | §F.4, part of `Q14` |
| `TBC-4` | `Q14` — the product-scoped review convention | **Dave, at this Gate** | §F.4 |

### F.3 Access path

Three stores under `CCF_CP_15_*` names, every one read-only. No new substrate.

### F.4 `Q14` — THE HITL CONVENTION, RULED 2026-09-21

**Approved by Dave. What follows is the convention, not a proposal.**

| element | ruled value | the reason, as ruled |
|---|---|---|
| `workflow_state_ref` | **the originating product's replay-RECORD reference** | it identifies *the exact governed determination that caused the human review*. **Not the content address**, and the reason is precise: **identical product bytes can participate in different governed determinations**, so an address alone cannot name which one referred the finding |
| `output_ref` | **the Context Product's content address** | the review item therefore carries **both** — the determination that created the referral, and the immutable product being reviewed |
| `lineage` | one evidence reference **per flagged person, where the product has that evidence** | **references are not manufactured** for members with no supporting evidence; a lineage entry pointing at nothing is worse than none |
| the product's own record | **`NO_HITL_ACTIONS` by construction** | the human action has not happened when the product is served |
| confidence | **the estate's, carried as evidence** | **not recomputed inside the HITL layer** — recomputing would invent a second authority and make the product disagree with the source it cites |

**THE HUMAN ACTION.** The original Context Product and its replay record are
**immutable**, and human review **does not modify either**. The disposition
creates a **second workflow/audit determination record** linked to: the
originating `workflow_state_ref`; the originating product `output_ref`; the
reviewer identity; the action or verdict; the timestamp; and any required
review rationale or evidence.

**That second record is NOT a Context Product** unless it independently
satisfies the Context Product contract, and **no synthetic "review product" is
required for this rung.** This rung does not build one.

### F.4.1 THE CONSTRUCTION BOUNDARY — load-bearing, and gated

**Ruled, and this is the part the gates must carry:**

> The Context Product must be **completely assembled, governed, assessed and
> immutable before enqueue**. The human review workflow **consumes its
> references**. HITL must not become part of Context Product construction, or
> a way to repair incomplete context manually.

Three consequences, each gated (`UBO-G19`, `UBO-G20`):

- **Enqueue happens after serve, never during assembly.** The queue is handed
  a content address and a replay reference that already exist. There is no
  path on which a pending review changes what the product says.
- **A referral cannot complete a product.** A finding referred for review is
  *served inside the product* as a finding; it is not a hole the reviewer
  fills.
- **The served bytes are the same whether or not a review was submitted.**
  This is the sharpest expression of the boundary and the one a sabotage can
  break: assembling with the queue disconnected must produce **byte-identical**
  output.

### F.4.2 The cycle counterfactual — RULED: do not engineer

**Ruled by Dave, 2026-09-21:** *"Do not engineer ownership cycles into the
estate for CP-15."*

**Measured estate fact, recorded as such:** no ownership cycles exist in the
current curated estate. The cycle-shaped product member is **kept** and served
**honestly as empty**, with that condition disclosed. The two planted cycles
the vault's manufacture envelope specifies are **not requested** — the
name-resolution counterfactual and the existing ownership, sanctions and
document contradictions provide sufficient non-vacuous evidence for this rung.

**The cycle gate proves four things** (`UBO-G19`):

1. absence is represented **honestly** — the member is present and empty, not
   omitted and not filled;
2. **no cycle is invented** — nothing in the served product asserts a cycle;
3. empty cycle evidence **does not invalidate unrelated KYC findings** — the
   reportable owners, the sub-threshold findings, the screening findings and
   the document contradictions all survive an empty cycle member;
4. the product **remains actionable** from the evidence the estate actually
   contains.

---

## G · Operate and govern

Degradation contract: a principal with no jurisdiction grant is refused by
name; an entity with no chain is served computed-empty; sanctions screening is
mandatory and never cached. Lifecycle: `draft` at this Gate.

### G.1 Intended product gates

The acceptance authority for every gate is **this clause** (`D-IMPL-326`).
Each id will be claimed by exactly one executing test. **Every gate is
directional, structural or relational; none pins a count or a date.**

| id | property |
|---|---|
| `UBO-G01` | the served operator plan names Policy before Similarity, read off the product |
| `UBO-G02` | no person record outside the principal's residency entitlement appears in any served product, and no member, count or marker indicates that one was withheld |
| `UBO-G03` | the entitled principal and an unentitled one, same entity same instant, receive different products at different addresses — and the entitled one's is a strict superset of persons |
| `UBO-G04` | every person carries a resolution confidence; none is served without one |
| `UBO-G05` | every reportable owner is at or above the applicable threshold, and every sub-threshold finding is below it |
| `UBO-G06` | the intent selects the threshold: the same entity under two intents yields two applicable thresholds and, where the estate supports it, two reportable sets |
| `UBO-G07` | a request below the estate's declared floor for `threshold` or `min_confidence` is refused by name, never honored |
| `UBO-G08` | a resolution below the confidence floor is a **finding inside the product**, never an absence |
| `UBO-G09` | **every finding has a review submission, and every submission names the served product's content address** |
| `UBO-G10` | the submitted `workflow_state_ref` is the originating **replay-record** reference and resolves — **not** the content address, because identical bytes can participate in different determinations |
| `UBO-G11` | the product's own replay record carries `NO_HITL_ACTIONS` |
| `UBO-G12` | a human verdict lands on a second record linked by the content hash, and the served product is unchanged by it |
| `UBO-G13` | a reviewer binding that echoes the wrong content hash is refused (the TOCTOU guard, exercised through a product) |
| `UBO-G14` | the payload's member set is a function of the perspective and never of the entity or the request |
| `UBO-G15` | a KYC document declaration contradicting the computed chain is served **beside** the computed figure, never reconciled into it |
| `UBO-G16` | the determination replays from its own record to its served bytes |
| `UBO-G17` | an entity with no chain is served computed-empty and is indistinguishable from an entity id that was never issued |
| `UBO-G18` | a principal with no jurisdiction grant is refused by name, as data, with a replay reference |
| `UBO-G19` | **the cycle member is served honestly empty**: present and empty, no cycle asserted anywhere in the product, and the reportable owners, sub-threshold findings, screening findings and document contradictions all survive it — the product stays actionable on the evidence the estate contains |
| `UBO-G20` | **the construction boundary holds**: the product is complete, governed, assessed and immutable before enqueue, and assembling with the review queue disconnected produces **byte-identical** output — HITL is not part of construction and cannot repair incomplete context |

Twenty intended gates, of which **seven (`UBO-G09` to `UBO-G13`, `UBO-G19`,
`UBO-G20`) exist only because of the new coverage shape** — which is the
proportion a Gate-1 delta review should expect when exactly one thing is new.
`UBO-G20` is the construction boundary and is the one Dave named load-bearing.

### G.2 The A2 measurement

Measured again on the same seven dimensions, against cp-13-canonical, cp-17,
cp-19 and cp-18. **Not reconsidered**: `D-GATE-cp-18` fixed the threshold —
revisit the **adopter documentation and the pattern first** if substantially
identical **generic** glue exceeds approximately **30 lines**, or a **fifth
undocumented concept** appears. `D-IMPL-343` is not reopened and no SDK
abstraction is pre-authorized.

---

## Gate 1 summary

**Already proven and reused unchanged:** seven mechanisms (§0.1).
**Genuinely new:** exactly one — a HITL primitive composed with a product.
**Open questions for Dave:** none remaining. Both were **ruled 2026-09-21**:
`Q14`'s convention is fixed at §F.4 with the construction boundary at §F.4.1,
and the cycle counterfactual is ruled *do not engineer* at §F.4.2.
**New SDK mechanism sought:** none.
**Estate:** complete for the name counterfactual, the residency pair, the
threshold-by-intent case and the review band; **empty for ownership cycles.**
**Gate 2:** GO given 2026-09-21 with these rulings folded in. Build minimally
on the existing SDK and the existing HITL primitives; stop only for a missing
KYC-required SDK capability, incorrect SDK behavior, a security or governance
defect, HITL proving uncomposable with the immutable product and replay
references without changing an SDK contract, or the A2 threshold being
crossed.
