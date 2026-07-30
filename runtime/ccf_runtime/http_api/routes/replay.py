"""The ``replay`` noun — decisions and exact-version resolution (D-IMPL-23).

Both reads go through :mod:`ccf.replay.engine`'s resolution path, so the
HTTP surface inherits its guarantees unchanged: an absent record is a 404,
divergent bytes are a 409, and ``@latest`` dies here exactly as it dies
in-process (:class:`~ccf.artifacts.protocol.MovingTargetRefused` → 409) —
replay resolves an exact version and has no fallback (D-IMPL-26).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ccf.artifacts.protocol import MovingTargetRefused
from ccf.replay.engine import ReplayDivergence, ReplayUnresolvable
from ccf.replay.engine import resolve_artifact, resolve_artifact_at_uri
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.routes import canonical_response

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]


def build_router(deps: ApiDependencies) -> APIRouter:
    """The replay router over the injected artifact store."""
    router = APIRouter()

    @router.get("/decisions", summary="Replay decision (D-IMPL-23)")
    def decision(content_address: str) -> Response:
        try:
            record = resolve_artifact(
                store=deps.artifact_store,
                content_address=content_address,
                contract=DecisionReplayRecord,
            )
        except ReplayUnresolvable as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        except ReplayDivergence as diverged:
            raise HTTPException(
                status_code=409, detail=str(diverged)
            ) from diverged
        return canonical_response(record)

    @router.get("/resolutions", summary="Replay resolve (D-IMPL-23)")
    def resolution(uri: str) -> Response:
        try:
            record = resolve_artifact_at_uri(
                store=deps.artifact_store,
                uri=uri,
                contract=DecisionReplayRecord,
            )
        except MovingTargetRefused as moving:
            raise HTTPException(status_code=409, detail=str(moving)) from moving
        except ReplayUnresolvable as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        except ReplayDivergence as diverged:
            raise HTTPException(
                status_code=409, detail=str(diverged)
            ) from diverged
        return canonical_response(record)

    return router
