"""SEC-013, option (C): what the SQLite file lease does NOT close, measured rather than implied.

``tests/graph/test_sqlite_writer_lease_file_identity.py`` measures what a declared ``writer_lease_lock_dir`` closes:
a second process's WRITER through a hard link or through the new name of a renamed live file is refused, among
writers that declare the same directory. Each test here asserts a limit as it stands, so a change that closes one
turns its test red and the disclosure must be revisited (``public/how-to/security-and-deployment.md`` §4.6):

1. Writers that declare different lock directories, or none, are not excluded through another name.
2. Renaming a live database file loses the writer's uncheckpointed commits to everyone who opens the file by its new
   name, with no second process at all: SQLite keeps the log under the name it opened, and its close does not fold
   that log into a file that has moved. No lock can close this; it is an operating rule.
3. The lease is taken when the writer is minted, after the store has opened the database and run its setup (the WAL
   pragma and the schema). A second process the lease refuses has therefore already written that setup through its
   own name; through a hard link, that leftover log later rolls the holder's committed data back when anything opens
   the file through the link — with ``integrity_check`` still ``ok``.

Raw ``sqlite3`` connections stand in for "a commit through the holder's name" and "a later reader through the
link": they share or open the same per-name logs the store's connection does. Every file lives in ``tmp_path``.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
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


#: A second process that boots the fabric READ-ONLY through the path it is given, then closes it (FW-2: no lease).
_READ_ONLY_BOOT = """
import sys
from tests.graph.test_sqlite_writer_lease_file_identity import _boot_read_only
_boot_read_only({"database_path": sys.argv[1]}).close()
"""


def _read_only_boot_in_another_process(path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    pythonpath = os.pathsep.join(str(part) for part in (root, root / "src", root / "runtime"))
    subprocess.run(
        [sys.executable, "-B", "-c", _READ_ONLY_BOOT, str(path)],
        cwd=root,
        env=dict(os.environ, PYTHONPATH=pythonpath),
        check=True,
        capture_output=True,
        timeout=120,
    )


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


def test_limit_a_process_refused_through_a_hard_link_has_already_written_setup_that_later_rolls_back_the_holder(
    tmp_path: Path,
) -> None:
    locks = _locks(tmp_path)
    held, linked = _two_names(tmp_path)
    holder = _boot("sqlite", _declared(held, locks))
    try:
        os.link(held, linked)
        refused = _run_child("sqlite", _declared(linked, locks))
        leftover_log = Path(f"{linked}-wal").stat().st_size
        _commit_a_table_through(held, "committed_after_the_refusal")
    finally:
        holder.close()
    before_the_link_is_opened, _ = _tables_and_integrity(held)
    _tables_and_integrity(linked)  # anything that later opens the file through the link
    after, integrity = _tables_and_integrity(held)

    assert refused[:2] == ("REFUSED", "SingleWriterViolation"), refused
    assert "is held by another writer that declared the same lock directory" in refused[2], refused
    assert leftover_log > 0, "the refused process's open was expected to leave a log beside the link"
    assert "committed_after_the_refusal" in before_the_link_is_opened, before_the_link_is_opened
    assert "committed_after_the_refusal" not in after, after
    assert integrity == "ok"


def test_limit_a_read_only_boot_through_a_hard_link_also_writes_setup_that_later_rolls_back_the_holder(
    tmp_path: Path,
) -> None:
    held, linked = _two_names(tmp_path)
    holder = _boot("sqlite", _declared(held, _locks(tmp_path)))
    try:
        os.link(held, linked)
        _read_only_boot_in_another_process(linked)
        leftover_log = Path(f"{linked}-wal").stat().st_size
        _commit_a_table_through(held, "committed_after_the_reader")
    finally:
        holder.close()
    before_the_link_is_opened, _ = _tables_and_integrity(held)
    _tables_and_integrity(linked)  # anything that later opens the file through the link
    after, integrity = _tables_and_integrity(held)

    assert leftover_log > 0, "the read-only boot's open was expected to leave a log beside the link"
    assert "committed_after_the_reader" in before_the_link_is_opened, before_the_link_is_opened
    assert "committed_after_the_reader" not in after, after
    assert integrity == "ok"
