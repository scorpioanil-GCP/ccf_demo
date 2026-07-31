"""examples/00-quickstart — "Hello, Context Product" (EXAM-01).

The smallest possible fabric, end to end and in one process: register an
ontology, ingest a handful of events through L1, assemble into the graph,
run the four-category operator chain, project, gate, record the decision,
and serve one typed Context Product — keyless and model-free, on SQLite and
the file-backed ArtifactStore (D-12/D-13).

Every domain value — entity classes, source systems, identifiers,
thresholds, policy versions, MAX_TTL, the query, the boundary, the expected
result — is loaded from ``artifacts/*.yaml``. The code below is thin loading
and asserting logic; deleting the artifacts leaves it with nothing
meaningful to run (CLAUDE.md §6.4, the No-Hardcoding Rule).

Run it: ``make example-00`` (or
``PYTHONPATH=src:runtime python examples/00-quickstart/run.py``).
Exit code 0 means every assertion below held; any failure exits nonzero.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from ccf.artifacts.file_store import FileArtifactStore
from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import boot
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    DEBT_PROFILE,
    HALF_LIFE_TABLE,
    DebtProfile,
    HalfLifeTable,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.halflife.decay import Observation, freshness
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
from ccf.replay.record import (
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, serve
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.similarity.protocol import TokenOverlapIndex
from collections.abc import Mapping

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    """Normalize an artifact timestamp to an explicit UTC instant.

    PyYAML resolves ``...Z`` timestamps to *naive* datetimes, and the
    canonical serializer refuses naive datetimes outright (D-IMPL-38 — an
    implicit timezone is a silent default). Attaching UTC at the artifact
    boundary is the loader's job; the fabric never guesses.
    """
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


class QuickstartPlan:
    """The deployment's Π: what the reconciled subgraph means to its reader.

    A projection is deployment code — this is what a user writes. It declares
    which operators its interpretation depends on and interprets their
    output; it does not run them and cannot tell the engine what ran (which
    is what leaves the L6 lineage gate something real to check).
    """

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


def main() -> int:
    ontology = _load("ontology.yaml")
    events = _load("events.yaml")
    control = _load("controlplane.yaml")
    halflife = _load("halflife.yaml")

    tenant_id: str = ontology["tenant_id"]
    keys = control["keys"]
    boundary = _instant(control["decision"]["temporal_boundary"])
    now = _instant(control["decision"]["now"])

    with tempfile.TemporaryDirectory(prefix="ccf-quickstart-") as scratch:
        root = Path(scratch)

        # --- Control Plane: register every declared artifact, versioned -----
        registry = ControlPlaneRegistry()
        spec_version = registry.register(
            keys["resolution_spec"], _resolution_spec(ontology)
        )
        policy_version = registry.register(
            keys["policy_bundle"], control["policy_bundle"]
        )
        table = parse_artifact(halflife["half_life_table"], HALF_LIFE_TABLE)
        profile = parse_artifact(halflife["debt_profile"], DEBT_PROFILE)
        assert isinstance(table, HalfLifeTable)
        assert isinstance(profile, DebtProfile)
        registry.register(keys["half_life_table"], table)
        registry.register(keys["debt_profile"], profile)

        # --- boot the fabric (SQLite reference backend) and ingest via L1 ---
        handle = boot(
            database_path=root / "quickstart.sqlite3",
            registry=registry,
            resolution_spec_key=keys["resolution_spec"],
            resolution_spec_version=spec_version,
            policy_bundle_key=keys["policy_bundle"],
            policy_bundle_version=policy_version,
        )
        try:
            for envelope in _envelopes(ontology, events):
                handle.worker.ingest(envelope)

            # --- L4/L5: the four-category operator chain, from artifacts ----
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
            plan = QuickstartPlan(
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

            # --- L6: the three validation gates ----------------------------
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

            # Lineage strict equality: what the product claims ran is exactly
            # what the engine resolved as having run.
            assert (
                gated.product.lineage.operators_invoked
                == execution.operators_invoked
            )

            # The served view matches what the deployment declared it expects.
            expected = control["expected"]
            payload = gated.product.payload
            assert payload["entity_count"] == expected["entity_count"], payload
            assert sorted(
                {entry["entity_class"] for entry in payload["entities"]}
            ) == sorted(expected["entity_classes"]), payload
            assert payload["relationship_types"] == sorted(
                expected["relationship_types"]
            ), payload

            # --- replay before delivery ------------------------------------
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
            store = FileArtifactStore(root=root / "artifacts")
            served = serve(
                product=gated,
                record=record,
                replay_writer=ReplayWriter(
                    store=store,
                    artifact_class=control["artifacts"]["replay_record_class"],
                ),
            )

            # The record is in the store, content-addressed, and carries all
            # five dimensions of this decision (whitepaper §7.10.1).
            assert store.exists(
                content_address=served.replay_ref.content_address
            )
            assert served.replay_ref.content_address == content_hash(record)
            restored = DecisionReplayRecord.model_validate_json(
                store.get(content_address=served.replay_ref.content_address)
            )
            assert restored == record
            assert restored.context_fabric_snapshot.temporal_boundary == boundary
            assert [
                binding.version
                for binding in restored.policy_bindings.bindings
            ] == [policy_version]
            assert restored.model_version.model_version == "none"  # keyless
            assert (
                restored.perspective_conditioning.role == perspective.role
            )
            assert restored.content_generation_path.plan_id == execution.plan_id

            # --- λ_c: freshness of a declared observation at decision time --
            demonstration = halflife["demonstration"]
            retained = freshness(
                Observation(
                    observation_type=demonstration["observation_type"],
                    observed_at=_instant(demonstration["observed_at"]),
                ),
                now=now,
                table=table,
                risk_sensitivity=profile.risk_sensitivity,
            )
            assert 0 < retained <= 1, retained

            print("examples/00-quickstart: OK")
            print(f"  tenant                 {tenant_id}")
            print(f"  product                {gated.product.schema_name}")
            print(f"  entities served        {payload['entity_count']}")
            print(f"  operators invoked      {len(execution.operators_invoked)}")
            print(f"  replay record          {served.replay_ref.content_address[:16]}…")
            print(
                "  freshness "
                f"({demonstration['observation_type']})  {retained}"
            )
            return 0
        finally:
            handle.close()


if __name__ == "__main__":
    sys.exit(main())
