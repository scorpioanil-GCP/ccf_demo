"""One authorized application, and the credentials to reach it (``SEC-001``).

Every test in this package now talks to an app whose gate is total, so every
test needs a credential and an artifact that authorizes it. Building those in
twenty modules would be twenty chances to build a *permissive* one, so they
are built once here.

**The SDK ships no permissive authorizer, and this file is not one either.**
What it builds is the real
:class:`~ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer` over a real
registered :class:`~ccf_runtime.authz.artifact.ScopeMappingArtifact` at a real
pinned version. The mapping happens to be wide, and **having to write it out
is the point**: the D-01 grammar refuses the bare ``"*"`` (WR-03), so *grant
everything* cannot be typed as one character — :data:`WIDE_RESOURCES` is what
it costs instead, and a reader can see at a glance that this grant is a test
fixture rather than a posture anyone would ship.

Every scope string, tenant name, token and pattern below is test deployment
vocabulary (CINV-01).
"""

from __future__ import annotations

import asyncio
import json
import string
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf_runtime.authz.artifact import (
    SCOPE_MAPPING,
    ScopeEntry,
    ScopeMappingArtifact,
)
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.authz import refusals
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.mcp.auth import TokenGrant, TokenSourceProtocol

#: Test vocabulary.
SCOPE_EVERYTHING = "gate:everything"
SCOPE_NOTHING = "gate:nothing"
TOKEN_EVERYTHING = "gate-token-everything"
TOKEN_NOTHING = "gate-token-nothing"
TOKEN_OTHER_TENANT = "gate-token-other-tenant"
TOKEN_UNTENANTED = "gate-token-untenanted"
CLIENT_ID = "gate-caller"
OTHER_TENANT = "gate-other-tenant"
MAPPING_KEY = "gate/scope-mapping"
ROLE = "gate-role"
AUDIT_INSTANT = datetime(2026, 8, 11, tzinfo=UTC)
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"

#: Every action identifier the SDK's doors declare, read off
#: :mod:`ccf_runtime.authz.refusals` rather than re-typed. A route added with
#: a new action id therefore joins this grant automatically — which is correct
#: for a fixture whose job is *authorized*, and which is exactly why the
#: totality evidence lives in ``test_total_gate.py`` against
#: :data:`TOKEN_NOTHING` instead of here.
ALL_ACTIONS: tuple[str, ...] = tuple(
    getattr(refusals, name) for name in refusals.__all__
)

#: *Everything*, spelled out, because the grammar will not let it be spelled
#: short. One single-character prefix glob per character a test resource can
#: start with: action ids, Control Plane keys, class ids, content addresses,
#: URIs, execution ids, product classes and skill names between them cover the
#: lower- and upper-case alphabet, the digits, and four punctuation marks.
WIDE_RESOURCES: tuple[str, ...] = tuple(
    f"{character}*"
    for character in (
        string.ascii_lowercase + string.ascii_uppercase + string.digits + "._-/"
    )
)


class TenantedTokenGrant(TokenGrant):
    """A :class:`~ccf_runtime.mcp.auth.TokenGrant` that names its tenant.

    ``SEC-002`` requires the tenant to come from the verified credential, and
    :class:`~ccf_runtime.mcp.auth.TokenGrant` does not yet carry one —
    ``runtime/ccf_runtime/mcp/auth.py`` belongs to another lane, so the field
    is owed there rather than added here. This subclass is what the shape looks
    like, and what these tests verify the whole path against: it satisfies
    :class:`~ccf_runtime.authz.tenancy.TenantedGrant`, and ``isinstance``
    against ``TokenGrant`` still holds, so every composition that narrows on
    the base type is unaffected.
    """

    tenant: str


@dataclass(frozen=True)
class _Tokens:
    """A token source over an in-memory table of tenanted grants."""

    grants: dict[str, TokenGrant]

    def grant_for(self, *, token: str) -> TokenGrant | None:
        return self.grants.get(token)


@dataclass(frozen=True)
class GateApp:
    """A built, fully-authorized application plus what a test needs to probe it.

    Attributes:
        app: The application.
        tenant: The tenant every credential here acts for.
        token_everything: A credential the scope mapping authorizes broadly.
        token_nothing: A recognised credential the mapping authorizes for
            **nothing** — the deny-side control, and the one the totality
            evidence is taken against.
        token_other_tenant: A credential for a different tenant, for the
            path-segment-versus-grant assertions.
        token_untenanted: A recognised credential carrying no tenant at all.
        mapping_version: The exact version the authorizer is pinned to.
        registry: The Control Plane the mapping is registered in.
        recorder: The one minting seam, for tests that read records back.
    """

    app: Any
    tenant: str
    token_everything: str
    token_nothing: str
    token_other_tenant: str
    token_untenanted: str
    mapping_version: str
    registry: ControlPlaneRegistry
    recorder: ReplayRefusalRecorder

    def auth(self, token: str | None = None) -> dict[str, str]:
        """An ``Authorization`` header for ``token`` (default: everything)."""
        return {"Authorization": f"Bearer {token or self.token_everything}"}


def build_gate_app(fabric: Any, root: Path) -> GateApp:
    """Build one authorized app over ``fabric``.

    Args:
        fabric: The shared :class:`~http_api.conftest.Fabric`.
        root: A writable directory for the recorder's artifact store.

    Returns:
        The built application and its credentials.
    """
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.dependencies import ApiDependencies

    tenant = str(fabric.product_address.tenant)
    tokens = _Tokens(
        grants={
            TOKEN_EVERYTHING: TenantedTokenGrant(
                client_id=CLIENT_ID,
                scopes=(SCOPE_EVERYTHING,),
                tenant=tenant,
            ),
            TOKEN_NOTHING: TenantedTokenGrant(
                client_id=CLIENT_ID, scopes=(SCOPE_NOTHING,), tenant=tenant
            ),
            TOKEN_OTHER_TENANT: TenantedTokenGrant(
                client_id=CLIENT_ID,
                scopes=(SCOPE_EVERYTHING,),
                tenant=OTHER_TENANT,
            ),
            # Deliberately the BASE type: what a token source that has not
            # been taught about tenancy mints today.
            TOKEN_UNTENANTED: TokenGrant(
                client_id=CLIENT_ID, scopes=(SCOPE_EVERYTHING,)
            ),
        }
    )
    source: TokenSourceProtocol = tokens

    # The scope mapping goes in its OWN registry, not the fabric's: the
    # authorizer pins one version, and a module-scoped fabric other tests
    # register into must not be able to shift what is at that key.
    registry = ControlPlaneRegistry()
    mapping_version = registry.register_typed(
        MAPPING_KEY,
        ScopeMappingArtifact(
            semver="1.0.0",
            scopes={
                SCOPE_EVERYTHING: ScopeEntry(
                    tenant_patterns=(tenant, OTHER_TENANT),
                    action_ids=ALL_ACTIONS,
                    resource_patterns=WIDE_RESOURCES,
                ),
                # Present and empty rather than absent: a mapping with no
                # entry at all would also deny, and the two must be different
                # test setups or the deny evidence proves the wrong thing.
                SCOPE_NOTHING: ScopeEntry(
                    tenant_patterns=(tenant,),
                    action_ids=(),
                    resource_patterns=WIDE_RESOURCES,
                ),
            },
        ),
        SCOPE_MAPPING,
    )
    assert isinstance(mapping_version, str)
    authorizer = ControlPlaneTenantAuthorizer(
        control_plane=registry,
        scope_mapping_key=MAPPING_KEY,
        scope_mapping_version=mapping_version,
        clock=lambda: AUDIT_INSTANT,
    )

    address = fabric.product_address
    entitlements = ControlPlaneRegistry()
    entitlements.register_typed(
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version="1.0.0",
            principals={
                CLIENT_ID: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({address.product_class}),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    entitlement_source = ControlPlaneProductEntitlementSource(
        control_plane=entitlements, clock=lambda: AUDIT_INSTANT
    )
    recorder = ReplayRefusalRecorder(
        artifact_store=FileArtifactStore(root=root / "gate-artifacts"),
        replay_record_class=REPLAY_RECORD_CLASS,
        tenant_id=address.tenant,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
        disclosure_level_for=entitlement_source.disclosure_level_for,
    )

    def perspective_resolver(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        return Perspective(
            principal_id=grant.client_id,
            role=requested_role if requested_role is not None else ROLE,
        )

    app = create_app(
        ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=fabric.hitl,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
        ),
        auth=BearerTokenAuth(token_source=source),
        authorizer=authorizer,
        product_entitlement=entitlement_source,
        perspective_resolver=perspective_resolver,
        refusal_recorder=recorder,
    )
    return GateApp(
        app=app,
        tenant=tenant,
        token_everything=TOKEN_EVERYTHING,
        token_nothing=TOKEN_NOTHING,
        token_other_tenant=TOKEN_OTHER_TENANT,
        token_untenanted=TOKEN_UNTENANTED,
        mapping_version=mapping_version,
        registry=registry,
        recorder=recorder,
    )


def probe(app: Any, method: str, url: str, **kwargs: Any) -> httpx.Response:
    """One in-process request that adds **nothing** of its own.

    Distinct from ``conftest.call``, which supplies a credential so that
    route-level tests stay about routes. Evidence about the gate has to be
    taken with a probe that adds no header, or the evidence is about the
    helper.
    """

    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://fabric.invalid"
        ) as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(go())


def token_file(path: Path, grants: dict[str, dict[str, Any]]) -> Path:
    """Write a dev token file, for the tests that exercise that source."""
    path.write_text(json.dumps(grants), encoding="utf-8")
    return path


def tenanted_source(
    grants: dict[str, tuple[Any, ...]], *, tenant: str
) -> TokenSourceProtocol:
    """A token source minting :class:`TenantedTokenGrant` for each token.

    ``{token: (client_id, scopes)}``, or ``(client_id, scopes, tenant)`` where
    a suite needs several tenants — which it does whenever its tests keep each
    other apart by tenant, since ``tenant := grant.tenant`` means one
    credential names exactly one. ``tenant`` is the default for the two-member
    form.

    The dev :class:`~ccf_runtime.mcp.auth.FileTokenSource` still mints the
    base ``TokenGrant``, which every door now refuses for carrying no tenant,
    so every suite that used a token file reaches for this instead until that
    source is taught about tenancy in its own tree.
    """
    table = {
        token: TenantedTokenGrant(
            client_id=entry[0],
            scopes=tuple(entry[1]),
            tenant=entry[2] if len(entry) > 2 else tenant,
        )
        for token, entry in grants.items()
    }
    return _Tokens(grants=dict(table))


def wide_authorizer(
    *,
    tenant: str | Sequence[str],
    key: str,
    clock_at: datetime = AUDIT_INSTANT,
) -> ControlPlaneTenantAuthorizer:
    """The real authorizer over a mapping registered wide for ``tenant``.

    For suites whose subject is something **other** than the gate — the
    product door's entitlement decision, the refusal-status table, the route
    shapes. They still need an authorizer because every app does, and building
    one here keeps them from each inventing a permissive stand-in.

    Wide, and visibly so: :data:`WIDE_RESOURCES` is what the D-01 grammar
    costs for *everything*, since the bare ``"*"`` is refused (WR-03).
    """
    registry = ControlPlaneRegistry()
    version = registry.register_typed(
        key,
        ScopeMappingArtifact(
            semver="1.0.0",
            scopes={
                SCOPE_EVERYTHING: ScopeEntry(
                    tenant_patterns=(
                        (tenant,) if isinstance(tenant, str) else tuple(tenant)
                    ),
                    action_ids=ALL_ACTIONS,
                    resource_patterns=WIDE_RESOURCES,
                )
            },
        ),
        SCOPE_MAPPING,
    )
    assert isinstance(version, str)
    return ControlPlaneTenantAuthorizer(
        control_plane=registry,
        scope_mapping_key=key,
        scope_mapping_version=version,
        clock=lambda: clock_at,
    )


def authority(
    *,
    tenant: str | Sequence[str],
    key: str,
    grants: dict[str, tuple[Any, ...]],
    product_entitlement: Any,
    perspective_resolver: Any,
    refusal_recorder: Any,
    clock_at: datetime = AUDIT_INSTANT,
) -> dict[str, Any]:
    """Every argument ``create_app`` now requires, as one keyword bundle.

    For the suites whose subject is something other than the gate: the
    evidence dereference, the HITL identity derivation, the signed-binding
    door. Each still has to bind five seams, and building them separately in
    each file is five chances to build a permissive one.

    Splat it and override what the suite is actually about::

        create_app(deps, **authority(..., product_entitlement=my_source, ...))
    """
    return {
        "auth": BearerTokenAuth(
            token_source=tenanted_source(
                grants,
                tenant=tenant if isinstance(tenant, str) else tenant[0],
            )
        ),
        "authorizer": wide_authorizer(
            tenant=tenant, key=key, clock_at=clock_at
        ),
        "product_entitlement": product_entitlement,
        "perspective_resolver": perspective_resolver,
        "refusal_recorder": refusal_recorder,
    }
