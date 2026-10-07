"""TP-04 — the ADK leg carries declared arguments and refuses undeclared ones.

``D-IMPL-361`` rates ``TP-04``: *"one leg drops every model-supplied argument
and audits an empty mapping."* Measured against google-adk 2.5.0 before this
module existed: ``FunctionTool._prepare_invocation_args``
(``google/adk/tools/function_tool.py:220-224``) filters the model's arguments
to ``inspect.signature(self.func).parameters``, and the adapter's tool callable
was ``call(**arguments: str)`` — whose only parameter NAME is ``arguments`` —
so every declared argument was filtered out and
:meth:`~ccf.agents.agent.Agent.invoke_skill` received the empty mapping. An
undeclared argument was dropped by the same filter, silently.

The ruling (Global Constraint 7 of the TP-01…05 plan): **declared arguments
arrive; undeclared ones are REFUSED, never dropped.** Both halves are asserted
here, through ADK's own ``run_async`` — the method ADK's flow calls with the
model's ``args`` — on the tool the adapter actually placed on the ``LlmAgent``.
``tool_context=None`` is what is passed: the vendor run path dereferences the
context only when a tool requires confirmation, and these tools do not.

Every agent, grant, skill and argument value comes from the banking fixtures
through the Agent Factory (the conformance suite's ``World``); the undeclared
key below is test vocabulary, meaningful nowhere else.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from conformance.test_harness_adapter import World, _harness_fixture, _tool_fixture
from conftest import harness_unavailable

#: A key the fixture entry's ``argument_schema`` does not declare. Test
#: vocabulary: what matters is only that the declared world does not name it.
UNDECLARED = "not_declared_by_this_skill"


class _Leg:
    """One governed ADK binding of the fixture agent, and a dispatch spy."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
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
        self.agent = world.agent_a
        self.skill_name = world.grant_a.skill_name
        self.declared: dict[str, str] = dict(_tool_fixture()["dispatch"]["arguments"])

        # Every dispatch the tool performs, as the fabric received it. The
        # introspection form (no ``arguments``) is the adapter resolving the
        # bound entry and is not a dispatch, so it is not recorded.
        self.dispatched: list[dict[str, str]] = []
        original = self.agent.invoke_skill

        def spy(name: str, *, arguments: Any = None) -> Any:
            if arguments is not None:
                self.dispatched.append(dict(arguments))
            return original(name, arguments=arguments)

        monkeypatch.setattr(self.agent, "invoke_skill", spy)

        carrier = adapter.inject_context(agent=self.agent, products=(), instructions=())
        tools = {tool.name: tool for tool in carrier.llm_agent.tools}  # type: ignore[attr-defined]
        self.tool = tools[self.skill_name]

    def run(self, args: dict[str, Any]) -> Any:
        """ADK's own run path, with the model-supplied ``args``."""
        return asyncio.run(self.tool.run_async(args=args, tool_context=None))


def test_a_declared_argument_reaches_invoke_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    """TP-04 (a): the model's declared argument is what the fabric dispatches.

    Asserted on the mapping ``invoke_skill`` received AND on the invocation it
    returned, so a leg that dispatched the right mapping but returned another
    (or the reverse) fails here.
    """
    leg = _Leg(monkeypatch)

    result = leg.run(dict(leg.declared))

    assert leg.dispatched == [leg.declared]
    invocation = json.loads(result)
    assert invocation["skill_name"] == leg.skill_name
    assert invocation["arguments"] == leg.declared


def test_an_undeclared_argument_is_refused_not_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TP-04 (b): an undeclared key is a typed refusal naming it; nothing dispatches.

    The refusal is the adapter's own ``EffectRefusal`` in the shape ADK
    short-circuits a tool call with (``REFUSAL_RESPONSE_KEY``), so the model
    and the audit see the same governed "no" the before-tool gate gives.
    """
    from ccf.harness.protocol import EffectRefusal
    from ccf_runtime.adapters.adk import HARNESS_ID, REFUSAL_RESPONSE_KEY

    leg = _Leg(monkeypatch)

    result = leg.run({**leg.declared, UNDECLARED: "smuggled"})

    assert leg.dispatched == [], "an undeclared argument reached the fabric"
    assert isinstance(result, dict) and set(result) == {REFUSAL_RESPONSE_KEY}, result
    refusal = EffectRefusal.model_validate_json(result[REFUSAL_RESPONSE_KEY])
    assert refusal.harness_id == HARNESS_ID
    assert refusal.agent_definition_hash == leg.agent.identity.definition_hash
    assert UNDECLARED in refusal.reason


def test_the_refusal_control_a_fully_declared_call_is_not_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The positive control for (b): the same call minus the extra key dispatches.

    Without it, a tool that refused everything would pass (b).
    """
    leg = _Leg(monkeypatch)

    result = leg.run(dict(leg.declared))

    assert isinstance(result, str), result
    assert len(leg.dispatched) == 1
