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

from fastapi.responses import JSONResponse, Response

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes

__ccf_mode__ = "algorithmic"

__all__ = ["canonical_response", "refusal_response"]

_JSON = "application/json"


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
