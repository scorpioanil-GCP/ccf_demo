#!/usr/bin/env python3
"""Wave 9 — fetch the Security Agreement exhibits the credit agreements defer to.

`extract_collateral.py` found 20 facilities that grant a security interest and
then hand the asset list to a separate document: *"the Collateral described in
the Security Agreement"*. The grant is filed fact; the asset breakdown was not
readable, so those assets were generated and labelled `synthetic — engineered`.

**A first attempt looked in the wrong place.** The obvious guess — that the
pledge is a sibling exhibit in the same accession — is wrong for this cast.
These are 8-K *amendment* filings; the security agreement was filed with the
original facility, sometimes years earlier, and is incorporated by reference.
Inspecting the six accessions turned up exactly one EX-10 candidate, and the
content gate correctly rejected it: a warrant.

So discovery runs through **EDGAR full-text search** instead, matched on **date
proximity to the facility's effective date**. That matters for correctness, not
convenience: every obligor here has 14–100 security-agreement exhibits spanning
2009–2026, and a 2013 collateral schedule does not describe a 2026 facility.
Attaching the wrong one would produce data that *looks* public and is wrong —
strictly worse than the labelled engineering it would replace.

The window is tight on purpose. Five of the six obligors have an exhibit within
**six days** of their facility's effective date and two within **zero**, which is
the signature of the same transaction. Anything beyond `--window` days is left
unmatched rather than attached on a guess, and the matched distance is recorded
per document so the evidence travels with the claim.

Filename gets a document fetched; **content decides whether it is kept.**

Output: sources/screening/security_agreements.json  (+ files under sources/ex10/)

    uv run generators/fetch_security_agreements.py --dry-run
    uv run generators/fetch_security_agreements.py
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from hashlib import sha256

import requests

from ccf.config import REPO_ROOT, SEC_USER_AGENT, pg_connect, PG_SCHEMA_V2
from ccf.fetch import SourceManifest, fetch
from generators.extract_facilities import TextExtractor

SCREEN = REPO_ROOT / "sources" / "screening"
FTS = ("https://efts.sec.gov/LATEST/search-index"
       "?q=%22security+agreement%22&ciks={cik}")
DOC = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{name}"

#: Confirms the document IS a security agreement. Checked after fetching —
#: this is what separated a real pledge from an EX-10 warrant on the first pass.
CONFIRM = re.compile(
    r"(grants?\s+(?:to\s+[^.]{0,80}?)?a\s+(?:continuing\s+)?security\s+interest"
    r"|\bsecurity\s+agreement\b|\bpledge\s+agreement\b"
    r"|\bcollateral\s+agreement\b)", re.I)

#: The asset schedule — the reason for fetching at all. A security agreement
#: with no asset description recovers nothing.
SCHEDULE = re.compile(
    r"(\bequipment\b|\binventory\b|\baccounts?\s+receivable\b|"
    r"\breal\s+propert|\bpledged\s+(?:equity|shares|stock))", re.I)


def to_text(raw: bytes) -> str:
    parser = TextExtractor()
    try:
        parser.feed(raw.decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
        return ""
    return parser.text()


def fts_hits(cik: str) -> list[dict]:
    headers = {"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    try:
        resp = requests.get(FTS.format(cik=cik), headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json().get("hits", {}).get("hits", [])
    except Exception as exc:  # noqa: BLE001
        print(f"  [skip] FTS {cik}: {type(exc).__name__}")
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--window", type=int, default=14,
                    help="max days between exhibit filing and facility "
                         "effective date for the match to be defensible")
    args = ap.parse_args()

    extracted = json.loads((SCREEN / "collateral_extracted.json").read_text())
    targets = [
        f for f in extracted["facilities"]
        if f["is_secured"] and not any(
            v.get("pledged") for c, v in f["asset_categories"].items()
            if c != "deposit_accounts")
    ]

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{PG_SCHEMA_V2}".crosswalk')
        cik_by_lei = {r[0]: str(r[1]) for r in cur.fetchall()}
        cur.execute(f'SELECT facility_id, effective_date FROM "{PG_SCHEMA_V2}".facility')
        eff_by_fac = dict(cur.fetchall())

    print("Wave 9 — Security Agreement exhibits via EDGAR full-text search\n")
    print(f"  facilities with a grant but no readable schedule: {len(targets)}")
    print(f"  match window: ±{args.window} days from facility effective date\n")

    # Group by obligor: one FTS query per CIK, reused across its facilities.
    by_lei: dict[str, list[dict]] = {}
    for f in targets:
        by_lei.setdefault(f["borrower_lei"], []).append(f)

    # Documents already in the corpus. A full-text search for "security
    # agreement" matches the CREDIT agreement too, because that is the document
    # doing the deferring — so without this filter the fetch re-finds what we
    # already have and reports it as recovery. Observed: 4 of 5 first-pass hits.
    known_docs = {f["source_document"] for f in extracted["facilities"]}

    plan: list[dict] = []
    for lei, facs in sorted(by_lei.items()):
        cik = cik_by_lei.get(lei)
        if not cik:
            continue
        hits = fts_hits(cik.zfill(10))
        for f in facs:
            eff = eff_by_fac.get(f["facility_id"])
            if not eff:
                continue
            best = None
            for h in hits:
                src = h.get("_source", {})
                fd = src.get("file_date")
                if not fd or ":" not in h.get("_id", ""):
                    continue
                days = abs((datetime.date.fromisoformat(fd) - eff).days)
                if days > args.window:
                    continue
                _, cand_name = h["_id"].split(":", 1)
                if cand_name in known_docs:
                    continue          # the credit agreement, not the pledge
                if best is None or days < best["days"]:
                    accn, name = h["_id"].split(":", 1)
                    best = {"days": days, "accession": accn, "name": name,
                            "file_date": fd, "file_type": src.get("file_type", "")}
            if best:
                plan.append({**best, "cik": cik.lstrip("0"), "lei": lei,
                             "facility_id": f["facility_id"],
                             "effective_date": eff.isoformat()})

    matched_f = {p["facility_id"] for p in plan}
    print(f"  matched {len(matched_f)}/{len(targets)} facilities to a "
          f"contemporaneous exhibit")
    for p in sorted(plan, key=lambda x: x["days"])[:10]:
        print(f"    {p['facility_id']:<14} {p['file_type']:<12} "
              f"{p['file_date']}  Δ{p['days']}d")

    if args.dry_run:
        print("\n  DRY RUN — nothing fetched.")
        return 0

    manifest = SourceManifest(
        source="ex10",
        description=("EDGAR EX-10 credit agreements, amendments, and the "
                     "security/pledge agreement exhibits they defer to"),
        licence="US government work / public filing",
    ).load()

    docs: dict[str, dict] = {}
    rejected = 0
    for p in plan:
        bare = p["accession"].replace("-", "")
        url = DOC.format(cik=p["cik"], accn=bare, name=p["name"])
        key = f"{p['accession']}:{p['name']}"
        if key in docs:
            docs[key]["facility_ids"].append(p["facility_id"])
            continue
        try:
            path = fetch(url, manifest, f"{bare}_{p['name']}", is_sec=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  [skip] {p['name']}: {type(exc).__name__}")
            continue
        if not path.exists():
            rec = manifest.already_fetched(url)
            if not rec or not (REPO_ROOT / rec.path).exists():
                continue
            path = REPO_ROOT / rec.path
        text = to_text(path.read_bytes())
        if not (CONFIRM.search(text) and SCHEDULE.search(text)):
            rejected += 1
            print(f"  [reject] {p['name']} — no grant + schedule in content")
            continue
        docs[key] = {
            "document_id": key, "accession": p["accession"], "cik": p["cik"],
            "lei": p["lei"], "document": p["name"], "url": url,
            "file_type": p["file_type"], "file_date": p["file_date"],
            "match_days_from_effective": p["days"],
            "text_length": len(text),
            "text_sha256": sha256(text.encode()).hexdigest(),
            "text": text,
            "facility_ids": [p["facility_id"]],
            "provenance": "public",
            "source": "SEC EDGAR security/pledge agreement exhibit, matched by "
                      "CIK and filing-date proximity to the facility",
        }
        print(f"  [keep] {p['name']:<34} {len(text):>9,} chars  Δ{p['days']}d")

    out = SCREEN / "security_agreements.json"
    out.write_text(json.dumps({
        "wave": 9,
        "generated_for": "collateral-and-setoff-coverage",
        "match_rule": (f"same CIK, exhibit containing 'security agreement', "
                       f"filed within {args.window} days of the facility's "
                       f"effective date, confirmed by content"),
        "documents": list(docs.values()),
    }, indent=2) + "\n")

    covered = {fid for d in docs.values() for fid in d["facility_ids"]}
    print(f"\n  confirmed {len(docs)} security agreements ({rejected} rejected "
          f"on content)")
    print(f"  facilities newly covered: {len(covered)} / {len(targets)}")
    print(f"  written: {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
