"""N-5 (PC3 residual): every lease acquisition re-checks the lock directory's owner and mode (`D-IMPL-374`; SEC-013).

PC3 (panel C3) judges a declared ``writer_lease_lock_dir`` at connection
validation: its own real path, existing, a directory, owned by this process's
effective user, not group- or world-writable. The scoped re-review measured
that an acquisition re-checked only the real path: a directory changed to
``0777`` after validation, or swapped for another real ``0777`` directory, was
ACQUIRED. Anyone who can write the directory can replace the lock file a
writer is about to take, so the rule must hold when the lock file is opened,
not only when the settings were read.

Held here, at the lease and through a real boot: a directory made group- or
world-writable, swapped, or reassigned to another owner after validation is
refused at acquisition, by name, and no lock file is created in it; an
unchanged private directory is acquired (the control).

Offline: lock directories under ``tmp_path``; the Fluree boot runs over an
in-process ``httpx`` double.
"""

from __future__ import annotations

import contextlib
import os
import pathlib
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from tests.graph.test_network_store_writer_lease import LEASE_FIELD, _boot, _connection

IDENTITY = "fluree:http://ledger.invalid:8090/ccf:n5"


def _private(tmp_path: pathlib.Path) -> pathlib.Path:
    locks = tmp_path / "locks"
    locks.mkdir(mode=0o700)
    return locks


def _lock_files(directory: pathlib.Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir() if entry.name.endswith(".lock"))


@pytest.mark.parametrize("mode", [0o777, 0o770, 0o702], ids=["0777", "0770", "0702"])
def test_a_directory_made_group_or_world_writable_after_validation_is_refused_at_acquisition(
    mode: int, tmp_path: pathlib.Path
) -> None:
    from ccf.graph.leases import lock_directory_writer_lease, require_private_lock_directory

    locks = _private(tmp_path)
    require_private_lock_directory(str(locks))  # validation passes: private, owned, real
    source = lock_directory_writer_lease(str(locks))
    locks.chmod(mode)
    with pytest.raises(ValueError, match="group- or world-writable"):
        source(IDENTITY)
    assert _lock_files(locks) == []


def test_a_directory_swapped_for_another_real_0777_directory_is_refused_at_acquisition(
    tmp_path: pathlib.Path,
) -> None:
    from ccf.graph.leases import lock_directory_writer_lease

    locks = _private(tmp_path)
    source = lock_directory_writer_lease(str(locks))
    locks.rename(tmp_path / "retired")
    locks.mkdir(mode=0o700)
    locks.chmod(0o777)  # another real directory, at the declared path
    with pytest.raises(ValueError, match="group- or world-writable"):
        source(IDENTITY)
    assert _lock_files(locks) == []


def test_a_directory_whose_owner_is_no_longer_this_user_is_refused_at_acquisition(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ccf.graph.leases as leases

    locks = _private(tmp_path)
    source = leases.lock_directory_writer_lease(str(locks))
    real_uid = os.geteuid()
    monkeypatch.setattr(leases.os, "geteuid", lambda: real_uid + 1)
    with pytest.raises(ValueError, match="owned by"):
        source(IDENTITY)
    assert _lock_files(locks) == []


def test_control_an_unchanged_private_directory_is_acquired_at_every_acquisition(
    tmp_path: pathlib.Path,
) -> None:
    from ccf.graph.leases import lock_directory_writer_lease

    locks = _private(tmp_path)
    source = lock_directory_writer_lease(str(locks))
    for _ in range(2):
        lease = source(IDENTITY)
        try:
            assert lease.scope == "cross-process"
        finally:
            lease.release()
    assert len(_lock_files(locks)) == 1


# --- through a real boot: validation passes, the directory changes, the mint refuses ----


@contextlib.contextmanager
def _fluree_double_that_widens(directory: pathlib.Path, mode: int) -> Iterator[None]:
    """An offline Fluree double whose ledger bootstrap changes ``directory``'s mode.

    The store's constructor runs after connection validation and before the
    boot mint acquires the lease, so a change made while it answers ``POST
    /create`` is exactly "after validation, before acquisition".
    """
    import httpx

    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/fluree.json":
            return httpx.Response(200, json={"api_base_url": "/v1/fluree"})
        if request.url.path.endswith("/create"):
            directory.chmod(mode)
            return httpx.Response(409, json={})
        return httpx.Response(200, json={})

    def _client(**kwargs: Any) -> httpx.Client:
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    httpx.Client = _client  # type: ignore[misc,assignment]
    try:
        yield
    finally:
        httpx.Client = real_client  # type: ignore[misc]


def test_a_boot_whose_lock_directory_is_widened_after_validation_is_refused_at_the_mint(
    tmp_path: pathlib.Path,
) -> None:
    locks = _private(tmp_path)
    connection = _connection("fluree", f"n5_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(locks)
    with _fluree_double_that_widens(locks, 0o777):
        with pytest.raises(ValueError, match="group- or world-writable"):
            handle = _boot("fluree", connection)
            handle.close()
    assert _lock_files(locks) == []
