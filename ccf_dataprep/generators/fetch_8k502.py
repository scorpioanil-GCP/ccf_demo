#!/usr/bin/env python3
"""Appointment and departure dates from 8-K Item 5.02.

Selection costs nothing: the EDGAR submissions index carries an `items` field
per filing, so Item 5.02 is a string match on METADATA. Only matching filings
are fetched, and each is searched for surnames already on the roster.

    uv run generators/fetch_8k502.py --dry-run
    uv run generators/fetch_8k502.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import SourceManifest, fetch, get_json
from generators.fetch_def14a import strip_html

SCREEN = REPO_ROOT / "sources" / "screening"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-per-issuer", type=int, default=12)
    args = ap.parse_args()

    roster_doc = json.loads((SCREEN / "wave10_persons.json").read_text())
    by_lei: dict[str, list[dict]] = {}
    for person in roster_doc["persons"]:
        if person["owner_kind"] != "natural":
            continue
        # A person can hold two roles (e.g. director + officer) at the same
        # LEI. Each LEI must see them once, or the search below matches twice
        # and manufactures a duplicate appointment record out of nothing.
        for lei in dict.fromkeys(role["lei"] for role in person["roles"]):
            by_lei.setdefault(lei, []).append(person)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{PG_SCHEMA_V2}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()

    manifest = SourceManifest(
        source="form8k502",
        description="EDGAR 8-K Item 5.02 filings for the anchor cast — "
                     "officer/director appointment and departure dates",
        licence="US government work / public filing",
    )
    appointments: list[dict] = []

    for lei, cik in anchors:
        submissions = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        # EDGAR `recent`-only: the index caps at ~1000 filings per issuer and
        # shards the remainder into `filings.files[]`, which this sweep does NOT
        # read. 40 of the 50 anchors have unread shards, so results here are a
        # FLOOR on the issuer's history, never the complete public record.
        # Estate-wide pattern across 7 fetchers; see docs/known-issues.md §9.11.
        recent = submissions["filings"]["recent"]
        items = recent.get("items", [""] * len(recent["form"]))
        rows = [(a, d, p) for f, a, d, p, it in zip(
            recent["form"], recent["accessionNumber"], recent["filingDate"],
            recent["primaryDocument"], items)
            if f == "8-K" and "5.02" in (it or "")][:args.max_per_issuer]
        print(f"  {lei}: {len(rows)} Item 5.02 filings")
        if args.dry_run:
            continue

        for accession, filing_date, primary in rows:
            url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                   f"{accession.replace('-', '')}/{primary}")
            path = fetch(url, manifest, f"{int(cik):010d}_{accession}.htm", is_sec=True)
            text = strip_html(path.read_text(encoding="utf-8", errors="replace"))
            for person in by_lei.get(lei, []):
                last = person["last"]
                if not last or not re.search(rf"\b{re.escape(last)}\b", text,
                                             re.IGNORECASE):
                    continue
                appointments.append({
                    "person_key": person["person_key"],
                    "lei": lei,
                    "appointment_date": filing_date,
                    "accession": accession,
                    "item": "5.02",
                    "provenance": "public",
                })

    if args.dry_run:
        print("  [dry-run] nothing fetched or written")
        return 0

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR 8-K Item 5.02",
        "appointments": appointments,
    }
    (SCREEN / "wave10_appointments.json").write_text(json.dumps(payload, indent=2))
    print(f"\n  {len(appointments)} appointment records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
