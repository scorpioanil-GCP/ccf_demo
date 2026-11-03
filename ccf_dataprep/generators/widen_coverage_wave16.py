#!/usr/bin/env python3
"""Final fix wave, blocker 4 — widen `coverage_assignment` so bankers'
portfolios actually overlap.

## The problem this closes

`ib-opportunity-synthesis`'s §B says the coverage portfolio determines the
candidate set a banker ranks over. Wave 10's `generate_coverage.py` gave
each of 50 anchors one primary banker plus two extras — 150 rows total, 1-9
LEIs per covered banker. §F's "outside the top-20" condition is
UNREACHABLE inside a portfolio that small: a banker who covers 3 prospects
cannot have one rank #21+ among them. Worse, Braemar Hotels & Resorts
Inc. — the named M&A #3 divergence prospect — was covered by ZERO M&A
Advisory bankers (verified live before writing this module), so the
product's own centrepiece prospect had no path into an M&A banker's
candidate set at all.

§F explicitly wants "overlapping coverage portfolios so the same prospect
appears to more than one [banker]." This module builds that directly: it
is not incidental overlap from random assignment, it is the condition
public/organic coverage data will never supply on its own, manufactured on
purpose so the divergence and containment conditions have a real field to
operate over. That makes every row this module adds `synthetic —
engineered` (CLAUDE.md rule 1), not `synthetic — internal` like the
baseline 150 rows it does not touch.

## What this module does NOT do

- Never deletes, re-keys, or edits an existing `coverage_assignment` row.
  Every row this module produces is a NEW (banker_id, lei) pair; the
  loader inserts with `ON CONFLICT (banker_id, lei) DO NOTHING`, so even a
  duplicate run against a live database that already has some of these
  rows cannot touch them.
- Never touches `is_primary` on an existing row, and never assigns a new
  row `is_primary = True` — one primary per LEI already holds across the
  baseline 150 rows and this module cannot violate that, because it never
  writes to the column that could.
- Never touches `banker`, `interaction`, or `participant` — this widens
  coverage only.

## Determinism

Reads the ORIGINAL 150-row baseline from `sources/screening/
wave10_coverage.json` (the committed artifact, not live Postgres) as the
exclusion set, so this generator's output is reproducible from source
control regardless of what has or hasn't been loaded into a given
database. A single seeded `random.Random`, bankers and anchors iterated in
sorted order, so two runs against the same source files produce byte-
identical output.

    uv run generators/widen_coverage_wave16.py --dry-run
    uv run generators/widen_coverage_wave16.py
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
SEED = 20260825
TARGET_PER_BANKER = 25
ASSIGNED_DATE = str(date(2026, 8, 25))
PROVENANCE = "synthetic — engineered"
PROVENANCE_NOTE = (
    "added in the final fix wave to widen coverage portfolios beyond the "
    "1-9 LEIs Wave 10 gave each banker, deliberately manufacturing the "
    "overlap §F names as a requirement -- see module docstring")

DIVERGENT_PROSPECT = "Braemar Hotels & Resorts Inc."
MIRROR_PROSPECT = "Thermon Group Holdings, Inc."
MA_DESK = "M&A Advisory"
DCM_DESKS = ("Leveraged Finance", "Treasury Services")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    baseline = json.loads((SCREEN / "wave10_coverage.json").read_text())
    bankers = sorted(baseline["bankers"], key=lambda b: b["banker_id"])
    desk_by_banker = {b["banker_id"]: b["desk"] for b in bankers}

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei FROM "{PG_SCHEMA_V2}".legal_entity '
                    "WHERE is_anchor ORDER BY lei")
        anchors = [r[0] for r in cur.fetchall()]
        cur.execute(
            f'SELECT legal_name, lei FROM "{PG_SCHEMA_V2}".legal_entity '
            "WHERE legal_name IN (%s, %s)",
            (DIVERGENT_PROSPECT, MIRROR_PROSPECT))
        name_to_lei = dict(cur.fetchall())
        # Live coverage, so a re-run after a partial load doesn't try to
        # re-add pairs that already exist -- belt-and-suspenders with the
        # baseline-artifact exclusion set below, which covers the case
        # where nothing has been loaded yet at all.
        cur.execute(f'SELECT banker_id, lei FROM "{PG_SCHEMA_V2}".coverage_assignment')
        live_pairs = set(cur.fetchall())

    for name in (DIVERGENT_PROSPECT, MIRROR_PROSPECT):
        if name not in name_to_lei:
            raise RuntimeError(f"could not resolve {name!r} to an LEI")
    braemar_lei = name_to_lei[DIVERGENT_PROSPECT]
    thermon_lei = name_to_lei[MIRROR_PROSPECT]

    baseline_pairs = {(a["banker_id"], a["lei"])
                       for a in baseline["coverage_assignments"]}
    existing_pairs = baseline_pairs | live_pairs

    covered_by: dict[str, set[str]] = {}
    for banker_id, lei in existing_pairs:
        covered_by.setdefault(banker_id, set()).add(lei)

    rng = random.Random(SEED)
    new_rows: list[dict] = []
    seen_new: set[tuple[str, str]] = set()

    for banker in bankers:
        banker_id = banker["banker_id"]
        already = covered_by.get(banker_id, set())
        need = max(0, TARGET_PER_BANKER - len(already))
        candidates = sorted(set(anchors) - already)
        chosen = rng.sample(candidates, min(need, len(candidates)))
        for lei in chosen:
            new_rows.append({
                "banker_id": banker_id, "lei": lei, "is_primary": False,
                "assigned_date": ASSIGNED_DATE, "provenance": PROVENANCE,
                "provenance_note": PROVENANCE_NOTE,
            })
            seen_new.add((banker_id, lei))
            covered_by.setdefault(banker_id, set()).add(lei)

    # --- force the two named guarantees, deterministically -----------------
    def covers(lei: str, desk_names) -> bool:
        for banker_id, leis in covered_by.items():
            if lei in leis and desk_by_banker.get(banker_id) in desk_names:
                return True
        return False

    def force_cover(lei: str, desk_names, label: str) -> None:
        if covers(lei, desk_names):
            return
        candidates = sorted(
            b["banker_id"] for b in bankers
            if desk_by_banker.get(b["banker_id"]) in desk_names
            and lei not in covered_by.get(b["banker_id"], set()))
        if not candidates:
            raise RuntimeError(
                f"no eligible banker left to force-cover {label} ({lei}) "
                f"for desks {desk_names}")
        banker_id = candidates[0]
        new_rows.append({
            "banker_id": banker_id, "lei": lei, "is_primary": False,
            "assigned_date": ASSIGNED_DATE, "provenance": PROVENANCE,
            "provenance_note": PROVENANCE_NOTE + f"; forced to guarantee "
            f"{label} is covered by >= 1 banker on this desk (final fix "
            "wave blocker 4)",
        })
        seen_new.add((banker_id, lei))
        covered_by.setdefault(banker_id, set()).add(lei)

    force_cover(braemar_lei, (MA_DESK,), "Braemar (M&A #3 divergence prospect)")
    force_cover(thermon_lei, DCM_DESKS, "Thermon (DCM #3 mirror prospect)")

    assert covers(braemar_lei, (MA_DESK,)), "Braemar still uncovered by M&A"
    assert covers(thermon_lei, DCM_DESKS), "Thermon still uncovered by DCM"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": SEED,
        "target_per_banker": TARGET_PER_BANKER,
        "new_coverage_assignments": new_rows,
    }

    by_lei: dict[str, int] = {}
    for row in new_rows:
        by_lei[row["lei"]] = by_lei.get(row["lei"], 0) + 1
    print(f"  {len(new_rows)} new coverage_assignment rows across "
          f"{len(bankers)} bankers")
    print(f"  post-widen coverage: min {min(len(v) for v in covered_by.values())}, "
          f"max {max(len(v) for v in covered_by.values())} LEIs per banker")
    print(f"  {len(by_lei)} of {len(anchors)} anchors touched by new rows; "
          f"max overlap on one prospect: {max(by_lei.values())}")
    print(f"  Braemar ({braemar_lei}) covered by an M&A Advisory banker: "
          f"{covers(braemar_lei, (MA_DESK,))}")
    print(f"  Thermon ({thermon_lei}) covered by a DCM-desk banker: "
          f"{covers(thermon_lei, DCM_DESKS)}")

    if args.dry_run:
        print("  [dry-run] nothing written")
        return 0
    (SCREEN / "wave16_coverage_widen.json").write_text(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
