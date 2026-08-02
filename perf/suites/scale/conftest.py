"""Scale-suite ladder, rounds, and per-rung fabric fixtures (PERF-02).

**D-07 rung flex (measured, 2026-08-01):** L2 ingestion runs at roughly
5 ms/envelope on the reference SQLite path — the pinned 1k rung
(8,090 envelopes) assembles in ~42 s. At that rate the 10k rung is
~7 min/round and 100k is over an hour, so the D-25 3-minute suite budget
cannot hold the pinned (1k, 10k, 100k) ladder for *assembly*. Per D-07 the
ladder flexes down: the scale suite runs rungs **(500, 1_000)** for both
curve families.

Why 500 and not a lower decade: the generator requires
``hub_count × tail_count >= K_AVG_DEGREE × rung`` unique (hub, tail)
pairs (each pair admits exactly one relationship type), and hubs are 1% of
entities — below ~400 entities the unique-edge sampler cannot terminate.
500 is the smallest comfortable rung (5 hubs × 495 tails = 2,475 possible
edges against a 1,500-edge target).

These rung values become baseline keys (Pitfall 6) — do not change them
without re-baselining; widening the ladder back up is 11-05's budget call
once ingestion throughput improves.

The generator is deterministic at any rung (seed = PERF_SEED + rung), so
the 500 rung is exactly as reproducible as the pinned ones.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Iterator

import pytest

from perf.conftest import build_fabric

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

#: The flexed ladder (D-07; see module docstring). Parametrized benchmark
#: IDs — e.g. ``test_assembly_scale[500]`` — derive from these values.
#:
#: Smoke knob (D-04, plan 11-05): the always-on bitrot smoke test sets
#: ``CCF_PERF_SMOKE=1`` and runs with ``--benchmark-disable`` — each callable
#: executes exactly once as a plain test, and the ladder collapses to its
#: smallest rung so always-on CI stays fast. Rung IDs are unchanged (they
#: remain baseline keys, Pitfall 6); the knob only trims which params run.
_FULL_RUNGS = (500, 1_000)
SCALE_RUNGS = (
    _FULL_RUNGS[:1] if os.environ.get("CCF_PERF_SMOKE") == "1" else _FULL_RUNGS
)

#: Explicit pedantic rounds per rung for the *assembly* curve (D-25 budget
#: split; Pitfall 3). Assembly is ~5 ms/envelope, so the 1k rung runs two
#: rounds to keep the suite inside the ~3-minute budget.
ASSEMBLY_ROUNDS = {500: 3, 1_000: 2}

#: Rounds for the read-only *projection* curve (sub-second callables).
PROJECTION_ROUNDS = 3


def _scale_fixture(rung: int) -> Any:
    @pytest.fixture(scope="session", name=f"scale_fabric_{rung}")
    def fixture(
        tmp_path_factory: pytest.TempPathFactory,
    ) -> Iterator["FabricHandle"]:
        handle = build_fabric(
            rung=rung,
            database_path=tmp_path_factory.mktemp("perf-scale")
            / f"rung-{rung}.sqlite3",
        )
        try:
            yield handle
        finally:
            handle.close()

    return fixture


scale_fabric_500 = _scale_fixture(500)
scale_fabric_1000 = _scale_fixture(1_000)


@pytest.fixture(scope="session")
def scale_fabric(request: pytest.FixtureRequest) -> "FabricHandle":
    """Indirect per-rung fixture: ``request.param`` is the rung."""
    handle: "FabricHandle" = request.getfixturevalue(
        f"scale_fabric_{request.param}"
    )
    return handle
