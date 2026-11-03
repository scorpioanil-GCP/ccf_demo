#!/usr/bin/env python3
"""Wave 13b Task 3 — load the pseudonymized PSC person layer into Postgres.

Reads `sources/screening/wave13b_psc_persons.json`. Every identity in it is
invented; see `generators/derive_psc_persons.py` for how, and for why no real
name, date of birth or mapping exists anywhere to load.

    person       +210 rows, person_key 'PSC-####', person_key_source 'psc'
    psc_person    210 rows, the PSC-specific attributes `person` has no
                  columns for

## Why these persons join the EXISTING `person` table

`person_name_variant` and `person_crosswalk` both carry a foreign key to
`person(person_key)`. §F5's condition — variants **across registries**, with
transliteration cases and a false-positive pair — is checked by
`validators/conditions.py` against `person_name_variant`. A parallel person
table would fragment exactly the join the product exists to demonstrate, and
the variants could not be stored at all without violating the FK.

So `person` is a **two-writer table** as of this wave: Wave 10 owns the 743
`sec_cik` rows, Wave 13b owns the `psc` rows. That boundary is enforced the way
Wave 12's `deposit_account` boundary was:

  - every person_key inserted here is asserted `PSC-` prefixed BEFORE the
    upsert, not merely by construction;
  - there is no DELETE or TRUNCATE against `person` anywhere in this file;
  - the upsert's ON CONFLICT target is `person_key` alone, so a rerun touches
    only rows this loader wrote;
  - `main()` ends by asserting Wave 10's 743 rows are still present and
    unchanged in count.

`validators/artifact_reproduces_store.py` was corrected in the same commit:
its Wave 10 comparison asserted set equality against the WHOLE `person` table,
which is a claim Wave 10's artifact was never in a position to make. It now
scopes to `person_key_source = 'sec_cik'`.

## Attributes here, edges later

§C files person-level beneficial ownership under Fluree. The estate's
established split — and CLAUDE.md's single-writer rule — puts ATTRIBUTES in
Postgres and NODES plus EDGES in Fluree, which is exactly what Wave 10 did
with its 743 persons and 704 Fluree Person nodes. This loader writes the
attributes; the Fluree person nodes and `hasBeneficialOwner` edges land with
the ownership chains they belong to. The §C wording is a punch-list item for
the vault, not a licence to duplicate attributes into two stores.

    uv run loaders/load_psc_persons_wave13b.py --dry-run
    uv run loaders/load_psc_persons_wave13b.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect

S = PG_SCHEMA_V2
SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13b_psc_persons.json"

#: The key prefix this loader owns. Wave 10's rows are bare CIK strings.
KEY_PREFIX = "PSC-"
KEY_SOURCE = "psc"
WAVE10_KEY_SOURCE = "sec_cik"

DDL = f"""
-- `person.person_key_source` was pinned to ('sec_cik','minted') by Wave 10.
-- Widening it is a schema change to a table this wave does not own, so it is
-- written as an idempotent migration rather than assumed: DROP ... IF EXISTS
-- then ADD re-validates every existing row, and re-running is a no-op.
-- Wave 10's own DDL carries the same widened list, for a fresh database.
ALTER TABLE "{S}".person DROP CONSTRAINT IF EXISTS person_person_key_source_check;
ALTER TABLE "{S}".person ADD CONSTRAINT person_person_key_source_check
    CHECK (person_key_source IN ('sec_cik', 'minted', 'psc'));

CREATE TABLE IF NOT EXISTS "{S}".psc_person (
    person_key            text     PRIMARY KEY
                          REFERENCES "{S}".person(person_key) ON DELETE CASCADE,
    nationality           text     NOT NULL,
    is_eu_national        boolean  NOT NULL,
    country_of_residence  text,
    -- TRUE where residence was engineered rather than resampled: §F7 needs
    -- EU-RESIDENT persons and PSC's own residence field is overwhelmingly
    -- England, so residence could not be met by a faithful draw.
    residence_engineered  boolean  NOT NULL,
    -- Month and year only, and banded before resampling. No individual's
    -- date of birth is copied; see the generator's privacy controls.
    dob_month             integer  NOT NULL,
    dob_year              integer  NOT NULL,
    dob_band              integer  NOT NULL,
    script_family         text     NOT NULL,
    -- The invented native form. It is what makes a transliteration case a
    -- transliteration rather than a misspelling: the Latin renderings are
    -- romanizations OF this, and the resolver has to see through them.
    native_forename       text     NOT NULL,
    native_surname        text     NOT NULL,
    particle              text,
    is_transliterated     boolean  NOT NULL,
    rendering_count       integer  NOT NULL,
    -- Verbatim from Companies House. A public controlled vocabulary, not
    -- personal data, so it survives pseudonymization unchanged.
    natures_of_control    text[]   NOT NULL,
    controls_n_companies  integer  NOT NULL,
    ceased                boolean  NOT NULL,
    -- How this person's attributes were sampled. Recorded per row so the
    -- privacy control is visible in the store, not only in a docstring.
    joint_resampled       boolean  NOT NULL,
    stratified            boolean  NOT NULL,
    provenance            text     NOT NULL,
    source                text     NOT NULL
);

CREATE INDEX IF NOT EXISTS psc_person_translit_idx
    ON "{S}".psc_person (is_transliterated) WHERE is_transliterated;
CREATE INDEX IF NOT EXISTS psc_person_nationality_idx
    ON "{S}".psc_person (nationality);
"""


def build_rows(doc: dict) -> tuple[list, list]:
    snapshot = doc["source_snapshot"]
    source = (f"pseudonymized from UK Companies House PSC snapshot "
              f"{snapshot['snapshot_date']} part {snapshot['part']}")
    retrieved = doc["generated_at"][:10]

    bad = [p["person_id"] for p in doc["persons"]
           if not p["person_id"].startswith(KEY_PREFIX)]
    if bad:
        raise RuntimeError(
            f"refusing to load: {len(bad)} person_key(s) lack the "
            f"{KEY_PREFIX!r} prefix this loader owns: {bad[:5]}"
        )

    person_rows = []
    psc_rows = []
    for p in doc["persons"]:
        person_rows.append(
            (
                p["person_id"], KEY_SOURCE, None, p["display_name"],
                p["display_name"], "natural", p["surname"], p["forename"],
                p["middle_name"], None, p["provenance"], source, retrieved,
            )
        )
        psc_rows.append(
            (
                p["person_id"], p["nationality"], p["is_eu_national"],
                p["country_of_residence"], p["residence_engineered"],
                p["dob_month"], p["dob_year"], p["dob_band"],
                p["script_family"], p["native_forename"], p["native_surname"],
                p["particle"], p["is_transliterated"], p["rendering_count"],
                p["natures_of_control"], p["controls_n_companies"],
                p["ceased"], p["joint_resampled"], p["stratified"],
                p["provenance"], source,
            )
        )
    return person_rows, psc_rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Load the PSC person layer")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(ARTIFACT.read_text())
    person_rows, psc_rows = build_rows(doc)

    scripts = Counter(p["script_family"] for p in doc["persons"])
    print(f"Wave 13b Task 3 — PSC person layer into {S}\n")
    print(f"  artifact            {ARTIFACT.relative_to(REPO_ROOT)}")
    print(f"  snapshot            {doc['source_snapshot']['snapshot_date']} "
          f"part {doc['source_snapshot']['part']} "
          f"({doc['source_snapshot']['records_scanned']:,} records scanned)")
    print(f"  privacy             k={doc['privacy_controls']['k_anonymity']}, "
          f"dob banded {doc['privacy_controls']['dob_band_years']}y, "
          f"mapping retained: {doc['privacy_controls']['mapping_retained']}, "
          f"raw deleted: {doc['privacy_controls']['raw_file_deleted']}")
    print(f"\n  person (+{KEY_SOURCE})     {len(person_rows):>5}   "
          f"EXTENDS Wave 10's table; never deletes from it")
    print(f"  psc_person          {len(psc_rows):>5}")
    print(f"  script families     {dict(scripts.most_common())}")
    print(f"  transliterated      {doc['transliterated_count']}")
    print(f"  EU-resident         {doc['eu_resident_count']}")
    print(f"  stratified          {doc['stratification']['stratified_persons']}"
          f"  (deliberate departure from the source distribution — see the "
          f"artifact's stratification note)")

    if args.dry_run:
        print("\n  [dry-run] no DDL executed, no rows written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM \"{S}\".person "
                    f"WHERE person_key_source = '{WAVE10_KEY_SOURCE}'")
        wave10_before = cur.fetchone()[0]

        cur.execute(DDL)

        cur.executemany(
            f'INSERT INTO "{S}".person '
            "(person_key, person_key_source, cik, name_as_filed, display_name, "
            " owner_kind, name_last, name_first, name_middle, name_suffix, "
            " provenance, source, retrieved_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (person_key) DO UPDATE SET "
            "person_key_source=EXCLUDED.person_key_source, cik=EXCLUDED.cik, "
            "name_as_filed=EXCLUDED.name_as_filed, "
            "display_name=EXCLUDED.display_name, "
            "owner_kind=EXCLUDED.owner_kind, name_last=EXCLUDED.name_last, "
            "name_first=EXCLUDED.name_first, name_middle=EXCLUDED.name_middle, "
            "name_suffix=EXCLUDED.name_suffix, provenance=EXCLUDED.provenance, "
            "source=EXCLUDED.source, retrieved_at=EXCLUDED.retrieved_at",
            person_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".psc_person '
            "(person_key, nationality, is_eu_national, country_of_residence, "
            " residence_engineered, dob_month, dob_year, dob_band, "
            " script_family, native_forename, native_surname, particle, "
            " is_transliterated, rendering_count, natures_of_control, "
            " controls_n_companies, ceased, joint_resampled, stratified, "
            " provenance, source) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (person_key) DO UPDATE SET "
            "nationality=EXCLUDED.nationality, "
            "is_eu_national=EXCLUDED.is_eu_national, "
            "country_of_residence=EXCLUDED.country_of_residence, "
            "residence_engineered=EXCLUDED.residence_engineered, "
            "dob_month=EXCLUDED.dob_month, dob_year=EXCLUDED.dob_year, "
            "dob_band=EXCLUDED.dob_band, script_family=EXCLUDED.script_family, "
            "native_forename=EXCLUDED.native_forename, "
            "native_surname=EXCLUDED.native_surname, "
            "particle=EXCLUDED.particle, "
            "is_transliterated=EXCLUDED.is_transliterated, "
            "rendering_count=EXCLUDED.rendering_count, "
            "natures_of_control=EXCLUDED.natures_of_control, "
            "controls_n_companies=EXCLUDED.controls_n_companies, "
            "ceased=EXCLUDED.ceased, joint_resampled=EXCLUDED.joint_resampled, "
            "stratified=EXCLUDED.stratified, provenance=EXCLUDED.provenance, "
            "source=EXCLUDED.source",
            psc_rows,
        )
        conn.commit()

        cur.execute(f"SELECT count(*) FROM \"{S}\".person "
                    f"WHERE person_key_source = '{WAVE10_KEY_SOURCE}'")
        wave10_after = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM \"{S}\".person "
                    f"WHERE person_key_source = '{KEY_SOURCE}'")
        n_psc_person = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".psc_person')
        n_psc = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".psc_person '
                    "WHERE is_transliterated")
        n_translit = cur.fetchone()[0]
        cur.execute(f"SELECT count(DISTINCT nationality) FROM \"{S}\".psc_person")
        n_nat = cur.fetchone()[0]

    print(f"\n  loaded: person(psc) {n_psc_person} · psc_person {n_psc} · "
          f"{n_translit} transliterated · {n_nat} nationalities")
    print(f"  Wave 10's sec_cik rows: {wave10_before} before, "
          f"{wave10_after} after")

    failures = []
    if wave10_after != wave10_before:
        failures.append(f"Wave 10's row count moved {wave10_before} -> "
                        f"{wave10_after}; this loader must never touch them")
    if n_psc_person != len(person_rows) or n_psc != len(psc_rows):
        failures.append(f"post-load count mismatch: expected "
                        f"{len(person_rows)}/{len(psc_rows)}, store holds "
                        f"{n_psc_person}/{n_psc}")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  store matches the artifact; Wave 10's rows are untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
