"""D-16 — signed-binding requiredness at the HITL transport authority path.

08-03 Task 1 (TDD RED). The N5/R2 residual accelerated into Phase 8: when
the Control Plane HITL policy in force declares
``signed_binding_required: true``, an unsigned submission at the authority
seam (:meth:`ccf.hitl.transport.InMemoryHitlTransport.submit`) is a typed
refusal — one exception class for binding-absent-but-required, a distinct
one for binding-invalid/principal-mismatch — so the doors (08-03 Task 2)
can map each to its own ``ERROR_SIGNED_BINDING_*`` constant.

Requiredness is a Control Plane value, never a code constant
(No-Hardcoding, CLAUDE.md §6.4): the ``HitlPolicy`` artifact contract
carries a schema-validated ``signed_binding_required`` boolean defaulting
to false when the key is absent from the document (Ollama C3 — no KeyError
path), and flipping the registered value flips transport behavior with
zero code change.

Designed within the D-IMPL-21/63/67 contract envelope; signing machinery
is the D-IMPL-21 reference impl #2 (:mod:`ccf.hitl.identity_binding`) —
never hand-rolled crypto (T-08-05).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest
from joserfc.jwk import ECKey

from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
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
    HitlActionSubmission,
    HitlPolicy,
    InMemoryHitlTransport,
    SignedBindingInvalidRefused,
    SignedBindingRequiredRefused,
    enforce_signed_binding,
    signed_binding_required,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
)

APPROVER_KID = "hitl-approver-signing-key"

#: Deployment vocabulary chosen by this test-as-deployment (CINV-01): the
#: Control Plane key the composition root binds its HITL policy under.
POLICY_KEY = "acme-bank/hitl/policy"

_TENANT = "acme-bank"


def _write_key(directory: Path, key_id: str) -> ECKey:
    key = ECKey.generate_key("P-256", parameters={"kid": key_id})
    (directory / f"{key_id}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return key


def _binding(subject_id: str = "approver-1") -> HumanPrincipalBinding:
    return HumanPrincipalBinding(
        approver=ApproverIdentity(
            subject_id=subject_id,
            identity_provider_ref="test-idp",
        ),
        authentication=AuthenticationContext(
            method="test-method",
            assurance_level="test-level",
            session_ref="test-session",
        ),
        action_time=datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC),
        product_content_hash=hashlib.sha256(b"fixture-product").hexdigest(),
    )


def _submission(
    principal: HumanPrincipalBinding,
    signed: SignedPrincipalBinding | None = None,
) -> HitlActionSubmission:
    return HitlActionSubmission(
        event_key="event-1",
        tenant=_TENANT,
        action="approve",
        principal=principal,
        signed_binding=signed,
    )


def _policy(*, required: bool, semver: str = "1.0.0") -> HitlPolicy:
    policy = parse_artifact(
        {"semver": semver, "signed_binding_required": required},
        HITL_POLICY,
    )
    assert isinstance(policy, HitlPolicy)
    return policy


@pytest.fixture
def key_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "keys"
    directory.mkdir()
    return directory


@pytest.fixture
def approver_key(key_dir: Path) -> ECKey:
    return _write_key(key_dir, APPROVER_KID)


@pytest.fixture
def provider(key_dir: Path) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )


@pytest.fixture
def trusted_keys(approver_key: ECKey) -> Mapping[str, JsonWebKey]:
    public: Mapping[str, str] = approver_key.as_dict(private=False)
    return {APPROVER_KID: public}


@pytest.fixture
def plane() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


def _transport(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> InMemoryHitlTransport:
    return InMemoryHitlTransport(
        control_plane=plane,
        hitl_policy_key=POLICY_KEY,
        identity_provider=provider,
        trusted_keys=trusted_keys,
    )


# --- Test 1: required + validly signed --------------------------------------


def test_required_and_validly_signed_submission_is_admitted(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> None:
    """A verified binding whose principal matches is admitted, binding kept."""
    plane.register_typed(POLICY_KEY, _policy(required=True), HITL_POLICY)
    transport = _transport(plane, provider, trusted_keys)
    binding = _binding()
    signed = sign_principal_binding(
        binding, provider=provider, key_id=APPROVER_KID
    )
    transport.submit(submission=_submission(binding, signed))
    recorded = transport.submissions(tenant=_TENANT)
    assert len(recorded) == 1
    # The binding lands on the recorded (audited) submission itself.
    assert recorded[0].signed_binding == signed


# --- Test 2: required + unsigned --------------------------------------------


def test_required_and_unsigned_submission_is_a_typed_refusal(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> None:
    plane.register_typed(POLICY_KEY, _policy(required=True), HITL_POLICY)
    transport = _transport(plane, provider, trusted_keys)
    with pytest.raises(SignedBindingRequiredRefused):
        transport.submit(submission=_submission(_binding(), None))
    assert transport.submissions(tenant=_TENANT) == ()


# --- Test 3: required + invalid signature / principal mismatch --------------


def test_required_and_invalid_or_mismatched_binding_is_refused(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> None:
    plane.register_typed(POLICY_KEY, _policy(required=True), HITL_POLICY)
    transport = _transport(plane, provider, trusted_keys)
    binding = _binding()
    signed = sign_principal_binding(
        binding, provider=provider, key_id=APPROVER_KID
    )
    # (a) tampered signature — verification fails.
    tampered = signed.model_copy(
        update={"signature": signed.signature[:-4] + "AAAA"}
    )
    with pytest.raises(SignedBindingInvalidRefused):
        transport.submit(submission=_submission(binding, tampered))
    # (b) valid signature over a DIFFERENT principal than the submission's
    # (spoofing, T-08-06) — principal-match enforcement refuses it.
    other = _binding("approver-2")
    signed_other = sign_principal_binding(
        other, provider=provider, key_id=APPROVER_KID
    )
    with pytest.raises(SignedBindingInvalidRefused):
        transport.submit(submission=_submission(binding, signed_other))
    assert transport.submissions(tenant=_TENANT) == ()


# --- Test 4: not required — behavior unchanged ------------------------------


def test_not_required_admits_unsigned_submissions_unchanged(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> None:
    plane.register_typed(POLICY_KEY, _policy(required=False), HITL_POLICY)
    transport = _transport(plane, provider, trusted_keys)
    transport.submit(submission=_submission(_binding(), None))
    assert len(transport.submissions(tenant=_TENANT)) == 1
    # An entirely unconfigured transport (no Control Plane bound) is the
    # pre-08-03 posture and admits exactly as before.
    bare = InMemoryHitlTransport()
    bare.submit(submission=_submission(_binding(), None))
    assert len(bare.submissions(tenant=_TENANT)) == 1


# --- Test 5: requiredness source is the Control Plane, never code -----------


def test_requiredness_is_a_control_plane_value_not_a_code_constant(
    plane: ControlPlaneRegistry,
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> None:
    """Flipping the registered value flips behavior with zero code change."""
    plane.register_typed(POLICY_KEY, _policy(required=False), HITL_POLICY)
    transport = _transport(plane, provider, trusted_keys)
    transport.submit(submission=_submission(_binding(), None))
    assert len(transport.submissions(tenant=_TENANT)) == 1
    # Flip the Control Plane value — same transport object, no code change.
    plane.register_typed(
        POLICY_KEY, _policy(required=True, semver="1.0.1"), HITL_POLICY
    )
    with pytest.raises(SignedBindingRequiredRefused):
        transport.submit(submission=_submission(_binding(), None))


def test_absent_key_in_the_policy_document_defaults_to_false() -> None:
    """A policy document without the key is well-defined — never a KeyError."""
    policy = parse_artifact({"semver": "1.0.0"}, HITL_POLICY)
    assert isinstance(policy, HitlPolicy)
    assert policy.signed_binding_required is False


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


def test_helper_signed_binding_required_resolves_per_call(
    plane: ControlPlaneRegistry,
) -> None:
    plane.register_typed(POLICY_KEY, _policy(required=False), HITL_POLICY)
    assert (
        signed_binding_required(
            control_plane=plane, hitl_policy_key=POLICY_KEY
        )
        is False
    )
    plane.register_typed(
        POLICY_KEY, _policy(required=True, semver="1.0.1"), HITL_POLICY
    )
    assert (
        signed_binding_required(
            control_plane=plane, hitl_policy_key=POLICY_KEY
        )
        is True
    )


def test_helper_signed_binding_required_rejects_non_hitl_policy(
    plane: ControlPlaneRegistry,
) -> None:
    """A key naming a non-HitlPolicy artifact is a TypeError, not a refusal."""
    plane.register(POLICY_KEY, {"not": "a-policy"})
    with pytest.raises(TypeError):
        signed_binding_required(
            control_plane=plane, hitl_policy_key=POLICY_KEY
        )


def test_helper_enforce_refuses_absent_binding(
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> None:
    with pytest.raises(SignedBindingRequiredRefused):
        enforce_signed_binding(
            _submission(_binding(), None),
            identity_provider=provider,
            trusted_keys=trusted_keys,
        )


def test_helper_enforce_broken_wiring_is_a_runtime_error(
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> None:
    """Requiring bindings without verification machinery is broken wiring."""
    binding = _binding()
    signed = sign_principal_binding(
        binding, provider=provider, key_id=APPROVER_KID
    )
    with pytest.raises(RuntimeError):
        enforce_signed_binding(
            _submission(binding, signed),
            identity_provider=None,
            trusted_keys=trusted_keys,
        )
    with pytest.raises(RuntimeError):
        enforce_signed_binding(
            _submission(binding, signed),
            identity_provider=provider,
            trusted_keys=None,
        )


def test_helper_enforce_refuses_invalid_or_mismatched_binding(
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> None:
    binding = _binding()
    signed = sign_principal_binding(
        binding, provider=provider, key_id=APPROVER_KID
    )
    tampered = signed.model_copy(
        update={"signature": signed.signature[:-4] + "AAAA"}
    )
    with pytest.raises(SignedBindingInvalidRefused):
        enforce_signed_binding(
            _submission(binding, tampered),
            identity_provider=provider,
            trusted_keys=trusted_keys,
        )
    other = _binding("approver-2")
    signed_other = sign_principal_binding(
        other, provider=provider, key_id=APPROVER_KID
    )
    with pytest.raises(SignedBindingInvalidRefused):
        enforce_signed_binding(
            _submission(binding, signed_other),
            identity_provider=provider,
            trusted_keys=trusted_keys,
        )


def test_helper_enforce_admits_a_valid_binding(
    provider: DetachedJwsIdentityProvider,
    trusted_keys: Mapping[str, JsonWebKey],
) -> None:
    binding = _binding()
    signed = sign_principal_binding(
        binding, provider=provider, key_id=APPROVER_KID
    )
    enforce_signed_binding(
        _submission(binding, signed),
        identity_provider=provider,
        trusted_keys=trusted_keys,
    )


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
