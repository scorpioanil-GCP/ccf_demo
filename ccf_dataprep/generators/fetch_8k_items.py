#!/usr/bin/env python3
"""Wave 11b — 8-K item events for the anchor cast.

Selection costs nothing: the EDGAR submissions index carries an `items` field
per filing, so all six item types are a string match on METADATA. No
full-text search, and therefore none of the paging traps that cost Wave 11a a
wrong diagnosis.

READS THE SHARDS. `filings.recent` caps at ~1000 filings per issuer and
shards the remainder into `filings.files[]`. `known-issues.md` §9.11 records
that 40 of 50 anchors have unread shards, making every prior sweep a FLOOR.
Item 2.04 is rare enough (58 filings across the whole cast, all history) that
a floor can hide it entirely, so this sweep reads the shards too.

    uv run generators/fetch_8k_items.py --dry-run
    uv run generators/fetch_8k_items.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import get_json

SCREEN = REPO_ROOT / "sources" / "screening"

# Decision D1, docs/wave11b-design.md §0. Fixed constants, never a rolling
# window: a rolling window makes the dataset depend on the day it was built.
WINDOW_START = "2024-08-19"
WINDOW_END = "2026-08-19"

# 2.01 added 2026-08-24 (Wave 16). `ib-opportunity-synthesis` §C assigns
# "M&A and material-agreement events / EDGAR 8-K Items 1.01 / 2.01" to Fluree.
# 1.01 is entry into a material agreement; 2.01 is completion of an
# acquisition or disposition -- an announced deal and a closed one are
# different signals about the same prospect, and the M&A ranking needs both.
ITEM_CODES: tuple[str, ...] = ("1.01", "2.01", "2.03", "2.04", "4.01", "4.02", "5.02")


def in_window(filing_date: str) -> bool:
    """ISO dates compare correctly as strings; both bounds inclusive."""
    return WINDOW_START <= filing_date <= WINDOW_END


def matching_items(items_field: str | None) -> list[str]:
    """Which wanted codes this filing carries.

    Token match, not substring: EDGAR renders "5.02,9.01", and a substring
    test for "4.01" would also fire on "14.01".
    """
    if not items_field:
        return []
    tokens = {t.strip() for t in items_field.split(",") if t.strip()}
    return [code for code in ITEM_CODES if code in tokens]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{PG_SCHEMA_V2}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()

    events: list[dict] = []
    shard_reads = 0
    for lei, cik in anchors:
        sub = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        blocks = [sub["filings"]["recent"]]
        for shard in sub["filings"].get("files", []):
            blocks.append(get_json(
                f"https://data.sec.gov/submissions/{shard['name']}", is_sec=True))
            shard_reads += 1

        found = 0
        for block in blocks:
            forms = block.get("form", [])
            items = block.get("items", [""] * len(forms))
            # strict=True: a ragged block (any parallel array shorter than
            # `form`) raises instead of truncating silently. Same lesson as
            # Wave 11a's Treasury par-curve zip guard — a quietly short
            # dataset is worse than a loud crash. The `items` default above
            # keeps the normal (key-absent) path from tripping this.
            for form, acc, date, primary, it in zip(
                    forms, block.get("accessionNumber", []),
                    block.get("filingDate", []),
                    block.get("primaryDocument", []), items,
                    strict=True):
                if form != "8-K" or not in_window(date):
                    continue
                for code in matching_items(it):
                    events.append({
                        "lei": lei, "cik": cik, "item": code,
                        "accession": acc, "filing_date": date,
                        "primary_document": primary,
                        "provenance": "public",
                    })
                    found += 1
        print(f"  {lei}: {found} in-window item events", flush=True)

    print(f"\n  shard files read: {shard_reads}")
    print(f"  {len(events)} events across "
          f"{len({e['lei'] for e in events})} obligors")

    if args.dry_run:
        print("  [dry-run] nothing written")
        return 0

    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave11b_8k_events.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR submissions index, `items` field, recent + shards",
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "events": events,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
