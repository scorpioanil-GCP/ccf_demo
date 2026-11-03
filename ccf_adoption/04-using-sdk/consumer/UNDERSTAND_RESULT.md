# Understand `Result`: served answer, refusal, and evidence

## Why this page matters

The most important consumer distinction in CCF is not success vs exception. It is:

- **served answer** — the product was assembled and delivered;
- **governed refusal** — the fabric evaluated the request and the governed answer was no;
- **caller error** — the question was malformed before transport;
- **binding / transport failure** — the wire never successfully spoke.

Treating those four states as one generic error path defeats the contract.

## Served result

A served result exposes product-specific payload plus evidence about the delivered Context Product.

Common fields include:

- `payload`
- `debt`
- `content_address`
- `lineage`
- `replay_ref`
- `expires_at`

The business payload changes by product. The evidence model does not.

```python
if not result.refused:
    use(result.payload)
    audit(result.content_address, result.replay_ref)
```

## Governed refusal

A refusal is a value, not an exception.

```python
if result.refused:
    log(result.refusal.reason)
    if result.refusal.key is not None:
        log(result.refusal.key)
```

The refusal tells the caller that the governed contract ran and did not authorize or admit a served product.

Examples of why a product might refuse can include policy, freshness, debt, entitlement, contract, or product-specific gate conditions. The consumer handles the refusal; it does not need to recreate the producer's gate logic.

## A refusal is still auditable

On the current SDK baseline, `replay_ref` is readable on either half when the producer emitted one. Refusal itself is treated as a decision worthy of replay rather than as a second-class outcome.

```python
if result.refused:
    print(result.replay_ref)
```

## Served-only fields are guarded

A refused result does not silently return `None` for fields that only exist after successful assembly.

The current guarded set is:

- `payload`
- `debt`
- `content_address`
- `lineage`
- `expires_at`

If caller code ignores `result.refused` and tries to read one of those fields, the SDK raises. This is deliberate: a silent empty value would make it impossible downstream to distinguish “the product returned no rows” from “the product was never served.”

## Fields readable on either half

The current client model keeps the request identity and outcome branch available:

- `refused`
- `refusal`
- `product_id`
- `parameters`
- `temporal_boundary`
- `replay_ref`

This is the information a caller can use to route, log, explain, or escalate the governed outcome.

## The exception taxonomy

### Governed refusal

**Do not catch an exception.** Branch on `result.refused`.

### Caller error

Malformed caller input can fail before transport. For example, a naive `datetime` supplied as `as_of` is invalid because the SDK does not silently assume UTC.

This is caller negligence, not an outage. Fix the question rather than retrying it.

### `BindingError`

The client could not resolve where or how to reach the product — for example, no binding was supplied or a scheme has no registered adapter.

### `TransportError`

The wire never successfully delivered a valid answer: connection failure, transport-level mismatch, corrupted/unverifiable return, and related wire failures.

A governed refusal must never be converted into `TransportError`.

## Recommended application shape

```python
from ccf.client import BindingError, ProductClient, TransportError

try:
    client = ProductClient.for_product("domain.product.v1")
    result = client.ask(parameters={"question_axis": "value"})
except BindingError as exc:
    handle_configuration_error(exc)
except TransportError as exc:
    handle_transport_failure(exc)
else:
    if result.refused:
        handle_governed_refusal(result.refusal, result.replay_ref)
    else:
        use(result.payload)
```

Validation errors caused by malformed caller arguments should be handled as caller bugs/validation failures rather than transport retries.

## Design principle

**The fabric saying “no” is normal governed behavior. The wire failing to speak is exceptional.**

That distinction should remain visible in application code, logs, monitoring, and user experience.
