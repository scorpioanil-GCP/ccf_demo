# S1-01 — Hello Context Product

> **Current execution baseline:** SDK `v1.0.2@5f85b389`. Follow [setup and configuration](../../examples/CONFIGURATION.md); dated qualification results below retain their original scope.

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/s1-01-hello-context-product/README.md`  
**Qualified specification:** _No separate CP-SPEC is shipped for this starter example at the qualified baseline._  
**Qualified source:** `examples/s1-01-hello-context-product`

> **Read the README before opening the implementation code. For the full specification-first producer pattern, begin with CP-00.**

## Why this example exists

This is the “Hello Context Product” assembler example: a small product that exercises a richer governed contract than S1-00.

It is useful for seeing where the fabric ends and the adopter's product-specific work begins.

## Important qualification note

At the pinned full qualification of `015be95f…`, the S1-01 functional nodes were **prerequisite-blocked** because the required Fluree service was unavailable during qualification.

That is not evidence of an SDK failure, and it is also not a basis to claim the full example was reproduced in that qualification run.

Use the commands below when a compatible Fluree endpoint is available.

## Prerequisites

```bash
make venv
```

The example requires Fluree. Follow the [shared setup and configuration rules](../../examples/CONFIGURATION.md) and replace every placeholder before running.

The [current source README](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/s1-01-hello-context-product/README.md) uses Fluree **4.2.4**. This example writes transactions: use a disposable instance, never the shared curated estate. Replace `<port>` with a free local port (8090 below is the container port):

```bash
docker run -d --rm --name ccf-s1-01-fluree --memory 4g -p "<port>:8090" fluree/server:4.2.4
```

Then expose the endpoint expected by the test/example environment:

```bash
export CCF_TEST_FLUREE_URL='http://localhost:<port>'
```

## Run it

Preferred target:

```bash
make example-s1-01
```

Direct path with the qualified virtualenv:

```bash
CCF_TEST_FLUREE_URL='http://localhost:<port>' \
PYTHONPATH=src:runtime \
.venv/bin/python examples/s1-01-hello-context-product/run.py
```

A pinned explicit question can also be asked directly according to the source example:

```bash
PYTHONPATH=src:runtime \
.venv/bin/python examples/s1-01-hello-context-product/run.py \
  --subject http://example.org/fibo/GammaBank \
  --as-of 2026-08-01T00:00:00Z \
  --decision-instant 2026-08-01T00:05:00Z
```

## Correctness leg

The example target proves the program runs.

The substrate leg is the stronger correctness path:

```bash
make leg-fluree
```

## What to read

1. `README.md`
2. the product specification/artifacts
3. deployment/configuration
4. assembly/product spine
5. `run.py`
6. `tests/examples/test_s1_01_output.py`

## What you should observe

With a compatible populated Fluree service:

- the declared questions are answered through the governed Context Product path;
- source/substrate-specific behavior is separated from the product contract;
- governance fields such as Debt/evidence/fulfillment are visible according to the example.

## Common failure

If the Fluree endpoint is absent/unreachable, the substrate-dependent nodes cannot complete. Treat that as a missing prerequisite, not as a product refusal.

## What this proves

When the substrate is available and the leg passes, it demonstrates a small governed product over a networked graph substrate.

## What it does not prove

The `015be95f…` full qualification did not independently reproduce its substrate-dependent functional path because Fluree was unavailable.

## Cowork lesson

Use this example for a small networked-substrate walkthrough, but use the canonical paved-road CP examples when generating the current preferred new-product structure.
