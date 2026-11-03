"""Interpolate a 5-minute intraday path between two REAL published closes.

Design §3.1. The two endpoints are read unmodified from `benchmark_curve`, so
the day-over-day move is real and only the within-day path is engineered.
That split is the whole provenance claim, and `anchor fidelity` -- first and
last tick equal the published values exactly -- is what keeps it true. A
bridge that merely starts and ends "close to" the anchors has quietly become
fiction.

Determinism matters as much: reloads must reproduce the series, so the path
is a function of (open, close, n, seed) with no ambient randomness.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta, timezone

#: A 6.5-hour session at 5-minute granularity.
SESSION_TICKS = 78

#: 90 minutes, the interval the spec's Latency Poisoned counterfactual names.
ROLLING_WINDOW_TICKS = 18

#: US cash-market session in UTC (09:30-16:00 ET, standard offset).
SESSION_OPEN_UTC = time(13, 30)


def session_times(day: date) -> list[datetime]:
    """78 UTC timestamps, 5 minutes apart, starting 13:30Z."""
    start = datetime.combine(day, SESSION_OPEN_UTC, tzinfo=timezone.utc)
    return [start + timedelta(minutes=5 * i) for i in range(SESSION_TICKS)]


def brownian_bridge(open_v: float, close_v: float, n: int,
                    seed: int) -> list[float]:
    """A Brownian bridge from `open_v` to `close_v` in `n` points.

    Both endpoints are returned EXACTLY -- the bridge correction is applied
    in full, and the endpoints are then reassigned rather than left to
    floating-point drift.
    """
    if n < 2:
        raise ValueError("need at least two ticks")

    rng = random.Random(seed)

    # Scale increments to the endpoint gap so a volatile day looks volatile
    # and a quiet day does not. A floor keeps a flat day from being a
    # straight line, which no real session is.
    gap = abs(close_v - open_v)
    step_sd = max(gap / (n ** 0.5), 0.0004)   # >= 0.04bp per tick

    walk = [0.0]
    for _ in range(n - 1):
        walk.append(walk[-1] + rng.gauss(0.0, step_sd))

    # Bridge correction: subtract the linear drift of the raw walk, then add
    # the linear path from open to close.
    drift = walk[-1]
    out = []
    for i, w in enumerate(walk):
        frac = i / (n - 1)
        bridged = w - drift * frac
        out.append(open_v + (close_v - open_v) * frac + bridged)

    # Exact anchors. Do not rely on the arithmetic above landing on them.
    out[0] = open_v
    out[-1] = close_v
    return out


def max_rolling_move_bp(values: list[float], window_ticks: int) -> float:
    """Largest ABSOLUTE move, in basis points, over any window of that width.

    Absolute, because a market that falls 8bp has moved 8bp. A signed max
    would report ~0 for a falling session and silently fail the condition.
    Inputs are percent (4.15 == 4.15%), so one basis point is 0.01.
    """
    if len(values) <= window_ticks:
        return abs(values[-1] - values[0]) * 100 if values else 0.0
    best = 0.0
    for i in range(len(values) - window_ticks):
        move = abs(values[i + window_ticks] - values[i]) * 100
        if move > best:
            best = move
    return best

# UNITS -- do not "fix" the 100 above to satisfy a failing test. Inputs are
# par yield in PERCENT: 4.15 means 4.15%, and one basis point is 0.01. So
# percent-difference x 100 = basis points, and a real 4.10 -> 4.18 move
# reports 8.0. A multiplier of 10000 makes that same move report 800, which
# passes every threshold check in the estate and makes the product's headline
# condition meaningless while showing green.
