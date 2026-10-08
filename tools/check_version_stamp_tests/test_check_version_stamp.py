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

import pytest

from tools.check_version_stamp import DISTRIBUTION

GATE = Path(__file__).resolve().parent.parent / "check_version_stamp.py"

#: The metadata-directory stem of ``DISTRIBUTION`` — ``-`` escaped to ``_``, as the
#: wheel specification requires and as ``pip`` writes it (``ccf_sdk-1.0.0.dist-info``).
#: The fixtures below follow the gate's own name; which name that is (SEC-027:
#: ``ccf-sdk``, never ``ccf``) is pinned by
#: ``tests/test_distribution_name.py::test_every_reader_of_the_sdks_own_metadata_names_the_declared_distribution``.
_STEM = DISTRIBUTION.replace("-", "_")

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


def _git_may_fail(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """`_git` without `check`, for asserting a fixture's git failure is real.

    The two git-failure postures below (fix round 4, finding 2) are only
    about the branch they name for as long as git actually fails the way they
    arrange. This runs the same command the gate will run and hands back the
    result so each test can assert that precondition explicitly, instead of
    failing obscurely later if a future git tolerates the damage.
    """
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
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
    """Write the SDK distribution's (``DISTRIBUTION``) metadata directly, no build tool involved.

    ``kind`` is ``"dist-info"`` (a normal installed wheel) or ``"egg-info"``
    (what a plain ``setup.py``/legacy editable build — or a stray leftover
    from one — writes into a source tree). Both are real shapes
    ``importlib.metadata`` recognizes; writing them by hand is what lets
    each scenario below control the exact "installed stamp" the gate sees.
    """
    if kind == "dist-info":
        info = root / f"{_STEM}-{version}.dist-info"
    elif kind == "egg-info":
        info = root / f"{_STEM}.egg-info"
    else:
        raise ValueError(kind)
    info.mkdir(parents=True, exist_ok=True)
    metadata_name = "METADATA" if kind == "dist-info" else "PKG-INFO"
    (info / metadata_name).write_text(
        f"Metadata-Version: 2.1\nName: {DISTRIBUTION}\nVersion: {version}\n"
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
    assert f"tag v2.0.0 but installed {DISTRIBUTION} is 2.0.1" in result.stdout


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


def test_a_tag_listing_failure_is_refused_with_its_own_message(tmp_path: Path) -> None:
    """`git tag -l` FAILING is its own DON'T-KNOW, never an absence of tags.

    Fix round 4, finding 2 (IMPORTANT): the re-reviewer deleted each of the
    gate's fourteen `print`s in turn and found exactly two branches that no
    test observed — this one and the `--points-at` one below. Both are
    git-failure refusals inside a security gate, and fix round 1's requirement
    was that every git-failure path exit non-zero with a DISTINCT message.
    Until now that requirement was met by inspection only: deleting either
    `print` left all twelve tests green.

    The posture makes `git tag` itself fail for this invocation while leaving
    `git rev-parse --verify HEAD` working, so the gate genuinely gets past the
    "cannot read git" branch and refuses at the tag listing: an unsupported
    `tag.sort` in the repository's own config, which is a real
    misconfiguration rather than a contrivance (a `[tag] sort = ...` inherited
    from a CI image's global config, or a key valid in a newer git than the
    one installed). MEASURED on git 2.43.0: `rev-parse --verify HEAD` exits 0
    while `git tag -l 'v[0-9]*'` exits 128 with `fatal: unknown field name`.
    The tag is created BEFORE the config is set, because creation would
    otherwise fail too.

    The needle has to be precise here, and for finding 1's exact reason:
    `"cannot list tags"` is a PREFIX of `"cannot list tags at HEAD"`, so a
    substring match would be satisfied by the OTHER branch's message and the
    two tests could not tell each other's refusals apart. Anchored on the full
    prefix including its colon, with the `at HEAD` spelling excluded outright.
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v1.0.0")  # created first: `git tag -a` would fail below
    _git(repo, "config", "tag.sort", "bogus-key")
    _write_distribution(repo, "1.0.0", kind="dist-info")

    readable_head = _git_may_fail(repo, "rev-parse", "--verify", "HEAD")
    assert readable_head.returncode == 0, (
        "fixture must leave HEAD readable, or the gate refuses at the EARLIER "
        f"'cannot read git' branch instead: {readable_head.stderr}"
    )
    listing = _git_may_fail(repo, "tag", "-l", "v[0-9]*")
    assert listing.returncode != 0, (
        "fixture no longer reproduces a tag-listing failure, so this test no "
        f"longer reaches the branch it names: rc={listing.returncode} "
        f"stdout={listing.stdout!r}"
    )

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.startswith(
        "check_version_stamp: cannot list tags: "
    ), result.stdout
    assert "at HEAD" not in result.stdout, result.stdout
    # git's own diagnosis is carried through the refusal, not swallowed — the
    # branch interpolates `stderr`, so an operator can see WHY listing failed.
    assert "bogus-key" in result.stdout, result.stdout


def test_a_points_at_failure_is_refused_with_its_own_message(tmp_path: Path) -> None:
    """`git tag --points-at HEAD` failing is a DIFFERENT DON'T-KNOW from the plain listing's.

    The second of fix round 4, finding 2's two unobserved branches. Reaching
    it requires a posture that distinguishes the gate's two `git tag`
    invocations, and the only difference between them is that `--points-at`
    must PEEL every matching tag to a commit while a plain `-l` merely lists
    ref names. So: a genuinely annotated tag whose tag OBJECT is then removed
    from the object store — a real partial-corruption shape (a truncated
    transfer, a lost object, an interrupted `gc`), not a mock.

    MEASURED on git 2.43.0, and this exact ordering is what the test needs:
    `rev-parse --verify HEAD` exits 0 (the commit is intact), `git tag -l
    'v[0-9]*'` exits 0 and still lists `v1.0.0` from its ref file alone (so
    the gate passes the "no tags visible" branch too), and only `git tag
    --points-at HEAD -l 'v[0-9]*'` exits 128 — `fatal: malformed object at
    'refs/tags/v1.0.0'` — because it is the only one that has to read the
    object that is gone.

    The detail assertion deliberately requires git's stderr to be non-empty
    rather than pinning its wording: the message text is git's to change
    between versions, but a refusal that carried NO diagnosis would leave an
    operator with nothing, which is the thing worth asserting.
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "-a", "v1.0.0", "-m", "annotated release tag")
    tag_object = _git(repo, "rev-parse", "v1.0.0").stdout.strip()
    assert (
        _git(repo, "cat-file", "-t", "v1.0.0").stdout.strip() == "tag"
    ), "fixture is not actually annotated, so nothing needs peeling"
    loose = repo / ".git" / "objects" / tag_object[:2] / tag_object[2:]
    assert loose.is_file(), f"tag object is not a loose object at {loose}"
    loose.unlink()  # the ref survives; the object it names does not
    _write_distribution(repo, "1.0.0", kind="dist-info")

    readable_head = _git_may_fail(repo, "rev-parse", "--verify", "HEAD")
    assert readable_head.returncode == 0, readable_head.stderr
    listing = _git_may_fail(repo, "tag", "-l", "v[0-9]*")
    assert listing.returncode == 0 and listing.stdout.strip() == "v1.0.0", (
        "fixture must let the PLAIN listing succeed and see the tag, or the "
        f"gate refuses at an earlier branch: {listing}"
    )
    peeled = _git_may_fail(repo, "tag", "--points-at", "HEAD", "-l", "v[0-9]*")
    assert peeled.returncode != 0, (
        "fixture no longer reproduces a --points-at failure, so this test no "
        f"longer reaches the branch it names: rc={peeled.returncode} "
        f"stdout={peeled.stdout!r}"
    )

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.startswith(
        "check_version_stamp: cannot list tags at HEAD: "
    ), result.stdout
    detail = result.stdout.split("cannot list tags at HEAD: ", 1)[1].strip()
    assert detail, "the refusal carried none of git's own diagnosis"


@pytest.mark.parametrize("marker", ["no-git-metadata", "no.git.metadata"])
def test_underived_fallback_stamp_is_refused_unconditionally(
    tmp_path: Path, marker: str
) -> None:
    """The fallback marker refuses in the very state the gate otherwise calls a benign PASS.

    Fix round 1 finding 2's other half: the marker announces the version was
    NOT derived from git, so its presence is never a state in which the tag
    comparison should even run.

    Fix round 4, finding 1 (BLOCKING), MEASURED: this test could not fail for
    the reason its own name claims, and it failed on BOTH halves at once.

    * **Its needle was its own stamp value.** It asserted
      `"no-git-metadata" in result.stdout`, and the tag-comparison refusal
      echoes the stamp back verbatim — measured output with the check removed
      was `check_version_stamp: tag v0.0.0 but installed ccf is
      0.0.0+no-git-metadata`. Deleting the ENTIRE marker check (the loop, not
      merely its `print`) left this test green: the gate fell through and
      refused for an unrelated reason, and `"==" not in result.stdout` held on
      that line too. So the test could not tell the marker refusal from the
      mismatch refusal, which is the whole of what it is named for. It is now
      anchored on the marker refusal's own opening text AND on the phrase
      stating the reason — neither of which any other path in the gate prints.
    * **Its fixture could not discriminate by return code.** The tag sat ON
      HEAD, where the comparison refuses anyway (`0.0.0+<marker>` never equals
      `0.0.0`), so exit 1 was guaranteed with or without the check — which
      also makes the old docstring's premise, that the value "would otherwise
      PASS (the version number matches the tag text)", simply false. The
      release tag now sits one commit BEHIND HEAD: the ordinary off-tag state
      the gate deliberately calls a benign `nothing to hold` **exit 0**. With
      the marker check removed this posture PASSES, so the return code is
      load-bearing alongside the message, and "unconditionally" is what that
      demonstrates rather than asserts.

    The off-tag shape is also the realistic one. A wheel built from a source
    tarball with no `.git` carries `fallback_version`; it is then installed
    into a venv and run inside an ordinary, correctly-tagged checkout whose
    HEAD simply is not a release — a state the gate is otherwise happy with.

    Both declared `_UNDERIVED_MARKERS` are exercised, because **the dotted one
    is the form a real build actually produces**: PEP 440 normalizes local
    version labels, so `pyproject.toml`'s literal `0.0.0+no-git-metadata` is
    recorded in `*.dist-info` as `0.0.0+no.git.metadata` (measured:
    `packaging.version.Version("0.0.0+no-git-metadata")` renders
    `0.0.0+no.git.metadata`). Covering only the hyphenated literal left the
    marker that actually reaches installed metadata with no test at all.
    """
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v0.0.0")
    (repo / "second.txt").write_text("x\n")
    _git(repo, "add", "second.txt")
    _git(repo, "commit", "-q", "-m", "second")  # the release tag is now BEHIND HEAD
    stamp = f"0.0.0+{marker}"
    _write_distribution(repo, stamp, kind="dist-info")

    result = _run_gate(repo)

    # Without the marker check this posture is the gate's benign off-tag
    # PASS (exit 0), so the return code alone catches the check's removal.
    assert result.returncode == 1, result.stdout + result.stderr
    # ...and the message catches it independently: this is the marker
    # refusal's OWN opening text, not a value the fall-through echoes back.
    assert result.stdout.startswith(
        f"check_version_stamp: installed {DISTRIBUTION} is {stamp!r} — "
    ), result.stdout
    assert (
        f"the {marker!r} marker means the version was NOT derived from git"
        in result.stdout
    ), result.stdout
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
    """Two SDK distributions with disagreeing versions in the same directory: REFUSE.

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
        f"check_version_stamp: ambiguous {DISTRIBUTION!r} metadata"
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
    (repo / f"{_STEM}-2.0.0.dist-info").mkdir()  # exists, but no METADATA inside

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
        f"check_version_stamp: {DISTRIBUTION!r} metadata is present but unreadable"
    ), result.stdout
    assert f"{_STEM}-2.0.0.dist-info" in result.stdout


def test_no_distribution_found_is_refused(tmp_path: Path) -> None:
    """No SDK distribution visible anywhere: REFUSE, not a crash and not a pass."""
    repo = _make_repo(tmp_path)
    _git(repo, "tag", "v1.0.0")

    result = _run_gate(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert f"no {DISTRIBUTION!r} distribution found" in result.stdout


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
