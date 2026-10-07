"""SEC-013: the single-writer guard must hold across processes, not only inside one.

Whitepaper §7.3 and INV-CH7-10 (exactly one writer per graph); CLAUDE.md §10
("the single-writer invariant ... is architectural, not advisory"). The boot
token's live-writer table (``src/ccf/graph/_writer.py::_LIVE_WRITERS``) is
module state, so before SEC-013 two processes booting the same SQLite file each
minted a writer and both booted through the real composition root. These tests
put a real second process (``multiprocessing``, spawn) against a graph the
first process holds and assert the second is refused **by name**.

Scope of what is proven here, stated so nobody reads more into it: the SQLite
and Postgres stores take a cross-process lease. The memory and demo stores
declare ``process`` scope, exact there because no second process can reach
their graph. The persistent network stores take a deployment-declared lease and
refuse to mint without one (D-IMPL-374); that is proven in
``tests/graph/test_network_store_writer_lease.py``.

Synchronization: the parent boots and holds *before* the child starts; the
child reports its outcome (status, exception class NAME, message) over a queue
— exceptions do not pickle reliably across spawn — and never sleeps to
synchronize. No estate is touched: SQLite files live in ``tmp_path``; the
Postgres twin uses the disposable ``postgres_dsn`` fixture only.
"""

from __future__ import annotations

import fcntl
import multiprocessing as mp
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from ccf.graph._writer import SingleWriterViolation

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

_TIMEOUT_SECONDS = 120


def _boot(backend: str, connection: dict[str, Any]) -> "FabricHandle":
    """Boot one fabric through the real composition root, the suite's recipe."""
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
    spec_version = register_at_composition(
        registry, RESOLUTION_SPEC_KEY, _resolution_spec()
    )
    policy_version = register_at_composition(
        registry, POLICY_BUNDLE_KEY, _policy_bundle()
    )
    return boot(
        backend=backend,
        connection=connection,
        registry=registry,
        resolution_spec_key=RESOLUTION_SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        policy_bundle_version=policy_version,
        tenant_ids=FIXTURE_TENANTS,
    )


def _child_boot(
    backend: str,
    connection: dict[str, Any],
    queue: "mp.Queue[tuple[str, str, str]]",
    close_before_exit: bool,
) -> None:
    """Spawned child: attempt one boot, report the outcome, then exit."""
    try:
        handle = _boot(backend, connection)
    except BaseException as exc:  # reported by name, asserted by the parent
        queue.put(("REFUSED", type(exc).__name__, str(exc)))
        return
    queue.put(("BOOTED", "", ""))
    if close_before_exit:
        handle.close()
    else:
        # A crash: no close, no release, no interpreter shutdown hooks. The
        # queue is flushed first so the report itself is not lost with it.
        queue.close()
        queue.join_thread()
        os._exit(0)


def _run_child(
    backend: str, connection: dict[str, Any], *, close_before_exit: bool = True
) -> tuple[str, str, str]:
    ctx = mp.get_context("spawn")
    queue: mp.Queue[tuple[str, str, str]] = ctx.Queue()
    process = ctx.Process(
        target=_child_boot, args=(backend, connection, queue, close_before_exit)
    )
    process.start()
    try:
        outcome = queue.get(timeout=_TIMEOUT_SECONDS)
    finally:
        process.join(timeout=_TIMEOUT_SECONDS)
    return outcome


def _sidecar(database_path: Path) -> Path:
    """Where the SQLite writer lease lives: beside the resolved database file."""
    return Path(f"{database_path.resolve()}.ccf-writer.lock")


def test_a_second_process_cannot_mint_a_writer_for_a_held_graph(
    tmp_path: Path,
) -> None:
    """Process A holds the graph; a spawned process B is refused by name."""
    database_path = tmp_path / "held.sqlite3"
    connection = {"database_path": database_path}
    holder = _boot("sqlite", connection)
    try:
        status, exc_name, message = _run_child("sqlite", connection)
    finally:
        holder.close()

    assert (status, exc_name) == ("REFUSED", "SingleWriterViolation"), (
        f"a second process obtained a writer over a graph another process holds:"
        f" child reported {status!r} {exc_name!r} {message!r}"
    )
    assert "already exists" in message


def test_after_the_holder_releases_a_second_process_boots(tmp_path: Path) -> None:
    """Closing the holder gives the graph back; a fresh process then boots."""
    database_path = tmp_path / "released.sqlite3"
    connection = {"database_path": database_path}
    holder = _boot("sqlite", connection)
    holder.close()

    status, exc_name, message = _run_child("sqlite", connection)

    assert status == "BOOTED", (
        f"the graph was released but a second process was refused:"
        f" {exc_name!r} {message!r}"
    )


def test_the_lease_is_an_os_lock_not_a_file_that_a_crash_leaves_behind(
    tmp_path: Path,
) -> None:
    """A holder that dies without closing must not wedge every later boot."""
    database_path = tmp_path / "crashed.sqlite3"
    connection = {"database_path": database_path}

    status, exc_name, message = _run_child(
        "sqlite", connection, close_before_exit=False
    )
    assert status == "BOOTED", f"{exc_name!r} {message!r}"

    survivor = _boot("sqlite", connection)
    survivor.close()


def test_the_lease_is_flock_so_a_second_descriptor_in_this_process_is_refused(
    tmp_path: Path,
) -> None:
    """``flock`` excludes a second open file description; ``lockf`` does not.

    POSIX record locks (``lockf``/``fcntl``) are per *process*: a second
    descriptor in the holding process is granted, and closing any descriptor
    drops them. Probed at the OS level, independent of the SDK's message.
    """
    database_path = tmp_path / "flock.sqlite3"
    holder = _boot("sqlite", {"database_path": database_path})
    try:
        fd = os.open(_sidecar(database_path), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)
    finally:
        holder.close()

    fd = os.open(_sidecar(database_path), os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # released: granted
    finally:
        os.close(fd)


def test_one_file_spelled_two_ways_is_still_one_graph(tmp_path: Path) -> None:
    """A relative and an absolute spelling of one file cannot mint two writers."""
    database_path = tmp_path / "spelled.sqlite3"
    other_spelling = Path(os.path.relpath(database_path))
    assert str(other_spelling) != str(database_path)
    holder = _boot("sqlite", {"database_path": database_path})
    try:
        with pytest.raises(SingleWriterViolation, match="already exists"):
            second = _boot("sqlite", {"database_path": other_spelling})
            second.close()
    finally:
        holder.close()


def test_the_in_process_refusal_is_byte_identical(tmp_path: Path) -> None:
    """Inside one process the live-writer table refuses first, with today's text."""
    database_path = tmp_path / "same.sqlite3"
    holder = _boot("sqlite", {"database_path": database_path})
    try:
        with pytest.raises(SingleWriterViolation) as refused:
            _boot("sqlite", {"database_path": database_path})
    finally:
        holder.close()
    assert str(refused.value) == (
        f"a GraphWriter already exists for graph {str(database_path)!r}; "
        "the fabric permits exactly one writer per graph (INV-CH7-10)"
    )


@pytest.mark.postgres
def test_a_second_process_cannot_mint_a_writer_for_a_held_postgres_graph(
    postgres_dsn: str,
) -> None:
    """The Postgres twin: one schema, two processes, a server-keyed advisory lock."""
    connection = {"dsn": postgres_dsn, "schema_name": f"ccf_test_{uuid.uuid4().hex}"}
    holder = _boot("postgres", connection)
    try:
        status, exc_name, message = _run_child("postgres", connection)
    finally:
        holder.close()
    assert (status, exc_name) == ("REFUSED", "SingleWriterViolation"), (
        f"child reported {status!r} {exc_name!r} {message!r}"
    )
    assert "already exists" in message

    status, exc_name, message = _run_child("postgres", connection)
    assert status == "BOOTED", f"{exc_name!r} {message!r}"
