"""The cross-store views must exist, and must be recreatable on demand.

## Why this file exists

`ccf_v2.v_entity_jurisdiction` and `ccf_v2.v_ownership_cross_border` went
missing and **31 tests in `test_large_exposure.py` failed with
`UndefinedTable` stack traces** that named the view but not the remedy. The
signal was there; it was just expensive to read, and it looked like 31
unrelated breakages rather than one missing object.

The deeper problem is ownership. `ccf.views.ensure_views` is the single
definition, but nothing *guarantees* the views exist — they are rebuilt only as
a side effect of running one of three loaders that happen to drop them first
(`load_abs_overlay_wave14`, `load_bo_chains_wave13b`, `load_gleif_l2_wave13b`).
An estate that never runs those loaders again has no path back to a view that
31 checks depend on.

This file is the cheap half of the fix: it turns "31 confusing failures" into
"one failure that names the command". The expensive half — giving the views a
real owner in the load order — is a design question recorded in the handoff
rather than decided here.
"""

from __future__ import annotations

import psycopg

from ccf import config as C
from ccf.views import ensure_views

#: Every view `ccf.views.ensure_views` is responsible for. Kept as a literal
#: rather than derived from the module, so that a view silently dropped from
#: the definition is a FAILURE here and not a quietly shrinking expectation.
EXPECTED = {"v_entity_jurisdiction", "v_ownership_cross_border"}


def _views() -> set[str]:
    with psycopg.connect(**C.PG) as conn:
        cur = conn.cursor()
        cur.execute("select table_name from information_schema.views "
                    "where table_schema = %s", (C.PG_SCHEMA_V2,))
        return {r[0] for r in cur.fetchall()}


def test_the_cross_store_views_exist() -> None:
    missing = EXPECTED - _views()
    assert not missing, (
        f"missing view(s) in {C.PG_SCHEMA_V2}: {sorted(missing)}.\n"
        "Rebuild with:\n"
        "  python -c \"import psycopg, ccf.config as C; "
        "from ccf.views import ensure_views; "
        "conn=psycopg.connect(**C.PG); "
        "ensure_views(conn.cursor(), C.PG_SCHEMA_V2); conn.commit()\"\n"
        "Without them, test_large_exposure.py fails 31 times with "
        "UndefinedTable and the cause is not obvious from any one of them.")


def test_the_views_actually_return_rows() -> None:
    """Existence is not enough -- a view over zero tables would still exist.

    POSITIVE control. `ensure_views` builds the union from whichever source
    tables are present, so a view built at the wrong moment can exist and be
    empty, which is the failure mode `ccf/views.py` was written to prevent.
    """
    with psycopg.connect(**C.PG) as conn:
        cur = conn.cursor()
        cur.execute(f'select count(*) from {C.PG_SCHEMA_V2}.v_entity_jurisdiction')
        n = cur.fetchone()[0]
    assert n > 0, "v_entity_jurisdiction exists but is empty"


def test_every_declared_source_reaches_the_view() -> None:
    """The union must draw on all three sources, not a subset.

    This is the exact regression `ccf/views.py` documents: re-running an
    EARLIER loader once rebuilt the view without a later source, and nothing
    failed -- the view still existed and still returned rows, just fewer.
    Counting rows cannot catch that. Counting DISTINCT owner_table can.
    """
    with psycopg.connect(**C.PG) as conn:
        cur = conn.cursor()
        cur.execute(f"select distinct owner_table "
                    f"from {C.PG_SCHEMA_V2}.v_entity_jurisdiction")
        owners = {r[0] for r in cur.fetchall()}
    assert owners == {"legal_entity", "registry_company", "engineered_entity"}, (
        f"v_entity_jurisdiction draws on {sorted(owners)}; a source is missing, "
        "which shrinks every cross-border count downstream without failing")


def test_ensure_views_is_idempotent() -> None:
    """Running it twice must leave the same views, not drop or duplicate one.

    Named-value proof, not a count: the owner_table set must survive, because a
    rebuild that lost a source would keep the view count at 2 and still be
    wrong.
    """
    with psycopg.connect(**C.PG) as conn:
        cur = conn.cursor()
        before = _owner_set(cur)
        ensure_views(cur, C.PG_SCHEMA_V2)
        ensure_views(cur, C.PG_SCHEMA_V2)
        conn.commit()
        after = _owner_set(cur)
    assert before == after, f"rebuild changed the source set: {before} -> {after}"


def _owner_set(cur) -> set[str]:
    cur.execute(f"select distinct owner_table "
                f"from {C.PG_SCHEMA_V2}.v_entity_jurisdiction")
    return {r[0] for r in cur.fetchall()}
