"""Four credentials, ONE standard door — and the same product over HTTP.

The SDK's standard door (`open_door`) mints a one-principal deployment. This
launcher passes its three typed overrides — a token source holding the four
credentials the environment names, a perspective resolver that maps a verified
`client_id` to its declared perspective, and, AFTER the door registered its
own one-principal policy, the tenant's three-grant entitlement policy (the
latest registration wins). The fourth principal holds a credential and no
grant.

WHERE THE PERSPECTIVE MAPPING COMES FROM. `ccf_v2.ib_projection_plan` and
`perspective_weight` are keyed by PERSPECTIVE and the estate maps no banker to
one (`CP-SPEC-018` §C.4 trap 3, §F.2 `TBC-1`), so the banker -> perspective
half of the mapping is this deployment's and is named here. The perspective ->
plan and -> weights halves are the estate's and are read from it. No estate
row is invented.

THE DOOR IS THE SETTLED MECHANISM, WIRED UNCHANGED. `CP-SPEC-018` §0.1 puts
the multi-principal door out of scope for redesign: 40 bankers rather than
three or four principals is a count, not a new mechanism.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent.parent
REPO_ROOT = EXAMPLE.parent.parent
for _path in (REPO_ROOT / "src", REPO_ROOT / "runtime", EXAMPLE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource  # noqa: E402
from ccf_runtime.http_api.app import create_app  # noqa: E402
from ccf_runtime.http_api.auth import BearerTokenAuth  # noqa: E402
from ccf_runtime.http_api.dependencies import ApiDependencies  # noqa: E402
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant  # noqa: E402
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser  # noqa: E402
from ccf_runtime.mcp.tenancy import ambient_stdio_identity  # noqa: E402
from ccf_runtime.mcp.product_door import ProductDoor, open_door  # noqa: E402
from ccf.products.entitlement import (  # noqa: E402
    PRODUCT_ENTITLEMENT_POLICY, ProductEntitlementGrant, ProductEntitlementPolicy, product_entitlement_key,
)
from ccf.products.product import OpenedProduct  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402

import acquisition  # noqa: E402
import deployment  # noqa: E402
import produce  # noqa: E402

#: The banker -> perspective mapping this DEPLOYMENT declares, because the
#: estate holds none (`TBC-1`). The ungranted fourth maps to a perspective no
#: plan exists for, which is what makes it the negative control.
PERSPECTIVE_BY_PRINCIPAL: Mapping[str, str] = {
    "BKR014": "ma",
    "BKR006": "dcm",
    "BKR027": "sector",
    "BKR999": "unmapped",
}


def token_source(opened: OpenedProduct) -> StaticTokenSource:
    """The four credentials the environment names, each to its banker."""
    scope = opened.door.required_scope if opened.door is not None else "ccf:egress"
    return StaticTokenSource(grants={
        token: TokenGrant(client_id=banker_id, scopes=(scope,))
        for token, banker_id in deployment.credential_grants(opened.sources).items()
    })


def perspective_resolver(opened: OpenedProduct) -> Callable[..., Perspective]:
    """`client_id` -> perspective, from this deployment's declared mapping."""
    del opened

    def resolve(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
        del tenant
        role = (
            requested_role
            if requested_role is not None
            else PERSPECTIVE_BY_PRINCIPAL.get(grant.client_id, "unmapped")
        )
        return Perspective(principal_id=grant.client_id, role=role)

    return resolve


def entitle(opened: OpenedProduct) -> None:
    """Register the tenant's three-grant policy — AFTER the door's own."""
    planned = set(acquisition.planned_perspectives(
        relational_settings=opened.sources[deployment.SOURCE_RELATIONAL],
    ))
    grantable = {
        banker_id: perspective
        for banker_id, perspective in PERSPECTIVE_BY_PRINCIPAL.items()
        if perspective in planned
    }
    opened.control_plane.register_typed(
        product_entitlement_key(tenant_id=opened.tenant_id),
        ProductEntitlementPolicy(
            tenant_id=opened.tenant_id,
            policy_version=opened.declaration.schema_version,
            principals={
                banker_id: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({opened.declaration.schema_name}),
                    permitted_roles=frozenset({perspective}),
                )
                for banker_id, perspective in grantable.items()
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )


def open_ib_door(opened: OpenedProduct, *, environ: Mapping[str, str] | None = None) -> ProductDoor:
    """The standard door with its three overrides, then the tenant policy."""
    door = open_door(
        opened,
        environ=environ,
        token_verifier=SourceBackedTokenVerifier(source=token_source(opened)),
        perspective_resolver=perspective_resolver(opened),
    )
    entitle(opened)
    return door


def http_app(opened: OpenedProduct):  # noqa: ANN201 — a FastAPI app; the type lives in the runtime
    """The HTTP door over the same opened product, tokens and recorder."""
    app = create_app(
        ApiDependencies(
            control_plane=opened.control_plane,
            artifact_store=opened.artifact_store,
            # SEC-009 (D-IMPL-374 (4), C1): the product's declared durable
            # erasure index — required wherever a store is composed.
            erasure_index=opened.erasure_index,
            product_resolver=opened.resolve,
        ),
        auth=BearerTokenAuth(token_source=token_source(opened)),
        product_entitlement=ControlPlaneProductEntitlementSource(
            control_plane=opened.control_plane, clock=lambda: datetime.now(UTC),
        ),
        perspective_resolver=perspective_resolver(opened),
        refusal_recorder=opened.refusal_recorder,
    )
    entitle(opened)
    return app


def serve() -> None:
    with tempfile.TemporaryDirectory(prefix="cp18-door-") as scratch, produce.product(Path(scratch)) as opened:
        door = open_ib_door(opened)
        door.serve_stdio(
            identity=AuthenticatedUser(
                ambient_stdio_identity(
                    credential=door.credential,
                    principal_id=door.principal_id,
                    scope=door.scope,
                    tenant=door.tenant_id,
                )
            )
        )


def loopback(*, announce: Callable[[int], None]) -> None:
    with tempfile.TemporaryDirectory(prefix="cp18-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_ib_door(opened).serve_loopback(announce=announce)


if __name__ == "__main__":
    serve()
