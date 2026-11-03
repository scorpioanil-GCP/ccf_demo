"""The engineered break populations, and the one break that must invert.

Design §3.4. Three systems each revalue the same FX trade internally
correctly, at their own observation time -- the trading system at execution,
the settlement system after post-affirmation processing, the risk system at
its own snapshot. Comparing their numbers RAW treats that timing gap as an
error. `align()` is the parameter carrying the product's whole lesson: it
projects a system's reading, using its recorded clock offset and the local
rate drift, to a single common `as_of` instant. The dataset must contain (at
least):

    raw comparison      -> variance exceeds materiality -> "genuine"
    clock-aligned        -> variance collapses            -> "timing"

for one named case (the inversion), and a second named case where alignment
changes nothing, so the product is not merely explaining every break away
(the survivor).

§7.5 is the trap: a break that flips because the materiality threshold
happens to fall between two arbitrary numbers is a coincidence wearing the
argument's costume. The construction below never leans on threshold
placement to produce the flip -- see `_timing_break`'s docstring for why the
inversion is arithmetically INEVITABLE rather than lucky, which is also why
a downstream validator can assert variance-decomposition closure
(timing-attributable + residual == total) rather than merely asserting a
flip occurred.

PURE MODULE. No filesystem, no network, no database -- every number these
functions need (the true execution instant, the anchor rate, the local
per-second drift) arrives already computed, in `trades`, from
`generate_fx_trades.py`, which is the one place allowed to read the
intraday tick artifact this drift actually comes from.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

#: System name -> recorded clock offset in seconds. Loaded to Fluree as
#: data; the reconciliation must READ these from the store, never hardcode
#: them -- this dict is the one place they are declared.
SYSTEMS: dict[str, int] = {
    "trading": 0,
    "settlement": 47,
    "risk": -112,
}

#: The designed inversion case: raw comparison classifies "genuine",
#: clock-aligned comparison classifies "timing". Named so a validator can
#: find it -- but the validator should RECOMPUTE the flip rather than
#: trusting this constant.
INVERSION_TRADE_ID = "TRD-W12-0417"

#: The genuine break that SURVIVES alignment -- a real booking error that
#: no amount of clock-and-drift correction explains away.
SURVIVOR_TRADE_ID = "TRD-W12-0288"


def align(value: float, observed_at: datetime, offset_s: int,
          as_of: datetime, drift_per_s: float) -> float:
    """Project a system's observed value to the common `as_of` point.

    The system's clock reads `offset_s` seconds away from true, so its
    recorded observation actually happened at `observed_at - offset_s`.
    Projecting forward to `as_of` applies the rate drift over the REAL
    elapsed interval between that true instant and `as_of` -- never over
    the recorded (possibly mislabeled) interval.
    """
    true_observed = observed_at - timedelta(seconds=offset_s)
    elapsed = (as_of - true_observed).total_seconds()
    return value + drift_per_s * elapsed


#: RULING F13 -- FX pip size is NOT uniform. JPY pairs quote to 2-3 decimals
#: so a pip is 0.01; every other major quotes to 4-5 decimals and a pip is
#: 0.0001. A single ABSOLUTE materiality across six pairs is therefore
#: meaningless: 0.0005 is 5 pips of EUR/USD (a normal spread) and 0.05 pips of
#: USD/JPY (every trade breaks). Thresholds are held in PIPS and converted per
#: pair. Same class of defect as an x100/x10000 units error elsewhere in this
#: estate: an arithmetic scale that looks fine until you check it against the
#: domain.
PIP_SIZE: dict[str, float] = {
    "EUR/USD": 0.0001, "GBP/USD": 0.0001, "AUD/USD": 0.0001,
    "USD/CAD": 0.0001, "EUR/GBP": 0.0001,
    "USD/JPY": 0.01,
}

#: Break-materiality by intent, in PIPS. RULING F2 -- produced HERE, next to
#: the break construction, rather than in `generate_fx_trades.py`, because a
#: threshold chosen apart from the variances it will judge is exactly how
#: §7.5's coincidence risk gets in: pick a number without reference to what
#: it's judging, and an inversion becomes an accident of where the line fell
#: rather than a consequence of the mechanism.
MATERIALITY: dict[str, float] = {
    "break-investigation": 2.0,
    "control-review": 5.0,
    "regulatory-report": 1.0,
}

#: Below this, a real tick-to-tick secant slope is treated as numerically
#: flat rather than divided by. Real intraday drift never actually lands
#: here; this only guards the pathological (session-boundary-clamped) case.
_MIN_DRIFT = 1e-9


def pips(pair: str, rate_difference: float) -> float:
    """Convert a raw rate difference into pips for that pair."""
    try:
        return abs(rate_difference) / PIP_SIZE[pair]
    except KeyError:
        raise ValueError(f"no pip size for {pair!r}") from None


def classify(pair: str, raw_a: float, raw_b: float,
             materiality_pips: float) -> str:
    """Two-way comparison, in pips, against the materiality threshold."""
    return ("genuine" if pips(pair, raw_a - raw_b) > materiality_pips
            else "within-tolerance")


def _floor_drift(drift_per_s: float) -> float:
    if abs(drift_per_s) >= _MIN_DRIFT:
        return drift_per_s
    return _MIN_DRIFT if drift_per_s >= 0 else -_MIN_DRIFT


def _pick_systems(rng: random.Random) -> tuple[str, str]:
    a, b = rng.sample(list(SYSTEMS), 2)
    return a, b


def _timing_break(trade: dict, sys_a: str, sys_b: str, intent: str,
                   target_multiple: float, *, is_named: bool = False) -> dict:
    """A break constructed so the flip is INEVITABLE, not lucky.

    The two systems' TRUE observation instants are set `gap_s` apart --
    `sys_a` at the trade's true execution instant, `sys_b` `gap_s` later
    (its post-affirmation read). `gap_s` is not a fixed constant: it is
    SOLVED FOR from the trade's own real local drift and the materiality
    threshold, so that the raw difference lands at exactly
    `target_multiple` times materiality above the line -- comfortably over,
    by construction, never by threshold placement. `sys_b`'s raw value is
    then the true value at that later instant (`anchor_rate + drift*gap_s`);
    aligning BOTH readings to `as_of = true_b` (the later of the two true
    instants) reconstructs the SAME true value from each, because each
    system's own recorded offset is what `align()` uses to recover its true
    observation instant in the first place -- the aligned difference is
    exactly zero, not merely below materiality, so no threshold choice
    could ever leave this case unflipped.
    """
    pair = trade["pair"]
    drift = _floor_drift(trade["local_drift_per_s"])
    anchor_rate = trade["anchor_rate"]
    t0 = trade["execution_ts"]
    off_a, off_b = SYSTEMS[sys_a], SYSTEMS[sys_b]
    materiality = MATERIALITY[intent]

    target_pips = materiality * target_multiple
    target_diff = target_pips * PIP_SIZE[pair]
    gap_s = abs(target_diff / drift)

    true_a = t0
    true_b = t0 + timedelta(seconds=gap_s)
    raw_a = anchor_rate
    raw_b = anchor_rate + drift * gap_s
    observed_a = true_a + timedelta(seconds=off_a)
    observed_b = true_b + timedelta(seconds=off_b)
    as_of = true_b

    aligned_a = align(raw_a, observed_a, off_a, as_of, drift)
    aligned_b = align(raw_b, observed_b, off_b, as_of, drift)

    raw_diff_pips = pips(pair, raw_a - raw_b)
    aligned_diff_pips = pips(pair, aligned_a - aligned_b)

    return {
        "break_id": f"BRK-{trade['trade_id']}-{sys_a}-{sys_b}",
        "trade_id": trade["trade_id"],
        "pair": pair,
        "intent": intent,
        "materiality_pips": materiality,
        "break_type": "timing",
        "system_a": sys_a, "system_b": sys_b,
        "true_a": true_a.isoformat(), "true_b": true_b.isoformat(),
        "observed_a": observed_a.isoformat(), "observed_b": observed_b.isoformat(),
        "as_of": as_of.isoformat(),
        "gap_s": round(gap_s, 3),
        "local_drift_per_s": drift,
        "raw_a": round(raw_a, 6), "raw_b": round(raw_b, 6),
        "aligned_a": round(aligned_a, 6), "aligned_b": round(aligned_b, 6),
        "raw_diff_pips": round(raw_diff_pips, 4),
        "aligned_diff_pips": round(aligned_diff_pips, 4),
        "timing_component_pips": round(raw_diff_pips - aligned_diff_pips, 4),
        "classification_raw": classify(pair, raw_a, raw_b, materiality),
        "classification_aligned": classify(pair, aligned_a, aligned_b, materiality),
        "provenance": "synthetic — engineered",
        "note": ("timing-attributable: sys_b observes gap_s later than "
                 "sys_a at the same drifting true rate; raw exceeds "
                 "materiality, clock-and-drift alignment to a common as_of "
                 "collapses the difference to exactly zero" +
                 (" -- THE NAMED INVERSION CASE (design §3.4)" if is_named else "")),
    }


def _genuine_break(trade: dict, sys_a: str, sys_b: str, intent: str,
                    error_multiple: float, sign: int,
                    *, is_named: bool = False) -> dict:
    """A booking error that clock alignment cannot explain away.

    Deliberately carries NO timing gap at all (`true_a == true_b == t0`):
    both systems' true observation instant is the trade's own execution
    instant, so there is nothing for drift or clock alignment to correct in
    the first place. `sys_b`'s raw value simply has a fixed error added on
    top. `align()` only ever shifts a value by `drift_per_s * elapsed`, and
    that elapsed is zero here for both systems (`as_of = t0`), so alignment
    is a no-op and the error survives in the aligned comparison exactly as
    it did in the raw one -- by construction, not by the threshold
    happening to still catch it.

    Earlier drafts derived a small extra gap from the trade's own
    `local_drift_per_s` to make this look less like a strawman. That
    reintroduced the SAME degeneracy `_timing_break`'s pool filter exists to
    avoid: most trades execute outside the 13:30-20:00Z tick session, where
    the intraday path is clamped flat and the measured local drift is
    exactly zero -- dividing a target pip amount by that produced gaps of
    YEARS on this trade population (measured: up to ~80,000,000s on one
    trade before this fix). A genuine booking error does not need a timing
    story to be genuine, so it does not carry one.
    """
    pair = trade["pair"]
    anchor_rate = trade["anchor_rate"]
    t0 = trade["execution_ts"]
    off_a, off_b = SYSTEMS[sys_a], SYSTEMS[sys_b]
    materiality = MATERIALITY[intent]
    # `drift` only matters here for `align()`'s signature and for recording
    # what the local rate of change was; with elapsed==0 for both systems
    # it contributes nothing to either value.
    drift = trade["local_drift_per_s"]

    error_pips = materiality * error_multiple
    error = sign * error_pips * PIP_SIZE[pair]

    true_a = true_b = t0
    raw_a = anchor_rate
    raw_b = anchor_rate + error
    observed_a = true_a + timedelta(seconds=off_a)
    observed_b = true_b + timedelta(seconds=off_b)
    as_of = t0

    aligned_a = align(raw_a, observed_a, off_a, as_of, drift)
    aligned_b = align(raw_b, observed_b, off_b, as_of, drift)

    raw_diff_pips = pips(pair, raw_a - raw_b)
    aligned_diff_pips = pips(pair, aligned_a - aligned_b)

    return {
        "break_id": f"BRK-{trade['trade_id']}-{sys_a}-{sys_b}",
        "trade_id": trade["trade_id"],
        "pair": pair,
        "intent": intent,
        "materiality_pips": materiality,
        "break_type": "genuine",
        "system_a": sys_a, "system_b": sys_b,
        "true_a": true_a.isoformat(), "true_b": true_b.isoformat(),
        "observed_a": observed_a.isoformat(), "observed_b": observed_b.isoformat(),
        "as_of": as_of.isoformat(),
        "gap_s": 0.0,
        "local_drift_per_s": drift,
        "booking_error_pips": round(sign * error_pips, 4),
        "raw_a": round(raw_a, 6), "raw_b": round(raw_b, 6),
        "aligned_a": round(aligned_a, 6), "aligned_b": round(aligned_b, 6),
        "raw_diff_pips": round(raw_diff_pips, 4),
        "aligned_diff_pips": round(aligned_diff_pips, 4),
        "timing_component_pips": round(raw_diff_pips - aligned_diff_pips, 4),
        "classification_raw": classify(pair, raw_a, raw_b, materiality),
        "classification_aligned": classify(pair, aligned_a, aligned_b, materiality),
        "provenance": "synthetic — engineered",
        "note": ("genuine: a booking error with no time dependence rides "
                 "through clock-and-drift alignment unchanged, so it "
                 "exceeds materiality under both comparisons" +
                 (" -- THE NAMED SURVIVOR CASE (design §3.4)" if is_named else "")),
    }


#: Bulk population sizes, EXCLUDING the two named cases (added on top).
_N_TIMING = 40
_N_GENUINE = 20

#: Named-case parameters, fixed (not drawn from rng) so the two cases the
#: product's argument rests on are reproducible constants, reportable
#: exactly, and never subject to the bulk population's random draws.
_INVERSION_TARGET_MULTIPLE = 3.0
_SURVIVOR_ERROR_MULTIPLE = 3.0

_DEFAULT_INTENT = "break-investigation"


def build_breaks(trades: list[dict], rng: random.Random) -> list[dict]:
    """~60 breaks: ~40 timing-attributable, ~20 genuine.

    `trades` must be enriched trade dicts carrying `trade_id`, `pair`, a
    TRUE `execution_ts` (tz-aware datetime), `anchor_rate` (the true rate at
    that instant) and `local_drift_per_s` (the real per-second secant slope
    of the intraday tick path around it -- `generate_fx_trades.py` is the
    only place with the tick artifact to compute that from; this module
    stays pure and just uses the number). Must include both
    `INVERSION_TRADE_ID` and `SURVIVOR_TRADE_ID`.

    TIMING candidates are restricted to trades with a NONZERO
    `local_drift_per_s`. Most of the 500 trades execute outside the
    13:30-20:00Z tick session (measured: 299/500) -- there the intraday
    path is clamped flat at its edge and the measured local drift comes
    back exactly 0.0. A `_timing_break` built on one of those has nothing
    real to divide the target pip gap by; an earlier draft floored the
    drift instead of filtering, which produced gaps of literal YEARS on
    this trade population (one measured at ~80,000,000s) -- a construction
    technically present but not remotely inevitable-from-the-mechanism.
    `_genuine_break` carries no such restriction; it does not use drift.
    """
    by_id = {t["trade_id"]: t for t in trades}
    if INVERSION_TRADE_ID not in by_id:
        raise ValueError(f"{INVERSION_TRADE_ID} not found among trades "
                          f"passed to build_breaks -- the named inversion "
                          f"case has nothing to sit on")
    if SURVIVOR_TRADE_ID not in by_id:
        raise ValueError(f"{SURVIVOR_TRADE_ID} not found among trades "
                          f"passed to build_breaks -- the named survivor "
                          f"case has nothing to sit on")
    if by_id[INVERSION_TRADE_ID]["local_drift_per_s"] == 0.0:
        raise ValueError(
            f"{INVERSION_TRADE_ID} has zero local_drift_per_s (its "
            f"execution_ts falls outside the intraday tick session) -- the "
            f"named inversion case needs real drift to invert on")

    need_timing = _N_TIMING - 1
    need_genuine = _N_GENUINE - 1
    pool = sorted(
        (t for t in trades
         if t["trade_id"] not in (INVERSION_TRADE_ID, SURVIVOR_TRADE_ID)),
        key=lambda t: t["trade_id"],
    )
    timing_candidates = [t for t in pool if t["local_drift_per_s"] != 0.0]
    if len(timing_candidates) < need_timing:
        raise ValueError(
            f"build_breaks needs >= {need_timing} trades with nonzero "
            f"local_drift_per_s for the timing population; got "
            f"{len(timing_candidates)}")
    rng.shuffle(timing_candidates)
    timing_trades = timing_candidates[:need_timing]

    used = {t["trade_id"] for t in timing_trades}
    genuine_candidates = [t for t in pool if t["trade_id"] not in used]
    if len(genuine_candidates) < need_genuine:
        raise ValueError(
            f"build_breaks needs >= {need_genuine} trades left over for the "
            f"genuine population; got {len(genuine_candidates)}")
    rng.shuffle(genuine_candidates)
    genuine_trades = genuine_candidates[:need_genuine]

    breaks = []
    breaks.append(_timing_break(
        by_id[INVERSION_TRADE_ID], "trading", "settlement", _DEFAULT_INTENT,
        _INVERSION_TARGET_MULTIPLE, is_named=True))
    for trade in timing_trades:
        sys_a, sys_b = _pick_systems(rng)
        multiple = rng.uniform(2.0, 4.0)
        breaks.append(_timing_break(trade, sys_a, sys_b, _DEFAULT_INTENT, multiple))

    breaks.append(_genuine_break(
        by_id[SURVIVOR_TRADE_ID], "trading", "risk", _DEFAULT_INTENT,
        _SURVIVOR_ERROR_MULTIPLE, sign=1, is_named=True))
    for trade in genuine_trades:
        sys_a, sys_b = _pick_systems(rng)
        error_multiple = rng.uniform(2.0, 4.0)
        sign = 1 if rng.random() < 0.5 else -1
        breaks.append(_genuine_break(trade, sys_a, sys_b, _DEFAULT_INTENT,
                                      error_multiple, sign))

    return breaks
