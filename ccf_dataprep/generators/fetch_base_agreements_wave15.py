#!/usr/bin/env python3
"""Wave 15 — fetch the BASE agreements our amendments amend.

`covenant-cross-reference` §C row 2 is "Amended-and-restated agreement text",
and §F asks for

    ">= 3 agreements with a filed amendment, so `as_of` changes which text
     governs"

`validators/spec_coverage.py` reported this as a gap, and the gap was real but
not the one it looked like. The corpus is FULL of amendments -- 18 of 25 credit
agreements carry an amendment marker in their first 4 KB -- so the missing
thing was never amendment text. It was the OTHER SIDE of the pair.

## Why the floor needs pairs and not amendments

The §F clause after the comma is the condition, not decoration. For `as_of` to
change which text governs there must be at least two texts for the SAME
agreement; with only the amendment held, an `as_of` before the amendment date
resolves to nothing. Counting "documents that look like amendments" would have
cleared a floor of 3 many times over while demonstrating nothing -- which is
the failure CLAUDE.md names: hitting the count and missing the condition.

Measured across the existing corpus, only two agreements have two texts:

    Celanese    CREDIT AGREEMENT 2025-08-11  +  FIRST AMENDMENT 2026-08-04
    TransDigm   AMENDMENT NO. 20 (2026-02-13) + NO. 21 (2026-04-17), both to
                the Second A&R Credit Agreement of 2014-06-04

Three near-misses had to be rejected on inspection, and each is a trap for a
filer-level or date-level heuristic:

    Vertiv      two documents, DIFFERENT instruments -- Amendment No. 6 to the
                2020 Term Loan agreement, and a brand-new 2026 revolver
    PAYCHEX     two amendments filed the SAME DAY, to two DIFFERENT agreements
                (the 2017 and the 2019 credit agreements)
    XPO         Amendment No. 11 plus an unrelated new Term Loan A agreement

So "same LEI, two credit-agreement documents" is not a pair, and neither is
"same accession". The agreement identity is what matters.

## What this fetches

The two base agreements whose amendments we already hold, giving four
agreements with two texts each:

    PAYCHEX 2019 Credit Agreement (2019-07-31) <- Amendment No. 4 (2026-01-26)
    Vertiv Term Loan Credit Agreement (2020-03-02) <- Amendment No. 6 (2025-08-12)

Both were located from the amendment text itself, which names the agreement it
amends and its date -- not guessed from a filing window.

## Exhibits are resolved from the filing index PAGE, not index.json

`index.json` omitted a real, fetchable exhibit earlier in this project, and it
does so again here: for PAYCHEX's 2017 8-K it lists only EX-99.1. The
`-index.htm` page carries the exhibit TYPE column, so an EX-10 can be
identified as such rather than inferred from a filename. That is also how the
2017 credit agreement was ruled out -- that 8-K genuinely has no EX-10, so the
2017 agreement is not fetchable from it and is not attempted.

Output: appends to sources/screening/ex10_index.json, caches to sources/ex10/

Run: uv run generators/fetch_base_agreements_wave15.py
Then: segment_passages.py -> load_mongo_wave6.py -> embed_passages.py
"""

from __future__ import annotations

import json
import re
import sys

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch, get

SCREEN = REPO_ROOT / "sources" / "screening"
EX10_DIR = REPO_ROOT / "sources" / "ex10"
INDEX = SCREEN / "ex10_index.json"

INDEX_PAGE = ("https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/"
              "{accession}-index.htm")
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{doc}"

#: The base agreements, each located from the amendment that names it.
#:
#: `expect` is a phrase that must appear in the fetched text. It is not
#: decoration: an exhibit-type match tells us the filer called it EX-10, not
#: that it is the agreement we went looking for, and caching the wrong
#: 600 KB exhibit under a base-agreement label would produce a pair that
#: joins cleanly and means nothing.
TARGETS = [
    {
        "cik": 723531,
        "lei": "529900K900DW6SUBM174",
        "sec_name": "PAYCHEX INC",
        "accession": "0000723531-19-000036",
        "filed_date": "2019-08-01",
        "form": "8-K",
        "agreement": "2019 Credit Agreement dated as of July 31, 2019",
        "amended_by": "AMENDMENT NO. 4 (0001193125-26-021794:payx-ex10_2.htm)",
        "expect": "CREDIT AGREEMENT",
    },
    {
        "cik": 1674101,
        "lei": "549300KTTIRAOGXCRV69",
        "sec_name": "Vertiv Holdings Co",
        "accession": "0001628280-20-002714",
        "filed_date": "2020-03-03",
        "form": "8-K",
        "agreement": "Term Loan Credit Agreement dated as of March 2, 2020",
        "amended_by": "AMENDMENT NO. 6 (0001193125-25-178982:d25970dex101.htm)",
        "expect": "TERM LOAN CREDIT AGREEMENT",
    },
]

#: Exhibit rows in the filing index page, with their declared TYPE.
EX10_ROW = re.compile(
    r"<td[^>]*>\s*(EX-10[.\d]*)\s*</td>.*?href=\"([^\"]+\.htm)\"", re.S | re.I)


def strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def exhibits(cik: int, accession: str) -> list[tuple[str, str]]:
    """[(exhibit_type, document_name)] from the filing index PAGE."""
    nodash = accession.replace("-", "")
    html = get(INDEX_PAGE.format(cik=cik, nodash=nodash, accession=accession),
               is_sec=True).text
    out: list[tuple[str, str]] = []
    for kind, href in EX10_ROW.findall(html):
        name = href.rsplit("/", 1)[-1]
        if (kind, name) not in out:
            out.append((kind, name))
    return out


def main() -> int:
    print("Wave 15 — base agreements for the amendments we already hold\n")
    index = json.loads(INDEX.read_text())
    known = {d["path"] for d in index["documents"]}
    # Same manifest the rest of the EX-10 corpus was fetched under, loaded so
    # these two appends join the existing provenance record rather than
    # replacing it.
    manifest = SourceManifest(
        source="ex10",
        description="EDGAR EX-10 credit agreements and amendments for the anchor cast",
        licence="US government work / public filing",
    ).load()
    added = 0

    for t in TARGETS:
        cik, acc = t["cik"], t["accession"]
        print(f"  {t['sec_name']} — {t['agreement']}")
        found = exhibits(cik, acc)
        if not found:
            print(f"    NO EX-10 in {acc}; skipping (not fetchable from here)")
            continue

        chosen = None
        for kind, name in found:
            nodash = acc.replace("-", "")
            url = ARCHIVE.format(cik=cik, nodash=nodash, doc=name)
            fname = f"{cik}_{acc}_{name}"
            target = EX10_DIR / fname
            rel = f"sources/ex10/{target.name}"
            if rel in known:
                print(f"    cached already: {name}")
                chosen = (name, target, rel)
                break
            target = fetch(url, manifest, fname, is_sec=True)
            body = strip_html(target.read_text(errors="ignore"))
            if t["expect"].lower() not in body.lower():
                # An EX-10 that is not the agreement we came for. Deleted
                # rather than kept: a cached file under a base-agreement
                # label is indistinguishable from the real thing later.
                print(f"    {name}: no {t['expect']!r} in text — discarding")
                target.unlink(missing_ok=True)
                # `fetch()` already recorded and saved this URL. Dropping the
                # payload without dropping the record would leave provenance
                # for a file that is not there -- harmless to re-runs, since
                # `already_fetched` checks the payload, but a manifest that
                # names a document the corpus does not hold is exactly the
                # kind of row a later reader trusts.
                manifest.fetches = [f for f in manifest.fetches if f.url != url]
                manifest.save()
                continue
            print(f"    fetched {name} ({target.stat().st_size:,} bytes, "
                  f"{kind})")
            chosen = (name, target, rel)
            break

        if chosen is None:
            print("    no exhibit matched the expected agreement text")
            continue

        name, target, rel = chosen
        if rel not in known:
            index["documents"].append({
                "cik": cik,
                "lei": t["lei"],
                "sec_name": t["sec_name"],
                "accession": acc,
                "filed_date": t["filed_date"],
                "form": t["form"],
                "document": name,
                "url": ARCHIVE.format(cik=cik, nodash=acc.replace("-", ""),
                                      doc=name),
                "path": rel,
                "bytes": target.stat().st_size,
                # Wave 15 provenance: why this document is in the corpus.
                "wave": 15,
                "role": "base_agreement",
                "agreement": t["agreement"],
                "amended_by": t["amended_by"],
            })
            added += 1

    index["document_count"] = len(index["documents"])
    index["distinct_filers"] = len({d["cik"] for d in index["documents"]})
    INDEX.write_text(json.dumps(index, indent=2) + "\n")
    manifest.save()
    print(f"\n  {added} base agreements added · "
          f"{index['document_count']} documents in the index")
    if added:
        print("  next: segment_passages.py -> load_mongo_wave6.py -> "
              "embed_passages.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
