#!/usr/bin/env python3
"""FRED ICE BofA OAS by rating band — the public market factor.

Five series, verified 2026-08-19 at 794 daily rows each. On 2026-08-18 they
read AA 0.60 < A 0.69 < BBB 1.00 < BB 1.63 < B 2.94 — a real credit curve,
monotonic by rating, which is the entire reason this leg is worth fetching
rather than inventing.

Values are PERCENT, not basis points: BBB reads 1.00 meaning 100bp. Converted
once, here, with the unit recorded in the payload so a later reader cannot
re-convert.

Dates are ISO, unlike Treasury's MM/DD/YYYY. `curves.py` parses both strictly.

    uv run generators/fetch_market_oas.py --dry-run
    uv run generators/fetch_market_oas.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch
from generators.curves import parse_fred_date

SCREEN = REPO_ROOT / "sources" / "screening"

#: AAA is deliberately absent — this cast is mid-market and leveraged, and no
#: anchor in it would price at AAA. BAMLC0A1CAAAEY exists and works but is the
#: effective-YIELD variant, not OAS; mixing the two is a units error.
SERIES = {
    "AA":  "BAMLC0A2CAA",
    "A":   "BAMLC0A3CA",
    "BBB": "BAMLC0A4CBBB",
    "BB":  "BAMLH0A1HYBB",
    "B":   "BAMLH0A2HYB",
}
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = SourceManifest(
        source="fred",
        description="ICE BofA US corporate OAS by rating band — market factor",
        licence="FRED/St. Louis Fed redistribution terms; ICE BofA index data",
    )

    out: dict[str, dict] = {}
    for band, sid in SERIES.items():
        url = URL.format(sid=sid)
        if args.dry_run:
            print(f"  [plan] {band:<4} {url}")
            continue
        path = fetch(url, manifest, f"{sid}.csv")
        reader = csv.reader(path.read_text(encoding="utf-8").splitlines())
        header = next(reader)
        if header[1].strip() != sid:
            raise RuntimeError(
                f"{sid}: expected column {sid!r}, got {header[1]!r} — FRED "
                "changed the CSV shape; do not guess, look at the file")
        points = []
        for row in reader:
            if len(row) < 2 or not row[1].strip() or row[1].strip() == ".":
                continue          # FRED renders a missing observation as "."
            points.append({"date": parse_fred_date(row[0]).isoformat(),
                           "oas_bp": round(float(row[1]) * 100, 2)})
        out[band] = {"fred_id": sid, "unit": "basis_points", "points": points}
        print(f"  {band:<4} {sid:<14} {len(points):>4} points  "
              f"{points[0]['date']} -> {points[-1]['date']}")

    if args.dry_run:
        print("  [dry-run] nothing fetched or written")
        return 0

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "FRED — ICE BofA US corporate index OAS",
        "provenance": "public",
        "series": out,
    }
    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave11a_oas.json").write_text(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
