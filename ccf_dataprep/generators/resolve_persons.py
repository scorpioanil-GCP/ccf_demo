#!/usr/bin/env python3
"""Build `person_crosswalk` and surface the false-positive pair.

§C: "Person identity is the hard join." The crosswalk is synthetic and
imperfect ON PURPOSE — a demo where every person resolves cleanly teaches the
wrong lesson and makes the resolution logic untestable.

The false-positive pair is NOT planted. The 2026-08-18 probe found a real one:
`Davison James E` (CIK 1403411) and `Davison James E. Jr.` (CIK 1403412), both
filing against Genesis Energy, two different people. Provenance is therefore
`public`. A found collision proves the case occurs in the wild; a planted one
proves only that the resolver handles a case built for it.

    uv run generators/resolve_persons.py --dry-run
    uv run generators/resolve_persons.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from itertools import combinations

from ccf.config import REPO_ROOT
from generators.persons import match_band, match_score

SCREEN = REPO_ROOT / "sources" / "screening"
FALSE_POSITIVE_FLOOR = 0.90


def find_false_positive_pairs(roster: list[dict]) -> list[dict]:
    """Distinct natural persons whose names collide at or above the floor."""
    people = [p for p in roster if p.get("owner_kind") == "natural"]
    pairs: list[dict] = []
    for a, b in combinations(people, 2):
        if a["person_key"] == b["person_key"]:
            continue
        score = match_score(a["name_as_filed"], b["name_as_filed"])
        if score < FALSE_POSITIVE_FLOOR:
            continue
        pairs.append({
            "person_key_a": a["person_key"],
            "person_key_b": b["person_key"],
            "name_a": a["name_as_filed"],
            "name_b": b["name_as_filed"],
            "match_score": round(score, 4),
            "match_band": match_band(score, same_cik=False),
            "is_true_match": False,
            "provenance": "public",
            "note": "distinct SEC CIKs; names collide at or above the floor",
        })
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    roster = json.loads((SCREEN / "wave10_persons.json").read_text())["persons"]
    variants = json.loads(
        (SCREEN / "wave10_name_variants.json").read_text())["variants"]
    by_key = {p["person_key"]: p for p in roster}

    rows: list[dict] = []

    # Form 4 resolves exactly: the CIK IS the key.
    for person in roster:
        rows.append({
            "source_system": "form4",
            "source_id": person["cik"],
            "source_name": person["name_as_filed"],
            "person_key": person["person_key"],
            "match_score": 1.0,
            "match_band": "exact",
            "is_true_match": True,
            "provenance": "public",
            "note": "reporting owner CIK is the person key",
        })

    # DEF 14A resolves by name against a known roster — genuinely imperfect.
    for variant in variants:
        person = by_key.get(variant["person_key"])
        if person is None:
            continue
        score = match_score(variant["variant_name"], person["name_as_filed"])
        rows.append({
            "source_system": "def14a",
            "source_id": f"{variant['person_key']}:{variant['variant_name']}",
            "source_name": variant["variant_name"],
            "person_key": variant["person_key"],
            "match_score": round(score, 4),
            "match_band": match_band(score, same_cik=None),
            "is_true_match": True,
            "provenance": "synthetic — engineered",
            "note": "resolved by bounded name search, not by identifier",
        })

    pairs = find_false_positive_pairs(roster)
    for pair in pairs:
        rows.append({
            "source_system": "resolver",
            "source_id": pair["person_key_b"],
            "source_name": pair["name_b"],
            "person_key": pair["person_key_a"],
            "match_score": pair["match_score"],
            "match_band": "false_positive",
            "is_true_match": False,
            "provenance": "public",
            "note": pair["note"],
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": rows,
        "false_positive_pairs": pairs,
    }
    print(f"  {len(rows)} crosswalk rows · {len(pairs)} false-positive pairs")
    for pair in pairs:
        print(f"    [fp] {pair['name_a']}  <->  {pair['name_b']}  "
              f"score={pair['match_score']}")

    if not pairs:
        print("\n  WARNING: rule 5 requires >= 1 false-positive pair and none was "
              "found. Do NOT plant one silently — record the shortfall and raise it.")

    if args.dry_run:
        print("  [dry-run] nothing written")
        return 0
    (SCREEN / "wave10_crosswalk.json").write_text(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
