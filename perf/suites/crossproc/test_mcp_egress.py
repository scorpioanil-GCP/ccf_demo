"""MCP egress round-trip benchmark (PERF-03; D-15/D-18/D-20).

Times one synchronous ``McpResourceClient.read_text`` of a real gated
Context Product served by a real ``/runtime`` egress server in a separate
OS process over 127.0.0.1. Startup and warm-up are excluded by the
session fixture; 50 rounds stabilize the median, and the crossproc suite's
looser 25% default in ``perf/thresholds.toml`` (D-20) absorbs localhost
scheduler noise.
"""

from __future__ import annotations

from typing import Any

from ccf.products.contract import ContextProductContract

from .conftest import CrossProcessEndpoints

#: Timed rounds per benchmark: ≥50 round-trips so the median is stable
#: (research Pattern 4); warm-up rounds are on top of the fixture's own.
ROUNDS = 50
WARMUP_ROUNDS = 5


def test_mcp_egress_roundtrip(
    benchmark: Any, crossproc_endpoints: CrossProcessEndpoints
) -> None:
    endpoints = crossproc_endpoints

    def roundtrip() -> str:
        return endpoints.mcp_client.read_text(endpoints.product_address)

    over_mcp = benchmark.pedantic(
        roundtrip, rounds=ROUNDS, iterations=1, warmup_rounds=WARMUP_ROUNDS
    )

    # Correctness: the returned payload is the typed product, not a stub.
    product = ContextProductContract.model_validate_json(over_mcp)
    assert product.tenant_id == endpoints.expected_tenant
    assert product.schema_name == endpoints.expected_schema_name
    assert product.lineage.operators_invoked
    assert product.payload["entity_count"] == (
        endpoints.product.payload["entity_count"]
    )
