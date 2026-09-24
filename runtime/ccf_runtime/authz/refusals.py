"""Door-declared action identifiers for tenant authorization (D-02/D-08).

SDK-defined (CLAUDE.md §8.3; D-IMPL-68; 10-CONTEXT D-02/D-08). The action
vocabulary a :class:`~ccf_runtime.authz.artifact.ScopeMappingArtifact`
matches against is declared by the doors themselves — the SDK invents no
scope vocabulary, but its shipped doors are code, so their action
identifiers are declared here once and imported by each, never re-typed. One
vocabulary, two renderings (D-08): the HTTP door refuses with the typed 403
body, the MCP door with its protocol-native error, both carrying
:data:`~ccf_runtime.http_api.errors.ERROR_TENANT_UNAUTHORIZED`.

**Every route on the HTTP front door declares one, with no exempt route**
(``SEC-001``). Five identifiers existed while five doors asked the question
inside their own handlers; the total gate
(:mod:`ccf_runtime.http_api.gate`) asks it for every mounted route, so every
mounted route names an action — liveness, the installed-adapter list, the
generated OpenAPI document and its viewer included. The alternative is a
carve-out list, and a carve-out list is an applicability switch whose key is
the path the caller chose.

These are **mechanism identifiers, not policy**: they name doors the SDK
ships, in the same sense as the error-code constants. What any of them
*reaches* is the deployment's statement, in its registered scope mapping.

The values are **stable API surface** in the same sense as the error-code
constants (:mod:`ccf_runtime.http_api.errors`): a deployment's registered
scope mappings name them, so renaming one is a breaking change to every
deployed artifact.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Final

__ccf_mode__ = "algorithmic"

__all__ = [
    "ACTION_AGENT_DECLARE",
    "ACTION_AGENT_LIST",
    "ACTION_AGENT_READ",
    "ACTION_AGENT_VERSIONS",
    "ACTION_ARTIFACT_READ",
    "ACTION_ARTIFACT_WRITE",
    "ACTION_BACKENDS_READ",
    "ACTION_CONFIG_KEYS_READ",
    "ACTION_CONFIG_REGISTER",
    "ACTION_CONFIG_RESOLVE",
    "ACTION_CONFIG_VERSIONS_READ",
    "ACTION_DOCS_READ",
    "ACTION_HEALTH_READ",
    "ACTION_HITL_ACTION_SUBMIT",
    "ACTION_HITL_QUEUE_READ",
    "ACTION_OPENAPI_READ",
    "ACTION_PRODUCT_RETRIEVE",
    "ACTION_REPLAY_READ",
    "ACTION_SCHEMA_LIST",
    "ACTION_SCHEMA_READ",
    "ACTION_SKILL_CATALOG_READ",
    "ACTION_SKILL_CATALOG_REGISTER",
    "ACTION_SKILL_GRANT",
    "ACTION_SKILL_REVOKE",
    "ACTION_WORKFLOW_INVOKE",
    "ACTION_WORKFLOW_RESUME",
    "ACTION_WORKFLOW_STATUS_READ",
]

#: Reading one tenant's pending HITL queue — declared by the HTTP door's
#: ``GET /hitl/queue`` and the MCP door's queue resource (D-02).
ACTION_HITL_QUEUE_READ: Final[str] = "hitl.queue.read"

#: Submitting one human action — declared by the HTTP door's
#: ``POST /hitl/actions`` and the MCP door's action tool (D-02).
ACTION_HITL_ACTION_SUBMIT: Final[str] = "hitl.action.submit"

#: Receiving one Context Product — declared by all **three** exposed product
#: doors (the MCP egress resource, the Experience front-door resource, and
#: the HTTP ``GET /product/...`` route) and carried on the
#: ``authz_decision`` event every entitlement decision appends. One action
#: id for three doors, deliberately: an examiner asking "who was served this
#: class?" must not have to know which surface the caller happened to reach
#: (D-02; D-08).
ACTION_PRODUCT_RETRIEVE: Final[str] = "product.retrieve"

#: Retrieving one Decision Replay record over a door — declared by the HTTP
#: ``GET /replay/decisions`` and ``GET /replay/resolutions`` routes
#: (``D-IMPL-345``, R-5). Distinct from :data:`ACTION_PRODUCT_RETRIEVE`
#: because the question differs: *retrieve* asks whether a principal may be
#: SERVED a class, this asks whether it may READ the governed evidence of a
#: determination already made. The event this id rides on is the trail of a
#: read — it names the reference asked and the address delivered, which the
#: entitlement decision's own event does not.
ACTION_REPLAY_READ: Final[str] = "replay.read"

#: Retrieving artifact bytes by content address over a door — declared by the
#: HTTP ``GET /artifact/{content_address}`` route (``D-IMPL-345``, R-3/R-5).
#: A separate id from :data:`ACTION_REPLAY_READ` because the two routes are
#: separately mountable and an examiner filtering on one must not silently
#: receive the other, even though ``D-IMPL-345`` decides both the same way.
ACTION_ARTIFACT_READ: Final[str] = "artifact.read"


# ---------------------------------------------------------------------------
# The rest of the HTTP front door (``SEC-001``). One identifier per mounted
# route, in the ruled noun order of ``D-IMPL-22/23``. A route's resource — the
# thing the action is performed *on* — is declared beside the handler
# (:mod:`ccf_runtime.authz.route_declaration`), not here: the action says what
# is being done and stays the same wherever the door is reached from, while
# the resource is read out of the request.
# ---------------------------------------------------------------------------

#: Registering one agent definition through the versioned Control Plane path
#: — the HTTP door's ``POST /agent/declarations``. **The ``SEC-002`` class of
#: action**: it writes an artifact other agents then run on, so a deployment
#: is expected to state resource patterns for it rather than a wide grant.
ACTION_AGENT_DECLARE: Final[str] = "agent.declare"

#: Listing the Control Plane keys that hold agent definitions — the HTTP
#: door's ``GET /agent/declarations``. A separate id from
#: :data:`ACTION_AGENT_READ` because enumeration and retrieval are different
#: disclosures: a principal may be entitled to read one key it already knows
#: without being entitled to learn which keys exist.
ACTION_AGENT_LIST: Final[str] = "agent.list"

#: Resolving one agent definition at one exact version — the HTTP door's
#: ``GET /agent/declaration``.
ACTION_AGENT_READ: Final[str] = "agent.read"

#: Listing the versions under one agent key — the HTTP door's
#: ``GET /agent/versions``.
ACTION_AGENT_VERSIONS: Final[str] = "agent.versions"

#: Storing bytes in the artifact store by content address — the HTTP door's
#: ``POST /artifact``. Distinct from :data:`ACTION_ARTIFACT_READ` because the
#: put path is the forgeable half named in ``D-IMPL-345``'s own reasoning, and
#: an examiner filtering on writes must not receive reads.
ACTION_ARTIFACT_WRITE: Final[str] = "artifact.write"

#: Listing the graph adapter names this deployment has installed — the HTTP
#: door's ``GET /backends``. It answers a question about the *process* rather
#: than about any tenant's data, and it is still authorized: what a caller
#: learns is a deployment's shape, which is reconnaissance (``T-15.4-11``).
ACTION_BACKENDS_READ: Final[str] = "backends.read"

#: Listing the Control Plane keys of one artifact class — the HTTP door's
#: ``GET /config/keys``.
ACTION_CONFIG_KEYS_READ: Final[str] = "config.keys.read"

#: Listing the versions under one Control Plane key — the HTTP door's
#: ``GET /config/versions``.
ACTION_CONFIG_VERSIONS_READ: Final[str] = "config.versions.read"

#: Resolving one Control Plane artifact at one exact version — the HTTP
#: door's ``GET /config/resolution``.
ACTION_CONFIG_RESOLVE: Final[str] = "config.resolve"

#: Registering one SDK-typed Control Plane artifact — the HTTP door's
#: ``POST /config/registrations``. **This is the ``SEC-002`` door**: the
#: prompt artifact an underwriting agent runs on is registered through it, and
#: the resource axis exists so that holding this action does not mean holding
#: every key.
ACTION_CONFIG_REGISTER: Final[str] = "config.register"

#: Reading the API's own generated description — the HTTP door's
#: ``GET /openapi.json``. Gated rather than carved out: the document names
#: every route, parameter and contract the deployment exposes, which is the
#: single most useful disclosure on the surface to someone who has none.
ACTION_OPENAPI_READ: Final[str] = "openapi.read"

#: Reading the interactive API documentation pages — the HTTP door's
#: ``GET /docs``, ``GET /docs/oauth2-redirect`` and ``GET /redoc``. **One id
#: for the three**, because the three serve one thing: viewers for the
#: document :data:`ACTION_OPENAPI_READ` governs. Splitting them would ask a
#: deployment to make three statements with one meaning, and the first two to
#: drift would be the two nobody re-reads.
ACTION_DOCS_READ: Final[str] = "docs.read"

#: Answering the liveness probe — the HTTP door's ``GET /health``.
#:
#: **It carries an action for the same reason every other route does**: an
#: exemption is a branch whose condition is the path, and the path is the
#: caller's. The operational consequence is real and is stated rather than
#: discovered — a liveness probe must present a credential the deployment
#: recognises, and a deployment that wants an open probe grants this one
#: action to the scope that probe carries. That grant is then a visible,
#: versioned line in an artifact instead of an invisible branch in SDK code.
ACTION_HEALTH_READ: Final[str] = "health.read"

#: Reading the JSON Schema of one SDK-owned artifact class — the HTTP door's
#: ``GET /schema/{class_id}``.
ACTION_SCHEMA_READ: Final[str] = "schema.read"

#: Listing the artifact classes the SDK serves schemas for — the HTTP door's
#: ``GET /schema``. Separate from :data:`ACTION_SCHEMA_READ` on the
#: enumeration-versus-retrieval line :data:`ACTION_AGENT_LIST` records.
ACTION_SCHEMA_LIST: Final[str] = "schema.list"

#: Reading the deployment's skill catalog — the HTTP door's
#: ``GET /skill/catalog``.
ACTION_SKILL_CATALOG_READ: Final[str] = "skill.catalog.read"

#: Registering one skill catalog entry — the HTTP door's
#: ``POST /skill/catalog``. A capability-defining write, so it is its own
#: action rather than a mode of the read.
ACTION_SKILL_CATALOG_REGISTER: Final[str] = "skill.catalog.register"

#: Issuing one skill grant through the two-tier ledger — the HTTP door's
#: ``POST /skill/grants`` (CLAUDE.md §6.2 channel 2).
ACTION_SKILL_GRANT: Final[str] = "skill.grant"

#: Revoking one skill grant — the HTTP door's ``POST /skill/revocations``.
#: Distinct from :data:`ACTION_SKILL_GRANT`, because a deployment may well
#: want revocation to be the wider of the two: removing a capability is the
#: safe direction, and tying it to the granting action would make the safe
#: direction the harder one.
ACTION_SKILL_REVOKE: Final[str] = "skill.revoke"

#: Invoking one workflow through the factory-and-engine path — the HTTP
#: door's ``POST /workflow/invocations`` (ORCH-01).
ACTION_WORKFLOW_INVOKE: Final[str] = "workflow.invoke"

#: Resuming one suspended workflow past its HITL gate — the HTTP door's
#: ``POST /workflow/resumptions``. **Never folded into**
#: :data:`ACTION_WORKFLOW_INVOKE`: resumption is the verb that carries a
#: human decision past an approval gate, and a deployment that grants
#: *start a workflow* has not thereby granted *approve one*.
ACTION_WORKFLOW_RESUME: Final[str] = "workflow.resume"

#: Reading one workflow execution's persisted state — the HTTP door's
#: ``GET /workflow/execution``.
ACTION_WORKFLOW_STATUS_READ: Final[str] = "workflow.status.read"
