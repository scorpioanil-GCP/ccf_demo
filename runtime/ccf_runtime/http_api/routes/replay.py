"""The ``replay`` noun — decisions and exact-version resolution (D-IMPL-23).

Both reads are **governed dereferences** (``D-IMPL-345``), not lookups. The
route authenticates through the app's own dependency, reads the verified
grant, calls the ONE governed step
:func:`~ccf_runtime.authz.delivery_boundary.govern_dereference`, and
**encodes what it returns**: a
:class:`~ccf.replay.record.DecisionReplayRecord` as its canonical bytes, or an
already-recorded, already-disclosed refusal shell through the same renderer
every other governed refusal on this API goes through. Nothing on this page
decides, mints a record, discloses, or reads a clock.

What changed, and why (``D-IMPL-345``, from ``S-01``). Before it, both
handlers took only their query parameter and answered ``200`` with the whole
five-dimension record to any recognized bearer — so a principal whose serve
had been refused at minimal disclosure could dereference the very
``replay_reference`` that refusal handed it and read the cause the shell
withheld, and any bearer holding another principal's record address could read
that principal's record. Absence answered in a different body shape from
presence, which is the existence oracle ``D-IMPL-253`` amendment 2 (4)
forbids. The guarantees this surface inherits from
:mod:`ccf.replay.engine` are unchanged underneath: an exact version is
resolved and there is no fallback, and ``@latest`` still dies here
(:class:`~ccf.artifacts.protocol.MovingTargetRefused` → 409) exactly as it
dies in-process (D-IMPL-26).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from starlette.requests import Request

from ccf.artifacts.protocol import MovingTargetRefused
from ccf.authz.capability import ReplayRead, kind_for_action
from ccf.products.refusal import RefusalEnvelope
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_HTTP_REPLAY_READ,
    DereferenceRequest,
    DisclosingRecorderProtocol,
    govern_dereference,
)
from ccf_runtime.authz.product_entitlement import (
    ProductEntitlementSourceProtocol,
)
from ccf_runtime.authz.refusals import ACTION_REPLAY_READ
from ccf_runtime.authz.route_declaration import (
    ProductClassBinding,
    ResourceBinding,
    authorizes,
)
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.grants import authorized_from_request
from ccf_runtime.http_api.routes import (
    canonical_response,
    governed_refusal_response,
)

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]

# The kind these two doors dereference under is the kind their declared action
# mints — the same lookup the gate performs; `kind_for_action` is the proof
# that `ReplayRead` is `replay.read`'s kind rather than an assumption of it.
assert kind_for_action(ACTION_REPLAY_READ) is ReplayRead


def _route_path(request: Request, reference: str) -> str:
    """The ROUTE the caller reached, never the string it asked for.

    ``/artifact/{content_address}`` rather than ``/artifact/<the address>``:
    the reference a caller supplied is echoed in exactly ONE place, its
    refusal's ``request.parameters``, so every other member of the shell is
    constant across asks and a control comparing two refusals is comparing
    the determination rather than the two strings that provoked it.
    """
    path = request.url.path
    template = str(getattr(request.scope.get("route"), "path", ""))
    if template.endswith("}") and path.endswith(reference):
        return path[: -len(reference)] + template[template.rfind("{") :]
    return path


def build_router(
    deps: ApiDependencies,
    *,
    entitlement_source: ProductEntitlementSourceProtocol,
    refusal_recorder: DisclosingRecorderProtocol,
) -> APIRouter:
    """The replay router over the injected artifact store and governance seams.

    Args:
        deps: The named provider bundle carrying the artifact store and the
            Control Plane whose audit log every dereference appends to.
        entitlement_source: The deployment's entitlement seam. **Required**
            (``SEC-001``): ``D-IMPL-345`` R-1 said a surface that cannot
            decide does not answer from the store, and it used to say that
            with a per-request ``503`` because ``create_app`` could be built
            without the seam. It cannot any more, so the rule is now held by
            the signature instead of by a branch.
        refusal_recorder: The ONE minting seam, which also states the
            disclosure level. **Required**, checked at construction by the
            app's
            :func:`~ccf_runtime.authz.delivery_boundary.disclosing_boundary`.
    """
    router = APIRouter()

    def _dereferenced(
        request: Request, reference: DereferenceRequest
    ) -> Response:
        """Authenticate, govern, encode. The route's whole job."""
        # D-IMPL-353 §1.4: `Authorized[ReplayRead]` for THIS reference, or
        # nothing — and the governed step verifies it again, bound to the
        # reference, before its first real statement (§1.2).
        authorized = authorized_from_request(request, kind=ReplayRead)
        try:
            decided = govern_dereference(
                authorized,
                reference=reference,
                store=deps.artifact_store,
                entitlement_source=entitlement_source,
                refusal_recorder=refusal_recorder,
                audit_log=deps.control_plane.audit_log,
                surface=SURFACE_HTTP_REPLAY_READ,
                address=_route_path(request, reference.reference),
            )
        except MovingTargetRefused as moving:
            # A request-shape refusal raised by the shared parser before any
            # lookup: it reveals nothing about the store, and it answered 409
            # here before D-IMPL-345 as it does in-process.
            raise HTTPException(status_code=409, detail=str(moving)) from moving
        if isinstance(decided, RefusalEnvelope):
            return governed_refusal_response(decided)
        return canonical_response(decided.record)

    @router.get("/decisions", summary="Replay decision (D-IMPL-23)")
    @authorizes(
        ACTION_REPLAY_READ,
        resource=ResourceBinding.query("content_address"),
        # SEC-017: a record's class is not on the wire; the deployment's
        # declared replay_record_product_class is what a roster is held to.
        products=ProductClassBinding.replay_declared(),
    )
    def decision(content_address: str, request: Request) -> Response:
        return _dereferenced(
            request,
            DereferenceRequest(
                reference=content_address, by_uri=False, wants_bytes=False
            ),
        )

    @router.get("/resolutions", summary="Replay resolve (D-IMPL-23)")
    @authorizes(
        ACTION_REPLAY_READ,
        resource=ResourceBinding.query("uri"),
        products=ProductClassBinding.replay_declared(),
    )
    def resolution(uri: str, request: Request) -> Response:
        return _dereferenced(
            request,
            DereferenceRequest(reference=uri, by_uri=True, wants_bytes=False),
        )

    return router
