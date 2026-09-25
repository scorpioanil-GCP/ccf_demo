"""The proto-quickstart: L1 → L6 end to end on a banking fixture (D-01/D-02).

The private precursor of ``archive/examples/00-quickstart``, which Phase 8 formalizes.
It runs the whole vertical slice — ingest signal envelopes through L2 into the
SQLite graph, execute the four-category operator chain, project, gate, record
the decision, deliver — and it exists to answer one question per invariant:
*would this catch the invariant being broken?*

===============================================  ==============================
Invariant                                        What would fail here
===============================================  ==============================
single-writer (INV-CH7-10)                       there is no writer to obtain;
                                                 the fabric is booted through
                                                 the real composition root
idempotent upsert (INV-CH7-16)                   a re-delivered envelope would
                                                 create a second claim
lineage set-union (INV-CH7-17)                   a second source would
                                                 overwrite instead of
                                                 accumulate; a re-delivery
                                                 would accumulate instead of
                                                 collapse
policy substitution (INV-CH7-26)                 the restricted covenant, or
                                                 the edge to it, would survive
similarity ranking (INV-CH7-27)                  the out-of-scope facility
                                                 would survive
bounded traversal (INV-CH7-24)                   the walk would reach past its
                                                 typed, depth-bounded
                                                 neighborhood
the three gates (INV-CH7-46/47/48)               a forged, empty or over-TTL
                                                 product would become servable
replay before delivery (INV-CH7-79)              a product would be served with
                                                 no record in the store
===============================================  ==============================

Every domain value — entity classes, source systems, identifiers, thresholds,
policy versions, MAX_TTL, the query, the boundary — is loaded from
``tests/fixtures/banking/*.yaml``. The code below is thin loading and asserting
logic; deleting the fixtures would leave it with nothing to run (CLAUDE.md
§6.4, applied to fixture code per CONTEXT.md).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

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
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import (
    EmptyOperatorRefusal,
    LineageMismatchRefusal,
    ServableProduct,
    TTLRefusal,
    run_gates,
)
from ccf.projection.engine import ExecutionResult, OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    NO_AGENT_DEFINITION,
    NO_GRANTS_SET_HASH,
    DecisionReplayRecord,
    PolicyBinding,
    ResolutionNotApplicable,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, ServedProduct, serve
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.similarity.protocol import TokenOverlapIndex
from tests.composition import register_at_composition
from tests.composition import composition_replay_mint, declaring_store

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


def _load(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    """Normalize a fixture timestamp to an explicit UTC instant.

    PyYAML resolves ``...Z`` timestamps to *naive* datetimes, and the canonical
    serializer refuses naive datetimes outright (D-IMPL-38 — an implicit
    timezone is a silent default). Attaching UTC here, at the fixture
    boundary, is the loader's job; the fabric never guesses.
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


# --- fixture loading -------------------------------------------------------


@pytest.fixture(scope="module")
def ontology() -> Any:
    return _load("ontology.yaml")


@pytest.fixture(scope="module")
def control() -> Any:
    return _load("controlplane.yaml")


@pytest.fixture(scope="module")
def events() -> Any:
    return _load("events.yaml")


def _resolution_spec(ontology: Any) -> EntityResolutionSpec:
    return EntityResolutionSpec(
        semver="1.0.0",
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


class _Fabric:
    """Everything the slice needs, wired the way a deployment would wire it."""

    def __init__(
        self,
        *,
        handle: FabricHandle,
        registry: ControlPlaneRegistry,
        policy_version: str,
        ontology: Any,
        control: Any,
    ) -> None:
        self.handle = handle
        self.registry = registry
        self.policy_version = policy_version
        self.ontology = ontology
        self.control = control
        self.tenant_id: str = ontology["tenant_id"]
        self.boundary = _instant(control["decision"]["temporal_boundary"])
        self.now = _instant(control["decision"]["now"])


@pytest.fixture
def fabric(
    tmp_path: Path, ontology: Any, control: Any, events: Any
) -> Iterator[_Fabric]:
    """Boot a fabric from the fixtures and ingest the whole event stream."""
    keys = control["keys"]
    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = register_at_composition(registry, keys["policy_bundle"], control["policy_bundle"])
    handle = boot(
        backend="sqlite",
        connection={"database_path": tmp_path / "acme-bank.sqlite3"},
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
        tenant_ids=(ontology["tenant_id"],),
    )
    try:
        for envelope in _envelopes(ontology, events):
            handle.worker.ingest(envelope)
        yield _Fabric(
            handle=handle,
            registry=registry,
            policy_version=policy_version,
            ontology=ontology,
            control=control,
        )
    finally:
        handle.close()


# --- the projection this deployment serves ---------------------------------


class CreditExposureSummaryPlan:
    """The deployment's Π: what the reconciled subgraph means to an analyst.

    A projection is deployment code — this is what a user writes. It declares
    which operators its interpretation depends on and interprets their output;
    it does not run them, does not know their order, and cannot tell the engine
    what ran (which is what leaves the L6 lineage gate something real to check).
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


def _operators(fabric: _Fabric) -> OperatorRegistry:
    """Register the slice's four operators, parameterized from the fixtures."""
    params = fabric.control["operator_parameters"]
    ontology = fabric.ontology
    registry = OperatorRegistry()
    registry.register(
        PolicyFilter(
            parameters=PolicyFilterParameters(
                permitted_policy_bundle_versions=frozenset({fabric.policy_version}),
                classification_attribute_by_class=dict(
                    ontology["classification_attribute_by_class"]
                ),
                permitted_classifications=frozenset(
                    params["policy"]["permitted_classifications"]
                ),
            )
        )
    )
    registry.register(
        SimilaritySelect(
            parameters=SimilaritySelectParameters(
                query=params["similarity"]["query"],
                minimum_score_percent=params["similarity"]["minimum_score_percent"],
                ranked_entity_classes=frozenset(
                    params["similarity"]["ranked_entity_classes"]
                ),
            ),
            index=_corpus_index(fabric),
        )
    )
    registry.register(
        TemporalAsOf(
            parameters=TemporalAsOfParameters(
                require_valid_at_boundary=params["temporal"][
                    "require_valid_at_boundary"
                ]
            )
        )
    )
    registry.register(
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
    return registry


def _corpus_index(fabric: _Fabric) -> TokenOverlapIndex:
    """Build the similarity corpus from the graph, per the ontology's mapping.

    The corpus is deployment content: which attribute means "this facility" is
    declared in the ontology fixture, and the SDK holds neither the mapping nor
    the text.
    """
    attribute_by_class = fabric.ontology["similarity_corpus_attribute_by_class"]
    view = fabric.handle.reader.as_of(
        tenant_id=fabric.tenant_id, at=fabric.boundary
    )
    corpus: dict[tuple[str, str], str] = {}
    for record in view.entities:
        attribute = attribute_by_class.get(record.claim.entity_class)
        if attribute is None:
            continue
        text = record.claim.attributes.get(attribute)
        if text is not None:
            corpus[(fabric.tenant_id, record.claim.entity_uri)] = text
    return TokenOverlapIndex(
        corpus=corpus,
        index_version=fabric.control["operator_parameters"]["similarity"][
            "index_version"
        ],
    )


def _execute(fabric: _Fabric) -> ExecutionResult:
    registry = _operators(fabric)
    plan = CreditExposureSummaryPlan(
        plan_id=fabric.control["product_class"]["plan_id"],
        required=registry.keys(),
    )
    engine = ProjectionEngine(reader=fabric.handle.reader, registry=registry)
    perspective_values = fabric.control["perspective"]
    return engine.execute(
        plan=plan,
        perspective=Perspective(
            principal_id=perspective_values["principal_id"],
            role=perspective_values["role"],
        ),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )


def _product_class(fabric: _Fabric) -> RegisteredProductClass:
    declared = fabric.control["product_class"]
    max_ttl_version = register_at_composition(fabric.registry, fabric.control["keys"]["max_ttl"],
        MaxTTL(seconds=fabric.control["max_ttl_seconds"]),
    )
    return register_product_class(
        registry=fabric.registry,
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        ttl_anchor=declared["ttl_anchor"],
        assembly_mode=declared["assembly_mode"],
        max_ttl_key=fabric.control["keys"]["max_ttl"],
        max_ttl_version=max_ttl_version,
    )


def _candidate(
    fabric: _Fabric,
    execution: ExecutionResult,
    product_class: RegisteredProductClass,
    *,
    operators: frozenset[str] | None = None,
    expires_at: datetime | None = None,
) -> ContextProductContract:
    declared = fabric.control["product_class"]
    return ContextProductContract(
        schema_name=product_class.schema_name,
        schema_version=product_class.schema_version,
        plan_id=execution.plan_id,
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
        expires_at=expires_at
        or fabric.now + timedelta(seconds=declared["product_ttl_seconds"]),
        ttl_anchor=product_class.ttl_anchor,
        lineage=ProductLineage(
            operators_invoked=(
                execution.operators_invoked if operators is None else operators
            ),
            policy_bundle_versions=frozenset({fabric.policy_version}),
            graph_snapshot_at=fabric.boundary,
        ),
        payload=execution.projection.payload,
    )


def _serve(fabric: _Fabric, store: FileArtifactStore) -> tuple[
    ExecutionResult, ServedProduct, DecisionReplayRecord
]:
    """The full serve path, exactly as a deployment would run it."""
    execution = _execute(fabric)
    product_class = _product_class(fabric)
    gated = run_gates(
        _candidate(fabric, execution, product_class),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct)
    record = build_replay_record(
        execution=execution,
        product=gated.product,
        perspective=Perspective(
            principal_id=fabric.control["perspective"]["principal_id"],
            role=fabric.control["perspective"]["role"],
        ),
        policy_bindings=(
            PolicyBinding(
                key=fabric.control["keys"]["policy_bundle"],
                version=fabric.policy_version,
            ),
        ),
        assembly_mode=fabric.control["product_class"]["assembly_mode"],
        recorded_at=fabric.now,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )
    served = serve(
        product=gated,
        record=record,
        replay_writer=ReplayWriter(
            # D-IMPL-354: the test is this fabric's composition root and mints
            # the ReplayMint for the class its control document declares.
            authorized=composition_replay_mint(
                fabric.registry,
                tenant=fabric.tenant_id,
                artifact_class=fabric.control["artifacts"]["replay_record_class"],
            ),
            store=store,
        ),
    )
    return execution, served, record


# --- L1 → L3: assembly, idempotence, lineage accumulation ------------------


def test_a_double_sourced_entity_is_one_node_with_accumulated_lineage(
    fabric: _Fabric,
) -> None:
    """One counterparty node; corroboration and supersession both visible.

    The same LEI arrives from core banking and the KYC registry asserting the
    same state — one claim, two lineage entries (INV-CH7-17/18). The verbatim
    re-delivery contributes nothing, because a lineage entry's identity is the
    whole observation. The later observation supersedes rather than overwrites,
    and the corroborated claim stays readable with its evidence intact
    (INV-CH7-04).
    """
    view = fabric.handle.reader.as_of(
        tenant_id=fabric.tenant_id, at=fabric.boundary
    )
    counterparties = [
        record for record in view.entities if record.claim.entity_class == "counterparty"
    ]
    assert len(counterparties) == 1

    history = fabric.handle.reader.entity_history(
        tenant_id=fabric.tenant_id,
        entity_uri=counterparties[0].claim.entity_uri,
    )
    assert len(history) == 2
    corroborated, current = history
    assert {entry.envelope_id for entry in corroborated.claim.lineage} == {
        "env-001",
        "env-002",
    }
    assert {entry.source.system_id for entry in corroborated.claim.lineage} == {
        "core-banking",
        "kyc-registry",
    }
    assert corroborated.superseded_by == current.claim_id
    assert {entry.envelope_id for entry in current.claim.lineage} == {"env-004"}


def test_re_delivering_an_envelope_changes_nothing(
    fabric: _Fabric, ontology: Any, events: Any
) -> None:
    """Idempotent upsert (INV-CH7-16): replay is not evidence."""
    before = fabric.handle.reader.as_of(
        tenant_id=fabric.tenant_id, at=fabric.boundary
    )
    result = fabric.handle.worker.ingest(_envelopes(ontology, events)[0])
    after = fabric.handle.reader.as_of(
        tenant_id=fabric.tenant_id, at=fabric.boundary
    )
    assert all(not upsert.claim_created for upsert in result.entities)
    assert all(upsert.lineage_added == 0 for upsert in result.entities)
    assert content_hash(after) == content_hash(before)


def test_every_entity_class_in_the_ontology_is_present_before_operators(
    fabric: _Fabric,
) -> None:
    """The graph holds the whole multi-type topology; operators reduce it."""
    view = fabric.handle.reader.as_of(
        tenant_id=fabric.tenant_id, at=fabric.boundary
    )
    assert {record.claim.entity_class for record in view.entities} == {
        "counterparty",
        "facility",
        "guarantee",
        "covenant",
    }


# --- L4 → L5: the operator chain and two-stage execution -------------------


def test_the_chain_runs_all_four_categories_in_dependency_order(
    fabric: _Fabric,
) -> None:
    """Policy → Similarity → Temporal → Traversal, every time (INV-CH7-26/28)."""
    execution = _execute(fabric)
    assert [step.category for step in execution.steps] == [
        "policy",
        "similarity",
        "temporal",
        "traversal",
    ]
    assert len(execution.operators_invoked) == 4


def test_restricted_state_is_substituted_out_along_with_its_edges(
    fabric: _Fabric,
) -> None:
    """Policy substitution, not row filtering (INV-CH7-26, INV-CH7-40).

    The restricted covenant is gone *and* so is the ``governs`` edge that
    would otherwise have leaked its existence by absence.
    """
    execution = _execute(fabric)
    classes = {record.claim.entity_class for record in execution.view.entities}
    assert "covenant" not in classes
    types = {edge.claim.relationship_type for edge in execution.view.relationships}
    assert "governs" not in types


def test_similarity_ranks_out_the_off_query_facility(fabric: _Fabric) -> None:
    """The equipment-lease facility is permitted, and still not relevant."""
    execution = _execute(fabric)
    descriptions = {
        record.claim.attributes.get("facility_description")
        for record in execution.view.entities
        if record.claim.entity_class == "facility"
    }
    assert descriptions == {"revolving credit facility usd senior secured"}


def test_the_traversal_reaches_exactly_its_bounded_neighborhood(
    fabric: _Fabric,
) -> None:
    """Bounded expansion of relevance (INV-CH7-24)."""
    execution = _execute(fabric)
    assert sorted(
        record.claim.entity_class for record in execution.view.entities
    ) == ["counterparty", "facility", "guarantee"]
    assert {
        edge.claim.relationship_type for edge in execution.view.relationships
    } == {"obligor_of", "guarantees"}


def test_the_provenance_chain_pins_the_similarity_index_version(
    fabric: _Fabric,
) -> None:
    """INV-CH7-27: the index version travels in L, not in a log line."""
    execution = _execute(fabric)
    assert execution.provenance is not None
    versions: set[str] = set()
    node = execution.provenance
    while True:
        if node.index_version is not None:
            versions.add(node.index_version)
        if not node.upstream:
            break
        node = node.upstream[0]
    assert versions == {
        fabric.control["operator_parameters"]["similarity"]["index_version"]
    }


def test_execution_is_deterministic_for_the_same_boundary(fabric: _Fabric) -> None:
    """Function-determinism (INV-CH7-31), asserted bit-for-bit."""
    assert content_hash(_execute(fabric)) == content_hash(_execute(fabric))


# --- L6: the gates refuse bad products -------------------------------------


def test_the_gates_admit_the_real_product(fabric: _Fabric) -> None:
    execution = _execute(fabric)
    product_class = _product_class(fabric)
    gated = run_gates(
        _candidate(fabric, execution, product_class),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct)
    assert gated.product.payload["entity_count"] == 3


def test_each_gate_refuses_its_own_bad_candidate(fabric: _Fabric) -> None:
    """One deliberately broken product per gate (INV-CH7-46/47/48)."""
    execution = _execute(fabric)
    product_class = _product_class(fabric)

    empty = run_gates(
        _candidate(fabric, execution, product_class, operators=frozenset()),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
    )
    assert isinstance(empty, EmptyOperatorRefusal)

    forged = run_gates(
        _candidate(
            fabric,
            execution,
            product_class,
            operators=execution.operators_invoked | {"operator.never-ran"},
        ),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
    )
    assert isinstance(forged, LineageMismatchRefusal)

    over_ttl = run_gates(
        _candidate(
            fabric,
            execution,
            product_class,
            expires_at=fabric.now
            + timedelta(seconds=fabric.control["max_ttl_seconds"] + 1),
        ),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
    )
    assert isinstance(over_ttl, TTLRefusal)


# --- replay: recorded before delivered, and resolvable afterwards ----------


def test_the_served_product_has_a_replay_record_in_the_store(
    fabric: _Fabric, tmp_path: Path
) -> None:
    store = declaring_store(tmp_path / "artifacts", fabric.control["artifacts"]["replay_record_class"])
    _execution, served, record = _serve(fabric, store)
    assert store.exists(content_address=served.replay_ref.content_address)
    assert served.replay_ref.content_address == content_hash(record)


def test_the_replay_record_round_trips_with_a_matching_content_hash(
    fabric: _Fabric, tmp_path: Path
) -> None:
    """D-IMPL-26: a replay resolves the exact artifact, byte for byte."""
    store = declaring_store(tmp_path / "artifacts", fabric.control["artifacts"]["replay_record_class"])
    _execution, served, record = _serve(fabric, store)
    restored = DecisionReplayRecord.model_validate_json(
        store.get(content_address=served.replay_ref.content_address)
    )
    assert content_hash(restored) == content_hash(record)
    assert restored == record


def test_the_record_carries_the_five_dimensions_of_this_decision(
    fabric: _Fabric, tmp_path: Path
) -> None:
    store = declaring_store(tmp_path / "artifacts", fabric.control["artifacts"]["replay_record_class"])
    execution, _served, record = _serve(fabric, store)

    snapshot = record.context_fabric_snapshot  # 1
    assert snapshot.temporal_boundary == fabric.boundary
    assert snapshot.store_watermark == execution.state_watermark()
    assert len(snapshot.touched_entities) == 3
    assert len(snapshot.touched_relationships) == 2

    assert [binding.version for binding in record.policy_bindings.bindings] == [
        fabric.policy_version
    ]  # 2

    assert record.model_version.model_version == "none"  # 3 — Mode 1

    conditioning = record.perspective_conditioning  # 4
    assert conditioning.role == fabric.control["perspective"]["role"]
    # D-06 extension, pre-agent decision: positive no-agent/no-grants claims
    # and the single-element originating-principal delegation chain (I.2).
    assert conditioning.grant_set_hash == NO_GRANTS_SET_HASH
    assert conditioning.agent_definition_hash == NO_AGENT_DEFINITION
    assert conditioning.delegation_chain == (conditioning.principal_id,)

    path = record.content_generation_path  # 5
    assert path.plan_id == fabric.control["product_class"]["plan_id"]
    assert len(path.steps) == 4
    assert path.operator_plan == tuple(step.operator_key for step in execution.steps)


def test_serving_twice_converges_on_one_immutable_record(
    fabric: _Fabric, tmp_path: Path
) -> None:
    """Same decision, same state, same record — content addressing, not luck."""
    store = declaring_store(tmp_path / "artifacts", fabric.control["artifacts"]["replay_record_class"])
    _e1, first, _r1 = _serve(fabric, store)
    _e2, second, _r2 = _serve(fabric, store)
    assert first.replay_ref.content_address == second.replay_ref.content_address
    stored = [
        path
        for path in (tmp_path / "artifacts").iterdir()
        if not path.name.startswith(".")
    ]
    assert len(stored) == 1
