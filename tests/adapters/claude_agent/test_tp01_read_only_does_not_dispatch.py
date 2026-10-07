"""TP-01 — a read-only binding must not dispatch (D-IMPL-361, spec §7.1).

The vendor (claude-agent-sdk 0.2.128) routes the CLI's ``tools/call`` straight
to the in-process MCP server's ``CallToolRequest`` handler
(``claude_agent_sdk/_internal/query.py:679-688``) with no Python-side
permission check. ``allowed_tools`` and ``can_use_tool`` are enforced by the
semi-trusted CLI, so the **only adapter-owned control on the Claude leg is
inside the in-process handler**. This test drives exactly that route — the
server instance the adapter placed on the carrier, its registered
``CallToolRequest`` handler, the skill's declared arguments — and asserts the
fabric's dispatch seam (:meth:`ccf.agents.agent.Agent.invoke_skill` with
arguments) is never reached under ``effects: unsupported``.

Offline: no CLI, no model, no socket (the conformance suite's guard is reused).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from ccf.agents.agent import Agent
from conftest import harness_unavailable
from conformance.test_harness_adapter import (
    World,
    _agent_fixture,
    _harness_fixture,
    no_model_reachable,  # noqa: F401 - autouse socket guard, reused not copied
)

pytestmark = [pytest.mark.harness]

LEG = "claude-agent"


@pytest.fixture
def dispatches(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Mapping[str, str]]]:
    """Every call that reached the fabric's dispatch seam, by its arguments.

    ``invoke_skill`` without arguments is introspection (the adapter uses it to
    build the tool surface); with arguments it dispatches. Only the second form
    is recorded, because only the second form is the hole.
    """
    reached: list[Mapping[str, str]] = []
    original = Agent.invoke_skill

    def recording(self: Agent, name: str, *, arguments: Any = None) -> Any:
        if arguments is not None:
            reached.append(dict(arguments))
        return original(self, name, arguments=arguments)

    monkeypatch.setattr(Agent, "invoke_skill", recording)
    yield reached


def _adapter(effects: str) -> Any:
    harness_unavailable("claude_agent_sdk", LEG)
    from ccf_runtime.adapters.claude_agent import ClaudeAgentAdapter

    values = _harness_fixture()[LEG]
    return ClaudeAgentAdapter(
        model=values["model"],
        mcp_server_name=values["mcp_server_name"],
        mcp_server_version=values["mcp_server_version"],
        effects=effects,  # type: ignore[arg-type]
    )


def _call_through_the_vendor_route(
    adapter: Any, agent: Agent, skill_name: str, arguments: Mapping[str, str]
) -> Any:
    """What the vendor does on a CLI ``tools/call``, and nothing more.

    ``query.py:679-688``: look up the server's ``CallToolRequest`` handler and
    await it with a ``CallToolRequest`` built from the wire's name and
    arguments. No permission callback is consulted on this path.
    """
    from mcp.types import CallToolRequest, CallToolRequestParams

    carrier = adapter.inject_context(agent=agent, products=(), instructions=())
    server = carrier.mcp_servers[_harness_fixture()[LEG]["mcp_server_name"]]
    handler = server["instance"].request_handlers[CallToolRequest]
    request = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=skill_name, arguments=dict(arguments)),
    )
    return asyncio.run(handler(request)).root


def _declared_arguments() -> dict[str, str]:
    return dict(_agent_fixture()["slice"]["granted_skill"]["arguments"])


def test_a_read_only_binding_does_not_reach_dispatch_through_the_in_process_handler(
    dispatches: list[Mapping[str, str]],
) -> None:
    """TP-01 as worded: ``effects: unsupported`` dispatches no skill."""
    world = World()
    world.bind(world.grant_a, world.definition_a)
    adapter = _adapter("unsupported")

    result = _call_through_the_vendor_route(
        adapter, world.agent_a, world.grant_a.skill_name, _declared_arguments()
    )

    assert dispatches == [], (
        "a binding declaring effects: unsupported reached Agent.invoke_skill"
        f" with arguments {dispatches!r} through the vendor's tools/call route"
        " — the CLI-side permission gate is the only thing standing in the way"
        " (TP-01)"
    )
    assert result.isError is True, (
        "the in-process handler returned a non-error result to the harness for"
        " a read-only binding (TP-01)"
    )
    text = " ".join(getattr(item, "text", "") for item in result.content)
    assert "effects='unsupported'" in text, (
        f"the refusal does not name the adapter's own reason: {text!r}"
    )


def test_a_revoked_skill_does_not_reach_dispatch_through_the_in_process_handler(
    dispatches: list[Mapping[str, str]],
) -> None:
    """The second condition, at call time: a skill revoked after the carrier was built."""
    from tests.skills.authority import revoke_capability

    world = World()
    grant_hash = world.bind(world.grant_a, world.definition_a)
    adapter = _adapter("governed")
    from mcp.types import CallToolRequest, CallToolRequestParams

    carrier = adapter.inject_context(agent=world.agent_a, products=(), instructions=())
    server = carrier.mcp_servers[_harness_fixture()[LEG]["mcp_server_name"]]
    handler = server["instance"].request_handlers[CallToolRequest]

    world.ledger.revoke(
        revoke_capability(
            grant_hash, tenant=world.definition_a.tenant, principal=world.actor
        )
    )
    assert world.grant_a.skill_name not in world.agent_a.bound_skill_names

    result = asyncio.run(
        handler(
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name=world.grant_a.skill_name, arguments=_declared_arguments()
                ),
            )
        )
    ).root
    assert dispatches == []
    assert result.isError is True
    text = " ".join(getattr(item, "text", "") for item in result.content)
    assert "bound skill-set" in text, text


def test_a_governed_binding_still_dispatches_the_bound_skill(
    dispatches: list[Mapping[str, str]],
) -> None:
    """The inversion: the control refuses read-only, not everything."""
    world = World()
    world.bind(world.grant_a, world.definition_a)
    adapter = _adapter("governed")

    result = _call_through_the_vendor_route(
        adapter, world.agent_a, world.grant_a.skill_name, _declared_arguments()
    )

    assert dispatches == [_declared_arguments()]
    assert result.isError is False
