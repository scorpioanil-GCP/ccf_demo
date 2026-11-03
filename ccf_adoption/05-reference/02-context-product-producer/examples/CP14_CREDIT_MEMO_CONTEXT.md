# CP-14 — Credit Memo Context — Composite

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-14-credit-memo-context/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP14_CREDIT_MEMO_CONTEXT_ANALYSIS.md) · [HTML reading edition](CP14_CREDIT_MEMO_CONTEXT_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-14-credit-memo-context/README.md`  
**Qualified specification:** `examples/cp-14-credit-memo-context/spec/CP-SPEC-014_Credit_Memo_Context.md`  
**Qualified source:** `examples/cp-14-credit-memo-context`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-14-credit-memo-context/spec/CP-SPEC-014_Credit_Memo_Context.md`

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

The first full composite Context Product. It consumes five child product classes through governed doors, admits/refuses child outcomes under declared requirements, and composes only admitted contracts. It proves that composition is product consumption, not a second Control Plane.

## The question

> Can a governed credit memo context be assembled from five independently governed child Context Products, and if not, which required child blocks the memo?

## What to understand before you run it

- A composite asks child products; it does not reach into their source/assembly internals.
- Required/optional child semantics and admission evidence belong to the composite contract.
- Composition must use the admitted child contracts exactly—addresses and evidence remain traceable.
- Child Debt can cause withholding before composition.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

Use the qualified/restored demonstration estate and read-only source credentials. This adoption guide uses placeholders even when the source README names a local development host.

```bash
export CCF_CP_14_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_14_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_14_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_14_FLUREE_LEDGER='fibo-v2'
# Also configure each producer's own source variables using its walkthrough below.
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-14-credit-memo-context/spec/` | Composite requirements, child mappings and admission semantics. |
| `examples/cp-14-credit-memo-context/ccf_config.yaml` | Composite class and `requires` declaration. |
| `examples/cp-14-credit-memo-context/ccf_environment.yaml` | Five producer-door URL/token names. |
| `examples/cp-14-credit-memo-context/artifacts/` | Child questions, gates, expected composition. |
| `examples/cp-14-credit-memo-context/deployment.py` | Child-question mapping and composite-specific vocabulary. |
| `examples/cp-14-credit-memo-context/projection.py` | Memo section assembly from admitted children. |
| `examples/cp-14-credit-memo-context/produce.py` | Composite paved-road binding. |
| `examples/cp-14-credit-memo-context/run.py` | Governed vs diagnostic tolerance cases. |

## Run it

Configure [spread](CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD.md), [family](CP04_CANONICAL_CORPORATE_FAMILY_TREE.md), [exposure](CP05_CREDIT_EXPOSURE_ROLLUP.md), [collateral](CP06_CANONICAL_COLLATERAL_AND_SETOFF_COVERAGE.md) and [covenant](CP13_CANONICAL_COVENANT_CROSS_REFERENCE.md) sources first. Start **each producer in a separate terminal**; each command blocks while serving. The family and covenant `--config-root` variants align their demonstration clocks with CP-14. Choose each producer's `CCF_CP_*_DOOR_TOKEN` before starting it, then use that same credential for its consumer variable.

```bash
make venv
.venv/bin/python examples/cp-03-canonical-obligor-financial-spread/run.py --door
.venv/bin/python examples/cp-04-canonical-corporate-family-tree/run.py --door \
  --config-root examples/cp-14-credit-memo-context/producer-demonstration/cp-04-canonical-corporate-family-tree
.venv/bin/python examples/door-cp-05-credit-exposure-rollup/run.py --door
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door
.venv/bin/python examples/cp-13-canonical-covenant-cross-reference/run.py --door \
  --config-root examples/cp-14-credit-memo-context/producer-demonstration/cp-13-canonical-covenant-cross-reference
```

In a sixth terminal, set the five endpoint/token pairs declared in `ccf_config.yaml`. Replace each port with that producer's `READY <port>` value:

```bash
export CCF_CP14_SPREAD_URL='http://127.0.0.1:<spread-port>/mcp'
export CCF_CP14_SPREAD_TOKEN='<spread-door-token>'
export CCF_CP14_FAMILY_URL='http://127.0.0.1:<family-port>/mcp'
export CCF_CP14_FAMILY_TOKEN='<family-door-token>'
export CCF_CP14_EXPOSURE_URL='http://127.0.0.1:<exposure-port>/mcp'
export CCF_CP14_EXPOSURE_TOKEN='<exposure-door-token>'
export CCF_CP14_COLLATERAL_URL='http://127.0.0.1:<collateral-port>/mcp'
export CCF_CP14_COLLATERAL_TOKEN='<collateral-door-token>'
export CCF_CP14_COVENANT_URL='http://127.0.0.1:<covenant-port>/mcp'
export CCF_CP14_COVENANT_TOKEN='<covenant-door-token>'
make -s example-cp-14
make -s example-cp-14 DEBT_TOLERANCE=--debt-tolerance=1.0
```

An intentional governed refusal may produce a non-zero example process exit. Read the reported refusal before treating non-zero as a broken deployment.

## What you should observe

- At the governed/default tolerance, several child producers withhold and the composite refuses because required slots are unavailable.
- At diagnostic tolerance 1.0, all five children are admitted and the composite serves.
- Each composed section records the content address of the admitted child contract it came from.
- The composite's outcome records all child rows/admission evidence even when a required child blocks the final product.

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
| Governed tolerance | `make -s example-cp-14` | Required child withholding causes honest composite refusal. |
| Diagnostic tolerance | `make -s example-cp-14 DEBT_TOLERANCE=--debt-tolerance=1.0` | All five admitted; memo serves. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_14_first_slice.py tests/examples/test_cp_14_second_slice.py tests/examples/test_cp_14_third_slice.py tests/examples/test_cp_14_fourth_slice.py -q
```

Do not stop at the happy path. The qualified SDK example's gate/sabotage tests are the evidence that the behavior is load-bearing.

## What this example proves

- Composite Context Products are governed consumers of child products.
- Child admission/refusal is explicit and traceable.
- Required child withholding can refuse the composite.
- Composition preserves child content identity/evidence.

## What it does not prove

- That a composite should always tolerate child Debt at 1.0; that is a labeled diagnostic case.
- That MCP itself is the composition abstraction—MCP is only a transport for these producer doors.
- Replay replacement-environment mechanics under active D-IMPL-346/347 work.

## Spec → code lesson for Cowork

Use CP-14 only when the approved spec truly requires product composition. Cowork should declare child requirements/questions first, then generate admission/composition logic; it must not bypass child products to read their underlying stores.

Product-specific values, thresholds, source names and policy must come from the **new approved spec/evidence**, never from this demonstration by convenience.

