"""Build the intraday tick series from REAL published daily closes.

Design §1.3 selected the window 2026-05-11 -> 2026-06-23 (30 trading days)
because it carries SEVEN real >=8bp day-over-day moves at the 2y tenor, where
the most recent windows carry exactly one sitting on the 8.0bp threshold.
Wave 11b's D1 is the precedent for choosing margin over recency.

Each day's path opens at the PRIOR session's published close and terminates
at that day's published close. Both are read from `benchmark_curve` and never
modified, so the day-over-day move is real; only the within-day path is
engineered, and every row says so.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf.config import pg_connect, PG_SCHEMA_V2                # noqa: E402
from ccf.currency import record_inputs                          # noqa: E402
from generators.ticks import (                                  # noqa: E402
    ROLLING_WINDOW_TICKS, SESSION_TICKS,
    brownian_bridge, max_rolling_move_bp, session_times,
)

WINDOW_START = date(2026, 5, 11)
WINDOW_END = date(2026, 6, 23)
TENORS = (0.25, 1.0, 2.0, 5.0, 10.0)
PROVENANCE = "synthetic — engineered"
OUT = Path(__file__).resolve().parent.parent / "sources" / "screening" / "wave12_ticks.json"


def load_closes(tenor: float) -> list[tuple[date, float]]:
    """Published closes for one tenor, one day BEFORE the window onward.

    The extra leading day supplies the first session's opening anchor.
    """
    with pg_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f'''SELECT curve_date, par_yield_pct
                  FROM "{PG_SCHEMA_V2}".benchmark_curve
                 WHERE tenor_years = %s AND curve_date <= %s
                 ORDER BY curve_date''',
            (tenor, WINDOW_END))
        rows = [(r[0], float(r[1])) for r in cur.fetchall()]
    # Keep the window plus exactly one prior trading day.
    inside = [r for r in rows if WINDOW_START <= r[0] <= WINDOW_END]
    before = [r for r in rows if r[0] < WINDOW_START]
    if not before:
        raise RuntimeError(f"tenor {tenor}: no prior close to open against")
    return [before[-1], *inside]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ticks, eight_bp_days, day_count = [], set(), None

    for tenor in TENORS:
        closes = load_closes(tenor)
        sessions = closes[1:]           # the window itself
        if day_count is None:
            day_count = len(sessions)
        elif day_count != len(sessions):
            raise RuntimeError(
                f"tenor {tenor} has {len(sessions)} sessions, expected {day_count} "
                "-- the curve is not rectangular over this window")

        for i, (day, close_v) in enumerate(sessions):
            open_v = closes[i][1]       # prior session's published close
            # Seed from the day and tenor so a reload reproduces exactly.
            seed = int(day.strftime("%Y%m%d")) * 1000 + int(tenor * 100)
            path = brownian_bridge(open_v, close_v, SESSION_TICKS, seed)
            stamps = session_times(day)

            move = max_rolling_move_bp(path, ROLLING_WINDOW_TICKS)
            if move >= 8.0:
                eight_bp_days.add(day.isoformat())

            for ts, v in zip(stamps, path, strict=True):
                ticks.append({
                    "tenor_years": tenor,
                    "trading_day": day.isoformat(),
                    "obs_ts": ts.isoformat(),
                    "value_pct": round(v, 6),
                    "provenance": PROVENANCE,
                })

    artifact = {
        "_meta": {
            "window_start": WINDOW_START.isoformat(),
            "window_end": WINDOW_END.isoformat(),
            "trading_days": day_count,
            "tenors": list(TENORS),
            "session_ticks": SESSION_TICKS,
            "anchor_source": "ccf_v2.benchmark_curve (Treasury.gov, public)",
            "note": ("Endpoints are real published closes; only the within-day "
                     "path is engineered."),
        },
        "_inputs": record_inputs(),
        "eight_bp_days": sorted(eight_bp_days),
        "ticks": ticks,
    }

    print(f"  {len(ticks)} ticks over {day_count} sessions x {len(TENORS)} tenors")
    print(f"  days carrying a >=8bp 90-minute move: {len(eight_bp_days)}")
    for d in sorted(eight_bp_days):
        print(f"    {d}")
    if not eight_bp_days:
        print("  FAIL: no day carries the 8bp condition", file=sys.stderr)
        return 1
    if args.dry_run:
        print("  --dry-run: not written")
        return 0
    OUT.write_text(json.dumps(artifact, indent=1))
    print(f"  wrote {OUT.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
