"""Attributability across a Peering, made structural rather than asserted.

This file is what D-IMPL-57's closure item 3 names. Dave's ruling of 2026-07-27
(reading (a)) is that INV-CH7-47 is *verifiable within a fabric, attributable
across one* — products admitted through a Peering (D-IMPL-59) are attributable;
locally assembled products are verifiable. That reading is only sound if the
declared lineage is genuinely inside the signed material, and only honest if the
gate that claims to check attribution has a failure mode that fires. Both are
pinned here, and each assertion is drafted from what a *broken* gate would do:

* a gate that compared the declared operator set against itself would pass every
  case in this file while checking nothing — the precise defect blocking finding
  B1 named — so the load-bearing case drives a **real mismatch through**
  :meth:`~ccf.a2a.admission.A2AAdmissionGate.admit`, never through
  ``run_federated_gates`` with a hand-supplied address;
* a gate whose only reachable mismatch required calling it directly would be the
  original defect wearing a new label, so the mismatch here is produced the way
  a real peer could produce it: a payload the peer genuinely signed which is
  valid JSON for the contract but is *not* ``canonical_bytes(product)``;
* a signature that did not cover ``lineage`` would make attributability nil, so
  mutating only the declared operator plan is asserted to fail verification;
* a suite with no untampered control could pass for an unrelated reason, so the
  sensitivity guard admits the same fixture's product unmodified.

Every value — peer id, key id, producer hash, schema, policy regime, operator
names, tenant — comes from ``tests/fixtures/banking/*.yaml`` (CINV-01: nothing
domain-shaped is authored in this module).
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
    INBOUND_PAYLOAD_CEILING,
    PRODUCER_ASSERTION_HEADER,
    A2AAdmissionGate,
    AdmittedProduct,
    InboundPayloadCeiling,
    SignatureRefusal,
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
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.operators.categories import (
    PolicyFilter,
    SimilaritySelect,
    TemporalAsOf,
    TraversalNeighborhood,
)
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import (
    GATE_LINEAGE_ATTRIBUTABILITY,
    LineageAttributionRefusal,
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

#: Operator keys come from the SDK's own operator categories, not from a string
#: authored here: an operator key is *mechanism* (it is declared in
#: ``ccf.operators.categories``), so restating one in a test module would be the
#: one place a drifted name could hide.
OPERATORS = frozenset({PolicyFilter.key, TraversalNeighborhood.key})
#: A policy regime is a deployment value; this one is the banking fixture's.
POLICY_REGIME = _fixture("controlplane.yaml")["policy_bundle"]["regime"]
BOUNDARY = datetime(2026, 3, 2, 11, 59, tzinfo=UTC)
MAX_TTL_KEY = "test/federated-attribution/max-ttl"


def _now() -> datetime:
    return BOUNDARY + timedelta(seconds=1)


def banking_product(
    *, operators: frozenset[str] = OPERATORS
) -> ContextProductContract:
    """A Context Product from the banking fixtures' declared class."""
    return ContextProductContract(
        schema_name=PRODUCT_CLASS["schema_name"],
        schema_version=PRODUCT_CLASS["schema_version"],
        plan_id=PRODUCT_CLASS["plan_id"],
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        expires_at=BOUNDARY + timedelta(seconds=60),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=operators,
            policy_bundle_versions=frozenset({POLICY_REGIME}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload={"exposure_state": "fixture"},
    )


def consumer_lineage() -> ProductLineage:
    return ProductLineage(
        operators_invoked=frozenset({TemporalAsOf.key}),
        policy_bundle_versions=frozenset({"consumer-policy-version"}),
        graph_snapshot_at=BOUNDARY - timedelta(days=1),
    )


# --- fixtures --------------------------------------------------------------


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


@pytest.fixture
def artifact_store(tmp_path: Path) -> FileArtifactStore:
    """Where an admitted crossing's ``AdmissionRecord`` lands (D-IMPL-58).

    Present because admission now persists a record before reporting success;
    the sensitivity guard in this file would otherwise fail for a reason that has
    nothing to do with attributability.
    """
    return FileArtifactStore(root=tmp_path / "admission-records")


@pytest.fixture
def gate(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: FileArtifactStore,
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


def _non_canonical_but_valid(product: ContextProductContract) -> dict[str, Any]:
    """Return a JSON body the contract accepts that is not the canonical form.

    The lever is timestamp precision, not key order: ``canonical_bytes`` sorts
    keys itself, so re-ordering them is a no-op, while its fixed-microsecond
    RFC3339 rendering is *one* of several forms the contract's own parser
    accepts. A peer whose serializer trims a zero microsecond field therefore
    signs bytes that parse to an equal product under a different address —
    which is exactly the condition the attributability gate exists to catch,
    arrived at without anybody behaving maliciously.
    """
    body: dict[str, Any] = json.loads(canonical_bytes(product))
    rendered = body["temporal_boundary"]
    assert isinstance(rendered, str) and rendered.endswith(".000000Z")
    body["temporal_boundary"] = rendered.replace(".000000Z", "Z")
    return body


# --- the sensitivity guard: the untampered product is admitted -------------


def test_the_untampered_fixture_product_is_admitted(
    provider: DetachedJwsIdentityProvider, gate: A2AAdmissionGate
) -> None:
    """Without this, every refusal below could be passing for another reason."""
    outcome = gate.admit(
        inbound=_inbound(_sign(provider, product=banking_product())),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, AdmittedProduct)
    assert outcome.product.lineage.operators_invoked == OPERATORS


# --- the property reading (a) stands or falls on ---------------------------


def test_mutating_a_signed_products_declared_lineage_breaks_verification(
    provider: DetachedJwsIdentityProvider, gate: A2AAdmissionGate
) -> None:
    """Attributability is sound only because ``lineage`` is inside the signature.

    The mutation is of *nothing but* the declared operator plan, re-presented
    under the original detached signature. Admission refuses at the signature
    check — not at a later one — because a claim carried outside the signature
    would be attributable to nobody, and reading (a) would then be strictly
    worse than refusing to run the gate at all (D-IMPL-57).
    """
    original = _sign(provider, product=banking_product())
    mutated = _sign(
        provider,
        product=banking_product(operators=OPERATORS | {SimilaritySelect.key}),
    )
    tampered = _inbound(
        SignedContextProduct(
            payload=mutated.payload,
            protected=original.protected,
            signature=original.signature,
        )
    )
    outcome = gate.admit(
        inbound=tampered, consumer_lineage=consumer_lineage(), now=_now()
    )
    assert isinstance(outcome, SignatureRefusal)
    assert not isinstance(outcome, LineageAttributionRefusal)


# --- the attributability gate, reached through ``admit`` -------------------


def test_a_signed_but_non_canonical_payload_is_refused_as_unattributable(
    provider: DetachedJwsIdentityProvider,
    gate: A2AAdmissionGate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Signature verification succeeds; attributability still refuses.

    The bytes are genuinely the peer's, signed with a key its trust-policy entry
    entitles it to use, and they parse to a product *equal* to the one the peer
    meant to send. What differs is the address: ``admit`` measured the payload as
    received, while the parsed product's canonical form is something else. So the
    declared operator plan is not covered by the address the signature verified,
    and the product is refused as unattributable rather than admitted on a claim
    nothing anchors.

    Driven through :meth:`~ccf.a2a.admission.A2AAdmissionGate.admit` rather than
    through ``run_federated_gates``: a gate that can only fail when called
    directly with a hand-supplied mismatched address is the original defect
    wearing a new label.
    """
    product = banking_product()
    verified: list[bool] = []
    original_verify = DetachedJwsIdentityProvider.verify

    def _watched(
        self: DetachedJwsIdentityProvider, **kwargs: Any
    ) -> bytes:
        payload = original_verify(self, **kwargs)
        verified.append(True)
        return payload

    monkeypatch.setattr(DetachedJwsIdentityProvider, "verify", _watched)

    signed = _sign(provider, product=_non_canonical_but_valid(product))
    outcome = gate.admit(
        inbound=_inbound(signed), consumer_lineage=consumer_lineage(), now=_now()
    )

    assert verified == [True], "the signature check did not succeed"
    assert isinstance(outcome, LineageAttributionRefusal)
    assert outcome.gate == GATE_LINEAGE_ATTRIBUTABILITY
    assert outcome.attested_address == signed.content_address()
    assert outcome.candidate_address == content_hash(product)
    assert outcome.attested_address != outcome.candidate_address
    assert outcome.declared == OPERATORS
    assert outcome.detail


def test_the_refused_payload_parses_to_an_equal_product(
    provider: DetachedJwsIdentityProvider,
) -> None:
    """The refusal is about *bytes*, not about a malformed or different product.

    Stated separately because it is what makes the previous test's case a
    genuine attributability failure rather than a contract failure in disguise:
    a reader must be able to see that nothing about the product changed.
    """
    product = banking_product()
    body = _non_canonical_but_valid(product)
    parsed = ContextProductContract.model_validate_json(
        canonical_bytes(body)
    )
    assert parsed == product
    assert content_hash(parsed) != content_hash(body)


def test_an_attributability_refusal_is_audited_as_unresolved(
    provider: DetachedJwsIdentityProvider,
    gate: A2AAdmissionGate,
    registry: ControlPlaneRegistry,
) -> None:
    """Every refusal on the federated path is audited, as the other five are."""
    outcome = gate.admit(
        inbound=_inbound(
            _sign(provider, product=_non_canonical_but_valid(banking_product()))
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, LineageAttributionRefusal)
    recorded = [
        event
        for event in registry.audit_events()
        if event.action == "a2a_admission_refused"
    ]
    assert len(recorded) == 1
    assert recorded[0].resolved is False
    assert recorded[0].actor == PEER


def test_the_refusal_is_a_returned_value_never_an_exception(
    provider: DetachedJwsIdentityProvider, gate: A2AAdmissionGate
) -> None:
    """A governance verdict a bare ``except`` could swallow is not a verdict."""
    outcome = gate.admit(
        inbound=_inbound(
            _sign(provider, product=_non_canonical_but_valid(banking_product()))
        ),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(outcome, LineageAttributionRefusal)
    assert not isinstance(outcome, BaseException)
