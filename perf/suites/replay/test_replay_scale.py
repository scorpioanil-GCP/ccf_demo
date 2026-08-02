"""Replay-at-scale: byte-exact per rung + curve-shape exponent (PERF-03).

The ladder (D-16): per rung of ``LADDER`` decision-history records the store
holds, (a) a HARD byte-exact reproduction assert through the full replay
engine (example 06's resolution flow — record resolved at its content
address, bindings at their pinned versions, projection re-executed against
the recorded snapshot, product rehydrated and hash-checked), then (b) a
pedantic-mode timing of exactly that replay. Population is session-scoped
(``conftest.history_store_factory``), so the timed callable never pays it.

After the ladder, ``test_curve_shape`` fits ``t = a * n^b`` over the three
rung medians (log-log least squares, stdlib ``math`` only) and asserts
``b <= 1.0 + EPS`` — the documented-linear bound that is PERF-03's primary
evidence (D-16/D-21; the 15% median gate is secondary). The fitted exponent
is written to ``perf/results/replay.curve.json`` AND attached to each
benchmark's ``extra_info`` (as ``history_records``) so Phase 14's
PERFORMANCE.md can cite it from the results artifacts.

Rung-ladder flex (D-07, recorded in the plan SUMMARY): the history counts
are exactly 1k/10k/100k records, sourced from
``decision_stream(100_000)`` (10k base records, ~6s to generate); the 100k
rung replicates them with a deterministic replica index rather than
generating ``decision_stream(1_000_000)``, whose 1M-entity topology takes
>5 minutes to build and blows the D-25 budget outright.

No absolute-time asserts anywhere — the exponent bound is a shape assert,
the ruled exception (D-16/D-21).
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.replay.engine import replay

from .conftest import PopulatedStore, RecordedDecision

#: The decision-record ladder (D-16): three decades of history size.
#:
#: Smoke knob (D-04, plan 11-05): under ``CCF_PERF_SMOKE=1`` (the always-on
#: bitrot smoke, run with ``--benchmark-disable``) the ladder collapses to
#: its smallest rung — the byte-exact reproduction assert still runs, only
#: the curve fit is skipped (it needs every rung's median).
_FULL_LADDER = (1_000, 10_000, 100_000)
LADDER = (
    _FULL_LADDER[:1]
    if os.environ.get("CCF_PERF_SMOKE") == "1"
    else _FULL_LADDER
)

#: Documented tolerance on the fitted exponent: ``b <= 1.0 + EPS`` is the
#: documented-linear bound (D-16/D-21). 0.1 absorbs three-point fit noise
#: without letting a super-linear trend through a decade ladder.
EPS = 0.1

#: Where the fitted curve lands for Phase 14's PERFORMANCE.md.
CURVE_ARTIFACT = (
    Path(__file__).resolve().parents[2] / "results" / "replay.curve.json"
)

#: Rung medians accumulated by the benchmark tests, read by the fit test.
_MEDIANS: dict[int, float] = {}


@pytest.mark.parametrize("history_records", LADDER)
def test_replay_at_scale(
    benchmark: Any,
    recorded_decision: RecordedDecision,
    history_store_factory: Any,
    history_records: int,
) -> None:
    populated: PopulatedStore = history_store_factory(history_records)
    assert populated.count == history_records

    def replay_once() -> Any:
        return replay(
            record_address=populated.record_address,
            store=populated.store,
            reader=recorded_decision.reader,
            control_plane=recorded_decision.registry,
            environment=recorded_decision.environment,
        )

    # (a) Deterministic correctness FIRST (threat T-11-11): the replayed
    # product reproduces the original byte-for-byte through the canonical
    # serializer. A hard assert, not a benchmark.
    outcome = replay_once()
    assert canonical_bytes(outcome.product) == canonical_bytes(
        recorded_decision.original_product
    )
    assert (
        outcome.product_content_address
        == recorded_decision.record.content_generation_path.product_content_address
    )

    # (b) The timing, over exactly the asserted path.
    benchmark.extra_info["history_records"] = history_records
    benchmark.pedantic(replay_once, rounds=3, iterations=1, warmup_rounds=1)
    # Under --benchmark-disable (the D-04 smoke) the fixture runs the
    # callable once and records no stats — nothing to feed the curve fit.
    if benchmark.stats is not None:
        _MEDIANS[history_records] = benchmark.stats.stats.median


def test_curve_shape(recorded_decision: RecordedDecision) -> None:
    """Fit ``t = a * n^b`` over the rung medians; assert documented-linear."""
    if len(LADDER) < 3 or not _MEDIANS:
        pytest.skip(
            "curve fit needs the full ladder with timing enabled — "
            "skipped under the CCF_PERF_SMOKE / --benchmark-disable bitrot run"
        )
    assert sorted(_MEDIANS) == sorted(LADDER), (
        "curve fit needs every ladder rung's median; got "
        f"{sorted(_MEDIANS)} — run the whole module, not a single rung"
    )
    points = [
        (math.log(rung), math.log(_MEDIANS[rung])) for rung in sorted(LADDER)
    ]
    n = len(points)
    mean_x = sum(x for x, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    exponent_b = sum(
        (x - mean_x) * (y - mean_y) for x, y in points
    ) / sum((x - mean_x) ** 2 for x, _ in points)
    intercept_a = math.exp(mean_y - exponent_b * mean_x)

    CURVE_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    CURVE_ARTIFACT.write_text(
        json.dumps(
            {
                "model": "t = a * n^b over decision-history size n",
                "exponent_b": exponent_b,
                "coefficient_a_seconds": intercept_a,
                "eps": EPS,
                "bound": "b <= 1.0 + eps (documented-linear, D-16/D-21)",
                "medians_seconds": {
                    str(rung): _MEDIANS[rung] for rung in sorted(LADDER)
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert exponent_b <= 1.0 + EPS, (
        f"replay time grows super-linearly with history size: fitted "
        f"b={exponent_b:.4f} > {1.0 + EPS} (medians {_MEDIANS})"
    )
