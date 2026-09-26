"""D-IMPL-357 §D (SEC-029): the version the replay record carries is the tag's.

Fix round 1, finding 5 (Opus + codex + cursor + Fable, all four sources):
`test_the_installed_version_is_not_the_stale_literal_and_is_git_derived`'s
three original assertions (`!= "0.1.0"`, a `^\\d+\\.\\d+\\.\\d+` shape, and
`_sdk_version() == version`) all PASS for a reintroduced static
`version = "0.2.0"` in `pyproject.toml`, AND for `0.0.0+no-git-metadata` —
the fallback whose entire purpose is to announce that the version was NOT
derived from git. A test named "...is_git_derived" must fail on both.
Rewritten below to assert the derivation itself (HEAD's own identity inside
the local version segment, off an exact tag) rather than the shape alone,
and to assert `pyproject.toml` still declares `version` dynamic.

Note (controller, fix round 1): this suite is RED under
`/home/parkave/ccf_code/.venv` — that shared venv still holds a static
`ccf-0.1.0.dist-info` and no `setuptools_scm`, installed before this task's
`pyproject.toml` change. That is the shared venv being stale, not this test
being wrong; the join reinstalls it once. This suite is not weakened to
accommodate that — it is run here, and is asserted GREEN, only against this
lane's private `.venv-d`.
"""
import importlib.metadata
import os
import re
import shlex
import subprocess
import tomllib
from pathlib import Path

import pytest

from ccf.graph.registry import SDK_DISTRIBUTION, _sdk_version

_GIT_TIMEOUT_SECONDS = 10
_REPO_ROOT = Path(__file__).resolve().parent.parent

#: Only release tags count (fix round 1, finding 3): this project also cuts
#: `phase-N-base` tags (CLAUDE.md §3.1), which must never be mistaken for a
#: release either by this test or by the gate it exercises.
_RELEASE_TAG_MATCH = ["--match", "v[0-9]*"]

#: Deterministic identity for the throwaway repos this module builds by
#: hand — no reliance on this host's global git config.
_GIT_IDENTITY_ENV = {
    "GIT_AUTHOR_NAME": "version-stamp-test",
    "GIT_AUTHOR_EMAIL": "version-stamp-test@example.invalid",
    "GIT_COMMITTER_NAME": "version-stamp-test",
    "GIT_COMMITTER_EMAIL": "version-stamp-test@example.invalid",
}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command building a scenario repo, raising on failure."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
        env={**os.environ, **_GIT_IDENTITY_ENV},
    )


def test_the_installed_version_is_not_the_stale_literal_and_is_git_derived() -> None:
    version = importlib.metadata.version(SDK_DISTRIBUTION)
    assert version != "0.1.0"
    assert re.match(r"^\d+\.\d+\.\d+", version), version
    assert _sdk_version() == version
    # Neither marker a fallback (`[tool.setuptools_scm] fallback_version`,
    # or a git-describe failure setuptools_scm cannot recover from) writes
    # into the local segment — its presence means NOT derived, whatever the
    # shape looks like (finding 5).
    assert "no-git-metadata" not in version
    assert "no.git.metadata" not in version

    exact = subprocess.run(
        ["git", "describe", "--tags", "--exact-match", *_RELEASE_TAG_MATCH],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    if exact.returncode == 0:
        # HEAD happens to be an exact release tag (this suite running as
        # part of a release qualification, say): there is no local segment
        # to check here — `test_on_an_exact_tag_the_stamp_equals_the_tag`
        # below is the assertion that matters in this state.
        return

    # The ordinary, off-tag state: the local version segment must carry
    # HEAD's own identity, or this is a static or fallback string that only
    # happens to be shaped like a version (finding 5). `setuptools_scm`
    # renders `X.Y.Z.devN+g<sha>[.dYYYYMMDD if dirty]`.
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
        check=True,
    ).stdout.strip()
    local_sha = re.search(r"\+g([0-9a-f]+)", version)
    assert local_sha, f"no +g<sha> local segment in {version!r}"
    # Round 2, finding 3's second addition: without a floor, a degenerate
    # single-hex-digit node (`+g1`) could satisfy `startswith` by a roughly
    # 1-in-16 coincidence rather than by actually identifying HEAD. `git`'s
    # own historical minimum abbreviation is 7; `--abbrev=40` plus
    # `vcs_versioning`'s fixed 9-hex truncation (see `pyproject.toml`'s
    # `git_describe_command` comment) should always clear this by two.
    assert len(local_sha.group(1)) >= 7, f"node too short to be meaningful: {version!r}"
    assert head_sha.startswith(local_sha.group(1)), (version, head_sha)


def test_on_an_exact_tag_the_stamp_equals_the_tag() -> None:
    described = subprocess.run(
        ["git", "describe", "--tags", "--exact-match", *_RELEASE_TAG_MATCH],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    if described.returncode != 0:
        pytest.skip("HEAD is not an exact release tag; the gate binds at release only")
    tag = described.stdout.strip()
    # `removeprefix`, not `lstrip` (finding 3): `lstrip("v")` strips every
    # leading character IN THE SET {"v"}, not the two-character prefix — a
    # tag like `v11.0.0` would lose both leading digits' worth of nothing,
    # but the general defect is `lstrip` operating on a character set at
    # all, which is the wrong primitive for a fixed-prefix strip.
    assert importlib.metadata.version(SDK_DISTRIBUTION) == tag.removeprefix("v")


def test_pyproject_declares_version_dynamic_not_static() -> None:
    """A reintroduced static `version = "..."` goes red immediately, not at the next tag.

    Finding 5's third assertion: the two derivation checks above pass just
    as well for a hand-typed `version = "0.2.0"` as for a real git-derived
    one at the moment that string happens to look plausible. Only reading
    `pyproject.toml` itself catches the regression at the source.
    """
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text())
    project = data["project"]
    assert "version" in project.get("dynamic", []), project.get("dynamic")
    assert "version" not in project


def test_the_configured_git_describe_command_scopes_to_release_tags(tmp_path: Path) -> None:
    """`pyproject.toml`'s `git_describe_command` line is executable and load-bearing.

    Round 2, finding 1: nothing ran this line — deleting it left every other
    test green, even though the re-reviewer measured that without it,
    `pip install -e .` raises `ValueError: Can't parse version from tag
    'phase-99-base'` the moment this project's own `phase-N-base` convention
    (CLAUDE.md §3.1) is nearer HEAD than any release tag. This test reads the
    ACTUAL configured command out of `pyproject.toml` with `tomllib` +
    `shlex` (never a hand-typed copy that could drift from the real one) and
    runs it for real in a throwaway repo shaped exactly like the measured
    failure: `v1.0.0` one commit behind HEAD, `phase-1-base` ON HEAD.
    """
    command = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text())["tool"][
        "setuptools_scm"
    ]["git_describe_command"]
    args = shlex.split(command)
    assert args[:2] == ["git", "describe"], args

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "a.txt").write_text("a\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "one")
    _git(repo, "tag", "v1.0.0")
    (repo / "b.txt").write_text("b\n")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "two")
    _git(repo, "tag", "phase-1-base")  # HEAD's own tag is NOT a release tag

    result = subprocess.run(
        args, cwd=repo, capture_output=True, text=True, timeout=_GIT_TIMEOUT_SECONDS
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert re.match(r"^v1\.0\.0-1-g[0-9a-f]+$", result.stdout.strip()), result.stdout

    # Negative control (the re-reviewer's own addition): swap the scoped
    # pattern for setuptools_scm's OLD default and confirm the SAME repo now
    # resolves against the non-release tag instead — proving the assertion
    # above is about the `--match` argument specifically, not merely about
    # git or about this repo shape.
    wide_args = [arg if arg != "v[0-9]*" else "*[0-9]*" for arg in args]
    assert wide_args != args, "the command under test does not contain the match pattern"
    wide_result = subprocess.run(
        wide_args, cwd=repo, capture_output=True, text=True, timeout=_GIT_TIMEOUT_SECONDS
    )
    assert wide_result.returncode == 0, wide_result.stdout + wide_result.stderr
    assert wide_result.stdout.strip().startswith("phase-1-base-0-g"), wide_result.stdout
