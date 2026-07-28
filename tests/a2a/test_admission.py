"""The A2A admission gate: six checks, two peers, two tenants.

Every test is named for the property it defends, and each assertion is drafted
from what a *broken* gate would do rather than from what the module intends:

* a gate that checked signatures against every key it holds would pass a
  single-peer suite and admit peer B's product under peer A's entry — which is
  the CR-01 class of defect D-23 exists to prevent, and the reason the two-peer
  case is the default here rather than an addendum;
* a gate that resolved one shared trust policy would pass a single-tenant suite
  and let tenant 1's grant admit a peer for tenant 2;
* a gate that raised on a governance verdict would look correct until a caller
  wrapped it in a bare ``except`` and proceeded;
* a gate that canonicalized first and measured afterwards would pass an
  oversize test while having already done the work the ceiling exists to avoid.

Concrete product and lineage values come from ``tests/fixtures/banking/``. Keys
are generated per test into a temp directory; no key material is committed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from joserfc.jwk import ECKey

from ccf.a2a.admission import (
    GATE_CONTRACT,
    GATE_LINEAGE_CONTINUITY,
    GATE_PAYLOAD_CEILING,
    GATE_POLICY_BINDING,
    GATE_SIGNATURE,
    INBOUND_PAYLOAD_CEILING,
    PRODUCER_ASSERTION_HEADER,
    A2AAdmissionGate,
    AdmissionBypassError,
    AdmissionRefusal,
    AdmittedProduct,
    ContractRefusal,
    InboundPayloadCeiling,
    PayloadTooLargeRefusal,
    PolicyBindingRefusal,
    SignatureRefusal,
    payload_ceiling_key,
    union_lineage,
)
from ccf.a2a.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
    SignedContextProduct,
)
from ccf.a2a.trust_policy import (
    A2A_TRUST_POLICY,
    A2ATrustPolicy,
    PeerTrustGrant,
    trust_policy_key,
)
from ccf.a2a.wire import InboundProduct, PeerRef, WireProtocol
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import TTLRefusal

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"

#: Fixture-side vocabulary. Peer names, key identifiers, producer hashes and
#: tenant names are deployment values; the SDK enumerates none of them, and
#: neither does its library code.
PEER_A = "acme-bank"
PEER_B = "zenith-bank"
PEER_A_KID = "acme-bank-a2a-1"
PEER_B_KID = "zenith-bank-a2a-1"
PEER_A_PRODUCER = "sha256:producer-a"
PEER_B_PRODUCER = "sha256:producer-b"
OTHER_TENANT = "northwind-trust"
CEILING_BYTES = 8192
POLICY_SEMVER = "1.0.0"


def _fixture(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


PRODUCT_CLASS = _fixture("controlplane.yaml")["product_class"]
TENANT = _fixture("ontology.yaml")["tenant_id"]
BOUNDARY = datetime(2026, 3, 2, 11, 59, tzinfo=UTC)
POLICY_REGIME = "policy-version-fixture"


# --- fixtures --------------------------------------------------------------


def banking_product(
    *,
    tenant_id: str = TENANT,
    schema_name: str = PRODUCT_CLASS["schema_name"],
    expires_at: datetime | None = None,
    policy_regimes: frozenset[str] = frozenset({POLICY_REGIME}),
    operators: frozenset[str] = frozenset({"policy.principal-subgraph"}),
) -> ContextProductContract:
    """A Context Product from the banking fixtures' declared class."""
    return ContextProductContract(
        schema_name=schema_name,
        schema_version=PRODUCT_CLASS["schema_version"],
        plan_id=PRODUCT_CLASS["plan_id"],
        tenant_id=tenant_id,
        temporal_boundary=BOUNDARY,
        expires_at=expires_at or (BOUNDARY + timedelta(seconds=60)),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=operators,
            policy_bundle_versions=policy_regimes,
            graph_snapshot_at=BOUNDARY,
        ),
        payload={"exposure_state": "fixture"},
    )


def consumer_lineage() -> ProductLineage:
    """The consuming fabric's own lineage, disjoint from the producer's."""
    return ProductLineage(
        operators_invoked=frozenset({"temporal.as-of"}),
        policy_bundle_versions=frozenset({"consumer-policy-version"}),
        graph_snapshot_at=BOUNDARY - timedelta(days=1),
    )


def _write_key(directory: Path, key_id: str) -> ECKey:
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
def provider(key_dir: Path) -> DetachedJwsIdentityProvider:
    _write_key(key_dir, PEER_A_KID)
    _write_key(key_dir, PEER_B_KID)
    return DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )


@pytest.fixture
def keys(key_dir: Path, provider: DetachedJwsIdentityProvider) -> dict[str, ECKey]:
    return {
        PEER_A_KID: ECKey.import_key(
            json.loads((key_dir / f"{PEER_A_KID}.jwk").read_text(encoding="utf-8"))
        ),
        PEER_B_KID: ECKey.import_key(
            json.loads((key_dir / f"{PEER_B_KID}.jwk").read_text(encoding="utf-8"))
        ),
    }


def _grant(
    *,
    kid: str,
    key: ECKey,
    producer: str,
    schema_name: str = PRODUCT_CLASS["schema_name"],
    regimes: frozenset[str] = frozenset({POLICY_REGIME}),
) -> PeerTrustGrant:
    return PeerTrustGrant(
        signing_keys={kid: _public(key)},
        permitted_producer_hashes=frozenset({producer}),
        permitted_schema_names=frozenset({schema_name}),
        permitted_policy_regimes=regimes,
    )


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


@pytest.fixture
def product_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    registry.register("max-ttl/fixture", MaxTTL(seconds=300))
    version, _ = registry.resolve_latest("max-ttl/fixture")
    return register_product_class(
        registry=registry,
        schema_name=PRODUCT_CLASS["schema_name"],
        schema_version=PRODUCT_CLASS["schema_version"],
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key="max-ttl/fixture",
        max_ttl_version=version,
    )


def _register_ceiling(
    registry: ControlPlaneRegistry, *, tenant_id: str, max_bytes: int = CEILING_BYTES
) -> str:
    return registry.register_typed(
        payload_ceiling_key(tenant_id=tenant_id),
        InboundPayloadCeiling(semver=POLICY_SEMVER, max_payload_bytes=max_bytes),
        INBOUND_PAYLOAD_CEILING,
    )


def _register_policy(
    registry: ControlPlaneRegistry,
    *,
    tenant_id: str,
    peers: Mapping[str, PeerTrustGrant],
) -> str:
    return registry.register_typed(
        trust_policy_key(tenant_id=tenant_id),
        A2ATrustPolicy(semver=POLICY_SEMVER, tenant_id=tenant_id, peers=dict(peers)),
        A2A_TRUST_POLICY,
    )


@pytest.fixture
def artifact_store(tmp_path: Path) -> FileArtifactStore:
    """Where each admitted crossing's ``AdmissionRecord`` lands (D-IMPL-58).

    A real reference store rather than a double: the gate's admission path now
    depends on a successful ``put``, and a double that silently accepted anything
    would make every admission in this file pass for the wrong reason.
    """
    return FileArtifactStore(root=tmp_path / "admission-records")


def _gate(
    *,
    provider: DetachedJwsIdentityProvider,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    tenant_id: str,
    policy_version: str,
    ceiling_version: str,
    artifact_store: ArtifactStoreProtocol,
) -> A2AAdmissionGate:
    return A2AAdmissionGate(
        identity=provider,
        control_plane=registry,
        audit_log=registry.audit_log,
        artifact_store=artifact_store,
        tenant_id=tenant_id,
        trust_policy_version=policy_version,
        payload_ceiling_version=ceiling_version,
        product_classes={PRODUCT_CLASS["schema_name"]: product_class},
    )


@pytest.fixture
def two_peer_gate(
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, ECKey],
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: FileArtifactStore,
) -> A2AAdmissionGate:
    """The default fixture: two peers, distinct keys, distinct entitlements."""
    policy_version = _register_policy(
        registry,
        tenant_id=TENANT,
        peers={
            PEER_A: _grant(
                kid=PEER_A_KID, key=keys[PEER_A_KID], producer=PEER_A_PRODUCER
            ),
            PEER_B: _grant(
                kid=PEER_B_KID, key=keys[PEER_B_KID], producer=PEER_B_PRODUCER
            ),
        },
    )
    ceiling_version = _register_ceiling(registry, tenant_id=TENANT)
    return _gate(
        provider=provider,
        registry=registry,
        product_class=product_class,
        tenant_id=TENANT,
        policy_version=policy_version,
        ceiling_version=ceiling_version,
        artifact_store=artifact_store,
    )


def _inbound(
    provider: DetachedJwsIdentityProvider,
    *,
    peer_id: str,
    kid: str,
    producer: str,
    product: ContextProductContract | None = None,
    tenant_id: str = TENANT,
) -> InboundProduct:
    signed = provider.sign(
        product=product if product is not None else banking_product(),
        key_id=kid,
        assertions={PRODUCER_ASSERTION_HEADER: producer},
    )
    return InboundProduct(
        observed_peer=PeerRef(tenant_id=tenant_id, peer_id=peer_id), signed=signed
    )


def _now() -> datetime:
    return BOUNDARY + timedelta(seconds=1)


# --- the happy path, so every refusal below is a difference of one thing ---


def test_a_correctly_signed_and_entitled_product_is_admitted(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """All six checks pass and the gate yields an AdmittedProduct."""
    outcome = two_peer_gate.admit(
        inbound=_inbound(
            provider, peer_id=PEER_A, kid=PEER_A_KID, producer=PEER_A_PRODUCER
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, AdmittedProduct)
    assert outcome.product.schema_name == PRODUCT_CLASS["schema_name"]
    assert outcome.peer.peer_id == PEER_A


def test_an_admission_is_audited_as_resolved(
    provider: DetachedJwsIdentityProvider,
    two_peer_gate: A2AAdmissionGate,
    registry: ControlPlaneRegistry,
) -> None:
    """The audit plane records what was let in, not only what was turned away."""
    two_peer_gate.admit(
        inbound=_inbound(
            provider, peer_id=PEER_A, kid=PEER_A_KID, producer=PEER_A_PRODUCER
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    admitted = [
        event for event in registry.audit_events() if event.action == "a2a_admitted"
    ]
    assert len(admitted) == 1
    assert admitted[0].resolved is True
    assert admitted[0].actor == PEER_A


# --- check 1: the size ceiling, before canonicalization --------------------


def test_an_oversized_payload_is_refused_before_canonicalization(
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, ECKey],
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ceiling refuses without decoding: the canonicalizer is never reached.

    Instrumented rather than asserted by timing — the point of the ordering is
    that no decode happens, and a decode is observable.
    """
    policy_version = _register_policy(
        registry,
        tenant_id=TENANT,
        peers={
            PEER_A: _grant(
                kid=PEER_A_KID, key=keys[PEER_A_KID], producer=PEER_A_PRODUCER
            )
        },
    )
    ceiling_version = _register_ceiling(registry, tenant_id=TENANT, max_bytes=16)
    gate = _gate(
        provider=provider,
        registry=registry,
        product_class=product_class,
        tenant_id=TENANT,
        policy_version=policy_version,
        ceiling_version=ceiling_version,
        artifact_store=artifact_store,
    )
    inbound = _inbound(
        provider, peer_id=PEER_A, kid=PEER_A_KID, producer=PEER_A_PRODUCER
    )

    decoded: list[str] = []
    original = SignedContextProduct.canonical_payload

    def _watched(self: SignedContextProduct) -> bytes:
        decoded.append("decoded")
        return original(self)

    monkeypatch.setattr(SignedContextProduct, "canonical_payload", _watched)

    outcome = gate.admit(
        inbound=inbound, consumer_lineage=consumer_lineage(), now=_now()
    )
    assert isinstance(outcome, PayloadTooLargeRefusal)
    assert outcome.gate == GATE_PAYLOAD_CEILING
    assert outcome.ceiling_bytes == 16
    assert outcome.observed_bytes > 16
    assert decoded == [], "the payload was decoded despite exceeding the ceiling"


# --- check 2: signature, bound to the peer's own keys (D-23) ---------------


def test_peer_bs_product_signed_with_peer_bs_key_is_refused_as_peer_a(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """A key belonging to another peer does not admit a product as this peer."""
    inbound = _inbound(
        provider, peer_id=PEER_A, kid=PEER_B_KID, producer=PEER_A_PRODUCER
    )
    outcome = two_peer_gate.admit(
        inbound=inbound, consumer_lineage=consumer_lineage(), now=_now()
    )
    assert isinstance(outcome, SignatureRefusal)
    assert outcome.gate == GATE_SIGNATURE
    assert outcome.declared_key_id == PEER_B_KID
    assert outcome.permitted_key_ids == frozenset({PEER_A_KID})


def test_a_product_from_an_unconfigured_peer_is_refused(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """An unknown peer is refused, never treated as unconstrained."""
    outcome = two_peer_gate.admit(
        inbound=_inbound(
            provider,
            peer_id="a-peer-nobody-configured",
            kid=PEER_A_KID,
            producer=PEER_A_PRODUCER,
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, SignatureRefusal)
    assert outcome.permitted_key_ids == frozenset()


def test_a_tampered_payload_is_refused_by_the_signature_check(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """Bytes and claim disagreeing is a signature failure, not a contract one."""
    inbound = _inbound(
        provider, peer_id=PEER_A, kid=PEER_A_KID, producer=PEER_A_PRODUCER
    )
    # The payload of a *different* product, under the original's signature: the
    # two now disagree, which is exactly the substitution a detached signature
    # exists to catch.
    other = provider.sign(
        product=banking_product(operators=frozenset({"traversal.neighborhood"})),
        key_id=PEER_A_KID,
        assertions={PRODUCER_ASSERTION_HEADER: PEER_A_PRODUCER},
    )
    tampered = InboundProduct(
        observed_peer=inbound.observed_peer,
        signed=SignedContextProduct(
            payload=other.payload,
            protected=inbound.signed.protected,
            signature=inbound.signed.signature,
        ),
    )
    outcome = two_peer_gate.admit(
        inbound=tampered, consumer_lineage=consumer_lineage(), now=_now()
    )
    assert isinstance(outcome, SignatureRefusal)


# --- check 3: contract validation over the verified bytes ------------------


def test_a_payload_that_is_not_a_context_product_is_refused(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """CCF's own extra=forbid validation is the typed boundary, not the wire's."""
    outcome = two_peer_gate.admit(
        inbound=InboundProduct(
            observed_peer=PeerRef(tenant_id=TENANT, peer_id=PEER_A),
            signed=provider.sign(
                product={"schema_name": PRODUCT_CLASS["schema_name"]},
                key_id=PEER_A_KID,
                assertions={PRODUCER_ASSERTION_HEADER: PEER_A_PRODUCER},
            ),
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, ContractRefusal)
    assert outcome.gate == GATE_CONTRACT
    assert outcome.schema_name is None


def test_a_product_class_this_consumer_does_not_serve_is_refused(
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, ECKey],
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
) -> None:
    """A schema the peer may send but the consumer cannot gate is refused."""
    other = "acme-bank.some-other-product"
    policy_version = _register_policy(
        registry,
        tenant_id=TENANT,
        peers={
            PEER_A: _grant(
                kid=PEER_A_KID,
                key=keys[PEER_A_KID],
                producer=PEER_A_PRODUCER,
                schema_name=other,
            )
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
        artifact_store=artifact_store,
    )
    outcome = gate.admit(
        inbound=_inbound(
            provider,
            peer_id=PEER_A,
            kid=PEER_A_KID,
            producer=PEER_A_PRODUCER,
            product=banking_product(schema_name=other),
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, ContractRefusal)
    assert outcome.schema_name == other


# --- check 4: policy bindings (D-23 two-peer, and two-tenant) --------------


def test_peer_a_may_not_assert_a_producer_only_peer_b_is_permitted(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """Peer A's correctly signed product asserting peer B's producer is refused."""
    outcome = two_peer_gate.admit(
        inbound=_inbound(
            provider, peer_id=PEER_A, kid=PEER_A_KID, producer=PEER_B_PRODUCER
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, PolicyBindingRefusal)
    assert outcome.gate == GATE_POLICY_BINDING
    assert outcome.assertion == PRODUCER_ASSERTION_HEADER
    assert outcome.asserted == frozenset({PEER_B_PRODUCER})
    assert outcome.permitted == frozenset({PEER_A_PRODUCER})


def test_the_same_product_is_admitted_for_peer_a_and_refused_for_peer_b(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """A gate correct for one peer and wrong for two is the CR-01 defect."""
    for_a = two_peer_gate.admit(
        inbound=_inbound(
            provider, peer_id=PEER_A, kid=PEER_A_KID, producer=PEER_A_PRODUCER
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    as_b = two_peer_gate.admit(
        inbound=_inbound(
            provider, peer_id=PEER_B, kid=PEER_A_KID, producer=PEER_A_PRODUCER
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(for_a, AdmittedProduct)
    assert isinstance(as_b, SignatureRefusal)


def test_a_policy_regime_outside_the_peers_grant_is_refused(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """Both sides of the regime mismatch are on the refusal."""
    outcome = two_peer_gate.admit(
        inbound=_inbound(
            provider,
            peer_id=PEER_A,
            kid=PEER_A_KID,
            producer=PEER_A_PRODUCER,
            product=banking_product(
                policy_regimes=frozenset({POLICY_REGIME, "a-regime-nobody-granted"})
            ),
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, PolicyBindingRefusal)
    assert outcome.assertion == "policy_bundle_versions"
    assert "a-regime-nobody-granted" in outcome.asserted
    assert outcome.permitted == frozenset({POLICY_REGIME})


def test_a_product_claiming_another_tenant_is_refused(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """Trust is per tenant; a cross-tenant claim does not ride in on a signature."""
    outcome = two_peer_gate.admit(
        inbound=_inbound(
            provider,
            peer_id=PEER_A,
            kid=PEER_A_KID,
            producer=PEER_A_PRODUCER,
            product=banking_product(tenant_id=OTHER_TENANT),
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, PolicyBindingRefusal)
    assert outcome.assertion == "tenant_id"


def test_one_tenants_grant_does_not_admit_the_same_peer_for_another_tenant(
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, ECKey],
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: FileArtifactStore,
) -> None:
    """The two-tenant obligation (D-23): same peer, two policies, two verdicts."""
    permitted_version = _register_policy(
        registry,
        tenant_id=TENANT,
        peers={
            PEER_A: _grant(
                kid=PEER_A_KID, key=keys[PEER_A_KID], producer=PEER_A_PRODUCER
            )
        },
    )
    # Tenant 2 names the same peer but grants it nothing this product asserts.
    denied_version = _register_policy(
        registry,
        tenant_id=OTHER_TENANT,
        peers={
            PEER_A: _grant(
                kid=PEER_A_KID,
                key=keys[PEER_A_KID],
                producer="sha256:a-producer-only-tenant-two-trusts",
            )
        },
    )
    permitting = _gate(
        provider=provider,
        registry=registry,
        product_class=product_class,
        tenant_id=TENANT,
        policy_version=permitted_version,
        ceiling_version=_register_ceiling(registry, tenant_id=TENANT),
        artifact_store=artifact_store,
    )
    denying = _gate(
        provider=provider,
        registry=registry,
        product_class=product_class,
        tenant_id=OTHER_TENANT,
        policy_version=denied_version,
        ceiling_version=_register_ceiling(registry, tenant_id=OTHER_TENANT),
        artifact_store=artifact_store,
    )
    signed_for_tenant_one = _inbound(
        provider, peer_id=PEER_A, kid=PEER_A_KID, producer=PEER_A_PRODUCER
    )
    admitted = permitting.admit(
        inbound=signed_for_tenant_one,
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    refused = denying.admit(
        inbound=signed_for_tenant_one,
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(admitted, AdmittedProduct)
    assert isinstance(refused, PolicyBindingRefusal)


def test_a_product_whose_signed_header_asserts_no_producer_is_refused(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """A peer that will not say what produced a product cannot be held to it."""
    outcome = two_peer_gate.admit(
        inbound=InboundProduct(
            observed_peer=PeerRef(tenant_id=TENANT, peer_id=PEER_A),
            signed=provider.sign(product=banking_product(), key_id=PEER_A_KID),
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, PolicyBindingRefusal)
    assert outcome.asserted == frozenset()


# --- check 5: TTL, via the existing contract gates -------------------------


def test_a_validly_signed_but_expired_product_is_refused_by_the_ttl_gate(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """Stale replay is refused by INV-CH7-48, wired in rather than reimplemented."""
    stale = banking_product(expires_at=BOUNDARY - timedelta(seconds=1))
    outcome = two_peer_gate.admit(
        inbound=_inbound(
            provider,
            peer_id=PEER_A,
            kid=PEER_A_KID,
            producer=PEER_A_PRODUCER,
            product=stale,
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, TTLRefusal)
    assert outcome.expires_at == stale.expires_at


# --- refusals are returned values, and they are audited --------------------


@pytest.mark.parametrize(
    ("kid", "producer"),
    [(PEER_B_KID, PEER_A_PRODUCER), (PEER_A_KID, PEER_B_PRODUCER)],
)
def test_a_refusal_is_a_returned_typed_value_never_an_exception(
    provider: DetachedJwsIdentityProvider,
    two_peer_gate: A2AAdmissionGate,
    kid: str,
    producer: str,
) -> None:
    """A governance verdict a bare except could swallow is not a verdict."""
    outcome = two_peer_gate.admit(
        inbound=_inbound(
            provider, peer_id=PEER_A, kid=kid, producer=producer
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, AdmissionRefusal)
    assert not isinstance(outcome, BaseException)
    assert outcome.detail


def test_every_refusal_lands_in_the_audit_journal_as_unresolved(
    provider: DetachedJwsIdentityProvider,
    two_peer_gate: A2AAdmissionGate,
    registry: ControlPlaneRegistry,
) -> None:
    """The audit plane records what it turned away (T-05-16, T-06-43)."""
    refusals = (
        _inbound(provider, peer_id=PEER_A, kid=PEER_B_KID, producer=PEER_A_PRODUCER),
        _inbound(provider, peer_id=PEER_A, kid=PEER_A_KID, producer=PEER_B_PRODUCER),
        _inbound(
            provider,
            peer_id=PEER_A,
            kid=PEER_A_KID,
            producer=PEER_A_PRODUCER,
            product=banking_product(expires_at=BOUNDARY - timedelta(seconds=1)),
        ),
    )
    for inbound in refusals:
        assert not isinstance(
            two_peer_gate.admit(
                inbound=inbound, consumer_lineage=consumer_lineage(), now=_now()
            ),
            AdmittedProduct,
        )
    recorded = [
        event
        for event in registry.audit_events()
        if event.action == "a2a_admission_refused"
    ]
    assert len(recorded) == len(refusals)
    assert all(event.resolved is False for event in recorded)
    assert all(event.actor == PEER_A for event in recorded)


# --- check 6: lineage set-union (concrete case; the law is a property) -----


def test_admission_extends_the_consumers_lineage_rather_than_replacing_it(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """Producer and consumer entries both survive, and the producer's anchor is kept."""
    consumer = consumer_lineage()
    outcome = two_peer_gate.admit(
        inbound=_inbound(
            provider, peer_id=PEER_A, kid=PEER_A_KID, producer=PEER_A_PRODUCER
        ),
        consumer_lineage=consumer,
        now=_now(),
    )
    assert isinstance(outcome, AdmittedProduct)
    merged = outcome.lineage
    assert outcome.product.lineage.operators_invoked <= merged.operators_invoked
    assert consumer.operators_invoked <= merged.operators_invoked
    assert (
        consumer.policy_bundle_versions <= merged.policy_bundle_versions
    )
    assert merged.graph_snapshot_at == outcome.product.lineage.graph_snapshot_at


def test_union_lineage_is_what_the_gate_uses(
    provider: DetachedJwsIdentityProvider, two_peer_gate: A2AAdmissionGate
) -> None:
    """The gate's merge is the same function the property suite pins."""
    consumer = consumer_lineage()
    outcome = two_peer_gate.admit(
        inbound=_inbound(
            provider, peer_id=PEER_A, kid=PEER_A_KID, producer=PEER_A_PRODUCER
        ),
        consumer_lineage=consumer,
        now=_now(),
    )
    assert isinstance(outcome, AdmittedProduct)
    assert outcome.lineage == union_lineage(
        producer=outcome.product.lineage, consumer=consumer
    )


# --- structural: the admitted type, and the transport's reach --------------


def test_an_admitted_product_cannot_be_constructed_outside_the_gate() -> None:
    """Admission is the only path by which a product becomes offerable to L2."""
    with pytest.raises(AdmissionBypassError):
        AdmittedProduct(
            banking_product(),
            consumer_lineage(),
            PeerRef(tenant_id=TENANT, peer_id=PEER_A),
            object(),
        )


#: The fabric write surfaces a transport must not be able to name. Reused from
#: ``tests/agents/test_consumption_discipline.py`` rather than restated with a
#: second, divergent list.
WRITE_SURFACE_NAMES = frozenset(
    {
        "AssemblyWorker",
        "BaseGraphWriter",
        "BootToken",
        "GraphStore",
        "GraphWriter",
        "OperatorEngine",
        "OperatorPlanner",
    }
)


def test_a_wire_protocol_implementation_can_name_no_write_surface() -> None:
    """A transport holds no route to L2, assembly, or the graph (D-12, T-06-38)."""
    import inspect

    for name, member in inspect.getmembers(
        WireProtocol, predicate=inspect.isfunction
    ):
        if name.startswith("_"):
            continue
        signature = inspect.signature(member)
        annotations = [str(signature.return_annotation)] + [
            str(parameter.annotation)
            for parameter in signature.parameters.values()
        ]
        for annotation in annotations:
            assert not any(
                surface in annotation for surface in WRITE_SURFACE_NAMES
            ), f"WireProtocol.{name} names a fabric write surface: {annotation}"
        for forbidden in ("L2", "assembly", "graph", "Graph"):
            assert forbidden not in str(signature.return_annotation)
