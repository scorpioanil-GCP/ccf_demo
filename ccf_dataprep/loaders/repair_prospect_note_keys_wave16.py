#!/usr/bin/env python3
"""Wave 16 — give the departmental notes a key that joins.

`prospect_note.banker` was a display name. Three of its four values are absent
from the Postgres roster entirely and the fourth matches four bankers, because
the roster carries 40 rows over 32 distinct names. Name is not an identity.

The repair assigns a real `banker_id` and KEEPS the original string in
`banker_display`, so the mapping stays auditable rather than being overwritten
by the thing that replaced it.

Assignment is deterministic (sorted note_id, round-robin over the coverage
bankers who actually cover that note's LEI), so a rerun produces the same
mapping. There is exactly one tier: if no banker covers the note's LEI, the
note keeps a NULL `banker_id` and is REPORTED -- never silently assigned,
because falling back to some other banker for that entity would assert a
coverage relationship that does not exist.

    uv run loaders/repair_prospect_note_keys_wave16.py --dry-run
    uv run loaders/repair_prospect_note_keys_wave16.py
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, assert_v2_schema, pg_connect

DB = REPO_ROOT / "data" / "departmental.sqlite"


def _candidate_index(note_id: str, n_candidates: int) -> int:
    """Deterministic index into a note's LEI's candidate banker list, keyed
    to the note's OWN id -- never to its position in a query result.

    FINAL FIX WAVE, item 9. The original `candidates[i % len(candidates)]`
    used `i`, the row's position in `SELECT ... ORDER BY note_id` over ALL
    notes in the table, including every other wave's. A future note whose
    id sorts before an existing one (e.g. a new wave using a different
    prefix) shifts every `i` after it, silently reassigning `banker_id` for
    every note from that point on -- this project's positional-identity
    defect class, seen four times before this one. Hashing the note's own
    id makes the assignment immune to any other row's existence, insertion,
    or deletion: two runs over the SAME notes produce the SAME assignment
    regardless of what else is in the table or what order it comes back in.
    """
    digest = hashlib.sha256(note_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % n_candidates


def coverage_map() -> dict[str, list[str]]:
    """lei -> banker_ids covering it, primary first then stable by id."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT lei, banker_id, is_primary FROM "{S}".coverage_assignment '
            "ORDER BY lei, is_primary DESC, banker_id"
        )
        out: dict[str, list[str]] = {}
        for lei, banker_id, _primary in cur.fetchall():
            out.setdefault(lei, []).append(banker_id)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_v2_schema(S)
    cov = coverage_map()

    con = sqlite3.connect(DB)
    cols = {r[1] for r in con.execute("PRAGMA table_info(prospect_note)")}
    if "banker_id" not in cols:
        con.execute("ALTER TABLE prospect_note ADD COLUMN banker_id TEXT")
    if "banker_display" not in cols:
        con.execute("ALTER TABLE prospect_note ADD COLUMN banker_display TEXT")

    rows = con.execute(
        "SELECT note_id, lei, banker FROM prospect_note ORDER BY note_id"
    ).fetchall()

    assigned, unassigned = [], []
    for note_id, lei, banker in rows:
        candidates = cov.get(lei or "", [])
        if candidates:
            idx = _candidate_index(note_id, len(candidates))
            assigned.append((candidates[idx], banker, note_id))
        else:
            unassigned.append(note_id)

    print(f"Wave 16 — re-key prospect_note to banker_id\n")
    print(f"  notes                {len(rows):>5}")
    print(f"  resolved to a banker {len(assigned):>5}")
    print(f"  NO coverage for LEI  {len(unassigned):>5}  {unassigned[:5]}")

    if unassigned:
        print("\n  Those notes keep a NULL banker_id. Assigning them a banker "
              "would invent a coverage relationship that does not exist.")

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    con.executemany(
        "UPDATE prospect_note SET banker_id = ?, banker_display = ? "
        "WHERE note_id = ?",
        assigned,
    )
    con.commit()

    still = con.execute(
        "SELECT COUNT(*) FROM prospect_note WHERE banker_id IS NULL"
    ).fetchone()[0]
    print(f"\n  written. notes still without a banker_id: {still}")
    if still:
        print(f"  non-zero exit: {still} note(s) landed on an LEI nobody "
              "covers -- decide what to do (not a crash).")
    # A NULL banker_id is the honest DATA state -- inventing a banker would
    # assert a coverage relationship that does not exist -- but it is not a
    # clean LOADER outcome, since it needs a human decision. Any unassigned
    # row, not just "all of them", should fail the exit code: the pytest
    # gate already requires every note to resolve, and the loader is run
    # standalone far more often than the suite, so it should agree.
    return 1 if still else 0


if __name__ == "__main__":
    sys.exit(main())
