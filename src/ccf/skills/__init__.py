"""The skill catalog — channel 2 of agent specialization (CLAUDE.md §6.2).

SDK-defined extension (CLAUDE.md §6, not whitepaper-derived): skills are
typed, governed capabilities registered in a catalog as versioned Control
Plane artifacts (D-IMPL-12), bound to agents by reference and governed
through the two-tier D-IMPL-29 machinery. This package holds the *mechanism*
— the four-type entry schema, the typed requirements declaration, and
registration/discovery over the Control Plane — never a skill: a skill found
in library code would be a defect of the same class as a hard-coded λ_c
table (No-Hardcoding Rule §6.4).

Module layout (05-RESEARCH.md Open Question 1 resolution): schemas and the
catalog live here in :mod:`ccf.skills.catalog`, with registration flowing
through the existing :class:`~ccf.controlplane.registry.ControlPlaneRegistry`
via its D-05 versioned path. Grant/revocation state, governance checks, and
dispatch land in the next wave (05-06); the schema covers all four skill
types from day one (D-08) so grants have a stable substrate to bind against.
"""

from ccf.skills.catalog import (
    SKILL_CATALOG_ENTRY,
    SKILL_TYPES,
    A2ABinding,
    LocalCallableBinding,
    McpBinding,
    SkillCatalog,
    SkillCatalogEntry,
    SkillNotInCatalog,
    SkillRequirements,
    ToolBinding,
    skill_catalog_key,
)

__all__ = [
    "SKILL_CATALOG_ENTRY",
    "SKILL_TYPES",
    "A2ABinding",
    "LocalCallableBinding",
    "McpBinding",
    "SkillCatalog",
    "SkillCatalogEntry",
    "SkillNotInCatalog",
    "SkillRequirements",
    "ToolBinding",
    "skill_catalog_key",
]
