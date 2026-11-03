#!/usr/bin/env python3
"""Wave 15 — group EX-10 documents into AGREEMENT VERSIONS.

`covenant-cross-reference` §F:

    ">= 3 agreements with a filed amendment, so `as_of` changes which text
     governs"

The clause after the comma is the condition. Holding an amendment is not
enough: for `as_of` to select a text there must be two or more texts for the
SAME agreement, and something that says they are the same agreement. Wave 15
fetched the missing base agreements (`fetch_base_agreements_wave15.py`), which
put both texts in the corpus and still left them unrelated -- `document`
records carry no agreement identity, so an `as_of` query has nothing to
resolve against.

This derives that identity. **From the documents, not from a hand-written
list**, because a hand-written pairing cannot be wrong in a way anything
detects, and the near-misses here are specifically designed to fool a
filer-level heuristic:

    Vertiv    Amendment No. 6 (2020 Term Loan) and a NEW 2026 revolver --
              same filer, two different instruments
    PAYCHEX   two amendments filed the SAME DAY to two DIFFERENT agreements
              (the 2017 and the 2019 credit agreements)
    XPO       Amendment No. 11 plus an unrelated new Term Loan A

So neither "same LEI" nor "same accession" is a pair. The agreement's own
DATE is the identity, and every amendment states it: an amendment's opening
recital names the agreement it amends and when it was dated. A base agreement
states its own date in its title block.

    agreement_id  = <lei>:<YYYY-MM-DD of the underlying agreement>
    role          = base | amendment
    governs_from  = the date THIS text takes effect (its own "dated as of")

`as_of` then resolves by picking, among the texts sharing an `agreement_id`,
the one with the latest `governs_from` at or before the requested instant.

Output: sources/screening/agreement_versions.json
Run:    uv run generators/link_agreement_versions_wave15.py
Then:   loaders/load_mongo_wave6.py  (carries the three fields onto `document`)
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date

from ccf.config import REPO_ROOT, mongo_db

SCREEN = REPO_ROOT / "sources" / "screening"
OUT = SCREEN / "agreement_versions.json"

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}

#: "dated as of August 11, 2025" / "Dated as of July 31, 2019"
DATED = re.compile(r"[Dd]ated as of\s+([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})")

#: An amendment announces itself in its title block. Matched against the first
#: few hundred characters only -- the body of a base agreement quotes the word
#: "amendment" constantly (amendment provisions, prior amendments, defined
#: terms) and a whole-document search would classify every agreement as one.
#:
#: Deliberately just the bare word. An earlier version required a SECOND
#: "AMENDMENT" within 40 characters of the first, which reads plausibly and is
#: wrong: "AMENDMENT NO. 4 Dated as of January 23, 2026 to 2019 CREDIT
#: AGREEMENT" spans 44, so every PAYCHEX and TransDigm amendment classified as
#: a base agreement, each became its own singleton, and the §F count still
#: reported 3 because three OTHER agreements happened to pair.
#:
#: "AMENDED AND RESTATED CREDIT AGREEMENT" is a base text and does not match:
#: "AMENDED" is a different word, and \b keeps it that way.
IS_AMENDMENT = re.compile(r"\bAMENDMENT\b", re.I)

TITLE_WINDOW = 400      # characters of title block inspected for the role
RECITAL_WINDOW = 6000   # characters searched for the amended agreement's date


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def parse_date(m: re.Match) -> str | None:
    month, day, year = m.group(1), int(m.group(2)), int(m.group(3))
    if month not in MONTHS:
        return None
    try:
        return date(year, MONTHS[month], day).isoformat()
    except ValueError:
        return None


def title_block(text: str) -> str:
    """The part of the document that states what it IS.

    The SEC HTML wrapper prefixes every exhibit with its own filename and
    type ("EX-10.1 2 payx-ex10_2.htm EX-10.1"), which carries no signal and
    would otherwise eat the window.
    """
    # lstrip FIRST: the extracted text opens with whitespace, so both patterns
    # below -- and the role match that depends on them -- were anchored past
    # the very characters they were written to remove.
    t = norm(text).lstrip()
    t = re.sub(r"^EX-[\d.]+\s+\d+\s+\S+(\s+EX-[\d.]+)*\s*", "", t, flags=re.I)
    t = re.sub(r"^(Exhibit\s+[\d.]+\s*)+", "", t, flags=re.I)
    return t[:TITLE_WINDOW]


def classify(text: str) -> tuple[str, str | None, str | None]:
    """(role, governs_from, underlying_agreement_date).

    For a base agreement the two dates are the same -- it IS the agreement, so
    the date it takes effect and the date identifying it coincide. For an
    amendment they differ, and that difference is the whole mechanism: the
    amendment governs from its own date while belonging to the agreement dated
    earlier.
    """
    head = title_block(text)
    body = norm(text)[:RECITAL_WINDOW]
    dates = [d for d in (parse_date(m) for m in DATED.finditer(body)) if d]

    if not IS_AMENDMENT.search(head):
        own = dates[0] if dates else None
        return "base", own, own

    # An amendment's first date is its own; the agreement it amends is named
    # after it, and is necessarily EARLIER. Taking "the second date" blindly
    # would break on an amendment that restates its own date twice, so the
    # underlying agreement is the first date strictly before the amendment's.
    own = dates[0] if dates else None
    underlying = next((d for d in dates[1:] if own and d < own), None)
    return "amendment", own, underlying


def main() -> int:
    db = mongo_db()
    docs = list(db["document"].find(
        {"document_id": {"$regex": r"\.htm$"}},
        {"document_id": 1, "lei": 1, "sec_name": 1, "form": 1,
         "filed_date": 1, "text": 1}))
    print(f"Classifying {len(docs)} corpus documents\n")

    records: list[dict] = []
    unresolved: list[tuple[str, str]] = []
    for d in docs:
        role, governs, underlying = classify(d.get("text", ""))
        if not underlying or not governs:
            unresolved.append((d["sec_name"], d["document_id"]))
            continue
        records.append({
            "document_id": d["document_id"],
            "lei": d.get("lei"),
            "sec_name": d.get("sec_name"),
            "filed_date": d.get("filed_date"),
            "agreement_id": f"{d.get('lei')}:{underlying}",
            "agreement_date": underlying,
            "role": role,
            "governs_from": governs,
        })

    by_agreement: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_agreement[r["agreement_id"]].append(r)

    # §F counts AGREEMENTS WITH MORE THAN ONE TEXT, not documents and not
    # amendments. Two texts sharing a governs_from would not let `as_of`
    # choose between them, so the distinct-date requirement is part of the
    # count rather than a refinement of it.
    versioned = {
        aid: rs for aid, rs in by_agreement.items()
        if len({r["governs_from"] for r in rs}) >= 2
    }

    print(f"  {len(records)} documents carry an agreement identity")
    print(f"  {len(by_agreement)} distinct agreements")
    print(f"  {len(versioned)} agreements with 2+ texts at DIFFERENT dates "
          f"(§F asks for >= 3)\n")
    for aid, rs in sorted(versioned.items()):
        print(f"  {rs[0]['sec_name']} — agreement dated {rs[0]['agreement_date']}")
        for r in sorted(rs, key=lambda x: x["governs_from"]):
            print(f"      {r['governs_from']}  {r['role']:9s} "
                  f"{r['document_id'].split(':')[1]}")
    if unresolved:
        print(f"\n  {len(unresolved)} documents left WITHOUT an identity "
              f"(no parseable 'dated as of'):")
        for name, did in unresolved[:8]:
            print(f"      {name[:28]:30s} {did.split(':')[1]}")
        if len(unresolved) > 8:
            print(f"      ... and {len(unresolved) - 8} more")

    OUT.write_text(json.dumps({
        "generated_for": "covenant-cross-reference §F — as_of selects which "
                         "text governs",
        "note": "agreement_id groups texts of the SAME agreement; as_of picks "
                "the latest governs_from at or before the requested instant",
        "document_count": len(records),
        "agreement_count": len(by_agreement),
        "versioned_agreement_count": len(versioned),
        "documents": records,
    }, indent=2) + "\n")
    print(f"\n  written: sources/screening/agreement_versions.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
