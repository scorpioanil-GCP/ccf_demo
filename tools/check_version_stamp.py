"""Fail when the installed ``ccf-sdk`` version stamp cannot be trusted (D-IMPL-357 §D, SEC-029).

The distribution is ``ccf-sdk`` since SEC-027 (``D-IMPL-376`` ruling 4); the import
name stays ``ccf``. ``ccf`` on public PyPI is Microsoft's Confidential Consortium
Framework, so this gate discovers by the distribution name and never by the import
name: with Microsoft's package installed, a lookup by ``ccf`` would certify its
version as the SDK's. ``DISTRIBUTION`` below equals ``[project] name`` and
``src/ccf/graph/registry.py::SDK_DISTRIBUTION``, the runtime reader this gate
certifies. The measurements quoted below were taken under the earlier name ``ccf``;
the renamed metadata directories are ``ccf_sdk.egg-info/`` and
``ccf_sdk-X.Y.Z.dist-info/``, and a stale ``ccf.egg-info/`` from before the rename
is invisible to both readers alike.

Three things this gate refuses, each measured against a real defect in fix
round 1 and each with its own posture below:

1. **Ambiguous metadata.** ``importlib.metadata.version(name)`` returns only
   the FIRST distribution matching ``name`` found while walking ``sys.path``,
   and silently ignores every other one. A stale, git-ignored
   ``ccf.egg-info/`` left in a source tree by an older editable build (or any
   directory holding a second ``ccf`` distribution) can sit ahead of the
   venv's real ``dist-info`` on ``sys.path`` whenever that directory is on
   it — which happens for every ``python -m`` launch and every
   ``PYTHONPATH=.:...`` invocation, both of which this project's own Makefile
   uses. Measured: with such a directory as the current working directory,
   ``ccf.graph.registry._sdk_version()`` returned the stale literal
   ``"0.1.0"`` that SEC-029 exists to retire, while this script — invoked as
   a bare script from a different cwd — read the correct venv stamp. A gate
   that reads a different source than the runtime it certifies is not a
   gate. So this script adds the current working directory to ``sys.path``
   itself (matching the worst-case runtime posture rather than whatever
   posture happens to invoke the script) and uses
   ``importlib.metadata.Distribution.discover`` to see EVERY ``ccf-sdk``
   distribution visible, refusing outright when more than one distinct
   version is found.
2. **An undetected fallback.** ``[tool.setuptools_scm] fallback_version``
   (``pyproject.toml``) exists to say "this checkout could not derive a
   version from git" — a shallow clone, a checkout with tags never fetched,
   a plain directory with no ``.git`` at all. That string is never a state
   in which "nothing to hold" is a true statement, so its presence in the
   installed stamp is refused unconditionally, before any tag logic runs.
3. **A DON'T-KNOW that reads as a PASS.** The original version of this gate
   folded every ``git describe`` failure — no ``.git``, no tags fetched, a
   corrupt repository, a permissions refusal — into the same "HEAD is not an
   exact tag" line used for the ordinary, benign, off-release-tag state of
   every branch and PR run. Those are different claims and must not render
   the same. This version checks, in order: that HEAD is readable at all;
   that at least one ``v*`` tag is visible ANYWHERE in the checkout (its
   absence is exactly the "tags never fetched" shallow-clone symptom,
   measured); and only then whether a ``v*`` tag points at HEAD specifically
   — scoped with ``v[0-9]*`` so this project's own non-release tag
   convention (``phase-N-base``, CLAUDE.md §3.1) is never mistaken for a
   release. Every path prints the installed stamp it read.
4. **Unreadable metadata read as a crash, not a refusal.** A distribution
   directory can exist — matching the discovery glob — while carrying no
   ``METADATA``/``PKG-INFO`` inside it (a botched or partial build).
   ``importlib.metadata`` reports this as a version of ``None`` rather than
   raising, and comparing ``None`` to a real version string during the
   ambiguity check (item 1) raised ``TypeError`` — still a non-zero exit,
   but a bare traceback rather than a named refusal (fix round 2, finding
   4/minor, measured). Checked first and refused by name, listing every
   unreadable path.
"""
from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys

#: The SDK's DISTRIBUTION name (SEC-027) — not the import name ``ccf``.
DISTRIBUTION = "ccf-sdk"

#: Markers `fallback_version` (or a git-describe failure setuptools_scm
#: cannot recover from) writes into the local version segment. Their
#: presence means the version was NOT derived from git, so it is never
#: safe to treat silently as "nothing to hold" (fix round 1, finding 2).
_UNDERIVED_MARKERS = ("no-git-metadata", "no.git.metadata")

#: Only release tags feed this gate's expectation — this project's own
#: `phase-N-base` convention (CLAUDE.md §3.1) is deliberately excluded
#: (fix round 1, finding 3, MEASURED: an unscoped `describe` on a
#: `phase-N-base` HEAD would report that name as the "expected" version).
_RELEASE_TAG_GLOB = "v[0-9]*"

_GIT_TIMEOUT_SECONDS = 10


def _discover_versions() -> dict[str, str | None]:
    """Every ``ccf-sdk`` distribution visible on ``sys.path``, keyed by its own
    metadata directory (its ``*.dist-info`` or ``*.egg-info``), never by the
    distribution's root.

    Adds the current working directory to ``sys.path`` first (if it is not
    already on it) so this check sees exactly what a ``python -m`` launch or
    a ``PYTHONPATH=.:...`` invocation would see — the posture in which the
    egg-info-shadowing defect was measured — rather than the more sheltered
    posture of running this file as a bare script.

    ``Distribution.locate_file("")`` resolves to the distribution's ROOT
    directory, not its metadata directory — measured: a directory holding
    both a stale ``ccf.egg-info/`` and a current ``ccf-X.Y.Z.dist-info/``
    (the exact half-migrated state this gate exists to catch) makes both
    distributions report the SAME ``locate_file("")``, and keying on it
    silently drops one of the two disagreeing versions instead of surfacing
    the disagreement. ``Distribution._path`` — the metadata directory itself
    — is unique per distribution; it is a private attribute of the standard
    library's own ``PathDistribution``, present on every distribution this
    discovery mechanism can find, and used here only as a dictionary key.
    """
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    found: dict[str, str | None] = {}
    for dist in importlib.metadata.Distribution.discover(name=DISTRIBUTION):
        key = str(getattr(dist, "_path", None) or id(dist))
        found[key] = dist.version
    return found


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand, turning "git itself could not run" into a result.

    A missing ``git`` executable, a timeout, or any other launch failure is
    folded into a synthetic non-zero result rather than raising — this is a
    gate, and an uncaught exception here would abort with a traceback
    instead of a refusal.
    """
    try:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, returncode=128, stdout="", stderr=str(exc))


def main() -> int:
    versions = _discover_versions()

    # A metadata directory that exists but carries no `METADATA`/`PKG-INFO`
    # inside it (a botched or partial build) makes `dist.version` `None`,
    # not an exception — measured (fix round 2, finding 4/minor). Left
    # unchecked, `sorted(set(versions.values()))` below raises `TypeError`
    # comparing `None` to `str` the moment a real distribution is ALSO
    # present, which still exits non-zero (fails closed) but as a bare
    # traceback rather than the named refusal every other posture prints —
    # an operator reading it cannot tell "broken environment" from "version
    # mismatch". Named and refused here, before that comparison ever runs.
    unreadable = sorted(path for path, version in versions.items() if version is None)
    if unreadable:
        print(
            f"check_version_stamp: {DISTRIBUTION!r} metadata is present but "
            "unreadable (no version recorded) at:"
        )
        for path in unreadable:
            print(f"  {path}")
        return 1

    distinct = sorted(set(versions.values()))

    if not distinct:
        print(f"check_version_stamp: no {DISTRIBUTION!r} distribution found on sys.path")
        return 1

    if len(distinct) > 1:
        print(
            f"check_version_stamp: ambiguous {DISTRIBUTION!r} metadata — "
            f"{len(versions)} distribution(s) on sys.path disagree:"
        )
        for path, version in sorted(versions.items()):
            print(f"  {version}  {path}")
        return 1

    stamped = distinct[0]

    for marker in _UNDERIVED_MARKERS:
        if marker in stamped:
            print(
                f"check_version_stamp: installed {DISTRIBUTION} is {stamped!r} — "
                f"the {marker!r} marker means the version was NOT derived from "
                "git; refusing rather than treating this as 'nothing to hold'"
            )
            return 1

    verified = _run_git(["rev-parse", "--verify", "HEAD"])
    if verified.returncode != 0:
        print(f"check_version_stamp: cannot read git: {verified.stderr.strip()}")
        return 1

    any_release_tags = _run_git(["tag", "-l", _RELEASE_TAG_GLOB])
    if any_release_tags.returncode != 0:
        print(f"check_version_stamp: cannot list tags: {any_release_tags.stderr.strip()}")
        return 1
    if not any_release_tags.stdout.strip():
        print(
            f"check_version_stamp: no {_RELEASE_TAG_GLOB!r} tags are visible in this "
            "checkout (shallow clone, or tags never fetched) — cannot determine "
            f"release state; installed {DISTRIBUTION} is {stamped}"
        )
        return 1

    at_head = _run_git(["tag", "--points-at", "HEAD", "-l", _RELEASE_TAG_GLOB])
    if at_head.returncode != 0:
        print(f"check_version_stamp: cannot list tags at HEAD: {at_head.stderr.strip()}")
        return 1
    tags_at_head = [line for line in at_head.stdout.splitlines() if line.strip()]

    if not tags_at_head:
        print(
            f"check_version_stamp: HEAD is not an exact {_RELEASE_TAG_GLOB!r} tag; "
            f"installed {DISTRIBUTION} is {stamped} — nothing to hold"
        )
        return 0

    if len(tags_at_head) > 1:
        print(
            "check_version_stamp: HEAD carries more than one release tag "
            f"({', '.join(tags_at_head)}); refusing rather than guessing which one governs"
        )
        return 1

    tag = tags_at_head[0]
    expected = tag.removeprefix("v")
    if stamped != expected:
        print(f"check_version_stamp: tag {tag} but installed {DISTRIBUTION} is {stamped}")
        return 1
    print(f"check_version_stamp: {tag} == {stamped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
