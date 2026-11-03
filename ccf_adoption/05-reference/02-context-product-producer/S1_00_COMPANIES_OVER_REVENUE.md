# S1-00 — Companies Over Revenue

> **Current execution baseline:** SDK `v1.0.2@5f85b389`. Follow [setup and configuration](../../examples/CONFIGURATION.md); dated qualification results below retain their original scope.

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/s1-00-companies-over-revenue/README.md`  
**Qualified specification:** _No separate CP-SPEC is shipped for this starter example at the qualified baseline._  
**Qualified source:** `examples/s1-00-companies-over-revenue`

> **Read the README before opening the implementation code. For the full specification-first producer pattern, begin with CP-00.**

## Why this example exists

This is the smallest assembler-oriented demonstration of a parameterized Context Product.

Business logic is intentionally simple:

> **Which companies have revenue over the caller's threshold?**

The purpose is to see what CCF adds beyond the equivalent SQL filter.

## Prerequisites

```bash
make venv
```

The example can provision its own PostgreSQL demonstration environment through Docker, or use an existing Postgres through `CCF_TEST_POSTGRES_DSN`.

## Run it

```bash
make example-s1-00 MIN_REVENUE=1000000000
```

## What you should observe

The business rows look like an ordinary SQL query.

The Context Product additionally reports:

- measured Context Debt from source `last_updated`;
- routing/debt signal;
- policy version in force;
- content address;
- replay reference.

Changing `MIN_REVENUE` changes the question and therefore the governed answer/content identity.

## What to read

1. `README.md`
2. `ccf_config.yaml`
3. `backends.yaml`
4. `deployment.py`
5. `produce.py`
6. `consume.py`

The `scenario/` content creates the demonstration data. It is not the CCF product pattern to copy into a real deployment.

## What this teaches about configuration

The current source consolidates governed declarations into `ccf_config.yaml`, while backend connection composition remains separate.

The request contract makes `revenue_threshold` required. Omitting it refuses before touching the graph.

## What it does not do

- no traversal;
- no MCP consumer in this example;
- no complex policy/perspective;
- no multi-store estate.

Those omissions are intentional.

## Validation

Run the example target and the SDK tests that exercise the starter examples. For new product development, use the Phase 5 reference plus canonical CP-03C rather than treating S1-00's exact internal shape as the newest paved-road template.

## Cowork lesson

Use S1-00 to explain:

- a request parameter is part of product identity;
- Context Debt and policy evidence accompany the answer;
- simple domain logic can still be a governed Context Product.

Use CP-03C for current producer code-generation structure.
