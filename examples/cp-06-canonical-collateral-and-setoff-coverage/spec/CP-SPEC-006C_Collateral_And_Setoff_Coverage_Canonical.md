---
product: credit-risk.collateral-coverage.v1
standard: v0-3
owner: vault
sdk_spec: cp-06-canonical
tier: 2
cost_band: "×1–2 — three PostgreSQL reads, eight Fluree reads, no LLM"
assembly_mode: 1
capability_classes: [relational, graph-traversal, in-memory]
prerequisites: [facility-terms-snapshot, corporate-family-tree]
topic: context-products
title: Collateral & Set-off Coverage (canonical) — Context Product Specification
generated: '2026-09-16'
---

# Collateral & Set-off Coverage (canonical) — Context Product Specification

**`CP-SPEC-006C` · the canonical rung-6 tree · Tier 2 · `credit-risk.collateral-coverage` @ `1.0.0` — the lane decided by measurement (§B.1, §D.4; measured 2026-09-16)**
**Fluree `fibo-v2` for edges, priority and the public register · PostgreSQL `ccf_v2` for valuations, balances and policy — read-only**

> What actually secures one credit facility and what can be applied against it
> — **written on the paved producer road (`D-IMPL-343`), serving the class
> `CP-SPEC-014` requires from another process, with the frozen rung-6
> specimen untouched.**

## 0 · What this document is

**This specification governs a SUCCESSOR, and the succession is disclosed
rather than glossed.** CP-14 Gate 2 slice 2 (Dave, 2026-09-15) classed the
frozen rung-6 specimen `examples/cp-06-collateral-and-setoff-coverage` **B**
under the A/B/C vocabulary — *leave frozen; a sibling would be the route* —
for three measured reasons: its pre-`D-IMPL-340` stdio door and `door.yaml`
carry a declared gate (`CSC-G12`) whose subject the paved road deletes; its
Π closes over two acquisition values (the facility's commitment and the
enforceable-jurisdiction register) that the graph does not carry, and the
road hands Π the effective request and nothing from the side; and
`D-IMPL-261` freezes the shipped specimen. Dave ruled the route on
2026-09-16: *a paved sibling tree, Gate 1 spec first; lane decided by
measurement; stop at the spec for a ruling.* This document is that Gate 1.

**It is producer substitution, not a renamed class.** The product identity is
unchanged: `credit-risk.collateral-coverage`, on the major lane `CP-SPEC-014`
§B.7 pins at a `1.0.0` floor. Which lane member this tree serves is **not
asserted here; it is measured at the build** (§D.4): the specimen serves the
same question today, so the successor can be held to the specimen's own
payload at a pinned instant, and the lane follows from whether it matches.

**It cites `CP-SPEC-006` nowhere as an authority** (`D-IMPL-327`, the
`cp-04-canonical` ruling). The business meaning the specimen fixed — the
reified pledge, the reverse walk, the two set-off predicates, the asserted
priority, the per-asset valuation date, the word for an unresolved debtor — is
preserved here and re-stated in this document's own words.

### 0.1 What this tree teaches, and what it does not

It teaches **coverage as fabric state, on the paved producer road**. Four
things, and they are the whole subject:

1. **boot / answer as two regions**, with the SDK owning the door, both
   operators, Π, the three L6 gates, the product's own declared gate, the
   five-dimension replay record, the query pins and the delivery — one
   `open_product` and one `open_door`, no `build_governed_resolver` and no
   hand-written door.
2. **The commitment IS the graph.** The specimen's Π received the facility's
   commitment and the enforceable-jurisdiction register through a closure over
   acquisition. Here the facility node carries its commitment as an attribute
   and every deposit node already carries its own enforceability; Π reads the
   view and nothing beside it. What the road would not pass from the side
   turned out to be a fact the graph should have held.
3. **`intent` is a governed axis**, declared once on
   `product_class.discovery.intents` and judged there — the specimen declares
   no discovery set, so an unknown intent is accepted there and refused here.
4. **The frozen specimen is the control**: the successor is held to the
   specimen's own payload at one pinned instant (§D.4), which is what lets the
   lane be measured rather than claimed.

It does **not** re-derive the collateral domain. The edge vocabulary, the
allocation rule, the haircut classes, the λ_c table and the twelve domain
properties the specimen's gates hold are the specimen's, carried forward in
`artifacts/` and `ccf_config.yaml` and restated in §G.1.

### 0.2 Placeholder discipline

No figure in this document is a promise. Every number in §A.2 and §E is a
measurement taken on 2026-09-16 against the live `ccf_v2` and `fibo-v2` estate
through the **frozen specimen** at the CP-14 instant, reproducible from
`examples/cp-06-collateral-and-setoff-coverage` with `asked_at` pinned, and
**no gate in §G.1 pins one of them**. The successor does not exist yet; its
first numbers are the build's, and §D.4 says what they must equal.

### 0.3 Front matter

`tier: 2` and `assembly_mode: 1`: three PostgreSQL reads (resolve, the two
policy registers, the batched enrichment), eight Fluree reads (the walk, its
reverse leg, two set-off predicates, the register and its amendments), one
allocation in Π. No LLM is reachable from any step.

### 0.4 The four-question test

*Who asks?* A credit officer sizing loss-given-default, or a composite such as
`CP-SPEC-014`, about one facility at one instant. *What changes the answer?*
The facility, the borrower scope the caller holds, the instant, the four
declared bases. *What does a `SELECT` not give you?* The priority the graph
reifies on the (facility, asset) pair, the set-off rights that live in a
different system, the debt in force, the content address, the record that
authorized it. *What is refused?* A facility the caller's scope may not walk
(an empty graph, never a redacted one), an unresolvable facility, an
over-allocated asset, an intent the class does not serve, `as_of`.

## A · Decision frame

### A.1 Counterfactual — `context-starved`

A memo writer reading `ccf_v2.collateral_pledge` gets four columns and no
priority, and cannot tell a first lien from a second recorded identically;
set-off rights never enter the frame at all.

### A.2 The uncomfortable conclusion, preserved

Measured through the frozen specimen at the CP-14 instant
`2026-09-07T12:00:00+00:00`, the class defaults in force (`apply_haircuts`,
`include_setoff`, `enforceable`, `priority`):

| | `FAC-5B8418` — BGC Group, Inc., the facility `CP-SPEC-014` names | `FAC-044206` — the specimen's demonstration anchor |
|---|---|---|
| commitment | 40,000,000 | 500,000,000 |
| collateral, after haircuts | 9,371,046 | 419,720,590 |
| enforceable set-off | 210,518,931 | 124,757,786 |
| coverage ratio | **5.4972 — covered, and covered by deposits, not by collateral** | 1.0890 — covered |
| assets pledged / shared with another facility | 1 (`COL-00019`, receivables) / 0 | 2 / 1 (`COL-00044`, senior) |
| set-off excluded as unenforceable | 4 accounts | 3 accounts |
| freshest valuation, and its age as the estate records it | 2025-12-20 — `valuation_age_days` 240 | 2026-08-15 — `valuation_age_days` 2 |
| `D_c` / signal | **0.3660 / `ok`** | 0.3769 / `ok` |
| payload content address (§D.4's baseline) | `d22b256eb343768f185ebbe09eed1949a44226cc1ffccc924550dbbc6f29a45c` | `8e3e567b194b1aad69bd08da53996dc89bbc4d3f9b335da119147c102d2ebe63` |

**Written out in full on 2026-09-18** (`D-IMPL-341`'s review): the table
carried eight-character prefixes, and with the frozen specimen no longer able
to serve — it declares the same anchor over a resolver the SDK can read no
clock from — those prefixes became the only record of the lane. The successor
was measured against them at each facility's control instant and matches to all
sixty-four characters. `CSCC-G13` is therefore a SNAPSHOT comparison: it goes
red on estate drift, and the answer then is to re-measure the evidence, never
to re-pin it to whatever the successor happens to serve.

**The memo's facility is covered five times over, and 96 % of that cover is
deposit set-off, not collateral.** A reader who takes the ratio at its face
misses that the collateral leg alone covers 23 % of the commitment and rests
on one receivables valuation dated 2025-12-20, which the estate ages at 240 days. The payload carries both
legs separately and dates the valuation; nothing here was tuned to change
that.

### A.3 A refusal is an answer

Every "no" this product says is returned as data with a replay reference —
the over-allocation gate, the contract, the intent set, a scope the caller does
not hold. Nothing raises for a question that merely has no answer.

## B · Contract

### B.1 The nine elements

| element | value |
|---|---|
| schema | `credit-risk.collateral-coverage` @ **`1.0.0`, measured** (§D.4, 2026-09-16): the successor's payload equals the specimen's at the pinned instant for both declared facilities, full canonical hashes `d22b256e…` and `8e3e567b…`, zero field-level differences — a second producer of the same product, satisfying `CP-SPEC-014`'s `1.0.0` floor |
| subject | the facility id, as `ProductRequest.subject` — the CP-14 question names the facility as the child's subject (`CP14-F-20`) |
| intent | `lgd-assessment` — declared on `discovery.intents`; judged, never an argument |
| freshness | `as-filed` (what `CP-SPEC-014` asks the collateral child at); `standard` retained for the specimen's own callers |
| TTL | **declared** `from_entity_freshness`; **served** `expires_at` runs from the freshest asset valuation date in the admitted view and the contract records it as `ttl_anchor_at` (since `D-IMPL-341`). Ceiling and window are both the **appraisal cycle** — `half_life.real_property_appraisal`, the valuation cadence governing 74 of this estate's 95 pledged assets — recalibrated 2026-09-18 from the 24-hour ceiling and one-day deposit-balance window this row previously carried, which named a cadence the anchor cannot read (`CP06C-F-05`, ruled). **Illustrative calibration** (`D-IMPL-323`). It does NOT establish that the undated deposit balances are fresh, and does NOT claim every asset was revalued within the window: per-asset valuation dates and ages stay in the payload, and `F` ages a marketable security under its own one-day cadence |
| assembly mode | 1 — algorithmic |
| operators | `policy.principal-subgraph` then `traversal.typed-neighborhood`, exactly two, policy before traversal |
| lineage | graph-supplied; every asset carries `provenance`, `valuation_date`, `lien_position`; every filing its number, dates and status |
| debt | `D_c = 1 − F·C·S`; `F` the SDK's freshness scorer over each asset's valuation age against its λ_c class; `C` the priced share of pledged assets; `S = 1` declared |

### B.2 Request parameter surface

| parameter | type | default | domain | note |
|---|---|---|---|---|
| `facility_id` | string | — | — | **required**; the anchor; unresolvable ⇒ refusal, never an empty payload |
| `borrower_scope` | array of string | — | — | **required**; what the policy operator admits on; a scope the caller does not hold yields an empty graph |
| `apply_haircuts` | boolean | true | — | at Π; changes the conclusion |
| `include_setoff` | boolean | true | — | widens `R` at acquisition |
| `jurisdiction_basis` | string | `enforceable` | `contractual` \| `enforceable` | at Π, off each deposit's own attributes |
| `shared_collateral` | string | `priority` | `priority` \| `pro-rata` | at Π |
| `as_of` | string | — | — | declared and refused, `not-supported-at-tier` |

`intent` is **not** a parameter. **The CP-14 question**, verbatim from the
consumer's mapping: `subject=<facility>`, `intent=lgd-assessment`,
`freshness=as-filed`, `parameters={facility_id, borrower_scope=[<obligor LEI>]}`,
no tolerance — the collateral contract takes none, and none is invented.

## C · Data catalog

Two stores, the specimen's own element table restated: 60 facilities and
their commitments; 95 `securedBy` edges and 95 reified pledges (93 primary,
2 subordinate); 91 assets with valuations aged 0–545 days; 120 deposit
accounts with 120 `setOffAgainst` and 73 `nettedUnder` edges; 6 haircut
classes; 12 jurisdictions of which 8 enforceable; 65 Florida UCC-1 filings
with 85 amendments, 13 carrying a termination; a debtor-name crosswalk of
which 1 of 16 is accepted.

### C.1 The traps, all load-bearing

1. **Priority is an authoritative input on the reified pledge** (`D-IMPL-321`):
   this product does not derive legal UCC priority from filing dates.
2. **The register keys on legal name and the fabric on LEI**; the unresolved
   count is served, never hidden.
3. **An amendment's action is not scalar** — two actions on one amendment.
4. **A shared scratch root is not a shared fabric** (`CP03C-F-02`): the fabric
   path is per run and Π is scoped to the request's subject.
5. **New here — the commitment is a claim, not a closure.** A value Π needs
   that the graph does not carry is a value replay cannot reconstruct from the
   snapshot; on the road it is ingested as the facility node's attribute and
   read off the view.

## D · Assembly recipe

### D.1 Client call

In-process: `produce.product(scratch, environ=)` → `opened.question(…)` →
`opened.answer(asked)` → `ServedProduct | RefusalEnvelope`. Over MCP:
`run.py --door`, the SDK's standard door (`open_door`) over the same opened
product, the `request_context_product` tool, the door's `ProducerAssertion` on
every outcome; a consumer registers `producer_id`
`cp-06-canonical-collateral-and-setoff-coverage-egress` under producer tenant
`cp-06-canonical-demo`.

### D.2 The two regions

`boot` (one `open_product` binding `acquire`, `project`, `assess` and the
product's own `gate` to the two documents) and `answer` (one governed
question). No registry, boot call, effective-request re-derivation, ingest
loop, builder call, store or record readback exists in the tree.
`acquire(context)` reads the effective `include_setoff` off the request the
road hands it, opens the two sources the environment document names, and
returns the specimen's envelopes — **edges first, attributed nodes last** —
with one addition: the facility node's `commitment`. `project(required,
request)` builds the specimen's Π from the effective request alone; the
anchor is the subject. `assess(context)` is the specimen's `D_c` over the
operator view with the booted λ_c table and profile. `gate(candidate,
evidence)` is the specimen's over-allocation guard, declared on the class as
`cp-06-canonical.over-allocation-guard@1.0.0`.

### D.3 Validation gates

The SDK's three L6 gates, the class's declared obligations, and the product's
own declared gate. A breach is a governed refusal with a record, never a
payload check.

### D.4 Determinism, replay and the lane measurement

Two runs of one question agree byte for byte; the door and the in-process run
agree byte for byte; replay dimension 1 lists every served entity and
dimension 2 carries the request contract and the policy bundle.

**The lane is measured, not asserted.** The successor's `payload` for
`FAC-5B8418` and for `FAC-044206`, at the CP-14 instant under the class
defaults, is hashed and compared with the specimen's payload addresses in
§A.2 (`d22b256e…`, `8e3e567b…`). The comparison is on the **payload**, not
the whole contract: the contract carries `tenant_id` and `plan_id`, which a
sibling under its own tenant cannot share, and the expiry, which the
specimen anchored on the instant and the successor, since `D-IMPL-341`, on
the valuation. If both payloads match, the
successor serves `1.0.0` — a second producer of the same product. If either
differs, the successor serves `1.1.0`, and §G.3 states every differing member
and why. **No payload member is adjusted to make the match.** The gate that
holds this is `CSCC-G13`.

## E · Volatility, debt and materialization

Two decay rates in one payload: marketable-securities marks and deposit
balances at ~1 day; real-property appraisals and lien structure at ~365 days;
the haircut schedule at ~180 days. **The product's own TTL window is the
appraisal cycle, and it is an illustrative calibration** (`D-IMPL-323`, ruled
2026-09-18 — see the TTL row in §B and `FINDINGS.md` `CP06C-F-05`):

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

It states how long a coverage answer stays current after a VALUATION, which is
what the expiry is anchored on. It is not a claim about the deposit balances:
this estate dates them by nothing at all, so they contribute no instant to the
anchor and the set-off leg's currency is unestablished — which is why coverage
is served with collateral value, set-off value and total kept apart.

**Measured for the CP-14 facility, both readings kept.** At the specimen's
reading `D_c` is 0.3660 with `C = 1` (the one pledged asset is priced) and
`S = 1`, so `F` is 0.634 by derivation — one receivables valuation aged 240 days
by the estate's own `valuation_age_days`. Since `D-IMPL-341` (`CP06C-F-04`) the
successor ages that asset from the valuation date the claim carries rather than
from the stored count, which at the CP-14 instant is 261 days rather than 240:
`F` 0.6086, `D_c` 0.3914, `C` and `S` unchanged. The older figure is the
specimen's and is kept because the lane comparison rests on it; the
coverage ratio would read the same with the valuation a day old, which is why
the payload dates it.
Derived on demand; structure cacheable, valuations not.

## F · Source binding and readiness

`ccf_environment.yaml`, the deployment-environment companion of
`ccf_config.yaml` under `D-IMPL-343`: two sources, `collateral_graph`
(`CCF_CP_06C_FLUREE_URL`, `CCF_CP_06C_FLUREE_LEDGER`) and
`collateral_attributes` (`CCF_CP_06C_POSTGRES_DSN`, `CCF_CP_06C_POSTGRES_SCHEMA`),
names and remedies only; the door's credential and advertised URLs
(`CCF_CP_06C_DOOR_TOKEN`, `_ISSUER_URL`, `_RESOURCE_URL`). The v2 namespaces
are `fibo-v2` and `ccf_v2`; `ccf_dataprep/.env` names v1. Read-only. No
`backends.yaml`, no `server/door.yaml`.

### F.4 Findings

Raised in the tree's `FINDINGS.md` under `docs/EXAMPLE-EVALUATION-CRITERIA.md`.
Two are known before the build: `D-IMPL-341` (the expiry anchor) is inherited
and disclosed (closed 2026-09-18; the migration it took and its consequence
for the demonstration are `CP06C-F-04` / `CP06C-F-05`); and whether the road's refusal to pass acquisition values to Π
is friction or the correct shape is recorded as a measurement (`§E` of the
criteria) — this specification's position is that it is the correct shape.

## G · Operate and govern

### G.1 Product gates

The acceptance authority for every gate below is **this clause**
(`D-IMPL-326`). Each id is claimed by the executing test named in
`artifacts/gates.yaml`. The first eleven restate the specimen's domain
properties under the successor's ids; the twelfth replaces the specimen's
`CSC-G12`, whose subject no longer exists.

| Gate | Asserts |
|---|---|
| `CSCC-G01` | haircuts reduce coverage |
| `CSCC-G02` | valid set-off increases coverage |
| `CSCC-G03` | `contractual` counts at least as much set-off as `enforceable` |
| `CSCC-G04` | `priority` and `pro-rata` disagree on a shared asset |
| `CSCC-G05` | the register reports a released lien |
| `CSCC-G06` | the CP-14 facility is **covered** and the specimen's MasTec anchor is **under-covered** — the direction, never the number |
| `CSCC-G07` | valuation dates are per asset, never flattened |
| `CSCC-G08` | priority is carried per (facility, asset) pair |
| `CSCC-G09` | source ids are served, never fabric URIs |
| `CSCC-G10` | the over-allocation gate is declared, identified, and runs on the governed path |
| `CSCC-G11` | replay dimension 2 is a superset of product policy lineage |
| `CSCC-G12` | **the door is the SDK's standard door opened from `door:`** — no door module, no `door.yaml`, no script path exists in the tree |
| `CSCC-G13` | **the lane measurement**: the successor's payload equals the specimen's at the pinned instant for both §A.2 facilities, or the lane is `1.1.0` and §G.3 names every differing member |
| `CSCC-G14` | the commitment is read off the facility node in the view; Π's constructor takes no commitment and no jurisdiction register |
| `CSCC-G15` | `shape_of` reads this tree as **paved**; no `build_governed_resolver` and no `build_replay_record` call exists |
| `CSCC-G16` | the frozen specimen is **untouched** and no specimen identity is reused — tenant, producer id, plan-id prefix, gate id |
| `CSCC-G17` | the CP-14-shaped question is answered by the producer **in another process** and admitted under `provider-controls` |
| `CSCC-G18` | the expected producer identity and tenant come from the registration — wrong id and wrong tenant refuse independently |
| `CSCC-G19` | an unknown intent is refused on the declared discovery set — the specimen accepts it |
| `CSCC-G20` | a scope the caller does not hold yields an empty graph and a refusal, never a redacted payload |
| `CSCC-G21` | the door and the in-process run serve **one** content address |
| `CSCC-G22` | a fresh fabric per run; two facilities under one root hash to their own addresses |
| `CSCC-G23` | `expires_at` is anchored on the freshest valuation, as declared, and `ttl_anchor_at` records it — live since `D-IMPL-341` (was quarantined evidence) |
| `CSCC-G24` | evidence older than the declared window is refused by the expiry gate, on a facility this estate really holds — the calibration's own negative control (2026-09-18) |

**All directional, structural or relational. No estate figure is pinned in a
gate** — the counts in §A.2 and §E are measurements a reader can reproduce.

### G.2 Acceptance criteria

1. A real governed `ServedProduct` of `credit-risk.collateral-coverage` on a
   lane `CP-SPEC-014` admits, for the CP-14 facility at the CP-14 instant,
   with debt, content address and replay record.
2. The lane is decided by `CSCC-G13`'s measurement and recorded in §B.1
   before the tree is offered to CP-14.
3. The commitment and the enforceability are fabric state; Π reads the view.
4. The expiry-anchor gap is raised, not hidden.
5. The product is acquired across a deployment boundary through `D-IMPL-340`
   and admitted; every negative control refuses through the SDK's own path.
6. The frozen specimen is unchanged; CP-14's `producers.collateral` is
   re-pointed to this tree only after this tree ships.

### G.3 Where the successor and the specimen differ — the difference ledger (measured 2026-09-16)

**No payload member differs** for either declared facility at the pinned instant
(`CSCC-G13`): full canonical payload hashes equal, field-level comparison empty,
debt factors equal (`F` 0.6340 / 0.6231, `C` 1, `S` 1), expiry equal (decision
instant + 24 h on both — `D-IMPL-341`, inherited), `operators_invoked` equal.
The lane is therefore **`1.0.0`**. Since `D-IMPL-341` (2026-09-18) the lane is
held to those recorded payload addresses rather than to a live specimen: the
frozen specimen declares the same anchor over a resolver wired with no λ_c
table, which the builder refuses as a configuration failure before any question
proceeds, and the successor's `F` and expiry now run from the valuation date
(`CSCC-G13`).

**What differs, by construction and by design — none of it in the payload:**

| member or behavior | specimen | successor | why |
|---|---|---|---|
| `tenant_id` | `cp-06-demo` | `cp-06-canonical-demo` | a sibling under its own tenant |
| `plan_id` | `cp-06.collateral-coverage/<facility>` | `cp-06-canonical.collateral-coverage/<facility>` | its own identity (`CSCC-G16`) |
| `lineage.policy_bundle_versions` | the specimen's policy artifact hash | the successor's | the class id on the policy document differs; the regime and rules do not |
| replay dimension 1 | facility node without `commitment` | facility node **with** `commitment` | the commitment is fabric state (`CSCC-G14`); the snapshot id differs accordingly |
| an unknown `intent` | served | **refused** on `discovery.intents` (`CSCC-G19`) | a governed axis the specimen left open — deliberate |
| a scope the caller does not hold | served: `assets: []`, `coverage_ratio: 0` over the empty view | **refused** — since `D-IMPL-341` by the SDK's own anchor gate (`ttl-anchor-refusal` / `ttl-anchor-unresolvable`: an empty view carries no evidence instant), which runs before the product's gate; the product's `no facility commitment in the admitted view` half is held directly on the candidate (`CSCC-G20`) | an empty graph is not a coverage of zero — deliberate; the specimen's zero reads as an uncovered facility |
| the door | 150 lines and a `door.yaml` naming a `module:callable` (`CSC-G12`) | a 27-line launcher over the SDK's standard door (`CSCC-G12`) | `D-IMPL-343` |
| documents | four (`ccf_config`, `backends`, `server/door`, gates) | two (`ccf_config`, `ccf_environment`) | one authority per value |

Neither deliberate tightening changes a unit, an allocation rule or the business
meaning of a served answer; each converts a served non-answer into a governed
refusal with a record.
