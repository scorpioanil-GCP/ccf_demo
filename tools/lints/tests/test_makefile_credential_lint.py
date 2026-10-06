"""Tests for `tools/lints/makefile_credentials.py` — the SEC-026 static guard.

Fixtures are the ones the row names
(``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
SEC-026): line 295's exact baked value (positive), a userinfo-free Mongo
default (negative), ``$(VAR)`` and ``${VAR}``, a continuation whose ``@`` sits
on the second physical line, an ``@echo $(DSN)``, and the ``PG_DSN_ENV``
indirection.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

from tools.lints import makefile_credentials as lint
from tools.lints.__main__ import WHOLE_TREE_CHECKERS

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _findings(source: str) -> list[str]:
    return lint.check_source(source, "Makefile")


# --- rule (iii): baked credential defaults -----------------------------------


def test_line_295s_exact_baked_value_is_refused() -> None:
    found = _findings("CCF_TEST_NEO4J_URI ?= neo4j://neo4j:ccf_test_password@localhost:7687\n")
    assert len(found) == 1 and "CCF_TEST_NEO4J_URI bakes a credential default" in found[0]
    assert found[0].startswith("Makefile:1 makefile-credentials ")


@pytest.mark.parametrize("op", ["=", ":=", "?="])
def test_every_assignment_operator_is_read_for_userinfo(op: str) -> None:
    assert _findings(f"X {op} postgresql://u:p@h/db\n")


def test_a_userinfo_free_default_is_not_refused() -> None:
    assert _findings("CCF_TEST_MONGO_URI ?= mongodb://localhost:27017/ccf_test\n") == []


def test_a_target_specific_baked_default_is_refused() -> None:
    assert _findings("leg: CCF_X_DSN = postgresql://u:p@h/db\n")


# --- rule (i): echoed expansion over joined logical lines --------------------


@pytest.mark.parametrize("ref", ["$(CCF_TEST_POSTGRES_DSN)", "${CCF_TEST_POSTGRES_DSN}"])
def test_both_reference_forms_are_refused_unsilenced(ref: str) -> None:
    found = _findings(f"t:\n\tcmd X={ref} \\\n\t\tmore\n")
    assert len(found) == 1 and "expands CCF_TEST_POSTGRES_DSN" in found[0]


@pytest.mark.parametrize("ref", ["$(CCF_TEST_POSTGRES_DSN)", "${CCF_TEST_POSTGRES_DSN}"])
def test_both_reference_forms_pass_behind_at(ref: str) -> None:
    assert _findings(f"t:\n\t@cmd X={ref} \\\n\t\tmore\n") == []


def test_an_at_on_the_second_physical_line_silences_nothing() -> None:
    found = _findings("t:\n\tcmd \\\n\t@X=$(CCF_TEST_POSTGRES_DSN) more\n")
    assert len(found) == 1 and found[0].startswith("Makefile:2 ")


@pytest.mark.parametrize("suffix", ["DSN", "URI", "URL", "PASSWORD"])
def test_the_name_class_is_in_scope_by_name(suffix: str) -> None:
    assert _findings(f"t:\n\tcmd $(SOME_{suffix})\n")


def test_a_userinfo_free_url_is_in_scope_by_name_not_by_value() -> None:
    source = "CCF_TEST_FLUREE_URL ?= http://localhost:8090\nt:\n\tcmd $(CCF_TEST_FLUREE_URL)\n"
    found = _findings(source)
    assert len(found) == 1 and "expands CCF_TEST_FLUREE_URL" in found[0]


def test_one_level_of_indirection_is_resolved_pg_dsn_env() -> None:
    source = (
        "ifneq ($(strip $(CCF_TEST_POSTGRES_DSN)),)\n"
        "PG_DSN_ENV := CCF_TEST_POSTGRES_DSN=$(CCF_TEST_POSTGRES_DSN)\n"
        "endif\n"
        "leg:\n"
        "\t$(ENV) CCF_REQUIRE_POSTGRES=1 $(PG_DSN_ENV) \\\n"
        "\t\t$(PYTHON) -m pytest tests\n"
    )
    found = _findings(source)
    assert len(found) == 1 and "expands PG_DSN_ENV" in found[0], found


def test_assignment_and_conditional_lines_are_not_recipe_lines() -> None:
    source = (
        "ifneq ($(strip $(CCF_TEST_POSTGRES_DSN)),)\n"
        "PG_DSN_ENV := CCF_TEST_POSTGRES_DSN=$(CCF_TEST_POSTGRES_DSN)\n"
        "endif\n"
    )
    assert _findings(source) == []


def test_a_shell_reference_is_not_a_make_expansion() -> None:
    assert _findings("t:\n\tcmd $$CCF_TEST_POSTGRES_DSN\n") == []


def test_a_non_credential_expansion_is_not_refused() -> None:
    assert _findings("t:\n\t$(ENV) $(PYTHON) -m pytest\n") == []


# --- rule (ii): printed even behind @ ----------------------------------------


def test_at_echo_of_a_credential_is_refused() -> None:
    found = _findings("t:\n\t@echo $(DSN)\n")
    assert len(found) == 1 and "echo/printf" in found[0]


def test_at_printf_of_a_credential_shell_variable_is_refused() -> None:
    assert _findings('t:\n\t@printf "%s" "$$CCF_TEST_MONGO_URI"\n')


def test_an_echo_naming_the_variable_without_its_value_is_allowed() -> None:
    assert _findings('t:\n\t@echo "CCF_TEST_NEO4J_URI is unset" >&2\n') == []


@pytest.mark.parametrize("line", ["\t@set -x; cmd\n", "\tset -ex; cmd\n", "\t@set -o xtrace; cmd\n"])
def test_set_x_in_a_recipe_is_refused(line: str) -> None:
    assert any("set -x" in f for f in _findings("t:\n" + line))


# --- wiring and the real tree ------------------------------------------------


def test_the_rule_is_registered_for_all() -> None:
    assert WHOLE_TREE_CHECKERS["makefile-credentials"] is lint.check_tree


def test_the_repository_makefile_has_no_finding() -> None:
    assert lint.check_tree(REPO_ROOT) == []


def test_the_gate_runs_the_rule_from_the_cli(tmp_path: pathlib.Path) -> None:
    (tmp_path / "Makefile").write_text("t:\n\tcmd $(CCF_TEST_POSTGRES_DSN)\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "tools.lints", "--all", "--base", str(tmp_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "makefile-credentials" in result.stdout
