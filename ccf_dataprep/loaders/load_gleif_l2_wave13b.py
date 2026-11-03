#!/usr/bin/env python3
"""Wave 13b Task 2 — GLEIF Level 2 ownership records into Postgres.

§C: *"Corporate ownership records across jurisdictions"* -> **Postgres**,
`public`. Its named source (OpenCorporates) is no longer free; GLEIF Level 2
is the approved substitute. Reads `sources/screening/wave13b_gleif_l2.json`.

    registry_company            140 non-anchor entities in the ownership graph
    corporate_ownership_record  280 ACTIVE DIRECT relationship records

## Why `registry_company` is not just more rows in `legal_entity`

Three checks in `validators/conditions.py` count `legal_entity` **without**
filtering `is_anchor`:

    entities in LAPSED registration            expects 5
    crosswalk resolves LEI <-> internal        expects 50
    crosswalk orphans (inverted, want 0)       FULL OUTER JOIN against crosswalk

Adding 140 GLEIF entities to that table would leave 140 rows with no crosswalk
counterpart and turn a green orphan gate red — and would silently move the
LAPSED count. `legal_entity` holds the anchor cast and the crosswalk keys it;
`registry_company` holds everyone else the ownership graph reaches. The two
are asserted disjoint at load, so "which table owns this LEI's attributes" has
exactly one answer.

## Why jurisdiction is not copied onto the ownership record

`cross_border` could be a stored column, computed once from both endpoints.
It is a view instead. Wave 12 lost a day to three systems storing identical
values, which made every difference it computed structurally zero
(`known-issues.md` §12). A jurisdiction copied onto 280 records is the same
mistake in miniature: it can disagree with the entity it was copied from, and
nothing would say so. `v_ownership_cross_border` joins to the owner of the
attribute every time it is asked.

`v_entity_jurisdiction` unions the two entity tables so downstream callers ask
one question rather than remembering the split. Neither view stores a row.

    uv run loaders/load_gleif_l2_wave13b.py --dry-run
    uv run loaders/load_gleif_l2_wave13b.py

Idempotent: both upserts key on their natural primary key and set EVERY
non-key column on conflict.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.views import ensure_views

S = PG_SCHEMA_V2
SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13b_gleif_l2.json"

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".registry_company (
    lei                  char(20)   PRIMARY KEY,
    legal_name           text       NOT NULL,
    legal_jurisdiction   text,               -- ISO 3166-2, e.g. 'US-DE', 'GB'
    legal_country        text,               -- ISO 3166-1, the part before '-'
    hq_country           text,
    legal_form           text,
    entity_category      text,
    entity_status        text,
    registration_status  text,
    initial_registration date,
    last_update          date,
    -- GLEIF publishes transliterated and previous names explicitly. §F5 needs
    -- transliteration STRUCTURE to exist somewhere real before the person
    -- layer imitates it, so these are carried rather than dropped.
    transliterated_names text[]     NOT NULL DEFAULT '{{}}',
    other_names          text[]     NOT NULL DEFAULT '{{}}',
    provenance           text       NOT NULL,
    source               text       NOT NULL,
    retrieved_at         date       NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".corporate_ownership_record (
    child_lei            char(20)   NOT NULL,
    parent_lei           char(20)   NOT NULL,
    -- RR-CDF: StartNode is the child, EndNode is the parent. Only
    -- IS_DIRECTLY_CONSOLIDATED_BY builds the hierarchy one hop at a time;
    -- IS_ULTIMATELY_CONSOLIDATED_BY is a shortcut to the top of the group and
    -- would both collapse depth and manufacture cycles if walked as an edge.
    relationship_type    text       NOT NULL,
    relationship_status  text       NOT NULL,   -- ACTIVE | INACTIVE
    registration_status  text       NOT NULL,
    initial_registration date,
    last_update          date,
    period_start         date,
    period_end           date,
    provenance           text       NOT NULL,
    source               text       NOT NULL,
    retrieved_at         date       NOT NULL,
    PRIMARY KEY (child_lei, parent_lei, relationship_type)
);

CREATE INDEX IF NOT EXISTS corporate_ownership_child_idx
    ON "{S}".corporate_ownership_record (child_lei);
CREATE INDEX IF NOT EXISTS corporate_ownership_parent_idx
    ON "{S}".corporate_ownership_record (parent_lei);

-- One question, one answer: where does this LEI's jurisdiction live?
-- `legal_entity` owns the anchor cast, `registry_company` owns the rest, and
-- the two are disjoint by assertion in this loader.
"""

SOURCE = "GLEIF RR-CDF Level 2 golden copy (daily full file)"


def country_of(jurisdiction: str | None) -> str | None:
    return jurisdiction.split("-")[0] if jurisdiction else None


def build_rows(doc: dict, anchor_leis: set[str]) -> tuple[list, list, dict]:
    retrieved = doc["generated_at"][:10]
    entities = doc["entities"]

    company_rows = []
    for lei, e in sorted(entities.items()):
        # The disjointness rule, applied at build time: an anchor's attributes
        # belong to `legal_entity` and are not copied here.
        if lei in anchor_leis:
            continue
        company_rows.append(
            (
                lei, e["legal_name"] or lei, e["legal_jurisdiction"],
                country_of(e["legal_jurisdiction"]), e["hq_country"],
                e["legal_form"], e["entity_category"], e["entity_status"],
                e["registration_status"], e["initial_registration"],
                e["last_update"], e["transliterated_names"], e["other_names"],
                "public", SOURCE, retrieved,
            )
        )

    seen: set[tuple] = set()
    record_rows = []
    for r in doc["records"]:
        key = (r["child_lei"], r["parent_lei"], r["relationship_type"])
        if key in seen:
            raise RuntimeError(f"duplicate ownership record in artifact: {key}")
        seen.add(key)
        record_rows.append(
            (
                r["child_lei"], r["parent_lei"], r["relationship_type"],
                r["relationship_status"], r["registration_status"],
                r["initial_registration"], r["last_update"],
                r["period_start"], r["period_end"],
                "public", SOURCE, retrieved,
            )
        )

    stats = {
        "anchors_skipped": len(entities) - len(company_rows),
        "jurisdictions": Counter(
            country_of(e["legal_jurisdiction"]) or "?" for e in entities.values()
        ),
        "with_transliteration": sum(
            1 for e in entities.values() if e["transliterated_names"]
        ),
    }
    return company_rows, record_rows, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Load GLEIF Level 2 records into Postgres")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(ARTIFACT.read_text())

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei FROM "{S}".legal_entity')
        legal_entity_leis = {r[0] for r in cur.fetchall()}

    company_rows, record_rows, stats = build_rows(doc, legal_entity_leis)

    print(f"Wave 13b Task 2 — GLEIF Level 2 into {S}\n")
    print(f"  artifact            {ARTIFACT.relative_to(REPO_ROOT)}")
    print(f"  golden copy         {doc['publication']['publish_date']} "
          f"({doc['publication']['cdf_version']})")
    print(f"\n  registry_company    {len(company_rows):>5}   "
          f"({stats['anchors_skipped']} anchors left to legal_entity)")
    print(f"  ownership records   {len(record_rows):>5}")
    print(f"  jurisdictions       {len(stats['jurisdictions']):>5} distinct, "
          f"top: {dict(stats['jurisdictions'].most_common(6))}")
    print(f"  entities w/ transliterated names {stats['with_transliteration']}")
    print(f"  depth histogram     {doc['depth_histogram']}   "
          f"(max depth {max(int(k) for k in doc['depth_histogram'])})")

    if args.dry_run:
        print("\n  [dry-run] no DDL executed, no rows written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        # Views live in ccf/views.py so this loader cannot rebuild one
        # without the sources a later wave added. See that module.
        sources = ensure_views(cur, S)

        cur.executemany(
            f'INSERT INTO "{S}".registry_company '
            "(lei, legal_name, legal_jurisdiction, legal_country, hq_country, "
            " legal_form, entity_category, entity_status, registration_status, "
            " initial_registration, last_update, transliterated_names, "
            " other_names, provenance, source, retrieved_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (lei) DO UPDATE SET "
            "legal_name=EXCLUDED.legal_name, "
            "legal_jurisdiction=EXCLUDED.legal_jurisdiction, "
            "legal_country=EXCLUDED.legal_country, "
            "hq_country=EXCLUDED.hq_country, legal_form=EXCLUDED.legal_form, "
            "entity_category=EXCLUDED.entity_category, "
            "entity_status=EXCLUDED.entity_status, "
            "registration_status=EXCLUDED.registration_status, "
            "initial_registration=EXCLUDED.initial_registration, "
            "last_update=EXCLUDED.last_update, "
            "transliterated_names=EXCLUDED.transliterated_names, "
            "other_names=EXCLUDED.other_names, "
            "provenance=EXCLUDED.provenance, source=EXCLUDED.source, "
            "retrieved_at=EXCLUDED.retrieved_at",
            company_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".corporate_ownership_record '
            "(child_lei, parent_lei, relationship_type, relationship_status, "
            " registration_status, initial_registration, last_update, "
            " period_start, period_end, provenance, source, retrieved_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (child_lei, parent_lei, relationship_type) DO UPDATE SET "
            "relationship_status=EXCLUDED.relationship_status, "
            "registration_status=EXCLUDED.registration_status, "
            "initial_registration=EXCLUDED.initial_registration, "
            "last_update=EXCLUDED.last_update, "
            "period_start=EXCLUDED.period_start, "
            "period_end=EXCLUDED.period_end, "
            "provenance=EXCLUDED.provenance, source=EXCLUDED.source, "
            "retrieved_at=EXCLUDED.retrieved_at",
            record_rows,
        )
        conn.commit()

        # --- what the store now holds, counted rather than restated --------
        cur.execute(f'SELECT count(*) FROM "{S}".registry_company')
        n_companies = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".corporate_ownership_record')
        n_records = cur.fetchone()[0]

        # Disjointness is the whole basis of the two-table split, so it is
        # verified against the live tables, not assumed from the build filter.
        cur.execute(
            f'SELECT count(*) FROM "{S}".registry_company r '
            f'JOIN "{S}".legal_entity e USING (lei)'
        )
        overlap = cur.fetchone()[0]

        cur.execute(
            f'SELECT count(*) FROM "{S}".v_ownership_cross_border '
            "WHERE cross_border"
        )
        n_cross = cur.fetchone()[0]
        cur.execute(
            f'SELECT count(*) FROM "{S}".v_ownership_cross_border '
            "WHERE child_country IS NULL OR parent_country IS NULL"
        )
        n_unresolved = cur.fetchone()[0]
        cur.execute(
            f'SELECT count(DISTINCT legal_country) '
            f'FROM "{S}".v_entity_jurisdiction WHERE legal_country <> \'\''
        )
        n_countries = cur.fetchone()[0]

    print(f"\n  jurisdiction view sources: {sources}")
    print(f"  loaded: registry_company {n_companies} · "
          f"corporate_ownership_record {n_records}")
    print(f"  cross-border records: {n_cross} of {n_records} "
          f"({n_unresolved} with an unresolved endpoint)")
    print(f"  countries across both entity tables: {n_countries}")

    failures = []
    if overlap:
        failures.append(f"{overlap} LEI(s) in BOTH legal_entity and "
                        f"registry_company — the split is not disjoint")
    if n_companies != len(company_rows) or n_records != len(record_rows):
        failures.append(f"post-load count mismatch: expected "
                        f"{len(company_rows)}/{len(record_rows)}, store holds "
                        f"{n_companies}/{n_records}")
    if n_unresolved:
        failures.append(f"{n_unresolved} record(s) have an endpoint with no "
                        f"jurisdiction in either entity table")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1

    print("  store matches the artifact; the two entity tables are disjoint")
    return 0


if __name__ == "__main__":
    sys.exit(main())
