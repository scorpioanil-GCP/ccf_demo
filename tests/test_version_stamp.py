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
import re
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
