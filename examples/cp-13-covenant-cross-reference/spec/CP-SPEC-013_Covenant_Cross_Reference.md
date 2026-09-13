---
product: credit-risk.covenant-cross-reference.v1
standard: v0-3
sdk_spec: cp-13
tier: 4
cost_band: "×3–5 materialized"
capability_classes: [relational, bitemporal-ledger, graph-traversal, document-passage, vector-index]
prerequisites: [covenant-in-force-as-of, facility-terms-snapshot]
build_order: 13
lifecycle: draft
accountable_owner: credit-risk-product-engineering
review_cadence: at every Control Plane change to the corpus-entitlement rules or the
  embedding model version; and no less than annually
topic: context-products
title: Covenant Cross-Reference — Context Product Specification
generated: '2026-09-13'
---

# Covenant Cross-Reference — Context Product Specification

**`CP-SPEC-013` · Tier 4 · `credit-risk.covenant-cross-reference.v1`**
**MongoDB for the text and the spans · Fluree for the typed relationships and the anchors · PostgreSQL for the entitlement rules**

> **What does this covenant actually require?**
>
> Not the threshold — the **definition**. Which EBITDA, with which addbacks, over
> which measurement period, per which section of which agreement. And every
> claim has to point at the text that says so.

## 0 · What this document is

A build specification for the engineer who will assemble this Context Product
from the markets and credit data estate. **Every figure below was measured
against the live estate on 2026-09-13 before this document was written**, and
the query that produced it is reproducible.

### 0.1 The governing question

> **Can a Context Product cite a passage it has actually checked — and refuse to
> cite one it cannot?**

This is the first rung where the evidence is **text**, and the first where a
claim can be wrong in a way that looks completely right. Measured on this
estate, **49 of the definition nodes carry a span that is correct, quotable, and
impossible to audit**: the offsets land on exactly the right words, and there is
no recorded hash and no named passage to check them against. Emitting that text
would feel safe. It would be an *asserted* citation rather than a *checked* one,
and the difference is the whole tier.

> **AMENDED 2026-09-13 (`CP13-F-01`).** This section previously led with a
> different number — 79 candidate citations of which 36 were wrong. That defect
> was real when measured, was **repaired at source by the estate owner** the
> same day, and **cannot be replayed**: the source ledger's `t` parameter is
> accepted and ignored on this instance, returning current state at every value.
> The old state is preserved as history at `CP13-F-01`, not as an executable
> trap. §C.3 TRAP 1 is now the span-unverifiable case.

### 0.2 Placeholder discipline

No `[TBC]` except the p95 budgets, which cannot exist before code does and close
at Gate 2.

### 0.3 Reads only — no write path anywhere in this product

Three stores are read. The ledger is append-only, so a write is permanent;
MongoDB `fibo_v2` is `ccf_dataprep`'s and is not ours to write. Nothing in this
product's assembly, its examples or its tests writes to any of them
(CLAUDE.md §9 — the curated estate is evidence).

### 0.4 No SDK gap

**Every capability this rung needs already exists**, and that is worth checking
rather than assuming at the tier where documents enter:

- **`ccf.contracts.claims.PassageAnchor`** — `{kind, locator}`, whitepaper
  §7.10.3 / `INV-CH7-19`. The SDK fixes the anchoring *obligation* and
  deliberately not the anchor schema.
- **`LineageEntry`** accumulates by set-union with per-source passage anchors
  preserved (`INV-CH7-17`).
- **`similarity.corpus-select`** with the `SimilarityIndexProtocol` seam
  (`D-IMPL-03`), and `read_intent()` returning `None` — Similarity is never
  pushable.
- **Policy-before-Similarity is achieved by operator ORDER in the plan**, which
  the planner topologically resolves. It does not need — and does not have — an
  allowlist parameter on `SimilaritySelectParameters`.

**One deployment obligation follows from that last point and is not an SDK gap.**
The permitted-document set bounds a retrieval against **MongoDB**, which is
outside the graph view the operators range over. Nothing in the SDK can enforce
it, because nothing in the SDK issues that query. §D.4 and `CXR-G09` carry it.

---

## A · Decision frame

**The decision.** A credit officer testing compliance who needs the definition
behind the threshold, not the threshold.

**The trigger.** A covenant test falls due, or an amendment lands.

**Consuming principals.** Three, and they are measured rather than declared —
see §B.3. This is the first rung where the principal changes *which documents
exist*, not merely which fields are returned.

### A.1 Counterfactual — `confident fusion`

The article names it precisely: an LLM fuses two covenant definitions because
their chunked similarity is high, while passage-level provenance would have
shown them originating in different documents governing different facilities.

Measured, this estate is built for it: **18 leverage covenants across 18
different documents**, with thresholds spanning **2.5× to 4.0×**. As text they
are near-identical. They are not the same covenant, they do not share addbacks,
and a retrieval pipeline ranking by similarity has no structural reason to keep
them apart.

### A.2 And a second failure this estate makes visible, which the article does not name

**A citation can be correct and still be unauditable.** The article's validation
gate is *passage resolvability* — every anchor must resolve to a span whose
`sha256` matches. That gate assumes there **is** a recorded hash. Measured here,
on all **49** `CovenantDefinition` nodes there is not:

```
48 of 49 carry startOffset, endOffset and documentId
 0 of 49 carry passageSha256
 0 of 49 carry evidencedBy
 0 passages in MongoDB match — or even contain — the span
```

The spans land on exactly the right text:

```
"Consolidated Fixed Charge Coverage Ratio" means, for any Measurement …
"Consolidated Leverage Ratio": as at the last day of any period, the r…
```

**That is what makes it the hard case.** A wrong citation is caught by a hash.
An unauditable one is caught only by a product that refuses to emit what it
cannot check — and refuses while the text on screen is visibly correct. See
TRAP 1.

---

## B · Contract

### B.1 The nine elements

| Element | Value |
|---|---|
| **Schema** | `credit-risk.covenant-cross-reference` — entities: `Covenant`, `CovenantDefinition`, `DefinedTerm`, `MeasurementPeriod`, `SourceDocument`, `Passage`; relationships: `definedBy`, `measuredBy`, `crossReferences`, `evidencedBy`, `unresolvedTerm`; measures: the definition chain, and a checked citation per claim |
| **Freshness SLA** | Amendment-driven |
| **TTL** | 7 days · `ttl_anchor: from_decision` |
| **Policy binding** | Corpus-scope entitlement from `ccf_v2.corpus_entitlement`; **Policy operator precedes Similarity operator** |
| **Lineage** | `operators_invoked` · `policy_bundle_versions` · `graph_snapshot_at` — **exactly three fields** |
| **Semantic version** | `v1.0.0` |
| **Discovery** | `credit-risk.covenant-cross-reference.v1` |
| **Addressability** | `/context-products/credit-risk/covenant-cross-reference/{covenant-source-id}` |
| **Assembly mode** | 1 — pure algorithmic. No model in the path |

### B.1a TWO THINGS ARE CALLED `L` AND THEY ARE NOT THE SAME CONTRACT

The article says *"passage-level `L` per claim"*. That is **not**
`ProductLineage`, and conflating them would put a per-claim structure into a
three-field contract that has no room for it.

| | what it is | where it lives | shape |
|---|---|---|---|
| **`ProductLineage`** | the product's own lineage | `ContextProduct.lineage` | **exactly** `operators_invoked`, `policy_bundle_versions`, `graph_snapshot_at` |
| **`LineageEntry` / `PassageAnchor`** | the *graph claim's* provenance, accumulating by set-union | `EntityClaim.lineage`, and the payload's per-claim citation | `{kind, locator}` per source |

**The served payload carries the checked citation on each claim.** The product's
lineage stays three fields. `CXR-G02` asserts both halves.

### B.2 Request parameter surface

The four §6.3 axes are `ProductRequest` **fields** — `subject`, `intent`,
`freshness`, `asked_at`.

| Parameter | Type | Moves | Default |
|---|---|---|---|
| `covenant_sources` | list, required | the policy operator's admitted set | — |
| `intent` | **field** | selects the entitlement row | `compliance-test` |
| `asked_at` | **field** | **which text governs** | — |
| `resolve_depth` | int 1–3 | the definition-chain depth | 3 |
| `corpus_scope` | enum `filed` \| `filed-and-internal` | **the `P` envelope** | `filed` |
| `include_passages` | bool | payload shape | `true` |
| `debt_tolerance` | decimal | the caller's ceiling on `D_c` | — |

**`corpus_scope` is a policy parameter, not a convenience filter.** Widening it
changes which documents may be retrieved at all, and for a principal without the
entitlement the widened scope is **refused rather than silently narrowed**
(`CXR-G10`). Measured, that refusal is reachable: see §B.3.

### B.3 The entitlement gradient is measured, not declared

`ccf_v2.corpus_entitlement` — six rows, three principals, read in full:

```
control-room          filed-and-internal   public-filed
control-room          filed-and-internal   internal-confidential
control-room          filed-and-internal   internal-restricted
credit-officer        filed                public-filed
credit-officer        filed-and-internal   internal-confidential
relationship-manager  filed                public-filed
```

Three principals, three different permitted sets, and the gradient is real:

- **`control-room`** may reach all three classifications.
- **`credit-officer`** may widen to internal, but **never to
  `internal-restricted`** — and **4 of the 40 memoranda carry exactly that
  class**, so the boundary has something behind it.
- **`relationship-manager`** has **no `filed-and-internal` row at all**, so the
  widened scope is a refusal rather than a narrower answer.

**That last row is the one the gate rests on** (`CXR-G10`): a principal with no
entitlement for the scope they asked for must be refused, because silently
narrowing to `filed` answers a question they did not ask and hides that the
document class exists.

### B.4 Temporal semantics, enumerated

**Seven clocks, and the product keeps them apart.**

| Clock | Where it lives | Used for |
|---|---|---|
| **Agreement date** | `document.agreement_date` | when the parties signed |
| **Governs-from** | `document.governs_from` | **which text is in force — the `as_of` axis** |
| **Filed date** | `document.filed_date`, 90 distinct | when it reached EDGAR |
| **Memorandum authored** | `memorandum.authored_date`, 40 distinct | internal-corpus recency |
| **Fabric-learning time** | `document.retrieved_at` — 2026-08-22, 2026-08-23, 2026-09-12 | provenance only. **Never a governing basis** |
| **Ledger `t`** | Fluree | `graph_snapshot_at` |
| **`as_of`** | `ProductRequest.asked_at`, from the caller | bounds every read |

**`governs_from` is the axis and `filed_date` is not.** An amendment is filed
days or weeks after it starts governing — measured, `529900E95812SYWMCE44`'s
amendment governs from **2026-06-29** while its base governs from **2026-06-09**
— and a product that reconstructed on the filing date would serve the old text
for the gap between them.

### B.5 Context Debt and freshness

| Class | `λ_c` | `decay_basis` | Notes |
|---|---|---|---|
| `cxr_document` | **no decay** (`supersede-only`) | — | Filed text is immutable once filed; supersession is by amendment, never revision |
| `cxr_definition` | 365 days | `valid-from` | Re-extracted on amendment |
| `cxr_memorandum` | 180 days | `valid-from` | |

**Filed text is the only genuinely immutable source in the catalog**, and
`supersede-only` is the honest statement for it. The illustrative-calibration
question that dominated rung 12 does not arise the same way here, because the
dominant class does not decay at all — but the two decaying classes are
calibration values and **`CP13-F-12` records them as such** with the measurement
that chose them at Gate 2.

**Completeness is where this product's `D_c` actually lives.** A definition-chain
node whose citation cannot be checked is a completeness shortfall the consumer
must see, not a gap to paper over. Measured, that is not a hypothetical: §C.3
TRAP 2.

---

## C · Data catalog

### C.1 What the estate holds, measured 2026-09-13

```
MongoDB  fibo_v2
  document              249      of which 36 carry agreement metadata
                                 68 are `SEC EDGAR EX-10 exhibit`, 36 of those with an agreement_id
                                 classification: 160 public-filed · 40 public · 49 ABSENT
  passage            37,865      start_offset 37,865 · end_offset 37,865
                                 sha256 37,317   <- 548 carry NO sha256
                                 embedding 37,781 (text-embedding-3-small, 1536-dim)
                                 alignment: window-split 20,572 · structure 8,545 · definition 5,405
                                            window 2,099 · window-head 614 · heading 82 · none 548
  memorandum             40      36 internal-confidential · 4 internal-restricted
                                 residency US 28 · UK 7 · EU 5
                                 embedding 22 of 40      <- 18 unreachable by similarity
  research_note          42      kyc_document 32      trigger_anchor 10

Fluree  fibo-v2
  ex:Covenant           182      181 `COV-*` + 1 `COVDEF-*`
  ex:DefinedTerm        158      ex:CovenantDefinition 49      ex:MeasurementPeriod 11
  ex:PassageAnchor       44      the passage-evidence nodes, TYPED — the seed (TRAP 3)
  ex:startOffset        261 assertions / 255 subjects
  ex:endOffset           91 assertions /  85 subjects
  ex:declaredAt         170 / 170    158 of them on DefinedTerm — see TRAP 2
  ex:definedBy           28 / 28     ex:measuredBy 13 / 11
  ex:crossReferences    216 / 49     ex:unresolvedTerm 2 / 2     ex:covenantOf 182 / 182
  ex:evidencedBy         44 / 44     44 of 44 re-hash correctly
  ex:governedBy           0      <- the article's schema names it; it does not exist here

  the four-literal anchor join returns 44 rows over 44 subjects — no fan-out

PostgreSQL  ccf_v2
  corpus_entitlement      6 rows, 3 principals (§B.3)
```

### C.2 Provenance, and what is public

| Element | Provenance |
|---|---|
| Credit agreement and amendment text, 10-K/10-Q/8-K text | **public** — SEC EDGAR, `retrieved_at` recorded per document |
| Passage spans, offsets and sha256 | **derived** at ingestion from the public text |
| Passage embeddings | **derived** — `text-embedding-3-small`, 1536-dim |
| Definition-chain edges and passage anchors | **derived** — extracted at ingestion |
| Internal credit memoranda | **synthetic — internal** · all 40 rows |
| Classification and residency tags | **synthetic — internal** |
| Corpus-scope entitlement rules | **synthetic — internal** |

### C.3 The data traps

**Six, and all six were run during Gate-1 measurement.**

**TRAP 1 — A SPAN CAN BE CORRECT AND STILL BE UNAUDITABLE.** All **49**
`CovenantDefinition` nodes carry a real span and nothing to check it against:

```
48 of 49  startOffset, endOffset, documentId
 0 of 49  passageSha256
 0 of 49  evidencedBy
 0        passages matching or containing the span
```

The extracted text is exactly right — `"Consolidated Fixed Charge Coverage
Ratio" means, for any Measurement …` — which is precisely the danger. A product
that emitted it would be **asserting** the citation, and an asserted citation is
indistinguishable from a checked one in the payload.

**Binding:** the citation unit is the named passage reached through
`ex:evidencedBy`, and a node with a span but no recorded hash is classified
`span-unverifiable` and reported as Context Debt (`CXR-G07`, `CXR-G08`,
`CXR-G19`). The wrong mechanism is not a join — it is **emitting the extracted
text because it looks right**.

> **TRAP 1 WAS A DIFFERENT DEFECT UNTIL 2026-09-13, AND THE REPLACEMENT IS
> RECORDED RATHER THAN THE HISTORY BEING DELETED.** It was an anchor-identity
> collision: the node URI was `COVSRC-{accession}-{covenant_type[:8]}` and
> **omitted the document**, so six URIs each absorbed two covenants from two
> different credit agreements filed in the same submission — XPO's `ex10-1` and
> `ex10-2` both carry a leverage covenant, at different thresholds and different
> spans. A four-literal join fanned out to 79 rows of which 36 failed their own
> hash and 12 sliced to the empty string.
>
> **The causal story this specification first gave was wrong.** It said RDF
> could not pair the literals. The numbers were right and the explanation was
> not: the pairing was never the problem, the *identity* was, and reifying the
> anchor would have produced a node correctly carrying two anchors and still no
> way to know it was two covenants. The estate owner re-keyed on
> `(accession, document, covenant_type)` — **44 URIs for 44 covenants, and the
> collision had been silently overwriting one.**
>
> **It cannot be replayed.** The source ledger's `t` parameter is accepted and
> ignored on this instance, returning current state at every value tried,
> including values well before the remediation. `FlureeGraphReader.query_pinned`
> pins CCF's own L3 and not a source ledger. So the old state is history, and
> this specification does not claim otherwise. `CP13-F-01`, `FIXED-upstream`.

**TRAP 2 — EVERY `DefinedTerm` IS A POINT ANCHOR, SO THE CHAIN'S LAST HOP CAN
NEVER BE EVIDENCED.** Measured: `ex:endOffset` is present on **0 of 158**
`DefinedTerm` nodes, while `ex:CovenantDefinition` carries both offsets on **48
of 49**. 170 subjects overall carry a start with no end — 158 `DefinedTerm`, 11
`MeasurementPeriod`, 1 `Covenant` — and **0 carry an end with no start**, which
rules out truncation.

`ex:startOffset` is doing two jobs under one name: a true span start on
`CovenantDefinition`, and a **point anchor** everywhere else. A point anchor
cannot check a citation — you cannot extract the quoted text from it.

**`ex:declaredAt` NOW EXISTS, AND IT DISTINGUISHES THE POINT ANCHOR WITHOUT
REPAIRING IT.** Measured 2026-09-13: **170 assertions over 170 subjects, 158 of
them on `DefinedTerm`** — appended alongside `startOffset` rather than narrowing
it, so a consumer reads *"this is intentionally a point"* off the graph instead
of inferring it from a missing end. **It does not make the anchor quotable and
it does not make it evidenced.** `endOffset` is still absent on all 158.

**Binding:** a depth-3 chain terminates in a node that is *located*, now
*explicitly declared a point*, and still not *quotable* — reported as **Context
Debt** rather than as a citation (`CXR-G08`, `CXR-G16`, `CXR-G20`).

**TRAP 3 — THE DEFINITION CHAIN DOES NOT HANG OFF `ex:Covenant`.** The obvious,
typed, correct-looking seed finds almost nothing:

```
seed on ex:Covenant (182 nodes):       depth 1 -> 2      depth 3 -> 1
seed on ex:PassageAnchor (44 nodes):   depth 1 -> 26     depth 3 -> 26
```

`definedBy` is carried by **26 `ex:PassageAnchor` nodes**, 1 `COVDEF-*` and 1
`COV-*`. The type whose *name* matches the question reaches almost nothing; the
type that carries the *evidence* reaches everything.

> **Amended 2026-09-13.** These nodes were **untyped** when this rung was
> specified, and the original binding read *"seed on the untyped evidence
> nodes"*. The estate owner typed them `ex:PassageAnchor` — deliberately not
> `ex:Covenant`, because an evidence node answering a covenant query would make
> every *"covenants in force"* traversal collect 44 anchors. **The divergence is
> unchanged at 26 against 1**; only the seed's spelling moved, and it is now
> selectable by class rather than by a `FILTER NOT EXISTS`.

**Binding:** the product seeds on `ex:PassageAnchor` and **declares** that it
does, rather than on the type whose name matches the question (`CXR-G12`,
`CXR-G21`).

**TRAP 4 — `governs_from` IS THE AXIS AND THE FILING DATE IS NOT.** 7 borrowers
carry both a base and an amendment, but **only 4 of the 7 have a `governs_from`
that actually separates them** — for the other 3 the amendment and the base
begin governing on the identical date, and both readings coincide. **Binding:**
any `as_of` gate must be asserted on one of the 4, never on one of the 3, or it
proves nothing (`CXR-G13`).

**TRAP 5 — POST-FILTERING SIMILARITY IS THE LEAK, NOT THE RESULT.** The
permitted-document set must bound the MongoDB retrieval *before* ranking. A
post-filter has already computed similarity against impermissible documents, and
in an MNPI context that computation is itself the leak. **Binding:** `CXR-G09`,
asserted where the two orders **differ** — a `relationship-manager` whose
permitted set excludes all 40 memoranda, against a `control-room` principal
whose set includes them.

**TRAP 6 — 548 PASSAGES CARRY NO `sha256`, AND 18 MEMORANDA CARRY NO EMBEDDING.**
The first cannot satisfy passage resolvability; the second cannot be reached by
similarity at all. Both are silent absences that present as "nothing relevant
found". **Binding:** a passage with no `sha256` is **not citable** and is
reported as such rather than cited unchecked (`CXR-G08`); the 18 unembedded
memoranda are declared in §E as an estate limitation rather than read as an
empty result.

---

## D · Assembly recipe

### D.1 Operator step table

| # | Operator | Store | What it does |
|---|---|---|---|
| 1 | `policy.principal-subgraph` | — | admits only the covenant sources the effective request names |
| 2 | `traversal.typed-neighborhood` | Fluree | the definition chain: `definedBy`, `crossReferences`, `measuredBy` |
| 3 | Π `CovenantCrossReferenceProjection` | in-memory | the chain, the checked citations, and the debt |

The deployment authors **no operator set**: the plan factory passes the
resolver's own `required` tuple through, as rungs 9–12 do.

### D.2 The computation

1. **Resolve the entitlement.** Read `corpus_entitlement` for the principal and
   the requested `corpus_scope`. **No row is a refusal**, not a narrowing.
2. **Compute the permitted document set** from the classifications the
   entitlement admits. This set bounds step 5 and is carried in the payload.
3. **Walk the definition chain** from the requested evidence nodes to
   `resolve_depth`, at the ledger point for `as_of`.
4. **Select the governing text** by `governs_from` at `as_of` — never by
   `filed_date`.
5. **Retrieve supporting passages within the permitted set only.**
6. **Check every citation.** Follow `ex:evidencedBy` to a named passage, read
   that passage's offsets and `sha256` from MongoDB, re-hash the span, and
   compare. **Never join the anchor predicates**, and never re-search for the
   text — a re-search can match a different occurrence and silently relocate the
   citation.
7. **Emit a citation only where the check passes.** A chain node that is located
   but not quotable, or whose passage carries no `sha256`, is reported as
   Context Debt with its reason.

**Step 6 is the honest half of step 3.** A chain that always produces a citation
produces a wrong one 36 times in 79.

### D.3 The scenarios

**Scenario 1 — the checked citation.** A single-anchored evidence node resolving
through `evidencedBy` to one passage whose re-hashed span matches. 31 of 37
nodes are this shape.

**Scenario 2 — the node with two anchors.** One of the 6. The product emits
**two** distinct citations, each checked against its own passage, and never the
cross-product. The naive join emits eight combinations of which two are right.

**Scenario 3 — the unquotable terminal.** A depth-3 chain ending at a
`DefinedTerm` with a start and no end. The chain is served; the citation is not;
`D_c` rises and the payload names the reason.

**Scenario 4 — the refused scope.** `relationship-manager` asking for
`filed-and-internal`. No entitlement row exists, so the request is refused rather
than narrowed to `filed`.

**Scenario 5 — the confident fusion, demonstrated.** Two leverage covenants from
different documents with different thresholds, textually near-identical. Ranked
by similarity alone they conflate; walked through the graph they never meet.

### D.4 Determinism and replay

**Determinism class: `deterministic`.** `payload_hash` is `sha256` over the
canonical bytes excluding `assembled_at`. Embeddings are read, never computed, so
no model call enters the path.

**The permitted-document set is part of the answer's identity**, not a filter
applied to it: two principals asking the same question receive different content
addresses, and `CXR-G09` asserts it.

### D.5 Validation gates

Six universal — empty-operator guard, lineage strict equality, TTL bounds, debt
gate, suppression silence, classification containment — then the product-specific
set at §F.1, **including passage resolvability**: every emitted citation must
re-hash to its recorded `sha256`, or it is not emitted.

**Error mapping.** `404` unknown covenant source · `403` not entitled for the
requested scope · `409` debt gate · `200` with notices otherwise. **A chain whose
citations cannot be checked is `200` with Context Debt** — not an empty payload
and not a silent omission.

---

## E · Findings

**Status vocabulary.** `D-IMPL-261`'s four — OPEN / FIXED-`<phase>` /
ESTATE-LIMITATION / NOT-A-GAP — plus one added at this rung on Dave's ruling of
2026-09-13:

> **`FIXED-upstream`** — the **estate or source owner repaired the underlying
> data** after the finding was raised. Materially different from
> `FIXED-gate-1/2`, which is a repair this repository made, and from
> `NOT-A-GAP`, which says there was nothing to repair. A `FIXED-upstream`
> finding **keeps its original measurement and its causal correction**: the
> defect was real, the product was specified against it, and the history is
> what explains why the specification reads as it does.

| id | finding | status |
|---|---|---|
| `CP13-F-01` | **An anchor-identity collision merged two covenants onto one URI, and it was repaired at source.** **As measured 2026-09-13 (original):** 6 of 37 evidence nodes carried two complete anchors; a four-literal join fanned out to **79** candidates of which **43** were valid and **36** false, **12** of those slicing to the empty string. **Causal correction:** this specification first attributed it to RDF being unable to pair the literals. That was wrong. The node URI was `COVSRC-{accession}-{covenant_type[:8]}` and **omitted the document**, so six URIs each absorbed two covenants from two different credit agreements in one filing. Reification — the repair this specification would have proposed — would have produced a node correctly carrying two anchors and still no way to know it was two covenants. **Repaired by the estate owner 2026-09-13** by re-keying on `(accession, document, covenant_type)`: **44 URIs for 44 covenants, join returns 44 rows, 44 of 44 hash, 0 inverted spans** — and the collision had been **silently overwriting one covenant**, so the repair recovered a record. **Not replayable:** the source ledger's `t` is accepted and ignored on this instance, and `query_pinned` pins CCF's own L3, not a source ledger. Preserved as history, not as an executable trap. | FIXED-upstream |
| `CP13-F-02` | **`ex:endOffset` is absent on all 158 `DefinedTerm` nodes.** 170 subjects carry a start with no end; 0 carry an end with no start. `ex:startOffset` is a span start on `CovenantDefinition` and a point anchor everywhere else. A point anchor cannot check a citation. TRAP 2. | ESTATE-LIMITATION |
| `CP13-F-03` | **`ex:declaredAt` was absent and is now present.** **As measured 2026-09-13 (original):** 0 assertions — the repair for `CP13-F-02` had been accepted upstream on 2026-09-12 and was not implemented, so the product was specified against the estate as it was. **Repaired by the estate owner the same day:** **170 assertions over 170 subjects, 158 on `DefinedTerm`**, appended alongside `startOffset` rather than narrowing it. **It distinguishes a point anchor; it does not repair one.** `endOffset` is still absent on all 158, so `CP13-F-02` stands unchanged and the terminal hop is still Context Debt (`CXR-G16`). | FIXED-upstream |
| `CP13-F-04` | **The definition chain does not hang off `ex:Covenant`.** Seeding on the 182 typed covenant nodes reaches depth 3 exactly **once**; seeding on the 37 untyped `COVSRC-*` evidence nodes reaches it **26** times. Fluree runs without reasoning. TRAP 3. | ESTATE-LIMITATION |
| `CP13-F-05` | **The upstream report of "43 `COVSRC-*` nodes" was an assertion count read as a subject count.** Measured then: **37 subjects**, 31 carrying one anchor and 6 carrying two, for **43 anchor assertions**. Corrected to the peer through the vault, accepted, and it led them to the real cause — the URI collision of `CP13-F-01`. The population is now **44 subjects / 44 assertions**, and the correct figure was never 43 *or* 37: it was 44 covenants all along, with 7 of them colliding onto 6 URIs. | FIXED-upstream |
| `CP13-F-06` | **`ex:governedBy` does not exist in this estate** — 0 assertions — though the article's §B schema names it as a relationship. No proxy is substituted; the product does not claim a governing edge it cannot read. | ESTATE-LIMITATION |
| `CP13-F-07` | **548 of 37,865 passages carry no `sha256`**, and those same 548 carry no `alignment`, `heading` or `structure_aligned`. They cannot satisfy passage resolvability and are not citable. | ESTATE-LIMITATION |
| `CP13-F-08` | **18 of 40 memoranda carry no embedding** and cannot be reached by similarity at all. An absent embedding presents as "nothing relevant found", which is the failure mode this product exists to refuse. | ESTATE-LIMITATION |
| `CP13-F-09` | **Only 4 of the 7 borrowers with both a base and an amendment have a `governs_from` that separates them.** For the other 3 both texts begin governing on the identical date and an `as_of` reading cannot distinguish them. Any `as_of` gate must select from the 4. TRAP 4. | ESTATE-LIMITATION |
| `CP13-F-10` | **49 of 249 documents carry no `classification` and no `residency`.** The entitlement rules key on classification, so an unclassified document has no admitting row. The product treats absence as **not admitted** rather than as unrestricted. | ESTATE-LIMITATION |
| `CP13-F-11` | **One `COVDEF-*` node is typed `ex:Covenant`**, mixing the two namespaces — 181 `COV-*` plus 1 `COVDEF-*` make the 182. Recorded so a count keyed on the type is read as what it is. | NOT-A-GAP |
| `CP13-F-12` | **The two decaying λ_c classes are calibration values** and will be recorded with the measurement that chose them at Gate 2, under CLAUDE.md §9 and `D-IMPL-323`. The dominant class does not decay at all, so the rung-12 problem does not arise in the same form. | OPEN — closes at Gate 2 |
| `CP13-F-13` | **A Gate-1 figure was understated, and the sabotage that defended it caught the correction before the estate was repaired.** §0.1 said *one* of the 36 false citations hashed to the empty string; the full run gave **12**. The Gate-1 claim came from a three-row printed sample rather than from the whole population. Recorded because the lesson outlives the defect: a figure taken from a printed sample is not a measurement of a population, and the gate caught it only because it **computed** both mechanisms instead of quoting either. The state it measured is now `FIXED-upstream` at `CP13-F-01`. | FIXED-gate-2 |
| `CP13-F-14` | **All 49 `CovenantDefinition` nodes carry a real span and nothing to check it against.** 48 of 49 have `startOffset`, `endOffset` and `documentId`; **0 of 49 have `passageSha256` or `evidencedBy`**, and no indexed passage matches or even contains the span. The spans land on exactly the right text — *"Consolidated Fixed Charge Coverage Ratio" means, for any Measurement…* — which is what makes this the hardest case in the product: emitting it would feel safe and would still be an **asserted** citation rather than a checked one. Classified `span-unverifiable` and reported as Context Debt, distinct from `point-anchor`. | ESTATE-LIMITATION |

---

## F · Gate-2 assertions

### F.1 The declared set

| id | statement | what it catches |
|---|---|---|
| `CXR-G01` | a plan with zero operator steps never serves | empty-operator |
| `CXR-G02` | served lineage is exactly `operators_invoked`, `policy_bundle_versions`, `graph_snapshot_at`; the per-claim citation lives in the payload and never in `ProductLineage` | §B.1a — two things called `L` |
| `CXR-G03` | `expires_at` derives from the decision instant and respects the ceiling | TTL fabrication |
| `CXR-G04` | `D_c` above tolerance refuses with the debt block | ungated debt |
| `CXR-G05` | the four §6.3 axes are `ProductRequest` fields, absent from `parameters` | request identity demoted |
| `CXR-G06` | the payload carries no second copy of `D_c`, the content address or the policy versions | two copies of one figure |
| `CXR-G07` | **the citation unit is the named passage reached through `ex:evidencedBy`.** Every emitted citation is resolved by following `ex:evidencedBy` to a passage IRI, reading *that passage's* own `start_offset`, `end_offset` and `sha256` from MongoDB, and re-hashing the span — and it re-hashes to the recorded `sha256` or it is not emitted. **The anchor predicates on the evidence node are never the citation** | an unchecked citation, and a citation assembled from the wrong unit |
| `CXR-G08` | a chain node that is located but not quotable — a point anchor, or a passage with no `sha256` — emits **no citation** and is reported as Context Debt with its reason | a citation the text does not support |
| `CXR-G09` | **Policy-before-Similarity holds on BOTH limbs.** (a) the policy operator precedes the similarity operator in the resolved plan order, asserted on `operators_invoked`; **and** (b) the permitted-document set bounds the **MongoDB** retrieval before any ranking runs — the document filter is an argument to the query, never a predicate applied to its results. Two principals with different entitlements receive different content addresses. **Post-filtering unauthorized hits is prohibited**, not merely discouraged | TRAP 5 — post-filtering, on either limb |
| `CXR-G10` | a principal with no entitlement row for the requested `corpus_scope` is **refused**, never silently narrowed | a widened scope answered as a narrow one |
| `CXR-G11` | the governing text is selected by `governs_from` at `as_of`, never by `filed_date` | the filing-date gap |
| `CXR-G12` | the payload **declares** which node set the traversal seeded on | TRAP 3 — a silent seed |
| `CXR-G13` | an `as_of` before an amendment's `governs_from` serves the base text, asserted on one of the 4 borrowers whose dates separate | TRAP 4 |
| `CXR-G14` | an unknown covenant source refuses distinctly from a source with no definition chain | request error vs world fact |
| `CXR-G15` | no passage text is served for a document outside the permitted set, at any depth | allowlist containment |
| `CXR-G16` | **`ex:declaredAt` marks a point anchor and does not repair one.** Measured **170 assertions / 170 subjects, 158 on `DefinedTerm`**. The gate asserts BOTH halves: (a) the product reads `declaredAt` and reports such a node as *intentionally a point* rather than as a missing end; **and** (b) that node still carries no `endOffset`, still emits **no citation**, and is still Context Debt. **A predicate that names a limitation has not lifted it** | a declaration mistaken for a repair |
| `CXR-G17` | **`ex:governedBy` is absent and is not invented.** The predicate is measured at **0 assertions** though the article's §B schema names it; the payload asserts no governing edge and substitutes no proxy for one | a schema term honored by fabrication |
| `CXR-G18` | **an absent embedding is `not-evaluable`, never "no relevant result".** 18 of the 40 memoranda carry no embedding and cannot be ranked at all; the payload reports them as unreachable-by-similarity with that reason, and the count of ranked candidates is stated beside the count of eligible documents | silent unreachability read as an empty result |

### F.1a THE FOUR TRAP GATES

**Each measured trap is its own gate and its own Gate-2 sabotage target**, under
the rule `CP-SPEC-012` §F.1a established and this rung inherits:

> **A trap gate must DISTINGUISH the wrong mechanism from the right one. Two
> answers coinciding is not evidence.**

| id | trap | the gate, and where the two mechanisms DIVERGE |
|---|---|---|
| `CXR-G19` | **TRAP 1 — the correct span that cannot be audited** | asserted on the **49** `CovenantDefinition` nodes: **48 carry `startOffset`, `endOffset` and `documentId`; 0 carry `passageSha256` or `evidencedBy`; 0 passages match or contain the span.** The correct product emits **no citation** and reports `span-unverifiable` as Context Debt. The defective implementation — **extract the span and emit it, because the text is right** — emits **26** citations on the seeded population that no hash and no passage can check. The gate computes both and asserts they differ, and asserts the extracted text IS correct, because a gate that only showed the text was wrong would be proving the easy case. **Not asserted on a `PassageAnchor` node**, where `evidencedBy` resolves and both mechanisms agree |
| `CXR-G20` | **TRAP 2 — the point anchor** | asserted on a `DefinedTerm`, where `endOffset` is absent on **all 158**. The correct product emits Context Debt; an implementation that treated `startOffset` as a span start emits a citation whose span is undefined. Not asserted on a `CovenantDefinition`, where 48 of 49 carry both offsets and the two coincide |
| `CXR-G21` | **TRAP 3 — the plausible seed** | the product seeds on `ex:PassageAnchor` and reaches depth 3 on **26** sources; seeding on `ex:Covenant` reaches it on **1**. The gate runs both traversals and asserts the counts differ, so a deployment that quietly changed the seed is caught by the number rather than by the prose |
| `CXR-G22` | **TRAP 5 — post-filter similarity** | asserted across two principals whose permitted sets genuinely differ — `relationship-manager` (no memoranda at all) against `control-room` (all 40). The gate asserts the retrieval never touched an impermissible document, and that the two content addresses differ |

**Every one of these is a Gate-2 sabotage target**, and the sabotage for each is
the defective mechanism the trap names — reintroduced, and observed producing the
wrong answer on the divergence case the gate selects.

### F.2 Acceptance

**22 gates, `CXR-G01`–`CXR-G22`** — the count is unchanged across the 2026-09-13
estate correction, which replaced `CXR-G19`'s subject rather than removing it. `CXR-G16`, `CXR-G17` and `CXR-G18` were added at Dave's Gate-1 GO, which required ten points to be explicit in the table rather than only in the prose; `CXR-G07`, `CXR-G09` and `CXR-G19` were tightened in the same pass. Every figure in this document is measured
against the live estate on 2026-09-13; no SDK gap was found, and none is
authorized. No proxy was substituted for an absent leg: `ex:governedBy` is
reported absent, `ex:declaredAt` is reported unimplemented, and the definition
chain is seeded where the edges actually are rather than where the type name
suggests.

**Gate 1 awaits Dave's ruling.**
