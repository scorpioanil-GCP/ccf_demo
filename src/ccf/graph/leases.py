"""The reference lock-directory writer lease: SEC-013, D-IMPL-374 (1).

SDK extension of whitepaper §7.3 / INV-CH7-10 and CLAUDE.md §10 ("the
single-writer invariant ... is architectural, not advisory"). A persistent
network store mints a writer only under a lease its deployment declares
(``src/ccf/graph/protocols.py::acquire_declared_writer_lease``). This module
is the one implementation of the lease a deployment can declare through
connection settings alone. Every network adapter's ``_open_store`` calls
:func:`declared_lock_directory_lease`, so the rule lives in one place.

**The deployment declares the directory. The mechanism chooses the file.** The
lock file is ``<directory>/<sha256(graph identity)>.lock``, derived from the
store's credential-free graph identity. Two writers of one graph that declare
the same directory therefore always contend for the same file, whatever else
they spell differently, and a deployment cannot point two writers of one graph
at two files. A relative directory is refused by name, because it would
resolve against each process's working directory.

**What a file lease covers, disclosed rather than implied.** An exclusive
``flock`` excludes only writers that share that filesystem with real
``flock`` semantics. Across hosts it enforces nothing, unless the directory is
on a shared filesystem whose locks work across hosts. Two writers that declare
*different* directories are not excluded either. A deployment that writes one
graph from several hosts needs a lock service every host reaches.

The lock file is opened ``O_NOFOLLOW`` with mode ``0o600``. A lock file this
user cannot open, or one another user owns, is refused as
``src/ccf/graph/protocols.py::WriterLeaseHeld``: another principal holds the
resource the lease is keyed on. A symbolic link at the lock path is refused by
name, never followed.
"""

from __future__ import annotations

import errno
import hashlib
import os
from pathlib import Path
from types import TracebackType
from typing import Annotated

from pydantic import AfterValidator

from ccf.graph.protocols import (
    WriterLease,
    WriterLeaseHeld,
    WriterLeaseScope,
    WriterLeaseSource,
)

try:  # pragma: no cover - import shape only
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - a platform without flock
    _fcntl = None  # type: ignore[assignment]

__ccf_mode__ = "algorithmic"

__all__ = [
    "LOCK_FILE_SUFFIX",
    "AbsoluteLockDirectory",
    "LockFileWriterLease",
    "declared_lock_directory_lease",
    "lock_directory_writer_lease",
    "lock_file_name",
    "require_absolute_lock_directory",
]

#: Appended to the identity digest to name a graph's lock file.
LOCK_FILE_SUFFIX = ".lock"


def lock_file_name(graph_identity: str) -> str:
    """The lock file's name for ``graph_identity``: its SHA-256, hex, plus the suffix.

    SEC-013 (D-IMPL-374 (1)). Derived, never chosen. The digest keeps the name
    filesystem-safe whatever the identity contains, and it reveals nothing the
    identity does not.
    """
    digest = hashlib.sha256(graph_identity.encode("utf-8")).hexdigest()
    return f"{digest}{LOCK_FILE_SUFFIX}"


def require_absolute_lock_directory(value: str) -> str:
    """Return ``value`` if it is an absolute path; refuse it by name otherwise.

    SEC-013 (D-IMPL-374 (1)). A relative lock directory resolves against each
    process's own working directory, so two writers of one graph started from
    different directories would lock two different files and both mint.

    Raises:
        ValueError: ``value`` is not an absolute path.
    """
    if not Path(value).is_absolute():
        raise ValueError(
            "writer_lease_lock_dir must be an absolute path: a relative lock"
            " directory resolves against each process's working directory, so"
            " two writers of one graph could lock two different files"
            " (SEC-013, D-IMPL-374)"
        )
    return value


#: A connection-settings type for a lock directory: a string refused at
#: validation unless it is an absolute path (SEC-013, D-IMPL-374 (1)).
AbsoluteLockDirectory = Annotated[str, AfterValidator(require_absolute_lock_directory)]


class LockFileWriterLease:
    """An exclusive ``flock`` on one lock file, held from the mint to the writer's close.

    SEC-013 (D-IMPL-374 (1)); whitepaper §7.3 / INV-CH7-10. Scope
    ``"cross-process"`` within the filesystem's ``flock`` semantics (see the
    module docstring). ``flock(LOCK_EX | LOCK_NB)``, never ``lockf``, because a
    ``flock`` belongs to an open file description, so a second descriptor in
    this process is refused too. The kernel drops it when the holder dies, so a
    crash never wedges a later boot. It never blocks.

    Args:
        path: The lock file. Opened ``O_RDWR | O_CREAT | O_CLOEXEC |
            O_NOFOLLOW`` with mode ``0o600``.

    Raises:
        WriterLeaseHeld: another holder has the lock, or the lock file is not
            this user's (unopenable, or owned by another user).
        RuntimeError: the lock path is a symbolic link, or the platform has no
            ``flock``.
    """

    def __init__(self, *, path: Path) -> None:
        if _fcntl is None:  # pragma: no cover - a platform without flock
            raise RuntimeError(
                "the lock-file writer lease requires fcntl.flock, which this"
                " platform lacks; refusing to mint a writer unleased (SEC-013)"
            )
        flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW
        try:
            fd = os.open(path, flags, 0o600)
        except PermissionError:
            raise WriterLeaseHeld(
                f"lock file {str(path)!r} cannot be opened by this user; another"
                " principal holds the resource this lease is keyed on"
            ) from None
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise RuntimeError(
                    f"lock file {str(path)!r} is a symbolic link; refusing to"
                    " follow it (SEC-013, D-IMPL-374)"
                ) from None
            raise
        try:
            if os.fstat(fd).st_uid != os.geteuid():
                raise WriterLeaseHeld(
                    f"lock file {str(path)!r} is owned by another user; another"
                    " principal holds the resource this lease is keyed on"
                )
            try:
                _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
            except BlockingIOError:
                raise WriterLeaseHeld(f"flock on {str(path)!r} is held") from None
        except BaseException:
            os.close(fd)
            raise
        self._fd: int | None = fd
        self._path = path

    @property
    def scope(self) -> WriterLeaseScope:
        return "cross-process"

    @property
    def mechanism(self) -> str:
        return f"flock on {str(self._path)!r}"

    def release(self) -> None:
        """Unlock and close the lock-file descriptor. Idempotent."""
        fd, self._fd = self._fd, None
        if fd is None:
            return
        try:
            if _fcntl is not None:
                _fcntl.flock(fd, _fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def __enter__(self) -> LockFileWriterLease:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


def lock_directory_writer_lease(lock_dir: str | Path) -> WriterLeaseSource:
    """The declared lease over the absolute directory ``lock_dir``, not yet held.

    SEC-013 (D-IMPL-374 (1)). Calling the result with a graph identity acquires
    :class:`LockFileWriterLease` on ``<resolved lock_dir>/``
    :func:`lock_file_name`. The directory is resolved at acquisition, so two
    spellings of one directory reach one file. The directory must exist.

    Raises:
        ValueError: ``lock_dir`` is not an absolute path.
    """
    directory = Path(require_absolute_lock_directory(str(lock_dir)))

    def acquire(graph_identity: str) -> WriterLease:
        return LockFileWriterLease(
            path=directory.resolve() / lock_file_name(graph_identity)
        )

    return acquire


def declared_lock_directory_lease(lock_dir: str | None) -> WriterLeaseSource | None:
    """The lock-directory lease a connection setting declares, or ``None`` if none does.

    SEC-013 (D-IMPL-374 (1)). The one helper every network adapter's
    ``_open_store`` calls with its ``writer_lease_lock_dir`` setting. ``None``
    means no lease was declared, and the store will then refuse to mint
    (``WriterLeaseRequired``).
    """
    return None if lock_dir is None else lock_directory_writer_lease(lock_dir)
