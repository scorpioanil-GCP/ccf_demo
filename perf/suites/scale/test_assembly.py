"""Assembly scale curve over the rung ladder (PERF-02; D-26).

Times the L1→L2 ingestion loop — ``handle.worker.ingest`` per envelope,
the single-writer path — against a **fresh graph per round**: the pedantic
``setup`` callable boots a new SQLite fabric each round, and envelope
generation happens once, outside every timed region. Only the ingest loop
is inside the clock.

Explicit rounds, iterations=1 (Pitfall 3: never auto-calibrate a
seconds-long callable). Timing judgments live only in ``perf/gate.py``.
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any

import pytest

from perf.conftest import boot_fabric
from perf.suites.scale.conftest import ASSEMBLY_ROUNDS, SCALE_RUNGS
from perf.synth.generator import generate_events

if TYPE_CHECKING:
    from ccf.boot import FabricHandle


def _ingest_all(handle: "FabricHandle", envelopes: Any) -> "FabricHandle":
    for envelope in envelopes:
        handle.worker.ingest(envelope)
    return handle


@pytest.mark.parametrize("rung", SCALE_RUNGS)
def test_assembly_scale(benchmark, rung: int, tmp_path) -> None:
    # Generation is deterministic and happens once, outside the clock.
    envelopes = generate_events(rung)
    counter = itertools.count()
    handles: list["FabricHandle"] = []

    def fresh_boot() -> tuple[tuple[Any, ...], dict[str, Any]]:
        handle = boot_fabric(
            database_path=tmp_path / f"assembly-{rung}-{next(counter)}.sqlite3"
        )
        handles.append(handle)
        return (handle, envelopes), {}

    try:
        benchmark.pedantic(
            _ingest_all,
            setup=fresh_boot,
            rounds=ASSEMBLY_ROUNDS[rung],
            iterations=1,
        )
        # Correctness sanity: the last round's fabric actually assembled
        # graph state from the stream (never a timing assert).
        from perf.suites.common import instant, load_artifact

        control = load_artifact("controlplane.yaml")
        ontology = load_artifact("ontology.yaml")
        view = handles[-1].reader.as_of(
            tenant_id=ontology["tenant_id"],
            at=instant(control["decision"]["temporal_boundary"]),
        )
        assert len(view.entities) == rung
        assert len(view.relationships) >= 1
    finally:
        for handle in handles:
            handle.close()
