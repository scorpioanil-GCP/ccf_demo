"""An ``ArgumentRefused`` raised inside dispatch is not THIS tool's argument refusal.

``TP-04`` follow-on (``D-IMPL-361``), from the integration review. The ADK
tool's ``run_async`` and the Claude in-process handler each wrapped the whole
of :meth:`~ccf.agents.agent.Agent.invoke_skill` in ``except ArgumentRefused``,
so an ``ArgumentRefused`` raised deep inside a ``local_callable``'s own
dispatch — about some OTHER surface the callable talks to — was rendered as
this tool's argument refusal: the harness was told its arguments were wrong
when they were not, and the dispatch failure was disguised as a governed
refusal.

What each leg already does with any other dispatch exception is measured here
first (the control): a ``RuntimeError`` raised by the callable propagates out
of the tool call. An inner ``ArgumentRefused`` must be treated the same way —
propagated, carrying the inner surface's name — never rendered as this tool's
refusal.

The deployment's callable registry is the composition root's (D-19); this
module registers a raising callable under the fixture entry's own
``callable_ref`` and holds no skill, grant or agent of its own (CLAUDE.md §6.4).
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable, Mapping
from typing import Any

import pytest

import conformance.test_harness_adapter as harness_suite
from ccf.agents.factory import AgentFactory
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SkillCatalogEntry
from ccf.skills.wire_arguments import UndeclaredArgumentRefused
from conformance.test_harness_adapter import (
    CLAUDE_ADAPTERS_BUILT,
    World,
    _harness_fixture,
    _tool_fixture,
    no_model_reachable,  # noqa: F401 - autouse socket guard, reused not copied
    remove_claude_prompt_directories,  # noqa: F401 - autouse teardown, reused
)
from conftest import harness_unavailable

pytestmark = [pytest.mark.harness]

#: The surface the callable's own inner refusal names — not the tool's.
INNER_SURFACE = "a-surface-the-callable-calls-not-this-tool"


def _raising_callable(failure: Callable[[], Exception]) -> Callable[[Mapping[str, str]], Any]:
    def callable_(arguments: Mapping[str, str]) -> Any:
        raise failure()

    return callable_


def _inner_refusal() -> Exception:
    return UndeclaredArgumentRefused(surface=INNER_SURFACE, undeclared=("inner_key",))


def _inner_runtime_error() -> Exception:
    return RuntimeError(INNER_SURFACE)


def _world(
    monkeypatch: pytest.MonkeyPatch, failure: Callable[[], Exception]
) -> tuple[World, str]:
    """A World whose agents resolve the local callable to one that raises ``failure``."""
    local: SkillCatalogEntry = harness_suite._parsed(
        _tool_fixture()["variants"]["local_callable"], harness_suite.SKILL_CATALOG_ENTRY
    )
    registry = CallableRegistry()
    registry.register(local.binding.callable_ref, _raising_callable(failure))  # type: ignore[union-attr]
    monkeypatch.setattr(
        harness_suite,
        "AgentFactory",
        functools.partial(AgentFactory, callable_registry=registry),
    )
    world = World()
    world.bind(world.grant_b, world.definition_b)
    assert world.grant_b.skill_name == local.name
    assert local.name in world.agent_b.bound_skill_names
    return world, local.name


def _declared() -> dict[str, str]:
    return dict(_tool_fixture()["dispatch"]["arguments"])


def _claude_call(world: World, skill_name: str) -> Any:
    harness_unavailable("claude_agent_sdk", "claude-agent")
    from ccf_runtime.adapters.claude_agent import ClaudeAgentAdapter

    values = _harness_fixture()["claude-agent"]
    adapter = ClaudeAgentAdapter(
        model=values["model"],
        mcp_server_name=values["mcp_server_name"],
        mcp_server_version=values["mcp_server_version"],
        effects="governed",
    )
    CLAUDE_ADAPTERS_BUILT.append(adapter)
    tool = adapter._skill_tool(world.agent_b, skill_name)
    return asyncio.run(tool.handler(_declared()))


def _adk_call(world: World, skill_name: str) -> Any:
    harness_unavailable("google.adk", "adk")
    from ccf_runtime.adapters.adk import AdkAdapter

    values = _harness_fixture()["adk"]
    adapter = AdkAdapter(
        model=values["model"],
        agent_name=values["agent_name"],
        session_id=values["session_id"],
        effects="governed",
    )
    carrier = adapter.inject_context(agent=world.agent_b, products=(), instructions=())
    tools = {tool.name: tool for tool in carrier.llm_agent.tools}  # type: ignore[attr-defined]
    return asyncio.run(tools[skill_name].run_async(args=_declared(), tool_context=None))


LEGS = {"claude-agent": _claude_call, "adk": _adk_call}


@pytest.mark.parametrize("leg", sorted(LEGS))
def test_the_control_another_dispatch_exception_propagates(
    leg: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What the leg already does for a dispatch failure: it propagates."""
    world, skill_name = _world(monkeypatch, _inner_runtime_error)
    with pytest.raises(RuntimeError, match=INNER_SURFACE):
        LEGS[leg](world, skill_name)


@pytest.mark.parametrize("leg", sorted(LEGS))
def test_an_argument_refusal_raised_inside_dispatch_is_not_this_tools_refusal(
    leg: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The inner refusal propagates like any dispatch failure, naming its own surface."""
    world, skill_name = _world(monkeypatch, _inner_refusal)
    try:
        rendered = LEGS[leg](world, skill_name)
    except UndeclaredArgumentRefused as refused:
        assert refused.surface == INNER_SURFACE
        return
    pytest.fail(
        f"{leg} rendered an ArgumentRefused raised inside {skill_name!r}'s dispatch"
        f" (about {INNER_SURFACE!r}) as this tool's argument refusal: {rendered!r}"
    )
