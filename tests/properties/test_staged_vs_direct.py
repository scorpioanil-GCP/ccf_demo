"""Two-stage execution equals direct composition (FABR-03, FEASIBILITY §11 D-08).

FEASIBILITY.md §11 names two property classes under D-08. ``test_composition``
covers the first, ``(A∘B)(G) = A(B(G))``; this module covers the second: the
projection engine's *two-stage* execution — resolve and run the operator plan,
then invoke Π over the result (whitepaper §7.5, INV-CH7-42) — must produce the
same product payload as folding the same operators into one composite and
invoking Π on that.

Why the second class is not implied by the first. Composition preservation is a
statement about the operator algebra; this is a statement about the *engine* —
that its planning, its per-execution intermediate cache (D-IMPL-36), its
provenance threading, and its Π invocation add nothing and lose nothing relative
to the algebra underneath. An engine could compose its operators correctly and
still hand Π a different view than the composite produced.

The engine reads through a :class:`~ccf.graph.protocols.GraphReader`, so the
harness supplies one over a fixed value. It is a *reader*: there is no writer
here, no test-only write path, and nothing that could reach L3 (conftest.py's
standing rule; INV-CH7-10).
"""

from __future__ import annotations

from tests.classification_authority import stamp

import functools
from datetime import datetime

import pytest
from hypothesis import given

from ccf.contracts.canonical import canonical_bytes
from ccf.graph.fallback import answer
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphReader,
    GraphView,
    RelationshipRecord,
    SourceAttestation,
)
from ccf.operators.base import Operator
from ccf.operators.planner import CATEGORY_ORDER, build_operator_plan, compose
from ccf.projection.engine import ProjectionEngine

from .strategies import (
    AUTHORITY,
    BOUNDARY,
    TENANT,
    CuratedGraph,
    banking_graph_states,
    curated_edge_graphs,
    harness_perspective,
    shipped_operators,
    slice_projection_plan,
)

REGISTRY = shipped_operators()
CURATED = curated_edge_graphs()


def _legal_plans() -> tuple[tuple[str, ...], ...]:
    """One legal plan per traversal shape — the plans the engine may run.

    `GQ-06` refuses two fragments of one family in a segment, so "every
    shipped operator" stopped being a legal plan when ledger row
    ``24.5-L-06`` registered ``traversal.typed-descendants`` beside
    ``traversal.typed-neighborhood`` — both emit a traverse family. The
    staged-vs-direct law is therefore stated per plan: the single operator
    of each other category plus ONE traversal shape, and every shape takes
    its turn. Derived from the registry, so a further sibling joins here on
    its own and a plan that named none of them is unreachable.
    """
    by_category = {
        category: tuple(
            registration.key for registration in REGISTRY.by_category(category)
        )
        for category in CATEGORY_ORDER
    }
    others = tuple(
        key
        for category in CATEGORY_ORDER
        if category != "traversal"
        for key in by_category[category]
    )
    assert len(others) == len(CATEGORY_ORDER) - 1, by_category
    return tuple(others + (shape,) for shape in by_category["traversal"])


#: The plans, identified by the traversal shape each one runs.
LEGAL_PLANS = _legal_plans()
PLAN_IDS = [keys[-1] for keys in LEGAL_PLANS]


class FixedViewReader:
    """A ``GraphReader`` that answers every as-of read with one fixed view.

    The property is about the engine's execution over graph state, not about
    the store's ability to produce that state — which the conformance suite
    owns. Pinning the view keeps the two concerns from being tested at once,
    and keeps the property suite off any database (04-RESEARCH.md Pitfall 6).
    """

    def __init__(self, view: GraphView) -> None:
        self._view = view

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        return self._view

    def query(self, q: GraphQuery) -> GraphView:
        """Answer with the fallback semantics over the fixed view's records."""
        entities, relationships = answer(
            self._view.entities, self._view.relationships, query=q
        )
        return stamp(GraphView(
            tenant_id=q.tenant_id,
            as_of=q.as_of,
            entities=tuple(
                sorted(entities, key=lambda record: record.claim.entity_uri)
            ),
            relationships=tuple(
                sorted(relationships, key=lambda record: record.relationship_key)
            ),
        ), AUTHORITY)

    @property
    def attestation(self) -> SourceAttestation:
        return SourceAttestation(
            policy_binding="assembly-stamped",
            lineage="graph-supplied",
            peer=None,
        )

    def entity_history(
        self, *, tenant_id: str, entity_uri: str
    ) -> tuple[EntityRecord, ...]:
        return tuple(
            record
            for record in self._view.entities
            if record.claim.entity_uri == entity_uri
        )

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        return tuple(
            edge
            for edge in self._view.relationships
            if edge.relationship_key == relationship_key
        )


_CONFORMANCE: tuple[type[GraphReader], ...] = (FixedViewReader,)


def _assert_staged_equals_direct(view: GraphView, keys: tuple[str, ...]) -> None:
    """Run the engine and the hand-folded composite; require identical bytes."""
    plan = slice_projection_plan(keys)
    perspective = harness_perspective()

    staged = ProjectionEngine(
        reader=FixedViewReader(view), registry=REGISTRY
    ).execute(
        plan=plan,
        perspective=perspective,
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
    )

    ordered = build_operator_plan(
        registry=REGISTRY, required_operators=plan.required_operators()
    ).operators
    composite: Operator = functools.reduce(
        lambda accumulated, operator: compose(operator, accumulated),
        ordered[1:],
        ordered[0],
    )
    direct = composite.apply(
        view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    projected = plan.invoke(
        view=direct.view,
        operator_outputs={},
        perspective=perspective,
        temporal_boundary=BOUNDARY,
    )

    assert canonical_bytes(staged.view) == canonical_bytes(direct.view)
    assert canonical_bytes(staged.projection) == canonical_bytes(projected)
    assert staged.provenance == direct.provenance


@pytest.mark.parametrize("keys", LEGAL_PLANS, ids=PLAN_IDS)
@given(view=banking_graph_states())
def test_staged_execution_equals_direct_composition_on_generated_graphs(
    keys: tuple[str, ...], view: GraphView
) -> None:
    """The engine adds nothing and loses nothing relative to the algebra."""
    _assert_staged_equals_direct(view, keys)


@pytest.mark.parametrize("keys", LEGAL_PLANS, ids=PLAN_IDS)
@pytest.mark.parametrize("case", CURATED, ids=[case.name for case in CURATED])
def test_staged_execution_equals_direct_composition_on_curated_graphs(
    case: CuratedGraph, keys: tuple[str, ...]
) -> None:
    """Same equality on the curated edge cases (D-14's second input class)."""
    _assert_staged_equals_direct(case.view, keys)


@pytest.mark.parametrize("keys", LEGAL_PLANS, ids=PLAN_IDS)
@given(view=banking_graph_states())
def test_the_engine_records_what_it_ran_in_dependency_order(
    keys: tuple[str, ...], view: GraphView
) -> None:
    """Policy → Similarity → Temporal → Traversal, on every drawn state.

    The engine-resolved step sequence is what lands in replay dimension 5 and
    what the L6 lineage gate compares against the plan's declaration; an
    ordering that varied with the input would make both meaningless.
    """
    execution = ProjectionEngine(
        reader=FixedViewReader(view), registry=REGISTRY
    ).execute(
        plan=slice_projection_plan(keys),
        perspective=harness_perspective(),
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
    )
    assert [step.category for step in execution.steps] == [
        "policy",
        "similarity",
        "temporal",
        "traversal",
    ]
    assert execution.operators_invoked == frozenset(keys)


def test_every_traversal_shape_takes_its_turn() -> None:
    """The plan roster is derived, and both shapes are in it (`24.5-L-06`)."""
    shapes = {keys[-1] for keys in LEGAL_PLANS}
    assert shapes == {
        registration.key for registration in REGISTRY.by_category("traversal")
    }
    assert "traversal.typed-descendants" in shapes
    assert "traversal.typed-neighborhood" in shapes
