import sys
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.ticks import (
    SESSION_TICKS, ROLLING_WINDOW_TICKS,
    session_times, brownian_bridge, max_rolling_move_bp,
)


def test_session_is_78_ticks_five_minutes_apart():
    ts = session_times(date(2026, 5, 11))
    assert len(ts) == SESSION_TICKS == 78
    gaps = {(ts[i] - ts[i - 1]).total_seconds() for i in range(1, len(ts))}
    assert gaps == {300.0}, f"non-uniform spacing: {gaps}"


def test_bridge_hits_both_anchors_exactly():
    """The anchor fidelity property. If this breaks, the series is fiction."""
    v = brownian_bridge(4.1000, 4.1500, SESSION_TICKS, seed=7)
    assert len(v) == SESSION_TICKS
    assert v[0] == 4.1000
    assert v[-1] == 4.1500


def test_bridge_is_deterministic_for_a_seed():
    a = brownian_bridge(4.10, 4.15, SESSION_TICKS, seed=7)
    b = brownian_bridge(4.10, 4.15, SESSION_TICKS, seed=7)
    assert a == b, "reload would not reproduce the series"


def test_different_seeds_give_different_paths_but_same_anchors():
    a = brownian_bridge(4.10, 4.15, SESSION_TICKS, seed=7)
    b = brownian_bridge(4.10, 4.15, SESSION_TICKS, seed=8)
    assert a != b
    assert a[0] == b[0] and a[-1] == b[-1]


def test_flat_day_still_anchors():
    v = brownian_bridge(4.10, 4.10, SESSION_TICKS, seed=1)
    assert v[0] == 4.10 and v[-1] == 4.10


def test_rolling_move_on_a_monotone_ramp():
    """A ramp of 1bp per tick moves exactly window_ticks bp per window.

    UNITS, because this is where the first attempt went wrong: values are
    par yield in PERCENT (4.15 == 4.15%), so one basis point is 0.01, NOT
    0.0001. A ramp of 0.0001/tick is 0.01bp/tick and would move 0.18bp per
    90-minute window, not 18bp.
    """
    vals = [4.0 + i * 0.01 for i in range(SESSION_TICKS)]
    got = max_rolling_move_bp(vals, ROLLING_WINDOW_TICKS)
    assert abs(got - ROLLING_WINDOW_TICKS) < 1e-6


def test_rolling_move_is_absolute():
    """A falling market moves too. A signed max would report ~0 here."""
    vals = [4.0 - i * 0.01 for i in range(SESSION_TICKS)]
    got = max_rolling_move_bp(vals, ROLLING_WINDOW_TICKS)
    assert abs(got - ROLLING_WINDOW_TICKS) < 1e-6


def test_a_real_eight_bp_move_reports_eight():
    """Anchor the units to REAL par-yield magnitudes, not a synthetic ramp.

    The 2y par yield moved 4.10 -> 4.18 on real days in the loaded curve.
    That is 8 basis points. A multiplier that is wrong by 100x still passes
    a ramp test tuned to it -- but not this one, because 4.10 and 4.18 are
    numbers the domain fixes, not the test.
    """
    vals = [4.10] * 30 + [4.18] * 48
    got = max_rolling_move_bp(vals, ROLLING_WINDOW_TICKS)
    assert abs(got - 8.0) < 1e-6, f"a real 8bp move reported {got}bp"


def test_one_basis_point_is_zero_point_zero_one():
    """The unit conversion, stated as its own assertion."""
    assert abs(max_rolling_move_bp([4.00, 4.01], 1) - 1.0) < 1e-9


def test_ninety_minute_window_is_eighteen_ticks():
    assert ROLLING_WINDOW_TICKS == 18
    assert ROLLING_WINDOW_TICKS * 5 == 90


def test_full_session_move_is_at_least_the_endpoint_gap():
    """Anchor fidelity restated as a property, over many seeds.

    Named for what it asserts. It does NOT prove a 90-minute window carries
    8bp -- that is a claim about the PATH, and only `validators/intraday.py`
    recomputing from loaded ticks can establish it. This test pins the
    weaker, exact property: the endpoints never drift, whatever the seed.
    """
    for seed in range(50):
        v = brownian_bridge(4.1000, 4.1800, SESSION_TICKS, seed=seed)
        full = abs(v[-1] - v[0]) * 100
        assert full >= 8.0 - 1e-9, f"seed {seed}: endpoints drifted"


if __name__ == "__main__":
    import traceback
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); passed += 1; print(f"  PASS {name}")
            except Exception:
                failed += 1; print(f"  FAIL {name}"); traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
