#!/usr/bin/env python3
"""Wave 1 — load the identity spine into Postgres schema ccf_v2.

Non-negotiable rule #4: the LEI <-> internal_client_id crosswalk is synthetic,
mandatory, and must exist **before any internal element loads**. It is created
and populated first here, ahead of risk grades, RM assignments, and
entitlements, because nothing joins without it.

Identifier formats are deliberately distinguishable (settled decision,
CLAUDE.md):

    real GLEIF LEI      20 chars, [A-Z0-9] only   549300UZHTN0CNKBOB19
    synthetic entity    'SYNTH-' prefix, hyphen   SYNTH-00000000000001
    internal client id  'CLI-' prefix             CLI-000001

A hyphen is not a legal LEI character, so the two can never be confused by
eye or by regex.

Writes ONLY to schema ccf_v2 (guarded in ccf.config). v1's public schema is
untouched.

    uv run loaders/load_postgres_wave1.py --dry-run    # show intent, write nothing
    uv run loaders/load_postgres_wave1.py              # load

Idempotent: re-runnable, upserts on primary key.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect

ANCHORS = REPO_ROOT / "sources" / "screening" / "anchors_final.json"

DDL = f"""
CREATE SCHEMA IF NOT EXISTS "{PG_SCHEMA_V2}";

-- The correlation spine. Built before every internal element.
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".crosswalk (
    internal_client_id  TEXT PRIMARY KEY,
    lei                 CHAR(20)    NOT NULL UNIQUE,
    cik                 INTEGER,
    ticker              TEXT,
    provenance          TEXT        NOT NULL,
    source              TEXT        NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE "{PG_SCHEMA_V2}".crosswalk IS
  'LEI <-> internal_client_id correlation key. Synthetic and mandatory (rule #4). '
  'Must be populated before any internal element loads.';

-- `lei` is declared CHAR(20) here and WIDENED TO VARCHAR(20) by
-- load_abs_overlay_wave14.py, which is the type live in the database. CHAR(20)
-- blank-pads anything shorter and returns the padding on read, which broke the
-- moment a non-LEI synthetic identifier (`SYN-TAOT-2022-B`) landed in the
-- column. Left as CHAR(20) rather than corrected in place: three child tables
-- carry CHAR(20) foreign keys to it, so changing this line alone would make a
-- fresh build differ from the one that has been exercised. Wave 14's
-- `ALTER COLUMN TYPE` is idempotent and runs after this.
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".legal_entity (
    lei                    CHAR(20) PRIMARY KEY,
    legal_name             TEXT NOT NULL,
    gleif_legal_name       TEXT,
    legal_jurisdiction     TEXT,
    entity_status          TEXT,
    registration_status    TEXT,
    next_renewal_date      DATE,
    initial_registration   DATE,
    legal_form             TEXT,
    -- Renamed from address_* in Wave 20. This triple is the LEGAL DOMICILE
    -- and always was; the old name did not say so, and a consumer reading
    -- it as the operating seat got Wilmington for a company run elsewhere.
    legal_address_country  TEXT,
    legal_address_city     TEXT,
    legal_address_region   TEXT,
    hq_address_country     TEXT,
    hq_address_city        TEXT,
    hq_address_region      TEXT,
    sic                    TEXT,
    sic_description        TEXT,
    fiscal_year_end        TEXT,
    is_anchor              BOOLEAN NOT NULL DEFAULT false,
    lei_match_band         TEXT,
    lei_match_score        NUMERIC(4,3),
    provenance             TEXT NOT NULL,
    source                 TEXT NOT NULL,
    retrieved_at           DATE NOT NULL
);
COMMENT ON TABLE "{PG_SCHEMA_V2}".legal_entity IS
  'Entity attributes. Postgres is sole author (single-writer discipline). '
  'Fluree nodes carry lei + label only and resolve attributes from here.';

-- Filing-history facts that drive §F condition satisfaction. Public.
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".filing_profile (
    lei                CHAR(20) PRIMARY KEY
                       REFERENCES "{PG_SCHEMA_V2}".legal_entity(lei),
    cik                INTEGER NOT NULL,
    count_8k_item_1_01 INTEGER NOT NULL DEFAULT 0,
    count_8k_item_2_03 INTEGER NOT NULL DEFAULT 0,
    count_8k_item_2_04 INTEGER NOT NULL DEFAULT 0,
    count_8k_item_4_02 INTEGER NOT NULL DEFAULT 0,
    count_10k          INTEGER NOT NULL DEFAULT 0,
    provenance         TEXT NOT NULL,
    source             TEXT NOT NULL,
    retrieved_at       DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_crosswalk_lei
    ON "{PG_SCHEMA_V2}".crosswalk (lei);
CREATE INDEX IF NOT EXISTS idx_crosswalk_cik
    ON "{PG_SCHEMA_V2}".crosswalk (cik);
CREATE INDEX IF NOT EXISTS idx_entity_anchor
    ON "{PG_SCHEMA_V2}".legal_entity (is_anchor) WHERE is_anchor;
"""


def nullable_date(value: str | None):
    if not value:
        return None
    return value[:10]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="print intended mutations and exit without writing")
    args = parser.parse_args()

    if not ANCHORS.exists():
        print(f"missing {ANCHORS} — run generators/finalize_anchors.py first")
        return 1

    payload = json.loads(ANCHORS.read_text())
    anchors = payload["anchors"]

    # NOT date.today(). `retrieved_at` is a fact about the FETCH, and this
    # loader only reads a file someone else fetched -- stamping the run date
    # made every re-run advance the anchors' provenance by however long had
    # passed. Caught 2026-08-24 by diffing the table field-by-field either
    # side of a re-run: 156 rows before, 156 after, and 50 of them silently
    # moved from 2026-08-16 to 2026-08-24. A row count cannot see that.
    #
    # Hard failure rather than a fallback: a missing date must stop the load,
    # because falling back to today is precisely the bug.
    when = payload.get("retrieved_at")
    if not when:
        print(f"  FAIL: {ANCHORS.name} carries no retrieved_at. Add the date "
              f"the GLEIF/EDGAR calls were made; do not substitute today.",
              file=sys.stderr)
        return 1
    today = when

    assert_v2_schema(PG_SCHEMA_V2)

    crosswalk_rows = []
    entity_rows = []
    filing_rows = []

    for seq, a in enumerate(sorted(anchors, key=lambda r: r["lei"]), start=1):
        internal_id = f"CLI-{seq:06d}"
        ticker = (a.get("tickers") or [""])[0]

        crosswalk_rows.append((
            internal_id, a["lei"], a["cik"], ticker,
            "synthetic — internal",
            "generated: no public LEI<->internal-id mapping exists",
        ))
        entity_rows.append((
            a["lei"], a["sec_name"], a.get("gleif_legal_name"),
            a.get("legal_jurisdiction"), a.get("entity_status"),
            a.get("registration_status"),
            nullable_date(a.get("next_renewal_date")),
            nullable_date(a.get("initial_registration_date")),
            a.get("legal_form"), a.get("legal_address_country"),
            a.get("legal_address_city"), a.get("legal_address_region"),
            a.get("sic"), a.get("sic_description"), a.get("fiscal_year_end"),
            True, a.get("match_band"), a.get("match_score"),
            "public", "GLEIF LEI record API + SEC EDGAR submissions API", today,
        ))
        filing_rows.append((
            a["lei"], a["cik"], a.get("item_1_01", 0), a.get("item_2_03", 0),
            a.get("item_2_04", 0), a.get("item_4_02", 0), a.get("count_10k", 0),
            "public", "SEC EDGAR submissions API", today,
        ))

    print(f"Wave 1 load into schema {PG_SCHEMA_V2}")
    print(f"  crosswalk      {len(crosswalk_rows):>4} rows  (built FIRST — rule #4)")
    print(f"  legal_entity   {len(entity_rows):>4} rows")
    print(f"  filing_profile {len(filing_rows):>4} rows")
    print(f"  identifier formats: real LEI (20 alnum) | CLI-nnnnnn (internal)")

    if args.dry_run:
        print("\n  DRY RUN — nothing written. Sample crosswalk rows:")
        for row in crosswalk_rows[:5]:
            print(f"    {row[0]}  <-> {row[1]}  cik={row[2]}  {row[3]}")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        # Crosswalk first. Everything else joins through it.
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".crosswalk '
            "(internal_client_id, lei, cik, ticker, provenance, source) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (internal_client_id) DO UPDATE SET "
            "lei=EXCLUDED.lei, cik=EXCLUDED.cik, ticker=EXCLUDED.ticker",
            crosswalk_rows,
        )
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".legal_entity '
            "(lei, legal_name, gleif_legal_name, legal_jurisdiction, entity_status, "
            " registration_status, next_renewal_date, initial_registration, legal_form, "
            " legal_address_country, legal_address_city, legal_address_region, "
            " sic, sic_description, "
            " fiscal_year_end, is_anchor, lei_match_band, lei_match_score, "
            " provenance, source, retrieved_at) "
            "VALUES (" + ",".join(["%s"] * 21) + ") "
            "ON CONFLICT (lei) DO UPDATE SET "
            "legal_name=EXCLUDED.legal_name, "
            "registration_status=EXCLUDED.registration_status, "
            "retrieved_at=EXCLUDED.retrieved_at",
            entity_rows,
        )
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".filing_profile '
            "(lei, cik, count_8k_item_1_01, count_8k_item_2_03, count_8k_item_2_04, "
            " count_8k_item_4_02, count_10k, provenance, source, retrieved_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (lei) DO UPDATE SET "
            "count_8k_item_1_01=EXCLUDED.count_8k_item_1_01, "
            "count_8k_item_2_04=EXCLUDED.count_8k_item_2_04, "
            "retrieved_at=EXCLUDED.retrieved_at",
            filing_rows,
        )
        conn.commit()

        print("\n  loaded. verifying join integrity:")
        # NARROWED 2026-08-24, with the matching check in conditions.py. This
        # was a FULL OUTER JOIN, so it counted every `legal_entity` row with
        # no `crosswalk` row -- correct while this loader was the only writer
        # of the table, and wrong once `load_gleif_subsidiaries.py` added 103
        # GLEIF REFERENCE entities the bank holds no internal data about. Left
        # as it was, this loader would refuse to re-run at all.
        #
        # What it means and still catches: a client id resolving to nobody,
        # and an ANCHOR -- this loader's own output -- with no client id.
        cur.execute(f"""
            SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".crosswalk c
            LEFT JOIN "{PG_SCHEMA_V2}".legal_entity e USING (lei)
            WHERE e.lei IS NULL
        """)
        orphans = cur.fetchone()[0]
        cur.execute(f"""
            SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".legal_entity e
            LEFT JOIN "{PG_SCHEMA_V2}".crosswalk c USING (lei)
            WHERE e.is_anchor AND c.lei IS NULL
        """)
        orphans += cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".crosswalk')
        n_cross = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".legal_entity')
        n_ent = cur.fetchone()[0]
        cur.execute(
            f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".legal_entity '
            "WHERE registration_status = 'LAPSED'"
        )
        n_lapsed = cur.fetchone()[0]

        print(f"    crosswalk rows          {n_cross}")
        print(f"    legal_entity rows       {n_ent}")
        print(f"    orphans (must be 0)     {orphans}")
        print(f"    LAPSED entities         {n_lapsed}  (§F floor 5)")

        if orphans:
            print("\n  FAIL: a client id resolves to no entity, or an anchor "
                  "has no client id")
            return 1

    print("\n  Wave 1 identity spine loaded. Every anchor joins LEI <-> internal id.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
