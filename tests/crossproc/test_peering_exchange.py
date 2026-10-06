"""Peering end to end: two producer processes, one consumer, one gate.

XPRC-02; CLAUDE.md §7.2; whitepaper §8.3 Pattern 4. The seam is a **Peering**
(``D-IMPL-59``, Dave, 2026-07-27) and A2A is one of its transports, which is why
both legs below run the *same* Control Plane gate rather than one each.

The question this file answers per assertion is the D-02 one — *would this catch the invariant being
broken?* — so every row below is drafted from what a broken consumer would do
rather than from what the plan intends.

=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
single-writer across a Peering             the transport has no writer to hand
(CLAUDE.md §10, criterion 4)               out; every admitted claim below
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
wire replaceability (CLAUDE.md §7.2,       an assertion that had to *differ* per
D-IMPL-14, D-11)                           transport. Every case below runs
                                           unchanged over both the typed-HTTP
                                           leg and the LF A2A leg; one that
                                           needed relaxing for either would mean
                                           the Context Product Contract was not
                                           actually the stable layer and the
                                           wire not actually replaceable
A2A serialization preserves the payload    a future ``a2a-sdk`` routing the
(T-06-54, research assumption A2)          payload through a protobuf ``Struct``
                                           rather than a ``bytes`` field. The
                                           signature would stop verifying over
                                           the carried bytes, which is asserted
                                           directly rather than inferred
=========================================  ===================================

**Every case runs twice, once per transport.** ``typed-http`` is 06-09's
standard-free leg; ``lf-a2a`` is the D-IMPL-14 default on ``a2a-sdk``. Only the
``transport`` fixture below knows which is in force — no assertion in this
module names a transport, and none was edited to accommodate the second one.

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
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, get_type_hints

import httpx
import pytest
import uvicorn
import yaml
from fastapi import FastAPI
from joserfc.jwk import ECKey

from ccf.peering.admission import (
    ADMISSION_RECORD,
    INBOUND_PAYLOAD_CEILING,
    PeeringAdmissionGate,
    AdmissionRefusal,
    AdmittedProduct,
    InboundPayloadCeiling,
    SignatureRefusal,
    payload_ceiling_key,
)
from ccf.peering.identity import FileBackedKeySource
from ccf.peering.trust_policy import (
    PEERING_TRUST_POLICY,
    PeeringTrustPolicy,
    PeerTrustGrant,
    trust_policy_key,
)
from ccf.peering.protocol import InboundProduct, PeerRef, PeeringProtocol
from ccf.artifacts.file_store import FileArtifactStore
from ccf.assembly.worker import (
    AssemblyWorker,
    EntityResolutionRule,
    EntityResolutionSpec,
    FederatedIngestSpec,
    IngestResult,
)
from ccf.boot import FabricHandle, boot
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import GateRefusal

from ccf_runtime.peering.lf_a2a import LfA2AWire, build_agent_card
from ccf_runtime.peering.typed_http import TypedHttpWire

from crossproc.conftest import spawn_child_server
from crossproc.servers import a2a_producer_child as child
from integration.test_proto_quickstart import _instant, _resolution_spec
from http_api.composition_authority import (
    composition_replay_mint,
    deployment_store,
    register_at_composition,
    register_typed_at_composition,
)

pytestmark = pytest.mark.crossproc

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"

SERVERS = Path(__file__).resolve().parent / "servers"


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

LF_A2A = FEDERATION["lf_a2a"]


# --- the two transports ------------------------------------------------------


@dataclass(frozen=True)
class TransportLeg:
    """One wire under test: how to build it, host it, and address it.

    The whole of this module's transport knowledge lives in this type and the
    two factories below. Everything past the ``consumer`` fixture sees a
    :class:`~ccf.peering.protocol.PeeringProtocol` and a URL, which is the point being
    demonstrated: if a leg needed a hook anywhere further down, the abstraction
    would not be carrying the exchange.

    Attributes:
        name: The transport's identifier, for failure messages only.
        child: The producer child that speaks this wire.
        build: Builds ``(wire, asgi_app)`` for the consuming side, given the
            consumer's clock, an HTTP client it may use, and the base URL it is
            about to be hosted at. The base URL is an argument because LF A2A
            publishes an Agent Card stating where this peer answers, and a card
            carrying a relative path is one no peer can dial — the port must
            therefore be bound before the transport exists.
        child_url: Turns the hosted base URL into the value the child is handed
            — a full endpoint URL for typed HTTP, a base URL for LF A2A, which
            discovers the endpoint from the Agent Card at the well-known path.
    """

    name: str
    child: Path
    build: Callable[[datetime, httpx.Client, str], tuple[PeeringProtocol, Any]]
    child_url: Callable[[str], str]


def _typed_http_leg() -> TransportLeg:
    """06-09's leg: plain typed HTTP, bound to no wire standard."""

    def build(
        now: datetime, http_client: httpx.Client, base_url: str
    ) -> tuple[PeeringProtocol, Any]:
        wire = TypedHttpWire(
            local_peer_id=CONSUMER["peer_id"],
            endpoints=lambda *, peer: "",
            http_client=http_client,
            clock=lambda: now,
            receive_path=CONSUMER["receive_path"],
            max_request_bytes=CONSUMER["max_request_bytes"],
            max_pending=CONSUMER["max_pending"],
        )
        return wire, wire.asgi_app()

    return TransportLeg(
        name="typed-http",
        child=SERVERS / "a2a_producer_child.py",
        build=build,
        child_url=lambda base: base + CONSUMER["receive_path"],
    )


def _lf_a2a_leg() -> TransportLeg:
    """The D-IMPL-14 default: Linux Foundation A2A on ``a2a-sdk``.

    The consuming side never emits here, so its card's ``rpc_url`` is only ever
    read back by peers resolving it — which is why the base URL is not known at
    construction time and the card is built against the mounted path. That is a
    deployment detail of hosting, not of the exchange.
    """

    def build(
        now: datetime, http_client: httpx.Client, base_url: str
    ) -> tuple[PeeringProtocol, Any]:
        wire = LfA2AWire(
            local_peer_id=CONSUMER["peer_id"],
            agent_card=build_agent_card(
                name=LF_A2A["card"]["name"],
                version=LF_A2A["card"]["version"],
                description=LF_A2A["card"]["description"],
                rpc_url=base_url + LF_A2A["rpc_path"],
            ),
            cards=lambda *, peer: "",
            http_client_factory=lambda: httpx.AsyncClient(timeout=30.0),
            clock=lambda: now,
            rpc_path=LF_A2A["rpc_path"],
            max_message_bytes=CONSUMER["max_request_bytes"],
            max_pending=CONSUMER["max_pending"],
        )
        app = FastAPI()
        for route in wire.routes():
            app.router.routes.append(route)
        return wire, app

    return TransportLeg(
        name="lf-a2a",
        child=SERVERS / "lf_a2a_producer_child.py",
        build=build,
        child_url=lambda base: base,
    )


@pytest.fixture(params=["typed-http", "lf-a2a"])
def transport(request: pytest.FixtureRequest) -> Iterator[TransportLeg]:
    """The wire under test, one param per implementation (D-11).

    Two params rather than two modules: a second copy of these assertions could
    drift from the first, and then "the same assertions pass over both wires"
    would be a claim about two files that happened to look alike rather than a
    property of one.
    """
    if request.param == "typed-http":
        yield _typed_http_leg()
        return
    if request.param == "lf-a2a":
        yield _lf_a2a_leg()
        return
    raise NotImplementedError(request.param)


# --- the consumer deployment -----------------------------------------------


@dataclass
class Consumer:
    """One consuming fabric, its gate, and what arrived over the wire."""

    handle: FabricHandle
    database_path: Path
    gate: PeeringAdmissionGate
    wire: PeeringProtocol
    key_dir: Path
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
        semver="1.0.0",
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
        # `SEC-022`: the issuance window this fixture declares for the peer.
        signature_max_age_seconds=declared["signature_max_age_seconds"],
        permitted_clock_skew_seconds=declared["permitted_clock_skew_seconds"],
    )


def _product_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    max_ttl_version = register_at_composition(registry, 
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
def _hosted(
    build_app: Callable[[str], tuple[Any, PeeringProtocol]],
) -> Iterator[tuple[str, PeeringProtocol]]:
    """Host what ``build_app`` builds on an ephemeral loopback port.

    ``build_app`` is handed the base URL and returns ``(asgi_app, wire)``;
    this yields ``(base_url, wire)``.

    Takes a *builder* rather than an application because the port must be bound
    before the transport exists: LF A2A publishes an Agent Card stating where
    this peer answers, and a card carrying a relative path is one no peer can
    dial. Binding first — which this already did, so the port would be known
    before the server started — is therefore also what makes the card
    constructible. The typed-HTTP leg does not care, and does not have to.

    Which routes a wire mounts, and how many, stays the transport's business:
    the typed-HTTP leg mounts one, and the LF A2A leg mounts the JSON-RPC route
    plus the Agent Card routes ``a2a-sdk`` builds. Yielding the *base* URL keeps
    that difference where it belongs — each leg's ``child_url`` turns it into
    what its own child needs.

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
    base_url = f"http://127.0.0.1:{port}"
    app, extra = build_app(base_url)
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
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
        yield base_url, extra
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        bound.close()


def _spawn_producer(
    stack: ExitStack,
    *,
    leg: TransportLeg,
    declared: Any,
    key_dir: Path,
    url: str,
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
    stack.enter_context(spawn_child_server(leg.child))


@pytest.fixture
def consumer(tmp_path: Path, transport: TransportLeg) -> Iterator[Consumer]:
    """Boot a consuming fabric, host its endpoint, and run both producers.

    Everything below the transport line is identical per leg — one Control
    Plane, one trust policy, one gate, two producers — which is why the
    parametrization stops here.
    """
    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    keys = {
        name: _write_key(key_dir, declared["key_id"])
        for name, declared in PEERS.items()
    }

    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, 
        CONTROL["keys"]["resolution_spec"], _consumer_resolution_spec()
    )
    policy_version = register_at_composition(registry, 
        CONTROL["keys"]["policy_bundle"], CONTROL["policy_bundle"]
    )
    assert policy_version == PRODUCER_POLICY_VERSION

    trust_version = register_typed_at_composition(registry, 
        trust_policy_key(tenant_id=TENANT),
        PeeringTrustPolicy(
            semver=CONSUMER["semver"],
            tenant_id=TENANT,
            peers={
                declared["peer_id"]: _grant(keys[name], declared)
                for name, declared in PEERS.items()
            },
        ),
        PEERING_TRUST_POLICY,
    )
    ceiling_version = register_typed_at_composition(registry, 
        payload_ceiling_key(tenant_id=TENANT),
        InboundPayloadCeiling(
            semver=CONSUMER["semver"],
            max_payload_bytes=CONSUMER["inbound_payload_ceiling_bytes"],
        ),
        INBOUND_PAYLOAD_CEILING,
    )

    database_path = tmp_path / "a2a-consumer.sqlite3"
    handle = boot(
        backend="sqlite",
        connection={"database_path": database_path},
        registry=registry,
        resolution_spec_key=CONTROL["keys"]["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=CONTROL["keys"]["policy_bundle"],
        policy_bundle_version=policy_version,
        # D-IMPL-354: the tenant(s) this test composes the fabric for.
        tenant_ids=(TENANT,),
    )
    gate = PeeringAdmissionGate(
        identity=_verifier(key_dir),
        control_plane=registry,
        audit_log=registry.audit_log,
        # Where each admitted crossing's ``AdmissionRecord`` lands (D-IMPL-58
        # reading (d)). A real reference store, so this end-to-end exchange
        # exercises the same persistence path a deployment would.
        # Declared for the admission-record class, and the gate holds the
        # ReplayMint its composition root minted for it (D-IMPL-354).
        artifact_store=deployment_store(tmp_path / "admission-records", ADMISSION_RECORD.class_id),
        authorized=composition_replay_mint(registry, tenant=TENANT, artifact_class=ADMISSION_RECORD.class_id),
        trust_policy_version=trust_version,
        payload_ceiling_version=ceiling_version,
        product_classes={PRODUCT_CLASS["schema_name"]: _product_class(registry)},
    )

    now = _instant(CONTROL["decision"]["now"])
    try:
        with httpx.Client(timeout=30.0) as client, ExitStack() as stack:
            def build_app(base_url: str) -> tuple[Any, PeeringProtocol]:
                built, app = transport.build(now, client, base_url)
                return app, built

            with _hosted(build_app) as (base_url, wire):
                for declared in PEERS.values():
                    _spawn_producer(
                        stack,
                        leg=transport,
                        declared=declared,
                        key_dir=key_dir,
                        url=transport.child_url(base_url),
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
            key_dir=key_dir,
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
    from ccf.peering.identity import DetachedJwsIdentityProvider  # noqa: PLC0415

    return DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )


# --- the one route into L3 --------------------------------------------------


def _federated_ingest_spec() -> FederatedIngestSpec:
    """This deployment's federation-ingest vocabulary, from the fixture."""
    declared = FEDERATION["federation"]
    return FederatedIngestSpec(
        source_system_id=declared["system_id"],
        payload_records_key=declared["payload_records_key"],
        record_key_aliases=dict(declared["record_key_aliases"]),
    )


def _ingest_admitted(
    consumer: Consumer, admitted: AdmittedProduct
) -> tuple[IngestResult, ...]:
    """Drive an admitted product into L3 — through L2's federated door.

    Since Dave's 2026-07-27 ruling this test builds no envelopes of its own.
    ``AssemblyWorker.ingest_admitted`` takes the ``AdmittedProduct`` itself and
    derives the envelopes from the deployment's declared spec, so the admission
    commitment (CLAUDE.md §7.2) is carried by the parameter's type rather than
    by this helper's discipline: an ``InboundProduct`` is not a value this call
    accepts.
    """
    return consumer.handle.worker.ingest_admitted(
        admitted, spec=_federated_ingest_spec(), ingested_at=consumer.now
    )


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
    """D-11: the typed-HTTP leg is a ``PeeringProtocol``, so LF A2A substitutes.

    What would fail here: a transport that grew a method the abstraction does
    not declare and became the thing callers type against. The next transport
    would then be a redesign rather than a substitution.
    """
    assert isinstance(consumer.wire, PeeringProtocol)


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
    """Criterion 4, the Peering legs: L2 is the only mutation path.

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

    assert _call_sites("ingest") == set()
    assert _call_sites("ingest_admitted") == {"_ingest_admitted"}


def test_the_federated_door_does_not_accept_an_unadmitted_product() -> None:
    """Dave, 2026-07-27: the admission commitment is a type, not a discipline.

    The observable is the *declared parameter type* of L2's federated entry
    point, not a call this module makes. Two halves, and both are needed:
    ``ingest_admitted`` is annotated ``AdmittedProduct``, and no *unforced* path
    constructs an ``AdmittedProduct`` outside the gate — every construction that
    does not carry the gate's token fails at construction — so the only values
    that satisfy the annotation are ones the gate produced or ones a caller went
    out of its way to forge.

    The stronger adjective is deliberately absent (advisory A2, D-21). Python's
    import model does not support it: ``_ADMISSION_TOKEN`` is importable, and
    :func:`test_the_unforgeability_claim_is_scoped_to_the_unforced_path` pins
    that boundary so the claim cannot be quietly upgraded again. The token still
    earns its place — see ``ccf.peering.admission``'s module docstring on why a lint
    cannot make this statement about transports the SDK does not ship — it is
    the *strength* of the claim that is re-scoped, not the mechanism.

    What would fail here: re-widening ``ingest_admitted`` to take an
    ``InboundProduct``, a payload, or ``object``; or dropping the construction
    token, at which point the annotation would still read correctly and mean
    nothing. The second half is asserted rather than assumed for exactly that
    reason.
    """
    from ccf.peering.admission import AdmissionBypassError  # noqa: PLC0415
    from ccf.peering.protocol import InboundProduct as _Inbound  # noqa: PLC0415, F401

    hints = get_type_hints(AssemblyWorker.ingest_admitted)
    assert hints["admitted"] is AdmittedProduct

    with pytest.raises(AdmissionBypassError):
        AdmittedProduct(None, None, None, object())  # type: ignore[arg-type]


def test_the_unforgeability_claim_is_scoped_to_the_unforced_path() -> None:
    """The boundary of the claim above, asserted rather than hoped (finding A2).

    Both branches, because the claim is a *scope* and a scope needs its two
    edges: with the token withheld, construction raises; with the private token
    named and passed, construction succeeds. The honest statement is therefore
    "no unforced path exists, and every forced path fails at construction" —
    forging requires a module willing to name a private member of
    ``ccf.peering.admission``, which Python permits and no runtime check can
    prevent.

    What would fail here: someone closing the forced path so that no
    construction outside the gate succeeds at all (this test would go red, and
    *should* — the wording would then be free to strengthen, deliberately and
    with evidence), or someone upgrading the wording without changing the
    mechanism, which is what A2 caught the first time. A claim whose limit is untested is a claim that
    drifts.
    """
    from ccf.peering.admission import (  # noqa: PLC0415
        _ADMISSION_TOKEN,
        AdmissionBypassError,
    )

    with pytest.raises(AdmissionBypassError):
        AdmittedProduct(None, None, None, object())  # type: ignore[arg-type]

    forced = AdmittedProduct(None, None, None, _ADMISSION_TOKEN)  # type: ignore[arg-type]
    assert isinstance(forced, AdmittedProduct)


def _call_sites(method: str) -> set[str]:
    """Every function in this module that calls ``.<method>(...)``.

    An AST scan rather than a text grep: a grep cannot tell a call from a
    docstring that mentions one, and this claim is precisely about call sites.
    Attribute equality, not prefix matching, so ``ingest`` does not match
    ``ingest_admitted``.
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
                and inner.func.attr == method
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
        if event.action == "peering_admission_refused"
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


# --- the serialization guard ------------------------------------------------


def test_the_carried_payload_is_byte_equal_and_still_verifies(
    consumer: Consumer,
) -> None:
    """T-06-54, research assumption A2: the wire did not touch the bytes.

    The standing regression guard for how the LF A2A leg carries its payload. It
    rides in a protobuf ``bytes`` field (``Part.raw``); a future ``a2a-sdk`` — or
    a future contributor — routing it through ``Part.data`` instead would put it
    through ``google.protobuf.Struct``'s JSON value model, where integers become
    doubles and key order is not preserved. This case is what fails then, rather
    than signatures silently breaking in production.

    Three observations, because the first two alone are each satisfiable by a
    broken transport:

    1. **The signature verifies over the bytes as carried.** This is the
       strongest available statement of byte-identity with what the producer
       emitted: verification succeeds only over exactly the bytes that were
       signed, and the producer signed the bytes it emitted. A transport that
       normalized so much as a space would fail here.
    2. **The verified payload *is* the carried payload**, rather than some
       reconstruction of it — so the assertion is about what the consumer
       actually holds, not about what a verifier happened to rebuild.
    3. **Re-serializing the parsed product reproduces the carried bytes
       exactly**, which pins the round trip end to end: bytes → contract →
       bytes, with no field lost, added, or reordered.

    It runs over both transports. It could not be expressed in the shared body
    above — it needs the peer's public key and the raw envelope, neither of which
    the admission assertions touch — but there is no reason to withhold it from
    the typed-HTTP leg, and running it on both is what makes a *difference*
    between the legs visible if one ever appears.
    """
    inbound = _first(consumer, "first")
    source = FileBackedKeySource(directory=consumer.key_dir)
    public_key = source.signing_key(key_id=PEERS["first"]["key_id"])

    carried = inbound.signed.canonical_payload()
    verified = _verifier(consumer.key_dir).verify(
        signed=inbound.signed,
        public_keys={PEERS["first"]["key_id"]: public_key},
    )
    assert verified == carried
    assert sha256(carried).hexdigest() == inbound.signed.content_address()

    admitted = _admit(consumer, inbound)
    assert isinstance(admitted, AdmittedProduct), admitted
    assert canonical_bytes(admitted.product) == carried
