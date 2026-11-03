# CCF-SDK example analysis companions

**New current-main companion:** [SK-01 — Declare and govern agent skills](SK01_DECLARE_AND_GOVERN_AGENT_SKILLS_ANALYSIS.md), with [implementation](SK01_DECLARE_AND_GOVERN_AGENT_SKILLS.md) and [HTML](SK01_DECLARE_AND_GOVERN_AGENT_SKILLS_ANALYSIS.html). Unlike CP00–CP24, SK-01 ships no final `spec/` file; its analysis maps actual declarations to Standard v0.3 without inventing a completed specification.

**Current-use note:** the CP source excerpts below remain dated evidence. Use Fluree **4.2.4** and the [current SDK migration guidance](../../05-technical-reference/MIGRATION_AND_LIMITATIONS.md) for operations. The former cp-example freeze has been lifted; wording in embedded historical specs is not a current restriction.

Business-to-spec walkthroughs for banking SMEs and Information Architects. The CP companions reconstruct each implementation example’s own final specification using Standard v0.3, with exact source snapshots for review. SK-01 instead maps its shipped declarations into that structure because it has no separate final specification. Figures are the source’s recorded teaching-estate measurements or declared values, not newly executed SDK results.

**Coverage:** CP00–CP24 plus SK-01: 26 implementation guides and 26 `_ANALYSIS.md` companions. CP02 retains the user-approved revision; CP01 is corrected against its own final spec. The canonical guides use the canonical specs for CP03, CP04, CP06 and CP13.

**Reading:** open a Markdown companion on GitHub, or download its HTML reading edition for tables and embedded sources without external source-link dependencies. Each implementation guide links back to both editions.

**Master reading edition:** [All 26 example analyses](CCF_EXAMPLES_ANALYSIS_REVIEW.html). Download and open this self-contained HTML file to browse the complete collection, with rendered tables and embedded sources.

**Source baseline:** SDK `37ac3055fd64ed64d78c6fd5555d79e451859153` for the 24 newly written/revised companions; approved CP02 retains SDK `4494b93621bb252154f2fd7dc304a71290394ee8`. Readiness findings, unimplemented obligations and conflicting historical wording are disclosed rather than silently rewritten. [Source manifest](ANALYSIS_SOURCES.json).

| Example | Analysis | HTML reading edition | SDK implementation walkthrough |
| --- | --- | --- | --- |
| CP-00 — Institutional Holders | [Analysis](CP00_INSTITUTIONAL_HOLDERS_ANALYSIS.md) | [HTML](CP00_INSTITUTIONAL_HOLDERS_ANALYSIS.html) | [Implementation](CP00_INSTITUTIONAL_HOLDERS.md) |
| CP-01 — Counterparty Reference Snapshot | [Analysis](CP01_COUNTERPARTY_REFERENCE_SNAPSHOT_ANALYSIS.md) | [HTML](CP01_COUNTERPARTY_REFERENCE_SNAPSHOT_ANALYSIS.html) | [Implementation](CP01_COUNTERPARTY_REFERENCE_SNAPSHOT.md) |
| CP-02 — Facility Terms Snapshot | [Analysis](CP02_FACILITY_TERMS_SNAPSHOT_ANALYSIS.md) | [HTML](CP02_FACILITY_TERMS_SNAPSHOT_ANALYSIS.html) | [Implementation](CP02_FACILITY_TERMS_SNAPSHOT.md) |
| CP-03 — Obligor Financial Spread — Canonical | [Analysis](CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD_ANALYSIS.md) | [HTML](CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD_ANALYSIS.html) | [Implementation](CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD.md) |
| CP-04 — Corporate Family Tree — Canonical | [Analysis](CP04_CANONICAL_CORPORATE_FAMILY_TREE_ANALYSIS.md) | [HTML](CP04_CANONICAL_CORPORATE_FAMILY_TREE_ANALYSIS.html) | [Implementation](CP04_CANONICAL_CORPORATE_FAMILY_TREE.md) |
| CP-05 — Credit Exposure Rollup | [Analysis](CP05_CREDIT_EXPOSURE_ROLLUP_ANALYSIS.md) | [HTML](CP05_CREDIT_EXPOSURE_ROLLUP_ANALYSIS.html) | [Implementation](CP05_CREDIT_EXPOSURE_ROLLUP.md) |
| CP-06 — Collateral & Set-off Coverage — Canonical | [Analysis](CP06_CANONICAL_COLLATERAL_AND_SETOFF_COVERAGE_ANALYSIS.md) | [HTML](CP06_CANONICAL_COLLATERAL_AND_SETOFF_COVERAGE_ANALYSIS.html) | [Implementation](CP06_CANONICAL_COLLATERAL_AND_SETOFF_COVERAGE.md) |
| CP-07 — Client 360 / Coverage Graph | [Analysis](CP07_CLIENT_360_COVERAGE_GRAPH_ANALYSIS.md) | [HTML](CP07_CLIENT_360_COVERAGE_GRAPH_ANALYSIS.html) | [Implementation](CP07_CLIENT_360_COVERAGE_GRAPH.md) |
| CP-08 — Covenant-in-Force As-Of | [Analysis](CP08_COVENANT_IN_FORCE_AS_OF_ANALYSIS.md) | [HTML](CP08_COVENANT_IN_FORCE_AS_OF_ANALYSIS.html) | [Implementation](CP08_COVENANT_IN_FORCE_AS_OF.md) |
| CP-09 — Treasury Liquidity Position | [Analysis](CP09_TREASURY_LIQUIDITY_POSITION_ANALYSIS.md) | [HTML](CP09_TREASURY_LIQUIDITY_POSITION_ANALYSIS.html) | [Implementation](CP09_TREASURY_LIQUIDITY_POSITION.md) |
| CP-10 — Rating & Spread Migration | [Analysis](CP10_RATING_AND_SPREAD_MIGRATION_ANALYSIS.md) | [HTML](CP10_RATING_AND_SPREAD_MIGRATION_ANALYSIS.html) | [Implementation](CP10_RATING_AND_SPREAD_MIGRATION.md) |
| CP-11 — Credit Surveillance / Early Warning | [Analysis](CP11_CREDIT_SURVEILLANCE_EARLY_WARNING_ANALYSIS.md) | [HTML](CP11_CREDIT_SURVEILLANCE_EARLY_WARNING_ANALYSIS.html) | [Implementation](CP11_CREDIT_SURVEILLANCE_EARLY_WARNING.md) |
| CP-12 — FX Post-Trade Reconciliation | [Analysis](CP12_FX_POST_TRADE_RECONCILIATION_ANALYSIS.md) | [HTML](CP12_FX_POST_TRADE_RECONCILIATION_ANALYSIS.html) | [Implementation](CP12_FX_POST_TRADE_RECONCILIATION.md) |
| CP-13 — Covenant Cross-Reference — Canonical | [Analysis](CP13_CANONICAL_COVENANT_CROSS_REFERENCE_ANALYSIS.md) | [HTML](CP13_CANONICAL_COVENANT_CROSS_REFERENCE_ANALYSIS.html) | [Implementation](CP13_CANONICAL_COVENANT_CROSS_REFERENCE.md) |
| CP-14 — Credit Memo Context — Composite | [Analysis](CP14_CREDIT_MEMO_CONTEXT_ANALYSIS.md) | [HTML](CP14_CREDIT_MEMO_CONTEXT_ANALYSIS.html) | [Implementation](CP14_CREDIT_MEMO_CONTEXT.md) |
| CP-15 — KYC Refresh / Beneficial Ownership | [Analysis](CP15_KYC_REFRESH_BENEFICIAL_OWNERSHIP_ANALYSIS.md) | [HTML](CP15_KYC_REFRESH_BENEFICIAL_OWNERSHIP_ANALYSIS.html) | [Implementation](CP15_KYC_REFRESH_BENEFICIAL_OWNERSHIP.md) |
| CP-16 — ABS / Securitization Surveillance | [Analysis](CP16_ABS_SECURITIZATION_SURVEILLANCE_ANALYSIS.md) | [HTML](CP16_ABS_SECURITIZATION_SURVEILLANCE_ANALYSIS.html) | [Implementation](CP16_ABS_SECURITIZATION_SURVEILLANCE.md) |
| CP-17 — MNPI Wall Enforcement | [Analysis](CP17_MNPI_WALL_ENFORCEMENT_ANALYSIS.md) | [HTML](CP17_MNPI_WALL_ENFORCEMENT_ANALYSIS.html) | [Implementation](CP17_MNPI_WALL_ENFORCEMENT.md) |
| CP-18 — IB Opportunity Synthesis | [Analysis](CP18_IB_OPPORTUNITY_SYNTHESIS_ANALYSIS.md) | [HTML](CP18_IB_OPPORTUNITY_SYNTHESIS_ANALYSIS.html) | [Implementation](CP18_IB_OPPORTUNITY_SYNTHESIS.md) |
| CP-19 — AML Typology Match | [Analysis](CP19_AML_TYPOLOGY_MATCH_ANALYSIS.md) | [HTML](CP19_AML_TYPOLOGY_MATCH_ANALYSIS.html) | [Implementation](CP19_AML_TYPOLOGY_MATCH.md) |
| CP-20 — Syndicated Lending Co-Lender | [Analysis](CP20_SYNDICATED_LENDING_CO_LENDER_ANALYSIS.md) | [HTML](CP20_SYNDICATED_LENDING_CO_LENDER_ANALYSIS.html) | [Implementation](CP20_SYNDICATED_LENDING_CO_LENDER.md) |
| CP-21 — Large Exposure / Concentration | [Analysis](CP21_LARGE_EXPOSURE_ANALYSIS.md) | [HTML](CP21_LARGE_EXPOSURE_ANALYSIS.html) | [Implementation](CP21_LARGE_EXPOSURE.md) |
| CP-22 — Agent-Internal Assembly | [Analysis](CP22_AGENT_INTERNAL_ASSEMBLY_ANALYSIS.md) | [HTML](CP22_AGENT_INTERNAL_ASSEMBLY_ANALYSIS.html) | [Implementation](CP22_AGENT_INTERNAL_ASSEMBLY.md) |
| CP-23 — Portfolio Early-Warning / Concentration | [Analysis](CP23_PORTFOLIO_EARLY_WARNING_ANALYSIS.md) | [HTML](CP23_PORTFOLIO_EARLY_WARNING_ANALYSIS.html) | [Implementation](CP23_PORTFOLIO_EARLY_WARNING.md) |
| CP-24 — Portfolio What-If / Stress | [Analysis](CP24_PORTFOLIO_WHAT_IF_ANALYSIS.md) | [HTML](CP24_PORTFOLIO_WHAT_IF_ANALYSIS.html) | [Implementation](CP24_PORTFOLIO_WHAT_IF.md) |

## Current SDK compatibility — 9 October 2026

All final-specification blob hashes in [ANALYSIS_SOURCES.json](ANALYSIS_SOURCES.json) match current main `f07e558e`. The source at `37ac3055` differs from current main only in `docs/DECISIONS.md`, so these business-to-spec narratives and embedded snapshots require no speculative rewrite. CP02 keeps its approved source snapshot; its final-spec blob also matches current main.

The implementation guides retain their historical qualification pins. Use [current SDK update status](../../../SDK_UPDATE_STATUS.md) and [technical reference](../../05-technical-reference/README.md) for migration, current API signatures and open security state. The master HTML is the unchanged snapshot reading edition.
