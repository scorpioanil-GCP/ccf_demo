#!/usr/bin/env python3
"""Fetch the three ABS deals' filings for the Wave 14 window.

    uv run generators/fetch_abs_deals.py --dry-run   # resolve, fetch nothing
    uv run generators/fetch_abs_deals.py             # ~5.4 GB, be patient

Idempotent: `ccf.fetch` skips any URL already recorded whose payload still
exists, so an interrupted run resumes for free.

## Why the window is keyed on reportDate

EDGAR's `filingDate` and `reportDate` differ by 2-7 weeks and the lag varies
by filer. Selecting on filing date would silently mis-align the three deals
by up to two reporting months, and a vintage benchmark that compares one
deal's July with another's September is not a benchmark -- it is noise with
a table around it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch, get, get_json

SOURCE = "absee"
OUT = REPO_ROOT / "sources" / SOURCE
REGISTRY = OUT / "deals.json"

WINDOW = tuple(f"{y}-{m:02d}" for y, m in
               [(2025, m) for m in range(7, 13)] + [(2026, m) for m in range(1, 7)])

#: `prospectus_filed` is the 424B5 filing date, verified on EDGAR 2026-08-22.
#: It is the assertion date for every original trigger threshold -- the date
#: the market could first have known the number. Task 9 depends on it, and
#: using today's date there instead would make the bitemporal check in Task 13
#: pass vacuously (`known_as_of` would find no assertion at all and return
#: None, so `as_of != known_as_of` would hold for the wrong reason).
DEALS = [
    {"deal_id": "SDART-2022-6", "slug": "sdart-2022-6", "cik": "1943670",
     "legal_name": "Santander Drive Auto Receivables Trust 2022-6",
     "credit_tier": "subprime", "vintage": 2022, "servicer": "Santander Consumer USA Inc.",
     "depositor_cik": "1383094", "prospectus_filed": "2022-09-14",
     "prospectus": ("0001193125-22-244774", "d399127d424b5.htm")},
    {"deal_id": "TAOT-2022-B", "slug": "taot-2022-b", "cik": "1914281",
     "legal_name": "Toyota Auto Receivables 2022-B Owner Trust",
     "credit_tier": "prime", "vintage": 2022, "servicer": "Toyota Motor Credit Corporation",
     "depositor_cik": "1131131", "prospectus_filed": "2022-04-11",
     "prospectus": ("0000929638-22-000773", "a424b5.htm")},
    {"deal_id": "SDART-2024-1", "slug": "sdart-2024-1", "cik": "2004812",
     "legal_name": "Santander Drive Auto Receivables Trust 2024-1",
     "credit_tier": "subprime", "vintage": 2024, "servicer": "Santander Consumer USA Inc.",
     "depositor_cik": "1383094", "prospectus_filed": "2024-01-16",
     "prospectus": ("0001193125-24-008591", "d605182d424b5.htm")},
]


def submissions(cik: str) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    return get_json(url, is_sec=True, timeout=60)


#: `<TYPE>...<FILENAME>` triples in an EDGAR submission header.
_DOC = re.compile(r"<TYPE>([^\r\n<]+)[\r\n]+<SEQUENCE>(\d+)[\r\n]+"
                  r"<FILENAME>([^\r\n<]+)")


def accession_files(cik: str, accession: str) -> list[tuple[str, str]]:
    """Return [(document_type, filename)] from the SUBMISSION HEADER.

    NOT from `index.json`. Measured 2026-08-23 on Toyota accession
    0001193125-26-322407: `index.json` lists four entries and OMITS
    `d70261dex991.htm`, the EX-99.1 servicer certificate -- which fetches
    perfectly well (HTTP 200, 140 KB) and is listed in the submission header
    as SEQUENCE 2. The same call on the Santander accessions lists their
    EX-99.1 correctly.

    That asymmetry is the danger: resolving through `index.json` works for two
    of the three deals and silently reports "no servicer report" for the
    third, across all twelve of its periods. A guard that raises on the empty
    result then reads as a data problem rather than a resolution bug.

    The header is fetched with a Range request -- the full submission text is
    the concatenation of every document (72 MB for an ABS-EE accession), and
    the header sits in the first few kilobytes.
    """
    acc = accession.replace("-", "")
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/"
           f"{accession}.txt")
    r = get(url, is_sec=True, timeout=60, headers={"Range": "bytes=0-32767"})
    docs = [(t.strip(), f.strip()) for t, _seq, f in _DOC.findall(r.text)]
    if not docs:
        raise RuntimeError(
            f"{accession}: no <TYPE>/<FILENAME> entries in the first 32 KB of "
            f"the submission header. Do not fall back to index.json -- it is "
            f"incomplete for at least one filer in this wave.")
    return docs


def archive(cik: str, accession: str, name: str) -> str:
    return (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
            f"{accession.replace('-', '')}/{name}")


def resolve(deal: dict) -> dict:
    """Map each window month to its ABS-EE and 10-D accession."""
    sub = submissions(deal["cik"])["filings"]["recent"]
    rows = list(zip(sub["form"], sub["accessionNumber"], sub["reportDate"]))

    periods: dict[str, dict] = {}
    for form, accession, report_date in rows:
        if not report_date:
            continue
        month = report_date[:7]
        if month not in WINDOW or form not in {"ABS-EE", "10-D"}:
            continue
        periods.setdefault(month, {})[form] = accession

    missing = [m for m in WINDOW if "ABS-EE" not in periods.get(m, {})]
    if missing:
        raise RuntimeError(
            f"{deal['deal_id']}: no ABS-EE for {missing}. The window is fixed "
            f"by docs/wave14-design.md §2.1 -- do not silently shorten it.")
    return periods


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch Wave 14 ABS deal filings")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve accessions and report sizes, fetch nothing")
    args = ap.parse_args()

    manifest = SourceManifest(
        source=SOURCE,
        description=("SEC Form ABS-EE loan-level XML, 424B5 prospectuses, "
                     "10-D servicer reports and ABS-15G repurchase filings "
                     "for three auto-ABS deals, 2025-07..2026-06."),
        licence="US public domain (SEC EDGAR)",
    ).load()

    registry = {"generated_at": date.today().isoformat(),
                "window": list(WINDOW), "deals": []}

    for deal in DEALS:
        print(f"\n{deal['deal_id']}  ({deal['legal_name']})")
        periods = resolve(deal)
        dest = OUT / deal["slug"]
        entry = {**deal, "periods": {}}

        # Prospectus -- one per deal, the anchor for every trigger threshold.
        acc, doc = deal["prospectus"]
        if not args.dry_run:
            fetch(archive(deal["cik"], acc, doc), manifest,
                  f"{deal['slug']}/prospectus.htm", is_sec=True)
        entry["prospectus_url"] = archive(deal["cik"], acc, doc)

        for month in WINDOW:
            found = periods[month]
            docs = accession_files(deal["cik"], found["ABS-EE"])
            names = [n for _t, n in docs]

            # Resolve by DECLARED TYPE first, falling back to the filename
            # suffix -- the two issuers lay accessions out differently, and
            # Santander's 10-D accession (fetched separately below) *also*
            # carries its own copy of the EX-102, so this must resolve the
            # loan-tape XML from *this* ABS-EE accession specifically.
            ex102 = [n for t, n in docs if t.upper() == "EX-102"] or \
                    [n for n in names if n.endswith("ex102.xml")]
            if len(ex102) != 1:
                raise RuntimeError(
                    f"{deal['deal_id']} {month}: expected exactly one "
                    f"*ex102.xml in {found['ABS-EE']}, found {ex102}")

            rec = {"absee_accession": found["ABS-EE"], "absee_file": ex102[0]}

            # The servicer report always lives in the 10-D accession, for
            # both issuers -- verified across all 36 periods:
            # absee_accession != servicer_accession in every case. (Santander's
            # 10-D also carries its own copy of the EX-102, a duplicate of the
            # loan tape -- not the one used above.) The found["ABS-EE"]
            # fallback below guards an issuer that folds both forms into one
            # accession; that case never occurred in this window.
            servicer_acc = found.get("10-D", found["ABS-EE"])
            servicer_docs = (docs if servicer_acc == found["ABS-EE"]
                             else accession_files(deal["cik"], servicer_acc))
            ex991 = [n for t, n in servicer_docs if t.upper() == "EX-99.1"] or \
                    [n for _t, n in servicer_docs if "ex991" in n.lower()]
            if not ex991:
                raise RuntimeError(
                    f"{deal['deal_id']} {month}: no EX-99.1 servicer report "
                    f"in {servicer_acc}. Do not fall back to the 10-D cover "
                    f"page -- it carries no distribution figures.")
            rec |= {"servicer_accession": servicer_acc, "servicer_file": ex991[0]}

            if not args.dry_run:
                fetch(archive(deal["cik"], found["ABS-EE"], ex102[0]), manifest,
                      f"{deal['slug']}/{month}.xml", is_sec=True, timeout=600)
                fetch(archive(deal["cik"], servicer_acc, ex991[0]), manifest,
                      f"{deal['slug']}/servicer-{month}.htm", is_sec=True)

            entry["periods"][month] = rec
            print(f"  {month}  {ex102[0]:<34} {ex991[0]}")

        registry["deals"].append(entry)

    # ABS-15G -- depositor level. A per-trust lookup returns nothing and
    # reads as "no repurchase activity", which is the wave's most plausible
    # silent-empty failure.
    seen = set()
    registry["repurchase"] = []
    for deal in DEALS:
        cik = deal["depositor_cik"]
        if cik in seen:
            continue
        seen.add(cik)
        sub = submissions(cik)["filings"]["recent"]
        filings = [(f, a, d) for f, a, d in
                   zip(sub["form"], sub["accessionNumber"], sub["filingDate"])
                   if f.startswith("ABS-15G")]
        if not filings:
            raise RuntimeError(
                f"depositor CIK {cik} has no ABS-15G. Check the CIK before "
                f"concluding there is no repurchase activity.")
        print(f"\nABS-15G depositor {cik}: {len(filings)} filings")
        # Cap at 4 most recent per depositor -- a deliberate local choice,
        # not a brief requirement. The registry needs enough repurchase
        # filings to demonstrate the join, not the depositor's full history
        # (44 for Toyota's depositor CIK 1131131 alone); raise or drop this
        # slice if a later task needs more.
        for form, accession, filed in filings[:4]:
            doc = next((n for _t, n in accession_files(cik, accession)
                        if n.endswith((".htm", ".txt")) and "index" not in n),
                       None)
            if doc and not args.dry_run:
                fetch(archive(cik, accession, doc), manifest,
                      f"repurchase/{cik}-{accession}.htm", is_sec=True)
            registry["repurchase"].append(
                {"depositor_cik": cik, "form": form,
                 "accession": accession, "filed_date": filed, "file": doc})

    if args.dry_run:
        print("\n  DRY RUN -- nothing fetched.")
        return 0

    manifest.save()
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(registry, indent=2) + "\n")
    print(f"\n  registry -> {REGISTRY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
