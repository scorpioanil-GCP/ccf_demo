# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A path-backed, single-process Control Plane state store and HITL transport (SEC-001, D-IMPL-391).

The SDK ships no approval store a second process can reach: its reference
state store and HITL transport are in memory. Dave's ruling 2(a) of
2026-10-17 13:27 MST (*"Stores labeled single-process get the graph store's
lock. A second process is refused by name."*) binds the implementations a
deployment brings, and the Protocol docstrings
(``src/ccf/controlplane/state.py::ConditionalStateStore``,
``src/ccf/hitl/transport.py::HITLTransportProtocol``) state it as a MUST. This
module is the test stand-in that meets it, so the acceptance criteria can be
proved in real OS processes:

* :class:`PathBackedStateStore` at ``P/state/`` and :class:`PathBackedHitlTransport`
  at ``P/queue/``, each declaring ``scope = "process"``;
* each takes an exclusive SEC-013 lease
  (``src/ccf/graph/leases.py::LockFileWriterLease``) on a lock file INSIDE its
  own directory when it is OPENED, before any record is read, so a second
  process can neither submit a verdict nor read in-flight state. A refused open
  logs one record naming the lock and the rule (Dave, 2026-10-17 15:25 MST:
  *"Logged by the refused process only."*) and raises
  :class:`~ccf.graph.protocols.WriterLeaseHeld`;
* the lease is released by :meth:`close` and, through ``weakref.finalize``,
  when the object is collected — a :class:`LockFileWriterLease` never releases
  itself;
* both halves are durable: every write is persisted before the call returns,
  so a later process that opens ``P`` sees the suspension, the verdicts and the
  closures;
* the state store mints its identity once (``secrets.token_hex(32)``) and
  records, beside it, where its substrate lives (the directory's device and
  inode). Opened anywhere else — a copied directory — it refuses by name until
  it is deliberately re-minted (:class:`SubstrateMoved`; the copy MUST of
  Dave's 2026-10-09 10:54 MST ruling).

Stand-in only: persistence is a whole-file pickle written by a single holder,
which the lease makes safe. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import logging
import os
import pickle
import secrets
import threading
import weakref
from pathlib import Path
from typing import Any

from ccf.controlplane.state import InMemoryStateStore
from ccf.graph.leases import LockFileWriterLease
from ccf.graph.protocols import WriterLeaseHeld
from ccf.hitl.transport import InMemoryHitlTransport

__all__ = [
    "LEASE_LOG",
    "LOCK_FILENAME",
    "SINGLE_PROCESS_RULE",
    "PathBackedHitlTransport",
    "PathBackedStateStore",
    "SubstrateMoved",
    "open_pair",
]

#: The lock file each half holds, inside its own directory.
LOCK_FILENAME = ".ccf-single-process.lock"
#: The rule a refused open names, in its log record and its exception.
SINGLE_PROCESS_RULE = (
    "a substrate declared scope 'process' is held by one process from open to"
    " close; a second process is refused by name (SEC-001; D-IMPL-391, ruling 2(a))"
)
#: The logger a refused open records to, in the refused process only.
LEASE_LOG = logging.getLogger("tests.support.path_backed_approval_pair")

_IDENTITY_FILE = "identity.pickle"
_RECORDS_FILE = "records.pickle"
_QUEUE_FILE = "queue.pickle"


class SubstrateMoved(RuntimeError):
    """The store was opened somewhere other than where its identity was minted (a copy)."""


def _private_directory(directory: Path) -> Path:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    return directory


def _take_lease(directory: Path, owner: object, *, what: str) -> LockFileWriterLease:
    """The exclusive lease on ``directory``, held by ``owner`` until close or collection."""
    lock = directory / LOCK_FILENAME
    try:
        lease = LockFileWriterLease(path=lock)
    except WriterLeaseHeld as exc:
        LEASE_LOG.error(
            "refused to open the %s at %s: flock on %s is held; %s",
            what,
            directory,
            lock,
            SINGLE_PROCESS_RULE,
        )
        raise WriterLeaseHeld(
            f"the {what} at {str(directory)!r} is held by another holder ({exc});"
            f" {SINGLE_PROCESS_RULE}"
        ) from None
    weakref.finalize(owner, lease.release)
    return lease


def _write_atomically(path: Path, payload: bytes) -> None:
    staging = path.with_name(f".{path.name}.{os.getpid()}.partial")
    fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
    staging.replace(path)


def _read(path: Path, default: object) -> Any:
    try:
        with path.open("rb") as handle:
            return pickle.load(handle)
    except FileNotFoundError:
        return default


class PathBackedStateStore(InMemoryStateStore):
    """A single-process :class:`~ccf.controlplane.state.ConditionalStateStore` at ``directory``.

    Args:
        directory: The substrate. Created ``0o700`` if absent.
        remint: Deliberately mint a new identity here (an operator's act after
            a copy). Every run in flight here then names the old identity and is
            refused as another store's; an operator reconciles them.

    Raises:
        WriterLeaseHeld: another holder has the substrate.
        SubstrateMoved: the substrate was copied from where it was minted.
    """

    scope = "process"

    def __init__(self, directory: Path | str, *, remint: bool = False) -> None:
        super().__init__()
        self.directory = _private_directory(Path(directory))
        # The lease FIRST: nothing is read until this process holds it.
        self._lease = _take_lease(self.directory, self, what="Control Plane state store")
        self._persist_lock = threading.Lock()
        here = os.stat(self.directory)
        location = (here.st_dev, here.st_ino)
        stamp = _read(self.directory / _IDENTITY_FILE, None)
        if stamp is None or remint:
            stamp = {"identity": secrets.token_hex(32), "location": location}
            _write_atomically(self.directory / _IDENTITY_FILE, pickle.dumps(stamp))
        elif tuple(stamp["location"]) != location:
            self.close()
            raise SubstrateMoved(
                f"the Control Plane state store at {str(self.directory)!r} was minted at"
                f" device/inode {tuple(stamp['location'])}, not {location}: it was copied."
                " A copied store refuses to open until an operator re-mints it, which"
                " strands its runs in flight (D-IMPL-391; the copy MUST)"
            )
        self._substrate_identity: str = stamp["identity"]
        records, versions = _read(self.directory / _RECORDS_FILE, ({}, {}))
        self._records.update(records)
        self._versions.update(versions)

    @property
    def identity(self) -> str:
        """Minted once for this substrate and persisted beside its records."""
        return self._substrate_identity

    def writer_lease(self) -> LockFileWriterLease:
        """The lease this store has held since it was opened."""
        return self._lease

    def close(self) -> None:
        self._lease.release()

    def _save(self) -> None:
        _write_atomically(
            self.directory / _RECORDS_FILE,
            pickle.dumps((dict(self._records), dict(self._versions))),
        )

    def put(self, *args: Any, **kwargs: Any) -> None:
        with self._persist_lock:
            super().put(*args, **kwargs)
            self._save()

    def put_if(self, *args: Any, **kwargs: Any) -> int:
        with self._persist_lock:
            version = super().put_if(*args, **kwargs)
            self._save()
            return version


class PathBackedHitlTransport(InMemoryHitlTransport):
    """A single-process HITL transport at ``directory``: durable queue, verdicts and closures.

    Raises:
        WriterLeaseHeld: another holder has the queue.
    """

    scope = "process"

    def __init__(self, directory: Path | str) -> None:
        super().__init__()
        self.directory = _private_directory(Path(directory))
        self._lease = _take_lease(self.directory, self, what="HITL transport")
        self._persist_lock = threading.Lock()
        saved = _read(self.directory / _QUEUE_FILE, None)
        if saved is not None:
            (
                self._pending,
                self._submissions,
                self._seen_nonces,
                self._claims,
                self._closures,
            ) = saved

    def writer_lease(self) -> LockFileWriterLease:
        """The lease this transport has held since it was opened."""
        return self._lease

    def close(self) -> None:
        self._lease.release()

    def _save(self) -> None:
        with self._lock:
            snapshot = (
                self._pending,
                self._submissions,
                self._seen_nonces,
                self._claims,
                self._closures,
            )
            payload = pickle.dumps(snapshot)
        _write_atomically(self.directory / _QUEUE_FILE, payload)

    def _persisted(self, call: Any) -> Any:
        with self._persist_lock:
            result = call()
            self._save()
            return result

    def enqueue(self, *, event: Any) -> None:
        self._persisted(lambda: super(PathBackedHitlTransport, self).enqueue(event=event))

    def dequeue(self, *, tenant: str) -> Any:
        return self._persisted(lambda: super(PathBackedHitlTransport, self).dequeue(tenant=tenant))

    def remove(self, *, tenant: str, event_key: str) -> Any:
        return self._persisted(
            lambda: super(PathBackedHitlTransport, self).remove(tenant=tenant, event_key=event_key)
        )

    def submit(self, authorized: Any, *, submission: Any) -> Any:
        return self._persisted(
            lambda: super(PathBackedHitlTransport, self).submit(authorized, submission=submission)
        )

    def close_gate(self, authorized: Any, **kwargs: Any) -> Any:
        return self._persisted(
            lambda: super(PathBackedHitlTransport, self).close_gate(authorized, **kwargs)
        )

    def retire(self, **kwargs: Any) -> Any:
        return self._persisted(lambda: super(PathBackedHitlTransport, self).retire(**kwargs))


def open_pair(root: Path | str) -> tuple[PathBackedStateStore, PathBackedHitlTransport]:
    """Open the state store at ``root/state`` and the transport at ``root/queue``.

    Each half holds its own lock inside its own directory, so one process's
    store and queue never refuse each other. The store is opened first; if the
    queue is then refused, the store is closed before the refusal propagates.
    """
    root = Path(root)
    store = PathBackedStateStore(root / "state")
    try:
        transport = PathBackedHitlTransport(root / "queue")
    except BaseException:
        store.close()
        raise
    return store, transport
