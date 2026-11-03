#!/usr/bin/env python3
"""Pure tests for instrument id minting, band derivation, and tenor laddering.

Not required by Task 4's brief (no pytest, no reference code), but the three
functions here are the load-bearing pure logic of `generate_instruments.py`
and cheap to pin in the project's house style.

    uv run validators/test_instruments.py
"""

from __future__ import annotations

import re
import sys
from datetime import date

from generators.generate_instruments import (band_for_leverage,
                                              eligible_tenors,
                                              mint_instrument_id)

ID_RE = re.compile(r"^syn-i-[0-9a-f]{6}$")
CUSIP_RE = re.compile(r"^[0-9A-Z]{9}$")


def check_id_minting() -> list[tuple[str, bool]]:
    a = mint_instrument_id(1, "LEIONE00000000000001", 0)
    b = mint_instrument_id(1, "LEIONE00000000000001", 0)
    c = mint_instrument_id(1, "LEIONE00000000000001", 1)
    d = mint_instrument_id(1, "LEITWO00000000000002", 0)
    e = mint_instrument_id(2, "LEIONE00000000000001", 0)
    return [
        ("same (seed, lei, sequence) mints the same id", a == b),
        ("a different sequence mints a different id", a != c),
        ("a different lei mints a different id", a != d),
        ("a different seed mints a different id", a != e),
        ("the id matches syn-i-<6 hex>", bool(ID_RE.match(a))),
        ("the id is never CUSIP-shaped",
         not CUSIP_RE.match(a.removeprefix("syn-i-"))),
    ]


def check_band_derivation() -> list[tuple[str, bool]]:
    return [
        ("very low leverage bands AA", band_for_leverage(0.05) == "AA"),
        ("the AA/A boundary is inclusive on the AA side",
         band_for_leverage(0.15) == "AA"),
        ("just past the AA/A boundary bands A",
         band_for_leverage(0.1501) == "A"),
        ("mid leverage bands BBB", band_for_leverage(0.45) == "BBB"),
        ("high leverage bands BB", band_for_leverage(0.65) == "BB"),
        ("very high leverage bands B", band_for_leverage(5.0) == "B"),
        ("missing leverage data bands B, not AA — unmeasured is not safe",
         band_for_leverage(None) == "B"),
        ("no band ever falls outside the five FRED series",
         band_for_leverage(0.2) in {"AA", "A", "BBB", "BB", "B"}),
    ]


def check_tenor_laddering() -> list[tuple[str, bool]]:
    floor = date(2027, 1, 1)
    ceiling = date(2052, 1, 1)  # 25y past floor -- room to test both edges
    ladder = [2, 3, 5, 7, 10, 12, 15, 20, 25, 30]
    recent = eligible_tenors(date(2026, 6, 1), floor, ceiling, ladder)
    old = eligible_tenors(date(2012, 9, 6), floor, ceiling, ladder)
    exact = eligible_tenors(floor, floor, ceiling, ladder)
    return [
        ("a recent issue date draws every tenor that stays under the "
         "ceiling", recent == [t for t in ladder if t < 30]),
        ("that recent issue date's LONGEST tenor is excluded -- it alone "
         "would outrun the curve's priceable range",
         30 not in recent),
        ("an old issue date is constrained to tenors that survive the floor",
         old == [t for t in ladder if t >= 15]),
        ("every surviving tenor for the old issue date actually matures on "
         "or after the floor",
         all(date(2012, 9, 6).year + t >= floor.year for t in old)),
        ("an issue date exactly at the floor is still bounded by the "
         "ceiling, not just the floor",
         exact == [t for t in ladder if t <= 25]),
        ("the fallback branch never returns an empty list",
         len(eligible_tenors(date(1990, 1, 1), floor, ceiling, ladder)) > 0),
        ("the fallback tenor still respects the floor even when it misses "
         "every ladder rung",
         date(1990, 1, 1).year
         + eligible_tenors(date(1990, 1, 1), floor, ceiling, ladder)[0]
         >= floor.year),
    ]


def main() -> int:
    cases = (check_id_minting() + check_band_derivation()
             + check_tenor_laddering())
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
