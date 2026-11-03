# CP-19 — AML Typology Match

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-19-aml-typology-match/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP19_AML_TYPOLOGY_MATCH_ANALYSIS.md) · [HTML reading edition](CP19_AML_TYPOLOGY_MATCH_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-19-aml-typology-match/README.md`  
**Qualified specification:** `examples/cp-19-aml-typology-match/spec/CP-SPEC-019_AML_Typology_Match.md`  
**Qualified source:** `examples/cp-19-aml-typology-match`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-19-aml-typology-match/spec/CP-SPEC-019_AML_Typology_Match.md`

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

Demonstrates policy-before-similarity in a high-sensitivity domain. The permitted disposition set is computed before candidate generation, restricted existence can disappear entirely from lower perspectives, and posture is selected at the decision instant.

## The question

> Which typology/disposition matches may this principal consider for this alert under the posture and entitlements in force at the requested instant?

## What to understand before you run it

- The policy bound must be computed before candidate generation.
- Restricted existence can be suppressed, not merely restricted content.
- Perspective fixes the payload member set so absence of a member does not itself leak information.
- Policy posture is effective-dated.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
export CCF_CP_19_SQLITE_PATH='<path-to-read-only-departmental.sqlite>'
export CCF_CP_19_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_19_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_19_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_19_FLUREE_LEDGER='fibo-v2'
export CCF_CP_19_MONGO_URI='mongodb://<read-only-user>:<password>@<host>:<port>/?authSource=<auth-database>'
export CCF_CP_19_MONGO_DB='fibo_v2'
export CCF_CP_19_TOKEN_L1='<credential>'
export CCF_CP_19_TOKEN_L2='<credential>'
export CCF_CP_19_TOKEN_EXAMINER='<credential>'
export CCF_CP_19_TOKEN_UNGRANTED='<credential>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-19-aml-typology-match/spec/` | Policy-before-similarity and perspective contract. |
| `examples/cp-19-aml-typology-match/ccf_config.yaml` | Product/request/operator/policy declarations. |
| `examples/cp-19-aml-typology-match/ccf_environment.yaml` | Credential/source names. |
| `examples/cp-19-aml-typology-match/artifacts/` | Postures, perspectives, vocabulary and gates. |
| `examples/cp-19-aml-typology-match/acquisition.py` | Posture-bound candidate acquisition. |
| `examples/cp-19-aml-typology-match/projection.py` | Perspective-specific shape. |
| `examples/cp-19-aml-typology-match/deployment.py` | Policy/debt semantics. |
| `examples/cp-19-aml-typology-match/run.py` | Role/time/refusal variations. |

## Run it

```bash
make venv
make -s example-cp-19
make -s example-cp-19 PRINCIPAL=--principal=PRIN-AML-L2
make -s example-cp-19 PRINCIPAL=--principal=PRIN-AML-EXAM
make -s example-cp-19 AS_OF=--as-of=2025-06-01T00:00:00+00:00
make -s example-cp-19 AS_OF=--as-of=2026-02-01T00:00:00+00:00
make -s example-cp-19 AS_OF=--as-of=2025-01-01T00:00:00+00:00
make -s example-cp-19 PRINCIPAL=--principal=PRIN-AML-XXX
make -s example-cp-19 SUBJECT=--subject=ALT-999999
make -s example-cp-19 SUBJECT=--subject=ALT-999999 DEBT_TOLERANCE=--debt-tolerance=1.0
.venv/bin/python examples/cp-19-aml-typology-match/run.py --door
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- L1, L2 and examiner perspectives expose progressively different governed evidence.
- Changing as_of selects a different regulatory/internal posture and therefore a different permitted candidate set.
- A posture before any permitted set yields no candidate rather than inventing a default.
- Restricted SAR-related existence is not exposed to principals below the allowed perspective.
- Unknown principal is refused; empty subject can be withheld or computed-empty under explicit tolerance.

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
| L2 reviewer | `make -s example-cp-19 PRINCIPAL=--principal=PRIN-AML-L2` | Wider governed evidence. |
| Examiner | `make -s example-cp-19 PRINCIPAL=--principal=PRIN-AML-EXAM` | Fuller chain/attribution. |
| Earlier posture | `make -s example-cp-19 AS_OF=--as-of=2025-06-01T00:00:00+00:00` | Different permitted disposition set. |
| No posture yet | `make -s example-cp-19 AS_OF=--as-of=2025-01-01T00:00:00+00:00` | Nothing permitted; no invented candidate. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_19_typology.py tests/examples/test_cp_19_door.py tests/examples/test_cp_19_sabotage.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- Policy can bound candidate generation before similarity.
- Perspective can suppress restricted existence.
- Effective-dated posture is a product input to governed reasoning.

## What it does not prove

- Production AML policy or typology effectiveness.
- Use of named real obligors—the example's synthetic-obligor constraint remains binding.

## Spec → code lesson for Cowork

Use CP-19 when similarity/ranking must operate only inside a policy-permitted universe. Cowork must generate Policy before Similarity structurally, not rank first and filter later.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.

