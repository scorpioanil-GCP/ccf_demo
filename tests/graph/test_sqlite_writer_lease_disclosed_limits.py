"""SEC-013 stays OPEN: the two limits of the SQLite writer lease's option (B), measured as they stand.

Dave ruled on 2026-10-08 at 21:24 MST (``D-IMPL-378``), verbatim: *"B now, with the rename gap and hard-link backup
restriction explicitly disclosed. Keep the affected SEC-013 closure open pending C; start C in parallel."* Option (B)
is ``src/ccf/graph/backends/sqlite.py::SqliteGraphStore``'s ``writer_lease``, which refuses a database file with more
than one name (its own tests: ``tests/graph/test_sqlite_writer_lease_hard_link.py``). This module measures the two
things the ruling requires an operator to be told, so that the disclosures in
``src/ccf/graph/backends/sqlite.py::SqliteWriterLease`` and on the security page cannot drift from the behavior:

* **The hard-link backup restriction.** A backup that links the database file instead of copying it gives the file a
  second name, so every writer boot of the graph is refused, with no writer live, until the backup's name is removed
  (:func:`test_a_hard_link_backup_refuses_every_writer_boot_until_it_is_removed`). Since P2 (b) (``D-IMPL-378``, lane
  ``378i-p2b``) the refusal comes when each boot's store opens, with ``WriterLeaseHeld``, and covers read-only boots
  too (``tests/graph/test_sqlite_open_refuses_a_file_with_more_than_one_name.py``). What to do instead: a copy SQLite
  writes itself, by its online backup API or by ``VACUUM INTO``, taken while a writer is live, leaves the file one
  name (:func:`test_a_copy_sqlite_makes_while_the_writer_is_live_leaves_the_file_one_name`).
* **The rename gap, which (B) does not close.** A live file moved to a new name keeps one name, so a writer booted
  through the new name in a second process is not refused
  (``tests/graph/test_sqlite_writer_lease_hard_link.py::test_a_second_process_boots_a_writer_through_the_new_name_of_a_moved_live_file``).
  Why that loses data: SQLite keeps the live write-ahead log beside the OLD name
  (:func:`test_a_moved_live_file_leaves_its_write_ahead_log_behind_and_its_commits_are_lost`). The safe way to move
  a database file: stop every process that has it open first
  (:func:`test_a_database_file_moved_while_no_process_has_it_open_is_leased_under_its_new_name`).

Nothing here is skipped or marked expected-to-fail: the rename gap is a measured, visible limit. The second process is
the recipe of ``tests/graph/test_single_writer_across_processes.py::_run_child``; a writer boots with
``tests/graph/test_single_writer_across_processes.py::_boot``. Every file lives in ``tmp_path``.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from ccf.graph.backends.sqlite import WRITER_LEASE_SUFFIX
from ccf.graph.protocols import WriterLeaseHeld
from tests.graph.test_single_writer_across_processes import _boot, _run_child

#: The refusal's own words for a database file with two names (the store's open, and the writer lease's).
_TWO_NAMES = "has 2 names (hard links)"

#: The store's own words when it refuses to open a file with more than one name (P2 (b)).
_REFUSED_AT_OPEN = "the store refuses to open it, readers included, before any connection or setup"


def _two_names(tmp_path: Path) -> tuple[Path, Path]:
    """Two directories, so the two names of one file share no parent and no sidecar."""
    first = tmp_path / "first" / "graph.sqlite3"
    second = tmp_path / "second" / "graph.sqlite3"
    first.parent.mkdir()
    second.parent.mkdir()
    return first, second


_TABLES_SEEN_THROUGH = r"""
import sqlite3, sys
connection = sqlite3.connect(sys.argv[1], isolation_level=None)
print(sorted(row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")))
connection.close()
"""


def _tables_seen_through(path: Path) -> str:
    """What a second process sees through ``path``: plain sqlite3, nothing of the SDK's."""
    return subprocess.run(
        [sys.executable, "-c", _TABLES_SEEN_THROUGH, str(path)], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_a_hard_link_backup_refuses_every_writer_boot_until_it_is_removed(tmp_path: Path) -> None:
    """A hard link a backup made, with no writer live: every writer boot, in this process and in another, through
    either name, is refused when its store opens (P2 (b): ``WriterLeaseHeld``, before the mint) naming the file's two
    names, until the link is removed."""
    live, backup = _two_names(tmp_path)
    _boot("sqlite", {"database_path": live}).close()  # a graph, and no writer live
    os.link(live, backup)  # what a hard-link backup does: the same file under a second name, not a copy
    assert os.stat(live).st_nlink == 2

    for name in (live, backup):
        with pytest.raises(WriterLeaseHeld) as in_process:
            _boot("sqlite", {"database_path": name})
        second_process = _run_child("sqlite", {"database_path": name})
        assert second_process[:2] == ("REFUSED", "WriterLeaseHeld"), second_process
        # The store's own refusal, before the mint: it names the file's two names and says it refused to open it.
        for message in (str(in_process.value), second_process[2]):
            assert _TWO_NAMES in message, message
            assert _REFUSED_AT_OPEN in message, message

    os.unlink(backup)
    _boot("sqlite", {"database_path": live}).close()  # control: the refusal goes with the backup's name


#: A copy SQLite writes itself, run in another process as a backup job would be.
_COPY_WITH = {
    "online-backup-api": (
        "import sqlite3, sys\n"
        "source, copy = sqlite3.connect(sys.argv[1]), sqlite3.connect(sys.argv[2])\n"
        "source.backup(copy)\n"
        "copy.close()\n"
        "source.close()\n"
    ),
    "vacuum-into": (
        "import sqlite3, sys\n"
        "source = sqlite3.connect(sys.argv[1])\n"
        "source.execute('VACUUM INTO ?', (sys.argv[2],))\n"
        "source.close()\n"
    ),
}


@pytest.mark.parametrize("method", sorted(_COPY_WITH))
def test_a_copy_sqlite_makes_while_the_writer_is_live_leaves_the_file_one_name(tmp_path: Path, method: str) -> None:
    """The backup to take instead: SQLite's online backup API or ``VACUUM INTO``, run while a writer is live, writes an
    independent copy holding the graph's tables and leaves the database file one name, so the next writer boots."""
    live, copy = _two_names(tmp_path)
    holder = _boot("sqlite", {"database_path": live})
    try:
        subprocess.run(
            [sys.executable, "-c", _COPY_WITH[method], str(live), str(copy)], check=True, capture_output=True
        )
        assert os.stat(live).st_nlink == 1
        assert not os.path.samefile(live, copy)
        copied = _tables_seen_through(copy)
        assert copied == _tables_seen_through(live) and "'entities'" in copied, copied
    finally:
        holder.close()
    _boot("sqlite", {"database_path": live}).close()  # the copy does not stand in the next writer's way


_SEE_THEN_COMMIT_THROUGH = r"""
import sqlite3, sys
connection = sqlite3.connect(sys.argv[1], isolation_level=None)
print(sorted(row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")))
connection.execute("CREATE TABLE committed_through_the_new_name (y)")
connection.close()
"""


def test_a_moved_live_file_leaves_its_write_ahead_log_behind_and_its_commits_are_lost(tmp_path: Path) -> None:
    """Why a live database file must not be moved: SQLite keeps the live write-ahead log beside the OLD name, so a
    second process through the new name does not see what was committed; once both names have been written through
    and closed, what was committed through the old name is gone, and the integrity check still reports ``ok``.
    Plain ``sqlite3``, nothing of the SDK's: this is the loss the rename gap leaves the lease unable to prevent."""
    held, moved = _two_names(tmp_path)
    first = sqlite3.connect(held, isolation_level=None)
    try:
        first.execute("PRAGMA journal_mode = WAL")
        first.execute("PRAGMA wal_autocheckpoint = 0")
        first.execute("CREATE TABLE committed_before_the_move (x)")
        os.rename(held, moved)
        left_behind = sorted(entry.name for entry in held.parent.iterdir())
        through_the_new_name = subprocess.run(
            [sys.executable, "-c", _SEE_THEN_COMMIT_THROUGH, str(moved)], capture_output=True, text=True, check=True
        ).stdout.strip()
    finally:
        first.close()
    after = sqlite3.connect(moved, isolation_level=None)
    try:
        surviving = sorted(row[0] for row in after.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))
        integrity = [row[0] for row in after.execute("PRAGMA integrity_check")]
    finally:
        after.close()

    assert left_behind == ["graph.sqlite3-shm", "graph.sqlite3-wal"], left_behind
    assert through_the_new_name == "[]"
    assert surviving == ["committed_through_the_new_name"], surviving
    assert integrity == ["ok"]


def test_a_database_file_moved_while_no_process_has_it_open_is_leased_under_its_new_name(tmp_path: Path) -> None:
    """The way to move a database file: stop every process that has it open first. Closed, it has no write-ahead log
    beside it, and under its new name it is one graph: a writer boots, and a second process is refused while it is
    live."""
    old, new = _two_names(tmp_path)
    _boot("sqlite", {"database_path": old}).close()
    beside_the_old_name = sorted(entry.name for entry in old.parent.iterdir())
    assert beside_the_old_name == ["graph.sqlite3", f"graph.sqlite3{WRITER_LEASE_SUFFIX}"], beside_the_old_name
    os.rename(old, new)
    holder = _boot("sqlite", {"database_path": new})
    try:
        second_process = _run_child("sqlite", {"database_path": new})
    finally:
        holder.close()
    assert second_process[:2] == ("REFUSED", "SingleWriterViolation"), second_process
    assert "'entities'" in _tables_seen_through(new)
