"""One shared derivation of the harness tool surface (D-IMPL-56; D-17).

SDK-defined (CLAUDE.md §6.2 channel 2, §7.3 seam 2). Every harness adapter
renders a bound skill as a harness-native tool, and each harness wants the
same two things: a description string and an argument schema. Before
D-IMPL-56 (ruled 2026-07-27) each adapter composed those independently —
three helpers that happened to agree, where the first divergence would have
silently broken the D-17/D-18 harness-portability equivalence. This module
is the ruling realized: **one pure derivation, three consumers**. No adapter
composes a description or a schema of its own; each imports
:func:`render_tool_surface` and applies the result to its harness's native
tool type.

The derivation composes *artifact-carried values only* — the entry's name,
version, skill type, declared description, and declared argument schema. It
authors no prose about any deployment's skill (No-Hardcoding Rule, CLAUDE.md
§6.4; CINV-01): what a skill is for is the deployment's statement, declared
on the catalog entry and versioned with it.

``procedure`` skills have no seam-2 tool surface at all: their instruction
content travels by pinned reference through seam 1 (context injection) only
(D-IMPL-56; T-07-05). Rendering one is refused, not defaulted — a procedure
that appeared as a callable tool would be instruction smuggling into the
dispatch surface.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ccf.skills.catalog import SkillCatalogEntry

__ccf_mode__ = "algorithmic"

__all__ = ["ProcedureHasNoToolSurface", "RenderedToolSurface", "render_tool_surface"]


class ProcedureHasNoToolSurface(ValueError):
    """A ``procedure`` entry was asked for a seam-2 tool surface.

    Raised, never defaulted: a procedure's instruction content is consumed on
    seam 1 only (D-IMPL-56; T-07-05), and an adapter that surfaced one as a
    harness tool would hand the harness a dispatch path the artifact never
    declared.
    """


@dataclass(frozen=True)
class RenderedToolSurface:
    """What every harness adapter applies to its native tool type.

    Attributes:
        description: The tool description, composed from the entry's declared
            identity and its declared ``description`` — identical across all
            three adapters by construction (D-17).
        input_schema: The MCP-``inputSchema``-shaped rendering of the entry's
            declared ``argument_schema``, with ``additionalProperties`` always
            ``false`` (:meth:`ccf.skills.catalog.SkillArgumentSchema.to_input_schema`).
    """

    description: str
    input_schema: dict[str, Any]


def render_tool_surface(entry: SkillCatalogEntry) -> RenderedToolSurface:
    """The one derivation from a catalog entry to a rendered tool surface.

    Pure: same entry, same surface, on every harness. Composes only values
    the artifact carries — ``name``, ``artifact_version``, ``skill_type``,
    ``description``, ``argument_schema`` — and nothing authored here
    (CINV-01; CLAUDE.md §6.4).

    Raises:
        ProcedureHasNoToolSurface: ``entry`` is a ``procedure`` skill, which
            has no seam-2 surface by construction (D-IMPL-56; T-07-05).
    """
    if entry.skill_type == "procedure":
        raise ProcedureHasNoToolSurface(
            f"procedure skill {entry.name!r} has no seam-2 tool surface; its"
            " instruction travels by pinned reference through seam 1 only"
            " (D-IMPL-56)"
        )
    return RenderedToolSurface(
        description=(
            f"{entry.name}@{entry.artifact_version}"
            f" [{entry.skill_type}]: {entry.description}"
        ),
        input_schema=entry.argument_schema.to_input_schema(),
    )
