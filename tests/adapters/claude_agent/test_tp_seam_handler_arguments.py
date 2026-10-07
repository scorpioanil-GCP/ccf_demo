"""The Claude leg's in-process handler applies the seam's argument rule (TP-04 follow-on).

``D-IMPL-361``. Task 3's review measured that the adapter's in-process handler
forwarded every key the harness supplied into
:meth:`ccf.agents.agent.Agent.invoke_skill`, which validated nothing against the
declared ``argument_schema`` — so an undeclared key was dispatched and audited.

What this module drives is the adapter-owned control: the handler the adapter
registered for the skill, awaited with the harness's arguments. (On the full
vendor route the ``mcp`` library's low-level server additionally validates the
arguments against the advertised ``inputSchema`` before the handler runs; that
is a vendor default, not an adapter-owned control, and TP-01 established that
the handler is the adapter's only control on this leg.)

The refusal is the adapter's ``is_error`` tool result carrying the seam's typed
refusal text, and nothing reaches :func:`ccf.skills.dispatch.dispatch_skill`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from conftest import harness_unavailable
from conformance.test_harness_adapter import (
    CLAUDE_ADAPTERS_BUILT,
    World,
    _harness_fixture,
    _tool_fixture,
    no_model_reachable,  # noqa: F401 - autouse socket guard, reused not copied
    remove_claude_prompt_directories,  # noqa: F401 - autouse teardown, reused
)

pytestmark = [pytest.mark.harness]

LEG = "claude-agent"

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


def _handle(arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Await the adapter's own in-process handler for the bound skill."""
    harness_unavailable("claude_agent_sdk", LEG)
    from ccf_runtime.adapters.claude_agent import ClaudeAgentAdapter

    values = _harness_fixture()[LEG]
    adapter = ClaudeAgentAdapter(
        model=values["model"],
        mcp_server_name=values["mcp_server_name"],
        mcp_server_version=values["mcp_server_version"],
        effects="governed",
    )
    CLAUDE_ADAPTERS_BUILT.append(adapter)
    world = World()
    world.bind(world.grant_a, world.definition_a)
    tool = adapter._skill_tool(world.agent_a, world.grant_a.skill_name)
    result: dict[str, Any] = asyncio.run(tool.handler(dict(arguments)))
    return result


def _declared() -> dict[str, str]:
    return dict(_tool_fixture()["dispatch"]["arguments"])


def _text(result: Mapping[str, Any]) -> str:
    return " ".join(str(item.get("text", "")) for item in result.get("content", ()))


def test_an_undeclared_argument_is_refused_by_the_handler_before_dispatch(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """(b): the undeclared key is refused with ``is_error``, by name; nothing dispatches."""
    result = _handle({**_declared(), UNDECLARED: "smuggled"})

    assert dispatched == [], (
        f"the handler forwarded an undeclared key into dispatch: {dispatched!r}"
        " (TP-04 follow-on, D-IMPL-361)"
    )
    assert result.get("is_error") is True, result
    assert UNDECLARED in _text(result)


def test_a_missing_required_argument_is_refused_by_the_handler(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """The handler refuses a call that leaves a required argument out."""
    result = _handle({})

    assert dispatched == [], f"a call missing its required argument dispatched: {dispatched!r}"
    assert result.get("is_error") is True, result
    assert next(iter(_declared())) in _text(result)


def test_a_wrong_typed_argument_is_refused_by_the_handler(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """A list where ``string`` is declared is refused, not stringified and dispatched."""
    name, value = next(iter(_declared().items()))

    result = _handle({name: [value]})

    assert dispatched == [], f"a wrong-typed argument was stringified and dispatched: {dispatched!r}"
    assert result.get("is_error") is True, result
    assert name in _text(result)


def test_the_control_a_declared_call_dispatches(dispatched: list[Mapping[str, Any]]) -> None:
    """The positive control: the declared call is not refused."""
    result = _handle(_declared())

    assert dispatched == [_declared()]
    assert not result.get("is_error"), result
