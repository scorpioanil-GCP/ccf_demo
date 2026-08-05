"""examples/04-cross-process — assembler and consumer across processes (EXAM-05).

An assembler agent (``ContextAssemblyAgent``) runs in one real OS subprocess
(``producer_child.py``); this process is the consumer. One typed Context Product
crosses the boundary over BOTH transports — MCP egress (whitepaper §8.3
Pattern 3; CLAUDE.md §7.1) and A2A federation (Pattern 4; CLAUDE.md §7.2) — with
Control Plane admission verification demonstrated on the consumer side,
including the refusal path.

What this spine demonstrates, checked in
``tests/examples/test_cross_process_output.py``:

* **Two processes, nothing shared but the wire.** The producer's fabric, graph
  and key live in the child's heap; the consumer's live here. Two deployments,
  two manifests, two Control Planes. The spawn uses the READY-handshake
  pattern — the child prints ``READY {mcp_port} {a2a_port}`` once its servers
  report started, and the blocking ``readline()`` below is the gate. No fixed
  ports, no sleeps.
* **MCP egress (Pattern 3).** The product is read back as an MCP Resource and
  its typed contract validates — and the bytes are the very bytes the A2A
  signature verifies over, so the two front doors serve one product.
* **A2A admission (Pattern 4, D-IMPL-16).** The genuine signed product is
  admitted only after signature verification against the peer's own trust-policy
  entry and the Control Plane policy-binding checks. An immutable
  ``AdmissionRecord`` is persisted at an exact content address before anything is
  reported admitted, and the merged lineage is the set-union of producer and
  consumer (CLAUDE.md §7.2: extends, never replaces).
* **Admission only through L2 (single-writer, CLAUDE.md §10).** The admitted
  product reaches L3 through ``AssemblyWorker.ingest_admitted`` — a door typed to
  accept only gate-produced ``AdmittedProduct`` values — and the graph digest
  moves only then.
* **The negative case.** A tampered envelope — a real signature spliced onto
  different payload bytes, emitted over the real socket — is refused as a value,
  the refusal is audited, and the consumer's L3 substrate is byte-identical
  before and after.

Every domain value — tenant, peer identities, ceilings, endpoint path,
federation vocabulary, the consumer's own lineage — is loaded from
``artifacts/*.yaml`` and enumerated by ``artifacts/consumer-manifest.yaml``.
Run it: ``make example-04``.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import traceback
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import cast

import httpx
import uvicorn
from joserfc.jwk import ECKey

import producer_child as producer

from ccf.artifacts.file_store import FileArtifactStore
from ccf.assembly.worker import FederatedIngestSpec
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.mcp.client import McpResourceClient, SyncMcpBridge
from ccf.peering.admission import (
    ADMISSION_RECORD,
    INBOUND_PAYLOAD_CEILING,
    AdmissionRecord,
    AdmittedProduct,
    InboundPayloadCeiling,
    PeeringAdmissionGate,
    payload_ceiling_key,
)
from ccf.peering.identity import DetachedJwsIdentityProvider, FileBackedKeySource
from ccf.peering.protocol import InboundProduct
from ccf.peering.trust_policy import (
    PEERING_TRUST_POLICY,
    PeeringTrustPolicy,
    PeerTrustGrant,
    trust_policy_key,
)
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import GateRefusal
from ccf_runtime.peering.typed_http import TypedHttpWire

EXAMPLE_ROOT = Path(__file__).resolve().parent
MANIFEST = EXAMPLE_ROOT / "artifacts" / "consumer-manifest.yaml"
CHILD = EXAMPLE_ROOT / "producer_child.py"

#: Deadline every synchronous MCP call is bounded by, and the grace given to
#: a terminated child before escalating to SIGKILL. Process-lifecycle
#: mechanism values, not domain values.
CALL_TIMEOUT_SECONDS = 20.0
TERMINATE_TIMEOUT_SECONDS = 10


def _write_key(directory: Path, key_id: str) -> ECKey:
    """Generate the producer's signing key for this run. Never committed."""
    import json  # noqa: PLC0415

    key = ECKey.generate_key("P-256", parameters={"kid": key_id})
    (directory / f"{key_id}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return key


def _graph_digest(database_path: Path) -> str:
    """The consumer's L3 substrate, byte for byte, WAL included.

    The SQLite backend runs in WAL mode, so a committed write lands in
    ``<db>-wal`` while the main file can stay byte-identical; digesting the
    main file alone would report "unchanged" after a real write. The ``-shm``
    index is excluded: process coordination state, not durable content.
    """
    digest = sha256()
    for suffix in ("", "-wal"):
        path = database_path.with_name(database_path.name + suffix)
        digest.update(path.read_bytes() if path.exists() else b"")
    return digest.hexdigest()


@dataclass(frozen=True)
class CrossProcessResult:
    """What one run of the spine produced, for a caller to inspect.

    The example returns its state rather than checking it here, so that
    ``tests/examples/test_cross_process_output.py`` can hold the assertions
    where a test runner will actually run them (D-09). The A2A trust boundary
    is the reason this list is long: the admission verdict, the record, the
    merged lineage, the refusal and the two graph digests are each a separate
    observable, and folding any pair together would let one stand in for the
    other.
    """

    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    consumer_policy_version: str
    over_mcp: str
    mcp_product: ContextProductContract
    genuine: InboundProduct
    tampered: InboundProduct
    admitted: AdmittedProduct
    consumer_lineage: ProductLineage
    admission_record: AdmissionRecord
    admission_record_address: str
    admission_store: FileArtifactStore
    audit_events: tuple[object, ...]
    federated_entity_uris: tuple[str, ...]
    digest_before_ingest: str
    digest_after_ingest: str
    digest_after_refusal: str
    refusal: GateRefusal


def run(*, root: Path) -> CrossProcessResult:
    """Run the consumer, spawn the producer, exchange, admit, refuse."""
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot. This is the
    #    CONSUMER's manifest: its own resolution spec, its own policy bundle,
    #    its own admitted product class, its own peering entitlement. The
    #    producer's artifact set is not in force here, which is precisely why
    #    the A2A trust boundary exists.
    database_path = root / "consumer.sqlite3"
    booted = load_and_boot(
        MANIFEST, registry=registry, database_path=str(database_path)
    )
    # --8<-- [end:boot]
    try:
        decision = cast(DeclaredArtifact, booted.artifacts["decision"])
        governance = cast(DeclaredArtifact, booted.artifacts["product-governance"])
        declared = cast(ProductClassDeclaration, booted.artifacts["product-class"])
        peering = cast(DeclaredArtifact, booted.artifacts["peering-trust"]).declaration
        lineage_declaration = cast(
            DeclaredArtifact, booted.artifacts["consumer-lineage"]
        ).declaration
        ingest_declaration = cast(
            DeclaredArtifact, booted.artifacts["federation-ingest"]
        ).declaration

        tenant_id = booted.tenant_id
        now = datetime.fromisoformat(decision.declaration["now"])

        key_dir = root / "keys"
        key_dir.mkdir()
        key = _write_key(key_dir, peering["producer_key_id"])

        # --8<-- [start:peer-trust-policy]
        # 2. Trust is declared, then pinned. The regime the consumer entitles
        #    the producer to claim is the version of the consumer's OWN policy
        #    bundle — a second, independent document from the producer's, so
        #    the entitlement is falsifiable: if either side's bundle is edited
        #    alone, the inbound product's asserted regime falls outside this
        #    grant and admission refuses.
        entitled_policy_version = booted.pins.version_for("policy-bundle")
        trust_version = registry.register_typed(
            trust_policy_key(tenant_id=tenant_id),
            PeeringTrustPolicy(
                semver=peering["trust_policy_semver"],
                tenant_id=tenant_id,
                peers={
                    peering["producer_peer_id"]: PeerTrustGrant(
                        # The only value not authorable in the artifact: key
                        # MATERIAL, generated per run and never committed.
                        signing_keys={
                            peering["producer_key_id"]: key.as_dict(private=False)
                        },
                        permitted_producer_hashes=frozenset(
                            {peering["producer_hash"]}
                        ),
                        permitted_schema_names=frozenset({declared.schema_name}),
                        permitted_policy_regimes=frozenset(
                            {entitled_policy_version}
                        ),
                    )
                },
            ),
            PEERING_TRUST_POLICY,
        )
        ceiling_version = registry.register_typed(
            payload_ceiling_key(tenant_id=tenant_id),
            InboundPayloadCeiling(
                semver=peering["trust_policy_semver"],
                max_payload_bytes=peering["inbound_payload_ceiling_bytes"],
            ),
            INBOUND_PAYLOAD_CEILING,
        )
        # --8<-- [end:peer-trust-policy]

        # 3. The consumer's own TTL ceiling and product-class registration.
        #    Minted here, not by the manifest, for the same reason as in the
        #    producer: the pin is a content hash of what was registered, so
        #    Gate 3 has two independently authored values to compare.
        max_ttl_version = registry.register(
            declared.max_ttl_key,
            MaxTTL(seconds=governance.declaration["max_ttl_seconds"]),
        )
        product_class = register_product_class(
            registry=registry,
            schema_name=declared.schema_name,
            schema_version=declared.schema_version,
            ttl_anchor=declared.ttl_anchor,
            assembly_mode=declared.assembly_mode,
            max_ttl_key=declared.max_ttl_key,
            max_ttl_version=max_ttl_version,
        )

        # --8<-- [start:peer-gate]
        # 4. The gate is the one door an inbound product may pass through. It
        #    holds the identity provider that verifies signatures, the Control
        #    Plane it checks policy bindings against, the audit log every
        #    verdict lands in, and the store that keeps admission records.
        admission_store = FileArtifactStore(root=root / "admission-records")
        gate = PeeringAdmissionGate(
            identity=DetachedJwsIdentityProvider(
                key_source=FileBackedKeySource(directory=key_dir)
            ),
            control_plane=registry,
            audit_log=registry.audit_log,
            artifact_store=admission_store,
            tenant_id=tenant_id,
            trust_policy_version=trust_version,
            payload_ceiling_version=ceiling_version,
            product_classes={declared.schema_name: product_class},
        )
        consumer_lineage = ProductLineage(
            operators_invoked=frozenset(lineage_declaration["operators_invoked"]),
            policy_bundle_versions=frozenset(
                lineage_declaration["policy_bundle_versions"]
            ),
            graph_snapshot_at=datetime.fromisoformat(
                lineage_declaration["graph_snapshot_at"]
            ),
        )
        # --8<-- [end:peer-gate]

        # --- host the consumer's A2A endpoint, port bound before serving ----
        bound = socket.socket()
        bound.bind(("127.0.0.1", 0))
        bound.listen(64)
        consumer_port = bound.getsockname()[1]

        proc: subprocess.Popen[bytes] | None = None
        stderr_path = root / "producer-child.stderr"
        try:
            with httpx.Client(timeout=30.0) as client:
                wire = TypedHttpWire(
                    local_peer_id=peering["consumer_peer_id"],
                    endpoints=lambda *, peer: "",
                    http_client=client,
                    clock=lambda: now,
                    receive_path=peering["receive_path"],
                    max_request_bytes=peering["max_request_bytes"],
                )
                server = uvicorn.Server(
                    uvicorn.Config(wire.asgi_app(), log_level="error")
                )
                thread = threading.Thread(
                    target=server.run, kwargs={"sockets": [bound]}, daemon=True
                )
                thread.start()
                while not server.started:
                    if not thread.is_alive():
                        raise RuntimeError("the consumer endpoint failed to start")

                # --8<-- [start:peer-spawn]
                # 5. Spawn the assembler subprocess, READY handshake. Its own
                #    session/process group, so teardown can reap the whole
                #    group; stderr captured for diagnosis on failure.
                with stderr_path.open("wb") as stderr_sink:
                    proc = subprocess.Popen(
                        [sys.executable, str(CHILD)],
                        stdout=subprocess.PIPE,
                        stderr=stderr_sink,
                        start_new_session=True,
                        env={
                            **os.environ,
                            producer.CONSUMER_URL_VAR: (
                                f"http://127.0.0.1:{consumer_port}"
                                + peering["receive_path"]
                            ),
                            producer.KEY_DIR_VAR: str(key_dir),
                        },
                    )
                if proc.stdout is None:
                    raise RuntimeError("the producer child has no stdout pipe")
                announcement = proc.stdout.readline().decode().strip()
                if not announcement.startswith("READY "):
                    raise RuntimeError(
                        f"producer child did not announce readiness:"
                        f" {announcement!r}"
                    )
                _token, mcp_port, _a2a_port = announcement.split()

                # The child emits before it announces, so both carriages —
                # genuine and tampered — have already been accepted here.
                received = tuple(wire.receive())
                # --8<-- [end:peer-spawn]
                server.should_exit = True
                thread.join(timeout=TERMINATE_TIMEOUT_SECONDS)

            genuine, tampered = received

            # --8<-- [start:mcp-egress]
            # 6. MCP egress: the typed contract validates over the wire.
            address = producer.ProductAddress(
                tenant=tenant_id,
                product_class=declared.schema_name,
                version=declared.schema_version,
            )
            with SyncMcpBridge(
                call_timeout_seconds=CALL_TIMEOUT_SECONDS
            ) as bridge:
                mcp_client = McpResourceClient(
                    url=f"http://127.0.0.1:{mcp_port}/mcp", bridge=bridge
                )
                over_mcp = mcp_client.read_text(address.uri)
            mcp_product = ContextProductContract.model_validate_json(over_mcp)
            # --8<-- [end:mcp-egress]

            # --8<-- [start:peer-admit]
            # 7. A2A admission: verified, recorded, then admitted. This call is
            #    the whole trust boundary — signature verification against the
            #    peer's own trust entry, the Control Plane policy-binding
            #    checks, and only then the lineage merge. Nothing below it may
            #    be reordered above it: an inbound product is not admissible to
            #    L3 until the consuming Control Plane has validated its policy
            #    bindings (CLAUDE.md §7.2, a structural commitment).
            match gate.admit(
                inbound=genuine, consumer_lineage=consumer_lineage, now=now
            ):
                case AdmittedProduct() as admitted:
                    pass
                case verdict:
                    raise RuntimeError(
                        f"the consuming Control Plane refused a product it was"
                        f" configured to admit: {verdict}"
                    )
            # --8<-- [end:peer-admit]

            # --8<-- [start:peer-admission-record]
            # 8. The immutable AdmissionRecord exists at an exact version: the
            #    audit verdict points at it by content address, the store holds
            #    it, and its content hashes back to that very address — no
            #    "latest", no overwrite path.
            audit_events = tuple(registry.audit_events())
            admitted_events = [
                event for event in audit_events if event.action == "peering_admitted"
            ]
            if len(admitted_events) != 1:
                raise RuntimeError(
                    f"expected exactly one admission verdict, saw"
                    f" {len(admitted_events)}"
                )
            record_address = admitted_events[0].version
            admission_record = AdmissionRecord.model_validate_json(
                admission_store.get(content_address=record_address)
            )
            # --8<-- [end:peer-admission-record]

            # --8<-- [start:peer-ingest]
            # 9. Admission only through L2 (single-writer): the graph moves
            #    only when the typed federated door ingests the admitted value.
            digest_before_ingest = _graph_digest(database_path)
            booted.handle.worker.ingest_admitted(
                admitted,
                spec=FederatedIngestSpec(
                    source_system_id=ingest_declaration["system_id"],
                    payload_records_key=ingest_declaration["payload_records_key"],
                    record_key_aliases=dict(
                        ingest_declaration["record_key_aliases"]
                    ),
                ),
                ingested_at=now,
            )
            digest_after_ingest = _graph_digest(database_path)
            view = booted.handle.reader.as_of(tenant_id=tenant_id, at=now)
            federated_entity_uris = tuple(
                record.claim.entity_uri
                for record in view.entities
                if record.claim.entity_class
                == ingest_declaration["federated_entity_class"]
            )
            # --8<-- [end:peer-ingest]

            # --8<-- [start:peer-refusal]
            # 10. The negative case: a real signature spliced onto different
            #     payload bytes, sent over the real socket, is refused as a
            #     typed VALUE rather than raised — and the consumer's substrate
            #     is byte-identical before and after.
            match gate.admit(
                inbound=tampered, consumer_lineage=consumer_lineage, now=now
            ):
                case GateRefusal() as refusal:
                    pass
                case admitted_tampered:
                    raise RuntimeError(
                        f"the consuming Control Plane ADMITTED a tampered"
                        f" envelope: {admitted_tampered}"
                    )
            digest_after_refusal = _graph_digest(database_path)
            # --8<-- [end:peer-refusal]

            return CrossProcessResult(
                tenant_id=tenant_id,
                artifacts=booted.artifacts,
                consumer_policy_version=entitled_policy_version,
                over_mcp=over_mcp,
                mcp_product=mcp_product,
                genuine=genuine,
                tampered=tampered,
                admitted=admitted,
                consumer_lineage=consumer_lineage,
                admission_record=admission_record,
                admission_record_address=record_address,
                admission_store=admission_store,
                audit_events=tuple(registry.audit_events()),
                federated_entity_uris=federated_entity_uris,
                digest_before_ingest=digest_before_ingest,
                digest_after_ingest=digest_after_ingest,
                digest_after_refusal=digest_after_refusal,
                refusal=refusal,
            )
        finally:
            if proc is not None:
                # Reap the whole process group: the child owns servers, and
                # an orphaned server holds ports past this run's lifetime.
                group = os.getpgid(proc.pid)
                try:
                    os.killpg(group, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=TERMINATE_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(group, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                if proc.stdout is not None:
                    proc.stdout.close()
    finally:
        booted.handle.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ccf-example04-consumer-") as scratch:
        root = Path(scratch)
        try:
            run(root=root)
        except BaseException:
            stderr_path = root / "producer-child.stderr"
            if stderr_path.exists():
                captured = stderr_path.read_text(encoding="utf-8")
                if captured:
                    print("producer child stderr:\n" + captured, file=sys.stderr)
            traceback.print_exc()
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
