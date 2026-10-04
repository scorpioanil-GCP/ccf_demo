"""SEC-005, the remaining leg — the signed-claims / time-window repair at the HTTP door (`D-IMPL-363`).

RED-FIRST. These tests state the design's §9 item 9 at the HTTP door as `D-IMPL-363`
ruled it (C1(a), C4(a), C6(a), C11(a), C12(a), C13(a)) and are committed before any
production change. They are written so that NOTHING fails at import, collection or
fixture setup: every ruled-but-absent surface is reached inside a test body, by
plain dicts on the wire and the existing signing primitive, and asserted on there —
so each red is a door or contract behavior, never a missing name.

The attestation on the wire (ruled E1(B), C12(a)): one object,
``{"claims": {...}, "signature": "<protected>..<signature>", "key_id": "<kid>"}``,
where the signature is the detached compact JWS over ``canonical_bytes(claims)``
made by the D-IMPL-15 provider — the same primitive that signs a Context Product.

The recorded limit this phase exists to close: today the only signed form is the
door-minted ``HumanPrincipalBinding``, ``action_time`` included, so a signer must
predict the door's clock reading; under a wall clock it cannot
(``docs/surface-changes/353-06-the-approval-record-is-server-attested.md``).

Fixture vocabulary is deployment vocabulary (CINV-01), following
``tests/http_api/test_signed_binding_door.py``.
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
from ccf.controlplane.artifacts import ArtifactLoadError, parse_artifact
from ccf.hitl.principal import AuthenticationClaims
from ccf.hitl.transport import HITL_POLICY, HitlPolicy, InMemoryHitlTransport
from ccf.peering.identity import DetachedJwsIdentityProvider, FileBackedKeySource, JsonWebKey
from ccf_runtime.mcp.auth import StaticTokenSource, TokenGrant

from .conftest import Fabric, call
from http_api.composition_authority import register_typed_at_composition

# Deployment vocabulary for this suite (CINV-01), restated rather than imported
# from the signed-binding door suite so the two modules do not share a fate.
APPROVER_KID = "attestation-approver-signing-key"
_VALID_HASH = "c" * 64
_CLIENT_ID = "attestation-auditor-1"
_TENANT_BASE = "attestation-door-tenant"
_SCOPE = "gate:everything"
_TENANTS = ("required", "invalid", "admitted", "upgraded", "mcp")
_CLAIMS = AuthenticationClaims(
    identity_provider_ref="idp://acme-bank/dev-token-file",
    method="bearer-token",
    assurance_level="dev",
    session_ref="attestation-session-1",
)


def _tenant(suffix: str) -> str:
    return f"{_TENANT_BASE}-{suffix}"


def _token_for(tenant: str) -> str:
    return f"attestation-token-{tenant.rsplit('-', 1)[-1]}"


def _grants() -> dict[str, TokenGrant]:
    return {
        _token_for(_tenant(suffix)): TokenGrant(
            client_id=_CLIENT_ID, scopes=(_SCOPE,), tenants=frozenset({_tenant(suffix)}), authentication=_CLAIMS
        )
        for suffix in _TENANTS
    }


@pytest.fixture(scope="module")
def key_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("attestation-keys")
    key = ECKey.generate_key("P-256", parameters={"kid": APPROVER_KID})
    (directory / f"{APPROVER_KID}.jwk").write_text(json.dumps(key.as_dict(private=True)), encoding="utf-8")
    return directory


@pytest.fixture(scope="module")
def provider(key_dir: Path) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(key_source=FileBackedKeySource(directory=key_dir))

POLICY_KEY = "acme-bank/hitl/attestation-policy"
OTHER_SUBJECT = "door-auditor-2"
OTHER_KID = "door-other-subject-signing-key"
#: Window values are deployment vocabulary chosen by this test-as-deployment.
MAX_AGE_SECONDS = 300
SKEW_SECONDS = 60
#: The two codes `D-IMPL-363` C4(a) / E6 rule, as literals so this module imports
#: nothing that does not exist yet.
CODE_MISMATCH = "signed-binding-mismatch"
CODE_STALE = "signed-binding-stale"
#: The injected door clock the window and skew negatives are judged against — a
#: fixed instant, so a slow run cannot slide a post-dated or expired claim into
#: the window. The positives keep a REAL wall clock on purpose.
FIXED_CLOCK = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


# --- the ruled policy document, and the fixture that registers the widest policy the tree accepts ---


def _public_jwk(key_dir: Path, kid: str) -> JsonWebKey:
    private = json.loads((key_dir / f"{kid}.jwk").read_text(encoding="utf-8"))
    return ECKey.import_key(private).as_dict(private=False)


@pytest.fixture(scope="module")
def other_key_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A second signing key, declared in the policy for a DIFFERENT subject."""
    directory = tmp_path_factory.mktemp("attestation-other-keys")
    key = ECKey.generate_key("P-256", parameters={"kid": OTHER_KID})
    (directory / f"{OTHER_KID}.jwk").write_text(json.dumps(key.as_dict(private=True)), encoding="utf-8")
    return directory


@pytest.fixture(scope="module")
def other_provider(other_key_dir: Path) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(key_source=FileBackedKeySource(directory=other_key_dir))


def _ruled_policy_document(key_dir: Path, other_key_dir: Path) -> dict[str, Any]:
    """The `HitlPolicy` `D-IMPL-363` rules (E3, E5, C6(a)): the window, and the
    per-subject trusted keys INSIDE the pinned policy."""
    return {
        "semver": "1.0.0",
        "signed_binding_required": True,
        "signature_max_age_seconds": MAX_AGE_SECONDS,
        "permitted_clock_skew_seconds": SKEW_SECONDS,
        "trusted_keys": {
            _CLIENT_ID: {APPROVER_KID: _public_jwk(key_dir, APPROVER_KID)},
            OTHER_SUBJECT: {OTHER_KID: _public_jwk(other_key_dir, OTHER_KID)},
        },
    }


def _todays_policy_document() -> dict[str, Any]:
    return {"semver": "1.0.0", "signed_binding_required": True}


@pytest.fixture()
def attesting_transport(
    fabric: Fabric,
    key_dir: Path,
    other_key_dir: Path,
    provider: DetachedJwsIdentityProvider,
) -> InMemoryHitlTransport:
    """A fresh transport bound to the RULED policy: the window and the per-subject
    keys live in the pinned policy and nowhere else (E3, E5, C6(a)) — there is no
    deployment-wide ``trusted_keys`` argument any more."""
    policy = parse_artifact(_ruled_policy_document(key_dir, other_key_dir), HITL_POLICY)
    assert isinstance(policy, HitlPolicy)
    register_typed_at_composition(fabric.registry, POLICY_KEY, policy, HITL_POLICY)
    return InMemoryHitlTransport(
        control_plane=fabric.registry,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
    )


def _build_app(fabric: Fabric, transport: InMemoryHitlTransport, tmp_path: Path, clock: Callable[[], datetime]) -> Any:
    """The HTTP app over the attesting transport, with the given door clock."""
    from ccf.projection.plan import Perspective
    from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.auth import BearerTokenAuth
    from ccf_runtime.http_api.dependencies import ApiDependencies

    from .gate_fixtures import authority
    from .test_product_declared_obligation_409 import _entitlement_registry, _recorder

    source = ControlPlaneProductEntitlementSource(
        control_plane=_entitlement_registry(fabric),
        clock=lambda: datetime(2026, 8, 11, tzinfo=UTC),
    )
    seams = authority(
        tenant=tuple(_tenant(suffix) for suffix in _TENANTS),
        key="attestation/mapping",
        grants={"unused": (_CLIENT_ID, (_SCOPE,), _tenant("required"))},
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(principal_id=grant.client_id, role="attestation-role")
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
            hitl_transport=transport,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
            clock=clock,
        ),
        **seams,
    )


@pytest.fixture()
def wall_clock_app(fabric: Fabric, attesting_transport: InMemoryHitlTransport, tmp_path: Path) -> Any:
    """A REAL wall clock at the door — the posture the 353-06 limit says the signed
    leg cannot work under. Used by the positives and by the negatives whose outcome
    does not depend on the instant."""
    return _build_app(fabric, attesting_transport, tmp_path, lambda: datetime.now(UTC))


@pytest.fixture()
def fixed_clock_app(fabric: Fabric, attesting_transport: InMemoryHitlTransport, tmp_path: Path) -> Any:
    """A deterministic door clock for the window and skew negatives, so that the
    margin past `max_age` / `skew` is exact rather than a race against execution."""
    return _build_app(fabric, attesting_transport, tmp_path, lambda: FIXED_CLOCK)


# --- the attestation on the wire ---


def _canonical_instant(instant: datetime) -> str:
    """The instant as the SDK's canonical serializer renders a datetime —
    microseconds and a ``Z`` — so a wire client's signed bytes are the bytes the
    verifier recomputes from the typed claims (one serialization in play)."""
    return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _claims(
    *,
    tenant: str,
    event_key: str = "attestation-event-1",
    action: str = "approve",
    product_content_hash: str = _VALID_HASH,
    subject_id: str = _CLIENT_ID,
    issued_at: datetime | None = None,
    nonce: str = "nonce-0001",
) -> dict[str, Any]:
    return {
        "tenant": tenant,
        "event_key": event_key,
        "action": action,
        "product_content_hash": product_content_hash,
        "subject_id": subject_id,
        "issued_at": _canonical_instant(issued_at or datetime.now(UTC)),
        "nonce": nonce,
    }


def _attest(claims: dict[str, Any], *, provider: DetachedJwsIdentityProvider, key_id: str) -> dict[str, Any]:
    """Sign the claims with the existing D-IMPL-15 primitive: a detached compact JWS
    over ``canonical_bytes(claims)``."""
    envelope = provider.sign(product=claims, key_id=key_id)
    return {"claims": claims, "signature": f"{envelope.protected}..{envelope.signature}", "key_id": key_id}


def _body(claims: dict[str, Any], attestation: dict[str, Any], *, action: str | None = None) -> dict[str, Any]:
    return {
        "event_key": claims["event_key"],
        "action": claims["action"] if action is None else action,
        "product_content_hash": claims["product_content_hash"],
        "annotation": None,
        "attestation": attestation,
    }


def _post(app: Any, tenant: str, body: dict[str, Any]) -> Any:
    return call(app, "POST", "/hitl/actions", json=body, headers={"Authorization": f"Bearer {_token_for(tenant)}"})


def _assert_refused(response: Any, transport: InMemoryHitlTransport, tenant: str, *, code: str) -> None:
    assert response.status_code == 403, (
        f"expected a 403 {code!r} refusal; got HTTP {response.status_code}: {response.text[:300]}"
    )
    detail = response.json()["detail"]
    assert detail["error_code"] == code, detail
    assert transport.submissions(tenant=tenant) == ()


# --- the contract: the policy carries the window and the per-subject keys (E3, E5) ---


def test_the_hitl_policy_carries_the_window_and_the_per_subject_keys(key_dir: Path, other_key_dir: Path) -> None:
    """`D-IMPL-363` E3 / E5 / C6(a): `signature_max_age_seconds`,
    `permitted_clock_skew_seconds` and the per-subject `trusted_keys` live INSIDE the
    pinned `HitlPolicy`."""
    document = _ruled_policy_document(key_dir, other_key_dir)
    try:
        policy = parse_artifact(document, HITL_POLICY)
    except ArtifactLoadError as error:
        pytest.fail(f"HitlPolicy refuses the ruled window and per-subject keys (D-IMPL-363 E3/E5): {error}")
    assert isinstance(policy, HitlPolicy)
    assert policy.signed_binding_required is True


def test_a_required_signed_policy_without_a_window_is_refused_at_parse() -> None:
    """E3: the window fields are REQUIRED whenever `signed_binding_required` is
    true; no SDK default (CINV-01) — a required policy without them is refused,
    never admitted with an invented window."""
    with pytest.raises(ArtifactLoadError):
        parse_artifact(_todays_policy_document(), HITL_POLICY)


# --- the positive: a signed submission succeeds under a WALL CLOCK (§9 item 9's closing clause) ---


def test_http_a_signed_submission_succeeds_under_a_wall_clock(
    wall_clock_app: Any, attesting_transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    """The 353-06 limit, closed: the signer states its OWN instant (`issued_at`) and
    a fresh nonce; the door mints `action_time` from its wall clock; the verifier
    compares the two within the pinned window and reads no clock of its own. Today
    the only signed form is the door-minted binding and this cannot pass."""
    tenant = _tenant("admitted")
    claims = _claims(tenant=tenant)
    attestation = _attest(claims, provider=provider, key_id=APPROVER_KID)
    response = _post(wall_clock_app, tenant, _body(claims, attestation))
    assert response.status_code == 200, (
        f"a signed submission under a wall clock must be admitted; got HTTP {response.status_code}: {response.text[:300]}"
    )
    receipt = response.json()
    assert receipt["status"] == "submitted"
    assert receipt["submission"]["attestation"] == attestation
    (recorded,) = attesting_transport.submissions(tenant=tenant)
    minted = recorded.principal.action_time
    assert minted.tzinfo is not None
    assert abs((datetime.now(UTC) - minted).total_seconds()) < MAX_AGE_SECONDS  # the door's reading, not the signer's
    assert receipt["submission"]["hitl_policy_ref"], "the submission records the admitting policy (E3)"


# --- the negatives, one per clause of §9 item 9 ---


def test_http_an_attestation_for_another_event_key_is_refused_mismatch(
    wall_clock_app: Any, attesting_transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    tenant = _tenant("required")
    claims = _claims(tenant=tenant, event_key="attestation-event-A")
    attestation = _attest(claims, provider=provider, key_id=APPROVER_KID)
    body = _body(claims, attestation)
    body["event_key"] = "attestation-event-B"  # presented on another event
    _assert_refused(_post(wall_clock_app, tenant, body), attesting_transport, tenant, code=CODE_MISMATCH)


def test_http_an_attestation_for_another_tenant_is_refused_mismatch(
    wall_clock_app: Any, attesting_transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    presented_in = _tenant("invalid")
    claims = _claims(tenant=_tenant("upgraded"))  # signed for a different tenant
    attestation = _attest(claims, provider=provider, key_id=APPROVER_KID)
    _assert_refused(_post(wall_clock_app, presented_in, _body(claims, attestation)), attesting_transport, presented_in, code=CODE_MISMATCH)


def test_http_an_attestation_signed_for_the_opposite_verdict_is_refused_mismatch(
    wall_clock_app: Any, attesting_transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    """C1(a) / C4(a): the signed `action` is `reject`; the presentation says `approve`."""
    tenant = _tenant("mcp")
    claims = _claims(tenant=tenant, action="reject")
    attestation = _attest(claims, provider=provider, key_id=APPROVER_KID)
    _assert_refused(_post(wall_clock_app, tenant, _body(claims, attestation, action="approve")), attesting_transport, tenant, code=CODE_MISMATCH)


def test_http_an_attestation_issued_past_the_window_is_refused_stale(
    fixed_clock_app: Any, attesting_transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    """Judged against the RECORDED door instant (E2): `action_time − issued_at` is
    one second over `max_age`, exactly, because the door clock is fixed."""
    tenant = _tenant("required")
    claims = _claims(tenant=tenant, issued_at=FIXED_CLOCK - timedelta(seconds=MAX_AGE_SECONDS + 1))
    attestation = _attest(claims, provider=provider, key_id=APPROVER_KID)
    _assert_refused(_post(fixed_clock_app, tenant, _body(claims, attestation)), attesting_transport, tenant, code=CODE_STALE)


def test_http_an_attestation_post_dated_beyond_the_skew_is_refused_stale(
    fixed_clock_app: Any, attesting_transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    """E3 is DIRECTIONAL: a claim issued after the door recorded the action, beyond
    the permitted skew, is refused — an absolute delta would admit it."""
    tenant = _tenant("invalid")
    claims = _claims(tenant=tenant, issued_at=FIXED_CLOCK + timedelta(seconds=SKEW_SECONDS + 1))
    attestation = _attest(claims, provider=provider, key_id=APPROVER_KID)
    _assert_refused(_post(fixed_clock_app, tenant, _body(claims, attestation)), attesting_transport, tenant, code=CODE_STALE)


def test_http_a_reused_nonce_is_refused_stale(
    wall_clock_app: Any, attesting_transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    """C11(a): the transport rejects reuse ATOMICALLY — the first presentation is
    admitted; the identical second one refuses and records nothing more."""
    tenant = _tenant("upgraded")
    claims = _claims(tenant=tenant, nonce="nonce-once")
    attestation = _attest(claims, provider=provider, key_id=APPROVER_KID)
    first = _post(wall_clock_app, tenant, _body(claims, attestation))
    assert first.status_code == 200, f"the first presentation must be admitted; got {first.status_code}: {first.text[:300]}"
    second = _post(wall_clock_app, tenant, _body(claims, attestation))
    assert second.status_code == 403, f"the reused nonce must be refused; got {second.status_code}: {second.text[:300]}"
    assert second.json()["detail"]["error_code"] == CODE_STALE
    assert len(attesting_transport.submissions(tenant=tenant)) == 1


def test_http_a_nonce_presented_concurrently_is_admitted_exactly_once(
    wall_clock_app: Any, attesting_transport: InMemoryHitlTransport, provider: DetachedJwsIdentityProvider
) -> None:
    """C11(a) is ATOMIC, not merely sequential: N identical presentations racing
    through the door admit exactly one; every other refuses `-stale`; one is
    recorded. A check-and-insert that is not one step under the lock admits two."""
    tenant = _tenant("admitted")
    claims = _claims(tenant=tenant, nonce="nonce-raced")
    attestation = _attest(claims, provider=provider, key_id=APPROVER_KID)
    body = _body(claims, attestation)
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: _post(wall_clock_app, tenant, body), range(8)))
    statuses = sorted(response.status_code for response in responses)
    assert statuses.count(200) == 1, f"exactly one presentation may be admitted; statuses={statuses}"
    assert all(code == 403 for code in statuses if code != 200), statuses
    assert all(
        response.json()["detail"]["error_code"] == CODE_STALE for response in responses if response.status_code == 403
    )
    assert len(attesting_transport.submissions(tenant=tenant)) == 1


def test_http_a_key_not_declared_for_the_subject_is_refused_mismatch(
    wall_clock_app: Any,
    attesting_transport: InMemoryHitlTransport,
    other_provider: DetachedJwsIdentityProvider,
) -> None:
    """E5 / C6(a): the key is trusted — for ANOTHER subject. A `kid` not declared for
    `claims.subject_id` in the pinned policy binds nothing."""
    tenant = _tenant("admitted")
    claims = _claims(tenant=tenant)  # subject_id is _CLIENT_ID
    attestation = _attest(claims, provider=other_provider, key_id=OTHER_KID)  # declared for OTHER_SUBJECT only
    _assert_refused(_post(wall_clock_app, tenant, _body(claims, attestation)), attesting_transport, tenant, code=CODE_MISMATCH)
