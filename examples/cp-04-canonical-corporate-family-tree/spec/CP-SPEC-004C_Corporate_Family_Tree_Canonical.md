---
product: reference.corporate-family.v2
standard: v0-3
owner: vault
sdk_spec: cp-04-canonical
tier: 2
cost_band: "×1–2 at the declared default depth"
assembly_mode: 1
capability_classes: [graph-traversal, relational, in-memory]
prerequisites: [counterparty-reference-snapshot]
topic: context-products
title: Corporate Family Tree (canonical) — Context Product Specification
generated: '2026-09-10'
---

# Corporate Family Tree (canonical) — Context Product Specification

**`CP-SPEC-004C` · the canonical rung-4 tree · Tier 2 · `reference.corporate-family` @ `2.0.0`**
**Fluree `fibo-v2` for family edges, the FIBO class chain and labels · PostgreSQL `ccf_v2` for GLEIF Level 1 attributes**

> Which legal entities belong to one corporate family, what each of them *is*,
> and where the answer is thin — **written the way an adopter should write a
> product on the SDK as it ships today.**

## 0 · What this document is

**This specification is RETROSPECTIVE, and that is disclosed rather than
glossed.** `D-IMPL-327` (Dave, 2026-09-10) ordered it because the standing rule
is *"every example has its own specification, every gate traces to that
specification, every declared gate is exercised by a real test"* — and this tree
had no specification at all. The implementation existed first, under
`D-IMPL-313` and `D-IMPL-319`. Every gate in §G.1 therefore describes a test
that already runs, and none of them was written to this document.

**It cites `CP-SPEC-004` nowhere, deliberately** (`D-IMPL-327`, Dave: *"do not
cite frozen cp-04"*). The frozen specimen's specification governs the frozen
specimen. A successor whose acceptance authority lived in its predecessor's
document would be governed by a document nobody may edit, and the two trees
answer the same question differently on purpose.

### 0.1 What this tree teaches, and what it does not

It teaches **the canonical producer shape**. Six things, and they are the whole
subject:

1. **boot / acquire / govern** as three regions, with the SDK owning the third.
2. **Bounded acquisition** — the walk is bounded at the depth governance
   resolved, never read wide and clipped afterwards.
3. **`max_depth` versus `depth_limit`** — the caller's request state and the
   backend's ceiling are two numbers, and collapsing them makes a product
   decision look like a capability limit.
4. **Thin edges first, attributed nodes last** — an ingestion order that is a
   contract, because the last claim at a URI wins and does not merge.
5. **The store pin is execution provenance, not product identity.**
6. **A canonical producer shape** a structural classifier can read off the code
   rather than off a roster.

It does **not** re-derive the corporate-family domain. Ownership semantics,
the FIBO class chain and the GLEIF attribute set are the domain this tree
borrows to have something real to walk; they are not what it exists to say.

### 0.2 Placeholder discipline

No `[TBC]` in this document. Every figure below was measured against the curated
`.76` estate and is reproducible by the run in §D.1.

### 0.3 Front matter

`reference.corporate-family` at class lane **`2.0.0`**, and the major lane is
doing real work: the frozen specimen serves `1.x` and this tree serves `2.x`.
Two lanes because the payload shape genuinely differs, not as a version bump for
its own sake.

### 0.4 The four-question test

- **Is the answer assembled rather than stored?** Yes. Neither store holds it:
  family edges and class chains are in the graph leg, GLEIF attributes in the
  relational leg, and **no schema author has joined them**.
- **Does more than one consumer need it?** Yes — KYC, credit aggregation and
  exposure rollup all need the same family, and rung 5 consumes exactly this.
- **Does it carry a governed freshness claim?** Yes. `D_c` is computed from what
  the answer resolved, not from what the estate holds.
- **Would a `SELECT` do?** No. The family is a traversal and the attribute leg
  is keyed by LEI in another store.

---

## A · Decision frame

**The decision.** *Which legal entities does this anchor's corporate family
contain, what is each one, and how much of that answer is actually resolved?*

**The consumer.** A credit or KYC analyst, or — more often — another Context
Product. Rung 5's exposure rollup cannot compute family-level exposure without
this answer and cannot be correct with a partial one.

### A.1 Counterfactual — `context-starved`

Without it, a consumer keys exposure on the borrower and misses the family.
`CP-SPEC-005` measured that failure at nearly seventy times understatement. The
counterfactual is not that the answer is *slower* to obtain; it is that a
borrower-keyed answer looks complete and is wrong.

### A.2 The second thing this rung surfaces: an answer that is honestly thin

At the declared default depth this family is **49 entities and 119 typed
edges**, of which **29 resolve** in the attribute leg. `D_c = 0.408163`, signal
`ok`.

**Most of this family's nodes have no row in the relational leg at all.** That
is not a defect to repair — it is the measured fact the product's Context Debt
is computed from, and serving it is the product's job.

### A.3 Cycles are findings, not errors

Mutual and circular ownership is ordinary in real corporate structures; this
family carries **22 mutual pairs**. A product that raised on one could not
describe the estates it exists to describe. Each circuit is returned with an
ordered roster and its **closing edge**, so a reader sees the loop rather than
being told one exists.

---

## B · Contract

### B.1 The nine elements

| # | Element | Value |
|---|---|---|
| 1 | **Name** | `reference.corporate-family` |
| 2 | **Version** | `2.0.0` — its own major lane |
| 3 | **Subject** | one anchor LEI |
| 4 | **Payload** | the family roster, each node's FIBO class chain and GLEIF attributes where resolved, the typed edges, and the ownership circuits as findings |
| 5 | **Lineage** | both legs, with the graph store's transaction-time head as execution provenance |
| 6 | **Policy** | the admitted family set, stated by the caller and verified |
| 7 | **Debt** | `D_c` from resolved ÷ served, computed on the answer |
| 8 | **TTL** | anchored on the latest assertion time among the family, never on request time |
| 9 | **Determinism** | class 1 — pure algorithmic, no model call |

### B.2 Request parameter surface

| Parameter | Type | Moves | Default | Expected effect |
|---|---|---|---|---|
| `lei` | string, **required** | anchor | — | unresolvable ⇒ refusal, never an empty payload |
| `families` | array, **required** | `P` envelope | — | the admitted set the policy operator reads |
| `max_depth` | int | `R` bound | **3** | absent takes the declared default; above the backend's capability ⇒ refusal, authority `technical` |
| `debt_tolerance` | number | fulfillment | class default | the caller's ceiling on assessed Debt |
| `as_of` | string | — | — | **declared and inert** — refused, never honored |

**`lei` and `families` are both required and the second is not derived from the
first.** A binding supplies a value and never converts one: a caller entitled to
two families asks about both without a second code path, and a caller entitled
to none is refused rather than silently scoped to its own anchor.

**An empty family is a claim about the world; an unresolvable anchor is a claim
about the request.** They are different answers and the product gives different
ones.

---

## C · Data catalog

| Element | Leg | Source |
|---|---|---|
| family edges, six predicates | graph | Fluree `fibo-v2` |
| FIBO class chain, labels, LEIs | graph | Fluree `fibo-v2` |
| GLEIF Level 1 attributes | relational | PostgreSQL `ccf_v2` |

The predicate IRIs, the table and its columns live in
`artifacts/source-vocabulary.yaml` — **the sources' own names, in the sources'
own namespace**, never in code.

### C.1 The two traps, and both are load-bearing

**Trap 1 — thin edges first, attributed nodes last.** Two kinds of envelope
reach L2: **edge** envelopes carrying two endpoint references and a predicate
and *no* attributes, and **node** envelopes carrying one node's attributes. The
edges must be ingested **first**. The last claim at a URI wins and does not
merge, so an edge envelope arriving after a node envelope supersedes it, and the
node is then served with no name, no LEI and no class chain — **and nothing
raises.** Chronological intuition says edges are learned later and should be
ingested later; that intuition is exactly what erases the attributes.
`deployment.ingest` asserts the outcome, so reversing the two lines fails loudly
rather than silently.

**Trap 2 — two depths, two authorities.** `max_depth` is the caller's request
state: it folds through the class default, the declared domain and the graph
leg's technical capability, and the effective value that survives is what
**acquisition** walks at. `depth_limit` on the traversal operator is the
**backend's ceiling** — what a request above it is refused against, with
authority `technical`. One number serving as both would make a product decision
look like a capability limit.

---

## D · Assembly recipe

### D.1 Client call

```
make example-cp-04-canonical
make example-cp-04-canonical MAX_DEPTH=1
```

Read-only on both legs: SPARQL `SELECT`s and one parameterised SQL `SELECT`.
The fabric's own graph and the replay record are written to a temporary
directory and discarded when the run exits. **`MAX_DEPTH` omitted asks the
question without the parameter**, so the class default resolves — a different
act from passing the default's value, and the run prints which happened.

### D.2 The three regions

| region | what it owns |
|---|---|
| **boot** | one `load_config_and_boot` over `ccf_config.yaml`; connection values arrive from the caller, never from the config, which names the backend as a KIND only |
| **acquire** | the two source legs, at the bound governance resolved, then L1 → L2 through the single write handle |
| **govern** | the door, both operators over L3, Π, the L6 gates, the five-dimension record and the delivery — **one object the SDK owns** |

`acquisition.py` **imports no `ccf` at all**, which is what makes the source
legs replaceable without touching the fabric.

### D.3 Validation gates

The SDK's three universal L6 gates apply unchanged: the empty-operator guard,
lineage strict equality, and TTL bounds. This product declares **no** fourth
gate of its own; its obligations are the thirteen in §G.1, which are tests
rather than serve-time gates (`D-IMPL-224`).

### D.4 Determinism and replay

Class 1. Two serves of one question at one instant reach one content address.
**The graph store's transaction-time head is recorded as execution provenance
and is NOT part of product identity** (`D-IMPL-309`): where the evidence lives,
not whether it exists. Replay dimension 2 is a **superset** of product lineage
(`D-IMPL-310`) — replay may carry governed artifacts lineage does not.

---

## E · Volatility, debt and materialization

`D_c` is computed from **resolved ÷ served**, on the answer rather than on the
estate:

| you ask | you are served | `D_c` |
|---|---|---|
| `max_depth` absent | 49 entities, 119 edges, 29 resolved | **0.408163**, `ok` |
| `max_depth=1` | 36 entities, 35 edges, 16 resolved | **0.555556**, `ok` |
| `max_depth=99` | *refused* — `bound-exceeded`, authority `technical` | — |

**A debt that stayed the same whatever was served would be decorative.** It
moves because the walk is genuinely bounded at the depth governance resolved, so
what was assembled and what was served are the same set.

The product is assembled per request and never materialized. TTL is anchored on
the latest assertion time among the family.

---

## F · Source binding and readiness

Connection material — host, port, credentials — comes from the estate's own
environment. **The namespaces do not**: `.env` names the **v1** estate, and this
product reads **v2** (`fibo-v2`, `ccf_v2`). Deriving the namespaces from `.env`
points the run at v1, where the anchor resolves in Postgres and has no node in
the graph (CLAUDE.md §9).

`backends.yaml` carries variable **names** only — no host, port, path or
credential.

**Watermark reporting** (`CP06-F-01`): the curated estate is named without a
branch segment, and a bare ledger name must still resolve a real transaction-time
head. An unknown ledger reports *unreported* rather than a number, and no
watermark is ever invented from a listing.

---

## G · Operate and govern

### G.1 Product gates

The acceptance authority for every gate below is **this clause**
(`D-IMPL-326`). Each id is claimed by the executing test named in
`artifacts/gates.yaml`.

| Gate | Asserts |
|---|---|
| `CFC-G01` | depth changes the served roster and the debt **together** — `D_c` is about the answer, not the estate |
| `CFC-G02` | the scorer and the payload see **one** set — the walk is bounded, not clipped after the fact |
| `CFC-G03` | a depth above the backend ceiling is refused, and refused with authority `technical` |
| `CFC-G04` | the class default resolves when the caller **omits** the depth — a different act from passing its value |
| `CFC-G05` | replay dimension 2 is a **superset** of product lineage |
| `CFC-G06` | the store pin is execution provenance and **not** product identity |
| `CFC-G07` | `shape_of` reads this tree as **canonical**, structurally rather than from a roster |
| `CFC-G08` | the plan factory takes its operators only from `required` |
| `CFC-G09` | the frozen specimen is **untouched** — zero files changed by this tree's work |
| `CFC-G10` | **no specimen identity is reused** — this tree's determination is provably its own |
| `CFC-G11` | a bare ledger name resolves a real watermark |
| `CFC-G12` | an unknown ledger reports *unreported* rather than a number |
| `CFC-G13` | the watermark is never invented from the listing |

**All directional or structural. No estate figure is pinned in a gate** — the
counts in §A.2 and §E are measurements a reader can reproduce, not assertions a
test holds, because a test pinning 49 would go red the next time the fixture
grows.

### G.2 Acceptance criteria

1. The family is walked at the depth governance resolved, and the served set is
   the scored set.
2. `D_c` moves with the answer and is computed from resolved ÷ served.
3. The two depth authorities stay distinct, and a request above the backend
   ceiling is refused by name.
4. Ownership circuits are served as findings with their closing edge.
5. The producer shape reads as canonical, and the frozen specimen is unchanged.
