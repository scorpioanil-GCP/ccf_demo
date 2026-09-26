"""``tools/check_version_stamp.py``'s own tests (D-IMPL-357 §D, SEC-029, fix round 1 finding 6).

Real temporary git repositories under ``tmp_path``, real subprocess
invocations of the gate script, real ``*.dist-info``/``*.egg-info``
directories written by hand to control what "the installed stamp" is for
each posture — no mocks, no clock. Before this module the gate script was
exercised nowhere: `tests/test_version_stamp.py` never invokes it, and
`make ci` / `ci-core` / `gate-tools` were unchanged, so its first real
execution would have been the `v*` push itself, and per fix round 1
finding 2 a broken invocation used to fail toward exit 0 (a silent PASS).

The gate is invoked with ``-S`` (skip ``site``) so the venv's OWN real
``ccf`` install (in ``site-packages``) is invisible to the child process —
every scenario below controls "what ``ccf`` looks installed as" entirely
through a hand-written distribution directory inside the scenario's own
``tmp_path``, which the gate's own `_discover_versions` puts on `sys.path`
by adding the cwd (this is the exact mechanism finding 1 added, and this
suite is what proves it does what it says: a scenario constructs a
directory holding an ambiguous PAIR of ``ccf`` metadata directories and
asserts the gate refuses, mirroring the real defect measured in
`/home/parkave/ccf_code`'s stale, git-ignored `ccf.egg-info/`).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parent.parent / "check_version_stamp.py"

#: Minimal, deterministic environment for the git-repo-building helpers
#: below — no reliance on this host's global git config for author identity.
_GIT_IDENTITY_ENV = {
    "GIT_AUTHOR_NAME": "gate-test",
    "GIT_AUTHOR_EMAIL": "gate-test@example.invalid",
    "GIT_COMMITTER_NAME": "gate-test",
    "GIT_COMMITTER_EMAIL": "gate-test@example.invalid",
}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command against a scenario repo, raising on failure.

    Full host environment plus a fixed author/committer identity — this
    helper BUILDS the fixture; it is not the thing under test, so it may
    rely on `git` being on `PATH` the normal way.
    """
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
        env={**os.environ, **_GIT_IDENTITY_ENV},
    )


def _make_repo(root: Path) -> Path:
    """A fresh git repo with one commit, no tags."""
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("gate fixture\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def _write_distribution(root: Path, version: str, *, kind: str) -> None:
    """Write a ``ccf`` distribution's metadata directly, no build tool involved.

    ``kind`` is ``"dist-info"`` (a normal installed wheel) or ``"egg-info"``
    (what a plain ``setup.py``/legacy editable build — or a stray leftover
    from one — writes into a source tree). Both are real shapes
    ``importlib.metadata`` recognizes; writing them by hand is what lets
    each scenario below control the exact "installed stamp" the gate sees.
    """
    if kind == "dist-info":
        info = root / f"ccf-{version}.dist-info"
    elif kind == "egg-info":
        info = root / "ccf.egg-info"
    else:
        raise ValueError(kind)
    info.mkdir(parents=True, exist_ok=True)
    metadata_name = "METADATA" if kind == "dist-info" else "PKG-INFO"
    (info / metadata_name).write_text(
        f"Metadata-Version: 2.1\nName: ccf\nVersion: {version}\n"
    )


def _run_gate(cwd: Path) -> subprocess.CompletedProcess[str]:
    """Invoke the real gate script as a subprocess, isolated from this venv's own `ccf`.

    `-S` skips `site` module processing, so `.venv-d`'s `site-packages` —
    where the SDK's actual, correctly-derived distribution lives — never
    lands on the child's `sys.path`. The only `ccf` the child can see is
    whatever the scenario wrote into `cwd`, via the gate's own cwd-insertion
    (finding 1's fix, exercised here rather than assumed).
    """
    return subprocess.run(
        [sys.executable, "-S", str(GATE)],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=15,
        env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/tmp")},
    )


def test_off_tag_is_a_positive_pass_that_prints_the_stamp(tmp_path: Path) -> None:
    """A release tag exists in the repo but not at HEAD: PASS, stamp printed.

    The ordinary state of every branch and PR run. Distinguishing this from
    the DON'T-KNOW postures below (finding 2) is the entire point of this
    module.
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v1.0.0")
    (repo / "second.txt").write_text("x\n")
    _git(repo, "add", "second.txt")
    _git(repo, "commit", "-q", "-m", "second")
    _write_distribution(repo, "1.0.0.dev1+gdeadbeef", kind="dist-info")

    result = _run_gate(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "nothing to hold" in result.stdout
    assert "1.0.0.dev1+gdeadbeef" in result.stdout


def test_matching_tag_is_a_pass(tmp_path: Path) -> None:
    """HEAD is an exact release tag and the installed stamp equals it: PASS."""
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v2.0.0")
    _write_distribution(repo, "2.0.0", kind="dist-info")

    result = _run_gate(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "v2.0.0 == 2.0.0" in result.stdout


def test_matching_annotated_tag_is_a_pass(tmp_path: Path) -> None:
    """The suite otherwise proves only LIGHTWEIGHT tags; every real release tag here is annotated.

    Fix round 2, finding 5 (minor): `git cat-file -t v1.0.1` in this actual
    repository reports `tag`, not `commit` — every real release this project
    has cut used an annotated tag. `git tag -l` and `git tag --points-at`
    (what this gate's own `_run_git` calls use) resolve an annotated tag's
    name identically to a lightweight one, but the suite had never exercised
    that shape until now.
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "-a", "v3.0.0", "-m", "annotated release tag")
    assert (
        _git(repo, "cat-file", "-t", "v3.0.0").stdout.strip() == "tag"
    ), "fixture is not actually annotated"
    _write_distribution(repo, "3.0.0", kind="dist-info")

    result = _run_gate(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "v3.0.0 == 3.0.0" in result.stdout


def test_mismatching_tag_is_refused(tmp_path: Path) -> None:
    """HEAD is an exact release tag but the installed stamp disagrees: REFUSE.

    This is the literal SEC-029 scenario: a tagged release whose runtime
    would still stamp replay records with the wrong version.
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v2.0.0")
    _write_distribution(repo, "2.0.1", kind="dist-info")

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "tag v2.0.0 but installed ccf is 2.0.1" in result.stdout


def test_no_git_at_all_is_refused_not_passed(tmp_path: Path) -> None:
    """No `.git` anywhere: REFUSE with a positive "cannot read git", never a silent pass.

    Fix round 1 finding 2, MEASURED posture 1: a directory with no git
    history at all used to fold into the same "nothing to hold" line as a
    genuine off-tag branch.
    """
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    _write_distribution(plain, "3.0.0", kind="dist-info")

    result = _run_gate(plain)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "cannot read git" in result.stdout


def test_no_release_tags_anywhere_is_refused_not_passed(tmp_path: Path) -> None:
    """A real git repo with zero `v*` tags anywhere: REFUSE, a DON'T-KNOW.

    Fix round 1 finding 2, MEASURED posture 2: this is the shallow-clone /
    tags-never-fetched symptom (`--depth 1`, zero tags) — the installed
    stamp can look plausible while the checkout has no way to confirm it
    against a tag, and the old gate passed silently.
    """
    repo = _make_repo(tmp_path)
    _write_distribution(repo, "4.0.0.dev0+gcafef00d", kind="dist-info")

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "no 'v[0-9]*' tags are visible" in result.stdout


def test_underived_fallback_stamp_is_refused_unconditionally(tmp_path: Path) -> None:
    """The `no-git-metadata` marker refuses even when HEAD IS an exact matching tag.

    Fix round 1 finding 2's other half: the marker announces the version was
    NOT derived from git, so its presence is never a state in which the tag
    comparison should even run — asserted here by making the tag comparison
    a value that would otherwise PASS (the version number matches the tag
    text) and confirming the marker still wins.
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v0.0.0")
    _write_distribution(repo, "0.0.0+no-git-metadata", kind="dist-info")

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "no-git-metadata" in result.stdout
    assert "==" not in result.stdout


def test_a_non_release_tag_on_head_takes_the_off_tag_path(tmp_path: Path) -> None:
    """`phase-N-base` (this project's own convention, CLAUDE.md §3.1) on HEAD is never mistaken for a release.

    Fix round 1 finding 3, scoping assertion: an unscoped `git describe
    --exact-match` would report a non-release tag on HEAD as the "expected"
    version. `v[0-9]*`-scoped `git tag --points-at` must not.
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v1.0.0")  # a real release tag exists in history
    (repo / "second.txt").write_text("x\n")
    _git(repo, "add", "second.txt")
    _git(repo, "commit", "-q", "-m", "second")
    _git(repo, "tag", "phase-1-base")  # HEAD's own tag is NOT a release tag
    _write_distribution(repo, "1.0.0.dev1+gabc1234", kind="dist-info")

    result = _run_gate(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "nothing to hold" in result.stdout
    assert "phase-1-base" not in result.stdout


def test_ambiguous_metadata_on_sys_path_is_refused(tmp_path: Path) -> None:
    """Two `ccf` distributions with disagreeing versions in the same directory: REFUSE.

    Fix round 1 finding 1, MEASURED: a stale, git-ignored `ccf.egg-info/`
    left by an older editable build sits beside the current install and
    used to win silently (`importlib.metadata.version()` returns only the
    first match). This is that exact shape, built by hand: a
    `ccf-X.Y.Z.dist-info/` (the correct, current stamp) and a `ccf.egg-info/`
    (the stale leftover) in the same directory, both visible once the gate
    adds that directory to `sys.path`.
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v2.0.0")
    _write_distribution(repo, "2.0.0", kind="dist-info")
    _write_distribution(repo, "0.1.0", kind="egg-info")

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    # `.startswith`, not `"ambiguous" in result.stdout` (fix round 3, finding
    # 1, MEASURED): pytest names `tmp_path` after the test function, so this
    # scenario's own directory is `.../test_ambiguous_metadata_on_sys0/...`
    # — the word is present in the PATH regardless of whether the gate ever
    # prints its refusal. Deleting the gate's header `print(...)` left this
    # assertion passing. Anchoring on the START of stdout is immune: nothing
    # this gate ever prints as its first line can be a fixture path, because
    # every code path's first `print` begins with `"check_version_stamp: "`.
    assert result.stdout.startswith(
        "check_version_stamp: ambiguous 'ccf' metadata"
    ), result.stdout
    assert "2.0.0" in result.stdout
    assert "0.1.0" in result.stdout


def test_unreadable_metadata_is_a_named_refusal_not_a_traceback(tmp_path: Path) -> None:
    """A metadata directory with no `METADATA`/`PKG-INFO` inside: a NAMED refusal, never a bare traceback.

    Fix round 2, finding 4/minor, MEASURED: `importlib.metadata` reports a
    distribution directory that matches the discovery glob but carries no
    metadata FILE inside it as `dist.version is None` — not an exception.
    Before this fix, `sorted(set(versions.values()))` then raised
    `TypeError: '<' not supported between instances of 'str' and
    'NoneType'` the moment a real, readable distribution was ALSO present:
    still a non-zero exit (fails closed), but a traceback rather than the
    refusal line every other posture in this suite prints, leaving an
    operator unable to tell "broken environment" from "version mismatch".
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v1.0.0")
    _write_distribution(repo, "1.0.0", kind="dist-info")
    (repo / "ccf-2.0.0.dist-info").mkdir()  # exists, but no METADATA inside

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Traceback" not in result.stderr, result.stderr
    # `.startswith`, not `"unreadable" in result.stdout` (fix round 3,
    # finding 1, MEASURED): pytest names `tmp_path` after the test function,
    # so this scenario's own directory is
    # `.../test_unreadable_metadata_is_a_0/repo/ccf-2.0.0.dist-info` — the
    # word is present in the PATH the gate prints on its SECOND line,
    # regardless of whether the header refusal line ever runs. Deleting the
    # gate's four-line header `print(...)` (leaving only the path line) left
    # this assertion passing; so did rewording the header to "not readable".
    # Anchoring on the START of stdout is immune to both.
    assert result.stdout.startswith(
        "check_version_stamp: 'ccf' metadata is present but unreadable"
    ), result.stdout
    assert "ccf-2.0.0.dist-info" in result.stdout


def test_no_distribution_found_is_refused(tmp_path: Path) -> None:
    """Nothing named `ccf` visible anywhere: REFUSE, not a crash and not a pass."""
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v1.0.0")

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "no 'ccf' distribution found" in result.stdout


def test_multiple_release_tags_on_head_is_refused_not_guessed(tmp_path: Path) -> None:
    """Two release tags on the same commit: REFUSE rather than pick one silently.

    Not one of the six required postures (recorded as a residual by the
    controller, not a required fix), but the code has an explicit branch for
    it and an explicit branch with no test is exactly last round's finding
    6 — so it is covered here too, real repo, no mock.
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v1.0.0")
    _git(repo, "tag", "v1.0.0-alt")  # still matches v[0-9]* and points at HEAD
    _write_distribution(repo, "1.0.0", kind="dist-info")

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "more than one release tag" in result.stdout
