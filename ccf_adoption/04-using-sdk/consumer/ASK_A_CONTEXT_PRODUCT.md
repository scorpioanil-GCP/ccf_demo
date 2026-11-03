# Ask a Context Product

> **Source and execution:** dated snippets below retain their original source baseline. For current SDK `v1.0.2@5f85b389`, use [setup and configuration](../../examples/CONFIGURATION.md) and the [current developer guide](../../05-reference/README.md).

## What you will do

Call one existing Context Product through the CCF client and handle the governed outcome.

This is the smallest SDK-client lesson. It intentionally does not explain how the product was assembled.

## Evidence baseline

`drcastillo/ccf_code@374a36007bb2fda3e968a83c2ead7d84993c0b23`

Primary evidence:

- `src/ccf/client/__init__.py`
- `src/ccf/client/client.py`
- `examples/hw1-companies-over-revenue/consume.py`

## 1. Import the consumer surface

```python
from ccf.client import ProductClient
```

The `ccf.client` package root deliberately exposes a very small consumer surface. You do not import deployment, graph, manifest, or Control Plane types to ask a product.

## 2. Choose the Context Product

```python
client = ProductClient.for_product("hw1.companies-over-revenue")
```

A `ProductClient` is bound to one product class. The caller does not need to repeat the product identity on every question.

Where that product is reached is a binding concern. The question itself remains a product concern.

## 3. Ask the question

```python
result = client.ask(
    parameters={"revenue_threshold": 1_000_000},
)
```

`parameters` is required. An empty mapping is valid when the product contract requires no product-specific parameters; omitting the mapping would be ambiguous.

### Optional temporal boundary

```python
from datetime import datetime

result = client.ask(
    parameters={"revenue_threshold": 1_000_000},
    as_of=datetime.fromisoformat("2026-09-01T12:00:00+00:00"),
)
```

When supplied, `as_of` must be timezone-aware.

When `as_of=None`, the current Phase 4A implementation resolves the default decision instant client-side in the shipped in-process and MCP-stdio adapters. The served vessel reports the graph snapshot the producer actually answered against. This is a documented current implementation boundary, not a reason for ordinary consumers to supply a timestamp unless their decision needs one.

For reproducible examples, prefer an explicit fixed instant.

## 4. Branch on the governed outcome

```python
if result.refused:
    print(result.refusal.reason)
else:
    print(result.payload)
```

This branch is part of normal application logic.

A refusal means CCF evaluated the request and the governed answer was no. It is not an exception and should not be handled as an outage.

## 5. Inspect the warrant behind a served answer

A consumer can inspect evidence carried with a successful result:

```python
if not result.refused:
    print(result.debt)
    print(result.content_address)
    print(result.lineage)
    print(result.replay_ref)
    print(result.expires_at)
```

The exact business payload is product-specific. The governed result behavior is shared.

## The complete pattern

```python
from ccf.client import ProductClient

client = ProductClient.for_product("hw1.companies-over-revenue")
result = client.ask(parameters={"revenue_threshold": 1_000_000})

if result.refused:
    print(f"refused: {result.refusal.reason}")
else:
    for company in result.payload["companies"]:
        print(company["name"], company["revenue"])

    print("debt:", result.debt)
    print("content address:", result.content_address)
    print("replay:", result.replay_ref)
```

## What just happened

The consumer supplied:

- the Context Product identity;
- the product-specific question;
- optionally, a temporal boundary.

The consumer did **not** supply:

- which graph backend to query;
- which source systems to join;
- which operators to execute;
- which policies to bind;
- how to assemble lineage or replay;
- how the deployment booted.

That separation is the point of the consumer contract.

## Next

Read `UNDERSTAND_RESULT.md` before writing production consumer code. The most important behavior to understand is the difference among:

- served answer;
- governed refusal;
- caller error;
- transport/binding failure.
