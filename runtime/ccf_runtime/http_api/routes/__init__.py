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

import base64
import hashlib
import json
from typing import Final, TypeVar

from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response

from types import MappingProxyType
from typing import Mapping

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import WireRequest
from ccf.products.refusal import REFUSAL_KINDS, RefusalEnvelope
from ccf_runtime.http_api.refusal_status import status_for
from ccf_runtime.http_api.errors import (
    ERROR_ROUTE_HANDLE_ABSENT,
    refusal_detail,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "CONTENT_ADDRESS_HEADER",
    "REPLAY_REF_HEADER",
    "REQUEST_ECHO_HEADER",
    "canonical_response",
    "governed_refusal_response",
    "refusal_response",
]

_JSON = "application/json"

#: The response header every canonical body publishes its own content address
#: under (``D-IMPL-126`` item (4); the address primitive is ``D-IMPL-26``).
#:
#: Named here rather than spelled at the one site that sets it, so a test and an
#: adopter's client reach for the same constant and a rename is one edit.
CONTENT_ADDRESS_HEADER: Final[str] = "X-CCF-Content-Address"

#: The response header a served product publishes its **replay reference**
#: under — the versioned URI of the record whose successful append authorized
#: the delivery (``D-IMPL-148`` Addendum A, Dave, 2026-08-17; the reference is
#: :attr:`~ccf.artifacts.protocol.ArtifactRef.uri`).
#:
#: **A sibling of the vessel, on the identical argument**
#: :data:`CONTENT_ADDRESS_HEADER` **is one.** The body *is* the product, so a
#: reference carried inside it would change the bytes and therefore change the
#: address they claim. The four reasons :func:`canonical_response` gives for
#: choosing an ``X-CCF-*`` name over a standard header apply here unchanged and
#: are not restated.
#:
#: **Set only when there is one to publish**, and its absence is meaningful:
#: this deployment's resolver answered with the narrower
#: :class:`~ccf.products.gates.ServableProduct`, which carries no reference.
#: Stamping an empty header would make "no record was named" and "the record is
#: named by nothing" the same observation.
REPLAY_REF_HEADER: Final[str] = "X-CCF-Replay-Ref"

#: The response header a served product publishes **the question this door was
#: asked** under — the caller's own :class:`~ccf.products.door.WireRequest`,
#: canonically serialized and base64url-wrapped (``C-09``).
#:
#: **A sibling of the vessel, on the identical argument** the two constants
#: above are. The body *is* the product, so a question carried inside it would
#: change the bytes and therefore change the address they claim. The four
#: reasons :func:`canonical_response` gives for choosing an ``X-CCF-*`` name
#: over a standard header apply here unchanged and are not restated. ``C-09``
#: scopes *one shape* to the doors that **have** an envelope; this door has a
#: header channel instead, so its ruling is extended rather than amended.
#:
#: **base64url rather than the canonical JSON verbatim**, and the reason is not
#: taste: a header value has to survive every intermediary, and canonical JSON
#: carries ``"`` and may carry non-ASCII, which RFC 9110 discourages in a field
#: value. The objection :class:`~ccf.products.door.WireRequest`'s own module
#: records against a *second rendering* does not transfer — that argument is
#: about the **vessel**, whose address is a function of its bytes, and nothing
#: anywhere hashes this echo.
#:
#: **Set only when there was a question**, and its absence is meaningful: a
#: caller who supplied none of the four §6.3 axes asked for the class's
#: standing answer and posed no question of their own — the positive assertion
#: the product route's ``_asked`` returns ``None`` to make. Stamping an empty
#: header would make "no question was asked" and "the question is named by
#: nothing" the same observation.
REQUEST_ECHO_HEADER: Final[str] = "X-CCF-Request-Echo"

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


def canonical_response(
    payload: object,
    *,
    replay_ref: str | None = None,
    asked: WireRequest | None = None,
) -> Response:
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

    **The MCP resource is deliberately untouched, and the MCP tool now carries
    the sibling in an envelope instead** (``D-IMPL-148`` Addendum A). The
    resource has no header channel and no envelope — its body *is* the product,
    so carrying anything inside it would change the body and therefore change
    the address it claims. The tool's return became a
    :class:`~ccf.products.door.DoorOutcome` because a refusal cannot be raised
    over FastMCP without prose, and a structure has room for siblings that a
    bare body does not. **The asymmetry is a property of the transports, not a
    difference in what the doors carry**: each surface publishes the same
    sibling values through whatever channel it actually has.

    All five call sites — ``agent.py:74``, ``config.py:98``, ``replay.py:47``,
    ``replay.py:65`` and ``product.py``'s ``retrieve`` — pass a
    :class:`~ccf.contracts.base.CCFContract`, so the claim is uniformly true at
    every one. :func:`refusal_response` sets no such header: a refusal is not a
    content-addressed artifact and stamping every response would make the
    header meaningless.

    Args:
        payload: The contract to serve. Serialized exactly once.
        replay_ref: The versioned URI of the replay record that authorized this
            delivery, published under :data:`REPLAY_REF_HEADER`. ``None`` — the
            default, and what the four non-product call sites pass — means
            **there is no reference to publish**, and the header is then absent
            rather than empty: those four serve Control Plane and replay
            artifacts rather than a delivered Context Product, and the product
            door itself passes ``None`` when its resolver answered with the
            narrower vessel that carries no reference.
        asked: The question this door parsed and answered, published under
            :data:`REQUEST_ECHO_HEADER` (``C-09``). ``None`` — the default, and
            what the four non-product call sites pass — means **no question was
            posed**, and the header is then absent rather than empty, on
            exactly the reasoning ``replay_ref`` carries one paragraph up.

            **Serialized independently of the vessel, and that is why the
            serialize-once discipline above is untouched.** ``body`` is still
            the single ``canonical_bytes`` call over ``payload``; this is a
            second
            serialization of a *different object*, which is what
            :data:`REPLAY_REF_HEADER` already is — a string obtained elsewhere
            and stamped beside the body. Nothing hashes the echo, so it can
            never disagree with the address.

            **A future HTTP adapter reconstructs this echo by decoding the
            header, never from its own state.** That sentence is the whole of
            ``C-09``: the value here originates producer-side, from the query
            axes the route itself parsed, so a consumer comparing it against
            what it sent is comparing two independently-sourced facts rather
            than an object with itself.

            **The transport asymmetry, recorded rather than engineered away.**
            This door requires ``asked_at`` whenever any §6.3 axis is supplied,
            so an echo published here never carries a ``None``
            ``temporal_boundary``; ``mcp+stdio`` carries ``None`` faithfully,
            because there a caller *can* say *defer to the server's decision
            instant*. A future HTTP adapter must therefore send an explicit
            instant. ``C-18``'s temporal cross-check consequently has no
            subject on this door — the echo's boundary is built **from** the
            one ``asked_at`` this route parsed, so there is exactly one source
            and a cross-check would compare a value with itself.
    """
    body = canonical_bytes(payload)
    headers = {CONTENT_ADDRESS_HEADER: hashlib.sha256(body).hexdigest()}
    if replay_ref is not None:
        headers[REPLAY_REF_HEADER] = replay_ref
    if asked is not None:
        headers[REQUEST_ECHO_HEADER] = base64.urlsafe_b64encode(
            canonical_bytes(asked)
        ).decode("ascii")
    return Response(content=body, media_type=_JSON, headers=headers)


def refusal_response(refusal: CCFContract, *, status_code: int) -> JSONResponse:
    """A typed refusal as a 4xx body — the refusal contract, nothing else."""
    return JSONResponse(
        status_code=status_code,
        content=json.loads(canonical_bytes(refusal)),
    )


#: :data:`~ccf.products.refusal.REFUSAL_KINDS`, read backwards.
#:
#: The body's ``refusal_type`` has been the Python class name since the first
#: mapped kind, and the two deleted branches each spelled one by hand
#: (``DeclaredObligationRefusal.__name__``). Derived here instead, so a body
#: shape that was correct for two kinds is correct for twenty-three without a
#: branch per kind — and so this module names no refusal class at all.
_TYPE_NAME_BY_KIND: Final[Mapping[str, str]] = MappingProxyType(
    {kind: refusal_type.__name__ for refusal_type, kind in REFUSAL_KINDS.items()}
)


def _type_name_for(kind: str) -> str:
    """The refusal class's own name, for the body's ``refusal_type`` member.

    Args:
        kind: :attr:`~ccf.products.refusal.RefusalEnvelope.kind`.

    Returns:
        The Python class name the kind was minted from.

    Raises:
        KeyError: ``kind`` is not in the vocabulary — the same invariant
            violation :func:`~ccf_runtime.http_api.refusal_status.status_for`
            refuses, and reached only by a caller that skipped the membership
            test this route runs first.
    """
    return _TYPE_NAME_BY_KIND[kind]


def governed_refusal_response(envelope: RefusalEnvelope) -> JSONResponse:
    """One governed refusal, one status class, one body shape.

    The ONE emission path for every governed refusal this API answers — a
    gate's, a
    request-conformity verdict's, the delivery boundary's entitlement
    determination and, since ``D-IMPL-345``, an evidence dereference's alike. That sameness is the D-27 property (``D-IMPL-253``
    amendment 2 (4)): an unauthorized principal and a nonexistent subject reach
    the consumer through this function, so the status, the schema, the field
    set and the message are the same by construction rather than by two
    branches that happen to agree.

    The status comes from the **disclosed** kind
    (:mod:`ccf_runtime.http_api.refusal_status`) and from nothing else. The
    body is the whole envelope in the ``routes/skill.py`` shape, so the debt
    block's numbers, a violation's reason and key, the request identity and the
    replay reference all travel — whatever of them the Disclosure layer
    permitted to cross (``D-IMPL-254``). This door withholds nothing of its own
    and adds nothing of its own.

    Args:
        envelope: The disclosed shell, as the fabric or the governed delivery
            boundary produced it.

    Returns:
        The response, ready to return.
    """
    return JSONResponse(
        status_code=status_for(envelope.kind),
        content={
            "kind": envelope.kind,
            "refusal_type": _type_name_for(envelope.kind),
            "refusal": json.loads(canonical_bytes(envelope)),
        },
    )
