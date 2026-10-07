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

Only the skill types in :data:`HARNESS_EXPOSABLE_SKILL_TYPES` — ``tool``,
``mcp`` and ``local_callable`` — have a seam-2 tool surface (``TP-03``,
``D-IMPL-361``). Every other type is refused with
:class:`SkillHasNoToolSurface`, not defaulted:

* ``procedure`` skills' instruction content travels by pinned reference
  through seam 1 (context injection) only (D-IMPL-56; T-07-05) — a procedure
  that appeared as a callable tool would be instruction smuggling into the
  dispatch surface.
* ``peering`` and ``mcp_product`` skills reach a peer's Context Products,
  which enter this fabric only through Control Plane admission (CLAUDE.md
  §7.2). Rendered as a harness tool, the model would call the peer directly,
  receive products nothing admitted, and drain the queue the admission gate
  reads.

The roster is a set of SDK skill-type names — mechanism, not deployment
values. Each harness adapter filters its agent's bound skill-set by the same
roster before rendering, so a bound non-exposable skill is skipped there and
never reaches this refusal; the refusal here is the derivation's own floor.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ccf.skills.catalog import SkillCatalogEntry

__ccf_mode__ = "algorithmic"

__all__ = [
    "HARNESS_EXPOSABLE_SKILL_TYPES",
    "ProcedureHasNoToolSurface",
    "RenderedToolSurface",
    "SkillHasNoToolSurface",
    "render_tool_surface",
]

#: The skill types that have a harness tool surface (``TP-03``,
#: ``D-IMPL-361``). SDK skill-type names from
#: :data:`ccf.skills.catalog.SkillType` — mechanism, not values. ``peering``,
#: ``mcp_product`` and ``procedure`` are deliberately absent.
HARNESS_EXPOSABLE_SKILL_TYPES: frozenset[str] = frozenset(
    {"tool", "mcp", "local_callable"}
)


class SkillHasNoToolSurface(ValueError):
    """A non-exposable entry was asked for a seam-2 tool surface.

    Raised for every skill type outside :data:`HARNESS_EXPOSABLE_SKILL_TYPES`
    (``TP-03``, ``D-IMPL-361``), never defaulted: a ``peering`` or
    ``mcp_product`` tool would hand the model unadmitted peer products, and a
    ``procedure`` tool would smuggle instruction content into dispatch.
    """


class ProcedureHasNoToolSurface(SkillHasNoToolSurface):
    """A ``procedure`` entry was asked for a seam-2 tool surface.

    A subclass of :class:`SkillHasNoToolSurface` (``TP-03``, ``D-IMPL-361``),
    so existing catches of this class keep holding.

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
        SkillHasNoToolSurface: ``entry``'s type is outside
            :data:`HARNESS_EXPOSABLE_SKILL_TYPES` (``TP-03``, ``D-IMPL-361``).
        ProcedureHasNoToolSurface: the :class:`SkillHasNoToolSurface` raised
            for a ``procedure`` skill, which has no seam-2 surface by
            construction (D-IMPL-56; T-07-05).
    """
    if entry.skill_type not in HARNESS_EXPOSABLE_SKILL_TYPES:
        if entry.skill_type == "procedure":
            raise ProcedureHasNoToolSurface(
                f"procedure skill {entry.name!r} has no seam-2 tool surface; its"
                " instruction travels by pinned reference through seam 1 only"
                " (D-IMPL-56)"
            )
        raise SkillHasNoToolSurface(
            f"{entry.skill_type} skill {entry.name!r} has no seam-2 tool"
            " surface; only harness-exposable skill types render as harness"
            " tools (TP-03)"
        )
    return RenderedToolSurface(
        description=(
            f"{entry.name}@{entry.artifact_version}"
            f" [{entry.skill_type}]: {entry.description}"
        ),
        input_schema=entry.argument_schema.to_input_schema(),
    )
