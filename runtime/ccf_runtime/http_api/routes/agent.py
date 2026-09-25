"""The ``agent`` noun — declare/list/show/versions (D-IMPL-22/23).

Declaration takes an artifact payload — a complete
:class:`~ccf.agents.definitions.AgentDefinition` — and registers it through
the same D-05 versioned Control Plane path any client takes; there are no
inline definition fields beyond the artifact itself (No-Hardcoding, CLAUDE.md
§6.4). Reads resolve the same versioned, audited artifacts every other
Control Plane consumer reads.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.authz.capability import AgentDeclare, AgentList, AgentRead, AgentVersions
from ccf.contracts.base import CCFContract
from ccf.controlplane.registry import ControlPlaneMissing, RegistrationRefusal
from ccf_runtime.authz.refusals import (
    ACTION_AGENT_DECLARE,
    ACTION_AGENT_LIST,
    ACTION_AGENT_READ,
    ACTION_AGENT_VERSIONS,
)
from ccf_runtime.authz.route_declaration import ResourceBinding, authorizes
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.grants import authorized_from_request
from ccf_runtime.http_api.routes import canonical_response, refusal_response

__ccf_mode__ = "algorithmic"

__all__ = ["AgentDeclarationRequest", "AgentDeclared", "build_router"]


class AgentDeclarationRequest(CCFContract):
    """One declaration: the Control Plane key and the artifact payload."""

    key: str
    definition: AgentDefinition


class AgentDeclared(CCFContract):
    """The registered outcome — the key and its content-hash version."""

    key: str
    version: str


def build_router(deps: ApiDependencies) -> APIRouter:
    """The agent router over the injected Control Plane."""
    router = APIRouter()

    @router.post(
        "/declarations",
        response_model=AgentDeclared,
        summary="Agent declare (D-IMPL-23)",
    )
    @authorizes(ACTION_AGENT_DECLARE, resource=ResourceBinding.body("key"))
    def declare(
        body: AgentDeclarationRequest, request: Request
    ) -> AgentDeclared | JSONResponse:
        # D-IMPL-353 §1.4: the handler holds the capability the gate minted
        # for THIS action, or it holds nothing and refuses.
        authorized = authorized_from_request(request, kind=AgentDeclare)
        # JOIN (§1.2, Lane HANDLES): `register_versioned(authorized, artifact,
        # artifact_class)` — the key becomes `authorized.resource`. Left on
        # today's signature; `authorized.resource == body.key` by the gate.
        assert authorized.resource == body.key
        outcome = deps.control_plane.register_versioned(
            body.key, body.definition, AGENT_DEFINITION
        )
        if isinstance(outcome, RegistrationRefusal):
            return refusal_response(outcome, status_code=409)
        return AgentDeclared(key=body.key, version=outcome)

    @router.get(
        "/declarations",
        response_model=list[str],
        summary="Agent list (D-IMPL-23)",
    )
    @authorizes(ACTION_AGENT_LIST, resource=ResourceBinding.route())
    def declarations(request: Request) -> list[str]:
        authorized_from_request(request, kind=AgentList)
        return list(deps.control_plane.keys_of_class(AGENT_DEFINITION.class_id))

    @router.get("/declaration", summary="Agent show (D-IMPL-23)")
    @authorizes(ACTION_AGENT_READ, resource=ResourceBinding.query("key"))
    def declaration(key: str, version: str, request: Request) -> Response:
        authorized_from_request(request, kind=AgentRead)
        try:
            artifact = deps.control_plane.resolve(key, version)
        except ControlPlaneMissing as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        return canonical_response(AGENT_DEFINITION.validate(artifact))

    @router.get(
        "/versions",
        response_model=list[str],
        summary="Agent versions (D-IMPL-23)",
    )
    @authorizes(ACTION_AGENT_VERSIONS, resource=ResourceBinding.query("key"))
    def versions(key: str, request: Request) -> list[str]:
        authorized_from_request(request, kind=AgentVersions)
        return list(deps.control_plane.versions(key))

    return router
