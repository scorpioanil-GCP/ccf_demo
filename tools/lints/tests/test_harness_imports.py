"""Unit tests for the CINV-02 harness-import checker (CLAUDE.md §7.3, D-06)."""

from __future__ import annotations

import pathlib

from tools.lints.harness_imports import (
    RULE_GRAPH_WRITER,
    RULE_HARNESS,
    check_source,
    is_write_module,
)

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
A2A = pathlib.Path("runtime/ccf_runtime/peering/lf_a2a.py")
CDC = pathlib.Path("runtime/ccf_runtime/cdc/adapter.py")
EVIL = pathlib.Path("runtime/ccf_runtime/adapters_evil.py")


def test_a_harness_import_inside_the_adapter_path_is_permitted() -> None:
    findings = check_source(
        "import langgraph\n", ADAPTER, "ccf_runtime.adapters.langgraph.adapter"
    )
    assert _rules(findings) == []


def test_a_harness_import_in_the_a2a_module_is_still_flagged() -> None:
    findings = check_source("import claude_agent_sdk\n", A2A, "ccf_runtime.peering.lf_a2a")
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


# --- the widened cinv02-graph-writer guarded set (D-01/D-03) ----------------
#
# The rule guards a *class* of modules — the neutral base plus every
# ``backends/<name>_write`` module — with two distinct permitted-importer sets.
# These tests watch it fire, watch it stay quiet, and pin the asymmetry between
# the two sets so that widening one cannot quietly widen the other.

A_WRITE_MODULE = "ccf.graph.backends.sqlite_write"
IMPORT_A_WRITE_MODULE = f"from {A_WRITE_MODULE} import SqliteGraphWriter\n"


def test_per_backend_write_module_import_outside_l2_is_flagged() -> None:
    findings = check_source(IMPORT_A_WRITE_MODULE, SRC, "ccf.operators.traversal")
    assert _rules(findings) == [RULE_GRAPH_WRITER]
    assert A_WRITE_MODULE in findings[0]


def test_per_backend_write_module_import_from_assembly_is_allowed() -> None:
    assert check_source(IMPORT_A_WRITE_MODULE, SRC, "ccf.assembly.worker") == []


def test_a_write_module_may_import_the_neutral_base() -> None:
    # Every write module subclasses BaseGraphWriter and implements _GraphTxn,
    # so naming the base is the subclass's whole reason to exist.
    findings = check_source(
        "from ccf.graph._writer import BaseGraphWriter\n", SRC, A_WRITE_MODULE
    )
    assert findings == []


def test_the_registry_may_not_import_a_per_backend_write_module() -> None:
    # The registry carve-out covers the neutral base and stops there. If this
    # test ever goes green the two permitted sets have been collapsed into one.
    findings = check_source(IMPORT_A_WRITE_MODULE, SRC, "ccf.graph.registry")
    assert _rules(findings) == [RULE_GRAPH_WRITER]


def test_the_registry_may_import_the_neutral_base() -> None:
    # It types the seam — BaseGraphWriter and BootToken — and never mints a
    # token or calls a factory.
    findings = check_source(
        "from ccf.graph._writer import BootToken\n", SRC, "ccf.graph.registry"
    )
    assert findings == []


def test_is_write_module_covers_the_base_and_the_per_backend_modules() -> None:
    assert is_write_module("ccf.graph._writer")
    assert is_write_module(A_WRITE_MODULE)


def test_is_write_module_is_dot_bounded() -> None:
    # `ccf.graph.backends_evil` shares a string prefix with the adapter package
    # but is not a dotted descendant of it.
    assert not is_write_module("ccf.graph.backends_evil.sqlite_write")


def test_a_read_module_inside_the_adapter_package_is_not_guarded() -> None:
    # Only `<name>_write` modules join the guarded set; the read module beside
    # them is imported by many callers and stays unguarded by this rule.
    assert not is_write_module("ccf.graph.backends.sqlite")


# --- both spellings of an import (CR-02) ------------------------------------
#
# The rule used to read only the dotted name an `ImportFrom` carries, so the
# two forms below produced nothing. Each is a negative control: the assertion
# is that the rule *fires*, and each of them was green-for-nothing before.


def test_from_package_import_of_the_neutral_base_is_flagged() -> None:
    """The blind spot that let any core module reach ``mint_boot_token``.

    ``from ccf.graph import _writer`` binds the neutral base and the name the
    statement carries is ``ccf.graph``, which matches nothing this rule denies.
    With it unseen, "even with a writer implementation on disk, no other module
    can name it" was not true as written.
    """
    findings = check_source(
        "from ccf.graph import _writer\n", SRC, "ccf.operators.traversal"
    )
    assert _rules(findings) == [RULE_GRAPH_WRITER]
    assert "ccf.graph._writer" in findings[0]


def test_from_package_import_of_a_per_backend_write_module_is_flagged() -> None:
    """And the blind spot that let one adapter name another's write module.

    ``cinv02-backend-import`` exempts everything under the adapter package —
    an adapter may name its siblings — so this rule is the only one that can
    see a *reader* reaching a **different** adapter's write module. It saw
    ``ccf.graph.backends`` and stopped.
    """
    findings = check_source(
        "from ccf.graph.backends import sqlite_write\n",
        SRC,
        "ccf.graph.backends.mongo",
    )
    assert _rules(findings) == [RULE_GRAPH_WRITER]
    assert A_WRITE_MODULE in findings[0]


def test_a_write_module_may_still_name_its_own_reader() -> None:
    # The other side of the bound: a read module is not in the guarded set, so
    # naming one through the package spelling stays legal.
    findings = check_source(
        "from ccf.graph.backends import mongo\n", SRC, "ccf.graph.backends.mongo_write"
    )
    assert findings == []


def test_a_write_module_may_name_the_base_through_the_package_spelling() -> None:
    findings = check_source(
        "from ccf.graph import _writer\n", SRC, A_WRITE_MODULE
    )
    assert findings == []


def test_two_write_modules_in_one_statement_report_once() -> None:
    findings = check_source(
        "from ccf.graph.backends import sqlite_write, mongo_write\n",
        SRC,
        "ccf.operators.traversal",
    )
    assert _rules(findings) == [RULE_GRAPH_WRITER]
