#!/usr/bin/env python3
"""Prove Wave 6's `context_debt` write replaces only its OWN rows.

    uv run validators/test_context_debt_scope.py

`ccf_v2.context_debt` is an estate-wide register with three writers:

    Wave 6   loaders/load_anchors_wave6.py    covenant-shaped, subject_kind NULL
    Wave 10  loaders/load_postgres_wave10.py  subject_kind='person'
    Wave 11a generators/fetch_rating_actions.py  subject_kind='rating_action'

Until 2026-08-22 Wave 6 opened its write with an unconditional
`TRUNCATE ccf_v2.context_debt`, so any re-run of it -- on any branch, for any
reason -- destroyed the other two waves' rows. That is how the live table came
to hold 1 row where the Wave 11a artifact expects 169. Full
record: known-issues.md §12.8.

**Why this file has a falsification arm.** Wave 12's dominant defect was
checks that pass because they are not looking at anything (known-issues.md
§12). A test that only asserts "the scoped DELETE spares the person row" would
pass just as happily against a DELETE that spares everything, or against no
DELETE at all. So `check_falsification` runs the ORIGINAL `TRUNCATE` through
the identical assertions and requires them to FAIL. If that arm ever goes
green, this file has stopped distinguishing the fix from the defect and is
decoration.

Nothing here touches the real table: both statements run against a TEMP table
built with `LIKE ... INCLUDING ALL`, so the real schema (including Wave 10's
partial unique index) is under test while the real rows are untouched.
"""

from __future__ import annotations

import sys

from ccf.config import PG_SCHEMA_V2, pg_connect
from loaders.load_anchors_wave6 import DEBT_OWNED_BY_WAVE6

#: One sentinel per writer, so a statement that spares the wrong territory is
#: visible rather than averaged away.
SENTINELS = [
    # (accession,        covenant_type, subject_kind,    subject_key)
    ("0000000000-00-000001", "leverage", None,            None),
    (None,                   None,       "person",        "TEST-PERSON-1"),
    (None,                   None,       "rating_action", "TEST-RATING-1"),
]


def _seed(cur, table: str) -> None:
    cur.execute(f"DELETE FROM {table}")
    cur.executemany(
        f"INSERT INTO {table} (accession, covenant_type, reason, recorded_at, "
        "subject_kind, subject_key) VALUES (%s,%s,'scope test',current_date,%s,%s)",
        SENTINELS)


def _survivors(cur, table: str) -> set[str]:
    """What is left, labelled by territory rather than by row id."""
    cur.execute(f"SELECT subject_kind FROM {table}")
    return {r[0] or "covenant" for r in cur.fetchall()}


def _assertions(survivors: set[str]) -> list[tuple[str, bool]]:
    """The claims. Run against BOTH statements; the old one must fail them."""
    return [
        ("Wave 10's person rows survive a Wave 6 re-run",
         "person" in survivors),
        ("Wave 11a's rating_action rows survive a Wave 6 re-run",
         "rating_action" in survivors),
        ("Wave 6's own covenant rows are cleared, so the re-run replaces "
         "rather than duplicates them",
         "covenant" not in survivors),
    ]


def _run(cur, table: str, statement: str) -> set[str]:
    _seed(cur, table)
    cur.execute(statement)
    return _survivors(cur, table)


def check_scoped_delete(cur, table: str) -> list[tuple[str, bool]]:
    survivors = _run(
        cur, table, f"DELETE FROM {table} WHERE {DEBT_OWNED_BY_WAVE6}")
    return _assertions(survivors)


def check_falsification(cur, table: str) -> list[tuple[str, bool]]:
    """The arm that proves the arm above is looking at something.

    Runs the pre-fix `TRUNCATE` through the SAME assertions. Every claim about
    a surviving row MUST fail; if any survives a TRUNCATE, the assertion was
    never reading the table.
    """
    survivors = _run(cur, table, f"TRUNCATE {table}")
    outcomes = _assertions(survivors)
    kept = [(label, ok) for label, ok in outcomes if "survive" in label]
    return [
        (f"falsification: TRUNCATE fails -- {label}", not ok)
        for label, ok in kept
    ] + [
        ("falsification: TRUNCATE leaves the table empty, so no assertion "
         "above could have passed by accident", survivors == set()),
    ]


def check_source(_cur, _table) -> list[tuple[str, bool]]:
    """The defect was a literal statement; guard against its return."""
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "loaders" / "load_anchors_wave6.py"
    text = src.read_text()
    body = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#"))
    return [
        ("load_anchors_wave6.py issues no unconditional TRUNCATE",
         "TRUNCATE" not in body),
        ("its DELETE is scoped by the exported predicate, not a copy of it",
         f"WHERE {{DEBT_OWNED_BY_WAVE6}}" in body),
        ("the predicate names subject_kind, the column the partial unique "
         "index keys the other writers on",
         "subject_kind" in DEBT_OWNED_BY_WAVE6),
    ]


def main() -> int:
    cases: list[tuple[str, bool]] = []
    with pg_connect() as conn, conn.cursor() as cur:
        table = "tmp_context_debt_scope"
        cur.execute(
            f'CREATE TEMP TABLE {table} '
            f'(LIKE "{PG_SCHEMA_V2}".context_debt INCLUDING ALL)')
        for check in (check_scoped_delete, check_falsification, check_source):
            cases += check(cur, table)
        conn.rollback()

    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
