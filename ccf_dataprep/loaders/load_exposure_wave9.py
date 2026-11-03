#!/usr/bin/env python3
"""Wave 9 — load the guarantee and cross-default topology.

Fluree owns the edges, Postgres owns the policy and the reconciliation.

Predicate bindings, all Wave 0 terms except one:

    guarantees        -> fibo-fbc-dae-gty:isGuarantorOf     REAL FIBO term
    borrowerOf        -> fibo-fbc-dae-dbt:hasBorrower       REAL FIBO term
    crossDefaultsWith -> ex:crossDefaultsWith               no FIBO equivalent

`fibo-fbc-dae-cre:CrossDefaultProvision` exists as a **class**, and
`hasDefaultThresholdAmount` describes it, but FIBO has no object property
linking two obligors under a cross-default. Same pattern as Wave 9's collateral
load: FIBO models the provision, not the relation between the parties it binds.
The provision is typed with the real class; the edge is an `ex:` extension.

**`hasBorrower` is loaded here for the first time.** Facilities existed only in
Postgres through Wave 8, so a traversal could reach an obligor and never reach
its facilities. `credit-exposure-rollup` walks from an entity to its exposure,
so the facility has to be a node.

Engineered ownership edges are loaded with `owns` and
`provenance: synthetic — engineered`, sitting beside the public GLEIF edges under
the same predicate. That is deliberate — the traversal must treat them
identically or the dedup case would not be exercised — and the provenance
attribute is what keeps them distinguishable.

    uv run loaders/load_exposure_wave9.py --dry-run
    uv run loaders/load_exposure_wave9.py

Idempotent: stable triples, Postgres upserts.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.config import (EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT,
                        pg_connect)

SCREEN = REPO_ROOT / "sources" / "screening"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

C_GUARANTY = f"{FIBO}FBC/DebtAndEquities/Guaranty/Guaranty"
C_GUARANTOR = f"{FIBO}FBC/DebtAndEquities/Guaranty/Guarantor"
C_XDEFAULT = f"{FIBO}FBC/DebtAndEquities/CreditEvents/CrossDefaultProvision"
C_FACILITY = f"{FIBO}FBC/DebtAndEquities/Debt/CreditFacility"

P_IS_GUARANTOR_OF = f"{FIBO}FBC/DebtAndEquities/Guaranty/isGuarantorOf"
P_HAS_BORROWER = f"{FIBO}FBC/DebtAndEquities/Debt/hasBorrower"
P_THRESHOLD = f"{FIBO}FBC/DebtAndEquities/CreditEvents/hasDefaultThresholdAmount"
P_OWNS = f"{FIBO}FND/OwnershipAndControl/Ownership/owns"
P_XDEFAULTS_WITH = f"{EX}crossDefaultsWith"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
BATCH = 400

DDL = f"""
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".limit_definition (
    intent                  TEXT PRIMARY KEY,
    counts_guarantees       BOOLEAN NOT NULL,
    counts_undrawn          BOOLEAN NOT NULL,
    connection_basis        TEXT NOT NULL,
    limit_pct_of_capital    NUMERIC NOT NULL,
    provenance              TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".guarantee_terms (
    guarantor_lei           TEXT NOT NULL,
    obligor_uri             TEXT NOT NULL,
    kind                    TEXT NOT NULL,
    covered_pct             NUMERIC NOT NULL,
    cap_amount              NUMERIC,
    provenance              TEXT NOT NULL,
    note                    TEXT,
    PRIMARY KEY (guarantor_lei, obligor_uri)
);
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".debt_reconciliation (
    lei                     TEXT PRIMARY KEY,
    committed               NUMERIC NOT NULL,
    reported_debt           NUMERIC NOT NULL,
    share                   NUMERIC NOT NULL,
    plausible               BOOLEAN NOT NULL
);
"""


def esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    layer = json.loads((SCREEN / "exposure_layer.json").read_text())

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT facility_id, borrower_lei FROM "{PG_SCHEMA_V2}".facility')
        facilities = cur.fetchall()
    # Fluree entity URIs are keyed by ex:lei; resolve them through the ledger.
    q = f"SELECT ?s ?l FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{EX}lei> ?l }}"
    uri_by_lei: dict[str, str] = {}
    for b in fluree.query(q)["results"]["bindings"]:
        uri_by_lei.setdefault(b["l"]["value"], b["s"]["value"])

    triples: list[str] = []
    for cls in (C_GUARANTY, C_GUARANTOR, C_XDEFAULT, C_FACILITY):
        triples.append(triple(cls, RDF_TYPE, OWL_CLASS))
        triples.append(triple(cls, RDFS_LABEL, cls.rsplit("/", 1)[-1], literal=True))

    # Facilities become nodes so a traversal can reach exposure from an entity.
    fac_nodes = 0
    for fid, lei in facilities:
        obligor = uri_by_lei.get(lei)
        if not obligor:
            continue
        node = f"{EX}{fid}"
        triples += [
            triple(node, RDF_TYPE, C_FACILITY),
            triple(node, RDFS_LABEL, fid, literal=True),
            triple(node, P_HAS_BORROWER, obligor),
        ]
        fac_nodes += 1

    # Engineered ownership, loaded under the SAME predicate as public edges so
    # traversal treats them alike; provenance keeps them distinguishable.
    for po in layer["planted_ownership"]:
        triples.append(triple(po["parent_uri"], P_OWNS, po["child_uri"]))

    for g in layer["guarantees"]:
        triples.append(triple(g["guarantor_uri"], P_IS_GUARANTOR_OF, g["obligor_uri"]))
        triples.append(triple(g["guarantor_uri"], RDF_TYPE, C_GUARANTOR))

    for i, x in enumerate(layer["cross_defaults"]):
        triples.append(triple(x["from_uri"], P_XDEFAULTS_WITH, x["to_uri"]))
        prov = f"{EX}XDP-{i + 1:04d}"
        triples += [
            triple(prov, RDF_TYPE, C_XDEFAULT),
            triple(prov, P_THRESHOLD, str(x["threshold_amount"]), literal=True),
        ]

    print("Wave 9 — exposure load\n")
    print(f"  Fluree   {len(triples)} triples")
    print(f"    facility nodes (hasBorrower)  {fac_nodes}")
    print(f"    guarantee edges               {len(layer['guarantees'])}")
    print(f"    cross-default edges           {len(layer['cross_defaults'])}")
    print(f"    engineered ownership edges    {len(layer['planted_ownership'])}")
    print(f"  Postgres {len(layer['limit_definitions'])} limit definitions, "
          f"{len(layer['guarantees'])} guarantee terms, "
          f"{len(layer['debt_reconciliation'])} reconciliations")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        for d in layer["limit_definitions"]:
            cur.execute(
                f'INSERT INTO "{PG_SCHEMA_V2}".limit_definition VALUES (%s,%s,%s,%s,%s,%s) '
                "ON CONFLICT (intent) DO UPDATE SET "
                "limit_pct_of_capital=EXCLUDED.limit_pct_of_capital",
                (d["intent"], d["counts_guarantees"], d["counts_undrawn"],
                 d["connection_basis"], d["limit_pct_of_capital"],
                 "synthetic — internal"))
        for g in layer["guarantees"]:
            cur.execute(
                f'INSERT INTO "{PG_SCHEMA_V2}".guarantee_terms VALUES (%s,%s,%s,%s,%s,%s,%s) '
                "ON CONFLICT (guarantor_lei, obligor_uri) DO UPDATE SET "
                "covered_pct=EXCLUDED.covered_pct",
                (g["guarantor_lei"], g["obligor_uri"], g["kind"],
                 g["covered_pct"], g["cap_amount"], g["provenance"], g["note"]))
        for r in layer["debt_reconciliation"]:
            cur.execute(
                f'INSERT INTO "{PG_SCHEMA_V2}".debt_reconciliation VALUES (%s,%s,%s,%s,%s) '
                "ON CONFLICT (lei) DO UPDATE SET share=EXCLUDED.share",
                (r["lei"], r["committed"], r["reported_debt"], r["share"],
                 r["share"] <= 1.5))
        conn.commit()
    print("\n  Postgres loaded.")

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"  Fluree t={fluree.ledger_t()}, {fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
