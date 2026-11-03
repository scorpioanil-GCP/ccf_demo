#!/usr/bin/env python3
"""Wave 13b Task 1 — fetch and parse the OFAC sanctions lists.

§C assigns *"Sanctions lists — OFAC SDN + Consolidated (daily XML/CSV)"* to
**Postgres**, provenance `public`. This script does the fetch and the parse;
`loaders/load_ofac_wave13b.py` does the load.

## Two lists, one schema

    SDN.XML    Specially Designated Nationals — the primary list
    CONS.XML   the Consolidated (non-SDN) list — SSI, FSE, NS-MBS, PLC and
               the other programmes that are sanctioned but not SDN

`CONS_ADVANCED.XML` (which the design table names) is a *different*, much
richer schema. `CONSOLIDATED.XML` is the same legacy `sdnList` shape as
`SDN.XML`, so one parser reads both. Nothing this product needs — names,
aliases, DOB, nationality, programme — is only in the advanced format.

**Not `CONS.XML`.** That path exists and answers **HTTP 200 with an empty
body**. It is a live example of the failure `ccf.fetch.fetch()` now guards
against: every signal short of reading the bytes says the fetch worked.

## Why the parser matches on LOCAL name

The payload's namespace has changed at least once (`http://tempuri.org/
sdnList.xsd` -> `https://sanctionslistservice.ofac.treas.gov/api/
PublicationPreview/exports/XML`). A parser keyed on the fully-qualified tag
keeps running after such a change and returns **zero entries**, which reads as
"the list is empty" rather than "the parser is broken". `main()` therefore
asserts the parsed count against the file's own `Record_Count`, so a namespace
change fails loudly instead of quietly.

## Why the recorded URL is not the URL that served the bytes

Both endpoints 302 to a signed S3 object whose query string expires in an
hour. `ccf.fetch.fetch()` records the URL *requested*, which stays valid, and
pins the payload with a sha256. Recording the effective URL would produce
provenance nobody could ever re-fetch.

Fetched payloads are gitignored; the parsed artifact is tracked, because it
is what the loader replays and what the store must reproduce.

Output: sources/screening/wave13b_ofac.json

    uv run generators/fetch_ofac.py
    uv run generators/fetch_ofac.py --force      # re-fetch, ignoring cache
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch

SCREEN = REPO_ROOT / "sources" / "screening"
BASE = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports"

#: (list name, remote file, local file). The list name becomes the
#: `list_name` column and half of every entry_id, so it is data, not cosmetics.
LISTS = [
    ("SDN", "SDN.XML", "sdn.xml"),
    ("CONS", "CONSOLIDATED.XML", "consolidated.xml"),
]


def local(tag: str) -> str:
    """Strip any XML namespace, leaving the local element name."""
    return tag.rsplit("}", 1)[-1]


def child_text(elem: ET.Element, name: str) -> str | None:
    for c in elem:
        if local(c.tag) == name:
            txt = (c.text or "").strip()
            return txt or None
    return None


def children(elem: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in elem if local(c.tag) == name]


def collect(elem: ET.Element, list_tag: str, item_tag: str, field: str) -> list[str]:
    """Pull one repeated field out of one of OFAC's `*List` wrappers."""
    out: list[str] = []
    for wrapper in children(elem, list_tag):
        for item in children(wrapper, item_tag):
            val = child_text(item, field)
            if val and val not in out:
                out.append(val)
    return out


def collect_text(elem: ET.Element, list_tag: str, item_tag: str) -> list[str]:
    """Same, for wrappers whose items carry their value as text, not a child.

    `<programList><program>CUBA</program></programList>` is this shape;
    `<nationalityList><nationality><country>..` is the other. Using the wrong
    reader silently yields an empty list rather than an error, which is why
    they are two named functions instead of one with a flag.
    """
    out: list[str] = []
    for wrapper in children(elem, list_tag):
        for item in children(wrapper, item_tag):
            val = (item.text or "").strip()
            if val and val not in out:
                out.append(val)
    return out


def compose_name(first: str | None, last: str | None) -> str:
    """OFAC splits individuals into first/last and puts entities wholly in last.

    Order matters for the resolution work downstream: the composed display
    form is `First Last`, and the components are kept separately so a scorer
    can reconstruct `LAST, FIRST` renderings without re-splitting a string.
    """
    parts = [p for p in (first, last) if p]
    return " ".join(parts)


def parse_entry(elem: ET.Element, list_name: str) -> dict:
    uid = child_text(elem, "uid")
    first = child_text(elem, "firstName")
    last = child_text(elem, "lastName")

    aliases = []
    for wrapper in children(elem, "akaList"):
        for aka in children(wrapper, "aka"):
            a_first = child_text(aka, "firstName")
            a_last = child_text(aka, "lastName")
            name = compose_name(a_first, a_last)
            if not name:
                continue
            aliases.append(
                {
                    "uid": int(child_text(aka, "uid") or 0),
                    "type": child_text(aka, "type") or "a.k.a.",
                    # `strong` vs `weak` is OFAC's own confidence in the alias.
                    # A weak alias matching is materially less evidence than a
                    # strong one, so it must survive into the store.
                    "category": child_text(aka, "category") or "",
                    "first_name": a_first,
                    "last_name": a_last,
                    "name": name,
                }
            )

    return {
        "list_name": list_name,
        "uid": int(uid) if uid else None,
        "sdn_type": child_text(elem, "sdnType") or "Unknown",
        "title": child_text(elem, "title"),
        "first_name": first,
        "last_name": last,
        "primary_name": compose_name(first, last),
        "programs": collect_text(elem, "programList", "program"),
        "nationalities": collect(elem, "nationalityList", "nationality", "country"),
        "citizenships": collect(elem, "citizenshipList", "citizenship", "country"),
        "countries": collect(elem, "addressList", "address", "country"),
        # Kept verbatim: OFAC writes "circa 1965", "1965 to 1967", "05 Mar 1968".
        # Normalizing here would throw away the ambiguity the resolution layer
        # is supposed to reason about.
        "dates_of_birth": collect(elem, "dateOfBirthList", "dateOfBirthItem", "dateOfBirth"),
        "places_of_birth": collect(elem, "placeOfBirthList", "placeOfBirthItem", "placeOfBirth"),
        "aliases": aliases,
    }


def parse_list(path: Path, list_name: str) -> tuple[dict, list[dict]]:
    root = ET.parse(path).getroot()

    publish: dict = {}
    for info in children(root, "publshInformation"):   # OFAC's own typo
        publish = {
            "publish_date": child_text(info, "Publish_Date"),
            "record_count": int(child_text(info, "Record_Count") or 0),
        }

    entries = [parse_entry(e, list_name) for e in children(root, "sdnEntry")]
    return publish, entries


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="re-fetch even if cached")
    args = ap.parse_args()

    manifest = SourceManifest(
        source="ofac",
        description="OFAC Specially Designated Nationals (SDN) and Consolidated "
                    "(non-SDN) sanctions lists, legacy sdnList XML format.",
        licence="US Government work — public domain. Published daily by the "
                "Office of Foreign Assets Control, US Department of the Treasury.",
    )

    all_entries: list[dict] = []
    publications: dict[str, dict] = {}

    for list_name, remote, filename in LISTS:
        print(f"\n{list_name}")
        path = fetch(f"{BASE}/{remote}", manifest, filename, force=args.force)
        publish, entries = parse_list(path, list_name)
        publications[list_name] = publish

        declared = publish.get("record_count")
        print(f"  publish date   : {publish.get('publish_date')}")
        print(f"  declared count : {declared:,}" if declared else "  declared count : ?")
        print(f"  parsed entries : {len(entries):,}")

        # The namespace guard. A parser that stopped matching would report 0
        # here and every count downstream would agree with it.
        if not entries:
            print(f"  FAIL: parsed zero entries from {filename}. The payload's "
                  f"element namespace or shape has changed.")
            return 1
        if declared and len(entries) != declared:
            print(f"  FAIL: parsed {len(entries):,} entries but the file "
                  f"declares {declared:,}.")
            return 1

        by_type: dict[str, int] = {}
        for e in entries:
            by_type[e["sdn_type"]] = by_type.get(e["sdn_type"], 0) + 1
        for t, n in sorted(by_type.items(), key=lambda kv: -kv[1]):
            print(f"    {t:<12} {n:,}")
        all_entries.extend(entries)

    individuals = [e for e in all_entries if e["sdn_type"] == "Individual"]
    alias_count = sum(len(e["aliases"]) for e in all_entries)
    weak = sum(1 for e in all_entries for a in e["aliases"] if a["category"] == "weak")
    with_dob = sum(1 for e in individuals if e["dates_of_birth"])
    with_nat = sum(1 for e in individuals if e["nationalities"] or e["citizenships"])

    print(f"\nTOTAL")
    print(f"  entries              : {len(all_entries):,}")
    print(f"  individuals          : {len(individuals):,}")
    print(f"  aliases              : {alias_count:,}  ({weak:,} weak)")
    print(f"  individuals w/ DOB   : {with_dob:,}")
    print(f"  individuals w/ nat.  : {with_nat:,}")

    # §D screens resolved persons against the list corroborated by DOB
    # month/year and nationality. If neither field were ever populated the
    # corroboration step would be untestable against real data.
    if with_dob == 0 or with_nat == 0:
        print("  FAIL: no individual carries DOB or nationality — the "
              "corroboration evidence §D requires is absent.")
        return 1

    out = SCREEN / "wave13b_ofac.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "Wave 13b — OFAC sanctions lists (kyc-refresh-"
                                 "beneficial-ownership §C, provenance: public)",
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_base": BASE,
                "publications": publications,
                "entry_count": len(all_entries),
                "alias_count": alias_count,
                "entries": all_entries,
            },
            indent=1,
        )
        + "\n"
    )
    print(f"\n  written: {out.relative_to(REPO_ROOT)}  "
          f"({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
