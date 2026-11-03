#!/usr/bin/env python3
"""Wave 9 — load the collateral and set-off layer into Fluree and Postgres.

Single-writer discipline, same split as every prior wave. **Fluree owns the
graph**: collateral assets, deposit accounts, and the typed edges between them
and the facilities they secure. **Postgres owns the numbers**: valuations,
valuation dates, balances, the haircut schedule, and the set-off enforceability
register. A Fluree node carries a label and its provenance and nothing else.

**Three of the spec's four relationships have no FIBO property.** Verified live
against `FBC/DebtAndEquities/Debt`, `FND/Agreements/Contracts`,
`FBC/ProductsAndServices/ClientsAndAccounts`, and `LOAN/LoansGeneral/Loans`:
FIBO's entire collateral-relation vocabulary is `isCollateralizedBy` and
`isCollateralizationOf`. So:

    securedBy      -> fibo-fbc-dae-dbt:isCollateralizedBy   REAL FIBO term
    pledgedBy      -> ex:pledgedBy                          no FIBO equivalent
    setOffAgainst  -> ex:setOffAgainst                      no FIBO equivalent
    nettedUnder    -> ex:nettedUnder                        no FIBO equivalent

`fibo-fnd-agr-ctr:NettingProvision` exists as a **class** but nothing links a
party to it, so the edge stays an extension. This is the same shape as the Wave 0
`Covenant` finding — FIBO models the instrument, not the bank's operational
relation to it — and the vault mirror needs to carry it.

Provenance travels per element, and it is not uniform within a single asset:
existence may be `public` (a granting clause names the category) or
`synthetic — engineered` (the grant is filed but its schedule is in an exhibit
that could not be recovered — see known-issues §2.8), while every valuation is
`synthetic — internal`. Lien priority is engineered throughout, because UCC-1
filing dates establish priority and this cast has no UCC access.

    uv run loaders/load_collateral_wave9.py --dry-run
    uv run loaders/load_collateral_wave9.py

Idempotent: Fluree writes are INSERT DATA of stable triples; Postgres upserts.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.config import EX, PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

C_COLLATERAL = f"{FIBO}FBC/DebtAndEquities/Debt/Collateral"
C_PHYSICAL = f"{FIBO}FBC/DebtAndEquities/Debt/PhysicalCollateral"
C_NONPHYSICAL = f"{FIBO}FBC/DebtAndEquities/Debt/NonPhysicalCollateral"
C_DEPOSIT = f"{FIBO}FBC/ProductsAndServices/ClientsAndAccounts/DepositAccount"
C_LIEN = f"{FIBO}LOAN/LoansGeneral/Loans/LenderLienPosition"

P_COLLATERALIZED_BY = f"{FIBO}FBC/DebtAndEquities/Debt/isCollateralizedBy"
P_PLEDGED_BY = f"{EX}pledgedBy"
P_SETOFF_AGAINST = f"{EX}setOffAgainst"
P_NETTED_UNDER = f"{EX}nettedUnder"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

#: Tangible vs intangible, per FIBO's own split.
PHYSICAL = {"real_property", "equipment", "inventory"}

BATCH = 400

DDL = f"""
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".collateral_asset (
    asset_id                TEXT PRIMARY KEY,
    category                TEXT NOT NULL,
    description             TEXT,
    pledgor_lei             TEXT NOT NULL,
    valuation               NUMERIC NOT NULL,
    valuation_date          DATE NOT NULL,
    valuation_age_days      INTEGER NOT NULL,
    haircut                 NUMERIC NOT NULL,
    provenance_existence    TEXT NOT NULL,
    provenance_valuation    TEXT NOT NULL,
    engineered_reason       TEXT,
    source_document         TEXT,
    source_offset           INTEGER
);
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".collateral_pledge (
    facility_id             TEXT NOT NULL,
    asset_id                TEXT NOT NULL,
    provenance              TEXT NOT NULL,
    basis                   TEXT,
    PRIMARY KEY (facility_id, asset_id)
);
-- `priority` was here until Wave 15. Lien priority is Fluree's per §C, and
-- lives on the reified pledge node as a FIBO LenderLienPosition value. Keeping
-- a copy here would be the duplication CLAUDE.md forbids outright.
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".deposit_account (
    account_id              TEXT PRIMARY KEY,
    holder_lei              TEXT NOT NULL,
    currency                TEXT NOT NULL,
    balance                 NUMERIC NOT NULL,
    jurisdiction            TEXT NOT NULL,
    setoff_contractual      BOOLEAN NOT NULL,
    setoff_enforceable      BOOLEAN NOT NULL,
    provenance              TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".haircut_schedule (
    asset_class             TEXT PRIMARY KEY,
    haircut                 NUMERIC NOT NULL,
    provenance              TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".setoff_enforceability (
    jurisdiction            TEXT PRIMARY KEY,
    enforceable             BOOLEAN NOT NULL,
    provenance              TEXT NOT NULL
);
"""


def uri(local: str) -> str:
    return f"{EX}{local}"


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def entity_uri_by_lei() -> dict[str, str]:
    """LEI -> the Fluree entity node Wave 3 actually created.

    Constructing `ex:{lei}` instead of resolving produces an edge that points at
    nothing: valid triple, correct count, traversal arrives nowhere. That is
    exactly the Wave 5 phantom-borrower defect, and this loader reproduced it on
    `pledgedBy` before `partition.py` grew a dangling-target check.
    """
    from ccf.config import FLUREE_LEDGER_V2
    q = f"SELECT ?s ?l FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{EX}lei> ?l }}"
    out: dict[str, str] = {}
    for b in fluree.query(q)["results"]["bindings"]:
        out.setdefault(b["l"]["value"], b["s"]["value"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    layer = json.loads((SCREEN / "collateral_layer.json").read_text())
    entity_uri = entity_uri_by_lei()
    assets = layer["assets"]
    pledges = layer["secured_edges"]
    deposits = layer["deposit_accounts"]

    # --- Fluree: nodes and typed edges ------------------------------------
    triples: list[str] = []
    for cls in (C_COLLATERAL, C_PHYSICAL, C_NONPHYSICAL, C_DEPOSIT, C_LIEN):
        triples.append(triple(cls, RDF_TYPE, "http://www.w3.org/2002/07/owl#Class"))
        triples.append(triple(cls, RDFS_LABEL, cls.rsplit("/", 1)[-1], literal=True))

    for a in assets:
        node = uri(a["asset_id"])
        specific = C_PHYSICAL if a["category"] in PHYSICAL else C_NONPHYSICAL
        triples += [
            triple(node, RDF_TYPE, C_COLLATERAL),
            triple(node, RDF_TYPE, specific),
            triple(node, RDFS_LABEL, a["description"], literal=True),
            # Provenance rides on the node because it is NOT uniform: existence
            # can be public while the valuation beside it is synthetic.
            triple(node, f"{EX}provenance", a["provenance_existence"], literal=True),
            # pledgedBy has no FIBO equivalent — see the module docstring.
        ]
        pledgor = entity_uri.get(a["pledgor_lei"])
        if pledgor:
            triples.append(triple(node, P_PLEDGED_BY, pledgor))

    for p in pledges:
        triples.append(triple(uri(p["facility_id"]), P_COLLATERALIZED_BY,
                              uri(p["asset_id"])))

    for d in deposits:
        node = uri(d["account_id"])
        triples += [
            triple(node, RDF_TYPE, C_DEPOSIT),
            triple(node, RDFS_LABEL, f"{d['currency']} deposit {d['account_id']}",
                   literal=True),
            triple(node, f"{EX}provenance", d["provenance"], literal=True),
        ]
        holder = entity_uri.get(d["holder_lei"])
        if holder:
            triples.append(triple(node, P_SETOFF_AGAINST, holder))
            if d["setoff_enforceable"]:
                triples.append(triple(node, P_NETTED_UNDER, holder))

    pub = sum(1 for a in assets if a["provenance_existence"] == "public")
    print("Wave 9 — collateral load\n")
    print(f"  Fluree   {len(triples)} triples "
          f"({len(assets)} assets, {len(pledges)} pledges, "
          f"{len(deposits)} deposits)")
    print(f"  Postgres {len(assets)} assets, {len(pledges)} pledges, "
          f"{len(deposits)} deposits, "
          f"{len(layer['haircut_schedule'])} haircuts, "
          f"{len(layer['enforceability_register'])} jurisdictions")
    print(f"\n  asset existence provenance: {pub} public, "
          f"{len(assets) - pub} synthetic — engineered")
    print(f"  set-off NOT enforceable: "
          f"{sum(1 for d in deposits if not d['setoff_enforceable'])}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        for a in assets:
            cur.execute(
                f'INSERT INTO "{PG_SCHEMA_V2}".collateral_asset VALUES '
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (asset_id) DO UPDATE SET valuation=EXCLUDED.valuation, "
                "valuation_date=EXCLUDED.valuation_date, haircut=EXCLUDED.haircut, "
                "provenance_existence=EXCLUDED.provenance_existence",
                (a["asset_id"], a["category"], a["description"], a["pledgor_lei"],
                 a["valuation"], a["valuation_date"], a["valuation_age_days"],
                 a["haircut"], a["provenance_existence"], a["provenance_valuation"],
                 a.get("engineered_reason"), a.get("source_document"),
                 a.get("source_offset")))
        for p in pledges:
            cur.execute(
                f'INSERT INTO "{PG_SCHEMA_V2}".collateral_pledge '
                "(facility_id, asset_id, provenance, basis) "
                "VALUES (%s,%s,%s,%s) "
                "ON CONFLICT (facility_id, asset_id) DO UPDATE SET "
                "provenance=EXCLUDED.provenance, basis=EXCLUDED.basis",
                (p["facility_id"], p["asset_id"], p["provenance"],
                 p.get("basis")))
        for d in deposits:
            cur.execute(
                f'INSERT INTO "{PG_SCHEMA_V2}".deposit_account VALUES (%s,%s,%s,%s,%s,%s,%s,%s) '
                "ON CONFLICT (account_id) DO UPDATE SET balance=EXCLUDED.balance, "
                "setoff_enforceable=EXCLUDED.setoff_enforceable",
                (d["account_id"], d["holder_lei"], d["currency"], d["balance"],
                 d["jurisdiction"], d["setoff_contractual"],
                 d["setoff_enforceable"], d["provenance"]))
        for cls, hc in layer["haircut_schedule"].items():
            cur.execute(
                f'INSERT INTO "{PG_SCHEMA_V2}".haircut_schedule VALUES (%s,%s,%s) '
                "ON CONFLICT (asset_class) DO UPDATE SET haircut=EXCLUDED.haircut",
                (cls, hc, "synthetic — internal"))
        for juris, ok in layer["enforceability_register"].items():
            cur.execute(
                f'INSERT INTO "{PG_SCHEMA_V2}".setoff_enforceability VALUES (%s,%s,%s) '
                "ON CONFLICT (jurisdiction) DO UPDATE SET enforceable=EXCLUDED.enforceable",
                (juris, ok, "synthetic — internal"))
        conn.commit()
    print("\n  Postgres loaded.")

    print(f"  writing Fluree in batches of {BATCH}...")
    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"  Fluree t={fluree.ledger_t()}, {fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
