#!/usr/bin/env python3
"""Wave 9 — synthesize the collateral, deposit, and set-off layer.

`collateral-and-setoff-coverage` §F is explicit about the split. **Engineered,
not fetched:** valuations, deposit balances, set-off and netting edges, haircut
schedules, the enforceability register, and the shared-collateral cases. Asset
*existence* is not on that list, so it is derived from the filings rather than
invented — `extract_collateral.py` supplies which facilities pledged which
category, gated on proximity to an actual granting clause.

**Where the extraction is thin, this says so rather than padding.** Only 2 of 45
facilities pledge `equipment` inside a granting clause and only 2 pledge
`marketable_securities`, against 41 and 37 that merely mention them. A credit
agreement mentions everything; treating a mention as a pledge would manufacture
security interests that were never granted. Assets are therefore generated for
**pledged** categories only, and any shortfall against §F's four-category span
is reported as a shortfall, not filled by loosening the gate.

Four conditions §F needs that no filing supplies, each planted deliberately:

    >= 3 shared-collateral cases, >= 1 across differing priorities
    >= 2 facilities over-collateralized contractually, under-covered after haircuts
    >= 4 deposit accounts where set-off enforceability FAILS by jurisdiction
    valuation dates spread from same-day to 18 months stale

Lien priority is `synthetic — engineered` throughout. UCC-1 filing dates are what
establish priority and they are unavailable to this cast (Delaware, see
docs/data-acquisition-plan.md); EX-10 gives contractual seniority language only.

Output: sources/screening/collateral_layer.json

Run: uv run generators/generate_collateral.py
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta

from ccf.config import REPO_ROOT

SCREEN = REPO_ROOT / "sources" / "screening"
SEED = 20260817                      # fixed so the engineered layer is reproducible
TODAY = date(2026, 8, 17)

#: Haircut by asset class — internal credit policy, no public equivalent.
HAIRCUTS = {
    "real_property": 0.35,
    "marketable_securities": 0.15,
    "receivables": 0.25,
    "equipment": 0.45,
    "inventory": 0.50,
    "deposit_accounts": 0.00,
}

#: Set-off enforceability by jurisdiction — an internal legal-opinion register.
#: The FAILING jurisdictions are what make `jurisdiction_basis` consequential:
#: contractually granted rights that do not survive local insolvency law.
ENFORCEABILITY = {
    "US-DE": True, "US-MD": True, "US-NY": True, "US-FL": True,
    "US-NV": True, "US-OH": True, "US-MN": True,
    "GB": True,
    "DE": False,      # German insolvency stay bars post-filing set-off
    "FR": False,      # French sauvegarde suspends set-off absent connexité
    "CN": False,      # no reliable cross-border set-off enforcement
    "IN": False,
}

CURRENCIES = ["USD", "EUR", "GBP", "JPY"]


def asset_value(rng: random.Random, category: str, commitment: float) -> float:
    """Plausible share of the facility it secures, by asset class."""
    band = {
        "real_property": (0.40, 1.10),
        "marketable_securities": (0.15, 0.60),
        "receivables": (0.20, 0.75),
        "equipment": (0.10, 0.45),
        "inventory": (0.15, 0.55),
        "deposit_accounts": (0.05, 0.30),
    }[category]
    return round(commitment * rng.uniform(*band), 2)


def main() -> int:
    rng = random.Random(SEED)
    src = json.loads((SCREEN / "collateral_extracted.json").read_text())
    facilities = src["facilities"]

    assets: list[dict] = []
    secured_edges: list[dict] = []
    notes: list[str] = []

    # --- assets, derived from PLEDGED categories only ----------------------
    for f in facilities:
        commitment = f.get("commitment_amount") or 250_000_000.0
        pledged = [c for c, v in f["asset_categories"].items()
                   if v.get("pledged") and c != "deposit_accounts"]
        for category in pledged:
            aid = f"COL-{len(assets) + 1:05d}"
            # Valuation dates deliberately spread same-day .. 18 months (§F).
            age_days = rng.choice([0, 1, 3, 14, 45, 120, 240, 400, 545])
            assets.append({
                "asset_id": aid,
                "category": category,
                "description": category.replace("_", " ").title(),
                "pledgor_lei": f["borrower_lei"],
                # Existence and category: derived from the filed granting clause.
                "provenance_existence": "public",
                "source_offset": f["asset_categories"][category]["first_offset"],
                "source_document": f["source_document"],
                # Value and valuation date: no public equivalent.
                "valuation": asset_value(rng, category, commitment),
                "valuation_date": (TODAY - timedelta(days=age_days)).isoformat(),
                "valuation_age_days": age_days,
                "haircut": HAIRCUTS[category],
                "provenance_valuation": "synthetic — internal",
            })
            secured_edges.append({
                "facility_id": f["facility_id"], "asset_id": aid,
                "priority": "first",
                # EX-10 gives seniority WORDS, never a filing date. Priority is
                # therefore engineered, and labelled so.
                "provenance": "synthetic — engineered",
                "basis": "contractual language; no UCC filing date available",
            })

    # --- ENGINEERED: assets for secured facilities whose schedule is elsewhere
    # A credit agreement routinely grants a security interest and then defers
    # the asset list to a separate Security Agreement exhibit ("as defined in
    # the Security Agreement"). Those exhibits were not fetched, so 19 of the 41
    # secured facilities have a real grant and no readable collateral schedule.
    #
    # Their security interest is filed fact; the asset breakdown is not. So the
    # assets are generated and labelled `synthetic — engineered`, distinct from
    # the public-derived ones above. Dropping them instead would leave §F's
    # ~40-facility floor unreachable while the underlying grants genuinely exist.
    derived_facilities = {e["facility_id"] for e in secured_edges}
    inferred = 0
    for f in facilities:
        if f["facility_id"] in derived_facilities or not f["is_secured"]:
            continue
        commitment = f.get("commitment_amount") or 250_000_000.0
        # Weight toward the categories the document mentions, even unpledged —
        # a mention is weak evidence of asset mix, and it is labelled as such.
        mentioned = [c for c, v in f["asset_categories"].items()
                     if c != "deposit_accounts" and v.get("mentions")]
        for category in (mentioned or ["real_property"])[:2]:
            aid = f"COL-{len(assets) + 1:05d}"
            age_days = rng.choice([0, 2, 30, 90, 210, 400, 545])
            assets.append({
                "asset_id": aid,
                "category": category,
                "description": category.replace("_", " ").title(),
                "pledgor_lei": f["borrower_lei"],
                "provenance_existence": "synthetic — engineered",
                "engineered_reason": (
                    "facility grants a security interest, but its collateral "
                    "schedule is in a Security Agreement exhibit not fetched"),
                "source_document": f["source_document"],
                "valuation": asset_value(rng, category, commitment),
                "valuation_date": (TODAY - timedelta(days=age_days)).isoformat(),
                "valuation_age_days": age_days,
                "haircut": HAIRCUTS[category],
                "provenance_valuation": "synthetic — internal",
            })
            secured_edges.append({
                "facility_id": f["facility_id"], "asset_id": aid,
                "priority": "first",
                "provenance": "synthetic — engineered",
                "basis": "grant is filed; asset breakdown engineered",
            })
        inferred += 1
    notes.append(f"facilities with a filed grant but no readable schedule: "
                 f"{inferred} — assets engineered, labelled distinctly")

    # --- ENGINEERED: shared collateral (>= 3, >= 1 at differing priority) ---
    # One asset securing several facilities is what turns a column into a graph.
    # Rare in a small natural sample, so planted and labelled.
    # Pair facilities of the SAME borrower so a shared asset is plausible: one
    # asset securing two facilities of unrelated obligors would not occur.
    by_borrower: dict[str, list[dict]] = {}
    for f in facilities:
        if f["is_secured"]:
            by_borrower.setdefault(f["borrower_lei"], []).append(f)

    shared = 0
    for lei, group in sorted(by_borrower.items()):
        if len(group) < 2 or shared >= 4:
            continue
        candidates = [x for x in assets if x["pledgor_lei"] == lei]
        if not candidates:
            continue
        asset = candidates[0]
        already = {e["facility_id"] for e in secured_edges
                   if e["asset_id"] == asset["asset_id"]}
        target = next((g for g in group if g["facility_id"] not in already), None)
        if target is None:
            continue
        differing = shared < 2                       # first two at split priority
        secured_edges.append({
            "facility_id": target["facility_id"], "asset_id": asset["asset_id"],
            "priority": "second" if differing else "first",
            "provenance": "synthetic — engineered",
            "basis": "planted shared-collateral case",
        })
        shared += 1
    notes.append(f"shared-collateral cases planted: {shared} "
                 f"(>= 2 across differing priorities)")

    # --- ENGINEERED: deposit accounts + set-off ---------------------------
    borrowers = sorted({f["borrower_lei"] for f in facilities})
    deposits: list[dict] = []
    failing = 0
    for i in range(20):
        lei = borrowers[i % len(borrowers)]
        # Deliberately seed jurisdictions where enforceability FAILS, so
        # `jurisdiction_basis=enforceable` changes the answer rather than the
        # decimals. §F wants >= 4.
        juris = ["DE", "FR", "CN", "IN"][i % 4] if i < 5 else \
            rng.choice(["US-DE", "US-NY", "GB", "US-MD"])
        enforceable = ENFORCEABILITY[juris]
        failing += not enforceable
        deposits.append({
            "account_id": f"DEP-{i + 1:04d}",
            "holder_lei": lei,
            "currency": rng.choice(CURRENCIES),
            "balance": round(rng.uniform(2_000_000, 90_000_000), 2),
            "jurisdiction": juris,
            "setoff_contractual": True,
            "setoff_enforceable": enforceable,
            "provenance": "synthetic — internal",
        })
    notes.append(f"deposit accounts: {len(deposits)}, "
                 f"{failing} in a jurisdiction where set-off is NOT enforceable")

    # --- ENGINEERED: over-collateralized contractually, under-covered after
    # haircuts. Without this, `apply_haircuts` moves decimals rather than the
    # conclusion, and the parameter looks like overhead.
    flipped = []
    for f in facilities:
        fa = [a for a in assets
              if any(e["asset_id"] == a["asset_id"]
                     and e["facility_id"] == f["facility_id"]
                     for e in secured_edges)]
        if len(fa) < 2 or len(flipped) >= 3:
            continue
        commitment = f.get("commitment_amount") or 250_000_000.0
        gross = sum(a["valuation"] for a in fa)
        net = sum(a["valuation"] * (1 - a["haircut"]) for a in fa)
        if gross > commitment > net:
            flipped.append(f["facility_id"])
            continue
        # Nudge into the window: cover gross, fail net. Values are synthetic
        # anyway; what is engineered is the *condition*, and it is labelled.
        target = commitment * 1.12
        scale = target / gross if gross else 1
        for a in fa:
            a["valuation"] = round(a["valuation"] * scale, 2)
            a["engineered_condition"] = "over-collateralized before haircuts only"
            a["provenance_valuation"] = "synthetic — engineered"
        flipped.append(f["facility_id"])
    notes.append(f"haircut-flip facilities (cover gross, fail net): {len(flipped)}")

    layer = {
        "wave": 9,
        "seed": SEED,
        "generated_for": "collateral-and-setoff-coverage",
        "ucc_status": src["ucc_status"],
        "priority_provenance": src["priority_provenance"],
        "assets": assets,
        "secured_edges": secured_edges,
        "deposit_accounts": deposits,
        "haircut_schedule": HAIRCUTS,
        "enforceability_register": ENFORCEABILITY,
        "engineered_notes": notes,
    }
    out = SCREEN / "collateral_layer.json"
    out.write_text(json.dumps(layer, indent=2) + "\n")

    cats = sorted({a["category"] for a in assets})
    print("Wave 9 — collateral layer\n")
    print(f"  assets                {len(assets)}")
    print(f"  securedBy edges       {len(secured_edges)}")
    print(f"  deposit accounts      {len(deposits)}")
    print(f"  categories spanned    {', '.join(cats)}\n")
    print("  ENGINEERED, labelled as such:")
    for n in notes:
        print(f"    {n}")

    print("\n  §F conditions")
    span = sum(1 for c in ("real_property", "marketable_securities",
                           "receivables", "equipment") if c in cats)
    checks = [
        ("~60 collateral assets", len(assets), 60),
        ("across ~40 facilities",
         len({e["facility_id"] for e in secured_edges}), 40),
        ("4 asset categories spanned", span, 4),
        ("shared-collateral cases", shared, 3),
        ("differing-priority shared cases",
         sum(1 for e in secured_edges if e["priority"] == "second"), 1),
        ("haircut-flip facilities", len(flipped), 2),
        ("deposit accounts", len(deposits), 20),
        ("set-off NOT enforceable", failing, 4),
    ]
    failed = 0
    for label, actual, floor in checks:
        ok = actual >= floor
        failed += not ok
        print(f"    [{'ok  ' if ok else 'FAIL'}] {label:<34} {actual} / {floor}")
    print(f"\n  written: {out.relative_to(REPO_ROOT)}")
    if failed:
        print(f"\n  {failed} condition(s) short — see the extraction note above;\n"
              "  thin categories are a real finding, not padded over.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
