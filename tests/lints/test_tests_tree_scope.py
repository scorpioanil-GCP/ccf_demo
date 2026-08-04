"""Lint posture over ``tests/`` — CINV-01 in, CINV-02 and CINV-03 out.

D-IMPL-78 (Dave, 2026-08-04; plan 15-04). D-09 relocates the example CI
assertions into ``tests/``, and those assertions carry domain expectations
read from ``expected:`` artifact blocks. ``tests/`` was not a linted tree, so
the relocation would have moved domain values out of the No-Hardcoding Rule's
reach while every CI gate stayed green — a CI-invisible weakening arrived at
as a side effect of an ergonomics change.

Four tests, paired by direction. The widening is pinned *and* proven not to
have widened anything else: an invariant's scope is a posture, and a posture
that only one direction of test constrains drifts silently in the other.

All four drive the same ``tools.lints.__main__.run`` entrypoint CI uses,
against synthetic tmp trees, so they prove the config as executed — the
sibling discipline of ``test_examples_scope.py``.
"""

from __future__ import annotations

import pathlib

from tests.lints.test_examples_scope import PROMPT_LITERAL
from tools.lints.__main__ import LINTED_TREES, RULE_TREE_SCOPE, run


def _write(base: pathlib.Path, rel: str, source: str) -> None:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


# --- Test 1: the config, both halves of it ------------------------------------


def test_cinv01_scope_includes_the_tests_tree() -> None:
    """Both assertions are load-bearing, and the second alone is a no-op.

    ``run()`` iterates ``LINTED_TREES`` and *then* filters each rule by
    ``RULE_TREE_SCOPE``. A tree named only in the scope map is never walked,
    so the rule would silently not run — the failure mode this test exists to
    make impossible.
    """
    assert "tests" in LINTED_TREES
    assert "tests" in RULE_TREE_SCOPE["no-hardcoding"]


# --- Test 2: positive direction — CINV-01 fires under tests/ ------------------


def test_cinv01_rejects_a_prompt_shaped_literal_under_tests(
    tmp_path: pathlib.Path,
) -> None:
    _write(tmp_path, "tests/foo/test_x.py", PROMPT_LITERAL)
    findings = run(tmp_path, ["no-hardcoding"])
    assert findings, "a prompt-shaped literal in tests/ must be rejected"
    assert any("cinv01a-prompt-shape" in f for f in findings)


# --- Test 3: negative direction — CINV-02 did not widen with CINV-01 ----------


def test_cinv02_does_not_flag_harness_imports_under_tests(
    tmp_path: pathlib.Path,
) -> None:
    """Test modules exercising the adapters import harness SDKs legitimately;
    CLAUDE.md §7.3 scopes "zero harness imports" to core."""
    _write(
        tmp_path,
        "tests/conformance/test_harness.py",
        "import langgraph\nimport claude_agent_sdk\nfrom google.adk import x\n",
    )
    assert run(tmp_path, ["harness-imports"]) == []


# --- Test 4: negative direction — CINV-03 did not widen either ----------------


def test_cinv03_does_not_flag_an_llm_import_under_tests(
    tmp_path: pathlib.Path,
) -> None:
    """An ``@algorithmic``-tagged test double importing an LLM client is a
    test of the alternation, not a violation of it."""
    _write(
        tmp_path,
        "tests/operators/test_algorithmic_double.py",
        '__ccf_mode__ = "algorithmic"\nimport anthropic\n',
    )
    assert run(tmp_path, ["algorithmic"]) == []


# --- Test 5: the regression guards for the other trees ------------------------


def test_the_other_rules_still_reject_their_own_tree(
    tmp_path: pathlib.Path,
) -> None:
    """The tests/ exemptions must not have leaked into src/."""
    _write(tmp_path, "src/ccf/evil.py", "import langgraph\n")
    _write(
        tmp_path,
        "src/ccf/evil_mode.py",
        '__ccf_mode__ = "algorithmic"\nimport anthropic\n',
    )
    assert any("cinv02-harness" in f for f in run(tmp_path, ["harness-imports"]))
    assert run(tmp_path, ["algorithmic"]) != []
