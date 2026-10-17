# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""D-IMPL-390 (register item 18): two writers racing one file-backed artifact store.

``src/ccf/artifacts/file_store.py::FileArtifactStore.put`` registers every
write in the store's naming index (``.artifact-names.json``):
``_register_name`` reads the whole index, appends one address under its name,
and ``_write_index`` replaces the file. Before ``D-IMPL-390`` nothing made that
read-append-replace exclusive, so two writers could both read the same index
and each replace it with only their own entry: one name-to-address entry was
lost while its artifact file sat on disk unreachable by name. Measured by
chance on ``3f914416`` with two processes, 40 workflow cycles each: 2 of 160
entries lost in each of 2 of 4 runs. The artifact file's own staging name was
per process too, so two threads putting the *same* artifact shared it and one
``replace`` found it gone.

**The interleaving is forced, not waited for.** Each test puts a rendezvous
exactly where the race lives:

- the index tests wrap the store's ``_read_index`` so each writer, having
  read, waits for the other writer to have read too;
- the same-artifact test wraps the module's ``_write_private`` so each
  writer, having written its artifact staging file, waits for the other.

Without exclusion both writers reach the rendezvous and the race happens every
time. With the lock (``D-IMPL-390``: a blocking ``flock`` on
``.artifact-names.lock`` around the read, the append and the replace) the
second writer cannot reach its read while the first holds the lock, so the
first writer's wait times out, it finishes, and the second then reads an index
that already holds the first entry. Both paths are asserted the same way:
every writer returned without raising, and every name holds its version.

Threads are daemon threads joined with a timeout and child processes are
joined with a timeout, so a lock regression fails the test instead of hanging
the suite.
"""

from __future__ import annotations

import multiprocessing as mp
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts import file_store as file_store_module
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import content_hash
from tests.controlplane.capabilities import capability

TENANT = "acme"
# Deployment vocabulary, declared in the test (CLAUDE.md §6.4).
ARTIFACT_CLASS = "acme.analyst-scratch"
INDEX_FILENAME = ".artifact-names.json"

#: How long a writer waits at the rendezvous for the other writer. On the
#: locked path this wait always expires (the other writer is blocked on the
#: lock), so it is the cost of each green run.
_RENDEZVOUS_SECONDS = 2.0
#: Ceiling on a whole writer, thread or process. Far above any green run.
_JOIN_SECONDS = 60.0


def _store(root: Path) -> FileArtifactStore:
    return FileArtifactStore(root=root, write_kinds=WriteKinds.declare({}))


def _put(store: FileArtifactStore, name: str, artifact: object) -> str:
    authorized = capability(
        ArtifactWrite, tenant=TENANT, resource=f"{ARTIFACT_CLASS}/{name}"
    )
    return store.put(authorized, artifact).content_address


def _versions(store: FileArtifactStore, name: str) -> tuple[str, ...]:
    return store.versions(tenant_id=TENANT, artifact_class=ARTIFACT_CLASS, name=name)


def _run_threads(writers: dict[str, Any]) -> dict[str, str]:
    """Start one daemon thread per writer; return ``{writer: error}`` for each that raised."""
    errors: dict[str, str] = {}

    def run(tag: str, body: Any) -> None:
        try:
            body()
        except BaseException as exc:  # reported by name, asserted by the caller
            errors[tag] = f"{type(exc).__name__}: {exc}"

    threads = [
        threading.Thread(target=run, args=(tag, body), daemon=True)
        for tag, body in writers.items()
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(_JOIN_SECONDS)
    hung = [tag for tag, thread in zip(writers, threads, strict=True) if thread.is_alive()]
    assert not hung, f"writers still running after {_JOIN_SECONDS}s: {hung}"
    return errors


def test_two_threads_with_distinct_names_both_keep_their_index_entry(
    tmp_path: Path,
) -> None:
    """Two threads, one store object, two names: each name holds its version."""
    store = _store(tmp_path / "store")
    barrier = threading.Barrier(2, timeout=_RENDEZVOUS_SECONDS)
    read_index = store._read_index

    def read_then_wait_for_the_other_reader() -> dict[str, list[str]]:
        index = read_index()
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            # The locked path: the other writer could not reach its read.
            pass
        return index

    store._read_index = read_then_wait_for_the_other_reader  # type: ignore[method-assign]

    errors = _run_threads(
        {
            name: (lambda name=name: _put(store, name, {"writer": name}))
            for name in ("writer-a", "writer-b")
        }
    )

    store._read_index = read_index  # type: ignore[method-assign]
    assert errors == {}, f"a put raised: {errors}"
    lost = [
        name
        for name in ("writer-a", "writer-b")
        if content_hash({"writer": name}) not in _versions(store, name)
    ]
    assert lost == [], (
        f"the naming index lost {lost}: both writers read the same index and "
        "each replaced it with only its own entry"
    )


def _wait_for(path: Path, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return True
        time.sleep(0.005)
    return False


def _child_put(
    root: str,
    marks: str,
    name: str,
    other: str,
    queue: "mp.Queue[tuple[str, str]]",
) -> None:
    """Spawned writer: put one artifact, rendezvousing with ``other`` after the index read."""
    store = _store(Path(root))
    mark_dir = Path(marks)
    read_index = store._read_index

    def read_then_wait_for_the_other_reader() -> dict[str, list[str]]:
        index = read_index()
        (mark_dir / f"read-{name}").touch()
        # Times out on the locked path, where the other writer is blocked.
        _wait_for(mark_dir / f"read-{other}", _RENDEZVOUS_SECONDS)
        return index

    store._read_index = read_then_wait_for_the_other_reader  # type: ignore[method-assign]
    # Both interpreters up before either writes, so a slow start cannot
    # serialize the writers and let an unlocked store pass by luck.
    (mark_dir / f"started-{name}").touch()
    if not _wait_for(mark_dir / f"started-{other}", _JOIN_SECONDS):
        queue.put(("ERROR", "the other writer never started"))
        return
    try:
        _put(store, name, {"writer": name})
    except BaseException as exc:  # reported by name, asserted by the parent
        queue.put(("ERROR", f"{type(exc).__name__}: {exc}"))
        return
    queue.put(("PUT", ""))


def test_two_processes_with_distinct_names_both_keep_their_index_entry(
    tmp_path: Path,
) -> None:
    """Two OS processes, one store root, two names: each name holds its version."""
    root = tmp_path / "store"
    _store(root)  # the deployment creates the root once, 0o700
    marks = tmp_path / "marks"
    marks.mkdir()
    ctx = mp.get_context("spawn")
    queues: dict[str, Any] = {}
    processes: dict[str, Any] = {}
    for name, other in (("writer-a", "writer-b"), ("writer-b", "writer-a")):
        queues[name] = ctx.Queue()
        processes[name] = ctx.Process(
            target=_child_put,
            args=(str(root), str(marks), name, other, queues[name]),
            daemon=True,
        )
        processes[name].start()
    outcomes: dict[str, tuple[str, str]] = {}
    try:
        for name, queue in queues.items():
            outcomes[name] = queue.get(timeout=_JOIN_SECONDS)
    finally:
        for process in processes.values():
            process.join(timeout=_JOIN_SECONDS)
            if process.is_alive():
                process.kill()

    assert all(status == "PUT" for status, _ in outcomes.values()), (
        f"a writer did not complete its put: {outcomes}"
    )
    store = _store(root)
    lost = [
        name
        for name in ("writer-a", "writer-b")
        if content_hash({"writer": name}) not in _versions(store, name)
    ]
    assert lost == [], (
        f"the naming index lost {lost}: both processes read the same index and "
        "each replaced it with only its own entry"
    )


def test_two_threads_putting_the_same_artifact_both_succeed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two threads put one artifact under one name at once: both succeed, one version."""
    store = _store(tmp_path / "store")
    barrier = threading.Barrier(2, timeout=_RENDEZVOUS_SECONDS)
    write_private = file_store_module._write_private

    def write_then_wait_for_the_other_writer(path: Path, payload: bytes) -> None:
        write_private(path, payload)
        if path.name.startswith(INDEX_FILENAME):
            return  # only the artifact's own staging file is the subject here
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass

    monkeypatch.setattr(
        file_store_module, "_write_private", write_then_wait_for_the_other_writer
    )
    artifact = {"same": "artifact"}
    addresses: dict[str, str] = {}

    def writer(tag: str) -> None:
        addresses[tag] = _put(store, "same-name", artifact)

    errors = _run_threads(
        {tag: (lambda tag=tag: writer(tag)) for tag in ("thread-1", "thread-2")}
    )
    monkeypatch.undo()

    assert errors == {}, (
        f"a put raised: {errors} — the two writers shared one staging file and "
        "the second replace found it already moved"
    )
    address = content_hash(artifact)
    assert addresses == {"thread-1": address, "thread-2": address}
    assert _versions(store, "same-name") == (address,)
    assert store.get(content_address=address)
    leftovers = sorted(
        path.name for path in store.root.iterdir() if path.name.endswith(".partial")
    )
    assert leftovers == [], f"staging files left behind: {leftovers}"
