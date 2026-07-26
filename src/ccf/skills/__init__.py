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
catalog live in :mod:`ccf.skills.catalog`, with registration flowing through
the existing :class:`~ccf.controlplane.registry.ControlPlaneRegistry` via its
D-05 versioned path; the two-tier grant machinery (D-IMPL-29) lives in
:mod:`ccf.skills.grants`; dispatch for the local_callable and tool types
lives in :mod:`ccf.skills.dispatch` — mcp/a2a dispatch raises the typed
``NotYetBound`` until I.3 binds the transports (D-08).
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
from ccf.skills.grants import (
    SKILL_GRANT,
    ApprovalOutcome,
    ApprovalRejected,
    ApprovalSink,
    BoundSkillView,
    GovernanceUndeclared,
    GrantCollisionError,
    GrantLedger,
    GrantRefusal,
    GrantTransitionError,
    PolicyRegimeGovernance,
    PolicyRegimeUnresolvable,
    RequirementsExceedRegime,
    SkillGrant,
    TenantMismatch,
    grant_set_hash,
    skill_grant_key,
)

__all__ = [
    "SKILL_CATALOG_ENTRY",
    "SKILL_GRANT",
    "SKILL_TYPES",
    "A2ABinding",
    "ApprovalOutcome",
    "ApprovalRejected",
    "ApprovalSink",
    "BoundSkillView",
    "GovernanceUndeclared",
    "GrantCollisionError",
    "GrantLedger",
    "GrantRefusal",
    "GrantTransitionError",
    "LocalCallableBinding",
    "McpBinding",
    "PolicyRegimeGovernance",
    "PolicyRegimeUnresolvable",
    "RequirementsExceedRegime",
    "SkillCatalog",
    "SkillCatalogEntry",
    "SkillGrant",
    "SkillNotInCatalog",
    "SkillRequirements",
    "TenantMismatch",
    "ToolBinding",
    "grant_set_hash",
    "skill_catalog_key",
    "skill_grant_key",
]
