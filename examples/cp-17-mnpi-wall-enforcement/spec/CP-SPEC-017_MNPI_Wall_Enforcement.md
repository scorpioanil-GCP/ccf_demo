---
product: cib.mnpi-wall.v1
standard: v0-3
owner: vault
sdk_spec: cp-17
tier: 5
cost_band: "×8–15 — one departmental SQLite read first, two PostgreSQL reads, three bounded Fluree literal reads, one MongoDB read; four operator categories; no LLM"
assembly_mode: 1
capability_classes: [relational, bitemporal-ledger, graph-traversal, document-passage, in-memory]
prerequisites: [client-360-coverage-graph, covenant-cross-reference, credit-memo-context]
topic: context-products
title: MNPI Wall Enforcement — Context Product Specification
generated: '2026-09-20'
---

# MNPI Wall Enforcement — Context Product Specification

**`CP-SPEC-017` · rung 17, the first Tier 5 product · `cib.mnpi-wall` @ `1.0.0` · Gate 1 — written before any code exists, per Dave's direction of 2026-09-20 (*"prepare MNPI Gate 1 and stop"*)**
**Departmental SQLite `departmental.sqlite` for the control-room restricted list · PostgreSQL `ccf_v2` for principals, projection plans, deals, interactions, positions and the issuer · Fluree `fibo-v2` for wall crossings, embargo windows, the Reg FD event and the issuer's family · MongoDB `fibo_v2` for research notes — every read read-only, every write to a per-request scratch fabric**

> One address, three credentials, three structurally different products. The
> product a principal receives is bounded by what its verified credential
> permits — never by a parameter it states — and a relationship the principal
> may not see does not survive into the view the fabric serves it: Policy
> runs first, removes what the credential does not admit, and endpoint
> closure takes every relationship to a removed entity with it.
> Written on the paved producer road (`D-IMPL-343`) through the SDK's standard
> door with three overrides, so that the friction of putting several
> principals behind one door is measured rather than described.

---

> ## READ THIS BEFORE YOU READ A NUMBER
>
> **These examples teach METHOD — how to engineer and construct a Context
> Product with the CCF SDK — not the figures.**
>
> Every count and date in this document is here to show how a specification
> binds to a real store, and for no other reason. Measured read-only on
> 2026-09-20 against the live estate: `ccf_v2.deal` 32 rows, `interaction`
> 2,050, `position` 10, `principal` 4, `projection_plan` 3 — all
> `synthetic — internal`; `fibo-v2` `WallCrossing` 4 (three
> `synthetic — internal`, one `synthetic — engineered` with a nine-day
> recording lag built in), `EmbargoWindow` 9, `RegFDEvent` 1; `fibo_v2`
> `research_note` 42 (33 published, 9 drafts under embargo); the departmental
> `restricted_list` 4 rows. The ten issuers these records hang off are real
> legal entities (`ccf_v2.legal_entity`, `provenance = 'public'`); **every
> deal, interaction, position, research note, wall crossing and restriction
> attached to them is invented.**
>
> **No number here is a fact about any real company, any real desk, or any
> real information barrier.**
>
> The same statement is repeated beside each figure cluster below rather than
> left here as a header a reader scrolls past.

---

## 0 · What this document is

A specification of **one** Context Product — `cib.mnpi-wall.v1` — written to
the Context Product Specification Standard v0.3 before the assembly it
specifies exists. It is the first rung of the ladder's Tier 5, and the vault
article it realizes says why it comes first: *"It is the smallest complete
demonstration of `Π` and `P` operating together, and every other T5 product
assumes the reader has seen it."*

**This document is a coverage test, not a design invitation.** Dave's
governing principle for the remaining rungs (2026-09-20) is carried here
verbatim because every section below was written under it: *"The remaining
examples are SDK coverage tests, not invitations to perfect the SDK. Build
the minimum honest example that exercises the capability. Change the SDK only
when an example exposes incorrect behavior, a genuinely missing required
capability, or repeated plumbing that materially harms adoption."* Nothing
in this specification asks for an SDK change. Where the vault's wording is
realized by a different mechanism than its words suggest, the difference is
disclosed in §0.1 and again where the reader meets it, and every one of those
realizations was ruled at Gate 0 (`docs/GATE-0-COVERAGE-CP15-24.md` §5.1,
Appendix B; `docs/DECISIONS.md`, GATE-0 DIRECTION, 2026-09-20).

**Status (Dave, 2026-09-20): Gate 1 ACCEPTED WITH SPEC CORRECTIONS —
IMPLEMENTATION HOLD.** Dave's nine rulings — eight corrections and the
implementation hold — are folded in where the reader meets them: the A6 property as a load-bearing gate (`MWE-G16`); the precise form of
claim 3; no jurisdictional rule (§C.4 trap 10); the HTTP door in scope for
the requested-role refusal (`MWE-G15`); the Reg FD widening held to
ccf-dataprep's evidence with two Gate-2 outcomes (§C.4 trap 5) — **answered
the same day: outcome B**; supervisor
semantics (claim 7, `MWE-G19`); the locked decisions preserved; both dataprep
debts in the owner register (§F.2). No producer, `run.py` or SDK change
exists. The hold's release condition was met on 2026-09-20 by ccf-dataprep's
answer (§F.2 row 1, outcome B); the build begins on Dave's GO and not before.

### 0.1 What this product intends to prove, and how each claim is realized

Seven claims, each with the SDK mechanism it rides and the gate in §G.1 that
holds it. This is the list Dave asked for — *"bring us the spec and what it
intends to prove"* — and it is the whole subject of the rung.

| # | What it proves | Realized by | Held by |
|---|---|---|---|
| 1 | **Several credentialed principals through ONE standard door.** Three bearer credentials reach one MCP door and receive three products with one schema, one plan and one operator set, and three distinct content addresses. A fourth real principal with no grant is refused as unconfigured. | `runtime/ccf_runtime/mcp/product_door.py` (`open_door`) with its three typed overrides — `token_verifier=` (a `StaticTokenSource` holding three grants), `perspective_resolver=` (client id → role, data-driven from `ccf_v2.principal`), and the tenant's three-grant `ProductEntitlementPolicy` registered **after** the door's own registration (the latest-wins ordering the Gate-0 matrix named as private knowledge — measured here, §G.2 item 12) | `MWE-G01`, `MWE-G14` |
| 2 | **Entitlement as a formative constraint sourced from the credential.** The bounding sets — which relationship classes and which classifications a principal may receive — come from the principal's projection-plan row keyed by the verified identity, never from a request parameter. The request surface carries no `perspective` and no `corpus_scope` (§B.4). | The acquisition seam: `src/ccf/products/product.py` (`AcquisitionContext.perspective`) — the second instance of the credential-derived envelope after cp-13-canonical, measured under the DX rubric (§G.2 item 12) as Dave ruled for A2 (*"build MNPI with the existing mechanism … measure at the third instance"*) | `MWE-G02`, `MWE-G03` |
| 3 | **Restricted relationships do not survive in the principal's governed view.** The precise property, as ruled (Dave, 2026-09-20): restricted entities *may* exist in the fabric; policy-first substitution removes inadmissible entities from the principal-conditioned view, and endpoint closure prevents any relationship to a removed entity from surviving in that view. The security claim is about the governed view presented to downstream operators and to Π — never about physical absence from L3. | Reification: engagements, notes and positions are entities carrying a `classification` attribute; `src/ccf/operators/categories.py` (`PolicyFilter`) runs first (`CATEGORY_ORDER`) and substitutes the admissible subgraph; `docs/GRAPH_QUERY_SEMANTICS.md` `GQ-16` (an edge exists only when both endpoints survive). **Ruled the accepted realization** of the vault's "not in the traversal's vocabulary" (Gate-0 direction, preserved rulings). | `MWE-G03`, `MWE-G05`, `MWE-G06` |
| 4 | **Policy before Similarity is not cosmetic.** No draft note under embargo participates in the public-side ranking of research — the candidates the Similarity operator ranks are drawn from the view Policy already formed. | `src/ccf/operators/base.py` (`CATEGORY_ORDER`: policy → similarity → temporal → traversal); `src/ccf/operators/categories.py` (`SimilaritySelect`) over the reified `research_note` entities with the reference lexical index — the first domain rung to run all four operator categories | `MWE-G07` |
| 5 | **Wall state is bitemporal.** Who was over the wall on a date is answered on two clocks: valid time (`validFrom`) and assertion time (`assertedAt`, the control room's recording). The same question at the same `asked_at` answers differently under `known_as_of` before and after the control room recorded the crossing. | `temporal.as-of-boundary` over the claims' validity windows at `asked_at`; `known_as_of` as a declared request parameter with a relative default, applied to the wall key at acquisition (the cp-08 / cp-12 pattern) | `MWE-G08` |
| 6 | **A Reg FD supersession as a classification-member change — outcome B, selected by the data.** ccf-dataprep states (2026-09-20, `contrib/ccf-dataprep/cp-17-regfd-000-designates-nothing-outcome-b`, a `measurement` with `reproduce_with`) that `REGFD-000` designates no records: generated in Wave 7 (`7a37a4d`) as a dated label — its issuer whichever entity sorts first, its date the run date minus 45 days, no field able to hold a record id, the prose description dropped at load — with zero incoming edges, zero literals naming it and no referencing column, each absence measured with a positive control. So claim 6 is the narrower property Dave's ruling allows: the issuer's `reg_fd_disclosure` member (§D.6), a dated public-filed fact, is `null` before the instant and carries the event after it, for every principal, and no engagement content is admitted to anyone on the strength of the label. **Outcome A is retired**: the stronger claim was never in the data and, by ruling, is not to be put there. Prior determinations that touched the issuer are invalidated, subject to `MWE-G11`'s `[TBC]` (§F.2 row 6). | The event served as a dated public-filed fact on the issuer whose classification member changes across the instant; `src/ccf/controlplane/invalidation.py` (`EntityInvalidationRegister`) for the boundary | `MWE-G10`, `MWE-G11` |
| 7 | **No disclosure; a supervisor is a separately entitled principal.** The served payload carries no count, marker or placeholder of withheld content; its member set is a function of the role and never of the subject; nothing restricted crosses the door in any byte; and a principal's product **and its replay record** omit the wall-decision inputs (which crossing, which restriction, which plan keyed the wall) whenever that principal is not entitled to them. "The supervisor learns everything" means a supervisor holds a different credential, entitlement and projection plan, whose independently governed product may carry the broader evidence because its plan permits it — it never means restricted information is hidden inside the banker's or the analyst's product. **The A6 property is a load-bearing gate here:** for an unentitled principal, a subject whose admissible claims are completely removed by Policy is observationally indistinguishable from a nonexistent subject on the paved serve path — an existence oracle is what it protects against. | The declared product gate (`ProductClassDeclaration.declared_product_gate`, one slot, three predicates); the A6 measurement of 2026-09-20 (`tests/products/test_policy_emptied_view_disclosure.py`, six tests, with its positive control) carried as `MWE-G16`; the replay record's pins (dimension 2 policy and plan versions, dimension 4 role) as a supervisor's reconstruction route under its own credential | `MWE-G04`, `MWE-G16`, `MWE-G19` |

Three of the vault's statements are realized differently from their wording,
by ruling, and the difference is disclosed rather than repaired:

- **"Walk only the permitted edge types"** is realized by reification and
  endpoint closure (claim 3), not by a per-principal traversal vocabulary on
  one plan — `TraversalNeighborhoodParameters.relationship_types` is
  class-level and the SDK has no per-perspective operator parameters. The
  vocabulary-containment gate is a deployment predicate (`MWE-G03`).
- **"`projection_plan_id` enters the lineage record"** is realized as one
  `plan_id` whose Π branches on the role, answered from replay dimension 5
  (the plan) and dimension 4 (the role) — ruled sufficient. `ProductLineage`
  carries no `projection_plan_id` member; the estate's `plan_version` reaches
  the record as a pinned Control Plane artifact (§D.3 step 7).
- **"`perspective` is requestable but never self-asserted"** is exercisable
  over HTTP only (`?role=`); both MCP doors call the resolver with no
  requested role, so over MCP a perspective cannot be asked for at all. The
  refuse-not-downgrade property is demonstrated on the HTTP door (`MWE-G15`)
  and stated, for MCP, as the absence of the channel.

### 0.2 Placeholder discipline

No figure in this document is a promise. Every count and date in §C and §F is
a read-only measurement of 2026-09-20 against the live `ccf_v2`, `fibo-v2`,
`fibo_v2` and departmental SQLite estate, reproducible from the queries §F.3
names and, since 2026-09-20, from ccf-dataprep's own coverage instrument for
this product (§F.2 row 15), which the spec cites in preference to its census
wherever the two overlap — and **no gate in §G.1 pins one of them** — every gate is directional,
structural or relational, so estate drift exercises the example rather than
breaking it (CLAUDE.md §9). Every `[TBC]` reappears in §F.2 with an owner.

### 0.3 Front matter

`tier: 5` because the product reads five capability classes across four
stores and runs all four operator categories. `assembly_mode: 1` — a
registration-time commitment: the wall is a structural property of the
assembled view and no model may reconcile, summarize or "helpfully" narrate
what a principal may see; a model in the trust path here would be a wall
breach by construction. `capability_classes` differs from the vault's list in
one member: `vector-index` is replaced by `in-memory`, because the estate's
research notes carry `text-embedding-3-small` vectors but the SDK ships no
embedder and no vector substrate on the paved road; the Similarity operator
runs the reference lexical index (§C.2, §D.3 step 3).

### 0.4 The four-question test

*Who asks?* A coverage banker, a research analyst and a trader — three
principals with three credentials — asking for context on one issuer at one
instant. *What changes the answer?* The credential (which side of the wall,
which plan), the instant (`asked_at`, the valid-time clock), the control
room's knowledge at `known_as_of` (the assertion-time clock), the issuer.
*What does a `SELECT` not give you?* A view in which the restricted
relationship does not exist rather than one it was deleted from; a ranking
that never scored a restricted document; a decision record from which a separately
entitled supervisor can see which plan version bounded what the analyst saw; the content address that proves three principals got three
products. *What is refused?* A principal with no grant (refused as
unconfigured, the deny audited, observationally the same as a nonexistent
product); a requested role outside the grant (refused by typed code, never
downgraded); an issuer with no row (served computed-empty, identical under every
entitled credential — never a refusal, `MWE-G16`); an intent the class does not serve; a debt above the caller's
tolerance; a product assembled without the control room's list. **All four
answers are the vault's own; none was softened.**

## A · Decision frame

### A.1 Counterfactual — Policy Blind, in its most consequential form

The vault's counterfactual, kept whole: a conventional architecture assembles
the full context and applies entitlement as a display filter. Three things
then go wrong, in increasing severity. The query already ran against
restricted material, so a public-side result set is *shaped by* documents the
analyst may not see (retrieve-then-filter versus project-then-retrieve,
whitepaper §6.1). Absence becomes informative: "3 results hidden" tells the
analyst that undisclosed activity exists. And the principle of §6.5 is
violated: entitlements determine what the context is allowed to *be*, and a
sensitive relationship must not reach an unauthorized consumer's view — the
vault's reading of §6.5; the precise property this rung claims is §0.1 claim 3.

### A.2 The counterfactual acceptance test

A numbered procedure ending in an assertion that can fail, discharged by a
test in the example.

1. Open the product; put three credentials behind the standard door.
2. Ask for issuer `0IDE18EMH1CUKQCUYE69` (SP Plus Corp — an issuer that on
   2026-09-20 carries two MNPI-bearing deals, two MNPI-bearing interactions,
   one position, five published research notes, a wall crossing for the
   coverage banker, a `research-restricted` row on the control room's list
   and the estate's only Reg FD event) at the pinned instant `T1 =
   2026-08-17T00:00:00Z`, `intent = client-review`, under each credential.
3. Record the three served vessels and their canonical bytes.
4. **Assert** the three content addresses differ, and the class, `plan_id`
   and operator set do not.
5. **Assert** no byte of the research analyst's or the trader's vessel
   contains any identifier of an MNPI-bearing deal or interaction
   (`DEAL-0030`, `DEAL-0000`, the two interaction ids) — not in the payload,
   not in the lineage, not in a finding.
6. **Assert** the member set of the analyst's payload for SP Plus at `T1`
   equals the member set of the analyst's payload for SP Plus at an instant
   before any of its MNPI-bearing records existed (`2025-01-01T00:00:00Z`;
   its earliest MNPI-bearing deal opened 2025-05-12): the shape is a function
   of the role, never of the subject's state. One demonstration issuer at two
   instants — no second issuer is introduced to manufacture a contrast.
7. Now run the *Policy Blind* control: assemble the banker's view and
   project it under the analyst's Π branch. **Assert** the result differs
   from step 3's analyst vessel — the control is what a display filter
   produces, and if it did not differ the wall would be cosmetic.

If step 4, 5, 6 or 7 fails, the product has not been demonstrated.

### A.3 A refusal is an answer

Three refusals are the wall's own and each is a successful demonstration, not
a red run (`docs/EXAMPLE-EVALUATION-CRITERIA.md` §A): the fourth principal in
the estate, `PRIN-KYC-004` (the EU KYC analyst, who has a credential in this
deployment and no grant), is refused as unconfigured on MCP and on HTTP
alike; each of the three entitled credentials asking over HTTP for a role
outside its own grant is refused by typed code, never downgraded; a
question posed before the control room's list could be read is refused for
every principal with the source class named.

## B · Contract

### B.1 The nine elements

| element | value |
|---|---|
| schema | `cib.mnpi-wall` @ **`1.0.0`** — the first producer of this class; payload type `mnpi_scoped_issuer_context`, machine-readable at `schemas/mnpi_scoped_issuer_context.v1.json` (§D.6), declaring the **maximal** shape; no principal receives all of it |
| subject | the issuer's LEI, the request `subject`; acquisition mints `issuer://<hash of {lei}>` and the traversal seeds on class `issuer` — a subject with no issuer row leaves the per-request fabric empty and is **served** as computed-empty, identically under every entitled credential, never refused: a refusal would distinguish a nonexistent subject from a policy-emptied one (`MWE-G16`, the A6 comparator) |
| intent | `client-review` — declared on `discovery.intents`; judged on the declared set, never an argument; an unknown intent is refused as class-mismatch |
| freshness | per signal class (§E.1): `position` intraday (illustrative 86,400 s half-life, §E.1 says why not the vault's hour); every other served class `supersede-only` — "event-driven" is a supersession event, not a number |
| TTL | product window 3,600 s (the vault's one hour), class ceiling `[TBC — this build]` (proposed 14,400 s), `ttl_anchor: from_decision`: `expires_at = decided_at + 3,600 s`, and `decided_at` is `asked_at` because the class declares no separate decision instant (§B.4, the past-instant trap) |
| policy binding | the wall (which classifications the principal's plan permits, unlocked per issuer by a valid, asserted crossing); research embargo windows; the Reg FD event as a supersession that changes the issuer's classification member (outcome B, selected by ccf-dataprep's answer of 2026-09-20 — §C.4 trap 5); the control room's restricted list read before any enterprise source. **No jurisdictional information-barrier rule** (ruled, Dave 2026-09-20): the estate's jurisdiction table is evidence and context only, never a filter or an admission rule, and a displayed jurisdiction is labeled non-governing context (§C.4 trap 10). The personal-account-dealing binding the vault names is **not bound** and its data is not invented (§F.2 row 10) |
| lineage | `operators_invoked` — the four SDK operator keys, typed; `policy_bundle_versions` — the tenant policy and the served principal's **own** projection-plan artifact, pinned (the principal is entitled to its own plan; no other principal's plan is carried — whether the pin can be scoped to one plan or pins the whole `policy` section is `[TBC — this build]`, §F.2 row 14); the λ_c table pinned in the replay record; `graph_snapshot_at` — the as-of boundary (the source ledger `t`, 5832 on 2026-09-20, is execution provenance recorded by acquisition as a watermark, never product identity — `D-IMPL-88`, `D-IMPL-309`); `serve_obligations.lineage_inputs_at` on `issuer` and `context_debt`; passage-level `L` on research notes as note ids with content hashes |
| debt | `D_c = 1 − F·C·S`. `F` the SDK's reference scorer over the composed view against the booted λ_c table (supersede-only classes read 1; `position` decays); `C` the share of the **principal's own** required signal classes present (§E.2 — a class the principal may not receive is not in that principal's `C_required`, `D-IMPL-105`); `S = 1` stated (one authority per element, §C.3) |

Assembly mode 1, semantic version `1.0.0`, discovery registered only after
§G is complete, addressability the SDK's own address form
(`/{tenant}/{product_class}/{version}` over HTTP, the three-segment MCP URI)
— which carries no principal by construction, and is the mechanism behind
"one address, three products". The vault's `/context-products/cib/issuer-
context/{lei}` template is declarative documentation read by no door and is
not restated as a route.

### B.2 Classification and residency

Highest classification of any §C element: `internal-restricted` (MNPI-bearing
engagements, draft research under embargo). Information barrier: the product
*is* the barrier's enforcement, so the barrier is stated as the three plans.
Residency and cross-border serving: not bound — no jurisdiction-based
filtering or admission logic exists on this rung by ruling (§C.4 trap 10);
the issuer's `legal_jurisdiction` member is non-governing context. **The
suppression rule, restated as this product's first-order obligation:** where
the wall excludes content the payload carries **no count, no marker, no
placeholder** — and this extends to the SDK's own marker channel, the served
`ComputedEmptyFinding`, which was measured on 2026-09-20 to say only that the
principal's admitted view is empty and never that a subject had restricted
material behind it. The payload's member set is fixed per role (§D.6).

### B.3 Model-risk annotation

Not applicable — no model in the trust path. Mode 1, enforced by the
`@algorithmic` import lint.

### B.4 Request parameter surface

| parameter | type | Moves | default | domain | note |
|---|---|---|---|---|---|
| `subject` | string(20), required | `E` anchor | — | an LEI | the issuer; resolved to `ccf_v2.legal_entity` at acquisition |
| `intent` | enum, required | `P` envelope selection | — | `client-review` | judged on the declared discovery set; not an argument |
| `asked_at` | datetime, required on the wire | `T` — the valid-time clock, the wall state "at a past point" | the door's instant | — | **this is the vault's `as_of`.** There is no separate `as_of` parameter: the SDK's as-of cut, the wall key's valid-time test and the TTL anchor all run at `asked_at`. **The past-instant trap, disclosed:** a forensic question at a past `asked_at` under a `from_decision` anchor carries `expires_at = asked_at + 3,600 s`, already elapsed by the wall clock — served, because the TTL-bounds gate's "now" is `decided_at` (`src/ccf/products/gates.py` (`_refuse_ttl`)). Every demonstration instant is pinned anyway (§C.5) |
| `known_as_of` | datetime | `T` — the assertion-time clock | `asked_at` (relative default, offset 0) | any instant; a forensic re-ask sets it after `asked_at` | the control room's knowledge: a crossing counts only if `assertedAt ≤ known_as_of` (`MWE-G08`); cp-08's pattern |
| `debt_tolerance` | number | a measure — the refusal threshold | the class default | 0–1 | above it the product is withheld with its debt block |

**Deliberately not on the surface, and why — this is the design decision of
the rung.** The vault's table names `perspective`, `corpus_scope` and
`sections`. None is declared:

- `perspective` — declaring it would be accepted by the SDK and never
  honored (only `intent` has a boot-time shadow refusal), and a Π that read
  it would condition on a caller's claim, the exact thing the wall forbids.
  The perspective is the door's: the verified credential, the resolver, the
  grant. Over HTTP a caller may *request* a role with `?role=`, which is a
  door query parameter validated against the grant, not a product parameter
  (`MWE-G15`).
- `corpus_scope` — the document envelope is the plan's
  `permitted_classifications` and `permitted_document_types` for the verified
  principal; a caller-stated scope would be the wall as the caller's claim.
  (cp-13-canonical's `corpus_scope` is a scope the *role's* register row
  bounds; here the row is the whole envelope and there is nothing left for a
  caller to choose.)
- `sections` — a formatting flag that moves no dimension; pushed to the
  consumer per the Standard.

None of the three is "declared but inert": they are absent, so a request
naming one is refused by the request contract as an unknown parameter rather
than accepted and ignored.

### B.5 Prerequisites, consumers and scope boundary

Prerequisites (vault): `client-360-coverage-graph` (cp-07),
`covenant-cross-reference` (cp-13), `credit-memo-context` (cp-14) — for the
reader, not the build: this product requires no child. Consumers, named
individually: `ib-opportunity-synthesis` (cp-18) inherits this product's wall
state as a governed child, and `aml-typology-match` (cp-19) reuses its
deployment shape (three principals, credential-sourced envelope,
policy-before-similarity) — named as catalog consumers only; neither is
authorized or in progress under the implementation hold. Scope boundary, the
vault's sentence: *"Three requests, one Context Graph, three products that
differ in what exists rather than in what is shown."* Checked against §C and
§D.6: the payload declares no field the vault's scope excludes; the two
control-room facts the vault lists as `P` elements (wall state, restricted
list) are envelope inputs and are **not payload members** for any principal this rung declares — a
separately entitled supervisor's own product may carry them (§D.3 step 1.7,
`CP17-F-02`) — (§C.1, §D.3 step 1), which is narrower than a reader of the vault's banker
row ("nothing structurally absent") might expect and is stated here so it is
not read as an oversight.

## C · Data catalog

### C.1 Element table

Store · schema · table named per element, as the Standard requires of the
implementation artifact. Provenance class from the closed list; `synthetic`
is a property of the estate (§0 banner), not a provenance class.

| element | system of record | store · table / collection · type | provenance class | classification assigned at acquisition | capability class | G | ontology IRI |
|---|---|---|---|---|---|---|---|
| Issuer | GLEIF via the estate's entity master | PostgreSQL `ccf_v2.legal_entity` (156 rows, 10 carry MNPI records) | public-filing | `public-filed` | relational | `E` | `fibo-be-le-cb:Corporation` |
| Issuer family (`owns`, `controls`) | the estate's ownership graph | Fluree `fibo-v2` predicates `owns` (636 assertions), `controls` (3) | public-filing | `public-filed` | graph-traversal | `R` | `cmns-org:` control / ownership |
| Deal pipeline and engagement records | internal deal system | PostgreSQL `ccf_v2.deal` (32; `mnpi_bearing` 11 over 10 issuers) | internal-SOR | `internal-restricted` when `mnpi_bearing`, else `internal-confidential` | relational | `E`, `R` (minted `hasDealEngagement` / `hasMnpiEngagement`) | `cmns-org:` engagement `[TBC — this build: exact IRI]` |
| MNPI-bearing and other interaction records | internal CRM | PostgreSQL `ccf_v2.interaction` (2,050; `mnpi_bearing` 18, `need_to_know` 10, both 0) | internal-SOR | `internal-restricted` when `mnpi_bearing` or `need_to_know`, else `internal-confidential` | relational | `E`, `R` (minted `hasInteraction`) | as above |
| Trading positions | internal position system | PostgreSQL `ccf_v2.position` (10, one per issuer, `as_of` 2026-08-15 … 17, date-grained) | internal-SOR | `internal-confidential` | relational | `E`, `R` (minted `hasPosition`) | `fibo-fbc:` position `[TBC — this build]` |
| Research notes, published and draft | internal research system | MongoDB `fibo_v2.research_note` (42: 33 `published` / `public-filed`, 9 `draft` / `internal-restricted`, all with `embargo_until`; 42 of 42 embedded, 1,536 dims) | internal-SOR | `public-filed` when published, `internal-restricted` when draft | document-passage | `E`, `L`, `R` (minted `hasPublishedResearch`) | `[TBC — this build]` |
| Wall-state assertions — who is over the wall, on which issuer, from when, recorded when | internal control-room system | Fluree `fibo-v2` type `WallCrossing` (4 nodes, all `principalId = PRIN-COV-001`, each with `validFrom`, `assertedAt`, `recordingLagDays`, `basis`) | internal-SOR | *envelope input — not a served claim* | bitemporal-ledger (literals; §C.4 trap 9) | `P`, `T` | — |
| Research embargo windows | internal research policy | Fluree `fibo-v2` type `EmbargoWindow` (9 nodes, one per draft note, `validFrom`/`validTo`) | internal-SOR | *envelope input* | bitemporal-ledger | `P`, `T` | — |
| Regulation FD disclosure event | public filing, engineered | Fluree `fibo-v2` type `RegFDEvent` (1 node: `REGFD-000`, SP Plus, `validFrom 2026-07-03`, `widensAccess true`; **designates no records** — ccf-dataprep 2026-09-20; its label reads `synthetic — internal`, which ccf-dataprep flags as arguably one class too weak; cited as measured) | public-filing | *supersession source (outcome B)* | bitemporal-ledger | `T`, `P` | — |
| Control-room restricted list | departmental system, compliance-maintained | SQLite `departmental.sqlite` table `restricted_list` (4 rows; `lei`, `restriction_type`, `added_date`, `removed_date` all NULL) | internal-SOR | *envelope input, read first* | relational (departmental) | `P` | — |
| `ProjectionPlan` definition per principal | internal | PostgreSQL `ccf_v2.projection_plan` (3 rows keyed by `principal_id`, `plan_version v1.0.0`: `permitted_edge_types`, `permitted_classifications`, `permitted_document_types`) | internal-SOR | *the envelope* | relational | `Π`, `P` | — |
| Principal register | internal identity substrate | PostgreSQL `ccf_v2.principal` (4: `PRIN-COV-001` coverage-banker private, `PRIN-RES-002` research-analyst public, `PRIN-TRD-003` trader public-surveilled, `PRIN-KYC-004` kyc-analyst private) | internal-SOR | *identity → role for the perspective resolver* | relational | `Π` | — |

*(The figures above are measured 2026-09-20 on an engineered estate; no number is a fact about any real company.)*

Dropped from the vault's catalog, with the reason where a reader meets it:
public filings and narrative text (the product cites research notes; filings
are the analyst's public corpus already served by cp-03 and cp-13 and add
nothing to the wall demonstration), Form 4 insider activity and blackout
windows (the blackout half has no type or predicate in `fibo-v2` — §C.4 trap
6), public market data and adverse media — no wall property rides on them, and ccf-dataprep states (2026-09-20, the coverage manifest) that **no issuer-level market data exists anywhere in the estate**: the three market tables are macro-grain and none carries an `lei` column, measured with a control (§C.4 trap 11) —
document classification and MNPI tags as a MongoDB element (the tags live in
PostgreSQL, the classification on the note — §C.4 trap 8, recorded as a
divergence in ccf-dataprep's manifest). Filings, where a later reader probes
them, key on `form`: `doc_type` is null on every EDGAR document in the estate
(ccf-dataprep, 2026-09-20).

### C.2 Capability decomposition

| required capability | separable property | availability | if absent |
|---|---|---|---|
| Departmental read before the enterprise stores | a file-backed SQLite reachable by path from the environment document | widely available | the product is refused for every principal, source class `control-room` named (`MWE-G09`) — silence is not a clean list |
| Bitemporal wall state | two date literals per crossing (`validFrom`, `assertedAt`) | sometimes — here real data on 4 nodes, one engineered with a 9-day lag | the assertion clock collapses onto the valid clock and `MWE-G08` cannot be demonstrated; state it |
| Per-principal envelope keyed by identity | one plan row per principal | sometimes | an unconfigured principal is refused, never given a default plan |
| Reified engagements with a classification | the deployment mints entities and edges from rows (§C.4 trap 1) | widely available | — |
| Similarity over research text behind Policy | the SDK's reference lexical index over an entity attribute | widely available (shipped); the vector path is not (no embedder ships) | interim posture: lexical ranking, the embeddings unused and said so (§0.3) |
| Reg FD supersession (outcome B — a dated label that designates no records) | a dated event naming the issuer | rare — one node | the demonstration is one event, once, as a classification-member change (§C.4 trap 5) |

### C.3 Correlation key, single-writer discipline, and identity authority

The join key is the LEI end to end: `legal_entity.lei` ↔ `deal.lei` ↔
`interaction.lei` ↔ `position.lei` ↔ `research_note.lei` ↔ `WallCrossing.lei`
↔ `restricted_list.lei` — no crosswalk is needed and coverage is total for
the ten issuers that carry MNPI records (measured: every deal, position,
interaction and note LEI resolves in `legal_entity`). Principal identity
comes from the verified credential's `client_id`, mapped to the estate's
`principal_id` by the deployment's token source, and to a role by
`ccf_v2.principal.perspective`. Wall state is keyed by `(principalId, lei)`
with a validity interval and an assertion date. One authoritative writer per
element: the fabric's L2 worker is the only writer to the per-request graph;
the estate is read only. `S = 1` because each element has one system of
record — the Fluree `Interaction` nodes (2,050) mirror the PostgreSQL rows
and are **not read**, so no second authority is consulted for the same claim.

### C.4 The data traps, each with the binding chosen and what it costs

1. **The plans' edge vocabulary exists nowhere in the ledger.** The three
   plans name `hasDealEngagement`, `hasInteraction`, `hasMnpiEngagement`,
   `hasPublishedResearch`, `hasPosition`; 0 of the 181 distinct `fibo-v2`
   predicates match (client-side count, 2026-09-19). *Binding:* the
   deployment **mints** these edges and their reified endpoint entities from
   PostgreSQL and MongoDB rows at acquisition, exactly as cp-04-canonical
   mints `depth`. *Cost:* the vocabulary is the deployment's and is disclosed
   in `artifacts/source-vocabulary.yaml`; a reader who expects to find it in
   the ledger will not.
2. **One engineered recording lag carries the bitemporal demonstration.**
   `WALL-000` (SP Plus, `validFrom 2026-03-07`, `assertedAt 2026-03-16`,
   `isEngineeredRecordingLag true`) is the only crossing whose two clocks
   differ by more than a day. *Binding:* `MWE-G08` is pinned to it. *Cost:*
   estate drift on one node would silence the gate; the gate asserts the
   two answers *differ* and names its node, never the dates.
3. **Drafts and published notes never coexist on one issuer, and the
   demonstration issuer has no drafts.** Charter (5 notes, all draft) and
   Agilysys (4, all draft) have no published research; the other eight
   issuers, SP Plus among them, have no drafts. *Binding:* SP Plus stays the
   single demonstration issuer (ruled — no second issuer to manufacture a
   contrast); the vault's "restricted documents would have altered the
   ranking" number is measured on SP Plus and is **zero by construction**
   (there is no draft to withhold), so the policy-before-similarity property
   is proven by sabotage instead: a draft claim injected into the analyst's
   per-request fabric must be absent from the Similarity operator's
   candidates and from the served product (`MWE-G07`) — a containment proof,
   not a re-ordering proof. *Cost:* said in §F.4 and the README. (Under the
   reference per-candidate index with a score floor the re-ordering number
   is structurally zero on any issuer anyway — Gate-0 matrix §4.2.)
4. **Restricted-list rows are positionally assigned by the loader.**
   ccf-dataprep's known-issues §13.3: a loader re-run would shift which LEIs
   are restricted. *Binding:* read-only, never re-run; this document pins
   the four as measured (BGC `full-restriction` 2026-04-19, American
   Healthcare REIT `deal-related` 2026-05-19, Charter `full-restriction`
   2026-07-05, SP Plus `research-restricted` 2026-07-11; none removed).
   *Cost:* none while the rule holds.
5. **The Reg FD event names the issuer and the instant, not the records it
   discloses — and ccf-dataprep has established that it names none.**
   `REGFD-000` carries `lei`, `validFrom` and `widensAccess`. *Binding —
   ruled (Dave, 2026-09-20):* the disclosed set is **not inferred from the
   event label.** *Answered 2026-09-20 by ccf-dataprep* (`contrib/ccf-dataprep/cp-17-regfd-000-designates-nothing-outcome-b`,
   measured against ccf_dataprep `fcf7ddd` with `reproduce_with`): the event
   was generated in Wave 7 (`7a37a4d`, 2026-08-17) as a dated label — the
   issuer is whichever entity sorts first, the date is the run date minus 45
   days, no field can hold a record id, and the loader writes six triples,
   dropping even the prose `description`; zero incoming edges, zero literals
   naming it, no Postgres column referencing it, each absence with a
   positive control. **Outcome B is selected by the data:** the event is
   served as a dated public-filed fact on the issuer — the `reg_fd_disclosure`
   member of §D.6, `null` before the instant and the event with its
   `public-filed` classification after it, for every principal — with no
   engagement content admitted to any principal on the strength of the label.
   **Outcome A is retired**: nothing is engineered to reach it. *Cost:* the
   vault's "widening supersession" is demonstrated as a member change, not as
   an admission of content, and §G.3 says so.
6. **Blackout windows do not exist.** No type or predicate in `fibo-v2`
   matches; the Form 4 half exists as 319 `OpportunitySignal` nodes the rung
   does not need. An `ex:InsiderDesignation` node exists and is a Regulation O
   related-persons designation (12 CFR 215), not a trading blackout —
   ccf-dataprep 2026-09-20, flagged so a later scan for "insider" is not read
   as a contradiction. *Binding:* the vault's row is dropped, disclosed here and
   in the README. *Cost:* the vault's "insider transaction and blackout
   windows" `T` element is unproven by this rung.
7. **Position `as_of` is a date.** A one-hour half-life on a date-grained
   field is unobservable: every position is 0 to 2 whole days old at any
   instant. *Binding:* λ_c(`position`) = 86,400 s, **illustrative**, chosen
   so the freshness term moves across three real subjects at `T1`
   (American Healthcare REIT 08-17 → 1.0; SP Plus 08-16 → 0.5; BGC 08-15 →
   0.25) — `D-IMPL-323`'s four conditions, disclosed in the artifact, the
   README and here (§E.1). SP Plus remains the single demonstration issuer
   for the wall and the no-disclosure contrast; `MWE-G12` reads two other
   issuers' positions only as freshness comparison subjects, as
   `D-IMPL-323` requires, and gives no second issuer a crossing. *Cost:* the vault's "~1 hour" is not the served
   value.
8. **The corpus-entitlement register is not this product's.**
   `ccf_v2.corpus_entitlement` (6 rows) is keyed by cp-13's roles
   (`credit-officer`, `relationship-manager`, `control-room`). *Binding:* the
   document envelope is read from `projection_plan.permitted_classifications`
   and `permitted_document_types` by `principal_id`. MNPI tags are PostgreSQL
   booleans (`deal.mnpi_bearing`, `interaction.mnpi_bearing`); MongoDB
   `document.mnpi` does not exist and `research_note.classification` is the
   note's only tag. *Cost:* one table choice, documented.
9. **As-of over the Fluree HTTP path silently ignores the ledger `t`**
   (ccf-dataprep known-issues §51), and date literals are untyped (§59).
   *Binding:* wall state at `asked_at` is derived from the `validFrom`,
   `validTo` and `assertedAt` literals read as strings and parsed by the
   deployment; the ledger `t` is recorded as a watermark only. *Cost:* the
   as-of answer is the deployment's arithmetic over literals, never the
   ledger's.
10. **Two of the vault's policy bindings have no estate, and one is ruled off
    this rung.** No personal-account-dealing table exists in any of the four
    stores — confirmed by ccf-dataprep on 2026-09-20 with a matcher and a
    positive control (§F.2 row 10, closed): the binding is not bound, and
    neither its data nor its function is invented because it is absent. `principal_jurisdiction` (17 rows) exists, but data
    existing does not make a policy — **ruled (Dave, 2026-09-20): no
    jurisdictional information-barrier rule on CP-17.** The table is evidence
    and context only; no jurisdiction-based filtering or admission logic
    anywhere in the tree; the issuer's `legal_jurisdiction` member, where
        displayed, is labeled non-governing context (§F.2 row 11, closed).
11. **The trader's "market data" does not exist per issuer.** The vault's
    trader row is "positions, market data, public disclosure". ccf-dataprep
    states (2026-09-20, the coverage manifest): the three `ccf_v2` market
    tables (`market_oas_series`, `intraday_tick`, `fx_intraday_tick`) are
    macro-grain — rating-band OAS, the Treasury curve, currency pairs — and
    none carries an `lei` column, against 25 tables that do (the control).
    *Binding:* the trader's product carries positions, the issuer and its
    family, and no price series; the trader perspective's distinctiveness
    rests on `hasPosition` being in its vocabulary while research and
    engagements are not, which the plan row already states. *Cost:* the
    vault's "public market data" `E`,`T` element is unproven by this rung,
    and no per-issuer series is invented to prove it.


### C.5 What this data is — stated once more, because it is the point

*(Every figure in this section is measured 2026-09-20 on an engineered
estate; no number is a fact about any real company.)* The demonstration
instants are pinned: `T1 = 2026-08-17T00:00:00Z` (the headline; every
crossing valid and asserted, every restriction in force, the Reg FD event
past, positions dated within the prior two days), `T0 = 2026-07-01T00:00:00Z`
(before the Reg FD event and before two of the four restrictions, Charter's and SP Plus's), and
`TW = 2026-03-10T00:00:00Z` (inside `WALL-000`'s nine-day recording lag).
Pinning `asked_at` is what a snapshot estate requires and it is disclosed
wherever the reader meets a date; nothing moves `asked_at` to get an answer.

## D · Assembly recipe

### D.1 Client call

In-process: `produce.product(scratch, environ=)` → `opened.question(…)` →
`opened.answer(asked, perspective=)` → `ServedProduct | RefusalEnvelope`. Over
MCP — the demonstration's primary route: `run.py --door`, the SDK's standard door
over the same opened product with three overrides (§D.3 step 0), the
`request_context_product` tool; three clients hold three bearer credentials
read by env name (`CCF_CP_17_TOKEN_COVERAGE`, `CCF_CP_17_TOKEN_RESEARCH`,
`CCF_CP_17_TOKEN_TRADER`) and a fourth holds `CCF_CP_17_TOKEN_KYC`. The
forensic call, which exercises the most surface:

```
request_context_product
  subject:      "0IDE18EMH1CUKQCUYE69"
  intent:       "client-review"
  asked_at:     "2026-03-10T00:00:00+00:00"
  parameters:   {"known_as_of": "2026-03-20T00:00:00+00:00", "debt_tolerance": 0.8}
```

under the coverage credential — the crossing valid on 2026-03-07, known to
the control room since 2026-03-16, asked as of 03-10 with 03-20's knowledge.
The same call with `known_as_of` omitted answers with 03-10's knowledge and
carries no MNPI engagement. Over HTTP — in scope by ruling, for the one
behavior MCP cannot expose (`MWE-G15`): `GET
/{tenant}/cib.mnpi-wall/1.0.0?subject=…&intent=client-review&asked_at=…`
with `?role=` present or absent, under the same three entitled credentials
and the fourth ungranted one. The HTTP door is `create_app(auth=)` with
`BearerTokenAuth` over the same token map, over the same opened product —
it exercises the role-request behavior, not a second product path.

### D.2 Operator step table

One operator per step, the closed vocabulary, with the SDK mechanism and its
layer as the eighth column. Steps the Standard names that are not SDK
operators (Resolve, Enrich, Compose) are stated as L2 assembly or Π with
`operator: null`, per `D-IMPL-223`. Budgets are `[TBC — this build]`,
measured at Gate 2 against a declared p95 envelope of 3,000 ms; the vault's
×8–15 band is the relative statement.

| # | operator | capability class | inputs | emits (as it appears in lineage) | failure behavior | p95 | SDK mechanism (layer) |
|---|---|---|---|---|---|---|---|
| 0 | *door* — not an operator | — | a bearer credential; the wire request | the verified grant, the entitled `Perspective`, the allow/deny audit event | **403** unconfigured principal, refused with no detail on what exists; **403** requested role outside the grant (HTTP) | `[TBC]` | `runtime/ccf_runtime/mcp/product_door.py` (`open_door`) with `token_verifier=`, `perspective_resolver=`; over HTTP `runtime/ccf_runtime/http_api/app.py` (`create_app`) with `BearerTokenAuth` over the same token map (`MWE-G15`); both through `runtime/ccf_runtime/authz/product_entitlement.py` (`entitled_perspective`) — the Experience layer |
| 1 | **Resolve** (`operator: null`) | relational · departmental · bitemporal-ledger literals · document-passage | the effective request; `context.perspective`; the source names | one `SignalEnvelope` per admissible claim, **edges first, attributed nodes last**; no wall-decision attribute for a principal not entitled to it (§D.3 step 1.7; no entitled principal is declared on this rung); the ledger watermark | **503** with the source class named when the departmental store or any mandatory source is unreachable; **no issuer row is not a failure** — acquisition emits nothing and the empty fabric is served as computed-empty on the same path a policy-emptied view takes (`MWE-G16`) | `[TBC]` | the deployment's `acquire` under `src/ccf/products/product.py` (`AcquireProtocol`, `AcquisitionContext`); ingested by `src/ccf/assembly/worker.py` (`AssemblyWorker`) — **L1 → L2**, the single writer |
| 2 | **Policy** | in-memory | the assembled view; the class's classification map and permitted vocabulary; the policy-bundle version | `policy.principal-subgraph` in `operators_invoked`; the substituted subgraph; `policy_bundle_versions` | a view every claim of which is inadmissible is served as computed-empty naming this key — identical, vessel and finding, to a subject whose fabric holds no claims at all (`MWE-G16`, A6); the finding is a fact about the view, never about what the fabric holds | `[TBC]` | `src/ccf/operators/categories.py` (`PolicyFilter`), first by `CATEGORY_ORDER` — **L4** |
| 3 | **Similarity** | in-memory (reference lexical index) | the policy-formed view; the class-level query literal; the floor | `similarity.corpus-select`; the ranked `research_note` candidates with `index_version` | an empty candidate set is served as computed-empty naming this key | `[TBC]` | `src/ccf/operators/categories.py` (`SimilaritySelect`) over the index `src/ccf/deployment/operators.py` (`build_operator_registry`) constructs — **L4** |
| 4 | **Traversal (mode `temporal`)** | bitemporal-ledger *(supplied by the fabric)* | the view; `asked_at` | `temporal.as-of-boundary`; the claims valid at the boundary; `graph_snapshot_at` | a claim with no validity window is not excluded (`GQ-09`, the absence limb) — every dated claim here carries one | `[TBC]` | `src/ccf/operators/categories.py` (`TemporalAsOf`, `require_valid_at_boundary: true`) — **L4** |
| 5 | **Traversal** | graph-traversal | the view; seed class `issuer`; the product's full edge vocabulary; depth 1 | `traversal.typed-neighborhood`; the issuer's neighborhood | an empty walk is served as computed-empty naming this key | `[TBC]` | `src/ccf/operators/categories.py` (`_bounded_walk`), `GQ-10`/`GQ-11`/`GQ-16` — **L4** |
| 6 | **Enrich** (`operator: null`) | — | — | — | — | 0 | nothing: every attribute arrives on its claim at step 1 |
| 7 | **Projection** | in-memory | the composed view; the entitled perspective; `known_as_of` | `plan_id` (one, role-branched) in replay dimension 5; the role in dimension 4; the typed payload of §D.6 | degrade with debt: a required class absent from the principal's `C_required` raises `D_c`, never a placeholder | `[TBC]` | `src/ccf/projection/plan.py` (`ProjectionPlan.invoke`) under `src/ccf/projection/engine.py` (`ProjectionEngine`) — **L5** |
| 8 | *contract assembly* — not an operator | in-memory | the payload, the declared lineage, TTL and anchor; the declared gate | the served `ContextProductContract` inside a `ServableProduct`; the replay record | **503** on any L6 gate; the declared gate's `ProductInvariantRefusal` by name; **409** above tolerance with the debt block | `[TBC]` | `src/ccf/products/gates.py` (`run_gates`) then the declared gate via `src/ccf/products/resolver.py` (`ProductGateProtocol`) — **L6** |

Mirrored into `artifacts/assembly-recipe.yaml` with a witness per step; a
step nothing executes is red.

### D.3 Step detail

**Step 0 — the door, and the one ordering rule.** `open_door` derives a
one-principal entitlement policy from `default_perspective` and registers it
unconditionally; the entitlement source reads the latest registration under
the tenant key. The deployment therefore registers its three-grant
`ProductEntitlementPolicy` (`src/ccf/products/entitlement.py`) **after**
`open_door` returns — grants for `PRIN-COV-001` (`coverage-banker`),
`PRIN-RES-002` (`research-analyst`), `PRIN-TRD-003` (`trader`), each
`permitted_schema_names = {cib.mnpi-wall}` and one `permitted_roles` member;
no grant for `PRIN-KYC-004`. The token source is a `StaticTokenSource`
(`runtime/ccf_runtime/mcp/auth.py`) holding four credentials read by env
name, each mapped to its `principal_id` as `client_id` and to the scope
`ccf:egress`. The perspective resolver maps `client_id` → role from
`ccf_v2.principal.perspective` read once at open; a resolver that minted an
ungranted role would be refused by the seam. **This ordering rule is
private knowledge and is counted as such under the DX rubric** (§G.2 item
12); the alternative — handing `entitlement_source=` its own registry — is
the same count with one more object.

**Step 1 — Resolve, and the envelope computed from the credential.** In
this order, and the order is load-bearing:

1. **The control room's list, first.** Open the departmental SQLite by the
   path the environment document names; read `restricted_list` for the
   subject LEI. Unreachable → refuse for every principal this product would
   ever serve — ruled to include a separately entitled supervisor, though
   this rung declares none — source class `control-room`. A row with `added_date ≤ asked_at < removed_date` (or
   NULL) is the restriction in force.
2. The issuer from `legal_entity`; no row → emit nothing, so the empty
   per-request fabric is served as computed-empty, identically under every
   entitled credential (`MWE-G16`) — **not** a refusal: a refused nonexistent subject
   beside a served policy-emptied one would be the existence oracle A6
   guards against.
3. The principal's plan row from `projection_plan` by
   `context.perspective.principal_id`. No row → refuse (a principal the
   door entitled but the estate has no plan for is a deployment
   misconfiguration, refused by name at serve; whether the refusal can move
   to open is `[TBC — this build]`, §F.2 row 13).
4. Wall state: every `WallCrossing` for `(principal_id, lei)` with
   `validFrom ≤ asked_at` and `assertedAt ≤ known_as_of`; embargo windows
   for the issuer's draft notes; the Reg FD event for the issuer.
5. **The envelope** `E(p, i, asked_at, known_as_of)`: the entity classes
   named by the plan's `permitted_edge_types` (axis 1, the vocabulary), and
   the classifications the plan permits (axis 2), where `internal-restricted`
   on issuer *i* is admitted **only if** a crossing from step 4 exists — the
   plan is the ceiling, the crossing is the key. Draft research is admitted
   by axis 2 alone (the research department's own drafts need no deal-team
   crossing; the vault's banker row).
6. Read deals, interactions, positions (PostgreSQL), research notes
   (MongoDB) and the family (`owns`/`controls`, Fluree) for the issuer;
   **emit envelopes only for claims inside `E`**, each reified entity
   carrying `classification`; mint the typed edge from the issuer. Outcome B
   is selected (§C.4 trap 5): emit the event itself as a dated public-filed
   fact on the issuer (the `reg_fd_disclosure` member, §D.6) and nothing
   else — no engagement record is re-classified by it. (Outcome A, a
   superseding public claim per disclosed record on the same entity URI, is
   retired: the data never held a disclosed set.)
7. **No wall-decision attribute is written into the fabric of a principal
   not entitled to it.** The crossing that keyed the wall and the restriction
   in force are consumed at this seam and are not emitted as claims or
   attributes for a principal not entitled to them — so neither the served
   vessel nor the replay record of the banker, the analyst or the trader
   carries them (`MWE-G19`, ruled). The principal's **own** plan version is
   pinned in `policy_bundle_versions` as a Control Plane artifact version,
   because the principal is entitled to its own plan; no other principal's
   plan is. A supervisor is a separately entitled
   principal whose own plan would admit the control-room elements; this rung
   declares no such principal (§F.4 `CP17-F-02`). What the issuer claim does
   carry: `ledger_t` as the watermark.

**Two filters on two axes are two filters.** Axis 1 (vocabulary) and axis 2
(classification, keyed per issuer by the crossing) are computed separately
and tested separately (`MWE-G03` and `MWE-G02`); a single combined test would
pass for the wrong reason whenever a class happens to be excluded on both.

**Where the per-principal envelope lives, stated plainly — this is the A2
measurement.** The SDK offers no way for the credential to reach the Policy
operator's `permitted_classifications`: its only binding is
`RequestBoundParameter` from the effective request — a caller's claim, which
is the thing a wall forbids — and a role-applicable `PolicyConstraint` folds
scalar membership only, so a list cannot be contained element-wise (Gate-0
A2, B1). The envelope is therefore applied at the acquisition seam from
`AcquisitionContext.perspective`, as cp-13-canonical applied its register.
**This is the second instance of that plumbing; it is counted, not
generalized** (Dave: *"Once we've written this plumbing for the third time,
measure it … decide then"*).

**Step 2 — Policy runs first even when it appears to do nothing.** With the
envelope applied upstream, the operator's class-level parameters — a
`classification` attribute mapped for every reified class, the permitted set
= the product's whole vocabulary `{public-filed, internal-confidential,
internal-restricted}`, the tenant's policy-bundle version — admit everything
acquisition emitted. It is not decorative: it is the containment guarantee
that any claim reaching the fabric outside the product's vocabulary, or from
a foreign policy-bundle version, is removed before anything ranks or walks,
and `MWE-G06` proves it live by sabotage. And it is what `GQ-16` closure
rides: an entity the operator removes takes its incident edges with it. The
two layers are deliberate — acquisition never fabricates an inadmissible
claim; Policy would remove one if it did — and each is tested on its own.

**Step 3 — Similarity behind Policy.** `ranked_entity_classes =
{research_note}`, the corpus attribute `body`, a class-level query literal
`[TBC — this build; illustrative]` drawn from the `client-review` intent's
vocabulary, `minimum_score_percent` `[TBC — this build]`. The candidates are
the notes already in the policy-formed view, so a draft is never scored for
the analyst or the trader. Π serves the top-k `[TBC — this build; proposed
3]` by score — the relative cutoff that makes the vault's "ranking
difference" number observable at all (§C.4 trap 3).

**Step 4 — the as-of cut is the valid-time clock.** Every dated claim
carries `valid_from` (deal `opened_date`, interaction `interaction_date`,
position `as_of`, note `authored_date`, the Reg FD supersession). The
assertion-time clock is not an operator axis: `known_as_of` is applied to
the wall key in step 1 (the crossing's `assertedAt`), which is where the
control room's knowledge bears.

**Step 5 — the walk.** Seed class `issuer`; `relationship_types` the
product's full minted vocabulary plus `owns` and `controls`; `depth_limit`
1. Per-principal narrowing is not the walk's — the walk sees only what
acquisition put in the fabric and Policy kept (the 2026-09-20 fixture fact:
a product is scoped by what acquisition put in the per-request fabric, not
by the traversal operator's parameters — Policy has already formed the view,
step 2).

**Step 7 — one plan, three branches.** Π reads `perspective.role` and shapes
the payload for that role from the governed view: the banker's members are
`issuer, family, deal_engagements, interactions, research`; the analyst's
`issuer, family, research`; the trader's `issuer, family, positions`; the issuer member carries
`reg_fd_disclosure` for every role (§D.6). The
member set is fixed per role (`MWE-G04`): Π adds no member because data
exists and drops none because it does not — an issuer with no published
research yields `research: []` for the analyst, which is public state. Π
reads the governed view and nothing beside it. The estate's three plan rows are registered as
Control Plane artifacts at open (`plan_version v1.0.0` each) so the served
principal's own version is pinned in `policy_bundle_versions` (whether the
pin can be scoped to one plan is §F.2 row 14); a supervisor's "which plan
version did this analyst see" is answered from that record's dimension 5
(`plan_id`) and dimension 4 (`role`) plus the analyst's own plan pin — which
the analyst's record carries because the analyst is entitled to it — read
under the supervisor's own credential; no crossing id, restriction row or
other principal's plan is carried there.

### D.4 Determinism class and payload hash

`deterministic`. The content address is the canonical hash over the vessel
excluding `assembled_at`; two runs of one question under one credential agree
byte for byte, the door and the in-process run agree byte for byte
(`MWE-G18`). Three credentials, one question, one instant: three addresses
(`MWE-G01`).

### D.5 Replay statement and replay test

1. Serve the banker's SP Plus product at `T1`; record.
2. Ask again at `asked_at = TW`, once with `known_as_of = TW` and once with
   `known_as_of = 2026-03-20` (different questions, not mutations — the
   estate is read-only) and confirm the two answers differ from each other.
3. Replay the step-1 record: the original returns, byte for byte, with no
   acquisition object alive (`MWE-G17`).
4. Replay the KYC principal's refusal: the record carries the cause
   (`unauthorized`) and the deny audit event, and reconstructs (`MWE-G17`).

Two time axes ⇒ a second test asserting the axes **disagree** under the
constructed case: same `asked_at = TW`, `known_as_of = TW` versus
`known_as_of = 2026-03-20` — different addresses (`MWE-G08`). Agreement would
mean the assertion-time filter was dropped.

### D.6 Emitted contract

`schemas/mnpi_scoped_issuer_context.v1.json`, `extra=forbid`, the maximal
shape; the members present are a function of the role (§D.3 step 7):

```
mnpi_scoped_issuer_context @ 1.0.0
  issuer:            {lei, legal_name, legal_jurisdiction, entity_status,      # legal_jurisdiction: non-governing context (ruled)
                      reg_fd_disclosure: {event_id, valid_from, classification: public-filed} | null}   # every role; null before the event; the member claim 6 proves (outcome B)
  family:            [{lei, legal_name, relationship: owns|controls}]
  deal_engagements:  [{deal_id, deal_type, stage, opened_date, classification}]      # coverage-banker
  interactions:      [{interaction_id, interaction_type, interaction_date, deal_id, classification}]   # coverage-banker
  research:          [{note_id, title, authored_date, status, classification, score_percent, content_hash}]   # coverage-banker, research-analyst
  positions:         [{position_id, book, quantity, as_of}]                          # trader
  known_as_of:       datetime
```

No member counts anything withheld; no member is a marker; `classification`
on a served member states the classification of what was served, which is
inside the principal's envelope by construction (`MWE-G02`).

### D.7 Validation gates

The SDK's three universal gates (`src/ccf/products/gates.py` (`run_gates`):
empty-operator guard, lineage strict equality, TTL bounds), the declared
obligations gate (`lineage_inputs_at` on `issuer` and `context_debt`), the
dependency-invalidation gate for the Reg FD boundary (§E.4), and the
product's own declared gate `cp-17.wall-holds@1.0.0` folding three
predicates under the one slot:

- **vocabulary containment** — every served edge type is in the principal's
  `permitted_edge_types`;
- **classification containment** — every served `classification` is in the
  principal's permitted set, with `internal-restricted` present only under a
  keyed crossing;
- **no disclosure** — the payload's member set equals the role's declared
  member set, and no member of any served vessel names a withheld
  identifier.

A breach is a `ProductInvariantRefusal` by name, as data, never a payload
check. The suppression-silence and classification-containment gates the
Standard names as universal are this declared gate; they do not ship in the
SDK and this is the **fourth** example-level writing of a containment gate
(cp-01, cp-02, cp-11, here) — recorded in §F.4 as the §H threshold reached,
not acted on.

Error mapping: no issuer row → served computed-empty, identical under
every entitled credential (`MWE-G16`); unentitled principal → refused with no
detail; requested role outside the grant → typed refusal (HTTP); departmental
store unreachable → mandatory input unavailable, source class named; above
tolerance → withheld with the debt block; unknown intent or parameter →
refused by the contract.

## E · Volatility, debt and materialization

### E.1 Half-life table

Per served signal class. Calibration basis stated on every row; **no row is
measured**, and one is illustrative in the `D-IMPL-323` sense with the
reason.

| signal class | λ_c | basis | decay driver | supersession event | owner |
|---|---|---|---|---|---|
| `issuer` | supersede-only | — | reference-data maintenance | GLEIF record update | SDK examples maintainer |
| `family_member` | supersede-only | — | ownership filing | superseding ownership assertion | as above |
| `deal_engagement` | supersede-only | — | deal stage change | stage or classification supersession (the Reg FD event is **not** one — outcome B, §C.4 trap 5) | as above |
| `interaction` | supersede-only | — | CRM correction | superseding interaction record | as above |
| `research_note` | supersede-only | — | publication | a draft published, a note withdrawn (in this estate no draft leaves `draft` at `embargo_until` — §E.4) | as above |
| `position` | **86,400 s — illustrative** | illustrative | intraday trading | the next position snapshot | as above |

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

The vault's ~1 hour for positions is unobservable on a date-grained `as_of`
(§C.4 trap 7); 86,400 s is the smallest value at which the term still
discriminates between three real subjects at `T1`, and `MWE-G12` asserts the
ordering, never the number. Wall state, embargo windows and the restricted
list carry no λ_c row because they are envelope inputs, not served
observations; their currency is the control room's, disclosed in §F.4.
`decay_basis: valid-from` on `position` so the age is the snapshot date, not
the ingestion instant (`D-IMPL-331`).

### E.2 Debt model and per-component debt

`D_c = 1 − F·C·S`, multiplicative. `F` over the composed view, normalized
over the principal's required classes. `C` per role: banker
`{issuer, deal_engagements, interactions, research}`; analyst
`{issuer, research}`; trader `{issuer, positions}`; `family` optional for
all. A class the principal may not receive is **not in that principal's
`C_required`** — the public-side product is not in debt for the MNPI it may
not see (`D-IMPL-105`; `MWE-G20`). `S = 1`.

| component | may be absent? | contribution | behavior when absent |
|---|---|---|---|
| `issuer` | no | mandatory — no other member exists without it | no issuer row → the empty fabric is served as computed-empty, never refused (`MWE-G16`) |
| `family` | yes | none (optional) | served without |
| `deal_engagements` / `interactions` (banker) | yes | `C` drops one required class each | served with elevated `D_c`; an issuer with no engagement at the instant is honest thin data |
| `research` (banker, analyst) | yes | `C` drops one class | `research: []`, elevated `D_c` |
| `positions` (trader) | yes | `C` drops one class; `F` decays | served with elevated `D_c`; at `T0` every position is in the future of the boundary and absent |

Profile `[TBC — this build]`: forced-LLM 0.60, fail-closed 0.95 (cp-13's
values) — checked against the default `debt_tolerance` so that no single
optional class refuses the product on its own.

### E.3 Materialization posture

**Derived on demand, per principal, always.** A materialized product would be
cached per principal per wall state, and a cache-key error here is a wall
breach rather than a stale read — the one product in the catalog where the
*risk* of materialization rules it out. The SDK has no product cache; the
cache key, stated for the record: tenant · schema · `plan_id` · snapshot ·
`asked_at` · `known_as_of` · principal · subject.

### E.4 Supersession triggers

| trigger | scope | mechanism | demonstrable here |
|---|---|---|---|
| Wall crossing recorded | local (the principal's products on that issuer) | a new crossing changes `E` for that principal; the register boundary on the issuer entity, reason `wall-crossing`, source the node id | yes — `TW` vs `T1` |
| Restricted-list update | local | the list is a mandatory input read first (`MWE-G09`); on this rung a restriction in force does not narrow `E` (§D.3 step 1.5), so a row's `added_date`/`removed_date` is declared as a trigger and not demonstrated as a supersession | **declared, not demonstrated** — no gate claims a restricted-list effect |
| Embargo expiry | local | the note's window ends | **no** — every embargoed note stays `draft` after `embargo_until` in this estate; declared, not demonstrable (§C.4 trap 3) |
| Reg FD disclosure — classification-member change (outcome B) | cascading to `ib-opportunity-synthesis` | the dated public-filed event on the issuer (§D.3 step 1.6) and an `EntityInvalidation` on the issuer at `2026-07-03`, reason `reg-fd-disclosure`, source `REGFD-000`, recorded through `ControlPlaneInvalidationSink`; the gate refuses re-serving a prior determination that touched the issuer | yes for the member change (`MWE-G10`); the register half `[TBC — this build]` (`MWE-G11`, §F.2 row 6) |

Re-derivation is lazy: invalidate for the next request, never re-materialize.

### E.5 The expiry and its refusals

`expires_at = decided_at + 3,600 s`, `decided_at = asked_at`. Two refusals:
the TTL-bounds gate refuses an `expires_at` beyond the class ceiling; and a
dependency-invalidation boundary between the product's state and its
decision refuses re-serve. The past-instant trap of §B.4 is served, not
refused, and is disclosed where an operator will look for it (§B.1, §B.4,
and the operate prose of §G).

## F · Source binding and readiness

### F.1 Element readiness

| element | interface · cadence | available today | gap owner · blocker |
|---|---|---|---|
| issuer, family | PostgreSQL / Fluree read · snapshot | yes | — |
| deals, interactions, positions | PostgreSQL read · snapshot | yes | — |
| research notes | MongoDB read · snapshot | yes (lexical only; embeddings unused) | — |
| wall crossings, embargo windows, Reg FD event | Fluree literal read · snapshot | yes | ccf-dataprep · which records `REGFD-000` discloses (§F.2 row 1) |
| restricted list | SQLite file read · snapshot | yes | — |
| projection plans, principals | PostgreSQL read · snapshot | yes | — |
| blackout windows | — | **no** | dropped (§C.4 trap 6) |
| personal-account-dealing restrictions | — | **no** | ccf-dataprep (§F.2 row 10) |

### F.2 Every `[TBC]` in this document, with an owner

Stated as a roster. No spec passes review with an unowned gap.

| # | term | owner | what was asked |
|---|---|---|---|
| 1 | ~~which exact records or content `REGFD-000` releases~~ **ANSWERED 2026-09-20 by ccf-dataprep: none — outcome B** | ccf-dataprep | `contrib/ccf-dataprep/cp-17-regfd-000-designates-nothing-outcome-b` (`measurement`, `reproduce_with` stated): a dated label from Wave 7 (`7a37a4d`), no record id anywhere in source or store, the description dropped at load; zero incoming edges, literals or referencing columns, each with a control. The hold's release condition is met; the build begins on Dave's GO. Closed |
| 2 | the Similarity query literal and `minimum_score_percent` | this build | illustrative, drawn from the intent vocabulary; disclosed in the artifact |
| 3 | the research top-k in Π | this build | proposed 3 |
| 4 | the class TTL ceiling | this build | proposed 14,400 s |
| 5 | the debt profile thresholds | this build | proposed 0.60 / 0.95 |
| 6 | whether the invalidation register's boundary is exercised on a per-request fabric (`MWE-G11`) | this build | the mechanism is direction-agnostic; what a "prior determination" is when every question boots its own fabric is the measurement |
| 7 | p95 budgets per step and the total against 3,000 ms | this build (Gate 2) | — |
| 8 | per-call absolute cost | this build | no billing meter; not invented |
| 9 | the ontology IRIs for engagement, interaction, position and research note | this build | OMG Commons / FIBO terms to be bound before registration |
| 10 | ~~whether a personal-account-dealing table exists~~ **ANSWERED 2026-09-20 by ccf-dataprep: no** | ccf-dataprep | none in any of the four stores (matcher with a positive control; 116 base tables and 2 views, 8 SQLite tables, 6 collections, 95 types); the binding stays unbound; nothing invented. Closed |
| 11 | ~~whether a jurisdictional information-barrier rule belongs on this rung~~ **RULED 2026-09-20: no** | Dave | the jurisdiction table is evidence and context only; no jurisdiction-based filtering or admission logic; a displayed jurisdiction is labeled non-governing context (§C.4 trap 10). Closed |
| 12 | ~~the HTTP door in scope for `MWE-G15`~~ **RULED 2026-09-20: yes** | Dave | HTTP proves the one behavior MCP cannot expose — a caller requesting a role it is not entitled to receives a governed refusal, never a silent downgrade — with the same three entitled principals plus the fourth ungranted one; not a new product path (§D.1). Closed |
| 13 | whether a missing plan row can be refused at open rather than at serve | this build | §D.3 step 1.3 |
| 14 | whether the plan-artifact pin in `policy_bundle_versions` can be scoped to the served principal's own plan, or pins the whole `policy` section | this build | §B.1 lineage; §D.3 steps 1.7 and 7; `MWE-G13`, `MWE-G19` — if it cannot be scoped, the three plan versions are pinned in every record and that is recorded as a finding against `MWE-G19`, never hidden |
| 15 | ~~a coverage-validator manifest for `mnpi-wall-enforcement`~~ **DONE 2026-09-20 by ccf-dataprep** (ccf_dataprep `6a8fb4c`) | Dave | `contrib/ccf-dataprep/cp-17-coverage-manifest-added-and-two-real-gaps`: `uv run validators/spec_coverage.py --product mnpi-wall-enforcement` → 15 of 15 catalog rows accounted for (11 probed clean · 2 covered by `conditions.py` · 2 GAP), exit 1 by design because a GAP is a real absence; 17 paired falsification tests. **The spec cites the instrument** (§0.2, §F.3). Closed |

### F.3 Access path, identifiers, history, text and volumetrics

`ccf_environment.yaml` names five sources by env name, values never in the
tree: `control_room` (`CCF_CP_17_SQLITE_PATH`), `deal_relational`
(`CCF_CP_17_POSTGRES_DSN`, `_SCHEMA` → `ccf_v2`), `wall_graph`
(`CCF_CP_17_FLUREE_URL`, `_LEDGER` → `fibo-v2`), `research_documents`
(`CCF_CP_17_MONGO_URI`, `_DB` → `fibo_v2`), and the door's credentials and
advertised URLs. Read-only; the v2 namespaces are declared only in
`ccf_dataprep/ccf/config.py` (never derived from `.env`, which names v1). The
identifier exists end to end (§C.3). History depth: the estate is a snapshot
with no deltas; the two-clock wall state is the only history the product
reconstructs, from literals. Text-source boundary: research note bodies are
the only text the product reads; filings are not read. **First-build
volumetrics:** ten issuers, four restricted, four crossings for one
principal, eleven MNPI-bearing deals, eighteen MNPI-bearing interactions,
nine drafts on two issuers, one Reg FD event, ten positions — every gate in
§G.1 has a subject to act on without widening the sample, with the two
degeneracies of §C.4 traps 3 and 5 disclosed rather than repaired.
Reproduce every figure with read-only SQL over `ccf_v2`, a SPARQL `SELECT …
FROM <fibo-v2>` over the three types, a `find` over `research_note`, and
`sqlite3 -readonly` over `restricted_list` — the queries are the ones this
document was written from and are committed with the example.

### F.4 Recorded findings — not `[TBC]`, because none of them needs a decision to build

- **`CP17-F-01` (predicted, to be measured under the DX rubric).** The
  per-principal envelope is applied at the acquisition seam from the
  credential; the Policy operator's per-principal input is not expressible
  on the operator. Second instance after cp-13-canonical (`A2`); counts of
  plumbing LOC, hand-built objects and private symbols recorded at close.
- **`CP17-F-02`.** The supervisor's side is out of scope on this rung, so
  Gate-0 row 47 remains a backlog record: no wall-decision attribute is
  written into the fabric or record of a principal not entitled to it
  (ruled), and the estate declares no supervisor principal or plan, so a
  separately entitled supervisor product — whose own plan could admit the
  broader evidence — is not built here. A supervisor reconstructs a
  decision from the record's own pins (dimension 2 policy and plan versions,
  dimension 4 role) under its own credential.
- **`CP17-F-03`.** The containment / no-disclosure gate is the fourth
  example-level writing of one (§D.7); §H threshold reached — a backlog
  record, not an SDK change in this rung.
- **`CP17-F-04`.** The vault's ranking-difference number degenerates to
  containment on this estate (§C.4 trap 3) and is structurally zero under
  the reference index without a relative cutoff; the rung measures it with a
  Π-side top-k and says so.
- **`CP17-F-05`.** The restricted list, wall state and embargo windows have
  no λ_c row because they are envelope inputs; their currency (list
  `added_date` 2026-04 … 07, crossings recorded 2026-02 … 03) is disclosed
  against the pinned instants.
- **`CP17-F-06`.** The replay environment for a paved product is still
  hand-assembled (`CP06C-F-01`, inherited; recipe-not-seam by ruling).
- **`CP17-F-07`.** Requesting a perspective is HTTP-only; over MCP the
  channel does not exist. Disclosed, not repaired.

## G · Operate and govern

Accountable owner: the SDK examples maintainer (role). Service objectives:
p95 `[TBC — this build]` against 3,000 ms; one issuer per call; payload
bounded by the issuer's records (largest: 45 interactions, 5 notes).
Degradation contract: `control-room` is **mandatory** (unreachable ⇒ refused,
source class named, `MWE-G09`); a subject with no issuer row is served
computed-empty, never refused (`MWE-G16`); every other class degrades with
debt. Observability: per-operator latency, `D_c`
by role, gate refusals by gate, entitlement denials by principal, the
assertion-clock disagreements. Retention: the replay record is the record of
record for every wall decision, served or refused. **Operator note:** a
question at a past `asked_at` under the `from_decision` anchor serves with
an `expires_at` already elapsed by the wall clock (§B.4) — disclosed, not
repaired. Service objectives also carry per-call absolute cost as
`[TBC — this build]` (no billing meter; §F.2 row 8). Lifecycle: `draft` at
Gate 1; `in-build` on Dave's GO — the hold's release condition (§F.2 row 1)
was met on 2026-09-20 by ccf-dataprep's answer, outcome B; `certified` at
Gate 2.

### G.1 Product gates

The acceptance authority for every gate is **this clause** (`D-IMPL-326`).
Each id is claimed by exactly one executing test in the example's
`tests/`; a gate no test claims is red — with one declared exception,
`MWE-G11`, which may instead be recorded as its `[TBC]` resolves (§F.2 row
6). Every gate is directional,
structural or relational; **none pins a count or a date.**

| id | property | shape |
|---|---|---|
| `MWE-G01` | three credentials, one question, one instant: three content addresses; one schema, one `plan_id`, one operator set | relational |
| `MWE-G02` | classification containment: no served `classification` outside the principal's permitted set; no MNPI-bearing identifier in any byte of a public-side vessel | structural |
| `MWE-G03` | vocabulary containment: every served edge type is in the principal's `permitted_edge_types` — the declared gate, with its refusal branch exercised by minting one extra edge | structural + sabotage |
| `MWE-G04` | no disclosure: the payload's member set is the role's and is identical for SP Plus at `T1` and at an instant before any of its MNPI-bearing records existed (§A.2 step 6) | relational |
| `MWE-G05` | the served plan lists `policy.principal-subgraph` first, before `similarity`, `temporal` and `traversal` | structural |
| `MWE-G06` | the Policy operator is live: a claim injected with a classification outside the vocabulary is absent from the served product, together with the edge minted to it (`GQ-16` endpoint closure) | sabotage |
| `MWE-G07` | policy before similarity: a draft claim injected into the analyst's per-request fabric is absent from the Similarity operator's candidates and from the served product; on SP Plus, which has no drafts, the banker's and the analyst's ranked sets are identical and the vault's ranking-difference number is recorded as zero by construction | sabotage + relational |
| `MWE-G08` | bitemporal wall: SP Plus, banker, `asked_at = TW`: `known_as_of = TW` serves no MNPI engagement, `known_as_of` after `WALL-000.assertedAt` serves it; two addresses | directional |
| `MWE-G09` | the control room first: an unreachable departmental store refuses the product for every principal with the source class named | sabotage |
| `MWE-G10` | Reg FD as a classification-member change (outcome B, §C.4 trap 5): SP Plus, every principal — the issuer's `reg_fd_disclosure` member is `null` at `T0` and carries the event at `T1`; outside that member the analyst's and the trader's vessels are byte-equal across the two instants, so no engagement content is admitted on the strength of the label | directional |
| `MWE-G11` | `[TBC — this build]` the Reg FD boundary in the invalidation register refuses re-serving a determination that touched the issuer before it | structural |
| `MWE-G12` | supersede-only in a served product: `F = 1` for the banker's and the analyst's products; for the trader `F` orders American Healthcare REIT ≥ SP Plus ≥ BGC at `T1` by position `as_of` — the ordering, never the number; the two other issuers are freshness comparison subjects only (§C.4 trap 7), not wall subjects | directional |
| `MWE-G13` | one plan, three roles: dimension 5 `plan_id` equal across the three records, dimension 4 `role` distinct; the served principal's own plan artifact version pinned in `policy_bundle_versions` | relational |
| `MWE-G14` | the unconfigured principal (`PRIN-KYC-004`'s credential) is refused with the deny audited, and the refusal is observationally the same as a nonexistent product at minimal disclosure | relational |
| `MWE-G15` | requested role over HTTP (in scope by ruling): each of the three entitled credentials with a `?role=` outside its own grant is refused by typed code, never downgraded; each with its own role served, byte-equal to the MCP vessel for the same question; the ungranted credential is refused as unconfigured on HTTP as on MCP | relational |
| `MWE-G16` | **A6, load-bearing — the existence oracle.** For an unentitled principal, a subject whose admissible claims Policy removes entirely is observationally indistinguishable on the paved serve path from a nonexistent subject — and the comparator is a subject whose per-request fabric holds no claims, **served** on the same path (vessel and computed-empty finding path-for-path equal), never a refusal. A LEI with no issuer row yields that same served outcome under each of the three entitled credentials (the ungranted credential is refused at the door before any subject is resolved, `MWE-G14`). **Positive control kept:** the same instrument distinguishes a fabric holding restricted claims from an empty fabric *before* Policy removes the restricted content, and distinguishes an entitled, assembled subject after it. The gate asserts nothing about whether the fabric holds the restricted entity — that is not the property (§0.1 claim 3). Rests on `tests/products/test_policy_emptied_view_disclosure.py` (measured 2026-09-20) and re-executes on this rung's serve path | relational + positive control |
| `MWE-G17` | replay: each principal's product rebuilds byte for byte from its record; the refused determination reconstructs with its cause | structural |
| `MWE-G18` | determinism: two runs agree; door and in-process agree | structural |
| `MWE-G19` | a principal's served vessel **and its replay record** carry no wall-decision input the principal is not entitled to — no crossing id, no restriction row, no other principal's plan; the record still replays (`MWE-G17`) | structural |
| `MWE-G20` | debt is entitlement-neutral: the analyst's `C_required` excludes the engagement classes; its `D_c` on SP Plus at `T1` is not raised by the MNPI it may not see | relational |
| `MWE-G21` | the Policy Blind control (§A.2 step 7) differs from the served analyst vessel | relational |

### G.2 Acceptance criteria

Each specific to this product, independently verifiable, phrased to fail.

1. The three products serve through **one** `open_door` with exactly the
   three overrides; no hand-written door, no `build_governed_resolver`, no
   second registry; the tree has the two-region shape of cp-13-canonical
   (boot / answer). The HTTP door of §D.1 (`create_app(auth=)` over the same
   opened product and token map) exercises the role-request behavior by
   ruling and is not a second product path.
2. `MWE-G01` through `MWE-G21` each claimed by one executing test, with
   `MWE-G11` claimed or recorded as its `[TBC]` resolves and `MWE-G10`
   executed in its outcome-B form (§F.2 row 1, answered).
3. The counterfactual acceptance test of §A.2 runs and fails when the wall
   is made cosmetic (the Policy Blind control).
4. Every step in §D.2 has a witness in `artifacts/assembly-recipe.yaml`,
   set-equal in both directions, each observed on a completed run.
5. The served plan names all four operator categories; lineage strict
   equality holds in both directions.
6. No `.py` file in the tree carries a domain value: the three plans, the
   classification vocabulary, the λ_c table, the query literal and the
   thresholds live in `ccf_config.yaml` and `artifacts/`.
7. The illustrative calibration is disclosed in the artifact, the README
   and this document, with the measurement that forced it.
8. Every `[TBC]` in §F.2 is closed, carried with its owner, or converted to
   a finding — never silently resolved.
9. Nothing seeds the curated estate; every question boots a per-request
   scratch fabric; the departmental file is opened read-only.
10. The Reg FD disclosed set (§C.4 trap 5) was answered by ccf-dataprep
    through the vault on 2026-09-20 — none exists; outcome B is executed and
    cites their measurement; no data is engineered to reach A.
11. The close report keeps the six sections of
    `docs/EXAMPLE-EVALUATION-CRITERIA.md` §K apart.
12. **The DX rubric is recorded** (Gate-0 §5.0; Dave, 2026-09-20) for the
    three batch-1 patterns — the credential-derived envelope, several
    principals through one door, policy-before-similarity over a corpus —
    on the eight counts: domain LOC; plumbing LOC; copied patterns;
    hand-built Control Plane / runtime objects (predicted 3 for the door);
    private symbols; configuration duplication (predicted 1: the door's
    derived grant beside the tenant policy); undocumented concepts
    (predicted: the latest-wins ordering, the served `computed_empty`
    channel, `GQ-16`); whether an AI coding agent could generate the tree
    from this document plus public SDK guidance. Each pattern classified
    under the four classes. **This rubric is recorded for the A2 measurement
    Dave ruled (the third instance, after AML); nothing beyond this rung's
    specification is authorized or in progress under the hold.**
13. Jurisdiction is never a filter or an admission rule anywhere in the
    tree; the issuer's `legal_jurisdiction` member is labeled non-governing
    context wherever it is displayed.

**Implementation hold (Dave, 2026-09-20) — release condition met.** §F.2
row 1 was answered by ccf-dataprep on 2026-09-20 (outcome B). Rows 1, 10,
11 and 12 are closed; row 15 is Dave's and non-blocking. The build begins on
Dave's GO and not on this document's authority.

### G.3 Catalog contribution

**What this product proves that nothing earlier proved.** Several
credentialed principals through one shipped door; an operator-bounding set
sourced from the credential rather than the effective request; all four
operator categories on one domain rung with Similarity behind Policy; a
supersede-only class in a served product beside a curve class; a Reg FD
supersession as a classification-member change (outcome B, §C.4 trap 5); the
departmental SQLite store
as a source read first; the
two-clock question answered from a control room's own record. It is the
first rung whose close report carries the DX rubric, and the second instance
of the envelope plumbing, counted under Dave's A2 ruling and not
generalized; no SDK review is proceeding.

**What it deliberately does not prove.** A per-principal traversal
vocabulary on one plan (reification is the ruled realization); a distinct
`plan_id` per perspective; a requested perspective over MCP; vector
similarity; a content-widening supersession (outcome A, retired — the data
holds no disclosed set); the embargo-expiry trigger; blackout windows; per-issuer market data (none exists — §C.4 trap 11); a jurisdictional
rule (ruled off this rung) or a personal-account-dealing binding; a
supervisor's separately entitled product; any A2A or peering route (the three
consumers are principals at a door — per the Gate-0 direction, A2A is
outside the SDK contract); a durable authorization event stream beyond the
replay record. None of these is a tier boundary read as an oversight; each
is named so a reviewer does not mistake it for one.
