"""SEC-013, PROPOSAL (lane ``378f-small2``, option B): the SQLite writer lease refuses a file with a second name.

``src/ccf/graph/backends/sqlite.py::SqliteWriterLease`` takes an exclusive ``flock`` on
``<resolved database path>.ccf-writer.lock``. ``Path.resolve`` folds a relative spelling or a symbolic link onto one
path, so those are one graph to the lease
(``tests/graph/test_single_writer_across_processes.py::test_one_file_spelled_two_ways_is_still_one_graph``). A hard
link is not folded: it resolves to itself, and the sidecar beside it is another file, so a lock beside one name cannot
exclude a writer through another. Under option B, ``src/ccf/graph/backends/sqlite.py::SqliteGraphStore`` refuses, in
``writer_lease``, a database file with more than one name, through either name: a second process is refused with
``SingleWriterViolation``, and the lease itself raises ``WriterLeaseHeld`` naming the file's names. The refusal goes
when the second name goes.

**What option B does not close, measured here too:** a live file moved to a new name keeps one name, so a writer booted
through the new name in a second process is not refused while the first process's writer is live.

Why a second name matters, measured on the installed SQLite rather than assumed: SQLite names its write-ahead log
after the path a connection opened, so a second name reads another log and misses what the first name committed.

The second process is the recipe of ``tests/graph/test_single_writer_across_processes.py::_run_child``, and the holder
boots with ``tests/graph/test_single_writer_across_processes.py::_boot``. Every file lives in ``tmp_path``.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.protocols import WriterLeaseHeld
from tests.graph.test_single_writer_across_processes import _boot, _run_child


def _two_names(tmp_path: Path) -> tuple[Path, Path]:
    """Two directories, so the two names of one file share no parent and no sidecar."""
    first = tmp_path / "first" / "graph.sqlite3"
    second = tmp_path / "second" / "graph.sqlite3"
    first.parent.mkdir()
    second.parent.mkdir()
    return first, second


def test_a_second_process_boots_a_writer_through_the_new_name_of_a_moved_live_file(tmp_path: Path) -> None:
    held, moved = _two_names(tmp_path)
    holder = _boot("sqlite", {"database_path": held})
    try:
        before = os.stat(held)
        os.rename(held, moved)
        after = os.stat(moved)
        assert (after.st_dev, after.st_ino, after.st_nlink) == (before.st_dev, before.st_ino, 1)
        new_name = _run_child("sqlite", {"database_path": moved})
    finally:
        holder.close()

    assert new_name == ("BOOTED", "", ""), (
        "a writer booted through the new name of a moved live file was refused; if the lease now follows the"
        f" file, SqliteWriterLease's docstring and this module are out of date: {new_name!r}"
    )


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


def test_sqlite_keeps_a_write_ahead_log_per_name_so_a_second_name_misses_what_the_first_committed(
    tmp_path: Path,
) -> None:
    held, linked = _two_names(tmp_path)
    first = sqlite3.connect(held, isolation_level=None)
    try:
        first.execute("PRAGMA journal_mode = WAL")
        first.execute("PRAGMA wal_autocheckpoint = 0")
        first.execute("CREATE TABLE committed_through_the_first_name (x)")
        os.link(held, linked)
        through_the_same_name = _tables_seen_through(held)
        through_the_other_name = _tables_seen_through(linked)
    finally:
        first.close()

    assert through_the_same_name == "['committed_through_the_first_name']"
    assert through_the_other_name == "[]"



def test_a_second_process_cannot_boot_a_writer_through_a_hard_link_to_a_held_graph(tmp_path: Path) -> None:
    held, linked = _two_names(tmp_path)
    holder = _boot("sqlite", {"database_path": held})
    try:
        os.link(held, linked)
        assert os.path.samefile(held, linked)
        same_name = _run_child("sqlite", {"database_path": held})
        other_name = _run_child("sqlite", {"database_path": linked})
    finally:
        holder.close()

    assert same_name[:2] == ("REFUSED", "SingleWriterViolation"), same_name
    assert other_name[:2] == ("REFUSED", "SingleWriterViolation"), other_name
    assert "has 2 names (hard links)" in other_name[2], other_name


def test_the_lease_refuses_a_database_file_with_a_second_name_through_either_name(tmp_path: Path) -> None:
    held, linked = _two_names(tmp_path)
    with SqliteGraphStore(database_path=held) as store:
        lease = store.writer_lease()  # control: a file with one name is leased
    try:
        os.link(held, linked)
        with SqliteGraphStore(database_path=linked) as store, pytest.raises(
            WriterLeaseHeld, match=r"has 2 names \(hard links\)"
        ):
            store.writer_lease()
    finally:
        lease.release()
    with SqliteGraphStore(database_path=held) as store, pytest.raises(
        WriterLeaseHeld, match=r"has 2 names \(hard links\)"
    ):
        store.writer_lease()
    os.unlink(linked)
    with SqliteGraphStore(database_path=held) as store:
        store.writer_lease().release()  # control: the refusal goes with the second name
