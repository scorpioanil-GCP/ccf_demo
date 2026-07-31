"""Unit tests for the `python -m tools.lints` gate runner (D-07)."""

from __future__ import annotations

import pathlib
import subprocess
import sys

from tools.lints.__main__ import main, module_name_for, run

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _write(base: pathlib.Path, relpath: str, source: str) -> pathlib.Path:
    path = base / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_module_names_are_derived_from_the_tree_root(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "src"
    assert module_name_for(root / "ccf" / "ops" / "t.py", root) == "ccf.ops.t"
    assert module_name_for(root / "ccf" / "__init__.py", root) == "ccf"


def test_clean_tree_yields_no_findings(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "src/ccf/ops/traversal.py", "import pathlib\n")
    assert run(tmp_path, list(("no-hardcoding", "harness-imports", "algorithmic"))) == []


def test_harness_import_under_src_is_caught_by_the_runner(
    tmp_path: pathlib.Path,
) -> None:
    _write(tmp_path, "src/ccf/ops/traversal.py", "import langgraph\n")
    findings = run(tmp_path, ["harness-imports"])
    assert len(findings) == 1
    assert "langgraph" in findings[0]


def test_main_exits_nonzero_on_a_violating_tree(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "src/ccf/ops/traversal.py", "import langgraph\n")
    assert main(["--all", "--base", str(tmp_path)]) == 1


def test_main_exits_zero_on_a_clean_tree(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "src/ccf/ops/traversal.py", "import pathlib\n")
    assert main(["--all", "--base", str(tmp_path)]) == 0


def test_missing_trees_are_skipped_not_errors(tmp_path: pathlib.Path) -> None:
    assert main(["--all", "--base", str(tmp_path)]) == 0


def test_examples_and_runtime_trees_are_linted(tmp_path: pathlib.Path) -> None:
    """Runtime is in CINV-02 scope; examples is not (plan 08-01 posture).

    CLAUDE.md §7.3 scopes "zero harness imports" to core, and example 03
    necessarily imports harness SDKs — RULE_TREE_SCOPE exempts the examples
    tree from `harness-imports` while `no-hardcoding` still covers it (see
    tests/lints/test_examples_scope.py for the full posture suite).
    """
    _write(tmp_path, "runtime/ccf_runtime/x.py", "import langgraph\n")
    _write(tmp_path, "examples/00/run.py", "import google.adk\n")
    assert len(run(tmp_path, ["harness-imports"])) == 1


def test_the_real_repo_tree_passes_the_gate() -> None:
    """The CI invocation itself, run as a subprocess exactly as ci.yml does."""
    result = subprocess.run(
        [sys.executable, "-m", "tools.lints", "--all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
