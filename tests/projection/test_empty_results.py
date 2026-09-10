"""``ExecutionResult.empty_results`` — the engine's own record of which operators returned nothing (``24.5-L-24``, ``24.6-L-06``).

The record is an observation only the thing that ran the plan can make: which
operator's output view carried zero entities AND zero relationships.
:meth:`ProjectionEngine.execute` computes it ALWAYS — one inspection of each
:class:`~ccf.operators.base.OperatorOutput` as it is produced — so the empty
set is the engine's positive *no operator returned empty*, never a sentinel
for absence.

**What reads it moved at ``24.6-05``** (``D-IMPL-242`` amendment 1,
``D-IMPL-253`` Q11/Q12). It used to feed a refusal — the returned half of the
empty-operator gate. It now feeds a FINDING on the served product,
:class:`~ccf.products.contract.ComputedEmptyFinding`, because an operator that
ran and returned nothing computed something. The engine's half of this row did
not change at all, which is the point of measuring it here: the record is the
same record, and the assertions below are the same assertions, with the one
consumer swapped.

What is proven, and where:

1. A one-operator plan whose operator returns an empty view → exactly that
   key. The operator is a ``PolicyFilter`` admitting a bundle version no
   claim in the booted banking fixture carries, so the pushed segment's
   answer is empty and the re-application over it is empty too.
2. The same operator admitting the fixture's real version → the empty set,
   with a non-empty view as the positive control.
3. A two-operator plan where only the SECOND — an in-process
   ``SimilaritySelect`` over an empty corpus — returns empty → exactly the
   second's key. The first (a pushed, admitting ``PolicyFilter``) is not
   named. The view is hand-built with the ``tests/properties`` record
   helpers and carries no relationships, because the similarity operator
   keeps ``view.relationships`` untouched by design and the record's
   definition is zero entities AND zero relationships.
4. The mechanism fact worth pinning rather than assuming: inside ONE pushed
   segment the answer is composed, so an empty answer is recorded against
   EVERY operator of that segment — the engine re-applies each over the
   answer (`GQ-19` at docs/GRAPH_QUERY_SEMANTICS.md:356) and each returns
   empty. The record names what each operator returned, not which fragment
   emptied the question.
5. A result built by hand without the field carries the empty set — the
   compatibility default (``D-10``).

Every domain value comes from ``tests/fixtures/banking/*.yaml`` through the
quickstart wiring, the reuse discipline ``tests/projection/test_attestation.py``
follows. The one value this module invents — a bundle version no claim
carries — is exactly the value that makes an operator return nothing.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.boot import boot
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphView,
    RelationshipRecord,
)
from ccf.operators.categories import (
    PolicyFilter,
    SimilaritySelect,
    TemporalAsOf,
)
from ccf.operators.params import (
    PolicyFilterParameters,
    SimilaritySelectParameters,
    TemporalAsOfParameters,
)
from ccf.operators.registry import OperatorRegistry
from ccf.products.contract import ComputedEmptyFinding
from ccf.projection.engine import ExecutionResult, ProjectionEngine
from ccf.projection.plan import Perspective
from ccf.similarity.protocol import TokenOverlapIndex

from tests.integration.test_proto_quickstart import (
    CreditExposureSummaryPlan,
    _envelopes,
    _Fabric,
    _load,
    _operators,
    _resolution_spec,
)
from tests.projection.test_segmentation import _perspective, _plan
from tests.properties import strategies

#: A bundle version no claim in the fixture carries. The one invented value.
NO_SUCH_VERSION = "policy-version-that-no-claim-carries"


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
    handle = boot(
        backend="sqlite",
        connection={"database_path": tmp_path / "acme-bank.sqlite3"},
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
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


def _policy_filter(fabric: _Fabric, *, permitted_version: str) -> PolicyFilter:
    """The fixture's policy operator, admitting exactly ``permitted_version``."""
    params = fabric.control["operator_parameters"]
    return PolicyFilter(
        parameters=PolicyFilterParameters(
            permitted_policy_bundle_versions=frozenset({permitted_version}),
            classification_attribute_by_class=dict(
                fabric.ontology["classification_attribute_by_class"]
            ),
            permitted_classifications=frozenset(
                params["policy"]["permitted_classifications"]
            ),
        )
    )


def _execute(
    fabric: _Fabric, registry: OperatorRegistry, required: tuple[str, ...]
) -> ExecutionResult:
    return ProjectionEngine(reader=fabric.handle.reader, registry=registry).execute(
        plan=_plan(fabric, required),
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )


# --- 1 and 2: one operator, empty and non-empty -----------------------------


def test_an_operator_that_returns_an_empty_view_is_recorded_by_key(
    fabric: _Fabric,
) -> None:
    """A policy filter admitting a version no claim carries returns nothing — and is named."""
    registry = OperatorRegistry()
    registry.register(_policy_filter(fabric, permitted_version=NO_SUCH_VERSION))

    execution = _execute(fabric, registry, (PolicyFilter.key,))

    assert execution.operators_invoked == frozenset({PolicyFilter.key})
    assert not execution.view.entities and not execution.view.relationships
    assert execution.empty_results == frozenset({PolicyFilter.key})


def test_an_admitting_operator_records_no_empty_result(fabric: _Fabric) -> None:
    """The positive control: the same operator admitting the real version returns entities and records nothing."""
    registry = OperatorRegistry()
    registry.register(_policy_filter(fabric, permitted_version=fabric.policy_version))

    execution = _execute(fabric, registry, (PolicyFilter.key,))

    assert execution.operators_invoked == frozenset({PolicyFilter.key})
    assert execution.view.entities, "the fixture's own version must admit something"
    assert execution.empty_results == frozenset()


def test_the_quickstart_plan_records_no_empty_result(fabric: _Fabric) -> None:
    """The four-operator quickstart plan, as shipped, returns empty nowhere."""
    registry = _operators(fabric)

    execution = _execute(fabric, registry, registry.keys())

    assert execution.empty_results == frozenset()
    assert len(execution.operators_invoked) == 4


# --- 3: only the second, in-process operator returns empty ------------------


class _ViewSource:
    """A ``GraphReader``-shaped source answering every read with one fixed view.

    The pushed policy segment's query is answered with the WHOLE view and the
    engine's re-application does the filtering, which is the fixed-point
    property `GQ-19` at docs/GRAPH_QUERY_SEMANTICS.md:356 relies on. No
    attestation, no pin — a pre-phase reader.
    """

    def __init__(self, view: GraphView) -> None:
        self._view = view

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        return self._view

    def query(self, q: GraphQuery) -> GraphView:
        return self._view

    def entity_history(
        self, *, tenant_id: str, entity_uri: str
    ) -> tuple[EntityRecord, ...]:
        return ()

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        return ()


def _entities_only_view(*, policy_bundle_version: str, classification: str) -> GraphView:
    """Two entities of the fixture's first two classes, no relationships."""
    instant = strategies.INSTANTS[0]
    records = tuple(
        strategies._entity_record(
            entity_uri=strategies.ENTITY_POOL[entity_class][0],
            entity_class=entity_class,
            classification=classification,
            policy_bundle_version=policy_bundle_version,
            observed_at=instant,
            valid_from=instant,
            valid_to=None,
            superseded_at=None,
            system_id=strategies.GENERATION["source_systems"][0],
        )
        for entity_class in strategies.ENTITY_CLASSES[:2]
    )
    return strategies._view(records, ())


def test_only_the_in_process_operator_that_returned_empty_is_recorded(
    fabric: _Fabric,
) -> None:
    """Pushed, admitting policy → non-empty; in-process similarity over an empty corpus → empty. Exactly the second's key."""
    classification = fabric.control["operator_parameters"]["policy"][
        "permitted_classifications"
    ][0]
    view = _entities_only_view(
        policy_bundle_version=fabric.policy_version, classification=classification
    )
    ranked = frozenset(record.claim.entity_class for record in view.entities)

    registry = OperatorRegistry()
    registry.register(_policy_filter(fabric, permitted_version=fabric.policy_version))
    registry.register(
        SimilaritySelect(
            parameters=SimilaritySelectParameters(
                query="nothing in this corpus",
                minimum_score_percent=1,
                ranked_entity_classes=ranked,
            ),
            index=TokenOverlapIndex(corpus={}, index_version="empty-corpus"),
        )
    )

    execution = ProjectionEngine(reader=_ViewSource(view), registry=registry).execute(
        plan=_plan(fabric, (PolicyFilter.key, SimilaritySelect.key)),
        perspective=_perspective(fabric),
        tenant_id=strategies.TENANT,
        temporal_boundary=strategies.BOUNDARY,
    )

    assert [step.operator_key for step in execution.steps] == [
        PolicyFilter.key,
        SimilaritySelect.key,
    ]
    assert execution.empty_results == frozenset({SimilaritySelect.key})
    assert PolicyFilter.key not in execution.empty_results


# --- 4: a pushed segment's empty answer is collective --------------------------


def test_a_pushed_segments_empty_answer_is_recorded_against_every_operator_in_it(
    fabric: _Fabric,
) -> None:
    """Policy (admitting nothing) and Temporal push as ONE segment; both are named, and the finding carries both."""
    params = fabric.control["operator_parameters"]
    registry = OperatorRegistry()
    registry.register(_policy_filter(fabric, permitted_version=NO_SUCH_VERSION))
    registry.register(
        TemporalAsOf(
            parameters=TemporalAsOfParameters(
                require_valid_at_boundary=params["temporal"]["require_valid_at_boundary"]
            )
        )
    )

    execution = _execute(fabric, registry, (PolicyFilter.key, TemporalAsOf.key))

    assert len(execution.executed_queries) == 1, "one pushed segment, one query"
    assert execution.empty_results == frozenset({PolicyFilter.key, TemporalAsOf.key})

    # The finding reads exactly this record, and now carries the whole search
    # rather than a first-offender key: which operators returned empty, and
    # every operator that was invoked (24.6-L-06).
    finding = ComputedEmptyFinding.of(execution, emptiness="attested")
    assert finding is not None
    assert finding.operators_returned_empty == execution.empty_results
    assert finding.operators_invoked == execution.operators_invoked
    assert finding.plan_id == execution.plan_id
    # And NOT the execution's store head (`D-IMPL-309`): the finding says what
    # was searched, the record says which physical state it was searched
    # against, and only the first decides what the finding is.
    assert "store_snapshot_pin" not in type(finding).model_fields
    assert execution.store_snapshot_pin is not None


# --- 5: the compatibility default --------------------------------------------


def test_a_result_built_without_the_field_carries_the_empty_set() -> None:
    """``D-10``: a hand-built result records *no operator returned empty*."""
    assert ExecutionResult.model_fields["empty_results"].default == frozenset()
    assert "empty_results" in ExecutionResult.model_fields
    assert list(ExecutionResult.model_fields)[-1] == "empty_results"


def test_an_execution_where_nothing_returned_empty_yields_no_finding(
    fabric: _Fabric,
) -> None:
    """The absence of the finding is how *no operator returned empty* is said.

    The mirror of the assertion above, on the consumer side: ``None`` rather
    than a finding naming nothing, so a served product that found rows renders
    exactly as it did before ``24.6-05`` (measured in
    ``tests/contracts/test_hash_transparency.py``).
    """
    registry = OperatorRegistry()
    registry.register(_policy_filter(fabric, permitted_version=fabric.policy_version))

    execution = _execute(fabric, registry, (PolicyFilter.key,))

    assert execution.view.entities, "the fixture's own version must admit something"
    assert execution.empty_results == frozenset()
    assert ComputedEmptyFinding.of(execution, emptiness="attested") is None
