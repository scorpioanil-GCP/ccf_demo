"""The golden ``13bd250`` decision: one deployment, written to run under two trees.

``D-IMPL-243`` (the CR-01 ruling: *"The fixture is the gate."*) and its
amendment 1; whitepaper §7.10; CLAUDE.md §7.4.

This module is imported by TWO trees and must keep working under both:

* under the **``13bd250`` tree** (the Phase 24.5 base, before any 24.5 field
  existed) it PRODUCES the fixture — boots a SQLite fabric at
  ``<fixture>/fabric.sqlite3``, ingests one envelope, runs the real serve
  path, and writes the decision record to a file-backed ArtifactStore at
  ``<fixture>/artifacts`` plus a ``manifest.json`` of every identity the
  record carries. The exact command is in ``README.md`` beside this file;
* under **HEAD** it supplies ``tests/replay/test_golden_13bd250.py`` with
  the same deployment — the plan, the operators, the product envelope — so
  ``replay()`` can re-execute the ``13bd250`` decision against the committed
  graph and hold every re-computed hash against the ones the base tree wrote.

Everything here is fixture: entity classes, identifiers, operator parameters,
the projection. Nothing domain-shaped reaches ``src/``. The module uses only
names that exist in both trees and never imports ``tests``; a name HEAD added
(``store_snapshot_pin`` on a lineage, ``admitted_entity_classes`` on a walk)
is never spelled here, which is the point — the record's walk is the walk as
it was, and HEAD's canonicalizer must render it as the base tree did.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ccf.artifacts.file_store import FileArtifactStore
from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import FabricHandle, boot
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.operators.categories import (
    TemporalAsOf,
    TemporalAsOfParameters,
    TraversalNeighborhood,
    TraversalNeighborhoodParameters,
)
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import ExecutionResult, OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan
from ccf.replay.record import (
    DecisionReplayRecord,
    PolicyBinding,
    ResolutionNotApplicable,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, serve
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

TENANT = "tenant-golden"
T_MARCH = datetime(2026, 3, 1, tzinfo=UTC)
BOUNDARY = datetime(2026, 3, 15, tzinfo=UTC)
NOW = datetime(2026, 3, 15, 12, tzinfo=UTC)

RESOLUTION_SPEC_KEY = "golden/entity-resolution-spec"
POLICY_BUNDLE_KEY = "golden/policy-bundle"
MAX_TTL_KEY = "golden/max-ttl"
PLAN_ID = "golden/exposure-summary"
ARTIFACT_CLASS = "decision-replay-record"
SCHEMA_NAME = "golden.exposure-summary"
SCHEMA_VERSION = "1.0.0"
PRODUCT_TTL_SECONDS = 600

DATABASE_FILE = "fabric.sqlite3"
ARTIFACTS_DIR = "artifacts"
MANIFEST_FILE = "manifest.json"


def resolution_spec() -> EntityResolutionSpec:
    """Two entity classes on different native identifiers, one typed edge."""
    return EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=(
            EntityResolutionRule(
                match_key="counterparty_lei",
                entity_class="counterparty",
                identity_keys=("counterparty_lei",),
                attribute_keys=("counterparty_name", "jurisdiction"),
            ),
            EntityResolutionRule(
                match_key="facility_id",
                entity_class="facility",
                identity_keys=("facility_id",),
                attribute_keys=("facility_type", "currency"),
            ),
        ),
        relationship_rules=(
            RelationshipResolutionRule(
                relationship_type="obligor_of",
                subject_entity_class="counterparty",
                object_entity_class="facility",
            ),
        ),
    )


def policy_bundle() -> dict[str, str]:
    return {"regime": "golden-fixture"}


def envelope() -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=TENANT,
        envelope_id="env-golden-001",
        source=SourceIdentity(system_id="core-banking"),
        ingestion_timestamp=T_MARCH,
        observed_time=T_MARCH,
        raw_payload={
            "counterparty_lei": "LEI-GOLDEN",
            "counterparty_name": "Golden Freight",
            "jurisdiction": "US",
            "facility_id": "FAC-G1",
            "facility_type": "revolver",
            "currency": "USD",
        },
    )


def traversal_parameters() -> TraversalNeighborhoodParameters:
    """The walk, spelled exactly as the base tree could spell it."""
    return TraversalNeighborhoodParameters(
        seed_entity_classes=frozenset({"counterparty"}),
        relationship_types=frozenset({"obligor_of"}),
        depth_limit=1,
    )


def operators() -> OperatorRegistry:
    registry = OperatorRegistry()
    registry.register(
        TemporalAsOf(parameters=TemporalAsOfParameters(require_valid_at_boundary=True))
    )
    registry.register(TraversalNeighborhood(parameters=traversal_parameters()))
    return registry


def perspective() -> Perspective:
    return Perspective(principal_id="analyst-golden", role="credit-analyst")


class Plan:
    """The deployment's Π — thin, fixture-owned, identical under both trees."""

    def required_operators(self) -> tuple[str, ...]:
        return ("temporal.as-of-boundary", "traversal.typed-neighborhood")

    @property
    def plan_id(self) -> str:
        return PLAN_ID

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=PLAN_ID,
            payload={
                "role": perspective.role,
                "entities": [
                    {
                        "entity_uri": record.claim.entity_uri,
                        "name": record.claim.attributes.get("counterparty_name", ""),
                    }
                    for record in view.entities
                ],
            },
        )


class Bindings:
    """What the Control Plane holds for this deployment, and at which versions."""

    def __init__(self, registry: ControlPlaneRegistry) -> None:
        self.registry = registry
        self.spec_version = registry.register(RESOLUTION_SPEC_KEY, resolution_spec())
        self.policy_version = registry.register(POLICY_BUNDLE_KEY, policy_bundle())
        self.max_ttl_version = registry.register(MAX_TTL_KEY, MaxTTL(seconds=3600))

    def product_class(self) -> RegisteredProductClass:
        return register_product_class(
            registry=self.registry,
            schema_name=SCHEMA_NAME,
            schema_version=SCHEMA_VERSION,
            ttl_anchor="from_decision",
            assembly_mode="algorithmic",
            max_ttl_key=MAX_TTL_KEY,
            max_ttl_version=self.max_ttl_version,
        )


def boot_fabric(*, database_path: Path, bindings: Bindings) -> FabricHandle:
    """Boot the fabric over ``database_path`` with the bindings already registered."""
    return boot(
        backend="sqlite",
        connection={"database_path": database_path},
        registry=bindings.registry,
        resolution_spec_key=RESOLUTION_SPEC_KEY,
        resolution_spec_version=bindings.spec_version,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        policy_bundle_version=bindings.policy_version,
    )


def execute(handle: FabricHandle) -> ExecutionResult:
    return ProjectionEngine(reader=handle.reader, registry=operators()).execute(
        plan=Plan(),
        perspective=perspective(),
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
    )


def candidate(execution: ExecutionResult, *, policy_version: str) -> ContextProductContract:
    return ContextProductContract(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        plan_id=execution.plan_id,
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        expires_at=NOW + timedelta(seconds=PRODUCT_TTL_SECONDS),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=execution.operators_invoked,
            policy_bundle_versions=frozenset({policy_version}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload=execution.projection.payload,
    )


class Environment:
    """The deployment side of replay, for HEAD to verify against the record.

    Every vessel field the record carries on dimension 5 is read back off the
    record — the ``D-IMPL-100``/``D-IMPL-118`` discipline — and every one of
    them sits at its sentinel for this decision, so the rebuilt product is
    the candidate as it was served.
    """

    def __init__(self, bindings: Bindings) -> None:
        self._plans: dict[str, ProjectionPlan] = {PLAN_ID: Plan()}

    def resolve_plan(self, *, plan_id: str) -> ProjectionPlan:
        try:
            return self._plans[plan_id]
        except KeyError:
            raise LookupError(plan_id) from None

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> OperatorRegistry:
        return operators()

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: ProjectionOutput
    ) -> ContextProductContract:
        path = record.content_generation_path
        return ContextProductContract(
            schema_name=SCHEMA_NAME,
            schema_version=SCHEMA_VERSION,
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=record.context_fabric_snapshot.temporal_boundary,
            expires_at=NOW + timedelta(seconds=PRODUCT_TTL_SECONDS),
            ttl_anchor="from_decision",
            lineage=ProductLineage(
                operators_invoked=frozenset(path.operator_plan),
                policy_bundle_versions=frozenset(
                    binding.version for binding in record.policy_bindings.bindings
                ),
                graph_snapshot_at=record.context_fabric_snapshot.temporal_boundary,
            ),
            payload=projection.payload,
            debt=path.debt,
            debt_evidence=path.debt_evidence,
            source_refresh_recency=path.source_refresh_recency,
            obligation_in_force=path.obligation_in_force,
        )


def produce(fixture_dir: Path) -> dict[str, Any]:
    """Write the fixture under ``fixture_dir``; return the manifest written."""
    database_path = fixture_dir / DATABASE_FILE
    artifacts = fixture_dir / ARTIFACTS_DIR
    if database_path.exists() or artifacts.exists():
        raise SystemExit(f"refusing to overwrite an existing fixture under {fixture_dir}")
    fixture_dir.mkdir(parents=True, exist_ok=True)

    bindings = Bindings(ControlPlaneRegistry())
    handle = boot_fabric(database_path=database_path, bindings=bindings)
    try:
        handle.worker.ingest(envelope())
        execution = execute(handle)
        product_class = bindings.product_class()
        gated = run_gates(
            candidate(execution, policy_version=bindings.policy_version),
            engine_resolved=execution.operators_invoked,
            now=NOW,
            registry=bindings.registry,
            product_class=product_class,
        )
        assert isinstance(gated, ServableProduct), gated
        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=perspective(),
            policy_bindings=(
                PolicyBinding(key=POLICY_BUNDLE_KEY, version=bindings.policy_version),
            ),
            assembly_mode="algorithmic",
            recorded_at=NOW,
            # 24.7-06 (D-IMPL-264 D-10 / D-12): the builder now requires an
            # explicit resolution state, and this path ran no resolution step.
            # This script is a REGENERATION AID whose OUTPUT is the committed
            # D-12 control (`artifacts/`, `manifest.json`, `fabric.sqlite3`),
            # captured at 13bd250 with the legacy sentinel. It is edited so it
            # stays a valid script against the ruled API; it is NOT run inside
            # 24.7, and `test_golden_13bd250.py` never calls `produce()` -- it
            # replays the STORED record. Running it would move the control.
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        )
        served = serve(
            product=gated,
            record=record,
            replay_writer=ReplayWriter(
                store=FileArtifactStore(root=artifacts), artifact_class=ARTIFACT_CLASS
            ),
        )
    finally:
        handle.close()

    import ccf

    path = record.content_generation_path
    manifest: dict[str, Any] = {
        "producing_commit": os.environ.get("GOLDEN_PRODUCING_COMMIT", "unstated"),
        "ccf_package_file": str(Path(ccf.__file__).resolve()),
        "record_content_address": served.replay_ref.content_address,
        "record_uri": served.replay_ref.uri,
        "tenant_id": TENANT,
        "temporal_boundary": BOUNDARY.isoformat(),
        "resolution_spec_version": bindings.spec_version,
        "policy_bundle_version": bindings.policy_version,
        "max_ttl_version": bindings.max_ttl_version,
        "product_class_content_hash": content_hash(product_class),
        "traversal_parameter_hash": content_hash(traversal_parameters()),
        "steps": [step.model_dump() for step in path.steps],
        "graph_query_sequence": list(path.graph_query_sequence),
        "product_content_address": path.product_content_address,
        "graph_snapshot_id": record.context_fabric_snapshot.graph_snapshot_id,
        "store_watermark": record.context_fabric_snapshot.store_watermark,
    }
    (fixture_dir / MANIFEST_FILE).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: produce.py <fixture-dir>")
    written = produce(Path(sys.argv[1]).resolve())
    print(json.dumps(written, indent=2, sort_keys=True))
