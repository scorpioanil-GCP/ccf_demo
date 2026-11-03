# CP-20 — Syndicated Lending Co-Lender

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-20-syndicated-lending-co-lender/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP20_SYNDICATED_LENDING_CO_LENDER_ANALYSIS.md) · [HTML reading edition](CP20_SYNDICATED_LENDING_CO_LENDER_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-20-syndicated-lending-co-lender/README.md`  
**Qualified specification:** `examples/cp-20-syndicated-lending-co-lender/spec/CP-SPEC-020_Syndicated_Lending_Co_Lender.md`  
**Qualified source:** `examples/cp-20-syndicated-lending-co-lender`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-20-syndicated-lending-co-lender/spec/CP-SPEC-020_Syndicated_Lending_Co_Lender.md`

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

First cross-organizational composition example. A local composite asks another organization's independently governed deployment and admits only what the peer is authorized and able to attest under the negotiated envelope.

## The question

> Can the required-lender consent threshold be evaluated using local positions plus governed claims from co-lenders without pretending the bank owns or can reconstruct the peer's internal data?

## What to understand before you run it

- Cross-organizational admission uses the same governed child-product principle, with additional peer identity/trust controls.
- Request envelope and disclosure envelope are separate; a fact not requestable must never be inferred.
- An unattested remote claim is refused rather than discounted.
- Banded disclosure remains a band; the consumer must not invent a midpoint.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The demonstrations read qualified/restored source estates. Use read-only source roles where the example requires them. The variable names below are contractual to the example; values are deployment-specific.

```bash
export CCF_CP_20_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_20_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_20_FLUREE_URL='http://<local-fluree-host>:<port>'
export CCF_CP_20_FLUREE_LEDGER='fibo-v2'
export CCF_CP_20_PEER_POSTGRES_DSN='host=<peer-host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_20_PEER_POSTGRES_SCHEMA='colender'
export CCF_CP_20_PEER_FLUREE_URL='http://<peer-fluree-host>:<port>'
export CCF_CP_20_PEER_FLUREE_LEDGER='<peer-ledger>'
export CCF_CP_20_PEER_DOOR_TOKEN='<peer-door-token>'
```

## Files to read

| Path | Why |
|---|---|
| `examples/cp-20-syndicated-lending-co-lender/spec/` | Federation/consent/envelope contract. |
| `examples/cp-20-syndicated-lending-co-lender/ccf_config.yaml` | Local composite/peer trust declarations. |
| `examples/cp-20-syndicated-lending-co-lender/ccf_environment.yaml` | Peer endpoint/token and local source names. |
| `examples/cp-20-syndicated-lending-co-lender/../peer-cp-20-co-lender/` | Independent peer deployment. |
| `examples/cp-20-syndicated-lending-co-lender/acquisition.py` | Local/peer acquisition and envelope handling. |
| `examples/cp-20-syndicated-lending-co-lender/projection.py` | Consent arithmetic and disclosed evidence. |
| `examples/cp-20-syndicated-lending-co-lender/deployment.py` | Peer admission/trust mappings. |
| `examples/cp-20-syndicated-lending-co-lender/run.py` | Cross-process demonstration. |

## Run it

Start the peer in a separate terminal with its source variables and chosen `CCF_CP_20_PEER_DOOR_TOKEN`; the door command blocks while serving. Run the local consumer in another terminal with the matching token and printed peer port.

```bash
make venv
.venv/bin/python examples/peer-cp-20-co-lender/run.py --door
```

In the consumer terminal:

```bash
# use the peer's READY <port> value
export CCF_CP20_PEER_URL='http://127.0.0.1:<port>/mcp'
export CCF_CP20_PEER_TOKEN='<peer-door-token>'
.venv/bin/python examples/cp-20-syndicated-lending-co-lender/run.py --include-federated
```

Some commands intentionally produce governed refusal/non-success and may exit non-zero. That is not equivalent to a transport/program crash.

## What you should observe

- Local and peer deployments retain separate tenants/control planes.
- The composite admits peer claims only when identity/trust/contract/attestation requirements hold.
- Peer disclosure envelope can expose a band without an exact share; no midpoint is created.
- Remote evidence is labeled remote-attested while local evidence remains local-reconstructible.
- An unattested peer claim can refuse the composite even when the slot is otherwise optional according to the governed rule.

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
| Peer door available | `run peer door + --include-federated` | Remote claim participates after admission. |
| Peer claim unattested | `use the source's documented negative scenario/test` | Composite refuses rather than estimating. |
| Banded peer disclosure | `use peer configuration that permits band only` | Bounds remain bounds; no exact position appears. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_20_co_lender.py tests/examples/test_cp_20_peer_and_identity.py -q
```

Validation is part of reproduction. A manual demonstration is not enough for a claim the example's tests/gates are designed to hold.

## What this example proves

- Cross-organizational Context Product exchange can preserve independent control boundaries.
- Receiving side admission separates identity, trust, contract and lineage concerns.
- Disclosure precision can be governed.
- Remote-attested evidence can coexist with local-reconstructible evidence without pretending equivalence.

## What it does not prove

- Production legal agreement enforceability.
- That A2A defines Peering; the example's peer door uses the qualified mechanism while Peering is the architectural category.
- Enterprise PKI/network deployment.

## Spec → code lesson for Cowork

Use CP-20 only when the approved spec crosses an organizational/fabric trust boundary. Cowork must preserve separate authorities and never read the peer's source estate from the local product.

When adapting the pattern, product-specific values must come from the new approved spec and measured source evidence. Do not copy demonstration calibration as policy.

