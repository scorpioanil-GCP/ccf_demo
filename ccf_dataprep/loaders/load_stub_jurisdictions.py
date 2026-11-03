#!/usr/bin/env python3
"""Exhibit 21 jurisdictions for the 344 bridging stubs, which were dropped.

`corporate-family-tree` §C row 6 asks for the subsidiary list as *name,
jurisdiction and ownership %*. `load_fluree_wave3.py` loads the name and
throws the other two away:

    triples += entity_triples(local, sub["name"], None, "synthetic — bridging")

Jurisdiction is not a source limitation. `sources/screening/exhibit21.json`
has held it since Wave 3 for 1,422 of 1,635 subsidiaries, and for 304 of the
344 stubs actually loaded. This puts it in the ledger.

**Why in Fluree, when Postgres owns entity attributes.** §D step 2 runs the
Policy Operator BEFORE traversal, so the jurisdiction envelope "shapes what is
walked rather than what is returned". A filter that cannot be evaluated during
the walk is not that filter. §C agrees and assigns this row to Fluree; §F's
`>= 1 family spanning three jurisdictions` is the condition it exists for.

**Two predicates, because normalising is lossy.**

    ex:jurisdictionCode    ISO 3166-1 alpha-3, the join and filter key
    ex:filedJurisdiction   the string exactly as filed

118 of the 344 stubs are filed as `Delaware` and 19 more as `DELAWARE`; every
one of them normalises to `USA`, and so do Nevada, Texas and twenty other
states. Keeping only the code would make a Delaware LLC and a Nevada LLC
indistinguishable, which is real filed information and free to carry. Keeping
only the filed string would put `Delaware` in the same field as `GBR` and
`HKG` — the 190 ICIJ nodes already on `ex:jurisdictionCode` are alpha-3, and
one predicate holding two vocabularies is the unit-field collision Wave 11b
was bitten by. So: both, each in its own predicate, and the map below is the
audit trail between them.

Run: uv run loaders/load_stub_jurisdictions.py --dry-run
     uv run loaders/load_stub_jurisdictions.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, REPO_ROOT

SOURCE = REPO_ROOT / "sources" / "screening" / "exhibit21.json"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
P_JURISDICTION_CODE = f"{EX}jurisdictionCode"
P_FILED_JURISDICTION = f"{EX}filedJurisdiction"
BRIDGING = "synthetic — bridging"
BATCH = 400

#: US states, DC and the territories that appear in Exhibit 21 filings. A
#: state of incorporation is not a jurisdiction in the sense §D's Policy
#: Operator means -- entitlement is jurisdiction VISIBILITY, and Delaware and
#: Florida are not separately visible to anyone -- so all of them collapse to
#: USA and the filed string is kept alongside.
US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "district of columbia", "florida", "georgia",
    "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
    "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "puerto rico", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
}

#: `Georgia` is BOTH a US state and a sovereign country (GEO), and the map
#: above resolves it to USA. That is a judgement, so it is written down: the
#: single occurrence in this corpus is `ICA South, Inc` in Amphenol's list,
#: sitting among New York, Washington and Delaware entries and carrying a US
#: corporate suffix. Read as the state. If a later filer means the country,
#: this line is where it will be wrong.
AMBIGUOUS_READ_AS_US_STATE = {"georgia"}

#: Sub-national names that are not US states but still resolve to a country.
SUBNATIONAL = {
    "ontario": "CAN", "british columbia": "CAN", "quebec": "CAN",
    "alberta": "CAN", "nova scotia": "CAN", "manitoba": "CAN",
    "new brunswick": "CAN", "saskatchewan": "CAN",
    "england": "GBR", "wales": "GBR", "scotland": "GBR",
    "northern ireland": "GBR", "england and wales": "GBR",
}

COUNTRIES = {
    "australia": "AUS", "austria": "AUT", "belgium": "BEL", "bermuda": "BMU",
    "brazil": "BRA", "canada": "CAN", "cayman islands": "CYM", "chile": "CHL",
    "china": "CHN", "colombia": "COL", "costa rica": "CRI",
    "czech republic": "CZE", "denmark": "DNK", "finland": "FIN",
    "france": "FRA", "germany": "DEU", "hong kong": "HKG", "hungary": "HUN",
    "india": "IND", "indonesia": "IDN", "ireland": "IRL", "israel": "ISR",
    "italy": "ITA", "japan": "JPN", "jersey": "JEY", "luxembourg": "LUX",
    "malaysia": "MYS", "malta": "MLT", "mexico": "MEX",
    "netherlands": "NLD", "new zealand": "NZL", "norway": "NOR",
    "panama": "PAN", "peru": "PER", "philippines": "PHL", "poland": "POL",
    "portugal": "PRT", "singapore": "SGP", "south africa": "ZAF",
    "south korea": "KOR", "korea": "KOR", "spain": "ESP", "sweden": "SWE",
    "switzerland": "CHE", "taiwan": "TWN", "thailand": "THA",
    "turkey": "TUR", "united arab emirates": "ARE", "united kingdom": "GBR",
    "united states": "USA", "uruguay": "URY", "vietnam": "VNM",
}


def alpha3(filed: str) -> str | None:
    """ISO 3166-1 alpha-3 for one filed jurisdiction string, or None.

    Returns None ONLY for the empty string. An unrecognised non-empty value
    raises, because the alternative -- skipping it -- would leave a stub
    silently without a jurisdiction and look identical to a stub whose filer
    left the column blank. Those are different facts.
    """
    key = filed.strip().lower()
    if not key:
        return None
    if key in US_STATES:
        return "USA"
    if key in SUBNATIONAL:
        return SUBNATIONAL[key]
    if key in COUNTRIES:
        return COUNTRIES[key]
    raise KeyError(filed)


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str) -> str:
    return f'<{s}> <{p}> "{esc(o)}" .'


def filed_by_name() -> dict[str, str]:
    """Subsidiary name -> the one non-empty jurisdiction any filer gave it.

    A name listed by two filers with two DIFFERENT jurisdictions cannot be
    resolved from the label alone, and the label is the only handle the ledger
    offers. Measured 0 such names over this corpus; kept as a hard error
    rather than a preference, because picking one silently is how a stub ends
    up carrying another company's country.
    """
    doc = json.loads(SOURCE.read_text())
    seen: dict[str, set[str]] = defaultdict(set)
    for filer in doc["filers"]:
        for sub in filer.get("subsidiaries") or []:
            value = (sub.get("jurisdiction") or "").strip()
            if value:
                seen[sub["name"]].add(value)
    clashes = {n: v for n, v in seen.items() if len(v) > 1}
    if clashes:
        print(f"  FAIL: {len(clashes)} subsidiary names carry two "
              f"jurisdictions: {list(clashes.items())[:3]}", file=sys.stderr)
        raise SystemExit(1)
    return {n: next(iter(v)) for n, v in seen.items()}


def stubs() -> list[tuple[str, list[str], bool]]:
    """(subject, its labels, already has a jurisdiction) per bridging stub.

    Keyed by SUBJECT, and labels is a list, because one node carries two.
    `local_name()` in load_fluree_wave3.py normalises through `.title()` and
    strips punctuation, so `SUBSIDIARY` and `Subsidiary` -- Exhibit 21 TABLE
    HEADERS mis-parsed as company names, one from Genesis Energy and one from
    Hain Celestial -- both became `SubSubsidiary` and both labels landed on
    the one node. It is the only such collision in all 1,635 subsidiaries, and
    it is recorded in known-issues; the point here is that iterating the query
    ROWS would process that subject twice and could give it two different
    jurisdictions, one silently overwriting nothing and both being asserted.
    """
    rows = fluree.query(
        f"SELECT ?s ?l FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
        f'?s <{EX}provenance> "{BRIDGING}" . ?s <{RDFS_LABEL}> ?l }} '
        f"LIMIT 2000")["results"]["bindings"]
    done = {b["s"]["value"] for b in fluree.query(
        f"SELECT ?s ?j FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
        f"?s <{P_JURISDICTION_CODE}> ?j }} LIMIT 5000")["results"]["bindings"]}
    labels: dict[str, list[str]] = defaultdict(list)
    for b in rows:
        labels[b["s"]["value"]].append(b["l"]["value"])
    return [(s, ls, s in done) for s, ls in labels.items()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    filed = filed_by_name()
    all_stubs = stubs()
    print(f"  bridging stubs in the ledger      {len(all_stubs)}")
    print(f"  already carrying a jurisdiction   "
          f"{sum(1 for _, _, d in all_stubs if d)}")

    unknown: list[str] = []
    triples: list[str] = []
    blank = 0
    unmatched = 0
    by_code: dict[str, int] = defaultdict(int)
    sample: tuple[str, str, str] | None = None

    known_names = {s["name"] for f in json.loads(SOURCE.read_text())["filers"]
                   for s in f.get("subsidiaries") or []}

    for subject, labels, already in all_stubs:
        if already:
            continue
        values = {filed[a] for a in labels if a in filed}
        if len(values) > 1:
            print(f"  FAIL: <{subject}> carries labels {labels} which name "
                  f"subsidiaries filed in {sorted(values)}. Two companies "
                  f"were merged into one node; resolve that before giving it "
                  f"a country.", file=sys.stderr)
            return 1
        if not values:
            # No jurisdiction to read. Two different reasons, counted apart:
            # the filer left the column blank, or the label names nothing in
            # the source at all.
            if any(a in known_names for a in labels):
                blank += 1
            else:
                unmatched += 1
            continue
        raw = next(iter(values))
        try:
            code = alpha3(raw)
        except KeyError:
            unknown.append(raw)
            continue
        assert code is not None          # filed_by_name drops empty values
        triples.append(triple(subject, P_JURISDICTION_CODE, code))
        triples.append(triple(subject, P_FILED_JURISDICTION, raw))
        by_code[code] += 1
        if sample is None:
            sample = (subject, code, raw)

    if unknown:
        print(f"\n  FAIL: {len(set(unknown))} filed jurisdictions are not in "
              f"the map: {sorted(set(unknown))}", file=sys.stderr)
        print("  Add them rather than skipping — an unmapped value and a "
              "blank column are different facts.", file=sys.stderr)
        return 1

    print(f"  filed blank by the filer          {blank}")
    if unmatched:
        print(f"  label absent from the source      {unmatched}")
    print(f"  to write                          {len(triples) // 2} "
          f"stubs, {len(triples)} triples")
    print(f"  distinct jurisdictions            {len(by_code)}  "
          f"{dict(sorted(by_code.items(), key=lambda x: -x[1]))}")

    # Every `ex:` term in this ledger declares itself as an application
    # extension rather than a FIBO term, so a consumer holding only the graph
    # can tell the two apart. `ex:jurisdictionCode` already carries the pair;
    # `ex:filedJurisdiction` is new here. Written unconditionally -- it is two
    # triples and RDF is a set, so re-asserting them is a no-op.
    schema = [
        triple(P_FILED_JURISDICTION, f"{EX}isFiboTerm", "false"),
        triple(P_FILED_JURISDICTION, f"{EX}schemaNote",
               "application extension: the jurisdiction string exactly as "
               "filed in EDGAR Exhibit 21, before normalisation to the ISO "
               "3166-1 alpha-3 code on ex:jurisdictionCode. Kept because "
               "normalising is lossy — 137 stubs are filed in Delaware and "
               "all of them normalise to USA. See "
               "docs/ccf_dataprep_v2.md and the fibo-iri-binding article."),
    ]

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        if sample:
            print(f"  sample: <{sample[0]}> jurisdictionCode \"{sample[1]}\" "
                  f"filedJurisdiction \"{sample[2]}\"")
        return 0

    fluree.update("INSERT DATA {\n" + "\n".join(schema) + "\n}")

    if not triples:
        print("\n  schema note re-asserted; every stub already carries a "
              "jurisdiction.")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    # Read back a NAMED subject and its exact VALUE, not a count. A count
    # cannot see a field that was written blank, overwritten, or written to
    # the wrong subject -- known-issues §19.2, where 17,387 embeddings were
    # nulled and the passage count was identical either side.
    assert sample is not None
    subject, code, raw = sample
    got = fluree.query(
        f"SELECT ?c ?f FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
        f"<{subject}> <{P_JURISDICTION_CODE}> ?c . "
        f"<{subject}> <{P_FILED_JURISDICTION}> ?f }}")["results"]["bindings"]
    values = {(b["c"]["value"], b["f"]["value"]) for b in got}
    if values != {(code, raw)}:
        print(f"\n  FAIL: <{subject}> reads back as {values}, expected "
              f"{{({code!r}, {raw!r})}}", file=sys.stderr)
        return 1
    print(f"\n  verified: <{subject.rsplit('/', 1)[-1]}> -> {code} "
          f"(filed {raw!r})")
    print(f"  {len(triples) // 2} stubs now carry a jurisdiction.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
