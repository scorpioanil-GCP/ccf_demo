"""Door-declared action identifiers — the vocabulary capabilities are minted for.

Relocated from ``ccf_runtime.authz.refusals`` under D-IMPL-353 so that ``src/``
handles can name the action they perform without importing ``runtime/``
(D-29: ``src ↛ runtime``). Mechanism identifiers, never policy: a deployment
scope mapping grants them by name; the SDK enumerates no grant.
"""

from __future__ import annotations

from typing import Final

__ccf_mode__ = "algorithmic"

__all__ = [
    "ACTION_HITL_QUEUE_READ",
    "ACTION_HITL_ACTION_SUBMIT",
    "ACTION_PRODUCT_RETRIEVE",
    "ACTION_REPLAY_READ",
    "ACTION_ARTIFACT_READ",
    "ACTION_AGENT_DECLARE",
    "ACTION_AGENT_LIST",
    "ACTION_AGENT_READ",
    "ACTION_AGENT_VERSIONS",
    "ACTION_ARTIFACT_WRITE",
    "ACTION_BACKENDS_READ",
    "ACTION_CONFIG_KEYS_READ",
    "ACTION_CONFIG_VERSIONS_READ",
    "ACTION_CONFIG_RESOLVE",
    "ACTION_CONFIG_REGISTER",
    "ACTION_OPENAPI_READ",
    "ACTION_DOCS_READ",
    "ACTION_HEALTH_READ",
    "ACTION_SCHEMA_READ",
    "ACTION_SCHEMA_LIST",
    "ACTION_SKILL_CATALOG_READ",
    "ACTION_SKILL_CATALOG_REGISTER",
    "ACTION_SKILL_GRANT",
    "ACTION_SKILL_REVOKE",
    "ACTION_WORKFLOW_INVOKE",
    "ACTION_WORKFLOW_RESUME",
    "ACTION_WORKFLOW_STATUS_READ",
]

#: ``GET /hitl/queue`` and the MCP door's queue resource (D-02).
ACTION_HITL_QUEUE_READ: Final[str] = "hitl.queue.read"
#: ``POST /hitl/actions`` and the MCP door's action tool (D-02).
ACTION_HITL_ACTION_SUBMIT: Final[str] = "hitl.action.submit"
#: (D-02; D-08).
ACTION_PRODUCT_RETRIEVE: Final[str] = "product.retrieve"
#: entitlement decision's own event does not.
ACTION_REPLAY_READ: Final[str] = "replay.read"
#: receive the other, even though ``D-IMPL-345`` decides both the same way.
ACTION_ARTIFACT_READ: Final[str] = "artifact.read"
#: is expected to state resource patterns for it rather than a wide grant.
ACTION_AGENT_DECLARE: Final[str] = "agent.declare"
#: without being entitled to learn which keys exist.
ACTION_AGENT_LIST: Final[str] = "agent.list"
#: ``GET /agent/declaration``.
ACTION_AGENT_READ: Final[str] = "agent.read"
#: ``GET /agent/versions``.
ACTION_AGENT_VERSIONS: Final[str] = "agent.versions"
#: an examiner filtering on writes must not receive reads.
ACTION_ARTIFACT_WRITE: Final[str] = "artifact.write"
#: learns is a deployment's shape, which is reconnaissance (``T-15.4-11``).
ACTION_BACKENDS_READ: Final[str] = "backends.read"
#: ``GET /config/keys``.
ACTION_CONFIG_KEYS_READ: Final[str] = "config.keys.read"
#: ``GET /config/versions``.
ACTION_CONFIG_VERSIONS_READ: Final[str] = "config.versions.read"
#: door's ``GET /config/resolution``.
ACTION_CONFIG_RESOLVE: Final[str] = "config.resolve"
#: every key.
ACTION_CONFIG_REGISTER: Final[str] = "config.register"
#: single most useful disclosure on the surface to someone who has none.
ACTION_OPENAPI_READ: Final[str] = "openapi.read"
#: drift would be the two nobody re-reads.
ACTION_DOCS_READ: Final[str] = "docs.read"
#: versioned line in an artifact instead of an invisible branch in SDK code.
ACTION_HEALTH_READ: Final[str] = "health.read"
#: ``GET /schema/{class_id}``.
ACTION_SCHEMA_READ: Final[str] = "schema.read"
#: enumeration-versus-retrieval line :data:`ACTION_AGENT_LIST` records.
ACTION_SCHEMA_LIST: Final[str] = "schema.list"
#: ``GET /skill/catalog``.
ACTION_SKILL_CATALOG_READ: Final[str] = "skill.catalog.read"
#: action rather than a mode of the read.
ACTION_SKILL_CATALOG_REGISTER: Final[str] = "skill.catalog.register"
#: ``POST /skill/grants`` (CLAUDE.md §6.2 channel 2).
ACTION_SKILL_GRANT: Final[str] = "skill.grant"
#: direction the harder one.
ACTION_SKILL_REVOKE: Final[str] = "skill.revoke"
#: door's ``POST /workflow/invocations`` (ORCH-01).
ACTION_WORKFLOW_INVOKE: Final[str] = "workflow.invoke"
#: *start a workflow* has not thereby granted *approve one*.
ACTION_WORKFLOW_RESUME: Final[str] = "workflow.resume"
#: ``GET /workflow/execution``.
ACTION_WORKFLOW_STATUS_READ: Final[str] = "workflow.status.read"
