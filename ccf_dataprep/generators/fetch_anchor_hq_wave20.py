#!/usr/bin/env python3
"""Wave 20 Task 3 -- fetch the 50 anchors' GLEIF Level 1 HEADQUARTERS address.

    uv run generators/fetch_anchor_hq_wave20.py

## Why this exists at all

`counterparty-reference-snapshot` §C names `addresses`, plural, and §B says
which two: `headquarters and legal address`. GLEIF LEI-CDF Level 1 publishes
both. This estate has only ever held one.

The 103 non-anchor subsidiaries are already fine -- Wave 15's
`generators/fetch_gleif_subsidiaries.py` captured `headquartersAddress`
alongside `legalAddress`, and `sources/gleif_l1/subsidiaries_l1.json` carries
both for all 103. The 50 ANCHORS predate that: their Level 1 came from Wave 1
screening (`sources/screening/anchors_final.json`), whose records carry
`legal_address_country / _city / _region` and no headquarters field at all.

So this is not a re-fetch of something we discarded. It is the half that was
never fetched, and it is the only half that needs the network.

## Why the distinction is worth the round trip

Measured on the 103 already held: 33 carry a headquarters address that
DIFFERS from the legal one, and the pattern is the one the catalog cares
about -- legal domicile Wilmington, Delaware; operating seat Westerville,
Alpharetta, Whippany. A consumer joining on "where is this counterparty"
against an unlabelled triple silently gets the registered agent's office in
Delaware rather than the place the business is run from. That is a wrong
answer returned confidently, not a missing one.

## Idempotency

Re-runnable. Writes one file, whole, and records `retrieved_at` in it. The
GLEIF API is read-only from here; nothing about this script mutates the
estate.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

ANCHORS = REPO_ROOT / "sources" / "screening" / "anchors_final.json"
OUT_DIR = REPO_ROOT / "sources" / "gleif_l1"
OUT = OUT_DIR / "anchors_hq_l1.json"

API = "https://api.gleif.org/api/v1/lei-records/{lei}"


def fetch_one(lei: str) -> dict | None:
    """Level 1 record for one LEI, or None if GLEIF does not hold it.

    A 404 is a real answer -- an LEI can lapse out of the published set -- and
    is recorded as an absence rather than retried or silently skipped.
    """
    req = urllib.request.Request(
        API.format(lei=lei), headers={"Accept": "application/vnd.api+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def extract(payload: dict) -> dict:
    ent = payload["data"]["attributes"]["entity"]
    hq = ent.get("headquartersAddress") or {}
    legal = ent.get("legalAddress") or {}
    return {
        "lei": payload["data"]["attributes"]["lei"],
        "hq_country": hq.get("country"),
        "hq_city": hq.get("city"),
        "hq_region": hq.get("region"),
        # Carried for comparison only. The legal address already in Postgres
        # came from Wave 1 screening; if these two ever disagree that is worth
        # knowing, and it costs nothing to keep the evidence.
        "address_country": legal.get("country"),
        "address_city": legal.get("city"),
        "address_region": legal.get("region"),
    }


def main() -> int:
    anchors = json.loads(ANCHORS.read_text())["anchors"]
    leis = [a["lei"] for a in anchors]
    print(f"fetching GLEIF Level 1 for {len(leis)} anchors")

    rows: list[dict] = []
    absent: list[str] = []
    for i, lei in enumerate(leis, 1):
        payload = fetch_one(lei)
        if payload is None:
            absent.append(lei)
            print(f"  [{i:2d}/{len(leis)}] {lei}  ABSENT from GLEIF")
        else:
            rows.append(extract(payload))
        time.sleep(0.2)          # courtesy; GLEIF publishes no hard rate limit

    differing = sum(1 for r in rows
                    if (r["hq_country"], r["hq_city"], r["hq_region"])
                    != (r["address_country"], r["address_city"], r["address_region"]))
    with_hq = sum(1 for r in rows if r["hq_country"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "description": "GLEIF LEI-CDF Level 1 headquarters + legal address for "
                       "the 50 anchor obligors. The subsidiaries' equivalent is "
                       "subsidiaries_l1.json; the anchors were never fetched "
                       "with a headquarters field, which is the gap this closes.",
        "source": "https://api.gleif.org/api/v1/lei-records/{lei}",
        "licence": "GLEIF publishes LEI reference data under CC0",
        "retrieved_at": date.today().isoformat(),
        "requested": len(leis),
        "resolved": len(rows),
        "absent": absent,
        "records": rows,
    }, indent=2) + "\n")

    print(f"\n  resolved {len(rows)} of {len(leis)}"
          + (f", {len(absent)} absent" if absent else ""))
    print(f"  {with_hq} carry a headquarters address")
    print(f"  {differing} differ from their legal address")
    print(f"  -> {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
