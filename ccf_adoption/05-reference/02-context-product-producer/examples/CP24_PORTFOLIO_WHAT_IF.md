# CP-24 — Portfolio What-If / Stress

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-24-portfolio-what-if/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP24_PORTFOLIO_WHAT_IF_ANALYSIS.md) · [HTML reading edition](CP24_PORTFOLIO_WHAT_IF_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-24-portfolio-what-if/README.md`  
**Qualified specification:** `examples/cp-24-portfolio-what-if/spec/CP-SPEC-024_Portfolio_What_If_Stress.md`  
**Qualified source:** `examples/cp-24-portfolio-what-if`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-24-portfolio-what-if/spec/CP-SPEC-024_Portfolio_What_If_Stress.md`

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

First explicitly conditional Context Product. It governs factual context and binds caller-supplied hypothetical assumptions while keeping assumptions separate from evidence, lineage freshness and Context Debt.

## The question

> Given the current governed portfolio evidence, what deterministic outputs follow under this explicit scenario, without pretending the scenario itself was observed?

## What to understand before you run it

- Scenario assumptions are request state, not evidence.
- Changing only the scenario must not refresh or improve Context Debt.
- Hypothetical outputs must name the assumption that produced them.
- Scenario magnitudes use canonical integer units for bit-stable requests.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
export CCF_CP_24_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_24_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_24_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_24_FLUREE_LEDGER='fibo-v2'
export CCF_CP_24_TOKEN_COVERAGE='<credential>'
export CCF_CP_24_TOKEN_CREDIT='<credential>'
export CCF_CP_24_TOKEN_PRODUCT='<credential>'
export CCF_CP_24_TOKEN_UNGRANTED='<credential>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-24-portfolio-what-if/spec/` | Conditional/hypothetical product contract. |
| `examples/cp-24-portfolio-what-if/ccf_config.yaml` | Closed scenario request schema and product/operator declarations. |
| `examples/cp-24-portfolio-what-if/ccf_environment.yaml` | Source/credential names. |
| `examples/cp-24-portfolio-what-if/artifacts/source-vocabulary.yaml` | Observed source mappings. |
| `examples/cp-24-portfolio-what-if/artifacts/sensitivities.yaml` | Illustrative sensitivities as declared values. |
| `examples/cp-24-portfolio-what-if/artifacts/question.yaml` | Demonstration population/instant/scenario. |
| `examples/cp-24-portfolio-what-if/acquisition.py` | Observed factual input acquisition. |
| `examples/cp-24-portfolio-what-if/projection.py` | Deterministic scenario arithmetic. |
| `examples/cp-24-portfolio-what-if/artifacts/gates.yaml` | 17 gates including assumption/evidence separation. |

## Run it

```bash
make venv
make -s example-cp-24
make -s example-cp-24 PRINCIPAL="--principal PRIN-CO-002" INTENT="--intent credit-review"
make -s example-cp-24 SCENARIO='--scenario {"rate_shift_bp":300,"collateral_shift_bp":-2000,"collateral_class":"real_property"}'
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- Scenario is recorded as a closed request object; undeclared members/types refuse.
- Derived interest/headroom/collateral outputs identify the assumptions used.
- Stale observed inputs remain stale after stress arithmetic; scenario does not reset observed_at, freshness, TTL or Debt.
- Changing scenario while holding evidence constant leaves Context Debt unchanged.
- The product remains deterministic what-if arithmetic, not a forecast/probability model.

For exact byte-for-byte output, content addresses or measured figures, use the qualified SDK tree's committed tests/transcripts. This guide describes the invariant behavior a reproducer should see.

## How the example works

```
qualified source estate
  ↓
acquisition
  ↓
SignalEnvelope / governed source evidence
  ↓
L2/L3 context state
  ↓
L4 operators + policy/temporal bounds
  ↓
L5 projection
  ↓
L6 gates / Debt fulfillment / composition where applicable
  ↓
served product OR governed refusal
```

## Variations to try

| Purpose | Command | Expected semantic change |
|---|---|---|
| Credit role | `make -s example-cp-24 PRINCIPAL="--principal PRIN-CO-002" INTENT="--intent credit-review"` | Different role-conditioned product. |
| More severe scenario | `make -s example-cp-24 SCENARIO='--scenario {"rate_shift_bp":300,"collateral_shift_bp":-2000,"collateral_class":"real_property"}'` | Scenario-derived outputs change; factual Debt should not. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_24_whatif.py tests/examples/test_cp_24_sabotage.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- Facts and hypotheticals can coexist without conflating their provenance.
- Scenario assumptions can be governed, hashed and replayable as request state.
- Changing assumptions need not change Context Debt when factual evidence is unchanged.

## What it does not prove

- Forecast accuracy or probabilities.
- Recommended stress/sensitivity calibration.
- That CP-24 is a composite over CP-23—it deliberately reads authoritative sources as a sibling product.

## Spec → code lesson for Cowork

Use CP-24 when the spec is explicitly conditional. Cowork must keep observed evidence and assumptions in different structures and tests should assert scenario-only changes do not alter factual Debt.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.

