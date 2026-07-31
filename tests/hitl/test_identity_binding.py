"""Tests for the JWS-signed principal binding (D-IMPL-21 reference impl #2).

The binding reuses the D-IMPL-15 signing machinery (``ccf.peering.identity``)
so a HITL approver identity carries cryptographic non-repudiation: a signed
:class:`~ccf.hitl.principal.HumanPrincipalBinding` whose fields are altered
after signing fails verification with a typed error. Keys are generated per
test into a tmp directory via the same ``FileBackedKeySource`` fixture
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
    PrincipalBindingInvalid,
    SignedPrincipalBinding,
    sign_principal_binding,
    verify_principal_binding,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
    SignatureInvalid,
    UnknownSigningKey,
)

APPROVER_KID = "hitl-approver-signing-key"


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


def test_a_signed_binding_round_trips_to_the_identical_binding(
    provider: DetachedJwsIdentityProvider, approver_key: ECKey
) -> None:
    binding = _binding()
    signed = sign_principal_binding(
        binding, provider=provider, key_id=APPROVER_KID
    )
    assert signed.key_id == APPROVER_KID
    verified = verify_principal_binding(
        signed, provider=provider, public_keys=_public(approver_key)
    )
    assert verified == binding


# --- Test 2: tamper (the red counterfactual) --------------------------------


def test_a_binding_with_a_substituted_approver_fails_verification(
    provider: DetachedJwsIdentityProvider, approver_key: ECKey
) -> None:
    """Re-bind the original signature to a different approver: typed failure."""
    signed = sign_principal_binding(
        _binding("approver-1"), provider=provider, key_id=APPROVER_KID
    )
    forged = SignedPrincipalBinding(
        binding=_binding("attacker-substituted-approver"),
        signature=signed.signature,
        key_id=signed.key_id,
    )
    with pytest.raises(PrincipalBindingInvalid) as caught:
        verify_principal_binding(
            forged, provider=provider, public_keys=_public(approver_key)
        )
    assert isinstance(caught.value.__cause__, SignatureInvalid)


# --- Test 3: unknown key ----------------------------------------------------


def test_verification_without_the_declared_key_fails_typed(
    provider: DetachedJwsIdentityProvider, approver_key: ECKey
) -> None:
    signed = sign_principal_binding(
        _binding(), provider=provider, key_id=APPROVER_KID
    )
    with pytest.raises(PrincipalBindingInvalid) as caught:
        verify_principal_binding(signed, provider=provider, public_keys={})
    assert isinstance(caught.value.__cause__, UnknownSigningKey)


# --- Test 4: contract discipline --------------------------------------------


def test_the_signed_binding_is_a_ccf_contract_and_rejects_extras(
    provider: DetachedJwsIdentityProvider, approver_key: ECKey
) -> None:
    signed = sign_principal_binding(
        _binding(), provider=provider, key_id=APPROVER_KID
    )
    assert isinstance(signed, CCFContract)
    with pytest.raises(ValidationError):
        SignedPrincipalBinding(
            binding=signed.binding,
            signature=signed.signature,
            key_id=signed.key_id,
            extra_field="forbidden",  # type: ignore[call-arg]
        )
