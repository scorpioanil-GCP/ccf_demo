# CP-22 — Agent-Internal Assembly

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-22-agent-internal-assembly/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP22_AGENT_INTERNAL_ASSEMBLY_ANALYSIS.md) · [HTML reading edition](CP22_AGENT_INTERNAL_ASSEMBLY_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-22-agent-internal-assembly/README.md`  
**Qualified specification:** `examples/cp-22-agent-internal-assembly/spec/CP-SPEC-022_Agent_Internal_Assembly.md`  
**Qualified source:** `examples/cp-22-agent-internal-assembly`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-22-agent-internal-assembly/spec/CP-SPEC-022_Agent_Internal_Assembly.md`

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

Demonstrates CCF terminating inside an agent process. Agent A speaks ordinary A2A to Agent B and never sees a Context Product; Agent B internally consumes CP-21, branches on governed fulfillment, extracts a deliberately lossy business answer and returns only that.

## The question

> Can an ordinary peer agent ask a banking question and receive a concise answer while the governed Context Product, Debt, lineage and replay evidence remain entirely inside the answering agent?

## What to understand before you run it

- A2A here is an external agent protocol, not a CCF product-delivery/Peering surface.
- Debt governs whether Agent B may use the product but does not travel to Agent A.
- The lossy extraction is intentional and measurable.
- Caller-supplied noise cannot widen Agent B's governed envelope.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
# CP-22 declares no new source binding; it consumes CP-21.
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
| `examples/cp-22-agent-internal-assembly/spec/` | Agent boundary and wire contract. |
| `examples/cp-22-agent-internal-assembly/artifacts/agent-b.yaml` | Everything that governs Agent B: consumed product, identity, envelope, tolerances and A2A card. |
| `examples/cp-22-agent-internal-assembly/artifacts/wire-contract.yaml` | Allowed inbound/outbound fields and forbidden CCF tokens. |
| `examples/cp-22-agent-internal-assembly/artifacts/question.yaml` | Agent A's vocabulary: subject + instant. |
| `examples/cp-22-agent-internal-assembly/agent_a.py` | Control: ordinary agent with no CCF import/vocabulary. |
| `examples/cp-22-agent-internal-assembly/agent_b.py` | Internal CCF ask and lossy extraction. |
| `examples/cp-22-agent-internal-assembly/run.py` | Separate-process A2A demonstration. |
| `examples/cp-22-agent-internal-assembly/artifacts/gates.yaml` | 12 gates / sabotage evidence. |

## Run it

```bash
make venv
make -s example-cp-22
make -s example-cp-22 NOISE=--noise
make -s example-cp-22 STRICT=--strict
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- Agent A sends only subject + instant and receives four business-answer fields.
- CCF contract, content address, Debt, lineage and replay reference do not cross the A2A wire.
- Default declared tolerance allows Agent B to answer; strict tolerance causes Agent B's internal Context Product to refuse and Agent A sees a protocol-level non-success, not a forwarded refusal envelope.
- Noise/probe fields cannot alter the governed envelope.

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
| Caller noise | `make -s example-cp-22 NOISE=--noise` | Noise cannot widen/change governed answer. |
| Strict internal tolerance | `make -s example-cp-22 STRICT=--strict` | Internal CCF refusal becomes an external protocol non-success. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_22_agent_internal.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- An external agent can remain completely CCF-unaware while a peer uses CCF internally.
- Governed context can constrain an answer without being exported.
- Lossy extraction can be intentional and measurable.
- A2A agent messaging is distinct from fabric Peering.

## What it does not prove

- That every agent-to-agent exchange should hide the product.
- That A2A is a Context Product transport.
- Replay environment mechanics.

## Spec → code lesson for Cowork

Use CP-22 when the product is an internal trust mechanism inside an agent/service. Cowork should keep the external wire contract minimal and explicitly prohibit leaking CCF governance internals unless the approved interface is a true Context Product delivery surface.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.

