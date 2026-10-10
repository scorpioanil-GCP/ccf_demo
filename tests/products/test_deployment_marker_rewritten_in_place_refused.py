"""SEC-020, D-IMPL-378 decision 17 (b): a stale marker rewritten in place after the boot's look is refused, and left.

Dave, 2026-10-09 16:38 MST, adopting Grok's recommendation (recorded on ``main`` @ ``c470416f``), verbatim:
*"(b) Compare the marker’s bytes."* The option he ruled, lane ``378j-boot``'s P-2 (b): *"Also compare the marker's
bytes (and a symbolic link's target), read at the look, immediately before the rename. This catches every rewrite or
recreation that changes the text. A change made after the re-check remains, as does a rewrite to identical bytes,
which is harmless."* SEC-020 stays OPEN: these tests measure what the SDK refuses, and nothing here closes it.

What was measured before, on ``83af5650`` (lane ``378j-bootlock``'s base): a plain boot at a path holding a stale
deployment marker and no store replaces that marker with its own (repair 1.2, built as P-1 (B)), after checking,
immediately before the rename, that the marker is still the file its look found, by device and inode only. A writer
outside the SDK that rewrote the stale marker IN PLACE between the look and the replacement kept the file's device and
inode, so the boot replaced it, booted ``"verified"``, and the outside writer's text was lost (lane ``378j-boot``'s
``probe_claimed_window.py``; this module's first test, red on that tree).

What is asserted, by mechanism:

1. **A stale marker rewritten in place, to other bytes, between the boot's look and its replacement is refused**
   ``DeploymentStoreNotVerified`` with reason ``claimed``, by name and marker path, and left exactly as the outside
   writer left it (the same file, the same bytes); no store and no staging file is created at the path.
2. **So is one rewritten in place to other bytes of the SAME LENGTH.** The comparison is of the bytes, not of the
   size: a check that compared only the length passed case 1, whose text has another length, and fails here.
3. **The disclosed residual, pinned: a rewrite in place to the SAME bytes is not told apart.** The boot replaces that
   marker like any stale one and verifies the store it creates with its one read, so it serves nothing it did not
   read. A tree that refused every replacement after a write would fail here, so this test is also the control that
   the first one is not passed by refusing everything.

Injection, the least invasive hook, as in
``tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_b_a_stale_marker_replaced_by_another_file_after_the_look_is_refused_as_claimed_and_left``:
the module's call into ``_replace_stale_deployment_marker`` is wrapped so that, when the boot makes it, an outside
writer first rewrites the marker in place (truncated and written through the same file, then synced), and the real
function then runs with what the boot's look found, passed through unchanged. Nothing the SDK computes is changed; only
the outside write's moment is chosen, inside the window between the look and the replacement's re-check, where a
writer outside the SDK's boots would land. Every domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import os
import pathlib
from typing import Any

import pytest

from tests.products import test_deployment_marker_serialized_and_stale_refused as sr
from tests.products import test_plain_boot_creating_its_store_finds_it_empty as tp
from tests.products import test_question_store_empty_at_boot_and_held_through_use as p4e

#: The stale states a deployment marker can be left in with no store beside it, as regular files this process can
#: read and rewrite (a symbolic link cannot be rewritten in place; a ``pending`` marker needs a killed boot, which the
#: other states' tests already construct).
REWRITABLE_STALE = (
    "verified, its store deleted",
    "the single-line marker of fe25536c",
    "text that is not the SDK's",
)


def _identity(path: pathlib.Path) -> tuple[int, int]:
    """The device and inode of what stands at ``path``, not following a symbolic link."""
    status = os.lstat(path)
    return status.st_dev, status.st_ino


def _rewrite_in_place(marker: pathlib.Path, text: bytes) -> None:
    """Rewrite ``marker`` in place: the same file (device and inode), its bytes replaced and synced."""
    with open(marker, "r+b") as rewritten:
        rewritten.truncate(0)
        rewritten.write(text)
        rewritten.flush()
        os.fsync(rewritten.fileno())


def _rewritten_after_the_look(
    monkeypatch: pytest.MonkeyPatch, marker: pathlib.Path, text: bytes
) -> list[tuple[tuple[int, int], tuple[int, int], bytes]]:
    """Make an outside writer rewrite ``marker`` in place when the boot reaches its replacement; what each write left."""
    import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

    real_replace = manifest_module._replace_stale_deployment_marker
    rewrites: list[tuple[tuple[int, int], tuple[int, int], bytes]] = []

    def an_outside_writer_rewrites_the_marker_in_place_first(path: pathlib.Path, found: Any) -> Any:
        before = _identity(marker)
        _rewrite_in_place(marker, text)
        rewrites.append((before, _identity(marker), marker.read_bytes()))
        return real_replace(path, found)

    monkeypatch.setattr(
        manifest_module, "_replace_stale_deployment_marker", an_outside_writer_rewrites_the_marker_in_place_first
    )
    return rewrites


@pytest.mark.parametrize("state", REWRITABLE_STALE)
def test_17_b_a_stale_marker_rewritten_in_place_after_the_look_is_refused_as_claimed_and_left(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """The same file, other bytes, after the boot looked: refused ``claimed``, and the outside writer's text kept.

    Red on ``83af5650``: the device-and-inode re-check passed, the boot replaced the rewritten marker by its own and
    booted ``"verified"``.
    """
    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "stale" / sr._STORE
    target.parent.mkdir()
    sr._stale_with_no_store(tmp_path, manifest, registry, target, state)
    marker = sr._marker(target)
    looked_at = _identity(marker)
    foreign = b"another writer's text, written in place after the boot looked\n"
    assert marker.read_bytes() != foreign, f"[{state}] the stale marker already holds the outside writer's text"
    rewrites = _rewritten_after_the_look(monkeypatch, marker, foreign)
    outcome = sr._boot(manifest, registry, target)
    assert len(rewrites) == 1, f"[{state}] the boot never reached the replacement; the case was not constructed"
    before, after, now = rewrites[0]
    assert before == after == looked_at and now == foreign, (
        f"[{state}] the outside write did not keep the file the boot looked at, or did not change its bytes; the case"
        " was not constructed"
    )
    sr._assert_refused_not_verified(
        outcome, marker=marker, reason="claimed", case=f"{state}, rewritten in place after the look"
    )
    assert _identity(marker) == looked_at and marker.read_bytes() == foreign, (
        f"[{state}] the refused boot replaced or changed the marker the outside writer rewrote"
    )
    assert not target.exists(), f"[{state}] a refused boot created a store at the path"
    assert not list(marker.parent.glob(f"{marker.name}.replacing-*")), f"[{state}] the refused boot left its staging file"


@pytest.mark.parametrize("state", REWRITABLE_STALE)
def test_17_b_a_stale_marker_rewritten_in_place_to_other_bytes_of_the_same_length_is_refused_as_claimed_and_left(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """The same file, the same length, every byte changed, after the boot looked: refused ``claimed``, and left.

    The re-check compares the marker's bytes, so a rewrite that keeps the length is told apart too. The coordinator's
    severing on ``150da08b`` (the content digest taken over the file's size instead of its bytes) left the first test
    green, because that rewrite changes the length; under it this one fails.
    """
    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "stale" / sr._STORE
    target.parent.mkdir()
    sr._stale_with_no_store(tmp_path, manifest, registry, target, state)
    marker = sr._marker(target)
    looked_at = _identity(marker)
    original = marker.read_bytes()
    same_length = bytes((byte + 1) % 256 for byte in original)  # every byte changed, the length kept
    assert len(same_length) == len(original) and all(a != b for a, b in zip(same_length, original)), (
        f"[{state}] the outside writer's bytes are not other bytes of the same length; the case was not constructed"
    )
    rewrites = _rewritten_after_the_look(monkeypatch, marker, same_length)
    outcome = sr._boot(manifest, registry, target)
    assert len(rewrites) == 1, f"[{state}] the boot never reached the replacement; the case was not constructed"
    before, after, now = rewrites[0]
    assert before == after == looked_at and now == same_length, (
        f"[{state}] the outside write did not keep the file the boot looked at, or did not write the same-length bytes;"
        " the case was not constructed"
    )
    sr._assert_refused_not_verified(
        outcome, marker=marker, reason="claimed", case=f"{state}, rewritten in place to other bytes of the same length"
    )
    assert _identity(marker) == looked_at and marker.read_bytes() == same_length, (
        f"[{state}] the refused boot replaced or changed the marker the outside writer rewrote"
    )
    assert not target.exists(), f"[{state}] a refused boot created a store at the path"
    assert not list(marker.parent.glob(f"{marker.name}.replacing-*")), f"[{state}] the refused boot left its staging file"


@pytest.mark.parametrize("state", REWRITABLE_STALE)
def test_17_b_measure_a_stale_marker_rewritten_in_place_to_the_same_bytes_is_replaced_and_the_new_store_verified(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """The disclosed residual: a rewrite to identical bytes changes nothing a boot reads, and is not told apart.

    The boot replaces the marker like any stale one, reads the store it creates once, and marks it ``verified``. A
    measurement of behavior as it stands (green before and after decision 17 (b)); it pins what the words say remains.
    """
    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "stale" / sr._STORE
    target.parent.mkdir()
    sr._stale_with_no_store(tmp_path, manifest, registry, target, state)
    marker = sr._marker(target)
    looked_at = _identity(marker)
    same = marker.read_bytes()
    stale_token = sr._token(marker)
    rewrites = _rewritten_after_the_look(monkeypatch, marker, same)
    events: list[tuple[str, ...]] = []
    p4e._record_reads(monkeypatch, events)
    outcome = sr._boot(manifest, registry, target)
    assert len(rewrites) == 1, f"[{state}] the boot never reached the replacement; the case was not constructed"
    before, after, now = rewrites[0]
    assert before == after == looked_at and now == same, (
        f"[{state}] the outside write did not keep the file and its bytes; the case was not constructed"
    )
    if isinstance(outcome, Exception):
        pytest.fail(
            f"[{state}] a stale marker rewritten to the same bytes was refused ({outcome!r}); nothing a boot reads"
            " changed, so the boot replaces it and verifies the store it creates"
        )
    try:
        reads = tp._latest_reads(events)
        creation, held = outcome.store_creation, p4e._held(outcome)
    finally:
        outcome.handle.close()
    assert reads == 1, f"[{state}] the boot that created the store must read it exactly once: {reads}"
    assert creation == "verified" and held == 0, f"[{state}] store_creation {creation!r}, {held} entities held"
    assert sr._state(marker) == "verified", f"[{state}] the marker must now be this boot's own, verified"
    assert sr._token(marker) not in (None, stale_token), f"[{state}] the stale marker was not replaced by this boot's own"
