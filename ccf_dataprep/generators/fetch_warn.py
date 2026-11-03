#!/usr/bin/env python3
"""Wave 11b — state WARN Act layoff notices: TX Socrata + CA XLSX + CA PDFs.

Three files carry the CA leg because the state publishes no single reachable
table spanning the 24-month window: `warn_report1.xlsx` is the *current*
fiscal year only, live and always-current, while the two prior fiscal years
exist solely as text-extractable PDFs. TX is a single Socrata resource with
the whole window in one call.

The employer name is preserved EXACTLY as published in every leg — no
normalisation. The next wave's obligor match is deliberately lossy
(CLAUDE.md rule 5) and depends on the warts ("Stearns Lending, LLC -
Corporate", "Avis Budget Car Rental-El Paso") surviving intact.

`pdftotext` (poppler-utils) is required for the CA PDF leg. Its absence is a
loud RuntimeError, never a silent zero-row CA-PDF result — that is exactly
the shape of Wave 10's Form 4 trap (HTTP 200, wrong content, identical
silent failure across 120 filings).

    uv run generators/fetch_warn.py --dry-run
    uv run generators/fetch_warn.py

Verification (design §7.2 — a plausible row count is not evidence of correct
extraction): after a real run, pick a few parsed CA PDF rows and read them
back out of the source bytes directly:

    pdftotext -layout sources/warn/warn-report-for-7-1-2024-to-06-30-2025.pdf - \\
        | grep -n "<employer name>"
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import openpyxl

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import SourceManifest, fetch
from generators.fetch_8k_items import WINDOW_END, WINDOW_START, in_window
from generators.warn_match import match_all
from generators.warn_sources import (WarnNotice, parse_ca_pdf_text,
                                     parse_ca_xlsx, parse_tx_socrata)

SCREEN = REPO_ROOT / "sources" / "screening"

TX_URL = "https://data.texas.gov/resource/8w53-c4f6.json?$limit=50000"
CA_XLSX_URL = "https://edd.ca.gov/siteassets/files/jobs_and_training/warn/warn_report1.xlsx"
CA_XLSX_SHEET = "Detailed WARN Report "  # trailing space is real, per wb.sheetnames
CA_PDF_URLS = [
    "https://edd.ca.gov/siteassets/files/jobs_and_training/warn/"
    "warn-report-for-7-1-2024-to-06-30-2025.pdf",
    "https://edd.ca.gov/siteassets/files/jobs_and_training/warn/"
    "warn-report-for-7-1-25-to-6-30-26.pdf",
]


def _require_pdftotext() -> None:
    if shutil.which("pdftotext") is None:
        raise RuntimeError(
            "pdftotext not found on PATH. It ships with poppler-utils "
            "(`apt-get install poppler-utils` / `brew install poppler`); "
            "without it the CA PDF leg would silently produce zero rows "
            "instead of failing loudly."
        )


def _tag_source(notices: list[WarnNotice], filename: str) -> list[WarnNotice]:
    """Prepend the fetched filename onto each notice's source_ref.

    The pure parsers (no filename in scope) stamp a row/line-local ref;
    this is the I/O layer's job of making that ref fully self-identifying,
    per Task 3 Step 4's "PDF filename plus line number" / "XLSX filename".
    """
    return [dataclasses.replace(n, source_ref=f"{filename}:{n.source_ref}")
            for n in notices]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.dry_run:
        _require_pdftotext()

    manifest = SourceManifest(
        source="warn",
        description="State WARN Act layoff notices — TX Socrata, CA XLSX + PDF",
        licence="US state government work, public",
    )

    all_notices: list[WarnNotice] = []

    # --- Texas: Socrata JSON, whole window in one call --------------------
    if args.dry_run:
        print(f"  [plan] {TX_URL}")
    else:
        path = fetch(TX_URL, manifest, "tx-warn.json")
        rows = json.loads(path.read_text(encoding="utf-8"))
        tx_notices = _tag_source(parse_tx_socrata(rows), path.name)
        all_notices.extend(tx_notices)
        print(f"  TX: {len(rows)} rows fetched, {len(tx_notices)} notices parsed")

    # --- California: current-FY XLSX ---------------------------------------
    if args.dry_run:
        print(f"  [plan] {CA_XLSX_URL}")
    else:
        path = fetch(CA_XLSX_URL, manifest, "warn_report1.xlsx")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        if CA_XLSX_SHEET not in wb.sheetnames:
            raise RuntimeError(
                f"sheet {CA_XLSX_SHEET!r} not found; workbook has "
                f"{wb.sheetnames!r} — the sheet name (trailing space "
                "included) may have changed upstream."
            )
        ws = wb[CA_XLSX_SHEET]
        raw_rows = [list(r) for r in ws.iter_rows(values_only=True)]
        # Row 0 is a title banner, row 1 is the real header — drop the banner
        # so parse_ca_xlsx sees the header first, per its documented contract.
        rows_for_parser = raw_rows[1:]
        ca_xlsx_notices = _tag_source(parse_ca_xlsx(rows_for_parser), path.name)
        all_notices.extend(ca_xlsx_notices)
        print(f"  CA XLSX: {len(raw_rows) - 2} data rows, "
              f"{len(ca_xlsx_notices)} notices parsed")

    # --- California: two per-FY PDFs, text-extracted -----------------------
    for url in CA_PDF_URLS:
        filename = url.rsplit("/", 1)[-1]
        if args.dry_run:
            print(f"  [plan] {url}")
            continue
        path = fetch(url, manifest, filename)
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True, text=True, check=True,
        )
        pdf_notices = _tag_source(parse_ca_pdf_text(result.stdout), path.name)
        all_notices.extend(pdf_notices)
        print(f"  {filename}: {len(pdf_notices)} notices parsed")

    if args.dry_run:
        print("  [dry-run] nothing fetched or written")
        return 0

    windowed = [n for n in all_notices if in_window(n.notice_date)]
    print(f"\n  {len(all_notices)} notices parsed across all sources")
    print(f"  {len(windowed)} survive the window [{WINDOW_START}, {WINDOW_END}]")
    by_state: dict[str, int] = {}
    for n in windowed:
        by_state[n.state] = by_state.get(n.state, 0) + 1
    for state, count in sorted(by_state.items()):
        print(f"    {state}: {count}")

    # --- Obligor <-> employer name join, deliberately lossy --------------
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, legal_name FROM "{PG_SCHEMA_V2}".legal_entity '
                    "ORDER BY legal_name")
        anchors = cur.fetchall()

    matches = match_all(anchors, windowed)
    resolved_obligors = sorted({m["anchor_name"] for m in matches
                                 if m["verdict"] == "resolved"})
    ambiguous_count = sum(1 for m in matches if m["verdict"] == "ambiguous")
    print(f"\n  {len(anchors)} anchor obligors matched against "
          f"{len(windowed)} windowed notices")
    print(f"  {len(matches)} pairs scored >= AMBIGUOUS_AT "
          f"({len(resolved_obligors)} distinct obligors resolved, "
          f"{ambiguous_count} ambiguous pairs)")
    for name in resolved_obligors:
        print(f"    resolved: {name}")

    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave11b_warn.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "TX data.texas.gov 8w53-c4f6; CA EDD warn_report1.xlsx + per-FY PDFs",
        "provenance": "public",
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "notices": [dataclasses.asdict(n) for n in windowed],
        "matches": matches,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
