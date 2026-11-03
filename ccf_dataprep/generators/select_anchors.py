#!/usr/bin/env python3
"""Wave 0 final — select the ~50 anchor obligor cast.

Not top-N by score. The §F conditions are a *covering* problem: a handful of
them are scarce, and taking the highest-scoring 50 can silently drop the only
obligors carrying a condition the flagship depends on.

So selection runs in three passes:

  1. RESERVE  — seat every obligor carrying a scarce condition, quota-capped
  2. CORE     — fill with obligors carrying full credit-agreement evidence
  3. SPREAD   — top up for SIC diversity so peer sets are constructible

Quotas come straight from the §F envelopes, with headroom over the floor so a
later data-quality drop does not breach the requirement.

Output: sources/screening/anchors.json — the proposed cast, with a coverage
report proving each condition is met.

Run: uv run generators/select_anchors.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

from ccf.config import REPO_ROOT

IN_PATH = REPO_ROOT / "sources" / "screening" / "verified.json"
OUT_PATH = REPO_ROOT / "sources" / "screening" / "anchors.json"

TARGET = 50

#: (condition key, predicate, floor from §F, headroom target)
SCARCE = [
    ("acceleration", lambda r: r["item_2_04"] >= 1, 2, 6),
    ("restatement", lambda r: r["item_4_02"] >= 1, 3, 6),
    ("non_dec_fye", lambda r: bool(r["fiscal_year_end"])
     and not r["fiscal_year_end"].startswith("12"), 2, 8),
]


def has_credit_agreement(row: dict) -> bool:
    """Screening found covenant/guarantor language in an EX-10 for this CIK."""
    screened = set(row.get("screened_conditions", []))
    return bool(
        screened & {"C1_financial_covenants", "C2_guarantor_schedule", "C3_defined_terms"}
    )


def main() -> int:
    if not IN_PATH.exists():
        print(f"missing {IN_PATH} — run generators/verify_obligors.py first")
        return 1

    rows = json.loads(IN_PATH.read_text())["candidates"]
    by_cik = {r["cik"]: r for r in rows}
    selected: dict[int, str] = {}   # cik -> reason seated

    # --- Pass 1: reserve seats for scarce conditions -----------------------
    print("PASS 1 — reserving seats for scarce conditions\n")
    for key, pred, floor, target in SCARCE:
        pool = [r for r in rows if pred(r)]
        # Prefer ones that also carry credit-agreement evidence and depth.
        pool.sort(
            key=lambda r: (has_credit_agreement(r), r["count_10k"], r["weight"]),
            reverse=True,
        )
        seated = 0
        for row in pool:
            if seated >= target:
                break
            if row["cik"] not in selected:
                selected[row["cik"]] = f"scarce:{key}"
                seated += 1
        status = "OK" if len(pool) >= floor else "SHORT"
        print(f"  {key:14s} available={len(pool):>3}  floor={floor}  "
              f"seated={seated:>2}  [{status}]")

    # --- Pass 2: core credit-agreement obligors ----------------------------
    print(f"\nPASS 2 — filling with credit-agreement obligors "
          f"({len(selected)}/{TARGET} seated)\n")
    core = [
        r for r in rows
        if r["cik"] not in selected
        and has_credit_agreement(r)
        and r["count_10k"] >= 2
    ]
    core.sort(key=lambda r: (r["item_1_01"], r["count_10k"], r["weight"]), reverse=True)
    for row in core:
        if len(selected) >= TARGET:
            break
        selected[row["cik"]] = "core:credit_agreement"
    print(f"  seated {sum(1 for v in selected.values() if v.startswith('core'))} "
          f"core obligors")

    # --- Pass 3: SIC spread ------------------------------------------------
    print(f"\nPASS 3 — SIC spread ({len(selected)}/{TARGET} seated)\n")
    sic_counts = Counter(by_cik[c]["sic"] for c in selected)
    remaining = [r for r in rows if r["cik"] not in selected and r["count_10k"] >= 1]
    remaining.sort(key=lambda r: (sic_counts[r["sic"]], -r["weight"]))
    for row in remaining:
        if len(selected) >= TARGET:
            break
        selected[row["cik"]] = "spread:sic"
        sic_counts[row["sic"]] += 1

    cast = [dict(by_cik[c], seated_for=reason) for c, reason in selected.items()]
    cast.sort(key=lambda r: (r["seated_for"], -r["weight"]))

    # --- Coverage proof ----------------------------------------------------
    print(f"\n{'=' * 66}\nCOVERAGE PROOF — {len(cast)} anchors selected\n{'=' * 66}")
    ok = True
    for key, pred, floor, _ in SCARCE:
        n = sum(1 for r in cast if pred(r))
        mark = "PASS" if n >= floor else "FAIL"
        if n < floor:
            ok = False
        print(f"  [{mark}] {key:14s} {n:>3} in cast  (§F floor {floor})")

    n_ca = sum(1 for r in cast if has_credit_agreement(r))
    print(f"  [{'PASS' if n_ca >= 15 else 'WARN'}] credit_agreement "
          f"{n_ca:>3} in cast  (need ~15 for covenant-cross-reference)")

    sics = Counter(r["sic_description"][:34] or "(none)" for r in cast)
    print(f"\n  SIC spread: {len(sics)} distinct industries")
    for sic, n in sics.most_common(8):
        print(f"    {n:>2}  {sic}")

    OUT_PATH.write_text(
        json.dumps(
            {
                "generated_for": "Wave 0 — proposed anchor obligor cast",
                "target_size": TARGET,
                "selected": len(cast),
                "selection_method": "condition-first: reserve scarce, fill core, spread SIC",
                "coverage": {
                    key: sum(1 for r in cast if pred(r)) for key, pred, _, _ in SCARCE
                },
                "anchors": cast,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  written: {OUT_PATH.relative_to(REPO_ROOT)}")

    print(f"\n  Cast (name / ticker / 1.01 / 2.04 / 4.02 / FYE / seated for):")
    for r in cast:
        tkr = (r["tickers"] or [""])[0]
        print(f"    {r['name'][:34]:36s} {tkr:6s} {r['item_1_01']:>3} "
              f"{r['item_2_04']:>3} {r['item_4_02']:>3}  {r['fiscal_year_end']:>4}  "
              f"{r['seated_for']}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
