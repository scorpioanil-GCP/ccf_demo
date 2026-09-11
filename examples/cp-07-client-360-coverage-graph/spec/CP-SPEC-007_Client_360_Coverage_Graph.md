---
product: coverage.client-360.v1
standard: v0-3
owner: vault
sdk_spec: cp-07
tier: 2
cost_band: "×1–2, approaching ×2–4 at high fan-out"
assembly_mode: 1
capability_classes: [relational, graph-traversal, in-memory]
prerequisites: [counterparty-reference-snapshot, corporate-family-tree]
topic: context-products
title: Client 360 / Coverage Graph — Context Product Specification
generated: '2026-09-10'
---

# Client 360 / Coverage Graph — Context Product Specification

**`CP-SPEC-007` · rung 07 · Tier 2 · `coverage.client-360.v1`**
**Fluree `fibo-v2` for the coverage and interaction graph · PostgreSQL `ccf_v2` for people, bankers, interactions and policy**

> Who at the bank knows whom at the client, and through what. **The tier at
> which traversal cost stops being free.**

## 0 · What this document is

**Gate 1. No implementation code exists** (`D-IMPL-321` — cp-07 returns to Gate
1 first; cp-06's spec-after-build inversion was disclosed, not a template).

Every figure below was **measured against the curated `.76` estate on
2026-09-10** before this document was written.

### 0.1 Placeholder discipline

`[TBC — <owner>]` markers reappear at §F.2 with an owner. An unmarked
assumption is a worse defect than a marked gap.

### 0.2 Front matter

| Field | Value |
|---|---|
| Registry name | `coverage.client-360.v1` |
| Tier | **2** — `relational`, `graph-traversal`, `in-memory` |
| **Assembly Mode** | **1 — pure algorithmic, DECLARED.** Relationship strength is deterministic arithmetic over policy-versioned weights; no LLM is reachable from any step |
| Cost band | **×1–2, approaching ×2–4 at high fan-out** — the first rung where the band moves with the question |
| Lifecycle state | **`draft`** — Gate 1 submitted, nothing built |
| Accountable owner | product: Coverage · data steward: CRM and HR · policy owner: need-to-know classification |
| Last review | 2026-09-10 |
| What it resolves | One client LEI to **the bank's own relationship graph with it**: which client-side officers exist, which bankers cover them, through which interactions and how recently — and **where the gaps are** |
| Four-question test | **YES / YES / YES / YES** — §0.4 |
| Build order | Seventh. Depends on rung 01 for identity and rung 04 for the family traversal |

### 0.3 Capability gate — above §A because it schedules the build

**Buildable. The estate has every capability, and one hazard is structural
rather than absent:**

| Sub-capability | Present? | Consequence |
|---|---|---|
| Depth-bounded traversal over typed edges | **yes** | rung 04's pattern, reused |
| Bounded traversal with in-traversal ordering | **the hazard** | `limit` must be applied **inside** the walk, ordered by recency. Fetching everything and truncating in memory satisfies the contract and defeats its purpose |
| Untyped ISO-8601 date comparison | **required** | this Fluree build corrupts `^^xsd:date`; `since` is compared as a string, which is correct because ISO-8601 sorts lexicographically |

### 0.4 The four-question test

| # | Question | Evidence | |
|---|---|---|---|
| 1 | Changes with **who is asking**? | 10 interactions are `need_to_know` and 18 are `mnpi_bearing`. A principal without clearance gets a **different graph**, not a redacted one | **yes** |
| 2 | Has a **validity window**? | interaction recency is the dominant signal and moves daily; λ_c ~7 days | **yes** |
| 3 | Must be **reconstructible**? | relationship strength is computed from policy-versioned weights; a score without its weights is unauditable | **yes** |
| 4 | Composed at runtime from sources **no schema author pre-joined**? | **Yes, measured.** Answering it joins `person_role`, `interaction`, `interaction_participant`, `banker`, `coverage_assignment` — five tables, 12,889 rows, joined at decision time and nowhere else | **yes** |

---

## A · Decision frame

**Decision and trigger.** A CIB banker preparing for a client meeting, or a
coverage head asking §1.4's canonical question: *"who at the bank has a
relationship with the CFO at this client?"*

**Consuming principals.** Single role at this tier (`coverage-banker`). The
role split is deferred to rung 18.

### A.1 Counterfactual — `context-starved`

**Closed-taxonomy member: `context-starved`.**

A CRM answers *"who is the covering banker?"* — one field. It cannot answer
*"who has met this person, in what capacity, how recently, and alongside which
colleagues?"* — **because that is a path, not a field.** The relationship
exists in the estate as five tables nobody joins at decision time.

### A.2 The second failure this rung surfaces: FAN-OUT

Where rung 04 fans out over entities, this fans out over **people, meetings and
interactions**. Measured: `JJAX4X60DE65EYFOTY73` carries **240 interactions**
against a declared `limit` of 200. **This is the first product in the catalog
where an unbounded traversal is a genuine operational hazard**, and where
`limit` and `since` are correctness features rather than conveniences.

### A.3 Fixture `C36-F01` — the counterfactual, falsifiable

1. Read `ccf_v2.coverage_assignment` for a client. It names the covering
   banker(s) and nothing about whom they have actually met.
2. Ask the product the same client. It returns the officers, the interactions
   that reached them, the recency, **and the officers nobody has met**.
3. **The CRM row cannot produce step 2's last clause.** Measured: client
   `529900L7KB2N9KXCDI76` has **9 named officers with zero bank-side
   interaction** — the insight the product exists to deliver, and one no
   coverage field contains.

---

## B · Contract

### B.1 The nine elements

| # | Element | Value |
|---|---|---|
| 1 | **Schema** | `client_360_coverage`. Entities: client entity, person, banker, interaction, deal. Relationships: `employedBy`, `coversClient`, `participatedIn`, `relatedToDeal`. Measures: relationship strength, recency, **coverage gaps** |
| 2 | **Freshness SLA** | daily for interactions; quarterly for the contact hierarchy |
| 3 | **TTL** | 12 hours · `ttl_anchor: from_decision` — **unlike rungs 02/04/06**: the answer is about the bank's own current posture, not about a filed document's age |
| 4 | **Policy Binding** | entitlement scope; **need-to-know on interaction content**, applied BEFORE traversal; MNPI suppression pending rung 17 |
| 5 | **Lineage** | `operators_invoked` · `graph_snapshot_at` · `policy_version` · `projection_plan_id` · `context_debt`. **Two registered operators**, per §D.2.1 |
| 6 | **Semantic Version** | `v1.0.0`; migration window `[TBC — product owner]` |
| 7 | **Discovery** | `coverage.client-360.v1` |
| 8 | **Addressability** | `/context-products/coverage/client-360/{lei}` |
| 9 | **Assembly Mode** | **1 — pure algorithmic.** §2.3 model-risk annotation not applicable, by decision |

### B.2 Request parameter surface

| Parameter | Type | Moves | Default | Expected effect |
|---|---|---|---|---|
| `lei` | string, **required** | anchor | — | unresolvable ⇒ refusal |
| `principal_scope` | array, **required** | `P` envelope | — | the admitted set |
| `since` | string (ISO date) | `T` window | −365 days | narrows the interaction window |
| `limit` | int ≤ 500 | `R` bound | 200 | **truncation disclosure fires at 240 on `JJAX4X60DE65EYFOTY73`** |
| `include_family` | bool | `R` scope | `true` | extends the anchor set to the corporate family |
| `include_need_to_know` | bool | `P` envelope | `false` | 10 interactions appear or do not |

**`limit` and `since` are required bounds, not optional refinements.** A
traversal without them can return a graph large enough to breach the SLO
envelope. `intent` is **not** declared as an argument — it is a top-level
`ProductRequest` field on this SDK (`D-IMPL-264`).

---

## C · Data catalog

| Element | Provenance | Class | Store | `G` | Measured |
|---|---|---|---|---|---|
| Client entities and family | inherited from rung 04 | public | Fluree / Postgres | `E`,`R` | 50 anchors |
| Named officers, roles, appointment dates | DEF 14A; Form 3/4/5; 8-K 5.02 | public | Postgres | `E`,`T` | **817 roles over 954 people** |
| `employedBy` edges — asserted as FIBO **`isEmployedBy`** | derived from DEF 14A / Form 4 | public | **Fluree** | `R` | **701** |
| Banker roster | internal HR | synthetic — internal | Postgres | `E` | **40** |
| `coversClient` edges | internal CRM | synthetic — internal | **Fluree** | `R` | **150** |
| Coverage assignments | internal CRM | synthetic — internal | Postgres | `E` | **1,000** |
| Interaction participants (attributes) | internal CRM | synthetic — internal | Postgres | `E` | 8,032 rows — **attributes only; the EDGE is Fluree's** |
| Interaction records | internal CRM | synthetic — internal | Postgres | `E` | **2,050**, 2024-08-24 → 2026-08-18 |
| **`ex:participatedIn` edges** | internal CRM | synthetic — internal | **Fluree** | `R` | **8,032 assertions over 731 subjects** (694 `ex:person-*`, 37 `ex:banker-*`) |
| Deals and **`ex:relatedToDeal`** | internal deal system | synthetic — internal | Postgres / **Fluree** | `E`,`R` | 32 deals; **129** edges |
| Scoring weights | internal coverage policy | synthetic — internal | Postgres | `P` | `scoring_weight` 6 |
| Need-to-know classification | internal | synthetic — internal | Postgres | `P` | **10 flagged; 18 MNPI-bearing** |
| Person name variants | derived | synthetic — internal | Postgres | `E` | **997 over 781 people** |

**The public-to-synthetic ratio INVERTS here**, and that is the point rather
than a weakness. The *client side* is public — DEF 14A names officers with
roles and dates. Every *bank-side* element is necessarily invented, because
interaction history exists nowhere public. **That is an accurate depiction of
the problem: no vendor can supply the bank's own graph, which is exactly why the
fabric has to assemble it.**

### C.1 Envelope, checked

| §F requirement | Required | Measured | |
|---|---|---|---|
| anchor clients | ~50 | **50** | ✅ |
| people per client | 8–25 | **9–33, avg 16.3** | ✅ (max exceeds) |
| bankers | ~40 | **40** | ✅ |
| interactions over 24 months | ~2,000 | **2,050**, 24-month span | ✅ |
| ≥1 client exceeding `limit=200` | ≥ 1 | **exactly 1** — 240 | ✅ |
| name variants | ≥ 5 | **997** | ✅ |
| coverage gaps | ≥ 3 | **9 on one client** | ✅ |
| need-to-know interactions | ~10 | **10** | ✅ |

### C.2 The traps

1. **Person identity is the hard join.** DEF 14A gives names, Form 4 gives a
   CIK, CRM keys on an internal id. The crosswalk is imperfect **on purpose** —
   997 variants over 781 people — because a demo where everyone resolves
   cleanly teaches the wrong lesson.
2. **§C's four short names span TWO NAMESPACES, and one is also renamed.**
   This trap cost this document a false claim before `ccf-dataprep` corrected
   it: an earlier draft asserted *"no corresponding predicate was found in
   `fibo-v2`"* on the strength of a search that only looked at `ex:` local
   names. **The predicate was there all along.**

   | §C says | actually asserted as | count |
   |---|---|---|
   | `participatedIn` | `ex:participatedIn` | **8,032** |
   | `coversClient` | `ex:coversClient` | **150** |
   | `relatedToDeal` | `ex:relatedToDeal` | **129** |
   | `employedBy` | **FIBO `isEmployedBy`** | **701** |

   Three are `ex:`, one is FIBO — and the FIBO one is renamed. A search
   assuming one namespace, or assuming §C's name is the local name, misses it.

   **And a decoy.** `ex:participationIn` and `ex:participationOf` (97 each) are
   the Wave 18 **syndicate** reification — same word, unrelated domain. Easy to
   find those, conclude *"that is not it"*, and move on.

   **A third reason an enumeration misleads:** `COUNT(*)` under-reports on
   multi-pattern clauses and `GROUP BY ?p` invents predicates that do not
   exist, so neither can be used to enumerate what a ledger holds. **Every
   count in this document is client-side over enumerated rows.**

3. **The R/E split is deliberate and enforced.** `validators/partition.py`
   allowlists `ex:participatedIn` among six Wave 10 edges a
   Person/Banker/Interaction/Deal node may carry: **Fluree owns the edge (the
   traversal), Postgres owns the attributes.** Nothing is duplicated —
   `party_kind` is not on the Fluree edge at all, it is encoded in the subject
   URI prefix (`ex:person-*` / `ex:banker-*`), which this build verified:
   731 subjects, 694 person and 37 banker. Single-writer holds.
4. **Silent truncation reads as completeness** and is the quiet failure mode of
   every bounded traversal.

---

## D · Assembly recipe

### D.1 Client call

```
GET /context-products/coverage/client-360/JJAX4X60DE65EYFOTY73
      ?principal_scope=…&since=2025-09-10&limit=200&include_family=true
```

### D.2 Step table

| # | Step | Operator | Store | Emits |
|---|---|---|---|---|
| 1 | Resolve the client, then its corporate family | `null` (L1 source access) | Postgres | canonical entity, name, family LEIs |
| 2 | Interactions within `since`, **ordered by recency, `limit` applied IN the read**; need-to-know excluded **in the `WHERE` clause** | `null` (L1 source access) | Postgres | admitted interactions, availability counts |
| 3 | Read the four declared edges for the **bounded** interaction set | `null` (L1 source access) | Fluree | typed edges, ledger `t` |
| 4 | Batch enrich — **one query per node type, regardless of graph size** | `null` (L2) | Postgres | people, bankers, deals |
| 5 | Admit to the fabric — **thin edges first, attributed nodes last** | `null` (L2, the single writer) | **L3** | the admitted coverage graph |
| 6 | Entitlement scope over the **admitted** graph | **`policy.principal-subgraph`** | **L3** | the principal's subgraph — a scope the caller does not hold yields an EMPTY graph, never a redacted one |
| 7 | Typed neighborhood over the **admitted** graph | **`traversal.typed-neighborhood`** | **L3** | the four declared edge types, within the backend depth ceiling |
| 8 | Score and find gaps | `null` (Π) | — | strength, recency, **gaps**, the evidence boundary |
| 9 | Govern, gate, record, serve | the SDK's | — | `ServedProduct` / `RefusalEnvelope` |

**Steps 6 and 7 are the only rows with a non-null Operator, and that is the
whole content of the column.** `operators_invoked` equals exactly
`{policy.principal-subgraph, traversal.typed-neighborhood}` and the plan orders
them 6 then 7 — policy **before** traversal, so a node the principal may not see
is never a seed and no edge to it is ever walked.

**The layer split in this table is load-bearing and an earlier revision of it was
wrong.** Steps 1–4 are *source access* against the two estates; step 5 is L2
admission through the single writer; steps 6–7 are *registered L4 operators
reading L3*. The Fluree read in step 3 is **not** the traversal operator — they
touch different stores, at different layers, at different times, and conflating
them makes the graph leg look like an operator invocation it is not. The
previous table named `traversal.typed-neighborhood` on the Fluree row and omitted
`policy.principal-subgraph` entirely, which contradicted §D.2.1 one paragraph
below and contradicted the product's own lineage. Corrected 2026-09-10 after
`D-GATE-cp-07`; the defect was in this document only and never in the shipped
product. `tests/examples/test_cp_07_output.py::test_the_spec_step_table_names_exactly_the_registered_operators`
now holds the table and the declaration to each other.

**Step 2's bound is a correctness feature.** Fetching 5,000 rows and slicing to
200 in memory satisfies the contract and defeats its purpose. So is its policy
clause: an interaction the principal may not see is never materialized, so no
participation edge to it is ever walked.

### D.2.1 Two registered operators, not five verbs

The vault lists `[Resolve, Policy, Traversal, Enrich, Score]`. On this SDK only
`policy.principal-subgraph` and `traversal.typed-neighborhood` are registered L4
operators; Resolve/Enrich are source access and Score is Π. A Standard verb that
is not a registered operator **does not enter `operators_invoked`**.

**`Resolve` is therefore `null` in the table above on purpose, not by omission.**
The SDK registers five operator keys in total — `policy.principal-subgraph`,
`similarity.corpus-select`, `temporal.as-of-boundary`,
`traversal.typed-descendants`, `traversal.typed-neighborhood` — across the four
canonical categories the whitepaper §7.4 commits to (Traversal, Temporal, Policy,
Similarity). There is no Resolve operator and no Enrich operator to name. Writing
one into the Operator column would put it into `operators_invoked`, and lineage
strict equality would then seal a document claiming work no operator did.

**The policy operator is not decorative.** Measured against the curated estate at
one instant, the same client under an entitled scope and a scope the caller does
not hold:

| `principal_scope` | bankers | people | edge types present |
|---|---|---|---|
| the client's own | 23 | 22 | `coversClient`, `employedBy`, `participatedIn` |
| a scope not held | **0** | **0** | — |

An empty graph, not a redacted one.

### D.3 Validation gates

Three from the SDK, and **a fourth this product declares**:

> **Truncation disclosure.** If `limit` was reached, the payload must say so.

Supplied as a `product_gate` with a declared identity — `D-IMPL-282` requires
one, or replay has nothing to stamp on a refusal the gate produced.

### D.4 Falsifiable replay test

Same client, same `since`/`limit`, same estate, **same pinned decision instant**
⇒ same content address. Change `limit` alone ⇒ address differs, operator plan
**unchanged**. The instant must be pinned: it enters the address.

---

## E · Volatility, debt, materialization

| Signal class | `λ_c` | basis |
|---|---|---|
| Interaction records | **90 days** | ILLUSTRATIVE — see below |
| Relationship-strength score | **90 days** | ILLUSTRATIVE — see below |
| Coverage assignment | ~180 days | reorganization cadence |
| Client officer roster | ~365 days | proxy-statement cadence |

**ILLUSTRATIVE CALIBRATION (Dave, 2026-09-10).** The first two rows read
`~7 days` when this section was first written, before the product was built
against the estate. Measured, that calibration made `D_c` read `fail_closed` on
every anchor and **inverted the ordering between a stale relationship and a
current one** — the term had stopped measuring recency. This example runs
against a point-in-time demonstration estate rather than continuously refreshed
production data; these half-lives are calibrated so the governed behavior is
observable in that snapshot. They demonstrate how the SDK applies the control and
**are not recommended production coverage-policy thresholds**. Nothing else is
adjusted to reach an answer: no timestamp is faked and `asked_at` is the real
decision instant. `examples/cp-07-client-360-coverage-graph/FINDINGS.md`
`CP07-F-01` carries the measurement and the ruling.

**Debt.** `F` from interaction recency against λ_c; `C` = people the enrich leg
resolved ÷ people the walk admitted; `S` = `[TBC — §F.2 row 3]`.

**Materialization: derived on demand.** Interaction recency is the dominant
signal and moves daily; a materialized graph would misstate the very thing the
product measures.

---

## F · Source binding and readiness

### F.1 Readiness

Every §C row is loaded and measured except `employedBy`, which is `[TBC]`.

### F.2 Every `[TBC]`, with an owner

| # | Item | Owner | Cleared by |
|---|---|---|---|
| 1 | ~~`employedBy` edge count~~ | — | **CLOSED** — asserted as FIBO `isEmployedBy`, **701** |
| 2 | ~~Fluree edge or Postgres table~~ | — | **CLOSED — it STAYS A FLUREE EDGE.** `ccf-dataprep`, 2026-09-10: going relational *"would break the traversal the product exists to demonstrate. This product's whole thesis is that coverage is a graph question; answering it with a join is the counterfactual, not the product."* |
| 3 | What `S` measures for a coverage graph | product owner | a definition |
| 4 | Semantic-version migration window | product owner | §G |
| 5 | ~~`include_family` in v1 scope~~ | — | **CLOSED — IN SCOPE** (Dave, 2026-09-10) |

### F.3 Access path

Fluree `fibo-v2`, PostgreSQL `ccf_v2`, **both read-only**, v2 namespaces.

---

## G · Operate and govern

### G.1 Product gates

| Gate | Asserts |
|---|---|
| `C36-G01` | a narrower `since` returns no more interactions than a wider one |
| `C36-G02` | a lower `limit` returns no more than a higher one |
| `C36-G03` | **truncation is disclosed** when `limit` is reached |
| `C36-G04` | `include_need_to_know=false` excludes the 10 flagged interactions |
| `C36-G05` | coverage gaps are reported and non-empty on the measured client |
| `C36-G06` | the enrich leg issues a fixed number of queries regardless of graph size |
| `C36-G07` | replay dimension 2 ⊇ product policy lineage |
| `C36-G08` | `shape_of` is `canonical` and the factory takes operators only from `required` |

**All directional. No estate figure is pinned** — a test asserting 240 would go
red the next time an interaction is logged.

### G.2 Acceptance criteria

1. Every §B.2 parameter changes the result in the tabulated direction.
2. Truncation is disclosed rather than silent, demonstrated on the one client
   that exceeds `limit`.
3. Coverage gaps are served — the insight, not a by-product.
4. The product writes to no source store.
5. `shape_of` canonical; `_sdk_supplied_operator_set` True.
