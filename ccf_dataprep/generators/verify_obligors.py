#!/usr/bin/env python3
"""Wave 0 stage 2 — verify screening candidates against filing history.

Stage 1 (`screen_obligors.py`) discovers candidates from EDGAR full-text
search, which ranks by relevance and therefore *understates* condition
overlap: a company can satisfy a condition without surfacing in that query's
top pages.

This stage settles it. For each candidate it reads the SEC submissions API —
the authoritative filing index for that CIK — and checks conditions against
actual filing history rather than search ranking.

Verified here:

    V1  8-K Item 1.01 count      (material agreement / amendment)
    V2  8-K Item 2.03 count      (direct financial obligation)
    V3  8-K Item 2.04 count      (acceleration / breach)  <- scarcest
    V4  10-K and 10-Q counts     (XBRL depth for financial spreads)
    V5  fiscal year end          (non-December is wanted for ~2 obligors)
    V6  EX-10 exhibit count      (credit agreement material)

Output: sources/screening/verified.json, ranked for selection.

Run: uv run generators/verify_obligors.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter

from ccf.config import REPO_ROOT
from ccf.fetch import get_json

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
IN_PATH = REPO_ROOT / "sources" / "screening" / "candidates.json"
OUT_PATH = REPO_ROOT / "sources" / "screening" / "verified.json"

#: Cap the verification pass. Every entry costs one SEC request.
MAX_VERIFY = 150


def verify_one(cik: int) -> dict | None:
    try:
        sub = get_json(SUBMISSIONS.format(cik=cik), is_sec=True)
    except Exception as exc:  # noqa: BLE001
        print(f"    CIK {cik}: {type(exc).__name__}")
        return None

    # EDGAR `recent`-only: the index caps at ~1000 filings per issuer and
    # shards the remainder into `filings.files[]`, which this sweep does NOT
    # read. 40 of the 50 anchors have unread shards, so results here are a
    # FLOOR on the issuer's history, never the complete public record.
    # Estate-wide pattern across 7 fetchers; see docs/known-issues.md §9.11.
    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    items_col = recent.get("items", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])

    item_counts: Counter[str] = Counter()
    item_evidence: dict[str, list[str]] = {}
    form_counts: Counter[str] = Counter()

    for idx, form in enumerate(forms):
        form_counts[form] += 1
        if form.startswith("8-K") and idx < len(items_col):
            raw = items_col[idx] or ""
            for item in {piece.strip() for piece in raw.split(",") if piece.strip()}:
                item_counts[item] += 1
                if item in {"1.01", "2.03", "2.04"}:
                    bucket = item_evidence.setdefault(item, [])
                    if len(bucket) < 3:
                        date = dates[idx] if idx < len(dates) else ""
                        acc = accessions[idx] if idx < len(accessions) else ""
                        bucket.append(f"{date} {acc}")

    return {
        "cik": cik,
        "name": sub.get("name", ""),
        "tickers": sub.get("tickers", []),
        "exchanges": sub.get("exchanges", []),
        "sic": str(sub.get("sic") or ""),
        "sic_description": sub.get("sicDescription", ""),
        "fiscal_year_end": sub.get("fiscalYearEnd", ""),
        "state_of_incorporation": sub.get("stateOfIncorporation", ""),
        "entity_type": sub.get("entityType", ""),
        "ein": sub.get("ein", ""),
        "item_1_01": item_counts.get("1.01", 0),
        "item_2_03": item_counts.get("2.03", 0),
        "item_2_04": item_counts.get("2.04", 0),
        "item_4_02": item_counts.get("4.02", 0),  # non-reliance = restatement signal
        "count_10k": form_counts.get("10-K", 0),
        "count_10q": form_counts.get("10-Q", 0),
        "count_8k": form_counts.get("8-K", 0),
        "item_evidence": item_evidence,
        "filings_indexed": len(forms),
    }


def score(row: dict, screened: dict) -> tuple[int, list[str]]:
    """Score a verified candidate against the §F condition union."""
    met: list[str] = []
    if screened.get("conditions"):
        met.extend(screened["conditions"])
    if row["item_1_01"] >= 1:
        met.append("V1_has_amendment_filing")
    if row["item_2_03"] >= 1:
        met.append("V2_has_obligation_filing")
    if row["item_2_04"] >= 1:
        met.append("V3_has_acceleration")     # scarcest, weight it
    if row["count_10k"] >= 2 and row["count_10q"] >= 6:
        met.append("V4_xbrl_depth")
    if row["fiscal_year_end"] and not row["fiscal_year_end"].startswith("12"):
        met.append("V5_non_dec_fye")
    if row["item_4_02"] >= 1:
        met.append("V6_non_reliance_restatement")

    unique = sorted(set(met))
    weight = len(unique) + (4 if "V3_has_acceleration" in unique else 0) \
                        + (3 if "V6_non_reliance_restatement" in unique else 0)
    return weight, unique


def main() -> int:
    if not IN_PATH.exists():
        print(f"missing {IN_PATH} — run generators/screen_obligors.py first")
        return 1

    data = json.loads(IN_PATH.read_text())
    candidates = data["candidates"]
    # Prefer candidates already showing credit-agreement evidence.
    candidates.sort(
        key=lambda c: (
            "C1_financial_covenants" in c["conditions"]
            or "C2_guarantor_schedule" in c["conditions"],
            c["condition_count"],
        ),
        reverse=True,
    )
    subset = candidates[:MAX_VERIFY]
    print(f"Verifying {len(subset)} of {len(candidates)} candidates "
          f"against SEC submissions API\n")

    verified = []
    for i, cand in enumerate(subset, 1):
        row = verify_one(cand["cik"])
        if row is None:
            continue
        weight, met = score(row, cand)
        row["conditions_met"] = met
        row["condition_count"] = len(met)
        row["weight"] = weight
        row["screened_conditions"] = cand["conditions"]
        verified.append(row)
        if i % 25 == 0:
            print(f"  ...{i}/{len(subset)}")

    verified.sort(key=lambda r: (r["weight"], r["condition_count"]), reverse=True)

    OUT_PATH.write_text(
        json.dumps(
            {
                "generated_for": "Wave 0 obligor verification (stage 2)",
                "source": "SEC submissions API (data.sec.gov)",
                "verified_count": len(verified),
                "candidates": verified,
            },
            indent=2,
        )
        + "\n"
    )

    print(f"\n  written: {OUT_PATH.relative_to(REPO_ROOT)}\n")

    scarce_204 = [r for r in verified if r["item_2_04"] >= 1]
    scarce_402 = [r for r in verified if r["item_4_02"] >= 1]
    non_dec = [r for r in verified if r["fiscal_year_end"]
               and not r["fiscal_year_end"].startswith("12")]

    print("  SCARCE CONDITIONS — these drive selection:")
    print(f"    8-K Item 2.04 (acceleration)  : {len(scarce_204):>3} obligors  (need >= 2)")
    for r in scarce_204[:8]:
        ev = r["item_evidence"].get("2.04", [])
        print(f"        {r['name'][:38]:40s} x{r['item_2_04']}  {ev[0] if ev else ''}")
    print(f"    8-K Item 4.02 (non-reliance)  : {len(scarce_402):>3} obligors  (need ~3 restatements)")
    for r in scarce_402[:8]:
        print(f"        {r['name'][:38]:40s} x{r['item_4_02']}")
    print(f"    non-December fiscal year end  : {len(non_dec):>3} obligors  (need ~2)")
    for r in non_dec[:6]:
        print(f"        {r['name'][:38]:40s} FYE={r['fiscal_year_end']}")

    print("\n  Top 20 by weighted condition coverage:")
    print(f"    {'name':42s} {'tkr':6s} {'1.01':>4} {'2.03':>4} {'2.04':>4} {'4.02':>4} {'10-K':>4} {'wt':>3}")
    for r in verified[:20]:
        tkr = (r["tickers"] or [""])[0]
        print(f"    {r['name'][:40]:42s} {tkr:6s} {r['item_1_01']:>4} "
              f"{r['item_2_03']:>4} {r['item_2_04']:>4} {r['item_4_02']:>4} "
              f"{r['count_10k']:>4} {r['weight']:>3}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
