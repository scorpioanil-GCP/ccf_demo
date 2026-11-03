#!/usr/bin/env python3
"""The 103 family-tree entities that had a LEI in Fluree and nothing in Postgres.

`corporate-family-tree` §C row 8 assigns entity attributes to Postgres, and
CLAUDE.md's single-writer rule says Fluree nodes carry `lei` plus a label and
nothing else, so every attribute a traversal needs resolves from here. Before
this loader, 155 ledger entities carried a real GLEIF LEI and 50 of them
resolved. The graph looked complete and the attribute join returned nothing
for the rest.

**No crosswalk rows, by ruling.** These are GLEIF reference entities: the bank
holds no facility, exposure, coverage assignment or interaction against any of
them, and minting an `internal_client_id` would invent 103 client
relationships that do not exist. Rule #4's crosswalk is mandatory for entities
the bank has internal data about; that is what makes it a CORRELATION key
rather than a registry.

Two checks assumed every `legal_entity` row was a client, and both are
narrowed alongside this load rather than relaxed — see the docstring on
`validators/conditions.py`'s crosswalk-orphan check.

Idempotent: upserts on `lei`, and refuses to touch an anchor row.

Run: uv run loaders/load_gleif_subsidiaries.py --dry-run
     uv run loaders/load_gleif_subsidiaries.py
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, pg_connect

SOURCE = REPO_ROOT / "sources" / "gleif_l1" / "subsidiaries_l1.json"
MANIFEST = REPO_ROOT / "sources" / "gleif_l1" / "manifest.json"

COLUMNS = [
    "lei", "legal_name", "gleif_legal_name", "legal_jurisdiction",
    "entity_status", "registration_status", "next_renewal_date",
    "initial_registration", "legal_form", "legal_address_country",
    "legal_address_city", "legal_address_region", "is_anchor", "provenance",
    "source", "retrieved_at",
]


def retrieved_at() -> str:
    """The date the payload was actually fetched, not the date of this run.

    Reading it from the manifest rather than `date.today()` keeps the
    provenance honest when the loader is re-run weeks after the fetch — a
    re-run does not make the data fresher.
    """
    fetches = json.loads(MANIFEST.read_text())["fetches"]
    return max(f["retrieved_at"] for f in fetches)[:10]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(SOURCE.read_text())
    when = retrieved_at()
    rows = [
        (r["lei"], r["legal_name"], r["legal_name"], r["legal_jurisdiction"],
         r["entity_status"], r["registration_status"], r["next_renewal_date"],
         r["initial_registration"], r["legal_form"], r["address_country"],
         r["address_city"], r["address_region"], False, "public",
         "GLEIF LEI-CDF Level 1, https://api.gleif.org/api/v1/lei-records",
         when)
        for r in doc["records"]
    ]
    print(f"  {len(rows)} Level 1 records, retrieved {when}")

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei FROM "{S}".legal_entity WHERE is_anchor')
        anchors = {r[0] for r in cur.fetchall()}
        clash = anchors & {r[0] for r in rows}
        if clash:
            # An anchor's row was built from a screened, name-matched fetch
            # with a match band and score. Overwriting it from a bulk pull
            # would silently drop that provenance, so this is a hard stop
            # rather than a filter.
            print(f"  FAIL: {len(clash)} of these LEIs are ANCHORS: "
                  f"{sorted(clash)[:3]}", file=sys.stderr)
            return 1

        cur.execute(f'SELECT COUNT(*) FROM "{S}".legal_entity')
        before = cur.fetchone()[0]
        print(f"  legal_entity before               {before}")

        if args.dry_run:
            print("\n  [dry-run] nothing written")
            print(f"  would insert/update {len(rows)}, none of them anchors")
            return 0

        placeholders = ", ".join(["%s"] * len(COLUMNS))
        updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in COLUMNS
                            if c not in ("lei", "is_anchor"))
        cur.executemany(
            f'INSERT INTO "{S}".legal_entity ({", ".join(COLUMNS)}) '
            f"VALUES ({placeholders}) ON CONFLICT (lei) DO UPDATE SET {updates}",
            rows,
        )
        conn.commit()

        cur.execute(f'SELECT COUNT(*) FROM "{S}".legal_entity')
        after = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{S}".legal_entity WHERE is_anchor')
        still_anchors = cur.fetchone()[0]

        # Read back a NAMED row and its VALUES. A row count cannot see an
        # anchor's attributes being overwritten with nulls, and cannot see a
        # second run resetting a field -- known-issues §19.2.
        probe = rows[0][0]
        cur.execute(
            f'SELECT legal_name, legal_jurisdiction, entity_status, '
            f'registration_status, is_anchor FROM "{S}".legal_entity '
            f"WHERE lei = %s", (probe,))
        got = cur.fetchone()

    print(f"  legal_entity after                {after}")
    print(f"  anchors still flagged             {still_anchors}  (must be 50)")
    print(f"  verified {probe}: {got}")
    if still_anchors != 50:
        print("\n  FAIL: the anchor count moved.", file=sys.stderr)
        return 1
    if got is None or got[4] is not False or not got[0]:
        print(f"\n  FAIL: {probe} did not read back as a non-anchor with a "
              f"name.", file=sys.stderr)
        return 1
    print("\n  Traversal results now resolve. No crosswalk rows written: "
          "these are reference entities, not clients.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
