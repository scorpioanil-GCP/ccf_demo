"""SEC-020, D-IMPL-380 ruling 3: a FIFO or socket at a deployment marker's path, with no store beside it, is refused.

Dave, 2026-10-10 05:34 MST (the ``D-IMPL-380`` amendment), verbatim: *"Refuse pipes, sockets, and devices without
opening or replacing them. Do not weaken the page."* The ruling it carries out (``D-IMPL-380`` ruling 3): *"For markers,
preserve my earlier ruling: unreadable markers are refused, not replaced."* — P-1 (b), ruled 2026-10-09 at 20:13 MST.

What was found (panel B-FIFO-MARKER at ``a7e4c2d2``, confirmed): ``src/ccf/deployment/manifest.py::
_replace_stale_deployment_marker`` refused ``"unreadable"`` only for a regular file or a symbolic link whose content
the boot could not read; a FIFO, a socket or a device — which ``_marker_snapshot`` records from ``lstat`` alone,
without opening it — was replaced, as that function's docstring disclosed, while
``public/how-to/security-and-deployment.md`` §4.12 says a marker the boot cannot read "is not replaced at all".

What is asserted, by mechanism: a stale FIFO (and a socket, bound through a relative path so the platform's
socket-path limit does not stop its construction) at the marker's path with no store beside it refuses the plain boot
``DeploymentStoreNotVerified`` with reason ``"unreadable"``, by name and marker path; the same inode, of the same type,
still stands there afterwards; and no store and no staging file is created. A device node cannot be created without
privilege, so it is not constructed here; the refusal is decided from the file type alone, as for these two. Every
domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import os
import pathlib
import socket
import stat
from collections.abc import Callable

import pytest

from tests.products import test_deployment_marker_serialized_and_stale_refused as sr
from tests.products import test_question_store_empty_at_boot_and_held_through_use as p4e


def _fifo(marker: pathlib.Path) -> object:
    os.mkfifo(marker)
    return None


def _socket(marker: pathlib.Path) -> object:
    bound = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    previous = os.getcwd()
    os.chdir(marker.parent)
    try:
        bound.bind(marker.name)
    finally:
        os.chdir(previous)
    return bound


#: Each special file a writer outside the SDK can leave at the marker's path, and how to make it.
SPECIAL: dict[str, tuple[Callable[[pathlib.Path], object], Callable[[int], bool]]] = {
    "a FIFO": (_fifo, stat.S_ISFIFO),
    "a socket": (_socket, stat.S_ISSOCK),
}


@pytest.mark.parametrize("kind", sorted(SPECIAL))
def test_380_3_a_special_file_at_the_marker_path_with_no_store_is_refused_unreadable_and_left(
    tmp_path: pathlib.Path, kind: str
) -> None:
    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "stale" / sr._STORE
    target.parent.mkdir()
    marker = sr._marker(target)
    make, is_kind = SPECIAL[kind]
    held = make(marker)
    try:
        looked_at = os.lstat(marker)
        assert is_kind(looked_at.st_mode) and not target.exists(), f"[{kind}] the case was not constructed"

        outcome = sr._boot(manifest, registry, target)

        sr._assert_refused_not_verified(outcome, marker=marker, reason="unreadable", case=f"{kind}, no store")
        after = os.lstat(marker)
        assert (after.st_dev, after.st_ino) == (looked_at.st_dev, looked_at.st_ino) and is_kind(after.st_mode), (
            f"[{kind}] the refused boot replaced the special file at the marker's path"
        )
        assert not target.exists(), f"[{kind}] a refused boot created a store at the path"
        assert not list(marker.parent.glob(f"{marker.name}.replacing-*")), f"[{kind}] the refused boot left a staging file"
    finally:
        if isinstance(held, socket.socket):
            held.close()


# --- D-IMPL-380 second round, item 1 (ruling 1 (a)): beside a store, the marker's type is checked before any open. ---
#
# Dave, 2026-10-10 07:39 MST (the ``D-IMPL-380`` amendment), verbatim: *"`lstat` first in `_read_deployment_marker`, so
# both beside-store reads and the boot's own re-reads are covered. The test counts opens and must see zero. State the
# swap race."* What was found (Fable seat 2, F2-1, at ``ef5d27a4``): beside an existing store,
# ``_mark_deployment_store`` (a writing boot) and ``_store_creation`` (a read-only boot) read the marker through
# ``_read_deployment_marker``, which opened the path and only then checked the descriptor's type: a FIFO there was
# opened once, then refused. What is asserted, by mechanism: ``os.open`` is wrapped and every call whose target is the
# special file's inode is counted; it must be zero, the outcome is what it was (the writing boot refused
# ``"unreadable"``; the read-only boot not vouched for, ``store_creation`` ``"unmarked"``), and the same inode, of the
# same type, still stands at the path.

BOOTS = ("a writing boot", "a read-only boot")


def _counting_opens_of(monkeypatch: pytest.MonkeyPatch, marker: pathlib.Path) -> list[int]:
    """Wrap ``os.open`` so every call whose target is ``marker``'s file (device and inode, by ``lstat``) is counted."""
    looked = os.lstat(marker)
    identity = (looked.st_dev, looked.st_ino)
    real_open = os.open
    counted = [0]

    def counting_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        if isinstance(path, (str, bytes, os.PathLike)) and kwargs.get("dir_fd") is None:
            try:
                status = os.lstat(path)
            except OSError:
                status = None
            if status is not None and (status.st_dev, status.st_ino) == identity:
                counted[0] += 1
        return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "open", counting_open)
    return counted


@pytest.mark.parametrize("boot", BOOTS)
@pytest.mark.parametrize("kind", sorted(SPECIAL))
def test_380b_1_a_special_file_at_the_marker_path_beside_a_store_is_never_opened_and_the_outcome_is_unchanged(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, kind: str, boot: str
) -> None:
    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "beside" / sr._STORE
    target.parent.mkdir()
    marker = sr._marker(target)
    booted: object = sr._boot(manifest, registry, target)
    assert not isinstance(booted, Exception), f"[{kind}, {boot}] the case was not constructed: {booted!r}"
    booted.handle.close()  # type: ignore[attr-defined]
    assert target.exists() and sr._state(marker) == "verified", f"[{kind}, {boot}] the case was not constructed"
    marker.unlink()
    make, is_kind = SPECIAL[kind]
    held = make(marker)
    try:
        looked_at = os.lstat(marker)
        assert is_kind(looked_at.st_mode), f"[{kind}, {boot}] the case was not constructed"
        counted = _counting_opens_of(monkeypatch, marker)

        outcome = sr._boot(manifest, registry, target, read_only=(boot == "a read-only boot"))

        monkeypatch.undo()
        try:
            assert counted[0] == 0, (
                f"[{kind}, {boot}] {kind} at the marker's path beside a store was opened {counted[0]} time(s); its"
                " type must be checked from lstat before any open, so it is opened 0 times"
            )
        finally:
            if not isinstance(outcome, Exception) and boot == "a read-only boot":
                creation = outcome.store_creation
                outcome.handle.close()
                outcome = creation
        if boot == "a writing boot":
            sr._assert_refused_not_verified(outcome, marker=marker, reason="unreadable", case=f"{kind}, beside a store")
        else:
            assert outcome == "unmarked", (
                f"[{kind}, {boot}] a read-only boot beside a store whose marker is a {kind} must boot with"
                f" store_creation 'unmarked', as before; got {outcome!r}"
            )
        after = os.lstat(marker)
        assert (after.st_dev, after.st_ino) == (looked_at.st_dev, looked_at.st_ino) and is_kind(after.st_mode), (
            f"[{kind}, {boot}] the boot replaced the special file at the marker's path"
        )
        assert target.exists(), f"[{kind}, {boot}] the boot removed the store"
    finally:
        if isinstance(held, socket.socket):
            held.close()
