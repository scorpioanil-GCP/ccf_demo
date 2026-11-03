# CP-15 — KYC Refresh / Beneficial Ownership

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-15-kyc-refresh-beneficial-ownership/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP15_KYC_REFRESH_BENEFICIAL_OWNERSHIP_ANALYSIS.md) · [HTML reading edition](CP15_KYC_REFRESH_BENEFICIAL_OWNERSHIP_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-15-kyc-refresh-beneficial-ownership/README.md`  
**Qualified specification:** `examples/cp-15-kyc-refresh-beneficial-ownership/spec/CP-SPEC-015_KYC_Refresh_Beneficial_Ownership.md`  
**Qualified source:** `examples/cp-15-kyc-refresh-beneficial-ownership`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-15-kyc-refresh-beneficial-ownership/spec/CP-SPEC-015_KYC_Refresh_Beneficial_Ownership.md`

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

Shows that a finding is not an absence and demonstrates a governed handoff from an immutable Context Product to HITL review. It also makes residency/entitlement formative: restricted persons are never materialized for an unentitled principal.

## The question

> Who are the relevant beneficial owners for this KYC intent, which findings require human review, and what governed evidence links the review back to the immutable product?

## What to understand before you run it

- Below-threshold or low-confidence resolution can remain as a named finding rather than disappearing.
- HITL referral is downstream of product construction; human action does not mutate the product.
- Residency/policy exclusion happens before projection and carries no count/marker of withheld identities.
- Intent can select the ownership threshold.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

Use the qualified/restored demonstration estate and read-only source credentials. This adoption guide uses placeholders even when the source README names a local development host.

```bash
export CCF_CP_15_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_15_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_15_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_15_FLUREE_LEDGER='fibo-v2'
export CCF_CP_15_MONGO_URI='mongodb://<read-only-user>:<password>@<host>:<port>/?authSource=<auth-database>'
export CCF_CP_15_MONGO_DB='fibo_v2'
export CCF_CP_15_TOKEN_KYC='<credential>'
export CCF_CP_15_TOKEN_COVERAGE='<credential>'
export CCF_CP_15_TOKEN_RESEARCH='<credential>'
export CCF_CP_15_TOKEN_UNGRANTED='<credential>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-15-kyc-refresh-beneficial-ownership/spec/` | Ownership, findings, residency and HITL contract. |
| `examples/cp-15-kyc-refresh-beneficial-ownership/ccf_config.yaml` | Intent/request/policy/debt declarations. |
| `examples/cp-15-kyc-refresh-beneficial-ownership/ccf_environment.yaml` | Three stores and credential names. |
| `examples/cp-15-kyc-refresh-beneficial-ownership/acquisition.py` | Ownership/source reads. |
| `examples/cp-15-kyc-refresh-beneficial-ownership/deployment.py` | Entitlement/threshold/assessment. |
| `examples/cp-15-kyc-refresh-beneficial-ownership/projection.py` | Owners and findings payload. |
| `examples/cp-15-kyc-refresh-beneficial-ownership/produce.py` | Governed product construction. |
| `examples/cp-15-kyc-refresh-beneficial-ownership/run.py` | Principal/intent/confidence cases. |
| `examples/cp-15-kyc-refresh-beneficial-ownership/tests/examples/test_cp_15_*` | Ownership, review, replay-link and sabotage evidence. |

## Run it

```bash
make venv
make -s example-cp-15
make -s example-cp-15 PRINCIPAL=--principal=PRIN-COV-001
make -s example-cp-15 ENTITY=--entity=ICJ-SPV-149
make -s example-cp-15 ENTITY=--entity=ICJ-SPV-149 INTENT=--intent=enhanced-due-diligence
make -s example-cp-15 ENTITY=--entity=ICJ-SPV-026
make -s example-cp-15 MIN_CONFIDENCE=--min-confidence=0.1
make -s example-cp-15 ENTITY=--entity=ICJ-SPV-999999
.venv/bin/python examples/cp-15-kyc-refresh-beneficial-ownership/run.py --door
```

An intentional governed refusal may produce a non-zero example process exit. Read the reported refusal before treating non-zero as a broken deployment.

## What you should observe

- Default KYC case can contain both an ownership-threshold finding and a sanctions-related finding and refer them to review.
- Coverage principal without residency entitlement does not see the restricted person at all.
- Same entity under a different intent can move a person from sub-threshold finding to reportable owner.
- Attempting to lower the declared confidence floor is refused by name.
- A nonexistent/no-chain entity is withheld rather than guessed.
- Review action produces a separate governed record linked to originating determination/output; product bytes remain unchanged.

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
| Residency denial | `make -s example-cp-15 PRINCIPAL=--principal=PRIN-COV-001` | Restricted person never materializes. |
| Intent contrast | `make -s example-cp-15 ENTITY=--entity=ICJ-SPV-149 INTENT=--intent=enhanced-due-diligence` | Threshold changes and ownership classification changes. |
| Raise/lower confidence boundary | `make -s example-cp-15 MIN_CONFIDENCE=--min-confidence=0.1` | Attempt to lower governed floor is refused. |
| Missing chain | `make -s example-cp-15 ENTITY=--entity=ICJ-SPV-999999` | Governed withholding/refusal. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_15_ownership.py tests/examples/test_cp_15_review.py tests/examples/test_cp_15_sabotage.py -q
```

Do not stop at the happy path. The qualified SDK example's gate/sabotage tests are the evidence that the behavior is load-bearing.

## What this example proves

- Findings can remain explicit without being treated as missing.
- HITL referral can preserve immutable product identity.
- Residency/policy can prevent materialization with suppression silence.
- Intent can be a load-bearing product axis.

## What it does not prove

- Production KYC ownership thresholds or sanctions policy.
- A complete enterprise HITL user interface.
- Detailed Replay environment construction.

## Spec → code lesson for Cowork

Use CP-15 when the new product produces reviewable findings. Cowork should keep product construction and human verdict as separate governed artifacts; never update the product after review.

Product-specific values, thresholds, source names and policy must come from the **new approved spec/evidence**, never from this demonstration by convenience.

