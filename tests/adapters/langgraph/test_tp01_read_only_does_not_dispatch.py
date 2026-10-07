"""TP-01 on the LangGraph leg — a read-only binding must not dispatch (D-IMPL-361, I-1).

The controller's ruling on the whole-branch review's I-1: ``effects:
unsupported`` means NO DISPATCH and no write-back, on every leg. The LangGraph
carrier exposes its :class:`~langgraph.prebuilt.ToolNode` as ``carrier.tools``
"so a deployment can wire it into its own topology", and a deployment that does
so calls the tools directly — the adapter-owned effect node is never on that
path. Measured at 80e9f7d9 by the review: a ``LangGraphAdapter(effects=
"unsupported")`` tool, invoked with the skill's declared arguments, reached
``dispatch_skill``.

So the only adapter-owned control on that path is inside the tool callable,
and this test drives exactly it: ``carrier.tools.tools_by_name[skill].invoke``
with the declared arguments (what the ``ToolNode`` itself calls). "Dispatched"
means :meth:`ccf.agents.agent.Agent.invoke_skill` was called with arguments.
Offline: no model, no graph run.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from ccf.agents.agent import Agent
from conformance.test_harness_adapter import World, _agent_fixture, _harness_fixture
from conftest import harness_unavailable

pytestmark = [pytest.mark.harness]

LEG = "langgraph"


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


def _adapter(effects: str) -> Any:
    harness_unavailable("langgraph", LEG)
    from ccf_runtime.adapters.langgraph import LangGraphAdapter

    values = _harness_fixture()[LEG]
    return LangGraphAdapter(
        model=values["model"],
        thread_id=values["thread_id"],
        run_tags=tuple(values["run_tags"]),
        effects=effects,  # type: ignore[arg-type]
    )


def _declared_arguments() -> dict[str, str]:
    return dict(_agent_fixture()["slice"]["granted_skill"]["arguments"])


def _refusal(result: object, world: World) -> str:
    """The typed refusal the tool returned, by its reason; asserts its shape."""
    from ccf.harness.protocol import EffectRefusal
    from ccf_runtime.adapters.langgraph import HARNESS_ID

    assert isinstance(result, str), f"the tool did not answer with a refusal: {result!r}"
    refusal = EffectRefusal.model_validate_json(result)
    assert refusal.harness_id == HARNESS_ID
    assert refusal.agent_definition_hash == world.agent_a.identity.definition_hash
    return refusal.reason


def test_a_read_only_binding_does_not_dispatch_through_the_carrier_tools(
    dispatches: list[Mapping[str, Any]],
) -> None:
    """TP-01 as worded, on the path a deployment wires: ``carrier.tools``."""
    world = World()
    world.bind(world.grant_a, world.definition_a)
    carrier = _adapter("unsupported").inject_context(
        agent=world.agent_a, products=(), instructions=()
    )
    tool = carrier.tools.tools_by_name[world.grant_a.skill_name]

    result = tool.invoke(_declared_arguments())

    assert dispatches == [], (
        "a LangGraph binding declaring effects: unsupported reached"
        f" Agent.invoke_skill with arguments {dispatches!r} through carrier.tools"
        " (TP-01, I-1, D-IMPL-361)"
    )
    assert "effects='unsupported'" in _refusal(result, world)


def test_a_revoked_skill_does_not_dispatch_through_the_carrier_tools(
    dispatches: list[Mapping[str, Any]],
) -> None:
    """The second condition, at call time: revoked after the carrier was built."""
    from tests.skills.authority import revoke_capability

    world = World()
    grant_hash = world.bind(world.grant_a, world.definition_a)
    carrier = _adapter("governed").inject_context(
        agent=world.agent_a, products=(), instructions=()
    )
    tool = carrier.tools.tools_by_name[world.grant_a.skill_name]
    world.ledger.revoke(
        revoke_capability(
            grant_hash, tenant=world.definition_a.tenant, principal=world.actor
        )
    )
    assert world.grant_a.skill_name not in world.agent_a.bound_skill_names

    result = tool.invoke(_declared_arguments())

    assert dispatches == []
    assert "bound skill-set" in _refusal(result, world)


def test_a_governed_binding_still_dispatches_the_bound_skill(
    dispatches: list[Mapping[str, Any]],
) -> None:
    """The inversion: the control refuses read-only, not everything."""
    world = World()
    world.bind(world.grant_a, world.definition_a)
    carrier = _adapter("governed").inject_context(
        agent=world.agent_a, products=(), instructions=()
    )

    carrier.tools.tools_by_name[world.grant_a.skill_name].invoke(_declared_arguments())

    assert dispatches == [_declared_arguments()]
