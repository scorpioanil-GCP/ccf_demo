"""``tests/examples/specimen_base.py::branch_point``: where a frozen-specimen pin
measures from (D-IMPL-378 C9).

A hosted branch checkout fetches every branch as ``refs/remotes/origin/*`` and
makes only the checked-out branch local, so the bare name ``main`` does not
resolve there and ``git merge-base HEAD main`` exits 128 (the D-IMPL-378 CI
diagnosis, §4.2). Each case builds the checkout shape it names under
``tmp_path``. Offline: git only, no estate.
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

from tests.examples.specimen_base import branch_point


def _git(cwd: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def _commit(repo: pathlib.Path, name: str) -> str:
    (repo / name).write_text(name, encoding="utf-8")
    _git(repo, "add", name)
    _git(
        repo,
        "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
        "commit", "-q", "-m", name,
    )
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def origin(tmp_path: pathlib.Path) -> tuple[pathlib.Path, str]:
    """A repository whose ``main`` holds one commit: the branch point."""
    repo = tmp_path / "origin"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    return repo, _commit(repo, "base")


def _hosted_branch_checkout(origin: pathlib.Path, dest: pathlib.Path) -> pathlib.Path:
    """The shape actions/checkout leaves: remote-tracking refs, one local branch."""
    _git(origin, "checkout", "-q", "-b", "lane")
    _commit(origin, "lane-work")
    _git(origin, "checkout", "-q", "main")
    dest.mkdir()
    _git(dest, "init", "-q")
    _git(dest, "remote", "add", "origin", str(origin))
    _git(dest, "fetch", "-q", "origin", "+refs/heads/*:refs/remotes/origin/*")
    _git(dest, "checkout", "-q", "--force", "-B", "lane", "refs/remotes/origin/lane")
    return dest


def test_a_hosted_branch_checkout_measures_from_origin_main(
    origin: tuple[pathlib.Path, str], tmp_path: pathlib.Path
) -> None:
    repo, base = origin
    checkout = _hosted_branch_checkout(repo, tmp_path / "hosted")
    no_local_main = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "main"], cwd=checkout, capture_output=True
    )
    assert no_local_main.returncode != 0, "the fixture must have no local main, as CI has none"
    assert branch_point(checkout) == base


def test_a_local_main_is_used_when_present(
    origin: tuple[pathlib.Path, str],
) -> None:
    repo, base = origin
    _git(repo, "checkout", "-q", "-b", "lane")
    _commit(repo, "lane-work")
    assert branch_point(repo) == base


def test_branch_point_fails_loudly_when_neither_ref_resolves(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "branch-only"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "lane")
    _commit(repo, "only")
    with pytest.raises(AssertionError, match="neither `main` nor `origin/main`"):
        branch_point(repo)


def test_an_existing_main_is_never_bypassed(
    origin: tuple[pathlib.Path, str], tmp_path: pathlib.Path
) -> None:
    """A local ``main`` sharing no history with HEAD fails; it is not a cue to try
    ``origin/main``, which here WOULD answer: falling back would hide a wrong checkout."""
    repo, _ = origin
    checkout = _hosted_branch_checkout(repo, tmp_path / "hosted")
    _git(checkout, "checkout", "-q", "--orphan", "main")
    _commit(checkout, "unrelated-root")
    _git(checkout, "checkout", "-q", "lane")
    with pytest.raises(subprocess.CalledProcessError):
        branch_point(checkout)
