#!/usr/bin/env python3
"""Wave 16 — the three perspectives and the weight vectors that separate them.

§C assigns "Per-perspective ranking weights" and "ProjectionPlan per
perspective" to Postgres as `synthetic — internal`, dimension Pi / P. They are
OURS to produce; the SDK's Rank Operator consumes them.

## Why the weights are the mechanism

SB: "the same underlying signals produce three different rankings -- not three
sorts of one ranking." That difference lives entirely here. A maturity wall is
the DCM banker's top signal and near-noise to the M&A originator, so the two
weight vectors must genuinely diverge or no signal data will make the lists
differ.

## Two versions, and why they must differ

SF requires two weight-vector versions so a ranking can be replayed under the
prior one. Two identical versions would satisfy a count and demonstrate
nothing, so v1 and v2 differ on the cells that reorder the list -- v1 is the
"pre-2026 origination policy" that under-weighted activist stakes.

## Half-life lives once

SE gives lambda_c per signal CLASS, not per perspective. Storing it per
(perspective, signal_type) would write every value three times and let the
copies drift silently. It lives on `ib_signal_class` alone.

## A note on `gov_revenue_concentration`

In the loaded USASpending data this signal is extremely concentrated: one
obligor (Granite Construction) accounts for $1.47bn of the $1.53bn total
awards, i.e. 96%. That is effectively a single-entity signal, not a broadly
distributed one -- a future reader should not mistake the weight below for a
claim about a diversified population. The weight values themselves are not
adjusted for this; they come from the brief unchanged.

    uv run generators/generate_ib_perspectives.py --dry-run
    uv run generators/generate_ib_perspectives.py
"""
from __future__ import annotations

import argparse
import json
import sys

from ccf.fetch import SOURCES_ROOT

PERSPECTIVES = [
    {"perspective_id": "PSP-MA", "label": "M&A originator",
     "ranks_on": "strategic catalyst, sponsor activity, sector consolidation",
     "provenance": "synthetic — internal"},
    {"perspective_id": "PSP-DCM", "label": "DCM banker",
     "ranks_on": "maturity walls, refinancing windows, rate sensitivity",
     "provenance": "synthetic — internal"},
    {"perspective_id": "PSP-SECTOR", "label": "sector strategist",
     "ranks_on": "thematic movement across the sector",
     "provenance": "synthetic — internal"},
]

#: lambda_c per SE. Half-life in days: a signal contributes
#: `weight * 0.5 ** (age_days / half_life_days)`.
SIGNAL_CLASSES = [
    {"signal_type": "activist_stake_13d", "half_life_days": 30,
     "note": "SE: catalyst value decays as the market absorbs it"},
    {"signal_type": "ma_event_8k", "half_life_days": 14, "note": "SE"},
    {"signal_type": "merger_proxy", "half_life_days": 30, "note": "deal terms filed"},
    {"signal_type": "registration_s4", "half_life_days": 30, "note": "merger registration"},
    {"signal_type": "insider_activity_form4", "half_life_days": 14, "note": "insider transactions"},
    {"signal_type": "institutional_positioning_13f", "half_life_days": 90,
     "note": "quarterly filing cadence sets the floor"},
    {"signal_type": "maturity_wall", "half_life_days": 90, "note": "SE"},
    {"signal_type": "spread_trajectory", "half_life_days": 1, "note": "SE"},
    {"signal_type": "sector_news_gdelt", "half_life_days": 7, "note": "SE"},
    {"signal_type": "gov_revenue_concentration", "half_life_days": 180,
     "note": "contract awards move slowly"},
    {"signal_type": "banker_local_note", "half_life_days": 60,
     "note": "SD step 6: local knowledge the fabric must reach"},
]


def _w(perspective: str, weights: dict[str, float], version: str,
       rationale: str) -> list[dict]:
    return [{"perspective_id": perspective, "signal_type": st,
             "weight_version": version, "weight": w, "rationale": rationale,
             "provenance": "synthetic — internal"}
            for st, w in sorted(weights.items())]


_MA_V2 = {
    "activist_stake_13d": 1.00, "ma_event_8k": 0.90, "merger_proxy": 0.85,
    "registration_s4": 0.75, "insider_activity_form4": 0.50,
    "institutional_positioning_13f": 0.40, "sector_news_gdelt": 0.30,
    "gov_revenue_concentration": 0.20, "maturity_wall": 0.05,
    "spread_trajectory": 0.05, "banker_local_note": 0.60,
}
_DCM_V2 = {
    "maturity_wall": 1.00, "spread_trajectory": 0.90, "registration_s4": 0.40,
    "institutional_positioning_13f": 0.25, "ma_event_8k": 0.20,
    "merger_proxy": 0.15, "activist_stake_13d": 0.10,
    "insider_activity_form4": 0.10, "sector_news_gdelt": 0.15,
    "gov_revenue_concentration": 0.30, "banker_local_note": 0.60,
}
_SECTOR_V2 = {
    "sector_news_gdelt": 1.00, "institutional_positioning_13f": 0.70,
    "spread_trajectory": 0.45, "merger_proxy": 0.40, "ma_event_8k": 0.40,
    "activist_stake_13d": 0.35, "maturity_wall": 0.30,
    "registration_s4": 0.30, "insider_activity_form4": 0.25,
    "gov_revenue_concentration": 0.35, "banker_local_note": 0.30,
}

WEIGHTS_V2 = (
    _w("PSP-MA", _MA_V2, "v2", "2026 origination policy")
    + _w("PSP-DCM", _DCM_V2, "v2", "2026 origination policy")
    + _w("PSP-SECTOR", _SECTOR_V2, "v2", "2026 origination policy")
)

# v1 is the PRIOR policy. It under-weighted activist stakes and over-weighted
# insider activity -- the change that motivated v2, and the change that makes
# a replay visibly reorder rather than merely re-run.
_MA_V1 = {**_MA_V2, "activist_stake_13d": 0.45, "insider_activity_form4": 0.85,
          "merger_proxy": 0.55}
_DCM_V1 = {**_DCM_V2, "spread_trajectory": 0.50, "maturity_wall": 0.80,
           "gov_revenue_concentration": 0.10}
_SECTOR_V1 = {**_SECTOR_V2, "sector_news_gdelt": 0.60,
              "institutional_positioning_13f": 0.90}

WEIGHTS_V1 = (
    _w("PSP-MA", _MA_V1, "v1", "pre-2026 policy: activist stakes under-weighted")
    + _w("PSP-DCM", _DCM_V1, "v1", "pre-2026 policy")
    + _w("PSP-SECTOR", _SECTOR_V1, "v1", "pre-2026 policy")
)

PROJECTION_PLANS = [
    {"projection_plan_id": "PP-IB-MA-v1", "perspective_id": "PSP-MA",
     "plan_version": "v1", "permitted_signal_types": sorted(_MA_V2),
     "provenance": "synthetic — internal"},
    {"projection_plan_id": "PP-IB-DCM-v1", "perspective_id": "PSP-DCM",
     "plan_version": "v1", "permitted_signal_types": sorted(_DCM_V2),
     "provenance": "synthetic — internal"},
    {"projection_plan_id": "PP-IB-SECTOR-v1", "perspective_id": "PSP-SECTOR",
     "plan_version": "v1", "permitted_signal_types": sorted(_SECTOR_V2),
     "provenance": "synthetic — internal"},
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    weights = WEIGHTS_V1 + WEIGHTS_V2
    print("Wave 16 — perspectives and weight vectors\n")
    print(f"  perspectives      {len(PERSPECTIVES):>4}")
    print(f"  signal classes    {len(SIGNAL_CLASSES):>4}")
    print(f"  weight rows       {len(weights):>4}  "
          f"({len(PERSPECTIVES)} x {len(SIGNAL_CLASSES)} x 2 versions)")
    print(f"  projection plans  {len(PROJECTION_PLANS):>4}")

    # Cheap first check: the raw total. This alone is not sufficient -- see
    # below.
    expected = len(PERSPECTIVES) * len(SIGNAL_CLASSES) * 2
    if len(weights) != expected:
        print(f"\n  FAIL: expected {expected} weight rows, built {len(weights)}. "
              f"A missing cell scores that signal as zero and silently changes "
              f"every ranking it appears in.")
        return 1

    # The real check: the total can stay 66 while the data is wrong -- a
    # cell missing from one (perspective, version) pair can be masked by a
    # stray or typo'd cell in another pair, since the count only sums
    # across all of them. The actual invariant is per-pair coverage: each
    # (perspective, version) must carry EXACTLY the signal-class set, no
    # more, no less. A typo'd signal_type means that signal scores as ZERO
    # for that perspective (an absent weight is deliberately treated as
    # zero, not full strength), so a single typo silently drops one signal
    # from one perspective's ranking with nothing else failing.
    expected_types = {c["signal_type"] for c in SIGNAL_CLASSES}
    expected_pairs = {(p["perspective_id"], v)
                       for p in PERSPECTIVES for v in ("v1", "v2")}

    by_pair: dict[tuple[str, str], set[str]] = {}
    for w in weights:
        key = (w["perspective_id"], w["weight_version"])
        by_pair.setdefault(key, set()).add(w["signal_type"])

    ok = True

    actual_pairs = set(by_pair)
    if actual_pairs != expected_pairs:
        missing_pairs = sorted(expected_pairs - actual_pairs)
        extra_pairs = sorted(actual_pairs - expected_pairs)
        print(f"\n  FAIL: (perspective, version) pairs wrong. "
              f"missing pairs {missing_pairs}, extra pairs {extra_pairs}")
        ok = False

    for pair in sorted(actual_pairs):
        actual_types = by_pair[pair]
        if actual_types != expected_types:
            missing = sorted(expected_types - actual_types)
            extra = sorted(actual_types - expected_types)
            print(f"\n  FAIL: {pair[0]} {pair[1]} is missing {missing} "
                  f"and has extra {extra}")
            ok = False

    if not ok:
        return 1

    print("\n  v1 vs v2 differences (these are what a replay reorders on):")
    v1 = {(w["perspective_id"], w["signal_type"]): w["weight"] for w in WEIGHTS_V1}
    v2 = {(w["perspective_id"], w["signal_type"]): w["weight"] for w in WEIGHTS_V2}
    for key in sorted(v1):
        if v1[key] != v2[key]:
            print(f"    {key[0]:12s} {key[1]:30s} {v1[key]:.2f} -> {v2[key]:.2f}")

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    out = SOURCES_ROOT / "screening" / "wave16_perspectives.json"
    out.write_text(json.dumps({
        "perspectives": PERSPECTIVES,
        "signal_classes": SIGNAL_CLASSES,
        "weights": weights,
        "projection_plans": PROJECTION_PLANS,
    }, indent=1))
    print(f"\n  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
