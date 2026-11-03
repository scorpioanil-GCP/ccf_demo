# Hello World of CCF — Ask One Context Product

> **Current execution baseline:** SDK `v1.0.2@5f85b389`. Follow [setup and configuration](../../examples/CONFIGURATION.md); dated qualification results below retain their original scope.

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**Source:** `examples/hw1-companies-over-revenue`

## The whole client idea first

Before setup or internals, this is the mental model:

```python
from ccf.client import ProductClient

client = ProductClient.for_product("...")
result = client.ask(parameters={...})

if result.refused:
    print(result.refusal.reason)
else:
    print(result.payload)
```

A Context Product is something the client **asks**. The client does not assemble it.

## Why this example exists

This is the cleanest consumer example in the qualified SDK.

The developer learns only:

1. choose a product;
2. choose a transport binding;
3. ask a question;
4. branch on governed refusal vs served result;
5. use the payload and evidence.

The consumer does **not** learn producer deployment, Control Plane, graph, operator, or projection internals.

## The question

> Which companies have revenue over the threshold I supply?

The important part is not the row filter. It is that the answer also carries measured Context Debt, content identity, expiry and governed decision evidence.

## Prerequisites

From the SDK repository root:

```bash
make venv
```

The example ships declared seed input. Populate a private deployment copy:

```bash
make example-hw1-seed
```

## Files to read

Read only these first:

1. `examples/hw1-companies-over-revenue/consume.py`
2. `examples/hw1-companies-over-revenue/README.md`

Do **not** begin in `deployment/`. The entire point is that a consumer should not need to understand it.

## Run it — in process

```bash
CCF_BINDING="inprocess:examples/hw1-companies-over-revenue/deployment" \
.venv/bin/python examples/hw1-companies-over-revenue/consume.py \
  --min-revenue 1000000000 \
  --as-of 2026-08-01T00:00:00+00:00
```

Or use the Make target, which seeds first:

```bash
make example-hw1
```

## Run it — MCP stdio

The same client code, same product, same question:

```bash
CCF_BINDING="mcp+stdio:examples/hw1-companies-over-revenue/deployment" \
.venv/bin/python examples/hw1-companies-over-revenue/consume.py \
  --min-revenue 1000000000 \
  --as-of 2026-08-01T00:00:00+00:00
```

Or:

```bash
make example-hw1-mcp
```

## What you should observe

Both transports should return the same governed answer and the same content address for the same pinned question.

The output includes:

- companies matching the threshold;
- count assembled;
- Context Debt and routing signal;
- content address;
- replay reference;
- expiry.

Only `CCF_BINDING` changes between the two transport demonstrations.

## Why the example pins as_of

For documentation, a fixed instant makes the result reproducible.

An ordinary caller may omit `as_of`, but a document quoting an exact content address should not rely on “now.”

Use a timezone-aware instant.

## Change the question

Try another threshold:

```bash
CCF_BINDING="inprocess:examples/hw1-companies-over-revenue/deployment" \
.venv/bin/python examples/hw1-companies-over-revenue/consume.py \
  --min-revenue 2000000000 \
  --as-of 2026-08-01T00:00:00+00:00
```

The answer changes and the content address should change because the caller's question is part of the determination.

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest \
  tests/examples/test_hw1_two_transports.py \
  tests/examples/test_hw1_readme_expected_output.py \
  tests/examples/test_hw1_empty_fabric_refusal.py -q
```

The qualified tests verify:

- transport parity;
- documented output;
- behavior on an unseeded/empty fabric;
- that a computed-empty answer is distinguished from “the system did not answer.”

## What this proves

- Consumer API is transport-neutral at the result contract.
- The producer side stays invisible to ordinary client code.
- A Context Product carries governed evidence beyond the business payload.
- A request parameter changes content identity.

## What it does not prove

- How a Context Product is assembled.
- How to author a new product.
- That in-process or MCP stdio is the required production transport.

## Cowork lesson

This is the right source for generating **consumer code**.

For **producer code**, do not extrapolate from this opaque deployment. Use the paved-road Context Product guides instead.
