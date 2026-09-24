"""Four credentials, ONE standard door — and the same product over HTTP.

The SDK's standard door (`open_door`) mints a one-principal deployment. This
launcher passes its three typed overrides — a token source holding the four
credentials the environment names, a perspective resolver that maps a verified
`client_id` to its declared perspective, and, AFTER the door registered its
own one-principal policy, the tenant's three-grant entitlement policy (the
latest registration wins; the ordering is private SDK knowledge counted under
the DX rubric). The fourth principal holds a credential and no grant.

WHERE THE PERSPECTIVE MAPPING COMES FROM, and why it differs from CP-17's.
CP-17 reads `client_id → role` out of the estate's `principal` register. The
estate holds no AML principal (`CP-SPEC-019` §C.2 trap 3, §F.2 `TBC-1`), and
`ccf_v2.aml_projection_plan` is keyed by perspective with no principal column,
so the credential → perspective half of the mapping is this deployment's and
is named in `ccf_environment.yaml`. The perspective → plan half is the
estate's and is read from it. No estate row is invented.

The HTTP door is `create_app(auth=)` over the SAME opened product and the same
token source — it exercises the one behavior MCP cannot expose, a requested
perspective refused rather than downgraded, and is not a second product path.
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
from ccf_runtime.mcp.product_door import ProductDoor, open_door  # noqa: E402
from ccf.products.entitlement import (  # noqa: E402
    PRODUCT_ENTITLEMENT_POLICY, ProductEntitlementGrant, ProductEntitlementPolicy, product_entitlement_key,
)
from ccf.products.product import OpenedProduct  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402

import acquisition  # noqa: E402
import deployment  # noqa: E402
import produce  # noqa: E402

#: The credential → perspective mapping this DEPLOYMENT declares, because the
#: estate holds none (`TBC-1`). Derived from the credential ids the
#: environment names, so adding a credential is a document edit, not a code
#: edit; the ungranted fourth maps to a perspective no plan exists for, which
#: is what makes it the negative control.
PERSPECTIVE_BY_PRINCIPAL: Mapping[str, str] = {
    "PRIN-AML-L1": "l1",
    "PRIN-AML-L2": "l2",
    "PRIN-AML-EXAM": "examiner",
    "PRIN-AML-XXX": "unmapped",
}


def token_source(opened: OpenedProduct) -> StaticTokenSource:
    """The four credentials the environment names, each to its principal."""
    scope = opened.door.required_scope if opened.door is not None else "ccf:egress"
    return StaticTokenSource(grants={
        token: TokenGrant(
            client_id=principal_id,
            scopes=(scope,),
            # This door serves ONE tenant, so every credential it recognises is
            # scoped to exactly that tenant (`SEC-018`). A grant with no tenant
            # reaches nothing, which is what makes forgetting this loud.
            tenants=frozenset({opened.tenant_id}),
        )
        for token, principal_id in deployment.credential_grants(opened.sources).items()
    })


def perspective_resolver(opened: OpenedProduct) -> Callable[..., Perspective]:
    """`client_id` → perspective, from this deployment's declared mapping.

    Every principal is mapped — the ungranted one included — so the resolver
    never raises; a requested perspective (HTTP `?role=`) is proposed as asked
    and the entitlement source refuses it when the grant does not permit it.
    """
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
    """Register the tenant's three-grant policy — AFTER the door registered its own.

    The grantable set is the principals whose declared perspective the ESTATE
    holds a projection plan for: the mapping is this deployment's, the plans
    are the estate's, and a principal mapped to a perspective with no plan is
    granted nothing.
    """
    planned = set(acquisition.planned_perspectives(
        relational_settings=opened.sources[deployment.SOURCE_RELATIONAL],
    ))
    grantable = {
        principal_id: perspective
        for principal_id, perspective in PERSPECTIVE_BY_PRINCIPAL.items()
        if perspective in planned
    }
    opened.control_plane.register_typed(
        product_entitlement_key(tenant_id=opened.tenant_id),
        ProductEntitlementPolicy(
            tenant_id=opened.tenant_id,
            policy_version=opened.declaration.schema_version,
            principals={
                principal_id: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({opened.declaration.schema_name}),
                    permitted_roles=frozenset({perspective}),
                )
                for principal_id, perspective in grantable.items()
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )


def open_aml_door(opened: OpenedProduct, *, environ: Mapping[str, str] | None = None) -> ProductDoor:
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
    with tempfile.TemporaryDirectory(prefix="cp19-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_aml_door(opened).serve_stdio()


def loopback(*, announce: Callable[[int], None]) -> None:
    with tempfile.TemporaryDirectory(prefix="cp19-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_aml_door(opened).serve_loopback(announce=announce)


if __name__ == "__main__":
    serve()
