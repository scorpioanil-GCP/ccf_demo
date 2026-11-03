# CP-21 — Large Exposure / Concentration

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-21-large-exposure/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP21_LARGE_EXPOSURE_ANALYSIS.md) · [HTML reading edition](CP21_LARGE_EXPOSURE_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-21-large-exposure/README.md`  
**Qualified specification:** `examples/cp-21-large-exposure/spec/CP-SPEC-021_Large_Exposure_Concentration.md`  
**Qualified source:** `examples/cp-21-large-exposure`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-21-large-exposure/spec/CP-SPEC-021_Large_Exposure_Concentration.md`

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

Combines derived connected-group membership, effective-dated regulatory limits, source-unit normalization, conflicting internal authorities and freshness asymmetry. It is a dense example of why governed context is more than a calculation.

## The question

> Does this derived connected counterparty group fit inside every binding exposure limit at the determination instant, under the applicable regime and internal authorities?

## What to understand before you run it

- The connected group is derived from relationships and changes with the caller's approved connection basis.
- Source units must be normalized at the acquisition boundary using a declared factor.
- A limit can be percentage-of-capital or absolute.
- Conflicting internal authorities can both be preserved while a declared rule selects which binds.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
export CCF_CP_21_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_21_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_21_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_21_FLUREE_LEDGER='fibo-v2'
export CCF_CP_21_MONGO_URI='mongodb://<read-only-user>:<password>@<host>:<port>/?authSource=<auth-database>'
export CCF_CP_21_MONGO_DB='fibo_v2'
export CCF_CP_21_TOKEN_COMMITTEE='<committee-token>'
export CCF_CP_21_TOKEN_CREDITOFFICER='<creditofficer-token>'
export CCF_CP_21_TOKEN_EXAMINER='<examiner-token>'
export CCF_CP_21_TOKEN_UNGRANTED='<ungranted-token>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-21-large-exposure/spec/` | Connected-group/regime/limit contract. |
| `examples/cp-21-large-exposure/artifacts/source-vocabulary.yaml` | Stores, URI prefixes, unit factor and admissible connection bases. |
| `examples/cp-21-large-exposure/artifacts/question.yaml` | Pinned demonstrations and expected outcomes. |
| `examples/cp-21-large-exposure/artifacts/perspectives.yaml` | Role-conditioned renderings. |
| `examples/cp-21-large-exposure/artifacts/gates.yaml` | 21 gates and sabotage evidence. |
| `examples/cp-21-large-exposure/ccf_config.yaml` | Operators/request/half-life/TTL/debt. |
| `examples/cp-21-large-exposure/ccf_environment.yaml` | Runtime variable names. |
| `examples/cp-21-large-exposure/acquisition.py` | Group derivation, unit normalization and source reads. |
| `examples/cp-21-large-exposure/projection.py` | Limits, conflicts, mitigation and headroom payload. |
| `examples/cp-21-large-exposure/run.py` | Breaching/fits/basis cases. |

## Run it

```bash
make venv
make -s example-cp-21 CASE="--case breaching"
make -s example-cp-21 CASE="--case fits"
make -s example-cp-21 CASE="--case fits" NO_MITIGATION=--no-mitigation
make -s example-cp-21 CASE="--case basis" CONNECTION_BASIS="--connection-basis control"
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- Changing connection basis changes group membership, facilities, aggregate exposure and headroom.
- Capital source is normalized from source units using a factor declared in source-vocabulary artifact, while raw and normalized values remain visible.
- Applicable regime/limit is selected effective-dated; absolute and percentage rules are both supported.
- Internal authorities can disagree; both are served and a declared selection rule identifies the binding one.
- Turning mitigation off can cross a limit by a small margin, demonstrating that mitigation is load-bearing.
- Old capital and fresh exposure remain an explicit unresolved freshness asymmetry.

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
| Breaching case | `make -s example-cp-21 CASE="--case breaching"` | Regulatory outcome breaches. |
| Fits case | `make -s example-cp-21 CASE="--case fits"` | Within binding limit. |
| Remove mitigation | `make -s example-cp-21 CASE="--case fits" NO_MITIGATION=--no-mitigation` | Same base case crosses the limit. |
| Control-only group | `make -s example-cp-21 CASE="--case basis" CONNECTION_BASIS="--connection-basis control"` | Smaller derived group/headroom changes. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_21_large_exposure.py tests/examples/test_cp_21_sabotage.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- Derived entity groups can be part of the product semantics.
- Source-unit normalization can be governed and testable by consequence.
- Effective-dated regulatory/internal limits can coexist.
- Freshness asymmetry can be disclosed without fabricating a fused timestamp.

## What it does not prove

- Production regulatory interpretation.
- That illustrative capital/limit values or thresholds should be reused.
- That the example's source ledger-point limitation represents all Fluree deployments.

## Spec → code lesson for Cowork

Use CP-21 when the spec derives membership or applies effective-dated rules to normalized source measures. Cowork must keep conversion factors and admissible bases in declared artifacts rather than burying them in code.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.

