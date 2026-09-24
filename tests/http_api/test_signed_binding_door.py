"""D-16 door mapping — transport refusals as typed error codes (08-03 T2).

TDD RED. The two typed transport refusals from the signed-binding
composition (:class:`ccf.hitl.transport.SignedBindingRequiredRefused` /
:class:`~ccf.hitl.transport.SignedBindingInvalidRefused`) must surface at
BOTH Experience-Layer doors as the shared 08-02 error-code constants
(``ERROR_SIGNED_BINDING_REQUIRED`` / ``ERROR_SIGNED_BINDING_INVALID``,
one source of truth in ``ccf_runtime.http_api.errors``) — never as a
prose-only body, and never as an unmapped 500 (review consensus concern 1:
Codex HIGH, Cursor HIGH, Ollama C2/C3; Cursor MCP-parity concern).

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
from ccf_runtime.mcp.auth import FileTokenSource

from .conftest import Fabric, call

APPROVER_KID = "door-approver-signing-key"
POLICY_KEY = "acme-bank/hitl/door-policy"

_VALID_HASH = "c" * 64
_AWARE_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
_TOKEN = "door-token"
_CLIENT_ID = "door-auditor-1"
_TENANT_BASE = "signed-binding-door-tenant"


def _binding(subject_id: str) -> HumanPrincipalBinding:
    return HumanPrincipalBinding(
        approver=ApproverIdentity(
            subject_id=subject_id,
            identity_provider_ref="idp://acme-bank/dev-token-file",
        ),
        authentication=AuthenticationContext(
            method="bearer-token",
            assurance_level="dev",
            session_ref="door-session-1",
        ),
        action_time=_AWARE_TIME,
        product_content_hash=_VALID_HASH,
    )


def _submission_body(
    *,
    subject_id: str,
    tenant: str,
    signed: SignedPrincipalBinding | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "event_key": "door-event-1",
        "tenant": tenant,
        "action": "approve",
        "principal": _binding(subject_id).model_dump(mode="json"),
        "annotation": None,
        "signed_binding": (
            None if signed is None else signed.model_dump(mode="json")
        ),
    }
    return body


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
    return DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )


@pytest.fixture(scope="module")
def trusted_keys(key_dir: Path) -> Mapping[str, JsonWebKey]:
    private = json.loads(
        (key_dir / f"{APPROVER_KID}.jwk").read_text(encoding="utf-8")
    )
    public = ECKey.import_key(private).as_dict(private=False)
    return {APPROVER_KID: public}


@pytest.fixture(scope="module")
def token_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("door-auth") / "tokens.json"
    path.write_text(
        json.dumps({_TOKEN: {"client_id": _CLIENT_ID, "scopes": ["hitl"]}}),
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def enforcing_transport(
    fabric: Fabric,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> InMemoryHitlTransport:
    """A fresh transport bound to a signed-binding-required policy."""
    policy = parse_artifact(
        {"semver": "1.0.0", "signed_binding_required": True}, HITL_POLICY
    )
    assert isinstance(policy, HitlPolicy)
    fabric.registry.register_typed(POLICY_KEY, policy, HITL_POLICY)
    return InMemoryHitlTransport(
        control_plane=fabric.registry,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
        trusted_keys=trusted_keys,
    )


@pytest.fixture()
def auth_app(
    fabric: Fabric,
    token_file: Path,
    enforcing_transport: InMemoryHitlTransport,
) -> Any:
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.auth import BearerTokenAuth
    from ccf_runtime.http_api.dependencies import ApiDependencies

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
        ),
        auth=BearerTokenAuth(token_source=FileTokenSource(path=token_file)),
    )


# --- Test 1: HTTP, required + unsigned → ERROR_SIGNED_BINDING_REQUIRED -----


def test_http_unsigned_submission_carries_the_required_code(
    auth_app: Any, enforcing_transport: InMemoryHitlTransport
) -> None:
    from ccf_runtime.http_api.errors import ERROR_SIGNED_BINDING_REQUIRED

    tenant = f"{_TENANT_BASE}-required"
    response = call(
        auth_app,
        "POST",
        "/hitl/actions",
        json=_submission_body(
            subject_id=_CLIENT_ID, tenant=tenant, signed=None
        ),
        headers={"Authorization": f"Bearer {_TOKEN}"},
    )
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

    tenant = f"{_TENANT_BASE}-invalid"
    binding = _binding(_CLIENT_ID)
    signed = sign_principal_binding(
        binding, provider=provider, key_id=APPROVER_KID
    )
    tampered = signed.model_copy(
        update={"signature": signed.signature[:-4] + "AAAA"}
    )
    response = call(
        auth_app,
        "POST",
        "/hitl/actions",
        json=_submission_body(
            subject_id=_CLIENT_ID, tenant=tenant, signed=tampered
        ),
        headers={"Authorization": f"Bearer {_TOKEN}"},
    )
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error_code"] == ERROR_SIGNED_BINDING_INVALID
    assert enforcing_transport.submissions(tenant=tenant) == ()


# --- Test 3: HTTP, valid signed submission → admitted, binding recorded -----


def test_http_valid_signed_submission_is_admitted_with_binding(
    auth_app: Any,
    enforcing_transport: InMemoryHitlTransport,
    provider: DetachedJwsIdentityProvider,
) -> None:
    tenant = f"{_TENANT_BASE}-admitted"
    binding = _binding(_CLIENT_ID)
    signed = sign_principal_binding(
        binding, provider=provider, key_id=APPROVER_KID
    )
    response = call(
        auth_app,
        "POST",
        "/hitl/actions",
        json=_submission_body(
            subject_id=_CLIENT_ID, tenant=tenant, signed=signed
        ),
        headers={"Authorization": f"Bearer {_TOKEN}"},
    )
    assert response.status_code == 200
    receipt = response.json()
    assert receipt["status"] == "submitted"
    assert receipt["submission"]["signed_binding"] is not None
    recorded = enforcing_transport.submissions(tenant=tenant)
    assert len(recorded) == 1
    assert recorded[0].signed_binding == signed


# --- Test 4: MCP parity — same codes in the MCP door's error payload --------


def _mcp_server(tmp_path: Path, action_route: Any) -> Any:
    from mcp.server.auth.settings import AuthSettings
    from pydantic import AnyHttpUrl

    from ccf.hitl.transport import PendingHitlEvent
    from ccf_runtime.mcp.auth import (
        FileTokenSource as McpTokenSource,
        SourceBackedTokenVerifier,
    )
    from ccf_runtime.mcp.hitl_server import build_hitl_server

    token_file = tmp_path / "tokens.json"
    token_file.write_text(
        json.dumps(
            {"unit-token": {"client_id": _CLIENT_ID, "scopes": ["h"]}}
        ),
        encoding="utf-8",
    )

    def queue_view(*, tenant: str) -> tuple[PendingHitlEvent, ...]:
        return ()

    return build_hitl_server(
        server_name="door-parity-hitl",
        queue_view=queue_view,
        action_route=action_route,
        token_verifier=SourceBackedTokenVerifier(
            source=McpTokenSource(path=token_file)
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://unit.invalid/mcp"),
            required_scopes=["h"],
        ),
    )


def _mcp_arguments(**overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "tenant": f"{_TENANT_BASE}-mcp",
        "event_key": "door-event-1",
        "action": "approve",
        "subject_id": _CLIENT_ID,
        "identity_provider_ref": "idp://acme-bank/dev-token-file",
        "method": "bearer-token",
        "assurance_level": "dev",
        "session_ref": "door-session-1",
        "action_time": _AWARE_TIME.isoformat(),
        "product_content_hash": _VALID_HASH,
    }
    arguments.update(overrides)
    return arguments


def _tool_fn(server: Any) -> Any:
    from ccf_runtime.mcp.hitl_server import SUBMIT_HITL_ACTION_TOOL

    return server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn


def test_mcp_door_returns_the_same_typed_error_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fabric: Fabric,
    enforcing_transport: InMemoryHitlTransport,
) -> None:
    """MCP parity: both refusal cases carry the shared constants."""
    import ccf_runtime.mcp.hitl_server as hitl_server
    from mcp.server.auth.provider import AccessToken

    from ccf.hitl.transport import HitlActionSubmission
    from ccf_runtime.http_api.errors import (
        ERROR_SIGNED_BINDING_INVALID,
        ERROR_SIGNED_BINDING_REQUIRED,
    )

    def action_route(*, submission: HitlActionSubmission) -> str:
        enforcing_transport.submit(submission=submission)
        return "{}"

    server = _mcp_server(tmp_path, action_route)
    # BOTH readers of the verified identity: the door, for its subject
    # binding, and `ccf_runtime.mcp.tenancy`, for the tenancy floor installed
    # at registration. Each imported the name into its own namespace, so one
    # patch leaves the other reading the real (empty) context (`SEC-018`).
    import ccf_runtime.mcp.tenancy as tenancy

    from ccf_runtime.mcp.auth import TokenGrant, tenant_claims

    _mcp_tenant = f"{_TENANT_BASE}-mcp"
    _token = AccessToken(
        token="unit-token",
        client_id=_CLIENT_ID,
        scopes=["h"],
        claims=dict(
            tenant_claims(
                TokenGrant(
                    client_id=_CLIENT_ID,
                    scopes=("h",),
                    tenants=frozenset({_mcp_tenant}),
                )
            )
        ),
    )
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: _token)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: _token)
    tool = _tool_fn(server)

    # Case 1: no signed binding presented — required code in the payload.
    with pytest.raises(ValueError) as required_error:
        tool(**_mcp_arguments())
    required_payload = json.loads(str(required_error.value))
    assert required_payload["error_code"] == ERROR_SIGNED_BINDING_REQUIRED

    # Case 2: an unverifiable signature — invalid code in the payload.
    with pytest.raises(ValueError) as invalid_error:
        tool(
            **_mcp_arguments(
                signed_binding_signature="not-a..real-signature",
                signed_binding_key_id=APPROVER_KID,
            )
        )
    invalid_payload = json.loads(str(invalid_error.value))
    assert invalid_payload["error_code"] == ERROR_SIGNED_BINDING_INVALID

    # Nothing landed on the transport for either refusal.
    assert (
        enforcing_transport.submissions(tenant=f"{_TENANT_BASE}-mcp") == ()
    )
