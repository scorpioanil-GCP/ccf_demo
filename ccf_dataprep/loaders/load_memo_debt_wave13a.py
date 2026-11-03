#!/usr/bin/env python3
"""Wave 13a stage 5b — per-obligor aggregate Context Debt into Postgres.

    uv run loaders/load_memo_debt_wave13a.py --dry-run
    uv run loaders/load_memo_debt_wave13a.py

Stores what `generators/compute_memo_debt.py` measured, so the product can
serve a `context_debt` block without recomputing on every request.

**The stored value is a cache, not the truth.** `validators/memo_debt.py`
recomputes every component from the loaded stores and compares — it never reads
this table to decide whether the table is right. That separation is the whole
point: Waves 11a, 11b and 12 each needed a recompute-from-loaded-data gate for
exactly this reason, and Wave 12's own record (known-issues.md §12) is seven
checks that passed because they read the number they were meant to be checking.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import assert_v2_schema, pg_connect
from generators.compute_memo_debt import ARTIFACT

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".memo_context_debt (
    lei                          CHAR(20) NOT NULL PRIMARY KEY,
    unresolved_passage_anchor    NUMERIC NOT NULL,
    peer_set_thinness            NUMERIC NOT NULL,
    signal_staleness             NUMERIC NOT NULL,
    inherited_prerequisite_debt  NUMERIC NOT NULL,
    aggregate_debt               NUMERIC NOT NULL,
    definition_refs_unverified   INTEGER NOT NULL,
    definition_refs_verified     INTEGER NOT NULL,
    provenance                   TEXT NOT NULL,
    as_of                        DATE NOT NULL,
    CONSTRAINT memo_debt_components_unit CHECK (
        unresolved_passage_anchor BETWEEN 0 AND 1
        AND peer_set_thinness BETWEEN 0 AND 1
        AND signal_staleness BETWEEN 0 AND 1
        AND inherited_prerequisite_debt BETWEEN 0 AND 1),
    CONSTRAINT memo_debt_aggregate_unit CHECK (aggregate_debt BETWEEN 0 AND 1)
);
COMMENT ON TABLE "{S}".memo_context_debt IS
  'credit-memo-context aggregate Context Debt per obligor. A CACHE of what '
  'generators/compute_memo_debt.py measured -- validators/memo_debt.py '
  'recomputes from the stores and never reads this table to validate it.';
"""


#: Idempotent migration for the `as_of` column. Backfills from the artifact's
#: own `generated_at` rather than from today, because today is precisely the
#: wrong answer -- the whole defect this closes was a validator substituting
#: its own clock for the evaluation date.
MIGRATE = f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = '{S}' AND table_name = 'memo_context_debt')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_schema = '{S}'
                         AND table_name = 'memo_context_debt'
                         AND column_name = 'as_of') THEN
        ALTER TABLE "{S}".memo_context_debt ADD COLUMN as_of DATE;
    END IF;
END $$;
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_v2_schema(S)
    rows = json.loads(ARTIFACT.read_text())["obligors"]
    print(f"Wave 13a — memo Context Debt\n\n  {len(rows)} obligors")
    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    artifact = json.loads(ARTIFACT.read_text())
    # Prefer the explicit evaluation date; fall back to the day the artifact
    # was written for artifacts generated before `as_of` existed. Never
    # date.today() -- see MIGRATE.
    as_of = artifact.get("as_of") or artifact["generated_at"][:10]
    print(f"  evaluation date (as_of): {as_of}")

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(MIGRATE)
        cur.execute(DDL)
        cur.executemany(
            f'INSERT INTO "{S}".memo_context_debt '
            "(lei, unresolved_passage_anchor, peer_set_thinness, "
            " signal_staleness, inherited_prerequisite_debt, aggregate_debt, "
            " definition_refs_unverified, definition_refs_verified, provenance, "
            " as_of) "
            "VALUES (" + ",".join(["%s"] * 10) + ") "
            "ON CONFLICT (lei) DO UPDATE SET "
            "unresolved_passage_anchor=EXCLUDED.unresolved_passage_anchor, "
            "peer_set_thinness=EXCLUDED.peer_set_thinness, "
            "signal_staleness=EXCLUDED.signal_staleness, "
            "inherited_prerequisite_debt=EXCLUDED.inherited_prerequisite_debt, "
            "aggregate_debt=EXCLUDED.aggregate_debt, "
            "definition_refs_unverified=EXCLUDED.definition_refs_unverified, "
            "definition_refs_verified=EXCLUDED.definition_refs_verified, "
            "as_of=EXCLUDED.as_of",
            [(r["lei"], r["components"]["unresolved_passage_anchor"],
              r["components"]["peer_set_thinness"],
              r["components"]["signal_staleness"],
              r["components"]["inherited_prerequisite_debt"],
              r["aggregate_debt"], r["definition_refs_unverified"],
              r["definition_refs_verified"], r["provenance"], as_of)
             for r in rows])
        # NOT NULL only after the backfill, so the migration and a fresh
        # CREATE TABLE converge on the same schema.
        cur.execute(f'ALTER TABLE "{S}".memo_context_debt '
                    "ALTER COLUMN as_of SET NOT NULL")
        conn.commit()
        cur.execute(f'SELECT count(*), count(*) FILTER (WHERE aggregate_debt > 0.30) '
                    f'FROM "{S}".memo_context_debt')
        n, over = cur.fetchone()
        print(f"  memo_context_debt   {n:>4} rows, {over} breaching 0.30")
    return 0


if __name__ == "__main__":
    sys.exit(main())
