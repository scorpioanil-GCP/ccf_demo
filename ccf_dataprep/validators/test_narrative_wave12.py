"""Wave 12 Task 13 -- the two break populations, and the one that inverts.

RULING F6: this suite's own file. `test_part43.py` already tests
`generators/part43.py`; appending unrelated assertions there would make one
file cover two stops that need to be greppable separately.

Not pytest -- a standalone script with a `__main__` block that counts and
exits non-zero on any failure, matching every other `test_*.py` in
`validators/`.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.narrative_wave12 import (
    SYSTEMS, MATERIALITY, PIP_SIZE, align, classify, pips, build_breaks,
    INVERSION_TRADE_ID, SURVIVOR_TRADE_ID,
)
from datetime import datetime, timezone, timedelta
import random


def test_clock_offsets_are_distinct_and_recorded():
    assert set(SYSTEMS) == {"trading", "settlement", "risk"}
    assert len(set(SYSTEMS.values())) == 3, "offsets must differ to matter"


def test_alignment_removes_a_pure_timing_difference():
    """Two systems, same trade, different observation times, drifting rate.

    Raw comparison sees a difference. Aligned comparison must not.

    NOTE ON THE FIXTURE: `raw_a`/`raw_b` must each be the value a system
    would ACTUALLY have recorded at its own TRUE observation instant --
    that is, at `observed_at - offset_s`, not at the recorded `observed_at`
    label itself. Building `raw_b` from the label (ignoring settlement's
    47s offset) makes the fixture describe a reading no real clock-skewed
    system could produce, and `align()` -- which correctly reverses the
    offset -- then has nothing consistent to reverse. This is the same
    class of mistake the brief warns about generally: a construction that
    LOOKS like it exercises the mechanism but is arithmetically decoupled
    from it.
    """
    as_of = datetime(2026, 8, 19, 17, 0, tzinfo=timezone.utc)
    drift = 0.00002                     # per second
    off_a = SYSTEMS["trading"]
    off_b = SYSTEMS["settlement"]
    t_a = as_of - timedelta(seconds=300)   # trading's recorded observed_at
    t_b = as_of - timedelta(seconds=60)    # settlement's recorded observed_at
    true_a = t_a - timedelta(seconds=off_a)
    true_b = t_b - timedelta(seconds=off_b)
    base = 1.1600
    raw_a = base + drift * (true_a - as_of).total_seconds()
    raw_b = base + drift * (true_b - as_of).total_seconds()
    assert abs(raw_a - raw_b) > 1e-6, "the fixture has no timing difference"

    a = align(raw_a, t_a, off_a, as_of, drift)
    b = align(raw_b, t_b, off_b, as_of, drift)
    assert abs(a - b) < 1e-6, "alignment failed to remove a pure timing gap"


def test_alignment_does_not_erase_a_genuine_difference():
    as_of = datetime(2026, 8, 19, 17, 0, tzinfo=timezone.utc)
    drift = 0.00002
    t = as_of - timedelta(seconds=120)
    a = align(1.1600, t, SYSTEMS["trading"], as_of, drift)
    b = align(1.1900, t, SYSTEMS["risk"], as_of, drift)   # a real 300-pip error
    assert abs(a - b) > 0.01, "alignment swallowed a genuine break"


def test_a_pip_is_not_the_same_size_in_every_pair():
    """RULING F13. The trap: one absolute threshold across six pairs."""
    assert PIP_SIZE["USD/JPY"] == 0.01
    assert PIP_SIZE["EUR/USD"] == 0.0001
    # The SAME raw difference is 5 pips of EUR/USD and 0.05 pips of USD/JPY.
    assert abs(pips("EUR/USD", 0.0005) - 5.0) < 1e-9
    assert abs(pips("USD/JPY", 0.0005) - 0.05) < 1e-9


def test_classification_is_scale_correct_across_pairs():
    """A 3-pip difference is the same BREAK in either pair, despite the
    raw numbers differing by 100x."""
    thr = 2.0
    assert classify("EUR/USD", 1.1600, 1.1603, thr) == "genuine"
    assert classify("USD/JPY", 152.85, 152.88, thr) == "genuine"
    assert classify("EUR/USD", 1.1600, 1.1601, thr) == "within-tolerance"
    assert classify("USD/JPY", 152.85, 152.86, thr) == "within-tolerance"


def test_an_unknown_pair_raises_rather_than_guessing_a_pip_size():
    try:
        pips("XXX/YYY", 0.001)
    except ValueError:
        return
    raise AssertionError("an unknown pair must raise, not assume 0.0001")


def test_the_inversion_trade_is_named():
    assert INVERSION_TRADE_ID, "the inversion case must be identifiable"


def _synthetic_trade_pool(n=58):
    """Minimal enriched trades for `build_breaks` -- pure, no I/O.

    Each trade carries the fields `build_breaks` actually needs: `pair`,
    a true `execution_ts`, an `anchor_rate`, and a `local_drift_per_s`
    (the real per-second secant slope `generate_fx_trades.py` derives from
    the intraday tick path -- here just varied deterministically so the
    mechanism has something nonzero to work with).
    """
    rng = random.Random(4242)
    pairs = list(PIP_SIZE)
    base_ts = datetime(2026, 8, 11, 14, 0, tzinfo=timezone.utc)
    trades = [{
        "trade_id": INVERSION_TRADE_ID,
        "pair": "EUR/USD",
        "execution_ts": base_ts,
        "anchor_rate": 1.1600,
        "local_drift_per_s": 0.0000045,
    }, {
        "trade_id": SURVIVOR_TRADE_ID,
        "pair": "USD/JPY",
        "execution_ts": base_ts,
        "anchor_rate": 152.85,
        "local_drift_per_s": 0.00003,
    }]
    for i in range(n):
        pair = pairs[i % len(pairs)]
        trades.append({
            "trade_id": f"TRD-SYN-{i:04d}",
            "pair": pair,
            "execution_ts": base_ts + timedelta(minutes=i),
            "anchor_rate": 1.2 if pair != "USD/JPY" else 150.0,
            "local_drift_per_s": rng.uniform(1e-6, 8e-5) * rng.choice([1, -1]),
        })
    return trades


def test_build_breaks_produces_named_cases_with_correct_mix():
    """The end-to-end property: build_breaks() must actually construct the
    inversion and the survivor, not merely export their trade ids.
    """
    trades = _synthetic_trade_pool()
    rng = random.Random(99)
    breaks = build_breaks(trades, rng)

    assert 55 <= len(breaks) <= 65, f"expected ~60 breaks, got {len(breaks)}"
    n_timing = sum(1 for b in breaks if b["break_type"] == "timing")
    n_genuine = sum(1 for b in breaks if b["break_type"] == "genuine")
    assert n_timing + n_genuine == len(breaks)
    ratio = n_timing / len(breaks)
    assert 0.55 <= ratio <= 0.78, f"expected ~2/3 timing, got {ratio:.2f}"

    inversion = next(b for b in breaks if b["trade_id"] == INVERSION_TRADE_ID)
    assert inversion["classification_raw"] == "genuine"
    assert inversion["classification_aligned"] == "within-tolerance"

    survivor = next(b for b in breaks if b["trade_id"] == SURVIVOR_TRADE_ID)
    assert survivor["classification_raw"] == "genuine"
    assert survivor["classification_aligned"] == "genuine"

    # variance-decomposition closure: the pips explained by timing plus
    # what's left over after alignment must reconstitute the raw total.
    for b in (inversion, survivor):
        closure = b["timing_component_pips"] + b["aligned_diff_pips"]
        assert abs(closure - b["raw_diff_pips"]) < 1e-6, (b["trade_id"], closure)


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
