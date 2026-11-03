#!/usr/bin/env python3
import json
import os
from pathlib import Path
from neo4j import GraphDatabase

# Prefer env vars; fall back to placeholders you can edit
URI = os.getenv("NEO4J_URI", "bolt://192.168.4.76:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "CHANGE_ME")

ENTITIES = Path("mongo-entities.json")
RELS = Path("mongo-relationships.json")

def load_jsonl(path: Path):
    docs = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs

def short_name(uri: str) -> str:
    return uri.rsplit("/", 1)[-1] if uri else uri

def main():
    entities = load_jsonl(ENTITIES)
    rels = load_jsonl(RELS)

    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    driver.verify_connectivity()
    print(f"Connected to {URI}")

    with driver.session() as session:
        # optional clean slate for this demo graph
        session.run("MATCH (n:KGEntity) DETACH DELETE n")

        # constraints / indexes
        session.run(
            "CREATE CONSTRAINT kg_entity_id IF NOT EXISTS "
            "FOR (e:KGEntity) REQUIRE e.id IS UNIQUE"
        )
        session.run(
            "CREATE INDEX kg_entity_label IF NOT EXISTS "
            "FOR (e:KGEntity) ON (e.label)"
        )
        session.run(
            "CREATE INDEX kg_entity_lei IF NOT EXISTS "
            "FOR (e:KGEntity) ON (e.lei)"
        )

        # load entities
        for e in entities:
            labels = ["KGEntity"]
            for t in e.get("types") or []:
                # sanitize label for Neo4j
                safe = "".join(ch if ch.isalnum() else "_" for ch in t)
                if safe and safe not in labels:
                    labels.append(safe)

            props = {
                "id": e.get("id") or e.get("_id"),
                "name": short_name(e.get("id") or e.get("_id")),
                "label": e.get("label"),
                "lei": e.get("lei"),
                "legalName": e.get("legalName"),
                "jurisdiction": e.get("jurisdiction"),
                "entityStatus": e.get("entityStatus"),
                "clientType": e.get("clientType"),
                "riskRating": e.get("riskRating"),
                "kycStatus": e.get("kycStatus"),
                "onboardingDate": e.get("onboardingDate"),
                "fullName": e.get("fullName"),
                "nationality": e.get("nationality"),
                "dateOfBirth": e.get("dateOfBirth"),
                "role": e.get("role"),
                "ownershipPercent": e.get("ownershipPercent"),
                "source": "neo4j-mirror",
            }
            # drop None values
            props = {k: v for k, v in props.items() if v is not None}

            label_cypher = ":".join(labels)
            session.run(
                f"MERGE (n:{label_cypher} {{id: $id}}) SET n += $props",
                id=props["id"],
                props=props,
            )

        print(f"Loaded {len(entities)} entities")

        # load relationships
        rel_map = {
            "hasOwnershipInterestIn": "HAS_OWNERSHIP_INTEREST_IN",
            "hasControllingInterestIn": "HAS_CONTROLLING_INTEREST_IN",
            "isRelatedTo": "IS_RELATED_TO",
        }

        for r in rels:
            rel_type = rel_map.get(r["type"], r["type"].upper())
            session.run(
                f"""
                MATCH (a:KGEntity {{id: $from_id}})
                MATCH (b:KGEntity {{id: $to_id}})
                MERGE (a)-[rel:{rel_type}]->(b)
                SET rel.source = 'neo4j-mirror',
                    rel.type = $orig_type,
                    rel.ownershipPercent = $pct
                """,
                from_id=r["from"],
                to_id=r["to"],
                orig_type=r["type"],
                # Per-EDGE ownership percentage. The original estate carried
                # ownershipPercent as an attribute of the owning Party, which
                # made every ownership chain exactly one hop and left "who
                # ultimately owns X?" unanswerable. Passing None is correct and
                # intended for non-ownership edges: Neo4j removes a property
                # set to null, so isRelatedTo edges simply carry none.
                pct=r.get("ownershipPercent"),
            )

        print(f"Loaded {len(rels)} relationships")

        # verify
        n_count = session.run("MATCH (n:KGEntity) RETURN count(n) AS c").single()["c"]
        r_count = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        print(f"Verify: {n_count} nodes, {r_count} relationships")

        print("\nSample ownership:")
        result = session.run(
            """
            MATCH (o:KGEntity)-[r:HAS_OWNERSHIP_INTEREST_IN]->(c:KGEntity)
            RETURN o.label AS owner, c.label AS company
            ORDER BY owner
            """
        )
        for row in result:
            print(f"  {row['owner']} -> {row['company']}")

    driver.close()

if __name__ == "__main__":
    main()
