"""Capability helpers for the skills-tree tests — D-IMPL-353 §1.2, test side only.

The grant ledger requires ``Authorized[SkillGrant]`` for the agent definition
key and ``Authorized[SkillRevoke]`` for the grant hash; these mint them the way
the ``skill.grant`` / ``skill.revoke`` doors do, from the definition (or hash)
the test holds. ``register_entry`` files a catalog entry straight through the
Control Plane registry under ``SkillCatalogRegister`` — the catalog's own
``register`` is an unowned caller of the registry handle that the join
migrates; the catalog *resolves* from registry state (IN-03), so entries
registered this way are discoverable exactly as before.
"""

from __future__ import annotations

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.authz.capability import Authorized, SkillCatalogRegister
from ccf.authz.capability import SkillGrant as SkillGrantKind
from ccf.authz.capability import SkillRevoke as SkillRevokeKind
from ccf.controlplane.registry import ControlPlaneRegistry, RegistrationRefusal
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalogEntry, skill_catalog_key
from tests.controlplane.capabilities import PRINCIPAL, capability, register_capability

__all__ = ["definition_key", "grant_capability", "register_entry", "revoke_capability"]


def definition_key(definition: AgentDefinition) -> str:
    """The Control Plane key the definition lives under — what the door decides on."""
    return f"{definition.tenant}/{AGENT_DEFINITION.class_id}/{definition.name}"


def grant_capability(
    definition: AgentDefinition, *, principal: str = PRINCIPAL
) -> Authorized[SkillGrantKind]:
    return capability(
        SkillGrantKind,
        tenant=definition.tenant,
        resource=definition_key(definition),
        principal=principal,
    )


def revoke_capability(
    grant_hash: str, *, tenant: str, principal: str = PRINCIPAL
) -> Authorized[SkillRevokeKind]:
    return capability(SkillRevokeKind, tenant=tenant, resource=grant_hash, principal=principal)


def register_entry(
    registry: ControlPlaneRegistry, entry: SkillCatalogEntry
) -> str | RegistrationRefusal:
    return registry.register_versioned(
        register_capability(skill_catalog_key(entry), SkillCatalogRegister),
        entry,
        SKILL_CATALOG_ENTRY,
    )
