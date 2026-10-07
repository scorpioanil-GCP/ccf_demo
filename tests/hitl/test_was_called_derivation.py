"""R1 was-called derivation assertions, under the door-minted binding (08-03 Task 3; D-IMPL-353 §2 P6).

The R1 finding (Cursor, LOW): the happy path proved *subject equality*, not
the derivation call — a regression that passed the caller's body principal
through would still have passed every prior test. Under P6 there is no body
principal to pass through, so the assertion sharpens: the binding that lands
IS the object :func:`~ccf_runtime.identity_binding.principal_from_authorized`
returned (identity, not equality), it was called exactly once, and it was
called with the capability's principal, the verified credential's claims and
the injected clock — never with anything from the request.

The negative guards, restated for the posture that replaced the one they
were written against (``SEC-002``): a credential-less request is refused by
the total gate before any handler runs, and a recognised credential naming
no tenant is refused before the derivation — so the derivation is never fed
anything unverified, and nothing lands on the transport.
"""

from __future__ import annotations

import json
from tests.composition import declared_hitl_policy_key, no_erasures
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.hitl.principal import AUTHENTICATION_CLAIM, AuthenticationClaims
from ccf_runtime.http_api.errors import (
    ERROR_UNAUTHENTICATED,
    ERROR_UNTENANTED_GRANT,
)
from ccf_runtime.mcp.auth import StaticTokenSource, TokenGrant

from http_api.conftest import Fabric, call
from http_api.composition_authority import refusal_recorder
from http_api.gate_fixtures import SCOPE_EVERYTHING
from tests.controlplane.composition import compose_register_typed

_VALID_HASH = "c" * 64
_CLOCK_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
_TOKEN = "derivation-token"
_MCP_TENANT = "was-called-mcp-tenant"
_HTTP_TENANT = "was-called-auth-tenant"
_CLIENT_ID = "derivation-auditor-1"
_ROLE = "was-called-role"
_MAPPING_KEY = "was-called/scope-mapping"
_CLAIMS = AuthenticationClaims(
    identity_provider_ref="idp://acme-bank/dev-token-file",
    method="bearer-token",
    assurance_level="dev",
    session_ref="derivation-session-1",
)


def _body(**extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "event_key": "derivation-event-1",
        "action": "approve",
        "product_content_hash": _VALID_HASH,
        "annotation": None,
    }
    body.update(extra)
    return body


@pytest.fixture(scope="module")
def fabric(tmp_path_factory: pytest.TempPathFactory) -> Fabric:
    return Fabric(tmp_path_factory.mktemp("was-called"))


def _grant() -> TokenGrant:
    return TokenGrant(
        client_id=_CLIENT_ID,
        scopes=(SCOPE_EVERYTHING,),
        tenants=frozenset({_HTTP_TENANT}),
        authentication=_CLAIMS,
    )


def _seams(fabric: Fabric, root: Path) -> dict[str, Any]:
    """Everything ``create_app`` requires, with this suite's credentials."""
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.artifacts.protocol import WriteKinds
    from ccf.authz.capability import ReplayMint
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.products.entitlement import (
        PRODUCT_ENTITLEMENT_POLICY,
        ProductEntitlementGrant,
        ProductEntitlementPolicy,
        product_entitlement_key,
    )
    from ccf.projection.plan import Perspective
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )
    from ccf_runtime.http_api.auth import BearerTokenAuth

    from http_api.gate_fixtures import authority

    address = fabric.product_address
    entitlements = ControlPlaneRegistry()
    compose_register_typed(entitlements,
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version="1.0.0",
            principals={
                _CLIENT_ID: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({address.product_class}),
                    permitted_roles=frozenset({_ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(
        control_plane=entitlements, clock=lambda: _CLOCK_TIME
    )
    seams = authority(
        tenant=(_HTTP_TENANT, address.tenant),
        key=_MAPPING_KEY,
        grants={"unused": (_CLIENT_ID, (SCOPE_EVERYTHING,), _HTTP_TENANT)},
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=_ROLE
            )
        ),
        # The recorder holds the ReplayMint its composition root minted for its
        # class (D-IMPL-354): the recipe, spelled once in `composition_authority`.
        refusal_recorder=refusal_recorder(
            entitlements,
            store=FileArtifactStore(
                root=root / "artifacts",
                # The recorder is fabric mechanism writing its own evidence
                # class (D-IMPL-353 §1.2): declared, so it admits the
                # ReplayMint the composition root hands the writer.
                write_kinds=WriteKinds.declare(
                    {"ccf.decision-replay-record": (ReplayMint,)}
                ),
            ),
            tenant=address.tenant,
            replay_record_class="ccf.decision-replay-record",
            assembly_mode="algorithmic",
            policy_bundle_pin=None,
            disclosure_level_for=source.disclosure_level_for,
        ),
    )
    seams["auth"] = BearerTokenAuth(
        token_source=StaticTokenSource(grants={_TOKEN: _grant()})
    )
    return seams


def _deps(fabric: Fabric) -> Any:
    from ccf_runtime.http_api.dependencies import ApiDependencies

    return ApiDependencies(erasure_index=no_erasures(), hitl_policy_key=declared_hitl_policy_key(), 
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
        workflow_factory=fabric.factory,
        workflow_engine=fabric.engine,
        hitl_transport=fabric.hitl,
        skill_catalog=fabric.catalog,
        grant_ledger=fabric.ledger,
        clock=lambda: _CLOCK_TIME,
    )


class _WrapCounter:
    """Wrap-and-count spy: the real derivation still runs (R1 discipline)."""

    def __init__(self, real: Any) -> None:
        self._real = real
        self.call_count = 0
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.returns: list[Any] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.call_count += 1
        self.calls.append((args, kwargs))
        result = self._real(*args, **kwargs)
        self.returns.append(result)
        return result


# --- Test 1: the HTTP door actually mints, from the verified inputs ---------


def test_http_door_invokes_the_mint_with_capability_claims_and_clock(
    fabric: Fabric, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ccf_runtime.http_api.routes.hitl as hitl_routes
    from ccf_runtime.http_api.app import create_app

    spy = _WrapCounter(hitl_routes.principal_from_authorized)
    monkeypatch.setattr(hitl_routes, "principal_from_authorized", spy)
    app = create_app(_deps(fabric), **_seams(fabric, tmp_path))
    response = call(
        app,
        "POST",
        "/hitl/actions",
        json=_body(),
        headers={"Authorization": f"Bearer {_TOKEN}"},
    )
    assert response.status_code == 200, response.text
    assert spy.call_count == 1
    (args, kwargs) = spy.calls[0]
    # The subject came from the capability, the claims from the credential,
    # the time from the clock — none from the request.
    assert args[0].principal == _CLIENT_ID
    assert args[0].tenant == _HTTP_TENANT
    assert kwargs["authentication"] == _CLAIMS
    assert kwargs["action_time"] == _CLOCK_TIME
    assert kwargs["product_content_hash"] == _VALID_HASH
    # The recorded principal IS the mint's return value — identity.
    (recorded,) = fabric.hitl.submissions(tenant=_HTTP_TENANT)
    assert recorded.principal is spy.returns[0]


# --- Test 2: no credential never reaches the mint ---------------------------


def test_a_credentialless_request_never_reaches_the_mint(
    fabric: Fabric, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ccf_runtime.http_api.routes.hitl as hitl_routes
    from ccf_runtime.http_api.app import create_app

    from http_api.gate_fixtures import probe

    spy = _WrapCounter(hitl_routes.principal_from_authorized)
    monkeypatch.setattr(hitl_routes, "principal_from_authorized", spy)
    app = create_app(_deps(fabric), **_seams(fabric, tmp_path))
    tenant = "was-called-unauth-tenant"
    response = probe(app, "POST", "/hitl/actions", json=_body())
    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == ERROR_UNAUTHENTICATED
    assert spy.call_count == 0
    assert fabric.hitl.submissions(tenant=tenant) == ()


def test_an_untenanted_grant_is_refused_before_the_mint(
    fabric: Fabric, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ccf_runtime.http_api.routes.hitl as hitl_routes
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.auth import BearerTokenAuth
    from ccf_runtime.mcp.auth import FileTokenSource

    from http_api.gate_fixtures import probe

    spy = _WrapCounter(hitl_routes.principal_from_authorized)
    monkeypatch.setattr(hitl_routes, "principal_from_authorized", spy)
    path = tmp_path / "dev-tokens.json"
    path.write_text(
        json.dumps({_TOKEN: {"client_id": _CLIENT_ID, "scopes": [SCOPE_EVERYTHING]}}),
        encoding="utf-8",
    )
    seams = _seams(fabric, tmp_path)
    seams["auth"] = BearerTokenAuth(token_source=FileTokenSource(path=path))
    app = create_app(_deps(fabric), **seams)
    tenant = "was-called-untenanted-tenant"
    response = probe(
        app,
        "POST",
        "/hitl/actions",
        json=_body(),
        headers={"Authorization": f"Bearer {_TOKEN}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == ERROR_UNTENANTED_GRANT
    assert spy.call_count == 0
    assert fabric.hitl.submissions(tenant=tenant) == ()


# --- Test 3: the MCP door's mint seam (R1 names it too) ---------------------


def test_mcp_door_invokes_the_mint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mcp.server.auth.provider import AccessToken
    from mcp.server.auth.settings import AnyHttpUrl, AuthSettings

    import ccf_runtime.mcp.hitl_server as hitl_server
    import ccf_runtime.mcp.tenancy as tenancy
    from ccf.authz.capability import Authorized, HitlSubmit, verify
    from ccf.hitl.transport import HitlActionSubmission
    from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, tenant_claims
    from ccf_runtime.mcp.hitl_server import SUBMIT_HITL_ACTION_TOOL, build_hitl_server

    from http_api.gate_fixtures import wide_authorizer

    spy = _WrapCounter(hitl_server.principal_from_authorized)
    monkeypatch.setattr(hitl_server, "principal_from_authorized", spy)
    grant = TokenGrant(
        client_id=_CLIENT_ID,
        scopes=(SCOPE_EVERYTHING,),
        tenants=frozenset({_MCP_TENANT}),
        authentication=_CLAIMS,
    )
    routed: list[tuple[Authorized[HitlSubmit], HitlActionSubmission]] = []

    def action_route(authorized: Authorized[HitlSubmit], *, submission: HitlActionSubmission) -> str:
        routed.append((authorized, submission))
        return "{}"

    server = build_hitl_server(
        server_name="was-called-hitl",
        queue_view=lambda authorized: (),
        action_route=action_route,
        token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(grants={"unit-token": grant})
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://unit.invalid/mcp"),
            required_scopes=[SCOPE_EVERYTHING],
        ),
        authorizer=wide_authorizer(tenant=_MCP_TENANT, key="was-called/mcp-mapping"),
        clock=lambda: _CLOCK_TIME,
    )
    token = AccessToken(
        token="unit-token",
        client_id=_CLIENT_ID,
        scopes=[SCOPE_EVERYTHING],
        claims={**tenant_claims(grant), AUTHENTICATION_CLAIM: _CLAIMS.model_dump(mode="json")},
    )
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: token)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: token)
    tool = server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn
    tool(
        tenant=_MCP_TENANT,
        event_key="derivation-event-1",
        action="approve",
        product_content_hash=_VALID_HASH,
    )
    assert spy.call_count == 1
    (args, kwargs) = spy.calls[0]
    assert args[0].principal == _CLIENT_ID
    assert kwargs["authentication"] == _CLAIMS
    assert kwargs["action_time"] == _CLOCK_TIME
    ((authorized, submission),) = routed
    assert submission.principal is spy.returns[0]
    # The route received a genuine capability for exactly this event.
    verify(authorized, kind=HitlSubmit, resource="derivation-event-1")
    assert authorized.tenant == _MCP_TENANT
