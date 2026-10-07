"""PC3 (panel C3): a writer-lease lock directory reached through a symbolic link is refused (SEC-013; `D-IMPL-374`).

The cross-AI panel measured it with two processes (probe
``probe_b6_symlink_dir.py``): ``writer_lease_lock_dir=/srv/ccf/current/locks``
with ``current`` a symlink retargeted at a release cut-over. The old process
holds ``v1/<sha256(identity)>.lock``; the new one acquires ``v2/<…>.lock`` for
the SAME network graph, because the declared directory is resolved at each
acquisition. Both minted — the single-writer invariant (INV-CH7-10) broken by a
deployment doing nothing unusual.

Ruled: refuse, by name and at config validation, a declared lock directory whose
path differs from its real path (any symlink component), naming the real path to
declare; and require the directory to be owned by the effective user and not
group- or world-writable (the erasure index's directory posture). Direct
construction (``lock_directory_writer_lease``) refuses the symlinked directory
too, and an acquisition re-checks it.

Offline: the SEC-013 suite's network-client doubles; lock directories under
``tmp_path``.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import uuid
from pathlib import Path
from typing import Any

import pytest

from tests.graph.test_network_store_writer_lease import (
    LEASE_FIELD,
    NETWORK_SUBSTRATES,
    _boot,
    _connection,
    _offline_clients,
)

_TIMEOUT_SECONDS = 120
IDENTITY = "fluree:http://ledger.invalid:8090/ccf:main"


def _release_layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    """``<tmp>/v1``, ``<tmp>/v2`` (both private) and ``<tmp>/current -> v1``."""
    v1, v2 = tmp_path / "v1", tmp_path / "v2"
    for directory in (v1, v2):
        directory.mkdir(mode=0o700)
    current = tmp_path / "current"
    current.symlink_to(v1)
    return v1, v2, current


def _acquire(declared: str, hold_seconds: float, queue: "mp.Queue[str]", go: Any) -> None:
    """A spawned writer: declare the lock directory, acquire, report, hold."""
    import time

    try:
        from ccf.graph.leases import lock_directory_writer_lease

        lease = lock_directory_writer_lease(declared)(IDENTITY)
    except BaseException as exc:  # noqa: BLE001 - reported by name
        queue.put(f"REFUSED {type(exc).__name__}: {exc}")
        return
    queue.put(f"ACQUIRED {lease.mechanism}")
    go.wait(hold_seconds)
    lease.release()


def test_pc3_a_retargeted_symlink_never_gives_one_graph_two_lock_files(tmp_path: Path) -> None:
    """Probe B6, inverted: the old and the new release, one declared string, one cut-over."""
    v1, v2, current = _release_layout(tmp_path)
    context = mp.get_context("spawn")
    queue: mp.Queue[str] = context.Queue()
    release = context.Event()
    old = context.Process(target=_acquire, args=(str(current), 30.0, queue, release))
    old.start()
    try:
        first = queue.get(timeout=_TIMEOUT_SECONDS)
        current.unlink()
        current.symlink_to(v2)  # the cut-over retargets the symlink
        new = context.Process(target=_acquire, args=(str(current), 0.0, queue, release))
        new.start()
        second = queue.get(timeout=_TIMEOUT_SECONDS)
        new.join(timeout=_TIMEOUT_SECONDS)
    finally:
        release.set()
        old.join(timeout=_TIMEOUT_SECONDS)
    assert not (first.startswith("ACQUIRED") and second.startswith("ACQUIRED")), (
        f"two writers of one graph both acquired a lease:\n  {first}\n  {second}"
    )
    for outcome in (first, second):
        assert outcome.startswith("REFUSED"), outcome
        assert "symbolic link" in outcome and str(os.path.realpath(current)).rsplit("/", 1)[0] in outcome, outcome


def test_pc3_direct_construction_names_the_real_path_to_declare(tmp_path: Path) -> None:
    from ccf.graph.leases import lock_directory_writer_lease

    v1, _v2, current = _release_layout(tmp_path)
    with pytest.raises(ValueError) as refused:
        lock_directory_writer_lease(str(current))
    assert "symbolic link" in str(refused.value) and repr(str(v1)) in str(refused.value), str(refused.value)


@pytest.mark.parametrize("substrate", NETWORK_SUBSTRATES)
def test_pc3_a_symlinked_lock_dir_is_refused_at_config_validation(substrate: str, tmp_path: Path) -> None:
    from ccf.graph.registry import InvalidBackendConfig

    v1, _v2, current = _release_layout(tmp_path)
    connection = _connection(substrate, f"pc3_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(current)
    with _offline_clients():
        with pytest.raises(InvalidBackendConfig) as refused:
            _boot(substrate, connection)
    assert "symbolic link" in str(refused.value) and str(v1) in str(refused.value), str(refused.value)


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("group-writable", "group- or world-writable"),
        ("world-writable", "group- or world-writable"),
        ("missing", "must exist"),
        ("not-a-directory", "not a directory"),
    ],
)
def test_pc3_an_insecure_or_absent_lock_dir_is_refused_at_config_validation(
    case: str, expected: str, tmp_path: Path
) -> None:
    from ccf.graph.registry import InvalidBackendConfig

    target = tmp_path / "locks"
    if case == "group-writable":
        target.mkdir(mode=0o700)
        target.chmod(0o770)
    elif case == "world-writable":
        target.mkdir(mode=0o700)
        target.chmod(0o703)
    elif case == "not-a-directory":
        target.write_text("")
    connection = _connection("fluree", f"pc3_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(target)
    with _offline_clients():
        with pytest.raises(InvalidBackendConfig) as refused:
            _boot("fluree", connection)
    assert expected in str(refused.value), str(refused.value)


def test_pc3_a_lock_dir_owned_by_another_user_is_refused_at_config_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ccf.graph.leases as leases
    from ccf.graph.registry import InvalidBackendConfig

    real_uid = os.geteuid()
    monkeypatch.setattr(leases.os, "geteuid", lambda: real_uid + 1)
    connection = _connection("fluree", f"pc3_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(tmp_path)
    with _offline_clients():
        with pytest.raises(InvalidBackendConfig) as refused:
            _boot("fluree", connection)
    assert "owned by" in str(refused.value), str(refused.value)


def test_pc3_control_a_private_real_lock_dir_boots(tmp_path: Path) -> None:
    locks = tmp_path / "locks"
    locks.mkdir(mode=0o700)
    connection = _connection("fluree", f"pc3_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(locks)
    with _offline_clients():
        handle = _boot("fluree", connection)
        try:
            assert handle.lease_scope == "cross-process"
        finally:
            handle.close()
