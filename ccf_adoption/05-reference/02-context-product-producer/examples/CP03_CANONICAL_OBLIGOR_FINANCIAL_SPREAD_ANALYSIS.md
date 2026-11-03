> **Current operations:** use [the refreshed implementation walkthrough](CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD.md) and Fluree **4.2.4** where required. The embedded specification remains historical evidence at its stated pin.

> **Reading copy:** [HTML edition](CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD_ANALYSIS.html), with rendered tables and sources included in this file.

# CP-03 — Obligor Financial Spread — Canonical — Analysis

**Audience:** banking SME and Information Architect. **Purpose:** reconstruct the journey from the business problem to this example’s final specification.

**Final specification:** `examples/cp-03-canonical-obligor-financial-spread/spec/CP-SPEC-003C_Obligor_Financial_Spread_Canonical.md`, read directly from `drcastillo/ccf_code` at `37ac3055fd64ed64d78c6fd5555d79e451859153`. [Open the included final spec](#source-spec). Its recorded decisions, corrections, findings and placeholders are the destination of this walkthrough. The [Standard v0.3](#source-standard) supplies the template and the [generation recipe](#source-recipe) explains the ownership and evidence sequence.

The figures below are the final spec’s teaching-estate measurements or declared design values. They are not new runtime measurements. Once the design journey is understood, continue with the [implementation walkthrough](#source-implementation).

## Start with a comparable financial spread

A credit analyst or credit-memo assembler needs one obligor's financial figures arranged by period, with a declared reporting basis and comparable peers. Reading facts directly can compare the obligor's Q3 with a peer's Q2 simply because both filings arrived in the same week. It can also mistake another accession for a restatement or turn an absent financial line into zero. Final-spec §A calls this failure `context-starved`.

The SME first defines what makes figures comparable: the period they describe, the reporting basis, the filing that asserted them and whether a later filing changed their value. The Information Architect turns those distinctions into the period key, fact-cell identity, restatement selection and filing lineage. The completed target is **CP-SPEC-003C**, the canonical successor, not the frozen CP-SPEC-003 specimen.

## Establish the contract and consumer — Standard §0–§B → final §0–§B

CP-14 requires the `credit-risk.spread` class on a compatible major lane. The final canonical spec serves **1.1.0**, satisfying the consumer's 1.0.0 floor while identifying a distinct lane member. It preserves the spreading semantics and makes them available through a governed canonical producer.

| element | value |
|---|---|
| schema | `credit-risk.spread` @ `1.1.0` (`CP-SPEC-014` floor `1.0.0`, same major) |
| subject | the obligor's LEI, as `ProductRequest.subject` |
| intent | `annual-review` — the declared discovery set; judged, never an argument |
| freshness | `filing-cadence` |
| TTL | 30 days, **declared** `from_entity_freshness` on the freshest filing in the payload; **served** `expires_at` runs from that filing and the contract records it as `ttl_anchor_at` (since `D-IMPL-341`, 2026-09-18; the gap was `CP03C-F-01`). The SDK's TTL gate refuses an expired spread before the declared product gate runs; that gate keeps its no-obligor half and cross-checks the payload's anchor member |
| assembly mode | 1 — algorithmic |
| operators | `policy.principal-subgraph`, and no other |
| lineage | graph-supplied; every reported line carries its own `accession`, `filed_date`, `form`, `basis_applied`, `restated`, `restatement_class` |
| debt | `D_c = 1 − F·C·S`, one observation per column typed by its signal class and aged from its filing (`decay_basis: valid-from`), `C` the evaluable fraction of declared lines, `S = 1` structurally |

The subject is the obligor LEI. `annual-review` is the declared intent judged by governance; neither `intent` nor `lei` is a shadow argument. That distinction matters when translating the banking request into a request contract: the caller selects an identity and purpose before supplying the product's measures and bounds.

| parameter | type | default | domain | note |
|---|---|---|---|---|
| `periods` | integer | 8 | ≥ 1 | distinct period ends, newest first |
| `basis` | string | `as-reported` | `as-reported` \| `latest-restated` | selects WITHIN a cell |
| `include_peers` | boolean | true | — | cohort at identical `period_end` |
| `peer_basis` | string | `sic` | `sic` | only what is implemented is declared (`CP03C-F-03`) |
| `debt_tolerance` | number | — | — | **required**, the caller's ceiling |
| `jurisdictions` | array of string | the default perspective's expanded grant | — | reaches the policy operator through the declared binding |
| `as_of` | string | — | — | declared and refused, `not-supported-at-tier` |

The SME decides whether the question asks for originally reported or latest-restated figures. The architect implements that choice **within a fact cell**, using `basis`, and keeps the period count separate. Peer comparison uses the obligor's period ends and the supported SIC basis. An unsupported basis, missing required tolerance or inert `as_of` produces an explicit governed refusal rather than a guessed interpretation.

## Make source meaning precise — Standard §C → final §C

The final binding uses seven PostgreSQL `ccf_v2` tables: `financial_fact`, `crosswalk`, `legal_entity`, `filing_profile`, `peer_fact`, `peer_entity` and `principal_jurisdiction`. Three reads provide crosswalk resolution, windowed fact cells and period-aligned cohort evidence. Resolve the obligor through the crosswalk rather than assuming `financial_fact.cik` supplies the authoritative identity join.

Four domain distinctions produce the final design. **Accession multiplicity is not restatement**: a changed value across accessions on the declared identity key is the relevant evidence. **Period end is not the whole period key**: `(period_end, fiscal_period)` keeps FY and Q1 distinct when they share a date. **Filing date is not comparability**: peer facts join on `period_end`. **Absence is a word, never zero**: a missing declared line remains `NOT_EVALUABLE`.

The final spec adds a fifth implementation finding with direct analytical consequences. A shared scratch root once reused a fabric containing the preceding obligor. The corrected specification requires a fresh fabric per run and projection scoped to the request's subject. Otherwise a correct spreading formula can still answer for the wrong customer.

## Specify a governed derivation — Standard §D → final §D

The architect separates **boot, acquire and govern**. Acquisition reads the sources and submits dated claims through the single writer. One `build_governed_resolver` owns the door, operator, projection, gates, debt and replay path. There is no manually assembled parallel gate/record/serve sequence.

The spread is represented as fabric state: obligor, period, line and cohort-statistic entities, each dated from the filing that asserted it. Projection and debt read that admitted view. Putting a completed spread only into a payload would prevent the evidence and scorer from describing the same facts.

The final TTL is **30 days from the freshest filing in the payload**. The served contract records `ttl_anchor_at`; the dated D-IMPL-341 amendment closes the earlier anchor gap. The SDK TTL gate rejects expiry first, while the declared product predicate still handles the no-obligor case and cross-checks its payload anchor. This is a recorded correction in the final spec, not a gap to reintroduce from an older specimen.

A consumer-facing refusal is data with a replay reference. Missing or suppressed obligors, disallowed intent, invalid request, excess debt and an expired spread have governed outcomes. The MCP door and in-process route must produce the same content address for the same question. Source acquisition, policy and projection therefore have to preserve the same meaning across both routes.

## Explain the debt before choosing a tolerance — Standard §E → final §A.2 and §E

Annual columns age against approximately 365 days and quarterly columns against 90 days, from **their own filing dates** through `decay_basis: valid-from`. Ingestion time would make old filings look newly fresh. C is the evaluable fraction of declared lines, and S is structurally one in this specification.

The recorded CP-14 demonstration is instructive: thirteen columns at eight distinct period ends, 119 non-evaluable lines out of 234, and `D_c = 0.8433`. The freshest filing is within the 30-day window, but the spread is withheld at CP-14's 0.25 tolerance. This separates **unexpired product validity** from **acceptable evidence quality**. The specification does not tune freshness or completeness to make the composite accept it. Opening tolerance changes fulfillment, not the assessed debt.

## Turn each decision into evidence — Standard §F–§G → final §F–§G

The environment companion identifies the read-only PostgreSQL source through variable names and explicit v2 namespace. Source bindings and source-backed time semantics remain part of the specification; connection secrets do not. The recorded findings retain the history of the now-corrected anchor and the per-run fabric issue.

The final spec provides **27 named acceptance gates**. They are included here because each is the concrete destination of a design decision, including cross-process acquisition and refusal behavior:

| Gate | Asserts |
|---|---|
| `OFC-G01` | a governed `ServedProduct` of the required class, on a `1.x` lane, at the CP-14 instant, byte-stable across two runs |
| `OFC-G02` | replay dimension 2 is a **superset** of product lineage; the operators invoked are exactly the one declared |
| `OFC-G03` | the spread **is fabric state** — every served period and line is a touched entity, and Π read the view |
| `OFC-G04` | every reported figure names the filing that asserted it, and the spread rests on more than one filing |
| `OFC-G05` | `D_c = 1 − F·C·S` over the view; `C` the evaluable fraction of declared lines; `F` below 1 because columns age from their filings |
| `OFC-G06` | a spread whose freshest filing is outside the declared window at the asked instant is refused — by the SDK's TTL gate first (`ttl-bounds`, since `D-IMPL-341`), and the product's own predicate still names the window on a candidate whose payload anchor lies outside it |
| `OFC-G07` | `expires_at` is anchored on the freshest filing, as declared, and `ttl_anchor_at` records it — live since `D-IMPL-341` (was quarantined evidence of `CP03C-F-01`) |
| `OFC-G08` | an obligor the principal may not see and one that does not exist refuse with one reason, one kind, one detail |
| `OFC-G09` | `intent` is judged on the declared discovery set, and the specimen's shadow argument is refused at contract construction |
| `OFC-G10` | `as_of`, an out-of-domain `peer_basis` and a missing `debt_tolerance` are refused as data, each with a record |
| `OFC-G11` | the caller's tolerance governs — withheld at CP-14's own ceiling, served wide open — and the debt does not move with it |
| `OFC-G12` | the basis changes a figure only where a later filing changed it, and selects within a cell, never across cells |
| `OFC-G13` | `shape_of` reads this tree as **canonical**, and no `build_replay_record` call exists |
| `OFC-G14` | the plan factory takes its operators only from `required` |
| `OFC-G15` | the frozen specimen is **untouched** and no specimen identity is reused |
| `OFC-G16` | the CP-14-shaped question is answered by the producer **in another process** and admitted under `provider-controls` |
| `OFC-G17` | the consumer process runs no producer assembler and holds no producer record |
| `OFC-G18` | the expected producer identity and tenant come from the registration — wrong id and wrong tenant refuse independently |
| `OFC-G19` | a lane the requirement does not admit is refused `version-incompatible`; an unoffered class is a wiring error before any socket |
| `OFC-G20` | no question argument becomes an address; an unresolvable subject is refused by the child's own gate — no fake child |
| `OFC-G21` | at CP-14's own tolerance the spread slot is withheld and the composite refuses on its required child |
| `OFC-G22` | a severed producer is a governed `producer-unavailable` refusal, not a fake child |
| `OFC-G23` | the door and the in-process run serve **one** content address |
| `OFC-G24` | a fresh fabric per run — two connections under one root name two files; an obligor served after another under one root hashes to its own address |
| `OFC-G25` | Π serves the subject's claims and **no other's** — two obligors in a view yield the subject's spread; only another's yields no obligor |
| `OFC-G26` | the dimension-two predicate **refuses** a record that no longer covers the lineage, and no SDK guard makes that state unreachable |
| `OFC-G27` | the fabric-state predicate **refuses** a payload-only representation, and no SDK guard makes that state unreachable |

The six closing acceptance criteria require a real governed product on the consumer's lane, absence of the specimen's two defects, fabric-backed claims and debt, the declared window, acquisition across the deployment boundary with negative controls, and an unchanged frozen specimen. The SME can thus trace period comparability and evidence sufficiency into tests; the architect can trace subject, policy, identity and producer boundaries into the same final artifact.


## Included source snapshots

Exact retrieved source texts, with their original historical statuses and internal links retained as source text. Tables quoted within the walkthrough come directly from the final spec; Markdown pipe escaping is normalized for display.

<a id="source-spec"></a>

<details>
<summary>Final example specification — ccf_code@37ac3055</summary>

Path: `examples/cp-03-canonical-obligor-financial-spread/spec/CP-SPEC-003C_Obligor_Financial_Spread_Canonical.md`

``````text
---
product: credit-risk.spread.v1
standard: v0-3
owner: vault
sdk_spec: cp-03-canonical
tier: 1
cost_band: "×1 — three SELECTs per question, no LLM"
assembly_mode: 1
capability_classes: [relational, in-memory]
prerequisites: [counterparty-reference-snapshot]
topic: context-products
title: Obligor Financial Spread (canonical) — Context Product Specification
generated: '2026-09-14'
---

# Obligor Financial Spread (canonical) — Context Product Specification

**`CP-SPEC-003C` · the canonical rung-3 tree · Tier 1 · `credit-risk.spread` @ `1.1.0`**
**PostgreSQL `ccf_v2` — `financial_fact`, `crosswalk`, `legal_entity`, `filing_profile`, `peer_fact`, `peer_entity`, `principal_jurisdiction` — read-only**

> One obligor to a typed, period-aligned financial spread in which every figure
> names the period it describes, the filing that asserted it, and whether a
> later filing changed it — **written the way an adopter should write a product
> on the SDK as it ships today, and serving the class `CP-SPEC-014` requires.**

## 0 · What this document is

**This specification governs a SUCCESSOR, and the succession is disclosed
rather than glossed.** `CP14-F-22` (Dave, 2026-09-14) ordered a canonical
governed producer of `credit-risk.spread` on the `cp-04-canonical` sibling
pattern, because the frozen rung-3 specimen `examples/cp-03-obligor-financial-
spread` does not serve on the current SDK: its request contract declares
`intent` under `arguments.properties` (refused at contract construction,
`D-IMPL-264` D-01) and its spine calls `build_replay_record` with no resolution
binding (`D-IMPL-264` D-10). Thirteen of its seventeen tests are quarantined
`xfail(strict=True)` for exactly those two mechanisms — the complete quarantined
population, measured by AST before this tree was written, and both are absent
here by construction (§D.2, `OFC-G09`, `OFC-G13`).

**It is producer substitution, not a renamed class.** The product identity is
unchanged: `credit-risk.spread`, on the major lane `CP-SPEC-014` §B.7 pins at a
`1.0.0` floor. This tree serves `1.1.0` — compatible with the floor, and a
different lane member from the specimen's `1.0.0` so two deployments never share
one lane.

**It cites `CP-SPEC-003` nowhere as an authority**, on the `cp-04-canonical`
ruling (`D-IMPL-327`). The frozen specimen's specification governs the frozen
specimen. The business meaning it fixed — the crosswalk, the identity key, the
basis, the period key, the peer join, the word for absence — is preserved here
and re-stated in this document's own words, because a successor governed by a
document nobody may edit would be governed by nothing.

### 0.1 What this tree teaches, and what it does not

It teaches **per-attribute temporal validity as fabric state**, on the
canonical producer shape. Five things, and they are the whole subject:

1. **boot / acquire / govern** as three regions, with the SDK owning the third
   — the door, the operator, Π, the three L6 gates, the product's own declared
   gate, the replay record and the delivery in one `build_governed_resolver`.
2. **The spread IS the graph.** One entity per obligor, per period, per line
   and per cohort statistic, each dated from the filing that asserted it; Π
   reads the view and nothing around it; the debt reading dates each column
   from the graph.
3. **`intent` is a governed axis**, declared once on
   `product_class.discovery.intents` and judged there — never an argument.
4. **The grant reaches the operator as request state** through a declared
   binding (`permitted_classifications: {source: effective_request}`), never
   as a value written over a resolved artifact.
5. **A declared window held by the product's own gate**, and the SDK gap
   beside it (`CP03C-F-01`) raised rather than papered over.

It does **not** re-derive the spreading domain. The tag map, the ratio
definitions, the restatement rule and the λ_c values are the specimen's,
carried forward byte for byte in `artifacts/` and `ccf_config.yaml`.

### 0.2 Placeholder discipline

No figure in this document is a promise. Every number in §A.2 and §E is a
measurement taken on 2026-09-14 against the live `ccf_v2` estate at the CP-14
instant, reproducible with `make example-cp-03-canonical`, and **no gate in §G.1
pins one of them**.

### 0.3 Front matter

`tier: 1` and `assembly_mode: 1`: three `SELECT`s, an arithmetic interpreter
over a declared convention, and a shaping. No LLM is reachable from any step.

### 0.4 The four-question test

*Who asks?* A credit analyst, or a composite such as `CP-SPEC-014`, about one
obligor at one instant. *What changes the answer?* The obligor, the instant,
the basis, the period count, the calling principal's grant. *What does a
`SELECT` not give you?* The debt in force, the content address, the record that
authorized it, and a refusal that names its gate. *What is refused?* An obligor
the principal may not see, a spread outside its declared window, an intent the
class does not serve, a debt above the caller's tolerance.

## A · Decision frame

### A.1 Counterfactual — `context-starved`

A memo writer reading `financial_fact` directly gets figures with no period
key, no basis, no restatement marking and no filing lineage — and will compare
a Q3 to a peer's Q2 because the two filed the same week.

### A.2 The uncomfortable conclusion, preserved

Measured at the CP-14 instant `2026-09-07T12:00:00+00:00`, tolerance wide open,
for the demonstration obligor (BGC Group, Inc., on `CP-SPEC-014`'s roster):

| | |
|---|---|
| columns served | 13 (8 distinct period ends; `FY` and quarterly columns are never collapsed) |
| freshest filing in the payload | 2026-08-10 — 28 days before the instant, inside the 30-day window |
| lines `NOT_EVALUABLE` | 119 of 234 — the filer files none of several declared tags |
| `F · C · S` | 0.3189 · 0.4915 · 1 |
| `D_c` | **0.8433 — `fail_closed`** |
| at `CP-SPEC-014`'s own tolerance (0.25) | **withheld, `tolerance-exceeded`** |
| peer cohort | 14 peers in SIC 6200 at the obligor's own period ends |

Under the declared 30-day window, **three of the estate's fifty obligors** can
be served at that instant, and **two of `CP-SPEC-014`'s twenty** (BGC Group,
B&G Foods). Nothing here was tuned to change that (`CP14-F-22` §8); it is the
count `CP14-F-22` said rung 3 was to measure.

### A.3 A refusal is an answer

Every "no" this product says is returned as data with a replay reference —
the product's own gate, the contract, the intent set, the tolerance. Nothing
raises for a question that merely has no answer.

## B · Contract

### B.1 The nine elements

| element | value |
|---|---|
| schema | `credit-risk.spread` @ `1.1.0` (`CP-SPEC-014` floor `1.0.0`, same major) |
| subject | the obligor's LEI, as `ProductRequest.subject` |
| intent | `annual-review` — the declared discovery set; judged, never an argument |
| freshness | `filing-cadence` |
| TTL | 30 days, **declared** `from_entity_freshness` on the freshest filing in the payload; **served** `expires_at` runs from that filing and the contract records it as `ttl_anchor_at` (since `D-IMPL-341`, 2026-09-18; the gap was `CP03C-F-01`). The SDK's TTL gate refuses an expired spread before the declared product gate runs; that gate keeps its no-obligor half and cross-checks the payload's anchor member |
| assembly mode | 1 — algorithmic |
| operators | `policy.principal-subgraph`, and no other |
| lineage | graph-supplied; every reported line carries its own `accession`, `filed_date`, `form`, `basis_applied`, `restated`, `restatement_class` |
| debt | `D_c = 1 − F·C·S`, one observation per column typed by its signal class and aged from its filing (`decay_basis: valid-from`), `C` the evaluable fraction of declared lines, `S = 1` structurally |

### B.2 Request parameter surface

| parameter | type | default | domain | note |
|---|---|---|---|---|
| `periods` | integer | 8 | ≥ 1 | distinct period ends, newest first |
| `basis` | string | `as-reported` | `as-reported` \| `latest-restated` | selects WITHIN a cell |
| `include_peers` | boolean | true | — | cohort at identical `period_end` |
| `peer_basis` | string | `sic` | `sic` | only what is implemented is declared (`CP03C-F-03`) |
| `debt_tolerance` | number | — | — | **required**, the caller's ceiling |
| `jurisdictions` | array of string | the default perspective's expanded grant | — | reaches the policy operator through the declared binding |
| `as_of` | string | — | — | declared and refused, `not-supported-at-tier` |

`intent` is **not** a parameter. `lei` is **not** a parameter: it is the subject.

## C · Data catalog

One store, seven tables, three `SELECT`s per question: resolution through the
crosswalk (never `financial_fact.cik`); one windowed read of every fact-cell for
every period, the partition built from `artifacts/restatement.yaml`'s identity
key; one cohort read at the obligor's own period ends, joined on `period_end`
and never on `filed_date`.

### C.1 The traps, all load-bearing

1. **Accession multiplicity is not restatement.** A restatement is a distinct
   value across accessions on the estate's own identity key.
2. **A period end is not a period.** `(period_end, fiscal_period)` is the
   column key; a non-December filer's `2026-03-31` carries both `FY` and `Q1`.
3. **Filing date is not comparability.** Peers match at identical
   `period_end`, structurally.
4. **Absence is a word, never a zero.**
5. **A shared scratch root is not a shared fabric.** Measured while building
   the door (`CP03C-F-02`): two questions under one root booted one SQLite
   file, and the second question's view held the first obligor. The fabric
   path is per run, and Π is scoped to the request's subject.

## D · Assembly recipe

### D.1 Client call

`deployment.request(lei=…, asked_at=…, debt_tolerance=…)` →
`produce.assemble_and_serve(asked=…, root=…)` → `Assembled | RefusalEnvelope`.
Over MCP: `server/serve.py`, the `request_context_product` tool, with the
door's `ProducerAssertion` on every outcome.

### D.2 The three regions

`boot` (one config, one boot), `acquire` (three `SELECT`s, one envelope per
dated claim, the single write handle), `govern` (one `build_governed_resolver`
with a NAMED `plan_factory`, an explicit `debt_scorer`, and the product's own
`product_gate`). No `gate`, `record` or `serve` region exists; no
`run_gates`, `build_replay_record` or `serve` call exists.

### D.3 Validation gates

The SDK's three L6 gates, the class's declared obligations, and the product's
own declared gate `cp-03-canonical.spread-freshness-window` — two refusals in
one governed verdict: no obligor in the admitted view (one text for absent and
suppressed), and a freshest filing outside the declared window at the asked
instant.

### D.4 Determinism and replay

Two runs of one question agree byte for byte (`OFC-G01`); the door and the
in-process run agree byte for byte (`OFC-G23`). Replay dimension 1 lists every
served entity; dimension 2 carries the request contract and the policy bundle.

## E · Volatility, debt and materialization

Two decay rates in one payload: annual columns against `annual_facts` (~365 d),
quarterly against `quarterly_facts` (~90 d), each from its own filing. `F` reads
0.3189 for the demonstration obligor because most of its thirteen columns are
years old; it read exactly 1 before `decay_basis: valid-from` was declared,
because `observed_at` is when the fabric learned the claim. `C` reads 0.4915
because a financial firm files none of several declared industrial tags. Neither
was moved.

## F · Source binding and readiness

`ccf_environment.yaml` (the deployment-environment companion of
`ccf_config.yaml` under `D-IMPL-343`; it replaced `backends.yaml` when this
tree was re-expressed on the paved road): two environment variables,
`CCF_CP_03C_POSTGRES_DSN` and `CCF_CP_03C_POSTGRES_SCHEMA`, names and remedies
only. The v2 namespace is
`ccf_v2`; `ccf_dataprep/.env` names v1. Read-only; the role needs `SELECT`.

### F.4 Findings

Raised in `FINDINGS.md`, adjudicated under `D-IMPL-315`. `CP03C-F-01` is the
SDK gap this tree surfaced; `D-IMPL-341` closed it (validation pass 2026-09-18),
and the migration it took — a clock row keyed by the entity class, a gate that
read its window off the wrong instant, and the SDK's gate running first — is
recorded under the finding.

## G · Operate and govern

### G.1 Product gates

The acceptance authority for every gate below is **this clause**
(`D-IMPL-326`). Each id is claimed by the executing test named in
`artifacts/gates.yaml`.

| Gate | Asserts |
|---|---|
| `OFC-G01` | a governed `ServedProduct` of the required class, on a `1.x` lane, at the CP-14 instant, byte-stable across two runs |
| `OFC-G02` | replay dimension 2 is a **superset** of product lineage; the operators invoked are exactly the one declared |
| `OFC-G03` | the spread **is fabric state** — every served period and line is a touched entity, and Π read the view |
| `OFC-G04` | every reported figure names the filing that asserted it, and the spread rests on more than one filing |
| `OFC-G05` | `D_c = 1 − F·C·S` over the view; `C` the evaluable fraction of declared lines; `F` below 1 because columns age from their filings |
| `OFC-G06` | a spread whose freshest filing is outside the declared window at the asked instant is refused — by the SDK's TTL gate first (`ttl-bounds`, since `D-IMPL-341`), and the product's own predicate still names the window on a candidate whose payload anchor lies outside it |
| `OFC-G07` | `expires_at` is anchored on the freshest filing, as declared, and `ttl_anchor_at` records it — live since `D-IMPL-341` (was quarantined evidence of `CP03C-F-01`) |
| `OFC-G08` | an obligor the principal may not see and one that does not exist refuse with one reason, one kind, one detail |
| `OFC-G09` | `intent` is judged on the declared discovery set, and the specimen's shadow argument is refused at contract construction |
| `OFC-G10` | `as_of`, an out-of-domain `peer_basis` and a missing `debt_tolerance` are refused as data, each with a record |
| `OFC-G11` | the caller's tolerance governs — withheld at CP-14's own ceiling, served wide open — and the debt does not move with it |
| `OFC-G12` | the basis changes a figure only where a later filing changed it, and selects within a cell, never across cells |
| `OFC-G13` | `shape_of` reads this tree as **canonical**, and no `build_replay_record` call exists |
| `OFC-G14` | the plan factory takes its operators only from `required` |
| `OFC-G15` | the frozen specimen is **untouched** and no specimen identity is reused |
| `OFC-G16` | the CP-14-shaped question is answered by the producer **in another process** and admitted under `provider-controls` |
| `OFC-G17` | the consumer process runs no producer assembler and holds no producer record |
| `OFC-G18` | the expected producer identity and tenant come from the registration — wrong id and wrong tenant refuse independently |
| `OFC-G19` | a lane the requirement does not admit is refused `version-incompatible`; an unoffered class is a wiring error before any socket |
| `OFC-G20` | no question argument becomes an address; an unresolvable subject is refused by the child's own gate — no fake child |
| `OFC-G21` | at CP-14's own tolerance the spread slot is withheld and the composite refuses on its required child |
| `OFC-G22` | a severed producer is a governed `producer-unavailable` refusal, not a fake child |
| `OFC-G23` | the door and the in-process run serve **one** content address |
| `OFC-G24` | a fresh fabric per run — two connections under one root name two files; an obligor served after another under one root hashes to its own address |
| `OFC-G25` | Π serves the subject's claims and **no other's** — two obligors in a view yield the subject's spread; only another's yields no obligor |
| `OFC-G26` | the dimension-two predicate **refuses** a record that no longer covers the lineage, and no SDK guard makes that state unreachable |
| `OFC-G27` | the fabric-state predicate **refuses** a payload-only representation, and no SDK guard makes that state unreachable |

**All directional, structural or relational. No estate figure is pinned in a
gate** — the counts in §A.2 and §E are measurements a reader can reproduce.

### G.2 Acceptance criteria

1. A real governed `ServedProduct` of `credit-risk.spread` on the lane CP-14
   requires, for a real roster obligor at the CP-14 instant, with debt,
   content address and replay record.
2. The two specimen defects are absent by construction and the SDK's refusal of
   the first is kept as a control.
3. The spread is fabric state; Π and the debt reading read the view.
4. The declared window is held; the expiry anchor gap is raised, not hidden.
5. The product is acquired across a deployment boundary through `D-IMPL-340`
   and admitted; every negative control refuses through the SDK's own path.
6. The frozen specimen is unchanged.

``````

</details>

<a id="source-standard"></a>

<details>
<summary>Specification Standard v0.3 — ccf_code@37ac3055</summary>

Path: `public/reference/specifications/Context_Product_Specification_Standard_v0-3.md`

``````text
# Context Product Specification Standard

**v0.3** — authoring standard for CB/CIB Context Products

**Status:** draft for Data Engineering review · **Basis:** CCF Whitepaper
v1.1, Ch 6 §§6.2–6.5 and Ch 7 §§7.4–7.10 · **Supersedes:** v0.2
(seven-section skeleton retained; twelve additions listed at §16)

Table of contents (updates when the document opens)

---

## 0 · What this document is

This is the **format contract** for a Context Product specification — not a
specification of any one product. A spec written to this standard is complete
enough that a data engineer can identify the source systems, build the
assembly path, register the product, and operate it without a further design
conversation.

Five rules govern the whole document.

- **A Context Product is not a dataset.** It is a unit of meaning — typed,
  governed, and fit to act on — assembled at request time for one intent, one
  perspective, one moment and one policy envelope.
- **The contract is nine elements, not eight.** Schema, Freshness SLA, TTL,
  Policy Binding, Lineage, Semantic Version, Discovery, Addressability,
  Assembly Mode.
- **Assembly is a composition of named operators over capability classes.**
  A spec describing bespoke logic instead of an operator composition has
  moved cost from the platform to the product, which is the failure mode
  this architecture exists to prevent.
- **The wire format is part of the standard.** Every product returns the
  same response envelope (§10). A consumer that must special-case a
  product's response shape does not have a contract, it has an integration.
- **Every claim in a spec is falsifiable or it is decoration.** *(new in
  v0.3)* A counterfactual, a replay guarantee, a determinism class and a
  validation gate are each stated as a test someone can run and watch fail.
  A spec whose assertions cannot be disproved has documented an intention,
  not a design.

### 0.1 Do you need a Context Product? — the four-question test

Build one only if the answer to **all four** is yes. If any is no, build the
data product and move on; the fabric is expensive precisely because it
carries guarantees a data product does not.

| # | Question | If no |
| --- | --- | --- |
| 1 | Does the answer change with who is asking, beyond formatting? | Build a view |
| 2 | Does the answer have a validity window after which acting on it is wrong? | Build a table with a refresh schedule |
| 3 | Must the answer be reconstructible after the fact, with the policy and freshness state that produced it? | Build a report and archive the output |
| 4 | Is it composed at runtime from sources no schema author pre-joined? | Build the join |

A qualified yes is a legitimate answer, but it must be written down as one.
A product admitted on two clear yeses and two partials is admitted on a
stated basis that a reviewer can challenge.

### 0.2 Placeholder discipline (new in v0.3)

Every unresolved item carries an explicit marker — `[TBC]` — and every
marker appears again in §F with a named owner. **A spec with honest gaps is
buildable; a spec with invented system names is not.** Reviewers should
treat an unmarked assumption as the more serious defect, because a marked
gap gets closed and an invented one gets built.

### 0.3 Section skeleton

| § | Section | Answers | Primary audience |
| --- | --- | --- | --- |
| A | Decision frame | What decision, for whom, and what breaks without it | Product owner, business sponsor |
| B | Contract | The nine elements and the request parameter surface | Consuming agent teams |
| C | Data catalog | Every element, its system of record, and where it lands in G | Data engineering |
| D | Assembly recipe | The operator composition, step by step, with emits, budgets and gates | Data engineering |
| E | Volatility & materialization | Per-signal half-life, debt model, supersession, caching posture | Platform, FinOps |
| F | Source binding & readiness | What exists today, what does not, who owns the gap | Data engineering, source owners |
| G | Operate & govern | Owner, SLOs, degradation, observability, retention, lifecycle | Platform, second line |

The seven sections appear in order, always. A product with nothing to say in
a section writes one line explaining why, rather than omitting the heading —
an absent section reads as an oversight and a short one reads as a decision.

### 0.4 Front matter (new in v0.3)

Before §A, every spec carries: registry name · tier · Assembly Mode · cost
band · lifecycle state · accountable owner · last review date · a
two-sentence statement of what the product resolves · the four-question
build test result · build-order note.

**Capability gate.** Where a product cannot be built at all without a
capability the estate may not have, that fact is stated **above §A**, not
discovered in §C. This is a scheduling decision, not a build detail: a spec
whose blocking dependency is buried is a spec that gets scheduled and then
stalls.

---

## 1 · Section A — Decision frame

**Decision & trigger.** The decision, the role taking it, and the event that
triggers the request, in language a business sponsor recognizes. Where a
product serves several distinct triggers that ask genuinely different
questions, tabulate them and name which axis each exercises — the forensic
and the live case are not the same request wearing different parameters.

**Consuming principals.** Every role that will call the product, and whether
each receives **materially different assembled content** — not different
formatting. Different content means a projection plan (§13.2); different
formatting belongs to the consuming application.

**Counterfactual failure.** What a conventional data product returns for
this decision and why it is wrong. Name the failure mode from the closed
taxonomy: **context-starved · temporally-incoherent · perspective-flat ·
policy-blind · evidence-free**. If you cannot write a counterfactual a
skeptical engineer accepts, the product does not belong in the catalog yet.

**Counterfactual acceptance test** *(new in v0.3)*. The counterfactual is
written as an executable test, not a narrative. State the query, the two
answers, and the condition under which they must differ. Where they agree,
the product is not doing the work the counterfactual claims for it — and
this is exactly the check a reviewer should be able to run on the built
product rather than accept on assertion.

**Primitive taught** *(optional, catalog coherence)*. Where the product is
the clearest instance of one architectural primitive, name it — the catalog
is also a teaching sequence, and a product that teaches nothing new is a
candidate for merger with its neighbour.

**Contrast pointer** *(optional)*. Where a sibling product makes the
opposite design choice on the same axis, name it and the axis. Two products
with opposite `ttl_anchor` values teach the anchor better than either does
alone.

---

## 2 · Section B — Contract

### 2.1 The nine elements

| Element | What to write | Common error |
| --- | --- | --- |
| Schema | Named payload type; entities, relationships, attributes and measures, each bound to an ontology IRI. Link the machine-readable schema artifact. | Prose in a table cell with no artifact. Prose is not a contract. |
| Freshness SLA | Per signal class, not one value for the product. | One "intraday" over a payload mixing intraday and annual signals. |
| TTL | Duration plus ttl_anchor: from_decision or from_entity_freshness. Where the product carries a dual TTL, state both branches and the condition that selects them. | Anchoring by habit rather than by decision shape. |
| Policy Binding | Every regime and internal policy constraining construction, each with a resolvable version id; entitlement scope bound to the actual entitlement service; data classification and residency constraints (§2.2). Where policy must be pinned to a past date, say so here and enforce it in §D. | Asserting "entitlement scope" with nothing behind it. |
| Lineage | operators_invoked[] · graph_snapshot_at · policy_version · projection_plan_id · passage anchors where any claim rests on text · context_debt · payload_hash · model_record for Mode 2/3. | Omitting context_debt; it is an output of every assembly. |
| Semantic Version | vMAJOR.MINOR.PATCH, prior supported version, migration window, and the change class rules at §14. | A version with no stated migration window. |
| Discovery | domain.product.vN. | Registering before §G is complete. |
| Addressability | URL pattern with a resolvable anchor identifier. | Anchoring on an internal surrogate key. |
| Assembly Mode | 1 pure algorithmic · 2 algorithmic with LLM packaging · 3 algorithmic orchestration with agent-swarm assembly, with a one-sentence cost/quality/determinism rationale. Modes 2 and 3 additionally require the model-risk annotation at §2.3. | Omitted entirely. |

**Assembly Mode is a registration-time commitment.** The product owner settles
it, with a stated rationale, when the product class is registered. **It is not
something the assembling agent works out for itself, and it cannot vary between
calls.** Changing it is a MAJOR change (§14).

### 2.2 Classification and residency

State, inside Policy Binding:

| Field | Values |
| --- | --- |
| Data classification | public · internal · confidential · restricted — highest classification of any element in §C |
| Information barrier | none · control-room restricted · MNPI-bearing |
| Residency constraints | Jurisdictions whose data may not leave, and the effect on assembly |
| Cross-border serving | May this product be served to a principal outside the data's jurisdiction, and under what condition |

**The suppression rule.** Where policy excludes content, the payload must
carry **no count, marker, or placeholder** indicating that anything was
withheld. Restricted content is never materialized and filtered — a "3 items
hidden" marker is itself a disclosure, and on an information-barrier product
it is a reportable one.

### 2.3 Model-risk annotation — Mode 2 and Mode 3 only

An LLM in the delivery path is a model, and model governance applies.
Record:

- Model identifier and version, pinned; temperature pinned; prompt template
  versioned and logged
- Model-risk registration reference and validation status
- **The substrate/presentation boundary** — which fields are algorithmic
  artifact-of-record and which are model-rendered presentation
- **The smoothing control** — how the design prevents the model reconciling
  a conflict the substrate deliberately surfaced. A product whose substrate
  reports two sources disagreeing and whose narrative reads as settled has
  failed, and this is the failure mode Mode 2 is most prone to

Mode 1 products state "not applicable — no model in the trust path," which
is the reason to prefer Mode 1 wherever the decision does not need
narrative.

### 2.4 Request parameter surface

A table of every parameter with a **"Moves"** column naming which dimension
it moves: E anchor, R scope, T reconstruction, P envelope, Π perspective, or
a measure. A parameter that moves nothing is a formatting flag; push it to
the consumer.

Required on every product: an anchor identifier, `intent` (from the intent
registry, §13.1), and `debt_tolerance`.

**Declared-but-inert parameters** *(new in v0.3)*. Where a parameter is part
of the uniform surface but unsupported at this product's tier, declare it
and have it **fail explicitly** — `not_supported_at_tier`. It must never
silently succeed against current state. A parameter that appears to work and
does not is worse than an absent one: it will be relied on in a dispute.

### 2.5 Prerequisites, consumers and scope boundary

- **Prerequisites** — products this one composes over, by registry name.
  This is the build order.
- **Consumers** — products and applications that depend on this one.
  Required because §E supersession cascades need a reverse dependency list,
  and because a MAJOR version change needs a notification list.
- **Deliberately out of scope** — capabilities a reader will expect and not
  find, and which product carries them. Flag these to consumers as *coming
  next*, not as gaps.

---

## 3 · Section C — Data catalog

### 3.1 Element table

One row per data element:

| Column | Content | Rule |
| --- | --- | --- |
| Element | The fact or signal, in business language | One row per element, not per table |
| System of record | The authoritative source system | A named system; "internal" is not a system |
| Provenance class | internal-SOR · vendor · public-filing · derived · inherited | derived requires the derivation to appear in §D |
| Classification | public · internal · confidential · restricted | Drives §2.2 |
| Capability class | The store capability required (§11.1) | Never a product name |
| G dimension | E · R · T · P · Π · L · schema | Every element lands somewhere in the graph or it is not context |
| Ontology IRI | Bound class or property from the shared ontology contract | Unbound elements block registration |

### 3.2 Capability decomposition (new in v0.3)

Where a product depends on a capability the estate may not have, **decompose
the capability into its separable properties** and state what is deliverable
if each is absent. An estate rarely fails a capability wholesale; it
satisfies two of four properties and fails the rest, and that is the finding
worth having.

| Column | Content |
| --- | --- |
| Property | The separable sub-capability |
| Common estate answer | Widely available · sometimes · rare |
| If absent | Blocking · degrades to a named partial · workaround with a stated cost |

Where the decomposition yields a partial, name the **interim posture** —
which triggers are deliverable, what the unsupported parameter returns, and
what version string the partial ships under. Shipping a partial as though it
were complete is the failure this section exists to prevent.

### 3.3 Correlation key and single-writer discipline

Close with the **correlation key** — the identifier(s) every element joins
on, where the crosswalk lives, and its **measured coverage**. An unmeasured
crosswalk is a stated risk, not a footnote.

**Single-writer discipline.** One system is authoritative per element; no
element is written by two. Where an element exists today in two systems,
name the authority and make the other a read replica. This is a prerequisite
to build, not a follow-up.

**Identity authority hierarchy** *(new in v0.3)*. Where an anchor identifier
does not exist for every entity the product must serve, tabulate the entity
classes, the identity authority for each, the source of record-status for
each, and the **freshness ceiling each class implies**. An anchor that
silently excludes a population is inherited by every downstream product, and
the asymmetry belongs in the payload rather than averaged into a single
freshness claim.

---

## 4 · Section D — Assembly recipe

### 4.1 Client call

The literal request with parameters populated. Where the product has a
forensic and a live case, show the forensic one — it exercises more of the
surface.

### 4.2 Operator step table (expanded in v0.3)

Numbered, **one operator per step**, as a table:

| Column | Content |
| --- | --- |
| # | Step order |
| Operator | One name from the closed vocabulary (§11.2) |
| Capability class | From §11.1 — never a product name |
| Inputs | What the step consumes |
| Emits | What the step produces, named as it appears in lineage |
| Failure behavior | fail closed → HTTP code · degrade with debt · skip |
| p95 budget | Milliseconds, summing to a stated total against the tier envelope |

The final step is always contract assembly. **State the budget total and the
envelope it is measured against.** A total at 97% of the envelope is a
design finding, not a rounding detail — say which step dominates and what
the first optimisation would be.

### 4.3 Step detail

Below the table, prose for any step carrying a non-obvious discipline. This
is where an engineer learns *why* an ordering exists, and it is the part
that prevents a well-meaning optimisation from removing a load-bearing step.

Two disciplines recur and should be written out wherever they apply:

- **Policy that appears to do nothing still runs first.** At Tier 1 the
  step is an entitlement check; at Tier 5 the same step is what makes a
  restricted edge structurally absent. The ordering is learned from the
  first product or retrofitted painfully later.
- **Two filters on two axes are two filters.** Where a product reconstructs
  both what was true and what was known, both filters are separately
  parameterised and separately testable. Applying one silently answers a
  different question, and the silence is the defect.

### 4.4 Determinism class and payload hash

| Class | Meaning | Applies to |
| --- | --- | --- |
| deterministic | Same anchor + as_of + policy_version + graph snapshot → byte-identical payload | Mode 1 |
| substrate-deterministic | Algorithmic substrate byte-identical; presentation reproducible only under pinned model, temperature and prompt | Mode 2, Mode 3 |

Every product publishes a **payload hash** over the deterministic portion,
excluding `assembled_at`. **Replay asserts hash equality, not similarity.**

### 4.5 Replay statement and replay test

**Replay statement.** What exactly the replay engine re-executes to return
the identical product. "A similar product" is a defect recorded in §G, not a
caveat.

**Falsifiable replay test** *(new in v0.3)*. A numbered procedure a reviewer
can run against the built product, ending in an assertion that can fail. The
pattern: serve and record the snapshot · mutate the underlying state ·
re-derive live and confirm the new value · re-derive at the recorded
snapshot and confirm the **original** value returns. If the final step
returns the new value, the snapshot is not load-bearing and
`graph_snapshot_at` is decorative.

Where the product carries two time axes, add a second test asserting the
axes **disagree** under a case constructed to separate them. Agreement means
a filter was dropped.

### 4.6 Emitted contract

The response envelope of §10, populated with this product's payload schema,
**with types**. This is what the consuming agent team codes against and what
CI validates. Prose describing a payload is not a payload.

`extra=forbid` is enforced as a build-time CI invariant: a per-product
subclass cannot quietly introduce a field absent from the base declaration, and
a pull request carrying a drifted contract fails before it reaches a deployment
surface.

### 4.7 Validation gates

**Universal**, applying to every product without re-argument:

- **Empty-operator guard** — no operator returns an empty set silently;
  empty is fail-closed or an explicit debt contribution
- **Lineage strict equality** — operators_invoked equals the operators
  executed
- **TTL bounds** — expires_at consistent with the declared TTL and anchor;
  where the TTL is dual, the branch matches the condition
- **Debt gate** — assembly halts and returns the debt signal where D_c
  exceeds debt_tolerance
- **Suppression silence** — payload carries no marker of withheld content
  (§2.2)
- **Classification containment** — no element above the declared
  classification appears in the payload

Then **product-specific gates**, each a testable assertion naming the defect
it detects, cross-referenced to a fixture ID:

> "reconciliation guard — gross exposure must be ≥ guarantee-adjusted
> exposure; a violation means the dedup logic double-subtracted. → fixture
> EXP-G01"

---

## 5 · Section E — Volatility, debt & materialization

### 5.1 Half-life table

One row per signal class: λ_c · **calibration basis** · decay driver ·
supersession event · owner.

λ_c is **Control Plane configuration per observation type**, not a
per-document attribute; conflicts between two specs resolve centrally. The
table in a spec is an **initial calibration proposal**, and saying so is the
difference between a value an engineer can challenge and a number they
assume was measured.

**Calibration basis** is one of: **illustrative** (a starting assumption) ·
**expert** (business judgment, named function) · **measured** (observed
decision-reversal or restatement data). A catalog whose λ_c values are all
illustrative is not calibrated, and stating that plainly is more useful than
implying otherwise. Review cadence: annually, or on any
supersession-pattern change.

### 5.2 Debt model and per-component debt table (expanded in v0.3)

`D_c = 1 − (F · C · S)` — **multiplicative**, so a collapsed dimension
forces escalation rather than being averaged away. **Normalize F over
required signal classes, not over the classes actually present**, or losing
a source improves the freshness score.

Beyond the model, every spec carries a **per-component debt table**:

| Column | Content |
| --- | --- |
| Component | The input or claim |
| May be absent? | yes · no |
| D_c contribution | The weight |
| Behavior when absent | Fail closed · serve with flag · mark the affected claim NOT_EVALUABLE |

**Debt is decomposed per claim, never only per product.** A product with
four claims where one input is missing returns three evaluated claims and
one marked unusable — not a product-level failure, and never a
silently-omitted fourth. The gap is captured **before** the decision is
taken and shapes it directly: it is a decision input, not a log line.

### 5.3 Materialization posture

`materialized` · `derived-on-demand` · `split` (state which fields and
why). The test is mechanical: **if the fastest-moving input's λ_c is shorter
than the intended cache window, materialization is wrong.**

State the **cache key** explicitly — tenant, schema name, plan id, snapshot,
any time-axis parameters, and principal binding. A cache key missing a
parameter that changes the payload is a correctness defect that presents as
an intermittent one.

### 5.4 Supersession triggers

Each event marked **local** or **cascading**, and for cascading, the named
downstream products from §2.5. Invalidation cascades to every product whose
`operators_invoked` touched the superseded entity, not only those named for
it.

Re-derivation is **lazy** — invalidate for next request; do not
re-materialize eagerly, or a routine upstream publication becomes a
thundering-herd event across the catalog.

---

## 6 · Section F — Source binding & readiness

| Element | System of record | Interface & cadence | Available today | Gap owner | Blocker |
| --- | --- | --- | --- | --- | --- |

**Available today** is yes · partial (name the fields) · no. Every partial
or no carries a named gap owner and a stated blocker. Close with:

- **Access path** — existing feed, CDC, API, event stream, or new build
- **Identifier reality** — does the correlation key exist end to end; who
  owns the crosswalk; measured coverage
- **History depth** — how far back the source reconstructs, which bounds
  any as_of the contract advertises. Where the source publishes snapshots
  without history, **start retaining deltas now**; history not captured
  cannot be reconstructed later
- **Text-source boundary** — build-time extraction or runtime operator. A
  spec reaching into a document at runtime has changed capability class and
  cost band
- **First-build volumetrics** *(new in v0.3)* — the population the first
  build must contain for every gate and counterfactual to have something to
  act on. Where a required case does not occur naturally in the sample,
  **widen the sample until it does** rather than proceeding without it; a
  demonstrable primitive with no instance in the data reads to reviewers as
  machinery without a purpose

**No spec passes review with an unowned gap.** "Does not exist yet" is a
valid state; unattributed is not.

---

## 7 · Section G — Operate & govern

| Entry | Content |
| --- | --- |
| Accountable owner | Product owner, data steward, policy owner — roles, not individuals |
| Service objectives | p50 / p95 assembly latency, expected volume, concurrency ceiling, payload bound, absolute per-call cost estimate alongside the relative band |
| Degradation contract | Per input class: partial payload with elevated D_c, or fail closed. Mandatory classes named explicitly |
| Debt model | Which inputs drive F, C and S; debt_tolerance default and its basis (§5.2) |
| Observability | Per-operator latency · D_c distribution · gate-failure counts by gate · cache hit rate · entitlement denials · degradation-branch frequency · supersession-triggered invalidations. This is also the evidence base for moving λ_c and debt_tolerance from illustrative to measured |
| Retention & record of record | Which system is the record of record for each element; the fabric references it and does not replace it. Replay-record retention tier — full-fidelity, compressed, or tombstoned — and the severity rule that assigns it |
| Test fixtures | Named fixtures for the happy path, each gate, each degradation branch, and a replay hash assertion |
| Lifecycle | draft · in-build · certified · deprecated, with date and reviewer. Deprecation requires: consumer notification from §2.5, a sunset date at least one migration window out, and a named successor or an explicit statement that none exists |

### 7.1 Acceptance criteria (new in v0.3)

Every spec closes with a checklist of assertions **specific to this
product**, each independently verifiable, each phrased so it can fail. The
universal definition of done is at §15; §7.1 is what this product must
additionally prove. Close with the **open decisions blocking build**, named
by their §F row.

### 7.2 Catalog contribution (new in v0.3, optional)

Where the catalog is also a teaching sequence: what this product proves that
no earlier product proved, and what it deliberately does not prove. A
product that proves nothing new is a merge candidate; a product whose
exclusions are unstated invites a reviewer to read a tier boundary as an
oversight.

---

## 8 · Response envelope

Every product returns the same envelope. This is a wire contract, not a
style guide.

```json
{
  "product": "credit-risk.exposure-rollup",
  "semantic_version": "1.0.0",
  "payload": { },
  "contract": {
    "assembled_at": "...",
    "expires_at": "...",
    "ttl_anchor": "from_decision",
    "ttl_basis": "...",
    "assembly_mode": 1,
    "determinism_class": "deterministic",
    "freshness": [
      { "signal_class": "...", "observed_at": "...",
        "lambda_c_hours": 4, "relevance": 0.87 }
    ]
  },
  "lineage": {
    "operators_invoked": [ ],
    "graph_snapshot_at": "...",
    "policy_version": "...",
    "projection_plan_id": "...",
    "model_record": null,
    "payload_hash": "..."
  },
  "context_debt": {
    "F": 0.91, "C": 1.0, "S": 1.0, "D_c": 0.09,
    "contributions": [ ]
  },
  "notices": [
    { "type": "degraded-input", "signal_class": "...", "effect": "..." }
  ]
}
```

Rules:

- `payload` is never returned without `contract`, `lineage` and
  `context_debt`. A consumer that receives context with no debt signal
  cannot know what it is trusting.
- `notices` **is for degradation the consumer must see**, not for logging.
  Anything policy suppressed never appears here (§2.2).

---

## 9 · Error semantics

Every product returns one of these, and §D names which step raises which.

| Condition | Response | Notes |
| --- | --- | --- |
| Anchor unresolvable | 404 | Never an empty payload |
| Principal not entitled | 403, no detail on what exists | Existence is itself disclosure |
| Parameter unsupported at tier | 400 not_supported_at_tier | Never a silent success against current state |
| Debt gate exceeded | 409 with the debt block | Not a 200 with a warning |
| Mandatory input unavailable | 503 with the failed source class named | Silence is not a negative answer — an unretrieved screening source is not a clean screen |
| Non-mandatory input unavailable | 200 with notices and elevated D_c | The degradation contract in §G governs which inputs are which |

---

## 10 · Operators and capability classes

### 10.1 Capability classes

| Class | Capability required | Typical use |
| --- | --- | --- |
| relational | Set-based query over structured records at scale | Resolve, Enrich, reference lookup |
| bitemporal-ledger | Append-only state with valid-time and observed-time, queryable at a past point | Traversal mode temporal, supersession chains |
| graph-traversal | Multi-hop typed edge traversal with predicate filters | Ownership, guarantee, cross-default |
| document-passage | Document storage with passage-level addressing | Passage lineage, evidence chains |
| vector-index | Similarity retrieval over embeddings | Typology and pattern matching |
| federated-external | Contract-bounded request outside the institution's trust boundary | Cross-organizational products |
| in-memory | Deterministic computation over assembled state | Evaluate in all modes |

Estate binding lives in one artifact owned by the platform team. **Product
specs never name a database.**

### 10.2 Closed operator vocabulary

| Operator | Purpose | Reads | Emits | Cost driver |
| --- | --- | --- | --- | --- |
| Resolve | Anchor to canonical entity | relational | canonical entity, principal perspective | O(1) |
| Policy | Load the envelope in force; compute permitted sets | relational, bitemporal-ledger | policy_version, permitted party / document / action sets | O(1); gates everything downstream |
| Projection | Resolve and apply the Π plan | relational | projection_plan_id, projection shape | O(1) |
| Traversal | Walk typed edges. Modes: current · temporal | graph-traversal, bitemporal-ledger | node set, edge set, graph_snapshot_at | fan-out × depth — dominant cost |
| Enrich | Resolve nodes to attributes. Always batched | relational, document-passage | attribute sets, passage spans | entity × attribute fan-out |
| Similarity | Rank candidates within the permitted set | vector-index | ranked candidates with scores | candidate-set size |
| Evaluate | Deterministic computation. Modes: aggregate · score · reconcile · rank | in-memory | measures, scores, variances | negligible |
| Federate | Contract-bounded request to an external fabric | federated-external | remote attested payload, attestation record | network + negotiation |

Retired names: Batch Enrich (batch is mandatory, not a variant), Temporal
Traversal (a Traversal mode), Aggregate / Score / Reconcile / Rank (Evaluate
modes), Compose (contract assembly, not an operator).

### 10.3 Composition invariants

1. **Policy before anything that reads graph state.** Impermissible content
   is never materialized, not filtered afterwards.
2. **Resolve before Traversal.** Traversal from an unresolved anchor
   answers plausibly about the wrong entity.
3. **Enrich is batched, always.** One query per source per step.
4. **Algorithmic substrate before any semantic stage.** Every LLM
   invocation reads only the typed substrate a preceding algorithmic
   operator produced, and the substrate remains artifact-of-record.

### 10.4 Cost estimation

Cost bands are relative multiples of the Tier-1 baseline and are
placeholders until measured. Estimate before building:

```
est_cost = baseline
         × (1 + traversal_fanout^depth / fanout_reference)
         × (1 + enrich_sources)
         × mode_multiplier          # Mode 1 = 1 · Mode 2 ≈ 3–5 · Mode 3 ≈ 15
         × materialization_factor   # materialized = 1/hit_rate · on-demand = 1
```

Record the assumed fan-out, depth and hit rate. The commonest cost surprise
is a traversal whose fan-out was estimated on the median entity and paid on
the tail — **state the p95 fan-out, not the mean**.

---

## 11 · Shared contracts

Six artifacts referenced by every spec. Only the first exists today; the
rest block certification, not build.

| Artifact | Owner | Purpose | State |
| --- | --- | --- | --- |
| Ontology / IRI binding | Data architecture | Class and property IRIs every schema binds to | exists |
| Intent registry | Product owners + second line | Enumerated intent values and the envelope each selects | missing |
| Projection plan registry | Product owners | Named Π plans and what each assembles differently | missing |
| Policy version registry | Second line / compliance | Versioned envelopes with effective dates, resolvable at replay | missing |
| Half-life calibration table | Platform | λ_c per observation type with calibration basis | missing |
| Capability binding | Platform | Capability class to estate system, per environment | missing |

**Extension namespace** *(new in v0.3)*. Where a schema needs a class or
property the shared ontology does not carry, it is minted in the `ex:`
extension namespace — **registered centrally with an owner, once**, not ad
hoc per product. Three products minting their own covenant model
independently is three incompatible covenant models, and the divergence is
discovered at integration rather than at design.

### 11.1 Intent registry record

`intent` is required on every product and selects the policy envelope, which
makes it a governed object. Each record carries: intent id · plain-language
decision · the policy envelope selected · permitted principals · products
accepting it · owner · effective date and version · deprecation status.

### 11.2 Projection plan record

Each plan carries: plan id · principal(s) · **what is assembled
differently** (not displayed differently) · entitlement precondition ·
suppression behavior confirming the silence rule · owner · version. A plan
whose difference is presentational is rejected — that is a consumer concern.

---

## 12 · Naming, versioning and change classes

| Convention | Rule |
| --- | --- |
| Registry name | domain.product.vN — domain from the approved list, product in kebab-case, N = MAJOR only |
| Address | /context-products/{domain}/{product}/{anchor-id} |
| Schema artifact | schemas/{payload_type}.v{MAJOR}.json |
| Fixture id | {PREFIX}-{F/G/D/R}{nn} — happy path, gate, degradation, replay |
| Spec document id | CP-SPEC-{nnn} — stable across versions of the same product |

Change classes:

| Class | Examples | Consumer impact |
| --- | --- | --- |
| PATCH | Gate added, telemetry added, documentation | None |
| MINOR | Additive payload field, new optional parameter, new projection plan, λ_c recalibration | Backward compatible; notify consumers |
| MAJOR | Field removed or retyped, parameter default changed, ttl_anchor changed, Assembly Mode changed, policy envelope semantics changed | Migration window required; both versions served |

A λ_c or debt_tolerance change is **MINOR by type and material by effect** —
it changes outputs without changing shape. Announce these to consumers
explicitly rather than letting them surface as unexplained behavior change.

---

## 13 · Tiers, review and certification

| Tier | Capability classes | Cost band | Required review |
| --- | --- | --- | --- |
| 1 | relational | ×1 baseline | Product owner |
| 2 | + graph-traversal | ×1–2 | Product owner + platform |
| 3 | + bitemporal-ledger | ×2–4 | + second line where P is regulatory |
| 4 | + document-passage, vector-index | ×3–5 materialized, ×8–15 on demand | + second line, evidence-chain review |
| 5 | + federated-external, multi-principal Π | ×8–15 | + legal / control room |

Tiers describe assembly complexity, not maturity, and **not build order** —
build order comes from the prerequisite graph.

**Certification evidence.** Moving to certified requires, on file: schema
artifact published; all fixtures passing including the replay hash
assertion; measured p95 latency and per-call cost; debt_tolerance justified
against observed data; every §F gap closed or accepted by a named owner;
and, for Mode 2/3, model-risk registration complete.

---

## 14 · Review checklist for the reviewer (new in v0.3)

A reviewer reads for six things, in this order. The first three reject a
spec; the last three return it with comments.

- **Is the counterfactual falsifiable?** Can I run the test in §A and watch
  it fail? If not, the product's reason to exist is an assertion.
- **Is every capability stated as a capability, not a product?** A named
  database in §C means the spec is bound to a platform decision that has
  not been made.
- **Does every gap have an owner?** An unowned [TBC] is an unassigned risk
  that will surface during build.
- **Does each §D step name one operator from the closed vocabulary?**
  Bespoke logic in a step means cost moved from platform to product.
- **Is debt decomposed per claim?** A single product-level D_c forces
  all-or-nothing escalation and wastes the primitive.
- **Does the payload carry types?** Prose describing a payload is not a
  payload.

---

## 15 · Definition of done

- All seven sections present, in order, with front matter and capability
  gate
- Four-question build test answered, including honest partials
- Nine contract elements populated, including Assembly Mode with rationale
- Classification, residency and information-barrier fields complete
- Model-risk annotation complete for Mode 2/3, or "not applicable" for
  Mode 1
- Every §C element has a system of record, provenance class,
  classification, capability class, G dimension and ontology IRI
- Capability decomposition present where the estate answer is unknown, with
  interim posture named
- Correlation key stated with measured coverage, or the measurement named
  as a §F gap
- Every §D step names one operator from the closed vocabulary, its
  capability class, its emits, its failure behavior and its budget
- The four composition invariants hold
- Determinism class stated and a payload hash defined
- Replay statement plus a numbered, falsifiable replay test
- Emitted contract shown with types, conformant to the §8 envelope; error
  taxonomy mapped to steps
- Product-specific gates written as testable assertions with fixture IDs
- Half-life table carries a calibration basis and an owner per row
- Per-component debt table present, with behavior-when-absent per
  component
- Every no or partial in §F has a named gap owner; first-build volumetrics
  stated
- §G complete, including degradation contract, debt model, observability,
  retention and lifecycle
- Consumers list populated and cascading supersession targets named
- Acceptance criteria written as failable assertions; open blocking
  decisions named

---

## 16 · What changed from v0.2

| # | Addition | Why |
| --- | --- | --- |
| 1 | Rule 5 — every claim falsifiable | v0.2 required a counterfactual and a replay statement but allowed both to be narrative; a reviewer had no test to run |
| 2 | §0.2 placeholder discipline | An invented system name is a more serious defect than a marked gap, and v0.2 had no convention for marking one |
| 3 | §0.4 front matter and the capability gate | A blocking platform dependency discovered in §C is discovered after scheduling |
| 4 | §1 counterfactual acceptance test | Turns the counterfactual from a rationale into an executable check on the built product |
| 5 | §2.4 declared-but-inert parameters | A parameter that appears to work and does not will be relied on in a dispute |
| 6 | §3.2 capability decomposition and interim posture | Estates fail capabilities partially, not wholesale; the partial is the useful finding |
| 7 | §3.3 identity authority hierarchy | An anchor that silently excludes a population propagates the exclusion catalog-wide |
| 8 | §4.2 operator step table with emits and budgets | v0.2 prescribed prose steps; engineers need inputs, outputs and a latency budget per step |
| 9 | §4.5 falsifiable replay test | v0.2 defined hash equality but gave no procedure to demonstrate it |
| 10 | §4.6 emitted contract with types | The largest remaining gap between an architecture document and a buildable one |
| 11 | §5.2 per-component debt table | Product-level D_c forces all-or-nothing escalation; per-claim decomposition is what makes the primitive useful |
| 12 | §7.1–7.2 acceptance criteria and catalog contribution; §14 reviewer checklist | v0.2 could be written but not reviewed consistently |

Two v0.2 disciplines were reinforced rather than changed: λ_c remains
Control Plane configuration that a spec proposes rather than fixes, and the
suppression silence rule is now also a universal validation gate rather than
a prose rule.

``````

</details>

<a id="source-recipe"></a>

<details>
<summary>Specification generation recipe — ccf_code@37ac3055</summary>

Path: `public/reference/specifications/spec_generation.md`

``````text
# Generating a Context Product Specification — recipe for SDK Claude

**Audience:** the Claude session working in `ccf_code`.
**Output of this recipe:** one `CP-SPEC-NNN_<Product_Name>.md` in
**`examples/cp-NN-<slug>/spec/`** — inside the example it governs, never in a
docs folder (§7.1) — authored as the **first step** of that example project,
**approved by Dave before any implementation**, and closed out against a build
that proves it.
**Status:** authoring instruction, not a specification. Written 2026-08-29 by
the vault Claude at Dave's direction.

**Owner: the vault.** Proposed by `ccf-sdk` and sent through the §11 return path
2026-08-29; reverse it here if the vault rules otherwise. The reason is this
document's own §1 — most of what follows states **what the vault and
`ccf_dataprep` owe `ccf_code`**, and an agent that owns the document stating its
own entitlements is writing another agent's term, which is the failure §0
records. So: **`ccf_code` proposes changes here through the return path rather than
editing freely** — with one narrow exception, and a test for it.

**§7 describes `ccf_code`'s own tree**, so `ccf_code` may edit §7 directly and
report back when the edit **records what the tree already is**: a path, a
filename, a directory that exists, a layout the examples already follow. That
is what happened to §7.2 on 2026-08-29 — the diagram predated `page/` and
`summary_explanations.md`, and a session following it would have built an
example missing both.

**The test: could this edit be wrong tomorrow without any file moving?** If it
could, it is a rule and not an observation, and it goes through the §11 return
path — even when it sits inside §7, even when the tree already disagrees with
it, and even when every example already does what the edit says. A requirement
that something be published, a gate ordering, an approval, any *shall* or
*must* or *never*: rules. Observing that no CP-SPEC is published is an
observation. **Deleting the requirement to publish one is a rule change.**

Recorded rather than implied: §7.1's publication requirement was deleted
directly at `a9c4e28b` on 2026-09-12 and reported through `contrib/ccf-sdk/`.
**The vault ruled the outcome correct and the route wrong.** The edit stands and
is not precedent for the next one. The report was complete and honest, which is
why this is a wording change here rather than a reversal there.

**The companion document is `ccf_code`'s.**
[How an example is delivered](example_delivery.md) covers everything after the
spec is approved — the `make` target, the venv, the README run block, the
documentation page mechanics, the banker-facing summary, the verbatim-output
discipline and a delivery definition of done. Nothing in it is another agent's
term, so it is owned, edited and gated by `ccf_code` without a return path.
**Where the two documents disagree about `ccf_code`'s tree, the companion
wins**; where they disagree about what a specification must contain, this one
does.

---

## 0 · What this document is

There are 21 Context Products described in the obsidian vault. None of them has
an SDK specification yet except `counterparty-reference-snapshot`, and that one
is on the older CP-SPEC-001 form. This document is the recipe for producing the
rest.

A Context Product specification here is assembled from **three inputs owned by
three different agents**, it is **the first step in building a Context Product
example**, and **it does not proceed to implementation until Dave has approved
it** (§2).

The single most important rule in this document is that **you may not write
another agent's term.**

That rule exists because it has already failed once. The vault wrote a scope
sentence — *"identity only — no exposure, no grade, no relationship"* —
with no implementation to check it against. `ccf_dataprep` read it, correctly
treated the vault as the requirements authority, and generated an estate with
**no risk grade and no coverage assignment**. Meanwhile CP-SPEC-001's emitted
contract declares `internal_risk_grade`, `coverage_rm_id`, `coverage_team` and
`coverage_lob`, and its §E.2 assigns the absent overlay a **0.30 `D_c`
contribution against a 0.25 `debt_tolerance`** — which trips the debt gate and
returns `409`. Three agents, no malice, one unservable product.

Everything below is designed so that cannot happen twenty more times.

---

## 1 · The law: three owners, one term each

| Term of the equation | Owner | Authoritative for | Published as |
|---|---|---|---|
| **why it exists** | **vault**<br>`obsidian-vault/wiki/context-products/content/` | Decision frame · trigger · consuming principals · counterfactual and its closed-taxonomy failure mode · four-question build test result *with honest partials* · tier · build order · prerequisites · **scope boundary** · primitive taught · contrast pointer · the seven-class Commons/FIBO typing chain | The vault article, prose. §A and the front matter of your spec derive from it |
| **what data exists** | **ccf_dataprep**<br>`/home/parkave/ccf_dataprep` | §C element rows — system of record · provenance class · classification · capability class · `G` dimension · **ontology IRI** · §F readiness and *measured* coverage · §E calibration evidence · first-build volumetrics · every count, threshold and match rate | Their repo: `docs/spec-digest.md`, `docs/data-acquisition-plan.md`, `docs/known-issues.md`, `validators/spec_coverage.py`, `ontology/`, and the live `ccf_v2.*` schema |
| **what it does** | **ccf_code (you)** | §B.1 element values the runtime enforces · parameter surface · §D operator steps, budgets and witnesses · determinism class · replay test · emitted contract · validation gates and fixtures · error mapping · §E materialization and debt · §G operations — **and the merge itself** | `examples/cp-NN-<slug>/` — spec, artifacts and code together |

**The rule.** When a term you need is missing from its owner, you write
`[TBC — <owner>]` and name what you asked for. **You never guess it.** A guessed
term is indistinguishable from an authoritative one once it is written down, and
that is precisely how the grade/coverage break happened.

This is the standard's own placeholder discipline (§0.2) applied *across* agents
rather than within a document: *"a marked gap gets closed and an invented one
gets built."*

### 1.1 · Two levels of specification — and you are writing the second

**Ruled by Dave, 2026-08-29:**

> *"We must distinguish between the specification at the vault level versus the
> SDK level. The vault level is an **implementation independent** product
> specification whereas the SDK is a **specific implementation artifact** for
> developing the context product."*

Both documents are legitimately called `CP-SPEC-001`. They are different
artifact classes answering different questions, and **neither supersedes the
other.**

| | **Vault level** | **SDK level — what you write** |
|---|---|---|
| Document | `wiki/context-products/content/<slug>.md` | `examples/cp-NN-<slug>/spec/CP-SPEC-NNN_….md` |
| Answers | **what the product is** | **how it is built** |
| Posture | implementation-independent | a specific implementation artifact, bound to one estate |
| **Names a store** | **no** | **yes — or a table reference means nothing** |

**The Standard's §10.1 — *"product specs never name a database"* — is written
for the vault level.** Applying it to an implementation artifact strips out the
one thing a developer needs: *"As a context product developer how do I know
where the data being referenced lives?"* (Dave). In a five-store estate
`ccf_v2.legal_entity` does not say whether that is the relational store, the
graph ledger, the document store or the departmental file.

**Three levels. Only the middle one moves:**

| Level | Example | Vault level | SDK level |
|---|---|---|---|
| Capability class — what the store must *do* | `relational` | yes | yes |
| **Store · schema · table — where the element *is*** | `PostgreSQL ccf_v2.legal_entity` | **no** | **yes** |
| Deployment — host, port, credential, instance | — | **never** | **never** |

**Deployment never appears in a specification of either kind.** It lives in
`backends.yaml` as an environment-variable *name*. A sweep of `examples/`,
`public/`, `src/` and `runtime/` for the estate's host address must return
nothing, and no credential enters the tree.

> **This distinction cost a working session before it was written down, and it
> produced two errors in opposite directions.** Read side by side without it,
> the vault article and the repo's `CP-SPEC-001` look like rival drafts of one
> document — 11 §C rows against 4 — and the apparent task is to adjudicate which
> wins. There was no conflict. Then the same gap, applied the other way, stripped
> store identification out of an implementation spec on the literal reading of a
> rule written for the other level. Carry the frame, not just the rules.

---

## 2 · The sequencing law: spec first, approved, then build

**Every specification must be approved by Dave, and the approved specification
is the first step in creating a Context Product example.** Nothing is
implemented before that approval. There are two gates.

### Gate 1 — the authored spec (blocking)

A CP-SPEC is **not** written for the whole catalog in advance. It is written as
**step one of one example project**, when that product comes up the ladder. At
Gate 1 you author everything knowable before code exists:

- §0 and the data banner · front matter · capability gate
- §A in full, including the counterfactual acceptance test as a procedure
- §B.1–B.5 — the nine elements, parameter surface, scope boundary
- §C in full — every element bound to a real table and IRI, coverage measured,
  traps named
- §D.1–D.3 — client call, the operator step table, step detail
- §D.7 gates and §G.2 acceptance criteria, **as intentions phrased so they can
  fail**
- §E.1–E.5 and §F.1–F.4 — with measured data reality from `ccf_dataprep`
- Everything not yet measurable marked **`[TBC — this build, phase Pn]`**

**Send it to Dave. Do not write implementation code until he approves it.** He
is approving the *design*: scope, decision frame, contract elements, operator
composition, and what the product will be held to. That is the cheapest moment
to catch a wrong product, and the grade/coverage break in §10.1 is what an
unreviewed scope boundary costs downstream.

### Gate 2 — the completed spec (close-out)

During and after the build, the measurable terms land: p95 budgets, payload
hashes, witnesses, replay results, gate-failure observations, final
materialization posture. You fill them in and clear every `[TBC — this build]`.

Gate 2 is **not** a second design review. It is a close-out: the approved design
is now discharged by something that runs.

**Nothing at Gate 2 may silently change a Gate-1 decision.** If the build
disproves an approved term — a λ_c, an operator step, a scope boundary — that is
a **deviation**: stop, state it, and take it back to Dave. Do not edit the
approved design to match what you built.

### An approved spec IS editable — classify the edit, not the document

**Ruled by Dave, 2026-08-29.** Approval does not freeze the file. It freezes
**what was approved**, which is not the same thing. Three classes:

| Class | Examples | What to do |
|---|---|---|
| **Editorial** | spelling, a heading brought into line with the Standard, formatting, a broken link, a typo | **Just edit it.** No notice, no approval. Name it in the commit message |
| **Corrective** | a factual error in something approved — a wrong table name, a miscounted row, a stale path | **Edit it, then say what changed and why.** No re-approval; visibility is the obligation |
| **Substantive** | a contract element value · scope boundary · operator step · λ_c · a gate · a parameter · anything that changes what the approval was *about* | **Still a deviation.** Stop, state it, take it back. Unchanged by this ruling |

The test is not *"is the document approved?"* — it always is. The test is
**"would Dave's approval have been different if the document had said this
originally?"** If no, edit. If yes, escalate.

Regenerating a published page after an editorial edit is part of the edit, not a
separate approval.

### Why the claims must still be discharged by a run

Approval makes the design binding; it does not make the claims true. That is
what `examples/cp-00-institutional-holders/artifacts/assembly-recipe.yaml`
holds you to:

> *"**THE §D OPERATOR STEP TABLE, AS DATA** — so that criterion 2 is discharged
> by a test rather than by a reading... **A prose table cannot be held against a
> run.** This document declares the same steps with, per step, a WITNESS — a fact
> a completed run either produced or did not... **a step nothing executes is
> RED.**"*

So: the spec is approved first and proven second. A section whose content cannot
be known before the build is `[TBC — this build]` at Gate 1, never a plausible
guess — a guessed budget that survives review becomes a number someone plans
against.

## 3 · Build order: the ladder is the vault's, not yours

Priority is **increasing complexity**, and the vault establishes it. Do not
reorder for convenience. Each rung teaches a primitive the next rung assumes,
and the catalog is a teaching sequence as much as an inventory.

`cp-00-institutional-holders` sits below the ladder as your own warm-up rung and
is already built. The vault's 21 follow:

| Rung | Tier | Product | What it exists to prove |
|---|---|---|---|
| 01 | **T1** | `counterparty-reference-snapshot` | The contract fires. Identity authority hierarchy. The replay harness itself |
| 02 | T1 | `facility-terms-snapshot` | Anchoring on something other than a legal entity; `from_entity_freshness` against a document-dated source |
| 03 | T1 | `obligor-financial-spread` | Attribute-level temporal validity before any graph exists |
| 04 | **T2** | `corporate-family-tree` | First multi-store product. Multi-hop traversal, cross-shareholding cycles as findings |
| 05 | T2 | `credit-exposure-rollup` | Traversal + aggregation; the concentration denominator a flat product gets wrong |
| 06 | T2 | `collateral-and-setoff-coverage` | Typed edge vocabulary; coverage as a graph question |
| 07 | T2 | `client-360-coverage-graph` | High fan-out; where traversal cost becomes a design constraint |
| 08 | **T3** | `covenant-in-force-as-of` | **Flagship.** Ledger time-travel, supersession preserved |
| 09 | T3 | `treasury-liquidity-position` | Fast `λ_c` forcing on-demand derivation |
| 10 | T3 | `rating-and-spread-migration` | Per-signal decay curves |
| 11 | T3 | `credit-surveillance-early-warning` | Supersession cascading across downstream products |
| 12 | T3 | `fx-post-trade-reconciliation` | Two time axes that must be separately parameterised |
| 13 | **T4** | `covenant-cross-reference` | Passage-level lineage across documents |
| 14 | T4 | `credit-memo-context` | Algorithmic/semantic stage alternation; debt across a multi-agent handoff |
| 15 | T4 | `kyc-refresh-beneficial-ownership` | Entity resolution; ownership to person level |
| 16 | T4 | `abs-securitization-surveillance` | Loan-level fan-out; forces the materialization decision |
| 17 | **T5** | `mnpi-wall-enforcement` | Entitlement as formative constraint — the edge never materializes |
| 18 | T5 | `ib-opportunity-synthesis` | Projection `Π` across three principals |
| 19 | T5 | `aml-typology-match` | Policy-before-Similarity. **Synthetic obligor only, never a named real company** |
| 20 | T5 | `syndicated-lending-co-lender` | Cross-organizational federation under a negotiated envelope |
| 21 | T5 | `large-exposure-rwa-concentration` | Composes every primitive below it |

**Tier is not build order within a tier** — the vault's index order above is.
Where a product's `Prerequisites` name another product, that dependency
overrides the list.

---

## 4 · Phase 0 — gather, before you write a line *(Gate 1)*

For product `<slug>`:

**4.1 Read the vault article in full.**
`/home/parkave/obsidian-vault/wiki/context-products/content/<slug>.md`
Or `get_article("context-products", "<slug>")` over MCP.

Extract and hold separately — these are the vault's terms and you will not
alter them:
- decision & trigger, consuming principals
- counterfactual failure + which closed-taxonomy mode it names
  (`context-starved · temporally-incoherent · perspective-flat · policy-blind · evidence-free`)
- the four-question test result, **including partials and nos**
- tier, build order note, prerequisites, consumers
- **scope boundary** — record it verbatim; see §10 warning
- primitive taught, contrast pointer

> ⚠️ **Twenty of the 21 vault articles are on the older Q019 form**, where **§F
> means *Manufacture envelope*, not *Source binding & readiness*.** Only
> `counterparty-reference-snapshot` is on v0.3. Resolve vault sections **by
> heading name, never by letter.**

**4.2 Pull the data reality from ccf_dataprep.**

| Need | Where |
|---|---|
| §C rows as dataprep holds them | `validators/spec_coverage.py` — `read_catalog()` and the per-product manifests |
| §C/§F as dataprep read the vault | `docs/spec-digest.md` |
| Obligor cast, waves, acquisition decisions | `docs/data-acquisition-plan.md` |
| Known defects and limits | `docs/known-issues.md` |
| Ontology IRI bindings | `ontology/`, plus the vault's `fibo-iri-binding` mirror |
| Anchor-cast satisfaction | `validators/cast_audit.py` |
| Live estate | the `ccf_v2.*` schema |

**Measure, do not assume.** Every count, coverage figure and match rate in your
spec must come from a query you ran or a dataprep artifact you can cite.
`bound is not the same as materialized` — an IRI documented in the binding
mirror does not mean rows exist against it.

**4.3 Re-read the Standard.**
`public/reference/specifications/Context_Product_Specification_Standard_v0-3.md`

Known errata — the document's own cross-references are stale in six places, so
resolve by heading, not by the number cited: response envelope is **§8** (cited
as §10, twice); intent registry **§11.1** (cited §13.1); projection plans
**§11.2** (cited §13.2); change classes **§12** (cited §14, twice); capability
classes and operator vocabulary **§10.1/§10.2** (cited §11.1/§11.2).

**4.4 Use CP-SPEC-000 as your template, not CP-SPEC-001.**
`examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`

CP-SPEC-001 predates the current form. CP-SPEC-000 carries the embedded §0, the
B.1–B.5 / C.1–C.5 / D.1–D.7 / **E.1–E.5** / F.1–F.4 / G.1–G.3 structure, the
`[TBC]`-with-owner register at F.2, and the mandatory data banner. Match it.

---

## 5 · Phase map — Gate 1, then build, then Gate 2

| Phase | Gate | What you do | Spec sections |
|---|---|---|---|
| **P1 · Frame** | 1 | Read vault article; confirm the product is real and belongs | §0, banner, front matter, §A, §B.5 |
| **P2 · Bind** | 1 | Map every element to a real table/column and IRI; measure coverage | §C.1–C.3, §F.1, §F.3 |
| **P3 · Trap** | 1 | Find what the data does *not* support cleanly; choose bindings, record their cost | **§C.4**, §C.2, §F.4 |
| **P4 · Design** | 1 | Contract elements, parameter surface, operator composition, intended gates and criteria | §B.1–B.4, §D.1–D.3, §D.7, §E.1–E.5, §G.2 *(budgets and measured values `[TBC — this build]`)* |
| **▶ GATE 1** | — | **Send to Dave. Stop. No implementation until approved.** | Spec complete except `[TBC — this build]` |
| **P5 · Assemble** | 2 | `assembler.py`, `produce.py`, `deployment.py`, `ccf_config.yaml`, `backends.yaml` | code; `artifacts/*.yaml` |
| **P6 · Run** | 2 | Execute; capture budgets, hashes, witnesses | §D.2 budgets, §D.4, §D.5, §D.6 |
| **P7 · Gate** | 2 | Fixtures; make each gate fail deliberately once | §D.7 fixture IDs, §G.2 results |
| **P8 · Operate** | 2 | Measure decay against read frequency; confirm posture | §E.1 basis, §E.3 posture, §G.1, §G.3 |
| **▶ GATE 2** | — | Clear every `[TBC — this build]`; file returns to vault and dataprep | §F.2 register closed |

A Gate-1 section written from imagination is the failure this map exists to
prevent. A Gate-2 value that contradicts an approved Gate-1 decision is a
**deviation** — see §2.

## 6 · Section-by-section recipe

Throughout: **SOURCE** = whose term it is · **NEVER INVENT** = the failure mode
· **DISCHARGED BY** = what proves it.

### §0 · What this document is

Restate the standard's five rules, the four-question test, placeholder
discipline, the section skeleton and front matter — as CP-SPEC-000 does. This is
deliberate duplication so the spec is readable standalone.

**Then the banner. It is mandatory and it is not boilerplate.**

CP-SPEC-000 opens with `READ THIS BEFORE YOU READ A NUMBER`, stating that the
examples **teach method, not figures**, with that product's own *measured*
provenance counts. Reproduce this with **your product's measured numbers**, and
follow CP-SPEC-000's discipline of repeating the statement **beside each figure
cluster** rather than leaving it as a header a reader scrolls past.

For `aml-typology-match` (rung 19) the vault adds a hard constraint: **synthetic
obligor only, never a named real company.** Carry it into the banner.

### Front matter

**SOURCE:** vault (registry name, tier, build order, what it resolves) ·
you (Assembly Mode, cost band, lifecycle).

Registry name is `domain.product.vN`. **Assembly Mode is a registration-time
commitment** — a documented decision with a one-sentence cost/quality/determinism
rationale, not a description of how you happened to build it. Modes 2 and 3
require §B.3.

**Capability gate above §A** where the product cannot be built without a
capability the estate may not have. This is a scheduling statement.

### §A · Decision frame

**SOURCE: vault, entirely.**
**NEVER INVENT:** the counterfactual, the failure-taxonomy mode, or the
four-question result. If the vault's four-question result carries a `no` or a
`partial`, **carry it through unchanged** — `counterparty-reference-snapshot` is
admitted on one no and one partial, stated openly, and that honesty is the
standard working.

**You add one thing:** the **counterfactual acceptance test** — the vault's
narrative counterfactual rewritten as a numbered procedure ending in an
assertion that can fail. State the query, both answers, and the condition under
which they must differ.

**DISCHARGED BY:** a test in the example that runs the counterfactual and fails
if the two answers agree.

### §B · Contract

**B.1 — the nine elements.** Schema · Freshness SLA · TTL · Policy Binding ·
Lineage · Semantic Version · Discovery · Addressability · **Assembly Mode**.

**SOURCE: you.** The vault's element values are theoretical and have been
measurably wrong — its `counterparty-reference-snapshot` set `λ_c ≈ 24h` where
the real half-life is ~365 days, having substituted publication cadence for
decay. Take element *intent* from the vault; take *values* from your runtime.

Rules that are not negotiable:
- **Schema** binds every entity, relationship, attribute and measure to an
  **ontology IRI**, and links a machine-readable artifact at
  `schemas/{payload_type}.v{MAJOR}.json`. *Prose in a table cell is not a
  contract.*
- **Freshness SLA** is **per signal class**, never one value over a mixed payload.
- **TTL** carries `ttl_anchor` **and states how `expires_at` is computed.** For
  `from_entity_freshness` that is source publication time, not request time —
  *a 23:00 request against an 06:00 file gets 7 hours of validity, not 24.*
  **Nine vault specs declare this anchor and none define the computation.** You
  must.
- **Lineage** is the full list: `operators_invoked[]` · `graph_snapshot_at` ·
  `policy_version` · `projection_plan_id` · passage anchors where a claim rests
  on text · `context_debt` · `payload_hash` · `model_record`. Plus any
  product-specific authority field. `operators_invoked` carries **typed operator
  references** — `ResolveOperator@entity-master.v1.0` — **not bare names**,
  because lineage strict equality compares them.
- **Discovery** is registered only after §G is complete.

**B.2 — classification and residency.** Data classification (highest of any §C
element) · information barrier · residency · cross-border serving. **The
suppression rule:** where policy excludes content the payload carries **no
count, marker or placeholder**. A "3 items hidden" marker is itself a
disclosure.

**B.3 — model-risk annotation.** Modes 2/3 only: pinned model and version,
pinned temperature, versioned prompt, model-risk registration, the
**substrate/presentation boundary**, and the **smoothing control** — how the
design stops the model reconciling a conflict the substrate deliberately
surfaced. Mode 1 states *"not applicable — no model in the trust path."*

**B.4 — request parameter surface.** Every parameter with a **Moves** column
naming which dimension it moves (`E` anchor · `R` scope · `T` reconstruction ·
`P` envelope · `Π` perspective · a measure). A parameter that moves nothing is a
formatting flag — push it to the consumer.

Required on every product: an anchor identifier, `intent`, `debt_tolerance`.

**Declared-but-inert parameters** must be declared and **fail explicitly** with
`not_supported_at_tier`, never silently succeed. This keeps the request surface
uniform so consumers do not learn a second calling convention at a higher tier.

**B.5 — prerequisites, consumers, scope boundary.**
**SOURCE: vault** for prerequisites and consumers (it owns build order).
Consumers must be **named individually** — supersession cascades and MAJOR
version notification both need a reverse dependency list, and *"every other
product"* cannot serve as one.

> ⚠️ **Scope boundary — treat with suspicion.** This is the field that broke.
> Copy the vault's sentence verbatim, then **check it against your §C and your
> payload.** If your payload declares a field the vault's scope excludes, you
> have found a live conflict: **do not silently resolve it.** Record it, raise
> it (§11), and mark the field `[TBC — ruling]` until it is settled.

### §C · Data catalog

**SOURCE: ccf_dataprep, entirely.**

**C.1 — element table.** One row per element, *not per table*:

`Element · System of record · Provenance class · Classification · Capability class · G dimension · Ontology IRI`

- **Provenance class** is the closed list: `internal-SOR · vendor ·
  public-filing · derived · inherited`. `synthetic` is **not** a provenance
  class — it is a property of the estate and belongs in the §0 banner or its own
  column. The vault conflates these; do not copy that.
- **Capability class** — never a product name. `relational ·
  bitemporal-ledger · graph-traversal · document-passage · vector-index ·
  federated-external · in-memory`. This column says what the store must *do*.
- **Store · schema · table — name it.** Per §1.1 you are writing the
  implementation artifact, so §C.1 carries a store column alongside capability
  class, and §F.3 states the estate binding collectively — including **which
  stores this product does not read, and why.** The vault article's store
  assignment is a **proposal** to confirm against the real estate, not residue
  to discard and not an authority to copy. **Deployment detail — host, port,
  credential — never appears.**
- **G dimension** — every element lands in `E · R · T · P · Π · L · schema`, or
  it is not context.
- **Ontology IRI** — unbound elements block registration. Foundational party
  terms are in **OMG Commons** (`cmns-org:`), not FIBO; only `Corporation` stays
  as `fibo-be-le-cb:Corporation`. A validator asserting every IRI begins
  `spec.edmcouncil.org` will reject correct data.

**C.2 — capability decomposition.** Decompose each required capability into
separable properties with `Widely available · sometimes · rare` and what is
deliverable if each is absent. State the **interim posture** where the answer is
partial. Estates fail capabilities partially, and the partial is the finding.

**C.3 — correlation key, single-writer, identity authority.** The join key,
where the crosswalk lives, its **measured** coverage. One authoritative writer
per element. Where an anchor does not exist for every entity the product serves,
tabulate entity classes, identity authority, and the **freshness ceiling each
implies** — an anchor that silently excludes a population propagates the
exclusion catalog-wide.

**C.4 — the data traps.** CP-SPEC-000's most valuable section and the one with
no vault equivalent. **Where the data does not cleanly support what the spec
wants, name the trap, the binding you chose, and what that choice costs.**
CP-SPEC-000 records ~22.5% weak issuer matching **by design** rather than as a
defect. A spec with no traps section has either a perfect estate or an
unexamined one.

**C.5 — what this data is.** Restate the synthetic/engineered posture beside the
figures, per the banner discipline.

### §D · Assembly recipe

**SOURCE: you, entirely. This section is code before it is prose.**

**D.1 — client call.** The literal request, parameters populated. Where the
product has a forensic and a live case, show the **forensic** one — it exercises
more surface.

**D.2 — operator step table.** One operator per step:

`# · Operator · Capability class · Inputs · Emits · Failure behavior · p95 budget`

Operators come from the closed vocabulary only: **Resolve · Policy · Projection
· Traversal · Enrich · Similarity · Evaluate · Federate**. Retired names —
Batch Enrich, Temporal Traversal, Aggregate/Score/Reconcile/Rank, Compose — are
not operators. Final step is always contract assembly.

**State the budget total and the envelope it is measured against.** A total at
97% of envelope is a design finding: say which step dominates and what the first
optimization would be.

**Mirror this table into `artifacts/assembly-recipe.yaml` with a WITNESS per
step.** A step nothing executes is RED.

**D.3 — step detail.** Prose only where a step carries a non-obvious discipline.
Two recur and must be written wherever they apply:
- **Policy runs first even when it appears to do nothing.** At T1 it is an
  entitlement check; at T5 it is what makes a restricted edge structurally
  absent. Learned from the first product or retrofitted painfully.
- **Two filters on two axes are two filters.** Separately parameterised,
  separately testable. Applying one silently answers a different question.

**D.4 — determinism class and payload hash.** `deterministic` (Mode 1) or
`substrate-deterministic` (Modes 2/3) — those exact enum strings; they ship in
the envelope. Publish a hash over the deterministic portion excluding
`assembled_at`. **Replay asserts hash equality, not similarity.**

**D.5 — replay statement and falsifiable replay test.** A numbered procedure
ending in an assertion that can fail: serve and record · mutate state ·
re-derive live and confirm the new value · re-derive at the recorded snapshot
and confirm the **original** returns. If the last step returns the new value,
`graph_snapshot_at` is decorative.

Two time axes ⇒ a second test asserting the axes **disagree** under a
constructed case. Agreement means a filter was dropped.

**D.6 — emitted contract.** The §8 envelope populated **with types**. This is
what consuming teams code against and what CI validates. `extra=forbid` is a
build-time invariant. *Prose describing a payload is not a payload.*

**D.7 — validation gates.** Six universal, without re-argument: empty-operator
guard · lineage strict equality · TTL bounds · debt gate · suppression silence ·
classification containment. Then **product-specific gates**, each a testable
assertion naming the defect it detects, cross-referenced to a fixture ID.

**Error mapping** — condition → raising step → response. `404` unresolvable ·
`403` not entitled, no detail on what exists · `400 not_supported_at_tier` ·
`409` debt gate with the debt block · `503` mandatory input unavailable, source
class named · `200` with notices for non-mandatory. **Silence is not a negative
answer** — an unretrieved screening source is not a clean screen.

### §E · Volatility, debt & materialization

**SOURCE: dataprep for calibration evidence, you for the model and posture.**

**E.1 — half-life table.** Per signal class: `λ_c` · **calibration basis** ·
decay driver · supersession event · owner.

> **λ_c is a half-life, not a refresh cadence.** A daily file does not make a
> legal name decay daily. This is the single most consequential error in the
> vault's version and it must not propagate.

Calibration basis is `illustrative · expert · measured`. **State plainly where
no row is measured.** λ_c is Control Plane configuration; your table is a
proposal.

**E.2 — debt model and per-component debt.** `D_c = 1 − (F · C · S)`,
multiplicative so a collapsed dimension forces escalation. **Normalize F over
required signal classes, not over classes present**, or losing a source improves
the score.

Then the per-component table: `Component · May be absent? · D_c contribution ·
Behavior when absent`. **Debt decomposes per claim, never only per product** —
four claims with one input missing returns three evaluated and one
`NOT_EVALUABLE`, not a product-level failure.

Check your contributions against `debt_tolerance`. A single optional component
contributing more than the default tolerance means the product refuses to serve
whenever it is absent — that is a design finding, not an accident.

**E.3 — materialization posture.** `materialized · derived-on-demand · split`.
The test is mechanical: **if the fastest-moving input's λ_c is shorter than the
intended cache window, materialization is wrong.** Feed it a real λ_c — fed a
cadence, it returns the wrong architecture while looking correctly applied.

State the **cache key** explicitly: tenant · schema · plan id · snapshot · time
parameters · principal binding · every parameter that changes the payload. A
missing key parameter is a correctness defect presenting as an intermittent one.

**E.4 — supersession triggers.** Each **local** or **cascading**; for cascading,
the named downstream products. Re-derivation is **lazy** — invalidate for next
request, never re-materialize eagerly.

**E.5 — the expiry and its refusals.** Per CP-SPEC-000: state what expiry
actually produces at the delivery boundary and which refusals it can raise.

### §F · Source binding & readiness

**SOURCE: dataprep, entirely.**

**F.1** — per element: system of record · interface & cadence · **available
today** (`yes · partial (name the fields) · no`) · gap owner · blocker.

**F.2** — **every `[TBC]` in the document, with an owner.** This is the register
that makes the cross-agent discipline auditable. Each row names the term, the
owning agent, and what was asked. **No spec passes review with an unowned gap.**
*"Does not exist yet" is a valid state; unattributed is not.*

**F.3** — access path · **identifier reality** (does the key exist end to end,
who owns the crosswalk, measured coverage) · **history depth** (where the source
publishes snapshots without history, say *start retaining deltas now* — history
not captured cannot be reconstructed later) · text-source boundary ·
**first-build volumetrics**: the population the first build needs for every gate
and counterfactual to have something to act on. Where a required case does not
occur naturally, **widen the sample until it does**.

**F.4** — **recorded findings that are not `[TBC]`**, because they need no
decision to build. Keep this distinct from F.2; conflating a finding with a
blocker inflates the blocker list and hides the real ones.

### §G · Operate & govern

**SOURCE: you.**

Accountable owner (roles, not individuals) · service objectives (p50/p95,
volume, concurrency, payload bound, **absolute** per-call cost alongside the
relative band) · degradation contract per input class with **mandatory classes
named** · debt model · observability (per-operator latency, `D_c` distribution,
gate failures by gate, cache hit rate, entitlement denials, degradation-branch
frequency, supersession invalidations — this is the evidence base that moves
λ_c from illustrative to measured) · retention and record of record · test
fixtures · lifecycle (`draft · in-build · certified · deprecated`).

**G.1** — restate the expiry obligation where an operator will look for it.

**G.2 — acceptance criteria.** Assertions **specific to this product**, each
independently verifiable, each phrased so it can fail. Close with the **open
decisions blocking build**, named by their §F.2 row.

**G.3 — catalog contribution.** What this product proves that nothing earlier
proved, and what it deliberately does not prove. The vault's *primitive taught*
is your input. A product that proves nothing new is a merge candidate; a product
whose exclusions are unstated invites a reviewer to read a tier boundary as an
oversight.

---

## 7 · Where the spec lives, and the artifacts around it

### 7.1 · The spec lives in the example, not in the docs tree

**A product spec belongs at `examples/cp-NN-<slug>/spec/CP-SPEC-NNN_<Name>.md`,
and is created there at Gate 1.** It is never authored in
`public/reference/specifications/`.

This follows from §2 rather than from filing preference. A spec whose §D steps
are discharged by witnesses in `artifacts/assembly-recipe.yaml`, and whose
emitted contract is validated by CI against code in the same directory, has to
be **versioned with the thing that proves it**. Move it into a documentation
tree and the claims and their evidence can drift in separate commits — which is
the entire failure this recipe exists to prevent.

The two trees have different jobs:

| Path | Holds | Example |
|---|---|---|
| `examples/cp-NN-<slug>/spec/` | **product specifications** — one per example, co-versioned with the code that discharges them | `CP-SPEC-000-institutional-holders.md` |
| `public/reference/specifications/` | **reference documents** — things that govern specs but describe no product | `Context_Product_Specification_Standard_v0-3.md`, this recipe |

**ONE CANONICAL SPEC, AND NO SECOND COPY THAT CAN DRIFT.** A product
specification lives in its example's `spec/` directory and **is not duplicated
into `public/`**. There is no second location and no per-spec nav entry.

| | Where |
|---|---|
| **Canonical, and the only copy** | `examples/cp-NN-<slug>/spec/`, from Gate 1 onward — versioned with the artifacts and code that discharge it |
| **`public/reference/specifications/`** | reference documents that **govern** specs and describe no product: the authoring standard, this recipe, the delivery companion |

Public documentation **may reference or summarize** a CP-SPEC — link to it,
quote a clause, explain what a rung proves. It must not create a second copy of
the document.

**This corrects what this section used to say, and the correction is a
documentation-rule fix rather than any product's deviation** (Dave,
2026-09-12). The previous text directed a copy into
`public/reference/specifications/` with a nav entry after Gate 2, and cited
`mkdocs.yml` for it. `mkdocs.yml` says the opposite, in a ruling of the same
author dated 2026-08-29:

> *"Individual CP-SPECs do NOT live here. A specification lives in its own
> example's `spec/` directory, beside the artifacts and code it governs.
> `CP-SPEC-001` sat here only to bootstrap the authoring process and was deleted
> at `59831ea5` once it had served that purpose — by then it had drifted to 640
> lines against a 1,355-line canonical source, silently dropping every section
> that recorded an open question."*

**The precedent is unanimous and was measured before this edit: no CP-SPEC for
`cp-00` through `cp-08` is published under `public/` at all.** Eight gates
closed without it. The surviving instruction here was stale, and it was caught
at rung 9's Gate 2 by an executor who stopped rather than following it.

**Why the deleted copy is the argument.** A specification is proven by the
artifacts and tests beside it; a copy somewhere else is proven by nothing, and
the first thing it loses is the sections recording open questions — which is
exactly what happened, and it happened silently, because a stale copy renders
perfectly well.

> ⚠️ `public/` has a strict docs build. **Any file you add under `public/`
> without a nav entry fails `mkdocs build --strict`.** That still holds for the
> reference documents this directory does carry.

> **`CP-SPEC-001_Counterparty_Reference_Snapshot.md` is a deliberately placed
> exemplar — *"what a spec would look like for counterparty reference"* (Dave,
> 2026-08-29) — and it is a **control, not a source.**
>
> The plan for rung 01 is that you author the spec **fresh from this recipe**,
> and Dave then compares your output against that file **by hand**. That
> comparison is a test of the recipe as much as of your spec, and it only works
> if you have not read CP-SPEC-001 as an input. **Deltas are expected and are
> the point.** Where your spec differs, the difference is the finding.
>
> So: author at `examples/cp-01-counterparty-reference-snapshot/spec/`. Do not
> copy from CP-SPEC-001, do not reconcile against it, and do not treat its
> values as authoritative — it predates the example-based structure, has no
> `artifacts/`, no witnesses, and the error classes cataloged in §10.2.

### 7.2 · The example layout

The spec is one file in a runnable example. Match `cp-01`'s layout:

```
examples/cp-NN-<slug>/
├── spec/CP-SPEC-NNN_<Product_Name>.md
├── artifacts/
│   ├── assembly-recipe.yaml   ← §D.2 as data, with a WITNESS per step
│   ├── expected.yaml          ← what the served product should contain
│   ├── question.yaml          ← the caller's vocabulary, read-side
│   └── ttl.yaml               ← the class TTL and its ceiling
├── assembler.py  produce.py  run.py  deployment.py
├── backends.yaml  ccf_config.yaml
├── page/                      ← build_page.py + template.html committed, render is not
├── README.md
└── summary_explanations.md    ← the banker-facing document
```

**The `page/` directory and `summary_explanations.md` are not optional**, and
what goes in them, plus the `example-cp-NN` target, the venv discipline and
the validation pass, are governed by
[How an example is delivered](example_delivery.md) — which is authoritative for
everything downstream of this section. This diagram is the summary; that
document is the recipe.

All `artifacts/*.yaml` validate against
`docs/schemas/ccf.declared-artifact.json`.

Follow `cp-00`'s `expected.yaml` discipline: **it derives nothing from a run.**
When artifacts change, run the suite, review the failure, and deliberately edit
the file in the same commit — so an expected-output change is an edit to a
reviewed artifact rather than a refreshed transcript.

---

## 8 · Definition of done — the specification

Ship when all of these hold. This is the standard's §15, plus what this pipeline
adds.

**These are the SPECIFICATION's conditions and they are half the deliverable.**
The example's conditions — the `make` target, the venv, the README run block,
the documentation page, the banker summary, the verbatim-output check and the
validation pass — are [How an example is delivered](example_delivery.md) §11.
Both lists must hold before anything is presented to Dave.

- **The spec was approved by Dave at Gate 1 before any implementation code was
  written**, and every Gate-2 deviation from the approved design was taken back
  to him rather than absorbed
- All seven sections present in order, with §0, front matter, capability gate
  and the data banner
- Four-question result carried from the vault **including partials**
- Nine contract elements populated, Assembly Mode with rationale
- Classification, residency, information-barrier complete; model-risk complete
  for Modes 2/3 or "not applicable" for Mode 1
- Every §C element has SOR, provenance class, classification, capability class,
  G dimension and ontology IRI — and **no §C row names a database**
- Capability decomposition present where the estate answer is unknown, with
  interim posture
- Correlation key stated with **measured** coverage, or the measurement named as
  an F.2 gap
- Every §D step names one closed-vocabulary operator with capability class,
  emits, failure behavior and budget — **and has a witness in
  `assembly-recipe.yaml`**
- The four composition invariants hold: Policy before any graph read · Resolve
  before Traversal · Enrich always batched · algorithmic substrate before any
  semantic stage
- Determinism class stated with an enum value; payload hash defined
- Replay statement plus a numbered falsifiable replay test that has been **run
  and observed to fail** when the snapshot is bypassed
- Emitted contract shown with types, conformant to the §8 envelope, passing
  `extra=forbid` in CI; error taxonomy mapped to steps
- Six universal gates plus product-specific gates with fixture IDs, **each made
  to fail deliberately at least once**
- Half-life table carries calibration basis and owner per row, and **no λ_c is a
  publication cadence**
- Per-component debt table present; contributions checked against
  `debt_tolerance`
- Materialization posture derived from measured λ_c against read frequency;
  cache key complete
- Every `no` or `partial` in §F has a named gap owner; volumetrics stated
- §G complete; consumers named individually; cascading supersession targets named
- **F.2 register complete — every `[TBC]` carries an owning agent**
- Acceptance criteria are failable assertions; blocking decisions named

---

## 9 · Cross-agent placeholder discipline

| Situation | Write |
|---|---|
| Vault has not framed something you need | `[TBC — vault]` + what you asked |
| Data reality unknown or unmeasured | `[TBC — ccf_dataprep]` + the measurement needed |
| Vault framing and build evidence conflict | `[TBC — ruling]` + both readings, verbatim |
| You have not built it yet | `[TBC — this build, phase Pn]` |

Never `[TBC]` bare. An unowned marker is an unassigned risk, and the F.2
register is what makes it collectable.

---

## 10 · Known conflicts — do not resolve these silently

**10.1 · `counterparty-reference-snapshot` grade and coverage — NOT blocking.
Author to the vault.**

The vault's scope boundary says *"identity only — no exposure, **no grade**, no
relationship."* CP-SPEC-001's payload declares `internal_risk_grade`,
`coverage_rm_id`, `coverage_team`, `coverage_lob` and an `internal_risk_grade`
freshness class. `ccf_dataprep` built to the vault's reading and carries **none**
of those fields.

**This is not a conflict between two authorities.** Scope boundary is the
**vault's term** under §1, and CP-SPEC-001 is an exemplar for later comparison
(§7.1), not a source. So:

- **Author to the vault's scope.** No internal overlay in rung 01.
- The overlay is then **not a debt component at all**, so CP-SPEC-001's
  0.30-against-0.25 `debt_tolerance` collision — and the `409` it implies —
  **does not arise.** That failure exists only under a per-component table
  counting a field the spec does not carry.
- **`ccf_dataprep` is already aligned.** Nothing needs regenerating.

If your build disproves the vault's scope, that is a §11 return, not a reason to
stop.

> **A ruling that was inferred rather than made.** On 2026-08-29 Dave pasted
> **both** documents — the vault's `counterparty-reference-snapshot` article at
> 03:23 MST with *"this is the one we need to build to"*, and the authoring
> Standard nine minutes later. Together that is the framing input and the
> structural basis: **the direction was unambiguous.**
>
> What it was not is a decision on the grade/coverage conflict, which §10.1 had
> marked blocking. **A document handover settles what you build to; it does not
> close a named conflict.** Those are closed by an explicit decision, named, or
> not at all — so **ask for one by name and wait.** Declining to close it alone
> was correct, and the inference pointed the right way.

**10.2 · Vault articles carry theoretical values that have been measurably
wrong.** Documented cases in `counterparty-reference-snapshot`: λ_c set to
publication cadence (24h vs ~365d); materialization posture inverted as a
consequence; `operators_invoked` as bare names; missing `payload_hash`,
`model_record` and the per-attribute authority field; a parameter surface
missing `debt_tolerance` and the inert `as_of`. **Assume the same class of error
in the other twenty.** Take framing from the vault; take values from your build.

**10.3 · The `references/` copies are history, not sources.**
`references/CP-SPEC-001_..._v2.md` and
`references/CP-SPEC-001_..._v0-3-restructure.md` are prior drafts. Read them for
audit history; author nothing from them. Same standing as CP-SPEC-001 itself
(§7.1).

**10.4 · Twenty vault articles are on the Q019 form** where §F means
*Manufacture envelope*. Resolve by heading name.

**10.5 · The vault's catalog count is stale** — it says 22 product specs in two
places; the measured figure is **21**, of which **20** declare no Assembly Mode.

---

## 11 · The return path

When your build contradicts an input, **send it back** — the failure this
pipeline exists to prevent is a correction that stalls at the boundary.

- **To the vault:** write into `~/.agent-exchange/<your-agent-id>/outbox/` as
  `<YYYY-MM-DDTHH-MM-SSZ>-<slug>.tmp/` containing `message.md` plus attachments,
  **then rename to drop `.tmp`** — the rename is what publishes it. A message
  left as `.tmp` never arrives, and this has already happened once: dataprep's
  2026-08-28 consumer signal sat unpublished until it was found by hand. State
  what your document **removes**, not only what it adds.
- **To ccf_dataprep:** same channel, their box is `ccf-dataprep`.
- **Your box is `ccf-sdk`** — `/home/parkave/.agent-exchange/ccf-sdk/`, with
  `inbox/`, `outbox/` and `_archive/`. Use that id, not a new one: a duplicate
  under a different id splits you into two agents.

Send back at minimum: any scope-boundary conflict, any λ_c the build disproves,
any element the vault names that the estate cannot supply, and any capability
the estate fails.

---

## 12 · Summary

1. Read the vault article — take **framing**, never values.
2. Pull the data reality from `ccf_dataprep` — **measure**, never assume.
3. Structure to the **Standard v0.3**, templated on **CP-SPEC-000**.
4. **Author the spec first, at `examples/cp-NN-<slug>/spec/`** — it is step one
   of the example project, and it lives with the code that will prove it. Mark
   what only the build can know as `[TBC — this build]`.
5. **▶ Send it to Dave. Stop. Nothing is implemented until he approves it.**
6. Build the example; fill the measured terms; clear every `[TBC]`. A build that
   disproves an approved term is a **deviation** — take it back, do not absorb it.
7. Never write another agent's term. `[TBC — owner]` instead.
8. Every claim discharged by something that runs; every gate made to fail once.
9. Send contradictions back, and **remember the rename**.
10. Work the ladder in order. Complexity is the vault's call, not yours.

``````

</details>

<a id="source-implementation"></a>

<details>
<summary>Implementation walkthrough — refreshed 18 October 2026, SDK v1.0.2</summary>

Path: `05-reference/02-context-product-producer/examples/CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD.md`

``````text
# CP-03 — Obligor Financial Spread — Canonical

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-03-canonical-obligor-financial-spread/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD_ANALYSIS.md) · [HTML reading edition](CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-03-canonical-obligor-financial-spread/README.md`  
**Qualified specification:** `examples/cp-03-canonical-obligor-financial-spread/spec/CP-SPEC-003C_Obligor_Financial_Spread_Canonical.md`  
**Qualified source:** `examples/cp-03-canonical-obligor-financial-spread`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-03-canonical-obligor-financial-spread/spec/CP-SPEC-003C_Obligor_Financial_Spread_Canonical.md`

Read it in this order before opening the Python:

| Spec section | What to learn | Where it lands |
|---|---|---|
| §A | decision, consumer, counterfactual, scope | README + acceptance tests |
| §B | product contract, request, TTL, policy/perspective | `ccf_config.yaml` + payload |
| §C | sources, identity, ontology, data traps | acquisition + environment/source declarations |
| §D | operators, projection, gates | `acquisition.py`, `deployment.py`, `projection.py`, `produce.py` |
| §E | half-life, Context Debt, materialization | config + assessment code |
| §F | source readiness and limitations | environment/source artifacts + findings |
| §G | acceptance and operational evidence | tests, gates, run evidence |

As you read the code, ask: **which approved spec term is this implementing?**

## Why this example exists

The primary paved-road implementation example. It modernizes the historical CP-03 without editing the frozen specimen and demonstrates how a current Context Product should separate configuration, environment, acquisition, graph state, projection, debt assessment and a very thin product spine.

## The question

> What is the obligor's period-aligned financial spread under the requested reporting basis, which filings asserted each figure, and is the resulting context fresh/complete enough to serve?

## What to understand before you run it

- This is the default code-generation precedent for a normal new product.
- Each dated financial fact becomes fabric state; projection and Debt both read the governed GraphView.
- `intent` is a top-level request axis, not a duplicate ordinary argument.
- Policy-bound request values are effective request state, not writes over resolved artifacts.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_03C_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_03C_POSTGRES_SCHEMA='ccf_v2'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-03-canonical-obligor-financial-spread/spec/` | Approved product contract and source/data traps. |
| `examples/cp-03-canonical-obligor-financial-spread/ccf_config.yaml` | Product class, request contract, operator parameters, TTL/half-life/debt/policy declarations. |
| `examples/cp-03-canonical-obligor-financial-spread/ccf_environment.yaml` | Names of source/substrate/door environment values; no secret values. |
| `examples/cp-03-canonical-obligor-financial-spread/acquisition.py` | Source-only leg; deliberately imports no CCF. |
| `examples/cp-03-canonical-obligor-financial-spread/deployment.py` | SignalEnvelope mapping, assessment and declared product predicate. |
| `examples/cp-03-canonical-obligor-financial-spread/projection.py` | Π from governed GraphView. |
| `examples/cp-03-canonical-obligor-financial-spread/produce.py` | The paved road: plan factory + open_product + opened.answer. |
| `examples/cp-03-canonical-obligor-financial-spread/run.py` | Demonstration caller and variations. |
| `examples/cp-03-canonical-obligor-financial-spread/FINDINGS.md` | Measured implementation/data findings. |

## Run it

```bash
make venv
make example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0
make example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=0.25
make -s example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0
make example-cp-03-canonical BASIS=latest-restated ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0
make example-cp-03-canonical PRINCIPAL=PRIN-KYC-004 ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- At wide tolerance the product serves; at the governed 0.25 tolerance the same question is withheld/refused with a replay reference.
- Changing basis changes the financial truth being requested and therefore the content address.
- Per-period/per-line filing dates remain visible; `NOT_EVALUABLE` is used instead of inventing zero.
- Expiry is anchored to the freshest filing in the admitted payload.
- A principal outside the jurisdiction grant gets no obligor in the admitted view.

Do not compare volatile content addresses or timestamps with prose unless the qualified SDK example itself publishes a pinned transcript. For exact byte-level claims, use the example's committed tests/transcript.

## How the example works

The general path is:

```
source estate (read only)
        ↓
acquisition / source interpretation
        ↓
SignalEnvelope(s)
        ↓
L2 assembly into governed L3 state
        ↓
L4 operators
        ↓
L5 projection Π over GraphView
        ↓
L6 Context Product gates / fulfillment
        ↓
served product OR governed refusal
```

The product-specific files above show where this rung changes that pattern.

## Variations to try

| Purpose | Command | Expected semantic change |
|---|---|---|
| Debt tolerance | `make example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=0.25` | Same assembled evidence, governed fulfillment changes to withholding. |
| Reporting basis | `make example-cp-03-canonical BASIS=latest-restated ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0` | Payload figures/basis and content address change. |
| Principal | `make example-cp-03-canonical PRINCIPAL=PRIN-KYC-004 ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0` | Policy-shaped view changes/refuses. |
| Alternative obligor | `make example-cp-03-canonical LEI=549300D0WZR1VI2QGB24 ASKED_AT=2026-08-29T12:00:00+00:00 DEBT_TOLERANCE=1.0` | Different subject and evidence. |

## Validate it

```bash
CCF_REQUIRE_ESTATE=1 PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_03_canonical_output.py tests/examples/test_cp_03_canonical_cross_deployment.py tests/examples/test_cp_03_canonical_paved_consumer.py -q -rs
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- Modern two-document paved-road deployment.
- GraphView discipline for projection and Debt.
- Per-attribute temporal/provenance semantics.
- Governed fulfillment by Debt tolerance.
- Canonical successor can replace an old implementation without rewriting the frozen specimen.

## What it does not prove

- That the example's half-lives/tolerances are production recommendations.
- That all financial spreading domains use the same line vocabulary.
- Decision Replay replacement environment mechanics currently under D-IMPL-346/347 work.

## Spec → code lesson for Cowork

This is the default structural code-generation target. Cowork should copy the separation and paved-road shape, not the domain values, table names, thresholds, or financial vocabulary.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.
``````

</details>

