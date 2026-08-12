"""The ``product`` noun — retrieval only (D-IMPL-23; whitepaper §8.3 P3).

Read-only by construction: the router registers GET and nothing else, and
the seam it holds is the egress resolver
(:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol`) — the same
already-servable-product seam the MCP front door holds, trading only in
gate-admitted :class:`~ccf.products.gates.ServableProduct`s. No write door
can exist here because no handle here could hold one (T-07-23).

**The 15.5-06 entitlement composition.** This is the third of the three
exposed product doors, and it asks the *same question* the two MCP doors ask,
through the *same code*: the seams and the resolution order come from
:mod:`ccf_runtime.authz.product_entitlement`, imported rather than
re-declared. Three doors that disagreed about what "entitled" means is the
drift ``run_gates``/``run_federated_gates`` share their comparison functions
specifically to prevent.

**Why the seams are optional here and required on the MCP doors.**
Authentication on this surface is ``create_app``'s ``auth=`` hook, which is
itself optional by ruling (D-IMPL-73 — the acknowledged insecure default, with
its own warning). An entitlement seam that were required here would make this
app unbuildable in the very posture the SDK explicitly still supports, so
instead the seams are optional and ``create_app`` warns when they are bound
without ``auth=`` — an entitlement check downstream of no authentication can
never run (WR-05's shape). On the MCP builders there is no such posture: both
are authenticated by construction, so their seams are required and there is no
inert configuration of either.

**The role is a query parameter, not a path segment.** The three path segments
are the product's *address*; a role is the caller's *request about capacity*,
and folding it into the address would change what a product URI means on a
surface whose MCP siblings address the same three facts. It is optional: with
no ``role``, the deployment's resolver derives one from the verified grant,
and whatever it derives is still checked against the grant.

**This is the one door with a query surface, so it is the one door that can
carry a request** (``D-IMPL-108``, closing plan ``15.5-08``'s undeliverable
must-have). Whitepaper §6.3 **Addressability**
(``docs/CCF_Whitepaper_1-2.md:1465``) writes the address as
``/context-products/credit-risk/counterparty/{counterparty-id}?intent=…&freshness=…``
— path for *what*, query for *what is being asked of it* — and that is exactly
the split this route now realizes. The four §6.3 axes arrive as query
parameters and the door assembles them into a
:class:`~ccf.products.request.ProductRequest` before the resolver is reached.

**The request's address is the door's, never the caller's.** ``schema_name``
and ``schema_version`` are filled from the *path segments this door already
resolved*, so a request addressed to a class other than the one being served
is **unrepresentable** rather than merely refused — the strongest available
form of "validated where it crosses the door, not downstream", and the reason
this route needs no address cross-check. The tenant is likewise not on the
request at all: it is a thing the door establishes.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from starlette.requests import Request

from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementRefused,
    ProductEntitlementSourceProtocol,
    entitled_perspective,
)
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import (
    ERROR_PRODUCT_DOOR_UNGOVERNED,
    ERROR_PRODUCT_REQUEST_INCOMPLETE,
    refusal_detail,
)
from ccf_runtime.http_api.grants import grant_from_request
from ccf_runtime.http_api.routes import canonical_response
from ccf_runtime.mcp.egress import ProductNotServable

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]


def build_router(
    deps: ApiDependencies,
    *,
    entitlement_source: ProductEntitlementSourceProtocol | None = None,
    perspective_resolver: PerspectiveResolverProtocol | None = None,
) -> APIRouter:
    """The product router over the injected resolver seam.

    Args:
        deps: The named provider bundle carrying the assemble-and-gate path.
        entitlement_source: The deployment's per-principal entitlement
            decision seam. Required *together* with ``perspective_resolver``
            when either is supplied: an entitlement with no perspective to
            decide about, or a perspective nothing checks, is a half-bound
            door that looks governed.
        perspective_resolver: The deployment's role-derivation seam.

    Raises:
        ValueError: exactly one of the two governance seams was supplied.
    """
    if (entitlement_source is None) != (perspective_resolver is None):
        raise ValueError(
            "entitlement_source and perspective_resolver are supplied"
            " together or not at all: an entitlement source with no"
            " perspective to decide about, or a perspective resolver whose"
            " output nothing checks, is a door that looks governed and"
            " enforces half a decision (15.5-06)"
        )
    router = APIRouter()

    @router.get(
        "/{tenant}/{product_class}/{version}",
        summary="Product retrieval (D-IMPL-23)",
    )
    def retrieve(
        tenant: str,
        product_class: str,
        version: str,
        request: Request,
        role: str | None = None,
        subject: str | None = None,
        intent: str | None = None,
        freshness: str | None = None,
        asked_at: datetime | None = None,
    ) -> Response:
        perspective = _authorized_perspective(
            request, tenant=tenant, product_class=product_class, role=role
        )
        asked = _asked(
            product_class=product_class,
            version=version,
            subject=subject,
            intent=intent,
            freshness=freshness,
            asked_at=asked_at,
        )
        try:
            servable = deps.product_resolver(
                tenant=tenant,
                product_class=product_class,
                version=version,
                perspective=perspective,
                request=asked,
            )
        except ProductNotServable as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        return canonical_response(servable.product)

    def _authorized_perspective(
        request: Request, *, tenant: str, product_class: str, role: str | None
    ) -> Perspective:
        """The conditioning this door authorizes, or no product at all.

        Ask the bound seams before the resolver is reached, and **return what
        they decided** rather than only whether they refused (``DI-15.5-03``,
        closed by ``D-IMPL-108``). Until plan ``15.5-15`` this function was
        called for its exception and its return value was discarded, so the
        route proved that an unentitled caller was refused while leaving
        unproven that the product it served was shaped under the perspective
        it had authorized.

        **It is no longer inert, and that is the substantive change.** The
        previous shape returned quietly when the seams were unbound or when no
        verified grant accompanied the call, and the resolver then ran with no
        perspective at all. That is no longer expressible: the resolver seam
        requires one, deliberately, because a door that manufactured a
        perspective would serve a product conditioned on a role nobody granted
        and nothing on the wire would say so. With no authorized perspective
        this door refuses — the plan's own truth, *"a door that cannot pass a
        perspective refuses rather than silently constructing one"*.

        The refusal is a 503 and not a 403 because the fault is the
        deployment's, not the caller's: ``create_app`` already warns at
        construction and at first request about both configurations that reach
        it (:data:`~ccf_runtime.http_api.app.CcfDeadEntitlementWarning` and the
        D-IMPL-73 insecure-default warning), and the operator reading this code
        is being told which of the two to fix.

        Raises:
            HTTPException: 403 with the typed refusal body when the entitlement
                refused the class or the role; 503 with
                :data:`~ccf_runtime.http_api.errors.ERROR_PRODUCT_DOOR_UNGOVERNED`
                when no authorized perspective can be produced at all.
        """
        if entitlement_source is None or perspective_resolver is None:
            raise HTTPException(
                status_code=503,
                detail=refusal_detail(
                    error_code=ERROR_PRODUCT_DOOR_UNGOVERNED,
                    message=(
                        "this product door has no entitlement seam and no"
                        " perspective resolver bound, so it cannot name the"
                        " Π conditioning a product would be shaped under;"
                        " it refuses rather than serving one conditioned on"
                        " a role nobody granted (D-IMPL-108, DI-15.5-03)."
                        " Supply product_entitlement= and"
                        " perspective_resolver= to create_app()"
                    ),
                ),
            )
        grant = grant_from_request(request)
        if grant is None:
            raise HTTPException(
                status_code=503,
                detail=refusal_detail(
                    error_code=ERROR_PRODUCT_DOOR_UNGOVERNED,
                    message=(
                        "this product door's entitlement seams are bound but"
                        " no verified grant accompanies the call, so there is"
                        " no principal to resolve a perspective for; deciding"
                        " about an unverified claim is worse than not"
                        " deciding, and serving without a perspective is"
                        " worse than both (D-IMPL-108). Bind auth= to"
                        " create_app()"
                    ),
                ),
            )
        try:
            return entitled_perspective(
                grant=grant,
                tenant=tenant,
                product_class=product_class,
                requested_role=role,
                entitlement_source=entitlement_source,
                perspective_resolver=perspective_resolver,
            )
        except ProductEntitlementRefused as refused:
            # The typed constant is the contract and the prose is human
            # context (D-08): the same decision the MCP doors render
            # protocol-natively, rendered here as the one 403 body shape.
            raise HTTPException(
                status_code=403,
                detail=refusal_detail(
                    error_code=refused.error_code, message=refused.message
                ),
            ) from refused

    def _asked(
        *,
        product_class: str,
        version: str,
        subject: str | None,
        intent: str | None,
        freshness: str | None,
        asked_at: datetime | None,
    ) -> ProductRequest | None:
        """The caller's typed question, or the honest absence of one.

        Whitepaper §6.3's four address axes arrive as query parameters and are
        assembled here, at the door, before anything is resolved — which is
        where ``D-IMPL-98``'s request surface was always supposed to be
        validated. ``schema_name`` and ``schema_version`` are taken from the
        **path this door already resolved**, never from the caller, so a
        request addressed to another class cannot be expressed on this surface
        at all.

        Three outcomes, and the middle one is the point:

        * none of the four supplied → ``None``, the positive assertion *this
          caller asked for the class's standing answer and posed no question of
          their own*;
        * some but not all → refused, because a defaulted axis is a question
          nobody asked, answered anyway;
        * all four → the typed request, ``parameters`` empty.

        ``parameters`` is the empty mapping rather than something read off the
        query string: the class-declared remainder is a *typed* surface whose
        declared types (``D-IMPL-103``'s one level of nested objects and
        lists-of-objects) a flat string-valued query cannot carry without the
        door guessing at coercions. An empty mapping is expressible and says
        *this question needs nothing beyond its four axes*, which is a
        statement rather than an omission; a caller needing declared parameters
        reaches the fabric in process or through a deployment's own surface.

        No clock is read here, and that is structural rather than incidental:
        ``asked_at`` is the caller's instant at serve time and the *recorded*
        boundary at replay time, through the same code path, which is the
        entire reason nothing downstream of the request reads one either.

        Raises:
            HTTPException: 400 with
                :data:`~ccf_runtime.http_api.errors.ERROR_PRODUCT_REQUEST_INCOMPLETE`
                when the address is partial.
        """
        supplied = [
            name
            for name, axis in (
                ("subject", subject),
                ("intent", intent),
                ("freshness", freshness),
                ("asked_at", asked_at),
            )
            if axis is not None
        ]
        if not supplied:
            return None
        if (
            subject is None
            or intent is None
            or freshness is None
            or asked_at is None
        ):
            raise HTTPException(
                status_code=400,
                detail=refusal_detail(
                    error_code=ERROR_PRODUCT_REQUEST_INCOMPLETE,
                    message=(
                        "a §6.3 request address is the four axes together:"
                        " subject, intent, freshness and asked_at. This call"
                        f" supplied {supplied}; the door fills none of the"
                        " rest, because a defaulted axis is a question nobody"
                        " asked, answered anyway (D-IMPL-98)"
                    ),
                ),
            )
        return ProductRequest(
            schema_name=product_class,
            schema_version=version,
            subject=subject,
            intent=intent,
            freshness=freshness,
            asked_at=asked_at,
            parameters={},
        )

    return router
