#!/usr/bin/env python3
"""Wave 18 Task 5 -- Postgres DDL for `syndicated-lending-co-lender`:
institution identity (`syndicate_member`) and financial condition
(`member_call_report`). Extended by Task 6, which adds `own_position` and
`competition_law_rule` to this same `DDL` constant and `main()`. Extended
again by Task 7, which adds `syndicate_projection_plan`.

## Task 6 -- own_position and competition_law_rule

`own_position` holds JPMorgan's own filed syndicate shares, plus our
invented rating and workout posture (Ruling T6-R1, see
`generators/generate_syndicate_internal.py`): a row exists ONLY where a
filed commitment schedule names us, keyed `(facility_id, member_id)`.
`competition_law_rule` is unrelated to any single facility -- it is the
standing set of constraints on what a syndicate desk may say to a
co-lender, keyed `rule_id`.

## Task 7 -- syndicate_projection_plan

Three rows, one per `perspective` (`agent` / `participant` / `prospective`).
Own table -- not a widening of Wave 7's `projection_plan` or Wave 16's
`ib_projection_plan`, both of which key on a different product's
vocabulary; Wave 16 and 17 set the "own table, keyed `perspective`"
precedent this follows. `elements` is a JSONB array naming what that
perspective assembles -- see `generators/generate_syndicate_internal.py`'s
`PLANS` for the full per-element rationale, built vs. planned.

## Task 15 -- one guarded `context_debt` row for the unattested declaration

`ccf_v2.context_debt` is a pre-existing, 303-row table another wave owns
(serial PK, no unique constraint on `(subject_kind, subject_key)`). This
loader gains exactly one write path into it -- PREFLIGHT RULING P2 -- and
that write path is guarded: `WHERE NOT EXISTS (...)` on
`(subject_kind='federation_attestation', subject_key=declaration_id)`, so
a re-run cannot add a second row for the same declaration. `debt_id` is
never supplied; the sequence assigns it. No DDL touches this table, and
no constraint is added -- it is not this loader's table to alter, only
one row of it is this loader's to insert. The row records, on OUR side,
the peer product declaration that came back with `attestation IS NULL`
(`loaders/load_peer_wave18.py`'s `colender.peer_product_declaration`) --
the debt is ours to carry, since we are the ones choosing to compose an
unattested remote claim rather than refuse it.

## Scope: institutions, not commitments

§C assigns per-member commitment shares and disclosure envelopes to
FLUREE, not Postgres. This loader writes only institution identity
(legal name, LEI, RSSD, how the id was derived, GLEIF category, the raw
name variants it was resolved from) and FDIC Call Report financial
figures. No `commitment`, `share`, or `envelope` column exists on
`syndicate_member` -- an earlier draft of this design put them here
"for convenience", which single-writer discipline (CLAUDE.md) forbids.
A test asserts the absence.

## `lei` is nullable -- five real institutions have no GLEIF registration

Ruling T3-R1: five members are real credit funds named in a real filed
credit agreement, with no GLEIF LEI under any spelling. They are neither
dropped nor given a SYN- synthetic identifier (that format is reserved
for INVENTED entities, not real ones GLEIF simply never registered).
`lei TEXT NULL UNIQUE` still constrains the 40 real LEIs -- PostgreSQL
permits many NULLs under a UNIQUE constraint.

## No crosswalk rows -- Preflight Ruling P1

Syndicate members are counterparty institutions, not bank clients: they
have no `internal_client_id`. §C names this product's correlation key as
`facility_id` plus lender LEI and RSSD, not the crosswalk. Inserting a
crosswalk row per member would violate `conditions.py`'s
CROSSWALK_INVARIANTS["crosswalk rows pointing at no entity"], which
requires every crosswalk row to join `legal_entity` by LEI -- and these
banks are not, and will not be, in `legal_entity`. This loader never
touches `"{S}".crosswalk`, and `validators/test_syndicate.py` asserts
zero syndicate members ever land there.

## Call reports: doc-level provenance, not per-row

`sources/screening/wave18_institutions.json`'s `call_reports` array
carries only `rssd, report_date, tier1_capital, total_assets,
total_equity` -- no per-row `provenance`/`source`. The whole artifact was
built by one FDIC BankFind fetch (`doc["provenance"]`, `doc["sources"]
["rssd_and_call_report"]`), so `load_call_reports` takes those two
values once from the caller and stamps every row with them, rather than
inventing per-row fields the artifact doesn't carry.

Idempotent: `load_members` upserts on `member_id`; `load_call_reports`
on `(rssd, report_date)`. A member with no RSSD correctly has no call
report row -- that is not a gap `load_call_reports` fills.

    uv run loaders/load_postgres_wave18.py
"""

from __future__ import annotations

import json
from datetime import date

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.syndicate import WAVE18_EXCLUDED_FACILITIES

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

DDL = f'''
CREATE TABLE IF NOT EXISTS "{S}".syndicate_member (
    member_id       TEXT PRIMARY KEY,
    legal_name      TEXT NOT NULL,
    -- NULLABLE, corrected 2026-08-26 against the real Task 3 artifact.
    -- Five members are credit funds with no GLEIF registration at all
    -- (ruling T3-R1); they are real firms named in a real filing, so they
    -- are neither dropped nor given a SYN- identifier. An earlier draft of
    -- this DDL said NOT NULL and would have failed on insert.
    -- UNIQUE still holds: PostgreSQL permits many NULLs under a UNIQUE
    -- constraint, so it constrains the 40 real LEIs and ignores the rest.
    lei             TEXT NULL UNIQUE,
    rssd            TEXT NULL,
    -- Which field member_id was derived from: 'lei' or 'legal_name'.
    id_basis        TEXT NOT NULL,
    -- GLEIF entity.category. Recorded so the BRANCH-vs-GENERAL defect that
    -- bound Bank of America and Citibank to Jakarta branch registrations
    -- stays detectable rather than being fixed once and forgotten.
    gleif_category  TEXT NULL,
    raw_names       JSONB NOT NULL,
    provenance      TEXT NOT NULL,
    source          TEXT NOT NULL,
    retrieved_at    DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".member_call_report (
    rssd                TEXT NOT NULL,
    report_date         DATE NOT NULL,
    tier1_capital       NUMERIC NULL,
    total_assets        NUMERIC NULL,
    total_equity        NUMERIC NULL,
    -- Wave 19 Task 1: unit of every money column in this row. Sourced from
    -- FDIC BankFind, which reports in THOUSANDS of dollars, while
    -- ccf_v2.facility.commitment_amount is in plain dollars. See
    -- loaders/load_wave19_postgres.py::assert_capital_magnitudes.
    unit                TEXT NOT NULL DEFAULT 'USD_THOUSANDS',
    provenance          TEXT NOT NULL,
    source              TEXT NOT NULL,
    PRIMARY KEY (rssd, report_date)
);

COMMENT ON COLUMN "{S}".member_call_report.unit IS
    'Unit of every money column in this row. See bank_capital.unit.';

-- Task 6. A row exists only where a filed commitment schedule names us as
-- a lender -- see Ruling T6-R1 in generate_syndicate_internal.py. Where it
-- does not, no row is written; there is no "zero position" sentinel here.
CREATE TABLE IF NOT EXISTS "{S}".own_position (
    facility_id       TEXT NOT NULL,
    member_id         TEXT NOT NULL,
    share_usd         NUMERIC NOT NULL,
    internal_rating   TEXT NOT NULL,
    workout_posture   TEXT NOT NULL,
    as_of             DATE NOT NULL,
    provenance        TEXT NOT NULL,
    PRIMARY KEY (facility_id, member_id)
);

CREATE TABLE IF NOT EXISTS "{S}".competition_law_rule (
    rule_id       TEXT PRIMARY KEY,
    jurisdiction  TEXT NOT NULL,
    constrains    TEXT NOT NULL,
    rule_text     TEXT NOT NULL,
    provenance    TEXT NOT NULL
);

-- Task 7. Own table, not a widening of Wave 7's `projection_plan`
-- (mnpi-wall-enforcement, keyed on a wall-crossing principal_id) or Wave
-- 16's `ib_projection_plan` (an IB perspective vocabulary) -- both encode a
-- different product's vocabulary. This one keys on `perspective`, the
-- vocabulary Wave 16 and Wave 17 both used for exactly this same shape.
-- `elements` names what a perspective assembles; see
-- generators/generate_syndicate_internal.py's PLANS table for the full
-- per-element rationale (built vs. planned in the estate).
CREATE TABLE IF NOT EXISTS "{S}".syndicate_projection_plan (
    perspective   TEXT PRIMARY KEY,
    elements      JSONB NOT NULL,
    provenance    TEXT NOT NULL
);
'''


def load_members(cur, members: list[dict]) -> int:
    """Upsert `syndicate_member` rows. Owns every column in the DDL above
    and touches nothing else -- no commitment/share/envelope column
    exists here at all (those are Fluree's, per §C)."""
    rows = [(m["member_id"], m["legal_name"], m["lei"], m.get("rssd"),
              m["id_basis"], m.get("gleif_category"),
              json.dumps(m["raw_names"]), m["provenance"], m["source"],
              m["retrieved_at"]) for m in members]
    cur.executemany(
        f'INSERT INTO "{S}".syndicate_member '
        "(member_id, legal_name, lei, rssd, id_basis, gleif_category, "
        " raw_names, provenance, source, retrieved_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (member_id) DO UPDATE SET "
        "legal_name=EXCLUDED.legal_name, lei=EXCLUDED.lei, "
        "rssd=EXCLUDED.rssd, id_basis=EXCLUDED.id_basis, "
        "gleif_category=EXCLUDED.gleif_category, "
        "raw_names=EXCLUDED.raw_names, "
        "provenance=EXCLUDED.provenance, source=EXCLUDED.source, "
        "retrieved_at=EXCLUDED.retrieved_at",
        rows)
    return len(rows)


def load_call_reports(cur, reports: list[dict], provenance: str,
                       source: str) -> int:
    """Upsert `member_call_report` rows. `provenance`/`source` are taken
    once from the artifact's doc-level fields (see module docstring) and
    stamped onto every row -- the per-row dicts don't carry them.
    Idempotent on `(rssd, report_date)`."""
    rows = [(r["rssd"], r["report_date"], r.get("tier1_capital"),
              r.get("total_assets"), r.get("total_equity"),
              provenance, source) for r in reports]
    cur.executemany(
        f'INSERT INTO "{S}".member_call_report '
        "(rssd, report_date, tier1_capital, total_assets, total_equity, "
        " provenance, source) VALUES (%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (rssd, report_date) DO UPDATE SET "
        "tier1_capital=EXCLUDED.tier1_capital, "
        "total_assets=EXCLUDED.total_assets, "
        "total_equity=EXCLUDED.total_equity, "
        "provenance=EXCLUDED.provenance, source=EXCLUDED.source",
        rows)
    return len(rows)


def load_own_positions(cur, rows: list[dict]) -> int:
    """Upsert `own_position` rows, keyed `(facility_id, member_id)`. Owns
    every column in the DDL above.

    Idempotent on the primary key -- but an upsert alone is only idempotent
    for rows the CURRENT artifact still contains. A row this table already
    held from a PRIOR run of this loader, for a facility Ruling T6-R2 has
    since excluded (`ccf.syndicate.WAVE18_EXCLUDED_FACILITIES` --
    FAC-105FC5 was loaded before the ruling), is not touched by an upsert
    that no longer proposes it and would sit there indefinitely. So this
    also deletes any row for an excluded facility_id, every run, regardless
    of what `rows` contains -- the exclusion is enforced by the loader
    itself, not merely by the generator no longer emitting one."""
    cur.execute(f'DELETE FROM "{S}".own_position WHERE facility_id = ANY(%s)',
                (list(WAVE18_EXCLUDED_FACILITIES),))

    assert not any(r["facility_id"] in WAVE18_EXCLUDED_FACILITIES for r in rows), (
        "the artifact itself proposes a row for an excluded facility -- "
        "the generator is out of date with ccf.syndicate.WAVE18_EXCLUDED_FACILITIES")

    values = [(r["facility_id"], r["member_id"], r["share_usd"],
               r["internal_rating"], r["workout_posture"], r["as_of"],
               r["provenance"]) for r in rows]
    cur.executemany(
        f'INSERT INTO "{S}".own_position '
        "(facility_id, member_id, share_usd, internal_rating, "
        " workout_posture, as_of, provenance) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (facility_id, member_id) DO UPDATE SET "
        "share_usd=EXCLUDED.share_usd, "
        "internal_rating=EXCLUDED.internal_rating, "
        "workout_posture=EXCLUDED.workout_posture, "
        "as_of=EXCLUDED.as_of, provenance=EXCLUDED.provenance",
        values)
    return len(values)


def load_competition_rules(cur, rows: list[dict]) -> int:
    """Upsert `competition_law_rule` rows, keyed `rule_id`. Idempotent."""
    values = [(r["rule_id"], r["jurisdiction"], r["constrains"],
               r["rule_text"], r["provenance"]) for r in rows]
    cur.executemany(
        f'INSERT INTO "{S}".competition_law_rule '
        "(rule_id, jurisdiction, constrains, rule_text, provenance) "
        "VALUES (%s,%s,%s,%s,%s) "
        "ON CONFLICT (rule_id) DO UPDATE SET "
        "jurisdiction=EXCLUDED.jurisdiction, "
        "constrains=EXCLUDED.constrains, "
        "rule_text=EXCLUDED.rule_text, "
        "provenance=EXCLUDED.provenance",
        values)
    return len(values)


def load_projection_plans(cur, plans: list[dict]) -> int:
    """Upsert `syndicate_projection_plan` rows, keyed `perspective`. Owns
    every column in the DDL above. Idempotent on the primary key."""
    values = [(p["perspective"], json.dumps(p["elements"]), p["provenance"])
              for p in plans]
    cur.executemany(
        f'INSERT INTO "{S}".syndicate_projection_plan '
        "(perspective, elements, provenance) VALUES (%s,%s,%s) "
        "ON CONFLICT (perspective) DO UPDATE SET "
        "elements=EXCLUDED.elements, provenance=EXCLUDED.provenance",
        values)
    return len(values)


def load_context_debt(cur, declarations: list[dict],
                       recorded_at: date) -> int:
    """PREFLIGHT RULING P2: `context_debt` has a serial PK and no unique
    constraint on `(subject_kind, subject_key)`, so this insert guards
    itself with `WHERE NOT EXISTS (...)` or a re-run adds a second row.
    Never supplies `debt_id` -- the sequence assigns it. No DDL, no
    constraint: this loader owns one row, not the table.

    Writes one row per unattested declaration in the artifact -- today
    that is exactly one, by construction of Task 15's contrast case (§F:
    >= 1 unattested remote claim). Returns the number of rows actually
    inserted (0 on a re-run that finds its row already there)."""
    inserted = 0
    for d in declarations:
        if d["attestation"] is not None:
            continue
        reason = (
            f"peer product declaration {d['declaration_id']} "
            f"(counterparty {d['counterparty']}, product {d['product_id']}) "
            f"is unattested -- federation attestation absent on the "
            f"co-lender fabric, recorded as Context Debt per §F rather "
            f"than admitted as a verified claim")
        cur.execute(
            f'INSERT INTO "{S}".context_debt '
            "(reason, recorded_at, subject_kind, subject_key) "
            "SELECT %s, %s, 'federation_attestation', %s "
            "WHERE NOT EXISTS (SELECT 1 FROM \"" + S + "\".context_debt "
            "  WHERE subject_kind = 'federation_attestation' "
            "  AND subject_key = %s)",
            (reason, recorded_at, d["declaration_id"], d["declaration_id"]))
        inserted += cur.rowcount
    return inserted


def main() -> int:
    doc = json.loads((SCREEN / "wave18_institutions.json").read_text())
    members = doc["members"]
    reports = doc["call_reports"]
    provenance = doc["provenance"]
    source = doc["sources"]["rssd_and_call_report"]

    internal = json.loads((SCREEN / "wave18_internal.json").read_text())
    positions = internal["own_positions"]
    rules = internal["competition_law_rules"]
    plans = internal["projection_plans"]

    # Task 15: the peer's product declarations, read from the SAME
    # artifact `loaders/load_peer_wave18.py` loads onto the peer fabric --
    # not re-typed here. Only the unattested one produces a context_debt
    # row; `load_context_debt` filters for that itself.
    peer_doc = json.loads((SCREEN / "wave18_peer.json").read_text())
    declarations = peer_doc["declarations"]
    recorded_at = date.fromisoformat(peer_doc["as_of"])

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        n_members = load_members(cur, members)
        n_reports = load_call_reports(cur, reports, provenance, source)
        n_positions = load_own_positions(cur, positions)
        n_rules = load_competition_rules(cur, rules)
        n_plans = load_projection_plans(cur, plans)
        n_debt = load_context_debt(cur, declarations, recorded_at)
        print(f"loaded: syndicate_member {n_members}, "
              f"member_call_report {n_reports}, "
              f"own_position {n_positions}, "
              f"competition_law_rule {n_rules}, "
              f"syndicate_projection_plan {n_plans}, "
              f"context_debt (new rows) {n_debt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
