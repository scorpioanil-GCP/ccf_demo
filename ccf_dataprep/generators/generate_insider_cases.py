#!/usr/bin/env python3
"""Wave 19 Task 8 — Regulation O insider case, with an invented insider.

**Decision (Dave, 2026-08-27): real rule text, invented insiders.** No real
person is named as a borrower on an engineered breach.

## Why the shape is one person, one related interest, one real facility

§6 of `docs/wave19-design.md` already measured and rejected inventing an
exposure large enough to breach CRR's or the PRA's 25%-of-capital limit: the
largest real connected group is 5.4% of JPMorgan's tier 1 capital, and
manufacturing a ~$74bn exposure to clear 25% would dwarf everything else in
the estate. Regulation O's binding number is different in kind, not degree:
12 CFR 215.4(b)(2) caps credit to an insider **and all related interests of
that person** at an absolute **$500,000** -- a dollar figure, not a
percentage. So instead of inventing a bigger loan, this case attaches an
invented INSIDER RELATIONSHIP to an existing, real-sized facility that was
never engineered for this purpose:

    Digital Turbine, Inc. (LEI 549300D0WZR1VI2QGB24, real, public,
    is_anchor=true) already carries FAC-18DF7D, a $285,000,000 Term Loan,
    loaded as an ordinary anchor-obligor facility with no connection to
    Reg O whatsoever.

That $285,000,000 is 0.096% of JPMorgan's $295.8bn tier 1 capital -- nowhere
near CRR's or the PRA's 25% line -- and simultaneously 570x over Reg O's
$500,000 absolute cap. Nothing about the exposure is invented. The ONLY
engineered fact is that an invented director/executive officer of the
reporting bank is deemed, for this case, to control Digital Turbine within
the meaning of 12 CFR 215.2(n)(1) ("a company that is controlled by that
person"). Real company, invented relationship -- the identical shape Task 7
already used for the four `economicallyDependentOn` edges, and the shape
`docs/wave19-design.md` names explicitly: *"a real company's public identity
is never in question, and no sentence here asserts anything about it as
fact."*

## Why the invented person is ONE person, not a director AND a separate
## executive officer

The brief's Step 1 names three things to invent: "the director, the
executive officer and the related interest." Read as three populated rows,
that would mean two placeholder natural persons with no distinguishing
function, when 12 CFR 215.4(b)(2) itself aggregates across "that person, AND
all related interests of that person" as ONE ceiling regardless of which
`215.2(h)` insider category (executive officer, director, or principal
shareholder) applies. A bank director who is also an executive officer is
ordinary (JPMorgan's own real proxy lists several) -- inventing a SECOND,
functionally-identical placeholder person would be inventory, not signal,
and this project's own rule ("hitting the count while missing the
condition is a failure") cuts the other way just as hard against padding a
count nobody asked to recompute. One dual-hatted insider plus one related
interest is what 215.4(b)(2)'s own aggregation actually tests.

## The real DEF 14A precedent, and what is deliberately NOT taken from it

JPMorgan Chase & Co.'s own most recent proxy (CIK 0000019617, DEF 14A filed
2026-04-06, accession 0000019617-26-000096) is fetched below and contains a
real, filed section -- "Policies and procedures for approval of related
party transactions" -- that names Regulation O by name:

    "These include transactions in the ordinary course of business involving
    financial products and services provided by, or to, the Firm, including
    loans, provided such transactions are in compliance with the
    Sarbanes-Oxley Act of 2002, Federal Reserve Board Regulation O and other
    applicable laws and regulations."

That sentence -- naming the REAL compliance mechanism (a written "Related
Persons Policy," reviewed by the General Counsel and the Governance
Committee) -- is the citable methodology precedent this case follows in
shape. The SAME filing's following section, "Transactions with directors,
executive officers and 5% shareholders," names REAL individuals and REAL
transactions (a preferred-stock redemption, a co-investment program, an
asset-management fee arrangement). None of those names, and no fact about
any of those transactions, appears anywhere in this generator's output --
that section exists in the fetched artifact for provenance completeness
only (recorded in `sources/def14a/manifest.json`, same as the 48 anchor-cast
proxies Wave 10 already fetched), and is never read past confirming the
Regulation O sentence exists. Task 11 ("methodology documentation ->
MongoDB") is the task that writes the citable methodology text; this task's
job stops at citing that a real precedent exists.

## Citations

Real 12 CFR 215 passages, loaded by Task 4/`load_regime_mongo.py`, resolved
live below rather than hand-copied (`docs/known-issues.md`'s repeated lesson
that a citation is a claim, verified here by querying the passage back):

    215.2(h)     "Insider means an executive officer, director, or
                  principal shareholder, and includes any related interest
                  of such a person."
    215.2(n)(1)  "A company that is controlled by that person; or"
    215.4(b)(2)  "In no event may a member bank extend credit to any
                  insider ... in an amount that, when aggregated with all
                  other extensions of credit to that person, and all
                  related interests of that person, exceeds $500,000..."

Output: sources/screening/wave19_insider_case.json

    uv run generators/generate_insider_cases.py
    uv run generators/generate_insider_cases.py --dry-run   # skip the DEF14A fetch
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, mongo_db, pg_connect
from ccf.fetch import SourceManifest, fetch, get_json

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave19_insider_case.json"

S = PG_SCHEMA_V2

PROVENANCE = "synthetic — engineered"

#: The invented insider. `SYN-` per docs/ccf_dataprep_v2.md's synthetic
#: identifier convention; `minted` (not `sec_cik` or `psc`) because this
#: person is not derived from any real registry -- the third
#: `person_key_source` the `person` table's own CHECK constraint already
#: permits, unused by any prior wave.
PERSON = {
    "person_key": "SYN-INSIDER-JPM-01",
    "person_key_source": "minted",
    "owner_kind": "natural",
    "cik": None,
    # NOT NULL in ccf_v2.person. There is no filing to quote, so this is
    # the display name itself -- the honest value when "as filed" does not
    # apply, not a null this schema's constraint would refuse anyway.
    "name_as_filed": "Marguerite Castellane",
    "display_name": "Marguerite Castellane",
    "name_first": "Marguerite",
    "name_last": "Castellane",
    "name_middle": None,
    "name_suffix": None,
    "provenance": PROVENANCE,
    "source": ("invented insider — Wave 19 Task 8, Regulation O (12 CFR "
               "215) demonstration; minted for this case, not derived from "
               "any DEF 14A roster or other real registry"),
}

#: The related interest. Real, existing, untouched by this task on the
#: exposure side -- the whole point per the module docstring above.
RELATED_INTEREST_LEI = "549300D0WZR1VI2QGB24"   # Digital Turbine, Inc.
RELATED_INTEREST_FACILITY = "FAC-18DF7D"         # $285,000,000 Term Loan

#: Real 12 CFR 215 passages (Task 4), resolved live in main() -- these are
#: the EXPECTED provisions; verify_citations() fails loudly if any of them
#: no longer resolves to the text quoted in the module docstring, rather
#: than trusting the hard-coded id.
CITATION_PROVISIONS = {
    "insider_definition": "215.2(h)",
    "related_interest_definition": "215.2(n)(1)",
    "absolute_cap": "215.4(b)(2)",
}

#: The compliance function the REAL DEF 14A names -- a functional office,
#: never a specific named individual, so citing it names no real person.
ASSERTED_BY = "JPMorganChase General Counsel — Related Persons Policy review"
ASSERTED_ON = "2026-06-15"

DEF14A_CIK = 19617
DEF14A_SOURCE = "def14a"


def verify_citations() -> dict[str, str]:
    """Resolve each expected provision to a live Mongo passage_id and text.

    Hard-codes the PROVISION LABEL, not the passage_id -- ids are
    content-derived hashes (`generators/extract_regime_passages.py`) and
    would silently go stale if that generator ever re-ran with a fix. The
    label is the stable handle; the id is looked up fresh every run.
    """
    db = mongo_db(write=False)
    out: dict[str, str] = {}
    texts: dict[str, str] = {}
    for key, provision in CITATION_PROVISIONS.items():
        row = db.passage.find_one({"regime": "reg-o", "provision": provision})
        if row is None:
            print(f"FATAL: no reg-o passage for provision {provision!r} -- "
                  "Task 4/load_regime_mongo.py must run first.")
            sys.exit(2)
        out[key] = row["passage_id"]
        texts[key] = row["text"]
    if "$500,000" not in texts["absolute_cap"]:
        print("FATAL: the resolved absolute_cap passage no longer contains "
              "'$500,000' -- the provision label may have drifted to a "
              "different paragraph. Not proceeding on an unverified cite.")
        sys.exit(2)
    if "controlled by that person" not in texts["related_interest_definition"]:
        print("FATAL: the resolved related_interest_definition passage no "
              "longer reads 'controlled by that person'.")
        sys.exit(2)
    return out


def verify_related_interest() -> dict:
    """The facility this case rests on, read live -- never assumed from the
    module docstring's own $285,000,000 figure."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT legal_name, is_anchor, provenance FROM "{S}".legal_entity '
            f'WHERE lei = %s', (RELATED_INTEREST_LEI,))
        row = cur.fetchone()
        if row is None:
            print(f"FATAL: {RELATED_INTEREST_LEI} not found in legal_entity.")
            sys.exit(2)
        legal_name, is_anchor, provenance = row
        cur.execute(
            f'SELECT commitment_amount, currency, facility_type '
            f'FROM "{S}".facility WHERE facility_id = %s AND borrower_lei = %s',
            (RELATED_INTEREST_FACILITY, RELATED_INTEREST_LEI))
        frow = cur.fetchone()
        if frow is None:
            print(f"FATAL: {RELATED_INTEREST_FACILITY} does not resolve to "
                  f"borrower {RELATED_INTEREST_LEI}.")
            sys.exit(2)
        commitment, currency, facility_type = frow
        cur.execute(f'SELECT tier1_capital, unit FROM "{S}".bank_capital '
                    f'ORDER BY report_date DESC LIMIT 1')
        tier1_row = cur.fetchone()
    if not is_anchor or provenance != "public":
        print(f"FATAL: {legal_name} is not a real public anchor obligor "
              f"(is_anchor={is_anchor}, provenance={provenance!r}) -- this "
              "case requires an UNTOUCHED real obligor on the exposure side.")
        sys.exit(2)
    commitment = float(commitment)
    if commitment <= 500_000:
        print(f"FATAL: {RELATED_INTEREST_FACILITY} commitment "
              f"{commitment:,.0f} does not exceed Reg O's $500,000 cap -- "
              "this case would not actually demonstrate a breach.")
        sys.exit(2)
    tier1_thousands = float(tier1_row[0]) if tier1_row else None
    tier1_usd = tier1_thousands * 1000 if tier1_thousands else None  # USD_THOUSANDS
    return {
        "lei": RELATED_INTEREST_LEI,
        "legal_name": legal_name,
        "facility_id": RELATED_INTEREST_FACILITY,
        "facility_type": facility_type,
        "commitment_amount": commitment,
        "currency": currency,
        "reg_o_cap_usd": 500_000,
        "multiple_of_reg_o_cap": round(commitment / 500_000, 1),
        "pct_of_tier1_capital": (round(commitment / tier1_usd * 100, 4)
                                  if tier1_usd else None),
        "crr_pra_limit_pct": 25.0,
    }


def fetch_def14a_precedent(*, dry_run: bool) -> dict:
    """The real precedent this case's SHAPE follows -- see module docstring.

    Fetched into the SAME `sources/def14a/` manifest Wave 10 already
    maintains for the 48 anchor-cast proxies, not a new directory, so
    provenance for JPMorgan's own filing sits beside theirs rather than in a
    second, competing location.
    """
    manifest = SourceManifest(
        source=DEF14A_SOURCE,
        description="EDGAR DEF 14A proxy statements — anchor cast (Wave 10) "
                     "plus JPMorgan Chase & Co.'s own proxy (Wave 19 Task 8), "
                     "cited for its real Related Persons Policy language only",
        licence="US government work / public filing",
    )
    submissions = get_json(
        f"https://data.sec.gov/submissions/CIK{DEF14A_CIK:010d}.json", is_sec=True)
    recent = submissions["filings"]["recent"]
    rows = [(a, d, p) for f, a, d, p in zip(
        recent["form"], recent["accessionNumber"],
        recent["filingDate"], recent["primaryDocument"])
        if f == "DEF 14A"]
    if not rows:
        print("FATAL: no DEF 14A found for JPMorgan Chase & Co. (CIK "
              f"{DEF14A_CIK}).")
        sys.exit(2)
    accession, filed, primary = rows[0]
    url = (f"https://www.sec.gov/Archives/edgar/data/{DEF14A_CIK}/"
           f"{accession.replace('-', '')}/{primary}")
    filename = f"{DEF14A_CIK:010d}_{accession}.htm"

    if dry_run:
        print(f"  [plan] {url}")
        return {
            "cik": DEF14A_CIK, "accession": accession, "filed": filed,
            "url": url, "quote": None, "retrieved_at": None,
        }

    path = fetch(url, manifest, filename, is_sec=True)
    raw = path.read_text(encoding="utf-8", errors="replace")
    plain = re.sub(r"<[^>]+>", " ", raw)
    plain = re.sub(r"&#?\w+;", " ", plain)
    plain = re.sub(r"\s+", " ", plain)
    idx = plain.find("Federal Reserve Board Regulation O")
    if idx < 0:
        print("FATAL: the fetched DEF 14A no longer names 'Federal Reserve "
              "Board Regulation O' -- the citation this case rests on has "
              "gone stale. Not proceeding on an unverified quote.")
        sys.exit(2)
    quote = plain[idx - 220:idx + 40].strip()
    return {
        "cik": DEF14A_CIK,
        "accession": accession,
        "filed": filed,
        "url": url,
        "quote": quote,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": ("Real, filed text naming Regulation O as the compliance "
                 "regime governing related-person loans. The filing's own "
                 "'Transactions with directors, executive officers and 5% "
                 "shareholders' section names real individuals and real "
                 "transactions -- NONE of them are used anywhere in this "
                 "dataset. Only this policy sentence is cited."),
    }


def build(*, dry_run: bool) -> dict:
    citations = verify_citations()
    related_interest = verify_related_interest()
    def14a = fetch_def14a_precedent(dry_run=dry_run)

    print("Wave 19 Task 8 — Regulation O insider case\n")
    print(f"  insider              {PERSON['display_name']} "
          f"({PERSON['person_key']}, {PERSON['provenance']})")
    print(f"  related interest     {related_interest['legal_name']} "
          f"({related_interest['lei']})")
    print(f"  facility             {related_interest['facility_id']}  "
          f"{related_interest['commitment_amount']:,.0f} "
          f"{related_interest['currency']}")
    print(f"  vs Reg O $500,000    {related_interest['multiple_of_reg_o_cap']}x over")
    if related_interest["pct_of_tier1_capital"] is not None:
        print(f"  vs tier 1 capital    {related_interest['pct_of_tier1_capital']}% "
              f"(CRR/PRA limit {related_interest['crr_pra_limit_pct']}%) — compliant")
    print(f"  citations            {list(citations.values())}")
    print(f"  DEF 14A precedent    CIK {def14a['cik']}, accession "
          f"{def14a['accession']}, filed {def14a['filed']}")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provenance": PROVENANCE,
        "person": PERSON,
        "insider_categories": ["director", "executive officer"],
        "reporting_bank_role": "reg_o_insider",
        "related_interest": related_interest,
        "citations": citations,
        "def14a_precedent": def14a,
        "asserted_by": ASSERTED_BY,
        "asserted_on": ASSERTED_ON,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                     help="verify citations and the facility, print the plan, "
                          "skip the DEF14A fetch and skip writing the artifact")
    args = ap.parse_args()

    doc = build(dry_run=args.dry_run)

    if args.dry_run:
        print("\n  [dry-run] nothing fetched, nothing written")
        return 0

    SCREEN.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"\n  wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
