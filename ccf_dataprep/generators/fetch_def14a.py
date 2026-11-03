#!/usr/bin/env python3
"""Fetch DEF 14A proxies and find how each renders names we already hold.

48 of 50 anchors file a proxy; the two that do not are MLPs, which hold no
annual meeting. They lose nothing — Form 4 already supplied their roster.

This is the ENRICHMENT pass, not the discovery pass. Yield is measured against
the known roster, so a shortfall costs variants rather than people.

    uv run generators/fetch_def14a.py --dry-run
    uv run generators/fetch_def14a.py
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import SourceManifest, fetch, get_json

SCREEN = REPO_ROOT / "sources" / "screening"
DEF14A_ROOT = REPO_ROOT / "sources" / "def14a"


def strip_html(raw: str) -> str:
    """Tags out, entities decoded, whitespace collapsed — cells stay separated."""
    without_scripts = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    spaced = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    return re.sub(r"\s+", " ", html.unescape(spaced)).strip()


def find_renderings(text: str, roster: list[dict], *, source: str) -> list[dict]:
    """For each roster member, the document's own rendering of their name.

    Bounded search: the answer set is the roster. A person the document does not
    mention yields nothing, and is never invented.
    """
    found: list[dict] = []
    for person in roster:
        last, first = person["last"], person["first"]
        if not last or not first:
            continue
        initial = re.escape(first[0])
        pattern = re.compile(
            rf"\b((?:{re.escape(first)}|{initial}\.?)"
            rf"(?:\s+[A-Z][a-zA-Z.'-]*)?\s+{re.escape(last)})\b",
            re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            continue
        variant = re.sub(r"\s+", " ", match.group(1)).strip()
        if variant.lower() == person["name_as_filed"].lower():
            continue
        found.append({
            "person_key": person["person_key"],
            "variant_name": variant,
            "source": source,
            "rendering": "display_order",
            "provenance": "public",
        })
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    roster_doc = json.loads((SCREEN / "wave10_persons.json").read_text())
    by_lei: dict[str, list[dict]] = {}
    for person in roster_doc["persons"]:
        if person["owner_kind"] != "natural":
            continue
        # A person can hold two roles (e.g. director + officer) at the same
        # LEI. Each LEI must see them once, or the search below matches twice
        # and manufactures a duplicate rendering out of nothing.
        for lei in dict.fromkeys(role["lei"] for role in person["roles"]):
            by_lei.setdefault(lei, []).append(person)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{PG_SCHEMA_V2}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()

    manifest = SourceManifest(
        source="def14a",
        description="EDGAR DEF 14A proxy statements for the anchor cast — "
                     "used to find document renderings of already-held names",
        licence="US government work / public filing",
    )
    variants: list[dict] = []
    no_proxy: list[str] = []

    for lei, cik in anchors:
        submissions = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        # EDGAR `recent`-only: the index caps at ~1000 filings per issuer and
        # shards the remainder into `filings.files[]`, which this sweep does NOT
        # read. 40 of the 50 anchors have unread shards, so results here are a
        # FLOOR on the issuer's history, never the complete public record.
        # Estate-wide pattern across 7 fetchers; see docs/known-issues.md §9.11.
        recent = submissions["filings"]["recent"]
        rows = [(a, d, p) for f, a, d, p in zip(
            recent["form"], recent["accessionNumber"],
            recent["filingDate"], recent["primaryDocument"])
            if f.startswith("DEF 14A")]
        if not rows:
            no_proxy.append(lei)
            print(f"  [none ] {lei}: no DEF 14A (expected for an MLP)")
            continue

        accession, filing_date, primary = rows[0]
        url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
               f"{accession.replace('-', '')}/{primary}")
        filename = f"{int(cik):010d}_{accession}.htm"
        if args.dry_run:
            print(f"  [plan  ] {lei}: {url}")
            continue

        path = fetch(url, manifest, filename, is_sec=True)
        text = strip_html(path.read_text(encoding="utf-8", errors="replace"))
        roster = by_lei.get(lei, [])
        hits = find_renderings(text, roster, source="def14a")
        variants.extend(hits)
        print(f"  [ok    ] {lei}: {len(hits)} renderings from {len(roster)} roster")

    if args.dry_run:
        print("  [dry-run] nothing fetched or written")
        return 0

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR DEF 14A",
        "anchors_without_a_proxy": no_proxy,
        "variants": variants,
    }
    (SCREEN / "wave10_name_variants.json").write_text(json.dumps(payload, indent=2))
    print(f"\n  {len(variants)} renderings · {len(no_proxy)} anchors without a proxy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
