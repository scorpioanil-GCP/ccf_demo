# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The cp-00…03 setup scripts refuse to run against a database that is not theirs.

`D-IMPL-379` option (b), Dave 2026-10-10 00:16 MST. The eight
`tests/examples/fixtures/cp_0[0-3]_*_{schema,rows}.sql` files drop, rebuild and
delete inside the hard-coded schema `ccf_v2` — the same schema name the curated
estate on `192.168.4.76` uses. Twice (2026-09-08 and 2026-09-22) they were run
against that estate and rebuilt eight of its tables without keys or defaults.
The session fence in `tests/conftest.py` keeps a pytest run off a curated host;
this is the second lock, inside the files themselves, so the same accident
through any other path (a hand-run `psql -f`, a scratch script, a regenerated
fixture) refuses before it writes.

The lock is the first statement of each file: a `DO` block that raises, naming
every relation in the schema that none of the eight files creates. A disposable
test database holds only those twelve tables; the real estate holds over a
hundred, so it refuses there. Each file is applied as ONE simple-query
`execute`, which Postgres runs as one implicit transaction, so a refusal leaves
nothing behind.

Three checks, in the order `D-IMPL-379` lists them:

* every file carries the lock, byte for byte the text `tools.fixture_write_lock`
  renders, as its first statement — and the regeneration tool emits the same;
* each file refuses a scratch database holding one stray table, BY NAME, and
  leaves the database untouched;
* the positive control: a clean scratch database seeds all eight in order.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.fixture_write_lock import FIXTURE_TABLES, write_lock  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
SCHEMA = "ccf_v2"

#: Seeding order: each example's schema then its rows, cp-00 first — the order
#: a session that runs every seeding module applies them in.
LOCKED_FILES = (
    "cp_00_13f_schema.sql",
    "cp_00_13f_rows.sql",
    "cp_01_counterparty_schema.sql",
    "cp_01_counterparty_rows.sql",
    "cp_02_facility_schema.sql",
    "cp_02_facility_rows.sql",
    "cp_03_census_schema.sql",
    "cp_03_census_rows.sql",
)

STRAY = "zz_curated_estate_table"


def _first_statement(text: str) -> str:
    """The file's text from its first line that is neither blank nor a comment."""
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("--"):
            return "".join(lines[index:])
    return ""


# ---------------------------------------------------------------------------
# Static: the lock is there, first, and has one authority.
# ---------------------------------------------------------------------------


def test_the_roster_is_every_seeding_file() -> None:
    """A ninth setup script added later must join the roster, or it is unlocked."""
    on_disk = sorted(p.name for p in FIXTURES.glob("cp_0[0-3]_*.sql"))
    assert on_disk == sorted(LOCKED_FILES), on_disk


def test_the_allowed_tables_are_exactly_what_the_files_create() -> None:
    """The lock's allow-list and the files' CREATE TABLEs cannot drift apart."""
    created: set[str] = set()
    for name in LOCKED_FILES:
        text = (FIXTURES / name).read_text(encoding="utf-8")
        created |= {
            m.lower()
            for m in re.findall(
                rf"(?i)create table (?:if not exists )?{SCHEMA}\.([a-z_]+)", text
            )
        }
    assert created == set(FIXTURE_TABLES), sorted(created ^ set(FIXTURE_TABLES))


@pytest.mark.parametrize("name", LOCKED_FILES)
def test_the_lock_is_the_first_statement(name: str) -> None:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    lock = write_lock(SCHEMA)
    # The lock opens with its own comment lines, which `_first_statement`
    # skips; the statement itself is its `DO` block, and the whole rendered
    # text — comments included — must sit immediately before it.
    statement = lock[lock.index("DO $ccf_write_lock$") :]
    assert _first_statement(text).startswith(statement), (
        f"{name}: the first statement is not the D-IMPL-379 write lock"
    )
    assert lock in text, f"{name}: the lock's text differs from the helper's"


def test_the_regeneration_tool_emits_the_lock() -> None:
    """`tools/dump_cp03_fixture.py` rewrites two of the eight; a regeneration
    must not silently drop the lock. Its preambles are compared with the
    committed files' opening bytes, so the tool and the files agree exactly."""
    from tools import dump_cp03_fixture as dump

    stamp = "2026-08-31"
    for name, preamble in (
        ("cp_03_census_schema.sql", dump.schema_preamble(SCHEMA, stamp)),
        ("cp_03_census_rows.sql", dump.rows_preamble(SCHEMA, stamp)),
    ):
        assert write_lock(SCHEMA) in preamble, name
        committed = (FIXTURES / name).read_text(encoding="utf-8")
        assert committed.startswith(preamble), (
            f"{name}: the committed file does not open with what the tool emits"
        )


# ---------------------------------------------------------------------------
# Live: on a disposable local Postgres, never the curated estate. Marked one by
# one rather than by module, and `psycopg` is imported inside them, so the
# database-free checks above run in the quick suite too.
# ---------------------------------------------------------------------------


def _relations(dsn: str) -> list[str]:
    import psycopg

    with psycopg.connect(dsn) as db, db.cursor() as cursor:
        cursor.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n"
            " ON n.oid = c.relnamespace WHERE n.nspname = %s"
            " AND c.relkind IN ('r','p','v','m','f') ORDER BY 1",
            (SCHEMA,),
        )
        return [row[0] for row in cursor.fetchall()]


@pytest.fixture
def scratch(postgres_dsn: str) -> Iterator[str]:
    """A clean `ccf_v2` on the session's disposable Postgres, dropped afterwards."""
    psycopg = pytest.importorskip("psycopg")
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    refuse_to_write_the_curated_estate(postgres_dsn)
    with psycopg.connect(postgres_dsn, autocommit=True) as db:
        db.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        db.execute(f"CREATE SCHEMA {SCHEMA}")
    yield postgres_dsn
    with psycopg.connect(postgres_dsn, autocommit=True) as db:
        db.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")


@pytest.mark.postgres
@pytest.mark.parametrize("name", LOCKED_FILES)
def test_a_database_that_is_not_ours_is_refused_by_name(
    scratch: str, name: str
) -> None:
    """One table no fixture creates is enough: the file raises, naming it, and
    writes nothing — the stray survives and no fixture table appears."""
    import psycopg

    with psycopg.connect(scratch, autocommit=True) as db:
        db.execute(f"CREATE TABLE {SCHEMA}.{STRAY} (id int)")
    before = _relations(scratch)

    refused: psycopg.Error | None = None
    with psycopg.connect(scratch, autocommit=True) as db, db.cursor() as cursor:
        try:
            cursor.execute((FIXTURES / name).read_text(encoding="utf-8"))
        except psycopg.Error as exc:
            refused = exc
    # A rows file run against an empty schema fails on its own (a missing
    # table) whether or not it is locked; that is not the lock refusing.
    assert refused is not None, (
        f"{name} ran to completion against a database holding {STRAY}"
    )
    assert isinstance(refused, psycopg.errors.RaiseException), (
        f"{name} failed on {type(refused).__name__}, not on the write lock:"
        f" {refused}"
    )

    message = str(refused)
    assert re.search(rf"(?<!\w){STRAY}(?!\w)", message), message
    assert "D-IMPL-379" in message, message
    assert _relations(scratch) == before == [STRAY]


@pytest.mark.postgres
def test_a_clean_scratch_database_seeds_all_eight(scratch: str) -> None:
    """Positive control: the lock does not refuse the database it exists for,
    including the second and later files, which find the earlier ones' tables."""
    import psycopg

    with psycopg.connect(scratch, autocommit=True) as db, db.cursor() as cursor:
        for name in LOCKED_FILES:
            cursor.execute((FIXTURES / name).read_text(encoding="utf-8"))
    assert set(_relations(scratch)) == set(FIXTURE_TABLES)


# ---------------------------------------------------------------------------
# D-IMPL-380 (Dave, 2026-10-10 05:34 MST): "Two separate barriers. The lock
# refuses an outside dependent. cp-03 drops without CASCADE. Each has its own
# test and its own severing." The relation-name check above inspects only
# relations INSIDE `ccf_v2`; an object in another schema that depends on one of
# the twelve tables passed it, and cp-03's `DROP TABLE ... CASCADE` then dropped
# that object (reproduced on a throwaway Postgres: views in `other`, 1 -> 0).
# Example-only: these are the cp-00..03 setup scripts and the harness that
# applies them, not the SDK.
# ---------------------------------------------------------------------------

OUTSIDE = "zz_outside_schema"
DEPENDENT = "zz_depends_on_legal_entity"
CP03_SCHEMA = "cp_03_census_schema.sql"


def test_the_regeneration_tool_drops_without_cascade() -> None:
    """`tools/dump_cp03_fixture.py::_ddl` emits a plain `DROP TABLE IF EXISTS`,
    so a drop that something else depends on fails instead of cascading."""
    from tools import dump_cp03_fixture as dump

    class _Cursor:
        def execute(self, *_args: object) -> None:
            return None

        def fetchall(self) -> list[tuple[object, ...]]:
            return [("id", "integer", None, "NO")]

    ddl = dump._ddl(_Cursor(), SCHEMA, "legal_entity")
    assert ddl.splitlines()[0] == f"DROP TABLE IF EXISTS {SCHEMA}.legal_entity;", ddl


def test_the_cp03_schema_file_drops_without_cascade() -> None:
    """The committed file carries the bytes the tool now emits: every drop is
    plain, and nothing in it cascades."""
    text = (FIXTURES / CP03_SCHEMA).read_text(encoding="utf-8")
    drops = [line for line in text.splitlines() if line.startswith("DROP TABLE")]
    assert drops, "the case was not constructed: cp-03's schema file must drop its tables"
    assert all(re.fullmatch(rf"DROP TABLE IF EXISTS {SCHEMA}\.[a-z_]+;", line) for line in drops), drops
    assert "CASCADE" not in text.upper(), "cp-03's schema file still cascades"


def _seed_all(dsn: str) -> None:
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as db, db.cursor() as cursor:
        for name in LOCKED_FILES:
            cursor.execute((FIXTURES / name).read_text(encoding="utf-8"))


def _state(dsn: str) -> dict[str, int | None]:
    """Every fixture table's row count, and the outside view's (``None`` when it is gone)."""
    import psycopg

    state: dict[str, int | None] = {}
    with psycopg.connect(dsn, autocommit=True) as db, db.cursor() as cursor:
        for table in _relations(dsn):
            cursor.execute(f"SELECT count(*) FROM {SCHEMA}.{table}")
            state[f"{SCHEMA}.{table}"] = cursor.fetchone()[0]
        cursor.execute(
            "SELECT count(*) FROM pg_views WHERE schemaname = %s AND viewname = %s",
            (OUTSIDE, DEPENDENT),
        )
        if cursor.fetchone()[0]:
            cursor.execute(f"SELECT count(*) FROM {OUTSIDE}.{DEPENDENT}")
            state[f"{OUTSIDE}.{DEPENDENT}"] = cursor.fetchone()[0]
        else:
            state[f"{OUTSIDE}.{DEPENDENT}"] = None
    return state


@pytest.fixture
def depended_on(scratch: str) -> Iterator[str]:
    """`ccf_v2` seeded by all eight files, plus a view in ANOTHER schema that
    depends on `ccf_v2.legal_entity`; the outside schema is dropped afterwards."""
    import psycopg

    _seed_all(scratch)
    with psycopg.connect(scratch, autocommit=True) as db:
        db.execute(f"DROP SCHEMA IF EXISTS {OUTSIDE} CASCADE")
        db.execute(f"CREATE SCHEMA {OUTSIDE}")
        db.execute(f"CREATE VIEW {OUTSIDE}.{DEPENDENT} AS SELECT * FROM {SCHEMA}.legal_entity")
    yield scratch
    with psycopg.connect(scratch, autocommit=True) as db:
        db.execute(f"DROP SCHEMA IF EXISTS {OUTSIDE} CASCADE")


@pytest.mark.postgres
@pytest.mark.parametrize("name", LOCKED_FILES)
def test_an_outside_dependent_is_refused_by_name_and_every_table_and_view_survives(
    depended_on: str, name: str
) -> None:
    """Barrier (a), the lock: each of the eight files is refused by the lock's
    own `RaiseException`, naming the dependent and its schema, and afterwards
    every `ccf_v2` table and the outside view still exist with their row counts
    unchanged."""
    import psycopg

    before = _state(depended_on)
    assert before[f"{OUTSIDE}.{DEPENDENT}"] is not None and set(_relations(depended_on)) == set(FIXTURE_TABLES), (
        "the case was not constructed: all twelve tables and the outside view must exist"
    )

    refused: psycopg.Error | None = None
    with psycopg.connect(depended_on, autocommit=True) as db, db.cursor() as cursor:
        try:
            cursor.execute((FIXTURES / name).read_text(encoding="utf-8"))
        except psycopg.Error as exc:
            refused = exc
    after = _state(depended_on)

    assert refused is not None, (
        f"{name} ran to completion while {OUTSIDE}.{DEPENDENT} depends on {SCHEMA}.legal_entity;"
        f" the outside view's row count went {before[f'{OUTSIDE}.{DEPENDENT}']} -> {after[f'{OUTSIDE}.{DEPENDENT}']}"
    )
    assert isinstance(refused, psycopg.errors.RaiseException), (
        f"{name} failed on {type(refused).__name__}, not on the write lock: {refused}"
    )
    message = str(refused)
    assert re.search(rf"(?<!\w){OUTSIDE}\.{DEPENDENT}(?!\w)", message), message
    assert "D-IMPL-380" in message, message
    assert after == before, f"{name}: refused, but the database changed: {before} -> {after}"


@pytest.mark.postgres
def test_cp03_drops_alone_fail_on_a_dependent_and_the_view_survives(depended_on: str) -> None:
    """Barrier (b), no CASCADE: cp-03's drop statements alone — the lock
    bypassed — fail on the outside dependent rather than dropping it, and in one
    simple-query `execute` they roll back together."""
    import psycopg

    drops = "\n".join(
        line
        for line in (FIXTURES / CP03_SCHEMA).read_text(encoding="utf-8").splitlines()
        if line.startswith("DROP TABLE")
    )
    assert drops, "the case was not constructed: cp-03's schema file must drop its tables"
    before = _state(depended_on)

    failed: psycopg.Error | None = None
    with psycopg.connect(depended_on, autocommit=True) as db, db.cursor() as cursor:
        try:
            cursor.execute(drops)
        except psycopg.Error as exc:
            failed = exc
    after = _state(depended_on)

    assert after[f"{OUTSIDE}.{DEPENDENT}"] is not None, (
        f"cp-03's drops removed {OUTSIDE}.{DEPENDENT}, which depends on {SCHEMA}.legal_entity: the drops cascade"
    )
    assert isinstance(failed, psycopg.errors.DependentObjectsStillExist), (
        f"cp-03's drops did not fail on the dependent: {type(failed).__name__}: {failed}"
    )
    assert after == before, f"the failed drops changed the database: {before} -> {after}"


@pytest.mark.postgres
def test_a_clean_scratch_database_seeds_all_eight_and_cp03_twice(scratch: str) -> None:
    """Positive control for both barriers: neither refuses the database it
    exists for, including cp-03's schema applied a second time in one session
    (as two seeding modules do), whose plain drops find nothing depending on
    its tables."""
    import psycopg

    _seed_all(scratch)
    with psycopg.connect(scratch, autocommit=True) as db, db.cursor() as cursor:
        cursor.execute((FIXTURES / CP03_SCHEMA).read_text(encoding="utf-8"))
    assert set(_relations(scratch)) == set(FIXTURE_TABLES)


# ---------------------------------------------------------------------------
# D-IMPL-380, second round, ruling 4 (a) (Dave, 2026-10-10 07:39 MST: *"A rule
# is named as a rule."*). EXAMPLE-ONLY. The lock labeled every `pg_rewrite`
# dependent "view" or "materialized view", so a rule on a table in another
# schema that reads one of the twelve tables was refused as a "view". A
# `_RETURN` rule is its view or materialized view; any other rule is named as a
# rule on its table. What the lock refuses does not change.
# ---------------------------------------------------------------------------

RULE_TABLE = "zz_rule_target"
RULE = "zz_reads_legal_entity"


@pytest.mark.postgres
def test_a_rule_dependent_is_refused_and_named_a_rule_not_a_view(scratch: str) -> None:
    """A rule on a table in ANOTHER schema, whose condition reads
    `ccf_v2.legal_entity`, is refused by the lock's own `RaiseException`, and the
    refusal names it as a rule on its table, never as a view."""
    import psycopg

    _seed_all(scratch)
    try:
        with psycopg.connect(scratch, autocommit=True) as db:
            db.execute(f"DROP SCHEMA IF EXISTS {OUTSIDE} CASCADE")
            db.execute(f"CREATE SCHEMA {OUTSIDE}")
            db.execute(f"CREATE TABLE {OUTSIDE}.{RULE_TABLE} (id int)")
            db.execute(
                f"CREATE RULE {RULE} AS ON INSERT TO {OUTSIDE}.{RULE_TABLE}"
                f" WHERE EXISTS (SELECT 1 FROM {SCHEMA}.legal_entity) DO INSTEAD NOTHING"
            )
        refused: psycopg.Error | None = None
        with psycopg.connect(scratch, autocommit=True) as db, db.cursor() as cursor:
            try:
                cursor.execute((FIXTURES / LOCKED_FILES[0]).read_text(encoding="utf-8"))
            except psycopg.Error as exc:
                refused = exc
    finally:
        with psycopg.connect(scratch, autocommit=True) as db:
            db.execute(f"DROP SCHEMA IF EXISTS {OUTSIDE} CASCADE")

    assert isinstance(refused, psycopg.errors.RaiseException), (
        f"{LOCKED_FILES[0]} was not refused by the write lock with a rule depending on {SCHEMA}.legal_entity:"
        f" {type(refused).__name__}: {refused}"
    )
    message = str(refused)
    assert "D-IMPL-380" in message, message
    assert re.search(rf"(?<!\w)rule {RULE} on table {OUTSIDE}\.{RULE_TABLE}(?!\w)", message), (
        f"the refusal does not name the rule as a rule on its table: {message}"
    )
    assert not re.search(rf"(?<!\w)view {OUTSIDE}\.{RULE_TABLE}(?!\w)", message), (
        f"the refusal calls a rule a view: {message}"
    )
