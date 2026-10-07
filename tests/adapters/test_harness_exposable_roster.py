"""TP-03 — every adapter exposes only the harness-exposable bound skills.

``D-IMPL-361`` rates ``TP-03`` HIGH. Measured on all three reference adapters
before this module existed: an agent bound to a ``peering`` or an
``mcp_product`` skill had that skill rendered as a harness tool (the model can
call the peer directly, receive unadmitted Context Products and drain the
admission queue), and an agent bound to a ``procedure`` skill made
``_tools()`` raise ``ProcedureHasNoToolSurface`` — so ``expose_skills`` and
``inject_context`` crashed and the agent's other skills never reached the
harness at all.

Asserted per leg, through each adapter's public seams: the agent is bound to
the exposable ``covenant-metrics`` tool AND one non-exposable skill; the
non-exposable skill is genuinely bound (the precondition), is absent from
``expose_skills`` and from every string the harness-native carrier holds, and
the exposable sibling is still exposed and carried.

This also re-reads D-IMPL-25: skill exposure is mandatory exactly when the
bound agent's EXPOSABLE skill-set is non-empty — a bound procedure, peering or
mcp_product skill is never a harness tool.

Every agent, entry and grant comes from the banking fixtures through the Agent
Factory (the conformance suite's ``World``); this module holds mechanism only
(CLAUDE.md §6.4).
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalogEntry
from conformance.test_harness_adapter import (
    HARNESS_PARAMS,
    World,
    _carried,
    _parsed,
    _tool_fixture,
    _yaml,
    build_harness_leg,
)
from tests.composition import register_skill_entry

pytestmark = [pytest.mark.harness]

NON_EXPOSABLE = ("peering", "mcp_product", "procedure")


def _entry_document(skill_type: str) -> dict[str, Any]:
    """The existing fixture entry each non-exposable grant names."""
    if skill_type == "mcp_product":
        document: dict[str, Any] = _yaml(
            "skills", "exposure_rollup_mcp_product.yaml"
        )["entry"]
        return document
    variant: dict[str, Any] = _tool_fixture()["variants"][skill_type]
    return variant


def _bound_world(skill_type: str) -> tuple[World, str]:
    """The slice agent bound to ``covenant-metrics`` plus one ``skill_type`` skill."""
    world = World()
    entry: SkillCatalogEntry = _parsed(_entry_document(skill_type), SKILL_CATALOG_ENTRY)
    assert entry.skill_type == skill_type
    assert isinstance(register_skill_entry(world.catalog, world.registry, entry), str)
    world.bind(world.grant_a, world.definition_a)
    grant = world._grant(
        _yaml("skills", "non_exposable_grants.yaml")["grants"][skill_type],
        world.definition_a,
    )
    world.bind(grant, world.definition_a)
    # Precondition: both skills really are bound, so an empty exposure below
    # could not be explained by a grant that never took.
    assert set(world.agent_a.bound_skill_names) == {
        world.grant_a.skill_name,
        entry.name,
    }
    return world, entry.name


@pytest.mark.parametrize("skill_type", NON_EXPOSABLE)
@pytest.mark.parametrize("harness", HARNESS_PARAMS)
def test_a_bound_non_exposable_skill_is_never_a_harness_tool(
    harness: str, skill_type: str
) -> None:
    """Exposure skips it, never raises, and still renders the exposable sibling."""
    leg = build_harness_leg(harness)
    world, hidden = _bound_world(skill_type)
    adapter = leg.adapter("governed")

    assert adapter.expose_skills(agent=world.agent_a) == (world.grant_a.skill_name,)

    carrier = adapter.inject_context(agent=world.agent_a, products=(), instructions=())
    assert not _carried(carrier, hidden), (
        f"{harness} carried the bound {skill_type} skill {hidden!r} to the harness"
    )
    assert _carried(carrier, world.grant_a.skill_name)
