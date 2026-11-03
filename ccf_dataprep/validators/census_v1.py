#!/usr/bin/env python3
"""Read-only census of what currently exists on db1 (192.168.4.76).

Answers "what is the v1 hello-world load, concretely?" before any v2 work
touches these stores. Issues no writes: SELECT/find/MATCH-count only.

Run: uv run validators/census_v1.py
"""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

FLUREE_URL = os.getenv("FLUREE_URL", "http://192.168.4.76:8092")
FLUREE_LEDGER = os.getenv("FLUREE_LEDGER", "fibo:main")


def rule(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


def fluree() -> None:
    rule("FLUREE")
    try:
        health = requests.get(f"{FLUREE_URL}/health", timeout=8).json()
        print(f"  version: {health.get('version')}  status: {health.get('status')}")
    except Exception as exc:
        print(f"  health check failed: {exc}")

    # Count triples and distinct subjects by rdf:type, per the v1 endpoint form.
    queries = {
        "distinct subjects": "SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s ?p ?o }",
        "total triples": "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }",
    }
    for label, q in queries.items():
        try:
            r = requests.post(
                f"{FLUREE_URL}/v1/fluree/query",
                headers={"Content-Type": "application/sparql-query"},
                data=f"FROM <{FLUREE_LEDGER}> {q}" if "FROM" not in q else q,
                timeout=30,
            )
            print(f"  {label}: HTTP {r.status_code} -> {r.text[:200]}")
        except Exception as exc:
            print(f"  {label}: FAILED {exc}")

    # Types present — the real question: what is loaded, and is it typed explicitly?
    type_q = """
    SELECT ?type (COUNT(?s) AS ?n)
    WHERE { ?s a ?type }
    GROUP BY ?type
    ORDER BY DESC(?n)
    """
    try:
        r = requests.post(
            f"{FLUREE_URL}/v1/fluree/query",
            headers={"Content-Type": "application/sparql-query"},
            data=type_q,
            timeout=30,
        )
        print(f"  types: HTTP {r.status_code}")
        print(f"    {r.text[:1500]}")
    except Exception as exc:
        print(f"  types: FAILED {exc}")


def postgres() -> None:
    rule("POSTGRES")
    try:
        import psycopg
    except ImportError:
        print("  psycopg not installed")
        return
    try:
        with psycopg.connect(
            host=os.getenv("PGHOST"),
            port=os.getenv("PGPORT"),
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            connect_timeout=8,
        ) as conn, conn.cursor() as cur:
            cur.execute("SELECT version()")
            print(f"  {cur.fetchone()[0][:70]}")

            cur.execute("""
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schemaname, tablename
            """)
            tables = cur.fetchall()
            if not tables:
                print("  no user tables")
                return
            print(f"  {len(tables)} user table(s):")
            for schema, table in tables:
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                    print(f"    {schema}.{table}: {cur.fetchone()[0]} rows")
                except Exception as exc:
                    print(f"    {schema}.{table}: count failed ({exc})")
    except Exception as exc:
        print(f"  connection FAILED: {exc}")


def mongo() -> None:
    rule("MONGODB")
    try:
        from pymongo import MongoClient
    except ImportError:
        print("  pymongo not installed")
        return
    try:
        client = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=8000)
        print(f"  server: {client.server_info()['version']}")
        for dbname in sorted(client.list_database_names()):
            if dbname in ("admin", "config", "local"):
                continue
            db = client[dbname]
            colls = sorted(db.list_collection_names())
            marker = "  <- target" if dbname == os.getenv("MONGO_DB") else ""
            print(f"  db '{dbname}'{marker}: {len(colls)} collection(s)")
            for coll in colls:
                print(f"    {coll}: {db[coll].estimated_document_count()} docs")
    except Exception as exc:
        print(f"  connection FAILED: {exc}")


def neo4j_census() -> None:
    rule("NEO4J")
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("  neo4j driver not installed")
        return
    try:
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://192.168.4.76:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD")),
            connection_timeout=8,
        )
        with driver.session() as session:
            n = session.run("MATCH (n) RETURN count(n) AS n").single()["n"]
            r = session.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
            print(f"  {n} nodes, {r} relationships")
            labels = session.run(
                "MATCH (n) UNWIND labels(n) AS l "
                "RETURN l, count(*) AS n ORDER BY n DESC"
            )
            for rec in labels:
                print(f"    :{rec['l']} -> {rec['n']}")
            rels = session.run(
                "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS n ORDER BY n DESC"
            )
            for rec in rels:
                print(f"    -[:{rec['t']}]-> {rec['n']}")
        driver.close()
    except Exception as exc:
        print(f"  connection FAILED: {exc}")


def sqlite_census() -> None:
    rule("SQLITE (departmental)")
    import sqlite3
    from pathlib import Path

    path = Path(os.getenv("SQLITE_PATH", "./data/departmental.sqlite"))
    print(f"  path: {path}")
    if not path.exists():
        print("  does not exist yet — Wave 0 creates it")
        return
    with sqlite3.connect(path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        print(f"  {len(tables)} table(s)")
        for (name,) in tables:
            count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            print(f"    {name}: {count} rows")


if __name__ == "__main__":
    print("READ-ONLY CENSUS — no writes are issued by this script")
    fluree()
    postgres()
    mongo()
    neo4j_census()
    sqlite_census()
    print("\nDone. Nothing was modified.")
