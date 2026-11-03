#!/usr/bin/env python3
"""Wave 13a stage 2b — collateral for the facilities Wave 13a added, and only those.

    uv run generators/extend_collateral_wave13a.py --dry-run
    uv run generators/extend_collateral_wave13a.py

`credit-memo-context` §F wants ~20 obligors covered across all five
prerequisite products. Stage 2a took exposure from 15 obligors to 22; collateral
is the remaining leg, with 8 memo-grade obligors holding a facility and no
pledge. This closes that leg.

**Why this is a separate module rather than a re-run of the Wave 9 chain.**
`generators/generate_collateral.py` mints asset ids positionally --
`COL-{len(assets)+1:05d}` -- over facilities that `generators/extract_collateral.py`
reads from Postgres `ORDER BY facility_id`. Wave 13a's twelve new facilities
sort *into* that ordering rather than after it: the first lands at index 2 of
57. Re-running the chain would therefore renumber essentially every existing
asset, and because `loaders/load_collateral_wave9.py` upserts
`ON CONFLICT (asset_id)`, each of the 81 existing rows would be **overwritten in
place with a different asset**, while the pledges referencing the old numbering
would silently come to point at the wrong collateral. Nothing would error.

That is the same family as known-issues.md §12.8 -- a loader whose re-run
quietly destroys another wave's rows -- and it is recorded there rather than
triggered here. This module is additive: it mints ids strictly above the
current maximum, writes only the new facilities' assets and pledges, and never
reads or rewrites an existing row.

Provenance follows Wave 9's own rule exactly, and is imported from it rather
than restated: a filed grant clause makes the security interest `public`, while
the asset breakdown behind it is `synthetic — engineered` whenever the credit
agreement defers the schedule to a Security Agreement exhibit that was never
fetched. Valuations are `synthetic — internal` — a bank's own marks.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import date, timedelta

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, mongo_db, pg_connect
from ccf.memo_grade import memo_grade_leis
from generators.extract_collateral import (ASSET_CATEGORIES, GRANT_ANCHOR,
                                           GRANT_WINDOW, all_offsets,
                                           first_match)
from generators.generate_collateral import HAIRCUTS, asset_value

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13a_collateral_extension.json"

#: Distinct from Wave 9's SEED so the two engineered layers cannot be confused
#: for one another in a reproduction check.
SEED = 20260822
TODAY = date.today()


def unpledged_memo_facilities(cur) -> list[dict]:
    """Memo-grade facilities with no collateral_pledge row of their own."""
    cur.execute(f"""
        SELECT f.facility_id, f.borrower_lei, f.facility_type,
               f.commitment_amount, f.source_document, f.source_accession
        FROM "{S}".facility f
        WHERE f.borrower_lei = ANY(%s)
          AND NOT EXISTS (SELECT 1 FROM "{S}".collateral_pledge p
                          WHERE p.facility_id = f.facility_id)
        ORDER BY f.facility_id
    """, (sorted(memo_grade_leis()),))
    return [{"facility_id": r[0], "borrower_lei": r[1], "facility_type": r[2],
             "commitment_amount": float(r[3]) if r[3] else None,
             "source_document": r[4], "source_accession": r[5]}
            for r in cur.fetchall()]


def grant_evidence(db, accession: str) -> tuple[bool, list[str]]:
    """Does this agreement actually grant a security interest, and over what?

    Reuses Wave 9's own anchor pattern and category vocabulary, imported rather
    than copied, so 'secured' means here exactly what it means there.
    """
    doc = db["document"].find_one({"accession": accession}, {"text": 1})
    if not doc or not doc.get("text"):
        return False, []
    text = doc["text"]
    anchor = first_match(text, GRANT_ANCHOR)
    if not anchor:
        return False, []
    start = max(0, anchor[0] - GRANT_WINDOW)
    window = text[start:anchor[0] + GRANT_WINDOW]
    cats = [name for name, pat in ASSET_CATEGORIES
            if name != "deposit_accounts" and re.search(pat, window, re.I)]
    return True, cats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rng = random.Random(SEED)
    db = mongo_db()

    with pg_connect() as conn, conn.cursor() as cur:
        facilities = unpledged_memo_facilities(cur)
        cur.execute(f'SELECT COALESCE(max(asset_id), %s) FROM "{S}".collateral_asset',
                    ("COL-00000",))
        start_n = int(cur.fetchone()[0].split("-")[1])

    print("Wave 13a — collateral for the newly-covered memo-grade facilities\n")
    print(f"  {len(facilities)} memo-grade facilities with no pledge")
    print(f"  asset ids continue from COL-{start_n:05d} — nothing existing is "
          f"renumbered\n")

    assets: list[dict] = []
    pledges: list[dict] = []
    unsecured = 0
    for f in facilities:
        secured, cats = grant_evidence(db, f["source_accession"])
        if not secured:
            unsecured += 1
            continue
        commitment = f["commitment_amount"] or 250_000_000.0
        for category in (cats or ["real_property"])[:2]:
            aid = f"COL-{start_n + len(assets) + 1:05d}"
            age = rng.choice([0, 2, 30, 90, 210, 400, 545])
            assets.append({
                "asset_id": aid, "category": category,
                "description": category.replace("_", " ").title(),
                "pledgor_lei": f["borrower_lei"],
                # The grant is filed; the breakdown behind it is not.
                "provenance_existence": "synthetic — engineered",
                "engineered_reason": (
                    "facility grants a security interest, but its collateral "
                    "schedule is in a Security Agreement exhibit not fetched"),
                "source_document": f["source_document"],
                "valuation": asset_value(rng, category, commitment),
                "valuation_date": (TODAY - timedelta(days=age)).isoformat(),
                "valuation_age_days": age,
                "haircut": HAIRCUTS[category],
                "provenance_valuation": "synthetic — internal",
            })
            pledges.append({
                "facility_id": f["facility_id"], "asset_id": aid,
                "priority": "first",
                "provenance": "synthetic — engineered",
                "basis": "grant is filed; asset breakdown engineered",
            })

    print(f"  facilities with a filed grant clause   {len(facilities) - unsecured:>4}")
    print(f"  facilities with NO grant clause        {unsecured:>4}   "
          f"(genuinely unsecured — no pledge invented)")
    print(f"  assets to add                          {len(assets):>4}")
    print(f"  pledges to add                         {len(pledges):>4}")

    if args.dry_run:
        print("\n  DRY RUN — artifact not written.")
        return 0

    ARTIFACT.write_text(json.dumps({
        "generated_for": "credit-memo-context §F condition 1",
        "seed": SEED,
        "asset_ids_start_after": f"COL-{start_n:05d}",
        "note": ("additive only -- Wave 9's positional asset numbering means a "
                 "re-run of its chain would renumber and overwrite existing "
                 "assets in place; see this module's docstring and "
                 "known-issues.md"),
        "assets": assets, "pledges": pledges,
    }, indent=2) + "\n")
    print(f"\n  wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
