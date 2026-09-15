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
| TTL | 30 days, **declared** `from_entity_freshness` on the freshest filing in the payload; **served** `expires_at` runs from the decision instant (`CP03C-F-01`); the window itself is held by the declared product gate |
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

`backends.yaml`: two environment variables, `CCF_CP_03C_POSTGRES_DSN` and
`CCF_CP_03C_POSTGRES_SCHEMA`, names and remedies only. The v2 namespace is
`ccf_v2`; `ccf_dataprep/.env` names v1. Read-only; the role needs `SELECT`.

### F.4 Findings

Raised in `FINDINGS.md`, adjudicated under `D-IMPL-315`. `CP03C-F-01` is the
SDK gap this tree surfaces and does not repair.

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
| `OFC-G06` | a spread whose freshest filing is outside the declared window at the asked instant is refused by the product's own gate |
| `OFC-G07` | `expires_at` is anchored on the freshest filing, as declared — **quarantined evidence of `CP03C-F-01`** |
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
