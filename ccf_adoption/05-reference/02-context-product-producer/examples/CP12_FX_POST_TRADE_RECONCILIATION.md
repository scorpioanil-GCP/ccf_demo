# CP-12 — FX Post-Trade Reconciliation

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-12-fx-post-trade-reconciliation/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP12_FX_POST_TRADE_RECONCILIATION_ANALYSIS.md) · [HTML reading edition](CP12_FX_POST_TRADE_RECONCILIATION_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-12-fx-post-trade-reconciliation/README.md`  
**Qualified specification:** `examples/cp-12-fx-post-trade-reconciliation/spec/CP-SPEC-012_FX_Post_Trade_Reconciliation.md`  
**Qualified source:** `examples/cp-12-fx-post-trade-reconciliation`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-12-fx-post-trade-reconciliation/spec/CP-SPEC-012_FX_Post_Trade_Reconciliation.md`

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

Shows why apparent disagreement among systems can be temporally coherent rather than a simple data-quality defect. It corrects system clocks, distinguishes timing from genuine breaks and refuses to decompose a break when the evidence resolution cannot support the claim.

## The question

> For each FX trade, which discrepancies are explained by observation timing/clock skew and which remain genuine after reconstruction?

## What to understand before you run it

- Recorded timestamp is not necessarily the true observation instant.
- Three systems create three pairs, but the unit of business work is the trade—not each pair.
- `not-evaluable` is safer than a false zero when market series resolution cannot explain the timing component.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

Use the qualified/restored demonstration estate and read-only source credentials. This adoption guide uses placeholders even when the source README names a local development host.

```bash
export CCF_CP_12_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_12_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_12_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_12_FLUREE_LEDGER='fibo-v2'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-12-fx-post-trade-reconciliation/spec/` | True-instant reconciliation contract and unit-of-analysis rules. |
| `examples/cp-12-fx-post-trade-reconciliation/artifacts/` | Clock/source/gate/question declarations. |
| `examples/cp-12-fx-post-trade-reconciliation/acquisition.py` | Three-system reads and clock correction. |
| `examples/cp-12-fx-post-trade-reconciliation/deployment.py` | Temporal/debt handling. |
| `examples/cp-12-fx-post-trade-reconciliation/projection.py` | Per-trade reconciliation payload. |
| `examples/cp-12-fx-post-trade-reconciliation/run.py` | Alignment/current-state/refusal variations. |

## Run it

```bash
make venv
make -s example-cp-12
make -s example-cp-12 COMPARE_AT=latest
make -s example-cp-12 NO_ALIGN_CLOCKS=1
make -s example-cp-12 TRADES=TRD-W12-0004 SCOPE=TRD-W12-0004
make -s example-cp-12 DEBT_TOLERANCE=0.02
```

An intentional governed refusal may produce a non-zero example process exit. Read the reported refusal before treating non-zero as a broken deployment.

## What you should observe

- Clock offsets are corrected before values are compared.
- Conventional no-alignment/latest-state variations change classification.
- A pinned trade remains a genuine break even when all corrected instants align.
- Insufficient market-series resolution returns not-evaluable rather than zero.
- Tight tolerance yields a governed refusal.

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
| Latest/current comparison | `make -s example-cp-12 COMPARE_AT=latest` | Shows what a current-state approach would see. |
| No clock alignment | `make -s example-cp-12 NO_ALIGN_CLOCKS=1` | Timing and genuine breaks become harder to distinguish. |
| Known genuine break | `make -s example-cp-12 TRADES=TRD-W12-0004 SCOPE=TRD-W12-0004` | All corrected clocks align; discrepancy remains. |
| Tight tolerance | `make -s example-cp-12 DEBT_TOLERANCE=0.02` | Governed refusal. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_12_output.py -q
```

Do not stop at the happy path. The qualified SDK example's gate/sabotage tests are the evidence that the behavior is load-bearing.

## What this example proves

- Temporal reconstruction can distinguish timing noise from genuine discrepancy.
- Not-evaluable is a legitimate governed outcome component.
- Unit-of-analysis choice changes operational consequence.

## What it does not prove

- Production FX reconciliation tolerances.
- That a 5-minute market series can explain every sub-5-minute move.

## Spec → code lesson for Cowork

Use CP-12 when multiple source clocks must be normalized. Cowork should make clock correction and evaluability rules explicit in the spec and code, not bury them in presentation.

Product-specific values, thresholds, source names and policy must come from the **new approved spec/evidence**, never from this demonstration by convenience.

