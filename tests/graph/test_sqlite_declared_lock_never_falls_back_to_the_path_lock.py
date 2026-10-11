# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-013 (``D-IMPL-378``, 2026-10-09): with a declared lock directory, a SQLite writer boot whose identity lock cannot
be taken is refused; it never boots on the path lock alone.

Dave's ruling, verbatim (the 06:06 MST list, item 10, confirmed at 06:21 MST): *"... Verify the identity lock still
blocks the renamed-file second writer. Do not fall back silently to the old path lock."* With ``writer_lease_lock_dir``
declared (option (C), lane ``378g-c8``) a writer holds two locks: the sidecar beside the database file's resolved path
(the path lock, ``src/ccf/graph/backends/sqlite.py::SqliteWriterLease``) and a lock keyed on the file's device and
inode in the declared directory (the identity lock, taken by ``src/ccf/graph/backends/sqlite.py::_with_the_file_lease``).
The renamed-file second writer is refused by the identity lock in
``tests/graph/test_sqlite_writer_lease_file_identity.py::test_a_second_process_is_refused_through_the_new_name_of_the_renamed_live_file``.

This module asserts, through a real boot, that when the identity lock cannot be taken the boot is refused and gives
the path lock back, for each way it can fail:

1. another holder has the identity lock;
2. the declared directory became group- or world-writable after the connection settings were validated, so the
   acquisition's own re-judgement (N-5) refuses it;
3. the identity lock's file is a symbolic link, which the lease refuses to follow.

A silent fallback would show as a boot that succeeds holding the path lock alone. Each case has a control: with the
obstacle gone, the same boot succeeds and its ``lease_mechanism`` names both locks, so the refusal was the identity
lock's and the declared configuration was the one in force. What a boot that declares no directory should do (P1 (a))
is design-first and is not asserted here. Every file lives in ``tmp_path``.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import re
from pathlib import Path

import pytest

import ccf.graph.backends.sqlite as sqlite_backend
from ccf.graph._writer import SingleWriterViolation
from ccf.graph.backends.sqlite import WRITER_LEASE_SUFFIX, SqliteGraphStore, _database_file_identity
from ccf.graph.leases import lock_file_name
from tests.graph.test_single_writer_across_processes import _boot
from tests.graph.test_sqlite_writer_lease_file_identity import _declared, _locks

_HELD = "another holder has the identity lock"
_WIDENED = "the lock directory was widened after validation"
_LINKED = "the identity lock's file is a symbolic link"


def _flock_is_free(path: Path) -> bool:
    """Whether an exclusive ``flock`` on ``path`` is granted now (a ``flock`` held by any descriptor refuses it)."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return True
    finally:
        os.close(fd)


@pytest.mark.parametrize("obstacle", [_HELD, _WIDENED, _LINKED])
def test_a_declared_writer_boot_whose_identity_lock_cannot_be_taken_is_refused_and_never_falls_back_to_the_path_lock(
    obstacle: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    locks = _locks(tmp_path)
    database = tmp_path / "graph.sqlite3"
    SqliteGraphStore(database_path=database).close()  # the file exists, so its identity and its lock's name are known
    identity = _database_file_identity(str(database))
    assert identity is not None
    identity_lock = locks / lock_file_name(identity)
    path_lock = Path(f"{database.resolve()}{WRITER_LEASE_SUFFIX}")

    with contextlib.ExitStack() as obstacles:
        expected: tuple[type[BaseException], str]
        if obstacle == _HELD:
            other_holder = os.open(identity_lock, os.O_RDWR | os.O_CREAT, 0o600)
            obstacles.callback(os.close, other_holder)
            fcntl.flock(other_holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
            expected = (SingleWriterViolation, re.escape(f"flock on {str(identity_lock)!r} is held"))
        elif obstacle == _WIDENED:
            identify = sqlite_backend._database_file_identity

            def widen_then_identify(database_path: str) -> str | None:
                # Runs inside the store's open: after the settings were validated, before the mint takes the lease.
                locks.chmod(0o777)
                return identify(database_path)

            monkeypatch.setattr(sqlite_backend, "_database_file_identity", widen_then_identify)
            obstacles.callback(locks.chmod, 0o700)
            obstacles.callback(monkeypatch.undo)
            expected = (ValueError, "group- or world-writable")
        else:
            decoy = tmp_path / "decoy"
            decoy.touch()
            identity_lock.symlink_to(decoy)
            obstacles.callback(identity_lock.unlink)
            expected = (RuntimeError, "is a symbolic link")

        with pytest.raises(expected[0], match=expected[1]):
            _boot("sqlite", _declared(database, locks)).close()
        assert _flock_is_free(path_lock), "the refused boot kept the path lock"

    holder = _boot("sqlite", _declared(database, locks))  # control: the obstacle gone, both locks are taken
    try:
        mechanism = holder.lease_mechanism or ""
    finally:
        holder.close()
    assert f"flock on {str(path_lock)!r}" in mechanism, mechanism
    assert f"flock on {str(identity_lock)!r}" in mechanism, mechanism
