"""D-16 door mapping under a signer-stated attestation (08-03 T2; D-IMPL-353 §2 P6; `D-IMPL-363`).

The typed transport refusals from the attestation composition must surface at
BOTH Experience-Layer doors as the shared 08-02 error-code constants —
``ERROR_SIGNED_BINDING_REQUIRED`` / ``ERROR_SIGNED_BINDING_INVALID`` /
``ERROR_SIGNED_BINDING_MISMATCH`` / ``ERROR_SIGNED_BINDING_STALE`` — never as
a prose-only body, and never as an unmapped 500.

**What `D-IMPL-363` changed about signing, and why this module was rewritten.**
Under P6 the signed object was the DOOR-minted
:class:`~ccf.hitl.principal.HumanPrincipalBinding`, ``action_time`` included,
so a signer had to predict the server's clock reading — the limit recorded at
``docs/surface-changes/353-06-the-approval-record-is-server-attested.md``.
`D-IMPL-363` replaces it with the signer's own
:class:`~ccf.hitl.identity_binding.HitlActionClaims`, carried as the
``attestation``. The binding stays door-minted and UNSIGNED, and the two legs
are now separately observable, which is what this suite holds:

* the door still mints the binding from the capability, the verified grant's
  claims and the injected clock — asserted here against an independently
  computed expectation, exactly as the P6 test did against the signed copy;
* the client's signed statement authorizes exactly one action and cannot
  smuggle a field the door mints. Assurance level is the measured case: it is
  not a member of :class:`HitlActionClaims` at all, so an attestation that
  states one is a MALFORMED attestation the door refuses at the body
  boundary, and the recorded assurance is the token's whatever the client
  sends.

The door clock here is FIXED (``_CLOCK_TIME``), so the window negatives at the
MCP leg are exact rather than a race against execution; the wall-clock
positive — the property the 353-06 limit was about — is held by
``tests/http_api/test_sec005_attestation_door.py``.

Test values are deployment vocabulary chosen by this test-as-deployment
(CINV-01), following ``tests/http_api/test_auth_hardening.py``.
"""

from __future__ import annotations

import json
from tests.composition import declared_erasure_trust, no_erasures
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from joserfc.jwk import ECKey

from ccf.controlplane.artifacts import parse_artifact
from ccf.hitl.identity_binding import (
    HitlActionClaims,
    SignedHitlAction,
    sign_hitl_action,
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
from http_api.composition_authority import (
    register_typed_at_composition,
)

APPROVER_KID = "door-approver-signing-key"
POLICY_KEY = "acme-bank/hitl/door-policy"

_VALID_HASH = "c" * 64
_CLOCK_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
_CLIENT_ID = "door-auditor-1"
_TENANT_BASE = "signed-binding-door-tenant"
_SCOPE = "gate:everything"
_EVENT_KEY = "door-event-1"

#: The pinned window this test-as-deployment states (`D-IMPL-363` E3). Both
#: are REQUIRED of a policy that requires an attestation; the SDK defaults
#: neither (CINV-01).
MAX_AGE_SECONDS = 300
SKEW_SECONDS = 60

#: What the verifier states about every credential in this suite.
_CLAIMS = AuthenticationClaims(
    identity_provider_ref="idp://acme-bank/dev-token-file",
    method="bearer-token",
    assurance_level="dev",
    session_ref="door-session-1",
)


def _minted_binding(*, assurance_level: str = _CLAIMS.assurance_level) -> HumanPrincipalBinding:
    """The binding the door WILL mint for this suite's credential, computed
    independently of the door (`D-IMPL-363` leaves it door-minted and
    unsigned). ``assurance_level`` is a parameter only so a test can state an
    assurance the door will NOT record."""
    return HumanPrincipalBinding(
        verdict="approve",
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


def _claims(
    *,
    tenant: str,
    event_key: str = _EVENT_KEY,
    action: str = "approve",
    product_content_hash: str = _VALID_HASH,
    subject_id: str = _CLIENT_ID,
    issued_at: datetime | None = None,
    nonce: str = "nonce-0001",
) -> HitlActionClaims:
    """What the signer states about one action — nothing the door mints
    (`D-IMPL-363` E1). ``issued_at`` defaults to the fixed door instant, so a
    claim is fresh unless a test moves it."""
    return HitlActionClaims(
        tenant=tenant,
        event_key=event_key,
        action=action,
        product_content_hash=product_content_hash,
        subject_id=subject_id,
        issued_at=_CLOCK_TIME if issued_at is None else issued_at,
        nonce=nonce,
    )


def _attest(
    claims: HitlActionClaims,
    *,
    provider: DetachedJwsIdentityProvider,
    key_id: str = APPROVER_KID,
) -> SignedHitlAction:
    return sign_hitl_action(claims, provider=provider, key_id=key_id)


def _body(
    *,
    attestation: SignedHitlAction | None,
    action: str = "approve",
    event_key: str = _EVENT_KEY,
) -> dict[str, Any]:
    return {
        "event_key": event_key,
        "action": action,
        "product_content_hash": _VALID_HASH,
        "annotation": None,
        "attestation": (
            None if attestation is None else attestation.model_dump(mode="json")
        ),
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
def public_jwk(key_dir: Path) -> JsonWebKey:
    """The approver's PUBLIC key, as the pinned policy declares it."""
    private = json.loads((key_dir / f"{APPROVER_KID}.jwk").read_text(encoding="utf-8"))
    public: JsonWebKey = ECKey.import_key(private).as_dict(private=False)
    return public


def _ruled_policy_document(public: JsonWebKey) -> dict[str, Any]:
    """The policy `D-IMPL-363` rules (E3, E5, C6(a)): the freshness window and
    the per-subject trusted keys INSIDE the pinned artifact — one trust source,
    never a transport constructor argument."""
    return {
        "semver": "1.0.0",
        "signed_binding_required": True,
        "signature_max_age_seconds": MAX_AGE_SECONDS,
        "permitted_clock_skew_seconds": SKEW_SECONDS,
        "trusted_keys": {_CLIENT_ID: {APPROVER_KID: public}},
    }


@pytest.fixture()
def enforcing_transport(
    fabric: Fabric,
    provider: DetachedJwsIdentityProvider,
    public_jwk: JsonWebKey,
) -> InMemoryHitlTransport:
    """A fresh transport bound to an attestation-required policy."""
    policy = parse_artifact(_ruled_policy_document(public_jwk), HITL_POLICY)
    assert isinstance(policy, HitlPolicy)
    register_typed_at_composition(fabric.registry, POLICY_KEY, policy, HITL_POLICY)
    return InMemoryHitlTransport(
        control_plane=fabric.registry,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
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
        ApiDependencies(erasure_index=no_erasures(), erasure_trust=declared_erasure_trust(), 
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=enforcing_transport,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
            # Fixed, not a wall clock: the minted ``action_time`` is what the
            # window is judged against (`D-IMPL-363` E2), so the negatives are
            # exact rather than a race.
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
    response = _post(auth_app, tenant, _body(attestation=None))
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error_code"] == ERROR_SIGNED_BINDING_REQUIRED
    assert "message" in detail  # code + prose, never prose-only
    assert enforcing_transport.submissions(tenant=tenant) == ()


# --- Test 2: HTTP, invalid signature → ERROR_SIGNED_BINDING_INVALID --------


def test_http_an_invalid_attestation_carries_the_invalid_code(
    auth_app: Any,
    enforcing_transport: InMemoryHitlTransport,
    provider: DetachedJwsIdentityProvider,
) -> None:
    """A presented attestation whose signature does not verify under the keys
    the policy declares for its subject maps to the shared INVALID code —
    the same door property the signed-binding leg pinned, now over
    :class:`SignedHitlAction`."""
    from ccf_runtime.http_api.errors import ERROR_SIGNED_BINDING_INVALID

    tenant = _tenant("invalid")
    signed = _attest(_claims(tenant=tenant), provider=provider)
    tampered = signed.model_copy(update={"signature": signed.signature[:-4] + "AAAA"})
    response = _post(auth_app, tenant, _body(attestation=tampered))
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == ERROR_SIGNED_BINDING_INVALID
    assert enforcing_transport.submissions(tenant=tenant) == ()


# --- Test 3: HTTP, valid attestation → admitted; attestation + binding recorded ---


def test_http_a_valid_attestation_is_admitted_and_the_door_minted_binding_is_recorded(
    auth_app: Any,
    enforcing_transport: InMemoryHitlTransport,
    provider: DetachedJwsIdentityProvider,
) -> None:
    """The admitted leg, and the two separated statements `D-IMPL-363` leaves:
    the signer's attestation is recorded verbatim, and the recorded binding is
    EXACTLY the one the door mints — subject from the capability, claims from
    the verified grant, instant from the injected clock. Had the door read any
    binding field from the body, or a wall clock, the independently computed
    expectation would not hold."""
    tenant = _tenant("admitted")
    signed = _attest(_claims(tenant=tenant), provider=provider)
    response = _post(auth_app, tenant, _body(attestation=signed))
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["status"] == "submitted"
    assert receipt["submission"]["attestation"] == signed.model_dump(mode="json")
    (recorded,) = enforcing_transport.submissions(tenant=tenant)
    assert recorded.attestation == signed
    assert recorded.principal == _minted_binding()
    # The admitting policy is stamped on the record (E3): a replay resolves the
    # window and the key map it was admitted under, not today's.
    assert recorded.hitl_policy_ref is not None
    assert recorded.hitl_policy_ref.startswith(f"{POLICY_KEY}@")


# --- Test 3b: a client cannot state the assurance the door records ----------


def test_http_a_client_cannot_state_assurance_in_the_claims_or_the_body(
    auth_app: Any,
    enforcing_transport: InMemoryHitlTransport,
    provider: DetachedJwsIdentityProvider,
) -> None:
    """The successor to the assurance-upgrade control, on the new mechanism.

    Under P6 a signer signed the whole minted binding, so the control was
    "a signature over a higher assurance than the verifier stated is invalid".
    Under `D-IMPL-363` the assurance level is not a member of
    :class:`HitlActionClaims` at all, and the contract is ``extra=forbid``, so
    the stronger property holds: an attestation that states an assurance is a
    MALFORMED attestation refused at the body boundary — never a verification
    question — and so is a body that states one. The old property survives as
    the closing leg: the recorded assurance is the TOKEN's, whatever the client
    sends."""
    tenant = _tenant("upgraded")
    signed = _attest(_claims(tenant=tenant), provider=provider)

    # (a) inside the signed claims: `HitlActionClaims` has no such member.
    assert "assurance_level" not in HitlActionClaims.model_fields
    smuggled = signed.model_dump(mode="json")
    smuggled["claims"]["assurance_level"] = "aal3"
    refused = _post(auth_app, tenant, {**_body(attestation=None), "attestation": smuggled})
    assert refused.status_code == 422, refused.text
    assert any(
        error["type"] == "extra_forbidden" and error["loc"][-1] == "assurance_level"
        for error in refused.json()["detail"]
    ), refused.text
    assert enforcing_transport.submissions(tenant=tenant) == ()

    # (b) on the body itself: `HitlActionRequest` is `extra=forbid` too.
    on_the_body = _post(
        auth_app, tenant, {**_body(attestation=signed), "assurance_level": "aal3"}
    )
    assert on_the_body.status_code == 422, on_the_body.text
    assert any(
        error["type"] == "extra_forbidden" and error["loc"] == ["body", "assurance_level"]
        for error in on_the_body.json()["detail"]
    ), on_the_body.text
    assert enforcing_transport.submissions(tenant=tenant) == ()

    # (c) the recorded assurance is the token's, and the door-minted binding is
    # not the raised one a client would have wanted.
    admitted = _post(auth_app, tenant, _body(attestation=signed))
    assert admitted.status_code == 200, admitted.text
    (recorded,) = enforcing_transport.submissions(tenant=tenant)
    assert recorded.principal.authentication.assurance_level == _CLAIMS.assurance_level
    assert recorded.principal == _minted_binding()
    assert recorded.principal != _minted_binding(assurance_level="aal3")


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
        "event_key": _EVENT_KEY,
        "action": "approve",
        "product_content_hash": _VALID_HASH,
    }
    arguments.update(overrides)
    return arguments


def test_mcp_door_returns_the_same_typed_error_codes(
    monkeypatch: pytest.MonkeyPatch,
    fabric: Fabric,
    enforcing_transport: InMemoryHitlTransport,
    provider: DetachedJwsIdentityProvider,
) -> None:
    """MCP parity: EVERY refusal case carries the shared constant the HTTP door
    carries — absence, invalidity, and (new under `D-IMPL-363` E6) mismatch and
    staleness. One source of truth for the code, machine-attributable at both
    doors (T-08-07b)."""
    import ccf_runtime.mcp.hitl_server as hitl_server
    import ccf_runtime.mcp.tenancy as tenancy
    from mcp.server.auth.provider import AccessToken

    from ccf.authz.capability import Authorized, HitlSubmit
    from ccf.hitl.principal import AUTHENTICATION_CLAIM
    from ccf.hitl.transport import HitlActionSubmission
    from ccf_runtime.http_api.errors import (
        ERROR_SIGNED_BINDING_INVALID,
        ERROR_SIGNED_BINDING_MISMATCH,
        ERROR_SIGNED_BINDING_REQUIRED,
        ERROR_SIGNED_BINDING_STALE,
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

    def _code(**overrides: Any) -> str:
        with pytest.raises(ValueError) as refused:
            tool(**_mcp_arguments(**overrides))
        payload: str = json.loads(str(refused.value))["error_code"]
        return payload

    # absent
    assert _code() == ERROR_SIGNED_BINDING_REQUIRED
    # presented and does not verify
    broken = _attest(_claims(tenant=tenant), provider=provider).model_dump(mode="json")
    broken["signature"] = "not-a..real-signature"
    assert _code(attestation=broken) == ERROR_SIGNED_BINDING_INVALID
    # malformed: an assurance smuggled into the claims. `HitlActionClaims` is
    # `extra=forbid`, so this door refuses it at `SignedHitlAction` validation
    # rather than at verification — the MCP half of the assurance control
    # above. The two doors refuse with DIFFERENT codes by construction (the
    # HTTP body boundary answers 422; this one carries the shared INVALID
    # constant), which is why both halves are pinned rather than assumed.
    smuggled = _attest(_claims(tenant=tenant), provider=provider).model_dump(mode="json")
    smuggled["claims"]["assurance_level"] = "aal3"
    assert _code(attestation=smuggled) == ERROR_SIGNED_BINDING_INVALID
    # verifies, but the signed event is not the one presented (E6)
    elsewhere = _attest(
        _claims(tenant=tenant, event_key="door-event-elsewhere"), provider=provider
    )
    assert (
        _code(attestation=elsewhere.model_dump(mode="json"))
        == ERROR_SIGNED_BINDING_MISMATCH
    )
    # verifies and matches, but issued one second past the pinned max age (E3)
    expired = _attest(
        _claims(
            tenant=tenant,
            issued_at=_CLOCK_TIME - timedelta(seconds=MAX_AGE_SECONDS + 1),
        ),
        provider=provider,
    )
    assert (
        _code(attestation=expired.model_dump(mode="json"))
        == ERROR_SIGNED_BINDING_STALE
    )

    assert enforcing_transport.submissions(tenant=tenant) == ()
