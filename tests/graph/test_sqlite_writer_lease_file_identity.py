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

**Since P2 (b)** (``D-IMPL-378``, lane ``378i-p2b``) a hard link never reaches the file lease: the second process's
store refuses a file with more than one name when it opens, before its setup and its mint
(``tests/graph/test_sqlite_open_refuses_a_file_with_more_than_one_name.py``). The file lease's refusal is measured
through the renamed file's new name, and the hard-link test here asserts the earlier refusal by name.

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

from ccf.graph.backends.sqlite import SqliteGraphStore, _database_file_identity
from ccf.graph.leases import lock_directory_writer_lease, lock_file_name
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


def test_a_second_process_through_a_hard_link_is_refused_when_its_store_opens_before_the_file_lease(
    tmp_path: Path,
) -> None:
    """P2 (b): with the holder's file lease in force, a writer through a hard link is refused earlier, when its store
    opens, by the store's own count of the file's names, before its setup and before its mint reaches the lease."""
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

    assert outcome[:2] == ("REFUSED", "WriterLeaseHeld"), outcome
    assert f"{str(linked)!r} has 2 names (hard links)" in outcome[2], outcome
    assert "the store refuses to open it, readers included, before any connection or setup" in outcome[2], outcome
    assert len(held_locks) == 1, f"the holder holds no lock in the declared directory: {held_locks!r}; {outcome!r}"


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


def test_a_lock_file_an_earlier_holder_of_the_same_file_identity_left_does_not_block_the_boot(tmp_path: Path) -> None:
    """A new file given a deleted file's inode number finds that file's old lock file, unheld, and boots.

    The lock file's name is derived from the device and inode, so a new database file that the filesystem gives a
    deleted file's inode number finds the lock file the deleted file's last writer left behind. The kernel dropped
    that writer's ``flock`` when it closed or died, so nobody holds the file and the new file's boot takes it.
    Exercised deterministically, by putting the lock file for the new file's identity there first, exactly as an
    earlier holder of that identity leaves it: whether and when a filesystem recycles an inode number depends on the
    filesystem and on every other process creating files on it.
    """
    locks = _locks(tmp_path)
    database = tmp_path / "given-a-recycled-inode.sqlite3"
    database.touch()
    identity = _database_file_identity(str(database))
    assert identity is not None
    left_behind = locks / lock_file_name(identity)
    os.close(os.open(left_behind, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))

    holder = _boot("sqlite", _declared(database, locks))
    try:
        assert _lock_files(locks) == [left_behind]
        assert f"flock on {str(left_behind)!r}" in (holder.lease_mechanism or ""), holder.lease_mechanism
    finally:
        holder.close()


def test_a_live_writers_file_identity_is_not_given_to_another_file_while_it_holds_the_lease(tmp_path: Path) -> None:
    """While the writer's connection holds its database file open, no other file is given that file's inode number.

    So a lease keyed on the identity is never held over an identity another file has been given, and cannot wedge
    that file's boot: the store opens the file before the lease is taken, and the boot's shutdown gives the lease
    back before it closes the store. Measured with the held file's only name deleted, which frees nothing while the
    connection holds the file.
    """
    locks = _locks(tmp_path)
    files = tmp_path / "files"
    files.mkdir()
    held = files / "held.sqlite3"
    holder = _boot("sqlite", _declared(held, locks))
    try:
        held_inode = os.stat(held).st_ino
        held.unlink()
        created = []
        for attempt in range(64):
            path = files / f"new-{attempt}.sqlite3"
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
            created.append(os.stat(path).st_ino)
        outcome = _run_child("sqlite", _declared(files / "new-0.sqlite3", locks))
    finally:
        holder.close()

    assert held_inode not in created
    assert outcome == ("BOOTED", "", ""), outcome


# --- The setting is validated as the network stores' is -------------------------------------------------------------


@pytest.mark.parametrize("case", ["relative", "through-a-symbolic-link", "missing", "group-writable"])
def test_a_writer_boot_refuses_a_lock_directory_the_precedent_refuses_naming_the_setting(
    case: str, tmp_path: Path
) -> None:
    real = _locks(tmp_path)
    if case == "relative":
        declared = "relative-locks"
    elif case == "through-a-symbolic-link":
        link = tmp_path / "current"
        link.symlink_to(real)
        declared = str(link)
    elif case == "missing":
        declared = str(tmp_path / "no-such-directory")
    else:
        real.chmod(0o770)
        declared = str(real)

    from ccf.graph.registry import InvalidBackendConfig

    with pytest.raises(InvalidBackendConfig) as refused:
        _boot("sqlite", {"database_path": tmp_path / "graph.sqlite3", LEASE_FIELD: declared})
    assert LEASE_FIELD in str(refused.value), str(refused.value)


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


def test_the_file_lease_is_keyed_on_the_file_the_store_opened_not_on_what_its_path_names_at_the_mint(
    tmp_path: Path,
) -> None:
    """A path re-pointed at another file between the store's open and the mint does not move the lease.

    The store reads the file's device and inode right after SQLite opens it. If the lease were keyed on whatever the
    path names when the mint takes it, a file swapped in under the path would be leased while the connection still
    writes the file it opened, which another writer holds.
    """
    locks = _locks(tmp_path)
    database = tmp_path / "opened.sqlite3"
    swapped_in = tmp_path / "swapped-in.sqlite3"
    swapped_in.touch()
    with SqliteGraphStore(database_path=database, writer_lease=lock_directory_writer_lease(str(locks))) as store:
        store.writer_lease().release()  # control: leased; the opened file's lock file now exists
        [opened_files_lock] = _lock_files(locks)
        other_holder = os.open(opened_files_lock, os.O_RDWR)
        try:
            fcntl.flock(other_holder, fcntl.LOCK_EX | fcntl.LOCK_NB)  # another writer holds the OPENED file
            os.replace(swapped_in, database)  # the path now names another file; the connection does not
            with pytest.raises(WriterLeaseHeld, match=r"is held by another writer"):
                store.writer_lease()
        finally:
            os.close(other_holder)


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
