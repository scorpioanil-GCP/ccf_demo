#!/usr/bin/env python3
"""Wave 16 — Schedule 13D activist stakes against the anchor set.

## Two form names, one form

The SEC's structured-XML mandate renamed Schedule 13D in December 2024. Filings
before that are `SC 13D` / `SC 13D/A`; after, `SCHEDULE 13D` / `SCHEDULE 13D/A`.

Matching only the legacy string returns ZERO filings after 2024-12-06 -- which
reads exactly like a dead source and is not one. Both eras are matched, and a
count is printed per era so a future rename is visible as a cliff rather than a
silence.

## Direction — resolved per row, not sampled (fix round 1)

A Schedule 13D is filed BY an activist ABOUT a subject company. The first
version of this script sampled the 12 most recent filings to check that
assumption and found `SUBJECT` in all 12 -- but that pre-design probe matched
only the LEGACY form names, so its sample silently excluded every modern-era
filing, which is exactly where an anchor turns out to sometimes be the FILER
(the two freshest rows in the full dataset, both modern-era, are both FILER).
A sampled check cannot serve as a filter: direction is a PER-ROW property, not
a population property. So `role` is now resolved for EVERY filing, not a
sample, and the artifact records SUBJECT / FILER / UNKNOWN honestly per row --
UNKNOWN is never defaulted to SUBJECT, because downstream filters on
`role == "SUBJECT"` and a silently-usable UNKNOWN would defeat that filter.

    uv run generators/fetch_schedule13d.py --dry-run
    uv run generators/fetch_schedule13d.py
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import pg_connect
from ccf.fetch import SOURCES_ROOT, get, get_json

#: Both eras. Order is display order, not precedence.
FORMS: tuple[str, ...] = ("SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A")

_SUBJECT = re.compile(r"SUBJECT COMPANY:.*?CENTRAL INDEX KEY:\s*(\d+)", re.S)
_FILED_BY = re.compile(r"FILED BY:.*?CENTRAL INDEX KEY:\s*(\d+)", re.S)


def matches(form: str) -> bool:
    """Exact membership, never substring.

    Substring would make `SCHEDULE 13D` swallow `SCHEDULE 13D-X` if the SEC
    ever mints one, and would match `SC 13D` inside longer strings.
    """
    return form.strip().upper() in FORMS


def header_role(cik: int, accession: str) -> str:
    """SUBJECT, FILER, or UNKNOWN, read from the submission header.

    Resolved from the header rather than `index.json`, which has been observed
    to omit a real, fetchable exhibit. UNKNOWN means the header could not be
    fetched or parsed -- it is never defaulted to SUBJECT, because downstream
    filters on `role == "SUBJECT"` and a silently-usable UNKNOWN would defeat
    that filter.
    """
    nodash = accession.replace("-", "")
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/"
           f"{accession}-index-headers.html")
    try:
        text = get(url, is_sec=True).text
    except Exception:  # noqa: BLE001 — a missing header is not a missing filing
        return "UNKNOWN"
    subject = _SUBJECT.search(text)
    filed_by = _FILED_BY.search(text)
    if subject and int(subject.group(1)) == cik:
        return "SUBJECT"
    if filed_by and int(filed_by.group(1)) == cik:
        return "FILER"
    return "UNKNOWN"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{S}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()
        cur.execute(f'SELECT lei, legal_name FROM "{S}".legal_entity')
        names = dict(cur.fetchall())

    filings: list[dict] = []
    for i, (lei, cik) in enumerate(anchors, start=1):
        print(f"  [{i}/{len(anchors)}] {lei}", flush=True)
        sub = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        blocks = [sub["filings"]["recent"]]
        for shard in sub["filings"].get("files", []):
            blocks.append(get_json(
                f"https://data.sec.gov/submissions/{shard['name']}", is_sec=True))
        for block in blocks:
            for form, acc, date in zip(
                    block.get("form", []), block.get("accessionNumber", []),
                    block.get("filingDate", []), strict=True):
                if matches(form):
                    filings.append({
                        "lei": lei, "cik": int(cik), "form": form.strip().upper(),
                        "accession": acc, "filing_date": date,
                        "role": None, "provenance": "public",
                    })

    filings.sort(key=lambda f: (f["filing_date"], f["accession"]), reverse=True)

    # Direction resolved for EVERY filing. Fix round 1: a sample cannot serve
    # as a filter -- direction is a per-row property, and the two freshest
    # filings in the whole dataset turned out to be exactly the rows a sample
    # of the legacy-only era could never have seen.
    print(f"\n  resolving role for {len(filings)} filings "
          "(one header fetch each, ~8/s) ...", flush=True)
    for i, f in enumerate(filings, start=1):
        f["role"] = header_role(f["cik"], f["accession"])
        if i % 50 == 0 or i == len(filings):
            print(f"  roles: {i}/{len(filings)}", flush=True)

    era = collections.Counter(
        "modern" if f["form"].startswith("SCHEDULE") else "legacy" for f in filings)
    roles = collections.Counter(f["role"] for f in filings)

    # Per-entity FILER counts, so an entity that is mostly-filer is visible
    # at a glance rather than discovered downstream.
    filer_counts: dict[str, int] = collections.Counter()
    total_counts: dict[str, int] = collections.Counter()
    for f in filings:
        total_counts[f["lei"]] += 1
        if f["role"] == "FILER":
            filer_counts[f["lei"]] += 1

    print("Wave 16 — Schedule 13D\n")
    print(f"  anchors queried   {len(anchors):>5}")
    print(f"  filings           {len(filings):>5}  "
          f"across {len({f['lei'] for f in filings})} entities")
    print(f"    legacy `SC 13D*`      {era['legacy']:>5}")
    print(f"    modern `SCHEDULE 13D*`{era['modern']:>5}   "
          f"<- zero here means the form was renamed again")
    print(f"  role split (ALL filings)  {dict(roles)}")

    if filer_counts:
        print("\n  entities with any FILER-role filings "
              "(lei, name, filer/total):")
        for lei, n in sorted(filer_counts.items(), key=lambda kv: -kv[1]):
            print(f"    {lei}  {names.get(lei, '?'):<32}"
                  f"{n}/{total_counts[lei]}")
        print("\n  WARNING: at least one anchor is the FILER, not the "
              "subject, on at least one filing. The join the spec assumes "
              "does not hold for those rows.")

    if roles.get("UNKNOWN"):
        print(f"\n  NOTE: {roles['UNKNOWN']} filing(s) have role UNKNOWN "
              "(header unfetchable/unparseable). Left UNKNOWN, not "
              "defaulted to SUBJECT.")

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    out = SOURCES_ROOT / "screening" / "wave16_13d.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "source": "SEC EDGAR submissions index, both Schedule 13D form-name eras",
        "forms": list(FORMS),
        "retrieved_at": datetime.now(timezone.utc).date().isoformat(),
        "window": "no date filter applied -- all dates in the submissions "
                  "index were collected",
        "role_split": dict(roles),
        "filings": filings,
    }, indent=1))
    print(f"\n  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
