# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A frozen specimen, pinned BY CONTENT, with its authorized amendments named.

Dave, 2026-10-11 16:23 MST, ruling 3 (`docs/DECISIONS.md`, "Tuesday delivery —
RULED"): *"Update affected specimen checks explicitly. A check passing merely
because the changes have reached main is not evidence that the repaired example
works."* The specimen gates (`CSCC-G16`, `CXRC-G17`) diffed the specimen against
the branch point, so they read red on any branch carrying an authorized
compatibility repair and green again once it reached `main` — measuring where a
commit was rather than what the specimen holds.

The replacement states what changed and asserts everything else frozen by its
bytes: every file NOT named as amended must hash to the value it held when the
specimen was frozen (the manifest, recorded from `a280082e`, the Tuesday
baseline, where both specimens were byte-identical to their freeze), the
amended set is exactly the named set (an unnamed edit to an amended file is
caught by the amendment log's review, an edit to any other file by its hash),
and no file was added or removed. Independent of git history and of where
`main` points.
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess

from tests.examples.specimen_base import is_documentation


def tracked_files(repo_root: pathlib.Path, specimen: pathlib.Path) -> set[str]:
    """Every file git tracks under ``specimen``, relative to it."""
    listing = subprocess.run(
        ["git", "ls-files", "--", str(specimen.relative_to(repo_root))],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout.split()
    prefix = str(specimen.relative_to(repo_root)) + "/"
    return {path[len(prefix):] for path in listing}


def frozen_by_content_violations(
    repo_root: pathlib.Path,
    specimen: pathlib.Path,
    *,
    frozen: dict[str, str],
    amended: dict[str, str],
) -> list[str]:
    """What breaks the freeze, as sentences; empty when the specimen holds.

    Documentation (``specimen_base.is_documentation``) is outside the freeze:
    correcting, adding or removing a Markdown file is never a violation, and a
    documentation entry in ``frozen`` is not checked (`D-IMPL-386`).

    Args:
        frozen: relative path → sha256 of the bytes it must still hold.
        amended: relative path → why it was amended (the dated amendment).
    """
    problems: list[str] = []
    overlap = set(frozen) & set(amended)
    if overlap:
        problems.append(f"a file is both frozen and amended: {sorted(overlap)}")
    present = {path for path in tracked_files(repo_root, specimen) if not is_documentation(path)}
    declared = {path for path in set(frozen) | set(amended) if not is_documentation(path)}
    if present - declared:
        problems.append(f"files added to the frozen specimen: {sorted(present - declared)}")
    if declared - present:
        problems.append(f"files removed from the frozen specimen: {sorted(declared - present)}")
    for relative, expected in sorted(frozen.items()):
        if is_documentation(relative):
            continue
        path = specimen / relative
        if not path.is_file():
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            problems.append(f"{relative} changed (sha256 {actual}, frozen {expected})")
    return problems
