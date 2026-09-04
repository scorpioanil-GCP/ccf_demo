# Corporate Family Tree — Context Product Specification

**`CP-SPEC-004` · rung 04 of the vault's ladder · Tier 2 · the FIRST of Tier 2**
**Fluree `fibo-v2` for edges and ontology · PostgreSQL `ccf_v2` for attributes**
**Registry name `reference.corporate-family.v1` · cost band ×1–2**

> Walks the ownership graph from an anchor obligor across its family and returns
> the tree, the ontology class of every node in it, and the cycles that tree
> contains as findings rather than as errors. **The ladder's first multi-store
> product, its first graph traversal, and its first door reachable over MCP.**

| | |
|---|---|
| **Source article** | `wiki/context-products/content/corporate-family-tree.md`, vault-owned, **`standard: q019`** |
| **Authored to** | `Context_Product_Specification_Standard_v0-3.md` — the article is on the older Q019 form and is *raised* to v0.3 here, per `spec_generation.md` §4 |
| **Gate 1 status** | **RULED — APPROVED WITH THREE AMENDMENTS, ON THE AMENDED TEXT.** **FORM AMENDMENT 2026-09-01 (Dave): twenty-two `path.py:LINE` citations converted to the `path.py::Symbol` form `D-IMPL-114` ruled. CITATION FORM ONLY — the sixteen gates, the MCP refusal and the consume path are untouched, and this is NOT a re-open of substance.** **SUBSTANCE AMENDMENT 2026-09-01 (Dave, `D-IMPL-230`), recorded SEPARATELY from the form amendment above because it is a different kind of change: §E.2's two `[TBC — this build]` markers become MEASURED VALUES — the factor table `F=1`, `C=1`, `S=20/22`, `D_c=0.090909…`, signal `ok`, and `debt_tolerance: "0.25"` (§E.2.1, §F.2 rows 15 and 16). NO WEIGHT WAS INVENTED: the declared model is multiplicative and has no weight term. `debt_tolerance` was NOT moved to rescue a number. The SIXTEEN gates, the MCP refusal, the consume path, the census, the 22-node subtree, the ceiling of 6 and the default of 3 are ALL UNTOUCHED, and NO NEW GATE ID IS MINTED — the roster's home is `CFT-G09` and the `D_c` MOVEMENT assertion is a test. **EXTENDED 2026-09-01 under `D-IMPL-231`, within this same substance amendment rather than as a third entry:** §E.2.1 now states in one line that **`D_c ≈ 0.0909` is NOT '20 missing jurisdictions'** — `S`'s twenty and the `unresolved_jurisdiction` roster's twenty are DIFFERENT populations that overlap in NINETEEN, so a reader meeting both numbers together cannot conflate them. Nothing else moves: no figure, no gate id, no threshold.** **SUBSTANCE CORRECTION 2026-09-01 (Dave), after the CLOSE PANEL's Finding 1, recorded as a fourth entry because it corrects a MECHANISM rather than clearing a marker:** `S` — and therefore `D_c` — are taken over the **SERVED ROSTER**, not over the deployment's source read. Dave: *"a scalar that cannot fail through the door. That is not the §E.2 weight TBC. It is a wrong denominator."* **ONLY THE SET CHANGED.** §E.2's routing, the absence of per-component weights, `debt_tolerance` at `0.25`, the SIXTEEN gates, the MCP refusal, the consume path, the census, the 22-node subtree, the ceiling of 6 and the default of 3 are ALL UNTOUCHED, `D_c` is NOT retied to the twenty missing jurisdictions, and **NO NEW GATE ID IS MINTED** — the pair `(depth 3 → 0.0909…, depth 1 → 0.1)` is pinned at `artifacts/expected.yaml::debt_by_depth` and held by a THIRD LIMB of `CFT-G05`. The headline figures do not move: at the declared default depth `S` is still `20/22`, `D_c` is still `0.090909…`, and the demonstration question still seals to `205ae065…`. What moves is every other depth. Recorded at §E.2.1 in the marked form, with the superseded reading preserved beside the correction rather than rewritten away. Approver: **Dave**. Date: **2026-08-31**. Decision: **`D-IMPL-225`**. The three amendments landed in `.planning/ROADMAP.md` (criteria 34, 37, 43, 47 and 49) and in `docs/DECISIONS.md` **BEFORE this row was flipped and before Wave 3**, on the `D-IMPL-222` precedent Dave invoked by name; until they had, nothing under `examples/cp-04-corporate-family-tree/` existed but this document — `example_delivery.md` §1: *"No implementation code before Gate 1."* Each ruling is recorded beside its conflict at §F.4 |
| **Gate 2 status** | **in progress.** Artifacts, deployment, spine, projection, assembler, the in-process caller and the `example-cp-04` target are built; the MCP door, the sixteen gate modules and the documentation page are not. §F.2 rows 15 and 16 are CLEARED (`D-IMPL-230`); eleven `[TBC — this build]` rows remain |
| **Estate** | Fluree ledger `fibo-v2` and PostgreSQL schema `ccf_v2` on the `ccf_dataprep` estate, both read-only. **Every figure in §C and §E was measured 2026-08-31 at `ledger_t = 5112`** and is traceable to a row in `24.4-MEASUREMENT.md` |
| **Stores** | **TWO — Fluree and PostgreSQL.** The split is the vault catalog's and is **not re-derived here** (`D-17`): **Fluree 7 rows, Postgres 4, both 1, twelve rows in total** — §C.1 |
| **Seventeen product gates** | `CFT-G01`…`CFT-G16` and `CFT-G18` (`CFT-G18` = the ambiguous anchor, `D-IMPL-245` (4), 2026-09-03; previously: ~~Sixteen product gates, `CFT-G01`…`CFT-G16`~~). **`CFT-G17` is WITHDRAWN** with ontology role 1, 2026-08-31 (Dave, `853ccc9`) — §D.2.1 and §G.2 |

---

## 0 · What this document is

A specification a competent engineer can build from **without a further design
conversation**, and which a reviewer can *falsify* rather than merely agree
with. Every figure in it was measured against the estate on 2026-08-31 at a
`ledger_t` read once, and the query that produced each is recoverable from
`24.4-MEASUREMENT.md`. Where a value is not yet known it is marked
`[TBC — <owner>]` and registered at §F.2.

**This document is the whole of Gate 1.** Nothing below is implemented.

**Three things in this document were conclusions somebody else had to rule on,
and they were not smoothed into prose.** §F.4 carries three measured conflicts
between the locked Phase 24.4 success criteria and the SDK as it ships, each
submitted with a proposed reading, an alternative, and **no resolution asserted
on Dave's behalf**. **All three were RULED at Gate 1 on 2026-08-31 (Dave,
`D-IMPL-225`), approved with three amendments**, and each ruling is recorded
beside its conflict. Two of the three **amended a locked criterion rather than
bending the product to it**; the amendments landed in `.planning/ROADMAP.md` and
`docs/DECISIONS.md` **before** this document was brought onto the amended text.

### 0.1 Do you need a Context Product? — the four-question test

The vault article is on the **older Q019 form**, which has no four-question
section. What the article's own text supports is recorded; the verdict belongs
to the test's owner and is **not asserted here**.

| Question | What the article and the estate support | Leaning |
|---|---|---|
| 1 · Does the answer change with who is asking, beyond formatting? | The article names an obvious `Π` split waiting at T5 — credit policy wants the **ultimate parent**; AML wants **beneficial ownership down to the natural person**. Same traversal, different terminal condition. At this rung one role is served and the perspective conditions on FIBO class rather than on a role map (§D.2.1 role 3) | leans **yes**, weakly |
| 2 · Does the answer have a validity window after which acting on it is wrong? | Yes. Ownership edges change on acquisition, disposal and restructuring; the article prices that at ~180 days and the ultimate-parent designation at ~365 (§E.1) | leans **yes** |
| 3 · Must the answer be reconstructible with the policy and freshness state that produced it? | Yes, and this rung is where it becomes hard: the tree came from one store and the attributes from another, so a reconstruction has to name **both** states, not one | leans **yes** |
| 4 · Is it composed at runtime from sources no schema author pre-joined? | **Yes, measured.** The 722 parent→child edges live in Fluree and the 142 resolving attribute rows live in PostgreSQL, and **no schema author has joined them**: 181 of 748 family nodes carry an LEI at all, and 20 of the anchor's 22 subtree nodes resolve to no Postgres row whatsoever (§C.5) | **yes** |
| **Result** | | **`[TBC — vault]`** — four leanings recorded, verdict not asserted; §F.2 row 1 |

> A qualified yes is a legitimate answer but it must be written down as one.
> This document records leanings and refuses to sign the test on the owner's
> behalf, which is the discipline rung 03 used and which surfaced a vault
> defect the first time it was applied.

### 0.2 Placeholder discipline

Every unresolved item carries `[TBC — <owner>]` and appears again at **§F.2**
with that owner and the gate that clears it.

- `[TBC — this build]` — a value only the build can supply. **Cleared at Gate 2.**
- `[TBC — <agent>]` — a term belonging to another agent under
  `spec_generation.md`. Cleared when that agent rules, never by this document.

**An unmarked assumption is a worse defect than a marked gap.** No `[TBC]` here
is a guess wearing a marker: each names a measurement nobody has taken or a term
nobody has ruled.

### 0.3 Section skeleton

`A` decision frame · `B` contract · `C` data catalog · `D` assembly recipe ·
`E` volatility, debt and materialization · `F` source binding and readiness ·
`G` operate and govern. The order is the Standard's and is not rearranged.

### 0.4 Front matter

| Field | Value |
|---|---|
| Registry name | `reference.corporate-family.v1` |
| Tier | **2** — the first of Tier 2. Capability classes `relational` **and** `graph-traversal` |
| **Assembly Mode** | **1 — pure algorithmic, DECLARED.** No LLM is invoked on any path in §D, and **`CFT-G12`** asserts that no LLM client is reachable from any step. The article's frontmatter carries `assembly_mode: null`; declaring it is a registration-time commitment and is proposed to the vault at §F.2 row 2 |
| Cost band | **×1–2** (the vault's, Tier 2) |
| Lifecycle state | **`draft`** — **Gate 1 APPROVED 2026-08-31 (Dave, `D-IMPL-225`) on the amended text.** Gate 2 not started: **no code, artifacts or tests exist yet** |
| Accountable owner | product: Credit Risk · data steward: reference data / entity master · policy owner: identity and access — **roles, not individuals** |
| Last review | 2026-08-31 (this authoring) |
| What it resolves | One anchor LEI to **the borrowing group as a typed graph**: every entity reachable from it across six declared family predicates, each node carrying its FIBO class chain, each edge carrying the predicate that produced it. Where that graph contains an ownership cycle, the cycle is returned as a **finding with an ordered roster and a closing edge** rather than silently broken or raised as an error |
| Four-question build test | **`[TBC — vault]`** — four leanings recorded at §0.1, verdict not asserted |
| Build order | **Fourth on the vault's ladder, first of Tier 2.** Depends on `counterparty-reference-snapshot` (rung 01) for the LEI-to-attribute resolution path. Supplies the family to `credit-exposure-rollup` (rung 05) and `kyc-refresh-beneficial-ownership` |
| Prerequisites | `counterparty-reference-snapshot` (rung 01) — **satisfied**: the attribute leg reads `ccf_v2.legal_entity`, the GLEIF Level 1 table rung 01 established, and **142 of the family graph's 181 LEI-bearing nodes resolve in it** (§C.5) |

### 0.5 Capability gate — stated above §A because it schedules the build

**This product cannot be built at all without `graph-traversal`, and the estate
has it.** Fluree `fibo-v2` carries the six family predicates as RDF triples and
answers depth-bounded walks through unioned fixed-length SPARQL patterns. Two
sub-capabilities the product needs are **absent**, and both are declared here
rather than discovered in §C:

| Sub-capability | Present? | Consequence |
|---|---|---|
| Depth-bounded multi-hop traversal over typed edges | **yes** | The walk is expressible. §C.2 |
| **Graph-algorithm library (cycle enumeration in-store)** | **NO** | Fluree has no GDS equivalent. **Cycle detection is the caller's responsibility and executes application-side, in the L2 assembler** (`D-10`). The recipe declares `operator: null` for that step — §D.2.2 |
| **Transaction-snapshot pinning of the read** | **NO** | The shipped Fluree adapter **floors** with `Fluree-Min-T` and does not pin — `D-26`, §F.4. This is why the reproducibility claim is bounded to a quiescent ledger *for that run* and to nothing wider — §G.4 |

---

## Section A — Decision frame

**Decision and trigger.** A credit officer is setting or testing a
concentration limit and needs to know the *real* borrowing group — not the
legal entity named on the facility document, but every entity whose credit
quality is correlated with it.

**Consuming principals.** Single role at this tier. The article notes the `Π`
split waiting at Tier 5 — credit policy wants the **ultimate parent** for
concentration and country-of-risk; AML wants **beneficial ownership down to the
natural person**. Same traversal, different terminal condition. That variant is
`kyc-refresh-beneficial-ownership`; here the product serves credit only. What
this rung *does* carry is the machinery for that split: **the perspective
conditions on FIBO class rather than on a hand-written role map**, so the T5
variant is a different class predicate rather than a different code path
(§D.2.1 role 3, gate `CFT-G16`).

### A.1 The counterfactual — `context-starved`

The article states the failure and this document adopts it as the counterfactual
the product exists to prevent:

> A data product returns the obligor's immediate parent from the CRM, because
> that is the field the CRM has. The credit officer therefore never learns that
> two apparently unrelated obligors in the portfolio share an ultimate parent
> four hops up. Concentration is computed against the wrong denominator, and the
> limit that was supposed to cap group exposure caps nothing. **The
> recommendation is a correct inference from an incorrectly assembled frame** —
> no model would have caught it, because the missing edge was never in the frame
> to begin with.

**Closed-taxonomy mode: `context-starved`.** The Standard's list is
`context-starved · temporally-incoherent · perspective-flat · policy-blind ·
evidence-free`. The article's own words — *"Counterfactual failure — Context
Starved"* — name a member, so unlike rung 03 there is nothing to migrate.

**Why the estate can carry this counterfactual and a single-store product
cannot.** The failure is *a missing edge*, and the edges are not in the store
that holds the attributes. Measured: the family graph has **748** nodes and
**722** normalized parent→child edges in Fluree, and **181** of those nodes
carry an LEI at all, of which **142** resolve to a PostgreSQL attribute row.
A product built on the attribute store alone can see at most 142 of 748
entities and **zero** of the 722 edges. That is the counterfactual as a
measurement rather than as a story.

### A.2 Fixture `CFT-F01` — the counterfactual, made falsifiable

The counterfactual is a claim, so it gets a test that can fail:

1. Ask for the family of `SuperMicroComputerInc` (LEI `54930022CZO1N2UGVW07`)
   at the **declared default `max_depth = 3`**.
2. The answer must contain **22 nodes** and reach **`CycThornburyCapitalLtd`
   at depth 3** — an entity three hops from the anchor and connected to it by
   no field any single record carries.
3. The same anchor read from the attribute store alone resolves **1 row**.
4. **The two answers must differ, and by 21 entities.** A build in which the
   family answer is the attribute answer has not implemented the product.

`[TBC — this build]` — the two calls and their outputs.

### A.3 Primitive taught, and the contrast pointer

**Primitive taught: a finding that is orthogonal to the payload.** Every earlier
rung's payload is the whole of its answer. This rung returns **a tree and a
separate `findings[]` list**, and the tree is not annotated with what the
findings say (`D-12`, gate `CFT-G08`). A cycle is *a set of nodes plus the edge
that closes it* — it is not a boolean on a node, and flattening it onto the
nodes destroys the closing edge, which is the only part that says where the loop
shuts.

**Contrast pointer — rung 03, on the axis of what a store is authoritative
for.** Rung 03 opens exactly one store and gate `OFS-G05` asserts that no other
store is opened at all. This rung opens two and gate `CFT-G10` asserts that
**each is opened for its own thing**: Fluree for edges and ontology, PostgreSQL
for attributes, and serving attributes out of Fluree turns the gate RED. The
two gates are the same discipline pointed in opposite directions, and neither
teaches single-writer discipline alone.

---

## Section B — Contract

### B.1 The nine elements

| # | Element | Value |
|---|---|---|
| 1 | **Schema** | `corporate_family` — entities: `LegalEntity` (and whatever FIBO classes the walk actually returns, served rather than assumed); relationships: the **six declared family predicates** of §C.5, each edge naming the predicate that produced it; `findings[]` carrying detected cycles and the duplicate-entity pair. Every node carries its **FIBO class chain**. Machine-readable artifact `[TBC — this build]` at `docs/schemas/corporate_family.v1.json` |
| 2 | **Freshness SLA** | **24 hours** — GLEIF RR-CDF publishes daily, and the ownership edge is the fastest-moving signal the product carries. The Exhibit 21 subsidiary list moves annually; §E.1 states the per-class rates, because one product-level figure over a payload mixing daily and annual signals is the error §E.1 exists to prevent |
| 3 | **TTL** | **24 hours**, `ttl_anchor: from_entity_freshness`, measured from **the latest assertion time among the family edges admitted to the payload** — §B.1.2 |
| 4 | **Policy Binding** | Entitlement scope, and the `policy_version` emitted from the Control Plane artifact in force. Jurisdiction visibility applies. **The intent-bound materiality threshold the article's §D step 2 names DOES NOT EXIST in the estate** — the vault recorded this itself on 2026-08-24 and this document does not paper over it; the parameter it would have driven is out of scope at this rung (§B.4.1) |
| 5 | **Lineage** | `operators_invoked` · `graph_snapshot_at` · `policy_version` · `projection_plan_id` · `context_debt` · `payload_hash`. **`model_record: null`** — Mode 1. The `ledger_t` the Fluree leg read at is recorded **beside** `graph_snapshot_at` and is not the same field — §B.1.1 |
| 6 | **Semantic Version** | `v1.0.0` |
| 7 | **Discovery** | `reference.corporate-family.v1` |
| 8 | **Addressability** | `/context-products/reference/corporate-family/{lei}` — and see §B.4.2, because at this rung the address is **not the door**: the served surface is `ProductClient` in-process and an MCP **tool**, never a `GET` on that path. The MCP product **resource** is registered and enumerable, and **refuses** — it never serves this product (§D.1, `CFT-G13`, `D-34`) |
| 9 | **Assembly Mode** | **1 — pure algorithmic.** No LLM on any path; `CFT-G12` asserts it. Rationale: the whole product is a walk, a normalization, a batched join and a circuit enumeration — every one deterministic, and a narrative layer over them would put a model between the officer and the edge that matters |

#### B.1.1 `graph_snapshot_at` and `ledger_t` are two fields, and conflating them was struck

**The article's §D says `graph_snapshot_at` carries the Fluree ledger `t`
value.** That is not implementable against the shipped contract and the claim
is **struck** (`D-03`, 2026-08-31):

- `graph_snapshot_at` is a **`datetime`** on the shipped contract
  (`src/ccf/products/contract.py::ProductLineage.graph_snapshot_at`). `ledger_t` is an **`int`**. They are
  different types describing different axes, and one cannot carry the other.
- The shipped Fluree adapter **floors** the read with `Fluree-Min-T` — *"do not
  answer older than this `t`"* — and leaves the upper bound open. **No `@t:` or
  `from: ledger@t:N` construction exists** in `src/ccf/graph/backends/fluree.py`.
  A floor and a pin are indistinguishable on a quiet ledger, and
  indistinguishable is not the same as equivalent. `D-26`, §F.4.
- **`D-IMPL-88` stands: `t` must not back `as_of`.** Snapshot pinning is a
  different axis and is simply not implemented. The two are not collapsed here.

**What the product therefore does.** It records the `ledger_t` it read at, as an
integer, beside `graph_snapshot_at`, and claims for it exactly what §G.4 claims
and nothing more. The measured reason the qualifier is load-bearing: **`ledger_t`
moved 4,560 to 5,112 between two sittings six days apart**. Quiet is a property
of a run.

#### B.1.2 The TTL anchor, against the test rung 03 set

Rung 03's `E.1.1` fixed the test a `from_entity_freshness` anchor must pass:

> A freshness anchor has to be an **observation timestamp that moves**… an
> origination date is fixed for the life of the agreement… that is a category
> error in the anchor, not a tight window.

**This anchor passes.** The anchored value is the assertion time of the family
edges the payload consumed, and GLEIF RR-CDF publishes daily — a new
relationship record advances it, and re-derivation clears the expiry. It is not
a fixed date on the entity.

**The 24-hour window itself is the vault's value and is not recalibrated here.**
Whether it should widen is a separate question from which observation it is
measured against, and conflating the two would hide one behind the other.

`[TBC — this build]` — the measured expiry for the pinned run, and the refusal
count under the declared window.

### B.2 Classification, residency and the information barrier

| Aspect | Value |
|---|---|
| **Payload classification** | `public`. Every §C element is public-filing or public-vendor data — GLEIF RR-CDF, GLEIF Level 1, EDGAR Exhibit 21, FIBO under MIT. **The one exception is the engineered cycle**, which is `synthetic — engineered` in the estate's own vocabulary and `public` by classification because it discloses nothing about anybody |
| **Information barrier** | **none.** No MNPI-bearing element. Stated deliberately, because `mnpi-wall-enforcement` at rung 17 depends on the reader knowing which corpora *do* |
| **Residency constraints** | **AMENDED 2026-09-01 by `D-IMPL-229` (Dave), which supersedes the `D-IMPL-228` text this row carried. THE POLICY AXIS IS OBSERVED FAMILY MEMBERSHIP; JURISDICTION IS A SERVED FIELD.** Policy admits on `family_id` — the anchor's LEI, **minted when a node is admitted to the walk**, so the value is OBSERVED rather than inferred from a store. Dave: *"If PolicyFilter can only key off a claim attribute, that attribute is membership, minted when the node is admitted to the walk."* **`{NL, US-DE}` remains the family's OBSERVED jurisdiction set and remains CLOSED with an unknown key refused, but it is SERVED-AND-ASSERTED rather than `permitted_classifications`.** A member with a `ccf_v2.legal_entity` row carries its **stored** `legal_jurisdiction`; a member with no row carries **none** — `attributes: null` — and **never the anchor's**. Dave: *"A missing Postgres row is not `US-DE`."* And: *"Cycle members already have no LEI; they must not pick up SMCI's Delaware because the walk started there."* The 20 row-less members surface as an **`unresolved_jurisdiction` finding carrying their ROSTER**, never a count and never `len(findings) > 0` (`D-13`, `CFT-G09`). **WHAT `D-IMPL-228` GOT RIGHT AND IS CARRIED FORWARD:** the struck nine-value list — `US, US-CA, US-DE, US-NY, NL, LU, DE, SG, KY` — claimed to be *"the jurisdiction set the family graph's LEI-bearing nodes resolve under"* and was false about itself: measured, that set is **33** values estate-wide and **TWO** over the 22-node population this product serves, and seven of the nine never touched the payload. Dave, verbatim: *"Nine-row 'coverage' is how idle gates look when the extra rows never fire."* **WHY THE STRUCK RULE HAD TO GO:** `PolicyFilter._admits` refuses an ABSENT attribute exactly as firmly as an out-of-grant one, so a jurisdiction-keyed envelope over a population 20 of whose 22 members hold no row deletes exactly what `CFT-G09` and criterion 33 protect — and anchor-inheritance, the fix that avoided it, put a value on 20 nodes no source ever asserted about them. Dave: *"Inheritance is the same class as the nine-row fiction: a value that was never observed, applied so a gate looks populated."* The WALK is still family-scoped — one root, 22 nodes. §B.2's own distinction still holds and is now structural: whether an edge to an entity may be returned is settled by MEMBERSHIP, and whether its attributes may be is settled by whether a row exists. **The certification question below is NOT closed by either ruling** |
| **Cross-border serving** | `[TBC — identity and access]` |

**The suppression rule, and why it bites harder on a graph.** Where policy
excludes content the payload carries **no count, marker or placeholder** saying
so. On a tree that is a stronger constraint than on a row: a suppressed node
must not leave a hole its neighbors' edges point into. **The resolution is
structural, not cosmetic** — an impermissible node is never materialized, so no
edge to it is ever built, per composition invariant 1. Policy runs before the
walk (§D.2 step 2), which is the whole reason for that ordering.

**Entitlement at this rung is `[TBC — this build]` as a measurement.** Rung 03
measured its four principals and found `49 / 47 / 0 / 0` — a real
discrimination. **No equivalent measurement has been taken over the family
population**, and this document does not assume the same principals discriminate
here. §F.2 row 6.

### B.3 Model-risk annotation

**Not applicable — Assembly Mode 1.** The Standard requires this section for
Modes 2 and 3 only. No LLM is invoked on any path in §D, and **`CFT-G12`**
asserts that no LLM client is reachable from any step — sabotaged by making one
reachable, and observed RED.

### B.4 Request parameter surface

| Parameter | Type | Moves | Default | Behavior |
|---|---|---|---|---|
| `lei` | string(20), **required** | **E** — the anchor | — | Unresolvable → **404**, never an empty payload |
| `intent` | enum, **required** | **P** — selects the policy envelope | — | Unknown intent → **400** |
| `max_depth` | int **1–6**, optional | **R** — scope | **3, DECLARED** | Above the ceiling → **REFUSED BY NAME**, never clamped. Absent → the **declared** default, never a value invented at serve time |
| `debt_tolerance` | float | **P** — the ceiling above which assembly refuses | `[TBC — this build]` | Breach → **409** with the debt block (SUPERSEDED 2026-09-03: since `24.5-L-14` the `409` is a CLASS-DECLARED ceiling — `src/ccf/products/gates.py::effective_debt_ceiling`, tightened but never loosened by a request; this class declares none, so its `debt_tolerance` is advisory) |
| `as_of` | — | **T** | — | **DECLARED-BUT-INERT. REFUSED `400 not_supported_at_tier`** |

#### B.4.1 `max_depth` — both numbers are measured, and the ceiling disagrees with the article

**The ceiling is 6 and the default is 3, and neither was picked.**

| Number | Measured basis | Where |
|---|---|---|
| **default 3** | From the anchor, the SMCI subtree is **22 nodes at maximum depth 3**, with depth **1** to `CycMeridianHoldingsSa`, **2** to `CycCalderIndustrialNv` and **3** to `CycThornburyCapitalLtd`. **The whole of cycle 1 is therefore visible at depth 3** — the default is the smallest depth at which the product's headline finding exists | `24.4-MEASUREMENT.md` criterion 11 |
| **ceiling 6** | Walking all **83** roots, the deepest tree anywhere in the estate is **depth 6**, which **`PSC-0124` attains**. A ceiling of 6 therefore truncates **no** tree in this estate. Depth distribution over the 83 roots: 33 at depth 1, 18 at 2, 13 at 3, 11 at 4, 1 at 5, **7 at 6** | `24.4-MEASUREMENT.md` criterion 13 |

> **`PSC-0124` is not the unique deepest root, and no assertion in this
> document says it is.** Depth 6 is attained by **seven** roots — `PSC-0018`,
> `PSC-0037`, `PSC-0053`, `PSC-0089`, **`PSC-0124`**, `PSC-0140`, `PSC-0153` —
> and nothing distinguishes `PSC-0124` among them: six of the seven span 7 nodes
> and `PSC-0037` spans **11**, so it is not even the largest. Every claim in
> this document is phrased **"depth 6, which `PSC-0124` attains"** and never
> *"the deepest root is `PSC-0124`"*, which would assert a uniqueness the estate
> does not carry. Recorded at §F.4 finding 7.

**THE ARTICLE SAYS `depth` IS `int 1–5`. THIS SPECIFICATION SAYS `max_depth`
IS `int 1–6`, AND THAT IS A DELIBERATE DIVERGENCE, NOT AN OVERSIGHT.** The
article's range predates the measurement; Dave ruled the ceiling at 6 on
2026-08-31 against the 83-root walk above, precisely so that no tree in this
estate is silently truncated at the cap. **Dave's ruling governs.** A reader
holding the article beside this document should see the disagreement named
rather than infer a transcription error. Proposed back to the vault at §F.2
row 3.

**Over-cap is refused by name and never clamped** (`D-07`). A silent clamp is
the failure mode this rung is most exposed to: the request says 8, the walk
does 6, the payload looks fine, and the content address greens. **Gate
`CFT-G03`** asserts the refusal and is sabotaged by *replacing the refusal with
a clamp* — the sabotage that a count-based check would not see.

**Absent takes the declared default** (`D-08`). Not a serve-time default, not a
literal in the request handler: the value is read from the declaration. **Gate
`CFT-G04`** is sabotaged by defaulting at serve time instead of reading the
declaration.

**Depth is part of product identity** (`D-09`). Two depths are two content
addresses, because they are two different answers to two different questions.
**Gate `CFT-G05`** is sabotaged by making `max_depth` not change the address.

#### B.4.2 Three parameters the article declares and this rung does not carry

`direction`, `materiality` and `include_dormant` are in the article's request
surface and are **out of scope for v1 of this product**. Each exclusion is
measured, not preferential:

| Parameter | Why not at this rung | Source of the reason |
|---|---|---|
| `materiality` (float, default 0.05) | It filters subsidiaries against consolidated total assets — and **Exhibit 21 carries no ownership percentage by rule** (17 CFR 229.601(b)(21)(i) does not require one), while **the intent-bound threshold has no table in the estate at all**. Both are the vault's own §C corrections 3 and 4, recorded 2026-08-24. A parameter with nothing behind it is the declared-but-inert case, and this rung already carries one (`as_of`); carrying a second that fails for a different reason teaches nothing new | vault article §C corrections 3, 4 |
| `direction` (`up`\|`down`\|`both`) | Every figure in §C.5 is a **downward** reach over normalized parent→child edges, and the direction of each predicate is itself a measured assertion (§C.4 trap 1). `direction` would multiply the surface the gates must cover by three before the one direction is proven once | §C.4 trap 1 |
| `include_dormant` (bool) | No dormancy signal exists on any family node in the estate | §C.5 |

**`out_of_scope` in the article is `null`, which the vault's notice says means
*not stated*, never *nothing*.** Four exclusions are proposed to it at §F.2
row 4: `as_of`-reconstruction, beneficial-ownership-to-natural-person,
materiality filtering, and A2A federation of the family across a trust boundary.

#### B.4.3 `as_of` is declared-but-inert and must fail loudly

Returning **`400 not_supported_at_tier`** (`D-01`), exactly as rungs 01, 02 and
03 refuse it. **Temporal remains Tier 3's subject**, whose flagship is
`covenant-in-force-as-of`. The tier boundary doing its job, not a gap.

**And the temptation here is specific and is refused by name.** This is the
first rung whose store carries a time axis of its own — Fluree's `t`, and
`@iso:` addressing over `db:time`. Neither is CCF `as_of`:

- **`t` is transaction time**, and `D-IMPL-88` rules it must not implement
  `as_of`.
- **`@iso:` searches *event* time**, nearest-at-or-before, and is
  **backdatable**. Legitimate for a clock pin; wrong for a transaction pin; and
  neither of the two is what `as_of` asks. `D-28`, §F.4.

**Gate `CFT-G06`** asserts the refusal and is sabotaged by silently honoring it.

### B.5 Prerequisites, consumers and scope boundary

**Prerequisite — satisfied, measured.** `counterparty-reference-snapshot`
(rung 01) established the LEI-to-attribute path against
**`ccf_v2.legal_entity`**, the GLEIF Level 1 table. Of the family graph's
**181** LEI-bearing nodes, **142** resolve there.

**Downstream consumers.** `credit-exposure-rollup` (rung 05) — the family is
the denominator its concentration is computed against;
`kyc-refresh-beneficial-ownership` — same traversal, different terminal
condition; `credit-memo-context` (rung 14).

**Deliberately out of scope, and which product carries each:**

| Out of scope | Why | Belongs to |
|---|---|---|
| **`as_of` — the family as it stood on a past date** | Requires ledger time-travel on the CCF axis, which arrives at Tier 3 | `covenant-in-force-as-of` (rung 08) |
| Beneficial ownership down to the natural person | A different terminal condition on the same walk, and a KYC/UBO policy envelope | `kyc-refresh-beneficial-ownership` |
| Materiality filtering of the returned family | No ownership percentage in the source, no intent-bound threshold in the estate — §B.4.2 | a later rung, once the reified edge exists |
| **A2A federation of the family across a trust boundary** | Ruled out of this phase explicitly. *"We will do A2A in a later example"* | a later example |
| Exposure aggregated across the family | A rollup, not a tree | `credit-exposure-rollup` |

---

## Section C — Data catalog

**The store split in §C.1 is the vault catalog's and is NOT re-derived here**
(`D-17`): **Fluree 7 rows, PostgreSQL 4, both 1 — twelve rows.** Where the
article's own currency figures have since moved, the movement is stated at
§C.1.1 rather than silently substituted, because a catalog is a dated snapshot
and correcting it in place erases the date.

**Everything in §C.5 was measured 2026-08-31** against `fibo-v2` at
`ledger_t = 5112` and against PostgreSQL schema `ccf_v2`, both read-only. Every
figure traces to a section of `24.4-MEASUREMENT.md`.

### C.1 Element table

| # | Element | System of record | Provenance class | Classification | Capability class | `G` | Ontology IRI | Store |
|---|---|---|---|---|---|---|---|---|
| 1 | **FIBO ontology (T-Box)** — Business Entities, Ownership and Control modules | EDM Council FIBO, OWL/RDF, MIT license | `vendor` | `public` | `graph-traversal` | **schema** | the T-Box **is** the binding | **Fluree** |
| 2 | **Direct parent relationship** | GLEIF **RR-CDF Level 2** relationship records | `vendor` | `public` | `graph-traversal` | **R** | `fibo-be-le-lei:isDirectlyConsolidatedBy` | **Fluree** |
| 3 | **Ultimate parent relationship** | GLEIF RR-CDF Level 2 | `vendor` | `public` | `graph-traversal` | **R** | `fibo-be-oac-cctl:hasGlobalUltimateParent` **and** `hasDomesticUltimateParent` — **two properties, not one** | **Fluree** |
| 4 | **Accounting consolidation basis** | GLEIF RR-CDF — **requires a reified edge**, §C.1.2 | `vendor` | `public` | `graph-traversal` | **R** | `[TBC — ccf_dataprep]`; the reified class does not exist | **Fluree** |
| 5 | **Relationship status** | GLEIF RR-CDF — resolves from PostgreSQL, not Fluree | `vendor` | `public` | `relational` | **E** | `[TBC — ccf_dataprep]` | **PostgreSQL** |
| 6 | **Relationship validity dates (valid time)** | GLEIF RR-CDF golden copy — **present at source, not fetched**, §C.1.2 | `vendor` | `public` | `bitemporal-ledger` | **T** | `[TBC — ccf_dataprep]` | **Fluree** |
| 7 | **Subsidiary list — name and jurisdiction** | EDGAR **Exhibit 21**, parsed at build time. **No ownership percentage — by rule** | `public-filing` | `public` | `graph-traversal` | **R** | `fibo-be-oac-cctl:hasSubsidiary` family | **Fluree** |
| 8 | **Stub entities for non-LEI subsidiaries** | Exhibit 21 names many subsidiaries holding no LEI; identified with the **`SYN-` scheme** | **`derived`** — bridging | `public` | `graph-traversal` · `relational` | **E** | `cmns-org:LegalEntity` | **Fluree + PostgreSQL** |
| 9 | **Entity attributes for traversal results** | inherited from `counterparty-reference-snapshot`; GLEIF **Level 1** → **PostgreSQL `ccf_v2.legal_entity`** | `inherited` | `public` | `relational` | **E** | `cmns-org:LegalEntity` | **PostgreSQL** |
| 10 | **Materiality threshold by intent** | internal credit policy — **not populated for this product**, §C.1.2 | `internal-SOR` | `internal` | `relational` | **P** | n/a — a threshold, not an entity | **PostgreSQL** |
| 11 | **Consolidated total assets** (materiality denominator) | XBRL `companyfacts` | `public-filing` | `public` | `relational` | **E** | `fibo-fnd-acc-cur:MonetaryAmount` | **PostgreSQL** |
| 12 | **Cross-shareholding cycle** | absent from real GLEIF at this scale — **deliberately planted and labeled as such** | **`derived`** — engineered | `public` | `graph-traversal` | **R** | `fibo-fnd-oac-own:owns` | **Fluree** |

**Seven Fluree, four PostgreSQL, one both. Twelve rows.** That is the split
`D-17` fixes, and this document does not re-derive it.

> **The provenance column uses the Standard's closed list**
> (`internal-SOR · vendor · public-filing · derived · inherited`), not the
> estate's own labels. `synthetic — bridging` and `synthetic — engineered` are
> estate properties describing how the demonstration data was produced; the
> catalog says plainly they *"do not belong in a §C provenance column."* Rows 8
> and 12 map to `derived` and the estate label is kept in the element text,
> where it is a fact about the data rather than a contract term.
>
> **Row 12 is this product's only engineered element**, and it is the one most
> open to challenge, which is why it is labeled in the element column rather
> than in a footnote. GLEIF Level 2 is a clean hierarchy; genuine
> cross-shareholding cycles are effectively absent at demo scale. Pretending the
> cycle emerged from public data would misrepresent what the product proves.

#### C.1.1 The article's currency table is stale in two cells, and the movement is stated rather than substituted

The article carries a per-term currency table verified against `fibo-v2` on
**2026-08-17 16:55**. Two of its rows have since moved. **The article is not
edited here; the divergence is recorded, because a dated snapshot that gets
silently corrected stops being evidence of anything.**

| Term | Article, 2026-08-17 | Measured, 2026-08-31 at `ledger_t = 5112` | What changed |
|---|---|---|---|
| `owns` | **462 edges** | **636 edges** | The estate loaded more. The article's instruction — *"do not forward-map, it is already right"* — still holds; only the count moved |
| `controls` | **0 edges** — *"bound, not yet generated against"* | **3 edges** | **It has been generated against.** The article's warning that *"a traversal matching only `controls` returns empty"* is now false; a traversal matching only `controls` returns three edges. **The instruction that matters is unchanged and is still right: match both, because they are siblings and not a hierarchy** |
| `hasDomesticUltimateParent` / `hasGlobalUltimateParent` | 36 / 103 | **36 / 103** | unchanged |
| `LegalEntity` on `cmns-org:` | 500 assertions | not re-counted | not this product's figure |

**`controls` at three edges is small enough to be invisible to a count and
large enough to matter.** Flipping its direction moves the family graph's root
count by exactly **one** — 83 to 82 — which is why §C.4 trap 1 asserts the
direction of all six predicates rather than of the four that carry volume.

#### C.1.2 Three elements the estate does not carry, and none of them blocks the build

**Recorded by the vault on 2026-08-24 and adopted here unchanged**, because a
gap somebody else already measured should not be re-measured into a different
shape:

1. **Rows 4 and 5 both need a reified edge, and §C never authorized one.**
   Fluree ownership edges carry no properties — one bare triple per fact — so
   there is nowhere to hang a consolidation basis. The estate has made this
   decision once already: `collateral-and-setoff-coverage` reifies
   `ex:CollateralPledge` because lien priority belongs to the *(facility, asset)*
   **pair**. Consolidation basis belongs to *(parent, child)* by the identical
   argument. **A property of a pair needs a node.** Not built at this rung; the
   product returns edges without a basis and says so.
2. **Row 6 conflates two times, and the correction was the vault's own.** The
   row claimed `T` on the strength of Fluree, but Fluree's ledger gives
   **assertion time** — when the edge was recorded — which §D already spends on
   the snapshot record. *"Validity dates"* are **valid time**, the interval the
   parentage actually held in the world. **Both questions are legitimate and
   this product answers only the first.** *Was this parentage in force on the
   drawdown date* is not answerable today. The RR **golden copy** carries
   `Relationship.Period` for **280 of 280** records; wave 3 fetched the
   relationship *API*, which returns parent, child, edge type and jurisdiction
   only. **A fetch not made is not a field the source lacks** — this is a
   deferral, not a waiver.
3. **Row 10 has no data at all.** The only table of that name in the estate
   holds an FX post-trade tolerance in **pips**, keyed to FX intents, belonging
   to a different product. Nothing binds an ownership **fraction** to a credit
   intent. §B.4.2 takes the parameter out of scope rather than shipping a
   filter with nothing behind it.

**None of the three blocks the build.** Rows 4, 5 and 6 are edge properties the
product does not return; row 10 drives a parameter this rung does not carry.

### C.2 Capability decomposition

The estate's `graph-traversal` answer is not wholesale. Decomposed:

| Property | Common estate answer | This estate | If absent |
|---|---|---|---|
| Multi-hop typed edge traversal with predicate filters | widely available | **yes** — six family predicates, 1,058 raw triples | **Blocking.** There is no product without it |
| **Bounded depth (`{m,n}`)** | sometimes | **yes, by construction** — SPARQL 1.1 property paths support `+ * ?` but **not** bounded `{m,n}` repetition, so the walk is expressed as **unioned fixed-length patterns** to the declared ceiling | Degrades to unbounded reach, which at 748 nodes is a table scan wearing a traversal's name |
| **In-store cycle enumeration** | rare | **NO.** Fluree has no graph-algorithm library equivalent to Neo4j GDS | **Degrades to a named partial: detection runs application-side, in the L2 assembler.** `ccf_dataprep` reached the same conclusion independently — *"depth-bounded traversal uses unioned fixed-length SPARQL patterns; cycle detection runs application-side"* — and Neo4j was dropped from the v2 estate on 2026-08-16 |
| **Transaction-snapshot pinning of the read** | sometimes | **NO** — the adapter floors, §B.1.1 and `D-26` | Degrades to a reproducibility claim bounded by quiescence. §G.4 states exactly that claim and nothing wider |
| **Node-class admission during the walk** | sometimes | **NO SDK EXPRESSION.** `GQ-10` types the walk on **edges only**; `seed_entity_classes` seeds the frontier and is never re-applied per hop | **This is why ontology role 1 was struck** — §D.2.1 and `D-33` |
| **A DIRECTED parent→child descendant walk** | assumed | **NO. The L4 walk is an UNDIRECTED NEIGHBORHOOD.** `src/ccf/operators/categories.py::TraversalNeighborhood` adds **both** `subject→object` and `object→subject` for every traversable edge, so depth is hops through adjacency and not generations of ownership | **`D-36`, RECORDED and not closed.** Measured over the demonstration anchor the operator serves **20 / 22 / 22** at depths 1 / 2 / 3 where the directed family tree gives **20 / 21 / 22**; the one divergent node, `CycThornburyCapitalLtd`, arrives at depth 2 through **cycle 1's closing edge** rather than as a child three generations down. **No declared figure moves** — every demonstration in this document sits at the declared default of 3, where both shapes give 22 |

**The interim posture.** Every trigger this product serves is deliverable. The
unsupported parameter (`as_of`) returns `400 not_supported_at_tier`. The partial
that is real — application-side cycle detection — ships **as the design**, is
declared `operator: null` in the recipe, and is not presented as an operator it
is not. Version string is `v1.0.0`; nothing is shipped under a version implying
a completeness it does not have.

### C.3 Correlation key, single-writer discipline and identity authority

**Correlation key: `LEI` throughout.** Fluree nodes carry `ex:lei` plus a label
and a class chain; **all attributes resolve from PostgreSQL**.

**Measured coverage, and it is the fact the product is built around:**

| Population | Figure |
|---|---|
| Family nodes | **748** |
| Of those, carrying `ex:lei` | **181** |
| Distinct LEI values on those 181 nodes | **181** — one-to-one; no node carries two, no LEI is shared |
| Of those 181, resolving in `ccf_v2.legal_entity` | **142** |
| **Family nodes with no attribute row at all** | **606 of 748** |

**An unmeasured crosswalk is a stated risk. This one is measured, and it is
mostly holes** — which is the product's subject rather than its defect
(`D-16`): a node carrying no LEI **stays in the tree and in the roster**, and a
failed join is a null resolution or a finding, **never a dropped member**. Gate
**`CFT-G09`** asserts it and is sabotaged by dropping members whose join fails.

**Single-writer discipline (whitepaper §7.3).** **PostgreSQL is authoritative
for entity attributes. Fluree is authoritative for edges and for the assertion
record of those edges.** Neither duplicates the other's authority, and neither
is a read replica of the other. Gate **`CFT-G10`** asserts the split at
runtime — sabotaged by serving attributes from Fluree, which is the exact shape
a well-meaning optimization would take.

**Identity authority hierarchy.** The anchor identifier does not exist for every
entity the product must serve, and that asymmetry belongs in the payload rather
than averaged into one freshness claim:

| Entity class | Identity authority | Record status | Freshness ceiling implied |
|---|---|---|---|
| LEI-bearing legal entity (**181** of 748) | GLEIF Level 1 | `ccf_v2.legal_entity`, **142 resolve** | GLEIF publication cadence — daily |
| Exhibit 21 stub (`SYN-` scheme) | the filer's own annual exhibit | Fluree node only, **no Postgres row** | **annual**, bounded by the 10-K cadence |
| Engineered cycle member (**6** nodes) | the estate itself | Fluree node only, no LEI | n/a — the condition is planted and labeled |

**A single product-level freshness figure over those three would be wrong**, and
§E.1 states them separately for that reason.

> **The `SYN-` scheme, and the schema note that comes with it.**
> `fibo-iri-binding` fixes the prefix format, chosen because a hyphen cannot
> occur in a real 20-character GLEIF LEI, so real and synthetic populations can
> never be confused visually or by regex. The accompanying note applies here
> unchanged: **`CHAR(20)` blank-pads a short synthetic value and returns the
> padding on every read; use `VARCHAR(20)`.**

### C.4 The traps — what the data does not support cleanly

#### Trap 1 — direction is asserted per predicate, and a count is blind to an arrow

**The six predicates do not all run parent→child.** Direction as measured, and
as documented by `ccf_dataprep`'s own
`validators/test_parent_edge_direction.py` — which exists because a bare
`COUNT` is blind to an arrow and **139 GLEIF edges were inverted for seven
waves with every check green**:

| Predicate | Reading | Basis |
|---|---|---|
| `owns` | **subject → object** | FIBO `owns` runs parent → child |
| `controls` | **subject → object** | the validator's explicit negative control against a blanket flip |
| `isDirectlyConsolidatedBy` | **object → subject** | the subject is the subsidiary |
| `isUltimatelyConsolidatedBy` | **object → subject** | the subject is the subsidiary |
| `hasGlobalUltimateParent` | **object → subject** | `rdfs:range GlobalUltimateParent` — the object is the parent |
| `hasDomesticUltimateParent` | **object → subject** | same |

**The positive control, measured.** Baseline is **83** roots over **722**
edges. Flip exactly one predicate and rebuild:

| Predicate flipped | edges | roots | moved? |
|---|---:|---:|:--:|
| `owns` | 825 | **391** | yes |
| `controls` | 722 | **82** | yes |
| `isDirectlyConsolidatedBy` | 841 | **59** | yes |
| `isUltimatelyConsolidatedBy` | 841 | **59** | yes |
| `hasGlobalUltimateParent` | 825 | **59** | yes |
| `hasDomesticUltimateParent` | 756 | **69** | yes |

**Every one of the six moves the root count away from 83**, including
`controls`, whose three triples move it by exactly one. That is what makes the
direction claim an assertion rather than a comment.

#### Trap 2 — 1,058 raw triples are 722 edges, and the collapse must be visible

The six predicates contribute **1,058** raw triples. Applying each predicate's
own direction and taking the **set** of parent→child pairs yields **722**
distinct edges — a **336**-triple collapse. The multiplicity:

| Raw triples mapping to one edge | Edges |
|---:|---:|
| 1 | 580 |
| 2 | 51 |
| 3 | 11 |
| 4 | 57 |
| 5 | 23 |

`580 + 51·2 + 11·3 + 57·4 + 23·5 = 1,058`, and `1,058 − 722 = 336`.

**The collapse is not a rounding artifact, and running a detector over the raw
set instead of the normalized set is a declared control**: the same circuit
enumeration over the 825 distinct subject→object pairs of the raw reading finds
**130** cycles, not 2. A three-order-of-magnitude-free gap like that is what
makes the control able to *discriminate* rather than merely to differ.

#### Trap 3 — the same company is in the tree twice, one hop from the anchor

| Node | LEI | Label | Classes |
|---|---|---|---:|
| `SuperMicroComputerBV` | **`549300F16C4PEFXU0S92`** | `SUPER MICRO COMPUTER B.V.` | 7 |
| `SubSuperMicroComputerBV` | **none** | `Super Micro Computer B.V` | 7 |

Both are direct children of `SuperMicroComputerInc`. They differ by case, by a
trailing period, and by whether a GLEIF identity exists. **The product surfaces
the pair as a finding rather than serving them as two distinct subsidiaries**,
which would inflate the family by one entity and the concentration denominator
with it.

**And the roster is answered with names, never with a count**, because a right
count with a wrong member audits clean forever. SMCI has **19** direct children:
**17** `Sub*` Exhibit 21 stubs plus `SuperMicroComputerBV` and
`CycMeridianHoldingsSa`. Note **two of the seventeen carry a lower-case
`micro`** — `SubSupermicroKk` and `SubSupermicroTechnologyBeijingCoLtd` — so a
roster built by matching `SubSuperMicro` finds **fifteen** and reports a
clean-looking count. The classification matches on the `Sub` prefix.

#### Trap 4 — the attribute leg reads `legal_entity`, and the decoy is `crosswalk`

The 181 family LEIs measured against the **wrong** PostgreSQL table give a real
number about the wrong thing, which survives re-checking:

| Table | Resolves |
|---|---:|
| **`ccf_v2.legal_entity`** — GLEIF Level 1, 156 rows — **correct** | **142** of 181 |
| `ccf_v2.crosswalk` — the decoy | **39** of 181 |

**142 and 39 are far enough apart that a check reading the wrong table cannot
report the right answer by accident.** §C.1 row 9 names `legal_entity`, and so
must the shipped census.

#### Trap 5 — the cycle roster order is a CONVENTION, and it has to be stated

The locked criteria assert **exact ordered rosters** for both cycles. **The same
elementary circuit entered from a different node is the same set in a different
order**, so an ordering convention has to be pinned or the roster assertion is
unstable across runs while every count stays right.

**The convention: each circuit is canonicalized by rotating it to start at its
lexicographically smallest member.** Under that rotation the enumerated circuits
reproduce the locked rosters exactly. **The shipped detector must carry this
convention**, or a correct detector will fail a correct assertion. It is stated
here so the build inherits it rather than rediscovering it.

### C.5 The measured population, stated once

Everything above rests on one pass, and the pass read `ledger_t` **once** at its
start rather than per query — a per-query read lets the anchor drift inside a
single pass and leaves no way to tell which figure was read against which state.

**`ledger_t = 5112`, 2026-08-31.**

**Every predicate figure is ENUMERATED, never aggregated.** Over this ledger the
aggregate forms invent phantoms: `COUNT(DISTINCT ?p)` returns 178 and
`GROUP BY ?p` returns 198 where `SELECT DISTINCT ?p` returns **171**, which is
the correct answer. The shape used throughout is
`SELECT ?s ?o FROM <fibo-v2> WHERE { ?s <PREDICATE-IRI> ?o }`, counted in
Python over the enumerated rows.

**The six family predicates, resolved from the ledger's own predicate
enumeration and not transcribed from a document:**

| Predicate | IRI | Triples |
|---|---|---:|
| `owns` | `…/FND/OwnershipAndControl/Ownership/owns` | **636** |
| `isDirectlyConsolidatedBy` | `…/BE/LegalEntities/LEIEntities/isDirectlyConsolidatedBy` | **140** |
| `isUltimatelyConsolidatedBy` | `…/BE/LegalEntities/LEIEntities/isUltimatelyConsolidatedBy` | **140** |
| `hasGlobalUltimateParent` | `…/BE/OwnershipAndControl/CorporateControl/hasGlobalUltimateParent` | **103** |
| `hasDomesticUltimateParent` | `…/BE/OwnershipAndControl/CorporateControl/hasDomesticUltimateParent` | **36** |
| `controls` | `…/FND/Relations/Relations/controls` | **3** |

Row count and distinct-pair count agree for every predicate, so **no predicate
carries a duplicated triple** and none of the six counts is inflated by
repetition.

> `hasSubsidiary`, `hasBeneficialOwner`, `isBeneficialOwnerOf`, `ownershipIn`,
> `hasOwnershipPercentage`, `isDirectorOf` and `isOfficerOf` also exist in this
> ledger and are **deliberately not** in the family set. The roster is the six
> above, and gate **`CFT-G02`** asserts that every returned edge is one of them —
> sabotaged by admitting a seventh.

**The graph:**

| Figure | Measured |
|---|---:|
| Raw family triples | **1,058** |
| Distinct normalized parent→child edges | **722** |
| Collapse | **336** |
| Distinct nodes | **748** |
| Roots | **83** |
| Deepest tree anywhere | **6**, which `PSC-0124` attains |

**The anchor:**

| Field | Measured |
|---|---|
| IRI | `http://example.org/fibo/SuperMicroComputerInc` |
| LEI | **`54930022CZO1N2UGVW07`** |
| Label | **`SUPER MICRO COMPUTER, INC.`** |
| FIBO type chain | **7** classes — `Corporation`, `FormalOrganization`, `LegalEntity`, `LegalPerson`, `Organization`, `Agent`, `Party` |
| Direct children | **19** — 17 `Sub*` stubs, `SuperMicroComputerBV`, `CycMeridianHoldingsSa` |
| Subtree | **22** nodes at max depth **3** |
| Subtree nodes carrying an LEI | **2 of 22** — both resolve |
| Subtree nodes resolving to **no** Postgres row | **20 of 22** |

**The cycles — exactly two, both wholly inside `owns`, and the claim is
measured safe:**

| # | Ordered members (rotated to the lexicographically smallest) | Closing edge | Predicate |
|---|---|---|---|
| 1 | `[CycCalderIndustrialNv, CycThornburyCapitalLtd, CycMeridianHoldingsSa]` | `[CycMeridianHoldingsSa, CycCalderIndustrialNv]` | `owns` |
| 2 | `[CycHarborstoneKy, CycLindenfeldGmbh, CycPahangPteLtd]` | `[CycPahangPteLtd, CycHarborstoneKy]` | `owns` |

All **6** cycle edges are present in the `owns` enumeration read
subject→object, and **zero** are contributed by any of the other five
predicates in either direction.

| Property | Measured |
|---|---|
| External edges into **any** cycle in the whole graph | **exactly one** — `SuperMicroComputerInc → CycMeridianHoldingsSa` |
| Cycle 2's external in-edges | **zero** — unreachable from any LEI-bearing anchor |
| LEI on any of the six cycle members | **none** |
| FIBO classes | cycle 1: **7** each · cycle 2: **5** each |

**Cycle 1 is the headline and cycle 2 is not** (`D-15`), and the reason is
measured rather than editorial: cycle 2 has **zero** external in-edges, so no
walk from an LEI-bearing anchor can reach it. The anchor's single edge into
cycle 1 is **the only path from the LEI-bearing population into either cycle**,
not one of several.

---

## Section D — Assembly recipe

### D.1 Client call

**The literal call, and it is not an HTTP `GET`.** Two callers share one
assembler (`D-21`), and neither reaches the product through
`/tenant/class/version`:

```python
# run.py — in-process, through the DOCUMENTED DIRECT-ADAPTER CONSTRUCTOR
# (src/ccf/client/client.py::ProductClient.__init__). The binding stays SINGLE-STORE and is not
# widened; the two-store assembly happens INSIDE the product.
client = ProductClient(product_id="reference.corporate-family.v1", adapter=...)
result = client.ask({
    "lei":       "54930022CZO1N2UGVW07",
    "intent":    "concentration-review",
    "max_depth": 3,
})
```

```
# server/serve.py — the MCP door. The TOOL is the only path that SERVES;
#                   the product RESOURCE is registered, enumerable, and REFUSES.
tool      request_context_product
args      tenant=…, product_class=reference.corporate-family, version=v1,
          subject=54930022CZO1N2UGVW07, intent=concentration-review,
          freshness=…, asked_at=…, parameters={"max_depth": 3}

resource  ccf://…/reference.corporate-family/v1
          → appears in resources/list, and a read returns ProductNotServable.
            NEVER a tree.
```

**Why the tool serves and the resource refuses** (`D-18`, and `D-IMPL-225`
amendment 1). The request needs an anchor LEI **and** a `max_depth`. The MCP
resource URI is three path segments — `tenant`, `class`, `version` — with **no
query surface**, so there is nowhere to put either. A resource would help only
if a standing, parameter-free answer existed for this product, and there is
none: **every answer is a walk from an anchor.**

**And the SDK registers the resource whether or not this product wants it.**
`runtime/ccf_runtime/mcp/egress.py::build_egress_server` registers
`@server.resource(PRODUCT_URI_TEMPLATE, …)` **unconditionally**; only the tool
at `:529` sits behind `expose_product_tool`. `build_egress_server` can be
resource-only or resource-plus-tool; **it cannot be tool-only.** `runtime/` is
**not** touched by this phase (`D-04`), so the door this rung ships is a
**REGISTERED RESOURCE THAT REFUSES**. Gate **`CFT-G13`** (§G.2) asserts the
three parts together: the resource **is** registered and enumerable in
`resources/list`; a resolve or read of it returns `ProductNotServable`
(`egress.py::ProductNotServable`) or the existing refusal type and **never a tree**; and the
**tool is the only path that serves**. That is strictly weaker than *"no
resource is exposed"* — the weakness is stated plainly at §F.4 Conflict 1 rather
than smoothed, criterion 37 was **amended** on 2026-08-31 to say what is true,
and the residual gap is **RECORDED as `D-34`** (§F.4 finding 9).

**And the consume path is the direct-adapter constructor, not a binding
document** (`D-IMPL-225` amendment 2). `src/ccf/client/adapters/binding_document.py::RULED_OUT_KEYS`
refuses a `resolver:` key **BY NAME**, so the `binding.yaml` path **structurally
cannot** express a two-store product. **The binding stays SINGLE-STORE and is
not widened.** cp-04 supplies an adapter of its own that conforms to
`ccf.client.wire.TransportAdapter` structurally and calls `assembler.py`, and
the two stores are opened **inside the assembly** — never by a fixture that
pre-opens both and hands the product a populated graph. `CFT-G10` asserts **the
ASSEMBLY opened both stores, not that the RUNNER did**. Nothing under `src/`
changes; no HTTP path exists anywhere in this example. §F.4 Conflict 2.

### D.2 Step table

Ten steps. `operator:` is a name from the Standard's **closed eight**
(§10.2) or **`null`**; `layer:` and `sdk_mechanism:` are what the recipe
artifact carries beside it, with a witness per step. **An L4 step's witness is
`operator_in_lineage`; an L2 step's witness is a `payload_key`.**

| # | Step | `operator:` | `layer:` | `sdk_mechanism:` | Emits | Fails |
|---|---|---|---|---|---|---|
| 1 | **Resolve the anchor** | `Resolve` | **L2** | L2 entity resolution under the assembly worker — **not** an L4 operator | canonical entity URI for the anchor LEI | fail closed → **404**, never an empty payload |
| 2 | **Load the policy envelope** | `Policy` | **L4** | `policy.<key>` — the shipped `PolicyFilter` | `policy_version`, permitted set | **403** on refusal; source unreachable → **503**, never a permissive default |
| 3 | **Read the family from Fluree** | **`null`** | **L1/L2** | the Fluree graph adapter — six predicates, unioned fixed-length SPARQL patterns to the **declared ceiling** | raw triples, `rdf:type` chains, `rdfs:label`, `ex:lei`, and the **`ledger_t` read at** | source unreachable → **503** with the source class named |
| 4 | **Normalize to parent→child** | **`null`** | **L2** | per-predicate direction from the declaration; set semantics | the edge set — **1,058 raw → 722 distinct** | a predicate with no declared direction → fail closed |
| 5 | **Bound the NEIGHBORHOOD at the caller's `max_depth`** | `Traversal` | **L4** | `traversal.typed-neighborhood` — the shipped `TraversalNeighborhood`, which expands **ADJACENCY** and not `owns` parent→child; see `D-36` and §C.2 | node set, edge set within `max_depth` **hops of undirected adjacency** | over-cap → **REFUSED BY NAME**; never clamped |
| 6 | **Resolve attributes from PostgreSQL** | `Enrich` | **L2** | **ONE batched select** over the collected LEIs against `ccf_v2.legal_entity` — §D.2.3 | attribute rows for the LEIs that resolve; **null resolution for those that do not** | degrade with debt; **never a dropped member** |
| 7 | **Detect cycles** | **`null`** | **L2** | application-side elementary-circuit enumeration, canonicalized by rotation to the lexicographically smallest member — §D.2.2 | `findings[]` entries, each with `type`, `predicate`, ordered `members`, `closing_edge` | a detector that cannot terminate → fail closed |
| 8 | **Surface the duplicate pair** | **`null`** | **L2** | label-and-identity comparison over the returned node set | a `findings[]` entry — §C.4 trap 3 | degrade with debt |
| 9 | **Project** | `Projection` | **L5** | perspective conditioned on **FIBO class**, not on a role map | `projection_plan_id`, the projected shape | plan unresolvable → **503** |
| 10 | **Contract assembly** | — | **L6** | not an operator; the Standard retires `Compose` | `ServableProduct`, `expires_at`, `payload_hash`, `context_debt` | **503** on gate refusal; **409** on debt |

**`operators_invoked` therefore carries exactly two entries** —
`policy.<key>` and `traversal.typed-neighborhood`, keys `[TBC — this build]`.
**Lineage strict equality holds because the L4 operators are the only steps
declared as operators to the registry**; a step declaring a Standard name against
a non-operator mechanism (step 6) does **not** enter `operators_invoked`, and
that distinction is the subject of §D.2.3.

**STEP 5 IS A NEIGHBORHOOD AND NOT A DIRECTED TREE, AND THE DIFFERENCE IS
MEASURED RATHER THAN CONCEDED** (`D-36`, ruled 2026-09-01, Dave, `D-IMPL-230`).
`TraversalNeighborhood` symmetrizes its adjacency, so *depth 2* means *two hops
of adjacency* and not *two generations of ownership*. **The lie is at depth 2 and
only there:** 20 / 22 / 22 served at depths 1 / 2 / 3 against the directed tree's
20 / 21 / 22. **NOT FIXED IN `src/`** — the same `D-04` posture as `D-33`, its
sibling in the same operator — and **no declared figure moves**, because every
demonstration sits at the declared default of 3 where both shapes give 22. What
changes is what this document is allowed to call it: a directed descendant walk
is not what this SDK walk is, and no §C, §D or example-facing string in this
build says otherwise.

**p95 budget:** per step and total `[TBC — this build]`, against a declared Tier
2 envelope of `[TBC — this build]`. **Step 5 dominates by construction** — the
Standard's own cost driver for `Traversal` is `fan-out × depth`, and the
measurement says the same thing about this estate: from SMCI, depth is cheap
(22 nodes at depth 3) and **fan-out is what would drag in the 748-node graph**.
State the **p95 fan-out**, not the mean, when it is measured.

#### D.2.1 The three ontology roles — and the fourth, which is STRUCK

The ROADMAP names four places the ontology is load-bearing at this rung.
**Role 1 was STRUCK from this rung on 2026-08-31 (Dave). This product carries
THREE.** The numbering is kept so a reader holding the ROADMAP beside this
document does not have to reconcile two numbering schemes.

**1 · Types constrain the walk — STRUCK FROM THIS RUNG. Not built and not
gated.** The claim, restated correctly for whatever rung can carry it: *the
walk stops when the neighbor's class is outside the admitted set.* It is struck
for **two independently measured reasons**, and either alone would be
sufficient:

- **The estate cannot exhibit the stop.** Measured over all **748** family
  nodes: **no LEI-bearing anchor reaches a node outside the 7-class
  `LegalPerson` `Corporation` profile within depth 3.** The class-diverse
  populations are real — `Person` **46**, `SpecialPurposeVehicle` **50**,
  5-class **123**, 4-class **68**, 3-class **29** — and **every one of them sits
  in a component no LEI-bearing anchor reaches downward.** A second anchor was
  measured and refused: Extreme Networks (22 nodes) and Celanese (53 nodes)
  carry no SPV and no Bank, and their only class variation is `Guarantor` added
  **to the root** — an additive class, not an exclusion, and a guarantor belongs
  inside a credit family anyway. **A gate over this would go green having proven
  nothing, and its sabotage would change no output.** Recorded as the estate gap
  **`D-32`**.
- **The SDK cannot express the stop.** The Traversal family types the walk on
  **EDGES ONLY** — `GQ-10`: *"the walk crosses only edges whose
  `relationship_type` is a member of `relationship_types`."* `seed_entity_classes`
  **seeds the frontier and is never re-applied per hop**
  (`src/ccf/operators/categories.py::TraversalNeighborhood`), and is documented as **"walk starting
  points"** (`src/ccf/graph/protocols.py::TraversalSpec`). **A node-class admission filter
  has no SDK expression.** Recorded as the mechanism gap **`D-33`**. Had the
  estate carried the data, the walk still could not have stopped without work
  under `src/` that this phase forbids.

> **`CFT-G17` is WITHDRAWN with role 1.** It appears in this document **only**
> as this withdrawal note and never as a gate row. The roster is **SEVENTEEN**
> gates, `CFT-G01`…`CFT-G16` and `CFT-G18` (2026-09-03, `D-IMPL-245` (4);
> previously: ~~The roster is **SIXTEEN** gates, `CFT-G01`…`CFT-G16`~~).
> `CFT-G17` remains withdrawn; `CFT-G18` is the next free id, never a re-mint.
>
> **It is deliberately NOT replaced by a positive-property restatement.**
> *"Every admitted node's class is in the declared set"* was refused **by name**:
> it is a tautology over a class-homogeneous population, and it would read as
> coverage while measuring nothing — the fourteen-idle-gates class exactly.
>
> **`seed_entity_classes` remains a REQUIRED field and stays declared, and
> declaring it reinstates nothing.** It means *walk starting points*. It does
> not mean *permitted classes*, it does not constrain the walk, and no sentence
> in this document says that it does.

**2 · Ontology is SERVED.** Each returned node carries its **FIBO class chain**
in the payload, on rung 01's precedent
(`payload["counterparty"]["type_chain"]`), so a consuming agent knows an SPV is
an SPV without a second lookup. **This is what makes the product self-describing
over MCP** — the tool's answer explains its own vocabulary. Gate **`CFT-G15`**,
sabotaged by serving the tree without type information.

**3 · Ontology drives the PROJECTION.** The perspective conditions on **FIBO
class** and not on a hand-written role map. A credit officer's view and a KYC
analyst's view of the same family differ **by class**, which is why the Tier 5
`Π` split the article anticipates is a different class predicate rather than a
different code path. Gate **`CFT-G16`**, sabotaged by substituting a
hand-written role map.

**4 · Ontology VALIDATES the assembly.** A declared product gate asserts that
**every returned node carries a known FIBO class** and **every returned edge is
one of the six declared family predicates**, so an untyped or off-ontology node
cannot enter silently. Gates **`CFT-G01`** (sabotaged by admitting an untyped
node) and **`CFT-G02`** (sabotaged by admitting a seventh predicate).

#### D.2.2 Cycle detection declares `operator: null`, deliberately

**Detection executes in the L2 assembler** (`D-10`), and the recipe step says so
with a `null` rather than borrowing a category to look tidy.

Three reasons, and the third is the binding one:

1. **The store cannot do it.** Fluree has no graph-algorithm library. The
   caller maintains the visited set — the article says so, and `ccf_dataprep`
   reached the same conclusion independently after Neo4j was dropped from the v2
   estate on 2026-08-16.
2. **None of the four scheduling classes describes it.** `OperatorCategory` is a
   **plan-order class carrying correctness rules**, not a synonym for a Standard
   name: `CATEGORY_ORDER` puts Policy first so Similarity ranks only over the
   principal-permissible subgraph (INV-CH7-26), and Temporal before Traversal so
   a walk expands over reconciled state (INV-CH7-28). Circuit enumeration over
   an already-collected edge set is none of those things.
3. **`D-IMPL-223` forbids registering it under Traversal to make a category
   fit.** Four scheduling classes stay, forever, as the scheduler; the
   Standard's eight are spec vocabulary; `OperatorCategory` is **closed for
   v0** and is not opened here. Registering circuit enumeration as a Traversal
   operator would make the lineage record say something untrue — the same
   defect rung 03 refused when it declined to register a batched select as
   `Enrich`.

**What a cycle looks like on the wire** (`D-11`). A cycle is **a set plus the
edge that closes it**, never a bit on a node:

```yaml
findings:
  - type: ownership_cycle
    predicate: owns
    members: [CycCalderIndustrialNv, CycThornburyCapitalLtd, CycMeridianHoldingsSa]
    closing_edge: [CycMeridianHoldingsSa, CycCalderIndustrialNv]
```

**The `members` order is the rotation of §C.4 trap 5** — canonicalized to start
at the lexicographically smallest member. Stated here so the shipped detector
inherits the convention rather than rediscovering it; a correct detector using a
different rotation would fail a correct assertion.

**The gate asserts the ROSTER, not `len(findings) > 0`** (`D-13`). A detector
reporting *"some cycle"* stays RED. Gate **`CFT-G07`** asserts type, ordered
members **and** the closing edge, and is sabotaged by dropping the closing edge —
which is precisely the part a flattened representation loses.

**Findings are ORTHOGONAL to the tree** (`D-12`). The tree stays the tree; the
findings sit beside it. Gate **`CFT-G08`** is sabotaged by flagging cycle
membership on the nodes instead, which destroys the closing edge while every
node count stays right.

#### D.2.3 Step 6 declares `Enrich`, and `Enrich` has no SDK expression

**Step 6 is the vault article's `Batch Enrich Operator`, and it is declared with
the Standard's name against a mechanism that is not an operator.** This is
stated rather than hidden, because the two vocabularies genuinely differ and
the difference is now ruled rather than open.

- The article's §B lineage reads
  `operators_invoked: [Resolve, Policy, Traversal, Enrich]`. **This document
  does not adopt that list into lineage**, because `operators_invoked` is
  checked for **strict equality against the operators the registry actually
  executed**, and only two were.
- **`D-IMPL-223` rules the shape:** the SDK's four categories are the
  scheduler; **the Standard's eight names are spec vocabulary.** A recipe step
  may therefore declare a Standard name against a mechanism that is not a
  registered operator — the same permission cycle detection uses when it
  declares `operator: null`.
- **`D-IMPL-212` — that `Enrich` has no SDK expression — is OPEN and is not
  closed by `D-IMPL-223`.** Recorded, not resolved. §F.4 finding 6.
- **Nothing is lost by the binding.** The fan-out still happens, still batched,
  still **one query per source per step**. What changes is only whether it is
  *named as an L4 operator in lineage*, and it is not.

**Batching is mandatory, not a variant.** Gate **`CFT-G11`** asserts that the
returned node set resolves in **ONE** batched PostgreSQL query, and is sabotaged
by firing one query per node — an example that fires per-node lookups works at
depth 2 and collapses at depth 4, which is the failure the whitepaper's §7.4
DataLoader-style resolution exists to prevent.

### D.3 Step detail

**Step 2 — Policy runs before anything reads graph state.** Composition
invariant 1, and here it is not decoration: **the envelope shapes what is
walked, not what is returned.** A node the principal may not see is never
materialized, so no edge to it is ever built and the suppression-silence rule of
§B.2 holds structurally rather than by filtering afterwards. This ordering is
learned from the first product that needs it or retrofitted painfully later.

**Step 3 — the Fluree read is bounded by the DECLARED CEILING, not by the
caller's `max_depth`.** The two bounds are different and both are needed:

- The **source read** is bounded at the declared ceiling **6**, so the assembler
  ingests the anchor's reachable component once.
- The **L4 operator** then applies the **caller's** `max_depth` over the ingested
  subgraph.

**That split is what makes depth an operator-parameter property**, and therefore
part of the content address (`D-09`, gate `CFT-G05`). If the caller's depth went
into the SPARQL instead, depth would be a source-read detail and two depths could
share an address.

The read requires an explicit `FROM <fibo-v2>` — the server returns an unhelpful
HTTP 500 without one — and emits the `ledger_t` it read at.

**Step 4 — normalization is where the arrow lives.** Direction is read from the
declaration, per predicate (§C.4 trap 1). **Set semantics, not list semantics**:
1,058 raw triples become 722 distinct edges, and the difference is reported
rather than hidden.

**Step 6 — attributes come from `ccf_v2.legal_entity`, and a miss is not a
drop.** Of the anchor's 22 subtree nodes, **20 resolve to no Postgres row at
all**. Those 20 stay in the tree and in the roster with a null resolution
(`D-16`). **A `JOIN` that silently drops them would return a tidier, smaller,
wrong family** — and it would present as a clean number with no error, which is
the defect shape this catalog keeps finding.

**Step 9 — the projection conditions on class.** Not on a role map, not on a
principal-to-shape lookup table.

**Step 10 — contract assembly is not an operator.** The Standard retires
`Compose`.

### D.4 Determinism class and payload hash

**`deterministic`** — Assembly Mode 1, no model in the trust path.

Same `(lei, intent, max_depth, principal, policy_version)` over the same graph
state → **byte-identical payload**, excluding `assembled_at`.

`payload_hash` = sha256 over the canonical bytes of the served product. Value
for the pinned run: `[TBC — this build]`.

**`max_depth` must change the content address** for an anchor whose tree is
deeper than the smaller of the two depths. Gate **`CFT-G05`**. The measured
material: from SMCI, depth 1 reaches 20 nodes, depth 2 reaches 21, depth 3
reaches 22 — three depths, three different answers, three addresses.

### D.5 Replay statement and replay test

**Replay statement.** Replay resolves the **exact** artifact versions — policy
bundle, recipe artifact, projection plan, operator parameters, prompt artifacts
(none, Mode 1) — never *"latest"*. `CFT-R01`, hashes `[TBC — this build]`.

**And it resolves them against a graph state the SDK cannot pin.** That is
stated here rather than discovered at replay:

> The Fluree adapter **floors** with `Fluree-Min-T` and does not pin. On a quiet
> ledger a floor and a pin are indistinguishable, and **indistinguishable is not
> equivalent — it is a vacant guarantee.** `D-26`, §F.4.

**Falsifiable replay test — and it is written to reach the honest ending.**

1. Serve the family for `SuperMicroComputerInc` at `max_depth=3`. Record the
   payload hash and the `ledger_t` read at.
2. Re-serve, unchanged, against the same quiescent ledger. **The hash must be
   identical.** A build in which it is not has a clock or a set-iteration order
   in its canonical bytes.
3. Mutate the underlying state — add one `owns` edge under the anchor. Re-derive
   live. **The new node must appear and the hash must change.** A build in which
   it does not is not reading the store.
4. **Step 4 is where the honest ending is.** Re-derive *at the recorded
   `ledger_t`* and assert the **original** payload returns. **This step is
   expected to FAIL against the shipped adapter**, because the adapter floors
   rather than pins, and a floor cannot exclude a later transaction. **That
   failure is the finding `D-26` records, not a defect in the test**, and the
   test is written to be run and to fail rather than omitted so the gap stays
   invisible.

**A second axis test is not applicable at this rung.** The product carries one
time axis. Valid time is at source and is not fetched (§C.1.2 item 2), and
`as_of` is refused (§B.4.3). Two axes arrive at Tier 3, and asserting that they
disagree here would be asserting something about an axis that is not present.

### D.6 Emitted contract

`CorporateFamilyContract@v1.0.0`, `extra=forbid` — enforced as a build-time CI
invariant, so a per-product subclass cannot silently add a field the base did
not declare.

| Field | Type | Why |
|---|---|---|
| `payload.anchor` | `{ uri: str, lei: str \| None, label: str \| None, type_chain: list[str] }` | The resolved anchor, carrying its own class chain like every other node |
| `payload.nodes` | `list[{ uri: str, lei: str \| None, label: str \| None, type_chain: list[str], depth: int, attributes: dict \| None }]` | **`lei`, `label` and `attributes` are all nullable, and that is the product's subject** — 606 of 748 family nodes have no attribute row. `type_chain` is **not** nullable: gate `CFT-G01` |
| `payload.edges` | `list[{ parent: str, child: str, predicate: str }]` | `predicate` is one of the six. Gate `CFT-G02` |
| `payload.findings` | `list[{ type: str, predicate: str \| None, members: list[str], closing_edge: list[str] \| None }]` | **Orthogonal to `nodes`.** No node carries a cycle flag. Gate `CFT-G08` |
| `payload.max_depth_applied` | `int` | The depth actually walked — equal to the request's, because over-cap is refused rather than clamped. Gate `CFT-G03` |
| `contract.*` | per the §8 envelope | `ttl_anchor: from_entity_freshness`, `assembly_mode: 1`, `determinism_class: deterministic` |
| `lineage.operators_invoked` | `list[str]` | **Exactly two** — §D.2 |
| `lineage.graph_snapshot_at` | `datetime` | **Not the ledger `t`.** §B.1.1 |
| `lineage.ledger_t` | `int` | The transaction the Fluree leg read at. Recorded **beside** the snapshot field, never inside it |
| `context_debt` | per the §8 envelope | §E.2 |
| `notices` | `list[…]` | Degradation the consumer must see. **Never a suppression marker** — §B.2 |

> **`attributes: null` is a served fact and not an omission.** A member whose
> Postgres join found nothing is present, in the tree and in the roster, with a
> null resolution. Gate `CFT-G09`.

### D.7 Validation gates

**The SDK's shipped gates run unchanged, and no gate is added to the SDK.**
`D-IMPL-224`: product gates are a **declared artifact plus CI coverage**; there
is **no `ProductGate` Protocol**, no serve path for them, and the universal
gates stay the only serve-time gates.

| Universal gate | Source | Applies here |
|---|---|---|
| Empty-operator guard | SDK | **yes** — two operators, both non-empty |
| Lineage strict equality | SDK | **yes** — and it is why step 6 does not enter `operators_invoked` (§D.2.3) |
| TTL bounds | SDK | **yes** — §B.1.2 |
| Debt gate | SDK | **yes** — breach → `409` with the debt block (SUPERSEDED 2026-09-03: `24.5-L-14` made the `409` class-declared — `src/ccf/products/gates.py::effective_debt_ceiling`; this class declares no ceiling, so no `409` fires here and `debt_tolerance` is advisory) |
| Suppression silence | SDK | **yes** — and structurally satisfied by ordering, §B.2 |
| Classification containment | SDK | **yes** — every element is `public` |

**The seventeen `CFT-G` gates are DECLARED PRODUCT GATES** (2026-09-03; previously
~~sixteen~~ — `CFT-G18` added, `CFT-G17` remains withdrawn), not additions to the
serve-time runner. They live as **DATA** in
`examples/cp-04-corporate-family-tree/artifacts/gates.yaml` under a **closed
schema**, and **no gate id appears anywhere as a YAML comment only** — the whole
point of the artifact. **The §G.2 table below is NOT the machine source for any
check** (`D-22`): CI must not depend on parsing prose out of Markdown, which is
the fragility the artifact exists to escape. *A prose table cannot be held
against a run.*

> **RULED at Gate 1 — `D-IMPL-225` amendment 3.** The closed schema is
> **`docs/schemas/product-gates/cp.product-gates.json`**: **inside**
> `docs/schemas/` as criterion 43 requires, and **deliberately OFF** the
> top-level `docs/schemas/*.json` glob that `tools/dump_schemas.py::committed` walks
> and `:399` `unlink()`s, so a hand-authored file is never destroyed as an
> orphan. **Enforcement is Phase 24.5's checker, not this phase** (`D-24`).
> §F.4 Conflict 3.

**`artifacts/expected.yaml` stays about expected VALUES** and is not widened to
carry gate rosters. Every expected figure in §C.5 is read from it and **never
authored in a test file** — a number authored in a test is the test agreeing
with itself.

**The coverage CHECKER is Phase 24.5, not this phase** (`D-24`). Today the link
between a declared gate id and an executing test is **naming convention**:
measured across the ladder, **40 product-level gate ids exist across four
products** and `grep -rnE "OFS-G|FTS-G|[A-Z]{2,4}-G[0-9]{2}" --include=*.py
src/ runtime/` returns **0**. `D-31`, §F.4.

> **2026-09-03:** that checker shipped in Phase 24.5 as `24.5-L-10`
> (`tools/check_product_gates.py`, run as `make product-gates`) — §F.4 finding 6's
> dated note. The paragraph above stands as the measurement it was.

### D.8 The snapshot the printed run reproduces

Per `D-IMPL-218`, the demonstrated run assembles **over a named pin**, and the
loaders stay **off the demonstrated path** — *"run the loader, then observe the
product"* must not appear as a reproduction recipe.

- **Pin:** anchor, `intent`, `max_depth` and `asked_at` all stated; the estate
  identified by ledger name and schema; **and the `ledger_t` the run was read
  at, stated as an integer.** Exact values `[TBC — this build]`.
- **Reproduction bar:** *same question → same answer*, against a quiescent
  ledger for that run. A reader whose numbers differ has **re-derived, not
  reproduced** — and the most likely reason is that the ledger moved, which is
  a property of the estate and not of the product.
- **The cycle is already in the estate**, planted and labeled, so nothing needs
  loading to demonstrate the headline finding and no `load_*` step is part of
  the demonstration.

---

## Section E — Volatility, debt and materialization

### E.1 Half-life table

| Signal class | `λ_c` | Calibration basis | Decay driver | Supersession event | Owner |
|---|---|---|---|---|---|
| **Ownership edges** (`owns`, `controls`) | **~180 days** | **illustrative** | acquisition, disposal, restructuring | GLEIF RR-CDF daily delta touching either endpoint | Platform |
| **Ultimate-parent designation** (`hasGlobalUltimateParent`, `hasDomesticUltimateParent`) | **~365 days** | **illustrative** | group reorganization | RR-CDF delta on the designation | Platform |
| **Consolidation relationships** (`isDirectlyConsolidatedBy`, `isUltimatelyConsolidatedBy`) | **~365 days** | **illustrative** | change of consolidating parent | RR-CDF delta | Platform |
| **Exhibit 21 subsidiary list** | **~365 days** | **illustrative** | annual filing cadence | a new 10-K Exhibit 21 for the filer | Platform |
| **Entity attributes** (GLEIF Level 1) | **~30 days** | **illustrative** | GLEIF Level 1 refresh | Level 1 record update | Platform |
| **FIBO T-Box** | **~365 days** | **illustrative** | an EDM Council release | a new FIBO version loaded | Data architecture |

**These are the vault's values, raised to the Standard's table shape, and they
are NOT recalibrated here.** `λ_c` is **Control Plane configuration per
observation type**, not a per-document attribute; the table in a spec is an
**initial calibration proposal**. **Every row's basis is `illustrative`, which
means this product is not calibrated**, and saying so plainly is more useful
than implying otherwise. `λ_c` measured against actual read frequency is
`[TBC — this build]`.

**The half-life is per signal class, not per product**, and this product is the
clearest case on the ladder so far: **a single payload carries an ownership edge
decaying at ~180 days beside an Exhibit 21 subsidiary decaying at ~365 and an
attribute row decaying at ~30.** A single product-level `λ_c` could not express
it, and normalizing `F` over the classes *present* rather than the classes
*required* would let a missing source improve the score.

### E.2 Debt model and per-component debt table

`D_c = 1 − (F · C · S)` — **multiplicative**, so a collapsed dimension forces
escalation rather than being averaged away. **`F` is normalized over the
required signal classes, not over the classes actually present.**

| Component | May be absent? | Contributes to | Behavior when absent |
|---|---|---|---|
| The anchor's own resolution | **no** | — | **Fail closed → `404`.** Never an empty payload |
| The policy envelope | **no** | — | **Fail closed → `403` / `503`.** Never a permissive default |
| The Fluree family read | **no** | `F` | **Fail closed → `503`** with the source class named. **Silence is not a negative answer** — an unreachable graph store is not an entity with no family |
| **Attribute resolution for a given node** | **yes, and usually** | `S` in principle; **NOT folded into `S` in this build** — §E.2.1 and `D-IMPL-230` | **Serve with a null resolution.** 606 of 748 family nodes have no row, and 20 of the demonstrated subtree's 22. The shortfall is served as the `unresolved_jurisdiction` **roster** finding (`D-IMPL-229`) rather than compressed into a scalar. **Never a dropped member** (`D-16`, gate `CFT-G09`) |
| Class chain on a returned node | **no** | `C` | **Fail closed.** An untyped node is not admitted (gate `CFT-G01`) |
| Cycle detection | **no** | `C` | **Fail closed.** A detector that did not run is not a graph with no cycles |
| The duplicate-pair check | **yes** | `S` | Serve with a notice and elevated `D_c` |
| Consolidation basis on an edge | **yes, always** | `S` | **Mark the affected claim `NOT_EVALUABLE`.** The reified edge does not exist (§C.1.2 item 1) — the basis is not returned, and it is not returned as `null` pretending to be a lookup that came back empty |
| Valid-time interval on an edge | **yes, always** | `S` | `NOT_EVALUABLE`. Not fetched at source (§C.1.2 item 2) |

**Debt is decomposed per claim, never only per product.** A family whose tree is
complete and whose attributes are 20-of-22 absent returns **a served tree and a
roster naming those twenty**, not a product-level failure and never a
silently-shortened roster. The gap is captured **before** the concentration
decision is taken and shapes it directly: *the group is these 22 entities, and we
hold reference data on two of them* is a decision input. **`606 of 748` is not a
defect report; it is the answer.**

#### E.2.1 The measured factor table — RULED 2026-09-01 (Dave, `D-IMPL-230`)

**Every value below is MEASURED against the committed fixture pair through the
shipped scorer, or is a definition this document already states. NO WEIGHT WAS
CHOSEN.** The two `[TBC — this build]` markers this section carried — §F.2 rows
15 and 16 — are cleared here, and the clearing is a **substance** amendment to a
ruled Gate 1 document rather than a form correction, which is why the front
matter's `Gate 1 status` row records it as one.

| Factor | Value | Where the value comes from |
|---|---|---|
| **`F`** — freshness, normalized over the **required** signal classes | **`1`** | **Measured, and it is a finding rather than a convenience.** No family node and no family edge in the ledger carries an assertion date of any kind — the store holds the six predicates, `ex:lei`, `rdfs:label` and `rdf:type`, and no timestamp — so every envelope carries `observed_time=None`, which `SignalEnvelope`'s own contract defines as *unknown*. Fluree's `t` is TRANSACTION time and `D-IMPL-88` rules it must not stand in for an observation, so the store offers no second candidate. Every observation is therefore dated at the read instant and the decay factor is 1 at every read. `produce.py::measure_debt` |
| **`C`** — completeness over the elements this table declares **required** | **`1`** | **Structural, not a measurement that could have come out otherwise.** The four elements this table marks *may be absent: no* — the anchor's own resolution, the policy envelope, the Fluree family read, and the class chain on every returned node — are fail-closed conditions reached long before the scorer, and cycle detection runs unconditionally. A product holding a gate-admitted vessel has all five |
| **`S`** — semantic consistency | **`20 / 22` = `0.909090…`** **at the declared default depth of 3** | **Measured.** The whitepaper defines `S` as the fraction of assembled sources whose structured assertions agree on the entities the decision cares about. This is the first rung that reads two stores and can therefore have one, and its graph leg carries a measured self-disagreement: the duplicate-identity finding, **`SuperMicroComputerBV` and `SubSuperMicroComputerBV`** — the same company entered twice, one hop from the anchor. Two of the twenty-two served members have an identity a finding disputes. **The denominator is the roster THIS PAYLOAD SERVED**, so the figure moves with the depth asked — at `max_depth=1` the payload carries 20 members and `S` is `18/20 = 0.9`. See the correction paragraph below. `produce.py::_agreement` |
| **`D_c = 1 − (F · C · S)`** | **`0.090909…`** **at the declared default depth of 3; `0.1` at `max_depth=1`** | Arithmetic over the three rows above. Multiplicative, so a collapsed dimension forces escalation rather than being averaged away |
| **signal** | **`ok`** | `0.090909…` is below `forced_llm_threshold` and below `fail_closed_threshold`; so is `0.1` |
| `risk_sensitivity` | **`1.0`** | `ccf_config.yaml::debt_profile` — declared, versioned Control Plane state |
| `forced_llm_threshold` | **`0.60`** | idem |
| `fail_closed_threshold` | **`0.77`** | idem |

`debt_tolerance` default: **`0.25`**, declared at
`artifacts/question.yaml::parameters.debt_tolerance` and quoted as text because
the canonical encoder refuses a float. Breach → **`409` with the debt block**,
not a `200` with a warning. **`0.090909…` against `0.25` SERVES**, and the
tolerance was **not moved to make it do so**: Dave, verbatim — *"Do not calibrate
`debt_tolerance` to rescue a 0.909… Don't raise tolerance to 0.95 and don't
pretend 0.909 is the whitepaper number."*

**THERE ARE NO PER-COMPONENT WEIGHTS, AND THAT IS THE ANSWER TO §F.2 ROW 15
RATHER THAN A VALUE WITHHELD.** The model this section declares is
`D_c = 1 − (F · C · S)` — **multiplicative**, with no weight term anywhere in it,
and `ccf.halflife.debt::assess_debt` takes exactly `(factors, profile)` and
applies none. A weights row would have had to be invented to be filled, and
inventing one would have been choosing the number that decides whether this
product's headline demonstration exists at all.

**`D_c ≈ 0.0909` IS NOT "20 MISSING JURISDICTIONS."** It is `1 − S` where `S` is
`20 / 22` **undisputed identities**; the twenty members carrying no
`ccf_v2.legal_entity` row are a **different twenty**, they move the roster and
not the debt, and the two sets overlap in **nineteen** (`D-IMPL-231` part 2).

**THE TWO TWENTIES ARE DIFFERENT POPULATIONS AND MUST NOT BE READ AS ONE.** `S`'s
numerator counts the **twenty members whose identity no finding disputes** — the
twenty-two served less the duplicate pair. The `unresolved_jurisdiction` roster
counts the **twenty members carrying no `ccf_v2.legal_entity` row** — the
twenty-two less the anchor and `SuperMicroComputerBV`. **Measured, the two sets
overlap in NINETEEN members and are not the same set:**
`SubSuperMicroComputerBV` is in the roster and not in `S`'s numerator, the anchor
`SuperMicroComputerInc` is in `S`'s numerator and not in the roster, and
`SuperMicroComputerBV` is in neither. **They agree on a number and disagree on a
membership**, which is exactly the coincidence a reader will otherwise resolve
the wrong way — and it is why the roster is asserted as a **roster** and never as
its cardinality (`D-13`).

**THE ARITHMETIC THAT LOOKED LIKE A CONTRADICTION, RECORDED SO IT IS NOT
RE-DERIVED.** Reading *"20 of 22 members lack a PostgreSQL row"* as a single lump
of context debt gives `S = 2/22` and `D_c ≈ 0.909`; against a `debt_tolerance` of
`0.25` that **`409`s and never serves the tree criteria 12 and 33 and gate
`CFT-G09` exist to protect**. That is the **lump** reading, not the factor path
the scorer runs, and it is not the whitepaper's number. This table is the factor
path.

**HOW `D_c` IS GATED — MOVEMENT, NEVER A FROZEN SCALAR.** The assertion is that
**`D_c` moves when its inputs move**, together with the twenty-member roster —
**never `D_c == 0.090909…` forever**. A frozen scalar is a constant agreeing with
itself, and a debt score that does not move when its inputs move is the
idle-gate class arriving through a float. **No new gate id is minted**: the
roster's home is `CFT-G09` and the movement assertion is a test. The roster stays
**seventeen**, `CFT-G01`…`CFT-G16` and `CFT-G18` (2026-09-03, `D-IMPL-245` (4);
previously: ~~**sixteen**, `CFT-G01`…`CFT-G16`~~; `CFT-G17` remains withdrawn).

**CORRECTION 2026-09-01 (Dave), AFTER THE CLOSE PANEL'S FINDING 1 — `S` IS TAKEN
OVER THE SERVED ROSTER, AND ONLY THAT SET CHANGED.** The paragraphs above are
preserved as written and none of their figures is withdrawn; what is corrected is
the population `S`'s fraction is taken over. `produce.py::_agreement` opened with
*"the fraction of SERVED members whose identity no finding disputes"* and computed
its denominator from the deployment's SOURCE READ — which is bounded by the
declared **ceiling** of 6, not by the caller's `max_depth`, because the walk is
bounded downstream by the L4 traversal. So `max_depth=1` served **20** members and
still reported `20/22`, and `D_c` read `0.0909` at depth 1, depth 2 and depth 3
alike. Dave, verbatim: *"a scalar that cannot fail **through the door**. That is
not the §E.2 weight TBC. It is a **wrong denominator**."*

**WHAT MOVED AND WHAT DID NOT.** Only the SET. §E.2's routing is unchanged, the
absence of per-component weights is unchanged, `debt_tolerance` is unchanged at
`0.25`, and **`D_c` is NOT retied to the twenty missing jurisdictions** — that
shortfall stays SERVED AS DATA through the `unresolved_jurisdiction` finding and
its roster (`D-IMPL-229`), exactly as the paragraphs above require. The headline
figure does not move either: at the declared default depth `S` is still `20/22`,
`D_c` is still `0.090909…`, and the demonstration question still seals to
`205ae065…`. What moves is every OTHER depth: at `max_depth=1`, `S = 18/20 = 0.9`
and `D_c = 0.1`, because both disputed members sit one hop from the anchor and
survive every depth this product accepts while the denominator shrinks.

**DEPTH IS NOW A SECOND GATED BOUNDARY, AND STILL NO NEW GATE ID.** The pair
`(depth 3 → 0.0909…, depth 1 → 0.1)` is pinned as DATA at
`artifacts/expected.yaml::debt_by_depth` and read from there by a **third limb of
`CFT-G05`** — whose statement, *depth is part of product identity*, is exactly
what it holds. The roster stays **sixteen** — seventeen since 2026-09-03, with
`CFT-G18`. Measured rather than assumed: with
the source-read denominator restored, exactly ONE test in the 216-test cp-04
suite went red and it was `CFT-G05`; the identity-boundary movement gate passed
whole, because it moves its boundary at a FIXED depth where the served roster and
the source read coincide on all 22. A movement gate over one boundary says
nothing about a second.

### E.3 Materialization posture

**`derived-on-demand`**, and the article's *"materialized for depth ≤ 3"* is
**not adopted at this rung.**

**The Standard's test is mechanical: if the fastest-moving input's `λ_c` is
shorter than the intended cache window, materialization is wrong.** The
fastest-moving input here is the **attribute row at ~30 days**, against a
declared **24-hour** TTL — so the test does not by itself forbid a cache.

**What forbids it is the cache key.** Depth is part of product identity
(`D-09`), so the key is
`(tenant, anchor_lei, intent, max_depth, principal, policy_version, plan_id)`.
**A cache key missing `max_depth` is a correctness defect that presents as an
intermittent one** — the officer who asked for depth 3 gets depth 1's answer
because someone asked first. Rather than ship a materialization whose key has
seven parts on the first Tier 2 rung, the posture is on-demand and the key is
stated so a later rung can materialize deliberately.

### E.4 Supersession triggers

| Trigger | Detection | Local or cascading |
|---|---|---|
| **GLEIF RR-CDF daily delta touching any node in the family** | new or retired relationship record on either endpoint | **cascading** |
| **New Exhibit 21** for any filer in the family | a new 10-K exhibit parsed | **cascading** |
| **8-K Item 2.01** — completed acquisition or disposition | filing event | **cascading** |
| GLEIF Level 1 record update for a resolving LEI | Level 1 refresh | **local** — attributes only; the tree is unchanged |
| FIBO T-Box release | a new ontology version loaded | **cascading** — class chains are served, so they are payload |

**Invalidation cascades to every product whose `operators_invoked` touched the
superseded entity, not merely those named for it.** Named downstream targets,
from §B.5: `credit-exposure-rollup` (rung 05),
`kyc-refresh-beneficial-ownership`, `credit-memo-context` (rung 14).

**Re-derivation is LAZY** — invalidate for the next request; do not
re-materialize eagerly. A GLEIF daily delta touching a widely-held ultimate
parent would otherwise become a thundering-herd event across every family that
parent sits above, and **`hasGlobalUltimateParent` carries 103 edges in this
estate**, so the fan-out is not hypothetical.

---

## Section F — Source binding and readiness

### F.1 Element readiness

| # | Element | System of record | Interface and cadence | Available today | Gap owner | Blocker |
|---|---|---|---|---|---|---|
| 1 | FIBO T-Box | EDM Council | OWL/RDF load into Fluree | **yes** | — | — |
| 2 | Direct parent relationship | GLEIF RR-CDF L2 | loaded; **140 edges** | **yes** | — | — |
| 3 | Ultimate parent relationship | GLEIF RR-CDF L2 | loaded; **103 + 36 edges** | **yes** | — | — |
| 4 | Accounting consolidation basis | GLEIF RR-CDF | **needs a reified edge** | **no** | `ccf_dataprep` | a modeling decision, not a load — §C.1.2 item 1 |
| 5 | Relationship status | GLEIF RR-CDF | PostgreSQL | **partial** — resolves from Postgres, not Fluree; not returned at this rung | `ccf_dataprep` | same reified-edge cause as row 4 |
| 6 | Relationship validity dates | GLEIF RR-CDF golden copy | **not fetched** — the API returns parent, child, type, jurisdiction only | **no** | `ccf_dataprep` | **a deferral, not a waiver** — 280 of 280 records carry `Relationship.Period` at source |
| 7 | Exhibit 21 subsidiary list | EDGAR | parsed at build time. **343 stubs, 306 carrying a jurisdiction (89%) — the VAULT's figure, dated 2026-08-24, estate-wide, and NOT re-measured this sitting.** The family-graph figure that *was* measured is **606 of 748 nodes with no attribute row** (§C.3); the two count different populations and are not interchangeable | **partial** — no ownership percentage, **by rule** | — | 17 CFR 229.601(b)(21)(i) does not require one. **No re-parse recovers a field the disclosure rule never asked for** |
| 8 | Stub entities (`SYN-`) | Exhibit 21 | Fluree nodes; scheme published | **yes** | — | — |
| 9 | Entity attributes | GLEIF Level 1 | `ccf_v2.legal_entity`, **156 rows** | **yes** — **142 of 181** family LEIs resolve | — | — |
| 10 | Materiality threshold by intent | internal credit policy | **no such table** | **no** | product owner | the only table of that name holds an **FX post-trade tolerance in pips** for a different product |
| 11 | Consolidated total assets | XBRL `companyfacts` | PostgreSQL | **yes** | — | not read at this rung — it is row 10's denominator |
| 12 | Cross-shareholding cycle | the estate, engineered | Fluree; **2 cycles, 6 members** | **yes** | — | planted and labeled |

**No element is a build blocker.** Rows 4, 6 and 10 are `no` and each is
**out of the served contract at this rung** rather than a gap the build must
work around — §C.1.2 and §B.4.2 say which and why.

> **The Exhibit 21 population is filer-truncated before the estate sees it.**
> 601(b)(21)(ii) permits omitting subsidiaries that in aggregate would not
> constitute a *significant subsidiary* under Reg S-X 1-02(w). **A "subsidiary
> list" from Exhibit 21 is a truncated list**, and the payload must not be
> described to a consumer as *"the full corporate family."* Recorded here
> because it is a property of the source, not of the build.

### F.2 Every `[TBC]` in this document, with an owner

Built by **enumerating every marker and mapping each to a row**, not by
comparing totals — *a count is not a roster*.

| # | Marker | Section | Owner | Cleared at |
|---|---|---|---|---|
| 1 | **Four-question build-test verdict** — four leanings recorded, verdict not asserted | §0.1, §0.4 | **vault** | a vault ruling |
| 2 | **Assembly Mode confirmation** — the article's frontmatter reads `assembly_mode: null`; Mode 1 is proposed | §0.4, §B.1 | **vault** | a vault ruling |
| 3 | **`depth` 1–5 versus `max_depth` 1–6** — the article's range against Dave's measured ceiling | §B.4.1 | **vault** | a vault ruling. **Dave's ruling governs the build regardless** |
| 4 | **`out_of_scope` is `null` in the article** — four exclusions proposed | §B.5 | **vault** | a vault ruling |
| 5 | Residency constraints; cross-border serving; **whether an edge to a restricted-jurisdiction entity is the same question as its attributes** | §B.2 | **identity and access** | certification |
| 6 | **Entitlement discrimination over the family population — NOT MEASURED** | §B.2 | **this build** | Gate 2 |
| 7 | Ontology IRIs for rows 4, 5, 6 of §C.1 | §C.1 | **`ccf_dataprep`** | when the reified edge exists |
| 8 | Schema artifact `corporate_family.v1.json` | §B.1 | this build | Gate 2 |
| 9 | p95 budget — per step, total, envelope; **and the p95 fan-out** | §D.2 | this build | Gate 2 |
| 10 | `payload_hash` for the pinned run | §D.4 | this build | Gate 2 |
| 11 | Replay fixture `CFT-R01`, hashes | §D.5 | this build | Gate 2 |
| 12 | The two L4 operator keys | §D.2 | this build | Gate 2 |
| 13 | Pin values for the demonstrated run, **including the `ledger_t`** | §D.8 | this build | Gate 2 |
| 14 | TTL expiry and refusal count for the pinned run | §B.1.2 | this build | Gate 2 |
| 15 | Per-component `D_c` weights — 9 rows — **CLEARED 2026-09-01 (Dave, `D-IMPL-230`): THERE ARE NONE.** The declared model is multiplicative and carries no weight term; the answer to this row is that the marker had no referent, not a value withheld — §E.2.1 | §E.2 | this build | **CLEARED** |
| 16 | `debt_tolerance` calibration — **CLEARED 2026-09-01 (Dave, `D-IMPL-230`): `0.25`, NOT moved.** The measured `D_c` is `0.090909…` and it SERVES against `0.25`; the tolerance was not calibrated to rescue a number — §E.2.1 | §B.4, §E.2 | this build | **CLEARED** |
| 17 | `λ_c` measured against read frequency | §E.1 | this build | Gate 2 |
| 18 | Counterfactual fixture `CFT-F01` — the two-answer comparison | §A.2 | this build | Gate 2 |
| 19 | **Sabotage result for each of the SEVENTEEN gates** (2026-09-03; previously ~~SIXTEEN~~; `CFT-G18`'s observed red is recorded in `artifacts/gates.yaml`) | §D.7, §G.2 | this build | Gate 2 |
| 20 | **The three Gate 1 conflicts of §F.4** — **CLEARED 2026-08-31 (Dave, `D-IMPL-225`)**: all three ruled, two by amending a locked criterion | §F.4 | **Dave** | **Gate 1 — CLEARED** |

**Twenty rows. Four belong to the vault, one to identity and access, one to
`ccf_dataprep`, thirteen to this build, and ONE to Dave. Dave's — row 20 — was
the only blocking row, and it is CLEARED at Gate 1** (`D-IMPL-225`), which
unblocks rows 8, 9 and 19. **Rows 15 and 16 are CLEARED 2026-09-01**
(`D-IMPL-230`), which is the §E.2 substance amendment recorded in the front
matter's `Gate 1 status` row. **SEVENTEEN rows remain open, and NONE of them
blocks**: eleven clear at Gate 2, six belong to the vault, identity-and-access
and `ccf_dataprep` and are named rather than invented. The count is taken by
enumerating the rows and not by subtracting from a remembered total.

### F.3 Access path, identifiers, history, volumetrics

**Estate binding — the two stores this product opens, and the three it does
not.** A reader asking *"which stores does this product touch?"* gets the whole
answer here.

| Store | Verdict for this product |
|---|---|
| **Fluree `fibo-v2`** | **READ.** Edges, ontology, labels, LEIs — §C.1 rows 1, 2, 3, 4, 6, 7, 8, 12. Read-only; every query carries an explicit `FROM <fibo-v2>` |
| **PostgreSQL `ccf_v2`** | **READ.** Attributes and entitlement — §C.1 rows 5, 8, 9, 10, 11. **The table is `legal_entity`, not `crosswalk`** (§C.4 trap 4) |
| MongoDB | **not read.** Filing text and passages; passage lineage arrives at rung 13 |
| SQLite (departmental) | **not read.** Nothing family-shaped |
| Neo4j | **not read.** **Dropped from the v2 estate 2026-08-16**, which is why cycle detection runs application-side |

**Two stores read, three excluded.** Gate **`CFT-G10`** asserts the positive
half — **both** stores are opened, each for its own thing — and is sabotaged by
serving attributes from Fluree.

**Connection.** Environment-variable **names** only, in `backends.yaml`; **never
a host, port, path or credential in the tree**. `ccf_dataprep` is **read-only**
to this repository and nothing in this build writes to it.

**Identifier reality.** `LEI` end to end. The crosswalk is *the LEI itself* —
Fluree carries `ex:lei` on a node, PostgreSQL keys on `lei`, and there is no
intermediate mapping table to own. **Measured coverage is §C.3, and it is
mostly holes by design.**

**History depth.** The Fluree ledger is append-only and carries assertion time
from load. **It does not carry valid time** (§C.1.2 item 2), so the history the
product can reconstruct is *what was recorded*, never *what was in force*. Where
the source publishes snapshots without history, retention starts now — the RR
golden copy's `Relationship.Period` is on disk upstream and unfetched, and
**history not captured cannot be reconstructed later.**

**First-build volumetrics — the population every gate and control needs
something to act on, and every one of them has it:**

| Required case | Present? | Population |
|---|---|---|
| An anchor with a family deep enough that `max_depth` changes the answer | **yes** | SMCI: 20 nodes at depth 1, 21 at 2, **22 at 3** |
| **At least one cycle reachable from an LEI-bearing anchor** | **yes — exactly one** | cycle 1, via the single edge `SuperMicroComputerInc → CycMeridianHoldingsSa` |
| A cycle that is **not** reachable, as the contrast | **yes** | cycle 2 — **zero** external in-edges |
| A negative control on production data that finds something and still finds no cycle | **yes** | the same anchor over `isDirectlyConsolidatedBy` alone: **2 nodes, depth 1, 0 cycles**. Not an empty walk |
| Nodes with no attribute row | **yes, abundantly** | **20 of 22** in the subtree; **606 of 748** in the graph |
| The same company entered twice | **yes** | `SuperMicroComputerBV` / `SubSuperMicroComputerBV`, one hop from the anchor |
| A tree at the declared ceiling | **yes** | depth **6**, which `PSC-0124` attains — **seven** roots do |
| A predicate small enough that a count would miss it | **yes** | `controls`, **3** edges, and flipping it moves the root count by **one** |

> **The criterion-19 control was nearly an empty walk, and that was caught by
> measuring rather than by reasoning.** An earlier draft of the control asserted
> that SMCI *"has no `isDirectlyConsolidatedBy` edge at all."* Measured, it has
> exactly **one**, to `SuperMicroComputerBV`. Had that stood, the negative
> control would have been **an empty walk asserting no cycle — a control that
> cannot fail.** Per-predicate child counts from the anchor, all measured:
> `owns` **19**, `isDirectlyConsolidatedBy` **1**, `isUltimatelyConsolidatedBy`
> **1**, `hasGlobalUltimateParent` **1**, `controls` **0**,
> `hasDomesticUltimateParent` **0**.

**No spec passes review with an unowned gap.** Every `no` and `partial` in §F.1
carries a named owner.

### F.4 Recorded findings, and the three Gate 1 conflicts AS RULED

**Findings 1 to 6, and finding 9, are RECORDED SDK gaps and NONE is closed
here.** `D-04` of `24-CONTEXT.md` governs: **a minor phase RECORDS gaps; a
separate phase closes them.** No file under `src/` or `runtime/` is modified by
this phase.

**Findings 7 and 8 are measurement notes.**

**Conflicts 1, 2 and 3 were the Gate 1 decision items, and ALL THREE ARE NOW
RULED** — **2026-08-31, Dave, `D-IMPL-225`: approved with three amendments.**
Each conflict below keeps its measurement and its alternative exactly as
submitted, and carries Dave's ruling beside it, **quoted rather than
paraphrased**. Two of the three amended a locked criterion rather than bending
the product to it, on the `D-IMPL-222` precedent; the amendments landed in
`.planning/ROADMAP.md` and `docs/DECISIONS.md` **before** the `Gate 1 status`
row was flipped and **before Wave 3**.

#### Finding 1 — `D-26` · the Fluree adapter floors but cannot pin

**RECORDED, not closed.** `Fluree-Min-T` sets a **lower** bound — *"do not
answer older than this `t`"* — and leaves the upper bound open. **No `@t:` or
`from: ledger@t:N` construction exists** in `src/ccf/graph/backends/fluree.py`.
On a quiet ledger a floor and a pin are indistinguishable; **that is a vacant
guarantee, not a satisfied one.** It is why §D.5's replay test is written to
reach a failing step 4 rather than to omit it.

> **CLOSED 2026-09-03 (Phase 24.5.1), by dated note; the observation above
> stands as measured.** When measured, on 2026-08-31, the adapter sent only a
> floor. Phase 24.5 closed the gap as `24.5-L-01` through `24.5-L-04`
> (`D-IMPL-240` (2)): the JSON-LD route pins a read as `from: <ledger>@t:N`
> (`src/ccf/graph/backends/fluree.py::FlureeGraphStore`), the lineage carries
> that pin as `store_snapshot_pin` on
> `src/ccf/products/contract.py::ProductLineage`, and the three time axes — event
> time, transaction time, `as_of` — are named apart in that adapter's docstring
> (`24.5-L-03`, `L-04`; `D-IMPL-88` stands: `t` never implements `as_of`). This
> rung's transcript was re-captured on 2026-09-03 with the ledger head at `5296`
> and reproduced byte for byte; §G.4's quiescent-ledger qualifier still describes
> what was demonstrated.

#### Finding 2 — `D-27` · `graph_snapshot_at` is a `datetime` and store `t` is an `int`

**RECORDED, not closed.** A type mismatch for transaction-snapshot pinning.
`src/ccf/products/contract.py::ProductLineage.graph_snapshot_at`. The product records `ledger_t` **beside**
the snapshot field rather than inside it (§D.6).

> **CLOSED 2026-09-03 (Phase 24.5.1), by dated note.** `24.5-L-02`
> (`D-IMPL-240` (2)) added the additive field `store_snapshot_pin` to
> `src/ccf/products/contract.py::ProductLineage`, so an `int` transaction pin has
> an L6 field of its own beside the `datetime` snapshot. Every `ProductLineage`
> field enters the content address, which is why `CFT-G16`'s two seals were
> re-sealed once, under `D-IMPL-240` (1), in the same commit as the field. The
> product still records `ledger_t` beside `graph_snapshot_at`.

#### Finding 3 — `D-28` · Fluree `@iso:` searches EVENT time and is backdatable

**RECORDED, not closed.** `@iso:` resolves nearest-at-or-before against
`db:time`. **Legitimate for a CLOCK pin, wrong for a TRANSACTION pin, and
neither of the two is CCF `as_of`.** Recorded so a later reader does not adopt
it as an `as_of` implementation on the strength of its shape.

#### Finding 4 — `D-29` · the adapter docstring collapses three time axes into two

**RECORDED, not closed.** A docstring defect, and **a different seam from
findings 1 to 3** — those are mechanism; this is a description of mechanism.
**`src/` is not edited in this phase**, so the correction is not made here.

#### Finding 5 — `D-30` · the MCP resource URI cannot address a parameterized product

**RECORDED, not closed.** `PRODUCT_URI_TEMPLATE` is three path segments with no
query surface. **Every Tier 2+ product will hit this**, because every one of
them takes an anchor plus at least one scope parameter. This is the finding
Conflict 1 is the mechanism face of, and **`D-34`** (finding 9) is its sibling:
`D-30` is *the resource cannot carry the parameters*, `D-34` is *the resource
cannot be withheld*. Both are recorded; neither is closed.

> **CLOSED 2026-09-03 (Phase 24.5.1), by dated note.** `24.5-L-08` gave the
> egress a PRODUCT ADDRESS with a fifth path segment carrying the canonical
> question (`runtime/ccf_runtime/mcp/egress.py::AddressedQuestion`), so a
> parameterized product is citable by a client; `24.5-L-09` made the resource
> optional (finding 9, below). Neither row changed what THIS door does: its
> registered product resource still refuses by name (`CFT-G13` limb (b)), which
> is now a ruling rather than a limit — see finding 9's note.

#### Finding 6 — `D-31` · declared product gates have NO SDK or CI expression

**RECORDED, not closed.** Measured: **40 product-level gate ids across four
products**, and
`grep -rnE "OFS-G|FTS-G|[A-Z]{2,4}-G[0-9]{2}" --include=*.py src/ runtime/`
returns **0**. Declaration lives in spec prose and artifact comments; execution
lives in hand-written pytest; **the link between them is naming convention.**
This is a **different seam** from findings 1 to 3 (mechanism) and from finding 4
(a docstring), and it is why **Phase 24.5** exists. **`D-IMPL-212` — that the
Standard's `Enrich` has no SDK expression — is likewise OPEN and is not closed
by `D-IMPL-223`** (§D.2.3).

> **CLOSED 2026-09-03 (Phase 24.5.1), by dated note.** `24.5-L-10` — under
> `D-IMPL-224`, which ORDERED a checker and refused a serve-time gate type —
> shipped `tools/check_product_gates.py`: every id in a product's `gates.yaml`
> must name an EXECUTING pytest node, checked in CI as `make product-gates`, and
> measured at this note's writing as `checked 5 product trees, 57 declared gates,
> 57 executing`. `24.5-L-18` folded into that design (the checker resolves an
> executing test, never a witness string), and `24.5-L-49` (Dave, 2026-09-02:
> *"Both: gates.yaml + missing tests"*) backfilled `gates.yaml` for cp-00 through
> cp-03 and their missing tests. `D-IMPL-212` (`Enrich`) is not closed by this
> note and stays OPEN.

#### Finding 7 — `PSC-0124` is not the unique deepest root

**A measurement note, and it changes how a check must be phrased.** Depth 6 is
attained by **seven** roots: `PSC-0018`, `PSC-0037`, `PSC-0053`, `PSC-0089`,
`PSC-0124`, `PSC-0140`, `PSC-0153`. `PSC-0124` is among them, so **the locked
criterion is TRUE as written and is not amended.** But a check phrased *"the
deepest root is `PSC-0124`"* would assert a uniqueness the estate does not
carry, and nothing distinguishes it — six of the seven span 7 nodes and
`PSC-0037` spans **11**. **Every assertion phrases it as "depth 6, which
`PSC-0124` attains".**

#### Finding 8 — the cycle roster order is a convention and must ship with the detector

**A measurement note.** Criteria asserting exact ordered rosters hold only under
**rotation to the lexicographically smallest member** (§C.4 trap 5). Stated in
this specification so the shipped detector inherits it; a correct detector using
a different rotation would fail a correct assertion, and the failure would look
like a product defect.

#### Finding 9 — `D-34` · `build_egress_server` cannot withhold the product resource

**RECORDED, not closed.** *`build_egress_server` cannot omit a product resource
from MCP `resources/list` without `runtime/` work, so a genuinely tool-only door
is not expressible today.* Same `D-04` posture and **the same class as `D-30`
and `D-33`**: a capability the specification wants, for which the shipped
surface has no expression, recorded rather than engineered around.

**It is numbered ninth because it was RULED at Gate 1, after findings 1 to 8
were written — but it belongs with findings 1 to 6 as an SDK gap, not with
findings 7 and 8 as a measurement note.** It arose from Conflict 1 below, it is
the reason criterion 37 was amended, and **criterion 49 is extended to it**: it
is recorded in `docs/DECISIONS.md`, it is closed by neither this phase nor any
other in this wave, and **no file under `src/` or `runtime/` is modified to
close it.**

> **CLOSED 2026-09-03 (Phase 24.5.1), by dated note — with a product ruling.**
> `24.5-L-09` gave `runtime/ccf_runtime/mcp/egress.py::build_egress_server` an
> `expose_product_resource` flag (default `True`), so a tool-only door IS
> expressible. This rung KEEPS its resource registered and refusing by name and
> passes no flag: switching it to a tool-only door is a design change for the
> rung's next rebuild, not a correction (`D-IMPL-245`, deferred list), so
> `CFT-G13` limb (a) now measures a choice rather than an SDK limit. Criterion 37
> as amended stands.

---

#### **Conflict 1 — criterion 37 (`CFT-G13`, tool-only) against `build_egress_server`**

**Measured, and the citation resolves.**
`runtime/ccf_runtime/mcp/egress.py::build_egress_server` registers
`@server.resource(PRODUCT_URI_TEMPLATE, mime_type=PRODUCT_MIME_TYPE)`
**unconditionally**. Only the tool, at `:529` — `if expose_product_tool:` —
is behind a flag. `expose_product_tool` defaults to `False`, so the builder can
be configured **resource-only**, or **resource-plus-tool**; it **cannot be
configured tool-only**. The resource handler passes `request=None` because the
URI carries no query surface, and its own docstring says so:
*"`PRODUCT_URI_TEMPLATE` is three path segments with no query surface, so no
caller reaching this handler has supplied a `ProductRequest`."*

**The bind:** criterion 37 requires *"the MCP door is TOOL-ONLY"* and criterion
38 requires that `server/serve.py` wrap the assembler with
`build_egress_server`. **Both cannot be literally satisfied by the shipped
builder.**

**Proposed reading, as submitted.** The resource stays registered — because the
SDK registers it — and **the deployment's resolver REFUSES BY NAME when
`request is None`**, raising the SDK's own `ProductNotServable`
(`runtime/ccf_runtime/mcp/egress.py::ProductNotServable`) stating that this product class is
parameterized and must be asked through the tool.

> **THE WEAKNESS IN THAT READING, STATED PLAINLY RATHER THAN SMOOTHED —
> reproduced here VERBATIM as submitted, because it is the record that the
> weakness was stated BEFORE the ruling and not discovered after it:**
>
> **A registered-but-refusing resource still appears in MCP `resources/list`.**
> A client enumerating the server's surface sees a product resource advertised.
> So the proposed reading satisfies *"the resource cannot be used to obtain this
> product"* — which is a **weaker** claim than criterion 37's *"no resource is
> exposed."* Dave should rule on that distinction knowingly. If the criterion
> means *not enumerable*, this reading does not satisfy it and the criterion
> needs amending or the builder needs widening.

**Alternative, as submitted.** Widen `build_egress_server` so resource
registration is conditional. **That touches `runtime/` and runs against `D-04`
of `24-CONTEXT.md`** — a minor phase records gaps and does not close them.

**RULED AT GATE 1 — 2026-08-31, Dave, `D-IMPL-225` amendment 1. THE CRITERION
WAS FALSE AGAINST THIS TREE AND WAS AMENDED RATHER THAN ENGINEERED AROUND.**

Dave, verbatim:

> *"`build_egress_server` cannot be tool-only. A listing that includes the
> resource is the SDK. Criterion 37 as written ('no resource is exposed') is
> false against this tree."*

**What ships.** `runtime/` is **NOT** touched (`D-04`). The door is a
**REGISTERED RESOURCE THAT REFUSES**, and `CFT-G13` (§G.2) asserts three things
**together**, never one of them alone:

1. the resource **IS** registered and **enumerable in `resources/list`**;
2. a resolve or read of it returns `ProductNotServable`
   (`runtime/ccf_runtime/mcp/egress.py::ProductNotServable`) or the existing refusal type, and
   **NEVER a tree**;
3. the **TOOL is the only path that SERVES**, taking a client-supplied `lei` and
   `max_depth`.

**Sabotage, stated here so the build inherits it: THE RESOLVER RETURNS A
PAYLOAD → `CFT-G13` MUST GO RED.**

**The weakness was ruled on, not smoothed.** What ships satisfies *"the resource
cannot be used to obtain this product"* and **NOT** the literal *"no resource is
exposed"* — a registered-but-refusing resource is **strictly weaker** than
absence, and it still appears in `resources/list`. **Criterion 37 was amended to
say what is true rather than left asserting something false.**

**The gap that leaves is RECORDED as `D-34`** — finding 9 above, same `D-04`
posture and the same class as `D-30` and `D-33`. **Criterion 49 is extended to
it. It is not closed here.**

**The alternative was declined**, for the reason stated when it was submitted:
it touches `runtime/`.

**Downstream.** Plan `24.4-09` (the MCP door) and plan `24.4-12` (the `CFT-G13`
sabotage) build to the ruled reading above — the three-part assertion, and the
resolver-returns-a-payload sabotage.

---

#### **Conflict 2 — criterion 47 (`run.py` consumes through `ProductClient`) against the in-process transport**

**Measured, and both citations resolve.**

- `src/ccf/client/adapters/binding_document.py::RULED_OUT_KEYS` defines
  `RULED_OUT_KEYS`, whose **first entry refuses `resolver:` BY NAME**: *"the SDK
  builds the resolver itself from the data keys below — a deployment supplies
  the projection through `plan:` and nothing else."* Refused **separately from
  an unknown key**, deliberately, so a rejected shape cannot return under a
  re-spelling.
- `src/ccf/client/adapters/inprocess.py::_boot` — `_boot` builds the resolver
  through `build_governed_resolver` from the `binding.yaml` data keys, against
  an **already-populated** graph. It performs no L1 ingest.

**The bind:** criterion 34 requires cp-04 to **open two systems of record during
the assembly**. The `binding.yaml` path cannot express that — it has no key for
a second store's read, and the one key that could carry a custom composition is
the one refused by name.

**Proposed reading, as submitted.** Use
**`ProductClient(product_id=…, adapter=…)`** — the constructor's **documented
direct-adapter form** (`src/ccf/client/client.py::ProductClient.__init__`: *"adapter: The
transport that carries the question. Supplied directly by an adapter author or a
test"*) — over an adapter cp-04 supplies that conforms to
`ccf.client.wire.TransportAdapter` **structurally** and calls `assembler.py`.

**Alternative, as submitted.** Pre-populate the graph producer-side, on `hw1`'s
shape, and let `binding.yaml` resolve against it. **That moves "both stores are
opened" out of the assembly and into a load step** — which would make `CFT-G10`
an assertion about a fixture loader rather than about the product, and
criterion 34 says *during the assembly*.

**RULED AT GATE 1 — 2026-08-31, Dave, `D-IMPL-225` amendment 2. THE PROPOSED
READING IS ADOPTED, AND THE BINDING IS NOT WIDENED.**

Dave, verbatim:

> *"Binding stays single-store. Two-store assembly happens inside the product,
> not via a forbidden `resolver:` key and not via a fixture that pre-opens both
> stores."*

**What ships.** `ProductClient(product_id=…, adapter=…)`, the documented public
constructor at `src/ccf/client/client.py::ProductClient.__init__`, over an adapter cp-04 supplies
that conforms to `ccf.client.wire.TransportAdapter` structurally and calls
`assembler.py`. **The binding stays SINGLE-STORE and is not widened** — the
two-store assembly happens **INSIDE the product**, by neither a forbidden
`resolver:` key nor a fixture that pre-opens both stores. **The consume path is
`ProductClient` exactly as `D-20` requires; no `GET /tenant/class/version` path
exists anywhere in the example; nothing under `src/` changes**, and
`for_product` remains the ordinary path for deployments that fit the binding
document.

**`CFT-G10` therefore asserts THE ASSEMBLY opened both stores, not that the
RUNNER did** — criterion 34 was **clarified** at Gate 1 to say exactly that,
because a fixture that pre-opens both and hands the product a populated graph
would turn the gate into an assertion about a fixture loader.

> **A CONSISTENCY FINDING WITH THE CLIENT WORK, RECORDED BECAUSE IT IS EASY TO
> MISREAD LATER.**
>
> **cp-04 is the FIRST `cp-*` rung to consume through the client seam at all.**
> `cp-00` through `cp-03` never import `ProductClient` — they go straight
> through `ContextAssemblerProtocol`.
>
> The client work of **Phases 17, 18 and 20** lives in the **`hw1-*`** trees and
> proves a **DIFFERENT** property, stated in that seam's own docstring as
> *"same `consume.py`, different `CCF_BINDING`, identical `Result`"* — a
> transport swap as an ops action, with no code change.
>
> **cp-04 supplies its adapter IN CODE and therefore does NOT re-prove that.**
> Its portability claim is **`D-21`'s**: one standalone assembler, two thin
> callers — `run.py` in-process and `server/serve.py` over MCP. **Both claims
> are legitimate and they are not the same claim.** No sentence in this
> specification, in the README, in the documentation page, in any artifact or in
> any test name may imply cp-04 re-proves hw1's.

**Downstream.** Plan `24.4-08` (`run.py` through `ProductClient`) and plan
`24.4-10` (the `CFT-G10` sabotage) build to the ruled reading above.

---

#### **Conflict 3 — criterion 43 (a closed schema under `docs/schemas/`) against criterion 49 (`src/` untouched)**

**Measured, and the citations resolve.**

- `tools/dump_schemas.py::committed` — `committed()` reads
  `sorted(SCHEMAS_DIR.glob("*.json"))`, **top-level only**, where
  `SCHEMAS_DIR = REPO_ROOT / "docs" / "schemas"` (`:82`).
- `differences()` reports any committed file **not** produced by
  `SDK_ARTIFACT_CLASSES` as `orphan: … (no such artifact class in
  SDK_ARTIFACT_CLASSES)`, which is **CI red**.
- `tools/dump_schemas.py::main` — `make schemas` **`unlink()`s** every orphan.
- `tests/cli/test_schema_export.py::test_an_orphan_schema_is_drift` — `test_an_orphan_schema_is_drift`
  asserts exactly that behavior.

**The bind:** criterion 43 requires a **closed schema for `gates.yaml`,
committed under `docs/schemas/`**. `SDK_ARTIFACT_CLASSES` lives in `src/`, and
criterion 49 forbids modifying any file under `src/`. **A hand-written
top-level `docs/schemas/*.json` is therefore CI-red on commit and deleted by the
next `make schemas`.**

**Proposed reading, as submitted.** The closed schema lands at
**`docs/schemas/product-gates/cp.product-gates.json`** — **inside**
`docs/schemas/` as criterion 43 requires, and **outside** the top-level glob, so
it is neither an orphan nor a deletion target. Verified: `docs/schemas/` today
contains 27 files and **no subdirectories**, so the subdirectory is a new,
unambiguous namespace rather than a collision. **It is correctly NOT SDK-owned**
— CLAUDE.md §11's *mechanism, not values*: the SDK never invents a schema for a
namespace that is not its own, and **a product-level gate roster is the
product's namespace, not the fabric's.** `gates.yaml`'s own header points at the
open `ccf.declared-artifact.json` envelope like every other example artifact,
and **cp-04's own test validates the document against the closed schema**.

**Alternative, as submitted.** Add an SDK artifact class so `dump_schemas`
generates the schema. **That modifies `src/` and breaks criterion 49**, and it
would make a per-product gate roster an SDK-owned concept — which `D-IMPL-224`
declined when it ruled out a `ProductGate` Protocol.

**RULED AT GATE 1 — 2026-08-31, Dave, `D-IMPL-225` amendment 3. THE PROPOSED
READING IS ADOPTED, AND THE SUBDIRECTORY IS DELIBERATE.**

**What ships.** **`docs/schemas/product-gates/cp.product-gates.json`**, with
**CLOSED keys**, validated against by
`examples/cp-04-corporate-family-tree/artifacts/gates.yaml`. It is **inside**
`docs/schemas/` as criterion 43 requires and **deliberately OFF** the top-level
`docs/schemas/*.json` glob that `tools/dump_schemas.py::committed` walks and `:399`
`unlink()`s, **so a hand-authored file is never destroyed as an orphan**.
Verified before the ruling: `docs/schemas/` holds **27** files and **ZERO**
subdirectories, so the namespace is new and uncontested. It is correctly **NOT
SDK-owned** — a per-product gate roster is the product's namespace, not the
fabric's, and making it an SDK artifact class is the surface `D-IMPL-224`
declined. **The subdirectory is what keeps criterion 43 and criterion 49 from
contradicting each other.**

**ENFORCEMENT IS PHASE 24.5's CHECKER, NOT THIS PHASE** (`D-24`). This phase
declares the roster as data under a closed schema and validates the document
against it; **the checker that binds a declared gate id to an executing test is
24.5's**, and until it exists the link remains naming convention — `D-31`,
finding 6.

**The alternative was declined**, for the reason stated when it was submitted:
it modifies `src/`.

**Downstream.** Plan `24.4-03` (`gates.yaml` and its closed schema) builds to
the ruled reading above.

---

## Section G — Operate and govern

### G.1 The operating contract

| Entry | Content |
|---|---|
| **Accountable owner** | product: Credit Risk · data steward: reference data / entity master · policy owner: identity and access — **roles, not individuals** |
| **Service objectives** | p50 / p95 assembly latency, expected volume, concurrency ceiling, payload bound, absolute per-call cost: `[TBC — this build]`. **Payload bound is the one to watch**: the anchor's family is 22 nodes, but the graph's largest is 11 and the deepest is 6, and a badly-chosen anchor at `max_depth=6` is bounded by fan-out rather than by depth |
| **Degradation contract** | **Mandatory (fail closed):** anchor resolution → `404`; entitlement → `403` / `503`; **the Fluree family read → `503` with the source class named**; the class chain on any returned node; cycle detection. **Non-mandatory (serve with elevated `D_c` and a notice):** attribute resolution per node, the duplicate-pair check, the consolidation basis, valid-time intervals |
| **Debt model** | §E.2, nine components. `debt_tolerance` default `[TBC — this build]` |
| **Observability** | per-operator latency · **`D_c` distribution** · **gate-failure counts by gate, all seventeen** (2026-09-03; previously ~~all sixteen~~) · **`max_depth` usage distribution** and **over-cap refusal rate** · **the ratio of returned nodes with `attributes: null` to those without** · cycle-finding rate · entitlement denials · TTL refusal rate · **the `ledger_t` each run read at**. This is also the evidence base for moving every `λ_c` in §E.1 off `illustrative` |
| **Retention and record of record** | **GLEIF is record of record for relationships and for Level 1 attributes; EDGAR for Exhibit 21; the estate itself for the engineered cycle.** The fabric references them and does not replace them. Replay-record retention tier: `[TBC — this build]` |
| **Test fixtures** | `CFT-F01` counterfactual (§A.2) · **`CFT-G01`…`CFT-G16` and `CFT-G18` — seventeen product gates** (§G.2; 2026-09-03, `D-IMPL-245` (4); previously ~~`CFT-G01`…`CFT-G16` — sixteen product gates~~; `CFT-G17` remains withdrawn) · `CFT-R01` replay assertion (§D.5) · the five negative controls of §G.3 |
| **Lifecycle** | **`draft`** — **Gate 1 APPROVED 2026-08-31 (Dave, `D-IMPL-225`) on the amended text**, with three amendments landed in `.planning/ROADMAP.md` and `docs/DECISIONS.md` before this row was written. Gate 2 not started: no code, artifacts or tests exist yet. Certification additionally requires every §F.2 row closed or accepted by a named owner |

**The obligation an operator must not lose.** **A member with no attribute row
is a member.** 606 of 748 family nodes have no row, and a build that quietly
serves only the 142 that do returns a smaller, tidier, wrong family — with no
error, and with a concentration denominator that is wrong in the safe-looking
direction.

### G.2 The seventeen product gates

**`CFT-G01` through `CFT-G16`, and `CFT-G18`** — seventeen since 2026-09-03
(`D-IMPL-245` (4); previously: ~~The sixteen product gates: `CFT-G01` through
`CFT-G16`~~; `CFT-G17` remains withdrawn and is never re-minted). Each is a
testable assertion naming the defect it detects and the sabotage that must turn
it RED.

> **This table is NOT the machine source for any check** (`D-22`).
> `artifacts/gates.yaml` is, under a closed schema, with **every id as DATA**.
> A prose table cannot be held against a run.

| Gate | Assertion | Sabotage that must turn it RED | Evidence |
|---|---|---|---|
| **`CFT-G01`** | **Every returned node carries a known FIBO class.** An untyped or off-ontology node cannot enter silently | admit an untyped node | §D.2.1 role 4 · §C.5 |
| **`CFT-G02`** | **Every returned edge is one of the six declared family predicates** — `owns`, `controls`, `isDirectlyConsolidatedBy`, `isUltimatelyConsolidatedBy`, `hasGlobalUltimateParent`, `hasDomesticUltimateParent` | admit a seventh predicate | §C.5 · seven other predicates exist in this ledger and are deliberately excluded |
| **`CFT-G03`** | **`max_depth` above the declared ceiling of 6 is REFUSED BY NAME.** Never clamped | replace the refusal with a **silent clamp to 6** | §B.4.1 · `D-07` |
| **`CFT-G04`** | **A missing `max_depth` takes the DECLARED default of 3** — read from the declaration, never invented at serve time | default at serve time instead of reading the declaration | §B.4.1 · `D-08` |
| **`CFT-G05`** | **Depth is part of product identity.** Two depths are two content addresses | make `max_depth` not change the content address | §D.4 · `D-09` |
| **`CFT-G06`** | **`as_of` is refused `400 not_supported_at_tier`** | silently honor it | §B.4.3 · `D-01` |
| **`CFT-G07`** | **A cycle reaches the consumer carrying `type`, ORDERED `members` AND the `closing_edge`** — asserted as the exact roster, never as `len(findings) > 0` | **drop the closing edge** | §D.2.2 · `D-11`, `D-13` |
| **`CFT-G08`** | **Findings are ORTHOGONAL to the tree.** No node carries a cycle flag | flag cycle membership **on the nodes** instead | §D.2.2 · `D-12` |
| **`CFT-G09`** | **A node carrying no LEI stays in the tree AND in the roster.** A failed join is a null resolution or a finding | **drop members whose Postgres join fails** | §C.3 · `D-16` · 606 of 748 |
| **`CFT-G10`** | **THE ASSEMBLY opened both stores — Fluree for edges and ontology, PostgreSQL for attributes.** The subject is the assembly, **NOT the runner**: a fixture that pre-opens both stores and hands the product a populated graph does **NOT** satisfy this gate | **serve attributes from Fluree** — and equally, **move the opening into a fixture loader** | §C.3 · §F.3 · criterion 34 **as clarified**, `D-IMPL-225` amendment 2 |
| **`CFT-G11`** | **The returned node set resolves to attributes in ONE batched PostgreSQL query** | **fire one query per node** | §D.2.3 |
| **`CFT-G12`** | **No LLM client is reachable from any §D step** — Assembly Mode 1 | make one reachable | §B.3 |
| **`CFT-G13`** | **The MCP door SERVES THROUGH THE TOOL ONLY, and the registered product resource REFUSES.** Three parts, asserted **together**: (a) the resource **IS** registered and **enumerable in `resources/list`**; (b) a resolve or read of it returns `ProductNotServable` (`runtime/ccf_runtime/mcp/egress.py::ProductNotServable`) or the existing refusal type and **NEVER a tree**; (c) the **TOOL is the only path that serves**, taking a client-supplied `lei` and `max_depth` | **the resolver returns a payload** — a resource read that yields a tree instead of refusing | §D.1 · `D-18` · `D-34` · criterion 37 **as amended**, `D-IMPL-225` amendment 1, and §F.4 Conflict 1 |
| **`CFT-G14`** | **One standalone assembler serves both callers.** `assembler.py` knows nothing about MCP | give `server/serve.py` its **own** assembly path | `D-21` — the standalone property is DEMONSTRATED by two callers sharing one module, not asserted |
| **`CFT-G15`** | **Each served node carries its FIBO class chain** | serve the tree without type information | §D.2.1 role 2 |
| **`CFT-G16`** | **Perspective conditions on FIBO class**, not on a hand-written role map | substitute a hand-written role map | §D.2.1 role 3 |
| **`CFT-G18`** | **An LEI carried by MORE THAN ONE node is REFUSED as `AnchorAmbiguityRefusal`** (`src/ccf/products/request.py::AnchorAmbiguityRefusal`) — typed ambiguity data returned through the D-60 channel, naming every colliding node; never the first binding of an unordered `SELECT`, never a 404, never a served family with a finding | **restore first-binding** — return the first binding `resolve_anchor` yields | §B.4 · `D-IMPL-245` (4) · `24.5-L-16` · Phase 24.5.1 criterion 19 (added 2026-09-03) |

**`CFT-G17` does not exist.** It is **WITHDRAWN** with ontology role 1
(2026-08-31, Dave), for the two independently measured reasons at §D.2.1: the
estate cannot exhibit the stop, and the SDK has no expression for it. **It is
not replaced by a positive-property restatement**, which was refused by name as
a tautology over a class-homogeneous population. **The roster is seventeen**
(2026-09-03, `D-IMPL-245` (4): `CFT-G18`, the ambiguous anchor, is the next free
id and not a re-mint; previously: ~~**The roster is sixteen.**~~).

**EVERY GATE MUST BE OBSERVED RED AT LEAST ONCE, AND THE SABOTAGE AND ITS
OBSERVED RESULT ARE RECORDED.** A gate that has never been seen red is not
evidence that it runs — measured across this ladder, fourteen declared gates
once sat idle behind exactly that assumption.

**And the general form this ladder has already earned, which every gate above
must be held to:**

> **A CHECK THAT READS A TOKEN PRESENT IN BOTH THE COMPLIANT AND THE VIOLATING
> CASE IS MEASURING VOCABULARY, NOT CONTENT.**

Three of rung 03's gates passed their first sabotage for exactly that reason —
one asserted a substring that its own docstring supplied. **The gates most
exposed to it here are `CFT-G13`** (a resolver docstring saying it *refuses* is
not the resolver refusing, and a refusal type merely *imported* is not a refusal
*raised* — the gate must drive a real resource read and a real tool ask),
**`CFT-G10`** (an import of a Postgres driver is not the attribute leg reading
Postgres, and a **fixture** that opened both stores is not **the assembly**
opening them) and **`CFT-G16`** (the word *class* appears in both a
class-conditioned projection and a role map keyed by class name).

`[TBC — this build]` — the sabotage applied to each of the seventeen (2026-09-03;
previously ~~sixteen~~) and the observed result.

### G.3 Acceptance criteria — each phrased so it can fail

Beyond the seventeen gates (2026-09-03; previously ~~sixteen~~), the build must
additionally prove:

1. **The six predicate counts are re-derived AT GATE TIME** from `fibo-v2` and
   report `owns` **636**, `isDirectlyConsolidatedBy` **140**,
   `isUltimatelyConsolidatedBy` **140**, `hasGlobalUltimateParent` **103**,
   `hasDomesticUltimateParent` **36**, `controls` **3**. **A hard-coded
   constant, an imported fixture, or a figure copied from this document is a
   FAILURE**, not a pass.
2. **The collapse is visible**: 1,058 raw triples, 722 normalized edges, 336
   collapsed — all three reported, not just the third.
3. **748 nodes and 83 roots**, re-derived.
4. **Reversing any one predicate's direction changes the reported root count**,
   executed for all six, so a bare count cannot stand in for the arrow.
5. **181 of 748 carry `ex:lei`, of which 142 resolve in `ccf_v2.legal_entity`** —
   and the census names `legal_entity`, never `crosswalk`.
6. **The anchor is re-derived**: LEI, label and a 7-class chain.
7. **SMCI's 19 direct children are asserted AS A ROSTER**, 17 `Sub*` plus the
   two named non-`Sub` children — never as a count.
8. **22 subtree nodes at max depth 3**, with depths 1, 2 and 3 to the three
   cycle-1 members named individually.
9. **2 of 22 resolve; 20 of 22 resolve to no Postgres row.**
10. **The deepest tree anywhere is depth 6, which `PSC-0124` attains** — phrased
    so it asserts no uniqueness (§F.4 finding 7).
11. **Exactly two cycles over the whole family graph, both wholly inside
    `owns`**, with both ordered rosters and both closing edges asserted exactly.
12. **Exactly one external edge into any cycle in the whole graph**, named.
13. **All six cycle members carry no LEI**; cycle 1's three carry 7 classes and
    cycle 2's carry 5.

**Five negative controls, each asserting BOTH its specific wrong result AND its
failure**, so a control that stops discriminating is itself detected:

| Control | Must yield | And must FAIL |
|---|---|---|
| The anchor over `isDirectlyConsolidatedBy` alone | **2 nodes, depth 1, 0 cycles** — a real walk that finds something | no `ownership_cycle` finding |
| Each of the five acyclic predicates alone | **0 cycles each** (`controls` 3 edges, `isDirectlyConsolidatedBy` 140, `isUltimatelyConsolidatedBy` 140, `hasGlobalUltimateParent` 103, `hasDomesticUltimateParent` 36); `owns` alone → **2** | a detector that fires on everything is caught |
| The detector over the **raw 1,058 triples** | **130** cycles, not 2 | an un-normalized graph cannot look green |
| `hasGlobalUltimateParent` read subject→object | **59** roots, not 83 | an inverted arrow is caught by something other than a count |
| `len(findings) > 0` against a **wrong three-member roster** | passes the weak assertion | **roster-blindness is itself detected** |

**Open decisions blocking build: NONE.** §F.2 row 20 — **Conflicts 1, 2 and 3 of
§F.4** — was the only blocking row, and all three were **RULED at Gate 1 on
2026-08-31 (Dave, `D-IMPL-225`)**. No other row blocks.

### G.4 Reproducibility — the claim, in exactly these words

**The product reproduces byte-identical against a quiescent ledger for that run.**

That sentence is the whole of the claim, and it is stated on one line here
deliberately: a claim a checker has to reassemble across a line break is a claim
a checker will silently fail to find. **No stronger claim appears anywhere
in this document, and none may appear in the README, the documentation page,
any artifact or any test name.**

**The qualifier "for that run" is load-bearing, and it is load-bearing because
it was measured.** `ledger_t` moved **4,560 → 5,112 between two sittings six
days apart** — 552 transactions. **Quiescence is a property of a run and never
of the database.** A claim that dropped the qualifier would be asserting
something about the store that the store does not offer.

**Three things this document therefore does NOT claim:**

1. **No claim that the ledger transaction number anchors a replay.** The
   estate survey once asserted the ledger `t` was *"the exact replay anchor for
   `graph_snapshot_at`"*; that was **STRUCK** on 2026-08-31 (`D-03`). There is
   no such claim here at any value of `t`, `4560` included.
2. **No claim that `t` implements `as_of`.** `D-IMPL-88` stands. Transaction
   time and CCF valid time are different axes and are not collapsed (§B.4.3).
3. **No claim that the read is snapshot-bounded.** The adapter **floors** and
   does not pin (`D-26`, §F.4 finding 1), and §D.5's replay test is written to
   reach a failing step 4 that demonstrates exactly that.

**What IS claimed, and what backs it.** Against a ledger nothing is writing to
during the run, the same question returns the same bytes: the assembly is
deterministic (Mode 1, no model), the normalization is set-valued and
order-independent, the cycle rosters are canonicalized by rotation (§C.4 trap
5), and the payload hash excludes `assembled_at`. **The fixture pair committed
for CI reproduces all 32 measured figures across two independent seedings, under
a comparison proven able to disagree by two planted single-edge defects that
moved 14 and 9 figures respectively while leaving the rest exactly right.**

### G.5 Catalog contribution

**What this rung proves that rungs 00 to 03 could not:**

- **Two systems of record in one assembly**, each authoritative for its own
  thing, with a gate that turns RED if either starts answering the other's
  question. Rung 03 proves the negative (*no store but one is opened*); this
  rung proves the positive.
- **A graph as a payload.** The first product whose answer is nodes and edges
  rather than rows, and the first whose correctness depends on **the direction
  of an arrow** — a property no count can check, and one this estate has already
  lost once for seven waves.
- **A finding that is orthogonal to the payload.** A cycle is a set plus a
  closing edge, returned beside the tree and never flattened onto it.
- **Ontology as mechanism rather than as documentation**, in three places at
  once: served in the payload, driving the projection, and validating the
  assembly.
- **The ladder's first MCP door**, and the first demonstration that one
  standalone assembler serves two callers — proven by the two callers sharing
  the module, not asserted. The door **serves through the tool only**; the
  product resource is registered and **refuses** (`D-IMPL-225` amendment 1),
  and the gap that leaves is recorded as `D-34`.
- **The first `cp-*` rung to consume through the client seam at all.** Rungs 00
  to 03 never import `ProductClient`; this one does, through the documented
  direct-adapter constructor, over a binding that **stays single-store** while
  the assembly opens two.
- **A partial capability shipped as a partial.** Cycle enumeration is not in the
  store, so it runs application-side and the recipe **says so with a `null`**
  rather than borrowing a category to look complete.

**What it deliberately does NOT prove, so a reader does not read a tier boundary
as an oversight:**

- **Not temporal.** `as_of` is refused; valid time is at source and unfetched.
  Tier 3's subject, and its flagship is `covenant-in-force-as-of`.
- **Not federated.** A2A is a later example, ruled explicitly.
- **Not materiality-filtered.** No ownership percentage in the source and no
  intent-bound threshold in the estate — §B.4.2.
- **Not a type-constrained walk.** Ontology role 1 is struck, for two measured
  reasons, and `CFT-G17` is withdrawn rather than replaced by something that
  would go green having proven nothing.
- **Not a full corporate family.** Exhibit 21 is filer-truncated by rule
  (§F.1), and the payload must never be described to a consumer as complete.
- **Not a transport swap.** cp-04 supplies its adapter **in code**, so it does
  **NOT** re-prove the `hw1-*` seam's *"same `consume.py`, different
  `CCF_BINDING`, identical `Result`"*. That property belongs to Phases 17, 18
  and 20 and to the `hw1-*` trees. **cp-04's portability claim is `D-21`'s** —
  one standalone assembler, two thin callers. **Both are legitimate; they are
  not the same claim**, and nothing this rung ships may imply otherwise. §F.4
  Conflict 2.
- **Not a tool-only MCP door in the literal sense.** The product resource is
  **registered and enumerable**; it refuses rather than being absent, because
  `build_egress_server` cannot withhold it without `runtime/` work. `D-34`,
  §F.4 finding 9 — recorded, not closed.

---

## Gate 1 — status

**SNAPSHOT — the state as of 2026-08-31, when Gate 1 was ruled.**

**GATE 1 IS RULED: APPROVED WITH THREE AMENDMENTS, ON THE AMENDED TEXT.**
**Approver: Dave. Date: 2026-08-31. Decision: `D-IMPL-225`.**

**The amendments landed BEFORE this verdict was recorded and BEFORE Wave 3**, on
the `D-IMPL-222` precedent Dave invoked by name: criteria **34, 37, 43, 47 and
49** were amended or clarified in `.planning/ROADMAP.md`, and `D-IMPL-225` was
written to `docs/DECISIONS.md`, **and only then** was this document brought onto
the amended text and the `Gate 1 status` row flipped. Two of the three
amendments **changed a locked criterion rather than bending the product to it**;
one clarified a criterion's subject.

- **Amendment 1 — the MCP door.** Criterion 37's *"no resource is exposed"* was
  **FALSE against this tree** and was amended rather than engineered around.
  `build_egress_server` **cannot be tool-only**. What ships is a **REGISTERED
  RESOURCE THAT REFUSES**, and `CFT-G13` asserts all three parts together;
  sabotage is **the resolver returning a payload**. `runtime/` is not touched.
  The residual gap is **`D-34`** — §F.4 finding 9, **RECORDED, not closed**, and
  criterion 49 is extended to it. §F.4 Conflict 1.
- **Amendment 2 — the consume path.** `ProductClient(product_id=…, adapter=…)`,
  the documented constructor at `src/ccf/client/client.py::ProductClient.__init__`. **The binding
  stays SINGLE-STORE and is not widened**; the two-store assembly happens
  **inside the product**. Criterion 34 is clarified: **`CFT-G10` asserts THE
  ASSEMBLY opened both stores, not that the RUNNER did.** Nothing under `src/`
  changes. §F.4 Conflict 2.
- **Amendment 3 — the gates schema.**
  `docs/schemas/product-gates/cp.product-gates.json`, **closed keys**, kept
  **off** the top-level glob `tools/dump_schemas.py` walks and `unlink()`s.
  **Enforcement is Phase 24.5's checker, not this phase.** §F.4 Conflict 3.

- **Nothing is implemented at this stamp.** No code, no artifacts, no tests. The
  example directory contains this document and nothing else, per
  `example_delivery.md` §1: **"No implementation code before Gate 1."** Dave's
  instruction was explicit — *the spec stays the only file under cp-04 until
  Gate 1 is green on the amended text* — and it held through the amendment pass.
- **Every figure was measured** on 2026-08-31 against `fibo-v2` at a `ledger_t`
  read **once** at the start of the pass — **`ledger_t = 5112`** — and against
  PostgreSQL schema `ccf_v2`, both read-only. Every §C and §E figure traces to a
  section of `24.4-MEASUREMENT.md`, which carries the query and the **population**
  behind each.
- **Thirteen `[TBC — this build]` rows clear at Gate 2.** Six belong to the
  vault, identity-and-access and `ccf_dataprep`, and are named rather than
  invented.
- **Two rulings carried in are recorded rather than re-litigated.**
  **`D-IMPL-223`** — four scheduling classes as the scheduler, the Standard's
  eight names as spec vocabulary, `OperatorCategory` closed for v0 and not
  opened here (§D.2.2, §D.2.3). **`D-IMPL-224`** — product gates are a declared
  artifact plus CI coverage, with no `ProductGate` Protocol and no serve path
  (§D.7).
- **One scope reduction made before this document was written is recorded, not
  reopened.** Ontology **role 1 is STRUCK** and **`CFT-G17` is WITHDRAWN**
  (Dave, 2026-08-31, `853ccc9`), for two independently measured reasons — the
  estate gap `D-32` and the mechanism gap `D-33`. **The roster is sixteen
  gates and three ontology roles**, and neither is restated under another name
  anywhere in this document.
- **Two divergences from the vault article are named rather than smoothed.**
  The depth range (article `1–5`; this specification `1–6` on Dave's measured
  ceiling — §B.4.1), and the lineage list (article
  `[Resolve, Policy, Traversal, Enrich]`; this specification's
  `operators_invoked` carries **two** entries, with `Enrich` declared as **spec
  vocabulary against a non-operator mechanism** — §D.2.3). A third — the three
  request parameters this rung does not carry — is at §B.4.2.
- **SEVEN SDK gaps are RECORDED and NONE is closed.** `D-26` through `D-31` at
  §F.4 findings 1 to 6, and **`D-34`** at §F.4 finding 9, under `D-04` of
  `24-CONTEXT.md`. **No file under `src/` or `runtime/` is modified by this
  phase.**
- **A consistency finding with the client work is recorded rather than left to
  be misread.** cp-04 is the **first `cp-*` rung to consume through the client
  seam at all**, and it proves **`D-21`'s** property — one standalone assembler,
  two thin callers — **not** the `hw1-*` trees' *"same `consume.py`, different
  `CCF_BINDING`, identical `Result`"*. §F.4 Conflict 2, §G.5.

**THE THREE CONFLICTS BETWEEN THE LOCKED SUCCESS CRITERIA AND THE SHIPPED SDK
WERE THE GATE 1 DECISION ITEMS, AND ALL THREE ARE NOW RULED.** Each was measured
against the tree and submitted with a proposed reading and an alternative, and
**none was resolved by this document on Dave's behalf.** They are at §F.4 as
**Conflict 1** (criterion 37 against `build_egress_server`'s unconditional
resource registration — **criterion AMENDED**), **Conflict 2** (criterion 47
against the in-process transport's `binding.yaml` path — **proposed reading
adopted, criterion 34 CLARIFIED**), and **Conflict 3** (criterion 43 against the
`docs/schemas/` orphan check — **proposed reading adopted**). Each carries
Dave's ruling beside it, quoted rather than paraphrased.

**Gate 1 has cleared. Plans `24.4-03` through `24.4-14` build to the ruled
readings above.**

---

*`CP-SPEC-004` · authored 2026-08-31 · Phase 24.4 plan `24.4-02` · **Gate 1
APPROVED 2026-08-31 (Dave, `D-IMPL-225`) with three amendments, on the amended
text.***
