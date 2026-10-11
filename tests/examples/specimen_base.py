"""Where a frozen-specimen pin measures from (D-IMPL-378 C9).

``D-IMPL-261`` freezes specimens, and each pin diffs its specimen against the
commit its branch left ``main`` at. A local clone has a ``main`` branch. A
hosted branch checkout does not: ``actions/checkout`` fetches every branch as
``refs/remotes/origin/*`` and makes only the checked-out one local, so the bare
``git merge-base HEAD main`` exits 128 there (the D-IMPL-378 CI diagnosis,
§4.2). ``origin/main`` is the same commit under another name.
"""

from __future__ import annotations

import hashlib
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


# ---------------------------------------------------------------------------
# AMENDED 2026-10-11 — the frozen specimens' pins measure CONTENT, not a branch
# point (Dave, ruling 3 of 2026-10-11 16:23 MST: "Update affected specimen
# checks explicitly. A check passing merely because the changes have reached
# main is not evidence that the repaired example works.").
#
# The compatibility repairs ruling 3 authorized touch named files of the frozen
# specimens. A pin that diffs the specimen against `merge-base HEAD main` reads
# red on the repair's branch and green once the repair reaches main — a check
# whose verdict is a fact about the branch, not about the specimen. So each pin
# now names the files the amendment changed, and asserts that EVERY OTHER file
# of the specimen is byte-for-byte what it was at the freeze: a pinned digest
# over the tracked files outside the named set, computed from their bytes on
# disk. It reads the same on any branch, in any clone, before and after a
# merge; it goes red when an unamended file changes, when a file is added or
# removed, or when an amended file is no longer where the pin names it.
# ---------------------------------------------------------------------------



def tracked_files(repo_root: pathlib.Path, specimen: pathlib.Path) -> tuple[str, ...]:
    """Every file git tracks under ``specimen``, relative to it, sorted.

    Tracked rather than walked, so a run's scratch output or a `__pycache__`
    left in the tree never enters the digest. ``git ls-files`` reads the index,
    not history, so it answers identically in a shallow or hosted checkout.
    """
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--", str(specimen.relative_to(repo_root))],
        cwd=repo_root,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    prefix = specimen.relative_to(repo_root).as_posix() + "/"
    return tuple(
        sorted(path[len(prefix):] for path in listed.split("\0") if path)
    )


def frozen_digest(
    repo_root: pathlib.Path, specimen: pathlib.Path, *, amended: frozenset[str]
) -> str:
    """SHA-256 over the specimen's tracked files OUTSIDE ``amended``.

    Each file contributes its relative path and the SHA-256 of its bytes, in
    sorted path order, so an added, removed or renamed file moves the digest as
    surely as an edited one.

    Raises:
        AssertionError: a file named in ``amended`` is not tracked under the
            specimen — the pin names a file the amendment did not leave there.
    """
    files = tracked_files(repo_root, specimen)
    missing = sorted(amended - set(files))
    assert not missing, (
        f"the amendment names {missing}, which {specimen.name} does not track;"
        " a pin that names a file that is not there asserts nothing about it"
    )
    digest = hashlib.sha256()
    for relative in files:
        if relative in amended:
            continue
        body = (specimen / relative).read_bytes()
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(body).hexdigest().encode("ascii") + b"\n")
    return digest.hexdigest()
