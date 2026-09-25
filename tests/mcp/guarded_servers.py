"""One built instance of each shipped MCP server, for the guard's roster test.

``tests/mcp/test_tenant_guard.py`` asserts that **every** surface on **every**
shipped server was registered through
:class:`~ccf_runtime.mcp.tenancy.TenantGuardedServer`. That assertion needs the
servers actually built, because the instrument reads ``FastMCP``'s own
registry — a source grep would answer a weaker question and would miss a
registration composed at runtime.

The seams are the thinnest stand-ins that let each builder complete. Nothing
here is exercised for behavior; the behavior tests drive real fixtures. What
matters is that every registration the builder performs actually happens, so
each server is built with its surfaces **maximally exposed** — every allowlist
opened, every optional flag on — since a surface that is not registered cannot
be found unguarded.

**Every builder now takes an authorizer, and this module builds a real one**
(``D-IMPL-353``). The wrapper is the MCP mint site: it asks the deployment's
:class:`~ccf_runtime.authz.protocol.TenantAuthorizerProtocol` before any body
runs and mints an ``Authorized`` from the *allowed* decision. The SDK ships no
permissive authorizer, and neither does this module — :func:`authorizer_granting`
registers a real :class:`~ccf_runtime.authz.artifact.ScopeMappingArtifact` at a
real pinned version and interprets it through the real
:class:`~ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer`. The mapping
is wide, and having to spell it out is the point: the D-01 grammar refuses the
bare ``"*"``, so *everything* costs :data:`WIDE_RESOURCES` and a reader can see
this is a fixture posture rather than a shipped one.

Tenant, principal, class, scope and token names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import pathlib
import string
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.authz import actions
from ccf_runtime.authz.artifact import (
    SCOPE_MAPPING,
    ScopeEntry,
    ScopeMappingArtifact,
)
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.mcp.auth import (
    SourceBackedTokenVerifier,
    StaticTokenSource,
    TokenGrant,
)
from tests.http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)

#: The record class this fixture's recorders file into. Test vocabulary.
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"

TENANT = "tenant-guard-own"
FOREIGN = "tenant-guard-foreign"
PRINCIPAL = "principal-guard"
SCOPE = "ccf:tenant-guard"
PRODUCT_CLASS = "class-guard"
MAPPING_KEY = "guard/scope-mapping"
AUDIT_INSTANT = datetime(2026, 5, 12, tzinfo=UTC)

#: Every action identifier the SDK's doors declare, read off the vocabulary
#: module rather than re-typed, so a door added with a new id joins the grant.
ALL_ACTIONS: tuple[str, ...] = tuple(
    getattr(actions, name) for name in actions.__all__
)

#: *Everything*, spelled out, because the D-01 grammar will not let it be
#: spelled short (WR-03): one single-character prefix glob per character a
#: test resource can begin with.
WIDE_RESOURCES: tuple[str, ...] = tuple(
    f"{character}*"
    for character in (
        string.ascii_lowercase + string.ascii_uppercase + string.digits + "._-/"
    )
)


def _auth() -> AuthSettings:
    return AuthSettings(
        issuer_url=AnyHttpUrl("https://issuer.invalid"),
        resource_server_url=AnyHttpUrl("https://guard.invalid/mcp"),
        required_scopes=[SCOPE],
    )


def _verifier() -> SourceBackedTokenVerifier:
    return SourceBackedTokenVerifier(
        source=StaticTokenSource(
            grants={
                "tok": TokenGrant(
                    client_id=PRINCIPAL,
                    scopes=(SCOPE,),
                    tenants=frozenset({TENANT}),
                )
            }
        )
    )


def authorizer_granting(
    *,
    tenants: Iterable[str] = (TENANT, FOREIGN),
    scopes: Iterable[str] = (SCOPE,),
    actions: Iterable[str] = ALL_ACTIONS,
    resources: Iterable[str] = WIDE_RESOURCES,
    registry: ControlPlaneRegistry | None = None,
) -> ControlPlaneTenantAuthorizer:
    """A real, deny-by-default authorizer whose one mapping grants what is named.

    Wide by default so a roster test exercises every registration; narrowed by
    a test that wants a deny, by naming fewer tenants, actions or resources —
    never by a flag, because there is no flag.

    Args:
        tenants: The tenant patterns each named scope reaches.
        scopes: The scope strings the mapping recognizes.
        actions: The door-declared action ids each scope may perform.
        resources: The resource patterns each scope reaches.
        registry: The Control Plane to register the mapping in; a fresh one
            when omitted, so a test's own registry is never the authorizer's
            unless the test says so.
    """
    control_plane = ControlPlaneRegistry() if registry is None else registry
    entry = ScopeEntry(
        tenant_patterns=tuple(tenants),
        action_ids=tuple(actions),
        resource_patterns=tuple(resources),
    )
    version = register_typed_at_composition(
        control_plane,
        MAPPING_KEY,
        ScopeMappingArtifact(
            semver="1.0.0", scopes={scope: entry for scope in scopes}
        ),
        SCOPE_MAPPING,
    )
    assert isinstance(version, str)
    return ControlPlaneTenantAuthorizer(
        control_plane=control_plane,
        scope_mapping_key=MAPPING_KEY,
        scope_mapping_version=version,
        clock=lambda: AUDIT_INSTANT,
    )


def wide_authorizer(*, scopes: Iterable[str]) -> ControlPlaneTenantAuthorizer:
    """An authorizer that grants ``scopes`` every tenant, action and resource.

    For fixtures whose subject is entitlement, disclosure or the wire shape —
    never authorization: the door must be authorized so the test reaches the
    thing it measures. Spelled out as prefix globs on both axes because the
    grammar refuses ``"*"``; a reader can see at a glance that this is a
    fixture posture and not one anybody would ship. A test about the
    authorizer itself narrows with :func:`authorizer_granting`.
    """
    return authorizer_granting(tenants=WIDE_RESOURCES, scopes=scopes)


def _entitlement_world(tmp_path: pathlib.Path) -> tuple[Any, Any]:
    """An entitlement source and a refusal recorder over a scratch store."""
    from ccf.products.entitlement import (
        PRODUCT_ENTITLEMENT_POLICY,
        ProductEntitlementGrant,
        ProductEntitlementPolicy,
        product_entitlement_key,
    )
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )

    registry = ControlPlaneRegistry()
    register_typed_at_composition(
        registry,
        product_entitlement_key(tenant_id=TENANT),
        ProductEntitlementPolicy(
            tenant_id=TENANT,
            policy_version="1.0.0",
            principals={
                PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({PRODUCT_CLASS}),
                    permitted_roles=frozenset({"role-guard"}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: AUDIT_INSTANT
    )
    recorder = refusal_recorder(
        registry,
        store=deployment_store(tmp_path / "replay", REPLAY_RECORD_CLASS),
        tenant=TENANT,
        replay_record_class=REPLAY_RECORD_CLASS,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
        disclosure_level_for=source.disclosure_level_for,
    )
    return source, recorder


def _perspective(*, grant: Any, tenant: str, requested_role: str | None) -> Any:
    from ccf.projection.plan import Perspective

    return Perspective(principal_id=grant.client_id, role="role-guard")


def build_for(builder: str, tmp_path: pathlib.Path) -> FastMCP:
    """Build one shipped server by name, with every surface exposed."""
    if builder == "artifact":
        from ccf_runtime.mcp.artifact_server import build_artifact_server

        source, recorder = _entitlement_world(tmp_path)
        return build_artifact_server(
            server_name="guard-artifact",
            store=deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS),
            token_verifier=_verifier(),
            auth_settings=_auth(),
            authorizer=authorizer_granting(),
            entitlement_source=source,
            refusal_recorder=recorder,
            audit_log=ControlPlaneRegistry().audit_log,
        )

    if builder == "hitl":
        from ccf_runtime.mcp.hitl_server import build_hitl_server

        return build_hitl_server(
            server_name="guard-hitl",
            queue_view=lambda authorized: (),
            action_route=lambda authorized, *, submission: "{}",
            token_verifier=_verifier(),
            auth_settings=_auth(),
            authorizer=authorizer_granting(),
            # Lane HITL-DOOR's builder takes the door's clock beside the
            # authorizer (D-IMPL-353 §2 P6 — the action time is the door's).
            clock=lambda: AUDIT_INSTANT,
        )

    if builder == "experience":
        from ccf_runtime.mcp.experience import (
            GET_CONTEXT_TOOL,
            GET_LINEAGE_TOOL,
            GET_REPLAY_RECORD_TOOL,
            INVOKE_AGENT_TOOL,
            LIST_AGENTS_TOOL,
            build_experience_server,
        )

        source, recorder = _entitlement_world(tmp_path)
        return build_experience_server(
            server_name="guard-experience",
            product_resolver=lambda **kw: None,
            agent_directory=lambda *, tenant: (),
            agent_invoker=lambda **kw: "{}",
            context_provider=lambda **kw: "{}",
            lineage_provider=lambda: "{}",
            replay_record_reader=lambda: "{}",
            get_context_description="guard fixture",
            get_lineage_description="guard fixture",
            get_replay_record_description="guard fixture",
            list_agents_description="guard fixture",
            invoke_agent_description="guard fixture",
            entitled_product_class=PRODUCT_CLASS,
            lineage_tenant=TENANT,
            replay_record_tenant=TENANT,
            tool_allowlist=frozenset(
                {
                    GET_CONTEXT_TOOL,
                    GET_LINEAGE_TOOL,
                    GET_REPLAY_RECORD_TOOL,
                    INVOKE_AGENT_TOOL,
                    LIST_AGENTS_TOOL,
                }
            ),
            token_verifier=_verifier(),
            auth_settings=_auth(),
            authorizer=authorizer_granting(),
            entitlement_source=source,
            perspective_resolver=_perspective,
            refusal_recorder=recorder,
        )

    if builder == "egress":
        from ccf_runtime.mcp.egress import build_egress_server

        source, recorder = _entitlement_world(tmp_path)
        return build_egress_server(
            server_name="guard-egress",
            resolver=lambda **kw: None,
            token_verifier=_verifier(),
            auth_settings=_auth(),
            authorizer=authorizer_granting(),
            entitlement_source=source,
            perspective_resolver=_perspective,
            refusal_recorder=recorder,
            # Every surface on, so none can hide from the roster.
            expose_product_resource=True,
            expose_product_tool=True,
            product_tool_description="guard fixture",
        )

    raise AssertionError(f"unknown builder {builder!r}")
