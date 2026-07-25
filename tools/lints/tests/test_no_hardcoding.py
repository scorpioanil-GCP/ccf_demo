"""Unit tests for the CINV-01 No-Hardcoding checker (CLAUDE.md §6.4, D-06/D-08)."""

from __future__ import annotations

import hashlib
import pathlib
import textwrap

import pytest

from tools.lints.no_hardcoding import (
    RULE_FACTORY_BYPASS,
    RULE_NUMERIC_TABLE,
    RULE_PROMPT_SHAPE,
    Allowlist,
    AllowlistEntry,
    apply_allowlist,
    check_source,
    fingerprint,
    load_allowlist,
)

SRC = pathlib.Path("src/ccf/operators/traversal.py")


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


def _src(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


# --- CINV-01a prompt shape -------------------------------------------------

PROMPT = (
    "You are a diligent credit analyst. Always ground every claim in the "
    "provided context product. Never speculate beyond the evidence you are "
    "given, and respond with a structured verdict for {entity} as of "
    "{as_of} under {policy_bundle}."
)


def test_prompt_shaped_literal_is_flagged() -> None:
    findings = check_source(f"SYSTEM = {PROMPT!r}\n", SRC, "ccf.operators.traversal")
    assert _rules(findings) == [RULE_PROMPT_SHAPE]


def test_short_message_literal_is_not_flagged() -> None:
    source = 'MESSAGE = "entity not found"\n'
    assert check_source(source, SRC, "ccf.operators.traversal") == []


def test_sql_literal_is_not_flagged() -> None:
    source = _src(
        """
        QUERY = (
            "SELECT entity_uri, valid_from, valid_to FROM entities "
            "WHERE tenant_id = ? AND entity_uri = ? ORDER BY valid_from DESC"
        )
        """
    )
    assert check_source(source, SRC, "ccf.operators.traversal") == []


def test_module_docstring_is_never_flagged() -> None:
    source = f'"""{PROMPT}"""\n'
    assert check_source(source, SRC, "ccf.operators.traversal") == []


def test_function_docstring_is_never_flagged() -> None:
    source = f'def f():\n    """{PROMPT}"""\n    return 1\n'
    assert check_source(source, SRC, "ccf.operators.traversal") == []


# --- CINV-01b numeric tables ----------------------------------------------


def test_module_level_numeric_table_is_flagged() -> None:
    source = _src(
        """
        HALF_LIVES = {
            "account_balance": 0.5,
            "address_change": 30.0,
            "employment_status": 90.0,
        }
        """
    )
    findings = check_source(source, SRC, "ccf.operators.traversal")
    assert _rules(findings) == [RULE_NUMERIC_TABLE]


def test_module_level_numeric_list_is_flagged() -> None:
    source = "THRESHOLDS = [0.85, 0.75, 0.65, 0.55]\n"
    assert _rules(check_source(source, SRC, "ccf.operators.traversal")) == [
        RULE_NUMERIC_TABLE
    ]


def test_non_numeric_mapping_is_not_flagged() -> None:
    source = 'BACKENDS = {"sqlite": SqliteStore, "postgres": PostgresStore}\n'
    assert check_source(source, SRC, "ccf.operators.traversal") == []


def test_numeric_table_inside_a_function_is_not_module_level() -> None:
    source = "def f():\n    counts = {'a': 1, 'b': 2, 'c': 3}\n    return counts\n"
    assert check_source(source, SRC, "ccf.operators.traversal") == []


def test_numeric_default_on_a_parameter_schema_field_is_flagged() -> None:
    source = "class DebtParams(BaseModel):\n    threshold: float = 0.85\n"
    path = pathlib.Path("src/ccf/debt/params.py")
    assert _rules(check_source(source, path, "ccf.debt.params")) == [
        RULE_NUMERIC_TABLE
    ]


def test_numeric_default_outside_a_parameter_schema_module_is_not_flagged() -> None:
    source = "class Page(BaseModel):\n    limit: int = 50\n"
    assert check_source(source, SRC, "ccf.operators.traversal") == []


# --- CINV-01c factory bypass ----------------------------------------------


def test_agent_construction_outside_a_factory_is_flagged() -> None:
    source = 'a = Agent("credit-analyst")\n'
    assert _rules(check_source(source, SRC, "ccf.operators.traversal")) == [
        RULE_FACTORY_BYPASS
    ]


def test_task_construction_inside_a_factory_module_is_allowed() -> None:
    source = "t = Task(spec)\n"
    path = pathlib.Path("src/ccf/agents/factory.py")
    assert check_source(source, path, "ccf.agents.factory") == []


# --- D-08 allowlist --------------------------------------------------------


def test_fingerprint_is_sha256_of_the_literal_value() -> None:
    assert fingerprint("hello") == hashlib.sha256(b"hello").hexdigest()
    assert fingerprint("hello") == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def _entry(rule: str, literal: str, file: str = str(SRC)) -> AllowlistEntry:
    return AllowlistEntry(
        file=file,
        rule=rule,
        fingerprint=fingerprint(literal),
        reason="reviewed exception",
        reviewer="dave",
    )


def test_allowlist_entry_suppresses_an_exact_match() -> None:
    findings = check_source(f"SYSTEM = {PROMPT!r}\n", SRC, "ccf.operators.traversal")
    allowlist = Allowlist([_entry(RULE_PROMPT_SHAPE, PROMPT)])
    assert apply_allowlist(findings, allowlist) == []


def test_allowlist_entry_for_another_file_does_not_suppress() -> None:
    findings = check_source(f"SYSTEM = {PROMPT!r}\n", SRC, "ccf.operators.traversal")
    allowlist = Allowlist([_entry(RULE_PROMPT_SHAPE, PROMPT, file="src/ccf/other.py")])
    assert apply_allowlist(findings, allowlist) == findings


def test_allowlist_entry_for_another_rule_does_not_suppress() -> None:
    findings = check_source(f"SYSTEM = {PROMPT!r}\n", SRC, "ccf.operators.traversal")
    allowlist = Allowlist([_entry(RULE_NUMERIC_TABLE, PROMPT)])
    assert apply_allowlist(findings, allowlist) == findings


def test_allowlist_entry_with_a_stale_fingerprint_does_not_suppress() -> None:
    findings = check_source(f"SYSTEM = {PROMPT!r}\n", SRC, "ccf.operators.traversal")
    allowlist = Allowlist([_entry(RULE_PROMPT_SHAPE, PROMPT + " drifted")])
    assert apply_allowlist(findings, allowlist) == findings


def test_shipped_allowlist_parses_and_is_empty() -> None:
    allowlist = load_allowlist()
    assert allowlist.entries == []


def test_allowlist_entry_missing_a_reviewer_is_rejected() -> None:
    with pytest.raises(ValueError):
        Allowlist.from_raw(
            [
                {
                    "file": str(SRC),
                    "rule": RULE_PROMPT_SHAPE,
                    "fingerprint": fingerprint(PROMPT),
                    "reason": "no reviewer named",
                }
            ]
        )
