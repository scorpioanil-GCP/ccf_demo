"""The ``config`` noun — Control Plane introspection (D-IMPL-22/23).

Reads only, and only through the registry's own introspection surface:
keys by artifact class, versions under a key, and pinned resolution — the
same versioned, audited artifacts every other Control Plane consumer
resolves. The SDK enumerates no class vocabulary here; ``class_id`` is the
caller's statement (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ccf.controlplane.registry import ControlPlaneMissing
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.routes import canonical_response

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]


def build_router(deps: ApiDependencies) -> APIRouter:
    """The config router over the injected Control Plane."""
    router = APIRouter()

    @router.get(
        "/keys",
        response_model=list[str],
        summary="Config keys (D-IMPL-23)",
    )
    def keys(class_id: str) -> list[str]:
        return list(deps.control_plane.keys_of_class(class_id))

    @router.get(
        "/versions",
        response_model=list[str],
        summary="Config versions (D-IMPL-23)",
    )
    def versions(key: str) -> list[str]:
        return list(deps.control_plane.versions(key))

    @router.get("/resolution", summary="Config resolve (D-IMPL-23)")
    def resolution(key: str, version: str) -> Response:
        try:
            artifact = deps.control_plane.resolve(key, version)
        except ControlPlaneMissing as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        return canonical_response(artifact)

    return router
