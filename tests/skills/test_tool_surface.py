"""D-17: all three adapters render the identical tool surface (D-IMPL-56).

The claim pinned here: for one and the same catalog entry, the tool surface
each of the three D-IMPL-24 reference adapters actually hands its harness —
the description string and the argument schema, read back off **real harness
tool objects**, never off CCF-side values — is identical across all three,
and identical to the one shared derivation in
:mod:`ccf.skills.toolsurface`.

What would go red here: any adapter re-deriving a description or a schema of
its own (the pre-D-IMPL-56 state, where three `_tool_description` helpers
happened to agree), or the shared derivation drifting from what any harness
tool actually carries. Harness-specific extraction lives in each leg below;
the equality assertion is shared and structural.

Absent-SDK legs skip visibly through the shared harness-extras machinery
(`conftest.harness_unavailable`), naming the missing module and the extra
that installs it; under ``CCF_REQUIRE_HARNESSES=1`` a missing leg is a
failure, never a silent skip.

Everything domain-specific comes from ``tests/fixtures/banking`` (CLAUDE.md
§6.4); this module holds mechanism only.
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf.skills.toolsurface import (
    ProcedureHasNoToolSurface,
    render_tool_surface,
)
from conftest import harness_unavailable
from conformance.test_harness_adapter import World, _harness_fixture
from skills.test_catalog import _tool_fixture

from ccf.skills.catalog import SkillCatalogEntry

pytestmark = [pytest.mark.harness]

#: The three D-IMPL-24 harness legs, keyed by the harness fixture's own block
#: names.
HARNESS_PARAMS = ("claude-agent", "adk", "langgraph")


def _normalized(description: str, schema_properties: dict[str, tuple[str, str]],
                required: frozenset[str]) -> dict[str, Any]:
    """One comparable shape for a rendered surface, whatever the harness."""
    return {
        "description": description,
        "properties": schema_properties,
        "required": required,
    }


def _normalize_input_schema(description: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize a JSON-schema-dict-carrying surface (Claude, LangGraph)."""
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    return _normalized(
        description,
        {
            name: (spec["type"], spec["description"])
            for name, spec in schema["properties"].items()
        },
        frozenset(schema["required"]),
    )


def _rendered_surface(leg: str, world: World) -> dict[str, Any]:
    """The tool surface one adapter's real harness tool object carries.

    Each branch reads the description and argument schema back off the
    harness-native tool the adapter constructed for the agent's bound skill —
    the same construction path ``inject_context``/``expose_skills`` use — so
    an adapter that re-derived either value would surface it here.
    """
    values = _harness_fixture()
    agent = world.agent_a
    (skill_name,) = agent.bound_skill_names

    if leg == "claude-agent":
        harness_unavailable("claude_agent_sdk", leg)
        from ccf_runtime.adapters.claude_agent import ClaudeAgentAdapter

        adapter = ClaudeAgentAdapter(
            model=values[leg]["model"],
            mcp_server_name=values[leg]["mcp_server_name"],
            mcp_server_version=values[leg]["mcp_server_version"],
            effects="governed",
        )
        handler = adapter._skill_tool(agent, skill_name)
        return _normalize_input_schema(handler.description, handler.input_schema)

    if leg == "langgraph":
        harness_unavailable("langgraph", leg)
        from ccf_runtime.adapters.langgraph import LangGraphAdapter

        adapter = LangGraphAdapter(
            model=values[leg]["model"],
            thread_id=values[leg]["thread_id"],
            run_tags=tuple(values[leg]["run_tags"]),
            effects="governed",
        )
        structured = adapter._skill_tool(agent, skill_name)
        return _normalize_input_schema(
            structured.description, dict(structured.args_schema)
        )

    if leg == "adk":
        harness_unavailable("google.adk", leg)
        from ccf_runtime.adapters.adk import AdkAdapter

        adapter = AdkAdapter(
            model=values[leg]["model"],
            agent_name=values[leg]["agent_name"],
            session_id=values[leg]["session_id"],
            effects="governed",
        )
        function_tool = adapter._skill_tool(agent, skill_name)
        declaration = function_tool._get_declaration()
        parameters = declaration.parameters
        assert parameters is not None and parameters.type is not None
        assert parameters.type.value.lower() == "object"
        assert declaration.description is not None
        return _normalized(
            declaration.description,
            {
                name: (spec.type.value.lower(), spec.description)
                for name, spec in (parameters.properties or {}).items()
            },
            frozenset(parameters.required or ()),
        )

    raise NotImplementedError(leg)


def test_all_three_adapters_render_one_identical_tool_surface() -> None:
    """D-17: three harnesses, one surface — byte-equal on every compared axis."""
    world = World()
    world.bind(world.grant_a, world.definition_a)
    (skill_name,) = world.agent_a.bound_skill_names
    entry = world.agent_a.invoke_skill(skill_name)
    assert isinstance(entry, SkillCatalogEntry)
    expected_surface = render_tool_surface(entry)
    expected = _normalize_input_schema(
        expected_surface.description, expected_surface.input_schema
    )

    rendered = {leg: _rendered_surface(leg, world) for leg in HARNESS_PARAMS}

    for leg, surface in rendered.items():
        assert surface == expected, (
            f"{leg} rendered a tool surface diverging from the shared"
            " derivation (D-IMPL-56/D-17)"
        )
    # The three-way statement itself, not only the shared-anchor one: any
    # adapter re-deriving on its own breaks this pairwise equality.
    values = list(rendered.values())
    assert values[0] == values[1] == values[2]


def test_the_shared_derivation_carries_the_declared_description() -> None:
    """The artifact's own description appears verbatim — never adapter prose."""
    entry = SkillCatalogEntry.model_validate(_tool_fixture()["entry"])
    surface = render_tool_surface(entry)
    assert entry.description in surface.description
    assert surface.input_schema == entry.argument_schema.to_input_schema()


def test_a_procedure_entry_is_refused_a_tool_surface() -> None:
    """Seam-1-only by construction (D-IMPL-56; T-07-05)."""
    procedure = SkillCatalogEntry.model_validate(
        _tool_fixture()["variants"]["procedure"]
    )
    with pytest.raises(ProcedureHasNoToolSurface):
        render_tool_surface(procedure)
