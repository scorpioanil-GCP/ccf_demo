#!/usr/bin/env python3
"""Engineered narrative for Wave 11a, shared by both generators.

WHY THIS MODULE EXISTS. `generate_grades.py` used to recover these
declarations by reading `wave11a_spreads.json` and parsing its
`divergence_windows` key -- which is nothing but a projection of the
`DIVERGENCES` literal below. That made grades depend on the spreads
ARTIFACT, which forced spreads to run first, which is why spreads could not
read the grade chains and so pinned its market leg to the day-1 rating band
(known-issues.md 9.10).

The dependency was on CONFIGURATION, not on computation. Declaring it in one
place both generators import dissolves the cycle at no behavioural cost.
"""

from __future__ import annotations

from datetime import date
from random import Random

#: Single source for both generators (Fix round: previously redeclared in
#: `generate_grades.py` and `generate_spreads.py`, each asserting by comment
#: that the other two agreed -- import it instead of restating it).
SEED = 20260817


def band_of_grade(grade: str) -> str:
    """Strip the +/- modifier to recover the band letter.

    Single source for both generators and `validators/series.py` (Fix
    round: previously duplicated in `generate_grades.py` and
    `generate_spreads.py`, on the theory that importing one generator's copy
    from the other would recreate the dependency this module exists to
    dissolve -- true when the only shared home was one of the two
    generators, false now that a cycle-free third module holds it).
    """
    return grade.rstrip("+-")


# --- divergence windows: MOVED VERBATIM from generate_spreads.py ----------
#: Divergence cases: a smooth trapezoid (ramp up, plateau, ramp down) added
#: on top of the instrument's normal idiosyncratic series across a bounded
#: date range. Four placed (only 3 required) for margin; the earliest-ending
#: one is flagged `confirm_later` because it leaves the most runway before
#: WINDOW_END for Task 6 to place a rerating that moves the grade in the
#: direction the spread already showed.
DIVERGENCES: list[dict] = [
    {
        "instrument_id": "syn-i-b23153",  # Celanese Corp, BB
        "start": date(2024, 11, 1),
        "end": date(2025, 2, 15),
        "peak_bp": 200.0,
        "confirm_later": True,
        "note": ("earliest-closing window; flagged for Task 6 to place a "
                  "confirming downgrade well before WINDOW_END"),
    },
    {
        "instrument_id": "syn-i-6e26db",  # BB, 254900HM1ABRDJ7T5718
        "start": date(2025, 4, 1),
        "end": date(2025, 6, 30),
        "peak_bp": 180.0,
        "confirm_later": False,
        "note": None,
    },
    {
        "instrument_id": "syn-i-991bbc",  # BBB, 5493004Q1NNH6JXCSI52
        "start": date(2025, 8, 15),
        "end": date(2025, 11, 1),
        "peak_bp": 160.0,
        "confirm_later": False,
        "note": None,
    },
    {
        "instrument_id": "syn-i-4d322a",  # B, 529900VKCYZW8GZ4WW58
        "start": date(2026, 1, 5),
        "end": date(2026, 3, 20),
        "peak_bp": 240.0,
        "confirm_later": False,
        "note": None,
    },
]
DIVERGENCE_RAMP_FRACTION = 0.25  # each side of the trapezoid


def divergence_windows_for_artifact(instruments: list[dict]) -> list[dict]:
    """The `divergence_windows` projection: DIVERGENCES enriched with each
    instrument's `lei` and `rating_band`.

    Lives here, not in either generator, because BOTH need it -- spreads to
    write it into its artifact, grades to consume it. Two implementations of
    one projection is how they would drift apart.
    """
    by_id = {i["instrument_id"]: i for i in instruments}
    return [
        {
            "instrument_id": dv["instrument_id"],
            "lei": by_id[dv["instrument_id"]]["lei"],
            "rating_band": by_id[dv["instrument_id"]]["rating_band"],
            "start_date": dv["start"].isoformat(),
            "end_date": dv["end"].isoformat(),
            "peak_bp": dv["peak_bp"],
            "confirm_later": dv["confirm_later"],
            "note": dv["note"],
        }
        for dv in DIVERGENCES
    ]


#: Market response to a band migration. Three shapes, DELIBERATELY
#: UNCORRELATED: the faintest signal carries the longest lead. A dataset
#: where strong signals always arrive early teaches a detector to read
#: timing as strength -- an artifact of this generator, not a fact about
#: credit markets, and Wave 11b is measured against exactly this.
#:
#: `lead_obs` is counted in OBSERVATION DATES present in the Treasury curve,
#: never calendar days: a calendar lead silently shortens across holidays.
MIGRATION_PROFILES: list[dict] = [
    {"name": "faint",      "anticipation": 0.30, "lead_obs": 110},
    {"name": "moderate",   "anticipation": 0.60, "lead_obs": 40},
    {"name": "pronounced", "anticipation": 0.90, "lead_obs": 75},
]


def assign_profiles(leis: list[str]) -> dict[str, dict]:
    """{lei: profile} by a seeded SHUFFLE of the catalogue over sorted LEIs.

    A permutation, NOT an independent per-LEI draw. Three independent draws
    from three profiles collide with probability ~0.78, so the "vary across
    the three" requirement would silently fail most of the time and the
    failure would look like data rather than like a bug. Sorting first makes
    the result independent of the caller's ordering.
    """
    ordered = sorted(leis)
    if not ordered:
        return {}
    shuffled = list(MIGRATION_PROFILES)
    Random(f"{SEED}|migration-profiles").shuffle(shuffled)
    return {lei: shuffled[i % len(shuffled)] for i, lei in enumerate(ordered)}
