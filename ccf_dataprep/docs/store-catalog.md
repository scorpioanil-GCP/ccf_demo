# ccf_dataprep — estate data catalog

Generated **2026-10-10T05:25:27.213827+00:00** by `generators/build_store_catalog.py`, read from the live stores. Regenerate rather than correct.

`ccf_dataprep` is authoritative for the **what data exists** term (exchange agreement, 2026-08-29): SOR, provenance class, `G` axis, volumetrics. This file is the evidence behind that claim.

Full column-level detail, including every type and key, is in the companion **`store-catalog.json`**.

## The partition

Nothing is mirrored. Each store is authoritative for a different slice, which is what makes cross-store assembly a real operation rather than a staged one.

| Store | Address | Owns | Scale |
|---|---|---|---|
| **Fluree** | ledger `fibo-v2` | `R`, `T`, lineage, policy binding | 89,148 triples · 12,087 subjects · 181 predicates |
| **Postgres** | schema `ccf_v2` in database `parkavedb` | `E`, policy reference | 116 tables · 993 columns · 2 views |
| **MongoDB** | database `fibo_v2` | passage-level lineage | 6 collections |
| **SQLite** | file `data/departmental.sqlite` | departmental | 8 tables |
| **Neo4j** | database `neo4j` | optional | 14 nodes · 16 relationships |

**Every address above names its own level**, because the five names are not the same kind of thing — a Fluree ledger, a Postgres schema *inside* a database, two databases, a file path — and `fibo-v2` and `fibo_v2` differ by one character. An unqualified name in that column is a defect, not a shorthand: it reads as a database name, and a reader who tries to connect to it fails. Anything mirroring this table must carry the Address column intact.

## Read this before trusting a number

- **Fluree predicate counts are not obtainable by aggregate.** This ledger answers *"how many predicates"* three ways and only one is right: `COUNT(DISTINCT ?p)` says 188, `GROUP BY ?p` says 210, and the truth is **181**. The aggregates surface 29 phantoms — `ex:_d0` and `ex:AdministrativeAgent` among them — which return ZERO rows when queried directly. Every predicate below was enumerated and then confirmed by asking for a row through it. See known-issues §56.
- **MongoDB field presence is sampled**, 500 documents per collection. A field in 100% of a sample is not a field that is always present, and absence from a sample is not absence.
- **Neo4j holds the v1 starter set only.** No v2 Context Product depends on it.

## Postgres — `E`, the bank-internal slice and all entity attributes

| Table | Rows | Cols | Provenance classes |
|---|---:|---:|---|
| `abs_loan_period` | 1,322,453 | 65 | — |
| `spread_observation` | 47,849 | 11 | — |
| `sanctions_name` | 45,511 | 9 | public |
| `peer_fact` | 22,494 | 15 | public |
| `institutional_holder` | 22,476 | 10 | public |
| `sanctions_entry` | 19,730 | 16 | public |
| `financial_fact` | 15,055 | 16 | public |
| `intraday_tick` | 11,700 | 5 | synthetic — engineered |
| `reference_rate` | 10,539 | 9 | public |
| `fx_intraday_tick` | 10,368 | 5 | synthetic — engineered |
| `benchmark_curve` | 8,917 | 4 | public |
| `interaction_participant` | 8,032 | 4 | synthetic — internal |
| `aml_transaction` | 4,358 | 7 | synthetic — engineered |
| `fx_reference_rate` | 3,942 | 8 | public |
| `market_oas_series` | 3,930 | 6 | public |
| `trend_delta` | 3,705 | 9 | public |
| `warn_notice` | 3,514 | 10 | public |
| `interaction` | 2,050 | 10 | synthetic — engineered, synthetic — internal |
| `person_crosswalk` | 1,815 | 9 | public, synthetic — engineered |
| `system_trade_record` | 1,815 | 5 | synthetic — internal |
| `peer_entity` | 1,678 | 6 | public |
| `signal_event` | 1,603 | 7 | public, synthetic — engineered |
| `coverage_assignment` | 1,000 | 5 | synthetic — engineered, synthetic — internal |
| `person_name_variant` | 997 | 6 | public, synthetic — engineered |
| `person` | 954 | 13 | public, synthetic — engineered |
| `gdelt_mention` | 951 | 11 | public |
| `person_role` | 817 | 9 | public |
| `fx_trade` | 500 | 7 | synthetic — internal |
| `peer_cohort` | 324 | 10 | public |
| `context_debt` | 303 | 7 | — |
| `corporate_ownership_record` | 280 | 12 | public |
| `psc_person` | 210 | 21 | synthetic — engineered |
| `aml_party` | 201 | 9 | synthetic — engineered |
| `investment_position` | 200 | 10 | synthetic — internal |
| `bo_chain_hop` | 169 | 8 | synthetic — engineered |
| `legal_entity` | 156 | 24 | public |
| `drawdown` | 151 | 10 | synthetic — engineered, synthetic — internal |
| `aml_alert` | 150 | 6 | synthetic — internal |
| `offshore_administration` | 150 | 4 | synthetic — engineered |
| `offshore_vehicle` | 150 | 7 | synthetic — engineered |
| `registry_company` | 140 | 16 | public |
| `abs_cohort_performance` | 132 | 11 | public |
| `engineered_entity` | 125 | 7 | synthetic — engineered |
| `deposit_account` | 120 | 8 | synthetic — internal |
| `gov_contract_concentration` | 104 | 9 | public |
| `debt_instrument` | 96 | 13 | synthetic — engineered |
| `collateral_pledge` | 95 | 4 | synthetic — engineered |
| `collateral_asset` | 91 | 13 | — |
| `crosswalk` | 83 | 7 | synthetic — internal |
| `perspective_weight` | 66 | 6 | synthetic — internal |
| `break_record` | 60 | 7 | synthetic — engineered |
| `concentration_limit` | 60 | 5 | synthetic — internal |
| `facility` | 60 | 23 | — |
| `aml_alert_link` | 50 | 3 | — |
| `bo_chain` | 50 | 10 | synthetic — engineered |
| `filing_profile` | 50 | 10 | public |
| `kyc_refresh_state` | 50 | 10 | synthetic — internal |
| `permitted_instrument` | 45 | 4 | synthetic — internal |
| `signal_weight` | 45 | 7 | synthetic — internal |
| `syndicate_member` | 45 | 10 | public |
| `part43_profile` | 44 | 6 | public |
| `banker` | 40 | 6 | synthetic — internal |
| `mandate` | 40 | 8 | synthetic — internal |
| `offshore_intermediary` | 40 | 6 | synthetic — engineered |
| `abs_servicer_report` | 36 | 17 | public |
| `warn_match` | 36 | 9 | synthetic — internal |
| `deal` | 32 | 8 | synthetic — internal |
| `memo_section_template` | 31 | 4 | synthetic — internal |
| `internal_client` | 30 | 17 | synthetic — internal |
| `guarantee_terms` | 28 | 7 | synthetic — engineered, synthetic — internal |
| `abs_cost_measurement` | 24 | 9 | — |
| `abs_vintage_benchmark` | 24 | 9 | public |
| `memo_context_debt` | 20 | 10 | derived |
| `sanctions_screening_result` | 19 | 12 | synthetic — engineered (person) / public (listing) |
| `abs_tranche` | 18 | 9 | public |
| `bo_threshold` | 18 | 5 | synthetic — internal |
| `principal_jurisdiction` | 17 | 3 | synthetic — internal |
| `member_call_report` | 16 | 8 | public |
| `ucc_debtor_crosswalk` | 16 | 6 | synthetic — internal |
| `rating_scale` | 15 | 6 | synthetic — internal |
| `treasury_client` | 15 | 8 | synthetic — internal |
| `debt_reconciliation` | 14 | 5 | — |
| `bank_capital` | 12 | 16 | public |
| `setoff_enforceability` | 12 | 3 | synthetic — internal |
| `ib_signal_class` | 11 | 4 | synthetic — internal |
| `position` | 10 | 6 | synthetic — internal |
| `divergence_threshold` | 9 | 5 | synthetic — internal |
| `abs_repurchase` | 8 | 10 | public |
| `abs_holding` | 6 | 7 | synthetic — internal |
| `corpus_entitlement` | 6 | 4 | synthetic — internal |
| `escalation_threshold` | 6 | 13 | synthetic — internal |
| `fx_pip_size` | 6 | 3 | public |
| `haircut_schedule` | 6 | 3 | synthetic — internal |
| `scoring_weight` | 6 | 5 | synthetic — internal |
| `name_variant_rule` | 5 | 3 | synthetic — internal |
| `own_position` | 5 | 7 | synthetic — internal |
| `abs_materialization_policy` | 4 | 5 | synthetic — internal |
| `competition_law_rule` | 4 | 5 | synthetic — internal |
| `debt_weight` | 4 | 3 | synthetic — internal |
| `principal` | 4 | 8 | synthetic — internal |
| `stale_signal` | 4 | 6 | synthetic — engineered |
| `abs_deal` | 3 | 10 | public |
| `abs_granularity_entitlement` | 3 | 4 | synthetic — internal |
| `aml_projection_plan` | 3 | 3 | synthetic — internal |
| `ib_perspective` | 3 | 4 | synthetic — internal |
| `ib_projection_plan` | 3 | 5 | synthetic — internal |
| `large_exposure_projection_plan` | 3 | 6 | synthetic — internal |
| `limit_definition` | 3 | 6 | synthetic — internal |
| `materiality_threshold` | 3 | 3 | synthetic — internal |
| `projection_plan` | 3 | 7 | synthetic — internal |
| `resolution_policy` | 3 | 5 | synthetic — internal |
| `syndicate_projection_plan` | 3 | 3 | synthetic — internal |
| `covenant_breach` | 2 | 9 | synthetic — engineered |
| `covenant_policy` | 2 | 7 | synthetic — internal |
| `exposure_proposal` | 2 | 8 | synthetic — engineered |
| `reporting_bank` | 2 | 11 | public |

**Views** (not base tables; a consumer would otherwise rebuild these joins by hand):

- `v_entity_jurisdiction` — 421 rows
- `v_ownership_cross_border` — 532 rows

## Fluree — `R` and `T`, the typed edge graph and its valid time

Nodes carry `lei` plus a display label and nothing else; every attribute resolves from Postgres. Top 40 predicates by assertion count:

| Predicate | Assertions |
|---|---:|
| `http://www.w3.org/1999/02/22-rdf-syntax-ns#type` | 18,738 |
| `http://www.w3.org/2000/01/rdf-schema#label` | 11,393 |
| `http://example.org/fibo/participatedIn` | 8,032 |
| `http://example.org/fibo/provenance` | 7,848 |
| `http://example.org/fibo/transactedWith` | 7,736 |
| `http://example.org/fibo/validFrom` | 3,022 |
| `http://example.org/fibo/amendmentSeq` | 1,920 |
| `http://example.org/fibo/signalAbout` | 1,863 |
| `http://example.org/fibo/observedIn` | 1,815 |
| `http://example.org/fibo/recordedBySystem` | 1,815 |
| `http://example.org/fibo/systemObservedAt` | 1,815 |
| `http://example.org/fibo/assertedAt` | 1,555 |
| `http://example.org/fibo/isCurrent` | 1,270 |
| `http://example.org/fibo/magnitude` | 1,270 |
| `http://example.org/fibo/sourceAccession` | 1,265 |
| `http://example.org/fibo/supersededBy` | 1,107 |
| `http://example.org/fibo/coveredBy` | 1,000 |
| `http://example.org/fibo/filedBy` | 788 |
| `https://spec.edmcouncil.org/fibo/ontology/FND/Organizations/FormalOrganizations/isEmployedBy` | 701 |
| `https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/Ownership/owns` | 636 |
| `http://example.org/fibo/item` | 535 |
| `http://example.org/fibo/triggeredBy` | 535 |
| `http://example.org/fibo/jurisdictionCode` | 496 |
| `http://example.org/fibo/lei` | 449 |
| `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Executives/isDirectorOf` | 436 |
| `http://example.org/fibo/variantId` | 426 |
| `https://spec.edmcouncil.org/fibo/ontology/FND/AgentsAndPeople/People/hasPersonName` | 426 |
| `https://www.omg.org/spec/Commons/Identifiers/isIdentifiedBy` | 426 |
| `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Executives/isOfficerOf` | 324 |
| `http://example.org/fibo/filedJurisdiction` | 306 |
| `http://example.org/fibo/covenantType` | 277 |
| `http://example.org/fibo/documentId` | 263 |
| `http://example.org/fibo/startOffset` | 262 |
| `https://spec.edmcouncil.org/fibo/ontology/FBC/DebtAndEquities/CreditRatings/concernsParty` | 254 |
| `http://example.org/fibo/grade` | 245 |
| `http://example.org/fibo/trigger` | 245 |
| `http://example.org/fibo/validTo` | 229 |
| `http://example.org/fibo/threshold` | 225 |
| `http://example.org/fibo/crossReferences` | 216 |
| `http://example.org/fibo/concentratedIn` | 200 |

*181 predicates total; the full list is in the JSON.*

Declared types by instance count (top 15):

| Type | Instances |
|---|---:|
| `http://example.org/fibo/Interaction` | 2,050 |
| `http://example.org/fibo/SystemObservation` | 1,815 |
| `http://example.org/fibo/OpportunitySignal` | 1,270 |
| `https://spec.edmcouncil.org/fibo/ontology/FND/AgentsAndPeople/People/Person` | 915 |
| `http://example.org/fibo/IssuanceEvent` | 908 |
| `https://www.omg.org/spec/Commons/Organizations/FormalOrganization` | 854 |
| `https://www.omg.org/spec/Commons/Organizations/LegalEntity` | 854 |
| `https://www.omg.org/spec/Commons/Organizations/LegalPerson` | 854 |
| `https://www.omg.org/spec/Commons/Organizations/Organization` | 854 |
| `https://www.omg.org/spec/Commons/PartiesAndSituations/Agent` | 854 |
| `https://www.omg.org/spec/Commons/PartiesAndSituations/Party` | 854 |
| `https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/CorporateBodies/Corporation` | 661 |
| `http://example.org/fibo/WarningSignal` | 538 |
| `https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/Trade` | 500 |
| `https://spec.edmcouncil.org/fibo/ontology/FND/AgentsAndPeople/People/PersonName` | 426 |

## MongoDB — passage-level lineage

### `document` — 249 documents (249 sampled)

| Field | Type(s) | Present in sample |
|---|---|---:|
| `_id` | str | 100.0% |
| `accession` | str | 64.3% |
| `advisory_number` | str | 1.6% |
| `agreement_date` | str | 14.5% |
| `agreement_id` | str | 14.5% |
| `agreement_role` | str | 14.5% |
| `alert_id` | str | 4.8% |
| `case_id` | str | 4.8% |
| `cik` | int, str | 79.9% |
| `citation` | str | 12.4% |
| `classification` | str | 80.3% |
| `deal_id` | str | 15.7% |
| `doc_type` | str | 28.5% |
| `document` | str | 64.3% |
| `document_id` | str | 100.0% |
| `effective_date` | NoneType, str | 12.4% |
| `filed_at` | str | 4.8% |
| `filed_date` | str | 64.3% |
| `filing_rationale` | str | 4.8% |
| `form` | str | 79.9% |
| `governs_from` | str | 14.5% |
| `issued` | str | 1.6% |
| `lei` | str | 64.3% |
| `page_count` | int | 0.4% |
| `passage_count` | int | 81.5% |
| `path` | str | 1.6% |
| `pdf_url` | str | 1.6% |
| `period` | str | 14.5% |
| `provenance` | str | 100.0% |
| `published_measures` | dict | 14.5% |
| `published_measures.source_format` | str | 14.5% |
| `regime` | str | 12.4% |
| `residency` | str | 80.3% |
| `retrieved_at` | str | 94.4% |
| `sar_id` | str | 4.8% |
| `sec_name` | str | 79.9% |
| `section` | str | 30.9% |
| `source` | str | 94.4% |
| `source_offset` | int | 30.9% |
| `source_sha256` | str | 12.4% |
| `subject_party` | str | 4.8% |
| `text` | str | 100.0% |
| `text_length` | int | 94.4% |
| `text_sha256` | str | 94.4% |
| `title` | str | 14.9% |
| `typology` | str | 1.6% |
| `typology_id` | str | 4.8% |
| `url` | str | 35.3% |

### `kyc_document` — 32 documents (32 sampled)

| Field | Type(s) | Present in sample |
|---|---|---:|
| `_id` | ObjectId | 100.0% |
| `applicable_threshold_pct` | float | 100.0% |
| `chain_id` | str | 100.0% |
| `classification` | str | 100.0% |
| `declared_on` | str | 100.0% |
| `declared_owner_name` | NoneType, str | 100.0% |
| `declared_owner_person_key` | NoneType, str | 100.0% |
| `declared_pct` | NoneType, float | 100.0% |
| `document_id` | str | 100.0% |
| `entity_id` | str | 100.0% |
| `entity_name` | str | 100.0% |
| `jurisdiction` | str | 100.0% |
| `kind` | str | 100.0% |
| `passage_count` | int | 100.0% |
| `planted_contradiction_kind` | NoneType, str | 100.0% |
| `provenance` | str | 100.0% |
| `residency` | str | 100.0% |
| `source` | str | 100.0% |
| `text` | str | 100.0% |
| `text_length` | int | 100.0% |
| `text_sha256` | str | 100.0% |
| `title` | str | 100.0% |

### `memorandum` — 40 documents (40 sampled)

| Field | Type(s) | Present in sample |
|---|---|---:|
| `_id` | str | 100.0% |
| `authored_date` | str | 100.0% |
| `body` | str | 100.0% |
| `borrower_lei` | str | 100.0% |
| `classification` | str | 100.0% |
| `embedding` | list | 55.0% |
| `embedding_dimensions` | int | 55.0% |
| `embedding_model` | str | 55.0% |
| `facility_id` | str | 100.0% |
| `memo_type` | str | 45.0% |
| `memorandum_id` | str | 100.0% |
| `provenance` | str | 100.0% |
| `residency` | str | 100.0% |
| `retrieved_at` | str | 100.0% |
| `source` | str | 100.0% |
| `text_sha256` | str | 100.0% |
| `title` | str | 100.0% |

### `passage` — 37,865 documents (500 sampled)

| Field | Type(s) | Present in sample |
|---|---|---:|
| `_id` | ObjectId, str | 100.0% |
| `alignment` | str | 98.8% |
| `document_id` | str | 100.0% |
| `effective_date` | NoneType, str | 1.2% |
| `embedding` | NoneType, list | 100.0% |
| `embedding_dimensions` | int | 96.6% |
| `embedding_model` | NoneType, str | 100.0% |
| `end_offset` | int | 100.0% |
| `heading` | str | 98.8% |
| `length` | int | 100.0% |
| `passage_id` | str | 100.0% |
| `provenance` | str | 100.0% |
| `provision` | str | 1.2% |
| `regime` | str | 1.2% |
| `sha256` | str | 98.8% |
| `start_offset` | int | 100.0% |
| `structure_aligned` | bool | 98.8% |
| `text` | str | 100.0% |

### `research_note` — 42 documents (42 sampled)

| Field | Type(s) | Present in sample |
|---|---|---:|
| `_id` | str | 100.0% |
| `authored_date` | str | 100.0% |
| `body` | str | 100.0% |
| `classification` | str | 100.0% |
| `embargo_until` | NoneType, str | 100.0% |
| `embedding` | list | 100.0% |
| `embedding_dimensions` | int | 100.0% |
| `embedding_model` | str | 100.0% |
| `lei` | str | 100.0% |
| `note_id` | str | 100.0% |
| `provenance` | str | 100.0% |
| `retrieved_at` | str | 100.0% |
| `status` | str | 100.0% |
| `title` | str | 100.0% |

### `trigger_anchor` — 10 documents (10 sampled)

| Field | Type(s) | Present in sample |
|---|---|---:|
| `_id` | str | 100.0% |
| `complete_span` | bool | 100.0% |
| `deal_id` | str | 100.0% |
| `document_id` | str | 100.0% |
| `end_offset` | int | 100.0% |
| `passage_id` | str | 100.0% |
| `provenance` | str | 100.0% |
| `quoted_text` | str | 100.0% |
| `start_offset` | int | 100.0% |
| `trigger_id` | str | 100.0% |

## SQLite — the departmental store

Deliberately a local file. The point of the narrative is that the fabric must reach a small, locally-maintained system to enforce an enterprise-critical policy.

- **`_schema_meta`** — 4 rows · `key` TEXT, `value` TEXT, `updated_at` TEXT
- **`covenant_tracker`** — 45 rows · `facility_id` TEXT, `covenant_type` TEXT, `next_test_date` TEXT, `last_test_result` TEXT, `watch_flag` INTEGER, `analyst_note` TEXT, `updated_at` TEXT, `provenance` TEXT
- **`large_exposure_limit_workbook`** — 5 rows · `line_id` TEXT, `group_label` TEXT, `limit_intent` TEXT, `limit_pct` REAL, `note` TEXT, `owner` TEXT, `reviewed_on` TEXT, `provenance` TEXT
- **`prospect_note`** — 50 rows · `note_id` TEXT, `lei` TEXT, `prospect_name` TEXT, `banker` TEXT, `note` TEXT, `priority` TEXT, `created_at` TEXT, `provenance` TEXT, `banker_id` TEXT, `banker_display` TEXT, `signal_type` TEXT, `materiality` TEXT, `rank_changing` INTEGER
- **`restricted_list`** — 4 rows · `lei` TEXT, `legal_name` TEXT, `ticker` TEXT, `restriction_type` TEXT, `added_date` TEXT, `removed_date` TEXT, `added_by` TEXT, `reason_code` TEXT, `provenance` TEXT
- **`risk_limit_workbook`** — 16 rows · `limit_id` TEXT, `scope` TEXT, `scope_value` TEXT, `limit_type` TEXT, `limit_amount` REAL, `utilisation` REAL, `owner` TEXT, `reviewed_at` TEXT, `provenance` TEXT
- **`sar_classification`** — 12 rows · `sar_id` TEXT, `alert_id` TEXT, `classification` TEXT, `visible_to_perspectives` TEXT, `provenance` TEXT
- **`syndicate_desk_tracker`** — 12 rows · `tracker_id` TEXT, `facility_id` TEXT, `desk_note` TEXT, `internal_flag` TEXT, `updated_at` TEXT, `provenance` TEXT

## Neo4j

v1 starter set only — no v2 Context Product depends on this store; see CLAUDE.md's open decision

- Labels: `Address`, `Corporation`, `KGEntity`, `Party`
- Relationship types: `HAS_CONTROLLING_INTEREST_IN`, `HAS_OWNERSHIP_INTEREST_IN`, `IS_RELATED_TO`

