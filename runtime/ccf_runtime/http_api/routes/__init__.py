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

import hashlib
import json
from typing import Final, TypeVar

from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf_runtime.http_api.errors import (
    ERROR_ROUTE_HANDLE_ABSENT,
    refusal_detail,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "CONTENT_ADDRESS_HEADER",
    "canonical_response",
    "refusal_response",
]

_JSON = "application/json"

#: The response header every canonical body publishes its own content address
#: under (``D-IMPL-126`` item (4); the address primitive is ``D-IMPL-26``).
#:
#: Named here rather than spelled at the one site that sets it, so a test and an
#: adopter's client reach for the same constant and a rename is one edit.
CONTENT_ADDRESS_HEADER: Final[str] = "X-CCF-Content-Address"

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
    of the body uses (the ``context_seam = context_provider`` pattern in
    ``runtime/ccf_runtime/mcp/experience.py::build_experience_server``), never
    once per read.

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
    """Serve ``payload`` as its canonical bytes, and publish their address.

    The bytes are the same serialization the content address and the A2A
    signature are computed over, so a consumer that hashes what it received
    gets the address the producer would. That claim was true before
    ``D-IMPL-126`` item (4) and merely unverifiable from outside: a consumer had
    to already own a CCF canonicalizer to check it. The address now travels on
    the response under :data:`CONTENT_ADDRESS_HEADER`, so a zero-``ccf`` client
    verifies it in one stdlib line —
    ``hashlib.sha256(response.content).hexdigest() ==
    response.headers["X-CCF-Content-Address"]``.

    **Serialized once.** The body and the digest are derived from one
    ``canonical_bytes`` call, never two: two serializations of the same object
    are two chances to disagree, and the whole value of the header is that it
    cannot. (A consequence worth stating because it looks like an omission:
    this function does not call
    :func:`~ccf.contracts.canonical.content_hash`. That function serializes and
    hashes; calling it here would be the second serialization. The equivalence
    to it is asserted in ``tests/http_api/test_content_address_header.py``,
    which is where an equivalence belongs.)

    **Why an ``X-CCF-*`` name and not ``ETag``.** Both were available and
    ``ETag`` was rejected; recorded here so it is not re-proposed as an
    oversight.

    1. **A CCF content address is an identity, not a cache validator.** It is
       the ``D-IMPL-26`` primitive the ArtifactStore resolves and replay pins
       against. RFC 9110 permits an intermediary to weaken a strong ``ETag`` to
       ``W/"..."`` or rewrite it across a content-coding transformation. An
       identity a proxy may legally alter is not an identity.
    2. **``ETag`` advertises cacheability on an entitlement-scoped body.** These
       responses are per-principal and per-perspective — ``entitled_perspective``
       decides before the resolver runs — and an ``ETag`` invites an
       intermediary to hold and re-serve a governed product. An ``X-CCF-*``
       header carries no HTTP caching semantics and issues no such invitation,
       which is also why no ``Cache-Control`` change is owed: the hazard is
       avoided by the header choice rather than papered over with a second
       header.
    3. **``ETag`` is per-representation; the address is per-object.** The moment
       this door gains content negotiation or compression the two must diverge,
       and an ``ETag`` set to the content address would then be lying.
    4. Implementing ``ETag`` honestly means ``If-None-Match`` and a 304 path —
       real behaviour on a shipped door, outside what ``D-IMPL-126`` ruled.

    Both were not shipped: two headers carrying the same hex string, one of
    which a proxy may rewrite, is a guarantee that fails silently.

    **The MCP doors are deliberately untouched.** They have no header channel,
    and their bodies *are* the product — so carrying the address inside the body
    would change the body and therefore change the address it claims. The
    asymmetry is a property of the transports, not an oversight.

    All five call sites — ``agent.py:74``, ``config.py:98``, ``replay.py:47``,
    ``replay.py:65`` and ``product.py:154`` — pass a
    :class:`~ccf.contracts.base.CCFContract`, so the claim is uniformly true at
    every one. :func:`refusal_response` sets no such header: a refusal is not a
    content-addressed artifact and stamping every response would make the
    header meaningless.
    """
    body = canonical_bytes(payload)
    return Response(
        content=body,
        media_type=_JSON,
        headers={CONTENT_ADDRESS_HEADER: hashlib.sha256(body).hexdigest()},
    )


def refusal_response(refusal: CCFContract, *, status_code: int) -> JSONResponse:
    """A typed refusal as a 4xx body — the refusal contract, nothing else."""
    return JSONResponse(
        status_code=status_code,
        content=json.loads(canonical_bytes(refusal)),
    )
