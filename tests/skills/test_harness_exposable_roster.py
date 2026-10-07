"""TP-03 — only harness-exposable skill types get a tool surface.

``D-IMPL-361`` rates ``TP-03`` HIGH: :func:`ccf.skills.toolsurface.render_tool_surface`
refused only ``procedure``, so a ``peering`` or ``mcp_product`` entry rendered
as a harness tool. A model holding that tool calls the peer directly, receives
Context Products the Control Plane never admitted, and drains the queue the
admission gate reads (CLAUDE.md §7.2 — an inbound product is not admissible
until the consuming Control Plane validates it).

The ruling (Global Constraint 7 of the TP-01…05 plan): the harness-exposable
skill types are exactly ``tool``, ``mcp`` and ``local_callable``. Those are SDK
skill-type NAMES — mechanism, not deployment values — so the roster is pinned
here. Every other member of :data:`ccf.skills.catalog.SkillType` is refused by
the one shared derivation with one typed exception.

The entries are the banking fixtures' own (CLAUDE.md §6.4); this module holds
mechanism only. The refusal class is looked up inside each test body rather
than imported at module scope, so a tree without it fails each assertion at
execution instead of failing collection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.skills import toolsurface
from ccf.skills.catalog import SKILL_TYPES, SkillCatalogEntry
from ccf.skills.toolsurface import ProcedureHasNoToolSurface, render_tool_surface

SKILLS = Path(__file__).resolve().parents[1] / "fixtures" / "banking" / "skills"

#: The controller's ruling, verbatim (TP-03; D-IMPL-361).
RULED_EXPOSABLE = frozenset({"tool", "mcp", "local_callable"})


def _yaml(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((SKILLS / name).read_text())
    return loaded


def _entry_of_type(skill_type: str) -> SkillCatalogEntry:
    """One fixture catalog entry per SDK skill type."""
    tool = _yaml("covenant_metrics_tool.yaml")
    documents: dict[str, Any] = {
        "tool": tool["entry"],
        "local_callable": tool["variants"]["local_callable"],
        "peering": _yaml("remote_products_peering.yaml")["entry"],
        "procedure": tool["variants"]["procedure"],
        "mcp": _yaml("document_fetch_mcp.yaml")["entry"],
        "mcp_product": _yaml("exposure_rollup_mcp_product.yaml")["entry"],
    }
    entry = SkillCatalogEntry.model_validate(documents[skill_type])
    assert entry.skill_type == skill_type
    return entry


def test_every_sdk_skill_type_has_a_fixture_entry() -> None:
    """The parametrization below covers the whole closed vocabulary."""
    for skill_type in SKILL_TYPES:
        _entry_of_type(skill_type)


def test_the_roster_is_exactly_the_ruled_set() -> None:
    """The roster constant is the ruling, and a subset of the vocabulary."""
    roster = toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES
    assert roster == RULED_EXPOSABLE
    assert roster <= SKILL_TYPES


@pytest.mark.parametrize("skill_type", sorted(SKILL_TYPES - RULED_EXPOSABLE))
def test_a_non_exposable_type_is_refused_a_tool_surface(skill_type: str) -> None:
    """``peering``, ``mcp_product`` and ``procedure`` never render (TP-03)."""
    entry = _entry_of_type(skill_type)
    with pytest.raises(ValueError) as caught:
        render_tool_surface(entry)
    assert isinstance(caught.value, toolsurface.SkillHasNoToolSurface)
    assert entry.name in str(caught.value)
    assert skill_type in str(caught.value)


@pytest.mark.parametrize("skill_type", sorted(RULED_EXPOSABLE))
def test_an_exposable_type_renders_its_declared_surface(skill_type: str) -> None:
    """The positive control: the roster refuses nothing it admits."""
    entry = _entry_of_type(skill_type)
    surface = render_tool_surface(entry)
    assert entry.description in surface.description
    assert surface.input_schema == entry.argument_schema.to_input_schema()


def test_the_procedure_refusal_keeps_its_existing_class() -> None:
    """Existing ``ProcedureHasNoToolSurface`` catches still hold."""
    assert issubclass(ProcedureHasNoToolSurface, toolsurface.SkillHasNoToolSurface)
    with pytest.raises(ProcedureHasNoToolSurface):
        render_tool_surface(_entry_of_type("procedure"))
