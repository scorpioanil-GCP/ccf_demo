# Same Product, Two Transports

The client abstraction is easiest to understand by holding everything constant except the transport.

Use the qualified HW-1 consumer example.

## In process

```bash
make venv
make example-hw1-seed

CCF_BINDING="inprocess:examples/hw1-companies-over-revenue/deployment" \
.venv/bin/python examples/hw1-companies-over-revenue/consume.py \
  --min-revenue 1000000000 \
  --as-of 2026-08-01T00:00:00+00:00
```

## MCP stdio

```bash
CCF_BINDING="mcp+stdio:examples/hw1-companies-over-revenue/deployment" \
.venv/bin/python examples/hw1-companies-over-revenue/consume.py \
  --min-revenue 1000000000 \
  --as-of 2026-08-01T00:00:00+00:00
```

## What should remain identical

The business question is the same.

The product is the same.

The result contract is the same.

For the pinned demonstration question, the qualified example asserts transport parity for the governed result/content identity.

## What changed

Only `CCF_BINDING`.

That is the client abstraction's central promise:

> **same client intent, different transport, same Context Product contract**

## Validate

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest \
  tests/examples/test_hw1_two_transports.py \
  tests/examples/test_hw1_readme_expected_output.py -q
```

## Next

[Consume the same product from three agent frameworks →](04-agent-harnesses.md)
