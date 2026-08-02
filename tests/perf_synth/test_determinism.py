"""Always-on determinism guard for the perf synthetic generator (D-08).

The pinned literals below were produced by running the generator once with
``PERF_SEED = 20260801`` and committing the observed values. **Changing any
generator logic (or the seed) REQUIRES updating these pins in the same
commit** — a mismatch here is the drift alarm working as designed, not a
flaky test.

This module is the cheap, always-on slice: rungs 1k and 10k only. The 100k
rung is exercised exclusively in the ``perf/`` tree (D-04) so ``pytest
tests/`` stays fast.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from perf.synth.generator import (
    PERF_SEED,
    decision_stream,
    generate_events,
    rung_checksum,
    rung_shape,
)

#: Pinned per-rung (entity_count, edge_count, observation_count) — D-08.
PINNED_SHAPES = {
    1_000: (1_000, 3_000, 5_090),
    10_000: (10_000, 30_000, 50_749),
}

#: Pinned per-rung sha256 over sorted entity URIs + edge triples — D-08.
PINNED_CHECKSUMS = {
    1_000: "6c79a33f8789f7653df24d95ec80c2d97fd1dd7a606c832a822792d956c30a77",
    10_000: "24ff0e669b456312e3d67d6467d4ce2dac9c7bf2ff8be612f64b82dda6b355df",
}


def test_seed_is_the_documented_one() -> None:
    assert PERF_SEED == 20260801


@pytest.mark.parametrize("rung", sorted(PINNED_SHAPES))
def test_pinned_shape_and_checksum(rung: int) -> None:
    """Test 1: shape and checksum equal the committed pins (drift alarm)."""
    assert rung_shape(rung) == PINNED_SHAPES[rung]
    assert rung_checksum(rung) == PINNED_CHECKSUMS[rung]
    # And a second invocation is byte-identical (determinism, not caching by
    # accident: the checksum is recomputed over the same topology).
    assert rung_checksum(rung) == PINNED_CHECKSUMS[rung]


def _stable(envelopes: tuple) -> list[str]:  # type: ignore[type-arg]
    return [
        json.dumps(
            {
                "envelope_id": e.envelope_id,
                "observed_time": e.observed_time.isoformat(),
                "payload": dict(sorted(e.raw_payload.items())),
            },
            sort_keys=True,
        )
        for e in envelopes
    ]


def test_envelope_stream_is_deterministic() -> None:
    """Test 2: two generations yield identical envelope sequences."""
    first = generate_events(1_000)
    second = generate_events(1_000)
    assert len(first) == len(second)
    assert _stable(first[:10]) == _stable(second[:10])
    assert _stable(first[-10:]) == _stable(second[-10:])


def test_decision_stream_deterministic_and_cross_referenced() -> None:
    """Test 3: decision stream is deterministic and references real URIs."""

    def checksum(records: tuple) -> str:  # type: ignore[type-arg]
        return hashlib.sha256(
            json.dumps(list(records), sort_keys=True).encode("utf-8")
        ).hexdigest()

    first = decision_stream(1_000)
    assert checksum(first) == checksum(decision_stream(1_000))

    from perf.synth.generator import _topology

    uris = {e.uri for e in _topology(1_000).hubs + _topology(1_000).tails}
    assert all(record["entity_uri"] in uris for record in first)


def test_fabric_fixture_boots_and_ingests_rung_1k(
    tmp_path: Path,
) -> None:
    """Test 4: a real fabric ingests rung 1k via handle.worker.ingest (L2)."""
    import yaml

    from perf.conftest import ARTIFACTS, build_fabric

    control = yaml.safe_load(
        (ARTIFACTS / "controlplane.yaml").read_text(encoding="utf-8")
    )
    ontology = yaml.safe_load(
        (ARTIFACTS / "ontology.yaml").read_text(encoding="utf-8")
    )
    handle = build_fabric(rung=1_000, database_path=tmp_path / "rung-1k.sqlite3")
    try:
        from datetime import UTC, datetime

        boundary = control["decision"]["temporal_boundary"]
        at = (
            boundary
            if isinstance(boundary, datetime)
            else datetime.fromisoformat(str(boundary).replace("Z", "+00:00"))
        )
        if at.tzinfo is None:
            at = at.replace(tzinfo=UTC)
        view = handle.reader.as_of(tenant_id=ontology["tenant_id"], at=at)
        assert len(view.entities) == PINNED_SHAPES[1_000][0]
    finally:
        handle.close()
