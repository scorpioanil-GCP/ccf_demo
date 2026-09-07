"""The directed descendant walk — criterion 9's mechanism half, ledger row `24.5-L-06`.

`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201 (INV-CH7-24). Before plan
`24.5-05`, the L4 walk was an undirected NEIGHBORHOOD — a node one hop from a
reached node was reached whichever way the edge was stored. The sibling key
``traversal.typed-descendants`` (``TraversalDescendants``) walks a stored
edge only from ``subject_uri`` to ``object_uri``; ``TraversalSpec.direction``
carries the choice to the oracle, and every backend either honors it
natively or hands the directed walk to the oracle (D-04; the postures were
plan `24.5-05`'s decline-everywhere, then plan `24.5-18`'s HONOR on sqlite,
postgres and neo4j with the decline kept on mongo and fluree). This module
proves each sentence in process, network-free, on ONE view whose one edge
stored INTO the seed is the whole difference:

* the forward walk does not cross that edge and reaches strictly less; the
  neighborhood walk on the same view still reaches it (additive, D-10);
* ``src/ccf/graph/fallback.py::_walk`` — the differential oracle — agrees
  with BOTH operators at every depth, so the two walks and the oracle are
  three spellings of one `GQ-10`;
* the direction is fixed by the operator, never by a parameter;
* the two DECLINING ``_translate_query`` hooks return ``None`` on a directed
  walk before touching any store — asserted with no store and no server, in
  the
  ``tests/graph/test_neo4j_backend.py::test_over_ceiling_depth_declines_to_the_fallback``
  voice — and the same reader on the same query with the default direction
  goes on toward its substrate, so the decline is attributable to the field;
  the three HONORING hooks go on toward the store under either direction,
  and what they render is a Python choice between two constants — the
  direction is never text and never a parameter (threat T-24.5-12);
* the sibling is registered in ``tests/properties/strategies.py::shipped_operators``
  (5 keys, 25 ordered pairs), and ``docs/GRAPH_QUERY_SEMANTICS.md`` records
  the direction at 1.2.0.

**Criterion 9, measured** (the second half of this module): the committed
cp-04 fixture ``tests/examples/fixtures/cp_04_family_fluree.json`` parsed
into a view and walked from its anchor — the directed walk reaches
20 / 21 / 22 members at depths 1 / 2 / 3 where the undirected neighborhood
reaches 20 / 22 / 22, and the one divergent node is asserted by id.

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

import ast
import functools
import importlib.util
import json
import pathlib
import subprocess
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


def test_direction_and_admission_compose_on_the_descendant_walk() -> None:
    """Phase 24.5 close panel (2026-09-03): forward AND admitted, together, on one walk.

    The admission suite exercises only the undirected operator and this
    module exercised only unadmitted walks, so a future split of the shared
    ``_bounded_walk`` could break the composition while both stayed green.
    On the oriented view (P → S, S → A, A → C; A and C of the child class):

    * forward + child class admitted → {S, A, C}: P is upstream (direction),
      A and C are admitted (class);
    * forward + parent class admitted → {S}: A is unadmitted, so C behind it
      is unreachable — admission prunes the hop, and direction still keeps P out;
    * the two controls that isolate each lever: undirected + parent admitted
      reaches P; forward + no admission reaches A and C.
    The fallback's ``_walk`` agrees with each, entities and edges.
    """
    def descendants(admitted: frozenset[str] | None) -> TraversalDescendants:
        return TraversalDescendants(
            parameters=TraversalDescendantsParameters(
                seed_entity_classes=frozenset({SEED_CLASS}),
                relationship_types=frozenset({EDGE_TYPE}),
                depth_limit=2,
                admitted_entity_classes=admitted,
            )
        )

    def neighborhood(admitted: frozenset[str] | None) -> TraversalNeighborhood:
        return TraversalNeighborhood(
            parameters=TraversalNeighborhoodParameters(
                seed_entity_classes=frozenset({SEED_CLASS}),
                relationship_types=frozenset({EDGE_TYPE}),
                depth_limit=2,
                admitted_entity_classes=admitted,
            )
        )

    assert _reached(descendants(frozenset({CHILD_CLASS}))) == {S_URI, A_URI, C_URI}
    assert _reached(descendants(frozenset({PARENT_CLASS}))) == {S_URI}
    # Controls: each lever alone.
    assert P_URI in _reached(neighborhood(frozenset({PARENT_CLASS})))
    assert _reached(descendants(None)) == {S_URI, A_URI, C_URI}
    for operator in (
        descendants(frozenset({CHILD_CLASS})),
        descendants(frozenset({PARENT_CLASS})),
        neighborhood(frozenset({PARENT_CLASS})),
    ):
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


# --- every backend honors the directed walk or declines it to the oracle (D-04)


#: The five readers, partitioned by posture (plan 24.5-18). The two that
#: DECLINE a directed walk to the oracle (`GQ-32`): mongo, whose doubled
#: forward/reverse edge documents have not been measured under a
#: restricted ``$graphLookup`` (24.5-RESEARCH.md assumption A1), and fluree,
#: whose interposed ``CCF_LINK`` carries no edge direction (Pitfall 5). The
#: three that HONOR it natively: the SQL dialects choose the crossable set
#: or the recursive join between two constant renderings, and neo4j puts
#: the arrow on its reach pattern — so their translation goes on toward the
#: store under either direction.
DECLINING: tuple[type[BaseGraphReader], ...] = (
    MongoGraphReader,
    FlureeGraphReader,
)
HONORING: tuple[type[BaseGraphReader], ...] = (
    SqliteGraphReader,
    PostgresGraphReader,
    Neo4jGraphReader,
)
READERS: tuple[type[BaseGraphReader], ...] = HONORING + DECLINING


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


def test_the_posture_roster_partitions_the_five_readers() -> None:
    """Set equality, never a count: every reader has exactly one posture."""
    assert set(DECLINING).isdisjoint(HONORING)
    assert set(READERS) == {
        SqliteGraphReader,
        PostgresGraphReader,
        Neo4jGraphReader,
        MongoGraphReader,
        FlureeGraphReader,
    }


@pytest.mark.parametrize("reader_class", DECLINING, ids=lambda c: c.__name__)
def test_every_declining_backend_declines_a_directed_walk_before_touching_its_store(
    reader_class: type[BaseGraphReader],
) -> None:
    """`_translate_query` returns `None` on `direction="forward"` (`GQ-32`, D-04).

    No store, no server: the reader is allocated without `__init__`, so any
    path that reached the substrate would raise `AttributeError` — and the
    control below shows that the SAME reader on the SAME query with the
    default direction does exactly that. The decline is therefore a pure
    function of the direction field, before any pipeline or request is
    built. Plan `24.5-05` asserted this of all five readers; plan `24.5-18`
    flipped sqlite/postgres/neo4j to HONOR (the test below) and re-pointed
    this one at the two that keep the decline.
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


@pytest.mark.parametrize("reader_class", HONORING, ids=lambda c: c.__name__)
def test_every_honoring_backend_translates_a_directed_walk_toward_its_store(
    reader_class: type[BaseGraphReader],
) -> None:
    """The guard is gone: a directed walk heads for the store like the undirected one.

    Same allocation trick, inverted: under BOTH directions the reader goes
    on toward the substrate it does not have and raises `AttributeError` —
    never `None`. What it renders on the way is asserted by the statement
    tests below; that the rendering answers what the oracle answers is the
    differential suite's job, on every leg
    (``tests/conformance/test_substrate_differential.py::test_every_backend_answers_byte_identical_to_the_fallback_under_direction``).
    """
    reader = reader_class.__new__(reader_class)
    for direction in ("forward", "undirected"):
        with pytest.raises(AttributeError):
            reader._translate_query(_query(direction))


# --- the direction is a branch between constants, never text (T-24.5-12) ----


def test_sqlite_renders_the_crossable_set_once_per_direction() -> None:
    """Forward: the edges as stored; undirected: both renderings — same params."""
    from ccf.graph.backends.sqlite import _translated_statements

    forward = _translated_statements(_query("forward"))
    undirected = _translated_statements(_query("undirected"))
    assert forward is not None and undirected is not None
    reversed_rendering = "SELECT c.object_uri, c.subject_uri FROM edges c"
    for sql in forward[:2]:
        assert "hops(subject_uri, object_uri)" in sql
        assert reversed_rendering not in sql, "the forward walk rendered the reverse edge"
        assert "forward" not in sql and "direction" not in sql
    for sql in undirected[:2]:
        assert reversed_rendering in sql
        assert "undirected" not in sql and "direction" not in sql
    # The direction is not a bound parameter either: it chose text.
    assert list(forward[2]) == list(undirected[2])
    assert forward[0] != undirected[0]


def test_postgres_renders_the_recursive_join_once_per_direction() -> None:
    """Forward: joined on the stored subject only; undirected: either endpoint."""
    from ccf.graph.backends.postgres import _translated_statements

    forward = _translated_statements(_query("forward"))
    undirected = _translated_statements(_query("undirected"))
    either_endpoint = "ON (c.subject_uri = w.uri OR c.object_uri = w.uri)"
    for sql in forward[:2]:
        assert "ON c.subject_uri = w.uri\n" in sql
        assert either_endpoint not in sql, "the forward walk joined either endpoint"
        assert "forward" not in sql and "direction" not in sql
    for sql in undirected[:2]:
        assert either_endpoint in sql
    assert list(forward[2]) == list(undirected[2])
    assert forward[0] != undirected[0]


def test_neo4j_puts_the_arrow_on_the_reach_pattern() -> None:
    """The ONE formatting site formats the depth; the tail is a chosen constant."""
    from ccf.graph.backends.neo4j import _reach_pattern

    assert _reach_pattern(2, forward=True) == "-[:CCF_EDGE*1..2]->"
    assert _reach_pattern(2, forward=False) == "-[:CCF_EDGE*1..2]-"
    assert _reach_pattern(2) == _reach_pattern(2, forward=False)


# --- the sibling is in the n² composition suite ------------------------------


def test_the_sibling_is_registered_beside_the_neighborhood() -> None:
    """`shipped_operators` carries both shapes: 5 keys, 25 ordered pairs.

    ``tests/properties/test_composition.py::test_the_parametrization_covers_every_ordered_pair``
    asserts ``len(OPERATOR_KEYS) ** 2`` over the same registry, so the pair
    law needs no edit to cover the sibling; this test pins the roster the
    law is enumerated from.
    """
    import itertools

    from tests.properties.strategies import shipped_operators

    registry = shipped_operators()
    assert "traversal.typed-descendants" in registry.keys()
    assert "traversal.typed-neighborhood" in registry.keys()
    assert len(registry.keys()) == 5
    assert len(tuple(itertools.product(registry.keys(), registry.keys()))) == 25
    assert registry.registration("traversal.typed-descendants").category == (
        registry.registration("traversal.typed-neighborhood").category
    )


# --- one walk, structurally: both operators call it --------------------------

#: The exact call the sabotage below re-points at a private copy. The shared
#: walk is invoked once per ``apply`` — twice in the whole module — and the
#: literal is asserted PRESENT at that count in the real source before any
#: copy is mutated, so the control cannot pass vacuously against a file that
#: never carried it. Same discipline as ``FORWARD_BRANCH`` above.
WALK_CALL = "        entities, traversable = _bounded_walk(\n"


def _apply_callees(source: str) -> dict[str, set[str]]:
    """Per traversal class, the plain-name callees of its ``apply`` body.

    ``ast.Name`` in ``func`` position only: an attribute call on ``self`` or
    on an imported module is deliberately not collected, because the property
    under test is that the ONE module-level function is what both bodies
    reach for.
    """
    wanted = {"TraversalNeighborhood", "TraversalDescendants"}
    callees: dict[str, set[str]] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef) or node.name not in wanted:
            continue
        for member in node.body:
            if not isinstance(member, ast.FunctionDef) or member.name != "apply":
                continue
            callees[node.name] = {
                inner.func.id
                for inner in ast.walk(member)
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
            }
    return callees


def _bounded_walk_definitions(source: str) -> int:
    """How many module-level ``def _bounded_walk`` the source declares."""
    return sum(
        1
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "_bounded_walk"
    )


def _assert_one_walk_pin(source: str) -> None:
    """The pin's assertion body, factored so its control can run it on a copy."""
    assert _bounded_walk_definitions(source) == 1, (
        "the shared bounded walk is not defined exactly once at module level"
    )
    callees = _apply_callees(source)
    assert set(callees) == {"TraversalNeighborhood", "TraversalDescendants"}
    for class_name, called in sorted(callees.items()):
        assert "_bounded_walk" in called, (
            f"{class_name}.apply does not call the shared _bounded_walk;"
            f" it calls {sorted(called)} — the two traversal shapes have drifted"
        )


def test_both_traversal_operators_call_the_one_bounded_walk() -> None:
    """D-08 (a): one walk, defined once, called by both ``apply`` bodies.

    ``src/ccf/operators/categories.py`` says so in prose at its head — the two
    walks *"differ in exactly that line and nothing else"* — and that sentence
    is what makes the conforming change of `D-IMPL-268` a single edit rather
    than two edits that can disagree. Ledger row ``24.5-L-06`` created the
    sibling; ``24.5-L-06``'s companion pin
    ``tests/operators/test_traversal_direction.py::test_the_sibling_is_registered_beside_the_neighborhood``
    pins the roster, and this one pins the shared mechanism underneath it.

    Structural, not textual: the assertion is over the parsed ``apply``
    bodies, so a reformatting of the call site does not red it and a private
    copy of the walk does — which is exactly what the control below shows.
    """
    real = CATEGORIES_SOURCE.read_text(encoding="utf-8")
    assert real.count(WALK_CALL) == 2, (
        "the shared-walk call site moved; re-anchor WALK_CALL against"
        " src/ccf/operators/categories.py"
    )
    _assert_one_walk_pin(real)


def test_control_the_one_walk_pin_fails_on_a_copy_with_a_private_walk(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage in a scratch copy: the descendants walk gets its own private walk.

    The LAST of the two call sites is re-pointed at ``_private_bounded_walk``
    and an alias for it is appended, so the copy is a module in which the two
    operators no longer share one walk — and could therefore drift — while
    still answering exactly what it answered before. The pin above fails on
    the copy naming ``TraversalDescendants``; the copy still walks. The
    sabotage removed the pin's premise and nothing else, which is what makes
    the control discriminating rather than merely red.

    The alias name deliberately ends in ``_bounded_walk(`` at its call site,
    so this control's own literal is not a second hit for the tree-wide
    bare-``_walk`` search the phase asserts elsewhere.
    """
    real = CATEGORIES_SOURCE.read_text(encoding="utf-8")
    assert real.count(WALK_CALL) == 2, "the shared-walk call site moved; re-anchor"
    head, _match, tail = real.rpartition(WALK_CALL)
    sabotaged = (
        head
        + "        entities, traversable = _private_bounded_walk(\n"
        + tail
        + "\n_private_bounded_walk = _bounded_walk\n"
    )
    assert sabotaged.count(WALK_CALL) == 1

    with pytest.raises(AssertionError, match="TraversalDescendants"):
        _assert_one_walk_pin(sabotaged)

    module = _import_scratch_copy(sabotaged, "_ccf_categories_private_walk", tmp_path)
    copy = module.TraversalDescendants(
        parameters=TraversalDescendantsParameters(
            seed_entity_classes=frozenset({SEED_CLASS}),
            relationship_types=frozenset({EDGE_TYPE}),
            depth_limit=1,
        )
    )
    assert _reached(copy) == _reached(_descendants(1))
    deeper = module.TraversalDescendants(
        parameters=TraversalDescendantsParameters(
            seed_entity_classes=frozenset({SEED_CLASS}),
            relationship_types=frozenset({EDGE_TYPE}),
            depth_limit=2,
        )
    )
    assert _reached(deeper) == _reached(_descendants(2))


# --- the vocabulary records the direction at 1.2.0 ---------------------------


def test_the_semantics_document_records_the_direction_at_1_2_0() -> None:
    """`GQ-10` names both directions and `GQ-35` carries the 1.2.0 entry."""
    document = (REPO_ROOT / "docs" / "GRAPH_QUERY_SEMANTICS.md").read_text(
        encoding="utf-8"
    )
    assert "**Semantics version: 1.2.0**" in document
    clause = document.split("### `GQ-10`")[1].split("### `GQ-11`")[0]
    assert 'direction="undirected"' in clause and 'direction="forward"' in clause
    amendments = document.split("### `GQ-35`")[1]
    entry = amendments.split("- **1.2.0**")[1].split("- **1.1.0**")[0]
    assert "`24.5-L-06`" in entry
    assert "20 / 21 / 22" in entry and "20 / 22 / 22" in entry


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


# --- criterion 9: the committed cp-04 fixture, MEASURED ----------------------
#
# The fixture is parsed here and walked; nothing is read from
# `examples/cp-04-corporate-family-tree/artifacts/expected.yaml::census`
# (that block is the product's own census and would be source substitution —
# threat T-24.5-47). If the walk and the locked criterion ever disagree, this
# module goes RED and the criterion is not retuned here.

FIXTURE = REPO_ROOT / "tests" / "examples" / "fixtures" / "cp_04_family_fluree.json"

#: THE ORIENTATION WALKED. The six family predicates of the fixture do not
#: all run parent to child: ``owns`` and ``controls`` read subject→object,
#: while the two consolidation predicates and the two ultimate-parent
#: predicates read object→subject. That is the cp-04 deployment's own
#: normalization (``examples/cp-04-corporate-family-tree/deployment.py``,
#: READ and restated — never imported, the examples being closed), so the
#: view below stores ONE ``parent -> child`` edge per distinct pair with the
#: parent as ``subject_uri`` and the child as ``object_uri``; "forward" is
#: therefore parent to child, and "descendant" means what the tree means.
PARENT_TO_CHILD: tuple[str, ...] = ("owns", "controls")
CHILD_TO_PARENT: tuple[str, ...] = (
    "isDirectlyConsolidatedBy",
    "isUltimatelyConsolidatedBy",
    "hasGlobalUltimateParent",
    "hasDomesticUltimateParent",
)
#: The anchor the criterion names, by fixture ``@id``; the one node the
#: undirected walk reaches at depth 2 and the directed walk only at depth 3
#: (a cycle's closing edge crossed against its orientation — 24.4-D-36).
ANCHOR = "http://example.org/fibo/SuperMicroComputerInc"
DIVERGENT_AT_DEPTH_2 = "http://example.org/fibo/CycThornburyCapitalLtd"



def _criterion_9() -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """The locked figures (ROADMAP criterion 9): directed, then undirected.

    Counted INCLUDING the anchor: `GQ-10` includes the walk starts in the
    answer, and the census counts the subtree — anchor plus descendants —
    the same way. Without the anchor the two triples read 19 / 20 / 21 and
    19 / 21 / 21. A function rather than a module-level table because the
    numeric-table lint (CINV-01b) reads a module-level tuple of numbers as a
    Control Plane value; these are measured figures a test asserts, and the
    assertion is the only reader.
    """
    return (20, 21, 22), (20, 22, 22)


DIRECTED_BY_DEPTH, UNDIRECTED_BY_DEPTH = _criterion_9()


def _normalized_family_edges(document: dict[str, object]) -> frozenset[tuple[str, str]]:
    """The distinct parent→child pairs of the fixture under the orientation above."""
    pairs: set[tuple[str, str]] = set()
    nodes = document["insert"]
    assert isinstance(nodes, list)
    for node in nodes:
        assert isinstance(node, dict)
        subject = node["@id"]
        for predicate_iri, objects in node.items():
            name = predicate_iri.rsplit("/", 1)[-1]
            if name in PARENT_TO_CHILD:
                pairs.update((subject, target["@id"]) for target in objects)
            elif name in CHILD_TO_PARENT:
                pairs.update((target["@id"], subject) for target in objects)
    return frozenset(pairs)


@functools.cache
def family_view() -> GraphView:
    """The fixture as a view: one entity per node, one typed edge per pair.

    The anchor alone carries the seed class so a seed-class walk starts
    there and nowhere else; every other member carries one other class —
    the walk is typed on EDGES, not nodes, so the member class is a role
    name and nothing more. Both classes and the edge type are the ontology
    fixture's, named by role above (CLAUDE.md §6.4).
    """
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    generated = document["_generated"]
    nodes = document["insert"]
    uris = [node["@id"] for node in nodes]
    assert len(uris) == len(set(uris)) == generated["nodes"], "the fixture's node roster moved"
    assert ANCHOR in uris
    pairs = _normalized_family_edges(document)
    members = set(uris)
    assert all(parent in members and child in members for parent, child in pairs)
    entities = tuple(
        _entity(uri, SEED_CLASS if uri == ANCHOR else CHILD_CLASS) for uri in uris
    )
    relationships = tuple(
        _edge(parent, child) for parent, child in sorted(pairs)
    )
    return _view(entities, relationships)


def _family(build: object, depth: int) -> frozenset[str]:
    return _reached(build(depth), family_view())  # type: ignore[operator]


def test_the_fixture_normalizes_to_the_seven_hundred_and_twenty_two_edges() -> None:
    """The measurement's premise: 748 nodes, 722 distinct parent→child pairs."""
    view = family_view()
    assert len(view.entities) == 748
    assert len(view.relationships) == 722
    assert sum(1 for r in view.entities if r.claim.entity_class == SEED_CLASS) == 1


def test_the_directed_walk_reaches_20_21_22() -> None:
    """Criterion 9, the directed triple: 20 / 21 / 22 at depths 1 / 2 / 3.

    Counted INCLUDING the anchor (see ``DIRECTED_BY_DEPTH``). The walk is
    ``traversal.typed-descendants`` — parent to child under the orientation
    stated at the top of this section — from the anchor as the only start.
    """
    measured = tuple(len(_family(_descendants, depth)) for depth in (1, 2, 3))
    assert measured == DIRECTED_BY_DEPTH, (
        f"traversal.typed-descendants reached {measured} from the anchor;"
        f" criterion 9 locks {DIRECTED_BY_DEPTH}"
    )
    for depth in (1, 2, 3):
        assert ANCHOR in _family(_descendants, depth)
    assert tuple(len(_family(_descendants, d)) - 1 for d in (1, 2, 3)) == (19, 20, 21)


def test_the_undirected_neighborhood_reaches_20_22_22() -> None:
    """Criterion 9, the undirected triple: 20 / 22 / 22 on the same view.

    ``traversal.typed-neighborhood`` from the same anchor, same depths, same
    edges — the 1.1.0 walk, unchanged (D-10), which is why the two triples
    differ at exactly one depth.
    """
    measured = tuple(len(_family(_neighborhood, depth)) for depth in (1, 2, 3))
    assert measured == UNDIRECTED_BY_DEPTH, (
        f"traversal.typed-neighborhood reached {measured} from the anchor;"
        f" criterion 9 locks {UNDIRECTED_BY_DEPTH}"
    )
    assert tuple(len(_family(_neighborhood, d)) - 1 for d in (1, 2, 3)) == (19, 21, 21)


def test_the_depth_2_divergent_node_is_the_cycle_closer_by_id() -> None:
    """The one node the neighborhood serves at depth 2 that the tree places at 3.

    24.4-D-36's measured cause: a cycle's closing edge is stored INTO a node
    the anchor reaches at depth 1, so one undirected hop reaches the closer
    at depth 2 while the directed walk reaches it only through the cycle,
    at depth 3. Asserted by id, and asserted to be the WHOLE difference —
    at depths 1 and 3 the two walks agree exactly.
    """
    assert _family(_neighborhood, 1) == _family(_descendants, 1)
    assert _family(_neighborhood, 2) - _family(_descendants, 2) == {DIVERGENT_AT_DEPTH_2}
    assert _family(_descendants, 2) < _family(_neighborhood, 2)
    assert DIVERGENT_AT_DEPTH_2 not in _family(_descendants, 2)
    assert DIVERGENT_AT_DEPTH_2 in _family(_descendants, 3)
    assert _family(_neighborhood, 3) == _family(_descendants, 3)


@pytest.mark.parametrize("depth", [1, 2, 3])
@pytest.mark.parametrize(
    "build",
    [_neighborhood, _descendants],
    ids=["typed-neighborhood", "typed-descendants"],
)
def test_the_fallback_agrees_on_both_walks(build: object, depth: int) -> None:
    """`_walk` under each operator's own intent answers the fixture identically.

    The oracle every backend is held to, held here to the operator on the
    criterion's own graph — entities AND edges — so the 20/21/22 and
    20/22/22 figures are the fallback's figures too.
    """
    view = family_view()
    operator = build(depth)  # type: ignore[operator]
    fragment = operator.read_intent()
    assert fragment.traverse is not None
    entities, edges = _walk(
        view.entities, view.relationships, traverse=fragment.traverse, seeds=None
    )
    output = operator.apply(
        view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    assert entities == output.view.entities
    assert edges == output.view.relationships


def test_control_the_fixture_measurement_fails_on_a_copy_that_ignores_direction(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage in a scratch copy: the forward-only adjacency made undirected.

    On the copy, ``traversal.typed-descendants`` reaches the neighborhood's
    20 / 22 / 22 and the 20 / 21 / 22 predicate FAILS naming the key; the
    real tree is untouched — asserted through ``git`` on the one file the
    copy is made from, in plan 24.5-04's shape.
    """
    real = CATEGORIES_SOURCE.read_text(encoding="utf-8")
    assert real.count(FORWARD_BRANCH) == 1, "the forward branch moved; re-anchor"
    sabotaged = real.replace(FORWARD_BRANCH, "        if True:\n", 1)
    module = _import_scratch_copy(
        sabotaged, "_ccf_categories_no_direction_fixture", tmp_path
    )

    def copy(depth: int) -> object:
        return module.TraversalDescendants(
            parameters=TraversalDescendantsParameters(
                seed_entity_classes=frozenset({SEED_CLASS}),
                relationship_types=frozenset({EDGE_TYPE}),
                depth_limit=depth,
            )
        )

    measured = tuple(len(_family(copy, depth)) for depth in (1, 2, 3))
    with pytest.raises(AssertionError, match="traversal.typed-descendants"):
        assert measured == DIRECTED_BY_DEPTH, (
            f"traversal.typed-descendants reached {measured} from the anchor;"
            f" criterion 9 locks {DIRECTED_BY_DEPTH}"
        )
    assert measured == UNDIRECTED_BY_DEPTH
    status = subprocess.run(
        ["git", "status", "--short", "--", str(CATEGORIES_SOURCE)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert status == "", f"the control edited the real tree: {status!r}"
