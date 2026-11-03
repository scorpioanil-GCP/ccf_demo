#!/usr/bin/env python3
"""Wave 11a Task 7 — load the rating-and-spread-migration data into Postgres.

Six tables, per `docs/wave11a-design.md` §3.1. Postgres owns `E` and policy
reference for this product; Fluree owns the grade-assertion supersession
chain (Task 8, not here).

    debt_instrument        synthetic — engineered   Task 4's ~60 instruments
    spread_observation     split, per column         Task 5's ~29,885 rows
    benchmark_curve        public                    Task 1's Treasury curve
    market_oas_series      public                    Task 2's five FRED series
    rating_scale           synthetic — internal       DERIVED from Task 6
    divergence_threshold   synthetic — internal       ORIGINATED here

**Two of the six tables have no upstream generator.** Neither is invented
independently of what already exists:

`rating_scale` is DERIVED from `wave11a_grades.json["grade_scale"]`, not a
second scale invented here. Task 6 already built a 15-grade scale (5 bands ×
3 notches, AA+..B-, notch 0=best..14=worst) and verified zero grade/notch
disagreements across 245 assertions. Inventing a second mapping here could
drift from it silently; deriving the (grade, notch, band, modifier) rows from
the one Task 6 already produced cannot. `policy_version` is minted here as
`'wave11a-v1'` — grades.json carries no explicit version string, and there is
exactly one scale in play across the whole artifact, so a single version
value is the honest statement of what "one" means, not a guess at a value
that was supposed to already exist.

`divergence_threshold` is ORIGINATED here — say so plainly, because nothing
upstream produces it and it must not be mistaken for derived data. "By
sector" needed a sector label per obligor that this estate does not already
carry, so the loader buckets `legal_entity.sic` into the ten standard 1987
SIC major divisions (a verifiable external scheme, not an invented one) and
assigns one threshold_bp per division actually present among the 30 Task-4
obligors (nine of ten; no obligor falls in Agriculture or Public
Administration, and one — CION Investment Corp — has no SIC on file and
lands in a ninth bucket, "Unclassified"). The threshold values themselves
ARE invented: chosen so every one of Task 5's four engineered divergence
windows (peak_bp 160-240) clears its own sector's threshold (80-120bp) with
room to spare, so the table is usable by a later validator rather than
merely present. `policy_version` is `'wave11a-v1'`, matching `rating_scale`.

Trap shapes checked against (project history, not hypothetical):
  1. Partial `ON CONFLICT ... DO UPDATE SET` — every upsert below sets EVERY
     non-key column, or the table is delete-then-insert. No column is ever
     left to go stale silently.
  2. A NOT NULL an insert path violates — none of these six tables is
     inherited or shared with another wave's writer, so there is no existing
     NOT NULL to collide with; new NOT NULLs here are set from artifact
     fields verified non-null for all rows before this script was written
     (see the task report).
  3. A `dict.get()` default masking a wrong key — every artifact access below
     is `d["key"]`, not `d.get("key")`, specifically so a renamed or
     misspelled field raises KeyError instead of silently writing NULL.

`spread_observation` keeps `benchmark_bp` (public), `market_oas_bp` (public)
and `idiosyncratic_bp` (synthetic — engineered) in separate columns, with a
matching `provenance_*` column each — the same shape Wave 9 used for
`collateral_asset.provenance_existence` / `provenance_valuation`. `spread_bp`
and `yield_bp` are stored as the generator computed them (sums of the above);
they carry no provenance column of their own because they are not a base
element, they are arithmetic over the three that are.

`market_oas_series` records the FRED series id per row (the provenance),
not just the rating band (which is our label for it).

    uv run loaders/load_postgres_wave11a.py --dry-run
    uv run loaders/load_postgres_wave11a.py

Idempotent: every write is an upsert on a natural key with a full-column SET.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

POLICY_VERSION = "wave11a-v1"

# Standard 1987 SIC major divisions (a verified external scheme — see
# https://www.osha.gov/data/sic-manual — not an invented bucketing). Only
# the divisions actually represented among Task 4's 30 obligors matter here;
# the rest of the table would sit at zero rows referenced by nothing.
SIC_DIVISIONS = [
    (1, 9, "Agriculture, Forestry & Fishing"),
    (10, 14, "Mining"),
    (15, 17, "Construction"),
    (20, 39, "Manufacturing"),
    (40, 49, "Transportation, Communications & Utilities"),
    (50, 51, "Wholesale Trade"),
    (52, 59, "Retail Trade"),
    (60, 67, "Finance, Insurance & Real Estate"),
    (70, 89, "Services"),
    (91, 99, "Public Administration"),
]

# Originated: chosen so every one of the four engineered divergence windows
# (Celanese/Manufacturing 200bp, Genesis Energy/Transportation 180bp,
# Pebblebrook/Finance-RE 160bp, Sabre/Services 240bp — see
# wave11a_spreads.json["divergence_windows"]) clears its own sector's
# threshold with room to spare. Sectors with no obligor in the loaded set
# still get a value (so a later re-selection of obligors does not need a
# schema change), set to the same default as the closest analog.
DIVERGENCE_THRESHOLD_BP = {
    "Agriculture, Forestry & Fishing": 100,
    "Mining": 120,
    "Construction": 100,
    "Manufacturing": 90,
    "Transportation, Communications & Utilities": 100,
    "Wholesale Trade": 85,
    "Retail Trade": 85,
    "Finance, Insurance & Real Estate": 80,
    "Services": 110,
    "Public Administration": 100,
    "Unclassified": 100,
}

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".debt_instrument (
    instrument_id          TEXT PRIMARY KEY,
    lei                     CHAR(20) NOT NULL
                            REFERENCES "{S}".legal_entity(lei),
    coupon_pct              NUMERIC NOT NULL,
    maturity                DATE NOT NULL,
    issue_date              DATE NOT NULL,
    face_amount_usd         NUMERIC NOT NULL,
    rating_band             TEXT NOT NULL CHECK (rating_band IN
                            ('AA','A','BBB','BB','B')),
    seniority               TEXT NOT NULL,
    tenor_years             INTEGER NOT NULL,
    anchored_to_real_filing BOOLEAN NOT NULL,
    anchor_accession        TEXT,
    provenance              TEXT NOT NULL,
    provenance_note         TEXT
);

CREATE TABLE IF NOT EXISTS "{S}".benchmark_curve (
    curve_date      DATE NOT NULL,
    tenor_years     NUMERIC NOT NULL,
    par_yield_pct   NUMERIC NOT NULL,
    provenance      TEXT NOT NULL,
    PRIMARY KEY (curve_date, tenor_years)
);

CREATE TABLE IF NOT EXISTS "{S}".market_oas_series (
    obs_date        DATE NOT NULL,
    rating_band     TEXT NOT NULL CHECK (rating_band IN
                    ('AA','A','BBB','BB','B')),
    fred_series_id  TEXT NOT NULL,
    oas_bp          NUMERIC NOT NULL,
    unit            TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    PRIMARY KEY (obs_date, rating_band)
);

CREATE TABLE IF NOT EXISTS "{S}".spread_observation (
    instrument_id             TEXT NOT NULL
                              REFERENCES "{S}".debt_instrument(instrument_id),
    obs_date                  DATE NOT NULL,
    years_to_maturity         NUMERIC NOT NULL,
    benchmark_bp               NUMERIC NOT NULL,
    market_oas_bp               NUMERIC NOT NULL,
    idiosyncratic_bp             NUMERIC NOT NULL,
    spread_bp                     NUMERIC NOT NULL,
    yield_bp                       NUMERIC NOT NULL,
    provenance_benchmark             TEXT NOT NULL,
    provenance_market_oas             TEXT NOT NULL,
    provenance_idiosyncratic           TEXT NOT NULL,
    PRIMARY KEY (instrument_id, obs_date)
);

CREATE TABLE IF NOT EXISTS "{S}".rating_scale (
    grade           TEXT NOT NULL,
    policy_version  TEXT NOT NULL,
    notch           INTEGER NOT NULL,
    rating_band     TEXT NOT NULL CHECK (rating_band IN
                    ('AA','A','BBB','BB','B')),
    modifier        TEXT NOT NULL CHECK (modifier IN ('+','flat','-')),
    provenance      TEXT NOT NULL,
    PRIMARY KEY (grade, policy_version)
);

CREATE TABLE IF NOT EXISTS "{S}".divergence_threshold (
    sector          TEXT NOT NULL,
    policy_version  TEXT NOT NULL,
    threshold_bp    NUMERIC NOT NULL,
    rationale       TEXT,
    provenance      TEXT NOT NULL,
    PRIMARY KEY (sector, policy_version)
);

CREATE INDEX IF NOT EXISTS ix_spread_observation_date
    ON "{S}".spread_observation (obs_date);
CREATE INDEX IF NOT EXISTS ix_debt_instrument_lei
    ON "{S}".debt_instrument (lei);
CREATE INDEX IF NOT EXISTS ix_market_oas_series_band
    ON "{S}".market_oas_series (rating_band);
"""


def load(name: str) -> dict:
    return json.loads((SCREEN / name).read_text())


def sector_for(sic: str | None) -> str:
    if not sic:
        return "Unclassified"
    try:
        code = int(sic[:2])
    except ValueError:
        return "Unclassified"
    for lo, hi, label in SIC_DIVISIONS:
        if lo <= code <= hi:
            return label
    return "Unclassified"


def grade_to_notch(grades: list[str]) -> list[tuple[str, int, str, str]]:
    """(grade, notch, rating_band, modifier) for every grade in scale order.

    notch 0 = best (first in the list) .. len-1 = worst, per Task 6's
    grade_scale.note. modifier is '+' / '-' by suffix, else 'flat'.
    """
    rows = []
    for notch, grade in enumerate(grades):
        if grade.endswith("+"):
            band, modifier = grade[:-1], "+"
        elif grade.endswith("-"):
            band, modifier = grade[:-1], "-"
        else:
            band, modifier = grade, "flat"
        rows.append((grade, notch, band, modifier))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    curve = load("wave11a_curve.json")
    oas = load("wave11a_oas.json")
    instruments_doc = load("wave11a_instruments.json")
    spreads_doc = load("wave11a_spreads.json")
    grades_doc = load("wave11a_grades.json")

    instruments = instruments_doc["instruments"]
    obligor_leis = {o["lei"] for o in instruments_doc["obligors"]}
    observations = spreads_doc["observations"]
    grade_scale = grades_doc["grade_scale"]["grades"]

    curve_rows: list[tuple] = [
        (row["date"], tenor, yld, curve["provenance"])
        for row in curve["curve"]
        for tenor, yld in row["tenors"].items()
    ]

    oas_rows: list[tuple] = [
        (point["date"], band, obj["fred_id"], point["oas_bp"], obj["unit"],
         oas["provenance"])
        for band, obj in oas["series"].items()
        for point in obj["points"]
    ]

    instrument_rows: list[tuple] = [
        (i["instrument_id"], i["lei"], i["coupon_pct"], i["maturity"],
         i["issue_date"], i["face_amount_usd"], i["rating_band"],
         i["seniority"], i["tenor_years"], i["anchored_to_real_filing"],
         i["anchor_accession"], i["provenance"], i["provenance_note"])
        for i in instruments
    ]

    spread_provenance = spreads_doc["provenance"]
    obs_rows: list[tuple] = [
        (o["instrument_id"], o["obs_date"], o["years_to_maturity"],
         o["benchmark_bp"], o["market_oas_bp"], o["idiosyncratic_bp"],
         o["spread_bp"], o["yield_bp"],
         spread_provenance["benchmark_bp"], spread_provenance["market_oas_bp"],
         spread_provenance["idiosyncratic_bp"])
        for o in observations
    ]

    rating_scale_rows: list[tuple] = [
        (grade, POLICY_VERSION, notch, band, modifier, "synthetic — internal")
        for grade, notch, band, modifier in grade_to_notch(grade_scale)
    ]

    # --- divergence_threshold: originated, sourced from legal_entity.sic ---
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT lei, sic FROM "{S}".legal_entity WHERE lei = ANY(%s)',
            (list(obligor_leis),),
        )
        sic_by_lei = {row[0].strip(): row[1] for row in cur.fetchall()}
    sectors_present = sorted({sector_for(sic_by_lei.get(lei)) for lei in obligor_leis})
    threshold_rows: list[tuple] = [
        (sector, POLICY_VERSION, DIVERGENCE_THRESHOLD_BP[sector],
         "originated in loaders/load_postgres_wave11a.py; not derived from "
         "any upstream artifact — see module docstring", "synthetic — internal")
        for sector in sectors_present
    ]

    print(f"Wave 11a Task 7 — load into {S}\n")
    print(f"  debt_instrument         {len(instrument_rows):>6}  (source: 60 instruments)")
    print(f"  spread_observation      {len(obs_rows):>6}  (source: 29,885 observations)")
    print(f"  benchmark_curve         {len(curve_rows):>6}  (source: 657 dates, 13-14 tenors each)")
    print(f"  market_oas_series       {len(oas_rows):>6}  (source: 5 series x 786 points)")
    print(f"  rating_scale            {len(rating_scale_rows):>6}  (derived: 15-grade scale from Task 6)")
    print(f"  divergence_threshold    {len(threshold_rows):>6}  (originated: {sectors_present})")

    if args.dry_run:
        print("\n  [dry-run] no DDL executed, no rows written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

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
            f'INSERT INTO "{S}".benchmark_curve '
            "(curve_date, tenor_years, par_yield_pct, provenance) "
            "VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (curve_date, tenor_years) DO UPDATE SET "
            "par_yield_pct=EXCLUDED.par_yield_pct, provenance=EXCLUDED.provenance",
            curve_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".market_oas_series '
            "(obs_date, rating_band, fred_series_id, oas_bp, unit, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (obs_date, rating_band) DO UPDATE SET "
            "fred_series_id=EXCLUDED.fred_series_id, oas_bp=EXCLUDED.oas_bp, "
            "unit=EXCLUDED.unit, provenance=EXCLUDED.provenance",
            oas_rows,
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

        cur.executemany(
            f'INSERT INTO "{S}".rating_scale '
            "(grade, policy_version, notch, rating_band, modifier, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (grade, policy_version) DO UPDATE SET "
            "notch=EXCLUDED.notch, rating_band=EXCLUDED.rating_band, "
            "modifier=EXCLUDED.modifier, provenance=EXCLUDED.provenance",
            rating_scale_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".divergence_threshold '
            "(sector, policy_version, threshold_bp, rationale, provenance) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (sector, policy_version) DO UPDATE SET "
            "threshold_bp=EXCLUDED.threshold_bp, rationale=EXCLUDED.rationale, "
            "provenance=EXCLUDED.provenance",
            threshold_rows,
        )

        conn.commit()

        for table in ("debt_instrument", "spread_observation", "benchmark_curve",
                      "market_oas_series", "rating_scale", "divergence_threshold"):
            cur.execute(f'SELECT COUNT(*) FROM "{S}".{table}')
            print(f"  {table:24} store count: {cur.fetchone()[0]}")

    print("\n  loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
