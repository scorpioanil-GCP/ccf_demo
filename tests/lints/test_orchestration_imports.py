"""D-06 module-split lint + the D-IMPL-60 carve-out, with negative tests.

Fixture-driven lint tests mirroring ``tools/lints/tests/test_harness_imports.py``:
synthetic sources attributed to real module paths, checked through the same
``check_source`` entrypoints CI runs.

The four D-24-discipline negative cases the plan names, all explicit:

1. a synthetic harness import in ``ccf_runtime.peering`` still FAILS the
   harness lint (the new carve-out is not an unguarded prefix match);
2. the same in ``ccf_runtime.cdc``;
3. a synthetic orchestration→adapters import fails the new split lint;
4. a synthetic adapters→orchestration import fails it too (both directions
   explicit, per Ollama S6).
"""

from __future__ import annotations

import pathlib

from tools.lints.harness_imports import (
    ORCHESTRATION_MODULES,
    RULE_HARNESS,
    check_source as harness_check,
)
from tools.lints.orchestration_imports import (
    RULE_SPLIT,
    check_source as split_check,
)

DRIVER = pathlib.Path("runtime/ccf_runtime/orchestration/langgraph/driver.py")
ADAPTER = pathlib.Path("runtime/ccf_runtime/adapters/langgraph/adapter.py")
A2A = pathlib.Path("runtime/ccf_runtime/peering/lf_a2a.py")
CDC = pathlib.Path("runtime/ccf_runtime/cdc/adapter.py")
EVIL = pathlib.Path("runtime/ccf_runtime/orchestration_evil.py")


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


# --- the carve-out itself ------------------------------------------------------


def test_the_orchestration_tree_has_its_own_carve_out_entry() -> None:
    """A distinct frozenset entry — not a widened prefix on the adapter one."""
    assert ORCHESTRATION_MODULES == frozenset({"ccf_runtime.orchestration"})


def test_a_harness_import_inside_the_orchestration_tree_is_permitted() -> None:
    findings = harness_check(
        "import langgraph\n", DRIVER, "ccf_runtime.orchestration.langgraph.driver"
    )
    assert _rules(findings) == []


# --- D-24 negative tests: the carve-out is guarded, not prefix-matched ---------


def test_a_harness_import_in_the_peering_module_still_fails() -> None:
    findings = harness_check(
        "import claude_agent_sdk\n", A2A, "ccf_runtime.peering.lf_a2a"
    )
    assert _rules(findings) == [RULE_HARNESS]


def test_a_harness_import_in_the_cdc_module_still_fails() -> None:
    findings = harness_check(
        "from google.adk import agents\n", CDC, "ccf_runtime.cdc.adapter"
    )
    assert _rules(findings) == [RULE_HARNESS]


def test_a_harness_import_in_a_lookalike_sibling_still_fails() -> None:
    # `ccf_runtime.orchestration_evil` shares a string prefix with the
    # carve-out but is not a dotted descendant; the boundary must hold.
    findings = harness_check(
        "import langgraph\n", EVIL, "ccf_runtime.orchestration_evil"
    )
    assert _rules(findings) == [RULE_HARNESS]


# --- the bidirectional split lint (D-IMPL-60 consequence (a), A7) -------------


def test_an_orchestration_to_adapters_import_fails() -> None:
    findings = split_check(
        "from ccf_runtime.adapters.langgraph import LangGraphAdapter\n",
        DRIVER,
        "ccf_runtime.orchestration.langgraph.driver",
    )
    assert _rules(findings) == [RULE_SPLIT]
    assert "adapter tree" in findings[0]


def test_an_adapters_to_orchestration_import_fails() -> None:
    findings = split_check(
        "import ccf_runtime.orchestration.langgraph.driver\n",
        ADAPTER,
        "ccf_runtime.adapters.langgraph.adapter",
    )
    assert _rules(findings) == [RULE_SPLIT]
    assert "orchestration tree" in findings[0]


# --- clean cases and wiring ----------------------------------------------------


def test_the_engine_import_a_driver_actually_needs_is_clean() -> None:
    source = "from ccf_runtime.workflow.engine import WorkflowEngine\n"
    assert (
        split_check(source, DRIVER, "ccf_runtime.orchestration.langgraph.driver")
        == []
    )


def test_a_module_outside_both_trees_is_not_the_split_lints_business() -> None:
    source = "import ccf_runtime.adapters.langgraph\n"
    assert split_check(source, A2A, "ccf_runtime.peering.lf_a2a") == []


def test_the_split_lint_is_wired_into_the_all_gate() -> None:
    """`tools.lints --all` runs every checker; the split must be one (D-07)."""
    from tools.lints.__main__ import CHECKERS

    assert "orchestration-imports" in CHECKERS
