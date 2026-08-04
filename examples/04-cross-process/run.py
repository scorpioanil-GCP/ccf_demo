"""examples/04-cross-process — assembler and consumer across processes (EXAM-05).

An assembler agent (``ContextAssemblyAgent``) runs in one real OS subprocess
(``producer_child.py``); this process is the consumer. One typed Context
Product crosses the boundary over BOTH transports — MCP egress (whitepaper
§8.3 Pattern 3; CLAUDE.md §7.1) and A2A federation (Pattern 4; CLAUDE.md
§7.2) — with Control Plane admission verification demonstrated on the
consumer side, including the refusal path.

What this demonstrates, as assertions:

* **Two processes, nothing shared but the wire.** The producer's fabric,
  graph and key live in the child's heap; the consumer's live here. The
  spawn uses the READY-handshake pattern — the child prints
  ``READY {mcp_port} {a2a_port}`` once its servers report started, and the
  blocking ``readline()`` below is the gate. No fixed ports, no sleeps.
* **MCP egress (Pattern 3).** The product is read back as an MCP Resource
  and its typed contract validates — and the bytes are the very bytes the
  A2A signature verifies over, so the two front doors serve one product.
* **A2A admission (Pattern 4, D-IMPL-16).** The genuine signed product is
  admitted only after signature verification against the peer's own
  trust-policy entry and the Control Plane policy-binding checks. An
  immutable ``AdmissionRecord`` is persisted at an exact content address
  before anything is reported admitted, and the merged lineage is the
  set-union of producer and consumer (CLAUDE.md §7.2: extends, never
  replaces).
* **Admission only through L2 (single-writer, CLAUDE.md §10).** The
  admitted product reaches L3 through ``AssemblyWorker.ingest_admitted`` —
  a door typed to accept only gate-produced ``AdmittedProduct`` values —
  and the graph digest moves only then.
* **The negative case.** A tampered envelope — a real signature spliced
  onto different payload bytes, emitted over the real socket — is refused
  as a value, the refusal is audited, and the consumer's L3 substrate is
  byte-identical before and after.

Every domain value — tenant, peer identities, ceilings, endpoint path,
federation vocabulary, the consumer's own lineage — is loaded from
``artifacts/*.yaml`` (property-intelligence domain, D-08, authored 100%
fresh per D-07). Run it: ``make example-04``. Exit 0 means every assertion
held; any failure prints the child's captured stderr and exits nonzero.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import traceback
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import httpx
import uvicorn
import yaml
from joserfc.jwk import ECKey

import producer_child as producer

from ccf.artifacts.file_store import FileArtifactStore
from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    FederatedIngestSpec,
)
from ccf.boot import boot
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.mcp.client import McpResourceClient, SyncMcpBridge
from ccf.peering.admission import (
    ADMISSION_RECORD,
    INBOUND_PAYLOAD_CEILING,
    AdmissionRecord,
    AdmittedProduct,
    InboundPayloadCeiling,
    PeeringAdmissionGate,
    SignatureRefusal,
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

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
CHILD = Path(__file__).resolve().parent / "producer_child.py"

#: Deadline every synchronous MCP call is bounded by, and the grace given to
#: a terminated child before escalating to SIGKILL. Process-lifecycle
#: mechanism values, not domain values.
CALL_TIMEOUT_SECONDS = 20.0
TERMINATE_TIMEOUT_SECONDS = 10


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _write_key(directory: Path, key_id: str) -> ECKey:
    """Generate the producer's signing key for this run. Never committed."""
    key = ECKey.generate_key("P-256", parameters={"kid": key_id})
    (directory / f"{key_id}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    return key


def _consumer_resolution_spec(federation: Any) -> EntityResolutionSpec:
    """The consumer's federation-ingress vocabulary, from the artifact.

    The producer's entities arrive as claims about *another* fabric's graph,
    so they resolve into their own declared entity class rather than merging
    into any vocabulary of the consumer's own.
    """
    declared = federation["federation"]["entity_rule"]
    return EntityResolutionSpec(
        semver=federation["artifact_version"],
        entity_rules=(
            EntityResolutionRule(
                match_key=declared["match_key"],
                entity_class=declared["entity_class"],
                identity_keys=tuple(declared["identity_keys"]),
                attribute_keys=tuple(declared["attribute_keys"]),
            ),
        ),
        relationship_rules=(),
    )


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


def main() -> int:
    ontology = _load("ontology.yaml")
    control = _load("controlplane.yaml")
    federation = _load("a2a.yaml")

    tenant_id: str = ontology["tenant_id"]
    consumer_values = federation["consumer"]
    producer_values = federation["producer"]
    declared_class = control["product_class"]
    now = _instant(control["decision"]["now"])

    # The regime the consumer entitles the producer to claim: the content
    # hash of the policy bundle both deployments declared (the Control Plane
    # versions artifacts by content, so no literal has to be transcribed).
    producer_policy_version = content_hash(control["policy_bundle"])

    with tempfile.TemporaryDirectory(prefix="ccf-example04-consumer-") as scratch:
        root = Path(scratch)
        key_dir = root / "keys"
        key_dir.mkdir()
        key = _write_key(key_dir, producer_values["key_id"])

        # --- the consumer's Control Plane: trust is declared, then pinned ---
        # --8<-- [start:peer-trust-policy]
        registry = ControlPlaneRegistry()
        spec_version = registry.register(
            control["keys"]["resolution_spec"],
            _consumer_resolution_spec(federation),
        )
        policy_version = registry.register(
            control["keys"]["policy_bundle"], control["policy_bundle"]
        )
        assert policy_version == producer_policy_version
        trust_version = registry.register_typed(
            trust_policy_key(tenant_id=tenant_id),
            PeeringTrustPolicy(
                semver=consumer_values["semver"],
                tenant_id=tenant_id,
                peers={
                    producer_values["peer_id"]: PeerTrustGrant(
                        signing_keys={
                            producer_values["key_id"]: key.as_dict(private=False)
                        },
                        permitted_producer_hashes=frozenset(
                            {producer_values["producer_hash"]}
                        ),
                        permitted_schema_names=frozenset(
                            {declared_class["schema_name"]}
                        ),
                        permitted_policy_regimes=frozenset(
                            {producer_policy_version}
                        ),
                    )
                },
            ),
            PEERING_TRUST_POLICY,
        )
        ceiling_version = registry.register_typed(
            payload_ceiling_key(tenant_id=tenant_id),
            InboundPayloadCeiling(
                semver=consumer_values["semver"],
                max_payload_bytes=consumer_values[
                    "inbound_payload_ceiling_bytes"
                ],
            ),
            INBOUND_PAYLOAD_CEILING,
        )
        # --8<-- [end:peer-trust-policy]

        # --- the consuming fabric, and the one gate before L2 ---------------
        database_path = root / "consumer.sqlite3"
        handle = boot(
            database_path=database_path,
            registry=registry,
            resolution_spec_key=control["keys"]["resolution_spec"],
            resolution_spec_version=spec_version,
            policy_bundle_key=control["keys"]["policy_bundle"],
            policy_bundle_version=policy_version,
        )
        max_ttl_version = registry.register(
            control["keys"]["max_ttl"],
            MaxTTL(seconds=control["max_ttl_seconds"]),
        )
        product_class = register_product_class(
            registry=registry,
            schema_name=declared_class["schema_name"],
            schema_version=declared_class["schema_version"],
            ttl_anchor=declared_class["ttl_anchor"],
            assembly_mode=declared_class["assembly_mode"],
            max_ttl_key=control["keys"]["max_ttl"],
            max_ttl_version=max_ttl_version,
        )
        # --8<-- [start:peer-gate]
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
            product_classes={declared_class["schema_name"]: product_class},
        )
        consumer_lineage = ProductLineage(
            operators_invoked=frozenset(
                consumer_values["lineage"]["operators_invoked"]
            ),
            policy_bundle_versions=frozenset(
                consumer_values["lineage"]["policy_bundle_versions"]
            ),
            graph_snapshot_at=_instant(
                consumer_values["lineage"]["graph_snapshot_at"]
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
                    local_peer_id=consumer_values["peer_id"],
                    endpoints=lambda *, peer: "",
                    http_client=client,
                    clock=lambda: now,
                    receive_path=consumer_values["receive_path"],
                    max_request_bytes=consumer_values["max_request_bytes"],
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
                        raise AssertionError(
                            "the consumer endpoint failed to start"
                        )

                # --- spawn the assembler subprocess, READY handshake --------
                # Its own session/process group, so teardown can reap the
                # whole group; stderr captured for diagnosis on failure.
                # --8<-- [start:peer-spawn]
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
                                + consumer_values["receive_path"]
                            ),
                            producer.KEY_DIR_VAR: str(key_dir),
                        },
                    )
                assert proc.stdout is not None
                announcement = proc.stdout.readline().decode().strip()
                assert announcement.startswith("READY "), (
                    f"producer child did not announce readiness: "
                    f"{announcement!r}"
                )
                _token, mcp_port, _a2a_port = announcement.split()

                # The child emits before it announces, so both carriages —
                # genuine and tampered — have already been accepted here.
                received = tuple(wire.receive())
                # --8<-- [end:peer-spawn]
                server.should_exit = True
                thread.join(timeout=TERMINATE_TIMEOUT_SECONDS)

            assert len(received) == 2, [m.observed_peer for m in received]
            assert all(
                message.observed_peer.peer_id == producer_values["peer_id"]
                for message in received
            )
            genuine, tampered = received

            # --- (1) MCP egress: typed contract validates over the wire -----
            # --8<-- [start:mcp-egress]
            address = producer.ProductAddress(
                tenant=tenant_id,
                product_class=declared_class["schema_name"],
                version=declared_class["schema_version"],
            )
            with SyncMcpBridge(
                call_timeout_seconds=CALL_TIMEOUT_SECONDS
            ) as bridge:
                mcp_client = McpResourceClient(
                    url=f"http://127.0.0.1:{mcp_port}/mcp", bridge=bridge
                )
                over_mcp = mcp_client.read_text(address.uri)
            mcp_product = ContextProductContract.model_validate_json(over_mcp)
            assert mcp_product.tenant_id == tenant_id
            assert mcp_product.schema_name == declared_class["schema_name"]
            assert mcp_product.lineage.operators_invoked
            # One product, two front doors: the MCP bytes are exactly the
            # bytes the A2A signature was made over.
            assert over_mcp.encode("utf-8") == genuine.signed.canonical_payload()
            # --8<-- [end:mcp-egress]

            # --- (2) A2A admission: verified, recorded, then admitted -------
            # --8<-- [start:peer-admit]
            admitted = gate.admit(
                inbound=genuine, consumer_lineage=consumer_lineage, now=now
            )
            assert isinstance(admitted, AdmittedProduct), admitted
            assert canonical_bytes(admitted.product) == (
                genuine.signed.canonical_payload()
            )

            # Lineage continuity by set-union (CLAUDE.md §7.2): the merged L
            # contains both sides, exactly.
            producer_lineage = admitted.product.lineage
            assert admitted.lineage.operators_invoked == (
                producer_lineage.operators_invoked
                | consumer_lineage.operators_invoked
            )
            assert admitted.lineage.policy_bundle_versions == (
                producer_lineage.policy_bundle_versions
                | consumer_lineage.policy_bundle_versions
            )
            assert producer_policy_version in (
                admitted.lineage.policy_bundle_versions
            )
            assert admitted.lineage.graph_snapshot_at == (
                producer_lineage.graph_snapshot_at
            )
            # --8<-- [end:peer-admit]

            # --8<-- [start:peer-admission-record]
            # The immutable AdmissionRecord exists at an exact version: the
            # audit verdict points at it by content address, the store holds
            # it, and its content hashes back to that very address — no
            # "latest", no overwrite path.
            admitted_events = [
                event
                for event in registry.audit_events()
                if event.action == "peering_admitted"
            ]
            assert len(admitted_events) == 1
            verdict = admitted_events[0]
            assert verdict.artifact_class == ADMISSION_RECORD.class_id
            record_address = verdict.version
            assert admission_store.exists(content_address=record_address)
            record = AdmissionRecord.model_validate_json(
                admission_store.get(content_address=record_address)
            )
            assert content_hash(record) == record_address
            assert record.peer_id == producer_values["peer_id"]
            assert record.merged_lineage == admitted.lineage
            assert record.producer_lineage == producer_lineage
            assert record.consumer_lineage == consumer_lineage
            # --8<-- [end:peer-admission-record]

            # Admission only through L2 (single-writer): the graph moves
            # only when the typed federated door ingests the admitted value.
            # --8<-- [start:peer-ingest]
            before_ingest = _graph_digest(database_path)
            declared_federation = federation["federation"]
            envelopes = handle.worker.ingest_admitted(
                admitted,
                spec=FederatedIngestSpec(
                    source_system_id=declared_federation["system_id"],
                    payload_records_key=declared_federation[
                        "payload_records_key"
                    ],
                    record_key_aliases=dict(
                        declared_federation["record_key_aliases"]
                    ),
                ),
                ingested_at=now,
            )
            assert envelopes
            assert _graph_digest(database_path) != before_ingest
            view = handle.reader.as_of(tenant_id=tenant_id, at=now)
            federated = [
                record_.claim
                for record_ in view.entities
                if record_.claim.entity_class
                == declared_federation["entity_rule"]["entity_class"]
            ]
            assert len(federated) == len(admitted.product.payload["entities"])
            # --8<-- [end:peer-ingest]

            # --- (3) the negative case: tampering is refused, L3 untouched --
            # --8<-- [start:peer-refusal]
            before_refusal = _graph_digest(database_path)
            refusal = gate.admit(
                inbound=tampered, consumer_lineage=consumer_lineage, now=now
            )
            assert isinstance(refusal, GateRefusal), refusal
            assert isinstance(refusal, SignatureRefusal), refusal
            assert refusal.peer_id == producer_values["peer_id"]
            assert _graph_digest(database_path) == before_refusal
            refused_events = [
                event
                for event in registry.audit_events()
                if event.action == "peering_admission_refused"
            ]
            assert refused_events
            assert all(event.resolved is False for event in refused_events)
            assert isinstance(tampered, InboundProduct)
            # --8<-- [end:peer-refusal]

            print("examples/04-cross-process: OK")
            print(f"  tenant                 {tenant_id}")
            print(f"  producer peer          {producer_values['peer_id']}")
            print(f"  product                {declared_class['schema_name']}")
            print(f"  over MCP               {len(over_mcp)} canonical bytes")
            print(
                "  admission record       "
                f"{record_address[:16]}… ({ADMISSION_RECORD.class_id})"
            )
            print(
                "  merged lineage ops     "
                f"{sorted(admitted.lineage.operators_invoked)}"
            )
            print(f"  tampered product       refused ({type(refusal).__name__})")
            return 0
        except BaseException:
            if stderr_path.exists():
                captured = stderr_path.read_text(encoding="utf-8")
                if captured:
                    print(
                        "producer child stderr:\n" + captured, file=sys.stderr
                    )
            traceback.print_exc()
            return 1
        finally:
            handle.close()
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


if __name__ == "__main__":
    sys.exit(main())
