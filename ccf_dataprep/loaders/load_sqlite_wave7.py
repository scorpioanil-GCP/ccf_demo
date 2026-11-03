#!/usr/bin/env python3
"""Wave 7 — populate the departmental SQLite store.

This store holds four things CLAUDE.md names, and the *reason* they live here
rather than in Postgres is the whole point of including SQLite at all:

    control-room restricted list   the enterprise-critical policy input
    covenant tracker               compliance's own working view
    banker prospect notes          coverage's local workbook
    risk limit workbook            a spreadsheet-shaped artefact

Per `mnpi-wall-enforcement` §C: a control-room restricted list is exactly the
kind of artefact that in real institutions lives in a small, locally-maintained
system owned by compliance — not the enterprise data platform. Placing it here
makes the integration story honest, because the fabric must reach a departmental
system to enforce an enterprise-critical policy, and must do so **before
anything else runs**. A demonstration where every signal sits in a
well-governed enterprise store misrepresents what integration looks like.

These tables deliberately do NOT hold entity attributes, facilities, or edges.
The partition validator asserts that: a departmental store that accumulates
enterprise data has stopped being departmental.

    uv run loaders/load_sqlite_wave7.py --dry-run
    uv run loaders/load_sqlite_wave7.py

Idempotent.
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from datetime import date, timedelta

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, SQLITE_PATH, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
SEED = 20260817
SCHEMA_VERSION = 1

DDL = """
-- The enterprise-critical policy input, owned by compliance, held locally.
CREATE TABLE IF NOT EXISTS restricted_list (
    lei              TEXT PRIMARY KEY,
    legal_name       TEXT NOT NULL,
    ticker           TEXT,
    restriction_type TEXT NOT NULL,
    added_date       TEXT NOT NULL,
    removed_date     TEXT,
    added_by         TEXT NOT NULL,
    reason_code      TEXT NOT NULL,
    provenance       TEXT NOT NULL
);

-- Compliance's own working view of covenant testing. Deliberately NOT the
-- authoritative covenant record -- that is Fluree's. This is what a
-- departmental team actually keeps, including its own commentary.
CREATE TABLE IF NOT EXISTS covenant_tracker (
    facility_id      TEXT NOT NULL,
    covenant_type    TEXT NOT NULL,
    next_test_date   TEXT,
    last_test_result TEXT,
    watch_flag       INTEGER NOT NULL DEFAULT 0,
    analyst_note     TEXT,
    updated_at       TEXT NOT NULL,
    provenance       TEXT NOT NULL,
    PRIMARY KEY (facility_id, covenant_type)
);

-- Coverage's local workbook. No enterprise system owns these.
CREATE TABLE IF NOT EXISTS prospect_note (
    note_id       TEXT PRIMARY KEY,
    lei           TEXT,
    prospect_name TEXT NOT NULL,
    banker        TEXT NOT NULL,
    note          TEXT NOT NULL,
    priority      TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    provenance    TEXT NOT NULL
);

-- A spreadsheet-shaped artefact, which is exactly why it is here.
CREATE TABLE IF NOT EXISTS risk_limit_workbook (
    limit_id     TEXT PRIMARY KEY,
    scope        TEXT NOT NULL,
    scope_value  TEXT NOT NULL,
    limit_type   TEXT NOT NULL,
    limit_amount REAL,
    utilisation  REAL,
    owner        TEXT NOT NULL,
    reviewed_at  TEXT NOT NULL,
    provenance   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_restricted_active
    ON restricted_list (removed_date) WHERE removed_date IS NULL;
CREATE INDEX IF NOT EXISTS idx_tracker_watch
    ON covenant_tracker (watch_flag) WHERE watch_flag = 1;
"""

BANKERS = ["A. Okonkwo", "M. Lindqvist", "R. Bhattacharya", "T. Nakamura"]
NOTES = [
    "Introduced at sector conference; receptive to a refinancing conversation "
    "ahead of the 2027 maturity wall.",
    "CFO transition expected; hold outreach until the successor is announced.",
    "Existing lender group is tight. Angle is an accordion rather than a new "
    "facility.",
    "Prior mandate lost on price. Revisit only with a structuring idea.",
    "Sponsor-owned; decision sits with the sponsor, not management.",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rng = random.Random(SEED)
    today = date.today()
    layer = json.loads((SCREEN / "mnpi_layer.json").read_text())

    # Covenant tracker draws facility/covenant pairs from the enterprise
    # record but keeps only compliance's own columns -- no thresholds, no
    # temporal assertions. Duplicating those would breach single-writer.
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT f.facility_id, cb.covenant_type
            FROM "{PG_SCHEMA_V2}".facility f
            LEFT JOIN "{PG_SCHEMA_V2}".covenant_breach cb
                   ON cb.facility_id = f.facility_id
            ORDER BY f.facility_id LIMIT 60
        """)
        pairs = [(r[0], r[1] or "leverage") for r in cur.fetchall()]
        cur.execute(f"""
            SELECT e.lei, e.legal_name FROM "{PG_SCHEMA_V2}".legal_entity e
            WHERE e.is_anchor ORDER BY e.lei LIMIT 18
        """)
        entities = cur.fetchall()

    tracker_rows = []
    seen: set[tuple] = set()
    for facility_id, covenant_type in pairs:
        if (facility_id, covenant_type) in seen:
            continue
        seen.add((facility_id, covenant_type))
        watch = 1 if rng.random() < 0.25 else 0
        tracker_rows.append((
            facility_id, covenant_type,
            (today + timedelta(days=rng.randint(5, 90))).isoformat(),
            rng.choice(["compliant", "compliant", "compliant", "cured"]),
            watch,
            ("Headroom narrowing; moved to quarterly monitoring."
             if watch else None),
            today.isoformat(),
            "synthetic — internal",
        ))

    prospect_rows = [
        (f"PN-{i:04d}", lei, name, rng.choice(BANKERS),
         NOTES[i % len(NOTES)],
         rng.choice(["high", "medium", "medium", "low"]),
         (today - timedelta(days=rng.randint(1, 200))).isoformat(),
         "synthetic — internal")
        for i, (lei, name) in enumerate(entities)
    ]

    limit_rows = []
    for i, (lei, name) in enumerate(entities[:12]):
        amount = rng.randrange(50_000_000, 900_000_000, 25_000_000)
        limit_rows.append((
            f"LIM-{i:04d}", "obligor", lei, "single-name exposure",
            float(amount), round(rng.uniform(0.15, 0.98), 3),
            "credit-risk", today.isoformat(), "synthetic — internal",
        ))
    for i, sector in enumerate(["REIT", "industrials", "technology", "energy"]):
        amount = rng.randrange(1_000_000_000, 5_000_000_000, 100_000_000)
        limit_rows.append((
            f"LIM-S{i:03d}", "sector", sector, "sector concentration",
            float(amount), round(rng.uniform(0.3, 0.9), 3),
            "credit-risk", today.isoformat(), "synthetic — internal",
        ))

    restricted = layer["restricted_list"]

    print(f"Wave 7 — SQLite departmental store\n")
    print(f"  path                 {SQLITE_PATH}")
    print(f"  restricted_list      {len(restricted):>4}   (§F floor 3)")
    print(f"  covenant_tracker     {len(tracker_rows):>4}")
    print(f"  prospect_note        {len(prospect_rows):>4}")
    print(f"  risk_limit_workbook  {len(limit_rows):>4}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.executescript(DDL)
        conn.executemany(
            "INSERT INTO restricted_list "
            "(lei, legal_name, ticker, restriction_type, added_date, "
            " removed_date, added_by, reason_code, provenance) "
            "VALUES (?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(lei) DO UPDATE SET "
            "restriction_type=excluded.restriction_type, "
            "removed_date=excluded.removed_date",
            [(r["lei"], r["legal_name"], r["ticker"], r["restriction_type"],
              r["added_date"], r["removed_date"], r["added_by"],
              r["reason_code"], r["provenance"]) for r in restricted],
        )
        conn.executemany(
            "INSERT INTO covenant_tracker "
            "(facility_id, covenant_type, next_test_date, last_test_result, "
            " watch_flag, analyst_note, updated_at, provenance) "
            "VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(facility_id, covenant_type) DO UPDATE SET "
            "next_test_date=excluded.next_test_date, "
            "updated_at=excluded.updated_at",
            tracker_rows,
        )
        conn.executemany(
            "INSERT INTO prospect_note "
            "(note_id, lei, prospect_name, banker, note, priority, "
            " created_at, provenance) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(note_id) DO UPDATE SET note=excluded.note",
            prospect_rows,
        )
        conn.executemany(
            "INSERT INTO risk_limit_workbook "
            "(limit_id, scope, scope_value, limit_type, limit_amount, "
            " utilisation, owner, reviewed_at, provenance) "
            "VALUES (?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(limit_id) DO UPDATE SET "
            "utilisation=excluded.utilisation, reviewed_at=excluded.reviewed_at",
            limit_rows,
        )
        conn.execute(
            "INSERT INTO _schema_meta (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=excluded.updated_at",
            ("schema_version", str(SCHEMA_VERSION), today.isoformat()),
        )
        conn.execute(
            "INSERT INTO _schema_meta (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=excluded.updated_at",
            ("wave", "7 — departmental tables populated", today.isoformat()),
        )

        counts = {
            name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in ("restricted_list", "covenant_tracker",
                         "prospect_note", "risk_limit_workbook")
        }
    print(f"\n  loaded: {counts}")
    print(f"  active restrictions: "
          f"{sum(1 for r in restricted if not r['removed_date'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
