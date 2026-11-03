# Bindings and errors

## Binding answers one question: where do I ask?

The consumer's business question and the transport used to reach the product are deliberately separate concerns.

`ProductClient.for_product()` resolves a binding in exactly this order:

1. an explicit `binding=` argument;
2. otherwise the `CCF_BINDING` environment variable;
3. otherwise `BindingError`.

There is no bindings file, per-product discovery chain, entry-point lookup, or hidden fallback on this baseline.

## Binding shape

A binding is a scheme-prefixed address.

Examples from the approved client implementation:

```text
inprocess:./deployment
mcp+stdio:./deployment
```

The scheme prefix is the transport selector. The remainder is the address the adapter receives.

## Explicit binding

```python
client = ProductClient.for_product(
    "hw1.companies-over-revenue",
    binding="inprocess:./deployment",
)
```

An explicit binding wins over `CCF_BINDING`.

## Environment binding

```bash
export CCF_BINDING='mcp+stdio:./deployment'
```

```python
client = ProductClient.for_product("hw1.companies-over-revenue")
```

This lets the same consumer code move across transports without embedding transport choice into the business logic.

## Adapter registration is explicit today

The binding registry starts empty. Shipped adapters register their schemes when their modules are imported.

For example, the HW-1 direct client imports the in-process and MCP-stdio adapter modules, but it does not choose between them in code; the binding does that.

This is current implementation behavior and should remain version-pinned in documentation.

## Error boundaries

### `BindingError`

Use this when the client cannot resolve a usable binding:

- no explicit binding and `CCF_BINDING` is unset;
- malformed scheme-prefixed address;
- no adapter registered for the requested scheme.

`BindingError` is a transport-family configuration failure, not a governed Context Product refusal.

### `TransportError`

Use this boundary for cases where the wire does not successfully yield a valid governed outcome.

`BindingError` is a subclass of `TransportError`, so an application may intentionally catch only `TransportError` when it wants one operational path for all "the wire never spoke" failures.

### Caller validation errors

Malformed caller arguments are not transport outages. A naive `datetime` supplied as `as_of`, for example, should be fixed by the caller rather than retried as though the transport failed.

### Governed refusal

Never map a governed refusal onto either error class.

```python
result = client.ask(parameters=question)

if result.refused:
    handle_refusal(result.refusal)
```

## Operational rule

**Switching transport should be an operational decision; changing the question should be an application decision.**

Keeping those separate is what makes the same consumer logic portable across in-process and MCP-oriented deployments.
