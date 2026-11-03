# CP-10 — Rating & Spread Migration

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-10-rating-and-spread-migration/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP10_RATING_AND_SPREAD_MIGRATION_ANALYSIS.md) · [HTML reading edition](CP10_RATING_AND_SPREAD_MIGRATION_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-10-rating-and-spread-migration/README.md`  
**Qualified specification:** `examples/cp-10-rating-and-spread-migration/spec/CP-SPEC-010_Rating_And_Spread_Migration.md`  
**Qualified source:** `examples/cp-10-rating-and-spread-migration`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-10-rating-and-spread-migration/spec/CP-SPEC-010_Rating_And_Spread_Migration.md`

Read it before the Python:

| Spec section | What to learn | Where it lands |
|---|---|---|
| §A | decision, consumer, counterfactual, scope | README + acceptance tests |
| §B | contract, request, TTL, policy/perspective | `ccf_config.yaml` + payload |
| §C | sources, identity, ontology, data traps | acquisition + environment/source declarations |
| §D | operators, projection, gates | `acquisition.py`, `deployment.py`, `projection.py`, `produce.py` |
| §E | half-life, Context Debt, materialization | config + assessment code |
| §F | source readiness and limitations | environment/source artifacts + findings |
| §G | acceptance and operational evidence | tests, gates, run evidence |

As you read the code, ask: **which approved spec term is this implementing?**

## Why this example exists

Demonstrates disagreement as useful context: market spread components, instrument-level behavior and internal grades can move differently. It also shows why freshness should read the leading edge of a retained time series rather than average the age of history.

## The question

> Is the observed spread movement issuer-specific deterioration, market-wide movement, or a disagreement that should remain visible beside the internal rating?

## What to understand before you run it

- Serve benchmark, band spread and issuer-specific residual separately; do not flatten them into a headline total.
- The instrument—not the obligor average—is the observation unit for traded spread behavior.
- Different signal classes can have radically different half-lives inside one product.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

Use the qualified/restored demonstration estate and read-only source credentials. This adoption guide uses placeholders even when the source README names a local development host.

```bash
export CCF_CP_10_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_10_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_10_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_10_FLUREE_LEDGER='fibo-v2'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-10-rating-and-spread-migration/spec/` | Migration question, bond-level correction and Gate-1/Gate-2 deviations. |
| `examples/cp-10-rating-and-spread-migration/artifacts/` | Scenarios, source vocabulary and gates. |
| `examples/cp-10-rating-and-spread-migration/acquisition.py` | Bond/rating/market reads and leading-edge selection. |
| `examples/cp-10-rating-and-spread-migration/deployment.py` | Per-class freshness and Debt. |
| `examples/cp-10-rating-and-spread-migration/projection.py` | Three-component spread decomposition. |
| `examples/cp-10-rating-and-spread-migration/run.py` | Three measured scenarios. |

## Run it

```bash
make venv
make -s example-cp-10
make -s example-cp-10 LEI=529900VKCYZW8GZ4WW58
make -s example-cp-10 LEI=549300TRW1LZMDJZAQ78 AS_OF=2025-04-07T00:00:00+00:00 WINDOW_DAYS=48 GRANULARITY=daily
make -s example-cp-10 DEBT_TOLERANCE=0.10
```

An intentional governed refusal may produce a non-zero example process exit. Read the reported refusal before treating non-zero as a broken deployment.

## What you should observe

- Default case shows a market move followed later by a rating action.
- A second obligor shows large bond-specific movement with no rating change.
- A market-wide widening can produce a large headline move but tiny issuer-specific residual and therefore not mean deterioration.
- Lower debt tolerance can govern/withhold the answer.

Exact content addresses, replay references, timestamps and measured figures should be checked against the qualified example's committed tests/transcripts rather than copied from memory.

## How the example works

```
source evidence
  ↓ acquisition
SignalEnvelope(s)
  ↓ governed assembly / L3
GraphView
  ↓ L4 operators
admitted/computed context
  ↓ Π
candidate product
  ↓ L6 gates + Debt fulfillment
served product OR governed refusal
```

This rung's distinctive behavior is described above; the listed source files show the implementation seam where it enters.

## Variations to try

| Purpose | Command | Expected semantic change |
|---|---|---|
| Standing disagreement | `make -s example-cp-10 LEI=529900VKCYZW8GZ4WW58` | Instrument move remains visible beside unchanged grade. |
| Market-wide widening | `make -s example-cp-10 LEI=549300TRW1LZMDJZAQ78 AS_OF=2025-04-07T00:00:00+00:00 WINDOW_DAYS=48 GRANULARITY=daily` | Headline and residual tell different stories. |
| Tighter tolerance | `make -s example-cp-10 DEBT_TOLERANCE=0.10` | Fulfillment/refusal changes. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_10_output.py -q
```

Do not stop at the happy path. The qualified SDK example's gate/sabotage tests are the evidence that the behavior is load-bearing.

## What this example proves

- Instrument-level aggregation can preserve signals obligor averages erase.
- Disagreement between market and rating evidence can be the answer.
- Freshness scoring should use decision-relevant leading observations.

## What it does not prove

- That synthetic/engineered ratings are licensed agency ratings.
- That the example is TRACE data.
- Production market/rating thresholds.

## Spec → code lesson for Cowork

Use CP-10 when a product must preserve competing signal explanations. Cowork should not 'reconcile' disagreement away unless the approved spec defines that reconciliation.

Product-specific values, thresholds, source names and policy must come from the **new approved spec/evidence**, never from this demonstration by convenience.

