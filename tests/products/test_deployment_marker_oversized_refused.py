# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-020, D-IMPL-380 ruling 4 (a): an oversized deployment marker is refused ``"oversized"``, and never read whole.

Dave, 2026-10-10 05:34 MST (the ``D-IMPL-380`` amendment), verbatim: *"Cap the read at the longest marker the SDK
writes. Refuse "oversized" by name. Do not replace the file. Count the bytes actually read."* The ruling it carries
out (``D-IMPL-380`` ruling 4 (a)): *"Bound marker reads to the documented format’s maximum size. Refuse oversized
markers by name. Test that boot does not read the entire oversized file."*

What was found (Fable F-3 / panel B-MARKER-SIZE at ``a7e4c2d2``; measured by the builder: a sparse 1 GiB marker in
0.49 s, 4 GiB in 1.97 s, under the store-creation lock): ``src/ccf/deployment/manifest.py::_marker_snapshot`` hashed
a regular-file marker to its full ``st_size``, while ``_read_deployment_marker`` already bounded its own read to the
longest marker the SDK writes.

What is asserted, by mechanism, for a sparse 1 GiB regular file at the marker's path — with no store beside it, and
separately beside a store a plain boot created and verified:

1. the plain boot is refused ``DeploymentStoreNotVerified`` with reason ``"oversized"``, by name and marker path;
2. the bytes read from that file, counted by wrapping ``os.read`` for any descriptor open on it, are at most the
   length of the longest marker the SDK writes plus one;
3. the file is untouched (the same device, inode, size and modification time), and no store is created where none
   stood.

The longest marker is computed here from the marker's documented form (its first line, ``state: verified``, and a
32-hex-digit boot token), not from an SDK helper, so a tree without the bound fails on its behavior, never on an
import. Every domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import os
import pathlib
from typing import Any

import pytest

from tests.products import test_deployment_marker_serialized_and_stale_refused as sr
from tests.products import test_question_store_empty_at_boot_and_held_through_use as p4e

#: The longest deployment marker the SDK writes, in bytes: its first line, then ``state: verified`` and a token.
LONGEST = len(f"{sr._MARKER_HEAD}state: verified\nboot: {'0' * 32}\n".encode())

#: The sparse size of the oversized marker.
GIB = 1 << 30

SITES = ("no store beside it", "beside a store")


def _fingerprint(path: pathlib.Path) -> tuple[int, int, int, int]:
    status = os.lstat(path)
    return status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns


def _counting_reads_of(monkeypatch: pytest.MonkeyPatch, marker: pathlib.Path) -> list[int]:
    """Wrap ``os.read`` so every byte read through a descriptor open on ``marker``'s file is counted."""
    looked = os.lstat(marker)
    identity = (looked.st_dev, looked.st_ino)
    real_read = os.read
    counted = [0]

    def counting_read(descriptor: int, size: int) -> bytes:
        data = real_read(descriptor, size)
        try:
            status = os.fstat(descriptor)
        except OSError:
            return data
        if (status.st_dev, status.st_ino) == identity:
            counted[0] += len(data)
        return data

    monkeypatch.setattr(os, "read", counting_read)
    return counted


@pytest.mark.parametrize("site", SITES)
def test_380_4_a_sparse_1_gib_marker_is_refused_oversized_read_at_most_the_bound_and_left(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, site: str
) -> None:
    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "oversized" / sr._STORE
    target.parent.mkdir()
    marker = sr._marker(target)
    if site == "beside a store":
        booted: Any = sr._boot(manifest, registry, target)
        assert not isinstance(booted, Exception), f"[{site}] the case was not constructed: {booted!r}"
        booted.handle.close()
        assert target.exists() and sr._state(marker) == "verified", f"[{site}] the case was not constructed"
    else:
        marker.touch()
    os.truncate(marker, GIB)
    before = _fingerprint(marker)
    assert before[2] == GIB and target.exists() == (site == "beside a store"), f"[{site}] the case was not constructed"
    counted = _counting_reads_of(monkeypatch, marker)

    outcome = sr._boot(manifest, registry, target)

    monkeypatch.undo()
    assert counted[0] <= LONGEST + 1, (
        f"[{site}] the boot read {counted[0]} bytes of a {GIB}-byte marker; the longest marker the SDK writes is"
        f" {LONGEST} bytes, so at most {LONGEST + 1} may be read"
    )
    sr._assert_refused_not_verified(outcome, marker=marker, reason="oversized", case=f"{site}, 1 GiB")
    assert _fingerprint(marker) == before, f"[{site}] the refused boot changed or replaced the oversized marker"
    assert target.exists() == (site == "beside a store"), f"[{site}] the refused boot created or removed a store"
    assert not list(marker.parent.glob(f"{marker.name}.replacing-*")), f"[{site}] the refused boot left a staging file"
