"""The segmented engine, pinned: split, threading, equivalence, cap, telemetry.

Plan 15.2-07's regression surface for the `D-IMPL-87` at docs/DECISIONS.md:290
resolution, executed at the engine tier:

* **structure-is-plan-static** — ``segment_plan`` is a pure function of the
  plan (`GQ-14` at docs/GRAPH_QUERY_SEMANTICS.md:289): the Similarity-bearing
  four-operator plan splits into exactly ``[pushable: policy]``,
  ``[in-process: similarity]``, ``[pushable: temporal, traversal]`` against
  ``CATEGORY_ORDER``; the no-Similarity plan is one pushable segment.
* **degenerate compile** — an all-``None``-intent plan opens with the implicit
  degenerate pushable segment whose compiled query is the everything-question
  (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122).
* **allowed_entities threading** — observed at the seam with a recording
  reader: the second query of the Similarity-bearing plan carries the
  post-Similarity survivor URIs as ``allowed_entities`` and authors no
  explicit seeds; walk starts are computed within the set (`GQ-15` at
  docs/GRAPH_QUERY_SEMANTICS.md:300, `GQ-17` at
  docs/GRAPH_QUERY_SEMANTICS.md:330).
* **per-plan equivalence, Gate 2 pinned** — for BOTH plan shapes the
  segmented path is byte-identical to the pre-segmentation path (the ``as_of``
  everything-read followed by all operators in-process, computed in-test) at
  the product, ``operators_invoked``, provenance-chain, and
  ``run_gates`` → ``ServableProduct`` levels. Product bytes alone cannot
  prove the lineage story survived re-application (T-15.2-24).
* **cap behavior** — `GQ-18` at docs/GRAPH_QUERY_SEMANTICS.md:342: a
  survivor cap below the survivor count drops the second round trip and
  changes nothing semantically (T-15.2-27: the cap value arrives at the
  constructor, never from SDK code).
* **set-size telemetry** — the D-10 locked sub-clause: one entry per
  in-process → pushable boundary, identical in capped and uncapped runs,
  empty for boundary-free plans, replaced per execution.
* **no-op telemetry** — the degenerate round trip is neither double- nor
  under-counted at the reader's own counters.

Every domain value — classes, thresholds, TTLs, the query, the boundary —
comes from ``tests/fixtures/banking/*.yaml``; the wiring helpers are reused
from ``tests/integration/test_proto_quickstart`` (the existing
``TokenOverlapIndex`` corpus fixture — deliberately not a new index stub).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from ccf.boot import boot
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.protocols import GraphQuery, GraphReader, GraphView
from ccf.operators.base import CATEGORY_ORDER
from ccf.operators.categories import (
    PolicyFilter,
    SimilaritySelect,
    TemporalAsOf,
    TraversalNeighborhood,
)
from ccf.operators.planner import IntermediateCache, build_operator_plan
from ccf.operators.registry import OperatorRegistry
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import ExecutionResult, ExecutionStep, ProjectionEngine
from ccf.projection.plan import Perspective
from ccf.projection.segmentation import (
    InProcessSegment,
    PushableSegment,
    compile_segment_query,
    segment_plan,
)

from tests.integration.test_proto_quickstart import (
    CreditExposureSummaryPlan,
    _candidate,
    _envelopes,
    _Fabric,
    _load,
    _operators,
    _product_class,
    _resolution_spec,
)
from tests.properties.strategies import BOUNDARY, TENANT, shipped_operators

FOUR_OPERATORS = (
    PolicyFilter.key,
    SimilaritySelect.key,
    TemporalAsOf.key,
    TraversalNeighborhood.key,
)
NO_SIMILARITY = (PolicyFilter.key, TemporalAsOf.key, TraversalNeighborhood.key)


# --- fixtures: the booted banking fabric (quickstart wiring, reused) --------


@pytest.fixture(scope="module")
def ontology() -> Any:
    return _load("ontology.yaml")


@pytest.fixture(scope="module")
def control() -> Any:
    return _load("controlplane.yaml")


@pytest.fixture(scope="module")
def events() -> Any:
    return _load("events.yaml")


@pytest.fixture
def fabric(
    tmp_path: Path, ontology: Any, control: Any, events: Any
) -> Iterator[_Fabric]:
    """Boot a fabric from the fixtures and ingest the whole event stream."""
    keys = control["keys"]
    registry = ControlPlaneRegistry()
    spec_version = registry.register(
        keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = registry.register(
        keys["policy_bundle"], control["policy_bundle"]
    )
    database_path = tmp_path / "acme-bank.sqlite3"
    handle = boot(
        backend="sqlite",
        connection={"database_path": database_path},
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
    )
    try:
        for envelope in _envelopes(ontology, events):
            handle.worker.ingest(envelope)
        fabric = _Fabric(
            handle=handle,
            registry=registry,
            policy_version=policy_version,
            ontology=ontology,
            control=control,
        )
        # Test-local annotation: the no-op telemetry test opens a second,
        # fresh read-only store over the same database.
        fabric.database_path = database_path  # type: ignore[attr-defined]
        yield fabric
    finally:
        handle.close()


class _RecordingReader:
    """Delegates to the real reader, recording each ``GraphQuery`` at the seam."""

    def __init__(self, inner: GraphReader) -> None:
        self._inner = inner
        self.queries: list[GraphQuery] = []

    def query(self, q: GraphQuery) -> GraphView:
        self.queries.append(q)
        return self._inner.query(q)

    def as_of(self, *, tenant_id: str, at: Any) -> GraphView:
        return self._inner.as_of(tenant_id=tenant_id, at=at)

    @property
    def attestation(self) -> Any:
        return self._inner.attestation

    def entity_history(self, *, tenant_id: str, entity_uri: str) -> Any:
        return self._inner.entity_history(
            tenant_id=tenant_id, entity_uri=entity_uri
        )

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> Any:
        return self._inner.relationship_history(
            tenant_id=tenant_id, relationship_key=relationship_key
        )


def _perspective(fabric: _Fabric) -> Perspective:
    declared = fabric.control["perspective"]
    return Perspective(
        principal_id=declared["principal_id"], role=declared["role"]
    )


def _plan(
    fabric: _Fabric, required: tuple[str, ...]
) -> CreditExposureSummaryPlan:
    return CreditExposureSummaryPlan(
        plan_id=fabric.control["product_class"]["plan_id"], required=required
    )


def _preseg_execution(
    fabric: _Fabric,
    registry: OperatorRegistry,
    plan: CreditExposureSummaryPlan,
) -> ExecutionResult:
    """The pre-segmentation path, computed in-test: everything-read + in-process.

    The ``as_of`` everything-read (the D-07 degenerate query through the
    production fallback — no dead engine code kept) followed by every plan
    operator in-process, threading the provenance chain exactly as the
    pre-phase engine loop did. Packaged as an :class:`ExecutionResult` so the
    same product-candidate construction runs on both legs.
    """
    view = fabric.handle.reader.as_of(
        tenant_id=fabric.tenant_id, at=fabric.boundary
    )
    operator_plan = build_operator_plan(
        registry=registry, required_operators=plan.required_operators()
    )
    cache = IntermediateCache()
    outputs = {}
    steps = []
    chain = ()
    for operator in operator_plan.operators:
        output = cache.run(
            operator,
            view=view,
            tenant_id=fabric.tenant_id,
            temporal_boundary=fabric.boundary,
            upstream=chain,
        )
        view = output.view
        outputs[operator.key] = output
        chain = (output.provenance,)
        steps.append(
            ExecutionStep(
                operator_key=operator.key,
                category=operator.category,
                parameter_hash=output.provenance.parameter_hash,
            )
        )
    projection = plan.invoke(
        view=view,
        operator_outputs=outputs,
        perspective=_perspective(fabric),
        temporal_boundary=fabric.boundary,
    )
    return ExecutionResult(
        plan_id=plan.plan_id,
        operators_invoked=frozenset(outputs),
        steps=tuple(steps),
        provenance=chain[0] if chain else None,
        projection=projection,
        view=view,
    )


def _post_similarity_survivors(
    fabric: _Fabric, registry: OperatorRegistry
) -> frozenset[str]:
    """The survivor set, derived independently of the engine under test."""
    view = fabric.handle.reader.as_of(
        tenant_id=fabric.tenant_id, at=fabric.boundary
    )
    cache = IntermediateCache()
    chain = ()
    operator_plan = build_operator_plan(
        registry=registry,
        required_operators=(PolicyFilter.key, SimilaritySelect.key),
    )
    for operator in operator_plan.operators:
        output = cache.run(
            operator,
            view=view,
            tenant_id=fabric.tenant_id,
            temporal_boundary=fabric.boundary,
            upstream=chain,
        )
        view = output.view
        chain = (output.provenance,)
    return frozenset(record.claim.entity_uri for record in view.entities)


# --- structure is plan-static ------------------------------------------------


def test_the_similarity_bearing_split_is_the_three_segment_alternation() -> None:
    """`GQ-14`: the four-operator plan splits at Similarity, exactly.

    Stated explicitly against ``CATEGORY_ORDER`` = (policy, similarity,
    temporal, traversal): the split is ``[pushable: policy]``,
    ``[in-process: similarity]``, ``[pushable: temporal, traversal]`` — and
    it is identical across calls, because the structure is a function of the
    plan and nothing else.
    """
    assert CATEGORY_ORDER == ("policy", "similarity", "temporal", "traversal")
    registry = shipped_operators()
    operator_plan = build_operator_plan(
        registry=registry, required_operators=FOUR_OPERATORS
    )
    segmented = segment_plan(operator_plan.operators)
    assert segmented == segment_plan(operator_plan.operators)

    assert [type(segment) for segment in segmented.segments] == [
        PushableSegment,
        InProcessSegment,
        PushableSegment,
    ]
    categories = [
        tuple(
            registry.registration(key).category
            for key in segment.operator_keys
        )
        for segment in segmented.segments
    ]
    assert categories == [("policy",), ("similarity",), ("temporal", "traversal")]


def test_the_no_similarity_plan_is_one_pushable_segment() -> None:
    """A fully-pushable plan is one segment — one round trip, no survivors."""
    registry = shipped_operators()
    operator_plan = build_operator_plan(
        registry=registry, required_operators=NO_SIMILARITY
    )
    segmented = segment_plan(operator_plan.operators)
    (segment,) = segmented.segments
    assert isinstance(segment, PushableSegment)
    assert tuple(
        registry.registration(key).category for key in segment.operator_keys
    ) == ("policy", "temporal", "traversal")
    assert len(segment.fragments) == 3


def test_an_all_none_intent_plan_compiles_to_the_degenerate_query() -> None:
    """`GQ-05`: nothing pushable compiles to exactly the everything-question."""
    registry = shipped_operators()
    operator_plan = build_operator_plan(
        registry=registry, required_operators=(SimilaritySelect.key,)
    )
    segmented = segment_plan(operator_plan.operators)
    first, second = segmented.segments
    assert isinstance(first, PushableSegment)
    assert first.operator_keys == ()
    assert first.fragments == ()
    assert isinstance(second, InProcessSegment)
    assert second.operator_keys == (SimilaritySelect.key,)

    compiled = compile_segment_query(
        first,
        tenant_id=TENANT,
        as_of=BOUNDARY,
        seeds=None,
        allowed_entities=None,
    )
    assert compiled == GraphQuery(tenant_id=TENANT, as_of=BOUNDARY)
    assert content_hash(compiled) == content_hash(
        GraphQuery(tenant_id=TENANT, as_of=BOUNDARY)
    )


# --- allowed_entities threading, observed at the seam ------------------------


def test_the_second_query_carries_the_survivors_as_allowed_entities(
    fabric: _Fabric,
) -> None:
    """The uniform rule at the seam (`GQ-15`, `GQ-17`; T-15.2-26).

    The Similarity-bearing plan issues two queries; the second carries
    ``allowed_entities`` equal to the post-Similarity survivor URIs —
    derived in-test, independently of the engine — and authors no explicit
    seeds: walk starting points are computed *within* the set by the
    answerer (``seed_entity_classes`` select within ``allowed_entities``),
    which the answered view's walk-start data confirms.
    """
    registry = _operators(fabric)
    recording = _RecordingReader(fabric.handle.reader)
    engine = ProjectionEngine(reader=recording, registry=registry)
    execution = engine.execute(
        plan=_plan(fabric, FOUR_OPERATORS),
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )

    assert len(recording.queries) == 2
    first, second = recording.queries
    assert first.allowed_entities is None
    assert first.permitted_policy_bundle_versions is not None
    assert first.traverse is None

    survivors = _post_similarity_survivors(fabric, registry)
    assert survivors, "the fixture must leave a non-empty survivor set"
    assert second.allowed_entities == survivors
    assert second.seeds is None
    assert second.require_valid_at_boundary is not None
    assert second.traverse is not None

    # Walk-start data lies within the set: every seed-class entity of the
    # final view — the starts the pushed walk actually used — is a survivor.
    seed_classes = second.traverse.seed_entity_classes
    walk_starts = {
        record.claim.entity_uri
        for record in execution.view.entities
        if record.claim.entity_class in seed_classes
    }
    assert walk_starts <= survivors

    # The executed sequence on the result is what ran, in order — the
    # execution-path surface plan 15.2-08 threads into the replay record.
    assert execution.executed_queries == tuple(recording.queries)


# --- per-plan equivalence, Gate 2 pinned -------------------------------------


@pytest.mark.parametrize(
    "required", [NO_SIMILARITY, FOUR_OPERATORS], ids=["no-similarity", "similarity"]
)
def test_segmented_execution_is_byte_identical_to_the_preseg_path(
    fabric: _Fabric, required: tuple[str, ...]
) -> None:
    """The end-to-end regression, both plan shapes, lineage level included.

    Versus the pre-segmentation path (everything-read + all operators
    in-process, computed in-test): (a) byte-identical ContextProduct, (b)
    identical ``operators_invoked``, (c) identical provenance chains
    including parameter hashes, (d) ``run_gates`` → ``ServableProduct`` —
    Gate 2 lineage strict equality holds against the re-applied path
    (T-15.2-24, T-15.2-04). Product bytes alone cannot prove the lineage
    story survived re-application; (b)–(d) are the review requirement
    carried from the void set.
    """
    registry = _operators(fabric)
    plan = _plan(fabric, required)
    engine = ProjectionEngine(reader=fabric.handle.reader, registry=registry)
    segmented_execution = engine.execute(
        plan=plan,
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )
    expected = _preseg_execution(fabric, registry, plan)

    # The split, visible per shape: one round trip without Similarity, two
    # with (`GQ-14`) — identical on every substrate by construction.
    assert len(segmented_execution.executed_queries) == (
        1 if required == NO_SIMILARITY else 2
    )

    # (a) byte-identical product.
    product_class = _product_class(fabric)
    assert canonical_bytes(
        _candidate(fabric, segmented_execution, product_class)
    ) == canonical_bytes(_candidate(fabric, expected, product_class))
    # ... and the composed view itself, the dimension-1 watermark source.
    assert canonical_bytes(segmented_execution.view) == canonical_bytes(
        expected.view
    )
    assert segmented_execution.state_watermark() == expected.state_watermark()

    # (b) identical operators_invoked.
    assert segmented_execution.operators_invoked == expected.operators_invoked

    # (c) identical provenance chains, parameter hashes included.
    assert segmented_execution.provenance == expected.provenance
    assert content_hash(segmented_execution.provenance) == content_hash(
        expected.provenance
    )
    assert segmented_execution.steps == expected.steps

    # (d) Gate 2 — lineage strict equality — passes on the segmented path.
    gated = run_gates(
        _candidate(fabric, segmented_execution, product_class),
        engine_resolved=segmented_execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct)


# --- cap behavior (`GQ-18`, D-10) --------------------------------------------


def test_the_cap_drops_the_round_trip_and_changes_nothing_semantic(
    fabric: _Fabric,
) -> None:
    """Cap firing is a performance decision, never a semantic one.

    With ``survivor_cap`` below the Similarity survivor count the same
    execution issues ONE query — the recording reader saw only the first —
    and the final product bytes are identical to the uncapped run. With the
    default ``survivor_cap=None``, two queries are issued. The cap value
    arrives at the constructor (Control Plane configuration, D-10); no
    number exists in SDK code (T-15.2-27).
    """
    registry = _operators(fabric)
    plan = _plan(fabric, FOUR_OPERATORS)
    survivors = _post_similarity_survivors(fabric, registry)

    uncapped_recording = _RecordingReader(fabric.handle.reader)
    uncapped = ProjectionEngine(
        reader=uncapped_recording, registry=registry
    ).execute(
        plan=plan,
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )
    assert len(uncapped_recording.queries) == 2

    capped_recording = _RecordingReader(fabric.handle.reader)
    capped_engine = ProjectionEngine(
        reader=capped_recording,
        registry=registry,
        survivor_cap=len(survivors) - 1,
    )
    capped = capped_engine.execute(
        plan=plan,
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )
    assert len(capped_recording.queries) == 1
    assert capped_recording.queries[0].allowed_entities is None
    assert capped.executed_queries == tuple(capped_recording.queries)

    product_class = _product_class(fabric)
    assert canonical_bytes(
        _candidate(fabric, capped, product_class)
    ) == canonical_bytes(_candidate(fabric, uncapped, product_class))
    assert canonical_bytes(capped.view) == canonical_bytes(uncapped.view)
    assert capped.provenance == uncapped.provenance
    assert capped.steps == uncapped.steps


# --- set-size telemetry (D-10's locked sub-clause) ---------------------------


def test_survivor_set_sizes_are_reported_per_execution(
    fabric: _Fabric,
) -> None:
    """One entry per boundary; independent of push-vs-cap; replace, not append.

    After the Similarity-bearing plan, ``last_survivor_set_sizes`` is a
    one-element tuple equal to the post-Similarity survivor count — in BOTH
    the uncapped (two-query) and capped (one-query) runs, proving the report
    is independent of the push-vs-cap outcome. After the no-Similarity plan
    it is empty (no in-process → pushable boundary exists), and a second
    ``execute()`` on the same engine REPLACES the prior value.
    """
    registry = _operators(fabric)
    survivor_count = len(_post_similarity_survivors(fabric, registry))

    engine = ProjectionEngine(reader=fabric.handle.reader, registry=registry)
    assert engine.last_survivor_set_sizes == ()

    engine.execute(
        plan=_plan(fabric, FOUR_OPERATORS),
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )
    assert engine.last_survivor_set_sizes == (survivor_count,)

    capped_engine = ProjectionEngine(
        reader=fabric.handle.reader,
        registry=registry,
        survivor_cap=survivor_count - 1,
    )
    capped_engine.execute(
        plan=_plan(fabric, FOUR_OPERATORS),
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )
    assert capped_engine.last_survivor_set_sizes == (survivor_count,)

    # Replace, never append: the no-Similarity plan has no boundary.
    engine.execute(
        plan=_plan(fabric, NO_SIMILARITY),
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )
    assert engine.last_survivor_set_sizes == ()


# --- no-op telemetry ---------------------------------------------------------


def test_the_degenerate_round_trip_counts_exactly_once(fabric: _Fabric) -> None:
    """An all-``None``-intent plan is one ``reader.query`` call, counted once.

    On a fresh reader — a second read-only store over the same database —
    ``translated_answers == 1`` and ``fallback_answers == 0`` after the
    execution: since plan 15.2-09 the sqlite backend answers the degenerate
    everything-question natively, so the one round trip lands on the
    translated counter, exactly once — neither double- nor under-counted.
    """
    registry = _operators(fabric)
    database_path: Path = fabric.database_path  # type: ignore[attr-defined]
    with SqliteGraphStore(database_path=database_path) as store:
        fresh = store.reader
        assert fresh.translated_answers == 0
        assert fresh.fallback_answers == 0

        engine = ProjectionEngine(reader=fresh, registry=registry)
        execution = engine.execute(
            plan=_plan(fabric, (SimilaritySelect.key,)),
            perspective=_perspective(fabric),
            tenant_id=fabric.tenant_id,
            temporal_boundary=fabric.boundary,
        )

        assert fresh.translated_answers == 1
        assert fresh.fallback_answers == 0
        assert len(execution.executed_queries) == 1
        assert execution.executed_queries[0] == GraphQuery(
            tenant_id=fabric.tenant_id, as_of=fabric.boundary
        )
        assert engine.last_survivor_set_sizes == ()
