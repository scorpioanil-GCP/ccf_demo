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

**Every credential here is a real** :class:`~ccf_runtime.mcp.auth.TokenGrant`
**minted through a real token source** (D-IMPL-353 §2 P1). This file used to
define ``TenantedTokenGrant``, a subclass carrying a ``tenant`` scalar that no
token source in the SDK ever minted, and the doors read that scalar — so the
whole suite stayed green while the HTTP door refused every credential a
deployment could actually issue. The subclass is deleted, not deprecated. What
a fixture can mint is exactly what
:class:`~ccf_runtime.mcp.auth.StaticTokenSource` and
:class:`~ccf_runtime.mcp.auth.FileTokenSource` mint: the base contract, with
its ``tenants`` set. **A fixture must not be able to pass where a deployment
fails.**

Every scope string, tenant name, token and pattern below is test deployment
vocabulary (CINV-01).
"""

from __future__ import annotations

import asyncio
import json
import string
from tests.composition import declared_erasure_trust, no_erasures
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

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
from ccf.hitl.principal import AuthenticationClaims
from ccf_runtime.mcp.auth import StaticTokenSource, TokenGrant, TokenSourceProtocol
from http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)

#: Test vocabulary.
SCOPE_EVERYTHING = "gate:everything"
SCOPE_NOTHING = "gate:nothing"
TOKEN_EVERYTHING = "gate-token-everything"
#: SEC-006 (D-IMPL-366 G1 (a)): the door client that APPROVES is not the one
#: that started the execution — requester ≠ approver is unconditional under a
#: bound approval policy. This token's client id is the banking fixture's
#: credit officer, who is eligible under the fixture's typed policies.
TOKEN_APPROVER = "gate-token-approver"
TOKEN_NOTHING = "gate-token-nothing"
TOKEN_OTHER_TENANT = "gate-token-other-tenant"
TOKEN_UNTENANTED = "gate-token-untenanted"
TOKEN_MULTI_TENANT = "gate-token-multi-tenant"
CLIENT_ID = "gate-caller"
APPROVER_CLIENT_ID = "credit-officer-11"
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


def grant(
    client_id: str, scopes: Iterable[str], tenants: Iterable[str]
) -> TokenGrant:
    """The base contract, with its ``tenants`` set — the only shape minted here.

    ``type(grant(...)) is TokenGrant`` holds by construction, and
    ``tests/http_api/test_capability_gate.py`` pins it: what this file mints
    is what a deployment's token source mints, and nothing else.
    """
    return TokenGrant(
        client_id=client_id,
        scopes=tuple(scopes),
        tenants=frozenset(tenants),
        # What the verifier attests about how this credential authenticated —
        # the HITL doors mint the approver binding from these claims and refuse
        # a credential stating nothing (D-IMPL-353 §2 P6). Test vocabulary.
        authentication=AuthenticationClaims(
            method="bearer-token",
            assurance_level="dev",
            identity_provider_ref="idp://gate-fixtures/dev-token-source",
            session_ref=f"session:{client_id}",
        ),
    )


@dataclass(frozen=True)
class GateApp:
    """A built, fully-authorized application plus what a test needs to probe it.

    Attributes:
        app: The application.
        tenant: The tenant every single-tenant credential here acts for.
        other_tenant: The second tenant the wide mapping names.
        token_everything: A credential the scope mapping authorizes broadly.
        token_nothing: A recognised credential the mapping authorizes for
            **nothing** — the deny-side control, and the one the totality
            evidence is taken against.
        token_other_tenant: A credential for a different tenant, for the
            path-segment-versus-grant assertions.
        token_untenanted: A recognised credential carrying no tenant at all.
        token_multi_tenant: A recognised credential spanning **both** tenants
            — the operator-credential shape ``SEC-018`` argued for, and the
            one the gate refuses to pick a tenant for (D-IMPL-353 §1.3).
        mapping_version: The exact version the authorizer is pinned to.
        registry: The Control Plane the mapping is registered in.
        recorder: The one minting seam, for tests that read records back.
    """

    app: Any
    tenant: str
    other_tenant: str
    token_everything: str
    token_nothing: str
    token_other_tenant: str
    token_untenanted: str
    token_multi_tenant: str
    mapping_version: str
    registry: ControlPlaneRegistry
    recorder: ReplayRefusalRecorder

    def auth(self, token: str | None = None) -> dict[str, str]:
        """An ``Authorization`` header for ``token`` (default: everything)."""
        return {"Authorization": f"Bearer {token or self.token_everything}"}


def build_gate_app(
    fabric: Any,
    root: Path,
    *,
    extra_grants: Mapping[str, TokenGrant] | None = None,
    app_options: Mapping[str, Any] | None = None,
) -> GateApp:
    """Build one authorized app over ``fabric``.

    Args:
        fabric: The shared :class:`~http_api.conftest.Fabric`.
        root: A writable directory for the recorder's artifact store.
        extra_grants: Further tokens the source recognizes, beside the
            standing ones — a test's own credential shape (``SEC-017``'s
            rostered grants), never a replacement for the standing ones.
        app_options: Further keyword arguments for ``create_app``.

    Returns:
        The built application and its credentials.
    """
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.dependencies import ApiDependencies

    tenant = str(fabric.product_address.tenant)
    # The REAL per-boot source over the REAL contract (D-IMPL-353 §2 P1).
    source: TokenSourceProtocol = StaticTokenSource(
        grants={
            TOKEN_EVERYTHING: grant(CLIENT_ID, (SCOPE_EVERYTHING,), (tenant,)),
            TOKEN_APPROVER: grant(APPROVER_CLIENT_ID, (SCOPE_EVERYTHING,), (tenant,)),
            TOKEN_NOTHING: grant(CLIENT_ID, (SCOPE_NOTHING,), (tenant,)),
            TOKEN_OTHER_TENANT: grant(
                CLIENT_ID, (SCOPE_EVERYTHING,), (OTHER_TENANT,)
            ),
            TOKEN_MULTI_TENANT: grant(
                CLIENT_ID, (SCOPE_EVERYTHING,), (tenant, OTHER_TENANT)
            ),
            # Deliberately EMPTY `tenants`: what a token source that was
            # never told a tenant mints — and what every door refuses.
            TOKEN_UNTENANTED: grant(CLIENT_ID, (SCOPE_EVERYTHING,), ()),
            **(extra_grants or {}),
        }
    )

    # The scope mapping goes in its OWN registry, not the fabric's: the
    # authorizer pins one version, and a module-scoped fabric other tests
    # register into must not be able to shift what is at that key.
    registry = ControlPlaneRegistry()
    # Every registration a fixture performs is the composition root's act,
    # minted through the D-IMPL-354 recipe for exactly that key.
    mapping_version = register_typed_at_composition(
        registry,
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
    register_typed_at_composition(
        entitlements,
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
    recorder = refusal_recorder(
        entitlements,
        store=deployment_store(root / "gate-artifacts", REPLAY_RECORD_CLASS),
        tenant=address.tenant,
        replay_record_class=REPLAY_RECORD_CLASS,
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
        ApiDependencies(erasure_index=no_erasures(), erasure_trust=declared_erasure_trust(), 
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=fabric.hitl,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
            # The hitl noun's action route stamps `action_time` from this,
            # never from the body (D-IMPL-353 §2 P6).
            clock=lambda: AUDIT_INSTANT,
        ),
        auth=BearerTokenAuth(token_source=source),
        authorizer=authorizer,
        product_entitlement=entitlement_source,
        perspective_resolver=perspective_resolver,
        refusal_recorder=recorder,
        # `SEC-017`; `D-IMPL-374`: `create_app` requires the declared replay
        # record class, so the fixture states it. `None` — none declared —
        # fails a rostered caller closed on every replay read; the suites
        # that are about the roster supply their own through `app_options`.
        **{"replay_record_product_class": None, **(app_options or {})},
    )
    return GateApp(
        app=app,
        tenant=tenant,
        other_tenant=OTHER_TENANT,
        token_everything=TOKEN_EVERYTHING,
        token_nothing=TOKEN_NOTHING,
        token_other_tenant=TOKEN_OTHER_TENANT,
        token_untenanted=TOKEN_UNTENANTED,
        token_multi_tenant=TOKEN_MULTI_TENANT,
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
    """Write a dev token file, for the tests that exercise that source.

    ``grants`` is the file's own grammar — ``{token: {"client_id", "scopes",
    "tenants"}}`` — exactly what :class:`~ccf_runtime.mcp.auth.FileTokenSource`
    parses. A test that omits ``tenants`` writes a credential that reaches
    nothing, which is the ``SEC-018`` posture and is what such a test is
    usually proving.
    """
    path.write_text(json.dumps(grants), encoding="utf-8")
    return path


def tenanted_source(
    grants: dict[str, tuple[Any, ...]], *, tenant: str
) -> TokenSourceProtocol:
    """A real :class:`~ccf_runtime.mcp.auth.StaticTokenSource` over real grants.

    ``{token: (client_id, scopes)}``, or ``(client_id, scopes, tenants)`` where
    a suite keeps its tests apart by tenant — ``tenants`` being one name or an
    iterable of names. ``tenant`` is the default for the two-member form.

    Nothing here is a subclass and nothing here is a stand-in: the source is
    the SDK's own per-boot source and the grant is the base contract with its
    ``tenants`` set, so a suite built on this helper is built on what a
    deployment can actually mint (D-IMPL-353 §2 P1).
    """
    table: dict[str, TokenGrant] = {}
    for token, entry in grants.items():
        declared = entry[2] if len(entry) > 2 else tenant
        tenants = (declared,) if isinstance(declared, str) else tuple(declared)
        table[token] = grant(entry[0], tuple(entry[1]), tenants)
    return StaticTokenSource(grants=table)


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
    version = register_typed_at_composition(
        registry,
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
    replay_record_product_class: str | None = None,
    clock_at: datetime = AUDIT_INSTANT,
) -> dict[str, Any]:
    """Every argument ``create_app`` now requires, as one keyword bundle.

    For the suites whose subject is something other than the gate: the
    evidence dereference, the HITL identity derivation, the signed-binding
    door. Each still has to bind five seams, and building them separately in
    each file is five chances to build a permissive one. The bundle also
    carries the sixth required key, ``replay_record_product_class``
    (``SEC-017``; ``D-IMPL-374``): ``create_app`` has no default for it, so
    this helper states ``None`` — none declared, a rostered caller refused
    every replay read — unless a suite that is about the roster passes its
    own.

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
        "replay_record_product_class": replay_record_product_class,
    }
