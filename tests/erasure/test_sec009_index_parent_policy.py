"""SEC-009 fix round 4, re-review M-b — the index's directory follows the artifact store's root policy.

The file store creates every missing directory, intermediate parents included,
owner-only (``0o700``), and refuses a pre-existing one with ANY mode bit
outside ``0o700`` — special bits included — or another owner (SEC-014). The
erasure index's parent is held to the same mechanism.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from tests.erasure import harness as h


def test_every_directory_the_index_creates_is_owner_only(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir(mode=0o700)
    base.chmod(0o700)
    h.erasure("FileErasureIndex")(base / "a" / "b" / "c" / ".erasure-index.jsonl")
    for created in (base / "a", base / "a" / "b", base / "a" / "b" / "c"):
        assert stat.S_IMODE(created.stat().st_mode) == 0o700, (created, oct(created.stat().st_mode))


def test_a_pre_existing_parent_with_a_special_bit_is_refused_by_name(tmp_path: Path) -> None:
    sticky = tmp_path / "sticky"
    sticky.mkdir()
    sticky.chmod(0o1700)
    with pytest.raises(h.erasure("ErasureIndexInsecure")):
        h.erasure("FileErasureIndex")(sticky / ".erasure-index.jsonl")
