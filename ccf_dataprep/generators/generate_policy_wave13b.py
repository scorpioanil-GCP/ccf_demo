#!/usr/bin/env python3
"""Wave 13b Task 6 — beneficial-ownership policy, residency, refresh state.

Three §C rows:

    Beneficial-ownership thresholds by jurisdiction  synthetic — internal  Postgres  P
    Data-residency constraints on person data        synthetic — internal  Fluree    P
    Refresh-cycle state per client                   synthetic — internal  Postgres  T

## Thresholds are bound to INTENT, not just jurisdiction

§B: *"beneficial-ownership threshold bound to `intent`."* The same jurisdiction
answers "who is a beneficial owner?" differently depending on why you are
asking. Onboarding a corporate client uses the statutory 25%; screening the
same ownership graph for sanctions exposure uses **any** stake, because a
sanctioned party at 3% still taints the payment. A single threshold per
jurisdiction would make the `intent` parameter decorative — it would change the
question asked and not the answer returned.

So the key is `(jurisdiction, intent)`, and the intents genuinely disagree.

## Residency is a legal claim, so the data has to support a real diff

§F7: *"≥ 2 entities with EU-resident persons, invisible to a principal lacking
EU entitlement."* `docs/wave13b-design.md` §5 requires the gate to run the same
traversal under two principals and diff the result — counting EU-resident
persons and separately counting entitlements proves nothing about whether
policy filters anything.

That needs two principals differing on **exactly one** entitlement, so the diff
has a single cause. This adds `sees_eu_person_data` to `principal` and a fourth
principal that has it, alongside the existing three that do not.

## Refresh state is the `T` element

Per-client cycle length keyed to risk rating, with a last-refresh date and a
derived due date. Deliberately includes clients that are **overdue** — a
refresh tracker where everything is current cannot demonstrate a refresh
falling due, which §E names as a supersession trigger.

Dates are anchored to a fixed `AS_OF`, never to `now()`. A tracker anchored on
the clock reclassifies its own rows every day it is not run, which is the
staleness defect Wave 12 recorded (`known-issues.md` §12).

Output: sources/screening/wave13b_policy.json

    uv run generators/generate_policy_wave13b.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from random import Random

from ccf.config import REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"

#: The decision reference for every derived date here. Never `now()`.
AS_OF = date(2026, 8, 22)

#: (jurisdiction, intent) -> (threshold_pct, basis)
#: Percentages are the real statutory figures; the ROWS are synthetic internal
#: policy, because a bank's own register is what a KYC system actually reads.
THRESHOLDS = {
    ("GB", "onboarding"): (25.0, "UK PSC regime: 'more than 25%' of shares or voting rights"),
    ("GB", "enhanced_due_diligence"): (10.0, "internal EDD policy tightens the statutory floor"),
    ("GB", "sanctions_screening"): (0.0, "any stake — a sanctioned party at 3% still taints the exposure"),
    ("US", "onboarding"): (25.0, "FinCEN CDD rule: 25% equity, plus one control person"),
    ("US", "enhanced_due_diligence"): (10.0, "internal EDD policy"),
    ("US", "sanctions_screening"): (0.0, "OFAC 50 Percent Rule aggregates any ownership"),
    ("DE", "onboarding"): (25.0, "EU 4AMLD/5AMLD transposition: more than 25%"),
    ("DE", "sanctions_screening"): (0.0, "EU restrictive measures aggregate"),
    ("NL", "onboarding"): (25.0, "EU 4AMLD/5AMLD transposition"),
    ("FR", "onboarding"): (25.0, "EU 4AMLD/5AMLD transposition"),
    ("IE", "onboarding"): (25.0, "EU 4AMLD/5AMLD transposition"),
    ("LU", "onboarding"): (25.0, "EU 4AMLD/5AMLD transposition"),
    ("CH", "onboarding"): (25.0, "Swiss AMLA beneficial-owner declaration"),
    ("SG", "onboarding"): (25.0, "Singapore register of registrable controllers"),
    ("HK", "onboarding"): (25.0, "Hong Kong significant controllers register"),
    ("VGB", "onboarding"): (25.0, "BVI BOSS Act registrable beneficial owner"),
    ("KY", "onboarding"): (25.0, "Cayman beneficial ownership regime"),
    ("PAN", "onboarding"): (25.0, "Panama final beneficiary register"),
}

#: The residency constraint §C files under Fluree.
EU_EEA_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece",
    "Hungary", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg",
    "Malta", "Netherlands", "Poland", "Portugal", "Romania", "Slovakia",
    "Slovenia", "Spain", "Sweden",
]

RESIDENCY_CONSTRAINT = {
    "constraint_id": "RESID-EU-001",
    "label": "EU/EEA resident person data requires EU entitlement",
    "requires_entitlement": "sees_eu_person_data",
    "applies_to_countries": EU_EEA_COUNTRIES,
    "basis": "GDPR Art. 44-49 restrict transfers of personal data outside the "
             "EEA. A principal without EU entitlement must not see person "
             "nodes resident there materialize at all — filtering after "
             "retrieval is not the same control.",
    "provenance": "synthetic — internal",
}

#: New principal, differing from the existing three on exactly one entitlement.
EU_PRINCIPAL = {
    "principal_id": "PRIN-KYC-004",
    "name": "EU KYC analyst",
    "side": "private",
    "perspective": "kyc-analyst",
    "sees_mnpi": False,
    "sees_need_to_know": False,
    "sees_eu_person_data": True,
    "provenance": "synthetic — internal",
}

#: Refresh cycle length by risk rating, in days.
CYCLE_DAYS = {"low": 1095, "standard": 730, "high": 365, "enhanced": 180}


def main() -> int:
    rng = Random(20260822)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT lei, legal_name FROM legal_entity WHERE is_anchor "
                    "ORDER BY lei")
        anchors = cur.fetchall()

    refresh_rows = []
    for lei, name in anchors:
        rating = rng.choices(list(CYCLE_DAYS),
                             weights=[25, 45, 22, 8], k=1)[0]
        cycle = CYCLE_DAYS[rating]
        # Spread last-refresh dates so some clients fall due and some do not.
        # A tracker where everything is current cannot show a refresh falling
        # due, which §E names as a supersession trigger.
        age = rng.randrange(int(cycle * 0.2), int(cycle * 1.45))
        last = AS_OF - timedelta(days=age)
        due = last + timedelta(days=cycle)
        overdue_days = (AS_OF - due).days
        refresh_rows.append({
            "lei": lei,
            "client_name": name,
            "risk_rating": rating,
            "cycle_days": cycle,
            "last_refresh": last.isoformat(),
            "next_due": due.isoformat(),
            "as_of": AS_OF.isoformat(),
            "status": ("overdue" if overdue_days > 0
                       else "due_soon" if overdue_days > -60 else "current"),
            "days_overdue": max(0, overdue_days),
            "provenance": "synthetic — internal",
        })

    threshold_rows = [
        {"jurisdiction": j, "intent": i, "threshold_pct": pct, "basis": basis,
         "provenance": "synthetic — internal"}
        for (j, i), (pct, basis) in sorted(THRESHOLDS.items())
    ]

    status = Counter(r["status"] for r in refresh_rows)
    ratings = Counter(r["risk_rating"] for r in refresh_rows)
    by_intent = Counter(r["intent"] for r in threshold_rows)

    print("Wave 13b Task 6 — policy, residency, refresh state\n")
    print(f"  as_of                 {AS_OF}  (fixed; never now())")
    print(f"  bo_threshold          {len(threshold_rows):>4}   "
          f"intents: {dict(by_intent)}")
    print(f"  jurisdictions         {len({r['jurisdiction'] for r in threshold_rows}):>4}")
    print(f"  residency constraint  {RESIDENCY_CONSTRAINT['constraint_id']} "
          f"over {len(EU_EEA_COUNTRIES)} countries")
    print(f"  new principal         {EU_PRINCIPAL['principal_id']} "
          f"({EU_PRINCIPAL['name']})")
    print(f"  kyc_refresh_state     {len(refresh_rows):>4}   "
          f"status: {dict(status)}  ratings: {dict(ratings)}")

    failures = []
    # A threshold set where every intent agrees makes `intent` decorative.
    spread = {j: {r["threshold_pct"] for r in threshold_rows
                  if r["jurisdiction"] == j}
              for j in {r["jurisdiction"] for r in threshold_rows}}
    if not any(len(v) > 1 for v in spread.values()):
        failures.append("no jurisdiction has thresholds that DIFFER by intent; "
                        "the intent parameter would be decorative")
    if status["overdue"] < 1:
        failures.append("no client is overdue; a refresh falling due cannot "
                        "be demonstrated")
    if status["current"] < 1:
        failures.append("no client is current; without both sides the status "
                        "discriminates nothing")
    if failures:
        for f in failures:
            print(f"\n  FAIL  {f}")
        return 1

    out = SCREEN / "wave13b_policy.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "Wave 13b — policy and refresh state "
                                 "(kyc-refresh-beneficial-ownership §C)",
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "as_of": AS_OF.isoformat(),
                "thresholds": threshold_rows,
                "residency_constraint": RESIDENCY_CONSTRAINT,
                "eu_principal": EU_PRINCIPAL,
                "refresh_state": refresh_rows,
            },
            indent=1,
        )
        + "\n"
    )
    print(f"\n  written: {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
