# CP-06 — Collateral & Set-off Coverage — Canonical

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-06-canonical-collateral-and-setoff-coverage/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP06_CANONICAL_COLLATERAL_AND_SETOFF_COVERAGE_ANALYSIS.md) · [HTML reading edition](CP06_CANONICAL_COLLATERAL_AND_SETOFF_COVERAGE_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-06-canonical-collateral-and-setoff-coverage/README.md`  
**Qualified specification:** `examples/cp-06-canonical-collateral-and-setoff-coverage/spec/CP-SPEC-006C_Collateral_And_Setoff_Coverage_Canonical.md`  
**Qualified source:** `examples/cp-06-canonical-collateral-and-setoff-coverage`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-06-canonical-collateral-and-setoff-coverage/spec/CP-SPEC-006C_Collateral_And_Setoff_Coverage_Canonical.md`

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

Canonical typed-relationship product on the paved road. It demonstrates collateral haircuts, set-off, lien/enforceability state and allocation as governed graph semantics rather than side data handed to projection.

## The question

> How much of this facility is actually covered after considering collateral, haircuts, set-off, enforceability, lien status and the declared allocation basis?

## What to understand before you run it

- The commitment and enforceability facts are fabric state and are read from the governed view.
- Payload equivalence does not mean two deployments have identical contract identity.
- Typed relationship semantics change the conclusion, not just the presentation.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_06C_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_06C_FLUREE_LEDGER='fibo-v2'
export CCF_CP_06C_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_06C_POSTGRES_SCHEMA='ccf_v2'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-06-canonical-collateral-and-setoff-coverage/spec/` | Coverage semantics and typed edge contract. |
| `examples/cp-06-canonical-collateral-and-setoff-coverage/ccf_config.yaml` | Class/operators/request/debt declarations. |
| `examples/cp-06-canonical-collateral-and-setoff-coverage/ccf_environment.yaml` | Runtime source names. |
| `examples/cp-06-canonical-collateral-and-setoff-coverage/acquisition.py` | Source relationship acquisition. |
| `examples/cp-06-canonical-collateral-and-setoff-coverage/projection.py` | Coverage payload from GraphView. |
| `examples/cp-06-canonical-collateral-and-setoff-coverage/deployment.py` | Assessment and governed predicates. |
| `examples/cp-06-canonical-collateral-and-setoff-coverage/produce.py` | Paved-road product. |
| `examples/cp-06-canonical-collateral-and-setoff-coverage/run.py` | Variations and door. |

## Run it

```bash
make venv
make example-cp-06-canonical
make example-cp-06-canonical FACILITY=--facility=FAC-044206 SCOPE=--scope=529900E95812SYWMCE44
make example-cp-06-canonical ASKED_AT=--asked-at=2026-09-07T12:00:00+00:00
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- Coverage separates collateral after haircuts, set-off and total rather than collapsing them.
- Released/unenforceable liens are treated according to the governed relationship state.
- Changing facility/scope changes the graph and content identity.
- The canonical path uses the standard product facade rather than older hand-wired infrastructure.

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
| Facility/scope | `make example-cp-06-canonical FACILITY=--facility=FAC-044206 SCOPE=--scope=529900E95812SYWMCE44` | Different governed relationship slice. |
| Decision instant | `make example-cp-06-canonical ASKED_AT=--asked-at=2026-09-07T12:00:00+00:00` | Temporal state may move. |
| Door | `.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door` | Serve same product across process boundary. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_06_canonical_output.py -q
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- Typed collateral/set-off relationships can be governed Context Graph facts.
- Paved-road successor can serve the same class as a historical specimen without copying its plumbing.
- Projection/debt use governed state.

## What it does not prove

- Production legal enforceability opinions.
- Recommended haircut/allocation policy.

## Spec → code lesson for Cowork

Use CP-06C when a new product's correctness depends on relationship type and relationship state. Copy the graph-state discipline, not the collateral domain constants.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.

## Current-main operational changes — 17 October 2026

At SDK `5f85b389efe9e4b1de62e84a5af62ca4b2e12178`, the [current example](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-06-canonical-collateral-and-setoff-coverage/README.md) adds durable evidence via `CCF_REPLAY_EVIDENCE_ROOT`, retained-evidence `decisions` / `why` / `replay` commands and declared source-outage refusal. Scoped acquisition now gives the same governed refusal for unknown and out-of-request-scope facilities in the tested deployment. The historical measurements above are not a rerun of this current tree.

Use **Fluree 4.2.4**, actual host/port settings and a complete Postgres DSN. See [current final spec](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-06-canonical-collateral-and-setoff-coverage/spec/CP-SPEC-006C_Collateral_And_Setoff_Coverage_Canonical.md), [replay operations](../../05-technical-reference/CLI_HTTP_OPERATIONS.md#retained-evidence-commands) and [scoped security/build status](../../05-technical-reference/SECURITY_AND_AUTHORIZATION.md#current-security-disposition-and-exact-delivery-scope--17-october-2026). [SK-01](SK01_DECLARE_AND_GOVERN_AGENT_SKILLS.md) now consumes this producer through a Context Skill.
