"""Four credentials, ONE standard door — and the same product over HTTP.

The SDK's standard door (`open_door`) mints a one-principal deployment. This
launcher passes its three typed overrides — a token source holding the four
credentials the environment names, a perspective resolver that maps a
verified `client_id` to the role the estate's principal register declares,
and, AFTER the door registered its own one-principal policy, the tenant's
three-grant entitlement policy (the latest registration wins; the ordering
is private SDK knowledge counted under the DX rubric, `CP-SPEC-017` §D.3
step 0). The fourth principal holds a credential and no grant.

AMENDED 2026-10-11 (round 3, SDK round 2 item 1, G4-F-04): the third
override is gone. A deployment can no longer register an entitlement policy
from code (D-IMPL-353), so the tenant's three-grant policy is DECLARED in
`ccf_config.yaml` (`product_entitlement:`) and registered by the SDK's
composition at open; the door composes over it (it registers its own
one-principal default only when nothing is declared). No ordering rule is
involved any more.

The HTTP door is `create_app(auth=)` over the SAME opened product and the
same token source — it exercises the one behavior MCP cannot expose, a
requested role refused rather than downgraded (`MWE-G15`), and is not a
second product path.
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
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer  # noqa: E402
from ccf_runtime.mcp.product_door import ProductDoor, open_door_with_verifier, scope_mapping_key  # noqa: E402
from ccf.products.product import OpenedProduct  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402

import acquisition  # noqa: E402
import deployment  # noqa: E402
import produce  # noqa: E402


def token_source(opened: OpenedProduct) -> StaticTokenSource:
    """The four credentials the environment names, each to its principal."""
    scope = opened.door.required_scope if opened.door is not None else "ccf:egress"
    return StaticTokenSource(grants={
        token: TokenGrant(client_id=principal_id, scopes=(scope,), tenants=frozenset({opened.tenant_id}))
        for token, principal_id in deployment.credential_grants(opened.sources).items()
    })


def perspective_resolver(opened: OpenedProduct) -> Callable[..., Perspective]:
    """`client_id` → role, from `ccf_v2.principal`, read once at open.

    Every principal is mapped — the ungranted one included — so the resolver
    never raises; a requested role (HTTP `?role=`) is proposed as asked and
    the entitlement source refuses it when the grant does not permit it.
    """
    roles: Mapping[str, str] = acquisition.principal_roles(
        relational_settings=opened.sources[deployment.SOURCE_RELATIONAL],
    )

    def resolve(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
        del tenant
        role = requested_role if requested_role is not None else roles.get(grant.client_id, "unmapped")
        return Perspective(principal_id=grant.client_id, role=role)

    return resolve


def open_wall_door(opened: OpenedProduct, *, environ: Mapping[str, str] | None = None) -> ProductDoor:
    """The standard door with its two overrides, over the DECLARED tenant policy (`ccf_config.yaml`)."""
    door = open_door_with_verifier(
        opened,
        environ=environ,
        token_verifier=SourceBackedTokenVerifier(source=token_source(opened)),
        perspective_resolver=perspective_resolver(opened),
    )
    return door


def http_app(opened: OpenedProduct):  # noqa: ANN201 — a FastAPI app; the type lives in the runtime
    """The HTTP door over the same opened product, tokens and recorder."""
    # AMENDED 2026-10-11 (round 3): `create_app` now REQUIRES an authorizer and a
    # replay-record class (D-IMPL-353 §4; SEC-017), and the SDK ships no paved HTTP
    # door. The HTTP door decides under the SAME scope mapping the standard door's
    # composition registers (tenant, `product.retrieve`, this class), pinned to the
    # exact version that composition just returned; a deployment cannot register a
    # mapping of its own. `replay_record_product_class=None` declares no class, which
    # fails closed for a rostered caller's replay reads.
    open_wall_door(opened)
    mapping = scope_mapping_key(tenant_id=opened.tenant_id)
    authorizer = ControlPlaneTenantAuthorizer(
        control_plane=opened.control_plane, scope_mapping_key=mapping,
        scope_mapping_version=opened.control_plane.versions(mapping)[-1],
        clock=lambda: datetime.now(UTC),
    )
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
        authorizer=authorizer,
        product_entitlement=ControlPlaneProductEntitlementSource(
            control_plane=opened.control_plane, clock=lambda: datetime.now(UTC),
        ),
        perspective_resolver=perspective_resolver(opened),
        refusal_recorder=opened.refusal_recorder,
        replay_record_product_class=None,
    )
    return app


def serve() -> None:
    with tempfile.TemporaryDirectory(prefix="cp17-door-") as scratch, produce.product(Path(scratch)) as opened:
        door = open_wall_door(opened)
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
    with tempfile.TemporaryDirectory(prefix="cp17-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_wall_door(opened).serve_loopback(announce=announce)


if __name__ == "__main__":
    serve()
