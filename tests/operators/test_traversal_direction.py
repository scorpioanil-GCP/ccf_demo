"""The directed descendant walk — criterion 9's mechanism half, ledger row `24.5-L-06`.

`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201 (INV-CH7-24). Before plan
`24.5-05`, the L4 walk was an undirected NEIGHBORHOOD — a node one hop from a
reached node was reached whichever way the edge was stored. The sibling key
``traversal.typed-descendants`` (``TraversalDescendants``) walks a stored
edge only from ``subject_uri`` to ``object_uri``; ``TraversalSpec.direction``
carries the choice to the oracle, and every backend hands a directed walk to
the oracle until plan `24.5-18` proves one can honor it (D-04). This module
proves each sentence in process, network-free, on ONE view whose one edge
stored INTO the seed is the whole difference:

* the forward walk does not cross that edge and reaches strictly less; the
  neighborhood walk on the same view still reaches it (additive, D-10);
* ``src/ccf/graph/fallback.py::_walk`` — the differential oracle — agrees
  with BOTH operators at every depth, so the two walks and the oracle are
  three spellings of one `GQ-10`;
* the direction is fixed by the operator, never by a parameter;
* all five ``_translate_query`` hooks DECLINE a directed walk before touching
  any store — asserted with no store and no server, in the
  ``tests/graph/test_neo4j_backend.py::test_over_ceiling_depth_declines_to_the_fallback``
  voice — and the same reader on the same query with the default direction
  goes on toward its substrate, so the decline is attributable to the field.

**The sabotage control.** ``src/ccf/operators/categories.py`` is copied to a
scratch module with the ``forward`` branch of the shared ``_bounded_walk``
disabled and imported under a scratch name; the strictly-less assertion must
FAIL on the copy, naming the direction. The real tree is never edited;
``tests/operators/test_traversal_admission.py::test_no_control_edits_the_real_source_tree``
already asserts that file's cleanliness through ``git`` on every run.

Fixture discipline inherited from ``tests/properties/strategies.py``: the
classes and the edge type are read from the ontology fixture and named here
by their ROLE in the view — no entity class and no relationship type is
written in this file (CLAUDE.md §6.4).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import ModuleType

import pytest

from ccf.graph.backends.fluree import FlureeGraphReader
from ccf.graph.backends.mongo import MongoGraphReader
from ccf.graph.backends.neo4j import Neo4jGraphReader
from ccf.graph.backends.postgres import PostgresGraphReader
from ccf.graph.backends.sqlite import SqliteGraphReader
from ccf.graph.fallback import _walk
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphView,
    RelationshipRecord,
    TraversalSpec,
)
from ccf.graph.reader import BaseGraphReader
from ccf.operators.base import Operator, OperatorCategory
from ccf.operators.categories import TraversalDescendants, TraversalNeighborhood
from ccf.operators.params import (
    TraversalDescendantsParameters,
    TraversalNeighborhoodParameters,
)

from tests.properties.strategies import (
    BOUNDARY,
    ENTITY_CLASSES,
    ENTITY_POOL,
    GENERATION,
    INSTANTS,
    RELATIONSHIP_RULES,
    TENANT,
    _entity_record,
    _relationship_record,
    _view,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CATEGORIES_SOURCE = REPO_ROOT / "src" / "ccf" / "operators" / "categories.py"

#: Three roles, in ontology vocabulary. The seed class starts the walk; the
#: child class is where a stored edge leads FROM the seed; the parent class is
#: where a stored edge leads INTO the seed — the node only an undirected hop
#: reaches.
SEED_CLASS, CHILD_CLASS, PARENT_CLASS = ENTITY_CLASSES[:3]
#: One typed edge from the ontology; the walk reads direction off the stored
#: subject/object, never off the type, so one type builds every shape here.
EDGE_TYPE: str = RELATIONSHIP_RULES[0][0]

#: The four nodes: P → S (stored INTO the seed), S → A, A → C.
S_URI = ENTITY_POOL[SEED_CLASS][0]
A_URI = ENTITY_POOL[CHILD_CLASS][0]
C_URI = ENTITY_POOL[CHILD_CLASS][1]
P_URI = ENTITY_POOL[PARENT_CLASS][0]

EARLY = INSTANTS[0]
BUNDLE: str = GENERATION["permitted_policy_bundle_version"]
CLASSIFICATION: str = GENERATION["classifications"][0]
SYSTEM: str = GENERATION["source_systems"][0]

#: The exact branch the sabotage disables: the shared walk adds the reverse
#: adjacency only when the walk is not forward. Asserted PRESENT in the real
#: source before the copy is mutated, so the control cannot pass vacuously.
FORWARD_BRANCH = "        if not forward:\n"


def _entity(uri: str, entity_class: str) -> EntityRecord:
    return _entity_record(
        entity_uri=uri,
        entity_class=entity_class,
        classification=CLASSIFICATION,
        policy_bundle_version=BUNDLE,
        observed_at=EARLY,
        valid_from=EARLY,
        valid_to=None,
        superseded_at=None,
        system_id=SYSTEM,
    )


def _edge(subject_uri: str, object_uri: str) -> RelationshipRecord:
    return _relationship_record(
        relationship_type=EDGE_TYPE,
        subject_uri=subject_uri,
        object_uri=object_uri,
        policy_bundle_version=BUNDLE,
        observed_at=EARLY,
        valid_from=EARLY,
        valid_to=None,
        superseded_at=None,
        system_id=SYSTEM,
    )


def oriented_view() -> GraphView:
    """P → S (into the seed), S → A, A → C — one edge stored against the walk."""
    entities = (
        _entity(S_URI, SEED_CLASS),
        _entity(A_URI, CHILD_CLASS),
        _entity(C_URI, CHILD_CLASS),
        _entity(P_URI, PARENT_CLASS),
    )
    relationships = (
        _edge(P_URI, S_URI),
        _edge(S_URI, A_URI),
        _edge(A_URI, C_URI),
    )
    return _view(entities, relationships)


VIEW = oriented_view()


def _neighborhood(depth: int) -> TraversalNeighborhood:
    return TraversalNeighborhood(
        parameters=TraversalNeighborhoodParameters(
            seed_entity_classes=frozenset({SEED_CLASS}),
            relationship_types=frozenset({EDGE_TYPE}),
            depth_limit=depth,
        )
    )


def _descendants(depth: int) -> TraversalDescendants:
    return TraversalDescendants(
        parameters=TraversalDescendantsParameters(
            seed_entity_classes=frozenset({SEED_CLASS}),
            relationship_types=frozenset({EDGE_TYPE}),
            depth_limit=depth,
        )
    )


def _reached(operator: Operator, view: GraphView = VIEW) -> frozenset[str]:
    output = operator.apply(
        view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    return frozenset(record.claim.entity_uri for record in output.view.entities)


# --- the walk ---------------------------------------------------------------


def test_the_forward_walk_does_not_cross_an_edge_stored_into_the_seed() -> None:
    """P → S is one undirected hop from S and zero forward hops.

    Depth 1: the neighborhood reaches P and A; the descendants walk reaches
    A only. Depth 2: the neighborhood reaches everything; the descendants
    walk reaches C through A and still not P. Strictly less at every depth
    that has the edge to cross — the reason the row exists (`24.4-D-36`).
    """
    assert _reached(_neighborhood(1)) == {S_URI, A_URI, P_URI}
    assert _reached(_descendants(1)) == {S_URI, A_URI}, (
        "the forward walk crossed an edge stored INTO the seed — direction"
        " is not being honored"
    )
    assert _reached(_neighborhood(2)) == {S_URI, A_URI, P_URI, C_URI}
    assert _reached(_descendants(2)) == {S_URI, A_URI, C_URI}
    # Depth 0 is the starts only, for both (`GQ-10`): the direction of an
    # edge nobody crosses is nothing.
    assert _reached(_neighborhood(0)) == _reached(_descendants(0)) == {S_URI}


def test_the_forward_walk_still_follows_a_chain_of_stored_edges() -> None:
    """Direction restricts the crossing, not the depth: S → A → C at depth 2."""
    assert C_URI not in _reached(_descendants(1))
    assert C_URI in _reached(_descendants(2))


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
@pytest.mark.parametrize(
    "build",
    [_neighborhood, _descendants],
    ids=["typed-neighborhood", "typed-descendants"],
)
def test_the_fallback_walk_agrees_with_the_operator(
    build: object, depth: int
) -> None:
    """`_walk` under the operator's own `read_intent()` answers what `apply()` does.

    Entities AND edges: `_walk` prunes to edges among reached nodes exactly
    as `_substitute` does (INV-CH7-40), so the two answers are compared whole.
    This is the equality the differential suite rests on — a pushed answer is
    held to `_walk`, and `_walk` is held here to the operator.
    """
    operator = build(depth)  # type: ignore[operator]
    fragment = operator.read_intent()
    assert fragment.traverse is not None
    entities, edges = _walk(
        VIEW.entities, VIEW.relationships, traverse=fragment.traverse, seeds=None
    )
    output = operator.apply(
        view=VIEW, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    assert entities == output.view.entities
    assert edges == output.view.relationships


# --- the direction is the operator's, never a parameter's --------------------


def test_read_intent_fixes_the_direction_by_operator() -> None:
    """The neighborhood emits `undirected`, the descendants walk `forward`,
    and neither parameter class carries a field that could say otherwise."""
    neighborhood = _neighborhood(1).read_intent().traverse
    descendants = _descendants(1).read_intent().traverse
    assert neighborhood is not None and descendants is not None
    assert neighborhood.direction == "undirected"
    assert descendants.direction == "forward"
    assert "direction" not in TraversalNeighborhoodParameters.model_fields
    assert "direction" not in TraversalDescendantsParameters.model_fields
    # The spec's default is the 1.0.x walk, and the vocabulary is closed.
    assert TraversalSpec.model_fields["direction"].default == "undirected"
    with pytest.raises(ValueError, match="direction"):
        TraversalSpec(
            seed_entity_classes=frozenset({SEED_CLASS}),
            relationship_types=frozenset({EDGE_TYPE}),
            depth_limit=1,
            direction="backward",  # type: ignore[arg-type]
        )


def test_the_sibling_is_a_second_shape_under_the_same_category() -> None:
    """D-IMPL-223: a sibling KEY, the category count untouched."""
    import typing

    assert TraversalDescendants.key == "traversal.typed-descendants"
    assert TraversalDescendants.key != TraversalNeighborhood.key
    assert TraversalDescendants.category == TraversalNeighborhood.category
    assert typing.get_args(OperatorCategory) == (
        "policy",
        "similarity",
        "temporal",
        "traversal",
    )


# --- every backend declines the directed walk to the oracle (D-04) -----------


READERS: tuple[type[BaseGraphReader], ...] = (
    SqliteGraphReader,
    PostgresGraphReader,
    Neo4jGraphReader,
    MongoGraphReader,
    FlureeGraphReader,
)


def _query(direction: str) -> GraphQuery:
    return GraphQuery(
        tenant_id=TENANT,
        as_of=BOUNDARY,
        traverse=TraversalSpec(
            seed_entity_classes=frozenset({SEED_CLASS}),
            relationship_types=frozenset({EDGE_TYPE}),
            depth_limit=1,
            direction=direction,  # type: ignore[arg-type]
        ),
    )


@pytest.mark.parametrize("reader_class", READERS, ids=lambda c: c.__name__)
def test_every_backend_declines_a_directed_walk_before_touching_its_store(
    reader_class: type[BaseGraphReader],
) -> None:
    """`_translate_query` returns `None` on `direction="forward"` (`GQ-32`, D-04).

    No store, no server: the reader is allocated without `__init__`, so any
    path that reached the substrate would raise `AttributeError` — and the
    control below shows that the SAME reader on the SAME query with the
    default direction does exactly that. The decline is therefore a pure
    function of the direction field, before any statement, session, pipeline
    or request is built. Plan `24.5-18` flips sqlite/postgres/neo4j to HONOR
    and re-points this test at the two that keep the decline.
    """
    reader = reader_class.__new__(reader_class)
    assert reader._translate_query(_query("forward")) is None, (
        f"{reader_class.__name__} translated a directed walk natively; the"
        " oracle must answer it until the backend is proven to honor"
        " direction (24.5-L-06)"
    )
    # Control: the undirected twin passes the guard and heads for the store
    # this reader does not have. If this ever returns None instead, the
    # decline above proves nothing about the field.
    with pytest.raises(AttributeError):
        reader._translate_query(_query("undirected"))


# --- the sabotage control: the copy without the forward branch fails ---------


def _import_scratch_copy(source: str, name: str, tmp_path: pathlib.Path) -> ModuleType:
    path = tmp_path / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def test_control_the_strictly_less_assertion_fails_on_a_copy_that_ignores_direction(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage in a scratch copy: `if not forward:` becomes `if True:`.

    The copy's descendants walk then builds the reverse adjacency too and
    reaches P — the same set as the neighborhood — and the strictly-less
    assertion fails naming the direction. The real module is untouched; the
    predicate is asserted present in the real source first.
    """
    real = CATEGORIES_SOURCE.read_text(encoding="utf-8")
    assert real.count(FORWARD_BRANCH) == 1, "the forward branch moved; re-anchor"
    sabotaged = real.replace(FORWARD_BRANCH, "        if True:\n", 1)
    module = _import_scratch_copy(sabotaged, "_ccf_categories_no_direction", tmp_path)
    copy = module.TraversalDescendants(
        parameters=TraversalDescendantsParameters(
            seed_entity_classes=frozenset({SEED_CLASS}),
            relationship_types=frozenset({EDGE_TYPE}),
            depth_limit=1,
        )
    )
    reached_by_copy = _reached(copy)
    with pytest.raises(AssertionError, match="direction"):
        assert reached_by_copy == {S_URI, A_URI}, (
            "the forward walk crossed an edge stored INTO the seed — direction"
            " is not being honored"
        )
    # And the copy reaches EXACTLY the undirected set — the sabotage removed
    # the direction and nothing else.
    assert reached_by_copy == _reached(_neighborhood(1))
    assert reached_by_copy - _reached(_descendants(1)) == {P_URI}
