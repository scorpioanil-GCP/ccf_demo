#!/usr/bin/env python3
"""Pure tests for the migration-transition mechanics.

    uv run validators/test_migration.py
"""

from __future__ import annotations

import sys
from datetime import date

from generators.generate_spreads import (band_of_grade, crossings_from_chain,
                                         migration_ramp_weight, ramp_start_index)
from generators.narrative_wave11a import MIGRATION_PROFILES, assign_profiles

THREE = ["5493003QENHHS261UR94", "5493004HBTOTE9DI9P12", "549300EQD0ZXRSMG3549"]


def check_profiles() -> list[tuple[str, bool]]:
    a = assign_profiles(THREE)
    b = assign_profiles(list(reversed(THREE)))
    names = sorted(p["name"] for p in a.values())
    return [
        ("catalogue holds exactly three profiles", len(MIGRATION_PROFILES) == 3),
        ("anticipation values are 0.30/0.60/0.90",
         sorted(p["anticipation"] for p in MIGRATION_PROFILES) == [0.30, 0.60, 0.90]),
        ("lead is uncorrelated with anticipation -- the weakest has the longest lead",
         max(MIGRATION_PROFILES, key=lambda p: p["lead_obs"])["anticipation"] == 0.30),
        ("three LEIs receive three DISTINCT profiles", len(set(names)) == 3),
        ("assignment is deterministic across runs", a == assign_profiles(THREE)),
        ("assignment does not depend on input order", a == b),
        ("a fourth LEI cycles rather than crashing",
         len(assign_profiles(THREE + ["EXTRA0000000000000X"])) == 4),
        ("no LEI means no assignment", assign_profiles([]) == {}),
    ]


def check_ramp() -> list[tuple[str, bool]]:
    m, start = 100, 60          # 40 observation dates of lead
    w = lambda i: migration_ramp_weight(i, start, m)
    return [
        ("weight is 0 at the ramp start", w(start) == 0.0),
        ("weight is 0 before the ramp start", w(start - 5) == 0.0),
        ("weight is 0 AT the migration -- anticipation is consumed", w(m) == 0.0),
        ("weight is 0 after the migration", w(m + 30) == 0.0),
        ("weight approaches 1 just before the migration", w(m - 1) == 0.975),
        ("weight is monotone non-decreasing across the ramp",
         all(w(i) <= w(i + 1) for i in range(start, m - 1))),
        ("weight never exceeds 1", all(w(i) <= 1.0 for i in range(start, m))),
        ("a zero-length ramp yields no weight rather than dividing by zero",
         migration_ramp_weight(50, 50, 50) == 0.0),
        ("lead is clipped at the window floor",
         ramp_start_index(m_idx=30, lead_obs=110, floor_idx=0) == 0),
        ("lead is clipped at a previous migration",
         ramp_start_index(m_idx=200, lead_obs=110, floor_idx=150) == 150),
        ("an unobstructed lead is taken in full",
         ramp_start_index(m_idx=200, lead_obs=40, floor_idx=0) == 160),
    ]


def check_crossings() -> list[tuple[str, bool]]:
    chain = [
        {"grade": "BB",  "asserted_at": "2024-08-21"},
        {"grade": "BB-", "asserted_at": "2024-11-20"},   # notch move, same band
        {"grade": "B",   "asserted_at": "2025-11-19"},   # DOWNGRADE across band
        {"grade": "BB",  "asserted_at": "2026-05-23"},   # UPGRADE back
    ]
    out = crossings_from_chain(chain)
    return [
        ("band strips a minus modifier", band_of_grade("BB-") == "BB"),
        ("band strips a plus modifier", band_of_grade("A+") == "A"),
        ("a plain grade is its own band", band_of_grade("BBB") == "BBB"),
        ("a notch move inside one band is not a crossing", len(out) == 2),
        ("the downgrade is found with its asserted_at",
         out[0] == {"asserted_at": date(2025, 11, 19), "from_band": "BB", "to_band": "B"}),
        ("the recovery is found as a separate crossing",
         out[1] == {"asserted_at": date(2026, 5, 23), "from_band": "B", "to_band": "BB"}),
        ("crossings come back in asserted_at order",
         out[0]["asserted_at"] < out[1]["asserted_at"]),
        ("a chain that never leaves its band yields nothing",
         crossings_from_chain([{"grade": "A", "asserted_at": "2024-08-21"},
                               {"grade": "A-", "asserted_at": "2025-01-01"}]) == []),
        ("a single-assertion chain yields nothing",
         crossings_from_chain([{"grade": "A", "asserted_at": "2024-08-21"}]) == []),
    ]


def main() -> int:
    cases = check_profiles() + check_ramp() + check_crossings()
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
