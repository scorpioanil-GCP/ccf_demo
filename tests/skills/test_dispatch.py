"""Skill dispatch — local_callable and tool work; mcp/a2a are NotYetBound (D-08).

What this suite holds ``src/ccf/skills/dispatch.py`` to:

* a ``local_callable`` entry resolves its dotted ``callable_ref`` and invokes
  it with the typed arguments, returning a typed result;
* a ``tool`` entry returns a typed invocation *value* carrying the descriptor
  command and arguments — the SDK ships no execution surface for commands,
  in the same returned-value discipline as ``Agent.emit_effect``;
* an ``mcp`` or ``a2a`` entry raises the typed ``NotYetBound`` exception
  (RESEARCH Open Question 2, RESOLVED): the build lacks the transport — I.3
  binds it — and nothing about the artifact is bad, which is why this is an
  exception (deployment shape) rather than a returned refusal (bad artifact).

All binding values, arguments, and expected outputs live in the skills
fixtures (§6.4); the fixture callable lives at the ref the entry declares
(T-05-18 — callables resolve only from registered catalog entries).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.errors import NotYetBound
from ccf.controlplane.artifacts import parse_artifact
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalogEntry
from ccf.skills.dispatch import SkillInvocation, ToolInvocation, dispatch_skill

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking" / "skills"


def _tool_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "covenant_metrics_tool.yaml").read_text()
    )
    return loaded


def _mcp_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "document_fetch_mcp.yaml").read_text()
    )
    return loaded


def _entry(document: dict[str, Any]) -> SkillCatalogEntry:
    parsed = parse_artifact(document, SKILL_CATALOG_ENTRY)
    assert isinstance(parsed, SkillCatalogEntry)
    return parsed


def test_a_local_callable_entry_resolves_and_invokes_with_typed_arguments() -> None:
    fixture = _tool_fixture()
    entry = _entry(fixture["variants"]["local_callable"])
    result = dispatch_skill(entry, arguments=fixture["dispatch"]["arguments"])
    assert isinstance(result, SkillInvocation)
    assert result.skill_name == entry.name
    assert result.skill_type == "local_callable"
    assert dict(result.output) == fixture["dispatch"]["expected_output"]


def test_a_tool_entry_returns_the_typed_invocation_value() -> None:
    """The invocation is a value the deployment carries onward — the SDK
    executes no command (mechanism, not an execution surface)."""
    fixture = _tool_fixture()
    entry = _entry(fixture["entry"])
    result = dispatch_skill(entry, arguments=fixture["dispatch"]["arguments"])
    assert isinstance(result, ToolInvocation)
    assert result.skill_name == entry.name
    assert result.command == fixture["entry"]["binding"]["command"]
    assert dict(result.arguments) == fixture["dispatch"]["arguments"]


def test_an_mcp_entry_raises_exactly_not_yet_bound() -> None:
    entry = _entry(_mcp_fixture()["entry"])
    with pytest.raises(NotYetBound) as excinfo:
        dispatch_skill(entry, arguments={})
    assert type(excinfo.value) is NotYetBound
    assert entry.name in str(excinfo.value)


def test_an_a2a_entry_raises_exactly_not_yet_bound() -> None:
    entry = _entry(_tool_fixture()["variants"]["a2a"])
    with pytest.raises(NotYetBound) as excinfo:
        dispatch_skill(entry, arguments={})
    assert type(excinfo.value) is NotYetBound


def test_not_yet_bound_is_a_typed_exception_not_a_refusal_value() -> None:
    """The refusal-vs-exception line, documented side: a granted, valid
    artifact whose transport this build lacks is a deployment-shape fact."""
    assert issubclass(NotYetBound, RuntimeError)
