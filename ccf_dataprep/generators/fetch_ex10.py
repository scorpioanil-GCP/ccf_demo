#!/usr/bin/env python3
"""Wave 4 — locate and cache EX-10 credit agreements for the anchor cast.

`facility-terms-snapshot` §C is explicit that these elements originate in
*text*, not a structured feed, and that parsing is a **build-time step**, not a
runtime operator. The source document itself is not addressable until MongoDB
arrives in Wave 6 — a T1 example that reaches into a document has silently
become a T4 example.

So this caches the documents to `sources/ex10/` (gitignored, manifest tracked)
and Wave 4's extractor reads from disk. Wave 6 re-uses the same cache for the
MongoDB corpus, so each document is fetched once.

Selection prefers anchors with many 8-K Item 1.01 filings, since an
amendment-rich filer is a facility-rich filer, and §F needs 12 facilities
carrying at least one amendment.

    uv run generators/fetch_ex10.py --limit 25

Idempotent: cached documents are not re-fetched.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch, get_json

SCREEN = REPO_ROOT / "sources" / "screening"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
FILING_INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/index.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{doc}"

#: Exhibit numbering for material contracts. EX-10.1 through 10.99 plus bare
#: EX-10; credit agreements are conventionally filed in this range.
EX10_DOC = re.compile(r"ex-?10[._-]?\d*\.(htm|html|txt)$", re.IGNORECASE)

#: Filenames that are material contracts but not credit agreements. Excluding
#: them up front avoids caching megabytes of equity plans.
NOT_CREDIT = re.compile(
    r"(equity|incentive|option|restricted|severance|employment|indemn|"
    r"director|bonus|deferred|retention|consult|lease|purchase|"
    r"registration|warrant|license)",
    re.IGNORECASE,
)

CREDIT_HINT = re.compile(
    r"(credit|loan|facility|revolv|term|financ|amend|forbear|note)",
    re.IGNORECASE,
)


def candidate_filings(cik: int, max_filings: int) -> list[tuple[str, str, str]]:
    """Return (accession, filing_date, form) for 8-K and 10-K filings."""
    try:
        sub = get_json(SUBMISSIONS.format(cik=cik), is_sec=True)
    except Exception:  # noqa: BLE001
        return []
    # EDGAR `recent`-only: the index caps at ~1000 filings per issuer and
    # shards the remainder into `filings.files[]`, which this sweep does NOT
    # read. 40 of the 50 anchors have unread shards, so results here are a
    # FLOOR on the issuer's history, never the complete public record.
    # Estate-wide pattern across 7 fetchers; see docs/known-issues.md §9.11.
    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accns = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    items = recent.get("items", [])

    out: list[tuple[str, str, str]] = []
    for i, form in enumerate(forms):
        if form not in ("8-K", "8-K/A", "10-K", "10-K/A", "10-Q"):
            continue
        # Prefer 8-Ks that actually announce an agreement.
        if form.startswith("8-K"):
            raw = items[i] if i < len(items) else ""
            if not any(code in (raw or "") for code in ("1.01", "2.03")):
                continue
        out.append((accns[i], dates[i] if i < len(dates) else "", form))
        if len(out) >= max_filings:
            break
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25,
                        help="number of anchors to pull documents for")
    parser.add_argument("--per-anchor", type=int, default=3,
                        help="max EX-10 documents cached per anchor")
    parser.add_argument("--max-filings", type=int, default=6,
                        help="filings inspected per anchor")
    args = parser.parse_args()

    anchors = json.loads((SCREEN / "anchors_final.json").read_text())["anchors"]
    # Amendment-rich filers first: they carry more facilities and satisfy §F's
    # "12 facilities with >= 1 amendment" without extra searching.
    anchors.sort(key=lambda a: -a.get("item_1_01", 0))
    anchors = anchors[: args.limit]

    manifest = SourceManifest(
        source="ex10",
        description="EDGAR EX-10 credit agreements and amendments for the anchor cast",
        licence="US government work / public filing",
    ).load()

    print(f"Caching EX-10 documents for {len(anchors)} amendment-rich anchors\n")

    index: list[dict] = []
    total_docs = 0
    for i, anchor in enumerate(anchors, 1):
        cik = anchor["cik"]
        got = 0
        for accn, filed, form in candidate_filings(cik, args.max_filings):
            if got >= args.per_anchor:
                break
            nodash = accn.replace("-", "")
            try:
                listing = get_json(
                    FILING_INDEX.format(cik=cik, nodash=nodash), is_sec=True
                )
            except Exception:  # noqa: BLE001
                continue
            for item in listing.get("directory", {}).get("item", []):
                if got >= args.per_anchor:
                    break
                name = item.get("name") or ""
                if not EX10_DOC.search(name):
                    continue
                desc = f"{name} {item.get('type','')}"
                if NOT_CREDIT.search(desc):
                    continue
                size = int(item.get("size") or 0)
                # Credit agreements are substantial; a 3KB exhibit is a cover
                # page or a consent, and a 6MB one is not worth the bandwidth.
                if size < 20_000 or size > 4_000_000:
                    continue
                url = ARCHIVE.format(cik=cik, nodash=nodash, doc=name)
                filename = f"{cik}_{accn}_{name}"
                try:
                    path = fetch(url, manifest, filename, is_sec=True, timeout=90)
                except Exception as exc:  # noqa: BLE001
                    print(f"    [fail] {name}: {type(exc).__name__}")
                    continue
                index.append({
                    "cik": cik, "lei": anchor["lei"],
                    "sec_name": anchor["sec_name"],
                    "accession": accn, "filed_date": filed, "form": form,
                    "document": name, "url": url,
                    "path": str(path.relative_to(REPO_ROOT)),
                    "bytes": size,
                })
                got += 1
                total_docs += 1
        if i % 5 == 0:
            print(f"  ...{i}/{len(anchors)}  ({total_docs} documents cached)")

    (SCREEN / "ex10_index.json").write_text(
        json.dumps(
            {
                "generated_for": "Wave 4 — cached EX-10 credit agreements",
                "source": "SEC EDGAR Archives",
                "document_count": len(index),
                "distinct_filers": len({d["cik"] for d in index}),
                "note": "Parsing is a build-time step. Documents become "
                        "addressable only in Wave 6 (MongoDB); a T1 product "
                        "reaching into them would silently be a T4 product.",
                "documents": index,
            },
            indent=2,
        )
        + "\n"
    )

    print(f"\n  {len(index)} documents cached across "
          f"{len({d['cik'] for d in index})} filers")
    print(f"  total {sum(d['bytes'] for d in index) / 1e6:.1f} MB")
    print(f"  written: sources/screening/ex10_index.json")
    print(f"  manifest: sources/ex10/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
