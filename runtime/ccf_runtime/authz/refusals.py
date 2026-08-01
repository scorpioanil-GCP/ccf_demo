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
    "ACTION_HITL_ACTION_SUBMIT",
    "ACTION_HITL_QUEUE_READ",
]

#: Reading one tenant's pending HITL queue — declared by the HTTP door's
#: ``GET /hitl/queue`` and the MCP door's queue resource (D-02).
ACTION_HITL_QUEUE_READ: Final[str] = "hitl.queue.read"

#: Submitting one human action — declared by the HTTP door's
#: ``POST /hitl/actions`` and the MCP door's action tool (D-02).
ACTION_HITL_ACTION_SUBMIT: Final[str] = "hitl.action.submit"
