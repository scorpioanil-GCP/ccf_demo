# CP-18 — IB Opportunity Synthesis

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-18-ib-opportunity-synthesis/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP18_IB_OPPORTUNITY_SYNTHESIS_ANALYSIS.md) · [HTML reading edition](CP18_IB_OPPORTUNITY_SYNTHESIS_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-18-ib-opportunity-synthesis/README.md`  
**Qualified specification:** `examples/cp-18-ib-opportunity-synthesis/spec/CP-SPEC-018_IB_Opportunity_Synthesis.md`  
**Qualified source:** `examples/cp-18-ib-opportunity-synthesis`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-18-ib-opportunity-synthesis/spec/CP-SPEC-018_IB_Opportunity_Synthesis.md`

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

Makes Perspective Π a first-class dimension of the product. Three principals can rank the same candidate signals differently because a pinned policy/versioned weight vector changes their interpretation, not because the source data changed.

## The question

> Given the same candidate opportunity signals, how should this principal's governed perspective rank and explain them?

## What to understand before you run it

- Perspective can change product content/ranking even when the underlying evidence set is identical.
- Weight vectors are pinned/versioned governance state and are not caller-selectable.
- Restricted prospects may remain candidates while the evidence admitted for them is constrained.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
export CCF_CP_18_SQLITE_PATH='<path-to-read-only-departmental.sqlite>'
export CCF_CP_18_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_18_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_18_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_18_FLUREE_LEDGER='fibo-v2'
export CCF_CP_18_MONGO_URI='mongodb://<read-only-user>:<password>@<host>:<port>/?authSource=<auth-database>'
export CCF_CP_18_MONGO_DB='fibo_v2'
export CCF_CP_18_TOKEN_MA='<credential>'
export CCF_CP_18_TOKEN_DCM='<credential>'
export CCF_CP_18_TOKEN_SECTOR='<credential>'
export CCF_CP_18_TOKEN_UNGRANTED='<credential>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-18-ib-opportunity-synthesis/spec/` | Perspective/ranking contract. |
| `examples/cp-18-ib-opportunity-synthesis/ccf_config.yaml` | Request/perspective/operator declarations. |
| `examples/cp-18-ib-opportunity-synthesis/ccf_environment.yaml` | Source and credential names. |
| `examples/cp-18-ib-opportunity-synthesis/artifacts/` | Perspective weights, source vocabulary, question and gates. |
| `examples/cp-18-ib-opportunity-synthesis/acquisition.py` | Candidate/evidence acquisition. |
| `examples/cp-18-ib-opportunity-synthesis/projection.py` | Perspective-conditioned ranking and explanation. |
| `examples/cp-18-ib-opportunity-synthesis/deployment.py` | Policy/debt handling. |
| `examples/cp-18-ib-opportunity-synthesis/run.py` | Three principal views and request variations. |

## Run it

```bash
make venv
make -s example-cp-18
make -s example-cp-18 BANKER=--banker=BKR006
make -s example-cp-18 BANKER=--banker=BKR027
make -s example-cp-18 LIMIT=--limit=5
make -s example-cp-18 SIGNAL_TYPES=--signal-types=ma_event_8k
make -s example-cp-18 SIGNAL_TYPES=--signal-types=not_a_signal_type
make -s example-cp-18 BANKER=--banker=BKR999
.venv/bin/python examples/cp-18-ib-opportunity-synthesis/run.py --door
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- M&A, DCM and sector perspectives produce different rankings/content addresses over the same evidence classes.
- Weight vector is resolved from governance state and appears in the hash-bound determination; caller cannot choose a more favorable vector.
- Restricting signal types or result limit changes the governed question.
- Invalid signal class or ungranted banker is refused rather than silently ignored.

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
| DCM banker | `make -s example-cp-18 BANKER=--banker=BKR006` | Same evidence, different ranking. |
| Sector strategist | `make -s example-cp-18 BANKER=--banker=BKR027` | Third perspective. |
| Narrow signal types | `make -s example-cp-18 SIGNAL_TYPES=--signal-types=ma_event_8k` | Smaller evidence basis/ranking. |
| Invalid signal type | `make -s example-cp-18 SIGNAL_TYPES=--signal-types=not_a_signal_type` | Request-domain refusal. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_18_ranking.py tests/examples/test_cp_18_sabotage.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- Π can materially change a Context Product.
- Perspective parameters/weights can be pinned governance rather than caller-controlled.
- Ranked output can carry the signals/weights explaining why each row is where it is.

## What it does not prove

- Production opportunity-ranking weights.
- That ranking is investment advice or a forecasting model.

## Spec → code lesson for Cowork

Use CP-18 when perspective changes interpretation. Cowork should generate the same substrate with separate pinned perspective logic; never let a caller self-select an advantageous weight vector.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.

