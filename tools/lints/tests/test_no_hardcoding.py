"""Unit tests for the CINV-01 No-Hardcoding checker (CLAUDE.md §6.4, D-06/D-08)."""

from __future__ import annotations

import hashlib
import pathlib
import textwrap

import pytest

from tools.lints.no_hardcoding import (
    DIAGNOSTIC_MARKERS,
    RULE_FACTORY_BYPASS,
    RULE_NUMERIC_TABLE,
    RULE_PROMPT_SHAPE,
    Allowlist,
    AllowlistEntry,
    addresses_a_reader,
    apply_allowlist,
    check_source,
    fingerprint,
    is_developer_diagnostic,
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


# --- CINV-01a: prompt vs developer diagnostic (Dave, 2026-08-04) -----------
#
# The ruling these tests pin: "a prompt is a string sent to a model; a
# diagnostic is a string shown to a developer", and the two are separated by
# rule refinement rather than by allowlist entries (plan 15-03 Task 4
# checkpoint; implemented in 15-04). Both directions are asserted here — a
# refinement proven only on the strings it was asked to stop flagging is not
# proven at all.

#: Verbatim shape of ``tests/http_api/test_openapi.py``'s ``_DRIFT_MESSAGE``:
#: multi-sentence, impersonal, naming the command that regenerates the
#: artifact. One of the two sites the ruling names.
DIAGNOSTIC = (
    "The committed openapi.json no longer matches what create_app() emits."
    " Run `make openapi` and commit the result. A moved endpoint or a"
    " FastAPI/Pydantic version bump legitimately changes the published"
    " contract — that diff is reviewable and desirable, not a test bug."
)

#: A prompt dressed in every developer-toolchain marker the discriminator
#: looks for. It must still be refused: the markers alone never excuse a
#: literal that addresses a reader.
PROMPT_WEARING_DIAGNOSTIC_MARKERS = (
    "You are a covenant analyst. Read the `make report` output from"
    " docs/policy.yaml and call render() before answering. Never speculate"
    " beyond the evidence you are given, and always cite the passage."
)


def test_a_developer_diagnostic_is_not_a_prompt() -> None:
    """The negative direction: the refinement clears the real sites."""
    assert is_developer_diagnostic(DIAGNOSTIC)
    source = f"_DRIFT_MESSAGE = {DIAGNOSTIC!r}\n"
    assert check_source(source, SRC, "ccf.operators.traversal") == []


def test_a_prompt_wearing_diagnostic_markers_is_still_flagged() -> None:
    """The positive direction: the rule still catches a genuine prompt.

    A refinement that can be defeated by mentioning a filename would have
    replaced a false-positive problem with a false-negative one.
    """
    assert not is_developer_diagnostic(PROMPT_WEARING_DIAGNOSTIC_MARKERS)
    source = f"SYSTEM = {PROMPT_WEARING_DIAGNOSTIC_MARKERS!r}\n"
    findings = check_source(source, SRC, "ccf.operators.traversal")
    assert _rules(findings) == [RULE_PROMPT_SHAPE]


def test_the_discriminator_needs_both_halves() -> None:
    """Neither half alone decides — impersonal prose without a toolchain
    marker is not a diagnostic, and second-person address is not enough to
    make one."""
    impersonal_prose_without_markers = (
        "The covenant headroom narrowed materially over the quarter."
        " Every claim must be grounded in the evidence provided."
        " Speculation beyond that evidence is not acceptable."
    )
    assert not is_developer_diagnostic(impersonal_prose_without_markers)
    assert addresses_a_reader(PROMPT)
    assert not addresses_a_reader(DIAGNOSTIC)


def test_every_diagnostic_marker_is_individually_sufficient() -> None:
    """Each marker in DIAGNOSTIC_MARKERS carries the classification alone,
    so the tuple is an enumerable discriminator rather than one regex with
    two unreachable siblings."""
    carriers = (
        "The committed artifact drifted. Run `make surface` and commit it."
        " That diff is reviewable, not a bug.",
        "The committed docs/surface/v0.2-surface.json no longer agrees with"
        " the live tree. Regenerate it. That diff is reviewable, not a bug.",
        "The document emitted by create_app() no longer agrees with the"
        " committed copy. Regenerate it. That diff is reviewable, not a bug.",
    )
    assert len(carriers) == len(DIAGNOSTIC_MARKERS)
    for text in carriers:
        assert is_developer_diagnostic(text), text
        assert check_source(f"M = {text!r}\n", SRC, "ccf.operators.traversal") == []


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


def test_shipped_allowlist_parses_and_entries_are_reviewed() -> None:
    """The shipped allowlist parses; every entry is complete and CINV-01-scoped.

    Superseded posture (plan 08-04): the list is no longer required to be
    empty — the ADK ``Workflow`` migration (D-14) carries two reviewed
    cinv01c entries for ``google.adk.workflow.Workflow``, the harness's own
    topology object name-colliding with CCF's factory-only ``Workflow``.
    """
    allowlist = load_allowlist()
    for entry in allowlist.entries:
        assert entry.rule.startswith("cinv01")
        assert entry.reviewer
        assert entry.reason
        assert len(entry.fingerprint) == 64


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
