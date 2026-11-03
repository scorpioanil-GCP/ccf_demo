# Client Developer Path

> **Baseline note.** The examples in this learning path remain intentionally small. For exact current `ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178` signatures and current refusal/security behavior, use the [technical reference](../05-technical-reference/README.md).

## Goal

Learn the smallest possible CCF experience first:

> **Ask a Context Product and use the governed result.**

You should be productive here before learning anything about product assembly.

## Learning path

### Step 1 — Hello World of CCF

[Hello World: ask one Context Product →](01-hello-world.md)

This is the minimum client program:

```python
from ccf.client import ProductClient

client = ProductClient.for_product("...")
result = client.ask(parameters={...})

if result.refused:
    print(result.refusal.reason)
else:
    print(result.payload)
```

Learn four ideas only:

1. a Context Product is something you **ask**;
2. the client does not construct the product;
3. the answer is served or governed-refused;
4. a served answer carries governed evidence in addition to payload.

### Step 2 — Understand the result

[ProductClient, Result, and governed refusal →](02-productclient-and-result.md)

Learn what is safe to read on both served and refused outcomes.

### Step 3 — Change the transport, not the application

[In-process vs MCP →](03-inprocess-vs-mcp.md)

Run the same product and same question over two transports.

### Step 4 — Use your agent framework

[ADK, Claude Agent SDK, and LangGraph →](04-agent-harnesses.md)

The same Context Product is consumed through three different agent harnesses.

### Step 5 — Go deeper only when needed

For exact signatures and runtime details, use the [technical reference](../05-technical-reference/README.md).

## What a client developer does not need yet

You do not need to learn:

- L1–L6 assembly;
- graph backends;
- Control Plane artifacts;
- product registration;
- operator planning;
- Context Product specifications;
- producer deployment.

Those belong to the producer path.
