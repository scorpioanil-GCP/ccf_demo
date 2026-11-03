#!/usr/bin/env python3
"""The narrowed crosswalk checks must still be able to fail.

Until 2026-08-24 rule #4 was enforced by one FULL OUTER JOIN: any
`legal_entity` row with no `crosswalk` row was an orphan. That was correct
while the table held only the bank's 50 obligors, and became wrong the moment
it held reference data — 103 GLEIF subsidiaries were loaded so that
`corporate-family-tree` traversal results resolve, and the bank holds no
facility, deal or coverage against any of them. Minting them internal client
ids to keep a validator quiet would have invented 103 client relationships.

Narrowing a check to accommodate new data is exactly the move that turns a
gate into decoration, so each of the three replacements is exercised here
against the LIVE database: inject one genuine violation inside a transaction,
require the count to move, roll back. Nothing is committed.

They run `conditions.CROSSWALK_INVARIANTS` itself rather than a copy. A
harness holding its own transcription of a query cannot notice the real one
drifting — the failure `conditions.py`'s own header describes, where a
validator sharing a defect with its subject agrees with itself.

    uv run --with pytest pytest validators/test_crosswalk_invariants.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import pg_connect

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "conditions", REPO / "validators" / "conditions.py")
cond = importlib.util.module_from_spec(_spec)
sys.modules["conditions"] = cond
_spec.loader.exec_module(cond)

DANGLING = "crosswalk rows pointing at no entity"
ANCHOR_UNKEYED = "anchors with no internal client id"
INTERNAL_UNKEYED = "entities with internal data, no client id"

#: A LEI in no table. 20 characters and well-formed, so nothing rejects it for
#: shape when the point is to test the JOIN.
GHOST_LEI = "ZZZZ00TESTONLY000000"


@pytest.fixture
def cur():
    """A cursor whose work is always rolled back."""
    with pg_connect() as conn:
        c = conn.cursor()
        yield c
        conn.rollback()


def count(cur, name: str) -> int:
    cur.execute(cond.CROSSWALK_INVARIANTS[name])
    return cur.fetchone()[0]


def test_all_three_invariants_hold_right_now(cur):
    """The known-good arm. Without it the injections prove nothing."""
    for name in cond.CROSSWALK_INVARIANTS:
        assert count(cur, name) == 0, f"{name} is already violated"


def test_a_client_id_pointing_at_nobody_is_caught(cur):
    before = count(cur, DANGLING)
    cur.execute(
        f'INSERT INTO "{S}".crosswalk (internal_client_id, lei, provenance, '
        f"source) VALUES ('CID-GHOST', %s, 'synthetic — internal', 'test')",
        (GHOST_LEI,))
    assert count(cur, DANGLING) == before + 1


def test_an_anchor_losing_its_client_id_is_caught(cur):
    before = count(cur, ANCHOR_UNKEYED)
    cur.execute(f'SELECT lei FROM "{S}".legal_entity WHERE is_anchor LIMIT 1')
    lei = cur.fetchone()[0]
    cur.execute(f'DELETE FROM "{S}".crosswalk WHERE lei = %s', (lei,))
    assert count(cur, ANCHOR_UNKEYED) == before + 1


def test_a_reference_entity_gaining_internal_data_is_caught(cur):
    """THE FALSIFIER for the narrowing itself.

    The tempting narrowing was "non-anchors are exempt", which would let a
    real client entity be added as a non-anchor and never be checked again.
    This check keys on where internal data ACTUALLY IS, so assigning a covering
    banker to one of the new reference subsidiaries — the cheapest way a
    reference entity becomes a client — makes it a violation immediately.
    """
    cur.execute(f'''
        SELECT e.lei FROM "{S}".legal_entity e
        LEFT JOIN "{S}".crosswalk c USING (lei)
        WHERE NOT e.is_anchor AND c.lei IS NULL LIMIT 1''')
    row = cur.fetchone()
    assert row is not None, "no unkeyed reference entity to promote"
    lei = row[0]

    assert count(cur, INTERNAL_UNKEYED) == 0
    cur.execute(f'SELECT banker_id FROM "{S}".banker LIMIT 1')
    banker = cur.fetchone()[0]
    cur.execute(
        f'INSERT INTO "{S}".coverage_assignment (banker_id, lei, is_primary, '
        f"assigned_date, provenance) VALUES (%s, %s, false, '2026-08-24', "
        f"'synthetic — internal')", (banker, lei))
    assert count(cur, INTERNAL_UNKEYED) == 1


def test_a_reference_entity_without_internal_data_is_NOT_a_violation(cur):
    """The negative control, and the whole reason the checks were narrowed.

    103 such rows exist right now. A check that flagged them would be the old
    one, and would force 103 invented client relationships to clear it.
    """
    cur.execute(f'''
        SELECT COUNT(*) FROM "{S}".legal_entity e
        LEFT JOIN "{S}".crosswalk c USING (lei)
        WHERE NOT e.is_anchor AND c.lei IS NULL''')
    assert cur.fetchone()[0] > 0, "no reference entities — arm proves nothing"
    assert count(cur, INTERNAL_UNKEYED) == 0
