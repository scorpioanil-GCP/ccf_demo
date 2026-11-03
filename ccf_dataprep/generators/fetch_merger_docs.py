#!/usr/bin/env python3
"""Wave 16 — merger proxies and merger-registration documents.

§C assigns two rows to MongoDB:

    Merger proxies and deal terms          EDGAR DEF 14A / DEFM14A
    IPO and merger registration pipeline   EDGAR S-1 / S-4

## S-1 is dropped, and this is the evidence

Probed 2026-08-24 across all 53 anchors carrying a CIK: 43 `S-1` filings
lifetime, and ZERO since 2023. That is a fact about the cast -- established
issuers do not file IPO registrations -- not a gap in the fetch. `S-4` covers
the merger-registration half of the same row, so the row is partially and
honestly accounted for, and `validators/spec_coverage.py` records it as a
NAMED GAP rather than a silent one.

`DEF 14A` is already on disk (49 files, `sources/def14a/`) from an earlier
wave. This fetcher adds the MERGER proxies specifically -- DEFM14A and PREM14A
-- which carry deal terms rather than routine annual-meeting business.

The window's top bound is `ccf.config.AS_OF_IB` -- Wave 16's pinned as-of
instant, NOT the wall clock. A re-run after that date must still see the same
corpus, or the pinned ranking would sit on top of a shifting document set.

    uv run generators/fetch_merger_docs.py --dry-run
    uv run generators/fetch_merger_docs.py
"""
from __future__ import annotations

import argparse
import collections
import json
import sys

from ccf.config import AS_OF_IB
from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import pg_connect
from ccf.fetch import SOURCES_ROOT, SourceManifest, fetch, get_json

#: `S-1` is deliberately absent. See the module docstring.
FORMS: tuple[str, ...] = ("DEFM14A", "PREM14A", "S-4", "S-4/A")

WINDOW_START = "2024-08-19"
#: Top bound is the wave's pinned as-of, not today() -- see module docstring.
WINDOW_END = AS_OF_IB


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{S}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()

    docs: list[dict] = []
    for n, (lei, cik) in enumerate(anchors, 1):
        # Progress with flush=True. This walk is minutes long, and a fetcher
        # that prints only on completion is indistinguishable from a hang --
        # which invites an operator to kill it and lose rate-limited work.
        print(f"  [{n}/{len(anchors)}] {lei}", flush=True)
        sub = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        blocks = [sub["filings"]["recent"]]
        for shard in sub["filings"].get("files", []):
            blocks.append(get_json(
                f"https://data.sec.gov/submissions/{shard['name']}", is_sec=True))
        for block in blocks:
            for form, acc, date, primary in zip(
                    block.get("form", []), block.get("accessionNumber", []),
                    block.get("filingDate", []),
                    block.get("primaryDocument", []), strict=True):
                if (form.strip().upper() in FORMS
                        and WINDOW_START <= date <= WINDOW_END):
                    docs.append({
                        "lei": lei, "cik": int(cik), "form": form.strip().upper(),
                        "accession": acc, "filing_date": date,
                        "primary_document": primary, "provenance": "public",
                    })

    by_form = collections.Counter(d["form"] for d in docs)
    print("Wave 16 — merger proxies and S-4 registrations\n")
    print(f"  window {WINDOW_START} .. {WINDOW_END} (pinned as-of)")
    for f in FORMS:
        print(f"    {f:10s} {by_form[f]:>4}")
    print(f"  total {len(docs)} across {len({d['lei'] for d in docs})} entities")
    print("\n  S-1: NOT fetched. 43 lifetime, 0 since 2023 -- the cast are "
          "established issuers. Recorded as a named gap in spec_coverage.py.")

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    manifest = SourceManifest(
        source="merger_docs",
        description="EDGAR merger proxies (DEFM14A/PREM14A) and "
                     "merger-registration statements (S-4/S-4/A) for the "
                     "anchor cast -- deal-term documents for the M&A "
                     "opportunity product",
        licence="US government work / public filing",
    )
    for i, d in enumerate(docs, 1):
        nodash = d["accession"].replace("-", "")
        url = (f"https://www.sec.gov/Archives/edgar/data/{d['cik']}/{nodash}/"
               f"{d['primary_document']}")
        filename = f"{d['cik']:010d}_{d['accession']}_{d['primary_document']}"
        try:
            path = fetch(url, manifest, filename, is_sec=True)
            d["path"] = str(path.relative_to(SOURCES_ROOT))
            print(f"    [{i}/{len(docs)}] ok   {filename}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"    [{i}/{len(docs)}] MISS {d['accession']}: {exc}", flush=True)
            d["path"] = None

    got = sum(1 for d in docs if d["path"])
    missed = len(docs) - got
    out = SOURCES_ROOT / "screening" / "wave16_merger_docs.json"
    out.write_text(json.dumps({
        "source": "SEC EDGAR submissions index + Archives",
        "forms": list(FORMS),
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "s1_excluded_because": "43 lifetime, 0 since 2023 across the anchor set",
        "documents": docs,
    }, indent=1))
    print(f"\n  downloaded {got}/{len(docs)} ({missed} failed); wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
