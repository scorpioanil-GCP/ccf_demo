#!/usr/bin/env python3
"""Treasury par yield curve — the benchmark leg, and it is genuinely public.

The URL is PER CALENDAR YEAR, so 24 months of history spans three files.
Dates render MM/DD/YYYY, unlike FRED's ISO; `curves.py` parses both strictly
so neither can be silently coerced into the other.

Blank cells are real and are dropped rather than defaulted, because a 0%
benchmark point would distort every spread interpolated across it.

The header is NOT fixed across the window: the 2024 CSV has no `1.5 Month`
column at all, while 2025 and 2026 carry it and populate it on essentially
every row from 2025-02-18 onward — Treasury added a 6-week bill benchmark
mid-series. That is why this script reads the header fresh from each year's
file rather than hardcoding one: hardcoding it would zip a 15-column header
against 2024's 14-column rows, misaligning every tenor from that point on.
The per-file read below is what makes that schema change survivable.

    uv run generators/fetch_treasury.py --dry-run
    uv run generators/fetch_treasury.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch
from generators.curves import parse_treasury_row

SCREEN = REPO_ROOT / "sources" / "screening"
YEARS = [2024, 2025, 2026]
URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
       "daily-treasury-rates.csv/{year}/all"
       "?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = SourceManifest(
        source="treasury",
        description="US Treasury daily par yield curve — benchmark leg for spreads",
        licence="US Government work, public domain",
    )

    rows: list[dict] = []
    for year in YEARS:
        url = URL.format(year=year)
        if args.dry_run:
            print(f"  [plan] {url}")
            continue
        path = fetch(url, manifest, f"treasury-{year}.csv")
        text = path.read_text(encoding="utf-8", errors="replace")
        reader = csv.reader(text.splitlines())
        header = next(reader)
        n = 0
        for raw in reader:
            if not raw or not raw[0].strip():
                continue
            d, curve = parse_treasury_row(header, raw)
            rows.append({"date": d.isoformat(),
                         "tenors": {f"{k:.6f}": v for k, v in sorted(curve.items())}})
            n += 1
        print(f"  {year}: {n} curve dates")

    if args.dry_run:
        print("  [dry-run] nothing fetched or written")
        return 0

    rows.sort(key=lambda r: r["date"])
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "US Treasury daily par yield curve",
        "provenance": "public",
        "curve": rows,
    }
    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave11a_curve.json").write_text(json.dumps(payload, indent=2))
    print(f"\n  {len(rows)} curve dates, {rows[0]['date']} -> {rows[-1]['date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
