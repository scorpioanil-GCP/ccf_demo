#!/usr/bin/env python3
"""Fetch Form 4 XML for all 50 anchors, at the escalating lookback.

~2,000 requests at the harness's 8 req/s, roughly five minutes. Every payload
goes through `ccf.fetch.fetch()` so retrieval date, URL and sha256 are recorded
without anyone remembering to.

**Fetch the RAW XML, never `primaryDocument` verbatim** — see `form4.raw_form4_url`.

A single filing that cannot be fetched — even after `ccf.fetch.fetch()` has
retried transient errors — must not discard ~25 minutes of prior work. Each
per-filing fetch is wrapped: a failure is recorded in the index's `failures`
list and the run moves on. The index is written even on partial completion,
including when the main loop dies on an unexpected exception, because "these
47 issuers are complete, these 3 filings failed" is worth far more than no
index at all.

    uv run generators/fetch_form4.py --dry-run
    uv run generators/fetch_form4.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import SourceManifest, fetch, get_json
from generators.extract_persons import LOOKBACK_CAP
from generators.form4 import raw_form4_url, select_form4_filings

SCREEN = REPO_ROOT / "sources" / "screening"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lookback", type=int, default=LOOKBACK_CAP,
                    help="filings to fetch per issuer; extract_persons walks "
                         "down from here, so fetch the cap once")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{PG_SCHEMA_V2}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()
    print(f"  {len(anchors)} anchors with a CIK")

    manifest = SourceManifest(
        source="form4",
        description="SEC EDGAR Form 4 reporting-owner XML for the anchor cast",
        licence="US government work / public filing",
    ).load()
    index: dict = {"issuers": {}}
    failures: list[dict] = []

    def write_index() -> None:
        index["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        index["source"] = "SEC EDGAR Form 4"
        index["provenance"] = "public"
        index["failures"] = failures
        if args.dry_run:
            print("  [dry-run] nothing fetched or written")
            return
        SCREEN.mkdir(parents=True, exist_ok=True)
        (SCREEN / "wave10_form4_index.json").write_text(json.dumps(index, indent=2))
        print(f"  wrote {SCREEN / 'wave10_form4_index.json'}")

    try:
        for lei, cik in anchors:
            submissions = get_json(
                f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
            # EDGAR `recent`-only: the index caps at ~1000 filings per issuer and
            # shards the remainder into `filings.files[]`, which this sweep does NOT
            # read. 40 of the 50 anchors have unread shards, so results here are a
            # FLOOR on the issuer's history, never the complete public record.
            # Estate-wide pattern across 7 fetchers; see docs/known-issues.md §9.11.
            selected = select_form4_filings(submissions["filings"]["recent"], args.lookback)
            print(f"  {lei} cik={cik}: {len(selected)} Form 4 filings")

            filings = []
            for accession, filing_date, primary in selected:
                url = raw_form4_url(int(cik), accession, primary)
                # Flat filename, not a nested `cik/accession.xml` path:
                # `fetch()` only mkdirs the manifest's own directory, matching
                # the flat naming convention already used by fetch_ex10.py
                # and fetch_security_agreements.py.
                filename = f"{int(cik):010d}_{accession}.xml"
                if not args.dry_run:
                    try:
                        fetch(url, manifest, filename, is_sec=True)
                    except Exception as exc:
                        failures.append({
                            "lei": lei, "accession": accession, "url": url,
                            "error": type(exc).__name__,
                        })
                        print(f"  [failed] {filename}: {type(exc).__name__}: {exc}")
                        continue
                filings.append({"accession": accession, "filing_date": filing_date,
                                "path": filename, "url": url})
            index["issuers"][lei] = {"cik": f"{int(cik):010d}", "filings": filings}
    except Exception:
        write_index()
        raise

    write_index()
    if failures:
        print(f"  {len(failures)} filing(s) failed after retries — see "
              f"index['failures']")
    return 0


if __name__ == "__main__":
    sys.exit(main())
