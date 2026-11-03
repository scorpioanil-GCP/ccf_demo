#!/usr/bin/env python3
"""Wave 19 Postgres -- the units repair, proposals, and ProjectionPlans.

The units repair comes first and everything else in the wave depends on it.
`bank_capital` and `member_call_report` are sourced from FDIC BankFind, which
publishes in THOUSANDS of dollars. `facility.commitment_amount` is in dollars.
`large-exposure-rwa-concentration` divides one by the other on every figure it
produces, so an unrecorded unit is a 1,000x error in the whole product.

The check already on `bank_capital` verifies tier 1 / RWA against the filed
CET1 ratio. It passes with or without the defect, because a ratio is
unit-invariant -- both operands carry the same unit and it cancels. The
magnitude assertion below does not cancel, and that is the whole point of it.

## Task 12 addition -- `large_exposure_projection_plan`

§C assigns a `ProjectionPlan` per perspective to Postgres. **`ProjectionPlan`
is a name collision with an SDK Protocol entity** (typed, composable
Traversal/Temporal/Policy/Similarity primitives, resolved through an
operator registry, executed in the Data Plane at request time -- see
CLAUDE.md's "What 'operator' means" note). The three rows this loader
writes are **catalog data describing what each perspective would
receive** -- nothing more. They do not resolve, do not assemble, and do
not run at request time. Stated here, in the table's own `COMMENT ON
TABLE`, and it will be stated again wherever Task 16 registers this
table in `conditions.py` -- three places, per the brief, because a reader
can land on any one of them without the other two.

The three rows are not interchangeable. `credit-officer` and `committee`
never request methodology or replay attribution; `examiner` carries both,
and *names* the two `doc_type='methodology'` documents Task 10 wrote to
MongoDB (`large-exposure-methodology-concentration`,
`large-exposure-methodology-replay-attribution`) rather than pointing at
them -- resolving that name into an actual fetch is exactly the runtime
behaviour this project does not build. `load_projection_plans()` verifies
both ids are live in Mongo before writing the examiner row, the same "a
citation is a claim, verify it" discipline `generate_limit_envelope.py`
uses for its regime citations -- naming a document that does not exist
would be a claim this loader could not back up.

## Task 13 addition -- `exposure_proposal`

Section 6 of `docs/wave19-design.md` rejected inventing ~$74bn of booked
exposure to demonstrate a breach. `generators/generate_proposals.py` builds
two hypothetical proposals, sized against the live estate; this loader
writes them into their **own** table, never into `facility` -- a proposal
landing in `facility` would recreate exactly the booked-exposure inflation
the design rejected, and move every portfolio total in the estate silently.

`assert_booked_total_unchanged()` runs **before and after** the proposal
write, checking both the summed commitment amount and the row count of
`ccf_v2.facility` against the exact figures measured 2026-08-27, before this
wave touched anything. Both are asserted because they fail differently: a
proposal mistakenly inserted as a facility row moves both; a proposal that
overwrote an existing row's amount in place would move only the sum -- a
row-count check alone would not notice.

    uv run loaders/load_wave19_postgres.py
"""
from __future__ import annotations

import json
import sys

from ccf.config import PG_SCHEMA_V2 as S, REPO_ROOT, mongo_db, pg_connect

UNIT_DDL = f"""
ALTER TABLE "{S}".bank_capital
    ADD COLUMN IF NOT EXISTS unit text NOT NULL DEFAULT 'USD_THOUSANDS';
COMMENT ON COLUMN "{S}".bank_capital.unit IS
    'Unit of every money column in this row. FDIC BankFind reports in '
    'thousands of dollars; ccf_v2.facility is in dollars. Recorded because '
    'the ratio checks on this table cannot observe the difference.';

ALTER TABLE "{S}".member_call_report
    ADD COLUMN IF NOT EXISTS unit text NOT NULL DEFAULT 'USD_THOUSANDS';
COMMENT ON COLUMN "{S}".member_call_report.unit IS
    'Unit of every money column in this row. See bank_capital.unit.';
"""

#: See docs/wave19-design.md section 3 for how this figure was chosen. It is
#: measured against the estate's own population, not guessed.
ASSETS_FLOOR_USD = 10_000_000_000
REPORTING_BANK_RSSD = "852218"
REPORTING_BANK_BAND_USD = (1_000_000_000_000, 10_000_000_000_000)

# --------------------------------------------------------------------------
# Task 12 -- large_exposure_projection_plan
# --------------------------------------------------------------------------

PROJECTION_PLAN_DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".large_exposure_projection_plan (
    plan_id                     TEXT PRIMARY KEY,
    perspective                 TEXT NOT NULL UNIQUE
        CHECK (perspective IN ('credit-officer', 'committee', 'examiner')),
    elements_included           TEXT[] NOT NULL,
    carries_methodology         BOOLEAN NOT NULL,
    carries_replay_attribution  BOOLEAN NOT NULL,
    provenance                  TEXT NOT NULL
);
COMMENT ON TABLE "{S}".large_exposure_projection_plan IS
    'Catalog data describing what each perspective would receive. NOT an SDK '
    'ProjectionPlan: does not resolve, does not assemble, does not run at '
    'request time. §C assigns the element to Postgres; this table holds it.';
"""

#: Two `doc_type='methodology'` documents Task 10 wrote to MongoDB. The
#: examiner ProjectionPlan NAMES these -- see `verify_methodology_docs()`
#: below -- and never resolves or fetches them; that is runtime SDK
#: behaviour this project does not build.
METHODOLOGY_DOC_IDS = (
    "large-exposure-methodology-concentration",
    "large-exposure-methodology-replay-attribution",
)

#: (perspective, elements_included, carries_methodology,
#:  carries_replay_attribution, provenance)
#:
#: The three `elements_included` lists are pairwise distinct SETS, which is
#: what Task 15's `projection_plans_differ` floor checks -- not merely that
#: three rows exist. `credit-officer` is the narrowest, obligor/facility
#: level view a line credit officer works from day to day. `committee` is
#: the aggregated, group-level view a credit committee decisions against --
#: broader than credit-officer's but still no methodology or replay
#: attribution, because a committee paper states a recommendation, not how
#: the concentration figure was computed or how to reconstruct it as of a
#: past date. `examiner` is the only one that carries both: an examiner's
#: review is exactly the case where "how was this number produced, and can
#: it be reproduced as of a stated date" is the question being asked, and
#: `large-exposure-methodology-replay-attribution` is the document that
#: methodology itself.
PROJECTION_PLANS = [
    (
        "credit-officer",
        [
            "connected_group_membership",
            "single_name_exposure_position",
            "facility_terms_and_covenants",
            "proposal_intent",
        ],
        False,
        False,
        "synthetic — internal",
    ),
    (
        "committee",
        [
            "connected_group_aggregate_exposure",
            "regime_limit_summary",
            "proposal_recommendation",
            "debt_tolerance_flag",
        ],
        False,
        False,
        "synthetic — internal",
    ),
    (
        "examiner",
        [
            "connected_group_aggregate_exposure",
            "regime_version_citations",
            f"methodology_document:{METHODOLOGY_DOC_IDS[0]}",
            f"methodology_document:{METHODOLOGY_DOC_IDS[1]}",
            "replay_attribution_log",
        ],
        True,
        True,
        "synthetic — internal",
    ),
]


def verify_methodology_docs() -> None:
    """Raise if either methodology document the examiner plan NAMES is not
    actually live in MongoDB. Named, not fetched -- see the module
    docstring -- but a name pointing at nothing would be a claim this
    loader could not back up, the same failure
    `generate_limit_envelope.py::resolve_regime_versions()` refuses to let
    a citation make silently.
    """
    db = mongo_db(write=False)
    missing = [
        doc_id for doc_id in METHODOLOGY_DOC_IDS
        if db.document.count_documents(
            {"document_id": doc_id, "doc_type": "methodology"}) == 0
    ]
    if missing:
        raise AssertionError(
            f"examiner ProjectionPlan names {missing} but no "
            "doc_type='methodology' document with that document_id exists "
            "in MongoDB -- run loaders/load_regime_mongo.py (Task 10) first")


def load_projection_plans(cur) -> int:
    """Upsert the three `large_exposure_projection_plan` rows, keyed on
    `perspective` (content-derived, never a row's position in
    `PROJECTION_PLANS`). `plan_id` is derived from `perspective` rather
    than hand-typed, so the two can never drift apart.

    Idempotent: `ON CONFLICT (perspective) DO UPDATE` overwrites every
    mutable column, so a row edited directly in the database -- or left
    over from a schema this loader no longer writes -- is corrected on
    the next run rather than accumulating beside a stale value.
    """
    verify_methodology_docs()
    rows = [
        (f"LEPP-{perspective.upper()}", perspective, elements,
         carries_methodology, carries_replay_attribution, provenance)
        for (perspective, elements, carries_methodology,
             carries_replay_attribution, provenance) in PROJECTION_PLANS
    ]
    cur.executemany(
        f'INSERT INTO "{S}".large_exposure_projection_plan '
        "(plan_id, perspective, elements_included, carries_methodology, "
        " carries_replay_attribution, provenance) "
        "VALUES (%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (perspective) DO UPDATE SET "
        "plan_id=EXCLUDED.plan_id, "
        "elements_included=EXCLUDED.elements_included, "
        "carries_methodology=EXCLUDED.carries_methodology, "
        "carries_replay_attribution=EXCLUDED.carries_replay_attribution, "
        "provenance=EXCLUDED.provenance",
        rows,
    )
    sets = [frozenset(r[2]) for r in rows]
    assert len(set(sets)) == len(sets), (
        "elements_included sets are not pairwise distinct -- "
        f"{[sorted(s) for s in sets]}")
    return len(rows)


# --------------------------------------------------------------------------
# Task 13 -- exposure_proposal
# --------------------------------------------------------------------------

#: ccf_v2.facility, measured 2026-08-27 before Wave 19 wrote anything. Exact
#: integers, so the comparison in `assert_booked_total_unchanged()` is exact:
#: a proposal landing here moves the sum by billions, and a tolerance would
#: only ever hide a smaller mistake.
BOOKED_COMMITMENT_AT_WAVE19_START = 55_719_058_576
FACILITY_COUNT_AT_WAVE19_START = 60

SCREEN = REPO_ROOT / "sources" / "screening"
PROPOSALS_ARTIFACT = SCREEN / "wave19_proposals.json"

PROPOSAL_DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".exposure_proposal (
    proposal_id         TEXT PRIMARY KEY,
    subject_lei         TEXT NOT NULL,
    facility_type       TEXT NOT NULL,
    commitment_amount   NUMERIC NOT NULL,
    currency            TEXT NOT NULL,
    is_hypothetical     BOOLEAN NOT NULL DEFAULT TRUE
        CHECK (is_hypothetical),
    expected_outcome    TEXT NOT NULL
        CHECK (expected_outcome IN ('breaches', 'fits_after_mitigation', 'fits')),
    provenance          TEXT NOT NULL
);
COMMENT ON TABLE "{S}".exposure_proposal IS
    'Hypothetical exposure scenarios only. NEVER a booked facility -- never '
    'joined into, or summed with, ccf_v2.facility. expected_outcome documents '
    'INTENT ONLY; Task 15 recomputes the actual gross/net crossing from the '
    'stores and never reads this column.';
"""


def assert_booked_total_unchanged(cur) -> None:
    """Wave 19 must not change the estate's booked commitment.

    Measured 2026-08-27, before this wave: $55,719,058,576 across 60
    facilities. A proposal written into `facility` by mistake would move
    this, and a row count alone would not notice an amount changing.
    """
    cur.execute(f'SELECT COALESCE(SUM(commitment_amount), 0), COUNT(*) '
                f'FROM "{S}".facility')
    total, count = cur.fetchone()
    if float(total) != float(BOOKED_COMMITMENT_AT_WAVE19_START):
        raise AssertionError(
            f"booked commitment moved from "
            f"${BOOKED_COMMITMENT_AT_WAVE19_START/1e9:.3f}bn to "
            f"${float(total)/1e9:.3f}bn -- did a proposal land in `facility`?")
    if count != FACILITY_COUNT_AT_WAVE19_START:
        raise AssertionError(
            f"facility count moved from {FACILITY_COUNT_AT_WAVE19_START} "
            f"to {count}")


def load_proposals(cur) -> int:
    """Upsert `exposure_proposal` from the artifact
    `generators/generate_proposals.py` writes, keyed on `proposal_id`
    (content-derived from subject_lei + expected_outcome, never a row's
    position in the artifact's list).

    Idempotent: `ON CONFLICT (proposal_id) DO UPDATE` overwrites every
    mutable column, matching `load_projection_plans()`'s convention above.
    """
    if not PROPOSALS_ARTIFACT.exists():
        raise AssertionError(
            f"{PROPOSALS_ARTIFACT} missing -- run "
            "generators/generate_proposals.py first")
    doc = json.loads(PROPOSALS_ARTIFACT.read_text())
    rows = [
        (p["proposal_id"], p["subject_lei"], p["facility_type"],
         p["commitment_amount"], p["currency"], p["is_hypothetical"],
         p["expected_outcome"], p["provenance"])
        for p in doc["proposals"]
    ]
    if not all(r[5] is True for r in rows):
        raise AssertionError("a proposal in the artifact is not flagged "
                              "is_hypothetical=true -- refusing to load it")
    cur.executemany(
        f'INSERT INTO "{S}".exposure_proposal '
        "(proposal_id, subject_lei, facility_type, commitment_amount, "
        " currency, is_hypothetical, expected_outcome, provenance) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (proposal_id) DO UPDATE SET "
        "subject_lei=EXCLUDED.subject_lei, "
        "facility_type=EXCLUDED.facility_type, "
        "commitment_amount=EXCLUDED.commitment_amount, "
        "currency=EXCLUDED.currency, "
        "is_hypothetical=EXCLUDED.is_hypothetical, "
        "expected_outcome=EXCLUDED.expected_outcome, "
        "provenance=EXCLUDED.provenance",
        rows,
    )
    return len(rows)


def assert_capital_magnitudes(cur) -> None:
    """Raise if any FDIC-sourced row's assets imply a lost 1,000x factor.

    Two tiers deliberately. A single JPM-class band would be a FALSE RED on
    the 16 peer banks, which span $159.8bn to $4.09tn; a single floor low
    enough for them would still catch every 1,000x error, because the wrong
    values top out at $4.09bn.
    """
    for table in ("bank_capital", "member_call_report"):
        cur.execute(f'SELECT rssd, total_assets, unit FROM "{S}".{table}')
        rows = cur.fetchall()
        if not rows:
            raise AssertionError(
                f"{table} is empty -- this assertion would pass vacuously")
        for rssd, assets, unit in rows:
            if unit != "USD_THOUSANDS":
                raise AssertionError(f"{table} {rssd}: unit {unit!r}")
            usd = float(assets) * 1000
            if usd < ASSETS_FLOOR_USD:
                raise AssertionError(
                    f"{table} {rssd}: assets ${usd/1e9:.1f}bn below the "
                    f"${ASSETS_FLOOR_USD/1e9:.0f}bn floor -- lost 1,000x?")

    lo, hi = REPORTING_BANK_BAND_USD
    cur.execute(f'SELECT total_assets, unit FROM "{S}".bank_capital '
                "WHERE rssd = %s", (REPORTING_BANK_RSSD,))
    bank_rows = cur.fetchall()
    if not bank_rows:
        raise AssertionError("no bank_capital rows for the reporting bank")
    for assets, unit in bank_rows:
        usd = float(assets) * 1000
        if not lo <= usd <= hi:
            raise AssertionError(
                f"reporting bank: ${usd/1e9:.1f}bn outside its band")


def main() -> int:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(UNIT_DDL)
        conn.commit()
        assert_capital_magnitudes(cur)

        cur.execute(PROJECTION_PLAN_DDL)
        conn.commit()
        n_plans = load_projection_plans(cur)
        conn.commit()
        print(f"  {n_plans} large_exposure_projection_plan rows, "
              "elements_included pairwise distinct")

        assert_booked_total_unchanged(cur)  # baseline, before this task writes
        cur.execute(PROPOSAL_DDL)
        conn.commit()
        n_proposals = load_proposals(cur)
        conn.commit()
        assert_booked_total_unchanged(cur)  # still true after the write
        print(f"  {n_proposals} exposure_proposal rows -- booked commitment "
              f"unchanged at ${BOOKED_COMMITMENT_AT_WAVE19_START/1e9:.3f}bn "
              f"across {FACILITY_COUNT_AT_WAVE19_START} facilities")

        # Counted, not written: bank_capital and member_call_report OVERLAP
        # on the reporting bank (RSSD 852218 is 12 bank_capital rows AND one
        # of the 16 member_call_report institutions), so "rows" and
        # "institutions" are two different numbers and neither is the sum of
        # the two table counts taken naively. A hard-coded total here is
        # exactly the defect this loader exists to prevent: a figure nobody
        # re-checks against the data it claims to describe. See Wave 19
        # Task 1 fix round 1 -- the design doc's own "17" was wrong for the
        # same reason.
        cur.execute(f'SELECT COUNT(*) FROM "{S}".bank_capital')
        rows = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{S}".member_call_report')
        rows += cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(DISTINCT rssd) FROM ('
                    f'SELECT rssd FROM "{S}".bank_capital '
                    f'UNION SELECT rssd FROM "{S}".member_call_report) u')
        institutions = cur.fetchone()[0]
    print(f"  units recorded and magnitudes asserted on {rows} rows "
          f"across {institutions} institutions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
