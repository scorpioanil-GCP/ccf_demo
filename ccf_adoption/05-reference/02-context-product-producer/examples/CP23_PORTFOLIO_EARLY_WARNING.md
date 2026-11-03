# CP-23 — Portfolio Early-Warning / Concentration

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-23-portfolio-early-warning/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP23_PORTFOLIO_EARLY_WARNING_ANALYSIS.md) · [HTML reading edition](CP23_PORTFOLIO_EARLY_WARNING_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-23-portfolio-early-warning/README.md`  
**Qualified specification:** `examples/cp-23-portfolio-early-warning/spec/CP-SPEC-023_Portfolio_Early_Warning_Concentration.md`  
**Qualified source:** `examples/cp-23-portfolio-early-warning`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-23-portfolio-early-warning/spec/CP-SPEC-023_Portfolio_Early_Warning_Concentration.md`

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

First Context Product whose subject is a population rather than one entity. It demonstrates population-grain assembly, worst-factor Context Debt across members, multi-class freshness and role-conditioned completeness.

## The question

> What is the governed early-warning state of this whole coverage book, including concentration and signal severity, and how does weak context in any member affect the product?

## What to understand before you run it

- Population membership is semantically a set and is canonicalized before the determination.
- Population Debt composes per-factor weakness across members; it is not merely max(member debt).
- A role that policy-excludes members incurs completeness cost; a caller who voluntarily narrows the question does not.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
export CCF_CP_23_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_23_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_23_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_23_FLUREE_LEDGER='fibo-v2'
export CCF_CP_23_TOKEN_COVERAGE='<credential>'
export CCF_CP_23_TOKEN_CREDIT='<credential>'
export CCF_CP_23_TOKEN_PRODUCT='<credential>'
export CCF_CP_23_TOKEN_UNGRANTED='<credential>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-23-portfolio-early-warning/spec/` | Population-grain product contract. |
| `examples/cp-23-portfolio-early-warning/ccf_config.yaml` | Population request/operator/product declarations. |
| `examples/cp-23-portfolio-early-warning/ccf_environment.yaml` | Source/credential names. |
| `examples/cp-23-portfolio-early-warning/artifacts/source-vocabulary.yaml` | Estate tables/IRIs. |
| `examples/cp-23-portfolio-early-warning/artifacts/perspectives.yaml` | Coverage/credit/product views. |
| `examples/cp-23-portfolio-early-warning/artifacts/severity-tiers.yaml` | Illustrative severity thresholds as Control Plane values. |
| `examples/cp-23-portfolio-early-warning/artifacts/question.yaml` | Demonstration book and instant. |
| `examples/cp-23-portfolio-early-warning/acquisition.py` | Population member/source reads. |
| `examples/cp-23-portfolio-early-warning/projection.py` | Book-level product. |
| `examples/cp-23-portfolio-early-warning/artifacts/gates.yaml` | 19 gate claims/reds. |

## Run it

```bash
make venv
make -s example-cp-23
make -s example-cp-23 PRINCIPAL="--principal PRIN-CO-002" INTENT="--intent credit-review"
make -s example-cp-23 SEVERITY_FLOOR="--severity-floor 0.45"
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- Default coverage role receives the book-level product over the demonstration population.
- Credit/product roles see different governed member/evidence sets.
- Population Debt identifies which member contributes the weakest factor.
- Raising severity floor narrows evidence and can increase Debt enough to withhold rather than serve a misleadingly thin book.

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
| Credit role | `make -s example-cp-23 PRINCIPAL="--principal PRIN-CO-002" INTENT="--intent credit-review"` | Role-conditioned view and evidence. |
| Higher severity floor | `make -s example-cp-23 SEVERITY_FLOOR="--severity-floor 0.45"` | Thinner evidence, Debt can rise/withhold. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_23_portfolio.py tests/examples/test_cp_23_sabotage.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- Context Product subject can be a governed population.
- Population Debt can compose per-factor weakness across members.
- Policy-conditioned missing members can affect completeness honestly.
- Severity thresholds can remain configuration rather than code.

## What it does not prove

- Portfolio-management functionality beyond the four declared demonstration limbs.
- Regulatory large-exposure logic—CP-21 owns that.
- Production severity calibration.

## Spec → code lesson for Cowork

Use CP-23 when the approved subject is a set/population. Cowork should canonicalize membership according to the spec before hashing/effective request and use the SDK's ruled debt composition rather than inventing an average.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.

