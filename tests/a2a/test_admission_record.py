"""The merged federated lineage, observed in persisted state (B2 closure).

This file is what D-IMPL-58's closure item 3 names. Dave's ruling of 2026-07-27
is **reading (d)**: the merged ``ProductLineage`` a Peering admission computes is
persisted at the boundary crossing as an immutable ``AdmissionRecord`` artifact,
and ``src/ccf/contracts/claims.py`` is not touched. The defect this closes is
precise, and every assertion below is drafted from it: ``admit`` computed a union
into ``AdmittedProduct.lineage`` and **nothing read it** — ``ingest_admitted``
reads ``admitted.product`` and never ``admitted.lineage`` — so a "lineage
continuity" claim was a property of a wrapper L2 discards.

Consequences for how this module is written:

* **The union is observed against retrieved artifact bytes, never against the
  wrapper.** Asserting on ``AdmittedProduct.lineage`` is exactly what made the
  property vacuous, so no assertion body here reads it.
* **The union is asserted per axis**, so dropping any one of
  ``operators_invoked``, ``policy_bundle_versions`` or ``graph_snapshot_at``
  turns a test red rather than passing on the two that remain.
* **Resolution goes through the replay path in** :mod:`ccf.replay.engine`, not
  through a test-local ``store.get``: a closure item verified only inside a test
  module is not verified.
* **``claims.py`` is asserted unchanged by content hash**, so reading (a) cannot
  creep back in later without a red test.

Every domain value — peer id, key id, producer hash, schema, policy regime,
tenant, ceiling, semver — comes from ``tests/fixtures/banking/*.yaml`` (CINV-01).
Operator keys come from :mod:`ccf.operators.categories` because an operator key
is *mechanism* declared in ``/src``, not a deployment value.
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
    ADMISSION_RECORD,
    INBOUND_PAYLOAD_CEILING,
    PRODUCER_ASSERTION_HEADER,
    A2AAdmissionGate,
    AdmissionNotRecorded,
    AdmissionRecord,
    AdmittedProduct,
    InboundPayloadCeiling,
    payload_ceiling_key,
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
from ccf.a2a.wire import InboundProduct, PeerRef
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreError
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.operators.categories import PolicyFilter, TemporalAsOf, TraversalNeighborhood
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


def _fixture(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


A2A = _fixture("a2a.yaml")
PRODUCT_CLASS = _fixture("controlplane.yaml")["product_class"]
TENANT = _fixture("ontology.yaml")["tenant_id"]

PEER = A2A["peers"]["first"]["peer_id"]
PEER_KID = A2A["peers"]["first"]["key_id"]
PEER_PRODUCER = A2A["peers"]["first"]["producer_hash"]
CEILING_BYTES = A2A["consumer"]["inbound_payload_ceiling_bytes"]
POLICY_SEMVER = A2A["consumer"]["semver"]
POLICY_REGIME = _fixture("controlplane.yaml")["policy_bundle"]["regime"]

#: Operator keys are *mechanism* declared in ``ccf.operators.categories``, so
#: they are read from there rather than restated as literals here — a restated
#: name is the one place a drift could hide.
PRODUCER_OPERATORS = frozenset({PolicyFilter.key, TraversalNeighborhood.key})
CONSUMER_OPERATORS = frozenset({TemporalAsOf.key})

BOUNDARY = datetime(2026, 3, 2, 11, 59, tzinfo=UTC)
MAX_TTL_KEY = "test/admission-record/max-ttl"


def _producer_lineage() -> ProductLineage:
    return ProductLineage(
        operators_invoked=PRODUCER_OPERATORS,
        policy_bundle_versions=frozenset({POLICY_REGIME}),
        graph_snapshot_at=BOUNDARY,
    )


def _consumer_lineage() -> ProductLineage:
    """The consuming fabric's own lineage.

    Deliberately disjoint from the producer's on all three axes: a union test
    against overlapping sets could pass while dropping a side.
    """
    return ProductLineage(
        operators_invoked=CONSUMER_OPERATORS,
        policy_bundle_versions=frozenset({"consumer-policy-version"}),
        graph_snapshot_at=BOUNDARY - timedelta(days=1),
    )


def _record() -> AdmissionRecord:
    producer = _producer_lineage()
    consumer = _consumer_lineage()
    return AdmissionRecord(
        tenant_id="tenant-under-test",
        peer_id="peer-under-test",
        product_content_address="0" * 64,
        producer_lineage=producer,
        consumer_lineage=consumer,
        merged_lineage=ProductLineage(
            operators_invoked=(
                producer.operators_invoked | consumer.operators_invoked
            ),
            policy_bundle_versions=(
                producer.policy_bundle_versions | consumer.policy_bundle_versions
            ),
            graph_snapshot_at=producer.graph_snapshot_at,
        ),
        admitted_at=BOUNDARY + timedelta(seconds=1),
    )


# --- Task 1: the artifact class -------------------------------------------


def test_the_class_id_follows_the_established_convention() -> None:
    """Dot-namespaced and kebab-cased, like every other class in the family.

    Pinned as a test rather than left to review because D-IMPL-58's amendment of
    2026-07-27 records a non-conforming id (``admission_record``) that was one
    plan-execution away from landing with the decision log's authority behind it.
    """
    assert ADMISSION_RECORD.class_id == "ccf.admission-record"
    assert ADMISSION_RECORD.contract is AdmissionRecord


def test_the_record_is_a_closed_world_contract() -> None:
    """``extra=forbid`` and frozen, by inheritance — a record is not a mapping."""
    assert issubclass(AdmissionRecord, CCFContract)
    record = _record()
    assert ADMISSION_RECORD.validate(record) is record


def test_the_record_decomposes_into_both_sides_of_its_merge() -> None:
    """A union that cannot be decomposed cannot be audited.

    Producer and consumer are carried *alongside* the merge, so an examiner can
    see which side contributed what rather than being handed a set and asked to
    trust it.
    """
    record = _record()
    assert record.producer_lineage == _producer_lineage()
    assert record.consumer_lineage == _consumer_lineage()
    assert (
        record.merged_lineage.operators_invoked
        == record.producer_lineage.operators_invoked
        | record.consumer_lineage.operators_invoked
    )


def test_the_record_is_content_addressable_and_therefore_immutable() -> None:
    """Two admissions of byte-identical content produce the same address.

    Which is what makes the class immutable per D-IMPL-27 without needing an
    ``overwrite`` flag anywhere: content addressing makes overwrite meaningless.
    """
    assert content_hash(_record()) == content_hash(_record())
    assert len(content_hash(_record())) == 64


# --- the gate harness ------------------------------------------------------


def banking_product() -> ContextProductContract:
    """A Context Product from the banking fixtures' declared class."""
    return ContextProductContract(
        schema_name=PRODUCT_CLASS["schema_name"],
        schema_version=PRODUCT_CLASS["schema_version"],
        plan_id=PRODUCT_CLASS["plan_id"],
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        expires_at=BOUNDARY + timedelta(seconds=60),
        ttl_anchor="from_decision",
        lineage=_producer_lineage(),
        payload={"exposure_state": "fixture"},
    )


def _now() -> datetime:
    return BOUNDARY + timedelta(seconds=1)


@pytest.fixture
def key_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "keys"
    directory.mkdir()
    key = ECKey.generate_key("P-256", parameters={"kid": PEER_KID})
    (directory / f"{PEER_KID}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return directory


@pytest.fixture
def provider(key_dir: Path) -> DetachedJwsIdentityProvider:
    return DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )


@pytest.fixture
def public_key(key_dir: Path) -> JsonWebKey:
    key = ECKey.import_key(
        json.loads((key_dir / f"{PEER_KID}.jwk").read_text(encoding="utf-8"))
    )
    public: Mapping[str, str] = key.as_dict(private=False)
    return public


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


@pytest.fixture
def store(tmp_path: Path) -> FileArtifactStore:
    """The same ``ArtifactStoreProtocol`` surface the conformance suite bars.

    A real reference store rather than a bespoke double: a double would let the
    record "persist" into something no deployment could resolve it from, which is
    the class of false green this file exists to prevent.
    """
    return FileArtifactStore(root=tmp_path / "artifacts")


@pytest.fixture
def product_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    version = registry.register(MAX_TTL_KEY, MaxTTL(seconds=300))
    return register_product_class(
        registry=registry,
        schema_name=PRODUCT_CLASS["schema_name"],
        schema_version=PRODUCT_CLASS["schema_version"],
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=MAX_TTL_KEY,
        max_ttl_version=version,
    )


def _build_gate(
    *,
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: Any,
) -> A2AAdmissionGate:
    policy_version = registry.register_typed(
        trust_policy_key(tenant_id=TENANT),
        A2ATrustPolicy(
            semver=POLICY_SEMVER,
            tenant_id=TENANT,
            peers={
                PEER: PeerTrustGrant(
                    signing_keys={PEER_KID: public_key},
                    permitted_producer_hashes=frozenset({PEER_PRODUCER}),
                    permitted_schema_names=frozenset(
                        {PRODUCT_CLASS["schema_name"]}
                    ),
                    permitted_policy_regimes=frozenset({POLICY_REGIME}),
                )
            },
        ),
        A2A_TRUST_POLICY,
    )
    ceiling_version = registry.register_typed(
        payload_ceiling_key(tenant_id=TENANT),
        InboundPayloadCeiling(
            semver=POLICY_SEMVER, max_payload_bytes=CEILING_BYTES
        ),
        INBOUND_PAYLOAD_CEILING,
    )
    return A2AAdmissionGate(
        identity=provider,
        control_plane=registry,
        audit_log=registry.audit_log,
        artifact_store=artifact_store,
        tenant_id=TENANT,
        trust_policy_version=policy_version,
        payload_ceiling_version=ceiling_version,
        product_classes={PRODUCT_CLASS["schema_name"]: product_class},
    )


@pytest.fixture
def gate(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
) -> A2AAdmissionGate:
    return _build_gate(
        provider=provider,
        public_key=public_key,
        registry=registry,
        product_class=product_class,
        artifact_store=store,
    )


def _sign(
    provider: DetachedJwsIdentityProvider, *, product: object
) -> SignedContextProduct:
    return provider.sign(
        product=product,
        key_id=PEER_KID,
        assertions={PRODUCER_ASSERTION_HEADER: PEER_PRODUCER},
    )


def _inbound(signed: SignedContextProduct) -> InboundProduct:
    return InboundProduct(
        observed_peer=PeerRef(tenant_id=TENANT, peer_id=PEER), signed=signed
    )


def _admit(gate: A2AAdmissionGate, provider: DetachedJwsIdentityProvider) -> Any:
    return gate.admit(
        inbound=_inbound(_sign(provider, product=banking_product())),
        consumer_lineage=_consumer_lineage(),
        now=_now(),
    )


# --- Task 2: admission persists the record --------------------------------


def test_an_admission_persists_an_admission_record(
    gate: A2AAdmissionGate,
    provider: DetachedJwsIdentityProvider,
    registry: ControlPlaneRegistry,
    store: FileArtifactStore,
) -> None:
    """The crossing leaves a durable record of *what* crossed.

    This is the property whose absence was blocking finding B2: the union was
    computed and then discarded with the wrapper.
    """
    outcome = _admit(gate, provider)
    assert isinstance(outcome, AdmittedProduct)

    admitted = [
        event
        for event in registry.audit_events()
        if event.action == "a2a_admitted"
    ]
    assert len(admitted) == 1
    assert store.exists(content_address=admitted[0].version)


def test_the_audit_append_carries_the_reference_triple(
    gate: A2AAdmissionGate,
    provider: DetachedJwsIdentityProvider,
    registry: ControlPlaneRegistry,
) -> None:
    """No new audit shape: the existing scalar append points at the artifact.

    D-IMPL-58's correction paragraph is explicit that ``AuditLog.append`` carries
    scalars only and gains no payload field. What the verdict gains is the
    ``artifact_class`` / ``key`` / ``version`` triple naming the record that
    carries the substance.
    """
    _admit(gate, provider)
    event = next(
        event
        for event in registry.audit_events()
        if event.action == "a2a_admitted"
    )
    assert event.artifact_class == ADMISSION_RECORD.class_id
    assert event.artifact_class == "ccf.admission-record"
    assert event.key
    assert len(event.version) == 64
    assert event.resolved is True
    assert event.actor == PEER


def test_a_refusal_persists_no_admission_record(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
) -> None:
    """There was no crossing to record — but the refusal is still audited.

    Both halves matter. A refusal that wrote a record would assert a crossing
    that did not happen; a refusal that stopped being audited would trade one
    repudiation hole for another.
    """
    gate = _build_gate(
        provider=provider,
        public_key=public_key,
        registry=registry,
        product_class=product_class,
        artifact_store=store,
    )
    unentitled = banking_product().model_copy(
        update={
            "lineage": ProductLineage(
                operators_invoked=PRODUCER_OPERATORS,
                policy_bundle_versions=frozenset(
                    {"a-regime-this-peer-may-not-claim"}
                ),
                graph_snapshot_at=BOUNDARY,
            )
        }
    )
    outcome = gate.admit(
        inbound=_inbound(_sign(provider, product=unentitled)),
        consumer_lineage=_consumer_lineage(),
        now=_now(),
    )
    assert not isinstance(outcome, AdmittedProduct)

    refused = [
        event
        for event in registry.audit_events()
        if event.action == "a2a_admission_refused"
    ]
    assert len(refused) == 1
    assert refused[0].resolved is False
    assert not [path for path in store.root.glob("*") if path.is_file()]


def test_a_store_outage_is_not_reported_as_an_admission(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
) -> None:
    """A crossing whose record was not persisted must not be reported admitted.

    Raised rather than refused, on this module's own established discipline: a
    fabric that cannot write to its own substrate is a broken deployment, not a
    badly behaved peer, and reporting the two the same way would let an outage
    read as a federation dispute. It is the reasoning
    :class:`~ccf.replay.serve.ReplayWriter` applies to serving — a failure to
    record is a failure to serve — applied to admitting.
    """

    class _BrokenStore:
        def put(self, **_: Any) -> ArtifactRef:
            raise ArtifactStoreError("the substrate is unreachable")

        def get(self, *, content_address: str) -> bytes:
            raise ArtifactStoreError("the substrate is unreachable")

        def exists(self, *, content_address: str) -> bool:
            return False

        def resolve_uri(self, *, uri: str) -> str:
            raise ArtifactStoreError("the substrate is unreachable")

    gate = _build_gate(
        provider=provider,
        public_key=public_key,
        registry=registry,
        product_class=product_class,
        artifact_store=_BrokenStore(),
    )
    with pytest.raises(AdmissionNotRecorded):
        _admit(gate, provider)


def test_the_gate_holds_no_graph_write_handle(
    gate: A2AAdmissionGate,
) -> None:
    """Single-writer survives this: the store is a substrate, not a second writer.

    Asserted as a negative as well as a positive, because "the gate has a store"
    is compatible with the gate having quietly acquired a graph handle too.
    Nothing the gate holds comes from :mod:`ccf.graph`.
    """
    held = [type(value).__module__ for value in vars(gate).values()]
    assert not [module for module in held if module.startswith("ccf.graph")]
