"""Fail when HEAD is an exact v* tag and the installed stamp is not that tag's (D-IMPL-357 §D)."""
from __future__ import annotations

import importlib.metadata
import subprocess
import sys

DISTRIBUTION = "ccf"


def main() -> int:
    described = subprocess.run(
        ["git", "describe", "--tags", "--exact-match"], capture_output=True, text=True
    )
    if described.returncode != 0:
        print("check_version_stamp: HEAD is not an exact tag; nothing to hold")
        return 0
    tag = described.stdout.strip()
    stamped = importlib.metadata.version(DISTRIBUTION)
    if stamped != tag.lstrip("v"):
        print(f"check_version_stamp: tag {tag} but installed {DISTRIBUTION} is {stamped}")
        return 1
    print(f"check_version_stamp: {tag} == {stamped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
