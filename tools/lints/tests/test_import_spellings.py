"""Every deny entry, against every spelling that reaches it (findings F0, F3).

The defect this module exists to prevent is not "``from google import adk`` was
missed". It is the *class*: a deny loop that reads one name per import
statement enforces its list against some spellings and not others, and a suite
that happens to test the covered spellings stays green while the invariant is
open. Phase 15.4's CR-02 fix landed exactly that shape — the write-module check
was moved onto the corrected helper and the harness deny loop 27 lines above it
was not — and the close-time panel found it by looking *beside* the fix rather
than at it.

So the parametrization below is **derived from the deny constants themselves**,
never from a hand-written list of spellings. A new harness on
``HARNESS_DENY``, a new vendor SDK on ``LLM_MODULES``, a third module tree —
each arrives already covered in every form, and a maintainer cannot add an
entry and test only the spelling they happened to think of. That is the same
reasoning that made ``is_write_module`` a predicate rather than an enumeration
(``harness_imports.py``), applied to the tests instead of to the rule.

Four checkers are covered because all four carry deny lists with a dot in them,
and every one of the dotted entries was reachable unseen before this module
existed. Which were blind was settled by execution, not by reading:

===========================  ==================  ===============================
rule                         dotted entries      single-segment entries
===========================  ==================  ===============================
``cinv02-harness``           ``google.adk``      ``langgraph``,
                             — **was blind**     ``claude_agent_sdk``,
                                                 ``anthropic`` — were never blind
``cinv03-algorithmic``       ``ccf.llm``,        ``anthropic``, ``openai``,
                             ``google.``         ``cohere``, ``litellm``,
                             ``generativeai``    ``mistralai`` — never blind
                             — **were blind**
``d06-orchestration-split``  both trees          (none)
                             — **were blind**
``cinv02-backend-import``    ``ccf.graph.``      (none)
                             ``backends`` — was
                             fixed by CR-02
===========================  ==================  ===============================

The single-segment column is why the hole survived: those entries have no
parent to be named by, so the spellings a suite naturally reaches for all
worked, and the asymmetry was invisible from the test file.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from tools.lints import (
    imported_module_names,
    package_for,
    reached_module_names,
)
from tools.lints.algorithmic import (
    ALGORITHMIC_MODE,
    LLM_MODULES,
    MODE_DUNDER,
    RULE_ALGORITHMIC,
)
from tools.lints.algorithmic import check_source as algorithmic_check
from tools.lints.backend_imports import (
    BACKENDS_PACKAGE,
    RULE_BACKEND_IMPORT,
)
from tools.lints.backend_imports import check_source as backend_check
from tools.lints.harness_imports import (
    HARNESS_DENY,
    RULE_GRAPH_WRITER,
    RULE_HARNESS,
    VENDOR_LLM_DENY,
)
from tools.lints.harness_imports import check_source as harness_check
from tools.lints.orchestration_imports import (
    ADAPTER_TREE,
    ORCHESTRATION_TREE,
    RULE_SPLIT,
)
from tools.lints.orchestration_imports import check_source as orchestration_check

# --- the spelling generator -------------------------------------------------


def denied_spellings(entry: str) -> list[str]:
    """Every import statement that binds `entry`, or something under it.

    The last two forms exist only for a dotted entry, and they are the family
    that was open: ``from google import adk`` names ``google`` and reaches
    ``google.adk``. A single-segment entry has no parent, which is precisely
    why ``langgraph`` and ``anthropic`` were always caught and ``google.adk``
    was not.
    """
    forms = [
        f"import {entry}",
        f"import {entry} as _bound",
        f"import {entry}.sub",
        f"from {entry} import thing",
        f"from {entry}.sub import thing",
        f"def f():\n    import {entry}\n    return {entry}",
    ]
    parent, _, leaf = entry.rpartition(".")
    if parent:
        forms += [
            f"from {parent} import {leaf}",
            f"from {parent} import {leaf} as _bound",
            f"from {parent} import other, {leaf}",
            f"def f():\n    from {parent} import {leaf}\n    return {leaf}",
        ]
    return forms


def permitted_lookalikes(entry: str) -> list[str]:
    """Statements that resemble `entry` without reaching it.

    A deny rule that fires on these is worse than one with a hole: it would
    push a maintainer toward an allowlist, which ``harness_imports.py`` and
    ``allowlist.yaml`` both refuse for exactly this rule family (D-13).

    ``import google`` is on the list deliberately. Binding a namespace package
    and reaching an attribute off it later is beyond any import lint — the same
    residual ``backend_imports.py`` records for ``importlib.import_module`` —
    and the honest posture is to state it rather than to fire on the parent and
    deny every unrelated distribution that shares it.
    """
    parent, _, leaf = entry.rpartition(".")
    forms = [
        f"import {entry}_evil",
        f"from {entry}_evil import thing",
        f"import {entry}x",
    ]
    if parent:
        forms += [
            f"import {parent}",
            f"from {parent} import {leaf}_evil",
            f"from {parent} import other",
        ]
    return forms


def _cases(entries: frozenset[str]) -> list[tuple[str, str]]:
    return [(entry, form) for entry in sorted(entries) for form in denied_spellings(entry)]


def _lookalike_cases(entries: frozenset[str]) -> list[tuple[str, str]]:
    return [
        (entry, form) for entry in sorted(entries) for form in permitted_lookalikes(entry)
    ]


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


def _tagged(source: str) -> str:
    return f'{MODE_DUNDER} = "{ALGORITHMIC_MODE}"\n{source}\n'


# --- fixtures: paths and module names --------------------------------------

CORE = pathlib.Path("src/ccf/operators/traversal.py")
CORE_MODULE = "ccf.operators.traversal"

HARNESS_ADAPTER = pathlib.Path("runtime/ccf_runtime/adapters/x/adapter.py")
HARNESS_ADAPTER_MODULE = "ccf_runtime.adapters.x.adapter"

DRIVER = pathlib.Path("runtime/ccf_runtime/orchestration/x/driver.py")
DRIVER_MODULE = "ccf_runtime.orchestration.x.driver"

LLM_ADAPTER = pathlib.Path("src/ccf/llm/anthropic_adapter.py")
LLM_ADAPTER_MODULE = "ccf.llm.anthropic_adapter"


# --- the deny sets are not empty -------------------------------------------


@pytest.mark.parametrize(
    "name,entries",
    [
        ("HARNESS_DENY", HARNESS_DENY),
        ("VENDOR_LLM_DENY", VENDOR_LLM_DENY),
        ("LLM_MODULES", LLM_MODULES),
        ("ADAPTER_TREE", ADAPTER_TREE),
        ("ORCHESTRATION_TREE", ORCHESTRATION_TREE),
    ],
)
def test_deny_sets_are_populated(name: str, entries: frozenset[str]) -> None:
    """An emptied deny set would make every test below vacuously pass.

    The ``substrate_vocabulary`` WR-03 lesson, applied here: a derived
    parametrization that derives from nothing passes loudly and proves nothing.
    """
    assert entries, f"{name} is empty; every derived case below would vanish"


def test_every_dotted_entry_has_a_parent_named_spelling() -> None:
    """The generator must actually generate the family that was open."""
    dotted = [
        e
        for e in HARNESS_DENY | VENDOR_LLM_DENY | LLM_MODULES | ADAPTER_TREE
        if "." in e
    ]
    assert dotted, "no dotted deny entry anywhere — the F0 family cannot be tested"
    for entry in dotted:
        parent, _, leaf = entry.rpartition(".")
        assert f"from {parent} import {leaf}" in denied_spellings(entry)


# --- cinv02-harness (CLAUDE.md §1, §7.3 — mission-level) --------------------


@pytest.mark.parametrize("entry,form", _cases(HARNESS_DENY))
def test_every_harness_spelling_is_flagged(entry: str, form: str) -> None:
    """``from google import adk`` produced no finding at all before F0.

    CLAUDE.md §1 makes harness neutrality one of four mission-level success
    conditions and §7.3 calls a harness import in ``/src`` a defect of the same
    class as an LLM client in an algorithmic module. ``from google import adk``
    is the idiomatic ADK spelling.
    """
    findings = harness_check(form + "\n", CORE, CORE_MODULE)
    assert _rules(findings) == [RULE_HARNESS], f"{entry} unseen as {form!r}"


@pytest.mark.parametrize("entry,form", _cases(VENDOR_LLM_DENY))
def test_every_vendor_llm_spelling_is_flagged(entry: str, form: str) -> None:
    findings = harness_check(form + "\n", CORE, CORE_MODULE)
    assert _rules(findings) == [RULE_HARNESS], f"{entry} unseen as {form!r}"


@pytest.mark.parametrize("entry,form", _lookalike_cases(HARNESS_DENY))
def test_no_harness_lookalike_is_flagged(entry: str, form: str) -> None:
    assert harness_check(form + "\n", CORE, CORE_MODULE) == []


@pytest.mark.parametrize("entry,form", _lookalike_cases(VENDOR_LLM_DENY))
def test_no_vendor_llm_lookalike_is_flagged(entry: str, form: str) -> None:
    assert harness_check(form + "\n", CORE, CORE_MODULE) == []


@pytest.mark.parametrize("entry,form", _cases(HARNESS_DENY))
def test_the_adapter_carve_out_covers_every_spelling(entry: str, form: str) -> None:
    """A carve-out narrower than the rule would be a new hole, mirrored.

    ``runtime/adapters/<harness>/`` is where CLAUDE.md §7.3 puts harness
    bindings, so the permission has to hold for the same set of spellings the
    denial does.
    """
    assert harness_check(form + "\n", HARNESS_ADAPTER, HARNESS_ADAPTER_MODULE) == []


@pytest.mark.parametrize("entry,form", _cases(VENDOR_LLM_DENY))
def test_the_llm_adapter_carve_out_covers_every_spelling(entry: str, form: str) -> None:
    assert algorithmic_check(form + "\n", LLM_ADAPTER, LLM_ADAPTER_MODULE) == []
    assert harness_check(form + "\n", LLM_ADAPTER, LLM_ADAPTER_MODULE) == []


# --- cinv03-algorithmic (CLAUDE.md §11) ------------------------------------


@pytest.mark.parametrize("entry,form", _cases(LLM_MODULES))
def test_every_llm_spelling_is_flagged_in_an_algorithmic_module(
    entry: str, form: str
) -> None:
    """``from ccf import llm`` reached the SDK's own LLM seam unremarked."""
    findings = algorithmic_check(_tagged(form), CORE, CORE_MODULE)
    assert _rules(findings) == [RULE_ALGORITHMIC], f"{entry} unseen as {form!r}"


@pytest.mark.parametrize("entry,form", _lookalike_cases(LLM_MODULES))
def test_no_llm_lookalike_is_flagged(entry: str, form: str) -> None:
    assert algorithmic_check(_tagged(form), CORE, CORE_MODULE) == []


@pytest.mark.parametrize("entry,form", _cases(LLM_MODULES))
def test_an_untagged_module_is_still_free_to_import_a_model_client(
    entry: str, form: str
) -> None:
    """The rule is the tag's, not the tree's — a semantic module is untouched."""
    assert algorithmic_check(form + "\n", CORE, CORE_MODULE) == []


# --- d06-orchestration-split (D-IMPL-60, D-IMPL-17) ------------------------


@pytest.mark.parametrize("entry,form", _cases(ADAPTER_TREE))
def test_every_adapter_spelling_is_flagged_inside_a_driver(
    entry: str, form: str
) -> None:
    findings = orchestration_check(form + "\n", DRIVER, DRIVER_MODULE)
    assert _rules(findings) == [RULE_SPLIT], f"{entry} unseen as {form!r}"


@pytest.mark.parametrize("entry,form", _cases(ORCHESTRATION_TREE))
def test_every_orchestration_spelling_is_flagged_inside_an_adapter(
    entry: str, form: str
) -> None:
    findings = orchestration_check(form + "\n", HARNESS_ADAPTER, HARNESS_ADAPTER_MODULE)
    assert _rules(findings) == [RULE_SPLIT], f"{entry} unseen as {form!r}"


@pytest.mark.parametrize("entry,form", _lookalike_cases(ADAPTER_TREE))
def test_no_adapter_lookalike_is_flagged_inside_a_driver(entry: str, form: str) -> None:
    assert orchestration_check(form + "\n", DRIVER, DRIVER_MODULE) == []


@pytest.mark.parametrize("entry,form", _cases(ADAPTER_TREE))
def test_a_module_in_neither_tree_is_untouched(entry: str, form: str) -> None:
    """The early return, pinned. The panel's own probe tripped over this.

    Cursor named this rule as carrying the F0 shape and the orchestrator's
    probe returned ``[]`` for *both* spellings, including the one that should
    have fired — because the module path it used was in neither tree, so
    ``check_source`` returned before reaching the walk. The probe established
    nothing either way, and the finding went into the record as unverified.
    This test is that early return stated, so the next probe reads it here
    instead of rediscovering it.
    """
    assert orchestration_check(form + "\n", CORE, CORE_MODULE) == []


# --- cinv02-backend-import (D-IMPL-93 property (1)) ------------------------


@pytest.mark.parametrize("entry,form", _cases(frozenset({BACKENDS_PACKAGE})))
def test_every_backend_spelling_is_flagged_in_core(entry: str, form: str) -> None:
    findings = backend_check(form + "\n", CORE, CORE_MODULE)
    assert _rules(findings) == [RULE_BACKEND_IMPORT], f"{entry} unseen as {form!r}"


# --- F3: relative imports, one negative control per rule -------------------
#
# Each case below returned no finding before the helpers learned to resolve a
# relative import against the importing module's package. `src/ccf` uses
# absolute imports by convention throughout — and "by convention" is the thing
# the lint exists to replace, which is the whole of why CR-02 was a blocker.


def test_relative_adapter_import_from_the_composition_root_is_flagged() -> None:
    """The review's own example: ``from .graph.backends import sqlite_write``."""
    findings = backend_check(
        "from .graph.backends import sqlite_write\n",
        pathlib.Path("src/ccf/boot.py"),
        "ccf.boot",
    )
    assert _rules(findings) == [RULE_BACKEND_IMPORT]
    assert f"{BACKENDS_PACKAGE}.sqlite_write" in findings[0]


def test_relative_write_module_import_from_a_reader_is_flagged() -> None:
    findings = harness_check(
        "from .backends import sqlite_write\n",
        pathlib.Path("src/ccf/graph/reader.py"),
        "ccf.graph.reader",
    )
    assert _rules(findings) == [RULE_GRAPH_WRITER]
    assert "ccf.graph.backends.sqlite_write" in findings[0]


def test_relative_import_inside_a_package_init_resolves_to_that_package() -> None:
    """``package_for``'s ``__init__.py`` branch, which no module name can carry.

    In ``src/ccf/graph/__init__.py`` the runner's module name is ``ccf.graph``,
    and ``from . import _writer`` resolves against ``ccf.graph`` — not against
    ``ccf``, which is what treating the name as a module would give.
    """
    findings = harness_check(
        "from . import _writer\n",
        pathlib.Path("src/ccf/graph/__init__.py"),
        "ccf.graph",
    )
    assert _rules(findings) == [RULE_GRAPH_WRITER]
    assert "ccf.graph._writer" in findings[0]


def test_relative_llm_import_in_an_algorithmic_module_is_flagged() -> None:
    findings = algorithmic_check(
        _tagged("from .. import llm"),
        pathlib.Path("src/ccf/assembly/worker.py"),
        "ccf.assembly.worker",
    )
    assert _rules(findings) == [RULE_ALGORITHMIC]
    assert "ccf.llm" in findings[0]


def test_relative_adapter_tree_import_in_a_driver_is_flagged() -> None:
    findings = orchestration_check(
        "from ...adapters import x\n", DRIVER, DRIVER_MODULE
    )
    assert _rules(findings) == [RULE_SPLIT]
    assert "ccf_runtime.adapters" in findings[0]


def test_a_relative_import_that_does_not_reach_the_denied_tree_is_clean() -> None:
    # `..adapters` from `ccf_runtime.orchestration.x.driver` is
    # `ccf_runtime.orchestration.adapters`, a sibling of the driver — not the
    # harness-adapter tree. Resolution has to be arithmetic, not a substring.
    assert orchestration_check("from ..adapters import x\n", DRIVER, DRIVER_MODULE) == []


# --- the helpers themselves -------------------------------------------------


def _node(source: str) -> ast.AST:
    return ast.parse(source).body[0]


def test_package_for_distinguishes_a_package_from_a_module() -> None:
    assert package_for(pathlib.Path("src/ccf/graph/__init__.py"), "ccf.graph") == (
        "ccf.graph"
    )
    assert package_for(pathlib.Path("src/ccf/boot.py"), "ccf.boot") == "ccf"
    assert package_for(pathlib.Path("src/ccf.py"), "ccf") == ""


def test_a_relative_import_climbing_past_the_root_resolves_to_nothing() -> None:
    """Unresolvable is reported as nothing, never as a guess."""
    assert reached_module_names(_node("from ... import x"), package="ccf.graph") == set()
    assert reached_module_names(_node("from . import x"), package="") == set()


def test_the_unexpanded_helper_still_reports_one_name_per_statement() -> None:
    """The helper is not the defect; reading *only* it was.

    ``imported_module_names`` is correct about what it claims — it cannot tell
    a submodule from an attribute without importing, which a lint must not do.
    This pins that contract so the fix cannot be misread as "the old helper was
    wrong", and so the asymmetry the deny loops now bridge stays visible.
    """
    assert imported_module_names(_node("from google import adk")) == ["google"]
    assert reached_module_names(_node("from google import adk")) == {
        "google",
        "google.adk",
    }
