"""Where a frozen-specimen pin measures from (D-IMPL-378 C9).

``D-IMPL-261`` freezes specimens, and each pin diffs its specimen against the
commit its branch left ``main`` at. A local clone has a ``main`` branch. A
hosted branch checkout does not: ``actions/checkout`` fetches every branch as
``refs/remotes/origin/*`` and makes only the checked-out one local, so the bare
``git merge-base HEAD main`` exits 128 there (the D-IMPL-378 CI diagnosis,
§4.2). ``origin/main`` is the same commit under another name.
"""

from __future__ import annotations

import pathlib
import subprocess

#: Tried in order. A ref that resolves is used and never second-guessed.
_CANDIDATES = ("main", "origin/main")


def _resolves(repo_root: pathlib.Path, ref: str) -> bool:
    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
            cwd=repo_root,
            capture_output=True,
        ).returncode
        == 0
    )


def branch_point(repo_root: pathlib.Path) -> str:
    """The merge base of ``HEAD`` with ``main``, or with ``origin/main`` where no
    local ``main`` exists.

    Only a ref that does not resolve moves the lookup on. A ``main`` that
    resolves but shares no history with ``HEAD`` raises
    ``subprocess.CalledProcessError`` rather than trying ``origin/main``: a pin
    must never pass by measuring from the wrong place. When neither resolves,
    ``AssertionError`` names both.
    """
    for ref in _CANDIDATES:
        if _resolves(repo_root, ref):
            return subprocess.run(
                ["git", "merge-base", "HEAD", ref],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
    raise AssertionError(
        "neither `main` nor `origin/main` resolves in this checkout, so the frozen"
        " specimen cannot be measured against its branch point"
    )
