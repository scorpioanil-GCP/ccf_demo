#!/usr/bin/env python3
"""Wave 9 — synthesize the guarantee and cross-default topology.

`credit-exposure-rollup` exists to show that exposure is **not additive across a
legal-entity list**: a guarantee means a subsidiary's exposure is also the
parent's, so summing facility balances by borrower LEI double-counts. §F asks for
>= 3 families where naive and guarantee-adjusted summation *differ materially*,
because without that the dedup step is unobservable and the product looks like
arithmetic anybody could do.

**That case has no natural carrier in this cast, and the reason is worth stating.**
The ownership graph has 462 edges and 118 subsidiaries sitting under the 9
borrowers that have children — and **not one of those subsidiaries is itself a
borrower**. Facilities were extracted from EX-10 exhibits, which are filed by the
*parent*, so every facility in the estate belongs to a family head. A parent
guaranteeing a subsidiary's facility therefore cannot occur naturally here.

So it is planted, deliberately and labelled, exactly as Wave 3 planted the depth
chains and the cross-shareholding cycle for the same reason. Two edges per case:
an ownership edge linking two borrower families, and the guarantee on top of it.

What IS natural: upstream guarantees to subsidiaries holding no facility, of
which there are 118 candidates. Those need no engineering beyond selection.

Every FIBO term used here was bound in Wave 0 and is real:
`fibo-fbc-dae-gty:Guaranty` / `hasGuarantor` / `isGuaranteedBy`,
`fibo-fbc-dae-cre:CrossDefaultProvision`, `fibo-fbc-dae-dbt:hasBorrower`.

Output: sources/screening/exposure_layer.json

Run: uv run generators/generate_exposure.py
"""

from __future__ import annotations

import json
import random
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
P_OWNS = f"{FIBO}FND/OwnershipAndControl/Ownership/owns"
SEED = 20260817

#: Group-limit definitions by intent. Versioned POLICY, not code — a change here
#: changes every rollup, which is why the lineage record carries policy_version.
LIMIT_DEFINITIONS = [
    {"intent": "group-limit-test", "counts_guarantees": True,
     "counts_undrawn": True, "connection_basis": "control",
     "limit_pct_of_capital": 0.25},
    {"intent": "regulatory-large-exposure", "counts_guarantees": True,
     "counts_undrawn": True, "connection_basis": "both",
     "limit_pct_of_capital": 0.25},
    {"intent": "internal-appetite", "counts_guarantees": False,
     "counts_undrawn": False, "connection_basis": "control",
     "limit_pct_of_capital": 0.15},
]


def main() -> int:
    rng = random.Random(SEED)

    # --- the graph as loaded -----------------------------------------------
    q = f"SELECT ?p ?c FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?p <{P_OWNS}> ?c }}"
    owns = [(b["p"]["value"], b["c"]["value"])
            for b in fluree.query(q)["results"]["bindings"]]
    q2 = f"SELECT ?s ?l FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{EX}lei> ?l }}"
    lei_by_uri = {b["s"]["value"]: b["l"]["value"]
                  for b in fluree.query(q2)["results"]["bindings"]}
    uri_by_lei: dict[str, str] = {}
    for uri, lei in lei_by_uri.items():
        uri_by_lei.setdefault(lei, uri)

    children: dict[str, list[str]] = {}
    for p, c in owns:
        children.setdefault(p, []).append(c)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT facility_id, borrower_lei, commitment_amount, '
                    f'outstanding_balance FROM "{PG_SCHEMA_V2}".facility')
        facilities = [{"facility_id": r[0], "lei": r[1],
                       "commitment": float(r[2] or 0),
                       "outstanding": float(r[3] or 0)} for r in cur.fetchall()]
    borrowers = sorted({f["lei"] for f in facilities})

    guarantees: list[dict] = []
    cross_defaults: list[dict] = []
    notes: list[str] = []

    # --- NATURAL: upstream guarantees to subsidiaries holding no facility ---
    # The case a borrower-keyed sum structurally cannot find: the parent is on
    # the hook for an entity that appears nowhere in the facility table.
    upstream = 0
    for parent_uri, kids in sorted(children.items()):
        parent_lei = lei_by_uri.get(parent_uri)
        if parent_lei not in borrowers or upstream >= 24:
            continue
        for kid in kids[:4]:
            if lei_by_uri.get(kid) in borrowers:
                continue
            guarantees.append({
                "guarantor_uri": parent_uri, "obligor_uri": kid,
                "guarantor_lei": parent_lei,
                "kind": "upstream",
                "covered_pct": round(rng.uniform(0.60, 1.00), 2),
                "cap_amount": None,
                "provenance": "synthetic — internal",
                "note": "parent guarantees a subsidiary that holds no facility",
            })
            upstream += 1
            if upstream >= 24:
                break
    notes.append(f"upstream guarantees to non-borrowing subsidiaries: {upstream} "
                 f"(natural — selected, not planted)")

    # --- ENGINEERED: the dedup case ---------------------------------------
    # No subsidiary in this estate holds a facility, so a parent-guarantees-
    # subsidiary's-facility case cannot arise. Planted: an ownership edge
    # linking two borrower families, then the guarantee on top.
    planted_owns: list[dict] = []
    dedup = 0
    pairs = [(borrowers[i], borrowers[i + 1])
             for i in range(0, min(8, len(borrowers) - 1), 2)]
    for parent_lei, child_lei in pairs:
        if dedup >= 4:
            break
        p_uri, c_uri = uri_by_lei.get(parent_lei), uri_by_lei.get(child_lei)
        if not p_uri or not c_uri or p_uri == c_uri:
            continue
        planted_owns.append({
            "parent_uri": p_uri, "child_uri": c_uri,
            "provenance": "synthetic — engineered",
            "note": "links two borrower families so a guarantee can create the "
                    "dedup case; no subsidiary in this estate holds a facility",
        })
        guarantees.append({
            "guarantor_uri": p_uri, "obligor_uri": c_uri,
            "guarantor_lei": parent_lei,
            "kind": "downstream-dedup",
            "covered_pct": 1.0, "cap_amount": None,
            "provenance": "synthetic — engineered",
            "note": "parent guarantees a borrowing subsidiary in full — naive "
                    "summation double-counts this exposure",
        })
        dedup += 1
    notes.append(f"engineered dedup families (naive != guarantee-adjusted): {dedup}")

    # --- cross-default, incl. reaching entities with no facility ----------
    no_facility = [u for u in lei_by_uri
                   if lei_by_uri.get(u) not in borrowers][:60]
    reaching = 0
    for i in range(15):
        src_lei = borrowers[i % len(borrowers)]
        src = uri_by_lei.get(src_lei)
        if not src:
            continue
        # >= 2 must reach an entity holding no facility — the entity a
        # borrower-keyed sum has no row for.
        if i < 5 and no_facility:
            dst = no_facility[i]
            reaching += 1
        else:
            dst = uri_by_lei.get(borrowers[(i + 3) % len(borrowers)])
        if not dst or dst == src:
            continue
        cross_defaults.append({
            "from_uri": src, "to_uri": dst,
            "threshold_amount": rng.choice([25_000_000, 50_000_000, 100_000_000]),
            "reaches_non_borrower": dst in no_facility,
            "provenance": "synthetic — internal",
        })
    notes.append(f"cross-default edges: {len(cross_defaults)}, "
                 f"{reaching} reaching an entity holding no facility")

    # --- reconciliation against reported debt ------------------------------
    # §C: synthetic commitments should be a PLAUSIBLE SHARE of real XBRL debt.
    # This is the credibility test the estate would otherwise lack — it stops a
    # mid-cap borrower carrying an implausible book.
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT x.lei, MAX(f.value) AS reported_debt
            FROM "{PG_SCHEMA_V2}".financial_fact f
            JOIN "{PG_SCHEMA_V2}".crosswalk x ON x.cik::text = f.cik::text
            WHERE f.tag IN ('LongTermDebt','LongTermDebtNoncurrent',
                            'DebtLongtermAndShorttermCombinedAmount')
            GROUP BY x.lei
        """)
        debt = {r[0]: float(r[1] or 0) for r in cur.fetchall()}

    recon = []
    for lei in borrowers:
        committed = sum(f["commitment"] for f in facilities if f["lei"] == lei)
        reported = debt.get(lei, 0.0)
        if reported > 0:
            recon.append({"lei": lei, "committed": committed,
                          "reported_debt": reported,
                          "share": round(committed / reported, 3)})
    implausible = [r for r in recon if r["share"] > 1.5]
    notes.append(f"debt reconciliation: {len(recon)} borrowers checked, "
                 f"{len(implausible)} with committed > 150% of reported debt")

    layer = {
        "wave": 9, "seed": SEED,
        "generated_for": "credit-exposure-rollup",
        "guarantees": guarantees,
        "cross_defaults": cross_defaults,
        "planted_ownership": planted_owns,
        "limit_definitions": LIMIT_DEFINITIONS,
        "debt_reconciliation": recon,
        "engineered_notes": notes,
    }
    out = SCREEN / "exposure_layer.json"
    out.write_text(json.dumps(layer, indent=2) + "\n")

    print("Wave 9 — exposure layer\n")
    print(f"  guarantees        {len(guarantees)}")
    print(f"  cross-defaults    {len(cross_defaults)}")
    print(f"  planted ownership {len(planted_owns)}")
    print(f"  limit definitions {len(LIMIT_DEFINITIONS)}\n")
    print("  ENGINEERED / SELECTED, labelled as such:")
    for n in notes:
        print(f"    {n}")

    print("\n  §F conditions")
    checks = [
        ("~25 guarantee edges", len(guarantees), 25),
        ("upstream to a non-borrowing sub", upstream, 3),
        ("families where naive != adjusted", dedup, 3),
        ("~15 cross-default edges", len(cross_defaults), 15),
        ("cross-default reaching a non-borrower", reaching, 2),
        ("borrowers reconciled to XBRL debt", len(recon), 10),
    ]
    short = 0
    for label, actual, floor in checks:
        ok = actual >= floor
        short += not ok
        print(f"    [{'ok  ' if ok else 'FAIL'}] {label:<38} {actual} / {floor}")
    print(f"\n  written: {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
