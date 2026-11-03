#!/usr/bin/env python3
"""Wave 16 — the deal pipeline and client appetite history.

**Inserted by controller ruling F0.** `generate_ib_mandates.py` appeared in the
plan's file structure and in Task 11's consumes-list, but no task built it.
Two §C rows depend on it: "Deal pipeline -- live mandates and stage" and
"Client stated appetite and mandate history", both `synthetic — internal`,
both bound for Postgres.

## Why this half cannot be public

Every opportunity SIGNAL in this product is public: activist 13D filings,
maturity ladders, insider Form 4 activity, sector news -- any competitor can
observe all of it. What is not observable is the bank's own coverage graph,
its live mandates, and its client appetite history. Those live only inside
the institution's deal system and CRM. The product's entire value comes from
composing public signal against this proprietary position, which is exactly
why no vendor can assemble it from the outside.

## The rule that matters most: mandates attach only to covered entities

A mandate against an entity nobody at the bank covers asserts a client
relationship that does not exist. That is worse than a thin pipeline --
it would join cleanly against `coverage_assignment` and be silently wrong,
with nothing downstream able to detect it. So mandates are drawn only from
the LEIs that already appear in Postgres `coverage_assignment`.

## `last_outcome` and `stated_appetite`: absence is data, not a gap

`last_outcome` is set ONLY when `stage` is "closed" or "lost". A live
mandate (pitched / mandated / in-execution) has no outcome yet, and
inventing one would make the pipeline unreadable -- a "closed" stage could
then be wrongly inferred from a field that should be empty.

`stated_appetite` can be `None`, and that is meaningful, not missing data: a
client who has said nothing is different from one who has said no-appetite,
and the two must never be conflated into the same value.

## Determinism

`random.Random(SEED)` only -- never the global `random` module, never
unseeded. Two calls to `build()` return equal dicts (there is a test for
exactly this). No timestamp is embedded in `build()`'s return value; a
`generated_at` field, if wanted, belongs at write time, outside `build()`.

    uv run generators/generate_ib_mandates.py --dry-run
    uv run generators/generate_ib_mandates.py
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone

from ccf.config import IB_WINDOW_END, IB_WINDOW_START, PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, pg_connect

SEED = 16

MANDATE_TYPES = (
    "m&a-sellside", "m&a-buyside", "dcm-bond", "dcm-loan",
    "ecm-follow-on", "ratings-advisory",
)

# A funnel, not a flat spread -- more pitched than mandated, more mandated
# than in-execution, and closed/lost trail further still. Weights are
# relative draw frequency, not a target percentage.
STAGE_WEIGHTS = (
    ("pitched", 6),
    ("mandated", 4),
    ("in-execution", 3),
    ("closed", 2),
    ("lost", 2),
)
STAGES = tuple(s for s, _ in STAGE_WEIGHTS)

APPETITES = ("acquisitive", "deleveraging", "opportunistic", "no-appetite", None)

TARGET_MANDATES = 40


def _covered_leis() -> list[str]:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT DISTINCT lei FROM "{S}".coverage_assignment ORDER BY lei')
        return [r[0] for r in cur.fetchall()]


def _weighted_stage(rng: random.Random) -> str:
    stages, weights = zip(*STAGE_WEIGHTS)
    return rng.choices(stages, weights=weights, k=1)[0]


def _days_between(start: str, end: str) -> int:
    a = datetime.strptime(start, "%Y-%m-%d")
    b = datetime.strptime(end, "%Y-%m-%d")
    return (b - a).days


def _random_date_in_window(rng: random.Random) -> str:
    span = _days_between(IB_WINDOW_START, IB_WINDOW_END)
    offset = rng.randint(0, span)
    d = datetime.strptime(IB_WINDOW_START, "%Y-%m-%d")
    from datetime import timedelta
    return (d + timedelta(days=offset)).strftime("%Y-%m-%d")


def build() -> dict:
    """Build the mandate document. Pure function of SEED and the covered-LEI
    set read from Postgres -- no clock, no filesystem write, no randomness
    outside the seeded RNG. Two calls return equal dicts."""
    rng = random.Random(SEED)
    covered = _covered_leis()
    if not covered:
        raise RuntimeError("coverage_assignment has no rows -- run Task 10 first")

    # Attach 1-3 mandates to a subset of covered LEIs, enough to clear the
    # >= 30 floor with room to spare so the funnel weighting still leaves
    # every stage and every mandate_type non-empty.
    n_anchors = min(len(covered), max(15, -(-TARGET_MANDATES // 2)))
    anchors = rng.sample(covered, n_anchors)

    mandates: list[dict] = []
    counter = 0
    idx = 0
    while len(mandates) < TARGET_MANDATES:
        lei = anchors[idx % len(anchors)]
        idx += 1
        per_lei = rng.randint(1, 3)
        for _ in range(per_lei):
            if len(mandates) >= TARGET_MANDATES:
                break
            counter += 1
            stage = _weighted_stage(rng)
            mandate_type = rng.choice(MANDATE_TYPES)
            appetite = rng.choice(APPETITES)
            outcome = None
            if stage in ("closed", "lost"):
                outcome = "won" if stage == "closed" else rng.choice(
                    ["lost-to-competitor", "client-withdrew", "mandate-declined"])
            mandates.append({
                "mandate_id": f"MDT-{counter:04d}",
                "lei": lei,
                "mandate_type": mandate_type,
                "stage": stage,
                "opened_date": _random_date_in_window(rng),
                "stated_appetite": appetite,
                "last_outcome": outcome,
                "provenance": "synthetic — internal",
            })

    return {"mandates": mandates}


def _table(rows: list[dict], key: str, universe: tuple) -> dict[str, int]:
    counts = {v: 0 for v in universe}
    for r in rows:
        counts[r[key]] = counts.get(r[key], 0) + 1
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = build()
    mandates = doc["mandates"]
    distinct_entities = len({m["lei"] for m in mandates})

    print("Wave 16 — deal pipeline and appetite history\n")
    print(f"  mandates          {len(mandates):>4}")
    print(f"  distinct entities {distinct_entities:>4}")

    stage_counts = _table(mandates, "stage", STAGES)
    print("\n  per-stage:")
    for stage in STAGES:
        print(f"    {stage:14s} {stage_counts[stage]:>4}")

    type_counts = _table(mandates, "mandate_type", MANDATE_TYPES)
    print("\n  per-mandate_type:")
    for mt in MANDATE_TYPES:
        print(f"    {mt:16s} {type_counts[mt]:>4}")

    ok = True
    zero_stages = [s for s in STAGES if stage_counts[s] == 0]
    if zero_stages:
        print(f"\n  FAIL: stage(s) with zero rows: {zero_stages}")
        ok = False
    zero_types = [t for t in MANDATE_TYPES if type_counts[t] == 0]
    if zero_types:
        print(f"\n  FAIL: mandate_type(s) with zero rows: {zero_types}")
        ok = False
    if not ok:
        return 1

    live_with_outcome = [m for m in mandates
                          if m["stage"] not in ("closed", "lost")
                          and m["last_outcome"] is not None]
    if live_with_outcome:
        print(f"\n  FAIL: {len(live_with_outcome)} live mandate(s) carry a "
              f"last_outcome: {live_with_outcome[:3]}")
        return 1
    closed_without_outcome = [m for m in mandates
                               if m["stage"] in ("closed", "lost")
                               and m["last_outcome"] is None]
    if closed_without_outcome:
        print(f"\n  FAIL: {len(closed_without_outcome)} closed/lost mandate(s) "
              f"missing last_outcome: {closed_without_outcome[:3]}")
        return 1

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    out_doc = dict(doc)
    out_doc["generated_at"] = datetime.now(timezone.utc).isoformat()
    out_path = REPO_ROOT / "sources" / "screening" / "wave16_mandates.json"
    out_path.write_text(json.dumps(out_doc, indent=1))
    print(f"\n  wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
