---
product: credit-risk.collateral-coverage.v1
standard: v0-3
owner: vault
sdk_spec: cp-06
tier: 2
cost_band: "×1–2"
assembly_mode: 1
capability_classes: [relational, graph-traversal, in-memory]
prerequisites: [facility-terms-snapshot, corporate-family-tree]
topic: context-products
title: Collateral & Set-off Coverage — Context Product Specification
generated: '2026-09-10'
---

# Collateral & Set-off Coverage — Context Product Specification

**`CP-SPEC-006` · rung 06 of the vault's ladder · Tier 2**
**Fluree `fibo-v2` for edges, priority and the public register · PostgreSQL `ccf_v2` for valuations, balances and policy**
**Registry name `credit-risk.collateral-coverage.v1` · cost band ×1–2**

> What actually secures an exposure, and what can be applied against it.
> Establishes the typed edge vocabulary — `securedBy`, `setOffAgainst`,
> `nettedUnder` — that §8.5 names as the wholesale graph's distinguishing
> feature, and joins it to the **filed public notice** that fixes a lien's date
> of priority.

## 0 · What this document is

A specification a competent engineer can build from **without a further design
conversation**, authored to
[[spec-standard-v0-3|Context Product Specification Standard v0.3]] and raised
from the vault's Q019-form article `wiki/context-products/content/collateral-and-setoff-coverage.md`.

### 0.1 THIS DOCUMENT WAS WRITTEN AFTER THE BUILD, AND THAT IS A DEVIATION

**Recorded first, because it changes how every claim below should be read.**

`CP-SPEC-004`'s own §0 states the discipline: *"No implementation code before
Gate 1."* The spec is Gate 1, it is ruled on, and only then does code exist. For
cp-06 that order was **inverted** — the implementation was built directly from
the vault article, and this document was authored afterwards on Dave's
instruction to write it and then re-verify the build against it (2026-09-10).

**What is therefore weaker here than in rungs 00–05:** nothing in this document
gated the design. A specification written after the fact can only describe
decisions already taken, and cannot have refused one.

**What is stronger, and is the reason the inversion was recoverable:** every
figure below was **measured against the live estate**, most of them before the
module that now produces them existed. §C's counts, §E's spread and §F's
readiness are observations rather than intentions. Where the build and this
document disagree, §G.3 records the disagreement rather than reconciling it
silently.

**Status:** Gate 1 **NOT** held. This document is submitted for it retroactively.

### 0.2 Placeholder discipline

Every unresolved item carries `[TBC — <owner>]` and reappears at §F.2 with that
owner. **An unmarked assumption is a worse defect than a marked gap**: a marked
gap gets closed, an invented one gets built.

### 0.3 Front matter

| Field | Value |
|---|---|
| Registry name | `credit-risk.collateral-coverage.v1` |
| Tier | **2** — capability classes `relational`, `graph-traversal`, `in-memory` |
| **Assembly Mode** | **1 — pure algorithmic, DECLARED.** No LLM is reachable from any §D step: a resolve, two policy reads, a bounded walk, a batched join and an allocation. Declaring it is a registration-time commitment; an absent Assembly Mode reads as an unwritten purity claim |
| Cost band | **×1–2** (the vault's, Tier 2) |
| Lifecycle state | **`draft`** — built, tested and documented; Gate 1 outstanding (§0.1) |
| Accountable owner | product: Credit Risk · data steward: collateral and lien records · policy owner: credit policy (haircuts) and legal (set-off enforceability) — **roles, not individuals** |
| Last review | 2026-09-10 (this authoring) |
| What it resolves | One credit facility to **what secures it and what can be applied against it**: the collateral it can reach, the priority it holds in each asset, the other facilities competing for the same asset, the deposits the bank may set off, and the public UCC filings behind each lien — including any the register says have been released |
| Four-question test | **YES / YES / YES / YES** — §0.5 |
| Build order | **Sixth on the ladder.** Depends on `facility-terms-snapshot` (rung 02) for the facility anchor and `corporate-family-tree` (rung 04) for the traversal pattern |

### 0.4 Capability gate — stated above §A because it schedules the build

**This product cannot be built without `graph-traversal`, and the estate has
it.** Two sub-capabilities are **absent** and are declared here rather than
discovered in §C:

| Sub-capability | Present? | Consequence |
|---|---|---|
| Depth-bounded traversal over typed edges | **yes** | the walk and its reverse leg are expressible (§D.2 step 3) |
| **Typed `^^xsd:date` literals** | **NO** | this Fluree build corrupts them on write — 65 of 65 filing dates stored wrong, 53 distinct deltas. **Every date in the register layer is an untyped ISO-8601 string and is compared as one.** Recorded upstream as `ccf_dataprep` known-issues §59 |
| **Reliable `COUNT(*)` over a multi-pattern WHERE** | **NO** | answers 17 where the query returns 65 rows. **Every count in this product is taken client-side.** Upstream §60 |

### 0.5 Do you need a Context Product? — the four-question test

| # | Question | Evidence | Verdict |
|---|---|---|---|
| 1 | Does the answer change with **who is asking**, beyond formatting? | `jurisdiction_basis` and `shared_collateral` change the *conclusion*: measured, coverage moves 1.089 → 1.353 and 1.089 → 0.800 on one facility, one estate, one instant. A workout team and a credit officer legitimately need different bases | **yes** |
| 2 | Does the answer have a **validity window**? | Marketable-securities marks decay in ~1 day, real-property appraisals in ~365. Acting on a stale mark misprices recovery | **yes** |
| 3 | Must the answer be **reconstructible** with the policy and freshness state that produced it? | The haircut schedule and the enforceability register are both policy, both versioned, and both change the number. A coverage figure without them is unauditable | **yes** |
| 4 | Is it **composed at runtime** from sources no schema author pre-joined? | **Yes, measured.** Priority lives in Fluree as 95 `ex:CollateralPledge` nodes; valuations live in PostgreSQL; the filed lien record lives in a third place again. `ccf_v2.collateral_pledge` carries **no priority column at all** | **yes** |
| **Result** | | | **BUILD** — four clear yeses |

---

## Section A — Decision frame

**Decision and trigger.** A credit officer sizing loss-given-default, or a
workout team asking what the bank can actually reach if the borrower fails.

**Consuming principals.** Single role at this tier (`credit-officer`). The
`Π` split waiting above this rung is workout versus origination, which want the
same graph under different `jurisdiction_basis` defaults.

### A.1 The counterfactual — `context-starved`

**Closed-taxonomy member: `context-starved`.** The answer needed context that
was never assembled into the frame.

Coverage is a graph question that gets stored as a column. A collateral field on
a facility record answers *"is this secured?"* and not *"by what, shared with
whom, and at what priority?"* One asset frequently secures several facilities,
sometimes at different priorities. **A second-lien position recorded as
"secured" beside a first-lien position recorded identically produces two
facilities that look equally protected and are not.** Meanwhile set-off rights —
deposits the bank holds that can be applied against the obligation — live in a
different system entirely and never enter the frame at all.

### A.2 Fixture `CSC-F01` — the counterfactual, made falsifiable

**The acceptance test, runnable against the curated estate:**

1. Read `ccf_v2.collateral_pledge` for `COL-00044`. It returns two rows —
   `FAC-044206` and `FAC-1F0DF6` — and **four columns**: `facility_id`,
   `asset_id`, `provenance`, `basis`. No priority appears.
2. Read `fibo-v2` for the same asset's `ex:CollateralPledge` nodes. They return
   `FAC-044206 → PrimaryLienPosition` and `FAC-1F0DF6 → SubordinateLienPosition`.
3. **The column-only reader cannot distinguish the two facilities. The graph
   reader can.** That difference is the product.

**Falsification:** if step 1 ever returns a priority column, this counterfactual
is dead in this estate and §A must be rewritten rather than defended.

### A.3 Primitive taught, and the contrast pointer

**Taught:** reified relationship properties — a fact belonging to a *pair*
rather than to either endpoint. **Contrast:** rung 04 walks a graph whose facts
belong to nodes; this rung is the first whose load-bearing fact belongs to an
edge.

---

## Section B — Contract

### B.1 The nine elements

| # | Element | Value |
|---|---|---|
| 1 | **Schema** | `collateral_coverage`. Entities: facility, collateral asset, deposit account, UCC filing, **reified pledge**. Relationships: `securedBy`, `pledgedFacility`, `pledgedAsset`, `pledgedBy`, `setOffAgainst`, `nettedUnder`, `amendedBy`. Measures: coverage ratio, priority-adjusted allocation, unencumbered value, shortfall. IRIs at [[fibo-iri-binding]] and, for the register layer, its Wave 21 section |
| 2 | **Freshness SLA** | **Per signal class** — daily for marketable-securities marks and deposit balances; annual for real-property appraisals and lien structure; 180 days for the haircut schedule. §E.1 |
| 3 | **TTL** | 24 hours ceiling · `ttl_anchor: from_entity_freshness`. The expiry follows the collateral evidence, never the request |
| 4 | **Policy Binding** | Entitlement scope (`borrower_scope`); the haircut schedule selected by `intent`; the set-off enforceability register selected by `jurisdiction_basis`. Emits `policy_version` |
| 5 | **Lineage** | `operators_invoked: [policy.principal-subgraph, traversal.typed-neighborhood]` · `graph_snapshot_at` · `policy_version` · `projection_plan_id` · `context_debt`. **Two, not five** — see §D.2.1 |
| 6 | **Semantic Version** | `v1.0.0`. Migration window `[TBC — product owner]` |
| 7 | **Discovery** | `credit-risk.collateral-coverage.v1` |
| 8 | **Addressability** | `/context-products/credit-risk/collateral-coverage/{facility-id}`. Anchors on `facility_id`, a resolvable business identifier, never a surrogate key |
| 9 | **Assembly Mode** | **1 — pure algorithmic.** No LLM is reachable from any step. §2.3 model-risk annotation is therefore **not applicable**, which is a decision rather than an omission |

### B.2 Request parameter surface

| Parameter | Type | Moves | Default | Measured effect |
|---|---|---|---|---|
| `facility_id` | string, **required** | anchor | — | unresolvable ⇒ refusal, never an empty payload |
| `borrower_scope` | array, **required** | `P` envelope | — | the policy operator's admitted set |
| `apply_haircuts` | bool | measure | `true` | 1.089 → **1.446** when false |
| `include_setoff` | bool | `R` scope | `true` | 1.089 → **0.839** when false — covered becomes under-covered |
| `jurisdiction_basis` | enum `contractual`\|`enforceable` | `P` envelope | `enforceable` | 1.089 → **1.353** under `contractual` |
| `shared_collateral` | enum `priority`\|`pro-rata` | measure | `priority` | 1.089 → **0.800** under `pro-rata` |

`jurisdiction_basis` is the parameter worth dwelling on. Set-off rights that are
contractually granted are not always enforceable in every jurisdiction.
Returning contractual rights as though they were enforceable **overstates
coverage** — and which answer is correct depends on the decision, not the data.
The default is the conservative one.

### B.3 Declared-but-inert parameters

**`as_of` is DECLARED AND REFUSED**, with an authored reason. Reconstructing
coverage as it stood on a past date requires ledger time-travel, which arrives
at Tier 3. *A parameter that appears to work and does not will be relied on in a
dispute* — so it is refused by name rather than silently ignored.

**`intent` is NOT declared as an argument.** It is a top-level `ProductRequest`
field on this SDK, and an argument of the same name shadows it (`D-IMPL-264`).
It still selects the haircut schedule; it simply travels as the request's own
field. **This is a divergence from the vault article's §B**, which lists
`intent` in the parameter surface — recorded at §G.3.

---

## Section C — Data catalog

### C.1 Element table

| Element | Provenance | Class | Store | `G` | Measured |
|---|---|---|---|---|---|
| Facility, borrower, commitment | internal loan system | synthetic — internal | Postgres | `E` | 60 facilities |
| `securedBy` edges (facility → asset) | EX-10 collateral schedules | public | **Fluree** | `R` | **95** |
| **Reified pledge and lien priority** | exhibit-level pledge records | public | **Fluree** | `R` | **95 nodes; 93 Primary, 2 Subordinate** |
| `pledgedBy` (asset → pledgor) | EX-10 collateral schedules | public | **Fluree** | `R` | 91 |
| Collateral descriptions and categories | UCC collateral description; FIBO asset classes | public | Postgres | `E` | 91 assets |
| Collateral valuations and valuation dates | internal appraisal and mark systems | synthetic — internal | Postgres | `E` | 91, ages **0–545 days** |
| Deposit balances | internal deposit system | synthetic — internal | Postgres | `E` | 120 accounts |
| `setOffAgainst` / `nettedUnder` edges | internal netting agreements | synthetic — internal | **Fluree** | `R` | 120 / 73 |
| Haircut schedule by asset class | internal credit policy | synthetic — internal | Postgres | `P` | 6 classes |
| Set-off enforceability by jurisdiction | internal legal opinion register | synthetic — internal | Postgres | `P` | 12 jurisdictions, 8 enforceable |
| **UCC-1 filings — secured party, debtor, FILING DATE** | Florida Secured Transaction Registry | **public** | **Fluree** | `R`, `T` | **65 filings, 85 amendments, 24 secured parties; 2005-11-14 … 2026-08-12** |
| **UCC amendment history (the `T` half)** | same | public | **Fluree** | `T` | 85 nodes, **13 filings carrying a Termination** |
| Debtor name → LEI crosswalk | derived, scored | synthetic — internal | Postgres | `E` | **1 of 16 accepted** |
| Shared-collateral case | engineered | synthetic — engineered | **Fluree** | `R` | **4 assets; 2 at differing priority** |

### C.2 The manufacture envelope, checked

| §F requirement | Required | Measured | |
|---|---|---|---|
| collateral assets | ~60 | **91** | ✅ |
| facilities | ~40 | **60** | ✅ |
| shared-collateral cases | ≥ 3 | **4** | ✅ |
| …at differing priority | ≥ 1 | **2** (`COL-00012`, `COL-00044`) | ✅ |
| over-collateralized gross, under-covered after haircuts | ≥ 2 | **23** | ✅ |
| deposits with set-off | ~20 | **120** | ✅ |
| …where enforceability fails | ≥ 4 | **36** | ✅ |
| valuation dates spread | same-day → 18 months | **0 → 545 days** | ✅ |

### C.3 Correlation key and identity authority

`facility_id` is the anchor. **The register keys on legal NAME and the fabric
keys on LEI**, and the match is a claim carrying a score, never asserted as
filed fact. Measured: `ucc_debtor_crosswalk` holds 16 filed names of which
**1 is `accepted`** and 15 are `below_threshold` — several visibly subsidiaries
of the one that resolves (`MASTEC NORTH AMERICA, INC.` scores 0.46 against
`MASTEC INC`). The product **serves the unresolved count** rather than hiding
it; resolving them properly is [[kyc-refresh-beneficial-ownership]]'s subject.

### C.4 The traps — what the data does not support cleanly

1. **Priority is asserted, not derived.** UCC Article 9 makes the *filing date*
   what establishes priority between competing secured parties. The reified
   `lienPosition` carries the position; the filing that would date it is
   attached to the **debtor**, not to the facility, because the register does
   not assert that link. **The product does not join them**, and §G.3 records
   this as the largest open question about the product's semantics.
2. **Register coverage is 8 of 50 anchors, Florida only.** Delaware — the
   majority of the cast at parent level — is closed to public search. **The §C
   lien-filing rows are NOT marked satisfied** on the strength of a 16%-of-cast
   layer.
3. **Collateral descriptions are EX-10-derived, not from the filing.** Florida
   supplies them only inside a scanned `.tif`, which is not OCR'd, because a
   mis-read description stored as filed fact is worse than an honest absence.
4. **An amendment's action is not scalar.** Two amendments carry two actions
   each, which is why 15 amendments carry a `Termination` while only 13 filings
   do. A consumer modelling one action per amendment drops half of a
   secured-party substitution.

---

## Section D — Assembly recipe

### D.1 Client call

```
GET /context-products/credit-risk/collateral-coverage/FAC-044206
      ?borrower_scope=529900E95812SYWMCE44&apply_haircuts=true
      &shared_collateral=priority&jurisdiction_basis=enforceable
```

In-process and over MCP alike. The MCP door names its implementation as a
module and callable, never a filesystem path: a consumer asks for the Context
Product and does not learn how the producer starts.

### D.2 Step table

| # | Step | Operator | Store | Emits | Budget |
|---|---|---|---|---|---|
| 1 | Resolve the facility | `null` (L1 source access) | Postgres | borrower LEI, name, commitment | 1 query |
| 2 | Load the policy registers | `null` (L1) | Postgres | haircut schedule, enforceable jurisdictions | 2 queries |
| 3a | Walk `securedBy`, then **reverse-walk** each asset | `traversal.typed-neighborhood` | Fluree | anchor pledges, sharing facilities, ledger `t` | 3 queries |
| 3b | Walk set-off / netting from the **borrower** | `traversal.typed-neighborhood` | Fluree | deposit accounts, per-predicate | 2 queries |
| 3c | Walk the register for this debtor's filed names | `traversal.typed-neighborhood` | Fluree | filings, secured parties, amendments | 3 queries |
| 4 | Batch enrich | `null` (L2) | Postgres | valuations, categories, balances | **2 queries, never one per node** |
| 5 | Allocate, filter, measure | `null` (Π, in-memory) | — | coverage, allocations, findings | — |
| 6 | Govern, gate, record, serve | the SDK's | — | `ServedProduct` or `RefusalEnvelope` | — |

**Step 3a's reverse leg is the product.** Having found the anchor's assets, the
walk goes *back* along each asset's `securedBy` edges to every other facility
sharing it. Skipping it is how shared collateral goes unnoticed, and the answer
looks fine without it.

### D.2.1 Why lineage carries TWO operators and not five

The vault article's §B lists `[Resolve, Policy, Traversal, Enrich, Aggregate]`.
On this SDK only **two of those are registered L4 operators**: the whitepaper
commits four canonical categories (Traversal, Temporal, Policy, Similarity), and
Resolve/Enrich are L1–L2 source access while Aggregate is Π. **A step that
carries a Standard verb but is not a registered operator does not enter
`operators_invoked`**, and lineage strict equality is why that distinction is
load-bearing rather than tidy. Declared: `policy.principal-subgraph`,
`traversal.typed-neighborhood`.

This is the standard's own open question — *"which layer is canonical must still
be ruled"* — reaching an implementation. Recorded at §F.2 row 1.

### D.3 Determinism and the payload

**Assembly Mode 1.** Same estate state, same parameters, same content address.
The graph read is **identical for every value of `apply_haircuts` and
`shared_collateral`**: both are applied at Π, so what the caller's choice
changes is the payload — and therefore the product's identity — rather than what
was read.

### D.4 Validation gates

Three from the SDK — empty-operator guard, lineage strict equality, TTL bounds —
and **a fourth this product declares**:

> **Over-allocation guard.** The sum of allocations against any single asset
> must not exceed its haircut value.

It is supplied as a `product_gate` with a **declared identity**
(`cp-06.over-allocation-guard@1.0.0`) on the class document. The SDK refuses to
build a resolver given a gate with no declared id, because replay would have
nothing to stamp on a refusal the gate produced (`D-IMPL-282`).

### D.5 Falsifiable replay test

1. Serve `FAC-044206` at the declared defaults **at a pinned decision
   instant**; record the content address.
2. Re-serve with the same parameters, the same estate state **and the same
   instant**. The instant is part of the determination — it sets the product's
   expiry and therefore enters the address — so two serves a millisecond apart
   are two questions and correctly disagree. A determinism test that did not
   pin it would be measuring the clock.
3. **The content addresses must be equal**, and both determinations must resolve
   the same `policy_version` and `projection_plan_id`.
4. Change **one** parameter — `shared_collateral=pro-rata`, instant held. The
   address must **differ**, and the operator plan must be **unchanged**,
   demonstrating that Π moved the answer and the read did not.
5. **The control**: the same question at a different instant must also differ.
   Without it, step 3 would pass equally against a product that ignored time.

---

## Section E — Volatility, debt and materialization

### E.1 Half-life table

| Signal class | `λ_c` | Notes |
|---|---|---|
| Marketable-securities valuations | ~1 day | |
| Deposit balances | ~1 day | |
| Real-property appraisals | ~365 days | **the widest spread in the catalog against the rows above** |
| Lien structure and priority | ~365 days | filing-driven |
| Haircut schedule | ~180 days | policy review cycle |

**λ_c remains Control Plane configuration this spec proposes rather than fixes.**

The valuation spread — one day against one year inside a single product — is
exactly the asymmetry §6.4 Temporal Validation refuses to let a product flatten.
**The payload carries the valuation date per asset**, never a single
product-level freshness.

### E.2 Debt model

`D_c = 1 − (F · C · S)`, per-component:

| Component | What it measures here | Moves? |
|---|---|---|
| **F** freshness | the SDK's `FreshnessScorer` over each asset's valuation age against its own λ_c class | **yes — the factor that moves** |
| **C** completeness | pledged assets the attribute leg priced ÷ pledged assets | yes, when a pledge has no valuation |
| **S** semantic consistency | declared `1` | no — `[TBC — product owner]`, §F.2 row 2 |

Measured at the demonstration anchor: `D_c ≈ 0.377`, signal `ok` against a
`forced_llm_threshold` of 0.60.

### E.3 Materialization posture

**Derived on demand.** Structure is cacheable; valuations are not.

### E.4 Supersession triggers

A new UCC filing or amendment on a pledged asset; an appraisal update; an
amendment adding or releasing collateral; a deposit balance movement beyond a
declared threshold.

---

## Section F — Source binding and readiness

### F.1 Element readiness

Every §C row is **loaded and measured** except as noted in §F.2. The estate
supports every one of the six behaviors §B.2 tabulates.

### F.2 Every `[TBC]` in this document, with an owner

| # | Item | Owner | Cleared by |
|---|---|---|---|
| 1 | Whether the closed eight-operator vocabulary or the whitepaper's four categories is canonical for `operators_invoked` | **vault / Dave** | a ruling; tracked in [[ccf-v2-schema-delta]] |
| 2 | Whether `S` should measure something in this product | product owner | a definition of semantic consistency for coverage |
| 3 | Semantic-version migration window | product owner | §G lifecycle |
| 4 | UCC-1 coverage beyond Florida (8 of 50 anchors) | **`ccf-dataprep`** | the other free states, or a ruling that Florida suffices |
| 5 | Collateral description from the filing rather than EX-10 | `ccf-dataprep` | OCR of the registry `.tif`, or a ruling that EX-10 suffices |
| 6 | Whether a filing should be joined to a facility | **vault / Dave** | §C.4 trap 1 — the register does not assert the link |

### F.3 Access path

Fluree ledger `fibo-v2` and PostgreSQL schema `ccf_v2` on the `.76` estate,
**both read-only**. Connection material from the environment; **the namespaces
are v2 and are not in `.env`** (CLAUDE.md §9).

### F.4 Recorded findings

`CP06-F-01` — a defect in a *sibling* example found while building this one, in
`FINDINGS.md`. Not this product's, and not fixed on this product's branch.

---

## Section G — Operate and govern

### G.1 The operating contract

Owner as §0.3. Degradation: an unreachable graph leg is a refusal, not a partial
answer — a coverage figure computed without the priority graph is precisely the
wrong answer this product exists to prevent.

### G.2 Product gates

| Gate | Asserts | Sabotaged by |
|---|---|---|
| `CSC-G01` | haircuts reduce coverage | applying the haircut as a premium |
| `CSC-G02` | valid set-off increases coverage | counting excluded set-off |
| `CSC-G03` | `contractual` ≥ `enforceable` set-off | inverting the basis filter |
| `CSC-G04` | `priority` and `pro-rata` disagree on a shared asset | collapsing one onto the other |
| `CSC-G05` | the register reports a released lien | dropping the amendment walk |
| `CSC-G06` | MasTec is under-covered | — |
| `CSC-G07` | valuation dates are per asset | flattening to one freshness |
| `CSC-G08` | priority is carried per (facility, asset) | hanging it on the asset |
| `CSC-G09` | source ids are served, not fabric URIs | serving `collateral_node://…` |
| `CSC-G10` | the over-allocation gate is declared and identified | dropping `declared_product_gate` |
| `CSC-G11` | replay dimension 2 ⊇ product policy lineage | — |
| `CSC-G12` | the door names a `module:callable`, not a script path | naming a `.py` path |

**Three were observed failing** under deliberate sabotage on 2026-09-10:
`CSC-G01`, `CSC-G04`, `CSC-G09`. The remainder are asserted but not yet
individually sabotaged — `[TBC — this build]`.

### G.3 Where the build and this document disagree

**Recorded rather than reconciled**, per §0.1.

| # | The vault article says | The build does | Disposition |
|---|---|---|---|
| 1 | `intent` is a request parameter | it is the request's own top-level field | **build is correct on this SDK** (`D-IMPL-264`); §B.3 |
| 2 | `operators_invoked: [Resolve, Policy, Traversal, Enrich, Aggregate]` | two registered operators | **build is correct**; §D.2.1, and the vocabulary question is §F.2 row 1 |
| 3 | lien priority from UCC filing date | priority asserted by the reified pledge; filings attached to the debtor | **open** — §C.4 trap 1, §F.2 row 6 |
| 4 | `~60` assets, `~40` facilities | 91 and 60 | estate exceeds the envelope; no action |

### G.4 Reproducibility — the claim, in exactly these words

**Against a quiescent estate, the same request at the same parameters produces
the same content address.** The claim is bounded to a quiescent ledger for that
run and to nothing wider: the graph leg **floors** rather than pins, so a
concurrent write to `fibo-v2` between two runs may legitimately change the
answer. Reproducibility of the *determination* is guaranteed by replay, which
resolves exact artifact versions.

### G.5 Acceptance criteria

Each phrased so it can fail:

1. Every parameter in §B.2 changes the served result in the tabulated direction.
2. `shape_of` reads `canonical`; `_sdk_supplied_operator_set` answers True.
3. No test pins an estate figure; all twelve §G.2 gates assert relationships.
4. The product writes to no source store; `.76` ledger count is unchanged
   across a full test run.
5. `D_c` is computed over the served roster and moves with the evidence.
6. The §C lien-filing rows are **not** marked satisfied while coverage is 8 of
   50 anchors.
