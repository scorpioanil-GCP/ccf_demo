#!/usr/bin/env python3
"""Pure curve helpers — date parsing, tenor labels, interpolation. No I/O.

Treasury and FRED publish the same kind of daily series in DIFFERENT date
formats, and this wave joins them on date. `MM/DD/YYYY` against ISO
`YYYY-MM-DD`. Both parsers are strict: handed the other's format they raise,
rather than silently producing a plausible wrong date.

Tenor matching is interpolation between bracketing points, never a snap to the
nearest column. §D forbids calendar proximity explicitly, and an instrument at
4.2 years matched to the 5-year point would produce a spread that is wrong by
the shape of the curve rather than by a visible error.
"""

from __future__ import annotations

from datetime import date, datetime

#: Treasury column label -> tenor in years. The schema is NOT fixed across the
#: window: the 2024 CSV header has no `1.5 Month` column at all (Treasury added
#: a 6-week bill benchmark starting 2025), and from 2025-02-18 onward that
#: column is populated on essentially every row — not sparse, once it exists.
#: The header must therefore be read PER FILE, never hardcoded: a hardcoded
#: 15-column header zipped against 2024's 14-column rows would misalign every
#: later tenor by one column, silently, unless the caller also zips with
#: `strict=True` (see `parse_treasury_row`).
TENORS: list[tuple[str, float]] = [
    ("1 Mo", 1 / 12), ("1.5 Month", 1.5 / 12), ("2 Mo", 2 / 12),
    ("3 Mo", 3 / 12), ("4 Mo", 4 / 12), ("6 Mo", 6 / 12),
    ("1 Yr", 1.0), ("2 Yr", 2.0), ("3 Yr", 3.0), ("5 Yr", 5.0),
    ("7 Yr", 7.0), ("10 Yr", 10.0), ("20 Yr", 20.0), ("30 Yr", 30.0),
]
_BY_LABEL = dict(TENORS)


def parse_treasury_date(raw: str) -> date:
    """`MM/DD/YYYY`. Strict — an ISO date raises rather than being coerced."""
    return datetime.strptime(raw.strip(), "%m/%d/%Y").date()


def parse_fred_date(raw: str) -> date:
    """ISO `YYYY-MM-DD`. Strict — a Treasury date raises."""
    return datetime.strptime(raw.strip(), "%Y-%m-%d").date()


def tenor_years(label: str) -> float | None:
    return _BY_LABEL.get(label.strip())


def parse_treasury_row(header: list[str], row: list[str]) -> tuple[date, dict[float, float]]:
    """One Treasury row -> (date, {tenor_years: par_yield}).

    A blank cell is DROPPED, never defaulted to zero. A zero yield is a
    meaningful value and a missing one is not; conflating them would put a
    fictional 0% point on the curve and silently distort every spread
    interpolated across it.
    """
    d = parse_treasury_date(row[0])
    curve: dict[float, float] = {}
    # strict=True ensures a short row (missing columns) raises ValueError instead of
    # silently misaligning tenor labels — the same strictness as the date parsers.
    for label, cell in zip(header[1:], row[1:], strict=True):
        years = tenor_years(label)
        text = (cell or "").strip()
        if years is None or not text:
            continue
        curve[years] = float(text)
    return d, curve


def interpolate_tenor(curve: dict[float, float], years: float) -> float | None:
    """Linear interpolation between the two bracketing tenors.

    Returns None outside the curve's range rather than extrapolating — an
    invented point beyond 30 years is not a benchmark, and a caller that gets
    None can record the gap instead of carrying a fabricated number forward.
    """
    if not curve:
        return None
    if years in curve:
        return curve[years]
    lower = [t for t in curve if t < years]
    upper = [t for t in curve if t > years]
    if not lower or not upper:
        return None
    lo, hi = max(lower), min(upper)
    span = hi - lo
    if span == 0:
        return curve[lo]
    weight = (years - lo) / span
    return curve[lo] + weight * (curve[hi] - curve[lo])
