#!/usr/bin/env python3
"""Wave 10 — every client-360 attribute lands in Postgres.

Single-writer discipline: Postgres owns `E` and `P`, Fluree owns `R`. A Fluree
Person node carries a URI, a type and a display label; role, title, dates and
match confidence all resolve from here.

`interaction` and `deal` are EXTENDED, not duplicated. Wave 7 created them for
mnpi-wall-enforcement with 50 and 32 rows; Wave 10 grows `interaction` to
~2,000. Growing a table another wave owns is correct; creating a second
interaction table would not be.

`context_debt` was covenant-shaped through Wave 9 (`accession` NOT NULL). A
person-subject debt row legitimately has no accession, so this load widens
`accession` to nullable rather than inventing a placeholder value. A partial
unique index on `(subject_kind, subject_key)` — scoped to rows this wave
writes, so Wave 9's covenant rows (subject_kind IS NULL) are untouched — gives
the existing bare `ON CONFLICT DO NOTHING` an arbiter; without it, every
re-run would insert a fresh batch of "no rendering found" rows for the same
135 persons.

`sees_need_to_know` on `principal` is new, additive to Wave 7. The spec asks
for interactions that are need-to-know and invisible to at least one test
principal, but `need_to_know` alone never defined *who* is blind to them.
Reusing `sees_mnpi` would conflate MNPI suppression with need-to-know
visibility — the design treats those as separate policy bindings — so this
adds a second, independent boolean instead. `PRIN-RES-002` and `PRIN-TRD-003`
(the public-side principals) are set FALSE; `PRIN-COV-001` stays TRUE.

`institutional_holder` arrives pre-aggregated: `generators/fetch_13f.py`
resolves `manager_cik` from `SUBMISSION.tsv`'s real `CIK` (not the
accession-number filing-agent prefix, which collapsed hundreds of distinct
institutions into one row and erased ~5,357 institution-issuer relationships
before this fix), resolves amendments (latest `FILING_DATE` wins, originals
it restates are discarded), and sums same-issuer line items within the one
winning accession. This loader no longer aggregates -- one input row is one
output row. `ON CONFLICT ... DO UPDATE` is kept regardless, because earlier
runs of this loader (under the old, wrong `manager_cik` derivation) already
landed rows under the wrong keys; see the task report for how those were
cleared.

    uv run loaders/load_postgres_wave10.py --dry-run
    uv run loaders/load_postgres_wave10.py

Idempotent: every write is an upsert on a natural key.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".person (
    person_key         TEXT PRIMARY KEY,
    -- 'psc' added by Wave 13b, which puts 210 pseudonymized PSC persons
    -- in this table (person_name_variant and person_crosswalk both carry
    -- an FK to person, so they could not live anywhere else). This DDL
    -- is the one a FRESH database runs, so the value has to be here as
    -- well as in Wave 13b's migration -- otherwise a rebuild from empty
    -- would create the narrow constraint and fail on load order.
    person_key_source  TEXT NOT NULL CHECK (person_key_source IN ('sec_cik','minted','psc')),
    cik                TEXT,
    name_as_filed      TEXT NOT NULL,
    display_name       TEXT NOT NULL,
    owner_kind         TEXT NOT NULL CHECK (owner_kind IN ('natural','entity')),
    name_last          TEXT, name_first TEXT, name_middle TEXT, name_suffix TEXT,
    provenance         TEXT NOT NULL,
    source             TEXT, retrieved_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "{S}".person_role (
    person_key      TEXT NOT NULL REFERENCES "{S}".person(person_key),
    lei             TEXT NOT NULL,
    role            TEXT NOT NULL
                    CHECK (role IN ('director','officer','ten_percent_owner')),
    officer_title   TEXT,
    first_seen      DATE, last_seen DATE,
    appointment_date DATE, appointment_source TEXT,
    provenance      TEXT NOT NULL,
    PRIMARY KEY (person_key, lei, role)
);

CREATE TABLE IF NOT EXISTS "{S}".person_name_variant (
    person_key   TEXT NOT NULL REFERENCES "{S}".person(person_key),
    variant_name TEXT NOT NULL,
    source       TEXT NOT NULL,
    rendering    TEXT,
    provenance   TEXT NOT NULL,
    PRIMARY KEY (person_key, variant_name, source)
);

CREATE TABLE IF NOT EXISTS "{S}".person_crosswalk (
    source_system TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    source_name   TEXT,
    person_key    TEXT NOT NULL REFERENCES "{S}".person(person_key),
    match_score   NUMERIC(6,4),
    match_band    TEXT NOT NULL
                  CHECK (match_band IN ('exact','strong','weak','false_positive')),
    is_true_match BOOLEAN NOT NULL,
    provenance    TEXT NOT NULL,
    note          TEXT,
    PRIMARY KEY (source_system, source_id, person_key)
);

CREATE TABLE IF NOT EXISTS "{S}".institutional_holder (
    lei                TEXT NOT NULL,
    manager_cik        TEXT NOT NULL,
    manager_name       TEXT,
    cusip              TEXT NOT NULL,
    value_usd          NUMERIC,
    shares             NUMERIC,
    report_period      TEXT,
    issuer_match_score NUMERIC(6,4),
    issuer_match_band  TEXT,
    provenance         TEXT NOT NULL,
    PRIMARY KEY (lei, manager_cik, cusip, report_period)
);

CREATE TABLE IF NOT EXISTS "{S}".banker (
    banker_id  TEXT PRIMARY KEY,
    full_name  TEXT NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('coverage','product','credit')),
    seniority  TEXT NOT NULL,
    desk       TEXT,
    provenance TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".coverage_assignment (
    banker_id     TEXT NOT NULL REFERENCES "{S}".banker(banker_id),
    lei           TEXT NOT NULL,
    is_primary    BOOLEAN NOT NULL DEFAULT FALSE,
    assigned_date DATE,
    provenance    TEXT NOT NULL,
    PRIMARY KEY (banker_id, lei)
);

CREATE TABLE IF NOT EXISTS "{S}".interaction_participant (
    interaction_id TEXT NOT NULL,
    party_kind     TEXT NOT NULL CHECK (party_kind IN ('person','banker')),
    party_key      TEXT NOT NULL,
    provenance     TEXT NOT NULL,
    PRIMARY KEY (interaction_id, party_kind, party_key)
);

CREATE TABLE IF NOT EXISTS "{S}".scoring_weight (
    weight_name    TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    weight_value   NUMERIC NOT NULL,
    effective_date DATE,
    provenance     TEXT NOT NULL,
    PRIMARY KEY (weight_name, policy_version)
);

ALTER TABLE "{S}".interaction ADD COLUMN IF NOT EXISTS channel TEXT;
ALTER TABLE "{S}".interaction ADD COLUMN IF NOT EXISTS subject TEXT;
ALTER TABLE "{S}".interaction ADD COLUMN IF NOT EXISTS need_to_know BOOLEAN
    NOT NULL DEFAULT FALSE;

ALTER TABLE "{S}".context_debt ADD COLUMN IF NOT EXISTS subject_kind TEXT;
ALTER TABLE "{S}".context_debt ADD COLUMN IF NOT EXISTS subject_key  TEXT;
-- A person-subject row has no filing accession; Wave 9 left this column
-- NOT NULL because every row until now was covenant-shaped.
ALTER TABLE "{S}".context_debt ALTER COLUMN accession DROP NOT NULL;
-- Arbiter for the bare ON CONFLICT DO NOTHING below. Partial so Wave 9's
-- covenant rows (subject_kind IS NULL) never participate.
CREATE UNIQUE INDEX IF NOT EXISTS ux_context_debt_subject
    ON "{S}".context_debt (subject_kind, subject_key)
    WHERE subject_kind IS NOT NULL;

-- Additive: a third, independent policy binding alongside entitlement scope
-- and MNPI suppression. See module docstring.
ALTER TABLE "{S}".principal ADD COLUMN IF NOT EXISTS sees_need_to_know BOOLEAN
    NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS ix_person_role_lei      ON "{S}".person_role (lei);
CREATE INDEX IF NOT EXISTS ix_participant_party    ON "{S}".interaction_participant (party_kind, party_key);
CREATE INDEX IF NOT EXISTS ix_interaction_lei_date ON "{S}".interaction (lei, interaction_date DESC);
"""


#: The `context_debt.reason` a roster member with no located rendering is
#: recorded with. A module constant, NOT an inline literal, because
#: `loaders/restore_context_debt.py` replays these rows from the same
#: artifacts this loader reads and must write the identical sentence -- a
#: copy is how Wave 11a shipped 134 rows describing a superseded gate across
#: three fix rounds (known-issues.md §9.1).
REASON_NO_RENDERING = (
    "no DEF 14A or 8-K rendering found for a Form 4 roster member; "
    "bounded search returned nothing, so no variant is asserted")


def load(path: str, key: str):
    return json.loads((SCREEN / path).read_text())[key]


def earliest_appointment(appointments: list[dict]) -> dict[tuple[str, str], dict]:
    """One appointment per (person_key, lei): the earliest by appointment_date.

    `person_role` carries a single row per (person_key, lei, role) with no
    time dimension, so only one appointment record can attach to it. 1,564
    appointment rows collapse to 542 distinct (person_key, lei) pairs — 332 of
    those pairs carry more than one 8-K Item 5.02 event (re-appointments,
    title changes). Folding with a plain dict comprehension keeps whichever
    record happens to appear last in file order, an accident of generation
    order rather than a considered choice, and is silently order-dependent.
    This keeps the earliest appointment_date explicitly, independent of input
    order.

    That earliest date is NOT "the date of original appointment to the
    role" — it cannot be. `fetch_8k502.py --max-per-issuer 12` only walks the
    12 most recent 8-Ks per issuer, so the earliest date reachable here is
    bounded by the earliest fetched filing, not the earliest one that exists.
    The search is also whole-filing-text on a roster surname rather than
    scoped to Item 5.02, so the value really means "filing date of an Item
    5.02-flagged 8-K somewhere mentioning this surname". See
    known-issues.md §8.13 for the 51 rows this makes self-contradictory
    (appointment_date after first_seen, nulled by this loader) and the 24
    that sit at a surname collision (left standing).
    """
    best: dict[tuple[str, str], dict] = {}
    for a in appointments:
        key = (a["person_key"], a["lei"])
        current = best.get(key)
        if current is None or a["appointment_date"] < current["appointment_date"]:
            best[key] = a
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    persons = load("wave10_persons.json", "persons")
    variants = load("wave10_name_variants.json", "variants")
    appointments = load("wave10_appointments.json", "appointments")
    holders = load("wave10_holders.json", "holders")
    crosswalk = load("wave10_crosswalk.json", "rows")
    coverage = json.loads((SCREEN / "wave10_coverage.json").read_text())

    counts = {
        "person": len(persons), "person_role": sum(len(p["roles"]) for p in persons),
        "person_name_variant": len(variants), "person_crosswalk": len(crosswalk),
        "institutional_holder": len(holders), "banker": len(coverage["bankers"]),
        "coverage_assignment": len(coverage["coverage_assignments"]),
        "interaction (new)": len(coverage["interactions"]),
        "interaction_participant": len(coverage["participants"]),
        "scoring_weight": len(coverage["scoring_weights"]),
    }
    for table, n in counts.items():
        print(f"  {table:26} {n:>6}")

    if args.dry_run:
        print("  [dry-run] no DDL executed, no rows written")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        cur.executemany(
            f'INSERT INTO "{S}".person (person_key, person_key_source, cik, '
            "name_as_filed, display_name, owner_kind, name_last, name_first, "
            "name_middle, name_suffix, provenance, source) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (person_key) DO UPDATE SET "
            "display_name = EXCLUDED.display_name, owner_kind = EXCLUDED.owner_kind",
            [(p["person_key"], p["person_key_source"], p["cik"], p["name_as_filed"],
              p["display_name"], p["owner_kind"], p["last"], p["first"],
              p["middle"], p["suffix"], "public", "SEC EDGAR Form 4")
             for p in persons])

        appt = earliest_appointment(appointments)
        cur.executemany(
            f'INSERT INTO "{S}".person_role (person_key, lei, role, officer_title, '
            "first_seen, last_seen, appointment_date, appointment_source, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (person_key, lei, role) DO UPDATE SET "
            "officer_title = COALESCE(EXCLUDED.officer_title, "
            f'"{S}".person_role.officer_title), '
            "last_seen = GREATEST(EXCLUDED.last_seen, "
            f'"{S}".person_role.last_seen)',
            [(p["person_key"], r["lei"], r["role"], r["officer_title"],
              r["first_seen"], r["last_seen"],
              appt.get((p["person_key"], r["lei"]), {}).get("appointment_date"),
              "8-K Item 5.02" if (p["person_key"], r["lei"]) in appt else None,
              "public")
             for p in persons for r in p["roles"]])

        # known-issues.md §8.13: fetch_8k502.py's whole-filing surname search
        # can land appointment_date on a filing about someone else's event.
        # 51 of 613 rows assert an appointment_date LATER than that same
        # row's first_seen -- i.e. the person was already observed filing in
        # the role before the "appointment" it is dated to. Self-contradictory
        # within one row, and cannot stand labelled provenance='public'.
        # Scoped and idempotent: re-running nulls the same rows every time,
        # rather than a one-off manual UPDATE that a reload would not
        # reproduce.
        cur.execute(
            f'UPDATE "{S}".person_role '
            "SET appointment_date = NULL, appointment_source = NULL "
            "WHERE appointment_source = %s AND appointment_date > first_seen",
            ("8-K Item 5.02",))
        print(f"  appointment_date nulled (self-contradictory): {cur.rowcount}")

        cur.executemany(
            f'INSERT INTO "{S}".person_name_variant '
            "(person_key, variant_name, source, rendering, provenance) "
            "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            [(v["person_key"], v["variant_name"], v["source"], v["rendering"],
              v["provenance"]) for v in variants])

        cur.executemany(
            f'INSERT INTO "{S}".person_crosswalk (source_system, source_id, '
            "source_name, person_key, match_score, match_band, is_true_match, "
            "provenance, note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (source_system, source_id, person_key) DO UPDATE SET "
            "match_band = EXCLUDED.match_band, match_score = EXCLUDED.match_score",
            [(c["source_system"], c["source_id"], c["source_name"], c["person_key"],
              c["match_score"], c["match_band"], c["is_true_match"],
              c["provenance"], c["note"]) for c in crosswalk])

        # generators/fetch_13f.py now aggregates upstream (real manager_cik,
        # amendments resolved, same-issuer line items summed within the
        # winning accession) -- one input row is one output row here.
        #
        # `DO UPDATE` alone cannot fully repair this table: earlier loader
        # runs (before the fetch_13f.py fix) landed rows keyed on the old,
        # wrong filing-agent-derived manager_cik, and those keys mostly do
        # not match any new row's key at all -- an UPSERT would correct the
        # rows that happen to collide and leave the rest sitting beside the
        # correct rows as orphaned, wrong data. institutional_holder has no
        # other writer and nothing references it by FK, so a full
        # clear-then-reload is the correct repair and stays idempotent
        # (re-running deletes the same set and reinserts the same set).
        cur.execute(f'DELETE FROM "{S}".institutional_holder')

        # `or None` is deliberately absent below -- value_usd/shares are
        # always present ints from the generator's sum (0 is a legitimate
        # reported position, not a missing one, and `x or None` would
        # wrongly null it). `DO UPDATE` is kept even after the DELETE above
        # so a re-run stays a true upsert, not insert-only.
        cur.executemany(
            f'INSERT INTO "{S}".institutional_holder (lei, manager_cik, manager_name, '
            "cusip, value_usd, shares, report_period, issuer_match_score, "
            "issuer_match_band, provenance) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (lei, manager_cik, cusip, report_period) DO UPDATE SET "
            "manager_name = EXCLUDED.manager_name, value_usd = EXCLUDED.value_usd, "
            "shares = EXCLUDED.shares, issuer_match_score = EXCLUDED.issuer_match_score, "
            "issuer_match_band = EXCLUDED.issuer_match_band",
            [(h["lei"], h["manager_cik"], h["manager_name"], h["cusip"],
              h["value_usd"], h["shares"], h["report_period"],
              h["issuer_match_score"], h["issuer_match_band"], h["provenance"])
             for h in holders])

        cur.executemany(
            f'INSERT INTO "{S}".banker (banker_id, full_name, role, seniority, '
            "desk, provenance) VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (banker_id) DO NOTHING",
            [(b["banker_id"], b["full_name"], b["role"], b["seniority"], b["desk"],
              b["provenance"]) for b in coverage["bankers"]])

        cur.executemany(
            f'INSERT INTO "{S}".coverage_assignment (banker_id, lei, is_primary, '
            "assigned_date, provenance) VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (banker_id, lei) DO NOTHING",
            [(a["banker_id"], a["lei"], a["is_primary"], a["assigned_date"],
              a["provenance"]) for a in coverage["coverage_assignments"]])

        # Found while verifying the owner_kind fix (2026-08-18): `interaction`
        # rows share the SAME rng stream as `participants` -- allocate_interactions,
        # the per-interaction quarter/day_offset/deal_id/type draws, and the
        # participant sampling all pull sequentially from one seeded
        # random.Random. Removing an eligible person (or any other pool-size
        # change) shifts every draw AFTER that point, which rewrites deal_id,
        # interaction_type, interaction_date, and mnpi_bearing for interaction
        # ids that already existed -- not just the participants. The narrow
        # `DO UPDATE SET need_to_know, channel` used before this fix left those
        # other columns stale: a live check found 128 rows with a non-null
        # deal_id in Postgres against 79 in the freshly generated JSON. That
        # breaks "the committed artifact reproduces the loaded database" --
        # loading the same JSON into an empty database would not match what
        # was sitting here. Wave 7's 50 pre-existing `INT-` rows (no `-W10-`
        # segment) are a disjoint id space with no writer here, so the DELETE
        # is scoped to `INT-W10-%` -- the same full-clear-then-reload shape as
        # institutional_holder and interaction_participant, just narrowed to
        # the slice this loader actually owns.
        cur.execute(f'DELETE FROM "{S}".interaction WHERE interaction_id LIKE %s',
                    ("INT-W10-%",))

        cur.executemany(
            f'INSERT INTO "{S}".interaction (interaction_id, lei, deal_id, '
            "interaction_type, interaction_date, mnpi_bearing, provenance, "
            "channel, subject, need_to_know) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [(i["interaction_id"], i["lei"], i["deal_id"], i["interaction_type"],
              i["interaction_date"], i["mnpi_bearing"], i["provenance"],
              i["channel"], i["subject"], i["need_to_know"])
             for i in coverage["interactions"]])

        # interaction_participant has no other writer and, unlike person_role's
        # (person_key, lei, role) key, its (interaction_id, party_kind,
        # party_key) composite key does not stay stable across a regenerate:
        # generate_coverage.py draws participants from a seeded RNG over the
        # eligible pool, so removing or reclassifying one person (the
        # owner_kind fix in generators/form4.py) shifts every subsequent draw.
        # A re-run's rows then land under different composite keys, and
        # `ON CONFLICT DO NOTHING` alone would leave the old draw's rows
        # sitting beside the new draw's as orphaned, wrong participants. Full
        # clear-then-reload keeps this idempotent (re-running deletes and
        # reinserts the same set), same shape as the institutional_holder
        # repair above.
        cur.execute(f'DELETE FROM "{S}".interaction_participant')

        cur.executemany(
            f'INSERT INTO "{S}".interaction_participant '
            "(interaction_id, party_kind, party_key, provenance) "
            "VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            [(p["interaction_id"], p["party_kind"], p["party_key"], p["provenance"])
             for p in coverage["participants"]])

        # Design §7.2: a roster member for whom NO document rendering was found
        # is Context Debt, not a silent gap. `context_debt` was covenant-shaped
        # until this wave widened it; the register is estate-wide, so one table
        # carries both rather than each wave minting its own.
        rendered = {v["person_key"] for v in variants}
        cur.executemany(
            f'INSERT INTO "{S}".context_debt (accession, covenant_type, reason, '
            "recorded_at, subject_kind, subject_key) "
            "VALUES (%s,%s,%s,current_date,%s,%s) ON CONFLICT DO NOTHING",
            [(None, None, REASON_NO_RENDERING,
              "person", p["person_key"])
             for p in persons
             if p["owner_kind"] == "natural" and p["person_key"] not in rendered])

        cur.executemany(
            f'INSERT INTO "{S}".scoring_weight (weight_name, policy_version, '
            "weight_value, effective_date, provenance) VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (weight_name, policy_version) DO UPDATE SET "
            "weight_value = EXCLUDED.weight_value",
            [(w["weight_name"], w["policy_version"], w["weight_value"],
              w["effective_date"], w["provenance"])
             for w in coverage["scoring_weights"]])

        # Ruling beyond the brief: a third policy binding, independent of
        # sees_mnpi. See module docstring.
        cur.execute(
            f'UPDATE "{S}".principal SET sees_need_to_know = FALSE '
            "WHERE principal_id IN ('PRIN-RES-002', 'PRIN-TRD-003')"
        )

        conn.commit()

    print("  loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
