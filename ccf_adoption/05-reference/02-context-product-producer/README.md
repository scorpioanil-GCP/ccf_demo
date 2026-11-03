# Context Product Producer / Data Engineer Path

**Running examples:** [current setup, Fluree 4.2.4 and connection configuration](../../examples/CONFIGURATION.md).

**New: [Context Skills](../05-technical-reference/CONTEXT_SKILLS.md)** — how a bank agent is granted authority to ask a Context Product, with the SK-01 implementation and SME/Information Architect analysis. Current Fluree requirement: **4.2.4**.

> **Current-main execution note (17 Oct 2026).** The learning sequence/specification lineage is intentionally preserved, but the executable SDK examples on current `ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178` have received demonstration-clock, entitlement/grant, door, integrity and remediation updates. When running an example, the current SDK tree and its documented command are the execution authority; use the companion page here to understand the business/spec lineage.

## Goal

Learn how an approved Context Product specification becomes governed configuration, source acquisition, graph state, projection, gates, and a servable product.

For the shipped CP examples, **the specification work is already done for you**.

Do not begin by asking an LLM to write a new spec.

Begin by learning to read a completed spec and trace it into running code.

## Before you begin — install the CCF data estate

The Context Product producer examples run against the same restored data estate the CCF SDK is built and evaluated against. **Install and verify that estate before starting CP-00.**

### Required local datastores

Install the pinned engines used by the estate:

| Engine | Required version | Notes |
|---|---:|---|
| PostgreSQL | **16** | The shipped custom-format dumps require PostgreSQL 16. |
| MongoDB | **8.x** | `mongorestore` comes from the separate MongoDB Database Tools package. |
| Fluree | **4.2.4** | Intel macOS uses the Docker path described by the estate install guide. |
| SQLite | any current version | Normally already present. |
| Neo4j | **2026.07.x** | Optional; no unique data is held only in Neo4j. |

### Restore and verify the estate

The restore package is the `ccf-estate-bundle`. Follow its platform-specific installation guide, then:

1. verify the downloaded archive and unpack it;
2. restore Fluree, PostgreSQL, MongoDB, SQLite, and optionally Neo4j;
3. start the Fluree server;
4. run the estate verifier;
5. clone `ccf_dataprep`;
6. point `ccf_dataprep/.env` at **your restored local stores**;
7. confirm the repository can read the restored estate;
8. run the data validators.

The restore verifier must complete successfully before you treat the environment as ready for the producer examples.

### Important: restored estate vs rebuilding the estate

The producer examples assume the estate has already been restored.

**Do not run the `ccf_dataprep` loaders after restoring the bundle.** Those loaders build/rebuild the estate and can overwrite what you restored.

### Important: environment variable names

The restore bundle and `ccf_dataprep` do not use identical variable names.

For example:

| Concept | Restore bundle | `ccf_dataprep` |
|---|---|---|
| Fluree endpoint | `CCF_FLUREE_URL` | `FLUREE_URL` |
| Mongo endpoint | `CCF_MONGO_URI` | `MONGO_URI` |
| SQLite path | `CCF_SQLITE_PATH` | `SQLITE_PATH` |
| PostgreSQL database | `CCF_PGDATABASE` | `PGDATABASE` |

After restoring, make sure `ccf_dataprep/.env` points to **your machine**, not to the original estate build host.

### What the restored estate contains

The producer ladder expects the restored estate to provide:

- Fluree `fibo-v2` — ontology and typed relationship graph;
- PostgreSQL `ccf_v2` — obligors, facilities, exposures, covenants, signals, and related structured data;
- MongoDB `fibo_v2` — filed documents and passage-level content;
- SQLite — departmental/restricted data used by later products;
- optional Neo4j — graph-algorithm backing;
- the peer fabric used by the co-lender/federation example.

Once this prerequisite is complete, begin with **CP-00**.

## The learning loop for every example

```
1. Open the completed approved spec
2. Read the decision and contract
3. Read the data catalog / source reality
4. Read the assembly recipe and gates
5. Map those sections to config + Python
6. Run the default case
7. Change one governed dimension
8. Exercise a refusal / boundary
9. Run the tests / gates
```

[How to read a shipped Context Product example →](00-how-to-read-an-example.md)

## Example progression

The examples are ordered intentionally.

### Foundation

- [CP-00 — Institutional Holders](examples/CP00_INSTITUTIONAL_HOLDERS.md)
- [CP-01 — Counterparty Reference Snapshot](examples/CP01_COUNTERPARTY_REFERENCE_SNAPSHOT.md)
- [CP-02 — Facility Terms Snapshot](examples/CP02_FACILITY_TERMS_SNAPSHOT.md)
- [CP-03 — Obligor Financial Spread — canonical](examples/CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD.md)

### Graph and relationship context

- [CP-04 — Corporate Family Tree — canonical](examples/CP04_CANONICAL_CORPORATE_FAMILY_TREE.md)
- [CP-05 — Credit Exposure Rollup](examples/CP05_CREDIT_EXPOSURE_ROLLUP.md)
- [CP-06 — Collateral & Set-off Coverage — canonical](examples/CP06_CANONICAL_COLLATERAL_AND_SETOFF_COVERAGE.md)
- [CP-07 — Client 360 / Coverage Graph](examples/CP07_CLIENT_360_COVERAGE_GRAPH.md)

### Temporal context

- [CP-08 — Covenant-in-Force As-Of](examples/CP08_COVENANT_IN_FORCE_AS_OF.md)
- [CP-09 — Treasury Liquidity Position](examples/CP09_TREASURY_LIQUIDITY_POSITION.md)
- [CP-10 — Rating & Spread Migration](examples/CP10_RATING_AND_SPREAD_MIGRATION.md)
- [CP-11 — Credit Surveillance / Early Warning](examples/CP11_CREDIT_SURVEILLANCE_EARLY_WARNING.md)
- [CP-12 — FX Post-Trade Reconciliation](examples/CP12_FX_POST_TRADE_RECONCILIATION.md)

### Documents, composition, and human review

- [CP-13 — Covenant Cross-Reference — canonical](examples/CP13_CANONICAL_COVENANT_CROSS_REFERENCE.md)
- [CP-14 — Credit Memo Context](examples/CP14_CREDIT_MEMO_CONTEXT.md)
- [CP-15 — KYC Refresh / Beneficial Ownership](examples/CP15_KYC_REFRESH_BENEFICIAL_OWNERSHIP.md)
- [CP-16 — ABS / Securitization Surveillance](examples/CP16_ABS_SECURITIZATION_SURVEILLANCE.md)

### Policy, perspective, and cross-boundary context

- [CP-17 — MNPI Wall Enforcement](examples/CP17_MNPI_WALL_ENFORCEMENT.md)
- [CP-18 — IB Opportunity Synthesis](examples/CP18_IB_OPPORTUNITY_SYNTHESIS.md)
- [CP-19 — AML Typology Match](examples/CP19_AML_TYPOLOGY_MATCH.md)
- [CP-20 — Syndicated Lending Co-Lender](examples/CP20_SYNDICATED_LENDING_CO_LENDER.md)

### Enterprise and population context

- [CP-21 — Large Exposure / Concentration](examples/CP21_LARGE_EXPOSURE.md)
- [CP-22 — Agent-Internal Assembly](examples/CP22_AGENT_INTERNAL_ASSEMBLY.md)
- [CP-23 — Portfolio Early-Warning](examples/CP23_PORTFOLIO_EARLY_WARNING.md)
- [CP-24 — Portfolio What-If / Stress](examples/CP24_PORTFOLIO_WHAT_IF.md)

## Final capability rungs — Decision Replay

After CP-24, complete the two Decision Replay examples. These are **not CP-25/CP-26**; the Context Product ladder remains closed at 24.

- [DR-01 — Replay a Governed Determination](../03-decision-replay/DR01_REPLAY_A_GOVERNED_DETERMINATION.md) — reconstruct a served product or governed refusal from its retained record.
- [DR-02 — Package a Context Product](../03-decision-replay/DR02_PACKAGE_A_CONTEXT_PRODUCT.md) — Assembly Mode 2: package an already-governed product with an LLM while pinning and gating the packaging.

[Decision Replay capability path →](../03-decision-replay/README.md)

## Optional pre-ladder examples

The SDK also contains smaller starter products. They are useful, but they are not the main CP-00→CP-24 learning ladder:

- [S1-00 — Companies Over Revenue](S1_00_COMPANIES_OVER_REVENUE.md)
- [S1-01 — Hello Context Product](S1_01_HELLO_CONTEXT_PRODUCT.md)

## After the examples

Once you can trace several completed specs into code, you are ready to [create your own Context Product](../04-create-your-own/README.md).
