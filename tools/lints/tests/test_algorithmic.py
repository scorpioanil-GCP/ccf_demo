"""Unit tests for the CINV-03 Algorithmic-Semantic checker (CLAUDE.md §11, D-06)."""

from __future__ import annotations

import pathlib

from tools.lints.algorithmic import RULE_ALGORITHMIC, check_source

SRC = pathlib.Path("src/ccf/operators/temporal.py")
TAG = '__ccf_mode__ = "algorithmic"\n'


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


# --- violating cases -------------------------------------------------------


def test_tagged_module_importing_ccf_llm_is_flagged() -> None:
    findings = check_source(TAG + "import ccf.llm\n", SRC, "ccf.operators.temporal")
    assert _rules(findings) == [RULE_ALGORITHMIC]
    assert "ccf.llm" in findings[0]


def test_tagged_module_from_importing_the_protocol_is_flagged() -> None:
    source = TAG + "from ccf.llm import LLMClientProtocol\n"
    findings = check_source(source, SRC, "ccf.operators.temporal")
    assert _rules(findings) == [RULE_ALGORITHMIC]


def test_tagged_module_importing_a_vendor_sdk_is_flagged() -> None:
    findings = check_source(TAG + "import anthropic\n", SRC, "ccf.operators.temporal")
    assert _rules(findings) == [RULE_ALGORITHMIC]


def test_tagged_module_with_deferred_llm_import_in_a_function_is_flagged() -> None:
    source = TAG + "def f():\n    from ccf.llm import LLMClientProtocol\n"
    findings = check_source(source, SRC, "ccf.operators.temporal")
    assert _rules(findings) == [RULE_ALGORITHMIC]
    assert findings[0].startswith(f"{SRC}:3 ")


# --- clean cases -----------------------------------------------------------


def test_untagged_module_may_import_ccf_llm() -> None:
    source = "from ccf.llm import LLMClientProtocol\n"
    assert check_source(source, SRC, "ccf.semantic.stage") == []


def test_tagged_module_without_llm_imports_is_clean() -> None:
    source = TAG + "import pathlib\nfrom ccf.graph import GraphReader\n"
    assert check_source(source, SRC, "ccf.operators.temporal") == []


def test_mode_tag_with_another_value_does_not_activate_the_rule() -> None:
    source = '__ccf_mode__ = "semantic"\nimport ccf.llm\n'
    assert check_source(source, SRC, "ccf.semantic.stage") == []
