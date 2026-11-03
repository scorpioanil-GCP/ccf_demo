#!/usr/bin/env python3
"""Generate the entire bank side of client-360. All `synthetic — internal`.

§C: interaction history exists nowhere public, so every element here is
invented. That is not a weakness in the demo — it is an accurate depiction of
the problem, and it is why no vendor can supply this half.

Two conditions are shaped rather than counted:

  recency weighting  — relationship strength decays with the interactions
                       beneath it (§E gives interaction records λ_c ~7 days),
                       so a FLAT distribution makes the score meaningless
  dense anchor       — §F wants >= 1 client whose depth-2 traversal exceeds
                       limit=200, and an even spread makes that unreachable

Determinism: seeded from a fixed constant so re-runs are byte-stable. No
`Math.random`-style drift between loads.

    uv run generators/generate_coverage.py --dry-run
    uv run generators/generate_coverage.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, datetime, timedelta, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
SEED = 20261018
BANKER_COUNT = 40
INTERACTION_TOTAL = 2000
MONTHS = 24
DENSE_SHARE = 0.12
NEED_TO_KNOW_COUNT = 10
COVERAGE_GAP_COUNT = 3

ROLES = ["coverage", "product", "credit"]
SENIORITY = ["analyst", "associate", "vice_president", "director", "managing_director"]
CHANNELS = ["meeting", "call", "email"]
FIRST = ["Alex", "Priya", "Marcus", "Yuki", "Sofia", "Daniel", "Nadia", "Tomas",
         "Grace", "Omar", "Elena", "Kwame", "Ingrid", "Rafael", "Mei", "Jonas"]
LAST = ["Okafor", "Lindqvist", "Varga", "Rahman", "Castellanos", "Novak",
        "Adeyemi", "Fischer", "Moreau", "Tanaka", "Silva", "Haddad",
        "Kowalski", "Bergström", "Nkosi", "Duarte"]


def recency_weights(quarters: int = 8) -> list[float]:
    """Normalised exponential decay, most recent quarter first."""
    raw = [0.75 ** i for i in range(quarters)]
    total = sum(raw)
    return [r / total for r in raw]


def allocate_interactions(total: int, anchors: list[str], dense_anchor: str,
                          dense_share: float) -> dict[str, int]:
    """Interactions per anchor, with one anchor deliberately concentrated."""
    dense = int(total * dense_share)
    remaining = total - dense
    others = [a for a in anchors if a != dense_anchor]
    base, extra = divmod(remaining, len(others))
    alloc = {dense_anchor: dense}
    for i, anchor in enumerate(others):
        alloc[anchor] = base + (1 if i < extra else 0)
    return alloc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    rng = random.Random(SEED)

    roster = json.loads((SCREEN / "wave10_persons.json").read_text())["persons"]
    people_by_lei: dict[str, list[dict]] = {}
    for person in roster:
        if person["owner_kind"] != "natural":
            continue
        # A person can hold two roles at the SAME LEI (director + officer is
        # common). Iterating `person["roles"]` directly would append them
        # once per role and double-count them into that anchor's roster,
        # inflating `eligible` participants, the dense-anchor selection, and
        # the coverage-gap selection. Dedupe to one append per distinct LEI.
        for lei in dict.fromkeys(role["lei"] for role in person["roles"]):
            people_by_lei.setdefault(lei, []).append(person)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei FROM "{PG_SCHEMA_V2}".legal_entity '
                    "WHERE is_anchor ORDER BY lei")
        anchors = [r[0] for r in cur.fetchall()]
        cur.execute(f'SELECT deal_id, lei FROM "{PG_SCHEMA_V2}".deal ORDER BY deal_id')
        deals_by_lei: dict[str, list[str]] = {}
        for deal_id, lei in cur.fetchall():
            deals_by_lei.setdefault(lei, []).append(deal_id)

    # The dense anchor is the one with the most client-side people, so the
    # concentration is plausible rather than arbitrary.
    dense_anchor = max(anchors, key=lambda l: len(people_by_lei.get(l, [])))

    bankers = [{
        "banker_id": f"BKR{i:03d}",
        "full_name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
        "role": ROLES[i % len(ROLES)],
        "seniority": rng.choice(SENIORITY),
        "desk": rng.choice(["CIB Coverage", "Leveraged Finance", "Treasury Services",
                            "Credit Risk", "M&A Advisory"]),
        "provenance": "synthetic — internal",
    } for i in range(BANKER_COUNT)]

    assignments = []
    for lei in anchors:
        primary = rng.choice([b for b in bankers if b["role"] == "coverage"])
        assignments.append({"banker_id": primary["banker_id"], "lei": lei,
                            "is_primary": True,
                            "assigned_date": str(date(2024, 1, 15)),
                            "provenance": "synthetic — internal"})
        for extra in rng.sample([b for b in bankers
                                 if b["banker_id"] != primary["banker_id"]], 2):
            assignments.append({"banker_id": extra["banker_id"], "lei": lei,
                                "is_primary": False,
                                "assigned_date": str(date(2024, 6, 1)),
                                "provenance": "synthetic — internal"})

    alloc = allocate_interactions(INTERACTION_TOTAL, anchors, dense_anchor, DENSE_SHARE)
    weights = recency_weights(quarters=MONTHS // 3)
    today = date(2026, 8, 18)

    # Coverage gaps: senior client officers deliberately excluded from every
    # interaction. §F wants >= 3, and the gap IS the insight the product sells.
    gap_people: list[dict] = []
    for lei in anchors:
        seniors = [p for p in people_by_lei.get(lei, [])
                   if any(r.get("officer_title") for r in p["roles"])]
        if seniors and len(gap_people) < COVERAGE_GAP_COUNT:
            gap_people.append({"person_key": seniors[0]["person_key"], "lei": lei,
                               "provenance": "synthetic — engineered",
                               "note": "withheld from every interaction to create "
                                       "a coverage gap"})
    gap_keys = {g["person_key"] for g in gap_people}

    interactions, participants = [], []
    counter = 0
    for lei, count in alloc.items():
        eligible = [p for p in people_by_lei.get(lei, [])
                    if p["person_key"] not in gap_keys]
        covering = [a["banker_id"] for a in assignments if a["lei"] == lei]
        if not eligible or not covering:
            continue
        for _ in range(count):
            counter += 1
            quarter = rng.choices(range(len(weights)), weights=weights, k=1)[0]
            day_offset = quarter * 91 + rng.randrange(91)
            interaction_id = f"INT-W10-{counter:05d}"
            deals = deals_by_lei.get(lei, [])
            interactions.append({
                "interaction_id": interaction_id,
                "lei": lei,
                "deal_id": rng.choice(deals) if deals and rng.random() < 0.25 else None,
                "interaction_type": rng.choice(["client_meeting", "diligence_call",
                                                "pitch", "check_in"]),
                "channel": rng.choice(CHANNELS),
                "subject": "client coverage interaction",
                "interaction_date": str(today - timedelta(days=day_offset)),
                "mnpi_bearing": False,
                "need_to_know": False,
                "provenance": "synthetic — internal",
            })
            for person in rng.sample(eligible, min(len(eligible), rng.randint(1, 3))):
                participants.append({"interaction_id": interaction_id,
                                     "party_kind": "person",
                                     "party_key": person["person_key"],
                                     "provenance": "synthetic — internal"})
            for banker_id in rng.sample(covering, min(len(covering), 2)):
                participants.append({"interaction_id": interaction_id,
                                     "party_kind": "banker",
                                     "party_key": banker_id,
                                     "provenance": "synthetic — internal"})

    for interaction in rng.sample(interactions, NEED_TO_KNOW_COUNT):
        interaction["need_to_know"] = True
        interaction["provenance"] = "synthetic — engineered"

    weights_rows = [
        {"weight_name": name, "weight_value": value, "policy_version": "v1.0.0",
         "effective_date": "2026-01-01", "provenance": "synthetic — internal"}
        for name, value in [("recency_half_life_days", 90.0),
                            ("frequency_weight", 0.35),
                            ("seniority_weight", 0.25),
                            ("channel_meeting_weight", 1.0),
                            ("channel_call_weight", 0.6),
                            ("channel_email_weight", 0.3)]]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": SEED,
        "dense_anchor": dense_anchor,
        "bankers": bankers,
        "coverage_assignments": assignments,
        "interactions": interactions,
        "participants": participants,
        "scoring_weights": weights_rows,
        "coverage_gaps": gap_people,
    }
    print(f"  {len(bankers)} bankers · {len(assignments)} assignments · "
          f"{len(interactions)} interactions · {len(participants)} participants")
    print(f"  dense anchor {dense_anchor}: {alloc[dense_anchor]} interactions")
    print(f"  coverage gaps: {len(gap_people)} · need-to-know: {NEED_TO_KNOW_COUNT}")

    if args.dry_run:
        print("  [dry-run] nothing written")
        return 0
    (SCREEN / "wave10_coverage.json").write_text(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
