#!/usr/bin/env python3
"""GLEIF Level 1 records for the subsidiaries the family tree already names.

`corporate-family-tree` §C row 8 assigns *"entity attributes for traversal
results"* to Postgres, inherited from `counterparty-reference-snapshot`. The
ledger holds 155 entities carrying a real GLEIF LEI and `ccf_v2.legal_entity`
resolves 50 of them, so a traversal returns entities whose Enrich step yields
nothing — and because the GRAPH is complete, the result looks correct.

Wave 3 fetched Level 2 (who owns whom) for these LEIs and never fetched
Level 1 (who they are). This fetches the Level 1 records.

**Which LEIs, and why derived rather than listed.** Every LEI in
`sources/screening/gleif_relationships.json` under `entities`, minus the 50
anchors, which `load_postgres_wave1.py` already loaded. That is 103. Deriving
it from the source file rather than pinning a hand-copied list means the set
cannot drift away from the graph it is supposed to resolve.

**Two LEIs in the ledger are deliberately NOT here.** JPMorgan Chase Bank NA
(`7H6GLXDRUGQFU57RNE97`) and JPMORGAN CHASE&CO (`8I5DZWZKVSZI1NUHU748`) also
carry real LEIs and are also absent from `legal_entity`, but they are not
missing: `ccf_v2.reporting_bank` is their single writer and holds name, LEI,
role, city and state. Copying them into `legal_entity` to make one join
tidier would break single-writer discipline for the sake of a count.

Output: sources/gleif_l1/ — raw API pages plus manifest.json

Run: uv run generators/fetch_gleif_subsidiaries.py
"""

from __future__ import annotations

import json
import sys

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch

RELATIONSHIPS = REPO_ROOT / "sources" / "screening" / "gleif_relationships.json"
ANCHORS = REPO_ROOT / "sources" / "screening" / "anchors_final.json"
OUT = REPO_ROOT / "sources" / "gleif_l1"
API = "https://api.gleif.org/api/v1/lei-records"

#: GLEIF accepts a comma-separated filter. 40 keeps the URL well under any
#: proxy's length limit and still costs only three requests.
CHUNK = 40


def target_leis() -> list[str]:
    entities = set(json.loads(RELATIONSHIPS.read_text())["entities"])
    anchors = {a["lei"] for a in json.loads(ANCHORS.read_text())["anchors"]}
    return sorted(entities - anchors)


def main() -> int:
    leis = target_leis()
    print(f"  {len(leis)} non-anchor LEIs named by the Level 2 graph")

    manifest = SourceManifest(
        source="gleif_l1",
        description=(
            "GLEIF LEI-CDF Level 1 reference records for the non-anchor "
            "entities in the corporate-family-tree graph. Level 2 (who owns "
            "whom) was fetched in Wave 3; this is who they are."),
        licence="CC0 1.0 — GLEIF publishes the LEI data under CC0",
    )

    records: dict[str, dict] = {}
    for i in range(0, len(leis), CHUNK):
        chunk = leis[i:i + CHUNK]
        url = f"{API}?filter[lei]={','.join(chunk)}&page[size]={CHUNK}"
        path = fetch(url, manifest, f"page-{i // CHUNK + 1:02d}.json",
                     headers={"Accept": "application/vnd.api+json"})
        payload = json.loads(path.read_text())
        for rec in payload.get("data", []):
            records[rec["id"]] = rec["attributes"]
        print(f"    page {i // CHUNK + 1}: asked {len(chunk)}, "
              f"have {len(records)} total")

    manifest.save()

    # A LEI the API does not return is a fact worth naming: it means the
    # record was retired or merged, not that the fetch failed. Silence here
    # would show up much later as an entity that still will not resolve.
    absent = [lei for lei in leis if lei not in records]
    if absent:
        print(f"\n  {len(absent)} LEIs returned NO record: {absent}")

    rows = []
    for lei in leis:
        a = records.get(lei)
        if a is None:
            continue
        ent, reg = a["entity"], a["registration"]
        hq = ent.get("headquartersAddress") or {}
        legal = ent.get("legalAddress") or {}
        rows.append({
            "lei": lei,
            "legal_name": ent["legalName"]["name"],
            "legal_jurisdiction": ent.get("jurisdiction"),
            "entity_status": ent.get("status"),
            "registration_status": reg.get("status"),
            "next_renewal_date": (reg.get("nextRenewalDate") or "")[:10] or None,
            "initial_registration": (reg.get("initialRegistrationDate") or "")[:10] or None,
            "legal_form": (ent.get("legalForm") or {}).get("id"),
            "address_country": legal.get("country"),
            "address_city": legal.get("city"),
            "address_region": legal.get("region"),
            # Fetched and recorded even though `legal_entity` has nowhere to
            # put it yet. counterparty-reference-snapshot §C names TWO
            # addresses and only the legal one was ever kept -- that gap is
            # live in spec_coverage.py, and throwing the field away here
            # would make closing it need a THIRD fetch of the same file.
            "hq_country": hq.get("country"),
            "hq_city": hq.get("city"),
            "hq_region": hq.get("region"),
        })

    out = OUT / "subsidiaries_l1.json"
    out.write_text(json.dumps({
        "description": "GLEIF Level 1 for non-anchor family-tree entities",
        "source": API,
        "requested": len(leis),
        "resolved": len(rows),
        "absent": absent,
        "records": rows,
    }, indent=2) + "\n")

    with_hq = sum(1 for r in rows if r["hq_country"])
    print(f"\n  {len(rows)} records written to {out.relative_to(REPO_ROOT)}")
    print(f"  {with_hq} carry a headquarters address distinct from the "
          f"legal one: "
          f"{sum(1 for r in rows if r['hq_country'] != r['address_country'])} "
          f"differ in COUNTRY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
