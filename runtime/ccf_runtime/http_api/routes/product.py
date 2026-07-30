"""The ``product`` noun — retrieval only (D-IMPL-23; whitepaper §8.3 P3).

Read-only by construction: the router registers GET and nothing else, and
the seam it holds is the egress resolver
(:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol`) — the same
already-servable-product seam the MCP front door holds, trading only in
gate-admitted :class:`~ccf.products.gates.ServableProduct`s. No write door
can exist here because no handle here could hold one (T-07-23).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.routes import canonical_response
from ccf_runtime.mcp.egress import ProductNotServable

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]


def build_router(deps: ApiDependencies) -> APIRouter:
    """The product router over the injected resolver seam."""
    router = APIRouter()

    @router.get(
        "/{tenant}/{product_class}/{version}",
        summary="Product retrieval (D-IMPL-23)",
    )
    def retrieve(tenant: str, product_class: str, version: str) -> Response:
        try:
            servable = deps.product_resolver(
                tenant=tenant, product_class=product_class, version=version
            )
        except ProductNotServable as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        return canonical_response(servable.product)

    return router
