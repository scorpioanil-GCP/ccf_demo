# CCF from ADK, Claude Agent SDK, and LangGraph

> **Current execution baseline:** SDK `v1.0.2@5f85b389`. Follow [setup and configuration](../../examples/CONFIGURATION.md); dated qualification results below retain their original scope.

The next step is not a more complicated Context Product. It is the **same product through a different application framework**.

Qualified source:

`examples/hw1-harness-clients`

The teaching frame is:

> **one product, one MCP door, three clients**

## Run each deterministic leg

### Google ADK

```bash
.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk
```

### Claude Agent SDK

```bash
.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs anthropic
```

### LangGraph

```bash
.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs langgraph
```

Or all three:

```bash
make example-hw1-harness-clients
```

## What to read

Read only the three client programs first:

- `client_adk.py`
- `client_anthropic.py`
- `client_langgraph.py`

The reader-visible clients do not import `ccf`.

They know the MCP tool/question contract, not the producer implementation.

## What differs

Harness API and MCP session ownership differ.

CCF's product contract does not.

## Validate

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest \
  tests/examples/test_hw1_harness_clients_no_model.py \
  tests/examples/test_hw1_harness_clients_wiring.py \
  tests/examples/test_client_example_purity.py -q
```

## Where next?

If you only consume products, you can stop here and use the [technical reference](../05-technical-reference/README.md) as needed.

If you need to build products, continue to the [Context Product Producer path](../02-context-product-producer/README.md).
