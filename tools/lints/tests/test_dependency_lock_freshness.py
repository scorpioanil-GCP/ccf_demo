"""Tests for the `dependency-lock-freshness` rule — the SEC-028-F1 exploit test.

The row (``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
SEC-028-F1, authorized by ``D-IMPL-370``): nothing detected that
``requirements.lock`` had drifted from what ``pyproject.toml`` declares, so a
pin bump in ``pyproject.toml`` left CI installing the old lock, green.

Dave's proof requirement is binding: the test **actually edits a copy of
``pyproject.toml``** (never the committed one) and observes the check fail, for
(1) a lower bound raised above the locked version, (2) a new declared
dependency, and (3) a build requirement; and observes the unedited copy green
(the restore). The committed tree is checked directly, read-only.

The checker is looked up through ``WHOLE_TREE_CHECKERS`` by its rule name, so
on a tree where the rule does not exist every test fails on an assertion
rather than erroring at import.
"""

from __future__ import annotations

import pathlib
import shutil
from typing import Callable

import pytest

from tools.lints.__main__ import WHOLE_TREE_CHECKERS

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
RULE = "dependency-lock-freshness"


def _checker() -> Callable[[pathlib.Path], list[str]]:
    checker = WHOLE_TREE_CHECKERS.get(RULE)
    assert checker is not None, (
        f"no `{RULE}` whole-tree checker is registered: nothing compares the"
        " declared requirements in pyproject.toml with requirements.lock"
    )
    return checker


def _copy(tmp_path: pathlib.Path) -> pathlib.Path:
    """A copy of the committed declaration and lock — the only files edited."""
    base = tmp_path / "tree"
    base.mkdir()
    for name in ("pyproject.toml", "requirements.lock"):
        shutil.copyfile(REPO_ROOT / name, base / name)
    return base


def _edit(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"edit anchor `{old}` must occur exactly once"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _rule_findings(findings: list[str]) -> list[str]:
    return [f for f in findings if f" {RULE} " in f]


# --- the committed tree, read-only ------------------------------------------------


def test_the_committed_lock_agrees_with_the_committed_declaration() -> None:
    assert _checker()(REPO_ROOT) == []


def test_the_unedited_copy_is_green(tmp_path: pathlib.Path) -> None:
    """The positive control every red case below is measured against."""
    assert _checker()(_copy(tmp_path)) == []


# --- the three ruled proof cases: edit a COPY of pyproject.toml ------------------


def test_a_lower_bound_raised_above_the_locked_version_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    base = _copy(tmp_path)
    _edit(base / "pyproject.toml", '"jinja2==3.1.6"', '"jinja2>=3.2"')
    findings = _rule_findings(_checker()(base))
    assert any("jinja2" in f and "3.1.6" in f for f in findings), findings
    # restore: the same copy, edit reverted, is green again
    _edit(base / "pyproject.toml", '"jinja2>=3.2"', '"jinja2==3.1.6"')
    assert _checker()(base) == []


def test_a_new_declared_dependency_absent_from_the_lock_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    base = _copy(tmp_path)
    _edit(base / "pyproject.toml", '"jinja2==3.1.6",', '"jinja2==3.1.6",\n  "leftpad-unlocked==1.0",')
    findings = _rule_findings(_checker()(base))
    assert any("leftpad-unlocked" in f for f in findings), findings
    _edit(base / "pyproject.toml", '"jinja2==3.1.6",\n  "leftpad-unlocked==1.0",', '"jinja2==3.1.6",')
    assert _checker()(base) == []


def test_a_build_requirement_raised_above_the_locked_version_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    base = _copy(tmp_path)
    _edit(base / "pyproject.toml", '"setuptools>=77"', '"setuptools>=999"')
    findings = _rule_findings(_checker()(base))
    assert any("setuptools" in f and "build-system" in f for f in findings), findings
    _edit(base / "pyproject.toml", '"setuptools>=999"', '"setuptools>=77"')
    assert _checker()(base) == []


def test_a_new_build_requirement_absent_from_the_lock_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    base = _copy(tmp_path)
    _edit(base / "pyproject.toml", '"setuptools_scm>=8"]', '"setuptools_scm>=8", "flit-core>=3.9"]')
    findings = _rule_findings(_checker()(base))
    assert any("flit-core" in f and "build-system" in f for f in findings), findings
    _edit(base / "pyproject.toml", '"setuptools_scm>=8", "flit-core>=3.9"]', '"setuptools_scm>=8"]')
    assert _checker()(base) == []


# --- the declared set is the locked extras, followed through self-references -----


def test_an_extra_reached_through_a_self_reference_is_checked(tmp_path: pathlib.Path) -> None:
    """``dev`` -> ``ccf[harnesses]`` -> ``ccf[adk,claude-agent,langgraph]``."""
    base = _copy(tmp_path)
    _edit(base / "pyproject.toml", 'langgraph = ["langgraph==1.2.9"]', 'langgraph = ["langgraph>=1.3"]')
    findings = _rule_findings(_checker()(base))
    assert any("langgraph" in f and "1.2.9" in f for f in findings), findings


def test_an_extra_the_lock_is_not_compiled_with_is_out_of_scope(tmp_path: pathlib.Path) -> None:
    """``chroma`` is deliberately not locked (README.md: no ``--all-extras``)."""
    base = _copy(tmp_path)
    _edit(base / "pyproject.toml", '"chromadb==1.5.9"', '"chromadb>=99"')
    assert _checker()(base) == []


# --- the lock's compile header names the ruled extras ----------------------------


def test_a_header_missing_a_locked_extra_is_refused(tmp_path: pathlib.Path) -> None:
    base = _copy(tmp_path)
    _edit(base / "requirements.lock", " --extra=mongo", "")
    findings = _rule_findings(_checker()(base))
    assert any("mongo" in f and "header" in f for f in findings), findings


def test_a_header_naming_an_extra_beyond_the_ruled_set_is_refused(tmp_path: pathlib.Path) -> None:
    base = _copy(tmp_path)
    _edit(base / "requirements.lock", " --extra=mongo", " --extra=mongo --extra=chroma")
    findings = _rule_findings(_checker()(base))
    assert any("chroma" in f and "header" in f for f in findings), findings


def test_a_header_without_all_build_deps_is_refused(tmp_path: pathlib.Path) -> None:
    base = _copy(tmp_path)
    _edit(base / "requirements.lock", "--all-build-deps ", "")
    findings = _rule_findings(_checker()(base))
    assert any("--all-build-deps" in f for f in findings), findings


def test_a_lock_without_a_compile_header_is_refused(tmp_path: pathlib.Path) -> None:
    base = _copy(tmp_path)
    lock = base / "requirements.lock"
    lock.write_text(
        "\n".join(l for l in lock.read_text(encoding="utf-8").splitlines() if "pip-compile " not in l),
        encoding="utf-8",
    )
    findings = _rule_findings(_checker()(base))
    assert any("header" in f for f in findings), findings


@pytest.mark.parametrize("name", ["pyproject.toml", "requirements.lock"])
def test_a_missing_file_is_a_finding_not_a_pass(tmp_path: pathlib.Path, name: str) -> None:
    base = _copy(tmp_path)
    (base / name).unlink()
    if name == "pyproject.toml":
        # a base with neither pyproject nor workflows is not a project
        (base / ".github" / "workflows").mkdir(parents=True)
    assert _rule_findings(_checker()(base)), name


def test_a_synthetic_non_project_tree_is_clean(tmp_path: pathlib.Path) -> None:
    assert _checker()(tmp_path) == []
