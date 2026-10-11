# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-013, P2 (b): a SQLite database file with more than one name is refused before any setup write, readers included.

Dave's ruling (``D-IMPL-378``, the 2026-10-09 06:06 MST list, item 10, confirmed at 06:21 MST as "P1(a), P2(b)"),
verbatim: *"Refuse undeclared identity-lock configuration; reject multi-name files before any setup writes, including
reader setup. Verify the identity lock still blocks the renamed-file second writer. Do not fall back silently to the
old path lock."* The option ruled, P2 (b) (lane ``378g-c8``), verbatim: *"In ``SqliteGraphStore.__init__``, refuse a
file with more than one name before the setup runs, for every open, readers included."* P1 (a), what a boot that
declares no lock directory does, is design-first and is not measured here.

**The hole, measured by lane ``378g-c8``.** ``src/ccf/graph/backends/sqlite.py::SqliteGraphStore`` runs its setup
(the write-ahead-log pragma and the schema) when it is opened, before any lease is consulted. SQLite keeps a
write-ahead log per name a file is opened through
(``tests/graph/test_sqlite_writer_lease_hard_link.py::test_sqlite_keeps_a_write_ahead_log_per_name_so_a_second_name_misses_what_the_first_committed``),
so an open through a hard link writes its setup into a log beside the link, and leaves that log behind while the
holder is live. Opened through the link again later, by anything, that log rolls back what the holder committed, and
``integrity_check`` still says ``ok``. Option (B)'s name count refuses at the writer lease and option (C)'s file lease
at the mint: both after the setup has written. A read-only boot takes no lease and was not refused at all.

**What this module asserts, each by its mechanism, never by a missing word:**

1. A second open through a hard link while a holder is live and has committed (a writer, a writer that declares the
   lock directory, and a read-only reader, each in another process) is refused with ``WriterLeaseHeld``, in words
   that name the file's two names and say the store refused to open it, and it wrote nothing: nothing appears beside
   the link (no ``-wal``, ``-shm``, journal or sidecar), the database file's bytes are unchanged, and once both have
   closed and the file is opened through the link again, the holder's committed row is still there.
2. A reader open of a file with two names, the store itself and a read-only boot (the examiner's road), is refused by
   name through either name, writes nothing, and opens again once the second name is gone.
3. The store opens no SQLite connection to a file with more than one name.
4. A second name made in the instant between the store's first count and its SQLite connection is refused by a
   second count, before the setup, and the connection the store opened is closed.

The second process is spawned as ``tests/graph/test_single_writer_across_processes.py::_run_child`` is, and reports
its outcome by exception class NAME and message. The database file's bytes are read only in another process: one open
and close of the file inside the holder's process drops SQLite's own locks there, and that alone hides the loss on the
base (measured; see ``_SHA256_OF``). Every file lives in ``tmp_path``.
"""

from __future__ import annotations

import contextlib
import multiprocessing as mp
import os
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.leases import lock_directory_writer_lease
from ccf.graph.protocols import WriterLeaseHeld
from tests.graph.test_single_writer_across_processes import _boot
from tests.graph.test_sqlite_writer_lease_file_identity import _boot_read_only, _declared, _locks
from tests.graph.test_sqlite_writer_lease_hard_link import _two_names

_TIMEOUT_SECONDS = 120

#: The refusal's own words for a database file with two names (option (B)'s at the lease use the same ones).
_TWO_NAMES = "has 2 names (hard links)"

#: The words that say the refusal came when the store was OPENED, not at the writer lease.
_REFUSED_AT_OPEN = "the store refuses to open it, readers included, before any connection or setup"

#: The row the holder commits through its own connection, in its own graph's table.
_TENANT = "tenant-p2b"
_COMMITTED_BY_THE_HOLDER = "urn:ccf:test:p2b:committed-by-the-holder"

_WRITER = "writer"
_DECLARING_WRITER = "writer declaring the lock directory"
_READER = "read-only reader"


#: Hashes a file's bytes in ANOTHER process. Opening and closing any descriptor on the database file inside a process
#: that holds a SQLite connection to it drops every POSIX lock that process holds on the file, SQLite's own included,
#: and that changes what a second open does: measured on this test's base, the second open then checkpoints its setup
#: into the shared file instead of leaving its log beside the link, and the holder's row survives. This module's own
#: process therefore never opens the database file while it holds it.
_SHA256_OF = "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())"


def _entries(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir())


def _sha256(path: Path) -> str:
    """The file's SHA-256, read in another process (see :data:`_SHA256_OF`)."""
    return subprocess.run(
        [sys.executable, "-c", _SHA256_OF, str(path)], capture_output=True, text=True, check=True
    ).stdout.strip()


@contextlib.contextmanager
def _a_live_writer_that_has_committed(held: Path, locks: Path | None) -> Iterator[None]:
    """A live writer over ``held``: its store open, its writer lease held, one row committed through its connection.

    The row stays in the holder's write-ahead log, uncheckpointed, until the holder closes, as a live writer's commits
    do between checkpoints.
    """
    store = SqliteGraphStore(
        database_path=held, writer_lease=None if locks is None else lock_directory_writer_lease(str(locks))
    )
    try:
        lease = store.writer_lease()
        try:
            with store.connection:
                store.connection.execute(
                    "INSERT INTO entities (tenant_id, entity_uri, entity_class, first_observed_at, last_observed_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (_TENANT, _COMMITTED_BY_THE_HOLDER, "Probe", "2026-10-09T00:00:00Z", "2026-10-09T00:00:00Z"),
                )
            yield
        finally:
            lease.release()
    finally:
        store.close()


def _holder_rows_seen_through(path: Path) -> tuple[list[str], str]:
    """What a later open through ``path`` sees of the holder's row, and SQLite's integrity check: plain ``sqlite3``."""
    connection = sqlite3.connect(path)
    try:
        rows = [row[0] for row in connection.execute("SELECT entity_uri FROM entities WHERE tenant_id = ?", (_TENANT,))]
        return rows, connection.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        connection.close()


def _child_open(kind: str, connection: dict[str, Any], queue: mp.Queue[tuple[str, str, str]]) -> None:
    """Spawned child: open the fabric once, as a writer boot or a read-only boot, report the outcome, then exit."""
    try:
        handle = _boot_read_only(connection) if kind == _READER else _boot("sqlite", connection)
    except BaseException as exc:  # reported by name, asserted by the parent
        queue.put(("REFUSED", type(exc).__name__, str(exc)))
        return
    queue.put(("OPENED", "", ""))
    handle.close()


def _open_in_another_process(kind: str, connection: dict[str, Any]) -> tuple[str, str, str]:
    """Run :func:`_child_open` in a spawned process and return its report once that process has exited."""
    ctx = mp.get_context("spawn")
    queue: mp.Queue[tuple[str, str, str]] = ctx.Queue()
    process = ctx.Process(target=_child_open, args=(kind, connection, queue))
    process.start()
    try:
        return queue.get(timeout=_TIMEOUT_SECONDS)
    finally:
        process.join(timeout=_TIMEOUT_SECONDS)


@pytest.mark.parametrize("kind", [_WRITER, _DECLARING_WRITER, _READER])
def test_a_second_open_through_a_hard_link_is_refused_before_it_writes_anything_and_the_holder_keeps_its_commit(
    kind: str, tmp_path: Path
) -> None:
    held, linked = _two_names(tmp_path)
    locks = _locks(tmp_path) if kind == _DECLARING_WRITER else None
    connection = {"database_path": linked} if locks is None else _declared(linked, locks)
    with _a_live_writer_that_has_committed(held, locks):
        os.link(held, linked)
        beside_the_link_before, bytes_before = _entries(linked.parent), _sha256(held)
        outcome = _open_in_another_process(kind, connection)
        beside_the_link_after, bytes_after = _entries(linked.parent), _sha256(held)
    # Both have closed: the holder here, and the second open's process has exited. Anything that now opens the file
    # through the link replays whatever log the second open left beside it.
    through_the_link, integrity = _holder_rows_seen_through(linked)
    through_the_holders_name, _ = _holder_rows_seen_through(held)
    observed = "\n".join(
        f"{label}: {value!r}"
        for label, value in (
            ("second open", outcome),
            ("beside the link before", beside_the_link_before),
            ("beside the link after", beside_the_link_after),
            ("database file bytes changed by the second open", bytes_after != bytes_before),
            ("holder's rows through the link after both closed", through_the_link),
            ("holder's rows through its own name after that", through_the_holders_name),
            ("integrity_check", integrity),
        )
    )

    assert outcome[:2] == ("REFUSED", "WriterLeaseHeld"), observed
    assert f"{str(linked)!r} {_TWO_NAMES}" in outcome[2], observed
    assert _REFUSED_AT_OPEN in outcome[2], observed
    assert beside_the_link_after == beside_the_link_before == ["graph.sqlite3"], observed
    assert bytes_after == bytes_before, observed
    assert through_the_link == through_the_holders_name == [_COMMITTED_BY_THE_HOLDER], observed
    assert integrity == "ok", observed


def test_a_reader_open_of_a_file_with_two_names_is_refused_by_name_through_either_name(tmp_path: Path) -> None:
    held, linked = _two_names(tmp_path)
    SqliteGraphStore(database_path=held).close()  # a graph, and nobody has it open
    os.link(held, linked)
    before = (_entries(held.parent), _entries(linked.parent), _sha256(held))

    for name in (held, linked):
        with pytest.raises(WriterLeaseHeld) as store_open:
            SqliteGraphStore(database_path=name)
        with pytest.raises(WriterLeaseHeld) as read_only_boot:
            _boot_read_only({"database_path": name})
        for refusal in (store_open, read_only_boot):
            assert f"{str(name)!r} {_TWO_NAMES}" in str(refusal.value), str(refusal.value)
            assert _REFUSED_AT_OPEN in str(refusal.value), str(refusal.value)

    assert (_entries(held.parent), _entries(linked.parent), _sha256(held)) == before
    os.unlink(linked)
    SqliteGraphStore(database_path=held).close()  # control: the refusal goes with the second name
    _boot_read_only({"database_path": held}).close()


def test_the_store_opens_no_sqlite_connection_to_a_file_with_more_than_one_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    held, linked = _two_names(tmp_path)
    SqliteGraphStore(database_path=held).close()
    os.link(held, linked)
    connected: list[str] = []
    real_connect = sqlite3.connect

    def counting_connect(database: Any, *args: Any, **kwargs: Any) -> sqlite3.Connection:
        connected.append(str(database))
        return real_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", counting_connect)
    with pytest.raises(WriterLeaseHeld) as refused:
        SqliteGraphStore(database_path=linked)
    monkeypatch.undo()

    assert _REFUSED_AT_OPEN in str(refused.value), str(refused.value)
    assert connected == [], f"the store opened a SQLite connection to a file with two names: {connected!r}"


def test_a_second_name_made_between_the_first_count_and_the_connection_is_refused_before_the_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    held, linked = _two_names(tmp_path)
    SqliteGraphStore(database_path=held).close()
    before = (_entries(held.parent), _sha256(held))
    opened: list[sqlite3.Connection] = []
    real_connect = sqlite3.connect

    def connect_after_a_second_name_appears(database: Any, *args: Any, **kwargs: Any) -> sqlite3.Connection:
        os.link(held, linked)  # made after the store's first count, before its connection
        connection = real_connect(database, *args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", connect_after_a_second_name_appears)
    with pytest.raises(WriterLeaseHeld) as refused:
        SqliteGraphStore(database_path=held)
    monkeypatch.undo()

    assert f"{str(held)!r} {_TWO_NAMES}" in str(refused.value), str(refused.value)
    assert _REFUSED_AT_OPEN in str(refused.value), str(refused.value)
    assert (_entries(held.parent), _sha256(held)) == before, "the setup ran: something was written beside the name"
    assert _entries(linked.parent) == ["graph.sqlite3"]
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")
