"""Tests for the JWS-signed HITL action attestation (D-IMPL-21 reference impl #2).

`D-IMPL-363` (SEC-005, the remaining leg) moved WHAT is signed: no longer the
door-minted :class:`~ccf.hitl.principal.HumanPrincipalBinding` — whose
``action_time`` the door stamps from its own clock, so a signer had to predict
the server's clock reading — but the signer's own
:class:`~ccf.hitl.identity_binding.HitlActionClaims`, carried as
:class:`~ccf.hitl.identity_binding.SignedHitlAction`.

The attestation reuses the D-IMPL-15 signing machinery
(``ccf.peering.identity``) so a HITL approver identity carries cryptographic
non-repudiation: claims whose subject, verdict or instant are altered after
signing fail verification with a typed error
(:class:`~ccf.hitl.identity_binding.AttestationInvalid`). Keys are generated
per test into a tmp directory via the same ``FileBackedKeySource`` fixture
pattern as ``tests/peering/test_identity.py``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest
from joserfc.jwk import ECKey
from pydantic import ValidationError

from ccf.contracts.base import CCFContract
from ccf.hitl.identity_binding import (
    AttestationInvalid,
    HitlActionClaims,
    SignedHitlAction,
    sign_hitl_action,
    verify_hitl_action,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
    SignatureInvalid,
    UnknownSigningKey,
)

APPROVER_KID = "hitl-approver-signing-key"

#: The signer's own instant. Fixed, because nothing in this module judges
#: freshness — the window lives at the verifier
#: (:func:`ccf.hitl.transport.enforce_attestation`), and these tests are about
#: the signature over the claims.
ISSUED_AT = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)


def _write_key(directory: Path, key_id: str) -> ECKey:
    """Generate a P-256 key, store the private JWK, return the key."""
    key = ECKey.generate_key("P-256", parameters={"kid": key_id})
    (directory / f"{key_id}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return key


def _public(key: ECKey) -> Mapping[str, JsonWebKey]:
    public: Mapping[str, str] = key.as_dict(private=False)
    return {APPROVER_KID: public}


def _claims(subject_id: str = "approver-1") -> HitlActionClaims:
    return HitlActionClaims(
        tenant="acme-bank",
        event_key="event-1",
        action="approve",
        product_content_hash=hashlib.sha256(b"fixture-product").hexdigest(),
        subject_id=subject_id,
        issued_at=ISSUED_AT,
        nonce="nonce-identity-binding-1",
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
def provider(key_dir: Path) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )


# --- Test 1: round trip -----------------------------------------------------


def test_a_signed_attestation_round_trips_to_the_identical_claims(
    provider: DetachedJwsIdentityProvider, approver_key: ECKey
) -> None:
    claims = _claims()
    signed = sign_hitl_action(claims, provider=provider, key_id=APPROVER_KID)
    assert signed.key_id == APPROVER_KID
    verified = verify_hitl_action(
        signed, provider=provider, public_keys=_public(approver_key)
    )
    assert verified == claims


# --- Test 2: tamper (the red counterfactual) --------------------------------


def test_claims_with_a_substituted_subject_fail_verification(
    provider: DetachedJwsIdentityProvider, approver_key: ECKey
) -> None:
    """Re-bind the original signature to a different subject: typed failure."""
    signed = sign_hitl_action(
        _claims("approver-1"), provider=provider, key_id=APPROVER_KID
    )
    forged = SignedHitlAction(
        claims=_claims("attacker-substituted-subject"),
        signature=signed.signature,
        key_id=signed.key_id,
    )
    with pytest.raises(AttestationInvalid) as caught:
        verify_hitl_action(
            forged, provider=provider, public_keys=_public(approver_key)
        )
    assert isinstance(caught.value.__cause__, SignatureInvalid)


# --- Test 3: unknown key ----------------------------------------------------


def test_verification_without_the_declared_key_fails_typed(
    provider: DetachedJwsIdentityProvider, approver_key: ECKey
) -> None:
    signed = sign_hitl_action(
        _claims(), provider=provider, key_id=APPROVER_KID
    )
    with pytest.raises(AttestationInvalid) as caught:
        verify_hitl_action(signed, provider=provider, public_keys={})
    assert isinstance(caught.value.__cause__, UnknownSigningKey)


# --- Test 4: contract discipline --------------------------------------------


def test_the_signed_attestation_is_a_ccf_contract_and_rejects_extras(
    provider: DetachedJwsIdentityProvider, approver_key: ECKey
) -> None:
    signed = sign_hitl_action(
        _claims(), provider=provider, key_id=APPROVER_KID
    )
    assert isinstance(signed, CCFContract)
    assert isinstance(signed.claims, CCFContract)
    with pytest.raises(ValidationError):
        SignedHitlAction(
            claims=signed.claims,
            signature=signed.signature,
            key_id=signed.key_id,
            extra_field="forbidden",  # type: ignore[call-arg]
        )
    with pytest.raises(ValidationError):
        HitlActionClaims(
            **signed.claims.model_dump(),
            extra_field="forbidden",  # type: ignore[call-arg]
        )
