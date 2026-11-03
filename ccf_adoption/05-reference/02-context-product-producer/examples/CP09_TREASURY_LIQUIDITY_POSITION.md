# CP-09 — Treasury Liquidity Position

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-09-treasury-liquidity-position/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP09_TREASURY_LIQUIDITY_POSITION_ANALYSIS.md) · [HTML reading edition](CP09_TREASURY_LIQUIDITY_POSITION_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-09-treasury-liquidity-position/README.md`  
**Qualified specification:** `examples/cp-09-treasury-liquidity-position/spec/CP-SPEC-009_Treasury_Liquidity_Position.md`  
**Qualified source:** `examples/cp-09-treasury-liquidity-position`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-09-treasury-liquidity-position/spec/CP-SPEC-009_Treasury_Liquidity_Position.md`

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

Shows that one decision instant can govern signals with different temporal semantics without flattening them into one freshness rule. It also establishes absence-vs-staleness and scope-before-freshness behavior.

## The question

> What is the client's governed liquidity position at this instant, using only signals actually in scope and distinguishing market observations, policy effectivity, filings and unobserved holdings?

## What to understand before you run it

- One as_of can select/bound different temporal classes differently.
- A source outside its declared coverage window is absent, not automatically stale.
- Scope determines participation before freshness determines fitness.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

Use the qualified/restored demonstration estate and read-only source credentials. This adoption guide uses placeholders even when the source README names a local development host.

```bash
export CCF_CP_09_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_09_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_09_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_09_FLUREE_LEDGER='fibo-v2'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-09-treasury-liquidity-position/spec/` | Temporal-class and liquidity decision design. |
| `examples/cp-09-treasury-liquidity-position/ccf_config.yaml` | Signal-class half-lives, request surface and product controls. |
| `examples/cp-09-treasury-liquidity-position/artifacts/` | Question/source vocabulary/gates. |
| `examples/cp-09-treasury-liquidity-position/acquisition.py` | Source coverage windows and scope logic. |
| `examples/cp-09-treasury-liquidity-position/deployment.py` | Debt/temporal mapping. |
| `examples/cp-09-treasury-liquidity-position/projection.py` | Liquidity payload. |
| `examples/cp-09-treasury-liquidity-position/run.py` | Posture/stale/scope variations. |

## Run it

```bash
make venv
make -s example-cp-09
make -s example-cp-09 AS_OF=2026-06-15T18:05:00+00:00
make -s example-cp-09 AS_OF=2026-08-21T16:00:00+00:00 CURRENCIES=USD
make -s example-cp-09 CURRENCIES=USD
```

An intentional governed refusal may produce a non-zero example process exit. Read the reported refusal before treating non-zero as a broken deployment.

## What you should observe

- Regulatory posture is selected by effectivity, not decayed like a market quote.
- Market observations are selected within their source coverage and decay against their own half-life.
- A USD-only question can remove FX from participation entirely.
- A stale participating signal can trigger fail-closed behavior.

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
| Posture flip | `make -s example-cp-09 AS_OF=2026-06-15T18:05:00+00:00` | Effective policy posture changes. |
| Stale USD signal | `make -s example-cp-09 AS_OF=2026-08-21T16:00:00+00:00 CURRENCIES=USD` | Governed fail-closed on participating stale evidence. |
| USD-only scope | `make -s example-cp-09 CURRENCIES=USD` | FX stops participating rather than being scored stale. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_09_output.py -q
```

Do not stop at the happy path. The qualified SDK example's gate/sabotage tests are the evidence that the behavior is load-bearing.

## What this example proves

- Mixed temporal semantics can coexist in one product.
- Absence and staleness are distinct.
- Freshness is evaluated only for evidence required by the scoped question.

## What it does not prove

- Production treasury half-life calibration.
- Complete intraday balance coverage.

## Spec → code lesson for Cowork

Use CP-09 when a spec mixes policy, market, filing and holdings clocks. Cowork must name each class's temporal semantics explicitly instead of giving the product one generic timestamp.

Product-specific values, thresholds, source names and policy must come from the **new approved spec/evidence**, never from this demonstration by convenience.

