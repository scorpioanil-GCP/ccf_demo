"""SEC-005, the remaining leg — the signed-claims / time-window repair at the MCP door (`D-IMPL-363`).

RED-FIRST, the MCP twin of ``tests/http_api/test_sec005_attestation_door.py``: the
design's §9 item 9 at the MCP door as `D-IMPL-363` ruled it (C12(a): ONE
``attestation`` object parameter, the same shape as the HTTP body), committed before
any production change. Nothing fails at import, collection or fixture setup: the
tool is reached through the guarded callable ``FastMCP`` holds and every absent
surface is asserted on inside the test body.

The server here routes to the REAL reference transport (``InMemoryHitlTransport``)
so verification actually runs — unlike ``tests/mcp/test_hitl_server_door.py``'s
recording stub — and its clock is a REAL wall clock.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from joserfc.jwk import ECKey
from mcp.server.auth.settings import AnyHttpUrl, AuthSettings
from ccf.authz.capability import Authorized, HitlQueueRead, HitlSubmit
from ccf.controlplane.artifacts import ArtifactLoadError, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.transport import HITL_POLICY, HitlActionSubmission, HitlPolicy, InMemoryHitlTransport, PendingHitlEvent
from ccf.peering.identity import DetachedJwsIdentityProvider, FileBackedKeySource, JsonWebKey
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource
from ccf_runtime.mcp.hitl_server import SUBMIT_HITL_ACTION_TOOL, build_hitl_server

from http_api.composition_authority import register_typed_at_composition
from http_api.gate_fixtures import wide_authorizer

import ccf_runtime.mcp.hitl_server as hitl_server
import ccf_runtime.mcp.tenancy as tenancy
from ccf.hitl.principal import AUTHENTICATION_CLAIM, AuthenticationClaims
from ccf_runtime.mcp.auth import TokenGrant, tenant_claims
from http_api.gate_fixtures import SCOPE_EVERYTHING
from mcp.server.auth.provider import AccessToken

# `tests/mcp` is not a package, so the sibling door suite's helpers are restated
# here rather than imported (bare module names collide across trees).
TENANT = "mcp-attestation-tenant"
CLIENT_ID = "mcp-attestation-auditor"
SCOPE = SCOPE_EVERYTHING
VALID_HASH = "d" * 64
CLAIMS = AuthenticationClaims(
    identity_provider_ref="idp://acme-bank/dev-token-file",
    method="bearer-token",
    assurance_level="aal3",
    session_ref="mcp-attestation-session",
)


def _grant(*, claims: AuthenticationClaims | None) -> TokenGrant:
    return TokenGrant(client_id=CLIENT_ID, scopes=(SCOPE,), tenants=frozenset({TENANT}), authentication=claims)


def _token(*, claims: AuthenticationClaims | None) -> AccessToken:
    grant = _grant(claims=claims)
    extra = {} if claims is None else {AUTHENTICATION_CLAIM: claims.model_dump(mode="json")}
    return AccessToken(token="unit-token", client_id=CLIENT_ID, scopes=[SCOPE], claims={**tenant_claims(grant), **extra})


def _verified_as(monkeypatch: pytest.MonkeyPatch, token: AccessToken) -> None:
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: token)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: token)

KID = "mcp-attestation-signing-key"
OTHER_SUBJECT = "mcp-door-auditor-2"
OTHER_KID = "mcp-other-subject-signing-key"
POLICY_KEY = "acme-bank/hitl/mcp-attestation-policy"
MAX_AGE_SECONDS = 300
SKEW_SECONDS = 60
CODE_MISMATCH = "signed-binding-mismatch"
CODE_STALE = "signed-binding-stale"
FIXED_CLOCK = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def _keypair(directory: Path, kid: str) -> JsonWebKey:
    key = ECKey.generate_key("P-256", parameters={"kid": kid})
    (directory / f"{kid}.jwk").write_text(json.dumps(key.as_dict(private=True)), encoding="utf-8")
    return key.as_dict(private=False)


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, JsonWebKey, JsonWebKey]:
    directory = tmp_path_factory.mktemp("mcp-attestation-keys")
    return directory, _keypair(directory, KID), _keypair(directory, OTHER_KID)


@pytest.fixture(scope="module")
def provider(keys: tuple[Path, JsonWebKey, JsonWebKey]) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(key_source=FileBackedKeySource(directory=keys[0]))


def _ruled_policy_document(public: JsonWebKey, other_public: JsonWebKey) -> dict[str, Any]:
    return {
        "semver": "1.0.0",
        "signed_binding_required": True,
        "signature_max_age_seconds": MAX_AGE_SECONDS,
        "permitted_clock_skew_seconds": SKEW_SECONDS,
        "trusted_keys": {CLIENT_ID: {KID: public}, OTHER_SUBJECT: {OTHER_KID: other_public}},
    }


@pytest.fixture()
def transport(keys: tuple[Path, JsonWebKey, JsonWebKey], provider: DetachedJwsIdentityProvider) -> InMemoryHitlTransport:
    """The ruled policy, or today's two-field policy until the contract accepts the
    ruled one (the gap is pinned at the HTTP twin); never a setup error."""
    _, public, other_public = keys
    registry = ControlPlaneRegistry()
    try:
        policy = parse_artifact(_ruled_policy_document(public, other_public), HITL_POLICY)
    except ArtifactLoadError:
        policy = parse_artifact({"semver": "1.0.0", "signed_binding_required": True}, HITL_POLICY)
    assert isinstance(policy, HitlPolicy)
    register_typed_at_composition(registry, POLICY_KEY, policy, HITL_POLICY)
    return InMemoryHitlTransport(
        control_plane=registry,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
        trusted_keys={KID: public, OTHER_KID: other_public},
    )


def _build_tool(transport: InMemoryHitlTransport, monkeypatch: pytest.MonkeyPatch, clock: Callable[[], datetime]) -> Any:
    """The MCP submit tool over the REAL transport, under the given door clock."""

    def queue_view(authorized: Authorized[HitlQueueRead]) -> tuple[PendingHitlEvent, ...]:
        return transport.view(authorized)

    def action_route(authorized: Authorized[HitlSubmit], *, submission: HitlActionSubmission) -> str:
        recorded = transport.submit(authorized, submission=submission)
        return json.dumps(recorded.model_dump(mode="json"))

    server = build_hitl_server(
        server_name="mcp-attestation-door",
        queue_view=queue_view,
        action_route=action_route,
        token_verifier=SourceBackedTokenVerifier(source=StaticTokenSource(grants={"unit-token": _grant(claims=CLAIMS)})),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://unit.invalid/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=wide_authorizer(tenant=TENANT, key="mcp-attestation/mapping"),
        clock=clock,
    )
    _verified_as(monkeypatch, _token(claims=CLAIMS))
    return server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn


@pytest.fixture()
def tool(transport: InMemoryHitlTransport, monkeypatch: pytest.MonkeyPatch) -> Any:
    """A REAL wall clock at the door — the positives and the instant-independent negatives."""
    return _build_tool(transport, monkeypatch, lambda: datetime.now(UTC))


@pytest.fixture()
def fixed_clock_tool(transport: InMemoryHitlTransport, monkeypatch: pytest.MonkeyPatch) -> Any:
    """A deterministic door clock for the window and skew negatives."""
    return _build_tool(transport, monkeypatch, lambda: FIXED_CLOCK)


def _claims(
    *,
    tenant: str = TENANT,
    event_key: str = "mcp-attestation-event",
    action: str = "approve",
    product_content_hash: str = VALID_HASH,
    subject_id: str = CLIENT_ID,
    issued_at: datetime | None = None,
    nonce: str = "nonce-0001",
) -> dict[str, Any]:
    return {
        "tenant": tenant,
        "event_key": event_key,
        "action": action,
        "product_content_hash": product_content_hash,
        "subject_id": subject_id,
        "issued_at": (issued_at or datetime.now(UTC)).isoformat(),
        "nonce": nonce,
    }


def _attest(claims: dict[str, Any], *, provider: DetachedJwsIdentityProvider, key_id: str) -> dict[str, Any]:
    envelope = provider.sign(product=claims, key_id=key_id)
    return {"claims": claims, "signature": f"{envelope.protected}..{envelope.signature}", "key_id": key_id}


def _arguments(claims: dict[str, Any], attestation: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "tenant": TENANT,
        "event_key": claims["event_key"],
        "action": claims["action"],
        "product_content_hash": claims["product_content_hash"],
        "attestation": attestation,
    }
    arguments.update(overrides)
    return arguments


def _submit(tool: Any, arguments: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Call the tool; return (receipt, refusal). A TypeError means the tool has no
    `attestation` parameter — asserted on as a failure, never an error."""
    try:
        result = tool(**arguments)
    except TypeError as error:
        pytest.fail(f"the MCP door has no `attestation` parameter (D-IMPL-363 C12(a)): {error}")
    except ValueError as error:
        return None, json.loads(str(error))
    return json.loads(result), None


def _assert_refused(tool: Any, transport: InMemoryHitlTransport, arguments: dict[str, Any], *, code: str) -> None:
    receipt, refusal = _submit(tool, arguments)
    assert refusal is not None, f"expected a {code!r} refusal; the door admitted: {receipt}"
    assert refusal["error_code"] == code, refusal
    assert transport.submissions(tenant=TENANT) == ()


# --- the positive ---


def test_mcp_a_signed_submission_succeeds_under_a_wall_clock(
    tool: Any, transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    claims = _claims()
    attestation = _attest(claims, provider=provider, key_id=KID)
    receipt, refusal = _submit(tool, _arguments(claims, attestation))
    assert refusal is None, f"a signed submission under a wall clock must be admitted; refused: {refusal}"
    assert receipt is not None and receipt["attestation"] == attestation
    (recorded,) = transport.submissions(tenant=TENANT)
    assert recorded.principal.action_time.tzinfo is not None
    assert abs((datetime.now(UTC) - recorded.principal.action_time).total_seconds()) < MAX_AGE_SECONDS
    assert receipt["hitl_policy_ref"], "the submission records the admitting policy (E3)"


# --- the negatives, one per clause of §9 item 9 ---


def test_mcp_an_attestation_for_another_event_key_is_refused_mismatch(
    tool: Any, transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    claims = _claims(event_key="mcp-event-A")
    attestation = _attest(claims, provider=provider, key_id=KID)
    _assert_refused(tool, transport, _arguments(claims, attestation, event_key="mcp-event-B"), code=CODE_MISMATCH)


def test_mcp_an_attestation_for_another_tenant_is_refused_mismatch(
    tool: Any, transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    claims = _claims(tenant="some-other-tenant")
    attestation = _attest(claims, provider=provider, key_id=KID)
    _assert_refused(tool, transport, _arguments(claims, attestation), code=CODE_MISMATCH)


def test_mcp_an_attestation_signed_for_the_opposite_verdict_is_refused_mismatch(
    tool: Any, transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    claims = _claims(action="reject")
    attestation = _attest(claims, provider=provider, key_id=KID)
    _assert_refused(tool, transport, _arguments(claims, attestation, action="approve"), code=CODE_MISMATCH)


def test_mcp_an_attestation_issued_past_the_window_is_refused_stale(
    fixed_clock_tool: Any, transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    claims = _claims(issued_at=FIXED_CLOCK - timedelta(seconds=MAX_AGE_SECONDS + 1))
    attestation = _attest(claims, provider=provider, key_id=KID)
    _assert_refused(fixed_clock_tool, transport, _arguments(claims, attestation), code=CODE_STALE)


def test_mcp_an_attestation_post_dated_beyond_the_skew_is_refused_stale(
    fixed_clock_tool: Any, transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    claims = _claims(issued_at=FIXED_CLOCK + timedelta(seconds=SKEW_SECONDS + 1))
    attestation = _attest(claims, provider=provider, key_id=KID)
    _assert_refused(fixed_clock_tool, transport, _arguments(claims, attestation), code=CODE_STALE)


def test_mcp_a_reused_nonce_is_refused_stale(
    tool: Any, transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    claims = _claims(nonce="nonce-once")
    attestation = _attest(claims, provider=provider, key_id=KID)
    receipt, refusal = _submit(tool, _arguments(claims, attestation))
    assert refusal is None, f"the first presentation must be admitted; refused: {refusal}"
    _, second = _submit(tool, _arguments(claims, attestation))
    assert second is not None and second["error_code"] == CODE_STALE, second
    assert len(transport.submissions(tenant=TENANT)) == 1


def test_mcp_a_nonce_presented_concurrently_is_admitted_exactly_once(
    tool: Any, transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    """C11(a) is ATOMIC: N identical presentations racing through the tool admit
    exactly one; the rest refuse `-stale`; one is recorded."""
    claims = _claims(nonce="nonce-raced")
    attestation = _attest(claims, provider=provider, key_id=KID)
    arguments = _arguments(claims, attestation)
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda _: _submit(tool, arguments), range(8)))
    admitted = [receipt for receipt, refusal in outcomes if refusal is None]
    refused = [refusal for receipt, refusal in outcomes if refusal is not None]
    assert len(admitted) == 1, f"exactly one presentation may be admitted; admitted={len(admitted)} refused={len(refused)}"
    assert all(refusal["error_code"] == CODE_STALE for refusal in refused), refused
    assert len(transport.submissions(tenant=TENANT)) == 1


def test_mcp_a_key_not_declared_for_the_subject_is_refused_mismatch(
    tool: Any, transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    claims = _claims()  # subject_id is CLIENT_ID
    attestation = _attest(claims, provider=provider, key_id=OTHER_KID)  # declared for OTHER_SUBJECT only
    _assert_refused(tool, transport, _arguments(claims, attestation), code=CODE_MISMATCH)
