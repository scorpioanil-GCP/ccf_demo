---
product: credit-risk.covenant-cross-reference.v1
standard: v0-3
owner: vault
sdk_spec: cp-13-canonical
tier: 3
cost_band: "×2–4 — one PostgreSQL read, a bounded Fluree walk, MongoDB passage reads and one bounded similarity retrieval, no LLM"
assembly_mode: 1
capability_classes: [relational, graph-traversal, document-passage, similarity]
prerequisites: [covenant-cross-reference]
topic: context-products
title: Covenant Cross-Reference (canonical) — Context Product Specification
generated: '2026-09-17'
---

# Covenant Cross-Reference (canonical) — Context Product Specification

**`CP-SPEC-013C` · the canonical rung-13 tree · Tier 3 · `credit-risk.covenant-cross-reference` @ `1.0.0` — the lane decided by measurement (§B.1, §D.4; measured 2026-09-17)**
**PostgreSQL `ccf_v2` for the corpus entitlement register · Fluree `fibo-v2` for the evidence anchors and their definition chains · MongoDB `fibo_v2` for passages, documents and memoranda — read-only**

> For each evidence node a caller may read, the definition chain walked to a
> declared depth, every citation re-hashed against the passage it names or
> reported as debt with its reason, and the policy envelope that bounded the
> retrieval before any ranking — **written on the paved producer road
> (`D-IMPL-343`), serving the class `CP-SPEC-014` requires from another
> process, with the frozen rung-13 specimen untouched.**

## 0 · What this document is

**This specification governs a SUCCESSOR, and the succession is disclosed
rather than glossed.** CP-14 Gate 2 slice 2 (Dave, 2026-09-15) classed the
frozen rung-13 specimen `examples/cp-13-covenant-cross-reference` **B** under
the A/B/C vocabulary — *leave frozen; a sibling would be the route* — for
three measured reasons: its Π and both of its measured debt factors close over
the whole acquisition result carried in through a closure, values the graph
never held and replay could not reconstruct from the snapshot; the entitlement
principal is a per-call argument on neither the request nor the perspective;
and it ships no door at all, so CP-14's covenant slot could not reach it
(`CP14-F-26`). Dave's consolidated GO of 2026-09-17 ruled the route: *build
the cp-13 paved successor following the established canonical-sibling route;
write and commit its specification before its implementation; keep the frozen
specimen untouched; preserve the required product class, supported questions,
entitlement behavior, citation checks and honest evidence debt; use the ruled
payload-comparison approach.* This document is that specification.

**It is producer substitution, not a renamed class.** The product identity is
unchanged: `credit-risk.covenant-cross-reference`, on the major lane
`CP-SPEC-014` §B.7 pins at a `1.0.0` floor. Which lane member this tree serves
is **measured, not asserted** (§D.4): the specimen serves the same question
today, so the successor is held to the specimen's own payload at a pinned
instant, and the lane follows from whether it matches.

**It cites `CP-SPEC-013` nowhere as an authority** (`D-IMPL-327`, the
`cp-04-canonical` ruling). The business meaning the specimen fixed — the
citation unit is the named passage reached through `ex:evidencedBy`; a point
anchor and an unverifiable span are debt with a reason, never a citation; the
entitlement bounds the retrieval before ranking; the governing text is chosen
by `governs_from`; `ex:governedBy` is absent and not invented — is preserved
here and re-stated in this document's own words.

### 0.1 What this tree teaches, and what it does not

It teaches **evidence as fabric state, on the paved producer road**. Four
things, and they are the whole subject:

1. **boot / answer as two regions**, with the SDK owning the door, both
   operators, Π, the three L6 gates, the product's own declared gate, the
   five-dimension replay record, the query pins and the delivery — one
   `open_product` and one `open_door`, no `build_governed_resolver` and no
   hand-written door.
2. **The evidence IS the graph.** The specimen's Π received the sources with
   their chains and citations, the policy envelope, the retrieval and the
   governing register through a closure over acquisition, and measured `C`
   and `S` off that same object. Here every admitted anchor node carries its
   own chain (every checked citation, every explained absence), the envelope
   and the governing register as claims; the debt reading and Π read the
   governed view and nothing beside it. A source the caller may not read is
   not in the view, and nothing about it is served — including its share of
   the debt.
3. **The entitlement principal is the perspective's role.** The specimen's
   `principal` argument named the roles the `corpus_entitlement` register
   keys on (`credit-officer`, `control-room`, `relationship-manager`). On the
   road the principal the acquisition checks is `context.perspective.role`:
   the deployment's declared default at the door, or the perspective a local
   caller states. A remote caller is served as the deployment's credit
   officer and never as a role it names itself.
4. **The frozen specimen is the control**: the successor is held to the
   specimen's own payload at one pinned instant (§D.4).

It does **not** re-derive the covenant domain. The anchor vocabulary, the
chain walk, the six-reason debt vocabulary, the entitlement register, the
bounded retrieval and the twenty-two properties the specimen's gates hold are
the specimen's, carried forward in `artifacts/` and `ccf_config.yaml` and
restated in §G.1.

### 0.2 Placeholder discipline

No figure in this document is a promise. Every number in §A.2 and §E is a
measurement taken on 2026-09-17 against the live `ccf_v2`, `fibo-v2` and
`fibo_v2` estate through the **frozen specimen** at its own demonstration
instant, reproducible from `examples/cp-13-covenant-cross-reference` with
`as_of` pinned, and **no gate in §G.1 pins one of them**.

### 0.3 Front matter

`tier: 3` and `assembly_mode: 1`: one PostgreSQL read (the entitlement
register), one bounded Fluree walk per source to `resolve_depth`, MongoDB
passage and document reads for every citation and governing date, one
similarity retrieval bounded by the permitted classification set BEFORE it
ranks. No LLM is reachable from any step.

### 0.4 The four-question test

*Who asks?* A credit officer testing compliance language, or a composite such
as `CP-SPEC-014`, about the evidence nodes of one or several agreements at one
instant. *What changes the answer?* The sources, the corpus scope the caller's
role is entitled to, the instant, the resolve depth. *What does a `SELECT` not
give you?* A citation that has been re-hashed against the passage it names,
the reason for every absence, the proof that the retrieval never scored an
impermissible document, which text governs at the instant, the debt in force,
the content address and the record that authorized it. *What is refused?* A
role with no entitlement row for the scope (refused, never narrowed), an
unknown evidence node (distinct from one with no chain), a debt above the
caller's tolerance, a payload with no admitted evidence node, an intent the
class does not serve.

## A · Decision frame

### A.1 Counterfactual — `confident fusion`

A memo writer who reads the definition text off the covenant node and quotes
it is quoting something no hash checks and no passage contains: the span is
correct and unauditable (`CXR-G19`'s trap). The product emits no such
citation and says why.

### A.2 The uncomfortable conclusion, preserved

Measured through the frozen specimen at its demonstration instant
`2026-09-13T00:00:00+00:00`, principal `credit-officer`, corpus scope `filed`,
resolve depth 3, the four evidence sources `artifacts/question.yaml` selects:

| | the four-source demonstration (`covenant-cross-reference-demo`) |
|---|---|
| chain nodes walked / checked citations | 21 / **4** |
| explained absences | 17 — 13 `point-anchor`, 4 `span-unverifiable`; 0 of the other four reasons |
| documents permitted / in force at the instant | 160 / 36; 0 not yet governing |
| similarity candidates examined / hits / not evaluable | 0 / 0 / 0 under `filed` — the filed scope permits no memorandum |
| entities in the governed view | 20 |
| `D_c` / signal | **0.8095 / `forced_llm`** — `F` 1, `C` 0.1905, `S` 1.0000 |
| expires | 2026-09-20T00:00:00+00:00 — the instant plus seven days, `ttl_anchor: from_decision` |
| payload content address (§D.4's baseline) | `5e87490c…` |

**Four citations can be checked out of twenty-one chain nodes, and the product
says so as debt rather than quoting the other seventeen.** `C` is 0.1905
because that is the evidenced share; nothing here was tuned to change it.

### A.3 A refusal is an answer, and two refusals are the walk's own

A debt above tolerance, an empty admitted view, an unknown intent, a wrong
producer identity at a consumer — each is returned as data with a replay
reference. Two conditions RAISE from the acquisition, exactly as the specimen
raises them, because they are the walk's own contract and the road does not
change it: an unknown evidence node (`UnknownCovenantSource`, "404", distinct
from a node with no chain) and a role with no entitlement row for the scope
(`ScopeNotEntitled`, "refused rather than narrowed"). `CP14-F-21` records that
a composite consumer sees these as the producer's door reports them.

## B · Contract

### B.1 The nine elements

| element | value |
|---|---|
| schema | `credit-risk.covenant-cross-reference` @ **`1.0.0`, measured** (§D.4, 2026-09-17): the successor's payload equals the specimen's at the pinned instant for the four demonstration sources, full canonical hash `5e87490c…`, zero field-level differences, equal debt factors, equal expiry — a second producer of the same product, satisfying `CP-SPEC-014`'s `1.0.0` floor |
| subject | one evidence node's URI when one source is asked; the caller's scope when several are — the specimen's own rule |
| intent | `compliance-test` — declared on `discovery.intents`; judged, never an argument |
| freshness | `amendment-driven` (the specimen's); `CP-SPEC-014` asks the covenant child at `as-filed` |
| TTL | fourteen days ceiling, product window seven days, `ttl_anchor: from_decision` — the instant plus seven days, as the specimen serves it |
| assembly mode | 1 — algorithmic |
| operators | `policy.principal-subgraph` then `traversal.typed-neighborhood`, exactly two, policy before traversal |
| lineage | graph-supplied; `serve_obligations.lineage_inputs_at` on `cross_references` and `citation_summary` |
| debt | `D_c = 1 − F·C·S`; `F` the SDK's reference freshness scorer over the view's observations with the booted λ_c table (every class `supersede-only`, so it reads 1 — `CP13-F-12`); `C` the share of chain nodes carrying a checked citation; `S` the share of absences carrying a closed-vocabulary reason — **both read off the admitted anchors' own chains in the view** and declared to the SDK's assembly scorer, so the three pins are the specimen's own |

### B.2 Request parameter surface

| parameter | type | default | domain | note |
|---|---|---|---|---|
| `covenant_sources` | array of string | — | — | **required**; the evidence nodes (`ex:PassageAnchor` URIs) this request may read; what the policy operator admits on |
| `corpus_scope` | string | `filed` | `filed` \| `filed-and-internal` | the policy envelope; a role with no row for it is refused, never narrowed |
| `resolve_depth` | integer | 3 | — | how deep the definition chain is walked |
| `debt_tolerance` | number | — | — | above it the product is withheld |

`intent` is **not** a parameter. **The CP-14 question** (`CP14-F-28`, the
parent logic this successor unblocks): `subject=<obligor LEI>` as the scope,
`intent=compliance-test`, `freshness=as-filed`,
`parameters={covenant_sources: <the evidence nodes of the obligor's facility
documents>, debt_tolerance}`. The consumer determines the sources from the
roster it owns — `ccf_v2.facility.(source_accession, source_document)` joined
as `"{accession}:{document}"` to the anchors' `ex:documentId` in `fibo-v2` —
and asks; it reconstructs no chain and no citation. Measured 2026-09-17: BGC
Group's `FAC-5B8418` names document `0001213900-26-057808:ea029103901ex10-1.htm`,
which carries two evidence anchors (`INTEREST_COVERAGE`, `LEVERAGE`).

## C · Data catalog

Three stores, the specimen's own element table restated: a six-row corpus
entitlement register keyed on (principal, corpus scope); 44 `ex:PassageAnchor`
evidence nodes of which 26 carry a definition chain, 49 `CovenantDefinition`
nodes, 158 `DefinedTerm` nodes, 170 `ex:declaredAt` point anchors; 249
documents, 37,865 passages, 40 memoranda of which 18 carry no embedding.

### C.1 The traps, all load-bearing

1. **The correct span that cannot be audited** — 48 of 49 covenant
   definitions carry offsets and no hash; the product emits no citation for
   them and reports `span-unverifiable`.
2. **The point anchor** — `ex:declaredAt` names a limitation and does not
   lift it; a `DefinedTerm` emits no citation and is `point-anchor` debt.
3. **The plausible seed** — the traversal seeds on `ex:PassageAnchor`, and the
   payload declares it.
4. **Post-filter similarity** — the permitted classification set is an
   argument to the MongoDB query, never a predicate over its results;
   `candidates_examined` is the figure that tells the two apart.
5. **New here — the evidence is a claim, not a closure.** A value Π needs
   that the graph does not carry is a value replay cannot reconstruct from
   the snapshot; on the road the chain, the envelope and the governing
   register are ingested as the anchor node's attributes and read off the
   view. The citation and chain-node entities are still ingested for the
   traversal; the policy operator maps no classification attribute for the
   citation class, so citations fall out of the view exactly as in the
   specimen and `entities_in_view` counts anchors and chain nodes.

## D · Assembly recipe

### D.1 Client call

In-process: `produce.product(scratch, environ=)` → `opened.question(…)` →
`opened.answer(asked, perspective=)` → `ServedProduct | RefusalEnvelope`, or
the walk's own two exceptions. Over MCP: `run.py --door`, the SDK's standard
door (`open_door`) over the same opened product, the `request_context_product`
tool, the door's `ProducerAssertion` on every outcome; a consumer registers
`producer_id` `cp-13-canonical-covenant-cross-reference-egress` under producer
tenant `cp-13-canonical-demo`.

### D.2 The two regions

`boot` (one `open_product` binding `acquire`, `project`, `assess` and the
product's own `gate` to the two documents) and `answer` (one governed
question). No registry, boot call, effective-request re-derivation, ingest
loop, builder call, store or record readback exists in the tree.
`acquire(context)` reads the effective `covenant_sources`, `corpus_scope` and
`resolve_depth` off the request the road hands it, the principal off
`context.perspective.role`, opens the three sources the environment document
names, and returns the specimen's envelopes — **edges first, attributed nodes
last** — with the anchor node carrying `source_json`, `envelope_json`,
`governing_json` and `seeded_on`. `project(required, request)` builds Π from
the effective request alone: the resolve depth and the declared seed; no
estate. `assess(context)` reads `C` and `S` off the view and states `F = 1`.
`gate(candidate, evidence)` is the specimen's citation gate, declared on the
class as `cp-13-canonical.citations-are-checked@1.0.0`.

### D.3 Validation gates

The SDK's three L6 gates, the class's declared lineage obligations (an empty
`cross_references` is refused by the SDK before the product's gate sees it),
and the product's own declared gate. A breach is a governed refusal with a
record, never a payload check.

### D.4 Determinism, replay and the lane measurement

Two runs of one question agree byte for byte; the door and the in-process run
agree byte for byte; replay dimension 1 lists every served entity and
dimension 2 carries the request contract and the policy bundle; replay
rebuilds the payload and the debt factors from the recorded snapshot with no
acquisition object alive.

**The lane is measured, not asserted.** The successor's `payload` for the four
demonstration sources at `2026-09-13T00:00:00+00:00` under the class defaults
and the declared perspective is hashed and compared with the specimen's payload
address in §A.2 (`5e87490c…`). The comparison is on the **payload**, not the
whole contract: the contract carries `tenant_id`, `plan_id` and the
policy-bundle version, which a sibling under its own tenant cannot share. If
the payloads match, the successor serves `1.0.0`; if they differ, `1.1.0`,
and §G.3 states every differing member and why. **No payload member is
adjusted to make the match.** The gate that holds this is `CXRC-G14`.

**Measured 2026-09-17, before this document was committed:** the payloads
match — full canonical hash `5e87490c…` on both sides, zero field-level
differences, `D_c` 0.8095 with `F` 1 / `C` 0.1905 / `S` 1.0000 on both,
expiry 2026-09-20T00:00:00+00:00 on both, 20 entities in view on both. The
lane is `1.0.0`.

## E · Volatility, debt and materialization

Every λ_c class of this product decays `supersede-only`: filed text does not
age, it is superseded, so `F` reads 1 and the debt is entirely evidence debt.
For the demonstration `C` is 0.1905 (4 of 21 chain nodes checked) and `S` is
1 (all 17 absences carry a reason from the closed set), so `D_c` is 0.8095
and the signal is `forced_llm` under the declared profile (forced 0.60,
fail-closed 0.95). Derived on demand; nothing cacheable across instants
because the governing register is chosen at the instant.

## F · Source binding and readiness

`ccf_environment.yaml`, the deployment-environment companion of
`ccf_config.yaml` under `D-IMPL-343`: three sources, `covenant_relational`
(`CCF_CP_13C_POSTGRES_DSN`, `_SCHEMA`), `covenant_graph`
(`CCF_CP_13C_FLUREE_URL`, `_LEDGER`) and `covenant_documents`
(`CCF_CP_13C_MONGO_URI`, `_DB`), names and remedies only; the door's
credential and advertised URLs (`CCF_CP_13C_DOOR_TOKEN`, `_ISSUER_URL`,
`_RESOURCE_URL`). The v2 namespaces are `fibo-v2`, `ccf_v2` and `fibo_v2`;
`ccf_dataprep/.env` names v1. Read-only. No `backends.yaml`, no
`server/door.yaml`.

### F.4 Findings

Raised in the tree's `FINDINGS.md` under `docs/EXAMPLE-EVALUATION-CRITERIA.md`.
Known before the build: the replay environment for a paved product is still
hand-assembled (`CP06C-F-01`, inherited); and whether the road's refusal to
pass acquisition values to Π is friction or the correct shape is recorded as a
measurement — this specification's position, as for `CP-SPEC-006C`, is that
it is the correct shape, and here it is also what makes a source the caller
may not read count for nothing in the debt.

## G · Operate and govern

### G.1 Product gates

The acceptance authority for every gate below is **this clause**
(`D-IMPL-326`). Each id is claimed by the executing test named in
`artifacts/gates.yaml`. The first twelve restate the specimen's properties
under the successor's ids; the rest are the successor's own.

| Gate | Asserts |
|---|---|
| `CXRC-G01` | **the citation unit is the named passage reached through `ex:evidencedBy`**: every served citation carries `checked: true` and the passage's own `sha256`; the anchor predicates on the evidence node are never the citation |
| `CXRC-G02` | a chain node that is located but not quotable — a point anchor, an unverifiable span — emits **no citation** and is reported as debt with a reason from the closed vocabulary; `ex:declaredAt` marks a point anchor and does not repair one |
| `CXRC-G03` | **the bound is applied before ranking, and two roles with different entitlements receive different content addresses**; `candidates_examined` never exceeds the permitted population |
| `CXRC-G04` | a role with no entitlement row for the requested `corpus_scope` is **refused, never narrowed** — the walk's own exception, as the specimen raises it |
| `CXRC-G05` | the governing text is selected by `governs_from` at `as_of`, never by `filed_date`; an instant before an amendment's `governs_from` serves the base text |
| `CXRC-G06` | the payload **declares** which node set the traversal seeded on |
| `CXRC-G07` | an unknown evidence node refuses distinctly from a node with no definition chain — the walk's own exception, as the specimen raises it |
| `CXRC-G08` | no passage text is served for a document outside the permitted set, at any depth |
| `CXRC-G09` | `ex:governedBy` is absent and is not invented; the payload asserts no governing edge and substitutes no proxy |
| `CXRC-G10` | an absent embedding is `not-evaluable`, never "no relevant result" |
| `CXRC-G11` | `D_c` above the caller's tolerance refuses with the debt block |
| `CXRC-G12` | replay dimension 2 is a superset of product policy lineage |
| `CXRC-G13` | **the door is the SDK's standard door opened from `door:`** — no door module, no `door.yaml`, no `backends.yaml` exists in the tree |
| `CXRC-G14` | **the lane measurement**: the successor's payload equals the specimen's at the pinned instant for the four demonstration sources, or the lane is `1.1.0` and §G.3 names every differing member |
| `CXRC-G15` | **the evidence is the view**: Π's constructor takes no estate and no source; a changed chain in the governed view changes the served citations AND the debt factor `C` in step |
| `CXRC-G16` | `shape_of` reads this tree as **paved**; no `build_governed_resolver` and no `build_replay_record` call exists |
| `CXRC-G17` | the frozen specimen is **untouched** and no specimen identity is reused — tenant, producer id, plan-id prefix, gate id, class ids |
| `CXRC-G18` | the CP-14-shaped question is answered by the producer **in another process** and admitted under `provider-controls` |
| `CXRC-G19` | the expected producer identity and tenant come from the registration — wrong id and wrong tenant refuse independently |
| `CXRC-G20` | the door and the in-process run serve **one** content address |
| `CXRC-G21` | an unknown intent is refused on the declared discovery set — the specimen accepts it |
| `CXRC-G22` | **the entitlement principal is the perspective's role**: through the door every caller is served as the declared credit officer; in-process a stated perspective changes the principal the envelope reports |
| `CXRC-G23` | a question that admits no evidence node is refused by the declared lineage obligation, never served empty |
| `CXRC-G24` | a fresh fabric per run; two questions under one root hash to their own addresses |
| `CXRC-G25` | replay reproduces the served bytes AND the debt factors from the recorded snapshot with no acquisition object alive; a tolerance refusal reconstructs through `replay_refusal` with no product rehydrated (`D-IMPL-344`) |

**All directional, structural or relational. No estate figure is pinned in a
gate** — the counts in §A.2 and §E are measurements a reader can reproduce.

### G.2 Acceptance criteria

1. A real governed `ServedProduct` of `credit-risk.covenant-cross-reference` on
   a lane `CP-SPEC-014` admits, with debt, content address and replay record.
2. The lane is decided by `CXRC-G14`'s measurement and recorded in §B.1.
3. The chain, the envelope and the governing register are fabric state; Π and
   the debt reading read the view.
4. The entitlement principal is the perspective's role, and the door serves
   under the declared default only.
5. The product is acquired across a deployment boundary through `D-IMPL-340`
   and admitted; every negative control refuses through the SDK's own path or
   raises as the specimen raises.
6. The frozen specimen is unchanged; CP-14's `producers.covenant` is
   re-pointed to this tree only after this tree's proofs are green.

### G.3 Where the successor and the specimen differ — the difference ledger (measured 2026-09-17)

**No payload member differs** for the demonstration question at the pinned
instant (`CXRC-G14`): full canonical payload hashes equal, field-level
comparison empty, debt value, factors and signal equal, expiry equal,
`operators_invoked` equal. The lane is therefore **`1.0.0`**.

**What differs, by construction and by design — none of it in the payload:**

| member or behavior | specimen | successor | why |
|---|---|---|---|
| `tenant_id` | `cp-13-crossref-demo` | `cp-13-canonical-demo` | a sibling under its own tenant |
| `plan_id` | `cp-13.covenant-cross-reference/<subject>` | `cp-13-canonical.covenant-cross-reference/<subject>` | its own identity (`CXRC-G17`) |
| `lineage.policy_bundle_versions` | the specimen's policy artifact hash | the successor's | the class id on the policy document differs; the regime and rules do not |
| replay dimension 1 | anchors carrying `covenant_type`/`threshold`/`document_id` only | anchors **also** carrying `source_json`, `envelope_json`, `governing_json`, `seeded_on` | the evidence is fabric state (`CXRC-G15`); the snapshot id differs accordingly |
| the entitlement principal | a per-call `principal=` argument, default `credit-officer` | `perspective.role`, default `credit-officer` | the road's sanctioned channel (`CXRC-G22`); the default is the same principal |
| `debt.scorers` — the pins `D-IMPL-47` records | `F` the SDK's freshness scorer; `C` and `S` the SDK's declared-factor scorer over two figures computed off the estate | **the same three pins**: the deployment runs the SDK's assembly scorer over the view and declares `C` and `S` to it — read off the view, not the estate | equal; the assessment is equal member for member |
| an unknown `intent` | served | **refused** on `discovery.intents` (`CXRC-G21`) | a governed axis the specimen left open — deliberate |
| zero sources | `request()` raises `ValueError` before any read | **refused** by the declared lineage obligation on `cross_references` (`CXRC-G23`), with a record | the road's own answer to an empty admitted view |
| the door | none (`CP14-F-26`) | a 27-line launcher over the SDK's standard door (`CXRC-G13`) | `D-IMPL-343` |
| documents | three (`ccf_config`, `backends`, gates) | two (`ccf_config`, `ccf_environment`) | one authority per value |

Neither deliberate tightening changes a citation, a debt reason, an
entitlement outcome or the business meaning of a served answer; each converts
an ungoverned path into a governed refusal with a record.
