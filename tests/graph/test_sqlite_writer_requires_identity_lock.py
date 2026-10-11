"""A SQLite file writer mints only under the identity lock; the standard product boot supplies it (P1 (a), Tuesday GO item 4).

Dave, 2026-10-11 14:51: *"SQLite: require the existing identity lock AND wire
the standard product boot to supply the agreed lock directory. Do not ship a
refusal that breaks the ordinary product path. Reuse the existing design and
prototype."* The design and prototype are
``records/2026-10-09-d-impl-378-designs/designs/gamma/DESIGN-P1a-sqlite-identity-lock.md``
on ``dl-378-record``; these are its three red tests (§7), plus the refusal
cases of the SDK-managed directory. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import multiprocessing as mp
import os
import traceback
from pathlib import Path
from typing import Any

import pytest

from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.leases import SDK_MANAGED_LOCK_DIRECTORY, lock_directory_writer_lease, sdk_managed_lock_directory
from ccf.graph.protocols import WriterLeaseHeld, WriterLeaseRequired
from tests.products.test_paved_road import _open, _write_tree


def test_an_undeclared_sqlite_writer_lease_is_refused_by_the_declared_lease_rule(tmp_path: Path) -> None:
    """No silent fallback to the path-only sidecar: the refusal is the declared-lease rule's, by its frame."""
    store = SqliteGraphStore(database_path=tmp_path / "graph.sqlite3")
    try:
        with pytest.raises(WriterLeaseRequired) as refused:
            store.writer_lease()
        assert traceback.extract_tb(refused.tb)[-1].name == "acquire_declared_writer_lease"
    finally:
        store.close()


def test_an_in_memory_sqlite_writer_is_process_scoped(tmp_path: Path) -> None:
    """No file, no file to rename: the in-memory database keeps its process-scoped declaration."""
    store = SqliteGraphStore(database_path=":memory:")
    try:
        lease = store.writer_lease()
        assert lease.scope == "process"
        lease.release()
    finally:
        store.close()


def test_the_paved_road_boots_under_the_sdk_managed_identity_lock(tmp_path: Path) -> None:
    """The ordinary product path still boots, and its writer holds the identity lock under scratch."""
    root, scratch = _write_tree(tmp_path), tmp_path / "scratch"
    opened = _open(root, scratch)
    fabric = opened._boot()
    try:
        mechanism = fabric.handle.lease_mechanism or ""
        lock_dir = scratch.resolve() / SDK_MANAGED_LOCK_DIRECTORY
        assert f"flock on '{lock_dir}{os.sep}" in mechanism, mechanism
        assert "keyed on the database file (sqlite-database-file:" in mechanism, mechanism
        assert opened.writer_lock_directory == str(lock_dir)
        assert (lock_dir.stat().st_mode & 0o777) == 0o700
    finally:
        fabric.handle.close()


def _hold(path: str, lock_dir: str, ready: Any, done: Any) -> None:
    store = SqliteGraphStore(database_path=path, writer_lease=lock_directory_writer_lease(lock_dir))
    lease = store.writer_lease()
    ready.set()
    done.wait(30)
    lease.release()
    store.close()


def test_a_renamed_live_paved_file_is_refused_by_the_sdk_managed_identity_lock(tmp_path: Path) -> None:
    """Dave, 2026-10-09: "Verify the identity lock still blocks the renamed-file second writer.\""""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    lock_dir = sdk_managed_lock_directory(os.path.realpath(scratch))
    first = scratch / "q_first.db"
    ctx = mp.get_context("spawn")
    ready, done = ctx.Event(), ctx.Event()
    holder = ctx.Process(target=_hold, args=(str(first), lock_dir, ready, done))
    holder.start()
    try:
        assert ready.wait(30)
        renamed = scratch / "q_renamed.db"
        os.rename(first, renamed)
        second = SqliteGraphStore(database_path=renamed, writer_lease=lock_directory_writer_lease(lock_dir))
        try:
            with pytest.raises(WriterLeaseHeld) as refused:
                second.writer_lease()
            assert lock_dir in str(refused.value)
        finally:
            second.close()
    finally:
        done.set()
        holder.join(30)


def test_the_managed_directory_refuses_a_relative_scratch_root() -> None:
    with pytest.raises(WriterLeaseRequired, match="not an absolute real path"):
        sdk_managed_lock_directory("relative/scratch")


def test_the_managed_directory_refuses_an_insecure_existing_directory(tmp_path: Path) -> None:
    """An existing directory is judged, never re-moded."""
    base = Path(os.path.realpath(tmp_path))
    (base / SDK_MANAGED_LOCK_DIRECTORY).mkdir(mode=0o700)
    os.chmod(base / SDK_MANAGED_LOCK_DIRECTORY, 0o777)
    with pytest.raises(WriterLeaseRequired, match="group- or world-writable"):
        sdk_managed_lock_directory(base)
    assert (base / SDK_MANAGED_LOCK_DIRECTORY).stat().st_mode & 0o777 == 0o777


def test_the_managed_directory_refuses_a_filesystem_it_does_not_trust(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ccf.graph.leases as leases

    monkeypatch.setattr(leases, "_filesystem_type", lambda _path: "nfs4")
    with pytest.raises(WriterLeaseRequired, match="'nfs4'"):
        sdk_managed_lock_directory(os.path.realpath(tmp_path))
