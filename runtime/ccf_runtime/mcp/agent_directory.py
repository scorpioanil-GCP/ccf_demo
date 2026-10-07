"""Directory entries for the Experience door, derived from agent definitions.

SDK-defined (CLAUDE.md §8.3, §6.2) — ``SEC-017``; ``D-IMPL-374`` (2), fix
round 1, IMPORTANT 3. A grant's declared product roster
(:attr:`~ccf_runtime.mcp.auth.TokenGrant.products`) is held, on
``invoke_agent`` and ``list_agents``, to the Context Product classes an agent
reaches. Those classes are the agent definition's own context contract —
``consumes ∪ emits`` — and a directory that could STATE them could narrow
them, which would widen every roster's reach. So this module is the one place
an :class:`~ccf_runtime.mcp.experience.ExposedAgent` receives its
``product_classes``: it reads them off the definition, and the entry refuses a
set stated any other way.

It lives beside the Experience server rather than in it because the server
holds no agents-package handle of any kind (T-07-20, asserted against its
source); a deployment's directory is where definitions already are.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.agents.definitions import AgentDefinition, ContextContract
from ccf.skills.catalog import SkillCatalogEntry
from ccf_runtime.mcp.experience import _DERIVED_PRODUCT_CLASSES, ExposedAgent

__ccf_mode__ = "algorithmic"

__all__ = ["context_contract_classes", "exposed_agent"]


def context_contract_classes(contract: ContextContract) -> frozenset[str]:
    """The Context Product classes a context contract names: ``consumes ∪ emits``.

    ``SEC-017``; ``D-IMPL-374`` (2) — the ONE derivation of what an exposed
    agent reaches.
    """
    return frozenset(c.product_class for c in contract.consumes) | frozenset(
        e.product_class for e in contract.emits
    )


def exposed_agent(
    definition: AgentDefinition,
    *,
    definition_key: str,
    definition_version: str,
    skills: tuple[SkillCatalogEntry, ...],
) -> ExposedAgent:
    """The directory entry for ``definition`` — the SDK's derivation helper.

    ``SEC-017``; ``D-IMPL-374`` (2), fix round 1. Every artifact-carried value
    is read from the definition — name, artifact version, archetype
    composition, and the product classes its context contract names — so a
    directory supplies only what the definition cannot know: the Control Plane
    key and pinned version the invoker constructs against, and the
    currently-bound skills.

    Args:
        definition: The exposed agent's definition artifact.
        definition_key: Its Control Plane key.
        definition_version: Its pinned Control Plane version.
        skills: Its currently-bound skill entries (CLAUDE.md §6.2 channel 2).
    """
    return ExposedAgent.model_validate(
        {
            "definition_key": definition_key,
            "definition_version": definition_version,
            "name": definition.name,
            "artifact_version": definition.artifact_version,
            "archetypes": definition.archetypes,
            "skills": skills,
            "product_classes": context_contract_classes(definition.context_contract),
        },
        context={_DERIVED_PRODUCT_CLASSES: True},
    )
