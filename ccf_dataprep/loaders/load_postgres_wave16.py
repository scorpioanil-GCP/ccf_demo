#!/usr/bin/env python3
"""Wave 16 Task 11 — load the IB perspective, weight and mandate layer.

Six new tables, per `task-11-brief.md` plus Fix Round 1 (see below):

    ib_perspective              synthetic — internal    3 rows
    ib_signal_class             synthetic — internal   11 rows
    perspective_weight          synthetic — internal   66 rows (v1 + v2)
    mandate                     synthetic — internal   40 rows
    gov_contract_concentration  public                104 rows
    ib_projection_plan          synthetic — internal    3 rows

This loader never writes a row into `projection_plan` — see Fix Round 1.

## SCOPE CORRECTION (see task-11-report.md for the full note)

The brief's Interfaces section says this task also extends `debt_instrument`
and `spread_observation`. It does not — Task 8b already created and loaded
those rows (36 `w16-i-` instruments, 17,964 spread observations). This loader
never mentions either table, let alone writes to it.

## Finding 1 — `ib_signal_class` artifact has no `provenance` field

`wave16_perspectives.json`'s `perspectives`, `weights` and `projection_plans`
arrays all carry `provenance` on every row; `signal_classes` does not — a gap
in `generators/generate_ib_perspectives.py`, not a data-content problem (every
other row in the same artifact, and every note on these eleven, is uniform
`synthetic — internal`: hand-chosen decay half-lives, nothing fetched). Rather
than silently patch a different task's already-committed generator, this
loader supplies the value explicitly at load time (`SIGNAL_CLASS_PROVENANCE`
below) and this file is the record of the gap. Flagged in the Task 11 report;
not fixed upstream.

## Finding 2, Fix Round 1 — `projection_plan` belongs to another product; use a table of our own

The first cut of this loader found that the live `projection_plan` table did
not match the brief's DDL sketch — it is Wave 7's table
(`load_mnpi_wave7.py`), built for `mnpi-wall-enforcement`, with `principal_id`
a NOT NULL foreign key into `principal`:

    projection_plan_id TEXT PRIMARY KEY
    principal_id       TEXT NOT NULL REFERENCES principal(principal_id)
    plan_version        TEXT NOT NULL
    permitted_edge_types      JSONB NOT NULL
    permitted_classifications JSONB NOT NULL
    permitted_document_types  JSONB NOT NULL
    provenance          TEXT NOT NULL

That first cut refused to fake a `principal` row for a ranking perspective —
correct — but then made `principal_id` and the three `permitted_*` columns
nullable and stored Wave 16's rows in the *same table* anyway. That was
wrong, and a controller ruling reverted it. Two reasons:

  1. `principal_id NOT NULL` was an invariant of Wave 7's table: "every
     projection plan belongs to a principal." Making it nullable makes that
     false for the whole table, silently, for every future reader —
     including one already written (`validators/projection.py`, which joins
     `principal JOIN projection_plan USING (principal_id)`). An inner join
     drops Wave 16's rows without complaint; an outer join would surface them
     as MNPI-wall plans with no principal, which they are not.
  2. It left the table holding two disjoint row shapes — Wave 7 rows with
     `principal_id` set and `perspective_id` NULL, Wave 16 rows the exact
     inverse — so every future consumer has to discriminate between them
     just to use the table at all.

§C assigns the ProjectionPlan concept to Postgres. It never assigned it to
*that* table. Single-writer discipline says `mnpi-wall-enforcement` owns
`projection_plan`; weakening its constraints to make room for an unrelated
product's rows is the same class of harm as writing into another wave's
table directly, by a different route — the debt-ladder task (8b) avoided
exactly this by using its own id prefix and its own table, and that is the
precedent this loader now follows too.

**What this loader does instead:**

  - creates `ib_projection_plan`, a table Wave 16 owns outright (DDL below,
    with the same reasoning recorded on the table itself);
  - moves the three `PP-IB-*` rows into it;
  - DELETEs those same three rows out of `projection_plan`, by their three
    explicit ids — never a `LIKE` or other broad predicate, so a rerun can
    never remove a row this loader did not itself add;
  - restores `projection_plan`'s original shape: drops the two columns the
    first cut added (`perspective_id`, `permitted_signal_types`) and puts
    `principal_id` / `permitted_edge_types` / `permitted_classifications` /
    `permitted_document_types` back to NOT NULL;
  - verifies Wave 7's three rows are byte-identical afterwards by naming a
    value, not by counting rows — a count cannot see a column silently
    nulled out and back.

If restoring NOT NULL ever fails, that means some row *other than* the three
this loader deleted is now non-conforming — a bigger finding than this one —
and the loader stops and reports rather than working around it.

    uv run loaders/load_postgres_wave16.py --dry-run
    uv run loaders/load_postgres_wave16.py

Idempotent: every upsert keys on its natural primary key
(`(perspective_id, signal_type, weight_version)` for `perspective_weight`,
`(lei, award_id)` for `gov_contract_concentration`, the bare id elsewhere) and
sets every non-key column on conflict. The `projection_plan` restoration
statements (DROP COLUMN IF EXISTS, DELETE ... WHERE id IN (three explicit
ids), SET NOT NULL) are themselves idempotent — a second run finds nothing
left to undo and no NULLs left to reject.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.currency import verify_current

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

#: Every `ib_projection_plan` row this loader writes must carry this
#: prefix -- the same guard `loaders/load_debt_ladder_wave16.py` (:53-59)
#: has and this path lacked. `plan_ids` is later used to DELETE the
#: matching Fix-Round-1 rows out of a DIFFERENT table (`projection_plan`,
#: Wave 7's), so an artifact-derived id that drifted outside this
#: namespace would delete whatever row it happened to match there instead
#: of failing loudly here.
PLAN_ID_PREFIX = "PP-IB-"

# Finding 1 (see module docstring). Every signal_class row in the artifact
# is a hand-chosen decay half-life, not a fetched value — uniform with every
# other row in this artifact, all of which are `synthetic — internal`.
SIGNAL_CLASS_PROVENANCE = "synthetic — internal"

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".ib_perspective (
    perspective_id  TEXT PRIMARY KEY,
    label           TEXT NOT NULL,
    ranks_on        TEXT NOT NULL,
    provenance      TEXT NOT NULL
);

-- lambda_c lives HERE and only here. Storing it per (perspective, signal_type)
-- would write every value three times and let the copies drift silently.
CREATE TABLE IF NOT EXISTS "{S}".ib_signal_class (
    signal_type     TEXT PRIMARY KEY,
    half_life_days  INTEGER NOT NULL CHECK (half_life_days > 0),
    note            TEXT NOT NULL,
    provenance      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".perspective_weight (
    perspective_id  TEXT NOT NULL REFERENCES "{S}".ib_perspective(perspective_id),
    signal_type     TEXT NOT NULL REFERENCES "{S}".ib_signal_class(signal_type),
    weight_version  TEXT NOT NULL,
    weight          NUMERIC NOT NULL CHECK (weight >= 0),
    rationale       TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    PRIMARY KEY (perspective_id, signal_type, weight_version)
);

CREATE TABLE IF NOT EXISTS "{S}".mandate (
    mandate_id      TEXT PRIMARY KEY,
    lei             TEXT NOT NULL,
    mandate_type    TEXT NOT NULL,
    stage           TEXT NOT NULL,
    opened_date     TEXT NOT NULL,
    stated_appetite TEXT,
    last_outcome    TEXT,
    provenance      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".gov_contract_concentration (
    lei             TEXT NOT NULL,
    recipient_name  TEXT NOT NULL,
    award_id        TEXT NOT NULL,
    awarding_agency TEXT,
    start_date      TEXT,
    obligated_usd   NUMERIC,
    -- USASpending has no LEI and no CIK. Every row is a name judgement, and
    -- says so rather than presenting itself as a resolved join.
    match_band      TEXT NOT NULL CHECK (match_band IN ('exact','verified-subsidiary')),
    verified_against TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    PRIMARY KEY (lei, award_id)
);

-- Fix Round 1: a table Wave 16 owns outright, instead of writing into
-- Wave 7's `projection_plan` (mnpi-wall-enforcement). §C assigns the
-- ProjectionPlan CONCEPT to Postgres; it never assigned it to that specific
-- table, and that table's principal_id / permitted_edge_types /
-- permitted_classifications / permitted_document_types columns encode a
-- different product's vocabulary (wall-crossing principals and RDF edge
-- types), not a ranking perspective's permitted signal-type list. Reusing
-- it would have meant either faking a `principal` row for "M&A originator"
-- (misrepresents a ranking perspective as a wall-crossing role) or relaxing
-- NOT NULL on another product's table (breaks its "every plan has a
-- principal" invariant for every future reader, per Fix Round 1's ruling).
-- A separate table, keyed and owned by us, avoids both.
CREATE TABLE IF NOT EXISTS "{S}".ib_projection_plan (
    projection_plan_id     TEXT PRIMARY KEY,
    perspective_id          TEXT NOT NULL
                            REFERENCES "{S}".ib_perspective(perspective_id),
    plan_version            TEXT NOT NULL,
    permitted_signal_types  JSONB NOT NULL,
    provenance              TEXT NOT NULL
);
"""

CURRENCY_NOTES: list[str] = []


def load(name: str) -> dict:
    """Read one artifact, refusing a STALE one (`ccf/currency.py`)."""
    doc, note = verify_current(name)
    CURRENCY_NOTES.append(note)
    return doc


def build_rows(perspectives_doc: dict, mandates_doc: dict, usaspending_doc: dict):
    perspective_rows = [
        (p["perspective_id"], p["label"], p["ranks_on"], p["provenance"])
        for p in perspectives_doc["perspectives"]
    ]

    signal_class_rows = [
        (c["signal_type"], c["half_life_days"], c["note"],
         SIGNAL_CLASS_PROVENANCE)
        for c in perspectives_doc["signal_classes"]
    ]

    weight_rows = [
        (w["perspective_id"], w["signal_type"], w["weight_version"],
         w["weight"], w["rationale"], w["provenance"])
        for w in perspectives_doc["weights"]
    ]

    plan_rows = [
        (p["projection_plan_id"], p["perspective_id"], p["plan_version"],
         list(p["permitted_signal_types"]), p["provenance"])
        for p in perspectives_doc["projection_plans"]
    ]

    mandate_rows = [
        (m["mandate_id"], m["lei"], m["mandate_type"], m["stage"],
         m["opened_date"], m.get("stated_appetite"), m.get("last_outcome"),
         m["provenance"])
        for m in mandates_doc["mandates"]
    ]

    awards = usaspending_doc["awards"]
    # gov_contract_concentration's CHECK admits only these two bands. If the
    # artifact ever carries a third, that is a real finding about the
    # artifact, not a reason to widen the constraint.
    allowed_bands = {"exact", "verified-subsidiary"}
    bad_bands = sorted({a["match_band"] for a in awards} - allowed_bands)
    if bad_bands:
        raise RuntimeError(
            f"refusing to load: wave16_usaspending.json contains match_band "
            f"value(s) not admitted by the CHECK constraint: {bad_bands}. "
            f"Widening the constraint to fit the data is the wrong fix — "
            f"this is a real finding about the artifact."
        )

    award_rows = [
        (a["lei"], a["recipient_name"], a["award_id"], a.get("awarding_agency"),
         a.get("start_date"), a.get("obligated_usd"), a["match_band"],
         a["verified_against"], a["provenance"])
        for a in awards
    ]

    return (perspective_rows, signal_class_rows, weight_rows, plan_rows,
            mandate_rows, award_rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    perspectives_doc = load("wave16_perspectives.json")
    mandates_doc = load("wave16_mandates.json")
    usaspending_doc = load("wave16_usaspending.json")

    (perspective_rows, signal_class_rows, weight_rows, plan_rows,
     mandate_rows, award_rows) = build_rows(
        perspectives_doc, mandates_doc, usaspending_doc)

    band_counts = Counter(r[6] for r in award_rows)
    plan_ids = [p[0] for p in plan_rows]

    bad_plan_ids = [pid for pid in plan_ids if not pid.startswith(PLAN_ID_PREFIX)]
    if bad_plan_ids:
        raise RuntimeError(
            f"refusing to load: {len(bad_plan_ids)} projection_plan id(s) "
            f"do not carry the {PLAN_ID_PREFIX!r} prefix -- this loader "
            "later DELETEs matching ids out of Wave 7's projection_plan "
            f"table and must never touch another wave's namespace: "
            f"{bad_plan_ids[:5]}")

    print(f"Wave 16 Task 11 — load into {S}\n")
    print("  artifact currency:")
    for note in CURRENCY_NOTES:
        print(f"    {note}")
    print()
    print(f"  ib_perspective              {len(perspective_rows):>6}")
    print(f"  ib_signal_class             {len(signal_class_rows):>6}")
    print(f"  perspective_weight          {len(weight_rows):>6}")
    print(f"  ib_projection_plan          {len(plan_rows):>6}  {plan_ids}")
    print(f"  mandate                     {len(mandate_rows):>6}")
    print(f"  gov_contract_concentration  {len(award_rows):>6}  "
          f"(match_band: {dict(band_counts)})")

    expected = {
        "ib_perspective": (len(perspective_rows), 3),
        "ib_signal_class": (len(signal_class_rows), 11),
        "perspective_weight": (len(weight_rows), 66),
        "ib_projection_plan": (len(plan_rows), 3),
        "mandate": (len(mandate_rows), 40),
        "gov_contract_concentration": (len(award_rows), 104),
    }
    mismatches = {k: v for k, v in expected.items() if v[0] != v[1]}
    if mismatches:
        raise RuntimeError(f"row-count mismatch vs. artifact expectation: "
                            f"{mismatches}")

    if args.dry_run:
        print("\n  [dry-run] no DDL executed, no rows written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        cur.executemany(
            f'INSERT INTO "{S}".ib_perspective '
            "(perspective_id, label, ranks_on, provenance) "
            "VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (perspective_id) DO UPDATE SET "
            "label=EXCLUDED.label, ranks_on=EXCLUDED.ranks_on, "
            "provenance=EXCLUDED.provenance",
            perspective_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".ib_signal_class '
            "(signal_type, half_life_days, note, provenance) "
            "VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (signal_type) DO UPDATE SET "
            "half_life_days=EXCLUDED.half_life_days, note=EXCLUDED.note, "
            "provenance=EXCLUDED.provenance",
            signal_class_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".perspective_weight '
            "(perspective_id, signal_type, weight_version, weight, "
            " rationale, provenance) VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (perspective_id, signal_type, weight_version) "
            "DO UPDATE SET weight=EXCLUDED.weight, "
            "rationale=EXCLUDED.rationale, provenance=EXCLUDED.provenance",
            weight_rows,
        )

        # Fix Round 1: ib_projection_plan is OURS. Ordinary keyed upsert.
        cur.executemany(
            f'INSERT INTO "{S}".ib_projection_plan '
            "(projection_plan_id, perspective_id, plan_version, "
            " permitted_signal_types, provenance) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (projection_plan_id) DO UPDATE SET "
            "perspective_id=EXCLUDED.perspective_id, "
            "plan_version=EXCLUDED.plan_version, "
            "permitted_signal_types=EXCLUDED.permitted_signal_types, "
            "provenance=EXCLUDED.provenance",
            [(pid, persp, ver, json.dumps(sig_types), prov)
             for pid, persp, ver, sig_types, prov in plan_rows],
        )

        cur.executemany(
            f'INSERT INTO "{S}".mandate '
            "(mandate_id, lei, mandate_type, stage, opened_date, "
            " stated_appetite, last_outcome, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (mandate_id) DO UPDATE SET "
            "lei=EXCLUDED.lei, mandate_type=EXCLUDED.mandate_type, "
            "stage=EXCLUDED.stage, opened_date=EXCLUDED.opened_date, "
            "stated_appetite=EXCLUDED.stated_appetite, "
            "last_outcome=EXCLUDED.last_outcome, "
            "provenance=EXCLUDED.provenance",
            mandate_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".gov_contract_concentration '
            "(lei, recipient_name, award_id, awarding_agency, start_date, "
            " obligated_usd, match_band, verified_against, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (lei, award_id) DO UPDATE SET "
            "recipient_name=EXCLUDED.recipient_name, "
            "awarding_agency=EXCLUDED.awarding_agency, "
            "start_date=EXCLUDED.start_date, "
            "obligated_usd=EXCLUDED.obligated_usd, "
            "match_band=EXCLUDED.match_band, "
            "verified_against=EXCLUDED.verified_against, "
            "provenance=EXCLUDED.provenance",
            award_rows,
        )

        # --- Fix Round 1: undo the first cut's changes to projection_plan --
        #
        # FINAL FIX WAVE, item 8: `DROP COLUMN IF EXISTS` is not an
        # ownership guard -- it drops whatever carries that name, forever,
        # on every load, whether or not THIS loader is the one that put it
        # there. Checked live instead: the whole remediation (delete our
        # three rows, drop the two stray columns, restore NOT NULL) now
        # only runs the one time it is still needed. Once the columns are
        # gone, every later run is a no-op that never touches Wave 7's
        # table again.
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = 'projection_plan' "
            "AND column_name IN ('perspective_id', 'permitted_signal_types')",
            (S,),
        )
        stray_columns = {r[0] for r in cur.fetchall()}

        if stray_columns:
            # Delete precisely the three rows this loader itself added, by
            # their explicit ids — never a LIKE or other broad predicate,
            # so a rerun (or a future bug) can never remove a row this
            # loader does not own.
            cur.execute(
                f'DELETE FROM "{S}".projection_plan '
                "WHERE projection_plan_id = ANY(%s)",
                (plan_ids,),
            )
            deleted = cur.rowcount
            print(f"\n  projection_plan: deleted {deleted} PP-IB-* row(s) "
                  f"(remediation ran because {sorted(stray_columns)} "
                  "were still present)")

            cur.execute(
                f'ALTER TABLE "{S}".projection_plan '
                "DROP COLUMN IF EXISTS perspective_id, "
                "DROP COLUMN IF EXISTS permitted_signal_types"
            )

            # Restoring NOT NULL fails loudly if some row this loader did
            # not touch is non-conforming — that would be a bigger finding
            # than this one, so it is never worked around.
            try:
                cur.execute(
                    f'ALTER TABLE "{S}".projection_plan '
                    "ALTER COLUMN principal_id SET NOT NULL, "
                    "ALTER COLUMN permitted_edge_types SET NOT NULL, "
                    "ALTER COLUMN permitted_classifications SET NOT NULL, "
                    "ALTER COLUMN permitted_document_types SET NOT NULL"
                )
            except Exception as exc:
                conn.rollback()
                raise RuntimeError(
                    "STOP: could not restore NOT NULL on projection_plan "
                    "(principal_id / permitted_edge_types / "
                    "permitted_classifications / permitted_document_types). "
                    "This means a row OTHER than the three this loader "
                    "deleted is non-conforming -- a bigger finding than "
                    "Fix Round 1's, and not something to work around. "
                    f"Original error: {exc}"
                ) from exc
        else:
            print("\n  projection_plan: already clean -- Fix Round 1 "
                  "remediation not re-run (no stray columns present)")

        # projection_plan restoration proof: row count, column count, and a
        # NAMED VALUE from Wave 7's row -- a count alone cannot see a column
        # silently nulled out and restored to the same-looking NULL.
        #
        # FINAL FIX WAVE, item 8: moved BEFORE conn.commit(). This proof
        # used to run after the commit, so a failed proof raised an error
        # about a state that was already permanent -- rollback was no
        # longer available by the time the problem was discovered. Now a
        # failure here still has an open transaction to roll back.
        cur.execute(f'SELECT COUNT(*) FROM "{S}".projection_plan')
        (pp_rows,) = cur.fetchone()
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = 'projection_plan'",
            (S,),
        )
        (pp_cols,) = cur.fetchone()
        cur.execute(
            f'SELECT principal_id, permitted_edge_types FROM "{S}"'
            ".projection_plan WHERE projection_plan_id = "
            "'PLAN-coverage-banker-v1'"
        )
        wave7_row = cur.fetchone()

        if pp_rows != 3 or pp_cols != 7:
            conn.rollback()
            raise RuntimeError(
                f"PROJECTION_PLAN RESTORE CHECK FAILED: expected 3 rows / "
                f"7 columns, found {pp_rows} rows / {pp_cols} columns."
            )
        expected_wave7 = (
            "PRIN-COV-001",
            ["owns", "controls", "hasDealEngagement", "hasInteraction",
             "hasMnpiEngagement"],
        )
        if wave7_row is None or tuple(wave7_row) != expected_wave7:
            conn.rollback()
            raise RuntimeError(
                f"PROJECTION_PLAN RESTORE CHECK FAILED: "
                f"PLAN-coverage-banker-v1 expected {expected_wave7}, "
                f"found {wave7_row}."
            )

        conn.commit()

        print()
        for table in ("ib_perspective", "ib_signal_class",
                      "perspective_weight", "ib_projection_plan", "mandate",
                      "gov_contract_concentration"):
            cur.execute(f'SELECT COUNT(*) FROM "{S}".{table}')
            print(f"  {table:28} store count: {cur.fetchone()[0]}")
        print(f"  {'projection_plan (restored)':28} store count: "
              f"{pp_rows} rows, {pp_cols} columns")
        print(f"  {'  Wave 7 named-value check':28} "
              f"PLAN-coverage-banker-v1 -> {wave7_row}")

    print("\n  loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
