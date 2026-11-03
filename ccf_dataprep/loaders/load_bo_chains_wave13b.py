#!/usr/bin/env python3
"""Wave 13b Task 8 — load beneficial-ownership chains and the second cycle.

Reads `sources/screening/wave13b_bo_chains.json`.

    Postgres  engineered_entity  125 rows  (119 holdcos + 6 cycle members)
              bo_chain            50 rows
              bo_chain_hop       169 rows
    Fluree    holdco + cycle nodes, `owns` hops, hasBeneficialOwner /
              isBeneficialOwnerOf, and one BeneficialOwnership node per chain
              carrying `fibo-be-le-lei:hasOwnershipPercentage`

## Why the percentage hangs on a reified node

`fibo-be-le-lei:hasOwnershipPercentage` is a real FIBO `owl:DatatypeProperty`
(verified 2026-08-22 at `BE/LegalEntities/LEIEntities.rdf:407`, range
`xsd:decimal`, *"the percentage ownership interest in the owned entity owned by
owning entity"*, adapted from the GLEIF LEI-CDF). A datatype property needs a
subject, and `A owns B` is an edge with no node to carry it — so each chain
gets a `fibo-be-oac-cown:BeneficialOwnership` node, a class bound since Wave 3
and, until now, never asserted.

The per-hop stakes stay in `bo_chain_hop`. Only the EFFECTIVE percentage
reaches the graph, because that is the number a traversal answers with.

## The existing cycle's edges are not rewritten

Wave 3 wrote `CYCLE-1`'s three `owns` edges and they are left exactly as they
are. This wave gives its members Postgres rows carrying the jurisdictions they
never had — the claim "spans jurisdictions" was previously unverifiable, since
the only evidence was a legal-form suffix inside a label. `CYCLE-2` is new in
full.

    uv run loaders/load_bo_chains_wave13b.py --dry-run
    uv run loaders/load_bo_chains_wave13b.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from ccf import fluree
from ccf.party_roles import with_ancestors
from ccf.views import ensure_views
from ccf.config import (
    EX,
    EX_EXTENSION_SCHEMA_NOTE,
    FLUREE_LEDGER_V2,
    PG_SCHEMA_V2,
    REPO_ROOT,
    assert_v2_schema,
    pg_connect,
)

S = PG_SCHEMA_V2
SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13b_bo_chains.json"
BATCH = 500

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
CMNS = "https://www.omg.org/spec/Commons/"
C_CORPORATION = f"{FIBO}BE/LegalEntities/CorporateBodies/Corporation"
C_ORGANIZATION = f"{CMNS}Organizations/Organization"
C_FORMAL_ORG = f"{CMNS}Organizations/FormalOrganization"
C_LEGAL_ENTITY = f"{CMNS}Organizations/LegalEntity"
C_LEGAL_PERSON = f"{CMNS}Organizations/LegalPerson"

C_BENEFICIAL_OWNERSHIP = f"{FIBO}BE/OwnershipAndControl/CorporateOwnership/BeneficialOwnership"
C_BENEFICIAL_OWNER = f"{FIBO}BE/OwnershipAndControl/CorporateOwnership/BeneficialOwner"
C_SIGNIFICANT_SHAREHOLDER = f"{FIBO}BE/OwnershipAndControl/CorporateControl/SignificantShareholder"
P_HAS_BENEFICIAL_OWNER = f"{FIBO}BE/OwnershipAndControl/CorporateOwnership/hasBeneficialOwner"
P_IS_BENEFICIAL_OWNER_OF = f"{FIBO}BE/OwnershipAndControl/CorporateOwnership/isBeneficialOwnerOf"
P_OWNS = f"{FIBO}FND/OwnershipAndControl/Ownership/owns"
P_OWNERSHIP_PCT = f"{FIBO}BE/LegalEntities/LEIEntities/hasOwnershipPercentage"

P_OWNERSHIP_IN = f"{EX}ownershipIn"
P_HELD_BY = f"{EX}heldBy"
P_PROVENANCE = f"{EX}provenance"
P_EDGE_PROVENANCE = f"{EX}edgeProvenance"
P_IS_FIBO_TERM = f"{EX}isFiboTerm"
P_SCHEMA_NOTE = f"{EX}schemaNote"

#: Corporation plus its whole chain. Previously a hand-written tuple that
#: stopped at LegalPerson, leaving every holdco unreachable by Party and Agent
#: (known-issues §62).
ORG_TYPES = with_ancestors(C_CORPORATION)

#: The statutory threshold most jurisdictions use. Read from `bo_threshold`
#: rather than written here — this name only documents which row is used.
DEFAULT_INTENT = "onboarding"

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".engineered_entity (
    entity_id    text PRIMARY KEY,
    name         text NOT NULL,
    jurisdiction text NOT NULL,   -- ISO 3166-1 alpha-2/3 as published
    country      text NOT NULL,
    kind         text NOT NULL,   -- holding_company | cycle_member
    cycle_group  text,
    provenance   text NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".bo_chain (
    chain_id             text     PRIMARY KEY,
    entity_id            text     NOT NULL,
    entity_kind          text     NOT NULL,
    person_key           text     NOT NULL
                         REFERENCES "{S}".person(person_key) ON DELETE CASCADE,
    depth                integer  NOT NULL,
    -- The product of the per-hop stakes. Recomputable from bo_chain_hop, and
    -- stored so a query can filter without a recursive join — the validator
    -- RECOMPUTES it rather than trusting it.
    effective_pct        numeric  NOT NULL,
    jurisdiction_path    text[]   NOT NULL,
    crosses_jurisdictions boolean NOT NULL,
    person_is_eu_resident boolean NOT NULL,
    provenance           text     NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".bo_chain_hop (
    chain_id   text    NOT NULL
               REFERENCES "{S}".bo_chain(chain_id) ON DELETE CASCADE,
    hop_index  integer NOT NULL,
    owner_id   text    NOT NULL,
    owner_kind text    NOT NULL,
    owned_id   text    NOT NULL,
    owned_kind text    NOT NULL,
    stake_pct  numeric NOT NULL,
    provenance text    NOT NULL,
    PRIMARY KEY (chain_id, hop_index)
);

CREATE INDEX IF NOT EXISTS bo_chain_depth_idx ON "{S}".bo_chain (depth);
CREATE INDEX IF NOT EXISTS bo_chain_person_idx ON "{S}".bo_chain (person_key);

"""


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def uri(local: str) -> str:
    return f"{EX}{local}"


def build_triples(doc: dict, threshold: float) -> list[str]:
    triples: list[str] = []

    for entity in doc["holdcos"] + doc["cycle_entities"]:
        node = uri(entity["entity_id"])
        for t in ORG_TYPES:
            triples.append(triple(node, RDF_TYPE, t))
        triples += [
            triple(node, RDFS_LABEL, entity["name"], literal=True),
            triple(node, P_PROVENANCE, entity["provenance"], literal=True),
        ]

    # Only the `owns` EDGE goes to Fluree. An earlier version also marked the
    # owner node with `ex:edgeProvenance`, which put a LITERAL on Person nodes
    # (hop 0's owner is always a person) and `validators/partition.py` failed
    # it, correctly — that is a node mark standing in for an edge mark, and the
    # hop's provenance is a `bo_chain_hop` column already.
    for hop in doc["hops"]:
        triples.append(triple(uri(hop["owner_id"]), P_OWNS,
                              uri(hop["owned_id"])))

    for edge in doc["cycle_edges"]:
        triples.append(triple(uri(edge["owner_id"]), P_OWNS,
                              uri(edge["owned_id"])))
        # Cycle members are entities, never persons, so the node-level
        # provenance mark Wave 3 established is safe here and keeps the two
        # cycles marked the same way.
        triples.append(triple(uri(edge["owner_id"]), P_EDGE_PROVENANCE,
                              edge["provenance"], literal=True))

    for i, chain in enumerate(doc["chains"], start=1):
        entity = uri(chain["entity_id"])
        person = uri(chain["person_key"])
        bo_node = uri(f"BO-{i:04d}")
        triples += [
            triple(entity, P_HAS_BENEFICIAL_OWNER, person),
            triple(person, P_IS_BENEFICIAL_OWNER_OF, entity),
            # Rule 7: no reasoner. A query for BeneficialOwner will not find a
            # node typed only Person, so the role is stated explicitly.
            triple(person, RDF_TYPE, C_BENEFICIAL_OWNER),
            triple(bo_node, RDF_TYPE, C_BENEFICIAL_OWNERSHIP),
            triple(bo_node, P_OWNERSHIP_IN, entity),
            triple(bo_node, P_HELD_BY, person),
            triple(bo_node, P_OWNERSHIP_PCT, str(chain["effective_pct"]),
                   literal=True),
            triple(bo_node, P_PROVENANCE, chain["provenance"], literal=True),
        ]
        # Significant only where the effective stake clears the LOADED
        # threshold — the row, not a constant in this file.
        if chain["effective_pct"] >= threshold:
            triples.append(triple(person, RDF_TYPE, C_SIGNIFICANT_SHAREHOLDER))

    for term in (P_OWNERSHIP_IN, P_HELD_BY):
        triples += [
            triple(term, P_IS_FIBO_TERM, "false", literal=True),
            triple(term, P_SCHEMA_NOTE, EX_EXTENSION_SCHEMA_NOTE, literal=True),
        ]
    return triples


def main() -> int:
    ap = argparse.ArgumentParser(description="Load BO chains and cycles")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(ARTIFACT.read_text())

    entity_rows = [
        (e["entity_id"], e["name"], e["jurisdiction"], e["country"],
         e["kind"], e.get("cycle_group"), e["provenance"])
        for e in doc["holdcos"] + doc["cycle_entities"]
    ]
    chain_rows = [
        (c["chain_id"], c["entity_id"], c["entity_kind"], c["person_key"],
         c["depth"], c["effective_pct"], c["jurisdiction_path"],
         c["crosses_jurisdictions"], c["person_is_eu_resident"],
         c["provenance"]) for c in doc["chains"]
    ]
    hop_rows = [
        (h["chain_id"], h["hop_index"], h["owner_id"], h["owner_kind"],
         h["owned_id"], h["owned_kind"], h["stake_pct"], h["provenance"])
        for h in doc["hops"]
    ]

    print(f"Wave 13b Task 8 — chains and cycles into {S} + Fluree\n")
    print(f"  engineered_entity   {len(entity_rows):>4}   "
          f"{dict(Counter(e[4] for e in entity_rows))}")
    print(f"  bo_chain            {len(chain_rows):>4}   depths "
          f"{dict(sorted(Counter(c[4] for c in chain_rows).items()))}")
    print(f"  bo_chain_hop        {len(hop_rows):>4}")

    if args.dry_run:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT threshold_pct FROM "{S}".bo_threshold '
                        "WHERE jurisdiction = 'GB' AND intent = %s",
                        (DEFAULT_INTENT,))
            row = cur.fetchone()
        print(f"  threshold (GB/{DEFAULT_INTENT}) {row[0] if row else 'MISSING'}")
        print("\n  [dry-run] nothing written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        sources = ensure_views(cur, S)

        # The threshold that decides SignificantShareholder comes from the
        # policy table, never from this file.
        cur.execute(f'SELECT threshold_pct FROM "{S}".bo_threshold '
                    "WHERE jurisdiction = 'GB' AND intent = %s",
                    (DEFAULT_INTENT,))
        row = cur.fetchone()
        if not row:
            print(f"  FAIL: no bo_threshold row for GB/{DEFAULT_INTENT}. "
                  f"Run loaders/load_policy_wave13b.py first.")
            return 1
        threshold = float(row[0])
        print(f"  threshold           {threshold}%  "
              f"(bo_threshold GB/{DEFAULT_INTENT}, read not hardcoded)")

        cur.executemany(
            f'INSERT INTO "{S}".engineered_entity '
            "(entity_id, name, jurisdiction, country, kind, cycle_group, "
            " provenance) VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (entity_id) DO UPDATE SET name=EXCLUDED.name, "
            "jurisdiction=EXCLUDED.jurisdiction, country=EXCLUDED.country, "
            "kind=EXCLUDED.kind, cycle_group=EXCLUDED.cycle_group, "
            "provenance=EXCLUDED.provenance",
            entity_rows,
        )
        cur.executemany(
            f'INSERT INTO "{S}".bo_chain '
            "(chain_id, entity_id, entity_kind, person_key, depth, "
            " effective_pct, jurisdiction_path, crosses_jurisdictions, "
            " person_is_eu_resident, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (chain_id) DO UPDATE SET entity_id=EXCLUDED.entity_id, "
            "entity_kind=EXCLUDED.entity_kind, person_key=EXCLUDED.person_key, "
            "depth=EXCLUDED.depth, effective_pct=EXCLUDED.effective_pct, "
            "jurisdiction_path=EXCLUDED.jurisdiction_path, "
            "crosses_jurisdictions=EXCLUDED.crosses_jurisdictions, "
            "person_is_eu_resident=EXCLUDED.person_is_eu_resident, "
            "provenance=EXCLUDED.provenance",
            chain_rows,
        )
        cur.executemany(
            f'INSERT INTO "{S}".bo_chain_hop '
            "(chain_id, hop_index, owner_id, owner_kind, owned_id, "
            " owned_kind, stake_pct, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (chain_id, hop_index) DO UPDATE SET "
            "owner_id=EXCLUDED.owner_id, owner_kind=EXCLUDED.owner_kind, "
            "owned_id=EXCLUDED.owned_id, owned_kind=EXCLUDED.owned_kind, "
            "stake_pct=EXCLUDED.stake_pct, provenance=EXCLUDED.provenance",
            hop_rows,
        )
        conn.commit()

        cur.execute(f'SELECT count(*) FROM "{S}".bo_chain')
        n_chains = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".bo_chain WHERE depth >= 5')
        n_deep = cur.fetchone()[0]
        cur.execute(f'SELECT count(DISTINCT entity_id) FROM "{S}".bo_chain '
                    "WHERE person_is_eu_resident")
        n_eu = cur.fetchone()[0]
        # Recomputed from the hops, not read back from `effective_pct`.
        cur.execute(f"""
            SELECT count(*) FROM (
              SELECT c.chain_id, c.effective_pct,
                     exp(sum(ln(h.stake_pct / 100.0))) * 100.0 AS recomputed
                FROM "{S}".bo_chain c
                JOIN "{S}".bo_chain_hop h USING (chain_id)
               GROUP BY c.chain_id, c.effective_pct) t
             WHERE abs(effective_pct - recomputed) > 0.01""")
        n_pct_drift = cur.fetchone()[0]

    triples = build_triples(doc, threshold)
    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    n_has_bo = fluree.stable_scalar(
        f"SELECT (COUNT(?o) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{P_HAS_BENEFICIAL_OWNER}> ?o }}")
    n_bo_nodes = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s a <{C_BENEFICIAL_OWNERSHIP}> }}")
    n_cycles_members = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?a) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?a <{P_OWNS}> ?b . ?b <{P_OWNS}> ?c . ?c <{P_OWNS}> ?a }}")
    n_sig = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s a <{C_SIGNIFICANT_SHAREHOLDER}> }}")

    print(f"\n  Postgres: bo_chain {n_chains} ({n_deep} at depth >= 5, "
          f"{n_eu} entities with an EU-resident owner)")
    print(f"            effective_pct rows disagreeing with their hops: "
          f"{n_pct_drift}")
    print(f"  Fluree:   {n_has_bo} hasBeneficialOwner · {n_bo_nodes} "
          f"BeneficialOwnership nodes · {n_sig} SignificantShareholder")
    print(f"            {n_cycles_members} nodes participate in a 3-cycle "
          f"(2 cycles x 3 members)")
    print(f"  jurisdiction view sources: {sources}")
    print(f"  ledger now at t={fluree.ledger_t()} · "
          f"{fluree.count_triples():,} triples")

    failures = []
    if n_chains != len(chain_rows):
        failures.append(f"{n_chains} chains loaded, expected {len(chain_rows)}")
    if n_deep < 3:
        failures.append(f"§F3: {n_deep} chains at depth >= 5, floor 3")
    if n_eu < 2:
        failures.append(f"§F7: {n_eu} entities with an EU-resident owner, floor 2")
    if n_pct_drift:
        failures.append(f"{n_pct_drift} chain(s) carry an effective_pct that "
                        f"disagrees with the product of their own hops")
    if n_has_bo != len(chain_rows):
        failures.append(f"{n_has_bo} hasBeneficialOwner edges, expected "
                        f"{len(chain_rows)}")
    if n_cycles_members < 6:
        failures.append(f"only {n_cycles_members} nodes in a 3-cycle; two "
                        f"independent cycles need 6")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  both stores match the artifact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
