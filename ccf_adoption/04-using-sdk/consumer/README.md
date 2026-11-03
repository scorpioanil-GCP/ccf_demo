# Consume Context Products

> **Source and execution:** dated snippets below retain their original source baseline. For current SDK `v1.0.2@5f85b389`, use [setup and configuration](../../examples/CONFIGURATION.md) and the [current developer guide](../../05-reference/README.md).

## Goal

This path is for an application or agent developer who wants to **use an existing Context Product**.

You do not need to learn how the Context Product was assembled before you can consume it.

At the SDK boundary, the normal client surface is deliberately small:

- `ProductClient`
- `Result`
- `TransportError`
- `BindingError`

The package root exports exactly those four names on the Phase 4A baseline. Producer-side manifest, deployment, Control Plane, graph, and assembly types do not cross the consumer boundary.

## The mental model

A consumer does three things:

1. **Choose a product class.** This is the governed Context Product contract you want to ask.
2. **Ask a question.** The question supplies the product-specific parameters and, when needed, a temporal boundary.
3. **Handle the governed outcome.** A `Result` is either a served Context Product or an explicit refusal.

A refusal is not a transport failure. It means the fabric evaluated the request and the governed answer was **no**.

## Two consumption lanes

### Lane A — use `ccf.client`

Use this when your application imports the CCF SDK and you want a transport-neutral client abstraction.

The core pattern is intentionally small:

```python
from ccf.client import ProductClient

client = ProductClient.for_product("hw1.companies-over-revenue")
result = client.ask(parameters={"revenue_threshold": 1_000_000})

if result.refused:
    handle_refusal(result.refusal)
else:
    use(result.payload)
```

Where the product lives is resolved separately from what the caller asks. The same application code can use a different binding without learning producer internals.

### Lane B — use an MCP-capable agent harness

If your harness already speaks MCP, the client program does **not** need to import CCF at all.

The approved harness-neutral example demonstrates the same governed Context Product through the same MCP door from:

- Google ADK
- Claude Agent SDK
- LangGraph

The product is constant; the harness is the variable.

## What a successful answer gives you

A served result exposes more than the business payload. Depending on the deployment, a consumer can inspect:

- payload
- Context Debt assessment
- content address
- lineage
- replay reference
- expiry / validity information

Those fields are evidence about the answer, not producer implementation details.

## What a refusal gives you

A refused result remains a governed outcome. The consumer can inspect the refusal and request identity, and the current SDK also carries a replay reference when the producer recorded one.

Fields that exist only after successful assembly are guarded. If caller code ignores `result.refused` and tries to read a served-only field, the SDK raises rather than silently returning `None`.

## Learning sequence

1. `ASK_A_CONTEXT_PRODUCT.md`
2. `UNDERSTAND_RESULT.md`
3. `BINDINGS_AND_ERRORS.md`
4. `CONSUME_OVER_MCP.md`

After those four pages, a consumer should be able to integrate an existing Context Product without learning the assembly path.

## Boundary

This section does **not** teach:

- how to author a Context Product specification;
- how to restore the full demonstration estate;
- how graph state is built;
- how operators are composed;
- how projection is implemented;
- how Control Plane artifacts are authored;
- how deployments are booted.

Those belong to the assembler track.
