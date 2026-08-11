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

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from starlette.requests import Request

from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementRefused,
    ProductEntitlementSourceProtocol,
    entitled_perspective,
)
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import refusal_detail
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
    ) -> Response:
        _enforce_entitlement(
            request, tenant=tenant, product_class=product_class, role=role
        )
        try:
            servable = deps.product_resolver(
                tenant=tenant, product_class=product_class, version=version
            )
        except ProductNotServable as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        return canonical_response(servable.product)

    def _enforce_entitlement(
        request: Request, *, tenant: str, product_class: str, role: str | None
    ) -> None:
        """Ask the bound seams before the resolver is reached.

        Inert when the seams are unbound, and inert when no verified grant
        exists (auth unbound — the D-06 posture ``hitl.py`` already holds):
        with no verified identity there is no principal to decide about, and
        deciding about an unverified claim is worse than not deciding.
        ``create_app`` is what warns about that configuration rather than
        this handler, because the caller is who can fix it.
        """
        if entitlement_source is None or perspective_resolver is None:
            return
        grant = grant_from_request(request)
        if grant is None:
            return
        try:
            entitled_perspective(
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

    return router
