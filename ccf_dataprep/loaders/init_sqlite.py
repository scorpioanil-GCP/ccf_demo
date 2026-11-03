#!/usr/bin/env python3
"""Create the departmental SQLite store.

Wave 0 creates the file and its provenance table only. The substantive
tables — control-room restricted list, covenant tracker, banker prospect
notes, risk limit workbook — land in Wave 7, once their specs have been
read. Creating empty tables now would assert a schema nobody has verified.

Idempotent: safe to re-run.

Run: uv run loaders/init_sqlite.py
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone

from ccf.config import SQLITE_PATH

SCHEMA_VERSION = 0


def main() -> int:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    existed = SQLITE_PATH.exists()

    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _schema_meta (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
            """
        )
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.executemany(
            "INSERT INTO _schema_meta (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=excluded.updated_at",
            [
                ("schema_version", str(SCHEMA_VERSION), now),
                ("purpose", "departmental store — restricted list, trackers, workbooks", now),
                ("owns", "P (policy) elements local to compliance and coverage teams", now),
                ("wave", "0 — file created; substantive tables land in Wave 7", now),
            ],
        )

    verb = "verified" if existed else "created"
    print(f"SQLite departmental store {verb}: {SQLITE_PATH}")
    with sqlite3.connect(SQLITE_PATH) as conn:
        rows = conn.execute(
            "SELECT key, value FROM _schema_meta ORDER BY key"
        ).fetchall()
    for key, value in rows:
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
