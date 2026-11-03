# CP-07 — Client 360 / Coverage Graph

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-07-client-360-coverage-graph/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP07_CLIENT_360_COVERAGE_GRAPH_ANALYSIS.md) · [HTML reading edition](CP07_CLIENT_360_COVERAGE_GRAPH_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-07-client-360-coverage-graph/README.md`  
**Qualified specification:** `examples/cp-07-client-360-coverage-graph/spec/CP-SPEC-007_Client_360_Coverage_Graph.md`  
**Qualified source:** `examples/cp-07-client-360-coverage-graph`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-07-client-360-coverage-graph/spec/CP-SPEC-007_Client_360_Coverage_Graph.md`

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

Introduces high fan-out and the critical distinction between a complete-looking graph and a complete graph. A bounded acquisition can fabricate a relationship gap; therefore truncation must become governed evidence/gating rather than a README warning.

## The question

> Who actually has meaningful recent relationships with this client's people, where are the coverage gaps, and did the acquisition bound hide interactions that would change that answer?

## What to understand before you run it

- Coverage is a path over interactions/people, not a single CRM coverage field.
- A query limit can change the apparent world and manufacture false gaps.
- Truncation disclosure is part of product correctness.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_07_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_07_FLUREE_LEDGER='fibo-v2'
export CCF_CP_07_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_07_POSTGRES_SCHEMA='ccf_v2'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-07-client-360-coverage-graph/spec/` | Coverage decision and bounded-acquisition correctness contract. |
| `examples/cp-07-client-360-coverage-graph/artifacts/` | Question, gates and data/evidence declarations. |
| `examples/cp-07-client-360-coverage-graph/acquisition.py / deployment.py` | Interaction graph acquisition and bounds. |
| `examples/cp-07-client-360-coverage-graph/projection.py` | Relationship-strength/gap payload. |
| `examples/cp-07-client-360-coverage-graph/produce.py` | Governed product. |
| `examples/cp-07-client-360-coverage-graph/run.py` | Anchor, limit and need-to-know variations. |
| `tests/examples/test_cp_07_output.py` | Proof that truncation/gaps behave as documented. |

## Run it

```bash
make venv
make example-cp-07
make example-cp-07 LEI=--lei=529900L7KB2N9KXCDI76
make example-cp-07 LEI=--lei=549300FA4CTCW903Y781
make example-cp-07 LIMIT=--limit=20
make example-cp-07 NTK=--need-to-know
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- Default/control anchors show measured banker relationship strength and coverage gaps.
- Lowering the acquisition limit can create gaps that disappear at the full bound.
- A stale client changes Context Debt/routing.
- Need-to-know produces a different governed graph, not a presentation redaction.

Do not compare volatile content addresses or timestamps with prose unless the qualified SDK example itself publishes a pinned transcript. For exact byte-level claims, use the example's committed tests/transcript.

## How the example works

The general path is:

```
source estate (read only)
        ↓
acquisition / source interpretation
        ↓
SignalEnvelope(s)
        ↓
L2 assembly into governed L3 state
        ↓
L4 operators
        ↓
L5 projection Π over GraphView
        ↓
L6 Context Product gates / fulfillment
        ↓
served product OR governed refusal
```

The product-specific files above show where this rung changes that pattern.

## Variations to try

| Purpose | Command | Expected semantic change |
|---|---|---|
| Control client | `make example-cp-07 LEI=--lei=529900L7KB2N9KXCDI76` | Untruncated comparison. |
| Stale client | `make example-cp-07 LEI=--lei=549300FA4CTCW903Y781` | Debt crosses a routing threshold. |
| Limit 20 | `make example-cp-07 LIMIT=--limit=20` | Apparent coverage gaps increase; truncation disclosure is load-bearing. |
| Need-to-know | `make example-cp-07 NTK=--need-to-know` | Different policy-shaped graph. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_07_output.py tests/examples/test_cp_07_mcp_door.py -q
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- High fan-out is a semantic/correctness concern, not merely performance.
- Bounded acquisition must disclose/refuse unsafe truncation.
- Relationship-strength and gap inference can be governed over interaction evidence.

## What it does not prove

- Enterprise-wide banker interaction completeness.
- That the example's relationship-strength formula or limit is production calibration.

## Spec → code lesson for Cowork

Use CP-07 when a new spec has fan-out or bounded retrieval. Cowork must generate a correctness story for truncation—not merely add LIMIT for performance.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.

