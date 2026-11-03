#!/usr/bin/env python3
"""Wave 13a stage 2b loader — the collateral extension, into Fluree and Postgres.

    uv run loaders/load_collateral_wave13a.py --dry-run
    uv run loaders/load_collateral_wave13a.py

Writes ONLY the assets and pledges `generators/extend_collateral_wave13a.py`
produced for facilities Wave 13a added. Strictly additive: asset ids start
above the existing maximum, so no existing row is read, rewritten or
renumbered. See that module's docstring for why the Wave 9 chain must not
simply be re-run.

Store split follows Q019 §3 unchanged, and mirrors Wave 9 exactly rather than
inventing a second convention: Fluree carries the typed nodes and the
`collateralizedBy` / `pledgedBy` edges; Postgres carries the attributes
(valuation, haircut, ages). No attribute is duplicated across the two.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, pg_connect
from generators.extend_collateral_wave13a import ARTIFACT
from loaders.load_collateral_wave9 import (C_COLLATERAL, C_NONPHYSICAL,
                                           C_PHYSICAL, EX, P_COLLATERALIZED_BY,
                                           P_PLEDGED_BY, PHYSICAL, RDF_TYPE,
                                           RDFS_LABEL, entity_uri_by_lei,
                                           triple, uri)

BATCH = 400


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    layer = json.loads(ARTIFACT.read_text())
    assets, pledges = layer["assets"], layer["pledges"]
    entity_uri = entity_uri_by_lei()

    triples: list[str] = []
    for a in assets:
        node = uri(a["asset_id"])
        specific = C_PHYSICAL if a["category"] in PHYSICAL else C_NONPHYSICAL
        triples += [
            triple(node, RDF_TYPE, C_COLLATERAL),
            triple(node, RDF_TYPE, specific),
            triple(node, RDFS_LABEL, a["description"], literal=True),
            triple(node, f"{EX}provenance", a["provenance_existence"],
                   literal=True),
        ]
        pledgor = entity_uri.get(a["pledgor_lei"])
        if pledgor:
            triples.append(triple(node, P_PLEDGED_BY, pledgor))
    for p in pledges:
        triples.append(triple(uri(p["facility_id"]), P_COLLATERALIZED_BY,
                              uri(p["asset_id"])))

    print("Wave 13a — collateral extension load\n")
    print(f"  Fluree    {len(triples)} triples "
          f"({len(assets)} assets, {len(pledges)} pledges)")
    print(f"  Postgres  {len(assets)} assets, {len(pledges)} pledges")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    with pg_connect() as conn, conn.cursor() as cur:
        for a in assets:
            cur.execute(
                f'INSERT INTO "{S}".collateral_asset VALUES '
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (asset_id) DO UPDATE SET "
                "valuation=EXCLUDED.valuation, "
                "valuation_date=EXCLUDED.valuation_date, "
                "haircut=EXCLUDED.haircut, "
                "provenance_existence=EXCLUDED.provenance_existence",
                (a["asset_id"], a["category"], a["description"], a["pledgor_lei"],
                 a["valuation"], a["valuation_date"], a["valuation_age_days"],
                 a["haircut"], a["provenance_existence"],
                 a["provenance_valuation"], a.get("engineered_reason"),
                 a.get("source_document"), a.get("source_offset")))
        for p in pledges:
            cur.execute(
                f'INSERT INTO "{S}".collateral_pledge '
                "(facility_id, asset_id, provenance, basis) "
                "VALUES (%s,%s,%s,%s) "
                "ON CONFLICT (facility_id, asset_id) DO UPDATE SET "
                "provenance=EXCLUDED.provenance, basis=EXCLUDED.basis",
                (p["facility_id"], p["asset_id"],
                 p["provenance"], p.get("basis")))
        conn.commit()
        for t in ("collateral_asset", "collateral_pledge"):
            cur.execute(f'SELECT count(*) FROM "{S}".{t}')
            print(f"  {t:<20} {cur.fetchone()[0]:>6}")
    print(f"\n  ledger t={fluree.ledger_t()}, {fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
