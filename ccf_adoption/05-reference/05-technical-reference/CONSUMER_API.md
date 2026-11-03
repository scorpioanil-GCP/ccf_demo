# Consumer API

**Package:** `ccf.client`  
**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

## Package-level surface

`ccf.client` exports exactly four adopter-facing names:

- `ProductClient`
- `Result`
- `BindingError`
- `TransportError`

That small surface is deliberate. Product assembly, deployment manifests, Control Plane artifacts and transport-specific types do not cross the ordinary consumer boundary.

## ProductClient

### Construct by product

```python
from ccf.client import ProductClient

client = ProductClient.for_product(
    "credit-risk.spread",
    binding="inprocess:./deployment",
)
```

Signature:

```python
ProductClient.for_product(product_id: str, binding: str | None = None) -> ProductClient
```

Binding resolution is exactly:

1. explicit `binding=`;
2. otherwise `CCF_BINDING`;
3. otherwise `BindingError`.

A binding is scheme-prefixed, for example:

- `inprocess:./deployment`
- `mcp+stdio:./deployment`
- another scheme registered by a shipped/installed adapter

The scheme is the consumer's transport choice. It is not part of the product contract.

### Ask

```python
result = client.ask(
    parameters={"revenue_threshold": 1_000_000},
    as_of=None,
)
```

Signature:

```python
ProductClient.ask(
    parameters: Mapping[str, Any],
    as_of: datetime | None = None,
) -> Result
```

`parameters` is required even when empty. An empty mapping means the class needs no additional parameter; it is not equivalent to forgetting to supply the argument.

For reproducible examples, pass an explicit timezone-aware `as_of`.

### Qualified-baseline clock note

At this qualified baseline, the shipped client transports resolve `as_of=None` client-side before sending the request. The served vessel still reports the graph snapshot/decision evidence used.

For documentation, tests, or exact reproduction, prefer an explicit timezone-aware instant.

## Result

Always branch first:

```python
if result.refused:
    print(result.refusal.reason)
    print(result.replay_ref)
else:
    print(result.payload)
    print(result.debt)
    print(result.content_address)
    print(result.lineage)
    print(result.expires_at)
```

### Readable on served or refused results

- `refused`
- `refusal`
- `product_id`
- `parameters`
- `temporal_boundary`
- `replay_ref`

### Served-only guarded fields

- `payload`
- `debt`
- `content_address`
- `lineage`
- `expires_at`

Reading a served-only field after a refusal raises `RefusedResultError`. That guard prevents a governed refusal from becoming an accidental empty answer downstream.

## Refusal

`result.refusal` is the SDK's canonical refusal envelope, not a client-side duplicate.

Useful fields include:

- `kind`
- `reason`
- `key`
- `detail`
- request identity
- policy/provenance information where disclosed
- pre-assembly lineage where applicable
- replay reference through the result

Disclosure is governed. A refusal may intentionally omit facts whose presence would itself reveal restricted context.

## Exceptions

### BindingError

The client could not resolve/build a transport binding.

Examples:

- `CCF_BINDING` unset and no explicit binding;
- missing scheme;
- unknown/unregistered scheme.

### TransportError

The wire never spoke correctly.

Examples:

- connection failure;
- invalid/corrupt response;
- response does not answer the sent request;
- content-address mismatch.

A governed refusal is **not** a `TransportError`.

### Validation errors

Malformed caller values can fail before transport. An explicit `as_of` must be timezone-aware.

## MCP-capable harnesses

An agent harness that already speaks MCP can consume a Context Product without importing `ccf` in the harness-side application.

Qualified example:

`examples/hw1-harness-clients`

It includes:

- Google ADK
- Claude Agent SDK
- LangGraph

See the existing Build-with-CCF page `04-using-sdk/consumer/CONSUME_OVER_MCP.md`.

## Best examples

- minimal consumer path: `examples/hw1-companies-over-revenue`
- harness-neutral MCP clients: `examples/hw1-harness-clients`
- normal governed product caller: canonical CP-03 `run.py`

