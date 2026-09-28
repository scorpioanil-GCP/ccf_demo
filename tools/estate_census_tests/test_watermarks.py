"""Controls over `tools/estate_census/watermarks.py` — the estate-posture half of
`D-IMPL-358` ruling 8 and CLAUDE.md §9.

Dave's requirement: *"Curated .76 is read-only. The census instrument has no
seed/mutation path to curated stores."* Three properties carry that here, in
decreasing strength:

* `test_the_postgres_probe_sets_the_connection_read_only_before_any_statement`
  — the strongest, because it is the SERVER that then refuses a write. Proved by
  substituting the driver and observing the assignment, not by reading the source.
* `test_this_module_names_no_write_verb` — a structural sweep of this module's own
  source, so a future edit that adds a write verb reddens a control rather than
  shipping.
* `test_an_unset_store_is_unmeasured_rather_than_measured_as_zero` — an outage
  must not be able to *prove* the estate did not move.

**Nothing here connects to anything.** The driver is substituted; the curated
estate is never contacted by this suite.

**The positive control is `test_the_write_verb_sweep_fires_on_a_source_that_does_contain_one`**,
which points the sweep at a string that does contain a write verb. Without it, a
green sweep could mean the module is clean or that the sweep matches nothing.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from tools.estate_census import watermarks
from tools.estate_census.watermarks import (
    StoreDeclaration,
    load_roster,
    measure,
    measure_one,
)

WATERMARKS_SOURCE = Path(watermarks.__file__).read_text()

#: Tokens that would mean this module can change an estate. Deliberately broad:
#: over-matching costs a false red that a reviewer resolves in a minute, while
#: under-matching costs a permanent write to an append-only curated ledger.
WRITE_VERBS: tuple[str, ...] = (
    "insert", "update", "delete", "drop", "truncate", "alter", "create",
    "transact", "upsert", "replace_one", "insert_one", "insert_many",
    "update_one", "update_many", "delete_one", "delete_many", "bulk_write",
    "drop_collection", "commit(", "execute_values", "copy(", "write_text", "write_bytes",
)


def write_verbs_in(source: str) -> list[str]:
    """Write verbs present in `source`, ignoring prose and this module's own roster.

    Only executable lines are considered: a docstring that NAMES a write verb in
    order to say the module does not use one must not redden the sweep.
    """
    executable: list[str] = []
    in_docstring = False
    delimiter = ""
    for line in source.splitlines():
        stripped = line.strip()
        if in_docstring:
            if delimiter in stripped:
                in_docstring = False
            continue
        if stripped.startswith(('"""', "'''")):
            delimiter = stripped[:3]
            if not (stripped.count(delimiter) >= 2 and len(stripped) > 3):
                in_docstring = True
            continue
        if stripped.startswith("#"):
            continue
        executable.append(line.lower())
    body = "\n".join(executable)
    return sorted({verb for verb in WRITE_VERBS if verb in body})


# --------------------------------------------------------------------------
# Preconditions and the positive control.
# --------------------------------------------------------------------------


def test_the_module_source_was_actually_read() -> None:
    """A vacuity guard: an empty source string passes every sweep below."""
    assert len(WATERMARKS_SOURCE) > 2000, len(WATERMARKS_SOURCE)
    assert "def measure_one" in WATERMARKS_SOURCE


def test_the_write_verb_sweep_fires_on_a_source_that_does_contain_one() -> None:
    """THE POSITIVE CONTROL for the structural sweep."""
    found = write_verbs_in('def go():\n    cursor.execute("INSERT INTO t VALUES (1)")\n')
    assert "insert" in found, found
    assert write_verbs_in("def go():\n    client.delete_many({})\n")


# --------------------------------------------------------------------------
# The properties.
# --------------------------------------------------------------------------


def test_the_write_verb_sweep_still_sees_this_modules_executable_lines() -> None:
    """A second vacuity guard, aimed at the DOCSTRING STRIPPER rather than the roster.

    The sweep ignores docstrings so that prose naming a write verb in order to say
    the module avoids one does not redden it. A stripper that over-reached would
    discard executable lines too, and the sweep would then be green because it was
    looking at almost nothing. Measured: 154 of 220 lines survive, and every
    executable token the probes depend on is among them.
    """
    executable: list[str] = []
    in_docstring = False
    delimiter = ""
    for line in WATERMARKS_SOURCE.splitlines():
        stripped = line.strip()
        if in_docstring:
            if delimiter in stripped:
                in_docstring = False
            continue
        if stripped.startswith(('"""', "\'\'\'")):
            delimiter = stripped[:3]
            if not (stripped.count(delimiter) >= 2 and len(stripped) > 3):
                in_docstring = True
            continue
        if stripped.startswith("#"):
            continue
        executable.append(line)
    body = "\n".join(executable)
    assert len(executable) > 120, f"the stripper kept only {len(executable)} lines"
    for token in (
        "def measure_one",
        "connection.read_only",
        "psycopg.connect",
        "count_documents",
        "httpx.get",
    ):
        assert token in body, f"the stripper discarded the executable line holding {token!r}"
    # and the docstring mention it is SUPPOSED to ignore is in fact ignored
    assert "transact" in WATERMARKS_SOURCE.lower()
    assert "transact" not in body.lower()


def test_this_module_names_no_write_verb() -> None:
    """`D-IMPL-358` ruling 8: the census instrument has no seed/mutation path to a
    curated store. A future edit that adds one reddens here."""
    assert write_verbs_in(WATERMARKS_SOURCE) == []


def test_the_postgres_probe_sets_the_connection_read_only_before_any_statement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The strongest guarantee available: with ``read_only`` set, the SERVER refuses
    a write on this connection. Proved by substituting the driver rather than by
    reading the source, because a source claim is not a posture.

    Also asserts Dave's *"reuse one read-only connection and close it"*: exactly one
    connection is opened, and it is closed.
    """
    events: list[str] = []

    class FakeCursor:
        def __enter__(self) -> FakeCursor:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def execute(self, statement: str, params: Any = None) -> None:
            events.append(f"execute:{statement.split()[0].lower()}")
            assert "read_only=True" in events, (
                "a statement was issued BEFORE the connection was made read-only"
            )

        def fetchone(self) -> tuple[int]:
            return (7,)

        def fetchall(self) -> list[tuple[str]]:
            return [("legal_entity",)]

    class FakeConnection:
        def __init__(self) -> None:
            self._read_only = False

        @property
        def read_only(self) -> bool:
            return self._read_only

        @read_only.setter
        def read_only(self, value: bool) -> None:
            events.append(f"read_only={value}")
            self._read_only = value

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def __enter__(self) -> FakeConnection:
            return self

        def __exit__(self, *_: object) -> None:
            events.append("closed")

    def fake_connect(dsn: str, **_: Any) -> FakeConnection:
        events.append("connect")
        return FakeConnection()

    monkeypatch.setitem(
        sys.modules, "psycopg", types.SimpleNamespace(connect=fake_connect)  # type: ignore[arg-type]
    )
    position = watermarks._postgres_counts("host=h dbname=d", ("ccf_v2",))

    assert events.count("connect") == 1, f"expected ONE connection, got {events}"
    assert events[1] == "read_only=True", f"read_only was not set first: {events}"
    assert "closed" in events, f"the connection was not closed: {events}"
    assert all(event.split(":")[1] == "select" for event in events if event.startswith("execute:")), events
    assert position["schema:ccf_v2"]["table_count"] == 1
    assert "per_table_sha256" in position["schema:ccf_v2"]


def test_an_unset_store_is_unmeasured_rather_than_measured_as_zero() -> None:
    """Recording zero would make an outage indistinguishable from an empty store,
    and comparing two zeros would then PROVE the estate did not move."""
    store = StoreDeclaration(key="f", kind="fluree", target_env="CCF_ABSENT_FOR_THIS_TEST")
    record = measure_one(store, environ={})
    assert "position" not in record
    assert "error" in record and "CCF_ABSENT_FOR_THIS_TEST" in record["error"]


def test_an_unreachable_store_records_the_failure_and_not_a_position() -> None:
    store = StoreDeclaration(key="f", kind="fluree", target_env="URL")
    record = measure_one(store, environ={"URL": "http://127.0.0.1:1"})
    assert "position" not in record
    assert "error" in record


def test_an_unknown_store_kind_is_refused_rather_than_silently_skipped() -> None:
    store = StoreDeclaration(key="x", kind="cassandra", target_env="T")
    record = measure_one(store, environ={"T": "somewhere"})
    assert "position" not in record
    assert "unknown store kind" in record["error"]


def test_the_recorded_target_is_redacted_so_a_measurement_names_no_credential() -> None:
    """A measurement records WHICH store was read without recording the credential
    that reached it."""
    store = StoreDeclaration(key="p", kind="postgres", target_env="DSN")
    record = measure_one(
        store, environ={"DSN": "postgresql://ccf:LEAKME@192.168.4.76:5432/ccf_v2"}
    )
    assert "LEAKME" not in json.dumps(record)
    assert "192.168.4.76" in record["target"]


def test_the_shipped_roster_declares_environment_variable_names_and_no_values() -> None:
    """The roster lives in the repository while the credential does not, which is
    what makes `D-IMPL-358` ruling 10 a roster edit rather than a code change."""
    roster_path = Path(watermarks.__file__).parent / "curated_stores.json"
    roster = load_roster(roster_path)
    assert roster is not None and len(roster) >= 3
    raw = roster_path.read_text()
    for forbidden in ("password", "://", "@"):
        assert forbidden not in raw, f"the roster names a {forbidden!r} — it must name env vars only"
    for store in roster:
        assert store.target_env.startswith("CCF_"), store.target_env


def test_an_unreadable_roster_is_none_and_not_an_empty_store_list(tmp_path: Path) -> None:
    """A census whose roster failed to load has measured nothing, and must not
    proceed as though the estate had no stores."""
    assert load_roster(tmp_path / "missing.json") is None
    (tmp_path / "bad.json").write_text("not json")
    assert load_roster(tmp_path / "bad.json") is None
    (tmp_path / "obj.json").write_text('{"key": "not-a-list"}')
    assert load_roster(tmp_path / "obj.json") is None
    (tmp_path / "wrong.json").write_text('[{"no_key_field": 1}]')
    assert load_roster(tmp_path / "wrong.json") is None


def test_measure_reports_every_declared_store_even_when_all_are_unmeasurable() -> None:
    roster = (
        StoreDeclaration(key="a", kind="fluree", target_env="A"),
        StoreDeclaration(key="b", kind="postgres", target_env="B"),
    )
    measured = measure(roster, environ={})
    assert set(measured) == {"a", "b"}
    assert all("error" in record for record in measured.values())
