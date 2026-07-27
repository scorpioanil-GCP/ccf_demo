"""A2A end to end: two producer processes, one consumer, one Control Plane gate.

XPRC-02; CLAUDE.md §7.2; whitepaper §8.3 Pattern 4. The question this file
answers per assertion is the D-02 one — *would this catch the invariant being
broken?* — so every row below is drafted from what a broken consumer would do
rather than from what the plan intends.

=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
single-writer across A2A (CLAUDE.md §10,   the transport has no writer to hand
criterion 4)                               out; every admitted claim below
                                           reaches L3 through ``worker.ingest``
                                           and this module asserts there is no
                                           other call site in the consumer
gate before assembly (CLAUDE.md §7.2,      a product that failed the gate would
D-IMPL-16)                                 otherwise appear in L3; the refused
                                           message's own entities are absent
                                           and the graph file is byte-identical
lineage continuity by union (D-14)         replacement instead of union would
                                           drop the producer's operator plan or
                                           the consumer's, and the producer's
                                           graph snapshot anchor would be lost
process separation (D-15)                  an in-process double would share a
                                           heap, and "the consumer holds no
                                           write handle to the producer's
                                           graph" would be vacuous rather than
                                           literally true
per-peer entitlement (D-23)                one peer's key or grant would admit
                                           another peer's product; a
                                           single-principal proof passes
                                           against exactly that defect
canonical bytes survive the wire           any re-serialization en route would
(T-06-47)                                  change the bytes the signature was
                                           made over, and the genuine product
                                           would refuse alongside the tampered
                                           one
=========================================  ===================================

Every domain value — the tenant, the product class, the peer identifiers, the
producer hashes, the ceilings, the endpoint path, the federation entity class —
comes from ``tests/fixtures/banking/``. Key *material* is generated per test
into a temp directory and never committed. Nothing here is sleep-gated:
readiness is the 06-04 fixture's stdout handshake, and the children emit before
they announce, so the parent's blocking ``readline()`` is also the gate on the
exchange having happened.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import socket
import threading
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn
import yaml
from joserfc.jwk import ECKey

from ccf.a2a.admission import (
    INBOUND_PAYLOAD_CEILING,
    A2AAdmissionGate,
    AdmissionRefusal,
    AdmittedProduct,
    InboundPayloadCeiling,
    SignatureRefusal,
    payload_ceiling_key,
)
from ccf.a2a.trust_policy import (
    A2A_TRUST_POLICY,
    A2ATrustPolicy,
    PeerTrustGrant,
    trust_policy_key,
)
from ccf.a2a.wire import InboundProduct, PeerRef, WireProtocol
from ccf.assembly.worker import EntityResolutionRule, EntityResolutionSpec
from ccf.boot import FabricHandle, boot
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import GateRefusal
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

from ccf_runtime.a2a.typed_http import TypedHttpWire

from crossproc.conftest import spawn_child_server
from crossproc.servers import a2a_producer_child as child
from integration.test_proto_quickstart import _instant, _resolution_spec

pytestmark = pytest.mark.crossproc

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"

PRODUCER_CHILD = (
    Path(__file__).resolve().parent / "servers" / "a2a_producer_child.py"
)


def _fixture(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


ONTOLOGY = _fixture("ontology.yaml")
CONTROL = _fixture("controlplane.yaml")
FEDERATION = _fixture("a2a.yaml")

TENANT: str = ONTOLOGY["tenant_id"]
PRODUCT_CLASS = CONTROL["product_class"]
CONSUMER = FEDERATION["consumer"]
PEERS = FEDERATION["peers"]

#: The Control Plane version the producer's fabric registers its policy bundle
#: under. Computed rather than transcribed: the registry versions an artifact by
#: its content hash, so the consumer can state which regime a peer is entitled
#: to claim without the two fixtures having to agree on a literal.
PRODUCER_POLICY_VERSION = content_hash(CONTROL["policy_bundle"])


# --- the consumer deployment -----------------------------------------------


@dataclass
class Consumer:
    """One consuming fabric, its gate, and what arrived over the wire."""

    handle: FabricHandle
    database_path: Path
    gate: A2AAdmissionGate
    wire: TypedHttpWire
    now: datetime
    lineage: ProductLineage
    inbound: dict[str, tuple[InboundProduct, ...]]

    def graph_digest(self) -> str:
        """The consumer's L3 substrate, byte for byte.

        Hashing the substrate rather than querying the graph is deliberate: a
        query only sees the rows a reader thought to ask about, while the digest
        covers every byte the substrate holds — including any a second writer
        would have added.

        **The write-ahead log is part of the substrate.** The SQLite backend
        runs in WAL mode, so a committed write lands in ``<db>-wal`` and the
        main file can stay byte-identical for a long time. A digest over the
        main file alone would therefore report "unchanged" after a real write,
        which would make an unchanged-assertion pass for the wrong reason —
        exactly the class of false observable this suite exists to avoid. The
        shared-memory index (``-shm``) is excluded: it is process coordination
        state, not durable content, and it churns on reads.
        """
        digest = sha256()
        for suffix in ("", "-wal"):
            path = self.database_path.with_name(self.database_path.name + suffix)
            digest.update(path.read_bytes() if path.exists() else b"")
        return digest.hexdigest()


def _consumer_resolution_spec() -> EntityResolutionSpec:
    """The banking spec, extended with the consumer's federation ingress rule.

    The producer's entities arrive as claims about *another* fabric's graph, so
    they resolve into their own declared entity class rather than merging into
    the consumer's counterparty/facility/covenant vocabulary — merging would
    assert the consumer had independently observed what a peer told it.
    """
    banking = _resolution_spec(ONTOLOGY)
    declared = FEDERATION["federation"]["entity_rule"]
    return EntityResolutionSpec(
        entity_rules=(
            *banking.entity_rules,
            EntityResolutionRule(
                match_key=declared["match_key"],
                entity_class=declared["entity_class"],
                identity_keys=tuple(declared["identity_keys"]),
                attribute_keys=tuple(declared["attribute_keys"]),
            ),
        ),
        relationship_rules=banking.relationship_rules,
    )


def _write_key(directory: Path, key_id: str) -> ECKey:
    key = ECKey.generate_key("P-256", parameters={"kid": key_id})
    (directory / f"{key_id}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return key


def _grant(key: ECKey, declared: Any) -> PeerTrustGrant:
    """One peer's entitlements, exactly as the fixture declares them."""
    return PeerTrustGrant(
        signing_keys={declared["key_id"]: key.as_dict(private=False)},
        permitted_producer_hashes=frozenset({declared["producer_hash"]}),
        permitted_schema_names=frozenset({PRODUCT_CLASS["schema_name"]}),
        permitted_policy_regimes=frozenset({PRODUCER_POLICY_VERSION}),
    )


def _product_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    max_ttl_version = registry.register(
        CONTROL["keys"]["max_ttl"], MaxTTL(seconds=CONTROL["max_ttl_seconds"])
    )
    return register_product_class(
        registry=registry,
        schema_name=PRODUCT_CLASS["schema_name"],
        schema_version=PRODUCT_CLASS["schema_version"],
        ttl_anchor=PRODUCT_CLASS["ttl_anchor"],
        assembly_mode=PRODUCT_CLASS["assembly_mode"],
        max_ttl_key=CONTROL["keys"]["max_ttl"],
        max_ttl_version=max_ttl_version,
    )


@contextmanager
def _hosted(wire: TypedHttpWire) -> Iterator[str]:
    """Host ``wire``'s endpoint on an ephemeral loopback port; yield its URL.

    The consumer is the parent here, so the 06-04 fixture's roles are inverted:
    the parent listens and the children connect. The mechanics are the same
    ones and for the same reasons — bind port 0 first so the port is known
    before the server starts, hand the bound socket to uvicorn, and gate on the
    server's own ``started`` flag rather than on a duration.

    The address is assembled test-side. ``/src`` and ``/runtime`` hold no host
    and no port (CINV-01); the deployment — here, the test — chooses the
    interface, and choosing loopback is what keeps the proof off any routable
    one.
    """
    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(64)
    port = bound.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(wire.asgi_app(), log_level="error"))
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [bound]}, daemon=True
    )
    thread.start()
    try:
        # Polling this process's own server object, not a parent-side
        # sleep-and-hope: it observes a real state flag rather than guessing a
        # duration, and nothing proceeds until the flag flips.
        while not server.started:
            if not thread.is_alive():
                raise AssertionError("the consumer endpoint failed to start")
        yield f"http://127.0.0.1:{port}{wire.receive_path}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        bound.close()


def _spawn_producer(
    stack: ExitStack, *, declared: Any, key_dir: Path, url: str
) -> None:
    """Run one producer child to completion of its two emissions.

    The child emits before it announces, so ``spawn_child_server`` returning is
    the guarantee that both carriages were accepted. Its lifetime is bound to
    ``stack`` so the fixture's ``terminate → wait → kill`` teardown still runs
    if an assertion below fails (T-06-17).
    """
    os.environ[child.CONSUMER_URL_VAR] = url
    os.environ[child.PEER_ID_VAR] = declared["peer_id"]
    os.environ[child.KEY_ID_VAR] = declared["key_id"]
    os.environ[child.PRODUCER_HASH_VAR] = declared["producer_hash"]
    os.environ[child.TENANT_VAR] = TENANT
    os.environ[child.KEY_DIR_VAR] = str(key_dir)
    stack.enter_context(spawn_child_server(PRODUCER_CHILD))


@pytest.fixture
def consumer(tmp_path: Path) -> Iterator[Consumer]:
    """Boot a consuming fabric, host its endpoint, and run both producers."""
    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    keys = {
        name: _write_key(key_dir, declared["key_id"])
        for name, declared in PEERS.items()
    }

    registry = ControlPlaneRegistry()
    spec_version = registry.register(
        CONTROL["keys"]["resolution_spec"], _consumer_resolution_spec()
    )
    policy_version = registry.register(
        CONTROL["keys"]["policy_bundle"], CONTROL["policy_bundle"]
    )
    assert policy_version == PRODUCER_POLICY_VERSION

    trust_version = registry.register_typed(
        trust_policy_key(tenant_id=TENANT),
        A2ATrustPolicy(
            semver=CONSUMER["semver"],
            tenant_id=TENANT,
            peers={
                declared["peer_id"]: _grant(keys[name], declared)
                for name, declared in PEERS.items()
            },
        ),
        A2A_TRUST_POLICY,
    )
    ceiling_version = registry.register_typed(
        payload_ceiling_key(tenant_id=TENANT),
        InboundPayloadCeiling(
            semver=CONSUMER["semver"],
            max_payload_bytes=CONSUMER["inbound_payload_ceiling_bytes"],
        ),
        INBOUND_PAYLOAD_CEILING,
    )

    database_path = tmp_path / "a2a-consumer.sqlite3"
    handle = boot(
        database_path=database_path,
        registry=registry,
        resolution_spec_key=CONTROL["keys"]["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=CONTROL["keys"]["policy_bundle"],
        policy_bundle_version=policy_version,
    )
    gate = A2AAdmissionGate(
        identity=_verifier(key_dir),
        control_plane=registry,
        audit_log=registry.audit_log,
        tenant_id=TENANT,
        trust_policy_version=trust_version,
        payload_ceiling_version=ceiling_version,
        product_classes={PRODUCT_CLASS["schema_name"]: _product_class(registry)},
    )

    now = _instant(CONTROL["decision"]["now"])
    try:
        with httpx.Client(timeout=30.0) as client, ExitStack() as stack:
            wire = TypedHttpWire(
                local_peer_id=CONSUMER["peer_id"],
                endpoints=lambda *, peer: "",
                http_client=client,
                clock=lambda: now,
                receive_path=CONSUMER["receive_path"],
                max_request_bytes=CONSUMER["max_request_bytes"],
            )
            with _hosted(wire) as url:
                for declared in PEERS.values():
                    _spawn_producer(
                        stack, declared=declared, key_dir=key_dir, url=url
                    )
                received = tuple(wire.receive())

        by_peer: dict[str, tuple[InboundProduct, ...]] = {}
        for message in received:
            peer_id = message.observed_peer.peer_id
            by_peer[peer_id] = (*by_peer.get(peer_id, ()), message)

        yield Consumer(
            handle=handle,
            database_path=database_path,
            gate=gate,
            wire=wire,
            now=now,
            lineage=ProductLineage(
                operators_invoked=frozenset({"temporal.as-of"}),
                policy_bundle_versions=frozenset({"consumer-own-policy"}),
                graph_snapshot_at=now,
            ),
            inbound=by_peer,
        )
    finally:
        handle.close()


def _verifier(key_dir: Path) -> Any:
    """The consumer's verifier.

    It reads the same directory the producers signed from only because this is
    one test process's temp space; what binds a product to a principal is the
    *public* key on the peer's trust-policy entry, which the gate hands to
    ``verify`` and which is the only key material the verification path
    consults.
    """
    from ccf.a2a.identity import (  # noqa: PLC0415
        DetachedJwsIdentityProvider,
        FileBackedKeySource,
    )

    return DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )


# --- the one route into L3 --------------------------------------------------


def _ingest_admitted(
    consumer: Consumer, admitted: AdmittedProduct
) -> tuple[SignalEnvelope, ...]:
    """Drive an admitted product into L3 — through L2, the only route.

    Deliberately the same shape as ``test_cdc_slice.py``'s ``_ingest_feed``:
    envelopes are built, then handed one by one to ``worker.ingest``. There is
    nothing else here, because there is nothing else available — the gate
    yielded a value, not a handle.
    """
    declared = FEDERATION["federation"]
    address = content_hash(admitted.product)
    envelopes = tuple(
        SignalEnvelope(
            tenant_id=admitted.product.tenant_id,
            envelope_id=f"{address}/{index}",
            source=SourceIdentity(system_id=declared["system_id"]),
            ingestion_timestamp=consumer.now,
            observed_time=admitted.product.temporal_boundary,
            raw_payload={
                "federated_entity_uri": entity["entity_uri"],
                "federated_entity_class": entity["entity_class"],
            },
        )
        for index, entity in enumerate(admitted.product.payload["entities"])
    )
    for envelope in envelopes:
        consumer.handle.worker.ingest(envelope)
    return envelopes


def _first(consumer: Consumer, name: str) -> InboundProduct:
    return consumer.inbound[PEERS[name]["peer_id"]][0]


def _tampered(consumer: Consumer, name: str) -> InboundProduct:
    return consumer.inbound[PEERS[name]["peer_id"]][1]


def _admit(consumer: Consumer, inbound: InboundProduct) -> Any:
    return consumer.gate.admit(
        inbound=inbound, consumer_lineage=consumer.lineage, now=consumer.now
    )


# --- the exchange -----------------------------------------------------------


def test_the_transport_satisfies_the_wire_protocol(consumer: Consumer) -> None:
    """D-11: the typed-HTTP leg is a ``WireProtocol``, so LF A2A substitutes.

    What would fail here: a transport that grew a method the abstraction does
    not declare and became the thing callers type against. The next transport
    would then be a redesign rather than a substitution.
    """
    assert isinstance(consumer.wire, WireProtocol)


def test_a_signed_product_crosses_two_processes_and_is_admitted(
    consumer: Consumer,
) -> None:
    """XPRC-02, criterion 2: real HTTP, real second heap, Control Plane verdict.

    What would fail here: any re-serialization of the payload en route. The
    signature is over the producer's canonical bytes, so a transport that
    normalized them would refuse the *genuine* product, not just the tampered
    one.
    """
    admitted = _admit(consumer, _first(consumer, "first"))
    assert isinstance(admitted, AdmittedProduct), admitted
    assert admitted.product.tenant_id == TENANT
    assert admitted.product.schema_name == PRODUCT_CLASS["schema_name"]
    assert admitted.peer.peer_id == PEERS["first"]["peer_id"]


def test_an_admitted_product_reaches_l3_only_through_the_assembly_worker(
    consumer: Consumer,
) -> None:
    """Criterion 4, the A2A leg: L2 is the only mutation path.

    What would fail here: a consumer that reached L3 by any other route. Two
    observations, because either alone is weak — the graph must actually change
    (or the "only through L2" claim is vacuous), and this module must contain
    no second ingest call site (or the claim is about one code path among
    several).
    """
    before = consumer.graph_digest()
    admitted = _admit(consumer, _first(consumer, "first"))
    assert isinstance(admitted, AdmittedProduct)
    envelopes = _ingest_admitted(consumer, admitted)
    assert envelopes
    assert consumer.graph_digest() != before

    view = consumer.handle.reader.as_of(tenant_id=TENANT, at=consumer.now)
    federated = [
        record.claim
        for record in view.entities
        if record.claim.entity_class
        == FEDERATION["federation"]["entity_rule"]["entity_class"]
    ]
    entities = admitted.product.payload["entities"]
    assert len(federated) == len(entities)
    assert {claim.attributes["federated_entity_class"] for claim in federated} == {
        entity["entity_class"] for entity in entities
    }
    # The consumer mints its *own* canonical URIs from its own resolution spec
    # rather than adopting the peer's. A fabric that took a peer's identifiers
    # verbatim would let a peer name nodes in someone else's graph.
    assert all(
        claim.entity_uri
        not in {entity["entity_uri"] for entity in entities}
        for claim in federated
    )

    assert _ingest_call_sites() == {"_ingest_admitted"}


def _ingest_call_sites() -> set[str]:
    """Every function in this module that calls ``.ingest(...)``.

    An AST scan rather than a text grep: a grep cannot tell a call from a
    docstring that mentions one, and this claim is precisely about call sites.
    """
    tree = ast.parse(inspect.getsource(_module()))
    sites: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "ingest"
            ):
                sites.add(node.name)
    return sites


def _module() -> Any:
    import sys  # noqa: PLC0415

    return sys.modules[__name__]


def test_admitted_lineage_is_the_union_of_producer_and_consumer(
    consumer: Consumer,
) -> None:
    """D-14, CLAUDE.md §7.2: inbound L extends, never replaces.

    What would fail here: replacement in either direction. The two operator
    sets are disjoint by construction, so a consumer that took the producer's
    lineage wholesale would lose ``temporal.as-of`` and one that ignored the
    producer's would lose the operators that actually produced the product.
    """
    admitted = _admit(consumer, _first(consumer, "first"))
    assert isinstance(admitted, AdmittedProduct)
    producer = admitted.product.lineage

    assert producer.operators_invoked <= admitted.lineage.operators_invoked
    assert (
        consumer.lineage.operators_invoked <= admitted.lineage.operators_invoked
    )
    assert admitted.lineage.operators_invoked == (
        producer.operators_invoked | consumer.lineage.operators_invoked
    )
    assert admitted.lineage.policy_bundle_versions == (
        producer.policy_bundle_versions
        | consumer.lineage.policy_bundle_versions
    )
    # The producer's operator plan, graph snapshot anchor and policy version
    # all survive the crossing.
    assert PRODUCER_POLICY_VERSION in admitted.lineage.policy_bundle_versions
    assert admitted.lineage.graph_snapshot_at == producer.graph_snapshot_at
    assert admitted.product.plan_id == PRODUCT_CLASS["plan_id"]


def test_a_tampered_product_is_refused_and_leaves_l3_byte_identical(
    consumer: Consumer,
) -> None:
    """Criterion 4 and T-06-47: refusal is a value, and L3 does not move.

    What would fail here: a consumer that handed the received product straight
    to ``worker.ingest``. The tampered message carries a real signature over
    *different* bytes, so it crosses the wire intact and is caught only by the
    gate; bypassing the gate would put its entities in L3 and change the digest.
    """
    before = consumer.graph_digest()
    refusal = _admit(consumer, _tampered(consumer, "first"))
    after = consumer.graph_digest()

    assert isinstance(refusal, GateRefusal), refusal
    assert isinstance(refusal, SignatureRefusal)
    assert refusal.peer_id == PEERS["first"]["peer_id"]
    assert after == before

    refused = [
        event
        for event in consumer.handle.registry.audit_events()
        if event.action == "a2a_admission_refused"
    ]
    assert refused
    assert all(event.resolved is False for event in refused)


def test_each_peer_is_admitted_against_its_own_trust_policy_entry(
    consumer: Consumer,
) -> None:
    """D-23: two peers, two keys, two entries, two independent verdicts.

    What would fail here: a gate that verified against every key it holds. That
    gate passes a single-peer suite and is wrong the moment a federation has
    two members, which is the CR-01 class of defect this case exists to catch.
    """
    for name in ("first", "second"):
        admitted = _admit(consumer, _first(consumer, name))
        assert isinstance(admitted, AdmittedProduct), (name, admitted)
        assert admitted.peer.peer_id == PEERS[name]["peer_id"]

        refusal = _admit(consumer, _tampered(consumer, name))
        assert isinstance(refusal, AdmissionRefusal), name
        assert refusal.peer_id == PEERS[name]["peer_id"]


def test_peer_a_admits_nothing_of_peer_b(consumer: Consumer) -> None:
    """D-23, T-06-49: an envelope is only ever this peer's if this key signed it.

    Peer B's genuine, entitled product is presented under peer A's identity.
    What would fail here: a gate that resolved keys globally rather than from
    the observed peer's own entry would admit it, and one peer's grant would
    silently cover another's traffic.
    """
    genuine_b = _first(consumer, "second")
    as_peer_a = InboundProduct(
        observed_peer=PeerRef(
            tenant_id=TENANT, peer_id=PEERS["first"]["peer_id"]
        ),
        signed=genuine_b.signed,
    )
    refusal = _admit(consumer, as_peer_a)
    assert isinstance(refusal, SignatureRefusal), refusal
    assert refusal.declared_key_id == PEERS["second"]["key_id"]
    assert refusal.permitted_key_ids == frozenset(
        {PEERS["first"]["key_id"]}
    )
