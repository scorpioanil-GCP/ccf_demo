#!/usr/bin/env python3
"""Wave 13b Task 4 — load the offshore intermediary layer.

Reads `sources/screening/wave13b_offshore.json`. Every name in it is invented;
`generators/derive_icij_structure.py` explains why ICIJ's real names are
deliberately not carried, and records that deviation from §C.

Two stores, split the way this estate always splits them:

    Postgres   offshore_intermediary   40 rows   attributes (`E`)
               offshore_vehicle       150 rows   attributes (`E`)
    Fluree     190 nodes, 150 edges              the graph (`R`)

§C files this element under Fluree, and the `R` half is there. The attributes
are not: CLAUDE.md's single-writer rule puts entity attributes in Postgres, and
Fluree nodes carry an identifier, a label and their edges. Duplicating
jurisdiction into both stores is the mistake Wave 12 spent a day on.

## Typing, with no reasoner to help

`cmns-org:ServiceProvider` is an **AgentRole**, not an entity type (verified
2026-08-22 against the live Commons Organizations module — see the binding
table). Fluree runs without inference, so an intermediary node is typed
explicitly as BOTH the Commons organization classes and the ServiceProvider
role: a query for `Organization` will not find a node typed only
`ServiceProvider`, and vice versa. Rule 7, applied rather than assumed.

Vehicles are typed `fibo-be-le-lp:SpecialPurposeVehicle` (already bound) plus
the same organization classes, for the same reason.

## New bindings asserted here

    cmns-org:ServiceProvider     verified against OMG Commons, 2026-08-22
    ex:isIntermediaryFor         FIBO has zero intermediary terms
    ex:jurisdictionCode          FIBO enumerates jurisdiction individuals and
                                 does not enumerate the offshore ones

All three are in `docs/ccf_dataprep_v2.md`. **The vault mirror needs
refreshing.**

    uv run loaders/load_offshore_wave13b.py --dry-run
    uv run loaders/load_offshore_wave13b.py

Idempotent in both stores: Postgres upserts set every non-key column; Fluree
`INSERT DATA` of an unchanged triple is a no-op on a set-valued predicate.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from ccf import fluree
from ccf.party_roles import with_ancestors
from ccf.config import (
    EX,
    FLUREE_LEDGER_V2,
    PG_SCHEMA_V2,
    REPO_ROOT,
    assert_v2_schema,
    pg_connect,
)

S = PG_SCHEMA_V2
SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13b_offshore.json"
BATCH = 500

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

CMNS = "https://www.omg.org/spec/Commons/"
C_ORGANIZATION = f"{CMNS}Organizations/Organization"
C_FORMAL_ORG = f"{CMNS}Organizations/FormalOrganization"
C_LEGAL_ENTITY = f"{CMNS}Organizations/LegalEntity"
C_SERVICE_PROVIDER = f"{CMNS}Organizations/ServiceProvider"
C_SPV = ("https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/"
         "LegalPersons/SpecialPurposeVehicle")

P_IS_INTERMEDIARY_FOR = f"{EX}isIntermediaryFor"
P_JURISDICTION_CODE = f"{EX}jurisdictionCode"
P_IS_FIBO_TERM = f"{EX}isFiboTerm"
P_SCHEMA_NOTE = f"{EX}schemaNote"

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".offshore_intermediary (
    intermediary_id text     PRIMARY KEY,
    name            text     NOT NULL,
    country_code    text     NOT NULL,   -- ISO 3166-1 alpha-3
    status          text     NOT NULL,
    provenance      text     NOT NULL,
    source          text     NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".offshore_vehicle (
    vehicle_id      text     PRIMARY KEY,
    name            text     NOT NULL,
    jurisdiction    text     NOT NULL,
    company_type    text     NOT NULL,
    status          text     NOT NULL,
    provenance      text     NOT NULL,
    source          text     NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".offshore_administration (
    intermediary_id text NOT NULL
                    REFERENCES "{S}".offshore_intermediary(intermediary_id)
                    ON DELETE CASCADE,
    vehicle_id      text NOT NULL
                    REFERENCES "{S}".offshore_vehicle(vehicle_id)
                    ON DELETE CASCADE,
    relationship    text NOT NULL,
    provenance      text NOT NULL,
    PRIMARY KEY (intermediary_id, vehicle_id)
);
"""


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def uri(local: str) -> str:
    return f"{EX}{local}"


def build_triples(doc: dict) -> tuple[list[str], set[str]]:
    triples: list[str] = []
    nodes: set[str] = set()

    for i in doc["intermediaries"]:
        node = uri(i["intermediary_id"])
        nodes.add(node)
        triples += [
            # An AgentRole and the organization classes, both stated. Fluree
            # has no reasoner: a query for Organization will not find a node
            # typed only ServiceProvider.
            # The full chain above LegalEntity comes from ccf.party_roles --
            # this tuple previously stopped at LegalEntity (known-issues §62).
            *(triple(node, RDF_TYPE, t)
              for t in with_ancestors(C_LEGAL_ENTITY)),
            triple(node, RDF_TYPE, C_SERVICE_PROVIDER),
            triple(node, RDFS_LABEL, i["name"], literal=True),
            triple(node, P_JURISDICTION_CODE, i["country_code"], literal=True),
        ]

    for v in doc["vehicles"]:
        node = uri(v["vehicle_id"])
        nodes.add(node)
        triples += [
            *(triple(node, RDF_TYPE, t) for t in with_ancestors(C_SPV)),
            triple(node, RDFS_LABEL, v["name"], literal=True),
            triple(node, P_JURISDICTION_CODE, v["jurisdiction"], literal=True),
        ]

    for e in doc["edges"]:
        triples.append(triple(uri(e["intermediary_id"]),
                              P_IS_INTERMEDIARY_FOR,
                              uri(e["vehicle_id"])))

    # T-Box self-description for the two `ex:` predicates, matching the estate's
    # existing pattern so a consumer holding only the graph can tell an
    # invented term from a FIBO one.
    from ccf.config import EX_EXTENSION_SCHEMA_NOTE
    for term in (P_IS_INTERMEDIARY_FOR, P_JURISDICTION_CODE):
        triples += [
            triple(term, P_IS_FIBO_TERM, "false", literal=True),
            triple(term, P_SCHEMA_NOTE, EX_EXTENSION_SCHEMA_NOTE, literal=True),
        ]
    return triples, nodes


def main() -> int:
    ap = argparse.ArgumentParser(description="Load the offshore layer")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(ARTIFACT.read_text())
    source = (f"structure derived from {doc['shape_source']['name']}; "
              f"names invented (see generators/derive_icij_structure.py)")

    inter_rows = [(i["intermediary_id"], i["name"], i["country_code"],
                   i["status"], i["provenance"], source)
                  for i in doc["intermediaries"]]
    veh_rows = [(v["vehicle_id"], v["name"], v["jurisdiction"],
                 v["company_type"], v["status"], v["provenance"], source)
                for v in doc["vehicles"]]
    adm_rows = [(e["intermediary_id"], e["vehicle_id"], e["relationship"],
                 e["provenance"]) for e in doc["edges"]]

    triples, nodes = build_triples(doc)
    fanout = Counter(e["intermediary_id"] for e in doc["edges"])

    print(f"Wave 13b Task 4 — offshore layer into {S} + Fluree\n")
    print(f"  artifact                {ARTIFACT.relative_to(REPO_ROOT)}")
    print(f"  shape source            {doc['shape_source']['name']} "
          f"({doc['shape_source']['relationships_read']:,} relationships read, "
          f"names taken: {doc['shape_source']['names_taken']})")
    print(f"\n  offshore_intermediary   {len(inter_rows):>5}")
    print(f"  offshore_vehicle        {len(veh_rows):>5}")
    print(f"  offshore_administration {len(adm_rows):>5}   "
          f"fan-out {min(fanout.values())}–{max(fanout.values())}")
    print(f"  Fluree nodes            {len(nodes):>5}")
    print(f"  Fluree triples          {len(triples):>5}")
    print(f"  jurisdictions           "
          f"{len({v['jurisdiction'] for v in doc['vehicles']})}")

    if args.dry_run:
        print("\n  [dry-run] nothing written to either store")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.executemany(
            f'INSERT INTO "{S}".offshore_intermediary '
            "(intermediary_id, name, country_code, status, provenance, source) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (intermediary_id) DO UPDATE SET "
            "name=EXCLUDED.name, country_code=EXCLUDED.country_code, "
            "status=EXCLUDED.status, provenance=EXCLUDED.provenance, "
            "source=EXCLUDED.source",
            inter_rows,
        )
        cur.executemany(
            f'INSERT INTO "{S}".offshore_vehicle '
            "(vehicle_id, name, jurisdiction, company_type, status, "
            " provenance, source) VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (vehicle_id) DO UPDATE SET "
            "name=EXCLUDED.name, jurisdiction=EXCLUDED.jurisdiction, "
            "company_type=EXCLUDED.company_type, status=EXCLUDED.status, "
            "provenance=EXCLUDED.provenance, source=EXCLUDED.source",
            veh_rows,
        )
        cur.executemany(
            f'INSERT INTO "{S}".offshore_administration '
            "(intermediary_id, vehicle_id, relationship, provenance) "
            "VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (intermediary_id, vehicle_id) DO UPDATE SET "
            "relationship=EXCLUDED.relationship, "
            "provenance=EXCLUDED.provenance",
            adm_rows,
        )
        conn.commit()

        cur.execute(f'SELECT count(*) FROM "{S}".offshore_intermediary')
        n_inter = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".offshore_vehicle')
        n_veh = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".offshore_administration')
        n_adm = cur.fetchone()[0]

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    # Counted from the ledger, not from what was sent: an INSERT that silently
    # wrote nothing would otherwise be indistinguishable from success.
    #
    # Read through `stable_scalar`, because a query issued immediately after
    # the write can be served ahead of the index. This loader's FIRST run
    # reported 0 edges from 40 subjects over the same predicate in the same
    # breath — the index, not the data. See ccf/fluree.stable_scalar.
    n_subjects = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{P_IS_INTERMEDIARY_FOR}> ?o }}")
    n_edges = fluree.stable_scalar(
        f"SELECT (COUNT(?o) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{P_IS_INTERMEDIARY_FOR}> ?o }}")
    n_providers = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s a <{C_SERVICE_PROVIDER}> }}")

    print(f"\n  Postgres: intermediary {n_inter} · vehicle {n_veh} · "
          f"administration {n_adm}")
    print(f"  Fluree:   {n_edges} isIntermediaryFor edges from "
          f"{n_subjects} providers · {n_providers} typed ServiceProvider")
    print(f"  ledger now at t={fluree.ledger_t()} · "
          f"{fluree.count_triples():,} triples")

    failures = []
    if (n_inter, n_veh, n_adm) != (len(inter_rows), len(veh_rows), len(adm_rows)):
        failures.append(f"Postgres counts disagree with the artifact")
    if n_edges != len(adm_rows):
        failures.append(f"Fluree holds {n_edges} edges, artifact has "
                        f"{len(adm_rows)}")
    if n_providers != len(inter_rows):
        failures.append(f"{n_providers} nodes typed ServiceProvider, expected "
                        f"{len(inter_rows)} — explicit typing did not land")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  both stores match the artifact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
