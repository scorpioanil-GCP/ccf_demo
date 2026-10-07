"""Four credentials, ONE standard door — and the same product over HTTP.

The SDK's standard door (`open_door`) mints a one-principal deployment. This
launcher passes its three typed overrides — a token source holding the four
credentials the environment names, a perspective resolver that maps a verified
`client_id` to its declared role, and, AFTER the door registered its own
one-principal policy, the tenant's three-grant entitlement policy (the latest
registration wins). The fourth principal holds a credential and no grant.

WHERE THE ROLE NAMES COME FROM, AND WHY THEY ARE THIS DEPLOYMENT'S HERE. Rung
23 took its role names from `ccf_v2.banker.role`, because the estate said them.
This estate says nothing about who asks a large-exposure question: there is no
register of credit officers, credit committees or supervisors anywhere in it.
So the three renderings — `credit-officer`, `committee`, `examiner` — are
DECLARED by this deployment in `artifacts/perspectives.yaml`, and the fact that
they are declared rather than read is stated rather than disguised.

THE DOOR IS THE SETTLED MECHANISM, WIRED UNCHANGED (`CP-SPEC-021` §0.1).
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

import deployment  # noqa: E402
import produce  # noqa: E402
import projection  # noqa: E402

#: `PRIN-UNG-004` holds a recognized credential and is granted nothing at the
#: door: the negative control.
UNGRANTED = "PRIN-UNG-004"


def perspective_by_principal() -> Mapping[str, str]:
    """`principal_id` -> role, from the DECLARED artifact.

    The role NAMES are the estate's; the principal ids are this deployment's.
    """
    return {principal_id: role for role, principal_id in projection.PRINCIPAL_ID.items()}


def token_source(opened: OpenedProduct) -> StaticTokenSource:
    """The four credentials the environment names, each to its principal."""
    scope = opened.door.required_scope if opened.door is not None else "ccf:egress"
    return StaticTokenSource(grants={
        token: TokenGrant(client_id=principal_id, scopes=(scope,))
        for token, principal_id in deployment.credential_grants(opened.sources).items()
    })


def perspective_resolver(opened: OpenedProduct) -> Callable[..., Perspective]:
    """`client_id` -> role. WHAT THE DETERMINATION SHOWS follows from the role.

    A caller may name a role it holds; it may never name the member or measure
    set that role implies. That is resolved at the acquisition seam, which is
    what makes it an envelope input rather than a request parameter.
    """
    del opened
    mapping = perspective_by_principal()

    def resolve(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
        del tenant
        role = (
            requested_role
            if requested_role is not None
            else mapping.get(grant.client_id, "unmapped")
        )
        return Perspective(principal_id=grant.client_id, role=role)

    return resolve


def entitle(opened: OpenedProduct) -> None:
    """Register the tenant's three-grant policy — AFTER the door's own."""
    mapping = perspective_by_principal()
    opened.control_plane.register_typed(
        product_entitlement_key(tenant_id=opened.tenant_id),
        ProductEntitlementPolicy(
            tenant_id=opened.tenant_id,
            policy_version=opened.declaration.schema_version,
            principals={
                principal_id: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({opened.declaration.schema_name}),
                    permitted_roles=frozenset({role}),
                )
                for principal_id, role in mapping.items()
                if principal_id != UNGRANTED
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )


def open_large_exposure_door(
    opened: OpenedProduct, *, environ: Mapping[str, str] | None = None,
) -> ProductDoor:
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
            erasure_trust=opened.erasure_trust,
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
    with tempfile.TemporaryDirectory(prefix="cp21-door-") as scratch, produce.product(Path(scratch)) as opened:
        door = open_large_exposure_door(opened)
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
    with tempfile.TemporaryDirectory(prefix="cp21-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_large_exposure_door(opened).serve_loopback(announce=announce)


if __name__ == "__main__":
    serve()
