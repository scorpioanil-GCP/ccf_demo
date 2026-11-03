#!/usr/bin/env python3
"""Pure tests for Form 4 URL derivation, selection, parsing and owner kind.

No network. The first case pins the 2026-08-18 probe defect: EDGAR's
`primaryDocument` names the XSL-RENDERED HTML view, which returns HTTP 200 and
a full HTML document. 120 filings failed silently and identically before anyone
looked at the bytes. A constructed URL cannot fail loudly.

    uv run validators/test_form4.py
"""

from __future__ import annotations

import sys

from generators.extract_persons import next_lookback
from generators.form4 import (ReportingOwner, owner_kind, parse_form4,
                              raw_form4_url, select_form4_filings)

FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
  <issuer><issuerCik>0000078749</issuerCik></issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001277036</rptOwnerCik>
      <rptOwnerName>SRINIVASAN RAMESH</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>1</isDirector>
      <isOfficer>1</isOfficer>
      <officerTitle>President &amp; CEO</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001266604</rptOwnerCik>
      <rptOwnerName>CCH II LLC</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isTenPercentOwner>true</isTenPercentOwner>
    </reportingOwnerRelationship>
  </reportingOwner>
</ownershipDocument>
"""

RECENT = {
    "form": ["4", "8-K", "4", "4", "DEF 14A"],
    "accessionNumber": ["a1", "a2", "a3", "a4", "a5"],
    "filingDate": ["2026-08-07", "2026-07-27", "2026-06-12", "2026-05-01", "2026-04-08"],
    "primaryDocument": ["xslF345X06/ownership.xml", "d1.htm",
                        "xslF345X06/ownership.xml", "ownership.xml", "d2.htm"],
}


def check_url() -> list[tuple[str, bool]]:
    got = raw_form4_url(78749, "0001193125-26-340549", "xslF345X06/ownership.xml")
    want = ("https://www.sec.gov/Archives/edgar/data/78749/"
            "000119312526340549/ownership.xml")
    bare = raw_form4_url(78749, "0001193125-26-340549", "ownership.xml")
    return [
        ("xsl-rendered prefix is stripped", got == want),
        ("dashes are removed from the accession", "000119312526340549" in got),
        ("an already-bare document is unchanged", bare == want),
    ]


def check_selection() -> list[tuple[str, bool]]:
    sel = select_form4_filings(RECENT, lookback=2)
    return [
        ("only form 4 is selected", all(a in {"a1", "a3", "a4"} for a, _, _ in sel)),
        ("lookback bounds the result", len(sel) == 2),
        ("most recent comes first", sel[0][0] == "a1"),
    ]


def check_parse() -> list[tuple[str, bool]]:
    owners = parse_form4(FORM4_XML)
    by_cik = {o.cik: o for o in owners}
    ceo = by_cik.get("0001277036")
    llc = by_cik.get("0001266604")
    return [
        ("both reporting owners are found", len(owners) == 2),
        ("cik is zero-padded to 10", ceo is not None and len(ceo.cik) == 10),
        ("isDirector 1 is truthy", ceo is not None and ceo.is_director),
        ("isOfficer 1 is truthy", ceo is not None and ceo.is_officer),
        ("officerTitle is carried, entities unescaped",
         ceo is not None and ceo.officer_title == "President & CEO"),
        ("isTenPercentOwner true is truthy",
         llc is not None and llc.is_ten_percent_owner),
        ("an owner with no title yields None",
         llc is not None and llc.officer_title is None),
    ]


def check_owner_kind() -> list[tuple[str, bool]]:
    natural = ["SRINIVASAN RAMESH", "Davison James E. Jr.", "alexander Richard R",
               "Jones Dana Sue", "Wood William David III"]
    entity = ["CCH II LLC", "Liberty Broadband Corp",
              "CHARTER COMMUNICATIONS HOLDINGS LLC", "GENESIS ENERGY LP",
              # 2026-08-18: both sailed past a trailing-token-only check.
              # EDGAR's state-of-incorporation marker sits after the real
              # entity marker; a personal-looking roman numeral does too.
              "CHARTER COMMUNICATIONS, INC. /MO/",
              "ESS Holdings Business Trust I"]
    return ([(f"natural: {n}", owner_kind(n) == "natural") for n in natural]
            + [(f"entity:  {n}", owner_kind(n) == "entity") for n in entity])


def check_escalation() -> list[tuple[str, bool]]:
    return [
        ("40 is the starting lookback", next_lookback(None, 0) == 40),
        ("a shortfall doubles the lookback", next_lookback(40, 6) == 80),
        ("doubling continues to 160", next_lookback(80, 7) == 160),
        ("160 is a hard cap — no further escalation",
         next_lookback(160, 6) is None),
        ("reaching 8 natural persons stops escalation",
         next_lookback(40, 8) is None),
        ("comfortably over the floor also stops",
         next_lookback(40, 21) is None),
    ]


def main() -> int:
    cases = (check_url() + check_selection() + check_parse() + check_owner_kind()
              + check_escalation())
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
