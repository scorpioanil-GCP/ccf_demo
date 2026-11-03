#!/usr/bin/env python3
"""Wave 3 — parse EDGAR Exhibit 21 subsidiary lists for the anchor cast.

GLEIF Level 2 gives breadth but almost no depth: it records direct and
ultimate parent only, and subsidiaries of US public filers rarely register
their own relationships, so the natural graph is one hop deep.

Exhibit 21 is the public source for the rest of the corporate tree. It is
filed annually with the 10-K, lists subsidiaries by name and jurisdiction, and
**most of those subsidiaries hold no LEI** — which is exactly the bridging
case §C calls for (`synthetic — bridging` stub entities, ~30 wanted).

Extraction is deliberate about its own limits. Exhibit 21 is free-form: some
filers use HTML tables, some nested indentation implying hierarchy, some a
flat comma-separated list. This parser reads tables and list items, records
the jurisdiction where present, and **does not infer hierarchy from
indentation** — a guessed parent edge would be indistinguishable from a filed
one downstream.

Output: sources/screening/exhibit21.json

Run: uv run generators/fetch_exhibit21.py
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser

from ccf.config import REPO_ROOT
from ccf.fetch import get_json, sec_headers, SEC_LIMITER

import requests

SCREEN = REPO_ROOT / "sources" / "screening"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/{doc}"
FILING_INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/index.json"

JURISDICTIONS = re.compile(
    r"\b(Delaware|Nevada|California|New York|Texas|Florida|Illinois|Ohio|"
    r"Georgia|Michigan|Virginia|Maryland|Massachusetts|Minnesota|Colorado|"
    r"Washington|Pennsylvania|New Jersey|Arizona|Wisconsin|Indiana|Missouri|"
    r"Tennessee|Connecticut|Oregon|Utah|Iowa|Kansas|Nebraska|Oklahoma|"
    r"United Kingdom|England|Wales|Scotland|Ireland|Canada|Ontario|Quebec|"
    r"British Columbia|Netherlands|Luxembourg|Germany|France|Switzerland|"
    r"Singapore|Hong Kong|China|Japan|Australia|India|Mexico|Brazil|Spain|"
    r"Italy|Sweden|Denmark|Norway|Belgium|Austria|Poland|Cayman Islands|"
    r"Bermuda|British Virgin Islands|Barbados|Jersey|Guernsey|Malta|Cyprus)\b",
    re.IGNORECASE,
)

#: Table cruft, in two shapes, because one regex cannot do both jobs.
#:
#: WHOLE-CELL words. A cell that is nothing but "Subsidiary" or "Country" is a
#: header; a cell that merely STARTS with one -- "Country Kitchen LLC",
#: "Entity Solutions Group, Inc", "Named Sub Holdings Inc" -- is a company.
#: The previous single prefix rule dropped all three of those silently, and
#: still let "Subsidiary" through: its `subsidiaries?` alternation applied the
#: `?` to the final `s`, matching "subsidiarie" and "subsidiaries" but never
#: the singular. Two filers' header cells reached the ledger as a company by
#: that route and were joint-owned by both -- known-issues §19.6.
BARE_HEADER = re.compile(
    r"^\s*("
    r"subsidiar(y|ies)|name|entity|entities|company|jurisdiction|state|"
    r"country|organization|domicile|page|percentage|owned|ownership|"
    r"legal\s+name|entity\s+name|company\s+name|"
    r"name\s+of\s+(the\s+)?(entity|subsidiar(y|ies)|company)|"
    r"place\s+of\s+(incorporation|organization)|"
    r"(state|jurisdiction)\s+(or\s+(other\s+)?jurisdiction\s+)?"
    r"of\s+(incorporation|organization)|"
    r"percent(age)?\s+owned|"
    r"\d+|[ivxlcdm]+"
    r")\s*[:.]?\s*$",
    re.IGNORECASE,
)

#: TRUE PREFIXES. These are safe to match at the start because no company name
#: begins with them.
NOISE = re.compile(
    r"^(of incorporation|list of|exhibit|table of contents)",
    re.IGNORECASE,
)


class CellExtractor(HTMLParser):
    """Collect text cells from tables and list items."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] = []
        self._cell: list[str] = []
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag in ("td", "th", "li", "p"):
            self._in_cell = True
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th", "li", "p") and self._in_cell:
            text = " ".join("".join(self._cell).split())
            if text:
                self._row.append(text)
            self._in_cell = False
        if tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = []

    def handle_data(self, data):
        if self._in_cell:
            self._cell.append(data)

    def close(self):
        super().close()
        if self._row:
            self.rows.append(self._row)


def sec_get_text(url: str, timeout: int = 60) -> str | None:
    SEC_LIMITER.wait()
    try:
        resp = requests.get(url, headers=sec_headers(), timeout=timeout)
        if resp.status_code != 200:
            return None
        return resp.text
    except Exception:  # noqa: BLE001
        return None


def find_exhibit21(cik: int) -> tuple[str, str] | None:
    """Locate the most recent Exhibit 21 document for a CIK."""
    try:
        sub = get_json(SUBMISSIONS.format(cik=cik), is_sec=True)
    except Exception:  # noqa: BLE001
        return None
    # EDGAR `recent`-only: the index caps at ~1000 filings per issuer and
    # shards the remainder into `filings.files[]`, which this sweep does NOT
    # read. 40 of the 50 anchors have unread shards, so results here are a
    # FLOOR on the issuer's history, never the complete public record.
    # Estate-wide pattern across 7 fetchers; see docs/known-issues.md §9.11.
    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accns = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])

    for idx, form in enumerate(forms):
        if form not in ("10-K", "10-K/A"):
            continue
        accn = accns[idx]
        nodash = accn.replace("-", "")
        try:
            index = get_json(
                FILING_INDEX.format(cik=cik, accn_nodash=nodash), is_sec=True
            )
        except Exception:  # noqa: BLE001
            continue
        for item in index.get("directory", {}).get("item", []):
            name = (item.get("name") or "").lower()
            if re.search(r"ex-?21", name) and name.endswith((".htm", ".html", ".txt")):
                return (
                    ARCHIVE.format(cik=cik, accn_nodash=nodash, doc=item["name"]),
                    dates[idx] if idx < len(dates) else "",
                )
        # Only inspect the two most recent 10-Ks; older ones add cost, not signal.
        if idx > 6:
            break
    return None


def parse_subsidiaries(html: str) -> list[dict]:
    parser = CellExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001
        return []

    out: list[dict] = []
    seen: set[str] = set()
    for row in parser.rows:
        if not row:
            continue
        name = row[0].strip(" . ")
        if len(name) < 4 or len(name) > 120:
            continue
        if NOISE.match(name) or BARE_HEADER.match(name):
            continue
        if not re.search(r"[A-Za-z]{3}", name):
            continue
        jurisdiction = ""
        for cell in row[1:4]:
            m = JURISDICTIONS.search(cell)
            if m:
                jurisdiction = m.group(0)
                break
        if not jurisdiction and len(row) == 1:
            m = JURISDICTIONS.search(name)
            if m:
                jurisdiction = m.group(0)
                name = JURISDICTIONS.sub("", name).strip(" ,.- ")
        key = name.lower()
        if key in seen or len(name) < 4:
            continue
        seen.add(key)
        out.append({"name": name, "jurisdiction": jurisdiction})
    return out


def main() -> int:
    anchors = json.loads((SCREEN / "anchors_final.json").read_text())["anchors"]
    print(f"Locating Exhibit 21 for {len(anchors)} anchors\n")

    results = []
    total_subs = 0
    with_juris = 0
    for i, anchor in enumerate(anchors, 1):
        found = find_exhibit21(anchor["cik"])
        if not found:
            results.append({**{k: anchor[k] for k in ("cik", "lei", "sec_name")},
                            "exhibit21_url": None, "subsidiaries": []})
            continue
        url, filed = found
        html = sec_get_text(url)
        subs = parse_subsidiaries(html) if html else []
        total_subs += len(subs)
        with_juris += sum(1 for s in subs if s["jurisdiction"])
        results.append({
            "cik": anchor["cik"], "lei": anchor["lei"],
            "sec_name": anchor["sec_name"],
            "exhibit21_url": url, "filed_date": filed,
            "subsidiary_count": len(subs), "subsidiaries": subs,
        })
        if i % 10 == 0:
            print(f"  ...{i}/{len(anchors)}  ({total_subs} subsidiaries so far)")

    found_n = sum(1 for r in results if r.get("exhibit21_url"))
    parsed_n = sum(1 for r in results if r["subsidiaries"])
    jurisdictions = {s["jurisdiction"] for r in results for s in r["subsidiaries"]
                     if s["jurisdiction"]}

    print(f"\n  Exhibit 21 located for {found_n}/{len(anchors)} anchors")
    print(f"  parsed subsidiaries from {parsed_n} of those")
    print(f"  {total_subs} subsidiaries total, {with_juris} with a jurisdiction")
    print(f"  {len(jurisdictions)} distinct jurisdictions")

    multi = [r for r in results
             if len({s["jurisdiction"] for s in r["subsidiaries"]
                     if s["jurisdiction"]}) >= 3]
    print(f"  {len(multi)} anchors span >= 3 jurisdictions  "
          f"(§F wants >= 1 family across three)")

    top = sorted(results, key=lambda r: -len(r["subsidiaries"]))[:8]
    for r in top:
        print(f"    {len(r['subsidiaries']):>4}  {r['sec_name'][:40]}")

    (SCREEN / "exhibit21.json").write_text(
        json.dumps(
            {
                "generated_for": "Wave 3 — Exhibit 21 subsidiary lists",
                "source": "SEC EDGAR Exhibit 21 (most recent 10-K per filer)",
                "anchors_with_exhibit": found_n,
                "total_subsidiaries": total_subs,
                "note": "Hierarchy is NOT inferred from indentation; these are "
                        "flat subsidiary lists as filed. Most hold no LEI and "
                        "become `synthetic — bridging` stub entities.",
                "filers": results,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  written: sources/screening/exhibit21.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
