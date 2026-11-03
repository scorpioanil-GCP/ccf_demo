# CP-17 — MNPI Wall Enforcement

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-17-mnpi-wall-enforcement/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP17_MNPI_WALL_ENFORCEMENT_ANALYSIS.md) · [HTML reading edition](CP17_MNPI_WALL_ENFORCEMENT_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-17-mnpi-wall-enforcement/README.md`  
**Qualified specification:** `examples/cp-17-mnpi-wall-enforcement/spec/CP-SPEC-017_MNPI_Wall_Enforcement.md`  
**Qualified source:** `examples/cp-17-mnpi-wall-enforcement`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-17-mnpi-wall-enforcement/spec/CP-SPEC-017_MNPI_Wall_Enforcement.md`

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

Demonstrates credential-driven formative policy and an information barrier on the paved road. The same product address serves several principals, but restricted relationships never survive into the governed view for an unauthorized principal.

## The question

> What context may this authenticated principal see about the subject at this instant, under the active information-barrier policy?

## What to understand before you run it

- The credential establishes the principal; the request does not self-assert its own privileged perspective.
- Policy runs before similarity/traversal and removes restricted relationships from the governed view.
- Suppression silence means no count or marker reveals what was withheld.
- Wall state can itself be bitemporal/known-at-time.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
export CCF_CP_17_SQLITE_PATH='<path-to-read-only-departmental.sqlite>'
export CCF_CP_17_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_17_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_17_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_17_FLUREE_LEDGER='fibo-v2'
export CCF_CP_17_MONGO_URI='mongodb://<read-only-user>:<password>@<host>:<port>/?authSource=<auth-database>'
export CCF_CP_17_MONGO_DB='fibo_v2'
export CCF_CP_17_TOKEN_COVERAGE='<credential>'
export CCF_CP_17_TOKEN_RESEARCH='<credential>'
export CCF_CP_17_TOKEN_TRADER='<credential>'
export CCF_CP_17_TOKEN_KYC='<credential>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-17-mnpi-wall-enforcement/spec/` | Information-barrier decision, roles and temporal wall semantics. |
| `examples/cp-17-mnpi-wall-enforcement/ccf_config.yaml` | Product/request/operator/policy declarations. |
| `examples/cp-17-mnpi-wall-enforcement/ccf_environment.yaml` | Credential and source names. |
| `examples/cp-17-mnpi-wall-enforcement/artifacts/perspectives.yaml` | Principal-conditioned views. |
| `examples/cp-17-mnpi-wall-enforcement/acquisition.py` | Source reads and credential-bound envelope inputs. |
| `examples/cp-17-mnpi-wall-enforcement/projection.py` | Role-conditioned payload from admitted view. |
| `examples/cp-17-mnpi-wall-enforcement/deployment.py` | Policy/debt bindings. |
| `examples/cp-17-mnpi-wall-enforcement/run.py` | Multi-principal and two-clock variations. |

## Run it

```bash
make venv
make -s example-cp-17
make -s example-cp-17 PRINCIPAL=--principal=PRIN-RES-002
make -s example-cp-17 PRINCIPAL=--principal=PRIN-TRD-003
make -s example-cp-17 ASKED_AT=--asked-at=2026-03-10T00:00:00+00:00
make -s example-cp-17 ASKED_AT=--asked-at=2026-03-10T00:00:00+00:00 KNOWN_AS_OF=--known-as-of=2026-03-20T00:00:00+00:00
make -s example-cp-17 PRINCIPAL=--principal=PRIN-KYC-004
make -s example-cp-17 SUBJECT=--subject=0000000000000000NOPE
make -s example-cp-17 SUBJECT=--subject=0000000000000000NOPE DEBT_TOLERANCE=--debt-tolerance=1.0
.venv/bin/python examples/cp-17-mnpi-wall-enforcement/run.py --door
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- Coverage, research and trader principals receive different admitted context through the same door.
- Restricted relationships are absent from the GraphView for unauthorized principals.
- A wall crossing can be absent at one known_as_of and present when the same valid-time question is reconstructed with later knowledge.
- Ungranted credential is refused; nonexistent subject can be withheld or, at tolerance 1.0, served as computed-empty according to the qualified product semantics.

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
| Research principal | `make -s example-cp-17 PRINCIPAL=--principal=PRIN-RES-002` | Published-research view. |
| Trader principal | `make -s example-cp-17 PRINCIPAL=--principal=PRIN-TRD-003` | Positions-oriented view. |
| Later knowledge | `make -s example-cp-17 ASKED_AT=--asked-at=2026-03-10T00:00:00+00:00 KNOWN_AS_OF=--known-as-of=2026-03-20T00:00:00+00:00` | Same valid instant, different known wall state. |
| Ungranted | `make -s example-cp-17 PRINCIPAL=--principal=PRIN-KYC-004` | Credential/perspective refusal. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_17_wall.py tests/examples/test_cp_17_doors.py tests/examples/test_cp_17_sabotage.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- Credential-driven principal binding.
- Information-barrier policy can be formative rather than redactive.
- Policy-before-Similarity/traversal is enforceable.
- Same product class/address can serve materially different governed views.

## What it does not prove

- Enterprise-wide MNPI policy certification.
- Production identity provider/IAM deployment.
- Security assessment beyond the named mechanism evidence.

## Spec → code lesson for Cowork

Use CP-17 when policy must remove context before reasoning. Cowork should derive perspective/entitlement from authenticated principal state, not let the request choose privileged context.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.

