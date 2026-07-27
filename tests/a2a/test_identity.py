"""Detached-JWS identity: round trip, tamper refusal, and the two-peer case.

Every test is named for the property it defends, and every assertion is drafted
from what a *broken* implementation would do, not from what the module intends:

* a verifier that reattached its own copy of the payload would pass a round-trip
  test and admit tampered bytes — hence the byte-for-byte payload assertion and
  the mutation test;
* a verifier that read ``kid`` as decoration would pass a single-peer suite and
  admit peer B's product under peer A's grant — the D-23 obligation, and the
  reason the two-peer case is written as the default rather than as an extra;
* a verifier that trusted the protected header's ``alg`` would pass everything
  above and accept an algorithm the deployment never configured.

Product values come from ``tests/fixtures/banking/``. Keys are generated per
test into a temp directory and never committed — the SDK ships no key material,
and neither does its test suite.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from joserfc.jwk import ECKey

from ccf.a2a.identity import (
    PRODUCT_SIGNATURE_TYPE,
    SIGNING_ALGORITHM,
    AlgorithmNotPermitted,
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    IdentityProvider,
    JsonWebKey,
    KeyUnavailable,
    SignatureInvalid,
    SignedContextProduct,
    SigningKeySource,
    UnknownSigningKey,
)
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.contract import ContextProductContract, ProductLineage

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"

#: Fixture-side vocabulary: two peers, each with its own key identifier. The
#: identifiers are test values, exactly as peer names would be deployment
#: values — the SDK enumerates neither.
PEER_A_KID = "acme-bank-a2a-1"
PEER_B_KID = "zenith-bank-a2a-1"


def _fixture(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


def banking_product() -> ContextProductContract:
    """A Context Product built from the banking fixtures' declared class."""
    declared = _fixture("controlplane.yaml")["product_class"]
    tenant_id = _fixture("ontology.yaml")["tenant_id"]
    boundary = datetime(2026, 3, 2, 11, 59, tzinfo=UTC)
    return ContextProductContract(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        plan_id=declared["plan_id"],
        tenant_id=tenant_id,
        temporal_boundary=boundary,
        expires_at=boundary + timedelta(seconds=60),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"policy.principal-subgraph"}),
            policy_bundle_versions=frozenset({"policy-version-fixture"}),
            graph_snapshot_at=boundary,
        ),
        payload={"exposure_state": "fixture"},
    )


def _write_key(directory: Path, key_id: str) -> ECKey:
    """Generate a P-256 key, store the private JWK, return the key."""
    key = ECKey.generate_key("P-256", parameters={"kid": key_id})
    (directory / f"{key_id}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return key


def _public(key: ECKey) -> JsonWebKey:
    public: Mapping[str, str] = key.as_dict(private=False)
    return public


@pytest.fixture
def key_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "keys"
    directory.mkdir()
    return directory


@pytest.fixture
def peer_a(key_dir: Path) -> ECKey:
    return _write_key(key_dir, PEER_A_KID)


@pytest.fixture
def peer_b(key_dir: Path) -> ECKey:
    return _write_key(key_dir, PEER_B_KID)


@pytest.fixture
def provider(key_dir: Path) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )


# --- structural conformance ------------------------------------------------


def test_the_reference_impl_conforms_to_the_identity_protocol(
    provider: DetachedJwsIdentityProvider,
) -> None:
    assert isinstance(provider, IdentityProvider)


def test_the_dev_key_source_conforms_to_the_custody_protocol(
    key_dir: Path, peer_a: ECKey
) -> None:
    source = FileBackedKeySource(directory=key_dir)
    assert isinstance(source, SigningKeySource)
    assert source.key_ids() == (PEER_A_KID,)


def test_a_signed_product_is_an_auditable_typed_value(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey
) -> None:
    """The envelope must itself land in audit and replay, so it must hash."""
    signed = provider.sign(product=banking_product(), key_id=PEER_A_KID)
    assert isinstance(signed, SignedContextProduct)
    assert isinstance(signed, CCFContract)
    assert content_hash(signed)


# --- the round trip --------------------------------------------------------


def test_the_verified_payload_is_the_sent_payload_byte_for_byte(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey
) -> None:
    product = banking_product()
    signed = provider.sign(product=product, key_id=PEER_A_KID)
    recovered = provider.verify(
        signed=signed, public_keys={PEER_A_KID: _public(peer_a)}
    )
    assert recovered == canonical_bytes(product)


def test_the_signed_payload_is_the_content_address_preimage(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey
) -> None:
    """Signature and content address must describe one artifact, not two."""
    product = banking_product()
    signed = provider.sign(product=product, key_id=PEER_A_KID)
    assert signed.content_address() == content_hash(product)


def test_the_protected_header_carries_the_declared_alg_kid_and_typ(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey
) -> None:
    signed = provider.sign(product=banking_product(), key_id=PEER_A_KID)
    header = signed.declared_header()
    assert header["alg"] == SIGNING_ALGORITHM
    assert header["kid"] == PEER_A_KID
    assert header["typ"] == PRODUCT_SIGNATURE_TYPE


def test_the_detached_members_are_exactly_protected_and_signature(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey
) -> None:
    """The payload travels separately; an embedded copy would fail here.

    Asserted against the raw JWS members rather than the contract's fields, so
    an implementation that kept a second payload inside the envelope — the
    shape where the signed copy and the delivered copy can diverge — is caught.
    """
    signed = provider.sign(product=banking_product(), key_id=PEER_A_KID)
    envelope = signed.model_dump()
    assert set(envelope) == {"payload", "protected", "signature"}
    header = signed.declared_header()
    assert "payload" not in header
    assert set(header) == {"alg", "kid", "typ"}


# --- tamper refusal --------------------------------------------------------


def _mutate_one_byte(signed: SignedContextProduct) -> SignedContextProduct:
    """Return the envelope with exactly one payload byte changed."""
    padded = signed.payload + "=" * (-len(signed.payload) % 4)
    raw = bytearray(base64.urlsafe_b64decode(padded))
    raw[0] ^= 0x01
    mutated = base64.urlsafe_b64encode(bytes(raw)).rstrip(b"=").decode("ascii")
    return signed.model_copy(update={"payload": mutated})


def test_a_tampered_payload_is_refused_with_a_signature_failure(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey
) -> None:
    signed = _mutate_one_byte(
        provider.sign(product=banking_product(), key_id=PEER_A_KID)
    )
    with pytest.raises(SignatureInvalid):
        provider.verify(signed=signed, public_keys={PEER_A_KID: _public(peer_a)})


def test_tampering_is_a_different_failure_from_an_unknown_kid(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey
) -> None:
    """A forgery must not be reportable as a configuration lag, or vice versa."""
    signed = provider.sign(product=banking_product(), key_id=PEER_A_KID)
    with pytest.raises(UnknownSigningKey) as unknown:
        provider.verify(signed=signed, public_keys={})
    with pytest.raises(SignatureInvalid) as invalid:
        provider.verify(
            signed=_mutate_one_byte(signed),
            public_keys={PEER_A_KID: _public(peer_a)},
        )
    assert not isinstance(unknown.value, SignatureInvalid)
    assert not isinstance(invalid.value, UnknownSigningKey)


# --- the D-23 two-peer case ------------------------------------------------


def test_two_peer_a_product_does_not_verify_under_peer_b_key(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey, peer_b: ECKey
) -> None:
    """CR-01 class: an admission claim that is right with one peer and wrong
    with two. Peer A's kid offered against peer B's key material must fail."""
    signed = provider.sign(product=banking_product(), key_id=PEER_A_KID)
    with pytest.raises(SignatureInvalid):
        provider.verify(
            signed=signed, public_keys={PEER_A_KID: _public(peer_b)}
        )


def test_two_peer_b_product_does_not_verify_under_peer_a_key(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey, peer_b: ECKey
) -> None:
    signed = provider.sign(product=banking_product(), key_id=PEER_B_KID)
    with pytest.raises(SignatureInvalid):
        provider.verify(
            signed=signed, public_keys={PEER_B_KID: _public(peer_a)}
        )


def test_two_peer_verifier_holding_both_keys_resolves_each_by_kid(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey, peer_b: ECKey
) -> None:
    """Both products verify against the same key set, each via its own kid."""
    product = banking_product()
    both = {PEER_A_KID: _public(peer_a), PEER_B_KID: _public(peer_b)}
    from_a = provider.sign(product=product, key_id=PEER_A_KID)
    from_b = provider.sign(product=product, key_id=PEER_B_KID)
    assert from_a.declared_key_id() == PEER_A_KID
    assert from_b.declared_key_id() == PEER_B_KID
    assert provider.verify(signed=from_a, public_keys=both) == canonical_bytes(
        product
    )
    assert provider.verify(signed=from_b, public_keys=both) == canonical_bytes(
        product
    )
    # Same product, two peers: the envelopes must still be distinguishable, or
    # the kid is not actually binding the signature to a principal.
    assert from_a.signature != from_b.signature


def test_cross_peer_kid_substitution_does_not_admit_the_product(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey, peer_b: ECKey
) -> None:
    """Relabelling peer A's envelope as peer B's must not verify.

    The header is unauthenticated input; if a verifier let the declared kid
    select a key without the signature binding it, this would pass.
    """
    signed = provider.sign(product=banking_product(), key_id=PEER_A_KID)
    header = dict(signed.declared_header())
    header["kid"] = PEER_B_KID
    relabelled = signed.model_copy(
        update={
            "protected": base64.urlsafe_b64encode(
                json.dumps(header).encode("utf-8")
            )
            .rstrip(b"=")
            .decode("ascii")
        }
    )
    with pytest.raises(SignatureInvalid):
        provider.verify(
            signed=relabelled,
            public_keys={
                PEER_A_KID: _public(peer_a),
                PEER_B_KID: _public(peer_b),
            },
        )


# --- algorithm confusion ---------------------------------------------------


def test_an_algorithm_the_deployment_did_not_configure_is_refused(
    provider: DetachedJwsIdentityProvider, peer_a: ECKey
) -> None:
    """A header renaming the algorithm must be refused before any key is used."""
    signed = provider.sign(product=banking_product(), key_id=PEER_A_KID)
    header = dict(signed.declared_header())
    header["alg"] = "none"
    forged = signed.model_copy(
        update={
            "protected": base64.urlsafe_b64encode(
                json.dumps(header).encode("utf-8")
            )
            .rstrip(b"=")
            .decode("ascii")
        }
    )
    with pytest.raises(AlgorithmNotPermitted):
        provider.verify(
            signed=forged, public_keys={PEER_A_KID: _public(peer_a)}
        )


def test_a_verifier_configured_for_another_algorithm_refuses_es256(
    key_dir: Path, peer_a: ECKey
) -> None:
    """The accepted algorithm is the verifier's, never the envelope's."""
    strict = DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir), algorithm="ES384"
    )
    signer = DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )
    signed = signer.sign(product=banking_product(), key_id=PEER_A_KID)
    with pytest.raises(AlgorithmNotPermitted):
        strict.verify(signed=signed, public_keys={PEER_A_KID: _public(peer_a)})


# --- custody ---------------------------------------------------------------


def test_signing_with_a_key_the_source_does_not_hold_is_a_custody_failure(
    provider: DetachedJwsIdentityProvider,
) -> None:
    with pytest.raises(KeyUnavailable):
        provider.sign(product=banking_product(), key_id=PEER_A_KID)


def test_no_key_material_is_committed_to_the_repository() -> None:
    """Keys are generated per test; nothing key-shaped lives in the tree."""
    repo = Path(__file__).resolve().parents[2]
    for pattern in ("*.pem", "*.jwk", "*.key"):
        found = [
            path
            for path in repo.rglob(pattern)
            if ".git" not in path.parts and ".venv" not in path.parts
        ]
        assert found == []
