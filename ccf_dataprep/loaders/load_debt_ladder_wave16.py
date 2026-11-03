#!/usr/bin/env python3
"""Wave 16 Task 8b — load the debt ladder extension into Postgres.

Reads `sources/screening/wave16_debt_ladder.json`
(`generators/extend_debt_ladder_wave16.py`) and upserts into
`debt_instrument` / `spread_observation` -- the same two tables Wave 11a's
`loaders/load_postgres_wave11a.py` already owns.

## The rule that matters most

This loader writes into ANOTHER wave's table. Every row it touches carries
the `w16-i-` prefix Wave 11a never uses, `ON CONFLICT (instrument_id) DO
UPDATE` (never DELETE), and `spread_observation` upserts on its own natural
key `(instrument_id, obs_date)`. It never issues a DELETE, a TRUNCATE, or any
statement that could renumber or re-key a `syn-i-*` row. Idempotency is
proved by naming a value (`coupon_pct`, `anchor_accession`) across two runs,
never by a row count, which cannot see a field silently reset.

    uv run loaders/load_debt_ladder_wave16.py --dry-run
    uv run loaders/load_debt_ladder_wave16.py
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, assert_v2_schema, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
ID_PREFIX = "w16-i-"


def load() -> dict:
    return json.loads((SCREEN / "wave16_debt_ladder.json").read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = load()
    instruments = doc["instruments"]
    observations = doc["observations"]
    spread_prov = doc["spread_provenance"]

    # Guard the namespace before touching the database at all: every id this
    # loader will write must carry the w16 prefix, or it has no business
    # being here.
    bad_ids = [i["instrument_id"] for i in instruments
               if not i["instrument_id"].startswith(ID_PREFIX)]
    if bad_ids:
        raise RuntimeError(
            f"refusing to load: {len(bad_ids)} instrument id(s) do not "
            f"carry the {ID_PREFIX!r} prefix -- this loader must never "
            f"touch another wave's namespace: {bad_ids[:5]}")

    instrument_rows: list[tuple] = [
        (i["instrument_id"], i["lei"], i["coupon_pct"], i["maturity"],
         i["issue_date"], i["face_amount_usd"], i["rating_band"],
         i["seniority"], i["tenor_years"], i["anchored_to_real_filing"],
         i["anchor_accession"], i["provenance"], i["provenance_note"])
        for i in instruments
    ]

    obs_rows: list[tuple] = [
        (o["instrument_id"], o["obs_date"], o["years_to_maturity"],
         o["benchmark_bp"], o["market_oas_bp"], o["idiosyncratic_bp"],
         o["spread_bp"], o["yield_bp"],
         spread_prov["benchmark_bp"], spread_prov["market_oas_bp"],
         spread_prov["idiosyncratic_bp"])
        for o in observations
    ]

    print(f"Wave 16 Task 8b — load into {S}\n")
    print(f"  debt_instrument   {len(instrument_rows):>6}  "
          f"(prefix {ID_PREFIX!r}, {len({r[1] for r in instrument_rows})} "
          f"distinct obligors)")
    print(f"  spread_observation {len(obs_rows):>6}")

    if args.dry_run:
        print("\n  [dry-run] no writes")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        # Belt-and-suspenders: confirm the two tables already exist (Wave
        # 11a's loader creates them) rather than redeclaring DDL here --
        # redeclaring it would risk a second, possibly-drifted definition of
        # a table this loader does not own the schema of.
        cur.execute(
            "SELECT to_regclass(%s), to_regclass(%s)",
            (f'"{S}".debt_instrument', f'"{S}".spread_observation'))
        di, so = cur.fetchone()
        if di is None or so is None:
            raise RuntimeError(
                "debt_instrument / spread_observation do not exist yet -- "
                "run loaders/load_postgres_wave11a.py first (load order: "
                "ontology -> crosswalk -> entities -> relationships -> ...).")

        cur.executemany(
            f'INSERT INTO "{S}".debt_instrument '
            "(instrument_id, lei, coupon_pct, maturity, issue_date, "
            " face_amount_usd, rating_band, seniority, tenor_years, "
            " anchored_to_real_filing, anchor_accession, provenance, "
            " provenance_note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (instrument_id) DO UPDATE SET "
            "lei=EXCLUDED.lei, coupon_pct=EXCLUDED.coupon_pct, "
            "maturity=EXCLUDED.maturity, issue_date=EXCLUDED.issue_date, "
            "face_amount_usd=EXCLUDED.face_amount_usd, "
            "rating_band=EXCLUDED.rating_band, seniority=EXCLUDED.seniority, "
            "tenor_years=EXCLUDED.tenor_years, "
            "anchored_to_real_filing=EXCLUDED.anchored_to_real_filing, "
            "anchor_accession=EXCLUDED.anchor_accession, "
            "provenance=EXCLUDED.provenance, "
            "provenance_note=EXCLUDED.provenance_note",
            instrument_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".spread_observation '
            "(instrument_id, obs_date, years_to_maturity, benchmark_bp, "
            " market_oas_bp, idiosyncratic_bp, spread_bp, yield_bp, "
            " provenance_benchmark, provenance_market_oas, "
            " provenance_idiosyncratic) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (instrument_id, obs_date) DO UPDATE SET "
            "years_to_maturity=EXCLUDED.years_to_maturity, "
            "benchmark_bp=EXCLUDED.benchmark_bp, "
            "market_oas_bp=EXCLUDED.market_oas_bp, "
            "idiosyncratic_bp=EXCLUDED.idiosyncratic_bp, "
            "spread_bp=EXCLUDED.spread_bp, yield_bp=EXCLUDED.yield_bp, "
            "provenance_benchmark=EXCLUDED.provenance_benchmark, "
            "provenance_market_oas=EXCLUDED.provenance_market_oas, "
            "provenance_idiosyncratic=EXCLUDED.provenance_idiosyncratic",
            obs_rows,
        )

        conn.commit()

        cur.execute(f'SELECT COUNT(*) FROM "{S}".debt_instrument '
                    "WHERE instrument_id LIKE %s", (f"{ID_PREFIX}%",))
        n_new = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{S}".debt_instrument '
                    "WHERE instrument_id NOT LIKE %s", (f"{ID_PREFIX}%",))
        n_old = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(DISTINCT lei) FROM "{S}".debt_instrument')
        n_obligors = cur.fetchone()[0]

    print(f"\n  debt_instrument store count   w16-i-*: {n_new}   "
          f"other (untouched): {n_old}   total distinct obligors: "
          f"{n_obligors}")
    print("\n  loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
