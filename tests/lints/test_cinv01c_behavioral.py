"""Behavioral proof the CINV-01c factory-bypass lint fires (D-12; CLAUDE.md §6.4).

D-12 makes the lint the no-bypass **mechanism of record** — no runtime
construction token exists. A mechanism of record that has never been observed
firing is vacuous, so this module writes synthetic bypassing modules to real
files and runs the shipped checker over them, asserting the
``cinv01c-factory-bypass`` finding fires (and does not fire) exactly per the
rule: ``Agent(...)`` / ``Task(...)`` construction outside a factory module is
a finding; the same construction inside a factory-marked path is not; and a
simple module-level alias of a factory-only name is caught rather than being
a silent hole.

The final test runs the full lint over the real tree, proving the rule's
zero-findings state is an observation, not an assumption.
"""

from __future__ import annotations

import pathlib

from tools.lints.no_hardcoding import RULE_FACTORY_BYPASS, check
from tools.lints.__main__ import run as run_lints

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _findings_for(tmp_path: pathlib.Path, source: str, filename: str) -> list[str]:
    """Write ``source`` to a real file under ``tmp_path`` and lint it."""
    target = tmp_path / filename
    target.write_text(source, encoding="utf-8")
    module_name = filename.removesuffix(".py")
    return check(target, module_name)


def _rules(findings: list[str]) -> list[str]:
    return [finding.split()[1] for finding in findings]


def test_agent_construction_outside_a_factory_fires_the_lint(
    tmp_path: pathlib.Path,
) -> None:
    findings = _findings_for(
        tmp_path, 'agent = Agent("bypass")\n', "sneaky_module.py"
    )
    assert _rules(findings) == [RULE_FACTORY_BYPASS]
    assert "Agent construction outside a factory" in findings[0]


def test_task_construction_outside_a_factory_fires_the_lint(
    tmp_path: pathlib.Path,
) -> None:
    findings = _findings_for(
        tmp_path, "task = Task(definition)\n", "sneaky_module.py"
    )
    assert _rules(findings) == [RULE_FACTORY_BYPASS]
    assert "Task construction outside a factory" in findings[0]


def test_construction_inside_a_factory_module_yields_no_finding(
    tmp_path: pathlib.Path,
) -> None:
    source = 'agent = Agent("legitimate")\ntask = Task(definition)\n'
    findings = _findings_for(tmp_path, source, "task_factory.py")
    assert findings == []


def test_a_module_level_alias_of_a_factory_only_name_is_caught(
    tmp_path: pathlib.Path,
) -> None:
    """``A = Agent; A(...)`` must not be a silent hole in the rule.

    The D-12 residual Dave accepted is *dynamic* construction
    (``globals()['Agent']``, importlib) — not a one-line static alias the
    AST can see. Extending cinv01c to simple module-level aliasing keeps the
    accepted residual exactly as ruled, no wider.
    """
    source = "A = Agent\nagent = A('aliased-bypass')\n"
    findings = _findings_for(tmp_path, source, "sneaky_module.py")
    assert _rules(findings) == [RULE_FACTORY_BYPASS]


def test_an_alias_inside_a_factory_module_yields_no_finding(
    tmp_path: pathlib.Path,
) -> None:
    source = "A = Agent\nagent = A('legitimate')\n"
    assert _findings_for(tmp_path, source, "task_factory.py") == []


def test_an_unrelated_module_level_alias_is_not_flagged(
    tmp_path: pathlib.Path,
) -> None:
    source = "B = Backend\nbackend = B('sqlite')\n"
    assert _findings_for(tmp_path, source, "sneaky_module.py") == []


def test_the_real_tree_yields_zero_factory_bypass_findings() -> None:
    """The zero-findings state of the shipped tree is observed, not assumed."""
    findings = run_lints(REPO_ROOT, ["no-hardcoding"])
    assert [f for f in findings if RULE_FACTORY_BYPASS in f] == []
