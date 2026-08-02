"""A2A/peering round-trip benchmark (PERF-03; D-15/D-18/D-20).

Times one ``TypedHttpWire.emit`` of a signed canonical Context Product to a
real peering endpoint hosted by the server child in a separate OS process
over 127.0.0.1 — the full carriage: canonical serialization, HTTP POST,
far-side framing checks, acknowledged receipt. The 25% crossproc default
(D-20) gates the median once a baseline exists.
"""

from __future__ import annotations

from typing import Any

from ccf.peering.protocol import EmitReceipt
from ccf.products.contract import ContextProductContract

from .conftest import CrossProcessEndpoints

#: Timed rounds per benchmark: ≥50 round-trips so the median is stable
#: (research Pattern 4); warm-up rounds are on top of the fixture's own.
ROUNDS = 50
WARMUP_ROUNDS = 5


def test_peering_roundtrip(
    benchmark: Any, crossproc_endpoints: CrossProcessEndpoints
) -> None:
    endpoints = crossproc_endpoints

    def roundtrip() -> EmitReceipt:
        return endpoints.wire.emit(
            peer=endpoints.peer, signed=endpoints.signed
        )

    receipt = benchmark.pedantic(
        roundtrip, rounds=ROUNDS, iterations=1, warmup_rounds=WARMUP_ROUNDS
    )

    # Correctness: the far side acknowledged this exact carriage.
    assert isinstance(receipt, EmitReceipt)
    assert receipt.content_address == endpoints.signed.content_address()
    assert receipt.wire_message_id

    # Consumer-side shape check (example 04's discipline): the canonical
    # bytes the envelope carries validate as the typed Context Product
    # Contract — the stable layer the wire exists to carry.
    carried = ContextProductContract.model_validate_json(
        endpoints.signed.canonical_payload().decode("utf-8")
    )
    assert carried.tenant_id == endpoints.expected_tenant
    assert carried.schema_name == endpoints.expected_schema_name
