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
    assert _first_statement(text).startswith(write_lock(SCHEMA)), (
        f"{name}: the first statement is not the D-IMPL-379 write lock"
    )


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
# Live: on a disposable local Postgres, never the curated estate.
# ---------------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


def _relations(dsn: str) -> list[str]:
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
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    refuse_to_write_the_curated_estate(postgres_dsn)
    with psycopg.connect(postgres_dsn, autocommit=True) as db:
        db.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        db.execute(f"CREATE SCHEMA {SCHEMA}")
    yield postgres_dsn
    with psycopg.connect(postgres_dsn, autocommit=True) as db:
        db.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")


@pytest.mark.parametrize("name", LOCKED_FILES)
def test_a_database_that_is_not_ours_is_refused_by_name(
    scratch: str, name: str
) -> None:
    """One table no fixture creates is enough: the file raises, naming it, and
    writes nothing — the stray survives and no fixture table appears."""
    with psycopg.connect(scratch, autocommit=True) as db:
        db.execute(f"CREATE TABLE {SCHEMA}.{STRAY} (id int)")
    before = _relations(scratch)

    with psycopg.connect(scratch, autocommit=True) as db, db.cursor() as cursor:
        with pytest.raises(psycopg.errors.RaiseException) as refused:
            cursor.execute((FIXTURES / name).read_text(encoding="utf-8"))

    message = str(refused.value)
    assert re.search(rf"(?<!\w){STRAY}(?!\w)", message), message
    assert "D-IMPL-379" in message, message
    assert _relations(scratch) == before == [STRAY]


def test_a_clean_scratch_database_seeds_all_eight(scratch: str) -> None:
    """Positive control: the lock does not refuse the database it exists for,
    including the second and later files, which find the earlier ones' tables."""
    with psycopg.connect(scratch, autocommit=True) as db, db.cursor() as cursor:
        for name in LOCKED_FILES:
            cursor.execute((FIXTURES / name).read_text(encoding="utf-8"))
    assert set(_relations(scratch)) == set(FIXTURE_TABLES)
