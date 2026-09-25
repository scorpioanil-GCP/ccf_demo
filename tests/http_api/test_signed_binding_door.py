"""D-16 door mapping under a door-minted binding (08-03 T2; D-IMPL-353 §2 P6).

The two typed transport refusals from the signed-binding composition
(:class:`ccf.hitl.transport.SignedBindingRequiredRefused` /
:class:`~ccf.hitl.transport.SignedBindingInvalidRefused`) must surface at
BOTH Experience-Layer doors as the shared 08-02 error-code constants
(``ERROR_SIGNED_BINDING_REQUIRED`` / ``ERROR_SIGNED_BINDING_INVALID``) —
never as a prose-only body, and never as an unmapped 500.

**What P6 changes about signing.** The binding the transport verifies the
signature against is the one the DOOR mints — subject from the capability,
claims from the verified credential, ``action_time`` from the injected
clock. A signer therefore attests the server's statement of the action, not
its own: a signature over a binding claiming a higher assurance than the
verifier stated is *invalid* here, which is the non-repudiation leg and the
server-attested leg agreeing. (The consequence for a production signer — it
must sign what the server will mint, so the clock reading must be known to
it — is recorded in the lane report as a D-16 follow-up, not resolved here.)

Test values are deployment vocabulary chosen by this test-as-deployment
(CINV-01), following ``tests/http_api/test_auth_hardening.py``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from joserfc.jwk import ECKey

from ccf.controlplane.artifacts import parse_artifact
from ccf.hitl.identity_binding import (
    SignedPrincipalBinding,
    sign_principal_binding,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationClaims,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import (
    HITL_POLICY,
    HitlPolicy,
    InMemoryHitlTransport,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
)
from ccf_runtime.mcp.auth import StaticTokenSource, TokenGrant

from .conftest import Fabric, call

APPROVER_KID = "door-approver-signing-key"
POLICY_KEY = "acme-bank/hitl/door-policy"

_VALID_HASH = "c" * 64
_CLOCK_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
_CLIENT_ID = "door-auditor-1"
_TENANT_BASE = "signed-binding-door-tenant"
_SCOPE = "gate:everything"

#: What the verifier states about every credential in this suite.
_CLAIMS = AuthenticationClaims(
    identity_provider_ref="idp://acme-bank/dev-token-file",
    method="bearer-token",
    assurance_level="dev",
    session_ref="door-session-1",
)


def _minted_binding(*, assurance_level: str = _CLAIMS.assurance_level) -> HumanPrincipalBinding:
    """The binding the door WILL mint for this suite's credential — what a
    signer must sign. ``assurance_level`` is a parameter only so a test can
    sign a binding the door will NOT mint."""
    return HumanPrincipalBinding(
        approver=ApproverIdentity(
            subject_id=_CLIENT_ID,
            identity_provider_ref=_CLAIMS.identity_provider_ref,
        ),
        authentication=AuthenticationContext(
            method=_CLAIMS.method,
            assurance_level=assurance_level,
            session_ref=_CLAIMS.session_ref,
        ),
        action_time=_CLOCK_TIME,
        product_content_hash=_VALID_HASH,
    )


def _body(*, signed: SignedPrincipalBinding | None) -> dict[str, Any]:
    return {
        "event_key": "door-event-1",
        "action": "approve",
        "product_content_hash": _VALID_HASH,
        "annotation": None,
        "signed_binding": None if signed is None else signed.model_dump(mode="json"),
    }


@pytest.fixture(scope="module")
def key_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("door-keys")
    key = ECKey.generate_key("P-256", parameters={"kid": APPROVER_KID})
    (directory / f"{APPROVER_KID}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return directory


@pytest.fixture(scope="module")
def provider(key_dir: Path) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(key_source=FileBackedKeySource(directory=key_dir))


@pytest.fixture(scope="module")
def trusted_keys(key_dir: Path) -> Mapping[str, JsonWebKey]:
    private = json.loads((key_dir / f"{APPROVER_KID}.jwk").read_text(encoding="utf-8"))
    public = ECKey.import_key(private).as_dict(private=False)
    return {APPROVER_KID: public}


@pytest.fixture()
def enforcing_transport(
    fabric: Fabric,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> InMemoryHitlTransport:
    """A fresh transport bound to a signed-binding-required policy."""
    policy = parse_artifact({"semver": "1.0.0", "signed_binding_required": True}, HITL_POLICY)
    assert isinstance(policy, HitlPolicy)
    fabric.registry.register_typed(POLICY_KEY, policy, HITL_POLICY)
    return InMemoryHitlTransport(
        control_plane=fabric.registry,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
        trusted_keys=trusted_keys,
    )


_TENANTS = ("required", "invalid", "admitted", "upgraded", "mcp")


def _tenant(suffix: str) -> str:
    return f"{_TENANT_BASE}-{suffix}"


def _token_for(tenant: str) -> str:
    return f"door-token-{tenant.rsplit('-', 1)[-1]}"


def _grants() -> dict[str, TokenGrant]:
    return {
        _token_for(_tenant(suffix)): TokenGrant(
            client_id=_CLIENT_ID,
            scopes=(_SCOPE,),
            tenants=frozenset({_tenant(suffix)}),
            authentication=_CLAIMS,
        )
        for suffix in _TENANTS
    }


@pytest.fixture()
def auth_app(
    fabric: Fabric, enforcing_transport: InMemoryHitlTransport, tmp_path: Path
) -> Any:
    from ccf.projection.plan import Perspective
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.auth import BearerTokenAuth
    from ccf_runtime.http_api.dependencies import ApiDependencies

    from .gate_fixtures import authority
    from .test_product_declared_obligation_409 import (
        _entitlement_registry,
        _recorder,
    )

    source = ControlPlaneProductEntitlementSource(
        control_plane=_entitlement_registry(fabric),
        clock=lambda: datetime(2026, 8, 11, tzinfo=UTC),
    )
    seams = authority(
        tenant=tuple(_tenant(suffix) for suffix in _TENANTS),
        key="signed-binding/mapping",
        grants={"unused": (_CLIENT_ID, (_SCOPE,), _tenant("required"))},
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role="signed-binding-role"
            )
        ),
        refusal_recorder=_recorder(fabric, tmp_path, source=source),
    )
    seams["auth"] = BearerTokenAuth(token_source=StaticTokenSource(grants=_grants()))
    return create_app(
        ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=enforcing_transport,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
            clock=lambda: _CLOCK_TIME,
        ),
        **seams,
    )


def _post(app: Any, tenant: str, body: dict[str, Any]) -> Any:
    return call(
        app,
        "POST",
        "/hitl/actions",
        json=body,
        headers={"Authorization": f"Bearer {_token_for(tenant)}"},
    )


# --- Test 1: HTTP, required + unsigned → ERROR_SIGNED_BINDING_REQUIRED -----


def test_http_unsigned_submission_carries_the_required_code(
    auth_app: Any, enforcing_transport: InMemoryHitlTransport
) -> None:
    from ccf_runtime.http_api.errors import ERROR_SIGNED_BINDING_REQUIRED

    tenant = _tenant("required")
    response = _post(auth_app, tenant, _body(signed=None))
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error_code"] == ERROR_SIGNED_BINDING_REQUIRED
    assert "message" in detail  # code + prose, never prose-only
    assert enforcing_transport.submissions(tenant=tenant) == ()


# --- Test 2: HTTP, invalid signature → ERROR_SIGNED_BINDING_INVALID --------


def test_http_invalid_binding_carries_the_invalid_code(
    auth_app: Any,
    enforcing_transport: InMemoryHitlTransport,
    provider: DetachedJwsIdentityProvider,
) -> None:
    from ccf_runtime.http_api.errors import ERROR_SIGNED_BINDING_INVALID

    tenant = _tenant("invalid")
    signed = sign_principal_binding(_minted_binding(), provider=provider, key_id=APPROVER_KID)
    tampered = signed.model_copy(update={"signature": signed.signature[:-4] + "AAAA"})
    response = _post(auth_app, tenant, _body(signed=tampered))
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == ERROR_SIGNED_BINDING_INVALID
    assert enforcing_transport.submissions(tenant=tenant) == ()


# --- Test 3: HTTP, valid signed submission → admitted, binding recorded -----


def test_http_valid_signed_submission_is_admitted_with_binding(
    auth_app: Any,
    enforcing_transport: InMemoryHitlTransport,
    provider: DetachedJwsIdentityProvider,
) -> None:
    tenant = _tenant("admitted")
    binding = _minted_binding()
    signed = sign_principal_binding(binding, provider=provider, key_id=APPROVER_KID)
    response = _post(auth_app, tenant, _body(signed=signed))
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["status"] == "submitted"
    assert receipt["submission"]["signed_binding"] is not None
    (recorded,) = enforcing_transport.submissions(tenant=tenant)
    assert recorded.signed_binding == signed
    # The property that makes this test load-bearing under P6: the door
    # minted EXACTLY the binding the signer attested — had it read any field
    # from the body, or the wall clock, the signature would not have held.
    assert recorded.principal == binding


# --- Test 3b: a signature cannot raise the assurance the verifier stated ----


def test_http_a_signed_binding_over_a_higher_assurance_than_the_tokens_is_invalid(
    auth_app: Any,
    enforcing_transport: InMemoryHitlTransport,
    provider: DetachedJwsIdentityProvider,
) -> None:
    from ccf_runtime.http_api.errors import ERROR_SIGNED_BINDING_INVALID

    tenant = _tenant("upgraded")
    upgraded = sign_principal_binding(
        _minted_binding(assurance_level="aal3"), provider=provider, key_id=APPROVER_KID
    )
    response = _post(auth_app, tenant, _body(signed=upgraded))
    assert response.status_code == 403, response.text
    assert response.json()["detail"]["error_code"] == ERROR_SIGNED_BINDING_INVALID
    assert enforcing_transport.submissions(tenant=tenant) == ()


# --- Test 4: MCP parity — same codes in the MCP door's error payload --------


def _mcp_server(action_route: Any) -> Any:
    from mcp.server.auth.settings import AuthSettings
    from pydantic import AnyHttpUrl

    from ccf_runtime.mcp.auth import SourceBackedTokenVerifier
    from ccf_runtime.mcp.hitl_server import build_hitl_server

    from .gate_fixtures import wide_authorizer

    return build_hitl_server(
        server_name="door-parity-hitl",
        queue_view=lambda authorized: (),
        action_route=action_route,
        token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(grants=_grants())
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://unit.invalid/mcp"),
            required_scopes=[_SCOPE],
        ),
        authorizer=wide_authorizer(tenant=_tenant("mcp"), key="signed-binding/mcp-mapping"),
        clock=lambda: _CLOCK_TIME,
    )


def _mcp_arguments(**overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "tenant": _tenant("mcp"),
        "event_key": "door-event-1",
        "action": "approve",
        "product_content_hash": _VALID_HASH,
    }
    arguments.update(overrides)
    return arguments


def test_mcp_door_returns_the_same_typed_error_codes(
    monkeypatch: pytest.MonkeyPatch,
    fabric: Fabric,
    enforcing_transport: InMemoryHitlTransport,
) -> None:
    """MCP parity: both refusal cases carry the shared constants."""
    import ccf_runtime.mcp.hitl_server as hitl_server
    import ccf_runtime.mcp.tenancy as tenancy
    from mcp.server.auth.provider import AccessToken

    from ccf.authz.capability import Authorized, HitlSubmit
    from ccf.hitl.principal import AUTHENTICATION_CLAIM
    from ccf.hitl.transport import HitlActionSubmission
    from ccf_runtime.http_api.errors import (
        ERROR_SIGNED_BINDING_INVALID,
        ERROR_SIGNED_BINDING_REQUIRED,
    )
    from ccf_runtime.mcp.auth import tenant_claims
    from ccf_runtime.mcp.hitl_server import SUBMIT_HITL_ACTION_TOOL

    def action_route(authorized: Authorized[HitlSubmit], *, submission: HitlActionSubmission) -> str:
        enforcing_transport.submit(authorized, submission=submission)
        return "{}"

    server = _mcp_server(action_route)
    tenant = _tenant("mcp")
    grant = _grants()[_token_for(tenant)]
    token = AccessToken(
        token=_token_for(tenant),
        client_id=_CLIENT_ID,
        scopes=[_SCOPE],
        claims={
            **tenant_claims(grant),
            AUTHENTICATION_CLAIM: _CLAIMS.model_dump(mode="json"),
        },
    )
    # BOTH readers of the verified identity: the wrapper (tenancy + mint) and
    # the door (authentication claims). Each imported the name into its own
    # namespace, so one patch leaves the other reading the real (empty)
    # context.
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: token)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: token)
    tool = server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn

    with pytest.raises(ValueError) as required_error:
        tool(**_mcp_arguments())
    assert json.loads(str(required_error.value))["error_code"] == ERROR_SIGNED_BINDING_REQUIRED

    with pytest.raises(ValueError) as invalid_error:
        tool(
            **_mcp_arguments(
                signed_binding_signature="not-a..real-signature",
                signed_binding_key_id=APPROVER_KID,
            )
        )
    assert json.loads(str(invalid_error.value))["error_code"] == ERROR_SIGNED_BINDING_INVALID

    assert enforcing_transport.submissions(tenant=tenant) == ()
