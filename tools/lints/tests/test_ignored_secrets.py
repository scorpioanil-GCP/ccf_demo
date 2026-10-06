"""LOW-04 exploit test — key material is ignored by git, and a lint holds it so.

The row (``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
"LOW-04 — `.gitignore` omits key material", and its MEASURED block, D-IMPL-372)
found ``*.pem`` and ``.env`` ignored and every other key-material shape not:
a ``FileBackedKeySource`` ``*.jwk``, a ``tokens.json`` token file, a PKCS#12
bundle or a Java keystore dropped into the checkout would be offered by
``git add -A``. CLAUDE.md §2.2: *never a secret in the tree*.

Two halves. The **behavioral** half asks git itself, with ``git check-ignore
--no-index``, whether a file of each shape would be ignored — that is the
property the row is about, independent of how any lint reads ``.gitignore``.
The **lint** half asks the registered ``ignored-secrets`` whole-tree checker
(``tools/lints/ignored_secrets.py::check_tree``) to report nothing on this
repository, and checks it reports a deleted pattern and a tracked match.
"""

from __future__ import annotations

import importlib
import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: One file name per pattern the row and its MEASURED block require.
KEY_MATERIAL_SAMPLES: tuple[str, ...] = (
    "signing.jwk",
    "server.key",
    "bundle.p12",
    "bundle.pfx",
    "trust.jks",
    "store.keystore",
    "cert.pem",
    "tokens.json",
    "deploy/tokens.json",
    ".env",
    ".env.production",
)


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
@pytest.mark.parametrize("sample", KEY_MATERIAL_SAMPLES)
def test_git_ignores_every_key_material_shape(sample: str) -> None:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", sample],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"git would NOT ignore {sample!r}: key material could be committed (LOW-04)"
    )


def _lint():  # type: ignore[no-untyped-def]
    try:
        return importlib.import_module("tools.lints.ignored_secrets")
    except ModuleNotFoundError:
        pytest.fail("tools/lints/ignored_secrets.py does not exist: no lint holds LOW-04")


def test_the_ignored_secrets_lint_is_registered_and_clean_on_this_tree() -> None:
    from tools.lints.__main__ import WHOLE_TREE_CHECKERS

    assert "ignored-secrets" in WHOLE_TREE_CHECKERS, "LOW-04 lint is not registered"
    lint = _lint()
    assert WHOLE_TREE_CHECKERS["ignored-secrets"] is lint.check_tree
    assert lint.check_tree(REPO_ROOT) == []


def _scratch_repo(tmp_path: pathlib.Path, gitignore: str) -> pathlib.Path:
    (tmp_path / ".gitignore").write_text(gitignore, encoding="utf-8")
    return tmp_path


def test_a_missing_pattern_is_one_finding(tmp_path: pathlib.Path) -> None:
    lint = _lint()
    complete = "\n".join(lint.REQUIRED_PATTERNS) + "\n"
    assert lint.check_patterns(complete, ".gitignore") == []
    for dropped in lint.REQUIRED_PATTERNS:
        text = "\n".join(p for p in lint.REQUIRED_PATTERNS if p != dropped) + "\n"
        found = lint.check_patterns(text, ".gitignore")
        assert len(found) == 1 and repr(dropped) in found[0], (dropped, found)
        assert found[0].startswith(".gitignore:1 ignored-secrets ")


def test_a_commented_or_negated_pattern_does_not_count() -> None:
    lint = _lint()
    others = [p for p in lint.REQUIRED_PATTERNS if p != "*.jwk"]
    for spoiled in ("# *.jwk", "!*.jwk", "  # *.jwk"):
        text = "\n".join([*others, spoiled]) + "\n"
        assert len(lint.check_patterns(text, ".gitignore")) == 1, spoiled


def test_a_later_negation_reopens_the_pattern() -> None:
    lint = _lint()
    text = "\n".join([*lint.REQUIRED_PATTERNS, "!keys/*.jwk"]) + "\n"
    found = lint.check_patterns(text, ".gitignore")
    assert len(found) == 1 and "!keys/*.jwk" in found[0]


def test_a_tracked_key_file_is_a_finding() -> None:
    lint = _lint()
    found = lint.check_tracked(["src/ccf/x.py", "keys/prod.jwk", "deploy/tokens.json"])
    assert len(found) == 2
    assert any("keys/prod.jwk" in f for f in found)
    assert any("deploy/tokens.json" in f for f in found)


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_scratch_git_repo_with_a_tracked_jwk_is_refused(tmp_path: pathlib.Path) -> None:
    lint = _lint()
    base = _scratch_repo(tmp_path, "\n".join(lint.REQUIRED_PATTERNS) + "\n")
    subprocess.run(["git", "init", "-q"], cwd=base, check=True)
    (base / "k.jwk").write_text("{}", encoding="utf-8")
    subprocess.run(["git", "add", "-f", "k.jwk"], cwd=base, check=True)
    found = lint.check_tree(base)
    assert len(found) == 1 and "k.jwk" in found[0]


def test_outside_git_the_patterns_are_still_checked_and_the_gap_is_said(
    tmp_path: pathlib.Path,
) -> None:
    lint = _lint()
    base = _scratch_repo(tmp_path, "*.pem\n")
    found = lint.check_tree(base)
    # every missing pattern is reported, and the tracked-file half says it did not run
    assert len([f for f in found if "is not ignored" in f]) == len(lint.REQUIRED_PATTERNS) - 1
    assert any("not a git checkout" in f for f in found)


def test_a_missing_gitignore_is_a_finding(tmp_path: pathlib.Path) -> None:
    lint = _lint()
    found = lint.check_tree(tmp_path)
    assert found and ".gitignore" in found[0]
