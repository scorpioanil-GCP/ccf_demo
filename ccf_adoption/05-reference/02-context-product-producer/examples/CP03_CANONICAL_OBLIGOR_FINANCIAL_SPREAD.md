# CP-03 — Obligor Financial Spread — Canonical

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-03-canonical-obligor-financial-spread/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD_ANALYSIS.md) · [HTML reading edition](CP03_CANONICAL_OBLIGOR_FINANCIAL_SPREAD_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-03-canonical-obligor-financial-spread/README.md`  
**Qualified specification:** `examples/cp-03-canonical-obligor-financial-spread/spec/CP-SPEC-003C_Obligor_Financial_Spread_Canonical.md`  
**Qualified source:** `examples/cp-03-canonical-obligor-financial-spread`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-03-canonical-obligor-financial-spread/spec/CP-SPEC-003C_Obligor_Financial_Spread_Canonical.md`

Read it in this order before opening the Python:

| Spec section | What to learn | Where it lands |
|---|---|---|
| §A | decision, consumer, counterfactual, scope | README + acceptance tests |
| §B | product contract, request, TTL, policy/perspective | `ccf_config.yaml` + payload |
| §C | sources, identity, ontology, data traps | acquisition + environment/source declarations |
| §D | operators, projection, gates | `acquisition.py`, `deployment.py`, `projection.py`, `produce.py` |
| §E | half-life, Context Debt, materialization | config + assessment code |
| §F | source readiness and limitations | environment/source artifacts + findings |
| §G | acceptance and operational evidence | tests, gates, run evidence |

As you read the code, ask: **which approved spec term is this implementing?**

## Why this example exists

The primary paved-road implementation example. It modernizes the historical CP-03 without editing the frozen specimen and demonstrates how a current Context Product should separate configuration, environment, acquisition, graph state, projection, debt assessment and a very thin product spine.

## The question

> What is the obligor's period-aligned financial spread under the requested reporting basis, which filings asserted each figure, and is the resulting context fresh/complete enough to serve?

## What to understand before you run it

- This is the default code-generation precedent for a normal new product.
- Each dated financial fact becomes fabric state; projection and Debt both read the governed GraphView.
- `intent` is a top-level request axis, not a duplicate ordinary argument.
- Policy-bound request values are effective request state, not writes over resolved artifacts.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_03C_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_03C_POSTGRES_SCHEMA='ccf_v2'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-03-canonical-obligor-financial-spread/spec/` | Approved product contract and source/data traps. |
| `examples/cp-03-canonical-obligor-financial-spread/ccf_config.yaml` | Product class, request contract, operator parameters, TTL/half-life/debt/policy declarations. |
| `examples/cp-03-canonical-obligor-financial-spread/ccf_environment.yaml` | Names of source/substrate/door environment values; no secret values. |
| `examples/cp-03-canonical-obligor-financial-spread/acquisition.py` | Source-only leg; deliberately imports no CCF. |
| `examples/cp-03-canonical-obligor-financial-spread/deployment.py` | SignalEnvelope mapping, assessment and declared product predicate. |
| `examples/cp-03-canonical-obligor-financial-spread/projection.py` | Π from governed GraphView. |
| `examples/cp-03-canonical-obligor-financial-spread/produce.py` | The paved road: plan factory + open_product + opened.answer. |
| `examples/cp-03-canonical-obligor-financial-spread/run.py` | Demonstration caller and variations. |
| `examples/cp-03-canonical-obligor-financial-spread/FINDINGS.md` | Measured implementation/data findings. |

## Run it

```bash
make venv
make example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0
make example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=0.25
make -s example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0
make example-cp-03-canonical BASIS=latest-restated ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0
make example-cp-03-canonical PRINCIPAL=PRIN-KYC-004 ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- At wide tolerance the product serves; at the governed 0.25 tolerance the same question is withheld/refused with a replay reference.
- Changing basis changes the financial truth being requested and therefore the content address.
- Per-period/per-line filing dates remain visible; `NOT_EVALUABLE` is used instead of inventing zero.
- Expiry is anchored to the freshest filing in the admitted payload.
- A principal outside the jurisdiction grant gets no obligor in the admitted view.

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
| Debt tolerance | `make example-cp-03-canonical ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=0.25` | Same assembled evidence, governed fulfillment changes to withholding. |
| Reporting basis | `make example-cp-03-canonical BASIS=latest-restated ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0` | Payload figures/basis and content address change. |
| Principal | `make example-cp-03-canonical PRINCIPAL=PRIN-KYC-004 ASKED_AT=2026-09-07T12:00:00+00:00 DEBT_TOLERANCE=1.0` | Policy-shaped view changes/refuses. |
| Alternative obligor | `make example-cp-03-canonical LEI=549300D0WZR1VI2QGB24 ASKED_AT=2026-08-29T12:00:00+00:00 DEBT_TOLERANCE=1.0` | Different subject and evidence. |

## Validate it

```bash
CCF_REQUIRE_ESTATE=1 PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_03_canonical_output.py tests/examples/test_cp_03_canonical_cross_deployment.py tests/examples/test_cp_03_canonical_paved_consumer.py -q -rs
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- Modern two-document paved-road deployment.
- GraphView discipline for projection and Debt.
- Per-attribute temporal/provenance semantics.
- Governed fulfillment by Debt tolerance.
- Canonical successor can replace an old implementation without rewriting the frozen specimen.

## What it does not prove

- That the example's half-lives/tolerances are production recommendations.
- That all financial spreading domains use the same line vocabulary.
- Decision Replay replacement environment mechanics currently under D-IMPL-346/347 work.

## Spec → code lesson for Cowork

This is the default structural code-generation target. Cowork should copy the separation and paved-road shape, not the domain values, table names, thresholds, or financial vocabulary.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.

