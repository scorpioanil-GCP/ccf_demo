# CP-16 — ABS / Securitization Surveillance

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-16-abs-securitization-surveillance/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP16_ABS_SECURITIZATION_SURVEILLANCE_ANALYSIS.md) · [HTML reading edition](CP16_ABS_SECURITIZATION_SURVEILLANCE_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-16-abs-securitization-surveillance/README.md`  
**Qualified specification:** `examples/cp-16-abs-securitization-surveillance/spec/CP-SPEC-016_ABS_Securitization_Surveillance.md`  
**Qualified source:** `examples/cp-16-abs-securitization-surveillance`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-16-abs-securitization-surveillance/spec/CP-SPEC-016_ABS_Securitization_Surveillance.md`

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

Introduces population-scale acquisition where a request parameter (`granularity`) changes payload shape, cost, and the caller's permitted ceiling. It proves that large loan populations must be bounded during acquisition—not materialized first and trimmed later.

## The question

> What surveillance context should be assembled for this securitization at the requested granularity, and is that granularity permitted and affordable for this principal?

## What to understand before you run it

- `granularity` is simultaneously a semantic shape lever, a cost lever and a governed entitlement ceiling.
- Loan-level scale makes acquisition pushdown mandatory.
- Cost is expressed in deterministic work units/records, not wall-clock timing.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
export CCF_CP_16_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_16_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_16_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_16_FLUREE_LEDGER='fibo-v2'
export CCF_CP_16_MONGO_URI='mongodb://<read-only-user>:<password>@<host>:<port>/?authSource=<auth-database>'
export CCF_CP_16_MONGO_DB='fibo_v2'
export CCF_CP_16_TOKEN_DESK='<credential>'
export CCF_CP_16_TOKEN_RISK='<credential>'
export CCF_CP_16_TOKEN_REPORTING='<credential>'
export CCF_CP_16_TOKEN_UNGRANTED='<credential>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-16-abs-securitization-surveillance/spec/` | Granularity/cost/role-ceiling contract and source limits. |
| `examples/cp-16-abs-securitization-surveillance/ccf_config.yaml` | Request domains, product/role constraints and Debt settings. |
| `examples/cp-16-abs-securitization-surveillance/ccf_environment.yaml` | Source and credential variable names. |
| `examples/cp-16-abs-securitization-surveillance/artifacts/` | Source vocabulary, perspectives, question and gates. |
| `examples/cp-16-abs-securitization-surveillance/acquisition.py` | Population-scale bounded reads/aggregation. |
| `examples/cp-16-abs-securitization-surveillance/projection.py` | Granularity-dependent payload. |
| `examples/cp-16-abs-securitization-surveillance/deployment.py` | Assessment and request/policy bindings. |
| `examples/cp-16-abs-securitization-surveillance/produce.py` | Paved-road product. |
| `examples/cp-16-abs-securitization-surveillance/run.py` | Granularity/principal variations. |

## Run it

```bash
make venv
make -s example-cp-16
make -s example-cp-16 GRANULARITY="--granularity cohort" PRINCIPAL="--principal PRIN-CRR-002"
make -s example-cp-16 GRANULARITY="--granularity loan" LOAN_SAMPLE="--loan-sample 300"
make -s example-cp-16 AS_OF="--as-of 2025-09-30T00:00:00+00:00" ASKED_AT="--asked-at 2025-09-30T00:00:00+00:00"
.venv/bin/python examples/cp-16-abs-securitization-surveillance/run.py --door
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- Different principals/granularities receive materially different product shapes.
- A request above the principal's granularity ceiling is refused by name rather than silently reduced.
- Loan-level path samples/aggregates during acquisition, before claims are minted.
- The product reports the deterministic cost of the caller's chosen question.

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
| Cohort view | `make -s example-cp-16 GRANULARITY="--granularity cohort" PRINCIPAL="--principal PRIN-CRR-002"` | Role-conditioned coarser product. |
| Loan sample | `make -s example-cp-16 GRANULARITY="--granularity loan" LOAN_SAMPLE="--loan-sample 300"` | Loan-level shape and higher deterministic cost. |
| Historical instant | `make -s example-cp-16 AS_OF="--as-of 2025-09-30T00:00:00+00:00" ASKED_AT="--asked-at 2025-09-30T00:00:00+00:00"` | Decision-time bounded acquisition changes evidence. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_16_granularity.py tests/examples/test_cp_16_surveillance.py tests/examples/test_cp_16_sabotage.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- Request shape/cost/entitlement can be the same governed axis.
- Large populations can be bounded before materialization.
- Cost disclosure can be deterministic and product-visible.

## What it does not prove

- Production securitization surveillance thresholds or cost bands.
- That all loan-level data can be materialized safely in memory.

## Spec → code lesson for Cowork

Use CP-16 when a request parameter controls data volume/shape. Cowork must implement the bound at acquisition and enforce the caller's ceiling before expensive work, not post-filter a fully materialized population.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.

