#!/usr/bin/env python3
"""Wave 12 Task 6 — load the FRED rate foundation into Postgres.

Two tables, per `task-6-brief.md` and design ruling F16:

    reference_rate       public   Task 2's 16-series, 10,539-row rate ledger
                                   (SOFR + its 4 percentiles, 11 DGS
                                   constant-maturity tenors)
    fx_reference_rate     public  Task 2's 6-pair, 3,942-row FX ledger

Both tables are read by later Wave 12 tasks (treasury positions, FX trades,
break detection); this loader only carries the artifact across into Postgres,
unchanged. Nothing here originates a rate, a tenor, or a derivation formula
— those all come from `generators/fetch_fred_rates.py` (Task 2) and
`generators/fred_series.py`'s `DGS_TENOR_YEARS` mapping.

## `derivation` — ruling F7 / F16, the reason this file exists

Five of the six FX pairs are fetched directly from FRED and carry
`derivation: ""`. `EUR/GBP` is not published by FRED at all
(`generators/fred_series.py`'s `DERIVED_CROSSES`) and is computed as
`(DEXUSEU) / (DEXUSUK)`; its rows carry that formula string. Both kinds
carry `provenance: "public"` — the derivation column is the ONLY thing that
keeps a computed quotient distinguishable from an observed rate once loaded.
An earlier DDL draft omitted the column (ruling F16); this file's DDL and
upsert both carry it, and `main()` asserts after loading that exactly one
pair has a non-empty `derivation`.

## `tenor_years` — NULL is not "unknown", it is "no tenor"

SOFR and its four percentiles are overnight rates with no constant-maturity
tenor; their `tenor_years` is NULL, never 0 or omitted. The 11 DGS series
get their tenor from `generators.fred_series.DGS_TENOR_YEARS`
(`{"DGS1MO": 1/12, ..., "DGS30": 30.0}`) rather than parsed out of the
series id string, per the brief's explicit instruction.

    uv run loaders/load_rates_wave12.py --dry-run
    uv run loaders/load_rates_wave12.py

Idempotent: both upserts key on their natural composite key
(`series_id, obs_date` / `pair, obs_date`) and set EVERY non-key column on
conflict — no column is left to go stale on reload.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.currency import verify_current
from generators.fred_series import DGS_TENOR_YEARS, SERIES

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".reference_rate (
    series_id    text        NOT NULL,
    obs_date     date        NOT NULL,
    value_pct    numeric     NOT NULL,
    unit         text        NOT NULL,
    label        text        NOT NULL,
    tenor_years  numeric,               -- NULL for SOFR and its percentiles
    provenance   text        NOT NULL,
    source       text        NOT NULL,
    retrieved_at timestamptz NOT NULL,
    PRIMARY KEY (series_id, obs_date)
);

CREATE TABLE IF NOT EXISTS "{S}".fx_reference_rate (
    pair         text        NOT NULL,
    obs_date     date        NOT NULL,
    rate         numeric     NOT NULL,
    series_id    text        NOT NULL,
    derivation   text        NOT NULL DEFAULT '',  -- RULING F7 / F16
    provenance   text        NOT NULL,
    source       text        NOT NULL,
    retrieved_at timestamptz NOT NULL,
    PRIMARY KEY (pair, obs_date)
);
"""

CURRENCY_NOTES: list[str] = []


def load(name: str) -> dict:
    """Read one artifact, refusing a STALE one (`ccf/currency.py`)."""
    doc, note = verify_current(name)
    CURRENCY_NOTES.append(note)
    return doc


def build_rows(rates_doc: dict):
    meta = rates_doc["_meta"]
    provenance = "public"
    source = meta["source"]
    retrieved_at = meta["retrieved_at"]

    rate_rows: list[tuple] = []
    for r in rates_doc["rates"]:
        sid = r["series_id"]
        label = SERIES[sid].label
        tenor = DGS_TENOR_YEARS.get(sid)  # None for SOFR family, by design
        rate_rows.append((
            sid, r["obs_date"], r["value"], r["unit"], label, tenor,
            provenance, source, retrieved_at,
        ))

    fx_rows: list[tuple] = [
        (f["pair"], f["obs_date"], f["rate"], f["series_id"],
         f["derivation"], provenance, source, retrieved_at)
        for f in rates_doc["fx"]
    ]

    return rate_rows, fx_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rates_doc = load("wave12_rates.json")
    rate_rows, fx_rows = build_rows(rates_doc)

    series_counts = Counter(r[0] for r in rate_rows)
    pair_counts = Counter(f[0] for f in fx_rows)
    derived_pairs = {f[0] for f in fx_rows if f[4] != ""}
    n_null_tenor = sum(1 for r in rate_rows if r[5] is None)

    print(f"Wave 12 Task 6 — load into {S}\n")
    print("  artifact currency:")
    for note in CURRENCY_NOTES:
        print(f"    {note}")
    print()
    print(f"  reference_rate       {len(rate_rows):>6}  "
          f"({len(series_counts)} series: {sorted(series_counts)})")
    print(f"                                tenor_years NULL on {n_null_tenor} "
          f"(SOFR + 4 percentiles)")
    print(f"  fx_reference_rate    {len(fx_rows):>6}  "
          f"({len(pair_counts)} pairs: {sorted(pair_counts)})")
    print(f"                                non-empty derivation on pair(s): "
          f"{sorted(derived_pairs)}")

    if len(derived_pairs) != 1:
        raise RuntimeError(
            f"expected exactly ONE fx pair with a non-empty derivation, "
            f"got {len(derived_pairs)}: {sorted(derived_pairs)}"
        )

    if args.dry_run:
        print("\n  [dry-run] no DDL executed, no rows written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        cur.executemany(
            f'INSERT INTO "{S}".reference_rate '
            "(series_id, obs_date, value_pct, unit, label, tenor_years, "
            " provenance, source, retrieved_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (series_id, obs_date) DO UPDATE SET "
            "value_pct=EXCLUDED.value_pct, unit=EXCLUDED.unit, "
            "label=EXCLUDED.label, tenor_years=EXCLUDED.tenor_years, "
            "provenance=EXCLUDED.provenance, source=EXCLUDED.source, "
            "retrieved_at=EXCLUDED.retrieved_at",
            rate_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".fx_reference_rate '
            "(pair, obs_date, rate, series_id, derivation, provenance, "
            " source, retrieved_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (pair, obs_date) DO UPDATE SET "
            "rate=EXCLUDED.rate, series_id=EXCLUDED.series_id, "
            "derivation=EXCLUDED.derivation, provenance=EXCLUDED.provenance, "
            "source=EXCLUDED.source, retrieved_at=EXCLUDED.retrieved_at",
            fx_rows,
        )

        conn.commit()

        for table in ("reference_rate", "fx_reference_rate"):
            cur.execute(f'SELECT COUNT(*) FROM "{S}".{table}')
            print(f"  {table:24} store count: {cur.fetchone()[0]}")

        cur.execute(
            f'SELECT DISTINCT pair FROM "{S}".fx_reference_rate '
            "WHERE derivation <> ''"
        )
        post_load_derived = [row[0] for row in cur.fetchall()]
        print(f"  post-load check: pair(s) with non-empty derivation = "
              f"{post_load_derived}")
        if post_load_derived != ["EUR/GBP"]:
            raise RuntimeError(
                f"post-load derivation check failed: expected exactly "
                f"['EUR/GBP'], got {post_load_derived}"
            )

    print("\n  loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
