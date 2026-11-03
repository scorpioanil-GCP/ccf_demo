# CP-11 — Credit Surveillance / Early Warning

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-11-credit-surveillance-early-warning/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP11_CREDIT_SURVEILLANCE_EARLY_WARNING_ANALYSIS.md) · [HTML reading edition](CP11_CREDIT_SURVEILLANCE_EARLY_WARNING_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-11-credit-surveillance-early-warning/README.md`  
**Qualified specification:** `examples/cp-11-credit-surveillance-early-warning/spec/CP-SPEC-011_Credit_Surveillance_Early_Warning.md`  
**Qualified source:** `examples/cp-11-credit-surveillance-early-warning`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-11-credit-surveillance-early-warning/spec/CP-SPEC-011_Credit_Surveillance_Early_Warning.md`

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

Introduces supersession and participation state into early-warning evidence. A fact can remain historically true yet stop contributing because newer evidence supersedes it; non-participating is separate from superseded.

## The question

> What current warning evidence should contribute to this obligor's surveillance state now, which evidence has been superseded, and how incomplete is the resulting context?

## What to understand before you run it

- Signals partition into current, superseded and not-participating.
- Evidence truth and decision relevance are different.
- Signal-weight decay and Context Debt freshness are different calculations.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

Use the qualified/restored demonstration estate and read-only source credentials. This adoption guide uses placeholders even when the source README names a local development host.

```bash
export CCF_CP_11_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_11_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_11_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_11_FLUREE_LEDGER='fibo-v2'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-11-credit-surveillance-early-warning/spec/` | Supersession, delta and surveillance design. |
| `examples/cp-11-credit-surveillance-early-warning/artifacts/` | Signal classes/gates/question. |
| `examples/cp-11-credit-surveillance-early-warning/acquisition.py` | Current/superseded/not-participating classification. |
| `examples/cp-11-credit-surveillance-early-warning/deployment.py` | Composite score vs Debt freshness separation. |
| `examples/cp-11-credit-surveillance-early-warning/projection.py` | Surveillance payload. |
| `examples/cp-11-credit-surveillance-early-warning/run.py` | Headline, thin-evidence, tolerance and earlier-time cases. |

## Run it

```bash
make venv
make -s example-cp-11
make -s example-cp-11 LEI=G8NWFN4YP7CR6FOP4886
make -s example-cp-11 DEBT_TOLERANCE=0.20
make -s example-cp-11 AS_OF=2026-07-20T00:00:00+00:00
```

An intentional governed refusal may produce a non-zero example process exit. Read the reported refusal before treating non-zero as a broken deployment.

## What you should observe

- Default case reaches a high surveillance band using current participating evidence.
- A thinly evidenced obligor reports absent classes through Debt rather than fabricating neutral signals.
- Tighter tolerance produces a governed refusal.
- Earlier decision instant changes which signals exist/participate.

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
| Thin evidence | `make -s example-cp-11 LEI=G8NWFN4YP7CR6FOP4886` | Missing classes increase context shortfall. |
| Tolerance refusal | `make -s example-cp-11 DEBT_TOLERANCE=0.20` | Governed refusal. |
| Earlier instant | `make -s example-cp-11 AS_OF=2026-07-20T00:00:00+00:00` | Fewer/different signals participate. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_11_output.py -q
```

Do not stop at the happy path. The qualified SDK example's gate/sabotage tests are the evidence that the behavior is load-bearing.

## What this example proves

- Supersession can end contribution without falsifying historical evidence.
- Not-participating is not the same as superseded.
- Debt can reflect missing classes independently from business-score decay.

## What it does not prove

- Production early-warning score calibration.
- That every event class has the same supersession semantics.

## Spec → code lesson for Cowork

Use CP-11 when the spec includes replacement/supersession chains or deltas. Cowork must encode participation states explicitly and keep business scoring separate from Context Debt scoring.

Product-specific values, thresholds, source names and policy must come from the **new approved spec/evidence**, never from this demonstration by convenience.

