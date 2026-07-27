"""Unit tests for the CINV-02 harness-import checker (CLAUDE.md §7.3, D-06)."""

from __future__ import annotations

import pathlib

from tools.lints.harness_imports import RULE_GRAPH_WRITER, RULE_HARNESS, check_source

SRC = pathlib.Path("src/ccf/operators/traversal.py")


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


# --- violating cases -------------------------------------------------------


def test_plain_harness_import_is_flagged() -> None:
    findings = check_source("import langgraph\n", SRC, "ccf.operators.traversal")
    assert _rules(findings) == [RULE_HARNESS]
    assert "langgraph" in findings[0]
    assert str(SRC) in findings[0]


def test_from_import_of_harness_submodule_is_flagged() -> None:
    findings = check_source(
        "from google.adk import agents\n", SRC, "ccf.operators.traversal"
    )
    assert _rules(findings) == [RULE_HARNESS]
    assert "google.adk" in findings[0]


def test_claude_agent_sdk_import_inside_function_is_flagged() -> None:
    source = "def f():\n    import claude_agent_sdk\n    return claude_agent_sdk\n"
    findings = check_source(source, SRC, "ccf.operators.traversal")
    assert _rules(findings) == [RULE_HARNESS]
    assert findings[0].startswith(f"{SRC}:2 ")


def test_anthropic_import_outside_the_llm_adapter_path_is_flagged() -> None:
    findings = check_source("import anthropic\n", SRC, "ccf.operators.traversal")
    assert _rules(findings) == [RULE_HARNESS]


def test_graph_writer_import_outside_l2_is_flagged() -> None:
    findings = check_source(
        "from ccf.graph._writer import SqliteGraphWriter\n",
        SRC,
        "ccf.operators.traversal",
    )
    assert _rules(findings) == [RULE_GRAPH_WRITER]


# --- clean cases -----------------------------------------------------------


def test_ordinary_stdlib_and_ccf_imports_are_clean() -> None:
    source = "import pathlib\nfrom ccf.graph import GraphReader\n"
    assert check_source(source, SRC, "ccf.operators.traversal") == []


def test_graph_writer_import_from_assembly_is_allowed() -> None:
    source = "from ccf.graph._writer import SqliteGraphWriter\n"
    assert check_source(source, SRC, "ccf.assembly.worker") == []


def test_graph_writer_import_from_boot_is_allowed() -> None:
    source = "from ccf.graph._writer import SqliteGraphWriter\n"
    assert check_source(source, SRC, "ccf.boot") == []


def test_anthropic_import_inside_the_llm_adapter_path_is_allowed() -> None:
    assert check_source("import anthropic\n", SRC, "ccf.llm.anthropic_adapter") == []


def test_module_named_like_a_harness_prefix_is_not_flagged() -> None:
    # `langgraphql` is not `langgraph`; prefix matching must respect dot bounds.
    assert check_source("import langgraphql\n", SRC, "ccf.operators.traversal") == []


# --- the HARNESS_ADAPTER_MODULES carve-out and its boundary (D-24, D-IMPL-53) -

ADAPTER = pathlib.Path("runtime/ccf_runtime/adapters/langgraph/adapter.py")
A2A = pathlib.Path("runtime/ccf_runtime/a2a/lf_a2a.py")
CDC = pathlib.Path("runtime/ccf_runtime/cdc/adapter.py")
EVIL = pathlib.Path("runtime/ccf_runtime/adapters_evil.py")


def test_a_harness_import_inside_the_adapter_path_is_permitted() -> None:
    findings = check_source(
        "import langgraph\n", ADAPTER, "ccf_runtime.adapters.langgraph.adapter"
    )
    assert _rules(findings) == []


def test_a_harness_import_in_the_a2a_module_is_still_flagged() -> None:
    findings = check_source("import claude_agent_sdk\n", A2A, "ccf_runtime.a2a.lf_a2a")
    assert _rules(findings) == [RULE_HARNESS]


def test_a_harness_import_in_the_cdc_module_is_still_flagged() -> None:
    findings = check_source(
        "from google.adk import agents\n", CDC, "ccf_runtime.cdc.adapter"
    )
    assert _rules(findings) == [RULE_HARNESS]


def test_a_harness_import_in_a_lookalike_sibling_module_is_still_flagged() -> None:
    # `ccf_runtime.adapters_evil` shares a string prefix with the carve-out but
    # is not a dotted descendant of it; the boundary must hold.
    findings = check_source("import langgraph\n", EVIL, "ccf_runtime.adapters_evil")
    assert _rules(findings) == [RULE_HARNESS]
