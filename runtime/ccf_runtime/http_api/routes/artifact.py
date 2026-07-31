"""The ``artifact`` noun — get/put against the injected store (D-IMPL-23).

Put stores through the same content-addressed, idempotent
:class:`~ccf.artifacts.protocol.ArtifactStoreProtocol` any client uses;
get returns the exact canonical bytes at an address — byte fidelity is the
store's contract, and deciding which contract those bytes are is the
caller's business. The store is a persistence substrate behind mechanism,
never a second writer to the graph (CLAUDE.md §7.4).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ccf.artifacts.protocol import ArtifactNotFound, ArtifactRef
from ccf.contracts.base import CCFContract
from ccf_runtime.http_api.dependencies import ApiDependencies

__ccf_mode__ = "algorithmic"

__all__ = ["ArtifactPutRequest", "build_router"]

_JSON = "application/json"


class ArtifactPutRequest(CCFContract):
    """One put: the addressing facts and the canonicalizable payload."""

    tenant_id: str
    artifact_class: str
    name: str
    artifact: dict[str, object]


def build_router(deps: ApiDependencies) -> APIRouter:
    """The artifact router over the injected store."""
    router = APIRouter()

    @router.post(
        "",
        response_model=ArtifactRef,
        summary="Artifact put (D-IMPL-23)",
    )
    def put(request: ArtifactPutRequest) -> ArtifactRef:
        return deps.artifact_store.put(
            tenant_id=request.tenant_id,
            artifact_class=request.artifact_class,
            name=request.name,
            artifact=request.artifact,
        )

    @router.get("/{content_address}", summary="Artifact get (D-IMPL-23)")
    def get(content_address: str) -> Response:
        try:
            stored = deps.artifact_store.get(content_address=content_address)
        except ArtifactNotFound as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        return Response(content=stored, media_type=_JSON)

    return router
