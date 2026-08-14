"""One APIRouter per ruled noun (D-IMPL-22/23), plus shared response plumbing.

SDK-defined (CLAUDE.md §8.3). Each sibling module exposes
``build_router(deps: ApiDependencies) -> APIRouter`` — a closure over the
injected bundle, never a module-level singleton — and every route body
delegates to the same factories and Control Plane actions any client uses
(T-07-25: zero privileged paths).

The refusal-vs-exception line holds over HTTP (T-07-26): an expected typed
refusal serializes as its own contract body under a 4xx status; broken
wiring raises and surfaces as FastAPI's opaque 500, detail-free.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from typing import TypeVar

from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf_runtime.http_api.errors import (
    ERROR_ROUTE_HANDLE_ABSENT,
    refusal_detail,
)

__ccf_mode__ = "algorithmic"

__all__ = ["canonical_response", "refusal_response"]

_JSON = "application/json"

_Handle = TypeVar("_Handle")


def _required_handle(
    handle: _Handle | None, *, field: str, routes: str
) -> _Handle:
    """The one narrowing for an optionally-wired ``ApiDependencies`` handle.

    SDK-defined (CLAUDE.md §8.3; ``D-IMPL-126`` item (3)). Five handles on the
    bundle default to ``None`` so a deployment exposing one noun does not have
    to fabricate seven, and ``None`` is the positive assertion *this deployment
    exposes no such route*. This is what turns that assertion into a typed
    refusal at the eleven sites that read them.

    **One helper rather than eleven ``if ... is None`` blocks**, and the reason
    is not brevity: the refusal shape, the status code and the prose voice are
    then one thing that cannot drift, and ``mypy --strict`` narrows through the
    return type — so a site that forgot to narrow is a ``union-attr`` error
    rather than a latent ``AttributeError`` on ``None`` in production.

    Called **once per handler body**, binding a non-``Optional`` local the rest
    of the body uses (the ``context_seam = context_provider`` pattern at
    ``runtime/ccf_runtime/mcp/experience.py:770``), never once per read.

    Deliberately **not** called at ``build_router`` time. A router must stay
    mountable so the OpenAPI document is complete and this refusal is reachable;
    narrowing at build time would make the route *vanish* rather than refuse,
    which is a different and unruled behaviour.

    Args:
        handle: The possibly-absent handle, read straight off the bundle.
        field: The bundle field's name — carried into the message, because an
            operator reading a 503 should not have to guess which of eight
            handles is missing.
        routes: What this handle gates, in the deployment's own reading order.

    Returns:
        The handle, narrowed to non-``None``.

    Raises:
        fastapi.HTTPException: 503 carrying
            :data:`~ccf_runtime.http_api.errors.ERROR_ROUTE_HANDLE_ABSENT`.
            503 and not 403 for the ``ERROR_PRODUCT_DOOR_UNGOVERNED`` reason:
            the fault is the deployment's, not the caller's.
    """
    if handle is not None:
        return handle
    raise HTTPException(
        status_code=503,
        detail=refusal_detail(
            error_code=ERROR_ROUTE_HANDLE_ABSENT,
            message=(
                f"this deployment did not wire {field}, so it exposes no"
                f" {routes}; the route refuses rather than serving half-wired."
                f" Supply {field}= to the ApiDependencies bundle passed to"
                " create_app() (D-IMPL-126)"
            ),
        ),
    )


def canonical_response(payload: object) -> Response:
    """Serve ``payload`` as its canonical bytes — the same serialization the
    content address and the A2A signature are computed over, so a consumer
    that hashes what it received gets the address the producer would."""
    return Response(content=canonical_bytes(payload), media_type=_JSON)


def refusal_response(refusal: CCFContract, *, status_code: int) -> JSONResponse:
    """A typed refusal as a 4xx body — the refusal contract, nothing else."""
    return JSONResponse(
        status_code=status_code,
        content=json.loads(canonical_bytes(refusal)),
    )
