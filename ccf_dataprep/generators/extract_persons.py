#!/usr/bin/env python3
"""Build the Wave 10 person roster from fetched Form 4 XML.

Escalation policy, per the design's global constraints: start at 40 filings and
double to a HARD CAP of 160 until an issuer yields >= 8 natural persons. An
issuer still short at 160 is RECORDED AS A SHORTFALL, never padded — hitting a
floor by invention is the "counted but not created" failure CLAUDE.md rejects.

    uv run generators/extract_persons.py --dry-run
    uv run generators/extract_persons.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

from ccf.config import REPO_ROOT
from generators.form4 import owner_kind, parse_form4
from generators.persons import parse_filed_name, person_key, render_display

FORM4_ROOT = REPO_ROOT / "sources" / "form4"
SCREEN = REPO_ROOT / "sources" / "screening"
NATURAL_PERSON_FLOOR = 8
LOOKBACK_START = 40
LOOKBACK_CAP = 160


def next_lookback(current: int | None, natural_persons: int) -> int | None:
    """The lookback to try next, or None when escalation should stop."""
    if current is None:
        return LOOKBACK_START
    if natural_persons >= NATURAL_PERSON_FLOOR:
        return None
    doubled = current * 2
    return doubled if doubled <= LOOKBACK_CAP else None


def roster_for_issuer(lei: str, xml_paths: list) -> tuple[dict, int]:
    """Fold a set of Form 4 XML files into `{person_key: person}` for one issuer."""
    people: dict[str, dict] = {}
    seen: dict[tuple[str, str], list[str]] = defaultdict(list)

    for path, filing_date in xml_paths:
        try:
            owners = parse_form4(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            print(f"    [skip] {path.name}: {exc}")
            continue
        for owner in owners:
            key = person_key(owner.cik, owner.name)
            parsed = parse_filed_name(owner.name)
            person = people.setdefault(key, {
                "person_key": key,
                "person_key_source": "sec_cik",
                "cik": owner.cik,
                "name_as_filed": owner.name,
                "display_name": render_display(parsed),
                "owner_kind": owner_kind(owner.name),
                **{k: parsed[k] for k in ("last", "first", "middle", "suffix")},
                "roles": [],
            })
            for role, active in (("director", owner.is_director),
                                 ("officer", owner.is_officer),
                                 ("ten_percent_owner", owner.is_ten_percent_owner)):
                if not active:
                    continue
                seen[(key, role)].append(filing_date)
                existing = next((r for r in person["roles"]
                                 if r["lei"] == lei and r["role"] == role), None)
                if existing is None:
                    person["roles"].append({
                        "lei": lei, "role": role,
                        "officer_title": owner.officer_title,
                        "first_seen": filing_date, "last_seen": filing_date,
                    })
                else:
                    existing["first_seen"] = min(existing["first_seen"], filing_date)
                    existing["last_seen"] = max(existing["last_seen"], filing_date)
                    if owner.officer_title and not existing["officer_title"]:
                        existing["officer_title"] = owner.officer_title

    natural = sum(1 for p in people.values() if p["owner_kind"] == "natural")
    return people, natural


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    index = json.loads((SCREEN / "wave10_form4_index.json").read_text())
    all_people: dict[str, dict] = {}
    lookback_used: dict[str, int] = {}
    shortfalls: list[dict] = []

    for lei, entry in index["issuers"].items():
        paths = [(FORM4_ROOT / f["path"], f["filing_date"]) for f in entry["filings"]]
        lookback = None
        while True:
            step = next_lookback(lookback, 0 if lookback is None else natural)
            if step is None:
                break
            lookback = step
            people, natural = roster_for_issuer(lei, paths[:lookback])
            if natural >= NATURAL_PERSON_FLOOR or lookback >= LOOKBACK_CAP:
                break

        lookback_used[lei] = lookback
        if natural < NATURAL_PERSON_FLOOR:
            shortfalls.append({"lei": lei, "natural_persons": natural})
            print(f"  [short] {lei}: {natural} natural persons at lookback {lookback}")

        for key, person in people.items():
            merged = all_people.setdefault(key, person)
            if merged is not person:
                merged["roles"].extend(person["roles"])

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lookback_used": lookback_used,
        "shortfalls": shortfalls,
        "persons": sorted(all_people.values(), key=lambda p: p["person_key"]),
    }
    natural_total = sum(1 for p in payload["persons"] if p["owner_kind"] == "natural")
    print(f"\n  {len(payload['persons'])} reporting owners "
          f"({natural_total} natural, "
          f"{len(payload['persons']) - natural_total} entity) "
          f"across {len(lookback_used)} issuers · {len(shortfalls)} shortfalls")

    if args.dry_run:
        print("  [dry-run] nothing written")
        return 0
    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave10_persons.json").write_text(json.dumps(payload, indent=2))
    print(f"  wrote {SCREEN / 'wave10_persons.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
