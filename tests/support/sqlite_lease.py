"""The identity-lock directory a test's SQLite writer declares (P1 (a), Tuesday GO item 4).

A SQLite file writer now mints only under a declared identity lock
(``src/ccf/graph/backends/sqlite.py::SqliteGraphStore.writer_lease``). Test
roots are private pytest directories, so a lock directory beside the database
file is sound in tests: every writer of that file in the test asks for the same
one. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import os
from pathlib import Path

from ccf.graph.leases import SDK_MANAGED_LOCK_DIRECTORY, lock_directory_writer_lease
from ccf.graph.protocols import WriterLeaseSource

__all__ = ["lease_beside", "lock_dir_beside", "private_lock_directory"]


def private_lock_directory(directory: str | Path) -> str:
    """Create ``directory`` private (mode ``0o700``) if absent and return its real absolute path.

    For a deployment whose binding document declares its lock directory as
    data (``writer_lease_lock_dir: {path: …}``): the declaration names the
    directory, and whoever materializes the deployment creates it.
    """
    path = Path(directory)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    else:
        os.chmod(path, 0o700)
    return os.path.realpath(path)


def lock_dir_beside(database_path: str | Path) -> str:
    """Create a private identity-lock directory for ``database_path`` and return its real absolute path.

    The directory is a SIBLING of the database's folder,
    ``<folder>.ccf-writer-locks`` (mode ``0o700``), not a child of it: tests
    assert what sits beside a database file, and a lock directory among those
    entries would change every such listing. Every writer of one database file
    in a test asks for the same directory.
    """
    path = Path(database_path)
    if not path.is_absolute():
        raise ValueError(f"lock_dir_beside needs an absolute database path, not {str(path)!r}")
    folder = Path(os.path.realpath(path.parent))
    directory = folder.parent / f"{folder.name}{SDK_MANAGED_LOCK_DIRECTORY}"
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError:
        pass
    else:
        os.chmod(directory, 0o700)
    return str(directory)


def lease_beside(database_path: str | Path) -> WriterLeaseSource:
    """The declared writer lease for a hand-built ``SqliteGraphStore`` of ``database_path``."""
    return lock_directory_writer_lease(lock_dir_beside(database_path))
