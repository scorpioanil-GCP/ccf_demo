"""The in-process transport creates the binding's SDK-managed identity-lock directory, and only that one (P1 (a)).

A SQLite file writer mints only under a declared identity lock, and the SDK
refuses a lock directory that does not exist. A binding document declaring
``<deployment root>/.ccf-writer-locks`` names the directory the SDK manages, so
``src/ccf/client/adapters/inprocess.py::_materialize_declared_sdk_lock_directory``
creates it through ``ccf.graph.leases.sdk_managed_lock_directory``. Any other
declared directory is the deployment's to create. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import os
from pathlib import Path

from ccf.client.adapters.inprocess import _materialize_declared_sdk_lock_directory
from ccf.graph.leases import LOCK_DIRECTORY_SETTING, SDK_MANAGED_LOCK_DIRECTORY


def test_the_sdk_managed_directory_under_the_root_is_created_private(tmp_path: Path) -> None:
    root = Path(os.path.realpath(tmp_path))
    declared = root / SDK_MANAGED_LOCK_DIRECTORY
    _materialize_declared_sdk_lock_directory({LOCK_DIRECTORY_SETTING: str(declared)}, root=root)
    assert declared.is_dir()
    assert declared.stat().st_mode & 0o777 == 0o700


def test_another_declared_directory_is_not_created(tmp_path: Path) -> None:
    root = Path(os.path.realpath(tmp_path))
    elsewhere = root / "operator-chosen-locks"
    _materialize_declared_sdk_lock_directory({LOCK_DIRECTORY_SETTING: str(elsewhere)}, root=root)
    assert not elsewhere.exists()


def test_a_binding_declaring_no_lock_directory_creates_nothing(tmp_path: Path) -> None:
    root = Path(os.path.realpath(tmp_path))
    _materialize_declared_sdk_lock_directory({"database_path": str(root / "graph.sqlite3")}, root=root)
    _materialize_declared_sdk_lock_directory(None, root=root)
    assert list(root.iterdir()) == []
