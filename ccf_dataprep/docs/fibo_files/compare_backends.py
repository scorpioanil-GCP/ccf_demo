#!/usr/bin/env python3
"""
Compare the same logical query across Fluree, MongoDB, Neo4j, and PostgreSQL.
Default query: ownership relationships (owner -> company).
"""

from __future__ import annotations

import os
import sys
from typing import Any

import requests
from pymongo import MongoClient
from neo4j import GraphDatabase
import psycopg2
from tabulate import tabulate

# ---------------------------------------------------------------------------
# Connection settings (override with env vars)
# ---------------------------------------------------------------------------
FLUREE_URL = os.getenv("FLUREE_URL", "http://192.168.4.76:8090")
FLUREE_LEDGER = os.getenv("FLUREE_LEDGER", "fibo:main")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://192.168.4.76:27017")
MONGO_DB = os.getenv("MONGO_DB", "fibo")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.4.76:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

PGHOST = os.getenv("PGHOST", "192.168.4.76")
PGPORT = int(os.getenv("PGPORT", "5432"))
PGDATABASE = os.getenv("PGDATABASE", "parkavedb")
PGUSER = os.getenv("PGUSER", "parkave")
PGPASSWORD = os.getenv("PGPASSWORD", "")


# ---------------------------------------------------------------------------
# Backend queries — each returns list[tuple[str, str]] of (owner, company)
# ---------------------------------------------------------------------------

def query_fluree() -> list[tuple[str, str]]:
    sparql = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX fibo-be-oac-cown: <https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Ownership/>

    SELECT ?ownerLabel ?companyLabel
    FROM <{FLUREE_LEDGER}>
    WHERE {{
      ?owner fibo-be-oac-cown:hasOwnershipInterestIn ?company .
      OPTIONAL {{ ?owner rdfs:label ?ownerLabel }}
      OPTIONAL {{ ?company rdfs:label ?companyLabel }}
    }}
    ORDER BY ?ownerLabel
    """
    r = requests.post(
        f"{FLUREE_URL}/v1/fluree/query",
        headers={"Content-Type": "application/sparql-query"},
        data=sparql,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    rows = []
    for b in data.get("results", {}).get("bindings", []):
        owner = b.get("ownerLabel", {}).get("value", "")
        company = b.get("companyLabel", {}).get("value", "")
        rows.append((owner, company))
    return rows


def query_mongo() -> list[tuple[str, str]]:
    db = MongoClient(MONGO_URI)[MONGO_DB]
    rows = []
    for rel in db.relationships.find({"type": "hasOwnershipInterestIn"}):
        owner = db.entities.find_one({"_id": rel["from"]}, {"label": 1}) or {}
        company = db.entities.find_one({"_id": rel["to"]}, {"label": 1}) or {}
        rows.append((owner.get("label", ""), company.get("label", "")))
    rows.sort(key=lambda x: (x[0], x[1]))
    return rows


def query_neo4j() -> list[tuple[str, str]]:
    if not NEO4J_PASSWORD:
        raise RuntimeError("Set NEO4J_PASSWORD")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    rows = []
    with driver.session() as session:
        result = session.run(
            """
            MATCH (o:KGEntity)-[:HAS_OWNERSHIP_INTEREST_IN]->(c:KGEntity)
            RETURN o.label AS owner, c.label AS company
            ORDER BY owner, company
            """
        )
        for rec in result:
            rows.append((rec["owner"] or "", rec["company"] or ""))
    driver.close()
    return rows


def query_postgres() -> list[tuple[str, str]]:
    if not PGPASSWORD:
        # allow empty password only if explicitly set to empty and user wants it
        pass
    conn = psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT o.label, c.label
        FROM relationships r
        JOIN entities o ON o.id = r.from_id
        JOIN entities c ON c.id = r.to_id
        WHERE r.type = 'hasOwnershipInterestIn'
        ORDER BY o.label, c.label
        """
    )
    rows = [(a or "", b or "") for a, b in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Compare + display
# ---------------------------------------------------------------------------

def normalize(rows: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return sorted({(o.strip(), c.strip()) for o, c in rows if o or c})


def main() -> int:
    backends = [
        ("Fluree", query_fluree),
        ("MongoDB", query_mongo),
        ("Neo4j", query_neo4j),
        ("PostgreSQL", query_postgres),
    ]

    results: dict[str, list[tuple[str, str]]] = {}
    errors: dict[str, str] = {}

    print("Running ownership query on all backends...\n")

    for name, fn in backends:
        try:
            rows = normalize(fn())
            results[name] = rows
            print(f"  {name}: {len(rows)} rows")
        except Exception as exc:  # noqa: BLE001
            errors[name] = str(exc)
            results[name] = []
            print(f"  {name}: ERROR — {exc}")

    # Side-by-side style table: one row per backend result set listing
    print("\n=== Ownership results by backend ===\n")
    for name, rows in results.items():
        print(f"--- {name} ---")
        if name in errors:
            print(f"  (failed: {errors[name]})")
        elif not rows:
            print("  (no rows)")
        else:
            print(tabulate(rows, headers=["Owner", "Company"], tablefmt="github"))
        print()

    # Unified comparison matrix
    all_pairs = sorted({pair for rows in results.values() for pair in rows})
    if all_pairs:
        matrix = []
        for owner, company in all_pairs:
            matrix.append(
                [
                    owner,
                    company,
                    "Y" if (owner, company) in results.get("Fluree", []) else "",
                    "Y" if (owner, company) in results.get("MongoDB", []) else "",
                    "Y" if (owner, company) in results.get("Neo4j", []) else "",
                    "Y" if (owner, company) in results.get("PostgreSQL", []) else "",
                ]
            )
        print("=== Presence matrix (Y = backend returned this pair) ===\n")
        print(
            tabulate(
                matrix,
                headers=["Owner", "Company", "Fluree", "MongoDB", "Neo4j", "PostgreSQL"],
                tablefmt="github",
            )
        )

    if errors:
        print("\nSome backends failed. Check credentials/env vars.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
