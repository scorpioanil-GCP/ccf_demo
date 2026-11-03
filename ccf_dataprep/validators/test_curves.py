#!/usr/bin/env python3
"""Pure tests for curve parsing and tenor matching.

Two traps are pinned here, both of the shape that has cost this project most.

TWO DATE FORMATS. Treasury renders MM/DD/YYYY, FRED renders ISO YYYY-MM-DD, and
the two are joined on date. Wave 8's amendment resolution compared DD-MON-YYYY
as raw strings and sorted by day-of-month, then month NAME alphabetically — it
was correct only by coincidence of that archive's date distribution. Parse, do
not pattern-match.

TENOR MATCHING, NOT CALENDAR PROXIMITY. §D forbids matching a benchmark point by
whichever tenor is nearest in the file. An instrument with 4.2 years to maturity
is interpolated between the 3-year and 5-year points, never snapped to one.

    uv run validators/test_curves.py
"""

from __future__ import annotations

import sys
from datetime import date

from generators.curves import (interpolate_tenor, parse_fred_date,
                               parse_treasury_date, parse_treasury_row,
                               tenor_years)
from generators.generate_spreads import compose_observation, dominance_ratio

HEADER = ["Date", "1 Mo", "1.5 Month", "2 Mo", "3 Mo", "4 Mo", "6 Mo", "1 Yr",
          "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]
ROW = ["01/02/2025", "4.45", "", "4.36", "4.36", "4.31", "4.25", "4.17",
       "4.25", "4.29", "4.38", "4.47", "4.57", "4.86", "4.79"]


def check_dates() -> list[tuple[str, bool]]:
    return [
        ("treasury MM/DD/YYYY parses",
         parse_treasury_date("01/02/2025") == date(2025, 1, 2)),
        ("treasury month and day are not transposed",
         parse_treasury_date("03/11/2025") == date(2025, 3, 11)),
        ("fred ISO parses", parse_fred_date("2026-08-18") == date(2026, 8, 18)),
        ("the two formats agree on the same day",
         parse_treasury_date("08/18/2026") == parse_fred_date("2026-08-18")),
        ("a treasury date is NOT accepted by the fred parser",
         _raises(parse_fred_date, "08/18/2026")),
        ("a fred date is NOT accepted by the treasury parser",
         _raises(parse_treasury_date, "2026-08-18")),
    ]


def _raises(fn, *args) -> bool:
    try:
        fn(*args)
    except Exception:
        return True
    return False


def check_tenors() -> list[tuple[str, bool]]:
    return [
        ("1 Mo is one twelfth of a year", abs(tenor_years("1 Mo") - 1 / 12) < 1e-9),
        ("1.5 Month parses as a month label", tenor_years("1.5 Month") is not None),
        ("10 Yr is ten years", tenor_years("10 Yr") == 10.0),
        ("an unknown label yields None", tenor_years("banana") is None),
    ]


def check_row() -> list[tuple[str, bool]]:
    d, curve = parse_treasury_row(HEADER, ROW)
    return [
        ("row date parses", d == date(2025, 1, 2)),
        ("the blank 1.5 Month cell is DROPPED, not zero",
         not any(abs(k - 0.125) < 1e-6 for k in curve)),
        ("a blank never becomes 0.0", 0.0 not in curve.values()),
        ("populated tenors survive", abs(curve[10.0] - 4.57) < 1e-9),
        ("all populated cells are present", len(curve) == 13),
        ("a short row raises rather than silently misaligning the curve",
         _raises(parse_treasury_row, HEADER, ROW[:-1])),
    ]


def check_interpolation() -> list[tuple[str, bool]]:
    curve = {3.0: 4.29, 5.0: 4.38, 10.0: 4.57}
    mid = interpolate_tenor(curve, 4.0)
    off = interpolate_tenor(curve, 4.2)
    return [
        ("an exact tenor returns its own point",
         interpolate_tenor(curve, 5.0) == 4.38),
        ("a midpoint interpolates linearly", abs(mid - 4.335) < 1e-9),
        ("4.2y sits between the 3y and 5y points, not snapped to either",
         off is not None and 4.29 < off < 4.38 and off != 4.29 and off != 4.38),
        ("4.2y is NOT the nearest tenor's value — proximity is forbidden",
         abs(off - 4.38) > 1e-9),
        ("beyond the longest tenor yields None rather than extrapolating",
         interpolate_tenor(curve, 40.0) is None),
        ("below the shortest tenor yields None",
         interpolate_tenor(curve, 0.5) is None),
    ]


def check_composition() -> list[tuple[str, bool]]:
    obs = compose_observation(benchmark_bp=430.0, market_oas_bp=163.0,
                              idiosyncratic_bp=45.0)
    return [
        ("spread is market plus idiosyncratic, not including benchmark",
         obs["spread_bp"] == 208.0),
        ("yield is benchmark plus spread", obs["yield_bp"] == 638.0),
        ("the two components stay separately addressable",
         obs["market_oas_bp"] == 163.0 and obs["idiosyncratic_bp"] == 45.0),
        ("a None benchmark yields no observation at all, never a zero",
         compose_observation(benchmark_bp=None, market_oas_bp=163.0,
                             idiosyncratic_bp=45.0) is None),
    ]


def check_dominance() -> list[tuple[str, bool]]:
    calm = [{"market_oas_bp": 160.0, "idiosyncratic_bp": 40.0}] * 10
    swamped = [{"market_oas_bp": 160.0, "idiosyncratic_bp": 200.0}] * 10
    return [
        ("a calm series passes the 40% dominance rule",
         dominance_ratio(calm) <= 0.40),
        ("a swamped series FAILS it — the check can go red",
         dominance_ratio(swamped) > 0.40),
        ("the ratio is median-based, so one outlier cannot flip it",
         dominance_ratio(calm + [{"market_oas_bp": 160.0,
                                  "idiosyncratic_bp": 900.0}]) <= 0.40),
    ]


def main() -> int:
    cases = (check_dates() + check_tenors() + check_row()
             + check_interpolation() + check_composition()
             + check_dominance())
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
