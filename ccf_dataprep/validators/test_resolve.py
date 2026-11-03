#!/usr/bin/env python3
"""Pure test for false-positive detection across the roster.

Rule 5 requires >= 1 pair of DIFFERENT people who fuzzy-match strongly. The
2026-08-18 Form 4 probe found a real one, so this is a detector for a condition
that already exists rather than a planter of one.

    uv run validators/test_resolve.py
"""

from __future__ import annotations

import sys

from generators.resolve_persons import find_false_positive_pairs

ROSTER = [
    {"person_key": "0001403411", "name_as_filed": "Davison James E",
     "owner_kind": "natural"},
    {"person_key": "0001403412", "name_as_filed": "Davison James E. Jr.",
     "owner_kind": "natural"},
    {"person_key": "0001277036", "name_as_filed": "SRINIVASAN RAMESH",
     "owner_kind": "natural"},
    {"person_key": "0001266604", "name_as_filed": "CCH II LLC",
     "owner_kind": "entity"},
]


def main() -> int:
    pairs = find_false_positive_pairs(ROSTER)
    keys = {tuple(sorted((p["person_key_a"], p["person_key_b"]))) for p in pairs}
    cases = [
        ("the real Davison pair is detected",
         ("0001403411", "0001403412") in keys),
        ("exactly one pair is found in this roster", len(pairs) == 1),
        ("the pair scores at or above the band threshold",
         all(p["match_score"] >= 0.90 for p in pairs)),
        ("it is banded false_positive, not a match",
         all(p["match_band"] == "false_positive" for p in pairs)),
        ("is_true_match is False", all(p["is_true_match"] is False for p in pairs)),
        ("provenance is public — the collision is real, not planted",
         all(p["provenance"] == "public" for p in pairs)),
        ("entities are excluded from person matching",
         all("0001266604" not in (p["person_key_a"], p["person_key_b"])
             for p in pairs)),
        ("a person does not match themselves",
         all(p["person_key_a"] != p["person_key_b"] for p in pairs)),
    ]
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
