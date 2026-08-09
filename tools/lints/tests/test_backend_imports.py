"""Unit tests for ``cinv02-backend-import`` (D-IMPL-93 property (1)).

Written before the property is true of the tree, and deliberately so. The
negative controls below are the evidence that the rule *fires*; a rule with
only green tests cannot be told apart from a rule with a broken matcher, and
this one will not run over the tree until the plan that turns the dependency
arrow around has landed (T-15.4-13).
"""

from __future__ import annotations

import pathlib

from tools.lints.backend_imports import (
    BACKENDS_PACKAGE,
    RULE_BACKEND_IMPORT,
    check_source,
)

BOOT = pathlib.Path("src/ccf/boot.py")
MANIFEST = pathlib.Path("src/ccf/deployment/manifest.py")
ADAPTER = pathlib.Path("src/ccf/graph/backends/sqlite_write.py")

A_BACKEND = f"{BACKENDS_PACKAGE}.sqlite"
A_WRITE_MODULE = f"{BACKENDS_PACKAGE}.sqlite_write"


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


# --- negative controls: the rule fires -------------------------------------


def test_from_import_of_an_adapter_is_flagged() -> None:
    findings = check_source(
        f"from {A_BACKEND} import SqliteGraphStore\n", BOOT, "ccf.boot"
    )
    assert _rules(findings) == [RULE_BACKEND_IMPORT]
    assert A_BACKEND in findings[0]
    assert str(BOOT) in findings[0]


def test_plain_import_of_an_adapter_is_flagged() -> None:
    findings = check_source(
        f"import {BACKENDS_PACKAGE}.mongo\n", MANIFEST, "ccf.deployment.manifest"
    )
    assert _rules(findings) == [RULE_BACKEND_IMPORT]
    assert f"{BACKENDS_PACKAGE}.mongo" in findings[0]


def test_import_of_the_adapter_package_itself_is_flagged() -> None:
    # `from ccf.graph.backends import sqlite_write` reaches an adapter module
    # just as surely as naming it in full; the package is the guarded unit.
    findings = check_source(
        f"from {BACKENDS_PACKAGE} import sqlite_write\n", BOOT, "ccf.boot"
    )
    assert _rules(findings) == [RULE_BACKEND_IMPORT]
    # One statement, one finding — and the finding names the write module
    # rather than the package that merely contains it (CR-02).
    assert A_WRITE_MODULE in findings[0]


def test_from_package_import_submodule_is_flagged_by_its_own_name() -> None:
    """CR-02 — the spelling `imported_module_names` alone cannot see.

    `from ccf.graph import backends` binds `ccf.graph.backends` at runtime,
    but the dotted name the statement carries is `ccf.graph`. The rule read
    only that name until this finding, so the plainest possible spelling of
    the import it exists to deny produced nothing at all.
    """
    findings = check_source("from ccf.graph import backends\n", BOOT, "ccf.boot")
    assert _rules(findings) == [RULE_BACKEND_IMPORT]
    assert BACKENDS_PACKAGE in findings[0]


def test_two_adapters_in_one_statement_report_once() -> None:
    # The finding is about the statement, not about how many spellings of the
    # guarded package it matches.
    findings = check_source(
        f"from {BACKENDS_PACKAGE} import sqlite_write, mongo_write\n",
        BOOT,
        "ccf.boot",
    )
    assert _rules(findings) == [RULE_BACKEND_IMPORT]


def test_function_scope_import_is_flagged_at_the_import_line() -> None:
    source = (
        "def open_store():\n"
        f"    from {A_BACKEND} import SqliteGraphStore\n"
        "    return SqliteGraphStore\n"
    )
    findings = check_source(source, BOOT, "ccf.boot")
    assert _rules(findings) == [RULE_BACKEND_IMPORT]
    # The finding points at the import, not at the `def` that hides it — a
    # lazy import inside a factory is exactly how this arrow got drawn.
    assert findings[0].startswith(f"{BOOT}:2 ")


def test_the_finding_names_the_registry_as_the_way_out() -> None:
    findings = check_source(f"import {A_BACKEND}\n", BOOT, "ccf.boot")
    assert "ccf.graph.registry" in findings[0]


# --- positive controls: the rule stays quiet -------------------------------


def test_an_adapter_may_import_a_sibling_adapter() -> None:
    source = f"from {A_BACKEND} import SqliteGraphStore\n"
    assert check_source(source, ADAPTER, A_WRITE_MODULE) == []


def test_the_adapter_package_root_is_itself_exempt() -> None:
    source = f"from {A_BACKEND} import SqliteGraphStore\n"
    assert check_source(source, ADAPTER, BACKENDS_PACKAGE) == []


def test_a_lookalike_sibling_package_is_not_matched() -> None:
    # `ccf.graph.backends_evil` shares a string prefix with the guarded package
    # but is not a dotted descendant of it; matching must respect dot bounds in
    # both directions.
    source = f"import {BACKENDS_PACKAGE}_evil.sqlite\n"
    assert check_source(source, BOOT, "ccf.boot") == []


def test_a_module_under_a_lookalike_package_is_not_exempt() -> None:
    # The other direction of the same bound: sitting in `backends_evil` does
    # not buy the exemption that sitting in `backends` does.
    source = f"from {A_BACKEND} import SqliteGraphStore\n"
    findings = check_source(source, BOOT, f"{BACKENDS_PACKAGE}_evil.sqlite")
    assert _rules(findings) == [RULE_BACKEND_IMPORT]


def test_ordinary_core_imports_are_clean() -> None:
    source = (
        "import pathlib\n"
        "from ccf.graph.protocols import GraphReader\n"
        "from ccf.graph.registry import resolve\n"
    )
    assert check_source(source, BOOT, "ccf.boot") == []


def test_relative_imports_are_reported_as_nothing() -> None:
    # A documented blind spot, pinned so it stays a known one: relative imports
    # carry no absolute module name and this rule reasons only about those.
    assert check_source("from . import sqlite\n", BOOT, "ccf.boot") == []
