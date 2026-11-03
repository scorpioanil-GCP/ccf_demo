#!/usr/bin/env python3
"""Restore the structure ccf-sdk's test fixtures stripped from eight ccf_v2 tables.

See docs/known-issues.md §63. Eight tables were dropped with CASCADE and
recreated without keys, defaults, indexes or comments, by ccf-sdk test
fixtures run against the shared host: `legal_entity`, `crosswalk`,
`filing_profile`, `financial_fact`, `principal`, `principal_jurisdiction`,
`peer_entity` and `peer_fact`. It happened at least twice: once before
2026-09-10 and once on 2026-09-22. The cascade also removed the two
cross-store views and twelve foreign keys, eight of them on tables that
were NOT rebuilt.

**Rows were not touched.** All eight, plus the four other tables the fixtures
wrote to, match the 2026-09-13 bundle dump row for row. This restores
structure only.

Sources for what to restore, in order of authority:

    keys + foreign keys   docs/store-catalog.json (2026-08-31), full definitions
    column types          the same catalog (varchar(20), numeric(4,3))
    defaults, indexes,    the loaders' own DDL (load_postgres_wave1,
    comments              load_xbrl_wave2, load_xbrl_peers, load_mnpi_wave7,
                          load_policy_wave13b, load_postgres_wave10)
    views                 ccf.views.ensure_views

One transaction: either every statement lands or none does. Each constraint is
added VALIDATED (no NOT VALID), so Postgres itself proves the data satisfies it.
A failure there is a finding about the data, not something to work around.

    uv run loaders/repair_ccf_v2_structure.py --dry-run
    uv run loaders/repair_ccf_v2_structure.py

Idempotent: each step checks the catalog first and skips what is present.
"""

from __future__ import annotations

import argparse
import sys

from ccf.config import PG_SCHEMA_V2, pg_connect
from ccf.views import ensure_views

S = PG_SCHEMA_V2

#: (table, constraint name, definition). Names are the ones Postgres generates
#: for the inline declarations in the loaders' DDL, so a fresh build and a
#: repaired one carry identical names.
KEYS = [
    ("legal_entity", "legal_entity_pkey", "PRIMARY KEY (lei)"),
    ("crosswalk", "crosswalk_pkey", "PRIMARY KEY (internal_client_id)"),
    ("crosswalk", "crosswalk_lei_key", "UNIQUE (lei)"),
    ("filing_profile", "filing_profile_pkey", "PRIMARY KEY (lei)"),
    ("financial_fact", "financial_fact_pkey",
     "PRIMARY KEY (cik, tag, unit, period_end, fiscal_period, accession)"),
    ("principal", "principal_pkey", "PRIMARY KEY (principal_id)"),
    ("principal_jurisdiction", "principal_jurisdiction_pkey",
     "PRIMARY KEY (principal_id, jurisdiction_prefix)"),
    ("peer_entity", "peer_entity_pkey", "PRIMARY KEY (cik)"),
    ("peer_fact", "peer_fact_pkey", "PRIMARY KEY (cik, tag, frame)"),
]

FOREIGN_KEYS = [
    ("filing_profile", "filing_profile_lei_fkey", "lei", "legal_entity(lei)"),
    ("financial_fact", "financial_fact_lei_fkey", "lei", "legal_entity(lei)"),
    ("principal_jurisdiction", "principal_jurisdiction_principal_id_fkey",
     "principal_id", "principal(principal_id)"),
    ("peer_fact", "peer_fact_cik_fkey", "cik", "peer_entity(cik)"),
    # Not rebuilt -- these tables kept their rows and silently lost the link.
    ("deal", "deal_lei_fkey", "lei", "legal_entity(lei)"),
    ("debt_instrument", "debt_instrument_lei_fkey", "lei", "legal_entity(lei)"),
    ("facility", "facility_borrower_lei_fkey", "borrower_lei", "legal_entity(lei)"),
    ("gdelt_mention", "gdelt_mention_lei_fkey", "lei", "legal_entity(lei)"),
    ("projection_plan", "projection_plan_principal_id_fkey", "principal_id",
     "principal(principal_id)"),
    ("signal_event", "signal_event_lei_fkey", "lei", "legal_entity(lei)"),
    ("trend_delta", "trend_delta_lei_fkey", "lei", "legal_entity(lei)"),
    ("warn_match", "warn_match_lei_fkey", "lei", "legal_entity(lei)"),
]

#: (table, column, target type). Values were measured to fit before this ran:
#: max lei length 20 in both tables, 0 of 50 scores change under numeric(4,3).
TYPES = [
    ("legal_entity", "lei", "varchar(20)"),
    ("crosswalk", "lei", "varchar(20)"),
    ("legal_entity", "lei_match_score", "numeric(4,3)"),
]

DEFAULTS = [
    ("crosswalk", "created_at", "now()"),
    ("legal_entity", "is_anchor", "false"),
    ("filing_profile", "count_8k_item_1_01", "0"),
    ("filing_profile", "count_8k_item_2_03", "0"),
    ("filing_profile", "count_8k_item_2_04", "0"),
    ("filing_profile", "count_8k_item_4_02", "0"),
    ("filing_profile", "count_10k", "0"),
    ("principal", "sees_eu_person_data", "false"),
    ("principal", "sees_need_to_know", "true"),
]

INDEXES = [
    ("idx_crosswalk_lei", "crosswalk (lei)"),
    ("idx_crosswalk_cik", "crosswalk (cik)"),
    ("idx_entity_anchor", "legal_entity (is_anchor) WHERE is_anchor"),
    ("idx_fact_lei_tag", "financial_fact (lei, tag, period_end)"),
    ("idx_fact_period", "financial_fact (period_end)"),
    ("idx_fact_restatement", "financial_fact (cik, tag, period_end, filed_date)"),
    ("idx_peer_fact_period", "peer_fact (period_end, tag)"),
]

COMMENTS = [
    ("TABLE", "crosswalk",
     "LEI <-> internal_client_id correlation key. Synthetic and mandatory "
     "(rule #4). Must be populated before any internal element loads."),
    ("TABLE", "legal_entity",
     "Entity attributes. Postgres is sole author (single-writer discipline). "
     "Fluree nodes carry lei + label only and resolve attributes from here."),
    ("COLUMN", "principal.perspective",
     "Requestable but NEVER self-asserted. A request for a perspective the "
     "credential does not support is REFUSED, not downgraded -- silent "
     "downgrade would let a caller probe the wall by observing which requests "
     "degrade."),
]


def has_constraint(cur, table: str, name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM pg_constraint WHERE conrelid = %s::regclass AND conname = %s",
        (f'"{S}".{table}', name))
    return cur.fetchone() is not None


def column(cur, table: str, col: str) -> tuple[str, str | None]:
    cur.execute(
        "SELECT format_type(a.atttypid, a.atttypmod), pg_get_expr(d.adbin, d.adrelid) "
        "FROM pg_attribute a LEFT JOIN pg_attrdef d "
        "  ON d.adrelid = a.attrelid AND d.adnum = a.attnum "
        "WHERE a.attrelid = %s::regclass AND a.attname = %s",
        (f'"{S}".{table}', col))
    row = cur.fetchone()
    assert row, f"{table}.{col} does not exist"
    return row


def plan(cur) -> list[str]:
    out: list[str] = []
    for table, col, typ in TYPES:
        if column(cur, table, col)[0] != typ.replace("varchar", "character varying"):
            out.append(f'ALTER TABLE "{S}".{table} ALTER COLUMN {col} TYPE {typ}')
    for table, name, definition in KEYS:
        if not has_constraint(cur, table, name):
            out.append(f'ALTER TABLE "{S}".{table} ADD CONSTRAINT {name} {definition}')
    for table, name, col, target in FOREIGN_KEYS:
        if not has_constraint(cur, table, name):
            out.append(f'ALTER TABLE "{S}".{table} ADD CONSTRAINT {name} '
                       f'FOREIGN KEY ({col}) REFERENCES "{S}".{target}')
    for table, col, default in DEFAULTS:
        if column(cur, table, col)[1] is None:
            out.append(f'ALTER TABLE "{S}".{table} ALTER COLUMN {col} SET DEFAULT {default}')
    for name, target in INDEXES:
        out.append(f'CREATE INDEX IF NOT EXISTS {name} ON "{S}".{target}')
    for kind, obj, text in COMMENTS:
        literal = text.replace("'", "''")
        out.append(f"COMMENT ON {kind} \"{S}\".{obj} IS '{literal}'")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        statements = plan(cur)
        for s in statements:
            print(f"  {s.splitlines()[0][:110]}")
        if args.dry_run:
            print(f"dry run: {len(statements)} statements, nothing written")
            conn.rollback()
            return 0
        for s in statements:
            cur.execute(s)
        used = ensure_views(cur, S)
        print(f"  views rebuilt over: {used}")
        conn.commit()

    with pg_connect() as conn, conn.cursor() as cur:
        remaining = [s for s in plan(cur) if not s.startswith(("CREATE INDEX", "COMMENT"))]
        if remaining:
            print(f"ERROR: {len(remaining)} steps still pending after commit")
            return 1
    print(f"applied {len(statements)} statements + views; nothing pending")
    return 0


if __name__ == "__main__":
    sys.exit(main())
