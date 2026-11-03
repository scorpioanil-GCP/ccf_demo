#!/usr/bin/env python3
"""Wave 20 Tasks 1-2 -- label the addresses, and load the headquarters half.

    uv run loaders/load_hq_address_wave20.py

## What was wrong

`ccf_v2.legal_entity` carried exactly one address triple, named
`address_country / _city / _region`, and NOTHING RECORDED WHICH OF THE TWO
ADDRESSES IT WAS. It is the legal domicile -- Wave 1 mapped it from
`sources/screening/anchors_final.json`'s `legal_address_*` fields -- but a
consumer reading the schema could not know that.

`counterparty-reference-snapshot` §C names `addresses`, plural, and §B names
which two: `headquarters and legal address`. So this was two defects at once:
a missing element, and an ambiguous name for the element that was present.

The ambiguity is the worse half. A missing column returns nothing and the
consumer notices. An unlabelled one returns Wilmington, Delaware for a
company run from Whippany, New Jersey, and the consumer does not.

## What this does

1. RENAMES `address_*` to `legal_address_*`, which is what it always was.
2. ADDS `hq_address_country / _city / _region`.
3. Loads the headquarters address for all 153 GLEIF-registered entities.

Sources, both already on disk after `fetch_anchor_hq_wave20.py`:

    sources/gleif_l1/subsidiaries_l1.json   103 subsidiaries (Wave 15)
    sources/gleif_l1/anchors_hq_l1.json      50 anchors      (Wave 20)

The source files keep their original `address_*` / `hq_*` key names. They are
retrieved artifacts with a `retrieved_at` date, and rewriting a fetched file
to match a later schema would falsify the record of what the source actually
returned. The mapping happens here instead.

## The three entities that get no headquarters, and why that is correct

`SYN-SDART-2022-6`, `SYN-SDART-2024-1`, `SYN-TAOT-2022-B` -- synthetic ABS
deal trusts. They carry `SYN-` identifiers rather than real LEIs, GLEIF has
no record of them, and no amount of fetching will produce one. The validator
excludes exactly this set and PROVES the exclusion is that set rather than
assuming it: an exclusion nobody re-derives is how a growing hole hides.

## Idempotency

Safely re-runnable. The rename is guarded on the column actually being there,
the ADDs are `IF NOT EXISTS`, and the load is an UPDATE keyed on `lei` -- it
writes no rows and creates no identity, so it cannot renumber anything.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ccf.config import PG_SCHEMA_V2, pg_connect  # noqa: E402

L1 = REPO_ROOT / "sources" / "gleif_l1"
SUBS = L1 / "subsidiaries_l1.json"
ANCHORS = L1 / "anchors_hq_l1.json"

S = PG_SCHEMA_V2


def _has_column(cur, table: str, column: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s AND column_name = %s",
        (S, table, column))
    return cur.fetchone() is not None


def migrate(cur) -> list[str]:
    """Rename the legal-address triple and add the headquarters triple."""
    done: list[str] = []
    for part in ("country", "city", "region"):
        old, new = f"address_{part}", f"legal_address_{part}"
        if _has_column(cur, "legal_entity", old) and not _has_column(
                cur, "legal_entity", new):
            cur.execute(f'ALTER TABLE "{S}".legal_entity '
                        f"RENAME COLUMN {old} TO {new}")
            done.append(f"renamed {old} -> {new}")
    for part in ("country", "city", "region"):
        col = f"hq_address_{part}"
        if not _has_column(cur, "legal_entity", col):
            cur.execute(f'ALTER TABLE "{S}".legal_entity '
                        f"ADD COLUMN {col} TEXT")
            done.append(f"added {col}")
    return done


def hq_rows() -> dict[str, tuple[str | None, str | None, str | None]]:
    """(country, city, region) per LEI, from both retained Level 1 files."""
    out: dict[str, tuple] = {}
    for path in (SUBS, ANCHORS):
        for r in json.loads(path.read_text())["records"]:
            out[r["lei"].strip()] = (
                r.get("hq_country"), r.get("hq_city"), r.get("hq_region"))
    return out


def main() -> int:
    hq = hq_rows()
    print(f"headquarters addresses available: {len(hq)}")

    with pg_connect() as conn, conn.cursor() as cur:
        for line in migrate(cur):
            print(f"  schema: {line}")

        cur.execute(f'SELECT lei FROM "{S}".legal_entity')
        present = {r[0].strip() for r in cur.fetchall()}

        updated = 0
        for lei, (country, city, region) in hq.items():
            if lei not in present:
                continue
            cur.execute(
                f'UPDATE "{S}".legal_entity SET hq_address_country = %s, '
                f"hq_address_city = %s, hq_address_region = %s WHERE lei = %s",
                (country, city, region, lei))
            updated += cur.rowcount
        conn.commit()

        cur.execute(f'SELECT count(*) FROM "{S}".legal_entity '
                    "WHERE hq_address_country IS NOT NULL")
        with_hq = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".legal_entity '
                    "WHERE hq_address_country IS DISTINCT FROM legal_address_country "
                    "OR hq_address_city IS DISTINCT FROM legal_address_city "
                    "OR hq_address_region IS DISTINCT FROM legal_address_region")
        differing = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".legal_entity')
        total = cur.fetchone()[0]
        cur.execute(f'SELECT lei FROM "{S}".legal_entity '
                    "WHERE hq_address_country IS NULL ORDER BY lei")
        missing = [r[0].strip() for r in cur.fetchall()]

    print(f"\n  updated {updated} rows")
    print(f"  {with_hq} of {total} carry a headquarters address")
    print(f"  {differing} differ from their legal address in some component")
    print(f"  {len(missing)} without one: {', '.join(missing) or '(none)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
