# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-013, option (C): what the SQLite file lease does NOT close, measured rather than implied.

``tests/graph/test_sqlite_writer_lease_file_identity.py`` measures what a declared ``writer_lease_lock_dir`` closes:
a second process's WRITER through the new name of a renamed live file is refused, among writers that declare the same
directory (one through a hard link is refused earlier, when its store opens: item 3). Each test here asserts a limit
as it stands, so a change that closes one turns its test red and the disclosure must be revisited
(``public/how-to/security-and-deployment.md`` §4.6):

1. Writers that declare different lock directories, or none, are not excluded through another name.
2. Renaming a live database file loses the writer's uncheckpointed commits to everyone who opens the file by its new
   name, with no second process at all: SQLite keeps the log under the name it opened, and its close does not fold
   that log into a file that has moved. No lock can close this; it is an operating rule.
3. **Closed by P2 (b)** (``D-IMPL-378``, lane ``378i-p2b``) for a second name that exists when the store opens. The
   lease is still taken when the writer is minted, after the store has opened the database and run its setup (the
   WAL pragma and the schema), and through a hard link a refused process, or a read-only boot, used to have written
   that setup already, leaving a log that rolled the holder's committed data back once anything opened the file
   through the link, with ``integrity_check`` still ``ok``. The store now refuses a file with more than one name
   before any connection or setup, readers included, so neither writes anything; the two tests that measured this
   limit went red with that change and were removed with it. Their scenarios are asserted closed, with what the
   second open leaves behind and the holder's row after both close, by
   ``tests/graph/test_sqlite_open_refuses_a_file_with_more_than_one_name.py::test_a_second_open_through_a_hard_link_is_refused_before_it_writes_anything_and_the_holder_keeps_its_commit``.
   What the store's two counts of the file's names still do not see is stated in
   ``src/ccf/graph/backends/sqlite.py::SqliteGraphStore``.

Raw ``sqlite3`` connections stand in for "a commit through the holder's name" and "a later reader": they share or
open the same per-name logs the store's connection does. Every file lives in ``tmp_path``.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from tests.graph.test_single_writer_across_processes import _boot, _run_child
from tests.graph.test_sqlite_writer_lease_file_identity import _declared, _locks
from tests.graph.test_sqlite_writer_lease_hard_link import _two_names


def _private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def _tables_and_integrity(path: Path) -> tuple[list[str], str]:
    connection = sqlite3.connect(path)
    try:
        tables = sorted(row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))
        return tables, connection.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        connection.close()


def _commit_a_table_through(path: Path, table: str) -> None:
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.execute(f"CREATE TABLE {table} (x)")
    finally:
        connection.close()


def test_limit_writers_that_declare_different_lock_directories_are_not_excluded_through_a_renamed_file(
    tmp_path: Path,
) -> None:
    held, moved = _two_names(tmp_path)
    holder = _boot("sqlite", _declared(held, _locks(tmp_path)))
    try:
        os.rename(held, moved)
        outcome = _run_child("sqlite", _declared(moved, _private_directory(tmp_path / "other-locks")))
    finally:
        holder.close()

    assert outcome == ("BOOTED", "", ""), outcome


def test_limit_a_writer_that_declares_no_lock_directory_is_not_excluded_through_a_renamed_file(
    tmp_path: Path,
) -> None:
    held, moved = _two_names(tmp_path)
    holder = _boot("sqlite", _declared(held, _locks(tmp_path)))
    try:
        os.rename(held, moved)
        outcome = _run_child("sqlite", {"database_path": moved})
    finally:
        holder.close()

    assert outcome == ("BOOTED", "", ""), outcome


def test_limit_renaming_a_live_database_file_strands_its_uncheckpointed_commits_under_the_old_name(
    tmp_path: Path,
) -> None:
    held, moved = _two_names(tmp_path)
    holder = _boot("sqlite", _declared(held, _locks(tmp_path)))
    try:
        _commit_a_table_through(held, "committed_before_the_rename")
        os.rename(held, moved)
    finally:
        holder.close()

    tables, integrity = _tables_and_integrity(moved)
    assert "committed_before_the_rename" not in tables, tables
    assert integrity == "ok"
    assert Path(f"{held}-wal").stat().st_size > 0, "the writer's log was expected to remain under the old name"
