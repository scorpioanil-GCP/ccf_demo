#!/usr/bin/env python3
"""Close the last hard cast gap — the reporting bank and its capital base.

`docs/spec-digest.md` §4 has carried this since the Wave 8 audit:

    A reporting bank entity with FFIEC Call Report / FR Y-9C
    🔴 Confirmed absent. The cast is obligors; the bank whose capital base is
    the denominator is not in the estate at all.

`large-exposure-rwa-concentration` §F asks for **"real Call Report and FR Y-9C
data for the reporting bank entity, so the capital base is genuine"**, and §C
marks the capital schedules and the NIC RSSD hierarchy `public`. A limit
utilisation is exposure divided by eligible capital — an invented denominator
makes every percentage in the capstone meaningless.

## Which bank, and why it is not an arbitrary pick

The estate already names real administrative agents, extracted from the EX-10
credit agreements in Wave 4. Measured 2026-08-22:

    JPMORGAN CHASE BANK, N.A.   15 facilities across  5 obligors
    BANK OF AMERICA, N.A.        6 facilities across  4 obligors
    GOLDMAN SACHS BANK USA       4 facilities across  1 obligor

So the reporting bank is chosen **from the estate's own filed documents**
rather than picked for size: JPMorgan Chase Bank, N.A. is already the
administrative agent on more of this cast's facilities than anyone else.

## What is real here, and what is not

Everything this script loads is **public and factual about the bank itself** —
its RSSD, its LEI, its holding company, and its own filed Call Report capital.
None of it is invented.

**The exposures are not, and that boundary must stay visible.** The estate's
facilities, balances and limits are `synthetic — internal` and always have
been; attaching them to a real bank is the same thing the estate already does
with 50 real named obligors. What this script must never do is let an
engineered breach read as a factual claim about a real institution — so it
loads the entity and the denominator only. **Every engineered limit breach
belongs to the capstone wave and must be labelled there**, and that is a
decision recorded for Wave 17, not one this script takes.

## A recorded source deviation

§C names FFIEC CDR Call Report schedules RC-C / RC-R, FR Y-9C and FFIEC 101.
This uses the **FDIC BankFind API**, which publishes the same Call Report
figures at bank level in JSON and needs no credential. Two consequences worth
stating rather than discovering later:

  - it is **bank-level** (RSSD 852218), not holding-company FR Y-9C
    (RSSD 1039502), so advanced-approaches detail from FFIEC 101 is absent;
  - the field names are FDIC's (`RBCT1J`, `RWAJT`), not the Call Report
    schedule line items.

Both are fine for a capital-base denominator and both are gaps the capstone
should close if it needs holding-company consolidation.

Output: sources/screening/reporting_bank.json

    uv run generators/fetch_reporting_bank.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from urllib.parse import quote

from ccf.config import REPO_ROOT
from ccf.fetch import get_json

SCREEN = REPO_ROOT / "sources" / "screening"

FDIC = "https://api.fdic.gov/banks"
GLEIF = "https://api.gleif.org/api/v1/lei-records"

#: JPMorgan Chase Bank, N.A. — see the docstring for why this one.
CERT = 628

#: Twelve quarters, so an `as_of` reconstruction over the capital base has
#: somewhere to go. §E puts the capital base at ~90 days' volatility, against
#: four hours for exposure — the sharpest freshness mismatch in the catalog.
QUARTERS = 12

#: The capital fields the capstone actually divides by, with what they are.
CAPITAL_FIELDS = {
    "RBCT1J": "tier 1 (core) capital",
    "RBCT2": "tier 2 capital",
    "RWAJT": "total risk-weighted assets",
    "RBC1RWAJ": "tier 1 risk-based capital ratio (%)",
    "RBCRWAJ": "total risk-based capital ratio (%)",
    "RBCT1CER": "common equity tier 1 ratio (%)",
    "ASSET": "total assets",
    "EQ": "total equity capital",
    "DEP": "total deposits",
}


def lei_for(name: str) -> dict | None:
    """Resolve a legal name to its GLEIF record. Never asserted from memory."""
    # Properly quoted, not hand-rolled: "JPMORGAN CHASE & CO." contains an
    # ampersand, which a replace()-based encoder turns into a query-parameter
    # separator and GLEIF rejects with a 400.
    payload = get_json(
        f"{GLEIF}?filter%5Bentity.names%5D={quote(name, safe='')}"
        f"&page%5Bsize%5D=5")
    for rec in payload.get("data", []):
        a = rec["attributes"]
        e = a["entity"]
        # US-jurisdiction and ACTIVE: the same legal name is used by foreign
        # branches carrying their own LEIs, and a branch is not the entity
        # whose capital base this is.
        if e.get("jurisdiction") == "US" and e.get("status") == "ACTIVE":
            return {"lei": a["lei"], "legal_name": e["legalName"]["name"],
                    "jurisdiction": e.get("jurisdiction"),
                    "status": e.get("status")}
    return None


def main() -> int:
    print("Reporting bank entity — closing the last hard cast gap\n")

    inst = get_json(
        f"{FDIC}/institutions?filters=CERT:{CERT}"
        f"&fields=NAME,CERT,FED_RSSD,RSSDHCR,NAMEHCR,CITY,STNAME,ESTYMD"
        f"&limit=1")
    if not inst.get("data"):
        print(f"  FAIL: FDIC returned no institution for CERT {CERT}")
        return 1
    bank = inst["data"][0]["data"]
    print(f"  bank        {bank['NAME']}")
    print(f"              RSSD {bank['FED_RSSD']} · CERT {bank['CERT']} · "
          f"{bank['CITY']}, {bank['STNAME']}")
    print(f"  holding co  {bank['NAMEHCR']}  RSSD {bank['RSSDHCR']}")

    fields = ",".join(["REPDTE", *CAPITAL_FIELDS])
    fin = get_json(
        f"{FDIC}/financials?filters=CERT:{CERT}&fields={fields}"
        f"&sort_by=REPDTE&sort_order=DESC&limit={QUARTERS}")
    quarters = [r["data"] for r in fin.get("data", [])]
    if not quarters:
        print("  FAIL: FDIC returned no financials")
        return 1

    bank_lei = lei_for("JPMorgan Chase Bank, National Association")

    # The holding company is resolved through the bank's own GLEIF Level 2
    # ULTIMATE-PARENT relationship, not by matching its name. FDIC writes
    # "JPMORGAN CHASE&CO" with no spaces and GLEIF writes "JPMORGAN CHASE &
    # CO." — a name match between the two registers fails on punctuation, and
    # guessing variants until one hits is how a wrong entity gets bound. The
    # relationship is what the registry itself asserts.
    holdco_lei = None
    if bank_lei:
        parent = get_json(f"{GLEIF}/{bank_lei['lei']}/ultimate-parent").get("data")
        if parent:
            a = parent["attributes"]
            e = a["entity"]
            holdco_lei = {"lei": a["lei"], "legal_name": e["legalName"]["name"],
                          "jurisdiction": e.get("jurisdiction"),
                          "status": e.get("status")}
    print(f"  bank LEI    {bank_lei['lei'] if bank_lei else 'NOT RESOLVED'}")
    print(f"  holdco LEI  {holdco_lei['lei'] if holdco_lei else 'NOT RESOLVED'}")

    print(f"\n  capital base, {len(quarters)} quarters "
          f"({quarters[-1]['REPDTE']} → {quarters[0]['REPDTE']})")
    for q in quarters[:3]:
        print(f"      {q['REPDTE']}  tier1 {q['RBCT1J']:>12,}  "
              f"rwa {q['RWAJT']:>14,.0f}  cet1 {q['RBCT1CER']}%")

    failures = []
    if holdco_lei is None:
        failures.append("the holding company did not resolve through GLEIF "
                        "Level 2; the RSSD hierarchy edge would have one "
                        "unidentified end")
    if bank_lei is None:
        failures.append("the bank's LEI did not resolve — the correlation key "
                        "to the rest of the estate would be missing")
    if len(quarters) < 4:
        failures.append(f"only {len(quarters)} quarters returned; an as-of "
                        f"reconstruction over the capital base needs several")
    # A capital base of zero, or missing RWA, makes every utilisation
    # percentage in the capstone either infinite or meaningless.
    for q in quarters:
        if not q.get("RBCT1J") or not q.get("RWAJT"):
            failures.append(f"{q['REPDTE']} is missing tier 1 capital or RWA")
            break
    if failures:
        print()
        for f in failures:
            print(f"  FAIL  {f}")
        return 1

    out = SCREEN / "reporting_bank.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "the reporting bank entity and its capital "
                                 "base — large-exposure-rwa-concentration §C/§F",
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "provenance": "public",
                "selection_basis": (
                    "chosen from the estate's own EX-10 filings: JPMorgan "
                    "Chase Bank, N.A. is the administrative agent on 15 "
                    "facilities across 5 obligors, more than any other agent "
                    "in the fetched corpus"),
                "source_deviation": (
                    "§C names FFIEC CDR RC-C/RC-R, FR Y-9C and FFIEC 101. This "
                    "uses the FDIC BankFind API, which publishes the same Call "
                    "Report figures at BANK level in JSON with no credential. "
                    "Holding-company FR Y-9C consolidation and FFIEC 101 "
                    "advanced-approaches detail are therefore absent."),
                "sources": {
                    "institution": f"{FDIC}/institutions?filters=CERT:{CERT}",
                    "financials": f"{FDIC}/financials?filters=CERT:{CERT}",
                    "lei": GLEIF,
                },
                "capital_field_meanings": CAPITAL_FIELDS,
                "bank": {
                    "rssd": bank["FED_RSSD"],
                    "cert": bank["CERT"],
                    "legal_name": bank["NAME"],
                    "city": bank["CITY"],
                    "state": bank["STNAME"],
                    "established": bank.get("ESTYMD"),
                    "lei": bank_lei["lei"] if bank_lei else None,
                    "gleif_legal_name": bank_lei["legal_name"] if bank_lei else None,
                },
                "holding_company": {
                    "rssd": bank["RSSDHCR"],
                    "legal_name": bank["NAMEHCR"],
                    "lei": holdco_lei["lei"] if holdco_lei else None,
                    "gleif_legal_name": (holdco_lei["legal_name"]
                                         if holdco_lei else None),
                    "resolved_via": ("GLEIF Level 2 ultimate-parent of the "
                                     "bank, not a name match"),
                },
                "quarter_count": len(quarters),
                "capital": quarters,
            },
            indent=1,
        )
        + "\n"
    )
    print(f"\n  written: {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
