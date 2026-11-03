# CP-08 — Covenant-in-Force As-Of

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-08-covenant-in-force-as-of/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP08_COVENANT_IN_FORCE_AS_OF_ANALYSIS.md) · [HTML reading edition](CP08_COVENANT_IN_FORCE_AS_OF_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-08-covenant-in-force-as-of/README.md`  
**Qualified specification:** `examples/cp-08-covenant-in-force-as-of/spec/CP-SPEC-008_Covenant_In_Force_As_Of.md`  
**Qualified source:** `examples/cp-08-covenant-in-force-as-of`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-08-covenant-in-force-as-of/spec/CP-SPEC-008_Covenant_In_Force_As_Of.md`

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

Introduces two independent time axes: when something was true and when the bank knew/recorded it. The same facility and valid date can produce a different governed answer when known_as_of moves.

## The question

> Which covenant/amendment terms were in force at the business instant, and which of those were actually known to the institution at the knowledge instant?

## What to understand before you run it

- Valid time answers 'was it in force?'; assertion/knowledge time answers 'had we booked/known it?'.
- A current-state SELECT cannot reconstruct both axes.
- The example deliberately withdrew an unsupported supersession claim when the estate did not contain evidence for it.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

Use the qualified/restored demonstration estate and read-only source credentials. This adoption guide uses placeholders even when the source README names a local development host.

```bash
export CCF_CP_08_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_08_FLUREE_LEDGER='fibo-v2'
export CCF_CP_08_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_08_POSTGRES_SCHEMA='ccf_v2'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-08-covenant-in-force-as-of/spec/` | Two-axis temporal contract and the Gate-1 correction that removed unsupported supersession. |
| `examples/cp-08-covenant-in-force-as-of/artifacts/` | Question/temporal/gate evidence. |
| `examples/cp-08-covenant-in-force-as-of/acquisition.py / deployment.py` | Dual temporal filtering and source mapping. |
| `examples/cp-08-covenant-in-force-as-of/projection.py` | Admitted amendments/covenants. |
| `examples/cp-08-covenant-in-force-as-of/produce.py` | Governed product path. |
| `examples/cp-08-covenant-in-force-as-of/run.py` | Pinned forensic question. |
| `examples/cp-08-covenant-in-force-as-of/README.md` | Measured story and limitations. |

## Run it

```bash
make venv
PYTHONPATH=src:runtime .venv/bin/python examples/cp-08-covenant-in-force-as-of/run.py
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_08_output.py -q
```

An intentional governed refusal may produce a non-zero example process exit. Read the reported refusal before treating non-zero as a broken deployment.

## What you should observe

- At the pinned example, one amendment is both in force and known while a second is already in force but excluded because it was not yet booked at known_as_of.
- Moving known_as_of later admits the later-booked amendment without changing the business valid-time question.
- Current covenant terms are labeled as current/unversioned when the estate cannot prove historical supersession.

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
| Knowledge instant equals valid instant | `set/request known_as_of=2025-09-09 for as_of=2025-09-09` | Only evidence booked by that date is admitted. |
| Later knowledge instant | `set/request known_as_of=2025-12-31 for as_of=2025-09-09` | Later-booked but already-effective amendment becomes admissible. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_08_output.py -q
```

Do not stop at the happy path. The qualified SDK example's gate/sabotage tests are the evidence that the behavior is load-bearing.

## What this example proves

- Valid time and assertion/knowledge time are separate governed dimensions.
- Unsupported historical claims should be withdrawn rather than simulated.
- Temporal reconstruction can materially change the admitted evidence.

## What it does not prove

- Historical covenant supersession in this estate; the measured estate did not contain it.
- That every domain requires two time axes.

## Spec → code lesson for Cowork

Use CP-08 when the approved spec distinguishes what was true from what was known. Cowork must generate two separately testable filters and must not collapse them into one as_of.

Product-specific values, thresholds, source names and policy must come from the **new approved spec/evidence**, never from this demonstration by convenience.

