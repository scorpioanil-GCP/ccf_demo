#!/usr/bin/env python3
import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch, Json

HOST = os.getenv("PGHOST", "192.168.4.76")
PORT = int(os.getenv("PGPORT", "5432"))
DBNAME = os.getenv("PGDATABASE", "fibo")
USER = os.getenv("PGUSER", "postgres")
PASSWORD = os.getenv("PGPASSWORD", "CHANGE_ME")

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

def main():
    entities = load_jsonl(ENTITIES)
    rels = load_jsonl(RELS)

    conn = psycopg2.connect(
        host=HOST, port=PORT, dbname=DBNAME, user=USER, password=PASSWORD
    )
    conn.autocommit = True
    cur = conn.cursor()

    # schema
    cur.execute("DROP TABLE IF EXISTS relationships")
    cur.execute("DROP TABLE IF EXISTS entities")

    cur.execute(
        """
        CREATE TABLE entities (
            id            TEXT PRIMARY KEY,
            name          TEXT,
            label         TEXT,
            types         TEXT[],
            lei           TEXT,
            legal_name    TEXT,
            jurisdiction  TEXT,
            entity_status TEXT,
            client_type   TEXT,
            risk_rating   TEXT,
            kyc_status    TEXT,
            onboarding_date TEXT,
            full_name     TEXT,
            nationality   TEXT,
            date_of_birth TEXT,
            role          TEXT,
            ownership_percent TEXT,
            attrs         JSONB,
            source        TEXT DEFAULT 'postgres-mirror'
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE relationships (
            id     TEXT PRIMARY KEY,
            from_id TEXT REFERENCES entities(id),
            to_id   TEXT REFERENCES entities(id),
            type    TEXT NOT NULL,
            source  TEXT DEFAULT 'postgres-mirror',
            -- Per-EDGE ownership percentage. Nullable on purpose: only
            -- hasOwnershipInterestIn edges carry one. The original estate
            -- held this as a column on the owning Party, which made every
            -- ownership chain one hop and left multi-hop UBO unanswerable.
            ownership_percent NUMERIC
        )
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_entities_label ON entities(label)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_entities_lei ON entities(lei)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_entities_client_type ON entities(client_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rel_to ON relationships(to_id)")

    entity_rows = []
    for e in entities:
        uri = e.get("id") or e.get("_id")
        entity_rows.append(
            (
                uri,
                uri.rsplit("/", 1)[-1] if uri else None,
                e.get("label"),
                e.get("types") or [],
                e.get("lei"),
                e.get("legalName"),
                e.get("jurisdiction"),
                e.get("entityStatus"),
                e.get("clientType"),
                e.get("riskRating"),
                e.get("kycStatus"),
                e.get("onboardingDate"),
                e.get("fullName"),
                e.get("nationality"),
                e.get("dateOfBirth"),
                e.get("role"),
                e.get("ownershipPercent"),
                Json(e.get("attrs") or {}),
                "postgres-mirror",
            )
        )

    execute_batch(
        cur,
        """
        INSERT INTO entities (
            id, name, label, types, lei, legal_name, jurisdiction,
            entity_status, client_type, risk_rating, kyc_status,
            onboarding_date, full_name, nationality, date_of_birth,
            role, ownership_percent, attrs, source
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,
            %s,%s,%s,%s,
            %s,%s,%s,%s
        )
        """,
        entity_rows,
    )

    rel_rows = []
    for r in rels:
        rel_rows.append(
            (
                r.get("_id"),
                r.get("from"),
                r.get("to"),
                r.get("type"),
                "postgres-mirror",
                r.get("ownershipPercent"),
            )
        )

    execute_batch(
        cur,
        """
        INSERT INTO relationships (id, from_id, to_id, type, source, ownership_percent)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        rel_rows,
    )

    cur.execute("SELECT COUNT(*) FROM entities")
    n_entities = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM relationships")
    n_rels = cur.fetchone()[0]
    print(f"Loaded {n_entities} entities, {n_rels} relationships")

    print("\nOwnership:")
    cur.execute(
        """
        SELECT o.label, c.label
        FROM relationships r
        JOIN entities o ON o.id = r.from_id
        JOIN entities c ON c.id = r.to_id
        WHERE r.type = 'hasOwnershipInterestIn'
        ORDER BY o.label
        """
    )
    for owner, company in cur.fetchall():
        print(f"  {owner} -> {company}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
