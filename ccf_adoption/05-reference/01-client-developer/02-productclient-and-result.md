# ProductClient, Result, and Governed Refusal

After Hello World, the entire client mental model is still small.

## ProductClient

`ProductClient` binds a client to one product class and one transport binding.

```python
client = ProductClient.for_product("domain.product")
```

The binding is resolved from:

1. explicit `binding=`;
2. otherwise `CCF_BINDING`;
3. otherwise a `BindingError`.

The transport is not part of the Context Product's business contract.

## Ask

```python
result = client.ask(
    parameters={"threshold": 100},
    as_of=decision_instant,
)
```

For reproducible examples, use an explicit timezone-aware `as_of`.

## One branch

Always check:

```python
if result.refused:
    ...
else:
    ...
```

A governed refusal is the fabric working correctly. It is not a transport outage.

### Readable on both outcomes

- `result.refused`
- `result.refusal`
- `result.product_id`
- `result.parameters`
- `result.temporal_boundary`
- `result.replay_ref` when the producer emitted one

### Served-only

- `result.payload`
- `result.debt`
- `result.content_address`
- `result.lineage`
- `result.expires_at`

The client guard prevents a refused product from quietly turning into an empty answer.

## Error taxonomy

Use exceptions for conditions such as:

- no binding;
- bad transport;
- malformed caller input;
- corrupt or mismatched wire result.

Use the returned refusal for governed outcomes such as:

- policy exclusion;
- unsupported request;
- TTL/freshness failure;
- excessive Context Debt;
- product-specific gate failure.

## Next

[Run the same product over in-process and MCP →](03-inprocess-vs-mcp.md)

Exact API shapes live in the [Consumer API reference](../05-technical-reference/CONSUMER_API.md).
