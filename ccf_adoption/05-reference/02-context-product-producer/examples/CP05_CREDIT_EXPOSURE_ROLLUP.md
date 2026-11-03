# CP-05 — Credit Exposure Rollup

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-05-credit-exposure-rollup/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP05_CREDIT_EXPOSURE_ROLLUP_ANALYSIS.md) · [HTML reading edition](CP05_CREDIT_EXPOSURE_ROLLUP_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-05-credit-exposure-rollup/README.md`  
**Qualified specification:** `examples/cp-05-credit-exposure-rollup/spec/CP-SPEC-005_Credit_Exposure_Rollup.md`  
**Qualified source:** `examples/cp-05-credit-exposure-rollup`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-05-credit-exposure-rollup/spec/CP-SPEC-005_Credit_Exposure_Rollup.md`

Read it in this order before opening the Python:

| Spec section | What to learn | Where it lands |
|---|---|---|
| §A | decision, consumer, counterfactual, scope | README + acceptance tests |
| §B | product contract, request, TTL, policy/perspective | `ccf_config.yaml` + payload |
| §C | sources, identity, ontology, data traps | acquisition + environment/source declarations |
| §D | operators, projection, gates | `acquisition.py`, `deployment.py`, `projection.py`, `produce.py` |
| §E | half-life, Context Debt, materialization | config + assessment code |
| §F | source readiness and limitations | environment/source artifacts + findings |
| §G | acceptance and operational evidence | tests, gates, run evidence |

As you read the code, ask: **which approved spec term is this implementing?**

## Why this example exists

Shows why a business metric such as total exposure is a context question, not a flat sum. It combines traversal, aggregation, guarantee/cross-default semantics, reconciliation, materiality and Debt-driven withholding.

## The question

> What is the bank's actual exposure to this corporate family after traversing the relationships that change the economic obligation and reconciling duplicate risk paths?

## What to understand before you run it

- A borrower-keyed sum can be confidently wrong because economic exposure follows relationships.
- Materialization can be the wrong posture when the fastest participating signal decays too quickly.
- A Context Product may refuse/withhold even after the arithmetic is successfully computed if Debt exceeds tolerance.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_05_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_05_FLUREE_LEDGER='fibo-v2'
export CCF_CP_05_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_05_POSTGRES_SCHEMA='ccf_v2'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-05-credit-exposure-rollup/spec/` | Exposure decision, reconciliation and materiality contract. |
| `examples/cp-05-credit-exposure-rollup/artifacts/` | Question/recipe/gates/expected evidence. |
| `examples/cp-05-credit-exposure-rollup/deployment.py / acquisition.py` | Source and exposure arithmetic. |
| `examples/cp-05-credit-exposure-rollup/projection.py` | Exposure payload. |
| `examples/cp-05-credit-exposure-rollup/produce.py` | Governed assembly. |
| `examples/cp-05-credit-exposure-rollup/run.py` | Scenarios and variations. |
| `examples/cp-05-credit-exposure-rollup/server/ / door example` | MCP exposure path. |

## Run it

```bash
make venv
make example-cp-05
make example-cp-05 SCENARIOS=1
make example-cp-05 INTENT=internal-appetite
make example-cp-05 DEBT_TOLERANCE=1.0
make example-cp-05 DEPTH=2
make example-cp-05 MATERIALITY=0.10
make example-cp-05 MATERIALITY=0.01
make example-cp-05 LEI=<lei>
make example-cp-05-server
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- The default demonstration is a governed refusal/withholding, not a crash.
- At a wider tolerance the same assembled product can serve, making fulfillment policy visible.
- Changing materiality changes which entities participate in aggregation.
- The product distinguishes naive borrower-keyed exposure from relationship-aware adjusted exposure.
- Every served/refused determination carries governed evidence.

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
| Wide debt tolerance | `make example-cp-05 DEBT_TOLERANCE=1.0` | Allows product that default fulfillment may withhold. |
| Materiality 10% | `make example-cp-05 MATERIALITY=0.10` | Coarser participating set. |
| Materiality 1% | `make example-cp-05 MATERIALITY=0.01` | Finer participating set. |
| Internal-appetite intent | `make example-cp-05 INTENT=internal-appetite` | Changes governed question/policy semantics. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_05_output.py tests/examples/test_cp_05_mcp_door.py -q
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- Relationship-aware aggregation can differ dramatically from flat sums.
- Product-specific reconciliation guard can catch plausible wrong answers.
- Debt-driven withholding is distinct from computational failure.
- MCP door can expose the same governed product.

## What it does not prove

- That example exposure amounts or materiality thresholds are production values.
- That all exposure calculations use the same guarantee/netting rules.

## Spec → code lesson for Cowork

Use CP-05 to learn how a spec turns business aggregation semantics into explicit traversals, reconciliation gates and fulfillment policy. Do not copy its calibration.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.

