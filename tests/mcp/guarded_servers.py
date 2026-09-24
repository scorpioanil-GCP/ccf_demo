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

Tenant, principal, class, scope and token names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime
from typing import Any

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from ccf_runtime.mcp.auth import (
    SourceBackedTokenVerifier,
    StaticTokenSource,
    TokenGrant,
)

TENANT = "tenant-guard-own"
PRINCIPAL = "principal-guard"
SCOPE = "ccf:tenant-guard"
PRODUCT_CLASS = "class-guard"


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


def _entitlement_world(tmp_path: pathlib.Path) -> tuple[Any, Any]:
    """An entitlement source and a refusal recorder over a scratch store."""
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.products.entitlement import (
        PRODUCT_ENTITLEMENT_POLICY,
        ProductEntitlementGrant,
        ProductEntitlementPolicy,
        product_entitlement_key,
    )
    from ccf.products.resolver import ReplayRefusalRecorder
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )

    registry = ControlPlaneRegistry()
    registry.register_typed(
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
        control_plane=registry, clock=lambda: datetime(2026, 5, 12, tzinfo=UTC)
    )
    recorder = ReplayRefusalRecorder(
        artifact_store=FileArtifactStore(root=tmp_path / "replay"),
        replay_record_class="ccf.decision-replay-record",
        tenant_id=TENANT,
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
        from ccf.artifacts.file_store import FileArtifactStore
        from ccf_runtime.mcp.artifact_server import build_artifact_server

        return build_artifact_server(
            server_name="guard-artifact",
            store=FileArtifactStore(root=tmp_path / "artifacts"),
            token_verifier=_verifier(),
            auth_settings=_auth(),
        )

    if builder == "hitl":
        from ccf_runtime.mcp.hitl_server import build_hitl_server

        return build_hitl_server(
            server_name="guard-hitl",
            queue_view=lambda *, tenant: (),
            action_route=lambda *, submission: "{}",
            token_verifier=_verifier(),
            auth_settings=_auth(),
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
            entitlement_source=source,
            perspective_resolver=_perspective,
            refusal_recorder=recorder,
            # Every surface on, so none can hide from the roster.
            expose_product_resource=True,
            expose_product_tool=True,
            product_tool_description="guard fixture",
        )

    raise AssertionError(f"unknown builder {builder!r}")
