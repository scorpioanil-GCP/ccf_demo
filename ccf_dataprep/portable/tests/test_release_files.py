#!/usr/bin/env python3
"""Every file the release tells someone to run must actually ship.

    uv run --with pytest pytest portable/tests/test_release_files.py

`package_release.sh` checks that the files exist on db1, but only after a
dump. This catches the earlier mistake, at commit time: a file written into
`portable/bundle/` that `stage_bundle_files.sh` never copies into the bundle.
`verify_bundle.sh` sat in exactly that gap from 2026-09-23 to 2026-10-17. It
was placed by hand once, and a rebuild from scratch would have shipped
without it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUNDLE_SRC = REPO / "portable" / "bundle"
STAGE = REPO / "portable" / "dump" / "stage_bundle_files.sh"
PACKAGE = REPO / "portable" / "dump" / "package_release.sh"

#: Shipped at the bundle root. RELEASE-README.md is NOT here: it goes beside
#: the tar, not inside it.
ROOT_FILES = {"restore.sh", "verify_bundle.sh", "README.md",
              "INSTALL-ubuntu.md", "INSTALL-macos.md", "PURGE.md"}


def _staged_names() -> set[str]:
    text = STAGE.read_text()
    return set(re.findall(r'cp "\$STAGED/bundle/([^"]+)" "\$BUNDLE/"', text))


def test_every_root_file_is_staged():
    missing = ROOT_FILES - _staged_names()
    assert not missing, f"stage_bundle_files.sh never copies: {sorted(missing)}"


def test_every_staged_file_exists_in_the_repo():
    absent = {n for n in _staged_names() if not (BUNDLE_SRC / n).is_file()}
    assert not absent, f"staged but not in portable/bundle/: {sorted(absent)}"


def test_release_readme_exists_and_names_the_one_command():
    text = (BUNDLE_SRC / "RELEASE-README.md").read_text()
    assert "bash restore.sh" in text


def test_package_checks_for_every_root_file():
    # package_release.sh refuses to package a bundle missing any of these.
    text = PACKAGE.read_text()
    for name in ROOT_FILES:
        assert name in text, f"package_release.sh does not check for {name}"


def test_scripts_parse():
    for script in (BUNDLE_SRC / "restore.sh", PACKAGE, STAGE):
        subprocess.run(["bash", "-n", str(script)], check=True)
