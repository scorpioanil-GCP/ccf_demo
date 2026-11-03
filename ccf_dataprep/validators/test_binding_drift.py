#!/usr/bin/env python3
"""Behaviour test for the drift verdicts. No stores touched — pure logic.

`binding_drift.py` reports AGREE against the current estate, and a validator that
only ever passes proves nothing. These cases pin the verdict for every
combination that matters, including **the actual 2026-08-17 bug as case 1**: the
vault claimed `owns` was contradicted, the §0.1 remediation had already landed,
and 462 correct assertions existed. A caveat pointing at correct data.

The two directions are asymmetric and both are represented:

    drift outlives the warning  -> consumer binds against stale data
    warning outlives the drift  -> consumer "fixes" data that is already right

    uv run validators/test_binding_drift.py
"""

from __future__ import annotations

import sys

from validators.binding_drift import (AGREE, CAVEAT_MISSING, CAVEAT_STALE,
                                      CAVEAT_WRONG, judge)

#: (label, (claim, correct_assertions, stale_assertions), expected_verdict)
CASES = [
    ("THE 2026-08-17 BUG — vault said contradicted, remediation had landed",
     ("contradicted", 462, 0), CAVEAT_STALE),
    ("genuine stale data, correctly warned",
     ("contradicted", 0, 500), AGREE),
    ("no drift in either direction, yet a warning stands",
     ("contradicted", 0, 0), CAVEAT_STALE),
    ("claimed absent, but data landed since publication",
     ("not_materialized", 103, 0), CAVEAT_STALE),
    ("estate is contradicted and the vault says nothing",
     ("not_materialized", 0, 500), CAVEAT_MISSING),
    ("vault promises data that does not exist",
     ("materialized", 0, 0), CAVEAT_WRONG),
    ("claimed materialized, estate is on the stale IRI",
     ("materialized", 0, 500), CAVEAT_MISSING),
    ("healthy materialized", ("materialized", 462, 0), AGREE),
    ("healthy not-materialized", ("not_materialized", 0, 0), AGREE),
]


def main() -> int:
    failures = 0
    for label, (claim, correct, stale), expected in CASES:
        got, _ = judge(claim, correct, stale)
        ok = got == expected
        failures += not ok
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
        print(f"         claim={claim} correct={correct} stale={stale} "
              f"-> {got}" + ("" if ok else f"  (expected {expected})"))
    print(f"\n  {len(CASES) - failures}/{len(CASES)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
