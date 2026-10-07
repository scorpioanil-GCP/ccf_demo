"""TP-03 on the MCP Experience Layer — the agent tool listing uses the roster.

``D-IMPL-361`` ``TP-03``: only skill types in
:data:`ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES` have a tool
surface. :func:`ccf_runtime.mcp.experience.agent_tool_listing` — the served
``list_agents`` door — skipped only ``procedure``. Before the TP-03 roster it
LISTED a bound ``peering`` or ``mcp_product`` skill as a tool; once
:func:`~ccf.skills.toolsurface.render_tool_surface` refused those types, the
listing RAISED ``SkillHasNoToolSurface`` instead. The rule asserted here is the
adapters' rule: filter by the roster, skip the rest, never raise, and still
list the exposable sibling.

The exposed agent is built the way the experience child server builds it
(``tests/crossproc/servers/mcp_experience_child.py::directory``): the bound
view off the grant ledger, for an agent constructed by the Agent Factory from
the banking fixture artifacts. Mechanism only (CLAUDE.md §6.4).
"""

from __future__ import annotations

import pytest

from adapters.test_harness_exposable_roster import NON_EXPOSABLE, _bound_world
from ccf.contracts.canonical import content_hash
from conformance.test_harness_adapter import _agent_fixture
from ccf_runtime.mcp.experience import ExposedAgent, agent_tool_listing


@pytest.mark.parametrize("skill_type", NON_EXPOSABLE)
def test_the_listing_skips_a_bound_non_exposable_skill(skill_type: str) -> None:
    """Listed: the exposable sibling only. Never raised on, never surfaced."""
    world, hidden = _bound_world(skill_type)
    bound = world.ledger.bound_view(content_hash(world.definition_a))
    assert hidden in bound  # precondition: the skill really is bound
    exposed = ExposedAgent(
        definition_key=_agent_fixture()["keys"]["agent_definition"],
        definition_version=world.definition_a.artifact_version,
        name=world.definition_a.name,
        artifact_version=world.definition_a.artifact_version,
        archetypes=world.definition_a.archetypes,
        skills=tuple(bound[name] for name in sorted(bound)),
    )

    listing = agent_tool_listing(exposed)

    assert tuple(tool.skill for tool in listing.tools) == (world.grant_a.skill_name,)
