#!/usr/bin/env python3
"""The bank-internal overlay for the ABS deals.

    uv run generators/generate_abs_overlay.py

Everything here is invented, because it is bank-internal by nature: what the
bank holds, how it materializes, and who may see loan-level detail. All rows
carry `synthetic — internal`.

## The restricted principal has to actually bind

Section F asks for a principal restricted to aggregate-only granularity. A
policy row that grants a ceiling nobody ever reaches is a label, not a
constraint -- Wave 13b's exact defect (`known-issues.md` and
`checks-that-pass-without-looking`). So the restricted principal
(`client-reporting`, ceiling `deal`) is one a realistic request WOULD
otherwise take to loan level, and `loaders/load_abs_overlay_wave14.py`'s
`effective_granularity` proves the ceiling actually lowers a `loan`-request
rather than merely existing as a row. Task 13's gate re-proves it end to end.
"""
from __future__ import annotations

import json
import sys
from datetime import date

from ccf.config import REPO_ROOT

OUT = REPO_ROOT / "sources" / "absee" / "overlay.json"

HOLDINGS = [
    # (deal_id, class, position type, notional, retention)
    ("SDART-2022-6", "A-3", "investment", "25000000", False),
    ("SDART-2022-6", "B",   "investment", "10000000", False),
    ("TAOT-2022-B",  "A-4", "investment", "40000000", False),
    ("TAOT-2022-B",  "B",   "risk-retention", "12500000", True),
    ("SDART-2024-1", "A-3", "investment", "30000000", False),
    ("SDART-2024-1", "C",   "risk-retention", "8000000", True),
]

MATERIALIZATION = [
    ("deal",    "materialized", 30, "read pre-aggregated deal state; one query"),
    ("tranche", "materialized", 30, "read pre-aggregated tranche state; one query"),
    ("cohort",  "materialized", 30, "cohort aggregates, batched per requested cohort"),
    ("loan",    "on-demand",     0, "stream loan rows; never materialize the pool"),
]

ENTITLEMENTS = [
    # (principal, max granularity, why)
    ("structured-finance-desk", "loan",
     "arranges and holds these deals; needs loan-level detail"),
    ("credit-risk", "cohort",
     "monitors trigger proximity; cohort detail is sufficient"),
    # The restricted principal. §F requires one, and it must BITE.
    ("client-reporting", "deal",
     "external-facing; loan-level borrower attributes are not disclosable"),
]

#: Fields a below-loan principal must never receive, even in aggregate form
#: with a small denominator. These are the quasi-identifiers in ABS-EE.
PRIVACY_RESTRICTED_FIELDS = [
    "obligor_credit_score", "obligor_geographic_location",
    "payment_to_income_percentage", "obligor_income_verification_level_code",
]


def main() -> int:
    payload = {
        "generated_at": date.today().isoformat(),
        "provenance": "synthetic — internal",
        "holdings": [
            {"deal_id": d, "class_name": c, "position_type": p,
             "notional": n, "is_risk_retention": r,
             "tranche_id": f"{d}-{c}"}
            for d, c, p, n, r in HOLDINGS],
        "materialization": [
            {"granularity": g, "posture": p, "refresh_days": r, "note": n}
            for g, p, r, n in MATERIALIZATION],
        "entitlements": [
            {"principal": p, "max_granularity": g, "rationale": r}
            for p, g, r in ENTITLEMENTS],
        "privacy_restricted_fields": PRIVACY_RESTRICTED_FIELDS,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"  {len(HOLDINGS)} holdings, {len(ENTITLEMENTS)} entitlements "
          f"(restricted: client-reporting -> deal)")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
