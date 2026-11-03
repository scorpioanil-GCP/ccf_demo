#!/usr/bin/env python3
"""Wave 18 Task 13 — the syndicate desk tracker, in the departmental store.

## Why this table lives in SQLite, and only here

SQLite owns the departmental slice: restricted lists, trackers, local
workbooks -- small, locally-maintained systems the fabric must reach to
enforce something no enterprise store holds. `syndicate_desk_tracker` is
the syndicate desk's own working view of the six Wave 18 credit agreements:
a per-facility flag plus a free-text note. Postgres already carries the
FORMAL record of our own participation (`own_position.internal_rating`,
`own_position.workout_posture`) and Fluree already carries the formal live
vote posture (`ex:votePosture` on FAC-A4A5EE's amendment vote). This table
is not a mirror of either -- it is the desk's own, less formal, sometimes
AHEAD-of-the-record read, and CLAUDE.md's single-writer rule means none of
it may be duplicated into the stores that own the formal version.

## The engineered row

`SDT-A4A5EE` (RB Global's revolving facility) is `synthetic — engineered`,
not `synthetic — internal` like the other eleven. Its `desk_note` records a
posture the desk holds and the credit file does not: Postgres's
`own_position` row for FAC-A4A5EE reads `internal_rating='BBB-'`,
`workout_posture='performing'`, and Fluree's live amendment vote (Task 9)
records our member node's `ex:votePosture` as `'consent'` -- both clean,
both formal, neither reflecting a lean the desk has not yet escalated. The
note states the desk is privately leaning toward WITHHOLD on a second vote
round over a covenant-cushion concern raised informally by the borrower's
treasury, a fact that exists nowhere else in the estate. `validators/
test_syndicate.py::test_tracker_is_departmental_only` proves the note text
is absent from Postgres, Fluree, and MongoDB (Ruling T13-R1) -- not merely
that no table is *named* like this one.

The other eleven rows are `synthetic — internal`: invented because a desk's
day-to-day tracking note is bank-internal by nature, not because any one of
them is engineered to prove an absence.

## Facility set -- derived, never hand-typed

The twelve `facility_id`s tracked here are every Postgres `facility` row
whose `source_document` matches one of the six Wave 18 agreements named as
keys in `ccf.syndicate.TRANCHE_TO_FACILITIES`, minus the two Ruling-T6-R2
exclusions in `ccf.syndicate.WAVE18_EXCLUDED_FACILITIES` (FAC-105FC5,
FAC-DFCB72 -- both artifacts of one Bausch parsing defect, not real
tranches). This resolves to two facilities each for RB Global, Bausch and
AHR, four for Regis (two with schedule rows, two without -- see Task 8's
own note on Regis in `ccf/syndicate.py`), one each for Paychex and Sabre --
twelve rows across six agreements, at least one per facility as required.

## Idempotent

`INSERT ... ON CONFLICT(tracker_id) DO UPDATE`, keyed on `tracker_id`, which
is content-derived (`"SDT-" + facility_id.removeprefix("FAC-")`) -- stable
across reruns and never a row's position in this file.

    uv run loaders/load_sqlite_wave18.py --dry-run
    uv run loaders/load_sqlite_wave18.py
"""

from __future__ import annotations

import argparse
import sqlite3
import sys

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import SQLITE_PATH, pg_connect
from ccf.syndicate import TRANCHE_TO_FACILITIES, WAVE18_EXCLUDED_FACILITIES

UPDATED_AT = "2026-08-26"

DDL = """
CREATE TABLE IF NOT EXISTS syndicate_desk_tracker (
    tracker_id     TEXT PRIMARY KEY,
    facility_id    TEXT NOT NULL,
    desk_note      TEXT NOT NULL,
    internal_flag  TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    provenance     TEXT NOT NULL
);
"""

# Basenames of the six Wave 18 source documents. Each `TRANCHE_TO_FACILITIES`
# key is `<cik>_<accession>_<basename>`, and the basename itself can contain
# underscores (e.g. "payx-ex10_1.htm") -- split on the first two only, so
# whatever remains matches Postgres's `facility.source_document` exactly.
WAVE18_SOURCE_DOCS = sorted(
    {key.split("_", 2)[-1] for key in TRANCHE_TO_FACILITIES})

# One desk_note per facility_id. FAC-A4A5EE (index 0 below) is the
# engineered row -- see the module docstring.
NOTES: dict[str, tuple[str, str, str]] = {
    # facility_id: (desk_note, internal_flag, provenance)
    "FAC-A4A5EE": (
        "Desk read on the RB Global revolver diverges from the formal "
        "record: our own_position shows 'performing' and the live "
        "amendment vote is recorded as consent, but a closed-door "
        "conversation with RB Global's treasury this week raised an "
        "asset-coverage cushion concern the credit file does not "
        "reflect. Desk is privately leaning toward WITHHOLD if the "
        "amendment reaches a second round. Not yet escalated to IC; "
        "formal vote record unchanged pending that escalation.",
        "reduce",
        "synthetic — engineered",
    ),
    "FAC-6F4065": (
        "Steady position on the RB Global term loan A. Consistent with "
        "the performing rating carried in our own book; no desk-level "
        "concerns beyond what the credit file already shows.",
        "hold",
        "synthetic — internal",
    ),
    "FAC-08F1D1": (
        "Tracking the Bausch term loan alongside our own watch rating. "
        "Routine desk monitoring only -- no new information beyond the "
        "credit file at this time.",
        "watch",
        "synthetic — internal",
    ),
    "FAC-E08688": (
        "Bausch Third Amendment revolver carried at watch, matching our "
        "own_position rating. Desk continuing routine monitoring; "
        "nothing to escalate this cycle.",
        "watch",
        "synthetic — internal",
    ),
    "FAC-E386A4": (
        "Paychex revolver holds cleanly at performing. Lowest-touch name "
        "on the desk's Wave 18 book; quarterly check-in only.",
        "hold",
        "synthetic — internal",
    ),
    "FAC-405B7A": (
        "No position on AHR's revolver. Desk is tracking it as a "
        "relationship-development target given the sector coverage "
        "plan; revisit if a future syndication round opens.",
        "monitor",
        "synthetic — internal",
    ),
    "FAC-2A2C38": (
        "No position on AHR's term loan. Same relationship-development "
        "rationale as the linked revolver; tracked together on the desk "
        "sheet.",
        "monitor",
        "synthetic — internal",
    ),
    "FAC-01BB3F": (
        "No position on Regis Term Loan A. Small facility, low desk "
        "priority; tracked for coverage completeness only.",
        "monitor",
        "synthetic — internal",
    ),
    "FAC-5F29AF": (
        "No position on Regis Term Loan B. Same coverage-completeness "
        "rationale as Term Loan A on this desk sheet.",
        "monitor",
        "synthetic — internal",
    ),
    "FAC-E4D2F8": (
        "No position on Regis's original Term Loan. No schedule rows in "
        "the First Amendment exhibit either, per Task 8's note -- desk "
        "has nothing new to add beyond tracking the facility exists.",
        "monitor",
        "synthetic — internal",
    ),
    "FAC-25F991": (
        "No position on Regis's Revolving Credit Facility. Tracked "
        "alongside the other three Regis facilities on this desk sheet.",
        "monitor",
        "synthetic — internal",
    ),
    "FAC-3DF1D5": (
        "No position on the Sabre term loan. Desk flags the missing "
        "commitment_amount in Postgres (a Wave 4 gap, carried forward "
        "per Task 8's report) for follow-up with the docs team; not a "
        "credit concern on the desk's part.",
        "monitor",
        "synthetic — internal",
    ),
}


def selected_facilities() -> list[str]:
    """Every Wave 18 facility_id, derived from Postgres + ccf.syndicate --
    never hand-typed. See the module docstring."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT facility_id FROM "{S}".facility '
            "WHERE source_document = ANY(%s) ORDER BY facility_id",
            (WAVE18_SOURCE_DOCS,),
        )
        ids = [r[0] for r in cur.fetchall()]
    return [f for f in ids if f not in WAVE18_EXCLUDED_FACILITIES]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    facilities = selected_facilities()
    missing = [f for f in facilities if f not in NOTES]
    assert not missing, (
        f"NOTES has no entry for {missing} -- the facility set drifted "
        "from what this loader was written against")

    rows = [
        (f"SDT-{fid.removeprefix('FAC-')}", fid, *NOTES[fid], UPDATED_AT)
        for fid in facilities
    ]

    print("Wave 18 Task 13 — SQLite load: syndicate_desk_tracker\n")
    print(f"  {len(facilities)} facilities across "
          f"{len(WAVE18_SOURCE_DOCS)} Wave 18 agreements")
    engineered = [r for r in rows if r[4] == "synthetic — engineered"]
    print(f"  {len(engineered)} engineered row(s): "
          f"{[r[1] for r in engineered]}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(SQLITE_PATH)
    con.execute(DDL)

    con.executemany(
        "INSERT INTO syndicate_desk_tracker "
        "(tracker_id, facility_id, desk_note, internal_flag, provenance, "
        " updated_at) "
        "VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(tracker_id) DO UPDATE SET "
        "facility_id=excluded.facility_id, "
        "desk_note=excluded.desk_note, "
        "internal_flag=excluded.internal_flag, "
        "provenance=excluded.provenance, "
        "updated_at=excluded.updated_at",
        rows,
    )
    con.commit()

    total = con.execute(
        "SELECT COUNT(*) FROM syndicate_desk_tracker").fetchone()[0]
    print(f"\n  loaded: {total} syndicate_desk_tracker rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
