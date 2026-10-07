"""TP-03 follow-on — the permission gates check the harness-exposable roster.

``D-IMPL-361``. ``TP-03`` filtered every adapter's tool surface by
:data:`~ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES`, but the two
harness-side permission gates — the Claude adapter's ``can_use_tool`` and the
ADK adapter's ``before_tool`` — still permitted any name in
``agent.bound_skill_names``. Measured on the integration branch: an agent
bound to a ``peering`` skill had the gate ALLOW the peering name, so a harness
naming the skill anyway (a tool it was never shown) passed the gate. A gate
that admits what the surface hides is the over-exposure defect one hop later.

Asserted per gate, per non-exposable type, on the gate the harness itself
calls (read off the carrier ``inject_context`` returns): the non-exposable
name is DENIED with the gate's own unbound-reason shape, and — the positive
control — the exposable sibling is still allowed, so a denial cannot be
explained by a gate that denies everything.

Every agent, entry and grant comes from the banking fixtures through the Agent
Factory (CLAUDE.md §6.4); this module holds mechanism only.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from adapters.test_harness_exposable_roster import NON_EXPOSABLE, _bound_world
from conformance.test_harness_adapter import build_harness_leg

pytestmark = [pytest.mark.harness]


def _claude_gate(adapter: Any, world: Any) -> Any:
    carrier = adapter.inject_context(agent=world.agent_a, products=(), instructions=())
    adapter.remove_prompt_directories()
    return carrier.can_use_tool


def _claude_decision(adapter: Any, gate: Any, skill_name: str) -> Any:
    qualified = f"mcp__{adapter._mcp_server_name}__{skill_name}"
    return asyncio.run(gate(qualified, {}, None))


@pytest.mark.parametrize("skill_type", NON_EXPOSABLE)
def test_claude_can_use_tool_denies_a_bound_non_exposable_skill(skill_type: str) -> None:
    pytest.importorskip("claude_agent_sdk")
    from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

    world, hidden = _bound_world(skill_type)
    adapter = build_harness_leg("claude-agent").adapter("governed")
    gate = _claude_gate(adapter, world)

    allowed = _claude_decision(adapter, gate, world.grant_a.skill_name)
    assert isinstance(allowed, PermissionResultAllow)

    decision = _claude_decision(adapter, gate, hidden)
    assert isinstance(decision, PermissionResultDeny), (
        f"can_use_tool allowed the bound {skill_type} skill {hidden!r}"
    )
    assert decision.message == (
        f"{'mcp__' + adapter._mcp_server_name + '__' + hidden!r}"
        " is not in the agent's bound skill-set"
    )


@pytest.mark.parametrize("skill_type", NON_EXPOSABLE)
def test_adk_before_tool_denies_a_bound_non_exposable_skill(skill_type: str) -> None:
    pytest.importorskip("google.adk")
    from ccf_runtime.adapters.adk.adapter import REFUSAL_RESPONSE_KEY

    world, hidden = _bound_world(skill_type)
    adapter = build_harness_leg("adk").adapter("governed")
    carrier = adapter.inject_context(agent=world.agent_a, products=(), instructions=())
    gate = carrier.llm_agent.before_tool_callback

    assert (
        gate(tool=SimpleNamespace(name=world.grant_a.skill_name), args={}, tool_context=None)
        is None
    )

    response = gate(tool=SimpleNamespace(name=hidden), args={}, tool_context=None)
    assert response is not None, (
        f"before_tool allowed the bound {skill_type} skill {hidden!r}"
    )
    assert f"{hidden!r} is not in the agent's bound skill-set" in str(
        response[REFUSAL_RESPONSE_KEY]
    ).replace('\\"', '"')
