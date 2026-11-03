#!/usr/bin/env python3
"""Wave 16 — federal contract concentration, joined on name and admitting it.

SC row: "Government-contract revenue concentration | USASpending.gov | public |
Postgres | E".

## The join is the problem

USASpending carries no LEI and no CIK. The only bridge to our anchors is a
company NAME, and its keywords filter searches award DESCRIPTION text, not
recipient identity -- it returned XPO -> Lockheed Martin and REGIS -> Humana
Government Business at $20.4bn. recipient_search_text narrows the search to
the recipient but still returns AMPHENOL -> MTS Systems.

CLAUDE.md rule 5 asks for joins that are imperfect ON PURPOSE, so that
resolution logic is testable. These are imperfect BY ACCIDENT, which is a
different thing: a concentration measure built on them would be wrong rather
than instructively fuzzy.

So the fetch runs against a HAND-VERIFIED allow-list
(sources/usaspending/recipient_allowlist.json), every row records its
match_band, and anything not on the list is dropped -- REJECTED BY OMISSION,
not logged as an error and not included at a low confidence score. --propose
regenerates the candidate sweep for a human to re-verify; it never writes the
allow-list itself, and this run never touches it either.

    uv run generators/fetch_usaspending.py --propose
    uv run generators/fetch_usaspending.py --dry-run
    uv run generators/fetch_usaspending.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

import requests

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import pg_connect
from ccf.fetch import SOURCES_ROOT

URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
ALLOWLIST = SOURCES_ROOT / "usaspending" / "recipient_allowlist.json"

MATCH_BANDS = ("exact", "verified-subsidiary", "rejected")

_SUFFIX = re.compile(
    r"[,.]?\s*(INC|CORP|CORPORATION|COMPANY|CO|LTD|LLC|L\.L\.C|PLC|HOLDINGS|"
    r"GROUP|TRUST|LP|L\.P)\.?$", re.I)


def _core(name: str) -> str:
    """Strip legal-form suffixes and punctuation for comparison only."""
    n = re.sub(r"\s*/[A-Z]{2}/\s*$", "", name).upper()
    while True:
        stripped = _SUFFIX.sub("", n).strip(" ,.")
        if stripped == n:
            return re.sub(r"[^A-Z0-9 ]", "", n).strip()
        n = stripped


def classify(recipient_name: str, anchor_name: str) -> str:
    """`exact` when the cores agree, else `rejected`.

    `verified-subsidiary` is never returned by this function -- it is a HUMAN
    judgement recorded in the allow-list, because deciding that
    "GRIFFON AEROSPACE, INC." is Griffon Corp's subsidiary requires checking
    an ownership record, not comparing two strings.
    """
    return "exact" if _core(recipient_name) == _core(anchor_name) else "rejected"


def anchors() -> list[tuple[str, str]]:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT e.lei, e.legal_name FROM "{S}".legal_entity e '
            f'JOIN "{S}".crosswalk c ON c.lei = e.lei '
            "WHERE c.cik IS NOT NULL AND e.lei NOT LIKE 'SYN-%' "
            "ORDER BY e.legal_name")
        return cur.fetchall()


def query(name: str) -> list[dict]:
    body = {
        "filters": {
            "recipient_search_text": [name],
            "award_type_codes": ["A", "B", "C", "D"],
            "time_period": [{"start_date": "2023-01-01", "end_date": "2026-08-24"}],
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
                   "Start Date"],
        "limit": 20, "page": 1, "sort": "Award Amount", "order": "desc",
    }
    resp = requests.post(URL, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json().get("results", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--propose", action="store_true",
                     help="print candidates for human verification; writes nothing")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.propose:
        anchor_list = anchors()
        print("# USASpending candidates — VERIFY EACH BY HAND\n")
        print("# auto_band is a string comparison only. verified-subsidiary")
        print("# is yours to decide against an ownership record.\n")
        for n, (lei, name) in enumerate(anchor_list, 1):
            # Progress with flush=True: this sweep is minutes long.
            print(f"# [{n}/{len(anchor_list)}] {name}", flush=True)
            core = _core(name)
            try:
                results = query(core)
            except Exception as exc:  # noqa: BLE001
                print(f"  ERR  {name}: {exc}")
                continue
            for r in results[:3]:
                rn = r.get("Recipient Name") or ""
                print(f"  {lei}  anchor={name[:34]:34s} recipient={rn[:38]:38s} "
                      f"amount={r.get('Award Amount')}  auto_band={classify(rn, name)}")
            time.sleep(0.35)
        return 0

    if not ALLOWLIST.exists():
        print(f"No allow-list at {ALLOWLIST}.\n"
              f"Run with --propose, verify the candidates by hand, and write it.\n"
              f"This fetcher will not guess a join it cannot check.")
        return 1

    allow = json.loads(ALLOWLIST.read_text())["entries"]
    for e in allow:
        assert e["match_band"] in MATCH_BANDS, \
            f"allow-list entry has an unknown match_band: {e}"
    keep = {(e["lei"], e["recipient_name"].upper()): e for e in allow
            if e["match_band"] != "rejected"}
    print(f"Wave 16 — USASpending\n\n  allow-list entries kept {len(keep)}")

    by_lei: dict[str, list[str]] = {}
    for lei, _rn in keep:
        by_lei.setdefault(lei, [])

    rows: list[dict] = []
    seen = 0
    errored_leis: list[str] = []
    name_of = dict(anchors())
    lei_list = sorted(by_lei)
    for i, lei in enumerate(lei_list, 1):
        # Progress with flush=True. A fetcher that prints only on completion
        # is indistinguishable from a hang -- which invites an operator to
        # kill it and lose rate-limited work.
        print(f"  [{i}/{len(lei_list)}] {lei} {name_of.get(lei, '')[:40]}",
              flush=True)
        try:
            results = query(_core(name_of.get(lei, "")))
        except Exception as exc:  # noqa: BLE001
            # A failed call and a genuine zero-contracts anchor must not
            # collapse into the same "zero rows" shape -- one is "could not
            # look", the other is "looked, found nothing". Recorded
            # separately so the artifact can tell them apart.
            print(f"    ERR  {lei}: {exc}", flush=True)
            errored_leis.append(lei)
            time.sleep(0.35)
            continue
        for r in results:
            seen += 1
            rn = (r.get("Recipient Name") or "").upper()
            entry = keep.get((lei, rn))
            if not entry:
                continue  # not on the list == rejected by omission
            rows.append({
                "lei": lei,
                "recipient_name": rn,
                "match_band": entry["match_band"],
                "verified_against": entry.get("verified_against", ""),
                "award_id": r.get("Award ID"),
                "awarding_agency": r.get("Awarding Agency"),
                "start_date": r.get("Start Date"),
                "obligated_usd": r.get("Award Amount"),
                "provenance": "public",
            })
        time.sleep(0.35)

    rejected = seen - len(rows)
    print(f"  awards seen              {seen}")
    print(f"  awards kept              {len(rows)}")
    print(f"  rejected by omission     {rejected}")
    print(f"  anchors errored          {len(errored_leis)}")
    print(f"  entities with any award  {len({r['lei'] for r in rows})}")
    print(f"  total obligated (kept)   ${sum(r['obligated_usd'] or 0 for r in rows):,.2f}")

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    out = SOURCES_ROOT / "screening" / "wave16_usaspending.json"
    out.write_text(json.dumps({
        "source": "USASpending.gov API v2 spending_by_award, recipient_search_text",
        "join": "company NAME against a hand-verified allow-list; no LEI or CIK exists",
        "retrieved_at": datetime.now(timezone.utc).date().isoformat(),
        "awards_seen": seen,
        "awards_kept": len(rows),
        "rejected_by_omission": rejected,
        "anchors_errored": len(errored_leis),
        "anchors_errored_leis": errored_leis,
        "awards": rows,
    }, indent=1))
    print(f"\n  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
