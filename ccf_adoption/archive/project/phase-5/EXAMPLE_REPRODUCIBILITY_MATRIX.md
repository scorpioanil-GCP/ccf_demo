# Phase 5 — Example Reproducibility Matrix

**Qualified SDK:** `drcastillo/ccf_code/main@ff470d400976815e9a1e49176ca51f97e4e691b1`

## Purpose

The short Example Catalog is not sufficient developer guidance by itself.

Every qualified Context Product now has a dedicated reproduction guide under
`05-reference/02-context-product-producer/examples/` that covers:

- why the example exists;
- the question it answers;
- prerequisites/environment;
- files to read;
- exact run commands;
- expected governed behavior;
- semantic variations;
- validation tests;
- what the example proves;
- what it does not prove;
- the spec-to-code lesson for Cowork.

## Context Product coverage

| Rung | Reproduction guide | Run | Vary | Validate | Boundaries | Cowork lesson |
|---:|---|:---:|:---:|:---:|:---:|:---:|
| CP-00 | `CP00_INSTITUTIONAL_HOLDERS.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-01 | `CP01_COUNTERPARTY_REFERENCE_SNAPSHOT.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-02 | `CP02_FACILITY_TERMS_SNAPSHOT.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-03 | `CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-04 | `CP04_CANONICAL_CORPORATE_FAMILY_TREE.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-05 | `CP05_CREDIT_EXPOSURE_ROLLUP.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-06 | `CP06_CANONICAL_COLLATERAL_AND_SETOFF_COVERAGE.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-07 | `CP07_CLIENT_360_COVERAGE_GRAPH.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-08 | `CP08_COVENANT_IN_FORCE_AS_OF.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-09 | `CP09_TREASURY_LIQUIDITY_POSITION.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-10 | `CP10_RATING_AND_SPREAD_MIGRATION.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-11 | `CP11_CREDIT_SURVEILLANCE_EARLY_WARNING.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-12 | `CP12_FX_POST_TRADE_RECONCILIATION.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-13 | `CP13_CANONICAL_COVENANT_CROSS_REFERENCE.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-14 | `CP14_CREDIT_MEMO_CONTEXT.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-15 | `CP15_KYC_REFRESH_BENEFICIAL_OWNERSHIP.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-16 | `CP16_ABS_SECURITIZATION_SURVEILLANCE.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-17 | `CP17_MNPI_WALL_ENFORCEMENT.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-18 | `CP18_IB_OPPORTUNITY_SYNTHESIS.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-19 | `CP19_AML_TYPOLOGY_MATCH.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-20 | `CP20_SYNDICATED_LENDING_CO_LENDER.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-21 | `CP21_LARGE_EXPOSURE.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-22 | `CP22_AGENT_INTERNAL_ASSEMBLY.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-23 | `CP23_PORTFOLIO_EARLY_WARNING.md` | ✓ | ✓ | ✓ | ✓ | ✓ |
| CP-24 | `CP24_PORTFOLIO_WHAT_IF.md` | ✓ | ✓ | ✓ | ✓ | ✓ |

## Decision Replay capability coverage

| Capability | Guide | Run | Vary | Validate | Boundaries |
|---|---|:---:|:---:|:---:|:---:|
| DR-01 — Replay a Governed Determination | `decision-replay/DR01_REPLAY_A_GOVERNED_DETERMINATION.md` | ✓ | ✓ | ✓ | ✓ |
| DR-02 — Package a Context Product | `decision-replay/DR02_PACKAGE_A_CONTEXT_PRODUCT.md` | ✓ | ✓ | ✓ | ✓ |

DR-01 and DR-02 are final capability examples over Context Products. They do not extend the CP-00 through CP-24 ladder.

## Starter / consumer coverage

| Example | Guide | Reproduction role |
|---|---|---|
| HW-1 consumer | `HW1_CLIENT_CONSUMER.md` | same product, in-process vs MCP |
| HW-1 harness clients | `HW1_HARNESS_CLIENTS.md` | ADK vs Claude Agent SDK vs LangGraph |
| S1-00 | `S1_00_COMPANIES_OVER_REVENUE.md` | smallest parameterized assembler example |
| S1-01 | `S1_01_HELLO_CONTEXT_PRODUCT.md` | small networked-substrate example, with qualification prerequisite caveat |

## Mechanical QA

- CP-00 through CP-24: complete detailed coverage.
- DR-01 and DR-02: detailed final capability coverage added.
- Starter/client guides remain available.
- Final release link/source-path verification is tracked in the Phase 5 release-readiness record.
- local-machine `192.168.*` addresses are not part of the adoption reproduction contract.

## Review question

The remaining question is qualitative:

> **Does each guide give a competent developer enough context to understand the example and reproduce the intended governed behavior without reverse-engineering the SDK repository?**

That is now a human-review question rather than a missing-documentation question.
