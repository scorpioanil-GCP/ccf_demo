# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SQLite reference ``GraphStore`` — schema, connection, and the read path.

Whitepaper §7.3 (the Context Graph as first-class persisted state); DESIGN.md
§2A.5.2 (the D-IMPL-34 semantics) and D-IMPL-02 (SQLite as the development
reference backend, load-bearing for the §9 examples discipline).

**What this module deliberately does not contain: any way to write.**
:class:`SqliteGraphStore` owns the connection and the schema; the read path is
here (as five statements handed to :class:`ccf.graph.reader.BaseGraphReader`);
every ``INSERT`` and every supersession ``UPDATE`` lives in
``ccf.graph._writer``, which the CINV-02 lint confines to ``ccf.assembly`` and
``ccf.boot``. Putting a "convenience" write helper here would hand a write path
to every module that legitimately needs to read (04-RESEARCH.md anti-patterns).

**Physical layout.** Five tables, none of them normative — the whitepaper's
"~10 collections" is reference grounding, not a count to match:

``entities`` / ``relationships``
    Node and edge identity. ``UNIQUE (tenant_id, entity_uri)`` puts compound
    uniqueness *at the persistence tier*, where a concurrent second writer or a
    buggy caller still cannot get around it — application-layer uniqueness
    checks are advisory in a way an index is not (INV-CH7-16).

``entity_claims`` / ``relationship_claims``
    Append-only claim history. Rows are never deleted and their content is
    never updated; the only columns that change after insert are
    ``superseded_by`` / ``superseded_at``, which is what supersession *is*
    (INV-CH7-04, INV-CH7-21). Keeping identity and history in separate tables
    is what lets both "one node per ``(tenant, uri)``" and "every claim ever
    made survives" be true simultaneously.

``lineage``
    Append-only child table keyed on the full lineage-entry identity, giving L
    set-union semantics for free: a re-delivered envelope collides and is
    ignored, a second source does not (INV-CH7-17).

Timestamps are stored as canonical RFC3339 UTC text
(:func:`ccf.contracts.canonical.canonical_timestamp`) so ordering comparisons
in SQL are chronological and so the text a backend stores is the same text the
canonical serializer produces.

Every statement is parameterized. There is no f-string SQL in this module and
none may be added: string-built SQL is how tenant scoping becomes bypassable.
The translated ``GraphQuery`` statements (plan 15.2-09) are *generated*, and
the rule holds for them in the form that matters: statement text is composed
exclusively of code-authored fragments plus ``?`` placeholder repetition sized
by set cardinality — every tenant id, boundary, policy version,
classification, entity URI, seed, JSON path and depth bound travels as a bound
parameter, never as text (threat T-15.2-01). The translated as-of predicates
compare canonical RFC3339 UTC text exactly as the five fixed statements do,
which is what keeps INV-CH7-14 pushable as plain text comparison (`GQ-24` at
docs/GRAPH_QUERY_SEMANTICS.md:482).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import os
import re
import sqlite3
import stat
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import TracebackType
from typing import ClassVar

from ccf.contracts.canonical import canonical_timestamp
from ccf.graph.protocols import (
    GraphQuery,
    ProcessScopedWriterLease,
    WriterLease,
    WriterLeaseHeld,
    WriterLeaseScope,
    WriterLeaseSource,
    acquire_declared_writer_lease,
)

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - a platform without flock (Windows)
    _fcntl = None  # type: ignore[assignment]
from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, BaseGraphReader, Row

__ccf_mode__ = "algorithmic"

__all__ = ["ENTITY_KIND", "RELATIONSHIP_KIND", "SqliteGraphReader", "SqliteGraphStore"]

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS entities (
        tenant_id TEXT NOT NULL,
        entity_uri TEXT NOT NULL,
        entity_class TEXT NOT NULL,
        first_observed_at TEXT NOT NULL,
        last_observed_at TEXT NOT NULL,
        UNIQUE (tenant_id, entity_uri)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entity_claims (
        tenant_id TEXT NOT NULL,
        entity_uri TEXT NOT NULL,
        claim_id TEXT NOT NULL,
        claim_json TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        policy_bundle_version TEXT NOT NULL,
        superseded_by TEXT,
        superseded_at TEXT,
        PRIMARY KEY (tenant_id, entity_uri, claim_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS relationships (
        tenant_id TEXT NOT NULL,
        relationship_key TEXT NOT NULL,
        relationship_type TEXT NOT NULL,
        subject_uri TEXT NOT NULL,
        object_uri TEXT NOT NULL,
        first_observed_at TEXT NOT NULL,
        last_observed_at TEXT NOT NULL,
        UNIQUE (tenant_id, relationship_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS relationship_claims (
        tenant_id TEXT NOT NULL,
        relationship_key TEXT NOT NULL,
        claim_id TEXT NOT NULL,
        claim_json TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        policy_bundle_version TEXT NOT NULL,
        superseded_by TEXT,
        superseded_at TEXT,
        PRIMARY KEY (tenant_id, relationship_key, claim_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lineage (
        tenant_id TEXT NOT NULL,
        claim_kind TEXT NOT NULL,
        node_key TEXT NOT NULL,
        claim_id TEXT NOT NULL,
        lineage_id TEXT NOT NULL,
        entry_json TEXT NOT NULL,
        PRIMARY KEY (tenant_id, claim_kind, node_key, claim_id, lineage_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_entity_claims_observed
        ON entity_claims (tenant_id, observed_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_relationship_claims_observed
        ON relationship_claims (tenant_id, observed_at)
    """,
)


#: Appended to the resolved database path to name the writer-lease sidecar.
#: Not ``.lock``: SQLite's own ``unix-dotfile`` VFS uses ``<db>.lock``.
WRITER_LEASE_SUFFIX = ".ccf-writer.lock"

#: SQLite's names for a database with no file of its own: ``":memory:"`` and the
#: private temporary database ``""``. No second process can reach either, and
#: neither has a device and inode a declared writer lease could follow.
_NO_FILE_DATABASES = frozenset({":memory:", ""})


def _database_file_identity(database_path: str) -> str | None:
    """The database file's identity — its device and inode — or ``None`` when it has none.

    SEC-013, option (C) (Dave, 2026-10-08 21:24 MST; D-IMPL-378). What a
    declared writer lease is keyed on: every name of one file, a hard link or
    the new name of a renamed file, has the same device and inode, so every
    writer of the file asks for the same lock, whatever name it reached it by.
    Read by :class:`SqliteGraphStore` right after SQLite opens the file.
    """
    if database_path in _NO_FILE_DATABASES:
        return None
    try:
        status = os.stat(database_path)
    except OSError:
        return None
    return f"sqlite-database-file:{status.st_dev}:{status.st_ino}"


def _refuse_a_file_with_more_than_one_name(database_path: str) -> None:
    """Refuse the database file ``database_path`` names if it has more than one name (a hard link).

    SEC-013, P2 (b) (Dave, 2026-10-09; ``D-IMPL-378``): *"reject multi-name
    files before any setup writes, including reader setup."* SQLite keeps a
    write-ahead log beside each name a file is opened through, so an open
    through a second name, even one that only reads, writes the store's setup
    into a log beside that name and leaves it there while another process
    holds the file; the next open through that name rolls back what was
    committed through the other, and SQLite's integrity check still reports
    ``ok`` (measured by
    ``tests/graph/test_sqlite_open_refuses_a_file_with_more_than_one_name.py::test_a_second_open_through_a_hard_link_is_refused_before_it_writes_anything_and_the_holder_keeps_its_commit``).
    :class:`SqliteGraphStore` calls this before SQLite connects and again once
    it has, before the setup's first statement.

    A path that names no file has no name to count: SQLite creates the file
    with one name, or refuses the path itself, as it always has. Only a
    regular file's names are counted: a hard link names a regular file, while
    a directory's link count counts its subdirectories, not other names for
    it. ``":memory:"`` and ``""`` have no file.

    Raises:
        WriterLeaseHeld: the file has more than one name. The type option (B)'s
            refusal at the writer lease raises, here raised by the store's
            open, readers included, where no mint translates it.
        OSError: the file's names cannot be counted for a reason other than
            there being no file at the path.
    """
    if database_path in _NO_FILE_DATABASES:
        return
    try:
        status = os.stat(database_path)
    except (FileNotFoundError, NotADirectoryError):
        return
    if stat.S_ISREG(status.st_mode) and status.st_nlink > 1:
        raise WriterLeaseHeld(
            f"the SQLite database file {database_path!r} has"
            f" {status.st_nlink} names (hard links); an open through any of"
            " them, even to read, can leave a write-ahead log beside that name"
            " that later rolls back what was committed through another, so"
            " the store refuses to open it, readers included, before any"
            " connection or setup: remove the other names (SEC-013)"
        )


class SqliteWriterLease:
    """The SQLite writer lease: an exclusive ``flock`` on a sidecar file.

    SEC-013 (D-IMPL-372); whitepaper §7.3 / INV-CH7-10, CLAUDE.md §10. Scope
    ``"cross-process"``. ``fcntl.flock(LOCK_EX | LOCK_NB)`` on
    ``<resolved database path>.ccf-writer.lock``, opened ``O_RDWR | O_CREAT |
    O_CLOEXEC`` with mode ``0o600``, and the descriptor kept open for the
    lease's life:

    * **``flock``, never ``lockf``.** A ``flock`` belongs to an open file
      description, so a second descriptor — in another process *or this one* —
      is refused. POSIX record locks (``lockf``/``fcntl``) are per process: a
      second descriptor in the holding process is granted, and closing *any*
      descriptor on the file drops them.
    * **An OS lock, never a file-existence check.** The kernel drops the lock
      when the holder dies, however it dies; the sidecar file persists and is
      harmless. A crashed holder therefore never wedges a later boot.
    * **Keyed on the resolved path, and on a file with one name.** A
      relative and an absolute spelling of one path, or a symbolic link to
      it, resolve to one sidecar, so they are one graph to the lease. A hard
      link resolves to itself and the sidecar beside it is another file, so a
      lock beside one name cannot exclude a writer through another:
      :meth:`SqliteGraphStore.writer_lease` therefore refuses a database file
      with more than one name, through either name, as ``WriterLeaseHeld``
      (measured by
      ``tests/graph/test_sqlite_writer_lease_hard_link.py::test_the_lease_refuses_a_database_file_with_a_second_name_through_either_name``).
      Since P2 (b) (``D-IMPL-378``) the store refuses such a file earlier,
      when it is opened, readers included, so a second process never boots
      through a hard link to a held graph
      (``tests/graph/test_sqlite_writer_lease_hard_link.py::test_a_second_process_cannot_boot_a_writer_through_a_hard_link_to_a_held_graph``);
      the lease's count refuses a second name made after the store opened.
      **Not closed:** a live file moved to a new name keeps one name, and a
      writer booted through the new name in a second process is not refused
      while the first process's writer is live (measured by
      ``tests/graph/test_sqlite_writer_lease_hard_link.py::test_a_second_process_boots_a_writer_through_the_new_name_of_a_moved_live_file``).
      **Unless a lock directory is declared:** with ``writer_lease_lock_dir``
      declared, :meth:`SqliteGraphStore.writer_lease` also holds a lock keyed
      on the database file's device and inode, which refuses that writer
      among writers that declare the same directory (a writer through a hard
      link is refused earlier, when its store opens) (SEC-013, option (C);
      measured by
      ``tests/graph/test_sqlite_writer_lease_file_identity.py::test_a_second_process_is_refused_through_the_new_name_of_the_renamed_live_file``).
      SQLite names its write-ahead log after the path too, so a second name
      reads another log and misses what the first committed
      (``tests/graph/test_sqlite_writer_lease_hard_link.py::test_sqlite_keeps_a_write_ahead_log_per_name_so_a_second_name_misses_what_the_first_committed``):
      do not move a live database file while a writer holds it.
    * **Never blocks.** A held lease raises
      ``src/ccf/graph/protocols.py::WriterLeaseHeld`` at once.

    Filesystem caveat: the lease is as good as the filesystem's ``flock``.
    WAL-mode SQLite (this store's mode) is already unsupported on network
    filesystems, so the sidecar adds no new constraint; a process ``fork``-ed
    while holding the lease shares it until that child exits.

    **Two limits an operator must know, disclosed by ruling** (``D-IMPL-378``,
    Dave, 2026-10-08 21:24 MST: option (B) "with the rename gap and hard-link
    backup restriction explicitly disclosed"). ``SEC-013`` stays open.

    * **Do not move a live database file.** A file moved to a new name while
      a writer holds it keeps one name, so it is not refused, and a writer
      booted through the new name in a second process is not refused while
      the first is live (measured above). SQLite leaves the live write-ahead
      log beside the old name, so the new name does not see what the writer
      committed; once both names have been written through and closed, what
      was committed through the old name is gone, and SQLite's integrity
      check still reports ``ok``
      (``tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_moved_live_file_leaves_its_write_ahead_log_behind_and_its_commits_are_lost``).
      Stop every process that has the file open before moving it: a file
      moved while closed is one graph under its new name
      (``tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_database_file_moved_while_no_process_has_it_open_is_leased_under_its_new_name``).
      Option (C), the lock keyed on the file's device and inode in a declared
      directory (``writer_lease_lock_dir``), refuses that second writer among
      writers that declare the same directory, but no lock keeps the old
      name's commits: do not move a live file either way. ``SEC-013`` stays
      open.
    * **A hard-link backup refuses every open, an examiner's included.** A
      backup that links the database file instead of copying it gives the
      file a second name. Until that name is removed, the store refuses to
      open the file through either name, even with no writer live, so every
      writer boot of the graph, in any process, is refused with
      ``WriterLeaseHeld`` when its store opens
      (``tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_hard_link_backup_refuses_every_writer_boot_until_it_is_removed``),
      and since P2 (b) (``D-IMPL-378``) so is every read-only boot: an
      examiner cannot open a file that has a hard-link backup
      (``tests/graph/test_sqlite_open_refuses_a_file_with_more_than_one_name.py::test_a_reader_open_of_a_file_with_two_names_is_refused_by_name_through_either_name``).
      Back the file up with a copy SQLite writes itself instead: its online
      backup API (``sqlite3.Connection.backup``) or ``VACUUM INTO``. Either
      can run while a writer is live, and the file keeps one name
      (``tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_copy_sqlite_makes_while_the_writer_is_live_leaves_the_file_one_name``).
    """

    def __init__(self, *, sidecar: Path) -> None:
        if _fcntl is None:  # pragma: no cover - a platform without flock
            raise RuntimeError(
                "the SQLite writer lease requires fcntl.flock, which this"
                " platform lacks; refusing to boot a writer unleased (SEC-013)"
            )
        fd = os.open(sidecar, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
        try:
            _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise WriterLeaseHeld(f"flock on {str(sidecar)!r} is held") from None
        except BaseException:
            os.close(fd)
            raise
        self._fd: int | None = fd
        self._sidecar = sidecar

    @property
    def scope(self) -> WriterLeaseScope:
        return "cross-process"

    @property
    def mechanism(self) -> str:
        return f"flock on {str(self._sidecar)!r}"

    def release(self) -> None:
        """Unlock and close the sidecar descriptor. Idempotent."""
        fd, self._fd = self._fd, None
        if fd is None:
            return
        try:
            if _fcntl is not None:
                _fcntl.flock(fd, _fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def __enter__(self) -> SqliteWriterLease:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


class _SqliteFileWriterLease:
    """The sidecar lease and a declared lease on the database FILE, held and given back together.

    SEC-013, option (C) (Dave, 2026-10-08 21:24 MST; D-IMPL-378). What
    :meth:`SqliteGraphStore.writer_lease` returns when the deployment declared
    a lease: the :class:`SqliteWriterLease` sidecar (keyed on the name) plus the
    declared lease keyed on the database file's device and inode. Scope
    ``"cross-process"``: both halves are. :meth:`release` gives back the file
    lease, then the sidecar, whatever the first does; both are idempotent, so
    this is too.
    """

    def __init__(
        self, *, sidecar: WriterLease, file_lease: WriterLease, file_identity: str
    ) -> None:
        self._sidecar = sidecar
        self._file_lease = file_lease
        self._file_identity = file_identity

    @property
    def scope(self) -> WriterLeaseScope:
        return "cross-process"

    @property
    def mechanism(self) -> str:
        return (
            f"{self._sidecar.mechanism}; and {self._file_lease.mechanism}, keyed"
            f" on the database file ({self._file_identity})"
        )

    def release(self) -> None:
        """Give back the file lease, then the sidecar. Idempotent."""
        try:
            self._file_lease.release()
        finally:
            self._sidecar.release()

    def __enter__(self) -> _SqliteFileWriterLease:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


def _with_the_file_lease(
    sidecar: WriterLease, declared: tuple[WriterLeaseSource, str], resolved: Path
) -> _SqliteFileWriterLease:
    """Acquire the declared lease on the database FILE beside the held sidecar, or give the sidecar back and refuse.

    SEC-013, option (C) (Dave, 2026-10-08 21:24 MST; D-IMPL-378). ``declared``
    is the deployment's lease source and the file identity
    (:func:`_database_file_identity`) read when the store opened the file. The
    acquisition goes through
    ``src/ccf/graph/protocols.py::acquire_declared_writer_lease``, as every
    network store's does, so a declared lease that does not exclude other
    processes is refused with ``WriterLeaseRequired``. Another holder of the
    file's lease is refused as ``WriterLeaseHeld`` naming the file, its
    identity and the lock that is held.
    """
    source, file_identity = declared
    try:
        file_lease = acquire_declared_writer_lease(
            source, substrate="sqlite", graph_identity=file_identity
        )
    except WriterLeaseHeld as exc:
        sidecar.release()
        raise WriterLeaseHeld(
            f"the database file {str(resolved)!r} ({file_identity}) is held by"
            " another writer that declared the same lock directory, whatever"
            f" name it reached the file by: {exc} (SEC-013)"
        ) from exc
    except BaseException:
        sidecar.release()
        raise
    return _SqliteFileWriterLease(
        sidecar=sidecar, file_lease=file_lease, file_identity=file_identity
    )


class SqliteGraphStore:
    """Connection and schema owner for the SQLite reference backend.

    Args:
        database_path: File to open. A distinct path per fabric is what makes
            "one writer per graph" a checkable statement at boot.
        writer_lease: A deployment-declared writer lease
            (``src/ccf/graph/protocols.py::WriterLeaseSource``) that follows
            the database FILE (SEC-013, option (C), D-IMPL-378): the boot
            passes the lock-directory lease ``writer_lease_lock_dir`` declares
            (``src/ccf/graph/backends/sqlite_write.py::SqliteConnection``).
            The store reads the file's device and inode right after SQLite
            opens it, and :meth:`writer_lease` acquires this lease for that
            identity, in addition to the sidecar. Never acquired at open.

    Raises:
        ValueError: ``writer_lease`` is declared and the database has no file
            to follow (``":memory:"`` or ``""``), or none at its path once
            opened. Raised before the store's own setup runs.
        WriterLeaseHeld: the database file has more than one name (a hard
            link), for every open, readers included (SEC-013, P2 (b),
            ``D-IMPL-378``). The names are counted before SQLite connects and
            again once it has, before the setup's first statement, so a
            refused open writes nothing through any name, and a connection
            opened between the two counts is closed unused (measured by
            ``tests/graph/test_sqlite_open_refuses_a_file_with_more_than_one_name.py::test_a_second_open_through_a_hard_link_is_refused_before_it_writes_anything_and_the_holder_keeps_its_commit``
            and
            ``tests/graph/test_sqlite_open_refuses_a_file_with_more_than_one_name.py::test_a_second_name_made_between_the_first_count_and_the_connection_is_refused_before_the_setup``).
            An examiner cannot open a file that has a hard-link backup either.

    **What the two counts do not see** (P2 (b)'s time-of-check window). Each
    count reads whatever file the path names at that moment. A second name
    made after the second count and before the setup's first statement (an
    instant) is not refused, and neither is a file swapped in under the path
    between SQLite's open and the second count: Python's ``sqlite3`` exposes no
    descriptor to count the opened file's names through. A name made after
    the store has opened is not this open's to refuse: the open connection
    keeps its own name, every later open through either name is refused, and
    a writer's lease refuses it at the mint (:meth:`writer_lease`). Only this
    store's opens are refused; a tool that opens the file with SQLite directly
    is not.

    The store is *not* a ``GraphStore`` in the sense of offering both halves of
    the Protocol: it offers :attr:`reader` and, to the writer module alone, the
    connection. See the module docstring.
    """

    def __init__(
        self,
        *,
        database_path: Path | str,
        writer_lease: WriterLeaseSource | None = None,
    ) -> None:
        self._database_path = str(database_path)
        # SEC-013, P2 (b): a file with more than one name is refused before
        # SQLite connects, so nothing is opened or written through any name...
        _refuse_a_file_with_more_than_one_name(self._database_path)
        self._connection = sqlite3.connect(self._database_path)
        try:
            # ...and counted again now that SQLite has it open, before the
            # setup's first statement: a name made between the two counts is
            # refused here, and the connection is closed unused.
            _refuse_a_file_with_more_than_one_name(self._database_path)
        except BaseException:
            self._connection.close()
            raise
        # SEC-013, option (C): the file THIS connection opened, read once, at
        # once, so the declared lease follows that file whatever it is called
        # when the mint takes the lease.
        self._declared_file_lease: tuple[WriterLeaseSource, str] | None = None
        if writer_lease is not None:
            file_identity = _database_file_identity(self._database_path)
            if file_identity is None:
                self._connection.close()
                raise ValueError(
                    f"the SQLite database {self._database_path!r} has no database"
                    " file (an in-memory database, or no file at its path once"
                    " opened), so a declared writer lease, which follows the"
                    " database file's device and inode, has nothing to follow"
                    " (SEC-013)"
                )
            self._declared_file_lease = (writer_lease, file_identity)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA foreign_keys = ON")
        with self._connection:
            for statement in _SCHEMA:
                self._connection.execute(statement)
        self._reader = SqliteGraphReader(self._connection)

    @property
    def graph_identity(self) -> str:
        """Stable identity of the persisted graph this store is attached to.

        The single-writer boot check keys on this: two writers over two
        different databases are two fabrics, while two writers over the same
        database are the violation.
        """
        return self._database_path

    def writer_lease(self) -> WriterLease:
        """Acquire the cross-process writer lease (SEC-013): see :class:`SqliteWriterLease`.

        Called by the mint only, never at open: a second, read-only store over
        a live fabric's file is legitimate and takes no lease.

        **With a lease declared** (``writer_lease=``; SEC-013, option (C),
        D-IMPL-378) the sidecar is taken first, then the declared lease for the
        database file's identity read at open — through
        ``src/ccf/graph/protocols.py::acquire_declared_writer_lease``, so a
        declared lease that does not exclude other processes is refused — and
        then the name count below; the lease returned holds both locks. A
        writer of the same file through the new name of a renamed file that
        declared the same directory is refused by the file lease, before the
        name count is read. A writer through a hard link never gets this far:
        the store refuses a file with more than one name when it is opened,
        before its setup (P2 (b), ``D-IMPL-378``; see :class:`SqliteGraphStore`).
        **This lease still comes after the store's own setup:** the mint takes
        it after the store has opened the database and run its setup, through
        whatever single name the store was opened by.

        The name count below refuses a database file that gained a second
        name after this store opened it, whether or not a writer is live; one
        that had a second name when the store opened was refused then. Either
        way a hard link a backup made to the file refuses every writer boot
        until it is removed, and, since P2 (b), every read-only boot too. A
        file moved to a new name while a
        writer holds it keeps one name and is not refused by the name count;
        only the declared file lease above refuses it, so a deployment that
        declares no lock directory keeps that gap (``SEC-013`` stays open on
        it). Both limits, and what an operator does instead, are disclosed in
        :class:`SqliteWriterLease`.

        Raises:
            WriterLeaseHeld: another holder — in any process — has the lease
                (the sidecar, or the declared lease on the database file), or
                the database file has gained a second name (a hard link) since
                this store opened it, so a lock beside this name could not
                exclude a writer through another.
            WriterLeaseRequired: the declared lease's scope is not
                ``"cross-process"``.
        """
        if self._declared_file_lease is None:
            # P1 (a) (D-IMPL-378; Tuesday GO item 4): a file database mints a
            # writer only under the declared identity lock. No silent fallback
            # to the path-only sidecar, which a renamed live file escapes.
            if self._database_path in _NO_FILE_DATABASES:
                return ProcessScopedWriterLease(substrate="sqlite")
            return acquire_declared_writer_lease(
                None, substrate="sqlite", graph_identity=self._database_path
            )
        resolved = Path(self._database_path).resolve()
        lease: WriterLease = SqliteWriterLease(
            sidecar=Path(f"{resolved}{WRITER_LEASE_SUFFIX}")
        )
        if self._declared_file_lease is not None:
            lease = _with_the_file_lease(lease, self._declared_file_lease, resolved)
        try:
            names = os.stat(resolved).st_nlink
        except FileNotFoundError:
            names = 1  # no file at the path (an in-memory database): no other name
        except BaseException:
            lease.release()
            raise
        if names > 1:
            lease.release()
            raise WriterLeaseHeld(
                f"the database file {str(resolved)!r} has {names} names (hard"
                " links); its writer lease is a lock beside one name and cannot"
                " exclude a writer through another, so it is refused (SEC-013)"
            )
        return lease

    @property
    def reader(self) -> SqliteGraphReader:
        """The read-only view of this graph — safe to hand to anyone."""
        return self._reader

    @property
    def connection(self) -> sqlite3.Connection:
        """The raw connection.

        Reachable in principle by any importer, which is why the write
        *statements* — not merely the handle — live behind the CINV-02 lint.
        The honest claim is DESIGN.md §9's: no unforced path exists, and every
        forced path fails CI or fails at boot.
        """
        return self._connection

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SqliteGraphStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


# --- GraphQuery translation (plan 15.2-09) -----------------------------------
#
# The native pushdown path: `_translated_statements` renders one GraphQuery as
# two SQL statements — surviving entity claims and surviving relationship
# claims — that together constitute the whole answer's row set, per the
# all-or-nothing hook contract (`GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583).
# The statements share one WITH chain and one parameter tuple; only the outer
# SELECT differs. Both feed `ccf.graph.reader.materialize_view` exactly as the
# five fixed statements do, so lineage-at-boundary and supersession-as-of stay
# rendered in the one shared place (INV-CH7-14).

#: The charset under which an attribute name maps 1:1 onto a JSON path step.
_ATTRIBUTE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")

#: A constant-false predicate: SQL has no empty IN list, and an empty set
#: admits nothing.
_FALSE = "0 = 1"

#: The six answer columns, aliased from the survivors CTE.
_ENTITY_ANSWER = (
    "SELECT s.entity_uri, s.claim_id, s.claim_json, s.policy_bundle_version,\n"
    "       s.superseded_by, s.superseded_at\n"
    "FROM survivors s\n"
)

#: The six answer columns, aliased from the edges CTE.
_RELATIONSHIP_ANSWER = (
    "SELECT c.relationship_key, c.claim_id, c.claim_json,\n"
    "       c.policy_bundle_version, c.superseded_by, c.superseded_at\n"
    "FROM edges c\n"
)

#: The undirected step: whichever endpoint of the joined crossable edge is
#: not the walk row's own node (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201
#: — an edge is crossable in either direction).
_REACHED = (
    "CASE WHEN c.subject_uri = w.uri THEN c.object_uri ELSE c.subject_uri END"
)

#: The crossable set stated ONCE per direction (`GQ-10` at
#: docs/GRAPH_QUERY_SEMANTICS.md:201, semantics version 1.2.0; ledger row
#: 24.5-L-06). Under ``direction="undirected"`` every edge is rendered in
#: both orientations, so the walk's equality join crosses it either way;
#: under ``direction="forward"`` an edge is rendered as stored, subject to
#: object, and nothing else. ``direction`` chooses between these two
#: code-authored constants in Python — it is never rendered into statement
#: text (threat T-24.5-12), and ``_REACHED`` above is unchanged: under the
#: forward rendering its CASE simply always takes the ``object_uri`` branch.
_HOPS_UNDIRECTED = (
    "    SELECT c.subject_uri, c.object_uri FROM edges c\n"
    "  UNION\n"
    "    SELECT c.object_uri, c.subject_uri FROM edges c\n"
    ")\n"
)
_HOPS_FORWARD = "    SELECT c.subject_uri, c.object_uri FROM edges c\n)\n"


def _json_attribute_path(attribute: str) -> str | None:
    """The ONE site where an artifact-authored attribute name becomes a path.

    Plan 15.2-09 identifier/path safety: classification attribute names are
    ARTIFACT-AUTHORED data, never SQL. The whole path is bound as a ``?``
    parameter to ``json_extract`` — the name never enters statement text —
    but a name outside the ``^[A-Za-z0-9_-]+$`` charset would change the
    *path semantics* (``$.attributes.a.b`` names a nested key, not the
    literal key ``a.b``), silently diverging from the fallback's
    ``attributes.get(name)``. Such a name declines translation: the hook
    returns ``None`` and the fallback answers the whole query instead
    (`GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583) — byte-identical under
    D-04, visible only in telemetry.
    """
    if _ATTRIBUTE_NAME.fullmatch(attribute) is None:
        return None
    return "$.attributes." + attribute


def _placeholders(count: int) -> str:
    """A generated ``?`` list of ``count`` members — structure, never values."""
    return ", ".join(["?"] * count)


def _in_clause(
    expression: str, values: Iterable[str]
) -> tuple[str, tuple[str, ...]]:
    """``expression IN (?, ...)`` with sorted bound values; empty is false.

    Set members are always values, never text (threat T-15.2-01): the
    fragment carries generated placeholders only, and the members return as
    parameters. Sorting makes the rendered statement a deterministic
    function of the query value.
    """
    ordered = tuple(sorted(values))
    if not ordered:
        return _FALSE, ()
    return expression + " IN (" + _placeholders(len(ordered)) + ")", ordered


def _utc_fixed_width(expression: str) -> str:
    """Normalize a claim-JSON timestamp rendering to fixed-width UTC text.

    Claim JSON renders UTC datetimes with a ``Z`` suffix and either no
    fractional part (whole seconds) or exactly six fractional digits — two
    widths that do NOT compare chronologically against the fixed-width
    canonical boundary (``...05Z`` sorts *after* ``...05.000000Z``). This
    expression widens the whole-second form so both compare as canonical
    text (`GQ-24` at docs/GRAPH_QUERY_SEMANTICS.md:482). A rendering that
    is not ``Z``-suffixed (a claim authored with a non-UTC offset — legal
    at the contract tier) yields NULL, and NULL fails every comparison:
    the pushed predicate is fail-closed on state it cannot chronologically
    order as text, never over-disclosing (threats T-15.2-03/T-15.2-26).
    """
    return (
        "CASE WHEN substr(" + expression + ", -1, 1) = 'Z'"
        " THEN CASE WHEN instr(" + expression + ", '.') > 0"
        " THEN " + expression
        + " ELSE replace(" + expression + ", 'Z', '.000000Z') END END"
    )


def _validity_clauses(
    prefix: str, json_column: str, boundary: str
) -> tuple[str, tuple[str, str]]:
    """The validity-window cut over the claim's own JSON fields.

    `GQ-09` at docs/GRAPH_QUERY_SEMANTICS.md:185: when the temporal family
    requires validity at the boundary, a record additionally survives only
    if ``valid_from <= as_of AND (valid_to IS NULL OR valid_to > as_of)``
    — cut 3 of the in-process temporal operator (INV-CH7-25), pushed as
    canonical-text comparison over the width-normalized renderings.
    """
    valid_from = "json_extract(" + json_column + ", '$.valid_from')"
    valid_to = "json_extract(" + json_column + ", '$.valid_to')"
    text = (
        # `GQ-09`'s ABSENCE LIMB (`D-IMPL-332`) — see the postgres twin.
        prefix + "AND (" + valid_from + " IS NULL OR "
        + _utc_fixed_width(valid_from) + " <= ?)\n"
        + prefix + "AND (" + valid_to + " IS NULL OR "
        + _utc_fixed_width(valid_to) + " > ?)\n"
    )
    return text, (boundary, boundary)


def _translated_statements(
    q: GraphQuery,
) -> tuple[str, str, tuple[object, ...]] | None:
    """Render ``q`` as the two whole-answer statements, or decline.

    Returns ``(entity_sql, relationship_sql, params)`` — both statements
    share one WITH chain and one positional parameter tuple — or ``None``
    when a classification attribute name falls outside the safe path
    charset (see :func:`_json_attribute_path`), in which case the fallback
    answers (`GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583; D-04).
    """
    boundary = canonical_timestamp(q.as_of)
    policy_versions = q.permitted_policy_bundle_versions
    attribute_by_class = q.classification_attribute_by_class
    classifications = q.permitted_classifications
    # Constraint presence gates endpoint closure exactly as the fallback's
    # step 4 does: any family present, or `allowed_entities` non-None. The
    # degenerate everything-question is exempt — its answer keeps dangling
    # first-class edges (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122;
    # `GQ-21` at docs/GRAPH_QUERY_SEMANTICS.md:446).
    constrained = (
        q.allowed_entities is not None
        or policy_versions is not None
        or q.require_valid_at_boundary is not None
        or q.traverse is not None
    )
    require_validity = q.require_valid_at_boundary is True

    text: list[str] = []
    params: list[object] = []

    # survivors: the surviving entity claims. The as-of cut is INV-CH7-14
    # rendered at the query tier (`GQ-07` at docs/GRAPH_QUERY_SEMANTICS.md:148)
    # over the canonical-text observed_at / superseded_at columns; the
    # remaining families narrow within it.
    # MATERIALIZED (SQLite 3.35+; well below the Python 3.12 floor's era)
    # removes planner discretion: each CTE computes once per statement, so
    # the walk's recursive term expands over a computed row set rather than
    # re-evaluating a subquery per candidate row — the difference between a
    # bounded walk and a combinatorial re-scan on demo-scale graphs.
    text.append("survivors AS MATERIALIZED (\n")
    text.append(
        "    SELECT ec.entity_uri, ec.claim_id, ec.claim_json,\n"
        "           ec.policy_bundle_version, ec.superseded_by,\n"
        "           ec.superseded_at\n"
        "    FROM entity_claims ec\n"
        "    WHERE ec.tenant_id = ?\n"
        "      AND ec.observed_at <= ?\n"
        "      AND (ec.superseded_at IS NULL OR ec.superseded_at > ?)\n"
    )
    params += [q.tenant_id, boundary, boundary]
    if require_validity:
        clause, bound = _validity_clauses("      ", "ec.claim_json", boundary)
        text.append(clause)
        params += list(bound)
    if policy_versions is not None:
        # Policy admissibility, all three cuts of `GQ-08` at
        # docs/GRAPH_QUERY_SEMANTICS.md:163 (INV-CH7-26): a permitted bundle
        # version; a class with a declared classification attribute — a
        # class with none is inadmissible, so admissibility is an OR over
        # the declared classes; and a permitted value of that attribute —
        # json_extract answers NULL for an absent attribute, and NULL is
        # never IN a permitted set, so "carries no value" is inadmissible.
        assert attribute_by_class is not None  # noqa: S101 - GQ-02 whole family
        assert classifications is not None  # noqa: S101 - GQ-02 whole family
        clause, values = _in_clause("ec.policy_bundle_version", policy_versions)
        text.append("      AND " + clause + "\n")
        params += list(values)
        alternatives: list[str] = []
        if classifications:
            for entity_class in sorted(attribute_by_class):
                path = _json_attribute_path(attribute_by_class[entity_class])
                if path is None:
                    return None
                alternatives.append(
                    "(json_extract(ec.claim_json, '$.entity_class') = ?"
                    " AND json_extract(ec.claim_json, ?) IN ("
                    + _placeholders(len(classifications))
                    + "))"
                )
                params += [entity_class, path, *sorted(classifications)]
        if alternatives:
            text.append(
                "      AND ("
                + "\n           OR ".join(alternatives)
                + ")\n"
            )
        else:
            text.append("      AND " + _FALSE + "\n")
    if q.allowed_entities is not None:
        # The uniform rule's set membership on entity selection (`GQ-15` at
        # docs/GRAPH_QUERY_SEMANTICS.md:300): every family computes within
        # the survivor set, restricted before anything else evaluates. The
        # set travels natively as generated placeholders (`GQ-30` at
        # docs/GRAPH_QUERY_SEMANTICS.md:563); a temp-table strategy is a
        # documented adapter-internal alternative for very large sets, not
        # required for conformance — the Control Plane cap (`GQ-18`)
        # governs set size upstream of this statement.
        clause, values = _in_clause("ec.entity_uri", q.allowed_entities)
        text.append("      AND " + clause + "\n")
        params += list(values)
    text.append(")")

    # edges: the surviving relationship claims that may appear in the answer
    # — and, on a traverse query, the walk's whole expansion surface: the
    # relationship_claims join carries the as-of predicate (INV-CH7-14;
    # `GQ-07` at docs/GRAPH_QUERY_SEMANTICS.md:148) plus the segment's
    # validity and policy predicates when present, and endpoint closure
    # below restricts crossability to edges between surviving entities.
    text.append(",\nedges AS MATERIALIZED (\n")
    text.append(
        "    SELECT rc.relationship_key, rc.claim_id, rc.claim_json,\n"
        "           rc.policy_bundle_version, rc.superseded_by,\n"
        "           rc.superseded_at, r.subject_uri, r.object_uri\n"
        "    FROM relationship_claims rc\n"
        "    JOIN relationships r\n"
        "      ON r.tenant_id = ?\n"
        "     AND r.relationship_key = rc.relationship_key\n"
        "    WHERE rc.tenant_id = ?\n"
        "      AND rc.observed_at <= ?\n"
        "      AND (rc.superseded_at IS NULL OR rc.superseded_at > ?)\n"
    )
    params += [q.tenant_id, q.tenant_id, boundary, boundary]
    if require_validity:
        clause, bound = _validity_clauses("      ", "rc.claim_json", boundary)
        text.append(clause)
        params += list(bound)
    if policy_versions is not None:
        # A relationship is admissible under the policy family iff its
        # bundle version is permitted (`GQ-08` at
        # docs/GRAPH_QUERY_SEMANTICS.md:163) — no classification cut of its
        # own; endpoint survival governs its exposure below.
        clause, values = _in_clause("rc.policy_bundle_version", policy_versions)
        text.append("      AND " + clause + "\n")
        params += list(values)
    if q.allowed_entities is not None:
        # The induced-subgraph rule (`GQ-16` at
        # docs/GRAPH_QUERY_SEMANTICS.md:316): both endpoints members of the
        # set, stated natively on the edge's own columns.
        clause, values = _in_clause("r.subject_uri", q.allowed_entities)
        text.append("      AND " + clause + "\n")
        params += list(values)
        clause, values = _in_clause("r.object_uri", q.allowed_entities)
        text.append("      AND " + clause + "\n")
        params += list(values)
    if q.traverse is not None:
        # Typed crossability doubles as answer membership: edges of other
        # types are absent even between reached endpoints (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201).
        clause, values = _in_clause(
            "r.relationship_type", q.traverse.relationship_types
        )
        text.append("      AND " + clause + "\n")
        params += list(values)
    if constrained:
        # Endpoint closure against the surviving universe (`GQ-16` at
        # docs/GRAPH_QUERY_SEMANTICS.md:316, INV-CH7-40): an answer view
        # never retains an edge to a node its principal may not see. The
        # degenerate everything-question skips this — a dangling
        # first-class edge is state, not a leak, in the unconstrained
        # answer (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122).
        text.append(
            "      AND EXISTS (SELECT 1 FROM survivors s\n"
            "                  WHERE s.entity_uri = r.subject_uri)\n"
            "      AND EXISTS (SELECT 1 FROM survivors s\n"
            "                  WHERE s.entity_uri = r.object_uri)\n"
        )
    text.append(")\n")

    if q.traverse is not None:
        # hops: the crossable set stated ONCE per direction, so the walk's
        # recursive term can find its next hops by EQUALITY on the walk row's
        # own node. `GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201 makes an edge
        # crossable in either direction, and the natural rendering of that —
        # `JOIN edges c ON (c.subject_uri = w.uri OR c.object_uri = w.uri)` —
        # is a disjunction SQLite cannot serve from an index, so every step of
        # the walk re-scanned the whole crossable set: |walk| x |edges| row
        # comparisons, quadratic in the segment's own answer. Pre-symmetrizing
        # is the same relation written so an equality join can index it; the
        # UNION (never UNION ALL) makes a self-loop's two renderings one row,
        # exactly as the disjunction's single match did. The reached-node
        # expression below is unchanged and still reads as the general
        # undirected step: under this join its CASE simply always takes the
        # `object_uri` branch. Under `direction="forward"` (1.2.0; ledger
        # row 24.5-L-06) the crossable set is the edges AS STORED — the
        # reverse rendering is simply never written — and the walk below
        # is otherwise the same statement: the direction is a Python
        # branch between two constants, never text (threat T-24.5-12).
        text.append(",\nhops(subject_uri, object_uri) AS MATERIALIZED (\n")
        text.append(
            _HOPS_FORWARD
            if q.traverse.direction == "forward"
            else _HOPS_UNDIRECTED
        )
        # The bounded typed undirected walk (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201, INV-CH7-24). Walk starting
        # points are the union of seed-class selection and explicit seeds,
        # computed over survivors only (`GQ-11` at
        # docs/GRAPH_QUERY_SEMANTICS.md:221) — so starts satisfy every
        # segment predicate and, when `allowed_entities` is present, sit
        # inside the set (seed classes select within it; explicit seeds
        # intersect with it, and a URI naming nothing in scope contributes
        # no start). depth_limit=0 is the base case alone: the walk
        # starting points only, a legal bound and not an error.
        text.append(",\nwalk(uri, depth) AS (\n")
        text.append(
            "    SELECT s.entity_uri, 0\n"
            "    FROM survivors s\n"
            "    WHERE "
        )
        starts: list[str] = []
        clause, values = _in_clause(
            "json_extract(s.claim_json, '$.entity_class')",
            q.traverse.seed_entity_classes,
        )
        starts.append(clause)
        params += list(values)
        if q.seeds:
            clause, values = _in_clause("s.entity_uri", q.seeds)
            starts.append(clause)
            params += list(values)
        text.append("(" + " OR ".join(starts) + ")\n")
        # The recursive term: hop admissibility enforced on every hop, not
        # on the result set (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261,
        # INV-CH7-40). The expansion surface is the materialized crossable
        # set above — relationship_claims joined with the as-of predicate,
        # the segment's validity and policy predicates, the permitted
        # types, and BOTH endpoints surviving — so an edge to an excluded
        # node is not a hop the walk can take, and a path through an
        # excluded node does not exist. Prune before walking, exactly the
        # fallback's shape. The expansion surface is reached through `hops`,
        # which is that same set with each edge stated in both directions —
        # every predicate above still governs it, because `hops` is derived
        # from `edges` and adds no row of its own.
        text.append(
            "  UNION\n"
            "    SELECT " + _REACHED + ",\n"
            "           w.depth + 1\n"
            "    FROM walk w\n"
            "    JOIN hops c\n"
            "      ON c.subject_uri = w.uri\n"
            "    WHERE w.depth < ?\n"
        )
        # Depth is a bound parameter in SQL — the literal-inlining
        # exception is Cypher-only (plan 15.2-09).
        params.append(q.traverse.depth_limit)
        if q.allowed_entities is not None:
            # The uniform rule inside the recursive term (`GQ-15` at
            # docs/GRAPH_QUERY_SEMANTICS.md:300): a hop to an out-of-set
            # node must not extend the walk — the D-IMPL-87 resurrection
            # defect closed in SQL. The crossable set's endpoint predicates
            # already imply membership (survivors are restricted to the
            # set); this predicate states it on the reached node itself, so
            # the closure is explicit in the term that expands the walk.
            clause, values = _in_clause(_REACHED, q.allowed_entities)
            text.append("      AND " + clause + "\n")
            params += list(values)
        if q.traverse.admitted_entity_classes is not None:
            # Node-class admission on the REACHED node, honored natively
            # (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201, semantics
            # version 1.1.0; ledger row 24.5-L-05): a hop lands only on a
            # survivor whose class is admitted. Stated inside the recursive
            # term so a path through an unadmitted node does not exist, and
            # never on the base case — starts are selected by `GQ-11` and
            # are not filtered by admission. The class list binds as
            # parameters, appended in the same order the seed-class binder
            # appends (threat T-24.5-10); an empty set renders the always-
            # false clause, so no hop is admitted and the starts answer.
            clause, values = _in_clause(
                "json_extract(a.claim_json, '$.entity_class')",
                q.traverse.admitted_entity_classes,
            )
            text.append(
                "      AND " + _REACHED + " IN (\n"
                "        SELECT a.entity_uri FROM survivors a\n"
                "        WHERE " + clause + ")\n"
            )
            params += list(values)
        text.append(")\n")

    prologue = "WITH RECURSIVE " if q.traverse is not None else "WITH "
    with_chain = prologue + "".join(text)

    entity_answer = _ENTITY_ANSWER
    relationship_answer = _RELATIONSHIP_ANSWER
    if q.traverse is not None:
        # The traverse answer: reached entities, and the permitted-type
        # surviving edges among them (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201).
        entity_answer += "WHERE s.entity_uri IN (SELECT uri FROM walk)\n"
        relationship_answer += (
            "WHERE c.subject_uri IN (SELECT uri FROM walk)\n"
            "  AND c.object_uri IN (SELECT uri FROM walk)\n"
        )
    entity_answer += "ORDER BY s.entity_uri"
    relationship_answer += "ORDER BY c.relationship_key"
    return (
        with_chain + entity_answer,
        with_chain + relationship_answer,
        tuple(params),
    )


class SqliteGraphReader(BaseGraphReader):
    """``GraphReader`` over a SQLite connection — dialect and rows only.

    The bitemporal rendering rules live in
    :class:`ccf.graph.reader.BaseGraphReader`; what is here is the SQLite
    dialect of the five reads and the connection they run on. ``rowid`` is the
    insertion-order tiebreak within one observed-time instant, which is what
    keeps history ordering total rather than merely chronological.

    Since plan 15.2-09 the reader also holds a native ``GraphQuery``
    translation: :meth:`_translate_query` answers whole queries by generated
    SQL — as-of + policy + validity predicates, ``allowed_entities``
    membership, and bounded undirected traversal via recursive CTE — and the
    differential suite holds the translated answers byte-identical to the
    fallback (`GQ-31` at docs/GRAPH_QUERY_SEMANTICS.md:573).
    """

    # The bitemporal read. `observed_at <= ?` excludes what the fabric had not
    # yet learned at the read boundary; the supersession clause keeps a claim
    # current until the instant it was superseded. Together: no future
    # information leaks into a historical view (INV-CH7-14).
    SELECT_LINEAGE: ClassVar[str] = """
        SELECT entry_json FROM lineage
        WHERE tenant_id = ? AND claim_kind = ? AND node_key = ? AND claim_id = ?
    """
    SELECT_ENTITY_HISTORY: ClassVar[str] = """
        SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM entity_claims
        WHERE tenant_id = ? AND entity_uri = ?
        ORDER BY observed_at, rowid
    """
    SELECT_RELATIONSHIP_HISTORY: ClassVar[str] = """
        SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM relationship_claims
        WHERE tenant_id = ? AND relationship_key = ?
        ORDER BY observed_at, rowid
    """
    SELECT_ENTITIES_AS_OF: ClassVar[str] = """
        SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM entity_claims
        WHERE tenant_id = ?
          AND observed_at <= ?
          AND (superseded_at IS NULL OR superseded_at > ?)
        ORDER BY entity_uri
    """
    SELECT_RELATIONSHIPS_AS_OF: ClassVar[str] = """
        SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM relationship_claims
        WHERE tenant_id = ?
          AND observed_at <= ?
          AND (superseded_at IS NULL OR superseded_at > ?)
        ORDER BY relationship_key
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def _query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        return self._connection.execute(sql, params).fetchall()

    def _translate_query(
        self, q: GraphQuery
    ) -> tuple[Sequence[Row], Sequence[Row]] | None:
        """Answer the whole query natively, or decline (plan 15.2-09).

        The hook contract is all-or-nothing (`GQ-32` at
        docs/GRAPH_QUERY_SEMANTICS.md:583): a non-``None`` return is the
        complete answer's row pair — every predicate family applied, hop
        admissibility applied, ``allowed_entities`` membership applied —
        and ``None`` hands the whole query to the fallback, which D-04
        makes byte-identical and invisible outside telemetry. This
        translation covers every well-formed query shape; the one decline
        is a classification attribute name outside the safe JSON-path
        charset (:func:`_json_attribute_path`). ``admitted_entity_classes``
        (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0) is HONORED
        natively — a class predicate on the reached survivor inside the
        recursive walk term, the classes bound as parameters. ``direction``
        (`GQ-10`, 1.2.0; ledger row ``24.5-L-06``) is HONORED natively: the
        walk's crossable set is rendered from the edges as stored under
        ``"forward"`` and from both orientations under ``"undirected"`` —
        a Python choice between :data:`_HOPS_FORWARD` and
        :data:`_HOPS_UNDIRECTED`, never a value in statement text — and
        the differential suite holds the answer to the fallback over
        ``tests/conformance/query_corpus.py::direction_cases``.
        """
        if q.allowed_entities is not None and not q.allowed_entities:
            # The empty survivor set IS the answer (`GQ-04` at
            # docs/GRAPH_QUERY_SEMANTICS.md:98): the empty view, answered
            # here without a substrate round trip. An empty answer is an
            # answer, never an error (`GQ-23` at
            # docs/GRAPH_QUERY_SEMANTICS.md:474).
            return (), ()
        statements = _translated_statements(q)
        if statements is None:
            return None
        entity_sql, relationship_sql, params = statements
        return (
            self._query(entity_sql, params),
            self._query(relationship_sql, params),
        )
