"""`SEC-022` residuals: the replay scope is the KEY, and the default seen-set is the process's.

Row ``SEC-022`` closed its replay defense for one gate and one observed peer id
(``tests/peering/test_admission_refuses_replay.py``). The owner's main-merge
record ``29a3c5a4`` held two residuals as "NOT accepted as closure evidence",
and both executed as admitted replays at ``8fceec83``:

* **SEC-022-C-01.** The nonce was scoped by the OBSERVED peer id
  (``src/ccf/peering/admission.py::PeeringAdmissionGate.admit``, the replay
  consult). A trust policy listing one signing key under two peer ids admitted
  the identical signed bytes once under each. **Ruling:** the replay key is
  scoped by the key the signature verified under, never by the observed or
  claimed peer id; the same signed bytes under an alias peer id with the same
  key are refused ``replayed``.
* **SEC-022-R1.** A second gate built with the DEFAULT seen-set admitted a
  replay the first gate had already admitted; sharing was a documented
  obligation, not an enforced one. **Ruling (executor's, for the owner to
  confirm — it changes Q14's "per gate" to "per process"):** the default is
  ONE seen-set shared by every gate in the process, behind the existing
  Protocol; an explicitly supplied seen-set still wins; a deployment whose
  receivers span processes must supply a shared implementation.

Both cases are written in the FIXED direction: each asserts the replay is
refused, so a failure names a residual that is present.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from joserfc.jwk import ECKey, OKPKey, RSAKey

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.peering.admission import (
    ADMISSION_RECORD,
    AdmittedProduct,
    SignatureRefusal,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
    KeyUnavailable,
    SignedContextProduct,
    jwk_thumbprint,
)
from ccf.peering.protocol import InboundProduct, PeerRef
from ccf.peering.trust_policy import PeerTrustGrant
from ccf.products.contract import RegisteredProductClass

from tests.peering.issuance_fixture import issuance_member, window
from tests.peering.test_admission import (  # noqa: F401  (pytest fixtures)
    BOUNDARY,
    PEER_A,
    PEER_A_KID,
    PEER_A_PRODUCER,
    PEER_B,
    PEER_B_KID,
    PEER_B_PRODUCER,
    POLICY_REGIME,
    PRODUCER_ASSERTION_HEADER,
    PRODUCT_CLASS,
    TENANT,
    _gate,
    _register_ceiling,
    _register_policy,
    artifact_store,
    banking_product,
    consumer_lineage,
    key_dir,
    keys,
    product_class,
    provider,
    registry,
)

#: The refusal token the issuance check and the replay consult share.
GATE_ISSUANCE = "peering-issuance"

#: A second peer id the receiver's trust policy lists with peer A's own key.
PEER_ALIAS = "acme-bank-alias"


def _now() -> datetime:
    return BOUNDARY + timedelta(seconds=1)


def _signed_once(provider: DetachedJwsIdentityProvider) -> object:
    """One honest envelope signed by peer A's key, with a fresh nonce."""
    body = banking_product()
    assertions = {PRODUCER_ASSERTION_HEADER: PEER_A_PRODUCER}
    assertions.update(issuance_member(product=body, issued_at=BOUNDARY))
    return provider.sign(product=body, key_id=PEER_A_KID, assertions=assertions)


def _presented(signed: object, *, as_peer: str) -> InboundProduct:
    return InboundProduct(
        observed_peer=PeerRef(tenant_id=TENANT, peer_id=as_peer),
        signed=signed,  # type: ignore[arg-type]
    )


def _grant_over(
    document: JsonWebKey,
    *,
    kid: str = PEER_A_KID,
    producer: str = PEER_A_PRODUCER,
) -> PeerTrustGrant:
    """Peer A's entitlements, with ``document`` as the key under ``kid``."""
    return PeerTrustGrant(
        signing_keys={kid: document},
        permitted_producer_hashes=frozenset({producer}),
        permitted_schema_names=frozenset({PRODUCT_CLASS["schema_name"]}),
        permitted_policy_regimes=frozenset({POLICY_REGIME}),
        **window(),
    )


def _as_written(key: ECKey) -> JsonWebKey:
    """The public JWK exactly as the primary grant writes it."""
    return dict(key.as_dict(private=False))


def _rewritten(key: ECKey) -> JsonWebKey:
    """The SAME key material, written with different non-key members.

    No ``kid`` member and an added ``use``: a different JWK document, the same
    key. A scope computed from the document rather than from the key would let
    the replay through here and nowhere else.
    """
    document = dict(key.as_dict(private=False))
    document.pop("kid", None)
    document["use"] = "sig"
    return document


def _events(registry: ControlPlaneRegistry, action: str) -> list[object]:
    return [e for e in registry.audit_events() if e.action == action]


# --- SEC-022-C-01: one key listed under two peer ids --------------------------


@pytest.mark.parametrize(
    "alias_rendering",
    [
        pytest.param(_as_written, id="same-jwk-document"),
        pytest.param(_rewritten, id="same-key-other-jwk-members"),
    ],
)
def test_c01_the_same_envelope_under_an_alias_peer_id_with_the_same_key_is_refused_replayed(
    alias_rendering: object,
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, ECKey],
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: object,
) -> None:
    """The identical signed bytes, admitted as peer A, are refused as the alias.

    One gate, one trust policy listing peer A's key under two peer ids; the
    second presentation is observed as the alias, thirty seconds later, inside
    every window.
    """
    render = alias_rendering
    policy_version = _register_policy(
        registry,
        tenant_id=TENANT,
        peers={
            PEER_A: _grant_over(_as_written(keys[PEER_A_KID])),
            PEER_ALIAS: _grant_over(render(keys[PEER_A_KID])),  # type: ignore[operator]
        },
    )
    ceiling_version = _register_ceiling(registry, tenant_id=TENANT)
    gate = _gate(
        provider=provider,
        registry=registry,
        product_class=product_class,
        tenant_id=TENANT,
        policy_version=policy_version,
        ceiling_version=ceiling_version,
        artifact_store=artifact_store,  # type: ignore[arg-type]
    )
    signed = _signed_once(provider)

    first = gate.admit(
        inbound=_presented(signed, as_peer=PEER_A),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(first, AdmittedProduct), first

    again = gate.admit(
        inbound=_presented(signed, as_peer=PEER_ALIAS),
        consumer_lineage=consumer_lineage(),
        now=_now() + timedelta(seconds=30),
    )
    assert not isinstance(again, AdmittedProduct), (
        "SEC-022-C-01: the identical signed bytes were ADMITTED a second time"
        f" under alias peer id {PEER_ALIAS!r}, signed by the same key"
        f" ({PEER_A_KID!r}), by the SAME gate"
    )
    assert getattr(again, "gate", None) == GATE_ISSUANCE, again
    assert getattr(again, "failure", None) == "replayed", again
    assert getattr(again, "peer_id", None) == PEER_ALIAS, again

    assert len(_events(registry, "peering_admitted")) == 1
    versions = artifact_store.versions(  # type: ignore[attr-defined]
        tenant_id=TENANT,
        artifact_class=ADMISSION_RECORD.class_id,
        name=first.content_address,
    )
    assert len(versions) == 1, versions


# --- SEC-022-R1: two gates, each with the default seen-set --------------------


def test_r1_a_second_gate_with_the_default_seen_set_refuses_the_replay_the_first_admitted(
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, ECKey],
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: object,
) -> None:
    """Two receivers in one process, neither handed a seen-set: one admission.

    Both gates are built exactly as a composition that never heard of the
    seen-set would build them — no ``seen=`` — over the same Control Plane.
    """
    policy_version = _register_policy(
        registry,
        tenant_id=TENANT,
        peers={PEER_A: _grant_over(_as_written(keys[PEER_A_KID]))},
    )
    ceiling_version = _register_ceiling(registry, tenant_id=TENANT)
    gates = [
        _gate(
            provider=provider,
            registry=registry,
            product_class=product_class,
            tenant_id=TENANT,
            policy_version=policy_version,
            ceiling_version=ceiling_version,
            artifact_store=artifact_store,  # type: ignore[arg-type]
        )
        for _ in range(2)
    ]
    assert gates[0] is not gates[1]
    inbound = _presented(_signed_once(provider), as_peer=PEER_A)

    first = gates[0].admit(
        inbound=inbound, consumer_lineage=consumer_lineage(), now=_now()
    )
    assert isinstance(first, AdmittedProduct), first

    again = gates[1].admit(
        inbound=inbound,
        consumer_lineage=consumer_lineage(),
        now=_now() + timedelta(seconds=30),
    )
    assert not isinstance(again, AdmittedProduct), (
        "SEC-022-R1: a second gate built with the DEFAULT seen-set ADMITTED the"
        " identical signed bytes the first gate had already admitted"
    )
    assert getattr(again, "gate", None) == GATE_ISSUANCE, again
    assert getattr(again, "failure", None) == "replayed", again
    assert len(_events(registry, "peering_admitted")) == 1


# --- SEC-022-C-01, the controls the fix's choices need -------------------------

#: One ``kid`` label two different peers' grants both use, for two different keys.
SHARED_KID_LABEL = "shared-kid-label"

#: One nonce two different producers both chose.
SHARED_NONCE = "nonce-chosen-by-two-producers"


def _provider_holding(directory: Path, *, kid: str) -> tuple[DetachedJwsIdentityProvider, ECKey]:
    """A producer of its own: a fresh P-256 key under ``kid``, and a provider signing with it."""
    directory.mkdir()
    key = ECKey.generate_key("P-256", parameters={"kid": kid})
    (directory / f"{kid}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return (
        DetachedJwsIdentityProvider(key_source=FileBackedKeySource(directory=directory)),
        key,
    )


def _signed_by(
    provider: DetachedJwsIdentityProvider,
    *,
    kid: str,
    producer: str,
    nonce: str | None = None,
) -> SignedContextProduct:
    body = banking_product()
    assertions = {PRODUCER_ASSERTION_HEADER: producer}
    assertions.update(issuance_member(product=body, issued_at=BOUNDARY, nonce=nonce))
    return provider.sign(product=body, key_id=kid, assertions=assertions)


def test_c01_two_keys_sharing_one_kid_label_keep_separate_nonce_scopes(
    tmp_path: Path,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: object,
) -> None:
    """The positive control that the scope is the KEY: not the label, and not nothing.

    Two peers, two different keys, one ``kid`` label, one nonce. A scope keyed
    on the label would let peer B's admission spend peer A's nonce (and peer A
    could burn peer B's); a scope of tenant and nonce alone would too. Both are
    admitted, and peer A's own bytes presented again are still refused — the
    consult ran, in A's key's scope.
    """
    producer_a, key_a = _provider_holding(tmp_path / "a", kid=SHARED_KID_LABEL)
    producer_b, key_b = _provider_holding(tmp_path / "b", kid=SHARED_KID_LABEL)
    assert jwk_thumbprint(_as_written(key_a)) != jwk_thumbprint(_as_written(key_b))
    policy_version = _register_policy(
        registry,
        tenant_id=TENANT,
        peers={
            PEER_A: _grant_over(_as_written(key_a), kid=SHARED_KID_LABEL),
            PEER_B: _grant_over(
                _as_written(key_b), kid=SHARED_KID_LABEL, producer=PEER_B_PRODUCER
            ),
        },
    )
    ceiling_version = _register_ceiling(registry, tenant_id=TENANT)
    gate = _gate(
        provider=producer_a,
        registry=registry,
        product_class=product_class,
        tenant_id=TENANT,
        policy_version=policy_version,
        ceiling_version=ceiling_version,
        artifact_store=artifact_store,  # type: ignore[arg-type]
    )
    from_a = _signed_by(
        producer_a, kid=SHARED_KID_LABEL, producer=PEER_A_PRODUCER, nonce=SHARED_NONCE
    )
    from_b = _signed_by(
        producer_b, kid=SHARED_KID_LABEL, producer=PEER_B_PRODUCER, nonce=SHARED_NONCE
    )

    admitted_a = gate.admit(
        inbound=_presented(from_a, as_peer=PEER_A),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(admitted_a, AdmittedProduct), admitted_a
    admitted_b = gate.admit(
        inbound=_presented(from_b, as_peer=PEER_B),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(admitted_b, AdmittedProduct), (
        "SEC-022-C-01: peer B's envelope, signed by a DIFFERENT key that shares"
        " peer A's kid label and nonce, was refused — the replay scope is the"
        f" label or nothing, not the key: {admitted_b}"
    )
    replay = gate.admit(
        inbound=_presented(from_a, as_peer=PEER_A),
        consumer_lineage=consumer_lineage(),
        now=_now() + timedelta(seconds=30),
    )
    assert getattr(replay, "failure", None) == "replayed", replay


class _RecordingProvider:
    """An identity provider that records the keys each verification was offered.

    ``returns_without_a_key`` makes it NON-conforming: its ``verify`` returns the
    payload whatever it was offered, as a provider that checks nothing would.
    """

    def __init__(
        self, signer: DetachedJwsIdentityProvider, *, returns_without_a_key: bool
    ) -> None:
        self._signer = signer
        self._returns_without_a_key = returns_without_a_key
        self.offered: list[frozenset[str]] = []

    def sign(self, **kwargs: Any) -> SignedContextProduct:
        return self._signer.sign(**kwargs)

    def verify(
        self, *, signed: SignedContextProduct, public_keys: Mapping[str, JsonWebKey]
    ) -> bytes:
        self.offered.append(frozenset(public_keys))
        if self._returns_without_a_key:
            return signed.canonical_payload()
        return self._signer.verify(signed=signed, public_keys=public_keys)


def _gate_verifying_with(
    identity: _RecordingProvider,
    *,
    grant: PeerTrustGrant,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: object,
) -> Any:
    policy_version = _register_policy(registry, tenant_id=TENANT, peers={PEER_A: grant})
    ceiling_version = _register_ceiling(registry, tenant_id=TENANT)
    return _gate(
        provider=identity,  # type: ignore[arg-type]
        registry=registry,
        product_class=product_class,
        tenant_id=TENANT,
        policy_version=policy_version,
        ceiling_version=ceiling_version,
        artifact_store=artifact_store,  # type: ignore[arg-type]
    )


def test_c01_verification_is_offered_only_the_key_the_header_names(
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, ECKey],
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: object,
) -> None:
    """Peer A holds two keys; an envelope naming one is verified against that one only.

    This is what makes "the key the signature verified under" a fact the gate
    holds rather than one it assumes of the provider.
    """
    grant = PeerTrustGrant(
        signing_keys={
            PEER_A_KID: _as_written(keys[PEER_A_KID]),
            PEER_B_KID: _as_written(keys[PEER_B_KID]),
        },
        permitted_producer_hashes=frozenset({PEER_A_PRODUCER}),
        permitted_schema_names=frozenset({PRODUCT_CLASS["schema_name"]}),
        permitted_policy_regimes=frozenset({POLICY_REGIME}),
        **window(),
    )
    identity = _RecordingProvider(provider, returns_without_a_key=False)
    gate = _gate_verifying_with(
        identity,
        grant=grant,
        registry=registry,
        product_class=product_class,
        artifact_store=artifact_store,
    )
    outcome = gate.admit(
        inbound=_presented(
            _signed_by(provider, kid=PEER_A_KID, producer=PEER_A_PRODUCER),
            as_peer=PEER_A,
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, AdmittedProduct), outcome
    assert identity.offered == [frozenset({PEER_A_KID})], identity.offered


def test_c01_a_provider_that_returns_with_no_key_offered_admits_nothing(
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, ECKey],
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: object,
) -> None:
    """A header naming a key outside the grant is offered no key at all.

    A NON-conforming provider that returns anyway has checked nothing a peer
    may sign with: the gate refuses at the signature check, audited, rather
    than admitting or raising.
    """
    identity = _RecordingProvider(provider, returns_without_a_key=True)
    gate = _gate_verifying_with(
        identity,
        grant=_grant_over(_as_written(keys[PEER_A_KID])),
        registry=registry,
        product_class=product_class,
        artifact_store=artifact_store,
    )
    outcome = gate.admit(
        inbound=_presented(
            _signed_by(provider, kid=PEER_B_KID, producer=PEER_A_PRODUCER),
            as_peer=PEER_A,
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert identity.offered == [frozenset()], identity.offered
    assert isinstance(outcome, SignatureRefusal), outcome
    assert outcome.failure == "UnknownSigningKey", outcome
    assert not _events(registry, "peering_admitted")
    assert len(_events(registry, "peering_admission_refused")) == 1


# --- the scope's identity: an RFC 7638 thumbprint ------------------------------


@pytest.mark.parametrize(
    "generate",
    [
        pytest.param(lambda: ECKey.generate_key("P-256"), id="EC"),
        pytest.param(lambda: OKPKey.generate_key("Ed25519"), id="OKP"),
        pytest.param(lambda: RSAKey.generate_key(2048), id="RSA"),
    ],
)
def test_jwk_thumbprint_is_rfc_7638_for_every_key_type_it_names(generate: Any) -> None:
    """Each row of the member table, against ``joserfc``'s own thumbprint (the oracle)."""
    key = generate()
    assert jwk_thumbprint(key.as_dict(private=False)) == key.thumbprint()


def test_jwk_thumbprint_names_the_key_not_its_document(keys: dict[str, ECKey]) -> None:
    """A different ``kid`` member or an added ``use`` is the same key; another key is not."""
    key = keys[PEER_A_KID]
    assert jwk_thumbprint(_rewritten(key)) == jwk_thumbprint(_as_written(key))
    assert jwk_thumbprint(_as_written(keys[PEER_B_KID])) != jwk_thumbprint(
        _as_written(key)
    )


@pytest.mark.parametrize(
    "document",
    [
        pytest.param({"kty": "oct", "k": "c2VjcmV0"}, id="symmetric"),
        pytest.param({"kty": "unknown"}, id="unknown-type"),
        pytest.param({}, id="no-type"),
        pytest.param({"kty": "EC", "crv": "P-256", "x": "AAAA"}, id="EC-without-y"),
    ],
)
def test_jwk_thumbprint_refuses_what_identifies_no_public_key(
    document: dict[str, str],
) -> None:
    with pytest.raises(KeyUnavailable):
        jwk_thumbprint(document)
