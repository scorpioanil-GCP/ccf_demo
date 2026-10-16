# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""cp-06C's door keeps its replay evidence in a private persistent folder (`D-IMPL-383`).

The reviewer's instruction 1, adopted by Dave (2026-10-15 20:27): *"Make
persistence mandatory in the bank launcher. Use a private directory under the
instance root, outside TemporaryDirectory, and pass it through the existing
scratch argument. The bank launcher must refuse if that directory is unusable.
Development examples can retain temporary storage."*

Estate-free: these tests exercise only the folder the door's scratch resolves
to, never the product. The live door is ``test_cp_06_mcp_door.py``'s.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
from types import ModuleType

import pytest

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "examples" / "cp-06-canonical-collateral-and-setoff-coverage"
LAUNCH = pathlib.Path(__file__).resolve().parents[2] / "packaging" / "bank-controlled" / "launch.sh"


@pytest.fixture()
def serve() -> ModuleType:
    saved = {name: sys.modules.pop(name, None) for name in ("produce", "deployment", "acquisition", "projection")}
    try:
        spec = importlib.util.spec_from_file_location("cp06c_server_serve", EXAMPLE / "server" / "serve.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, value in saved.items():
            sys.modules.pop(name, None)
            if value is not None:
                sys.modules[name] = value


def _private(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def _world_readable(path: pathlib.Path) -> pathlib.Path:
    path.mkdir()
    path.chmod(0o755)
    return path


def test_a_private_evidence_folder_is_used_as_scratch_and_survives_the_door(
    serve: ModuleType, tmp_path: pathlib.Path
) -> None:
    folder = _private(tmp_path / "evidence")
    with serve.door_scratch(folder) as scratch:
        assert scratch == folder
        (scratch / "kept.sqlite3").write_bytes(b"graph")
    assert (folder / "kept.sqlite3").read_bytes() == b"graph", "nothing deletes retained evidence"


def test_without_an_evidence_folder_the_development_door_keeps_temporary_storage(
    serve: ModuleType,
) -> None:
    with serve.door_scratch(None) as scratch:
        held = pathlib.Path(scratch)
        assert held.is_dir()
    assert not held.exists(), "the development door's scratch is still temporary"


@pytest.mark.parametrize(
    ("prepare", "named"),
    [
        (lambda tmp: tmp / "absent", "does not exist"),
        (lambda tmp: (tmp / "afile").write_bytes(b"") or tmp / "afile", "not a directory"),
        (lambda tmp: _world_readable(tmp / "open"), "mode 700"),
        (lambda tmp: pathlib.Path("relative/evidence"), "absolute"),
    ],
)
def test_an_unusable_evidence_folder_is_refused_before_the_door_opens(
    serve: ModuleType, tmp_path: pathlib.Path, prepare: object, named: str
) -> None:
    folder = prepare(tmp_path)  # type: ignore[operator]
    with pytest.raises(SystemExit, match=named):
        with serve.door_scratch(folder):
            pytest.fail("the door opened over an unusable evidence folder")


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere; the check is meaningful only unprivileged")
def test_a_read_only_folder_is_refused(serve: ModuleType, tmp_path: pathlib.Path) -> None:
    """A folder the account cannot write is refused. Mode 500 trips the mode-700 check first;
    the separate writable check covers what a mode cannot show (a read-only mount), and needs
    privileges to stage, so it is not exercised here."""
    folder = _private(tmp_path / "readonly")
    folder.chmod(0o500)
    try:
        with pytest.raises(SystemExit, match="mode 700"):
            with serve.door_scratch(folder):
                pytest.fail("the door opened over a folder it cannot write")
    finally:
        folder.chmod(0o700)


def test_the_bank_launcher_always_hands_the_door_a_private_evidence_folder() -> None:
    script = LAUNCH.read_text(encoding="utf-8")
    assert "for d in scratch run logs evidence; do install -d -m 700" in script, "the launcher creates it private"
    assert '--evidence-dir "$ROOT/evidence"' in script, "persistence is mandatory in the bank launcher"


def test_a_symlinked_evidence_folder_is_refused_before_the_door_opens(
    serve: ModuleType, tmp_path: pathlib.Path
) -> None:
    """The evidence must be under the instance root: a symlink to a private folder elsewhere is refused."""
    target = _private(tmp_path / "elsewhere")
    link = tmp_path / "evidence"
    link.symlink_to(target)
    with pytest.raises(SystemExit, match="symlink"):
        with serve.door_scratch(link):
            pass


def test_the_bank_launcher_refuses_a_symlinked_evidence_folder() -> None:
    assert '-L "$ROOT/evidence"' in LAUNCH.read_text(encoding="utf-8")
