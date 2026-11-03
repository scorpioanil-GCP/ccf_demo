# CP-13 — Covenant Cross-Reference — Canonical

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-13-canonical-covenant-cross-reference/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP13_CANONICAL_COVENANT_CROSS_REFERENCE_ANALYSIS.md) · [HTML reading edition](CP13_CANONICAL_COVENANT_CROSS_REFERENCE_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-13-canonical-covenant-cross-reference/README.md`  
**Qualified specification:** `examples/cp-13-canonical-covenant-cross-reference/spec/CP-SPEC-013C_Covenant_Cross_Reference_Canonical.md`  
**Qualified source:** `examples/cp-13-canonical-covenant-cross-reference`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-13-canonical-covenant-cross-reference/spec/CP-SPEC-013C_Covenant_Cross_Reference_Canonical.md`

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

Canonical paved-road document/evidence product. It moves retrieved document evidence, chains, policy envelope and governing register into governed fabric state so projection and Debt read the same admitted evidence.

## The question

> Which covenant evidence and passages are relevant to this request, under this role/corpus scope, with enough lineage to support the conclusion?

## What to understand before you run it

- Document evidence should become governed state rather than a side object closed over by projection.
- The entitlement principal comes from the governed perspective/role.
- Requested corpus scope can be refused rather than silently narrowed.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

Use the qualified/restored demonstration estate and read-only source credentials. This adoption guide uses placeholders even when the source README names a local development host.

```bash
export CCF_CP_13C_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_13C_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_13C_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_13C_FLUREE_LEDGER='fibo-v2'
export CCF_CP_13C_MONGO_URI='mongodb://<read-only-user>:<password>@<host>:<port>/?authSource=<auth-database>'
export CCF_CP_13C_MONGO_DB='fibo_v2'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-13-canonical-covenant-cross-reference/spec/` | Passage-level lineage and corpus/role contract. |
| `examples/cp-13-canonical-covenant-cross-reference/ccf_config.yaml` | Product/request/policy declarations. |
| `examples/cp-13-canonical-covenant-cross-reference/ccf_environment.yaml` | Postgres/Fluree/Mongo environment names. |
| `examples/cp-13-canonical-covenant-cross-reference/acquisition.py` | Document/source acquisition. |
| `examples/cp-13-canonical-covenant-cross-reference/deployment.py` | Claims/evidence/debt mapping. |
| `examples/cp-13-canonical-covenant-cross-reference/projection.py` | Cross-reference payload from governed view. |
| `examples/cp-13-canonical-covenant-cross-reference/produce.py` | Paved road. |
| `examples/cp-13-canonical-covenant-cross-reference/run.py` | Role/corpus/tolerance variations. |

## Run it

```bash
make venv
make -s example-cp-13-canonical
make -s example-cp-13-canonical ROLE=--role=control-room CORPUS_SCOPE=--corpus-scope=filed-and-internal
make -s example-cp-13-canonical ROLE=--role=relationship-manager CORPUS_SCOPE=--corpus-scope=filed-and-internal
make -s example-cp-13-canonical DEBT_TOLERANCE=--debt-tolerance=0.10
.venv/bin/python examples/cp-13-canonical-covenant-cross-reference/run.py --door
```

An intentional governed refusal may produce a non-zero example process exit. Read the reported refusal before treating non-zero as a broken deployment.

## What you should observe

- Default product serves evidence anchored to document passages.
- Control-room role can request broader corpus when entitled.
- Relationship-manager request for that corpus is refused rather than silently narrowed.
- Tight debt tolerance withholds the product.
- Canonical path exposes the same class through its own governed door.

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
| Control-room wider corpus | `make -s example-cp-13-canonical ROLE=--role=control-room CORPUS_SCOPE=--corpus-scope=filed-and-internal` | Broader entitled evidence. |
| Unauthorized wider corpus | `make -s example-cp-13-canonical ROLE=--role=relationship-manager CORPUS_SCOPE=--corpus-scope=filed-and-internal` | Governed refusal; never silent narrowing. |
| Tight debt | `make -s example-cp-13-canonical DEBT_TOLERANCE=--debt-tolerance=0.10` | Withholding/refusal. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_13_canonical_output.py -q
```

Do not stop at the happy path. The qualified SDK example's gate/sabotage tests are the evidence that the behavior is load-bearing.

## What this example proves

- Passage/document lineage can be part of governed context.
- Evidence and Debt can be based on the same admitted graph state.
- Role/corpus request policy can refuse unsafe widening.

## What it does not prove

- Production document corpus completeness.
- That the frozen historical CP-13 implementation is a copy target.

## Spec → code lesson for Cowork

Use CP-13C when the approved spec relies on document/passages. Cowork should move evidence needed by projection/debt into governed state and preserve passage anchors; do not pass raw retrieval objects around the graph.

Product-specific values, thresholds, source names and policy must come from the **new approved spec/evidence**, never from this demonstration by convenience.

