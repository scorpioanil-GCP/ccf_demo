# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""cp-06C's door keeps its replay evidence in a private persistent folder (`D-IMPL-383`).

Dave, 2026-10-16: *"introduce a distinct ``evidence_root`` parameter. Do not
reuse ``scratch`` for durable evidence."* Only the bank launcher reads
``CCF_REPLAY_EVIDENCE_ROOT``; set, it validates the folder and passes it as
``evidence_root=``, and still supplies a temporary directory as ``scratch``.
Unset, it omits ``evidence_root`` and keeps today's temporary behavior. The
``--evidence-dir`` flag is gone, so there is exactly one setting.

Estate-free: these tests exercise only the folders the door resolves, never the
product. The live door is ``test_cp_06_mcp_door.py``'s.
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


VARIABLE = "CCF_REPLAY_EVIDENCE_ROOT"


def test_a_configured_evidence_root_is_the_folder_named_and_scratch_is_still_temporary(
    serve: ModuleType, tmp_path: pathlib.Path
) -> None:
    folder = _private(tmp_path / "evidence")
    with serve.door_roots({VARIABLE: str(folder)}) as (scratch, evidence_root):
        assert evidence_root == folder
        assert scratch != folder and folder not in scratch.parents and scratch not in folder.parents
        held = scratch
        (evidence_root / "kept.sqlite3").write_bytes(b"graph")
    assert not held.exists(), "the scratch is temporary even when the evidence root is configured"
    assert (folder / "kept.sqlite3").read_bytes() == b"graph", "nothing deletes retained evidence"


def test_without_the_variable_there_is_no_evidence_root_and_scratch_is_temporary(serve: ModuleType) -> None:
    with serve.door_roots({}) as (scratch, evidence_root):
        assert evidence_root is None
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
        (lambda tmp: pathlib.Path(""), "absolute"),
    ],
)
def test_an_unusable_evidence_root_is_refused_before_the_door_opens(
    serve: ModuleType, tmp_path: pathlib.Path, prepare: object, named: str
) -> None:
    folder = prepare(tmp_path)  # type: ignore[operator]
    with pytest.raises(SystemExit, match=named):
        with serve.door_roots({VARIABLE: str(folder) if str(folder) != "." else ""}):
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
            with serve.door_roots({VARIABLE: str(folder)}):
                pytest.fail("the door opened over a folder it cannot write")
    finally:
        folder.chmod(0o700)


def test_a_symlinked_evidence_root_is_refused_before_the_door_opens(
    serve: ModuleType, tmp_path: pathlib.Path
) -> None:
    """The evidence must be in the folder named: a symlink to a private folder elsewhere is refused."""
    target = _private(tmp_path / "elsewhere")
    link = tmp_path / "evidence"
    link.symlink_to(target)
    with pytest.raises(SystemExit, match="symlink"):
        with serve.door_roots({VARIABLE: str(link)}):
            pass


def test_the_bank_launcher_always_sets_the_evidence_root_and_passes_no_flag() -> None:
    script = LAUNCH.read_text(encoding="utf-8")
    assert "for d in scratch run logs evidence; do install -d -m 700" in script, "the launcher creates it private"
    assert 'CCF_REPLAY_EVIDENCE_ROOT="$ROOT/evidence"' in script, "persistence is mandatory in the bank launcher"
    assert "--evidence-dir" not in script, "one setting, not two"
    assert '-L "$ROOT/evidence"' in script, "the launcher refuses a symlinked evidence folder"


def test_the_flag_is_gone_and_only_the_launcher_reads_the_variable() -> None:
    """Exactly one setting: no ``--evidence-dir`` anywhere, and the SDK core never reads the variable."""
    repo = EXAMPLE.parents[1]
    for launcher in (EXAMPLE / "run.py", EXAMPLE / "server" / "serve.py"):
        assert "--evidence-dir" not in launcher.read_text(encoding="utf-8"), launcher
    readers = [
        str(path.relative_to(repo))
        for top in ("src", "runtime")
        for path in (repo / top).rglob("*.py")
        if VARIABLE in path.read_text(encoding="utf-8")
    ]
    assert readers == [], f"the SDK core must never read {VARIABLE}: {readers}"


@pytest.mark.parametrize("command", [["decisions"], ["why", "0" * 64], ["replay", "0" * 64]])
def test_the_evidence_commands_refuse_when_nothing_was_retained(
    serve: ModuleType, command: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """``decisions``/``why``/``replay`` read the evidence root; unset, they say so rather than answer empty."""
    monkeypatch.delenv(serve.EVIDENCE_ROOT_VARIABLE, raising=False)
    with pytest.raises(SystemExit, match=f"{serve.EVIDENCE_ROOT_VARIABLE} is not set"):
        serve.main(command)


def test_the_launcher_offers_exactly_the_sdk_evidence_verbs(serve: ModuleType) -> None:
    held = pathlib.Path(serve.__file__).read_text(encoding="utf-8")
    assert "inspection.register(" in held and "inspection.run(" in held
    assert serve.inspection.VERBS == ("decisions", "why", "replay")
