# CP-04 — Corporate Family Tree — Canonical

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-04-canonical-corporate-family-tree/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP04_CANONICAL_CORPORATE_FAMILY_TREE_ANALYSIS.md) · [HTML reading edition](CP04_CANONICAL_CORPORATE_FAMILY_TREE_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-04-canonical-corporate-family-tree/README.md`  
**Qualified specification:** `examples/cp-04-canonical-corporate-family-tree/spec/CP-SPEC-004C_Corporate_Family_Tree_Canonical.md`  
**Qualified source:** `examples/cp-04-canonical-corporate-family-tree`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-04-canonical-corporate-family-tree/spec/CP-SPEC-004C_Corporate_Family_Tree_Canonical.md`

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

The first canonical multi-store graph product. It demonstrates that no single source is complete, that traversal depth is a caller/governance concern, that cycles are findings rather than automatic errors, and that product Debt can move with the graph returned.

## The question

> What is the governed corporate family around this legal entity at the requested depth, assembled across authoritative stores?

## What to understand before you run it

- Multi-store context is composed into one governed graph view rather than pre-flattened into one table.
- Traversal depth requested by the caller and the operator's allowed ceiling are different concepts.
- Cycles/cross-shareholdings can be valid findings.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_04C_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_04C_FLUREE_LEDGER='fibo-v2'
export CCF_CP_04C_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_04C_POSTGRES_SCHEMA='ccf_v2'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-04-canonical-corporate-family-tree/spec/` | Business/graph contract and source bindings. |
| `examples/cp-04-canonical-corporate-family-tree/ccf_config.yaml` | Traversal/operator/product declarations. |
| `examples/cp-04-canonical-corporate-family-tree/ccf_environment.yaml` | Source and door environment names. |
| `examples/cp-04-canonical-corporate-family-tree/acquisition.py` | Multi-store source access. |
| `examples/cp-04-canonical-corporate-family-tree/projection.py` | Family-tree payload from governed GraphView. |
| `examples/cp-04-canonical-corporate-family-tree/deployment.py` | Envelope/debt/product-specific logic. |
| `examples/cp-04-canonical-corporate-family-tree/produce.py` | Paved-road binding. |
| `examples/cp-04-canonical-corporate-family-tree/run.py` | Default and depth/anchor variations. |

## Run it

```bash
make venv
make example-cp-04-canonical
make example-cp-04-canonical MAX_DEPTH=1
make example-cp-04-canonical LEI=<another-lei> MAX_DEPTH=2
.venv/bin/python examples/cp-04-canonical-corporate-family-tree/run.py --door
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- The answer is assembled from graph/relational evidence; neither store alone is treated as the whole family.
- Reducing depth changes membership and content identity.
- Cycles are surfaced as governed findings rather than erased.
- Context Debt is associated with the specific assembled answer.

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
| Depth 1 | `make example-cp-04-canonical MAX_DEPTH=1` | Smaller graph and different evidence/content address. |
| Different anchor | `make example-cp-04-canonical LEI=<another-lei> MAX_DEPTH=2` | Different corporate family. |
| Door mode | `.venv/bin/python examples/cp-04-canonical-corporate-family-tree/run.py --door` | Expose same governed product for another process. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_04_canonical_output.py -q
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- Canonical multi-store assembly.
- Traversal is a governed computation over context, not a prejoined reporting hierarchy.
- Cycles can remain evidence.
- Canonical paved-road product can expose an MCP door.

## What it does not prove

- Complete enterprise legal-entity resolution.
- That one graph technology is required for Context Graphs.
- Production traversal-depth limits.

## Spec → code lesson for Cowork

Use CP-04C when the new spec requires graph traversal across multiple stores. Copy the seam boundaries and traversal discipline; source bindings and edge vocabulary must come from the new product's evidence.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.

