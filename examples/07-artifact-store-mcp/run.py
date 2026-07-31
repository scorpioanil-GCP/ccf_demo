"""examples/07-artifact-store-mcp — the §7.4 pluggability proof (EXAM-08).

One fabric workload — boot from artifacts, ingest through L1, run the
four-category operator chain, project, gate, record the decision, persist
the product and its replay record — executed twice: once against the
file-backed ``FileArtifactStore``, once against the MCP-backed reference
store running in a real subprocess. **Nothing else in the deployment
changes** (CLAUDE.md §7.4): the store is constructed from a store-config
artifact through one factory seam, there is exactly one workload function,
and the only thing that differs between the two runs is which YAML file
names the store.

What this demonstrates, as assertions:

* **Byte equality.** The served Context Product's canonical bytes are
  identical across the two runs — the substrate is invisible to the fabric.
* **Same artifacts, exact versions.** The same artifact classes land at the
  same content addresses under the same versioned URIs on both stores, and
  every URI the MCP run recorded resolves against a *fresh* client to its
  exact address (never "latest") with the exact bytes behind it.
* **Configuration, not code.** The workload never mentions a backend; the
  store choice lives in ``artifacts/store_{file,mcp}.yaml``. Deleting the
  artifacts leaves this driver nothing to run (CLAUDE.md §6.4).

Domain values (logistics, D-09 — the swap is the point, the domain is
scenery) all live in ``artifacts/*.yaml``. Run it: ``make example-07``.
Exit 0 means every assertion held; any failure prints the store child's
captured stderr and exits nonzero.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import yaml

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol
from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import boot
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.mcp.client import SyncMcpBridge
from ccf.mcp.errors import McpServerUnreachable
from ccf.operators.base import OperatorOutput
from ccf.operators.categories import (
    PolicyFilter,
    PolicyFilterParameters,
    SimilaritySelect,
    SimilaritySelectParameters,
    TemporalAsOf,
    TemporalAsOfParameters,
    TraversalNeighborhood,
    TraversalNeighborhoodParameters,
)
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import PolicyBinding, build_replay_record
from ccf.replay.serve import ReplayWriter, serve
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.similarity.protocol import TokenOverlapIndex
from collections.abc import Mapping

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
CHILD = Path(__file__).resolve().parent / "mcp_store_child.py"

#: Deadline every synchronous MCP call is bounded by, the grace given to a
#: terminated child before escalating to SIGKILL, and the health-check
#: cadence. Process-lifecycle mechanism values, not domain values.
CALL_TIMEOUT_SECONDS = 20.0
TERMINATE_TIMEOUT_SECONDS = 10
HEALTH_CHECK_ATTEMPTS = 5
HEALTH_CHECK_INTERVAL_SECONDS = 1.0


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _resolution_spec(ontology: Any) -> EntityResolutionSpec:
    return EntityResolutionSpec(
        entity_rules=tuple(
            EntityResolutionRule(
                match_key=rule["match_key"],
                entity_class=rule["entity_class"],
                identity_keys=tuple(rule["identity_keys"]),
                attribute_keys=tuple(rule.get("attribute_keys", ())),
            )
            for rule in ontology["entity_rules"]
        ),
        relationship_rules=tuple(
            RelationshipResolutionRule(
                relationship_type=rule["relationship_type"],
                subject_entity_class=rule["subject_entity_class"],
                object_entity_class=rule["object_entity_class"],
            )
            for rule in ontology["relationship_rules"]
        ),
    )


def _envelopes(ontology: Any, events: Any) -> tuple[SignalEnvelope, ...]:
    return tuple(
        SignalEnvelope(
            tenant_id=ontology["tenant_id"],
            envelope_id=item["envelope_id"],
            source=SourceIdentity(system_id=item["source_system_id"]),
            ingestion_timestamp=_instant(item["ingestion_timestamp"]),
            observed_time=_instant(item["observed_time"]),
            raw_payload=dict(item["payload"]),
        )
        for item in events["envelopes"]
    )


class ShipmentPlan:
    """The deployment's Π: what the reconciled subgraph means to its reader."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...]) -> None:
        self._plan_id = plan_id
        self._required = required

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "entity_count": len(view.entities),
                "entities": [
                    {
                        "entity_uri": record.claim.entity_uri,
                        "entity_class": record.claim.entity_class,
                    }
                    for record in view.entities
                ],
                "relationship_types": sorted(
                    {edge.claim.relationship_type for edge in view.relationships}
                ),
            },
        )


# --- the one store seam ------------------------------------------------------
#
# A factory keyed by the config artifact's declared `store.type`. This is the
# only place in the file a backend is named, and the workload below receives
# whatever the artifact declared — no conditional around workload logic.


def _file_store(declared: Any, stack: ExitStack) -> ArtifactStoreProtocol:
    return FileArtifactStore(root=os.environ[declared["root_env"]])


def _mcp_store(declared: Any, stack: ExitStack) -> ArtifactStoreProtocol:
    auth = declared["auth"]

    def authorized_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={"Authorization": f"Bearer {auth['token']}"}
        )

    bridge = stack.enter_context(
        SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS)
    )
    return McpArtifactStore(
        url=os.environ[declared["endpoint_env"]],
        bridge=bridge,
        http_client_factory=authorized_client,
    )


_STORE_FACTORIES = {"file": _file_store, "mcp": _mcp_store}


def build_store(config_name: str, stack: ExitStack) -> ArtifactStoreProtocol:
    """Construct the store the named config artifact declares."""
    declared = _load(config_name)["store"]
    return _STORE_FACTORIES[declared["type"]](declared, stack)


# --- the one workload --------------------------------------------------------


def workload(
    store_config_name: str,
) -> tuple[bytes, tuple[ArtifactRef, ...]]:
    """Run the full fabric workload against the configured store.

    Called exactly twice, with only ``store_config_name`` differing — that
    is the structural form of "nothing else in the deployment changes".

    Returns:
        The served product's canonical bytes, and the refs of every artifact
        persisted to the store (the replay record and the product at rest).
    """
    ontology = _load("ontology.yaml")
    events = _load("events.yaml")
    control = _load("controlplane.yaml")

    tenant_id: str = ontology["tenant_id"]
    keys = control["keys"]
    boundary = _instant(control["decision"]["temporal_boundary"])
    now = _instant(control["decision"]["now"])

    with tempfile.TemporaryDirectory(prefix="ccf-example07-run-") as scratch:
        root = Path(scratch)

        registry = ControlPlaneRegistry()
        spec_version = registry.register(
            keys["resolution_spec"], _resolution_spec(ontology)
        )
        policy_version = registry.register(
            keys["policy_bundle"], control["policy_bundle"]
        )

        handle = boot(
            database_path=root / "fabric.sqlite3",
            registry=registry,
            resolution_spec_key=keys["resolution_spec"],
            resolution_spec_version=spec_version,
            policy_bundle_key=keys["policy_bundle"],
            policy_bundle_version=policy_version,
        )
        try:
            for envelope in _envelopes(ontology, events):
                handle.worker.ingest(envelope)

            params = control["operator_parameters"]
            operators = OperatorRegistry()
            operators.register(
                PolicyFilter(
                    parameters=PolicyFilterParameters(
                        permitted_policy_bundle_versions=frozenset(
                            {policy_version}
                        ),
                        classification_attribute_by_class=dict(
                            ontology["classification_attribute_by_class"]
                        ),
                        permitted_classifications=frozenset(
                            params["policy"]["permitted_classifications"]
                        ),
                    )
                )
            )
            corpus_attribute = ontology["similarity_corpus_attribute_by_class"]
            view = handle.reader.as_of(tenant_id=tenant_id, at=boundary)
            corpus = {
                (tenant_id, record.claim.entity_uri): record.claim.attributes[
                    corpus_attribute[record.claim.entity_class]
                ]
                for record in view.entities
                if record.claim.entity_class in corpus_attribute
            }
            operators.register(
                SimilaritySelect(
                    parameters=SimilaritySelectParameters(
                        query=params["similarity"]["query"],
                        minimum_score_percent=params["similarity"][
                            "minimum_score_percent"
                        ],
                        ranked_entity_classes=frozenset(
                            params["similarity"]["ranked_entity_classes"]
                        ),
                    ),
                    index=TokenOverlapIndex(
                        corpus=corpus,
                        index_version=params["similarity"]["index_version"],
                    ),
                )
            )
            operators.register(
                TemporalAsOf(
                    parameters=TemporalAsOfParameters(
                        require_valid_at_boundary=params["temporal"][
                            "require_valid_at_boundary"
                        ]
                    )
                )
            )
            operators.register(
                TraversalNeighborhood(
                    parameters=TraversalNeighborhoodParameters(
                        seed_entity_classes=frozenset(
                            params["traversal"]["seed_entity_classes"]
                        ),
                        relationship_types=frozenset(
                            params["traversal"]["relationship_types"]
                        ),
                        depth_limit=params["traversal"]["depth_limit"],
                    )
                )
            )

            declared = control["product_class"]
            plan = ShipmentPlan(
                plan_id=declared["plan_id"], required=operators.keys()
            )
            perspective = Perspective(
                principal_id=control["perspective"]["principal_id"],
                role=control["perspective"]["role"],
            )
            engine = ProjectionEngine(reader=handle.reader, registry=operators)
            execution = engine.execute(
                plan=plan,
                perspective=perspective,
                tenant_id=tenant_id,
                temporal_boundary=boundary,
            )

            max_ttl_version = registry.register(
                keys["max_ttl"], MaxTTL(seconds=control["max_ttl_seconds"])
            )
            product_class = register_product_class(
                registry=registry,
                schema_name=declared["schema_name"],
                schema_version=declared["schema_version"],
                ttl_anchor=declared["ttl_anchor"],
                assembly_mode=declared["assembly_mode"],
                max_ttl_key=keys["max_ttl"],
                max_ttl_version=max_ttl_version,
            )
            candidate = ContextProductContract(
                schema_name=product_class.schema_name,
                schema_version=product_class.schema_version,
                plan_id=execution.plan_id,
                tenant_id=tenant_id,
                temporal_boundary=boundary,
                expires_at=now
                + timedelta(seconds=declared["product_ttl_seconds"]),
                ttl_anchor=product_class.ttl_anchor,
                lineage=ProductLineage(
                    operators_invoked=execution.operators_invoked,
                    policy_bundle_versions=frozenset({policy_version}),
                    graph_snapshot_at=boundary,
                ),
                payload=execution.projection.payload,
            )
            gated = run_gates(
                candidate,
                engine_resolved=execution.operators_invoked,
                now=now,
                registry=registry,
                product_class=product_class,
            )
            assert isinstance(gated, ServableProduct), gated

            expected = control["expected"]
            payload = gated.product.payload
            assert payload["entity_count"] == expected["entity_count"], payload
            assert sorted(
                {entry["entity_class"] for entry in payload["entities"]}
            ) == sorted(expected["entity_classes"]), payload
            assert payload["relationship_types"] == sorted(
                expected["relationship_types"]
            ), payload

            record = build_replay_record(
                execution=execution,
                product=gated.product,
                perspective=perspective,
                policy_bindings=(
                    PolicyBinding(
                        key=keys["policy_bundle"], version=policy_version
                    ),
                ),
                assembly_mode=declared["assembly_mode"],
                recorded_at=now,
            )

            # --- persistence: the ONLY store-touching lines in the workload --
            with ExitStack() as stack:
                store = build_store(store_config_name, stack)
                served = serve(
                    product=gated,
                    record=record,
                    replay_writer=ReplayWriter(
                        store=store,
                        artifact_class=control["artifacts"][
                            "replay_record_class"
                        ],
                    ),
                )
                product_ref = store.put(
                    tenant_id=tenant_id,
                    artifact_class=control["artifacts"]["product_class"],
                    name=control["artifacts"]["product_name"],
                    artifact=gated.product,
                )
            return canonical_bytes(gated.product), (
                served.replay_ref,
                product_ref,
            )
        finally:
            handle.close()


# --- child lifecycle and health ---------------------------------------------


def _health_check(store_config_name: str) -> None:
    """Prove the MCP store answers before running the workload against it.

    Up to five attempts a second apart against the store's presence surface.
    A child that never becomes healthy surfaces here as a clear startup
    error rather than as a masked connection failure mid-workload.
    """
    probe = content_hash(_load("controlplane.yaml")["policy_bundle"])
    last: Exception | None = None
    for _ in range(HEALTH_CHECK_ATTEMPTS):
        with ExitStack() as stack:
            store = build_store(store_config_name, stack)
            try:
                store.exists(content_address=probe)
                return
            except McpServerUnreachable as refused:
                last = refused
        time.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
    raise AssertionError(
        f"the MCP artifact store never became healthy "
        f"({HEALTH_CHECK_ATTEMPTS} attempts): {last}"
    )


def main() -> int:
    store_mcp = _load("store_mcp.yaml")["store"]
    store_file = _load("store_file.yaml")["store"]

    proc: subprocess.Popen[bytes] | None = None
    with tempfile.TemporaryDirectory(prefix="ccf-example07-") as scratch:
        root = Path(scratch)
        stderr_path = root / "mcp-store-child.stderr"
        try:
            # --- run 1: the file-backed store ---------------------------------
            os.environ[store_file["root_env"]] = str(root / "file-artifacts")
            file_bytes, file_refs = workload("store_file.yaml")

            # --- spawn the MCP artifact server, READY handshake ---------------
            with stderr_path.open("wb") as stderr_sink:
                proc = subprocess.Popen(
                    [sys.executable, str(CHILD)],
                    stdout=subprocess.PIPE,
                    stderr=stderr_sink,
                    start_new_session=True,
                )
            assert proc.stdout is not None
            announcement = proc.stdout.readline().decode().strip()
            assert announcement.startswith("READY "), (
                f"store child did not announce readiness: {announcement!r}"
            )
            port = int(announcement.split()[1])
            os.environ[store_mcp["endpoint_env"]] = (
                f"http://127.0.0.1:{port}/mcp"
            )
            _health_check("store_mcp.yaml")

            # --- run 2: the identical workload, MCP-backed store --------------
            mcp_bytes, mcp_refs = workload("store_mcp.yaml")

            # --- the pluggability assertions ----------------------------------
            # (1) The served product is byte-identical across the two stores.
            assert mcp_bytes == file_bytes

            # (2) The same artifacts landed, at the same exact versions: same
            # classes and names in the URIs, same content addresses.
            assert len(mcp_refs) == len(file_refs)
            for over_file, over_mcp in zip(file_refs, mcp_refs, strict=True):
                assert over_mcp.uri == over_file.uri
                assert over_mcp.content_address == over_file.content_address

            # (3) Every artifact the MCP run recorded is retrievable from a
            # FRESH client at its exact version — the naming index is the
            # server's, and no "latest" was ever involved.
            with ExitStack() as stack:
                fresh = build_store("store_mcp.yaml", stack)
                for ref in mcp_refs:
                    assert fresh.resolve_uri(uri=ref.uri) == ref.content_address
                    assert fresh.exists(content_address=ref.content_address)
                served_product = ContextProductContract.model_validate_json(
                    fresh.get(content_address=mcp_refs[1].content_address)
                )
            assert canonical_bytes(served_product) == file_bytes

            print("examples/07-artifact-store-mcp: OK")
            print("  stores                 FileArtifactStore, McpArtifactStore")
            print(f"  product bytes          {len(file_bytes)} (byte-identical)")
            for ref in mcp_refs:
                print(f"  artifact               {ref.uri}")
            print("  swap surface           artifacts/store_{file,mcp}.yaml")
            return 0
        except BaseException:
            if stderr_path.exists():
                captured = stderr_path.read_text(encoding="utf-8")
                if captured:
                    print(
                        "mcp store child stderr:\n" + captured, file=sys.stderr
                    )
            traceback.print_exc()
            return 1
        finally:
            if proc is not None:
                # Reap the whole process group: the child owns a server, and
                # an orphaned server holds its port past this run's lifetime.
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
