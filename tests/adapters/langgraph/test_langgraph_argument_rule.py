"""The LangGraph leg's tool call path applies the seam's argument rule (TP-04 follow-on).

``D-IMPL-361``. Measured before this module existed: the adapter's
``StructuredTool`` is built with the declared schema as a plain JSON-Schema
``args_schema``, which langchain-core does not validate, and the tool callable
took ``**arguments`` and stringified every value — so an undeclared key, a
missing required argument and a wrong-typed value all reached
:func:`ccf.skills.dispatch.dispatch_skill` and the audited invocation.

The ruling is one rule at the seam (:meth:`ccf.agents.agent.Agent.invoke_skill`).
On this leg the refusal is the seam's typed
:class:`~ccf.skills.wire_arguments.ArgumentRefused`, raised out of the tool call
— fail-closed — and nothing dispatches. Driven through the tool the adapter
placed in its ``ToolNode``, with ``StructuredTool.invoke`` (the call the node
makes with the model's arguments). Offline: no model, no graph run.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from conformance.test_harness_adapter import World, _harness_fixture, _tool_fixture
from conftest import harness_unavailable

pytestmark = [pytest.mark.harness]

#: A key the fixture entry's ``argument_schema`` does not declare.
UNDECLARED = "not_declared_by_this_skill"


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


def _invoke(arguments: Mapping[str, Any]) -> BaseException | None:
    harness_unavailable("langgraph", "langgraph")
    from ccf_runtime.adapters.langgraph import LangGraphAdapter

    values = _harness_fixture()["langgraph"]
    adapter = LangGraphAdapter(
        model=values["model"],
        thread_id=values["thread_id"],
        run_tags=tuple(values["run_tags"]),
        effects="governed",
    )
    world = World()
    world.bind(world.grant_a, world.definition_a)
    tool = adapter._tool_node(world.agent_a).tools_by_name[world.grant_a.skill_name]
    try:
        tool.invoke(dict(arguments))
    except Exception as raised:  # noqa: BLE001 - the type is asserted after the hole
        return raised
    return None


def _declared() -> dict[str, str]:
    return dict(_tool_fixture()["dispatch"]["arguments"])


def _assert_refused(
    raised: BaseException | None, reached: list[Mapping[str, Any]], *, key: str
) -> None:
    assert reached == [], (
        f"the LangGraph tool call dispatched {reached!r} (TP-04 follow-on, D-IMPL-361)"
    )
    from ccf.skills.wire_arguments import ArgumentRefused

    assert isinstance(raised, ArgumentRefused), f"not the typed refusal: {raised!r}"
    assert key in str(raised)


def test_an_undeclared_argument_is_refused_not_dispatched(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """(d): an undeclared key is refused by name."""
    raised = _invoke({**_declared(), UNDECLARED: "smuggled"})

    _assert_refused(raised, dispatched, key=UNDECLARED)


def test_a_missing_required_argument_is_refused_not_dispatched(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """(d): a required argument left out is refused by name."""
    raised = _invoke({})

    _assert_refused(raised, dispatched, key=next(iter(_declared())))


def test_a_wrong_typed_argument_is_refused_not_stringified(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """(d): a list where ``string`` is declared is refused by name."""
    name, value = next(iter(_declared().items()))

    raised = _invoke({name: [value]})

    _assert_refused(raised, dispatched, key=name)


def test_the_control_a_declared_call_dispatches(dispatched: list[Mapping[str, Any]]) -> None:
    """The positive control: the declared call is not refused."""
    raised = _invoke(_declared())

    assert raised is None, raised
    assert dispatched == [_declared()]
