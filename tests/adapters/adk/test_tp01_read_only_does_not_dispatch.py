"""TP-01 on the ADK leg — a read-only binding must not dispatch (D-IMPL-361, I-1).

The controller's ruling on the whole-branch review's I-1: ``effects:
unsupported`` means NO DISPATCH and no write-back, on every leg. On ADK the only
refusal was the ``LlmAgent``'s ``before_tool_callback``; the tool itself
(``_DeclaredSkillTool.run_async``) never checked effects, so a deployment that
reuses ``carrier.llm_agent.tools`` under another agent (or any caller of
``run_async``) dispatches.

This test drives the tool's own ``run_async`` with the skill's declared
arguments — with no callback in the way — and asserts
:meth:`ccf.agents.agent.Agent.invoke_skill` is never reached with arguments.
``tool_context=None`` as in ``test_adk_wire_arguments.py``. Offline.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from ccf.agents.agent import Agent
from conformance.test_harness_adapter import World, _agent_fixture, _harness_fixture
from conftest import harness_unavailable

pytestmark = [pytest.mark.harness]


@pytest.fixture
def dispatches(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Mapping[str, Any]]]:
    """Every call that reached the fabric's dispatch seam, by its arguments."""
    reached: list[Mapping[str, Any]] = []
    original = Agent.invoke_skill

    def recording(self: Agent, name: str, *, arguments: Any = None) -> Any:
        if arguments is not None:
            reached.append(dict(arguments))
        return original(self, name, arguments=arguments)

    monkeypatch.setattr(Agent, "invoke_skill", recording)
    yield reached


def _run(effects: str) -> tuple[Any, World]:
    harness_unavailable("google.adk", "adk")
    from ccf_runtime.adapters.adk import AdkAdapter

    world = World()
    world.bind(world.grant_a, world.definition_a)
    values = _harness_fixture()["adk"]
    adapter = AdkAdapter(
        model=values["model"],
        agent_name=values["agent_name"],
        session_id=values["session_id"],
        effects=effects,  # type: ignore[arg-type]
    )
    carrier = adapter.inject_context(agent=world.agent_a, products=(), instructions=())
    tools = {tool.name: tool for tool in carrier.llm_agent.tools}  # type: ignore[attr-defined]
    tool = tools[world.grant_a.skill_name]
    declared = dict(_agent_fixture()["slice"]["granted_skill"]["arguments"])
    return asyncio.run(tool.run_async(args=declared, tool_context=None)), world


def test_a_read_only_binding_does_not_dispatch_through_the_tool_itself(
    dispatches: list[Mapping[str, Any]],
) -> None:
    """TP-01 as worded, independent of the ``before_tool`` callback."""
    from ccf.harness.protocol import EffectRefusal
    from ccf_runtime.adapters.adk import HARNESS_ID, REFUSAL_RESPONSE_KEY

    result, world = _run("unsupported")

    assert dispatches == [], (
        "an ADK binding declaring effects: unsupported reached Agent.invoke_skill"
        f" with arguments {dispatches!r} through _DeclaredSkillTool.run_async"
        " (TP-01, I-1, D-IMPL-361)"
    )
    assert isinstance(result, dict) and set(result) == {REFUSAL_RESPONSE_KEY}, result
    refusal = EffectRefusal.model_validate_json(result[REFUSAL_RESPONSE_KEY])
    assert refusal.harness_id == HARNESS_ID
    assert refusal.agent_definition_hash == world.agent_a.identity.definition_hash
    assert "effects='unsupported'" in refusal.reason


def test_a_governed_binding_still_dispatches_the_bound_skill(
    dispatches: list[Mapping[str, Any]],
) -> None:
    """The inversion: the control refuses read-only, not everything."""
    _run("governed")

    assert dispatches == [dict(_agent_fixture()["slice"]["granted_skill"]["arguments"])]
