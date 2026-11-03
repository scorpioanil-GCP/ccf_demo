# CP-00 — Institutional Holders

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-00-institutional-holders/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP00_INSTITUTIONAL_HOLDERS_ANALYSIS.md) · [HTML reading edition](CP00_INSTITUTIONAL_HOLDERS_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-00-institutional-holders/README.md`  
**Qualified specification:** `examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`  
**Qualified source:** `examples/cp-00-institutional-holders`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`

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

The warm-up Context Product: one source store, one system of record, one decision question. It proves that a Context Product starts with an approved specification and returns governed evidence beyond what a SELECT can provide. It also exercises the producer/assembler seam explicitly.

## The question

> Which institutional holders meet the caller's position threshold, and what governed evidence makes that answer safe to use?

## What to understand before you run it

- A Context Product is specified before it is coded.
- The source system is read-only; fabric state and product evidence are separate from the system of record.
- Assembly Mode 1 is pure algorithmic—no model participates in the trust path.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_00_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-00-institutional-holders/spec/` | The approved implementation specification; read first. |
| `examples/cp-00-institutional-holders/artifacts/` | Machine-readable recipe/question/expected evidence. |
| `examples/cp-00-institutional-holders/assembler.py` | The product's explicit ContextAssemblerProtocol implementation. |
| `examples/cp-00-institutional-holders/produce.py` | The governed product construction path. |
| `examples/cp-00-institutional-holders/run.py` | The demonstration caller/presentation. |
| `examples/cp-00-institutional-holders/README.md` | Qualified source narrative and run contract. |

## Run it

```bash
make venv
make example-cp-00
make example-cp-00 MIN_POSITION=500000000
make example-cp-00 SPEC=brief
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- A served product listing holders above the threshold.
- Context Debt, TTL/expiry, lineage/content identity and replay evidence accompanying the business answer.
- The threshold changes the governed answer rather than merely changing presentation.

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
| Raise/lower position threshold | `make example-cp-00 MIN_POSITION=500000000` | Membership and content address change. |
| Brief spec rendering | `make example-cp-00 SPEC=brief` | Only the displayed specification changes; product semantics do not. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_00_output.py tests/examples/test_cp_00_recipe_steps.py tests/examples/test_cp_00_is_algorithmic.py -q
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- Spec-first product construction.
- Producer/assembler seam is real and structurally exercised.
- Pure algorithmic Context Product can still carry Debt, lineage, TTL and content identity.

## What it does not prove

- That this early source-tree shape is the preferred code-generation pattern for new products; use a canonical paved-road example such as CP-03C for that.
- Production calibration of thresholds or half-lives.

## Spec → code lesson for Cowork

Use CP-00 primarily for specification discipline and the smallest honest product. Do not copy its older explicit producer plumbing when the new product can use the paved-road facade.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.

