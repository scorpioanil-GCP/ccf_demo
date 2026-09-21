"""Door-declared action identifiers for tenant authorization (D-02/D-08).

SDK-defined (CLAUDE.md §8.3; D-IMPL-68; 10-CONTEXT D-02/D-08). The action
vocabulary a :class:`~ccf_runtime.authz.artifact.ScopeMappingArtifact`
matches against is declared by the doors themselves — the SDK invents no
scope vocabulary, but its two shipped HITL doors are code, so their action
identifiers are declared here once and imported by both (HTTP route and
MCP tool), never re-typed. One vocabulary, two renderings (D-08): the HTTP
door refuses with the typed 403 body, the MCP door with its
protocol-native error, both carrying
:data:`~ccf_runtime.http_api.errors.ERROR_TENANT_UNAUTHORIZED`.

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
    "ACTION_ARTIFACT_READ",
    "ACTION_HITL_ACTION_SUBMIT",
    "ACTION_HITL_QUEUE_READ",
    "ACTION_PRODUCT_RETRIEVE",
    "ACTION_REPLAY_READ",
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
