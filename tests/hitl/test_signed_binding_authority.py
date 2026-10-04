"""D-16 — attestation requiredness and the shared verifier at the HITL authority path.

08-03 Task 1 (TDD RED), as `D-IMPL-363` (SEC-005, the remaining leg) reshaped
it. When the Control Plane HITL policy in force declares
``signed_binding_required: true``, an unsigned submission at the authority
seam (:meth:`ccf.hitl.transport.InMemoryHitlTransport.submit`) is a typed
refusal — one exception class for attestation-absent-but-required, one for
a signature that does not verify, one for a signed claim that does not match
the capability/request/binding, and one for a claim outside the freshness
window — so the doors can map each to its own ``ERROR_SIGNED_BINDING_*``
constant.

**What is signed changed under `D-IMPL-363`.** The signer no longer signs the
door-minted :class:`~ccf.hitl.principal.HumanPrincipalBinding` (whose
``action_time`` it would have to predict) but its own
:class:`~ccf.hitl.identity_binding.HitlActionClaims`, carried as the
submission's ``attestation``. The shared verifier,
:func:`~ccf.hitl.transport.enforce_attestation`, compares every claim to the
capability, the request and the minted binding, and windows the signer's
``issued_at`` against the RECORDED ``action_time`` — **it reads no clock**.
That is why every window case below fixes ``action_time`` and states
``issued_at`` relative to it: nothing here races a wall clock.

Requiredness is a Control Plane value, never a code constant
(No-Hardcoding, CLAUDE.md §6.4): the ``HitlPolicy`` artifact contract
carries a schema-validated ``signed_binding_required`` boolean defaulting
to false when the key is absent from the document (Ollama C3 — no KeyError
path), and flipping the registered value flips transport behavior with
zero code change. Under `D-IMPL-363` E3/E5 a policy that declares it *true*
must also state the window and the per-subject trusted keys, and is refused
at parse otherwise — there is no SDK default and no constructor fallback
(CINV-01).

Designed within the D-IMPL-21/63/67 contract envelope; signing machinery
is the D-IMPL-21 reference impl #2 (:mod:`ccf.hitl.identity_binding`) —
never hand-rolled crypto (T-08-05).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from joserfc.jwk import ECKey

from ccf.authz.capability import Authorized, HitlSubmit
from ccf.controlplane.artifacts import ArtifactLoadError, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.identity_binding import (
    AttestationInvalid,
    HitlActionClaims,
    SignedHitlAction,
    sign_hitl_action,
    verify_hitl_action,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import (
    HITL_POLICY,
    HitlActionSubmission,
    HitlPolicy,
    InMemoryHitlTransport,
    SignedBindingInvalidRefused,
    SignedBindingMismatchRefused,
    SignedBindingRequiredRefused,
    SignedBindingStaleRefused,
    enforce_attestation,
    resolve_hitl_policy,
    signed_binding_required,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
)
from tests.controlplane.composition import compose_register, compose_register_typed

APPROVER_KID = "hitl-approver-signing-key"
#: A second key, declared in the policy for a DIFFERENT subject — so a key
#: trusted for one approver can be shown signing for no other (E5 / C6(a)).
OTHER_KID = "hitl-other-subject-signing-key"

#: Deployment vocabulary chosen by this test-as-deployment (CINV-01): the
#: Control Plane key the composition root binds its HITL policy under.
POLICY_KEY = "acme-bank/hitl/policy"

#: The window this test-as-deployment states (CINV-01 — no SDK default).
MAX_AGE_SECONDS = 300
SKEW_SECONDS = 60

from .capabilities import submit_capability

_TENANT = "acme-bank"
_SUBJECT = "approver-1"
_OTHER_SUBJECT = "approver-2"
_EVENT_KEY = "event-1"

#: The door-minted instant every binding below records. FIXED: the verifier
#: windows ``issued_at`` against THIS value and reads no clock of its own, so
#: every freshness case is exact rather than a race against execution (C7).
ACTION_TIME = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)

_PRODUCT_HASH = hashlib.sha256(b"fixture-product").hexdigest()


def _write_key(directory: Path, key_id: str) -> ECKey:
    key = ECKey.generate_key("P-256", parameters={"kid": key_id})
    (directory / f"{key_id}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return key


def _binding(
    subject_id: str = _SUBJECT,
    *,
    verdict: str = "approve",
    product_content_hash: str = _PRODUCT_HASH,
    action_time: datetime = ACTION_TIME,
) -> HumanPrincipalBinding:
    return HumanPrincipalBinding(
        verdict=verdict,
        approver=ApproverIdentity(
            subject_id=subject_id,
            identity_provider_ref="test-idp",
        ),
        authentication=AuthenticationContext(
            method="test-method",
            assurance_level="test-level",
            session_ref="test-session",
        ),
        action_time=action_time,
        product_content_hash=product_content_hash,
    )


def _claims(
    *,
    tenant: str = _TENANT,
    event_key: str = _EVENT_KEY,
    action: str = "approve",
    product_content_hash: str = _PRODUCT_HASH,
    subject_id: str = _SUBJECT,
    issued_at: datetime = ACTION_TIME,
    nonce: str = "nonce-authority-0001",
) -> HitlActionClaims:
    """The claim set a signer states from the served queue view plus its own
    decision, identity, instant and nonce (E1). ``issued_at`` defaults to the
    recorded door instant — dead centre of any window."""
    return HitlActionClaims(
        tenant=tenant,
        event_key=event_key,
        action=action,
        product_content_hash=product_content_hash,
        subject_id=subject_id,
        issued_at=issued_at,
        nonce=nonce,
    )


def _submission(
    principal: HumanPrincipalBinding,
    attestation: SignedHitlAction | None = None,
    *,
    action: str = "approve",
    event_key: str = _EVENT_KEY,
) -> HitlActionSubmission:
    return HitlActionSubmission(
        event_key=event_key,
        action=action,
        principal=principal,
        attestation=attestation,
    )


def _authorized(
    tenant: str, event_key: str, *, principal: str = _SUBJECT
) -> Authorized[HitlSubmit]:
    """The capability a submitter presents (D-IMPL-353 §1.2), minted for
    exactly this tenant, event and subject."""
    return submit_capability(
        tenant=tenant, principal=principal, event_key=event_key
    )


def _submit(
    transport: InMemoryHitlTransport,
    principal: HumanPrincipalBinding,
    attestation: SignedHitlAction | None = None,
) -> HitlActionSubmission:
    """Submit through the authority path under a capability minted for the
    binding's own subject — so what these tests exercise is the attestation
    leg, not the actor check."""
    return transport.submit(
        _authorized(_TENANT, _EVENT_KEY, principal=principal.approver.subject_id),
        submission=_submission(principal, attestation),
    )


@pytest.fixture
def key_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "keys"
    directory.mkdir()
    return directory


@pytest.fixture
def approver_key(key_dir: Path) -> ECKey:
    return _write_key(key_dir, APPROVER_KID)


@pytest.fixture
def other_key(key_dir: Path) -> ECKey:
    return _write_key(key_dir, OTHER_KID)


@pytest.fixture
def provider(key_dir: Path) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )


@pytest.fixture
def trusted_keys(
    approver_key: ECKey, other_key: ECKey
) -> dict[str, dict[str, JsonWebKey]]:
    """The ONE trust source (E5 / C6(a)): approver subject → ``kid`` → public
    JWK, carried INSIDE the pinned policy. ``OTHER_KID`` is declared for
    ``_OTHER_SUBJECT`` only, so it signs for nobody else."""
    return {
        _SUBJECT: {APPROVER_KID: approver_key.as_dict(private=False)},
        _OTHER_SUBJECT: {OTHER_KID: other_key.as_dict(private=False)},
    }


def _policy_document(
    *,
    required: bool,
    semver: str = "1.0.0",
    trusted_keys: dict[str, dict[str, JsonWebKey]] | None = None,
    max_age: int | None = MAX_AGE_SECONDS,
    skew: int | None = SKEW_SECONDS,
) -> dict[str, Any]:
    """The ruled policy document (E3, E5): a *required* policy states its
    window and its per-subject keys; a not-required one need not."""
    document: dict[str, Any] = {
        "semver": semver,
        "signed_binding_required": required,
    }
    if required:
        document["signature_max_age_seconds"] = max_age
        document["permitted_clock_skew_seconds"] = skew
        document["trusted_keys"] = trusted_keys or {}
    return document


def _policy(
    *,
    required: bool,
    semver: str = "1.0.0",
    trusted_keys: dict[str, dict[str, JsonWebKey]] | None = None,
) -> HitlPolicy:
    policy = parse_artifact(
        _policy_document(
            required=required, semver=semver, trusted_keys=trusted_keys
        ),
        HITL_POLICY,
    )
    assert isinstance(policy, HitlPolicy)
    return policy


@pytest.fixture
def plane() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


def _transport(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
) -> InMemoryHitlTransport:
    """The transport as `D-IMPL-363` E5 leaves it: no ``trusted_keys``
    argument — the keys are the pinned policy's and nowhere else."""
    return InMemoryHitlTransport(
        control_plane=plane,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
    )


def _attest(
    claims: HitlActionClaims,
    provider: DetachedJwsIdentityProvider,
    *,
    key_id: str = APPROVER_KID,
) -> SignedHitlAction:
    return sign_hitl_action(claims, provider=provider, key_id=key_id)


# --- Test 1: required + validly signed --------------------------------------


def test_required_and_validly_signed_submission_is_admitted(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    """A verified attestation whose claims match is admitted, attestation kept."""
    compose_register_typed(
        plane, POLICY_KEY, _policy(required=True, trusted_keys=trusted_keys), HITL_POLICY
    )
    transport = _transport(plane, provider)
    binding = _binding()
    attestation = _attest(_claims(), provider)
    _submit(transport, binding, attestation)
    recorded = transport.submissions(tenant=_TENANT)
    assert len(recorded) == 1
    # The attestation lands on the recorded (audited) submission itself.
    assert recorded[0].attestation == attestation
    # ... and so does the policy that admitted it (E3): the transport stamps
    # the pinned ``key@version`` the resolver returned, never the artifact's
    # own semver lane — the registry's version IS its content address.
    resolved = resolve_hitl_policy(
        control_plane=plane, hitl_policy_key=POLICY_KEY
    )
    assert resolved is not None
    assert recorded[0].hitl_policy_ref == f"{POLICY_KEY}@{resolved[0]}"


# --- Test 2: required + unsigned --------------------------------------------


def test_required_and_unsigned_submission_is_a_typed_refusal(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    compose_register_typed(
        plane, POLICY_KEY, _policy(required=True, trusted_keys=trusted_keys), HITL_POLICY
    )
    transport = _transport(plane, provider)
    with pytest.raises(SignedBindingRequiredRefused):
        _submit(transport, _binding(), None)
    assert transport.submissions(tenant=_TENANT) == ()


# --- Test 3: required + invalid signature / mismatched subject --------------


def test_required_and_invalid_or_mismatched_attestation_is_refused(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    compose_register_typed(
        plane, POLICY_KEY, _policy(required=True, trusted_keys=trusted_keys), HITL_POLICY
    )
    transport = _transport(plane, provider)
    binding = _binding()
    attestation = _attest(_claims(), provider)
    # (a) tampered signature — verification fails.
    tampered = attestation.model_copy(
        update={"signature": attestation.signature[:-4] + "AAAA"}
    )
    with pytest.raises(SignedBindingInvalidRefused):
        _submit(transport, binding, tampered)
    # (b) a VALID signature over a DIFFERENT subject than the submission's
    # (spoofing, T-08-06) — the subject comparison refuses it as a mismatch.
    other = _attest(
        _claims(subject_id=_OTHER_SUBJECT),
        provider,
        key_id=OTHER_KID,
    )
    with pytest.raises(SignedBindingMismatchRefused):
        _submit(transport, binding, other)
    assert transport.submissions(tenant=_TENANT) == ()


# --- Test 4: not required — behavior unchanged ------------------------------


def test_not_required_admits_unsigned_submissions_unchanged(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
) -> None:
    compose_register_typed(plane, POLICY_KEY, _policy(required=False), HITL_POLICY)
    transport = _transport(plane, provider)
    _submit(transport, _binding(), None)
    assert len(transport.submissions(tenant=_TENANT)) == 1
    # An entirely unconfigured transport (no Control Plane bound) is the
    # pre-08-03 posture and admits exactly as before.
    bare = InMemoryHitlTransport()
    _submit(bare, _binding(), None)
    assert len(bare.submissions(tenant=_TENANT)) == 1


# --- Test 5: requiredness source is the Control Plane, never code -----------


def test_requiredness_is_a_control_plane_value_not_a_code_constant(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    """Flipping the registered value flips behavior with zero code change."""
    compose_register_typed(plane, POLICY_KEY, _policy(required=False), HITL_POLICY)
    transport = _transport(plane, provider)
    _submit(transport, _binding(), None)
    assert len(transport.submissions(tenant=_TENANT)) == 1
    # Flip the Control Plane value — same transport object, no code change.
    compose_register_typed(
        plane,
        POLICY_KEY,
        _policy(required=True, semver="1.0.1", trusted_keys=trusted_keys),
        HITL_POLICY,
    )
    with pytest.raises(SignedBindingRequiredRefused):
        _submit(transport, _binding(), None)


def test_absent_key_in_the_policy_document_defaults_to_false() -> None:
    """A policy document without the key is well-defined — never a KeyError."""
    policy = parse_artifact({"semver": "1.0.0"}, HITL_POLICY)
    assert isinstance(policy, HitlPolicy)
    assert policy.signed_binding_required is False


def test_a_required_policy_without_its_window_or_keys_is_refused_at_parse(
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    """E3 / E5 / CINV-01: requiredness *true* obliges the policy to state the
    window AND the per-subject keys the verifier judges an attestation
    against. Each omission is refused at parse — never admitted under a
    window or a key map the deployment did not write."""
    for document in (
        # No window at all.
        {"semver": "1.0.0", "signed_binding_required": True},
        # Max age only.
        _policy_document(required=True, trusted_keys=trusted_keys, skew=None),
        # Skew only.
        _policy_document(required=True, trusted_keys=trusted_keys, max_age=None),
        # Window but no keys.
        {
            "semver": "1.0.0",
            "signed_binding_required": True,
            "signature_max_age_seconds": MAX_AGE_SECONDS,
            "permitted_clock_skew_seconds": SKEW_SECONDS,
        },
    ):
        with pytest.raises(ArtifactLoadError):
            parse_artifact(document, HITL_POLICY)


# --- 10-02 Task 1: module-level shared helpers (D-IMPL-69; D-13) ------------


def test_helper_signed_binding_required_unbound_is_false() -> None:
    """Unbound Control Plane or key is the pre-composition posture."""
    assert (
        signed_binding_required(control_plane=None, hitl_policy_key=None)
        is False
    )
    assert (
        signed_binding_required(
            control_plane=None, hitl_policy_key=POLICY_KEY
        )
        is False
    )
    # The policy resolver that backs it reports the same absence as ``None``,
    # rather than an invented policy (E3).
    assert (
        resolve_hitl_policy(control_plane=None, hitl_policy_key=POLICY_KEY)
        is None
    )


def test_helper_signed_binding_required_resolves_per_call(
    plane: ControlPlaneRegistry,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    compose_register_typed(plane, POLICY_KEY, _policy(required=False), HITL_POLICY)
    assert (
        signed_binding_required(
            control_plane=plane, hitl_policy_key=POLICY_KEY
        )
        is False
    )
    compose_register_typed(
        plane,
        POLICY_KEY,
        _policy(required=True, semver="1.0.1", trusted_keys=trusted_keys),
        HITL_POLICY,
    )
    assert (
        signed_binding_required(
            control_plane=plane, hitl_policy_key=POLICY_KEY
        )
        is True
    )


def test_helper_resolve_hitl_policy_returns_the_pinned_version_and_policy(
    plane: ControlPlaneRegistry,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    """E3: the resolver hands its callers the version AND the policy, so the
    recorded ``hitl_policy_ref`` names the window and the keys that decided
    an admission rather than whatever is registered at replay time."""
    compose_register_typed(
        plane,
        POLICY_KEY,
        _policy(required=True, semver="1.0.0", trusted_keys=trusted_keys),
        HITL_POLICY,
    )
    resolved = resolve_hitl_policy(
        control_plane=plane, hitl_policy_key=POLICY_KEY
    )
    assert resolved is not None
    version, policy = resolved
    # The registry's version is the artifact's content address, not its
    # semver lane — the pin a replay resolves EXACTLY (D-IMPL-26).
    assert re.fullmatch(r"[0-9a-f]{64}", version), version
    assert policy.semver == "1.0.0"
    assert policy.signature_max_age_seconds == MAX_AGE_SECONDS
    assert policy.permitted_clock_skew_seconds == SKEW_SECONDS
    assert set(policy.keys_for(_SUBJECT)) == {APPROVER_KID}
    assert set(policy.keys_for(_OTHER_SUBJECT)) == {OTHER_KID}
    assert policy.keys_for("nobody") == {}
    assert policy.pinned_ref(key=POLICY_KEY, version=version) == (
        f"{POLICY_KEY}@{version}"
    )


def test_helper_signed_binding_required_rejects_non_hitl_policy(
    plane: ControlPlaneRegistry,
) -> None:
    """A key naming a non-HitlPolicy artifact is a TypeError, not a refusal."""
    compose_register(plane, POLICY_KEY, {"not": "a-policy"})
    with pytest.raises(TypeError):
        signed_binding_required(
            control_plane=plane, hitl_policy_key=POLICY_KEY
        )
    with pytest.raises(TypeError):
        resolve_hitl_policy(control_plane=plane, hitl_policy_key=POLICY_KEY)


def test_helper_enforce_refuses_absent_attestation(
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    with pytest.raises(SignedBindingRequiredRefused):
        enforce_attestation(
            _authorized(_TENANT, _EVENT_KEY),
            _submission(_binding(), None),
            identity_provider=provider,
            policy=_policy(required=True, trusted_keys=trusted_keys),
        )


def test_helper_enforce_broken_wiring_is_a_runtime_error(
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    """Requiring attestations without verification machinery, or judging one
    against a policy that states no window, is broken wiring — a RuntimeError,
    never a governance refusal a door would map to a 403."""
    binding = _binding()
    attestation = _attest(_claims(), provider)
    submission = _submission(binding, attestation)
    authorized = _authorized(_TENANT, _EVENT_KEY)
    with pytest.raises(RuntimeError):
        enforce_attestation(
            authorized,
            submission,
            identity_provider=None,
            policy=_policy(required=True, trusted_keys=trusted_keys),
        )
    # A policy with no window cannot declare requiredness (refused at parse),
    # so reaching the verifier with one is wiring that bypassed the artifact.
    windowless = _policy(required=False)
    assert windowless.signature_max_age_seconds is None
    assert windowless.permitted_clock_skew_seconds is None
    with pytest.raises(RuntimeError):
        enforce_attestation(
            authorized,
            submission,
            identity_provider=provider,
            policy=windowless,
        )


def test_helper_enforce_refuses_invalid_or_mismatched_attestation(
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    policy = _policy(required=True, trusted_keys=trusted_keys)
    binding = _binding()
    authorized = _authorized(_TENANT, _EVENT_KEY)
    attestation = _attest(_claims(), provider)
    tampered = attestation.model_copy(
        update={"signature": attestation.signature[:-4] + "AAAA"}
    )
    with pytest.raises(SignedBindingInvalidRefused):
        enforce_attestation(
            authorized,
            _submission(binding, tampered),
            identity_provider=provider,
            policy=policy,
        )
    other = _attest(
        _claims(subject_id=_OTHER_SUBJECT), provider, key_id=OTHER_KID
    )
    with pytest.raises(SignedBindingMismatchRefused):
        enforce_attestation(
            authorized,
            _submission(binding, other),
            identity_provider=provider,
            policy=policy,
        )


def test_helper_enforce_admits_a_valid_attestation(
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    claims = _claims()
    verified = enforce_attestation(
        _authorized(_TENANT, _EVENT_KEY),
        _submission(_binding(), _attest(claims, provider)),
        identity_provider=provider,
        policy=_policy(required=True, trusted_keys=trusted_keys),
    )
    # The verifier RETURNS the verified claims — what the transport consumes
    # the nonce from, and what a replay re-verification compares.
    assert verified == claims


def test_no_boolean_constant_in_src_encodes_requiredness() -> None:
    """Grep-style assertion: no ``signed_binding_required = True`` in /src.

    The only admissible occurrence of the name in library code is the
    schema field declaration whose default is ``False`` (the well-defined
    absence value) — requiredness true can ONLY come from a registered
    Control Plane artifact (T-08-07).
    """
    src = Path(__file__).resolve().parents[2] / "src"
    pattern = re.compile(r"signed_binding_required\s*[:=]\s*True")
    offenders = [
        str(path)
        for path in src.rglob("*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


# --- design §9 item 9: one verifier-level negative per comparison ------------
#
# `D-IMPL-363` E6 enumerates exactly what :func:`enforce_attestation` holds a
# signed claim against. Each case below alters ONE of them, re-signs so the
# signature itself is genuine, and asserts the specific refusal class — so a
# comparison that is dropped from the verifier cannot be hidden by another
# comparison happening to fire. The window cases state ``issued_at``
# relative to the FIXED recorded ``action_time``; no clock is read, by the
# verifier or by this test.


@pytest.fixture
def ruled_policy(
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> HitlPolicy:
    return _policy(required=True, trusted_keys=trusted_keys)


def _enforce(
    claims: HitlActionClaims,
    provider: DetachedJwsIdentityProvider,
    policy: HitlPolicy,
    *,
    key_id: str = APPROVER_KID,
    binding: HumanPrincipalBinding | None = None,
    submission_action: str = "approve",
) -> HitlActionClaims:
    """Verify genuinely-signed ``claims`` against the capability, the request
    and the door-minted binding this module fixes."""
    principal = _binding() if binding is None else binding
    return enforce_attestation(
        _authorized(_TENANT, _EVENT_KEY),
        _submission(
            principal, _attest(claims, provider, key_id=key_id),
            action=submission_action,
        ),
        identity_provider=provider,
        policy=policy,
    )


def test_verifier_admits_the_unaltered_control_claims(
    provider: DetachedJwsIdentityProvider, ruled_policy: HitlPolicy
) -> None:
    """The positive control for every negative below: the SAME helper, the
    SAME default claim set, altered in nothing — admitted. Without this, a
    verifier that refused everything would make all eight negatives pass."""
    assert _enforce(_claims(), provider, ruled_policy) == _claims()


def test_verifier_refuses_an_attestation_for_another_tenant(
    provider: DetachedJwsIdentityProvider, ruled_policy: HitlPolicy
) -> None:
    """E6: ``claims.tenant`` must be the capability's tenant."""
    with pytest.raises(SignedBindingMismatchRefused, match="tenant"):
        _enforce(_claims(tenant="globex"), provider, ruled_policy)


def test_verifier_refuses_an_attestation_for_another_event_key(
    provider: DetachedJwsIdentityProvider, ruled_policy: HitlPolicy
) -> None:
    """E6: ``claims.event_key`` must be the capability's resource — a
    signature over one pending event does not authorize another."""
    with pytest.raises(SignedBindingMismatchRefused, match="event_key"):
        _enforce(_claims(event_key="event-2"), provider, ruled_policy)


def test_verifier_refuses_an_attestation_for_another_subject(
    provider: DetachedJwsIdentityProvider, ruled_policy: HitlPolicy
) -> None:
    """E6: ``claims.subject_id`` must be the capability's principal AND the
    minted binding's approver. The key here IS declared for that other
    subject, so the refusal is the subject comparison and not the key map."""
    with pytest.raises(SignedBindingMismatchRefused, match="subject_id"):
        _enforce(
            _claims(subject_id=_OTHER_SUBJECT),
            provider,
            ruled_policy,
            key_id=OTHER_KID,
        )


def test_verifier_refuses_an_attestation_whose_action_is_not_the_verdict(
    provider: DetachedJwsIdentityProvider, ruled_policy: HitlPolicy
) -> None:
    """E6 / C1(a): ``claims.action`` must equal the presented action AND the
    minted binding's ``verdict``. Both legs, because a signature that covered
    only one of them would let the other be swapped after signing."""
    # (a) the signed action disagrees with the action presented.
    with pytest.raises(SignedBindingMismatchRefused, match="action"):
        _enforce(_claims(action="reject"), provider, ruled_policy)
    # (b) the signed action agrees with the request but not with the verdict
    # the door recorded on the binding.
    with pytest.raises(SignedBindingMismatchRefused, match="action"):
        _enforce(
            _claims(action="approve"),
            provider,
            ruled_policy,
            binding=_binding(verdict="reject"),
        )


def test_verifier_refuses_an_attestation_over_another_product_hash(
    provider: DetachedJwsIdentityProvider, ruled_policy: HitlPolicy
) -> None:
    """E6: ``claims.product_content_hash`` must equal the minted binding's —
    a signature over what the human saw, not over something else."""
    other_hash = hashlib.sha256(b"a-different-product").hexdigest()
    with pytest.raises(
        SignedBindingMismatchRefused, match="product_content_hash"
    ):
        _enforce(
            _claims(product_content_hash=other_hash), provider, ruled_policy
        )


def test_verifier_refuses_a_key_not_declared_for_the_claims_subject(
    provider: DetachedJwsIdentityProvider, ruled_policy: HitlPolicy
) -> None:
    """E5 / C6(a): the ``key_id`` must be one the pinned policy declares for
    ``claims.subject_id``. ``OTHER_KID`` is declared — for somebody else — so
    this pins per-subject scoping rather than mere key existence."""
    with pytest.raises(SignedBindingMismatchRefused, match="not declared"):
        _enforce(_claims(), provider, ruled_policy, key_id=OTHER_KID)


ROTATION_KID = "hitl-approver-rotation-key"


def test_verifier_refuses_an_attestation_whose_key_id_is_not_the_signing_kid(
    key_dir: Path,
    provider: DetachedJwsIdentityProvider,
    approver_key: ECKey,
) -> None:
    """The protected header's ``kid`` must equal the presented ``key_id``.

    ``enforce_attestation`` judges the PRESENTED ``key_id`` against the pinned
    policy's per-subject map, while the provider verifies the signature under
    the key the PROTECTED HEADER names. ``verify_hitl_action`` is what ties the
    two together, and the close panel measured that nothing pinned it
    (`D-IMPL-363` CR-363-10): with the comparison removed, a holder of one of an
    approver's keys could sign with it and present another of that approver's
    keys as ``key_id`` — admitted, and recorded in dimension 2 under a key that
    did not make the signature. Two keys for ONE approver is the routine
    rotation shape, so both are declared for ``_SUBJECT`` here, and the
    mislabelled attestation must refuse while the honestly labelled one is
    admitted — so the refusal is the comparison's, not the key map's.
    """
    rotation_key = _write_key(key_dir, ROTATION_KID)
    policy = _policy(
        required=True,
        trusted_keys={
            _SUBJECT: {
                APPROVER_KID: approver_key.as_dict(private=False),
                ROTATION_KID: rotation_key.as_dict(private=False),
            }
        },
    )
    signed_with_rotation_key = _attest(_claims(), provider, key_id=ROTATION_KID)
    mislabelled = SignedHitlAction(
        claims=signed_with_rotation_key.claims,
        signature=signed_with_rotation_key.signature,
        key_id=APPROVER_KID,
    )
    # The verifier itself names the disagreement.
    with pytest.raises(AttestationInvalid, match="declares kid"):
        verify_hitl_action(
            mislabelled,
            provider=provider,
            public_keys=policy.keys_for(_SUBJECT),
        )
    # And the shared verifier refuses it as an invalid attestation, before any
    # claim is compared.
    with pytest.raises(SignedBindingInvalidRefused):
        enforce_attestation(
            _authorized(_TENANT, _EVENT_KEY),
            _submission(_binding(), mislabelled, action="approve"),
            identity_provider=provider,
            policy=policy,
        )
    # Positive control: the same signature, honestly labelled, is admitted —
    # the rotation key IS declared for the approver.
    admitted = enforce_attestation(
        _authorized(_TENANT, _EVENT_KEY),
        _submission(_binding(), signed_with_rotation_key, action="approve"),
        identity_provider=provider,
        policy=policy,
    )
    assert admitted == _claims()


def test_verifier_refuses_an_expired_attestation(
    provider: DetachedJwsIdentityProvider, ruled_policy: HitlPolicy
) -> None:
    """E3: ``action_time − issued_at`` beyond ``signature_max_age_seconds``
    is stale. Judged against the FIXED recorded instant — one second inside
    the window is admitted, one second past it is refused."""
    inside = _enforce(
        _claims(issued_at=ACTION_TIME - timedelta(seconds=MAX_AGE_SECONDS)),
        provider,
        ruled_policy,
    )
    assert inside.issued_at == ACTION_TIME - timedelta(seconds=MAX_AGE_SECONDS)
    with pytest.raises(SignedBindingStaleRefused, match="expired"):
        _enforce(
            _claims(
                issued_at=ACTION_TIME
                - timedelta(seconds=MAX_AGE_SECONDS + 1)
            ),
            provider,
            ruled_policy,
        )


def test_verifier_refuses_a_post_dated_attestation(
    provider: DetachedJwsIdentityProvider, ruled_policy: HitlPolicy
) -> None:
    """E3: the window is DIRECTIONAL — ``issued_at`` beyond
    ``permitted_clock_skew_seconds`` AFTER the recorded instant is stale. An
    absolute delta would admit a claim issued after the door recorded the
    action."""
    inside = _enforce(
        _claims(issued_at=ACTION_TIME + timedelta(seconds=SKEW_SECONDS)),
        provider,
        ruled_policy,
    )
    assert inside.issued_at == ACTION_TIME + timedelta(seconds=SKEW_SECONDS)
    with pytest.raises(SignedBindingStaleRefused, match="post-dated"):
        _enforce(
            _claims(issued_at=ACTION_TIME + timedelta(seconds=SKEW_SECONDS + 1)),
            provider,
            ruled_policy,
        )


# --- 10-02 Task 3: composed double-verification idempotency (D-13) ----------
#
# A primitive AND its transport both verify independently. One valid signed
# submission traverses BOTH verifications end-to-end without refusal;
# removing the attestation is refused at the primitive layer before the
# transport is touched. No verified-marker exists between the layers — the
# structural absence D-13 demands is asserted by the composition itself:
# nothing is passed from primitive to transport except the submission the
# transport re-verifies from scratch.
#
# `D-IMPL-363` C7 adds a second property to both controls: the primitive's
# own clock TICKS on every call (it stamps audit records), and the admission
# is judged purely against the binding's FIXED ``action_time`` and the
# claim's ``issued_at`` — the verifier reads no clock, so a ticking gate
# cannot slide a fresh claim out of the window.


def _both_layers_bound(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> InMemoryHitlTransport:
    compose_register_typed(
        plane, POLICY_KEY, _policy(required=True, trusted_keys=trusted_keys), HITL_POLICY
    )
    return _transport(plane, provider)


def _ticking_clock() -> Any:
    """A clock that advances on EVERY read, so a test cannot accidentally
    depend on the primitive's instant being stable."""
    state = {"now": datetime(2026, 7, 30, tzinfo=UTC)}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


def test_approval_gate_double_verification_is_idempotent(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    from ccf.contracts.canonical import content_hash
    from ccf.controlplane.audit import AuditLog
    from ccf.hitl.approval_gate import ApprovalGate, GateResolution
    from ccf.hitl.transport import PendingHitlEvent

    transport = _both_layers_bound(plane, provider, trusted_keys)
    gate = ApprovalGate(
        transport=transport,
        audit=AuditLog(),
        clock=_ticking_clock(),
        control_plane=plane,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
    )
    document = {
        "event_key": "acme-bank/exec-hitl/idempotency-gate",
        "event_class": "approval-gate",
        "tenant": _TENANT,
        "workflow_state_ref": "acme-bank/exec-hitl",
    }
    event = PendingHitlEvent(
        **document, product_content_hash=content_hash(document)
    )
    transport.enqueue(event=event)
    # The binding's action_time is FIXED (C7): the gate's clock ticks, the
    # verifier reads none, and the window is judged against this instant.
    principal = _binding(product_content_hash=event.product_content_hash)
    assert principal.action_time == ACTION_TIME
    # Unsigned: refused at the primitive layer BEFORE the transport is
    # touched — no submission recorded, event still pending.
    with pytest.raises(SignedBindingRequiredRefused):
        gate.resolve(
            _authorized(_TENANT, event.event_key),
            event_key=event.event_key,
            action="approve",
            principal=principal,
        )
    assert transport.submissions(tenant=_TENANT) == ()
    assert transport.pending(tenant=_TENANT) == (event,)
    # Valid signed, with ``issued_at`` INSIDE the window around the fixed
    # recorded instant: passes primitive verification AND the transport's own
    # independent verification (idempotent double verification, D-13).
    attestation = _attest(
        _claims(
            event_key=event.event_key,
            product_content_hash=event.product_content_hash,
            issued_at=ACTION_TIME - timedelta(seconds=5),
            nonce="nonce-gate-idempotency-1",
        ),
        provider,
    )
    resolution = gate.resolve(
        _authorized(_TENANT, event.event_key),
        event_key=event.event_key,
        action="approve",
        principal=principal,
        attestation=attestation,
    )
    assert isinstance(resolution, GateResolution)
    recorded = transport.submissions(tenant=_TENANT)
    assert len(recorded) == 1
    assert recorded[0].attestation == attestation


def test_review_queue_double_verification_is_idempotent(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: dict[str, dict[str, JsonWebKey]],
) -> None:
    from ccf.contracts.canonical import content_hash
    from ccf.contracts.claims import LineageEntry, PassageAnchor
    from ccf.controlplane.audit import AuditLog
    from ccf.hitl.review_queue import (
        ReviewQueue,
        ReviewQueueItem,
        ReviewResolution,
    )
    from ccf.signal.envelope import SourceIdentity

    transport = _both_layers_bound(plane, provider, trusted_keys)
    queue = ReviewQueue(
        transport=transport,
        audit=AuditLog(),
        clock=_ticking_clock(),
        control_plane=plane,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
    )
    item = ReviewQueueItem(
        output_ref="ccf-artifact://acme-bank/review/output@1.0.0",
        lineage=(
            LineageEntry(
                source=SourceIdentity(system_id="fixture-system"),
                envelope_id="env-idempotency-1",
                observed_at=datetime(2026, 7, 15, tzinfo=UTC),
                passage_anchor=PassageAnchor(
                    kind="document-page", locator="fixture/1#p1"
                ),
            ),
        ),
    )
    event_key = "acme-bank/exec-rev/idempotency-review"
    queue.submit_for_review(
        tenant=_TENANT,
        event_key=event_key,
        workflow_state_ref="acme-bank/exec-rev",
        item=item,
    )
    principal = _binding(product_content_hash=content_hash(item))
    assert principal.action_time == ACTION_TIME
    with pytest.raises(SignedBindingRequiredRefused):
        queue.release(
            _authorized(_TENANT, event_key),
            event_key=event_key,
            principal=principal,
        )
    assert transport.submissions(tenant=_TENANT) == ()
    assert len(transport.pending(tenant=_TENANT)) == 1
    # ``release`` DERIVES the action "approve"; the signed claims must equal
    # that derived action, not a caller-stated one.
    attestation = _attest(
        _claims(
            event_key=event_key,
            action="approve",
            product_content_hash=content_hash(item),
            issued_at=ACTION_TIME + timedelta(seconds=5),
            nonce="nonce-review-idempotency-1",
        ),
        provider,
    )
    resolution = queue.release(
        _authorized(_TENANT, event_key),
        event_key=event_key,
        principal=principal,
        attestation=attestation,
    )
    assert isinstance(resolution, ReviewResolution)
    recorded = transport.submissions(tenant=_TENANT)
    assert len(recorded) == 1
    assert recorded[0].attestation == attestation
