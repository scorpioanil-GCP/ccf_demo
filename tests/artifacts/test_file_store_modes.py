"""SEC-014 exploit test — the file-backed artifact store's file modes (D-IMPL-368, Q8).

Ruled behavior (``docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md``
Q8, fixed modes, no knob): every regular file
``src/ccf/artifacts/file_store.py::FileArtifactStore`` creates is ``0o600`` and
every directory it creates, intermediate parents included, is ``0o700``,
**regardless of the process umask**. ``D-IMPL-369`` replaces the pilot's
tighten reading: an insecure pre-existing root (any mode wider than ``0o700``,
or not owned by the process) is REFUSED BY NAME, without ``chmod``, and its
permissions are left unchanged; pre-existing parents are not the store's.

Every case runs under ``os.umask(0o000)``: that is the umask under which a store
that leaves modes to the host writes ``0o666`` files and ``0o777`` directories,
so a store that only inherits the umask is red here, not lucky. The store is
built at a root that does NOT exist below ``tmp_path`` (which pytest already
creates ``0o700``), so the directory assertion measures directories the store
itself made.

The fourth case is an executor addition beyond the row's three: under a umask
that removes OWNER bits, a store that relied on ``mkdir(mode=0o700)`` or
``os.open(..., 0o600)`` alone would come out ``0o500``/``0o400`` — the
"set the mode explicitly after creation" clause is observable only there,
because a umask can only narrow a requested mode.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from ccf.artifacts import file_store as file_store_module
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ArtifactWrite
from tests.controlplane.capabilities import capability

TENANT = "acme"
# Deployment vocabulary, declared in the test (CLAUDE.md §6.4).
TARGET = "acme.analyst-scratch/modes-probe"
INDEX_FILENAME = ".artifact-names.json"


@contextmanager
def _umask(mask: int) -> Iterator[None]:
    """Run the body under ``mask``; fail if the body left a different umask.

    The row declares a store-local ``umask`` non-conforming (it is process-wide
    and leaks to every thread), and such a store would otherwise pass every
    mode assertion here. Measured: with every ``chmod``/``fchmod`` severed and
    ``os.umask(0o077)`` added to the constructor, the four cases were green
    until this check existed.
    """
    previous = os.umask(mask)
    try:
        yield
        leaked = os.umask(mask)
        assert leaked == mask, (
            f"the store changed the process umask to {oct(leaked)} (set {oct(mask)})"
        )
    finally:
        os.umask(previous)


def _refusal() -> type[Exception]:
    """The typed refusal, read off the module at call time.

    Looked up lazily so that a tree WITHOUT the refusal fails case 2 alone,
    at the case, rather than failing collection for every case in the file.
    """
    refusal: type[Exception] = file_store_module.InsecureArtifactStoreRoot
    return refusal


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def _put_one(store: FileArtifactStore) -> str:
    ref = store.put(
        capability(ArtifactWrite, tenant=TENANT, resource=TARGET),
        {"probe": "sec-014"},
    )
    return ref.content_address


def _walk_modes(top: Path) -> tuple[dict[str, int], dict[str, int]]:
    dirs: dict[str, int] = {str(top): _mode(top)}
    files: dict[str, int] = {}
    for here, subdirs, names in os.walk(top):
        for d in subdirs:
            p = Path(here) / d
            dirs[str(p)] = _mode(p)
        for n in names:
            p = Path(here) / n
            assert p.is_file() and not p.is_symlink(), p
            files[str(p)] = _mode(p)
    return dirs, files


def _assert_private_tree(top: Path, root: Path, address: str) -> None:
    dirs, files = _walk_modes(top)
    # Non-vacuity: the walk reached every directory the store created and
    # both files a put writes (the content file and the naming index).
    expected_dirs = {str(top), str(top / "b"), str(root)}
    assert expected_dirs <= set(dirs), sorted(dirs)
    assert {str(root / address), str(root / INDEX_FILENAME)} <= set(files), sorted(files)
    wide_dirs = {p: oct(m) for p, m in dirs.items() if m != 0o700}
    wide_files = {p: oct(m) for p, m in files.items() if m != 0o600}
    assert wide_dirs == {}, f"directories not 0o700: {wide_dirs}"
    assert wide_files == {}, f"files not 0o600: {wide_files}"


def test_a_store_created_at_a_new_root_is_private_to_the_owner(tmp_path: Path) -> None:
    root = tmp_path / "a" / "b" / "store"
    assert not (tmp_path / "a").exists()
    with _umask(0o000):
        store = FileArtifactStore(root=root, write_kinds=WriteKinds.declare({}))
        address = _put_one(store)
    _assert_private_tree(tmp_path / "a", root, address)


class TestAnInsecurePreExistingRootIsRefusedWithoutChange:
    """``test_an_insecure_pre_existing_root_is_refused_without_change`` (D-IMPL-369).

    Dave, 2026-10-05: "SDK-created roots are owner-only. An insecure
    pre-existing root is refused by name, without chmod. Verify that refusal
    leaves its permissions unchanged."
    """

    def test_an_insecure_pre_existing_root_is_refused_without_change(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "store"
        with _umask(0o000):
            root.mkdir(mode=0o777)
            assert _mode(root) == 0o777  # the precondition the case is about
            with pytest.raises(_refusal()) as refused:
                FileArtifactStore(root=root, write_kinds=WriteKinds.declare({}))
        assert _mode(root) == 0o777, f"the refusal changed the root: {oct(_mode(root))}"
        assert str(root) in str(refused.value)
        assert "0o777" in str(refused.value)
        assert list(root.iterdir()) == []  # nothing written into a refused root

    def test_a_root_owned_by_another_uid_is_refused_without_change(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Executor addition: the not-owned branch of the ruling.

        A non-root test cannot ``chown``, so the process's effective uid is
        made to differ from the root's owner instead.
        """
        root = tmp_path / "store"
        with _umask(0o000):
            root.mkdir(mode=0o700)
            os.chmod(root, 0o700)
            owner = root.stat().st_uid
            monkeypatch.setattr(os, "geteuid", lambda: owner + 1)
            with pytest.raises(_refusal()) as refused:
                FileArtifactStore(root=root, write_kinds=WriteKinds.declare({}))
        assert _mode(root) == 0o700
        assert str(root) in str(refused.value)

    def test_a_pre_existing_owner_only_root_constructs_normally(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "store"
        with _umask(0o000):
            root.mkdir(mode=0o700)
            os.chmod(root, 0o700)
            store = FileArtifactStore(root=root, write_kinds=WriteKinds.declare({}))
            address = _put_one(store)
        assert _mode(root) == 0o700
        assert _mode(root / address) == 0o600


def test_the_staging_file_is_never_wider_than_its_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ``.partial`` staging file is ``0o600`` at the moment it is moved.

    Spied at ``Path.replace``: the mode the staging file holds when it is
    renamed onto its target is the mode the target inherits.
    """
    seen: dict[str, int] = {}
    original = Path.replace

    def spy(self: Path, target: str | os.PathLike[str]) -> Path:
        if self.name.endswith(".partial"):
            seen[self.name] = _mode(self)
        return original(self, target)

    monkeypatch.setattr(Path, "replace", spy)
    with _umask(0o000):
        store = FileArtifactStore(
            root=tmp_path / "x" / "store", write_kinds=WriteKinds.declare({})
        )
        address = _put_one(store)
    # Non-vacuity: both staging writes (content and index) were observed.
    assert any(name.startswith(f".{address}.") for name in seen), seen
    assert any(name.startswith(f"{INDEX_FILENAME}.") for name in seen), seen
    wide = {n: oct(m) for n, m in seen.items() if m != 0o600}
    assert wide == {}, f"staging files wider than 0o600 at replace: {wide}"
    assert _mode(store.root / address) == 0o600


def test_modes_are_exact_under_a_umask_that_strips_owner_bits(tmp_path: Path) -> None:
    """Executor addition: the modes are SET, not requested and masked."""
    root = tmp_path / "a" / "b" / "store"
    with _umask(0o277):
        store = FileArtifactStore(root=root, write_kinds=WriteKinds.declare({}))
        address = _put_one(store)
    _assert_private_tree(tmp_path / "a", root, address)
