"""The ADK leg applies the seam's whole argument rule, not only the undeclared-key half.

``TP-04`` follow-on (``D-IMPL-361``). Task 3 made ``_DeclaredSkillTool.run_async``
refuse undeclared keys, and its review measured the rest: a call MISSING a
required argument still dispatched, and no type check ran — the adapter
stringified every value, so a list where ``string`` is declared passed as its
``str``. The ruling is one rule at the seam
(:meth:`ccf.agents.agent.Agent.invoke_skill`), with the ADK leg delegating to it
and rendering its refusal as the adapter's own ``EffectRefusal``.

Driven through ADK's own ``run_async`` on the tool the adapter placed on the
``LlmAgent`` (see ``test_adk_wire_arguments.py`` for why ``tool_context=None``).
"Dispatched" means :func:`ccf.skills.dispatch.dispatch_skill` was called.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from conformance.test_harness_adapter import World, _harness_fixture, _tool_fixture
from conftest import harness_unavailable


@pytest.fixture
def dispatched(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Mapping[str, Any]]]:
    """Every argument mapping that reached ``dispatch_skill``."""
    import ccf.skills.dispatch as dispatch_module

    reached: list[Mapping[str, Any]] = []
    original = dispatch_module.dispatch_skill

    def recording(entry: Any, *, arguments: Mapping[str, Any], **kwargs: Any) -> Any:
        reached.append(dict(arguments))
        return original(entry, arguments=arguments, **kwargs)

    monkeypatch.setattr(dispatch_module, "dispatch_skill", recording)
    yield reached


def _run(args: dict[str, Any]) -> tuple[Any, World]:
    harness_unavailable("google.adk", "adk")
    from ccf_runtime.adapters.adk import AdkAdapter

    world = World()
    world.bind(world.grant_a, world.definition_a)
    values = _harness_fixture()["adk"]
    adapter = AdkAdapter(
        model=values["model"],
        agent_name=values["agent_name"],
        session_id=values["session_id"],
        effects="governed",
    )
    carrier = adapter.inject_context(agent=world.agent_a, products=(), instructions=())
    tools = {tool.name: tool for tool in carrier.llm_agent.tools}  # type: ignore[attr-defined]
    tool = tools[world.grant_a.skill_name]
    return asyncio.run(tool.run_async(args=args, tool_context=None)), world


def _declared() -> dict[str, str]:
    return dict(_tool_fixture()["dispatch"]["arguments"])


def _refusal_reason(result: Any, world: World) -> str:
    from ccf.harness.protocol import EffectRefusal
    from ccf_runtime.adapters.adk import HARNESS_ID, REFUSAL_RESPONSE_KEY

    assert isinstance(result, dict) and set(result) == {REFUSAL_RESPONSE_KEY}, result
    refusal = EffectRefusal.model_validate_json(result[REFUSAL_RESPONSE_KEY])
    assert refusal.harness_id == HARNESS_ID
    assert refusal.agent_definition_hash == world.agent_a.identity.definition_hash
    return refusal.reason


def test_a_missing_required_argument_is_refused_not_dispatched(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """(c): a required argument left out is a typed refusal naming it; nothing dispatches."""
    result, world = _run({})

    assert dispatched == [], (
        f"a call missing its required argument dispatched: {dispatched!r}"
        " (TP-04 follow-on, D-IMPL-361)"
    )
    assert next(iter(_declared())) in _refusal_reason(result, world)


def test_a_wrong_typed_argument_is_refused_not_stringified(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """A list where ``string`` is declared is refused, not dispatched as its ``str``."""
    name, value = next(iter(_declared().items()))

    result, world = _run({name: [value]})

    assert dispatched == [], f"a wrong-typed argument was stringified and dispatched: {dispatched!r}"
    assert name in _refusal_reason(result, world)
