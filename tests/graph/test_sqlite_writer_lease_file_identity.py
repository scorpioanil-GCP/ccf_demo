"""SEC-013, option (C) (Dave, 2026-10-08 21:24 MST): the SQLite writer lease follows the database FILE, not its name.

The hole, measured by lane ``378f-small2``: ``src/ccf/graph/backends/sqlite.py::SqliteWriterLease`` is a ``flock``
on a sidecar beside the resolved database path, so while one process held the writer, a second process booted a
writer through a hard link to the same file and through the new name of the renamed live file. Option (B),
``src/ccf/graph/backends/sqlite.py::SqliteGraphStore.writer_lease`` refusing a file with more than one name, closed
the hard link and not the rename.

Option (C), on the network stores' precedent (``src/ccf/graph/leases.py::lock_directory_writer_lease``): a deployment
declares ``writer_lease_lock_dir`` on the SQLite connection settings, and the writer then also holds an exclusive
``flock`` on a lock file in that directory whose name is derived from the database file's device and inode. Every
writer of one file that declares the same directory contends for that one lock, whatever name it reached the file
by.

Each refusal is asserted by its mechanism, never by a missing word: the second process is refused with
``SingleWriterViolation`` and its message names the lock file the holder holds in the declared directory. Before the
lease is enforced, the rename boots and the hard link is refused only by option (B)'s name count, whose message
names no lock file in the directory.

The second process is ``tests/graph/test_single_writer_across_processes.py::_run_child`` (spawn; outcome reported by
exception class NAME and message), the holder boots with
``tests/graph/test_single_writer_across_processes.py::_boot``, and every file lives in ``tmp_path``.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.leases import lock_directory_writer_lease
from ccf.graph.protocols import ProcessScopedWriterLease, WriterLeaseHeld, WriterLeaseRequired
from tests.graph.test_single_writer_across_processes import _boot, _run_child
from tests.graph.test_sqlite_writer_lease_hard_link import _two_names

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

#: The connection setting a deployment declares the file-identity lease by (the network stores' name).
LEASE_FIELD = "writer_lease_lock_dir"


def _locks(tmp_path: Path) -> Path:
    """A lock directory the precedent's validation admits: real, existing, this user's, mode 0700."""
    locks = tmp_path / "locks"
    locks.mkdir(mode=0o700)
    locks.chmod(0o700)
    return locks


def _declared(database_path: Path | str, locks: Path) -> dict[str, Any]:
    return {"database_path": database_path, LEASE_FIELD: str(locks)}


def _lock_files(locks: Path) -> list[Path]:
    return sorted(locks.iterdir())


def _boot_read_only(connection: dict[str, Any]) -> FabricHandle:
    """``_boot``'s recipe with ``read_only=True`` (FW-2): no token, no writer, no lease."""
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    from tests.composition import register_at_composition
    from tests.conftest import (
        FIXTURE_TENANTS,
        POLICY_BUNDLE_KEY,
        RESOLUTION_SPEC_KEY,
        _policy_bundle,
        _resolution_spec,
    )

    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, RESOLUTION_SPEC_KEY, _resolution_spec())
    policy_version = register_at_composition(registry, POLICY_BUNDLE_KEY, _policy_bundle())
    return boot(
        backend="sqlite",
        connection=connection,
        registry=registry,
        resolution_spec_key=RESOLUTION_SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        policy_bundle_version=policy_version,
        tenant_ids=FIXTURE_TENANTS,
        read_only=True,
    )


# --- The hole, as worded: a second process through another name of the held file -----------------------------------


def test_a_second_process_is_refused_through_the_new_name_of_the_renamed_live_file(tmp_path: Path) -> None:
    locks = _locks(tmp_path)
    held, moved = _two_names(tmp_path)
    holder = _boot("sqlite", _declared(held, locks))
    try:
        os.rename(held, moved)
        outcome = _run_child("sqlite", _declared(moved, locks))
        held_locks = _lock_files(locks)
    finally:
        holder.close()

    assert outcome[:2] == ("REFUSED", "SingleWriterViolation"), (
        f"a second process booted a writer through the new name of a renamed live file: {outcome!r}"
    )
    assert len(held_locks) == 1, f"the holder holds no lock in the declared directory: {held_locks!r}; {outcome!r}"
    assert f"flock on {str(held_locks[0])!r} is held" in outcome[2], outcome


def test_a_second_process_is_refused_through_a_hard_link_by_the_file_lease_before_the_name_count(
    tmp_path: Path,
) -> None:
    locks = _locks(tmp_path)
    held, linked = _two_names(tmp_path)
    holder = _boot("sqlite", _declared(held, locks))
    try:
        os.link(held, linked)
        assert os.path.samefile(held, linked)
        outcome = _run_child("sqlite", _declared(linked, locks))
        held_locks = _lock_files(locks)
    finally:
        holder.close()

    assert outcome[:2] == ("REFUSED", "SingleWriterViolation"), outcome
    assert len(held_locks) == 1, f"the holder holds no lock in the declared directory: {held_locks!r}; {outcome!r}"
    assert f"flock on {str(held_locks[0])!r} is held" in outcome[2], outcome


# --- Controls: what the file lease must NOT refuse ------------------------------------------------------------------


def test_control_another_database_file_boots_under_the_same_lock_directory_while_the_holder_is_live(
    tmp_path: Path,
) -> None:
    locks = _locks(tmp_path)
    held, _ = _two_names(tmp_path)
    holder = _boot("sqlite", _declared(held, locks))
    try:
        outcome = _run_child("sqlite", _declared(tmp_path / "another.sqlite3", locks))
    finally:
        holder.close()

    assert outcome == ("BOOTED", "", ""), outcome


def test_control_a_read_only_boot_of_the_held_file_is_not_refused(tmp_path: Path) -> None:
    locks = _locks(tmp_path)
    held, _ = _two_names(tmp_path)
    holder = _boot("sqlite", _declared(held, locks))
    try:
        reader = _boot_read_only(_declared(held, locks))
        try:
            assert reader.lease_scope == "read-only"
        finally:
            reader.close()
        # N-2: a read-only boot sets the lock directory aside unvalidated, so a missing one does not refuse it.
        elsewhere = _boot_read_only(_declared(held, tmp_path / "no-such-directory"))
        elsewhere.close()
    finally:
        holder.close()


def test_after_the_holder_closes_the_file_boots_through_its_new_name(tmp_path: Path) -> None:
    locks = _locks(tmp_path)
    held, moved = _two_names(tmp_path)
    _boot("sqlite", _declared(held, locks)).close()
    os.rename(held, moved)

    assert _run_child("sqlite", _declared(moved, locks)) == ("BOOTED", "", "")


# --- What the lease reports, and what it leaves behind --------------------------------------------------------------


def test_the_holder_reports_both_locks_and_an_undeclared_boot_reports_the_sidecar_alone(tmp_path: Path) -> None:
    locks = _locks(tmp_path)
    declared = tmp_path / "declared.sqlite3"
    undeclared = tmp_path / "undeclared.sqlite3"
    sidecar = f"{declared.resolve()}.ccf-writer.lock"

    holder = _boot("sqlite", _declared(declared, locks))
    try:
        mechanism = holder.lease_mechanism or ""
        held_locks = _lock_files(locks)
    finally:
        holder.close()
    plain = _boot("sqlite", {"database_path": undeclared})
    try:
        plain_mechanism = plain.lease_mechanism
    finally:
        plain.close()

    assert len(held_locks) == 1, held_locks
    assert f"flock on {sidecar!r}" in mechanism, mechanism
    assert f"flock on {str(held_locks[0])!r}" in mechanism, mechanism
    assert plain_mechanism == f"flock on {str(undeclared.resolve()) + '.ccf-writer.lock'!r}"


def test_a_holder_that_dies_without_closing_does_not_block_the_next_boot_through_its_lock_file(
    tmp_path: Path,
) -> None:
    locks = _locks(tmp_path)
    database = tmp_path / "crashed.sqlite3"

    assert _run_child("sqlite", _declared(database, locks), close_before_exit=False) == ("BOOTED", "", "")
    stale = _lock_files(locks)
    assert len(stale) == 1, f"the dead holder left no lock file in the declared directory: {stale!r}"

    survivor = _boot("sqlite", _declared(database, locks))
    try:
        assert f"flock on {str(stale[0])!r}" in (survivor.lease_mechanism or ""), survivor.lease_mechanism
    finally:
        survivor.close()


def test_a_recycled_inode_number_does_not_wedge_a_new_database_file(tmp_path: Path) -> None:
    """A deleted database file's inode number, given to a new file, finds an unheld lock file and boots.

    Requires a filesystem that recycles inode numbers (ext4 and tmpfs do: measured 20 of 20 immediate reuses on this
    host); on one that never does, the test fails by name rather than passing without exercising reuse.
    """
    locks = _locks(tmp_path)
    files = tmp_path / "files"
    files.mkdir()
    first = files / "first.sqlite3"
    _boot("sqlite", _declared(first, locks)).close()
    recycled = os.stat(first).st_ino
    stale = _lock_files(locks)
    assert len(stale) == 1, f"the first writer left no lock file in the declared directory: {stale!r}"
    for leftover in files.iterdir():
        leftover.unlink()

    candidate = None
    for attempt in range(64):
        path = files / f"new-{attempt}.sqlite3"
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        if os.stat(path).st_ino == recycled:
            candidate = path
            break
    assert candidate is not None, "this filesystem did not recycle the inode number, so reuse is not exercised here"

    second = _boot("sqlite", _declared(candidate, locks))
    try:
        assert f"flock on {str(stale[0])!r}" in (second.lease_mechanism or ""), second.lease_mechanism
    finally:
        second.close()


# --- The lease's own refusals, in one process -----------------------------------------------------------------------


def test_a_refused_file_lease_gives_back_the_sidecar_so_a_corrected_retry_is_leased(tmp_path: Path) -> None:
    locks = _locks(tmp_path)
    database = tmp_path / "retry.sqlite3"
    with SqliteGraphStore(database_path=database, writer_lease=lock_directory_writer_lease(str(locks))) as store:
        store.writer_lease().release()  # control: leased, and the file's lock file now exists
        held_locks = _lock_files(locks)
        assert len(held_locks) == 1, held_locks
        other_holder = os.open(held_locks[0], os.O_RDWR)
        try:
            fcntl.flock(other_holder, fcntl.LOCK_EX | fcntl.LOCK_NB)  # another holder of this FILE's lock
            with pytest.raises(WriterLeaseHeld, match=r"is held"):
                store.writer_lease()
        finally:
            os.close(other_holder)
        store.writer_lease().release()  # the refused attempt gave its sidecar back


def test_a_declared_lease_with_no_database_file_is_refused_when_the_store_is_built(tmp_path: Path) -> None:
    locks = _locks(tmp_path)
    with pytest.raises(ValueError, match=r"has no database file"):
        SqliteGraphStore(database_path=":memory:", writer_lease=lock_directory_writer_lease(str(locks)))
    with pytest.raises(ValueError, match=r"has no database file"):
        _boot("sqlite", _declared(":memory:", locks))


def test_a_declared_lease_that_does_not_exclude_other_processes_is_refused(tmp_path: Path) -> None:
    database = tmp_path / "process-scope.sqlite3"

    def a_process_scoped_lease(_identity: str) -> ProcessScopedWriterLease:
        return ProcessScopedWriterLease(substrate="a deployment's own")

    with SqliteGraphStore(database_path=database, writer_lease=a_process_scoped_lease) as store:
        with pytest.raises(WriterLeaseRequired, match=r"has scope 'process'"):
            store.writer_lease()
    with SqliteGraphStore(database_path=database) as store:
        store.writer_lease().release()  # the refused attempt gave its sidecar back
