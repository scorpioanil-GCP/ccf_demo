"""Four credentials, ONE standard door — and the same product over HTTP.

The SDK's standard door (`open_door`) mints a one-principal deployment. This
launcher passes its two typed overrides — a token source holding the four
credentials the environment names, and a perspective resolver that maps a
verified `client_id` to its declared perspective. The tenant's three-grant
entitlement policy is DECLARED in `ccf_config.yaml` (`product_entitlement:`)
and registered by the SDK's composition at open; the door composes over it
(2026-10-11 compatibility repair, SDK round 2, G4-F-04 — this launcher used to
register it by hand, which D-IMPL-353 refuses). The fourth principal holds a
credential and no grant.

WHERE THE PERSPECTIVE MAPPING COMES FROM — and this rung is the exception.
`ccf_v2.principal` already carries both halves this product needs: the
`perspective` each principal asks under, and `sees_eu_person_data`, the
residency entitlement. The resolver still reads the perspective from the
estate. AMENDED 2026-10-11: the GRANT (who may ask, under which role) is now
also stated in `ccf_config.yaml`, because a deployment can no longer register
it from estate reads at runtime — so the role is stated twice (estate and
declaration). A role the two disagree on is refused at the door
(`product-role-ungranted`), never silently served; the duplication is recorded
as SDK friction (G4-F-04), not hidden.

THE DOOR IS THE SETTLED MECHANISM, WIRED UNCHANGED (`CP-SPEC-015` §0.1).
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

#: The principal -> perspective mapping is READ FROM THE ESTATE rather than
#: declared here. `ccf_v2.principal.perspective` already names each
#: principal's role and `sees_eu_person_data` already names its residency
#: entitlement, so — unlike rungs 17, 19 and 18 — this deployment invents no
#: mapping at all. Only the credential -> principal half is this deployment's,
#: and it lives in `ccf_environment.yaml`.
#:
#: `PRIN-TRD-003` is registered in the estate and granted nothing at the door
#: (absent from `ccf_config.yaml`'s `product_entitlement:`): the negative control.
UNGRANTED = "PRIN-TRD-003"


def perspective_by_principal(opened: OpenedProduct) -> Mapping[str, str]:
    """`principal_id` -> perspective, from the ESTATE's own register."""
    return acquisition.registered_principals(
        relational_settings=opened.sources[deployment.SOURCE_RELATIONAL],
    )


def token_source(opened: OpenedProduct) -> StaticTokenSource:
    """The four credentials the environment names, each to its principal."""
    scope = opened.door.required_scope if opened.door is not None else "ccf:egress"
    return StaticTokenSource(grants={
        token: TokenGrant(client_id=principal_id, scopes=(scope,), tenants=frozenset({opened.tenant_id}))
        for token, principal_id in deployment.credential_grants(opened.sources).items()
    })


def perspective_resolver(opened: OpenedProduct) -> Callable[..., Perspective]:
    """`client_id` -> perspective, from the ESTATE's own principal register."""
    mapping = perspective_by_principal(opened)

    def resolve(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
        del tenant
        role = (
            requested_role
            if requested_role is not None
            else mapping.get(grant.client_id, "unmapped")
        )
        return Perspective(principal_id=grant.client_id, role=role)

    return resolve


def open_kyc_door(opened: OpenedProduct, *, environ: Mapping[str, str] | None = None) -> ProductDoor:
    """The standard door with its two overrides, over the DECLARED tenant policy."""
    return open_door_with_verifier(
        opened,
        environ=environ,
        token_verifier=SourceBackedTokenVerifier(source=token_source(opened)),
        perspective_resolver=perspective_resolver(opened),
    )


def http_app(opened: OpenedProduct):  # noqa: ANN201 — a FastAPI app; the type lives in the runtime
    """The HTTP door over the same opened product, tokens and recorder."""
    # AMENDED 2026-10-11 (round 3): `create_app` now REQUIRES an authorizer and a
    # replay-record class (D-IMPL-353 §4; SEC-017), and the SDK ships no paved HTTP
    # door. The HTTP door decides under the SAME scope mapping the standard door's
    # composition registers (tenant, `product.retrieve`, this class), pinned to the
    # exact version that composition just returned; a deployment cannot register a
    # mapping of its own. `replay_record_product_class=None` declares no class, which
    # fails closed for a rostered caller's replay reads.
    open_kyc_door(opened)
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
    with tempfile.TemporaryDirectory(prefix="cp15-door-") as scratch, produce.product(Path(scratch)) as opened:
        door = open_kyc_door(opened)
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
    with tempfile.TemporaryDirectory(prefix="cp15-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_kyc_door(opened).serve_loopback(announce=announce)


if __name__ == "__main__":
    serve()
