#!/usr/bin/env python3
"""Wave 7 — load the MNPI wall across Postgres, Fluree, and MongoDB.

Store split per `mnpi-wall-enforcement` §C. SQLite is loaded separately by
`load_sqlite_wave7.py` because the Policy Operator reads it FIRST and its
output bounds every subsequent step.

    Postgres  deal pipeline, MNPI interactions, positions, ProjectionPlans
    Fluree    wall-state assertions (valid + assertion time), embargo windows,
              Reg FD events
    MongoDB   research notes, published and draft, with MNPI classification

The `ProjectionPlan` is a structural interface with its own identity (§7.5), so
`projection_plan_id` enters the lineage record. A supervisor asking *why did
this analyst see this* gets an answer naming the plan version, not an
explanation.

**Edge-type permission is stored on the plan, not applied as a filter.** An
MNPI-bearing engagement edge is not traversed and discarded for a public-side
principal; it is not in the traversal's vocabulary. Storing the permitted set
per principal is what makes that expressible downstream.

    uv run loaders/load_mnpi_wave7.py --dry-run
    uv run loaders/load_mnpi_wave7.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from pymongo import ASCENDING, UpdateOne

from ccf import fluree
from ccf.config import (
    EX, EX_EXTENSION_SCHEMA_NOTE, PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema,
    mongo_db, pg_connect,
)

SCREEN = REPO_ROOT / "sources" / "screening"
BATCH = 400
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

PG_DDL = f"""
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".principal (
    principal_id   TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    side           TEXT NOT NULL,
    perspective    TEXT NOT NULL,
    sees_mnpi      BOOLEAN NOT NULL,
    provenance     TEXT NOT NULL
);
COMMENT ON COLUMN "{PG_SCHEMA_V2}".principal.perspective IS
  'Requestable but NEVER self-asserted. A request for a perspective the '
  'credential does not support is REFUSED, not downgraded -- silent downgrade '
  'would let a caller probe the wall by observing which requests degrade.';

CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".projection_plan (
    projection_plan_id TEXT PRIMARY KEY,
    principal_id       TEXT NOT NULL
                       REFERENCES "{PG_SCHEMA_V2}".principal(principal_id),
    plan_version       TEXT NOT NULL,
    permitted_edge_types      JSONB NOT NULL,
    permitted_classifications JSONB NOT NULL,
    permitted_document_types  JSONB NOT NULL,
    provenance         TEXT NOT NULL
);
COMMENT ON TABLE "{PG_SCHEMA_V2}".projection_plan IS
  'A structural interface with its own identity (§7.5). projection_plan_id '
  'enters the lineage record so a supervisor asking why an analyst saw '
  'something gets a plan version, not an explanation. Permitted edge types '
  'bound the traversal VOCABULARY -- a forbidden edge is never traversed, not '
  'traversed and discarded.';

CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".deal (
    deal_id       TEXT PRIMARY KEY,
    lei           CHAR(20) NOT NULL
                  REFERENCES "{PG_SCHEMA_V2}".legal_entity(lei),
    deal_type     TEXT NOT NULL,
    stage         TEXT NOT NULL,
    opened_date   DATE NOT NULL,
    mnpi_bearing  BOOLEAN NOT NULL,
    estimated_fee_usd NUMERIC,
    provenance    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".interaction (
    interaction_id   TEXT PRIMARY KEY,
    lei              CHAR(20) NOT NULL,
    deal_id          TEXT,
    interaction_type TEXT NOT NULL,
    interaction_date DATE NOT NULL,
    mnpi_bearing     BOOLEAN NOT NULL,
    provenance       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".position (
    position_id TEXT PRIMARY KEY,
    lei         CHAR(20) NOT NULL,
    quantity    NUMERIC NOT NULL,
    as_of       DATE NOT NULL,
    book        TEXT NOT NULL,
    provenance  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_deal_mnpi
    ON "{PG_SCHEMA_V2}".deal (mnpi_bearing) WHERE mnpi_bearing;
CREATE INDEX IF NOT EXISTS idx_interaction_mnpi
    ON "{PG_SCHEMA_V2}".interaction (mnpi_bearing) WHERE mnpi_bearing;
"""


def t(s: str, p: str, o: str, *, lit: bool = False) -> str:
    obj = ('"' + str(o).replace("\\", "\\\\").replace('"', '\\"')
           .replace("\n", " ") + '"') if lit else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    assert_v2_schema(PG_SCHEMA_V2)
    layer = json.loads((SCREEN / "mnpi_layer.json").read_text())
    today = date.today().isoformat()

    principals = layer["principals"]
    deals = layer["deals"]
    interactions = layer["interactions"]
    positions = layer["positions"]
    research = layer["research_notes"]
    crossings = layer["wall_crossings"]
    reg_fd = layer["reg_fd_events"]

    # --- Fluree triples: wall state, embargoes, Reg FD --------------------
    triples: list[str] = []
    for cls, label in [
        (f"{EX}WallCrossing", "WallCrossing (ex: extension)"),
        (f"{EX}EmbargoWindow", "EmbargoWindow (ex: extension)"),
        (f"{EX}RegFDEvent", "RegFDEvent (ex: extension)"),
    ]:
        triples.append(t(cls, RDF_TYPE, "http://www.w3.org/2002/07/owl#Class"))
        triples.append(t(cls, RDFS_LABEL, label, lit=True))
        triples.append(t(cls, f"{EX}isFiboTerm", "false", lit=True))
        triples.append(t(cls, f"{EX}schemaNote",
                         EX_EXTENSION_SCHEMA_NOTE, lit=True))

    for w in crossings:
        wid = f"{EX}{w['crossing_id']}"
        triples += [
            t(wid, RDF_TYPE, f"{EX}WallCrossing"),
            t(wid, RDFS_LABEL,
              f"wall crossing {w['principal_id']} / {w['lei']}", lit=True),
            t(wid, f"{EX}principalId", w["principal_id"], lit=True),
            t(wid, f"{EX}lei", w["lei"], lit=True),
            # Wall state is T as much as P: valid time for when the wall
            # applied, assertion time for when the control room recorded it.
            t(wid, f"{EX}validFrom", w["valid_from"], lit=True),
            t(wid, f"{EX}assertedAt", w["asserted_at"], lit=True),
            t(wid, f"{EX}recordingLagDays", str(w["recording_lag_days"]), lit=True),
            t(wid, f"{EX}basis", w["basis"], lit=True),
            t(wid, f"{EX}provenance", w["provenance"], lit=True),
        ]
        if w["recording_lag_days"] > 3:
            triples.append(t(wid, f"{EX}isEngineeredRecordingLag", "true", lit=True))

    for r in research:
        if not r["embargo_until"]:
            continue
        eid = f"{EX}EMB-{r['note_id']}"
        triples += [
            t(eid, RDF_TYPE, f"{EX}EmbargoWindow"),
            t(eid, f"{EX}noteId", r["note_id"], lit=True),
            t(eid, f"{EX}lei", r["lei"], lit=True),
            t(eid, f"{EX}validFrom", r["authored_date"], lit=True),
            t(eid, f"{EX}validTo", r["embargo_until"], lit=True),
            t(eid, f"{EX}provenance", r["provenance"], lit=True),
        ]

    for e in reg_fd:
        rid = f"{EX}{e['event_id']}"
        triples += [
            t(rid, RDF_TYPE, f"{EX}RegFDEvent"),
            t(rid, RDFS_LABEL, f"Reg FD disclosure {e['disclosure_date']}", lit=True),
            t(rid, f"{EX}lei", e["lei"], lit=True),
            t(rid, f"{EX}validFrom", e["disclosure_date"], lit=True),
            t(rid, f"{EX}widensAccess", "true", lit=True),
            t(rid, f"{EX}provenance", e["provenance"], lit=True),
        ]

    print("Wave 7 — MNPI wall load\n")
    print(f"  Postgres  principals {len(principals)}, plans {len(principals)}, "
          f"deals {len(deals)}, interactions {len(interactions)}, "
          f"positions {len(positions)}")
    print(f"  Fluree    {len(triples)} triples "
          f"({len(crossings)} crossings, "
          f"{sum(1 for r in research if r['embargo_until'])} embargoes, "
          f"{len(reg_fd)} Reg FD)")
    print(f"  MongoDB   {len(research)} research notes")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    # --- Postgres ---------------------------------------------------------
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(PG_DDL)
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".principal '
            "(principal_id, name, side, perspective, sees_mnpi, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (principal_id) DO UPDATE SET name=EXCLUDED.name",
            [(p["principal_id"], p["name"], p["side"], p["perspective"],
              p["sees_mnpi"], "synthetic — internal") for p in principals],
        )
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".projection_plan '
            "(projection_plan_id, principal_id, plan_version, "
            " permitted_edge_types, permitted_classifications, "
            " permitted_document_types, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (projection_plan_id) DO UPDATE SET "
            "permitted_edge_types=EXCLUDED.permitted_edge_types, "
            "permitted_document_types=EXCLUDED.permitted_document_types",
            [(f"PLAN-{p['perspective']}-v1", p["principal_id"], "v1.0.0",
              json.dumps(p["permitted_edge_types"]),
              json.dumps(p["permitted_classifications"]),
              json.dumps(p["permitted_document_types"]),
              "synthetic — internal") for p in principals],
        )
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".deal '
            "(deal_id, lei, deal_type, stage, opened_date, mnpi_bearing, "
            " estimated_fee_usd, provenance) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (deal_id) DO UPDATE SET stage=EXCLUDED.stage",
            [(d["deal_id"], d["lei"], d["deal_type"], d["stage"],
              d["opened_date"], d["mnpi_bearing"], d["estimated_fee_usd"],
              d["provenance"]) for d in deals],
        )
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".interaction '
            "(interaction_id, lei, deal_id, interaction_type, "
            " interaction_date, mnpi_bearing, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (interaction_id) DO NOTHING",
            [(i["interaction_id"], i["lei"], i["deal_id"],
              i["interaction_type"], i["interaction_date"],
              i["mnpi_bearing"], i["provenance"]) for i in interactions],
        )
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".position '
            "(position_id, lei, quantity, as_of, book, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (position_id) DO UPDATE SET "
            "quantity=EXCLUDED.quantity, as_of=EXCLUDED.as_of",
            [(p["position_id"], p["lei"], p["quantity"], p["as_of"],
              p["book"], p["provenance"]) for p in positions],
        )
        conn.commit()

    # --- MongoDB ----------------------------------------------------------
    db = mongo_db()
    db["research_note"].bulk_write([
        UpdateOne({"_id": r["note_id"]}, {"$set": {**r, "retrieved_at": today}},
                  upsert=True)
        for r in research
    ], ordered=False)
    db["research_note"].create_index([("classification", ASCENDING)])
    db["research_note"].create_index([("status", ASCENDING)])

    # --- Fluree -----------------------------------------------------------
    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".deal '
                    "WHERE mnpi_bearing")
        n_mnpi = cur.fetchone()[0]
    print(f"\n  loaded. MNPI-bearing deals: {n_mnpi}")
    print(f"  research notes in Mongo: "
          f"{db['research_note'].count_documents({})} "
          f"({db['research_note'].count_documents({'status': 'draft'})} draft)")
    print(f"  Fluree t={fluree.ledger_t()}, {fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
