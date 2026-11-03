#!/usr/bin/env python3
"""Wave 1 — backfill rejected anchors and finalize the cast.

Five of the fifty proposed anchors could not be resolved to a real GLEIF LEI
at 'strong' or better. Three appear to genuinely lack an LEI (smaller filers
are not required to hold one); one matched an operating subsidiary rather
than the parent, which is a different legal entity and would silently
mis-anchor every downstream join.

Rather than force those matches, this backfills from the verified pool and
re-checks that scarce-condition coverage survives the swap.

Output: sources/screening/anchors_final.json — the cast Wave 1 actually loads.

Run: uv run generators/finalize_anchors.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter

from ccf.config import REPO_ROOT
from generators.resolve_leis import best_match

SCREEN = REPO_ROOT / "sources" / "screening"
TARGET = 50

SCARCE = [
    ("acceleration", lambda r: r.get("item_2_04", 0) >= 1, 2),
    ("restatement", lambda r: r.get("item_4_02", 0) >= 1, 3),
    ("non_dec_fye", lambda r: bool(r.get("fiscal_year_end"))
     and not r["fiscal_year_end"].startswith("12"), 2),
]


def main() -> int:
    matches = json.loads((SCREEN / "lei_matches.json").read_text())["matches"]
    verified = json.loads((SCREEN / "verified.json").read_text())["candidates"]
    by_cik = {r["cik"]: r for r in verified}

    accepted = [m for m in matches if m.get("accepted")]
    rejected = [m for m in matches if not m.get("accepted")]
    seated_ciks = {m["cik"] for m in matches}

    print(f"accepted {len(accepted)}  rejected {len(rejected)}  "
          f"backfilling to {TARGET}\n")

    for r in rejected:
        print(f"  dropped: {r['sec_name'][:38]:40s} "
              f"[{r['match_band']}] {r.get('rejection_reason', '')}")

    # Candidate pool: verified, not already seated, with filing depth.
    pool = [
        r for r in verified
        if r["cik"] not in seated_ciks and r["count_10k"] >= 2
    ]
    pool.sort(key=lambda r: (r["weight"], r["item_1_01"]), reverse=True)

    print(f"\n  resolving backfill candidates from pool of {len(pool)}...")
    backfilled = []
    for cand in pool:
        if len(accepted) + len(backfilled) >= TARGET:
            break
        match = best_match(cand["name"])
        if not match or match["match_band"] not in ("exact", "strong"):
            continue
        row = {
            "cik": cand["cik"],
            "sec_name": cand["name"],
            "tickers": cand["tickers"],
            "sic": cand["sic"],
            "seated_for": "backfill",
            "accepted": True,
            **match,
        }
        backfilled.append(row)
        print(f"    + {cand['name'][:36]:38s} {match['lei']}  "
              f"[{match['match_band']}]")

    final = accepted + backfilled

    # Re-attach the verification row so coverage can be re-proved.
    for row in final:
        src = by_cik.get(row["cik"], {})
        row["item_1_01"] = src.get("item_1_01", 0)
        row["item_2_03"] = src.get("item_2_03", 0)
        row["item_2_04"] = src.get("item_2_04", 0)
        row["item_4_02"] = src.get("item_4_02", 0)
        row["fiscal_year_end"] = src.get("fiscal_year_end", "")
        row["count_10k"] = src.get("count_10k", 0)
        row["sic_description"] = src.get("sic_description", "")

    print(f"\n{'=' * 64}\nFINAL CAST — {len(final)} anchors, all with real LEIs\n{'=' * 64}")
    ok = True
    for key, pred, floor in SCARCE:
        n = sum(1 for r in final if pred(r))
        mark = "PASS" if n >= floor else "FAIL"
        if n < floor:
            ok = False
        print(f"  [{mark}] {key:14s} {n:>3}  (§F floor {floor})")

    reg = Counter(r.get("registration_status", "?") for r in final)
    lapsed = reg.get("LAPSED", 0)
    mark = "PASS" if lapsed >= 5 else "FAIL"
    if lapsed < 5:
        ok = False
    print(f"  [{mark}] {'lapsed_lei':14s} {lapsed:>3}  (§F floor 5)")

    juris = Counter(r.get("legal_jurisdiction", "?") for r in final)
    print(f"\n  jurisdictions: {dict(juris.most_common(6))}")
    print(f"  registration:  {dict(reg)}")
    sics = Counter((r.get("sic_description") or "?")[:30] for r in final)
    print(f"  SIC spread:    {len(sics)} distinct industries")

    (SCREEN / "anchors_final.json").write_text(
        json.dumps(
            {
                "generated_for": "Wave 1 — final anchor cast with real GLEIF LEIs",
                "count": len(final),
                "all_leis_real": True,
                "match_threshold": "strong (>=0.85) or exact (>=0.95)",
                "dropped": [
                    {"sec_name": r["sec_name"], "reason": r.get("rejection_reason", "")}
                    for r in rejected
                ],
                "coverage": {
                    key: sum(1 for r in final if pred(r)) for key, pred, _ in SCARCE
                } | {"lapsed_lei": lapsed},
                "anchors": final,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  written: sources/screening/anchors_final.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
