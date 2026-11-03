#!/usr/bin/env python3
"""Final fix wave, blocker 4 — load the widened coverage rows.

Reads `sources/screening/wave16_coverage_widen.json`
(`generators/widen_coverage_wave16.py`) and inserts ONLY into
`"{S}".coverage_assignment`. `banker`, `interaction`, and `participant` are
untouched — this loader does not read those tables' artifact data at all.

**ADD ONLY.** `ON CONFLICT (banker_id, lei) DO NOTHING` means an existing
row — from the Wave 10 baseline of 150, or from an earlier run of this
loader — is never updated, and in particular `is_primary` on an existing
row can never change. No row this loader inserts ever carries
`is_primary = True`; the generator enforces that upstream and this loader
does not second-guess it.

**Verifies the single-writer invariant survives, every run.** Exactly one
`is_primary = TRUE` row per covered `lei` held before this loader ever
existed; a bug here that somehow flipped that would be exactly the kind of
silent break `CLAUDE.md`'s definition-of-done exists to catch. Checked
after every load, not assumed.

    uv run loaders/load_coverage_widen_wave16.py --dry-run
    uv run loaders/load_coverage_widen_wave16.py
"""
from __future__ import annotations

import argparse
import json
import sys

from ccf.config import PG_SCHEMA_V2 as S, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    payload = json.loads((SCREEN / "wave16_coverage_widen.json").read_text())
    rows = payload["new_coverage_assignments"]

    bad_primary = [r for r in rows if r["is_primary"]]
    if bad_primary:
        raise RuntimeError(
            f"refusing to load: {len(bad_primary)} widened row(s) carry "
            "is_primary=True -- this loader must never add a second "
            f"primary: {bad_primary[:3]}")

    print(f"  {len(rows)} widened coverage_assignment rows to insert "
          "(ON CONFLICT DO NOTHING -- existing rows untouched)")

    if args.dry_run:
        print("  [dry-run] nothing written")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT count(*) FROM "{S}".coverage_assignment')
        before = cur.fetchone()[0]

        cur.executemany(
            f'INSERT INTO "{S}".coverage_assignment '
            "(banker_id, lei, is_primary, assigned_date, provenance) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (banker_id, lei) DO NOTHING",
            [(r["banker_id"], r["lei"], r["is_primary"], r["assigned_date"],
              r["provenance"]) for r in rows])

        cur.execute(f'SELECT count(*) FROM "{S}".coverage_assignment')
        after = cur.fetchone()[0]

        # Single-writer invariant: exactly one primary per covered LEI,
        # checked live, not assumed to still hold because this loader
        # never writes is_primary=True.
        cur.execute(f"""
            SELECT lei, count(*) FROM "{S}".coverage_assignment
            WHERE is_primary GROUP BY lei HAVING count(*) <> 1
        """)
        violations = cur.fetchall()
        if violations:
            conn.rollback()
            raise RuntimeError(
                f"refusing to commit: {len(violations)} LEI(s) do not have "
                f"exactly one primary banker after load: {violations}")

        conn.commit()
        print(f"  coverage_assignment: {before} -> {after} rows "
              f"(+{after - before})")
        print(f"  single-primary-per-LEI invariant holds: 0 violations")

    return 0


if __name__ == "__main__":
    sys.exit(main())
