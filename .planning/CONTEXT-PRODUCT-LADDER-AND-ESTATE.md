# The Context Product ladder and the data estate behind it

**Written:** 2026-08-28. **Method:** the ladder comes from the Obsidian vault over
the `obsidian-vault` MCP server (`list_articles("context-products")`); the estate
figures come from **live read-only queries against the databases**, not from any
file in `ccf_dataprep`. Every number below was returned by a query on the date above.

**Why this file exists.** The equivalent analysis was done on 2026-08-28 at 15:27
and written down nowhere. It died with the session. This file is the durable copy.

---

## 1. The ladder — 21 Context Products, simplest first

The vault topic `context-products` holds **25 articles: 4 standards/reference and
21 product specifications**, ordered simplest-first across a **five-tier build
ladder**. The tier is the complexity order; within a tier the vault's own order is
kept.

### Reference and standards (not products)

| Article | Role |
| --- | --- |
| `spec-standard-v0-3` | What a spec must contain to be buildable. Nine-element contract, four-question build test. **Supersedes the Q019 authoring standard.** |
| `ccf-sdk-de-requirements` | The seven-station data-engineer journey (author, validate, bind, build, register, certify, operate). `D-IMPL-31` (closed operator vocabulary vs four canonical categories) still open there. |
| `fibo-iri-binding` | The exact FIBO/Commons IRIs behind the module names. **Caution it carries: bound ≠ materialized.** |
| `ccf-v2-schema-delta` | A waiting structure for CCF v2.0. Every item `[TBC]`; no v2.0 document read yet. |

### Tier 1 — Postgres only. One store, no graph.

| # | Product | The question it answers |
| --- | --- | --- |
| 1 | `counterparty-reference-snapshot` | **Start here.** Minimum viable Context Product — resolve one counterparty to a typed identity snapshot. Proves the contract fires rather than demonstrating assembly. The **only** spec authored to `spec-standard-v0-3`. |
| 2 | `facility-terms-snapshot` | How does a product anchor on something other than a legal entity? Demonstrates the `from_entity_freshness` TTL anchor. |
| 3 | `obligor-financial-spread` | Temporal validity at attribute level before any graph — period-end and filing date are not the same thing. |

### Tier 2 — Postgres + Fluree. First multi-store products.

| # | Product | The question |
| --- | --- | --- |
| 4 | `corporate-family-tree` | Who ultimately owns this obligor? Multi-hop traversal; cycles returned as findings, not errors. |
| 5 | `credit-exposure-rollup` | Total exposure to a corporate family; the concentration denominator a flat data product gets wrong. |
| 6 | `collateral-and-setoff-coverage` | What actually secures this exposure? Coverage as a graph question, not a column. |
| 7 | `client-360-coverage-graph` | Who at the bank knows whom at the client? High fan-out; traversal cost becomes a design constraint. |

### Tier 3 — Postgres + Fluree, temporal and forensic.

| # | Product | The question |
| --- | --- | --- |
| 8 | `covenant-in-force-as-of` | **Flagship.** Which covenants were in force on the drawdown date? Ledger time-travel with supersession preserved. |
| 9 | `treasury-liquidity-position` | Cash and rate posture right now. Fast `λ_c`; the Latency-Poisoned counterfactual. |
| 10 | `rating-and-spread-migration` | How has credit quality moved? Per-signal decay curves. |
| 11 | `credit-surveillance-early-warning` | What changed overnight? Supersession driving cache-invalidation cascade. |
| 12 | `fx-post-trade-reconciliation` | Why do two systems disagree about one trade? The answer depends whose clock you reconstruct against. |

### Tier 4 — adds MongoDB. Documents and passage-level lineage.

| # | Product | The question |
| --- | --- | --- |
| 13 | `covenant-cross-reference` | What does this covenant actually require? Passage-level lineage across documents. |
| 14 | `credit-memo-context` | What goes in the credit memo? Algorithmic/semantic alternation; Context Debt across a multi-agent handoff. |
| 15 | `kyc-refresh-beneficial-ownership` | Who are the natural persons behind this entity? Ownership walked to person level. |
| 16 | `abs-securitization-surveillance` | How is this securitization performing? Loan-level fan-out; forces the materialization decision. |

### Tier 5 — all stores. Policy, perspective, federation.

| # | Product | The question |
| --- | --- | --- |
| 17 | `mnpi-wall-enforcement` | What must this agent never see? The edge is not filtered — it **never materializes**. |
| 18 | `ib-opportunity-synthesis` | Which prospects matter to this banker? Projection across three roles; the Perspective-Flat failure. |
| 19 | `aml-typology-match` | Does this pattern match a known typology? Policy-before-Similarity. **Synthetic obligor only — never a named real company.** |
| 20 | `syndicated-lending-co-lender` | What does the other bank see? **A2A** across organizations, under a negotiated policy envelope. |
| 21 | `large-exposure-rwa-concentration` | Are we within limits? Composes every primitive below it. |

---

## 2. The estate — five stores, all on one host

`ccf_dataprep` loads **v2 into fresh namespaces beside v1, never over it.**
Rollback is dropping one namespace per store.

| Store | Address | v2 namespace | v1 namespace (read-only, preserved) |
| --- | --- | --- | --- |
| Postgres | `192.168.4.76:5432`, db `parkavedb` | schema **`ccf_v2`** | `public` |
| Fluree 4.1.4 | `http://192.168.4.76:8090` | ledger **`fibo-v2`** | `fibo:main` |
| MongoDB | `192.168.4.76:27017` | db **`fibo_v2`** | `fibo` |
| SQLite | `ccf_dataprep/data/departmental.sqlite` | (single file) | — |
| Neo4j | `bolt://192.168.4.76:7687` | optional, graph algorithms only; **may be dropped entirely** | — |

**The host is shared and that is dangerous.** The same MongoDB carries `rtdetect`,
~5.5M documents of live pool-safety telemetry. `ccf/config.py` holds a denylist
plus a narrow allowlist so a cleanup loop cannot reach it.

A **second fabric** (`CO_LENDER_*`) is specified in `.env.example` for
`syndicated-lending-co-lender` and is **not provisioned** — the whole block is
commented out. Nothing falls back to the local fabric; `ccf.config.assert_distinct_fabrics`
refuses a peer sharing our database, role, or ledger.

---

## 3. Live census — 2026-08-28

### Postgres — `parkavedb`, schema `ccf_v2` — 113 tables

Largest and most load-bearing:

| Table | Rows | Table | Rows |
| --- | ---: | --- | ---: |
| `abs_loan_period` | 1,322,453 | `spread_observation` | 47,849 |
| `sanctions_name` | 45,511 | `peer_fact` | 22,494 |
| `institutional_holder` | 22,476 | `sanctions_entry` | 19,730 |
| `financial_fact` | 15,055 | `intraday_tick` | 11,700 |
| `reference_rate` | 10,539 | `fx_intraday_tick` | 10,368 |
| `benchmark_curve` | 8,917 | `interaction_participant` | 8,032 |
| `aml_transaction` | 4,358 | `fx_reference_rate` | 3,942 |
| `market_oas_series` | 3,930 | `trend_delta` | 3,705 |
| `warn_notice` | 3,514 | `interaction` | 2,050 |
| `person_crosswalk` | 1,815 | `system_trade_record` | 1,815 |
| `peer_entity` | 1,678 | `signal_event` | 1,603 |
| `coverage_assignment` | 1,000 | `person_name_variant` | 997 |
| `person` | 954 | `gdelt_mention` | 951 |
| `person_role` | 817 | `peer_cohort` | 324 |
| `context_debt` | 304 | `corporate_ownership_record` | 280 |
| `psc_person` | 210 | `aml_party` | 201 |
| `investment_position` | 200 | `bo_chain_hop` | 169 |
| `legal_entity` | 156 | `drawdown` | 151 |
| `offshore_vehicle` / `offshore_administration` | 150 each | `registry_company` | 140 |
| `engineered_entity` | 125 | `deposit_account` | 120 |
| `abs_cohort_performance` | 132 | `gov_contract_concentration` | 104 |
| `debt_instrument` | 96 | `collateral_pledge` | 95 |
| `collateral_asset` | 91 | `perspective_weight` | 66 |
| `facility` / `break_record` / `concentration_limit` | 60 each | `crosswalk` | 53 |
| `bo_chain` / `filing_profile` / `kyc_refresh_state` | 50 each | `syndicate_member` / `permitted_instrument` / `signal_weight` | 45 each |

Postgres `public` (v1): `entities` 14, `relationships` 16. Untouched.

### Fluree `fibo-v2` — **t = 4,560**, 87,162 triples, 91 classes, 171 predicates

Top classes: `Interaction` 2,050 · `SystemObservation` 1,815 · `OpportunitySignal` 1,270 ·
`Person` 915 · `IssuanceEvent` 908 · `FormalOrganization`/`LegalEntity`/`Organization` 854 each ·
`Corporation`/`LegalPerson` 661 · `Agent`/`Party` 539 · `WarningSignal` 538 · `Trade` 500 ·
`CorporateOfficer` 323 · `CreditRating` 245 · `Covenant` 182 · `SpecialPurposeVehicle` 150 ·
`CollateralPledge` 95 · `Collateral` 91 · `BeneficialOwnership` 50 · `CreditFacility` 45.

Top predicates: `rdf:type` 17,697 · `rdfs:label` 11,369 · `participatedIn` 8,032 ·
`provenance` 7,841 · `transactedWith` 7,736 · `validFrom` 3,022 · `supersededBy` 1,107 ·
`owns` 636 · `isUltimatelyConsolidatedBy`/`isDirectlyConsolidatedBy` 140 each ·
`hasGlobalUltimateParent` 103.

**`ledger_t` = 4,560 is the exact replay anchor** for `graph_snapshot_at` — the named
snapshot `D-IMPL-218` requires.

Fluree `fibo:main` (v1): t = 5, six class rows. A hello-world load.

### MongoDB `fibo_v2` — 6 collections

`passage` 37,865 · `document` 249 · `research_note` 42 · `memorandum` 40 ·
`kyc_document` 32 · `trigger_anchor` 10.

`fibo` (v1): `entities` 14, `relationships` 16.

### SQLite `data/departmental.sqlite` — 100 KB, 8 tables

`prospect_note` 50 · `covenant_tracker` 45 · `risk_limit_workbook` 16 ·
`sar_classification` 12 · `syndicate_desk_tracker` 12 ·
`large_exposure_limit_workbook` 5 · `restricted_list` 4 · `_schema_meta` 4.

**This is the departmental store** — the spreadsheet-shaped source that only
Tier 5 products touch (`aml-typology-match`, `ib-opportunity-synthesis`,
`mnpi-wall-enforcement`, `syndicated-lending-co-lender`, `large-exposure-rwa-concentration`),
one §C row each.

---

## 4. Which stores each product needs — from each spec's §C Data Catalog

Row counts are §C data-catalog rows assigned to that store.

| Tier | Product | §C rows | Store assignment |
| --- | --- | ---: | --- |
| T1 | `counterparty-reference-snapshot` | 4 | Postgres 4 |
| T1 | `facility-terms-snapshot` | 10 | Postgres 10 |
| T1 | `obligor-financial-spread` | 8 | Postgres 8 |
| T2 | `corporate-family-tree` | 12 | Fluree 7, Postgres 4, both 1 |
| T2 | `credit-exposure-rollup` | 9 | Postgres 5, Fluree 4 |
| T2 | `collateral-and-setoff-coverage` | 16 | Fluree 10, Postgres 6 |
| T2 | `client-360-coverage-graph` | 13 | Postgres 7, Fluree 5, either 1 |
| T3 | `covenant-in-force-as-of` | 15 | Fluree 11, Postgres 4 |
| T3 | `treasury-liquidity-position` | 14 | Postgres 11, Fluree 3 |
| T3 | `rating-and-spread-migration` | 12 | Postgres 6, Fluree 6 |
| T3 | `credit-surveillance-early-warning` | 14 | Postgres 8, Fluree 6 |
| T3 | `fx-post-trade-reconciliation` | 13 | Postgres 8, Fluree 5 |
| T4 | `covenant-cross-reference` | 15 | MongoDB 8, Fluree 6, Postgres 1 |
| T4 | `credit-memo-context` | 15 | MongoDB 6, Postgres 6, Fluree 1, mixed 2 |
| T4 | `kyc-refresh-beneficial-ownership` | 15 | Postgres 7, Fluree 6, MongoDB 2 |
| T4 | `abs-securitization-surveillance` | 13 | Postgres 5, Fluree 4, MongoDB 3, both 1 |
| T5 | `mnpi-wall-enforcement` | 15 | Postgres 6, Fluree 4, MongoDB 3, SQLite 1, either 1 |
| T5 | `ib-opportunity-synthesis` | 18 | Postgres 10, Fluree 3, MongoDB 3, SQLite 1, either 1 |
| T5 | `aml-typology-match` | 16 | Fluree 6, Postgres 5, MongoDB 3, SQLite 1, either 1 |
| T5 | `syndicated-lending-co-lender` | 16 | Fluree 5, Postgres 5, MongoDB 3, SQLite 1, **separate instance 1**, both 1 |
| T5 | `large-exposure-rwa-concentration` | 17 | Fluree 7, Postgres 4, MongoDB 3, SQLite 1, mixed 2 |

**Provenance mix** across the catalog is roughly two-thirds `public` (GLEIF, SEC
EDGAR/XBRL, FRED, Companies House, GDELT, WARN, OFAC) and one-third
`synthetic — internal` (the bank-side data no public source can supply:
entitlements, internal ratings, coverage assignments, ranking weights).

---

## 5. What is empirically confirmed, and what is only asserted

`validators/spec_coverage.py` walks each spec's §C and probes the live stores.
**Only 9 of 21 products are in its manifest.** For the other 12, the store
assignment above is what the spec says — it is *not* a confirmed load.

Run 2026-08-28 (`PASS` = live probe returned > 0; `COVER` = asserted by a named
check elsewhere; `GAP` = real, named shortfall):

| Product | PASS | COVER | WAIVE | GAP | FAIL |
| --- | ---: | ---: | ---: | ---: | ---: |
| `aml-typology-match` | 16 | 0 | 0 | 0 | 0 |
| `syndicated-lending-co-lender` | 16 | 0 | 0 | 0 | 0 |
| `covenant-in-force-as-of` | 7 | 8 | 0 | 0 | 0 |
| `covenant-cross-reference` | 9 | 6 | 0 | 0 | 0 |
| `ib-opportunity-synthesis` | 12 | 5 | 0 | 1 | 0 |
| `large-exposure-rwa-concentration` | 12 | 4 | 0 | 1 | 0 |
| `collateral-and-setoff-coverage` | 7 | 6 | 1 | 2 | 0 |
| `corporate-family-tree` | 6 | 1 | 0 | 4 | 1 † |
| `counterparty-reference-snapshot` | — | — | — | — | — ‡ |

† The single `FAIL` was a **gate defect, not a data gap** — see §6.2. **Repaired
2026-08-28**; the row now passes. The table above is the pre-repair run.
‡ Crashes before probing; see §6.1.

**Unprobed (12):** all three T1 except `counterparty-reference-snapshot`, plus
`credit-exposure-rollup`, `client-360-coverage-graph`, `treasury-liquidity-position`,
`rating-and-spread-migration`, `credit-surveillance-early-warning`,
`fx-post-trade-reconciliation`, `credit-memo-context`,
`kyc-refresh-beneficial-ownership`, `abs-securitization-surveillance`,
`mnpi-wall-enforcement`.

### T1 — what direct column inspection showed, and where it fell short

Tier 1 had no probes when this section was written, so its backing was checked by
querying `information_schema` directly.

> **CORRECTED 2026-08-28 18:54.** The claim below that all three T1 specs are
> *"fully backed"* is **wrong for `counterparty-reference-snapshot`**, which now
> reports three real gaps once its manifest was re-derived — see §6.1.1. Column
> presence is a weaker test than element satisfaction. `facility-terms-snapshot`
> and `obligor-financial-spread` remain **unprobed**, so what follows is what the
> tables hold, not a verdict on the specs.

**The tables named below do hold what they are described as holding:**

- `counterparty-reference-snapshot` → `legal_entity` (156 rows; `lei`, `legal_name`,
  `legal_jurisdiction`, `entity_status`, `registration_status`, `legal_form`,
  **one** address triple, `lei_match_band`), `crosswalk` (53; internal_client_id ↔
  lei ↔ cik ↔ ticker). **Three §C elements are NOT satisfied** — the second address,
  no-LEI entities (0 rows), and jurisdiction entitlement (no such column). See
  §6.1.1. `engineered_entity` (125) is *not* the no-LEI population this spec asks
  for; `corpus_entitlement` (6) scopes corpora, not jurisdictions.
- `facility-terms-snapshot` → `facility` (60; commitment, currency, effective/maturity
  dates, `pricing_grid`, `administrative_agent`, `outstanding_balance`,
  `undrawn_availability`, `internal_risk_rating`, `source_accession`/`source_offsets`),
  `drawdown` (151), `debt_reconciliation` (14), `guarantee_terms` (28).
- `obligor-financial-spread` → `financial_fact` (15,055; every fact carries
  `period_end`, `filed_date`, `accession`, `form` — the restatement chain is native),
  `peer_fact` (22,494), `peer_entity` (1,678), `peer_cohort` (324), `filing_profile` (50).

---

## 6. Defects found while surveying — status as of 2026-08-28 18:54

**Both are repaired as of 2026-08-28 18:54.** The full `spec_coverage.py` run
now completes and reaches all 21 products: **129 of 280 catalog rows accounted
for** — 87 probed clean, 30 covered by `conditions.py`, 1 waived, 11 deferred —
with 151 rows unchecked, all of them inside the 12 products that still have no
manifest. `rc=1` is the designed state while any `GAP` stands; it is not a
failure of the run.

**The counterparty repair did not just unblock the run — it exposed three real
gaps on the ladder's first rung that the crash had been hiding. See §6.1.**

**Both defects below belong to `ccf_dataprep` and Dave owns the fixes. Nothing in
that repository was changed by this survey — it was read from only.**

This section was rewritten. The first defect was **understated**; the second was
real but **diagnosed wrongly**. Both corrections are Dave's, verified independently
against the live stores before being written here.

### 6.1 The counterparty crash is a spec collapse, not a reworded string

`validators/spec_coverage.py` aborts the whole-catalog run with
`RuntimeError: mapping 'LEI, legal name, legal jurisdiction' matched 0 catalog
rows`. The first reading — that the vault reworded one row — was wrong.

**The vault collapsed §C from 10 rows to 4.** Confirmed by query: the manifest
holds **10 mappings**, the current spec holds **4 rows**.

| Manifest mapping | Fate |
| --- | --- |
| `LEI, legal name, legal jurisdiction` | **Merged.** Four mappings became one §C row: *"LEI, legal name, jurisdiction, entity status, registration status, legal form, addresses"* |
| `Entity status` | merged into the row above |
| `Entity legal form` | merged into the row above |
| `Legal address` | merged into the row above |
| `internal_client_id` | survives |
| `Principal entitlement scope` | survives |
| `CIK` | **gone from §C** |
| `SIC code` | **gone from §C** |
| `Internal obligor risk grade` | **gone from §C** |
| `Coverage RM assignment` | **gone from §C** |

The match string fails only because the spec now says *"jurisdiction"* where it
said *"legal jurisdiction"*. **Patching that string just moves the crash along.**
Four elements are no longer requested by the spec at all, and the estate still
holds data for every one of them.

**This needs a ruling, not a patch.** Three options for CIK, SIC, internal obligor
risk grade and coverage RM assignment: waive them with the reason recorded; keep
probing them as extra beyond spec; or ask the vault custodian whether the collapse
was deliberate. It sits on the exact product the ladder says to build first.

> **REPAIRED 2026-08-28** at merge `cf03d28` (`fix-counterparty-manifest`), by
> **re-deriving the manifest from the current §C** rather than patching the match
> string. Ten mappings became four. The crash is gone and the whole catalog runs.
>
> **CIK was not dropped.** The rewrite folds it into the crosswalk probe, which now
> requires `lei`, `internal_client_id` **and** `cik` non-null on the same row — 53
> rows satisfy it. The stated reason is that `LEI → CIK → ticker` is the join six
> other specs depend on, so CIK is asserted explicitly rather than quietly leaving
> with its row. **SIC code, internal obligor risk grade and coverage RM assignment
> are no longer asserted anywhere.** The estate still holds them. Whether that is
> the right outcome is still Dave's call, but it is now a much smaller question than
> it was: the join everything depends on is protected.

Because the run is alphabetical, this one crash hid every product after `c`.
Running each product separately shows the truth is better than it looked:
**8 of the 9 manifests are clean**, and the remaining 12 products have no manifest
at all.

### 6.1.1 What the crash was hiding: the first rung is not build-ready

With the run unblocked, `counterparty-reference-snapshot` reports **1 PASS and 3
GAPs**. Every one verified independently against Postgres on 2026-08-28.

| § C row | State | What is actually there |
| --- | --- | --- |
| LEI, legal name, jurisdiction, status, registration status, legal form, addresses | **GAP — six of seven** | 153 of 156 rows carry the first six together. The seventh is **addresses, plural** — §B names *headquarters and legal address*. Only `address_country / _city / _region` exist: **one address, and nothing records which of the two it is.** |
| Internal client identity for no-LEI entities | **GAP — zero** | `legal_entity` holds **0 rows with a null LEI** out of 156; `crosswalk` holds 0. Every entity in the estate has an LEI. |
| Entitlement scope by jurisdiction | **GAP — wrong quantity** | `principal` has 4 rows and **no jurisdiction column at all** (`principal_id, name, side, perspective, sees_mnpi, provenance, sees_need_to_know, sees_eu_person_data`). `corpus_entitlement` scopes document corpora, not jurisdictions. |
| LEI ↔ internal client crosswalk | **PASS** | 53 rows carrying `lei` + `internal_client_id` + `cik` together. |

**Two of these are worse than they look.**

*The no-LEI gap is the spec's own §D counterfactual, realised.* The spec warns that
*"an LEI-only anchor silently excludes privately-held middle-market borrowers, and
every downstream product inherits the exclusion."* The estate is exactly that
anchor. The predecessor manifest marked this `COVERED` against crosswalk floors —
**and every one of those floors is keyed on LEI**, so they were structurally
incapable of reporting the absence of entities that have none. Closing it is a
generation task nobody has run.

*The entitlement gap makes the Policy Operator a no-op* — in the product every other
product inherits its contract machinery from. §B defines the T1 policy binding as
*jurisdiction visibility per calling principal*, and no query over this estate can
distinguish one principal's jurisdiction entitlement from another's.

*The address gap is not a source limitation.* Headquarters is fetchable from the
same daily GLEIF Level 1 file already in use. A consumer joining on headquarters
jurisdiction — the usual question, since legal domicile and operating seat diverge
precisely for the offshore structures this catalog cares about — **silently gets the
legal domicile instead of an empty result.**

**This corrects §5 of this document.** Its claim that all three T1 specs are *"fully
backed"* was reached by checking that the named columns exist, which is a weaker
test than asking whether the §C element is satisfied. Column presence cannot see a
required element with no rows at all, cannot see a missing distinction between two
values sharing one column, and cannot see a missing column on a *different* table.
Same measurement-error class as the one recorded in §6.2 — a check whose population
is not the question.

### 6.1.2 All three gaps closed and independently verified — 2026-08-28 evening

`ccf_dataprep` closed the address gap the same day it was reported, at
`465ba4d` *(Wave 20 gap 3: label the addresses and load the headquarters half)*.
Everything below was re-derived here against the live store rather than read off
that repo's report.

| What was claimed | What the store says |
| --- | --- |
| Schema migrated and the addresses **labelled** | `legal_address_{country,city,region}` **and** `hq_address_{country,city,region}`. The unlabelled triple named in §6.1.1 no longer exists. |
| 153 headquarters addresses loaded | 153 present, 153 legal present, 3 absent — against a control of 156 rows. |
| 69 of 153 differ at city/region | 69. |
| The three absent rows are exactly the synthetic ABS trusts | **Proven as set equality, in both directions** (below). |

**The excluded set is proven, not assumed.** `ccf_dataprep` flagged this as
outstanding; it is discharged here. The three rows with no headquarters address are
`SYN-SDART-2022-6`, `SYN-SDART-2024-1` and `SYN-TAOT-2022-B` — Santander Drive Auto
Receivables 2022-6 and 2024-1, and Toyota Auto Receivables 2022-B Owner Trust. GLEIF
holds no record of any of them and never will. The test is run **both ways**: no
`SYN-` row carries a headquarters address, and no non-`SYN-` row lacks one. Both
difference sets are empty. A count of three matching a count of three would not have
shown this — see [[verify-rosters-not-counts]]: a right count with a wrong member
audits clean forever.

**The discriminating power is the Delaware pattern, and it is real.** Registered in
Wilmington, operated from somewhere else: `Agilysys NV LLC` Wilmington US-DE →
Alpharetta US-GA; `AVIS BUDGET GROUP` Wilmington US-DE → Parsippany US-NJ; `BGC
Group` Wilmington US-DE → New York US-NY; `Bausch Health` Vancouver CA-BC → Laval
CA-QC. This is precisely the divergence a consumer joining on headquarters
jurisdiction needs, and precisely what §6.1.1 said the single unlabelled address
would silently answer wrong.

**One finding for the validator that is still owed.** Of the 69 differing rows,
**four differ only by letter case** — `AMPHENOL CORP /DE/`, `HNA ACQUISITION ULC`,
`MURPHY OIL COMPANY LTD.` and `VML US FINANCE LLC`, each carrying e.g. `WILMINGTON`
against `Wilmington` in the same region. Under `lower(btrim(…))` the count is **65 of
153**, not 69. The conclusion is untouched — 65 of 153 is 42% and the distinction is
unambiguous — but a distinguishability assertion written on raw `is distinct from`
scores those four as two addresses when they are one address typed twice, and that
assertion is what the product's suppression-silence gate leans on.

**A CORRECTION ON THE RECORD, MINE, AND IT IS THE SECOND OF THIS CLASS IN THIS
DOCUMENT.** Before `465ba4d` landed, this session argued that the on-disk headquarters
data could not close the gap, on the evidence that `legal_country` and `hq_country`
**differ in only 9 of 140 rows — 6%** — and therefore offered a distinction with
almost no discriminating power. That measurement is correct and it is about
**`registry_company`**, a different table, at **country granularity only**. What
`ccf_dataprep` had actually loaded was GLEIF Level 1 at **city and region**, where
the figure is 69 of 153. **A claim about the estate was built from the wrong table
and generalized to a load that had not been looked at.** The same session also
corrected "50 fetchable anchors" to 53 by arithmetic (156 − 103) without checking
what the three were; three of them are the ABS trusts above, and 50 was right.

Both errors are the class this document keeps recording: **a check whose population
is not its question.** The wrong version runs, returns a number, and fails by
answering rather than by erroring. §6.1.1 records it against column-presence
testing; §6.2 records it against the family-tree probe; this section records it
against a table substitution.

**THE OTHER TWO GAPS CLOSED WHILE THIS SECTION WAS BEING WRITTEN**, at `39f373d`
and `5b957af`, and both were verified here rather than accepted. The validator now
reports **4 of 4 catalog rows accounted for, zero `GAP`** — but that is a count, and
the whole argument of this document is that a count is not the question. What
follows is the question.

*Entitlement scope by jurisdiction* landed as a `principal_jurisdiction` table — 17
rows, `(principal_id, jurisdiction_prefix, provenance)` — rather than a column on
`principal`, which is the right shape for a many-to-many scope. **A jurisdiction
column would have been necessary and not sufficient.** The bar is §D's
*suppression silence* gate: the **visible entity set must differ between
principals**. Tested directly, joining `legal_entity.legal_jurisdiction` against the
prefix:

| Principal | Scope | Entities visible |
| --- | --- | --- |
| `PRIN-RES-002` research analyst | US, CA, GB | 102 |
| `PRIN-COV-001` coverage banker | US | 74 |
| `PRIN-KYC-004` EU KYC analyst | AT BE DE ES HU IT LU NL SE | 21 |
| `PRIN-TRD-003` trader | GB HK JP SG | 21 |

**All six pairs discriminate**, against a control of 156 entities. Two details a
pass/fail would have hidden: `PRIN-COV-001` is a strict **subset** of
`PRIN-RES-002` (`|A\B| = 0`, `|B\A| = 28`) — containment, not disjointness, which is
realistic and still discriminating; and `KYC` and `TRD` both see 21 but see
*different* 21s (`|A\B| = |B\A| = 21`), so a cardinality check would have called them
equal. **The test carries a negative control** — a principal differenced against
itself reports identical — so a `DISCRIMINATES` verdict is known to be capable of
reading the other way. The Policy Operator is not a no-op.

*Internal client identity for no-LEI entities* landed as an `internal_client` table
of **30 rows**, exactly the shape §C's single-writer paragraph assigns to the
internal client master. Verified against `D-IMPL-220` clause by clause: provenance is
`synthetic — internal` on all 30; the `source` column reads *"internal client master
(invented: public sources cannot supply a no-LEI entity)"*, which states the
invention rather than disguising it; `crosswalk.lei` is now nullable with **30 null
rows**, all 30 joining an `internal_client` and **zero orphaned**; and the table
carries `kyc_last_refresh`, `kyc_cycle_days`, `kyc_next_due` and
`freshness_ceiling_days` at 180/270/365 days, which is what makes §G's acceptance
criterion — *"a no-LEI entity resolves and reports the lower freshness ceiling in the
payload"* — testable rather than aspirational.

**The `SYN-` prohibition was checked as a roster and it holds.** Three `crosswalk`
rows do carry a `SYN-` LEI, which is the literal shape `D-IMPL-220` forbids — but
they are `CLI-000051`–`53` mapping to `SYN-SDART-2022-6`, `SYN-SDART-2024-1` and
`SYN-TAOT-2022-B`, **exactly and only the three ABS trusts**, a pre-existing
convention for securitization vehicles that are modelled as legal entities and have
no GLEIF record. **Zero of the 30 internal clients carries any LEI at all.** Counting
`SYN-` rows would have reported a violation; enumerating them shows there is none.

### 6.2 The red ZERO on `corporate-family-tree` — right red, wrong reason

The first reading said the assertion had never been flipped. **It was flipped, and
correctly.** `unresolved_graph_leis()` returns `1` when every LEI-bearing entity
resolves and `0` when any does not, and its docstring says exactly that; the
inversion exists because a `Mapping` probe passes on `> 0` and the quantity that
decides the row is the *shortfall*.

What misled the first reading is **one line of prose in the mapping text** —
*"so it is 0 only while nothing is unresolved"* — which states the opposite of the
code three lines above it and is simply wrong.

**The real cause is scope: the denominator outgrew the question.** Measured live:

| Population | Nodes | Unresolved |
| --- | ---: | ---: |
| Every `ex:lei` node in the ledger — *what the probe uses* | 434 distinct LEI values (449 triples) | **279** |
| Nodes on `owns` / `controls` / ultimate-parent edges — *actual traversal results* | 711 touched, 144 LEI-bearing | **0** |

The 279 are **201 `SYN-AML-*` parties** (Wave 17), **39 syndicate members**
(Wave 18), **37 registry companies**, and **2 genuinely homeless LEIs**. None are
family-tree traversal results; each resolves from its own single-writer table,
which is what partition discipline requires.

**`corporate-family-tree`'s data is fine. The gate is broken.** The probe was
written when the ledger was mostly the family tree, and the ledger outgrew it.

> **REPAIRED 2026-08-28** by `ccf_dataprep` at merge `96b88ae`
> (`fix-family-tree-population`), and confirmed here by re-run: the row now reads
> `[PASS] 1 found`. The fix derives the population from the four family predicates
> — **136 entities, 0 unresolved** — rather than from every `ex:lei` node, and the
> stale mapping prose is corrected in place. It also **names where narrowing moved
> the vacuity risk**: `_all_resolve` returns 1 on an empty input, so the floor that
> now holds the row honest is `conditions.py`'s *"ownership graph edges (all
> predicates) >= 500"*, not its entity floor. That is the floor assertion this
> survey said was needed, made explicit in the docstring.
>
> **The same commit found a second defect this survey missed.** The measure
> *"entities carrying a real LEI"* counted **bindings, not entities**, and counted
> synthetic `SYN-` identifiers as real: it reported **449 against a real population
> of 233**. That 449 is the same figure this document used as a denominator without
> asking what it counted. Both defects survived, in `ccf_dataprep`'s own words,
> because *"a `>= N` floor set low enough to be safe is also low enough to absorb a
> number counting the wrong thing."*

**The two homeless LEIs** — `5493000FN178SW540N88` and `549300LFK257DF2RVN05` —
carry LEIs in the ledger and resolve from no Postgres table. Not family-tree
entities, so they are some other product's gap, but genuinely unowned.

**The lesson, which generalises past this probe.** The docstring records that a
plain count passed at *"50 of 155"* for twelve waves, so the author inverted it to
measure the shortfall. That fix was right. But it pinned the denominator to
*every LEI in the ledger* — and a denominator that grows with every unrelated wave
turns a sharp check into a permanent red. The inverted probe now measures **too
much**, not too little. A scoped population needs a floor assertion beside it, or
narrowing the scope later silently hides entities instead of failing.

### 6.3 Named `GAP`s elsewhere in the catalog — real, in the specs' own words

*(The three counterparty gaps are in §6.1.1, not repeated here.)*

UCC-1 lien filing dates never loaded; negative-pledge covenant presence absent from
Fluree; accounting consolidation basis missing as an edge property; ownership-edge
valid-time dates; stub entities for non-LEI subsidiaries half-done; the
materiality-threshold-by-intent table holds a different quantity; the S-4 half of
the IPO/merger registration pipeline; FFIEC 101 advanced-approaches capital detail
never fetched.

## 7. What this does not settle

- **`cp-00` is not on this ladder.** Phase 24.1's example (institutional holders
  above a caller-chosen threshold, SEC 13F, `ccf_v2.institutional_holder`, 22,476 rows)
  is an SDK pressure test, not one of the 21 CB/CIB products. The ladder's own
  starting rung is `counterparty-reference-snapshot`.
- **Which product is CP #1 is Dave's call**, not this file's. The vault says
  *"start here"* about `counterparty-reference-snapshot`; that is the vault's
  ordering, not a ruling — and as of 2026-08-28 that product carries **three named
  gaps** (§6.1.1), one of which would leave its Policy Operator with nothing to
  filter on. Building it first now means closing those first, or choosing a
  different rung.
- **Buildable ≠ built.** Twelve of twenty-one products have no live probe. For
  those, this file reports what the spec assigns, and says so.
