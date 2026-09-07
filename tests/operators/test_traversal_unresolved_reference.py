"""An unresolved reference is not a traversal member — G-28, ledger row `CP04-G-28`.

`D-IMPL-267` rules the meaning of a dangling endpoint and `D-IMPL-268` rules
the mechanism. The rulings this module proves, in the order they were made:

* **D-01** — a claim-less endpoint is an *unresolved reference*: legal
  persisted graph state (whitepaper §7.3, INV-CH7-20 — edges are first-class
  claims, never derived joins), but not a traversal member until an entity
  claim exists for it.
* **D-02** — traversal membership requires an entity claim. An edge
  establishes a relationship assertion; it does not establish the existence
  or the type of an entity for traversal purposes.
* **D-03** — the endpoint is not admitted and no placeholder record is
  manufactured; a synthetic entity would assert context no source did.
* **D-04** — exclusion is a traversal *semantic*, not an invariant failure:
  the walk raises nothing, refuses nothing, and annotates nothing.
* **D-05 / P-2** — equivalent questions over equivalent pinned state yield
  the same canonical result whatever the execution path, so every equality
  here is on ``canonical_bytes``, never on a URI set.
* **D-06** — one rule for anchors and neighbors alike: a claim-less URI is
  neither a valid walk start nor an intermediate hop.
* **D-07** — an excluded endpoint consumes no depth and lies on no path, so
  a bypass around it answers at the depth the bypass costs.
* **P-1** — persisted graph state and traversal membership are not the same
  universe.

**The oracle is** ``src/ccf/graph/fallback.py::answer`` — the query tier's
ruled sequence, closure included: step 4 endpoint-closes the surviving edges
against the surviving entity universe (`GQ-16` at
docs/GRAPH_QUERY_SEMANTICS.md:316, `GQ-13` at
docs/GRAPH_QUERY_SEMANTICS.md:261) *before* step 5 walks (`GQ-10` at
docs/GRAPH_QUERY_SEMANTICS.md:201). It is emphatically NOT
``src/ccf/graph/fallback.py::_walk``: the bare walk skips that closure and
therefore AGREES with the shipped operator on exactly the shape this module
is about, which is why
``tests/operators/test_traversal_admission.py::test_the_fallback_walk_agrees_with_the_operator``
stays green in both states and is not the G-28 instrument (`D-GATE-24.5` R1).

**Written RED first.** Against the shipped ``_bounded_walk`` the discriminating
tests here FAIL: the in-process walk steps onto the claim-less URI, spends a
hop on it, and continues to whatever claimed node lies beyond. That red is the
evidence; the conforming close-then-walk change is `D-IMPL-268` decision 2 and
lands separately. The copy-and-mutate sabotage controls that prove each of
these tests can also fail *for the right reason* land with it.

Whitepaper §7.4 (INV-CH7-24 the bounded walk, INV-CH7-40 no leak by absence).

Fixture discipline inherited from ``tests/properties/strategies.py``: the
classes and the edge type are read from the ontology fixture and named here by
their ROLE in the view — no entity class and no relationship type is written
in this file (CLAUDE.md §6.4).
"""

from __future__ import annotations

import ast
import importlib.util
import logging
import pathlib
import subprocess
import sys
import warnings
from types import ModuleType

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.graph.fallback import answer
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphView,
    RelationshipRecord,
)
from ccf.operators.base import OperatorOutput
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
SRC_PACKAGE = REPO_ROOT / "src" / "ccf"
#: The one source file every sabotage control below copies and mutates. Never
#: written to — the controls write under ``tmp_path`` and the last test in the
#: module reads this file's cleanliness back out of ``git``.
CATEGORIES_SOURCE = SRC_PACKAGE / "operators" / "categories.py"

#: The three roles, in ontology vocabulary. The seed class starts the walk;
#: the unresolved class is the one NO claimed entity in this module carries,
#: so a URI drawn from its pool is claim-less on every view built here; the
#: target class is what lies beyond the unresolved reference, and what the
#: bypass is built from.
SEED_CLASS, UNRESOLVED_CLASS, TARGET_CLASS = ENTITY_CLASSES[:3]
#: One typed edge from the ontology. The walk crosses EDGES by type and reads
#: a reached node's class only through admission, so one type builds every
#: shape this module needs.
EDGE_TYPE: str = RELATIONSHIP_RULES[0][0]

#: A (claimed, the anchor) — X (the unresolved reference) — B (claimed,
#: beyond it); C and D are the claimed intermediates of the G3 bypass.
A_URI = ENTITY_POOL[SEED_CLASS][0]
#: X is drawn from the pool and is NEVER given an ``_entity`` record on G1,
#: G2 or G3: it is named by edges and by nothing else. That is the whole
#: shape (D-01, P-1). The twin view below is the one place it gets a claim.
X_URI = ENTITY_POOL[UNRESOLVED_CLASS][2]
B_URI = ENTITY_POOL[TARGET_CLASS][0]
C_URI = ENTITY_POOL[TARGET_CLASS][1]
D_URI = ENTITY_POOL[TARGET_CLASS][2]

EARLY = INSTANTS[0]
BUNDLE: str = GENERATION["permitted_policy_bundle_version"]
CLASSIFICATION: str = GENERATION["classifications"][0]
SYSTEM: str = GENERATION["source_systems"][0]

#: The class names a class-name scan would find if some tier ever
#: manufactured a stand-in for an unresolved endpoint (D-03). Substrings,
#: lowercased, matched against ``ClassDef`` names only — plan 04's docstrings
#: legitimately say "unresolved reference" in prose, and prose is not a type.
PLACEHOLDER_TOKENS: tuple[str, ...] = (
    "placeholder",
    "unresolved",
    "phantom",
    "dangling",
    "standin",
    "stand_in",
    "sentinel",
)

#: The exact closure clause mechanism (i) added to ``_bounded_walk``
#: (`D-IMPL-268`). Asserted PRESENT exactly once in the real source before any
#: copy is mutated, so no control below can pass vacuously against a file that
#: never carried it — the ``ADMISSION_PREDICATE`` voice from
#: ``tests/operators/test_traversal_admission.py``.
CLOSURE_PREDICATE = (
    "if edge.claim.subject_uri in universe and edge.claim.object_uri in universe"
)
#: The line that turns the reached URI set back into records. The
#: planted-placeholder control replaces it to manufacture the record D-03
#: forbids; present once.
REACHED_ENTITIES = (
    "record for record in view.entities if record.claim.entity_uri in reached"
)
#: Every operator in the module mints provenance through this one call, so the
#: conditional-annotation control replaces all FOUR occurrences at once and the
#: two traversal shapes cannot disagree about what they stamped.
PROVENANCE_CALL = "provenance=mint_provenance(self, upstream=upstream),"
#: The WHOLE frontier comprehension, because ``    frontier = {`` alone occurs
#: twice (the seed selection and the per-hop rebuild). The seeding control
#: replaces this block so starts come from persisted edge endpoints instead of
#: entity claims; present once.
FRONTIER_BLOCK = """    frontier = {
        record.claim.entity_uri
        for record in view.entities
        if record.claim.entity_class in seed_classes
    }"""

#: Which declared-parameter contract each traversal operator reads. The two
#: shapes share the ``traversal`` category and differ in the direction their
#: own class fixes (ledger row ``24.5-L-06``).
PARAMETERS_FOR: dict[type, type] = {
    TraversalNeighborhood: TraversalNeighborhoodParameters,
    TraversalDescendants: TraversalDescendantsParameters,
}

#: Both shapes, for the parametrizations below.
OPERATOR_CLASSES: tuple[type, ...] = (TraversalNeighborhood, TraversalDescendants)
OPERATOR_IDS: tuple[str, ...] = ("typed-neighborhood", "typed-descendants")


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


# --- the three ruled shapes, plus the fully-claimed twin ---------------------


def g1_view() -> GraphView:
    """G1, the chain: A → X → B, with X carrying no entity claim."""
    entities = (_entity(A_URI, SEED_CLASS), _entity(B_URI, TARGET_CLASS))
    relationships = (_edge(A_URI, X_URI), _edge(X_URI, B_URI))
    return _view(entities, relationships)


def g2_view() -> GraphView:
    """G2, the cycle: G1 plus X → A, so the unresolved reference closes a loop."""
    entities = (_entity(A_URI, SEED_CLASS), _entity(B_URI, TARGET_CLASS))
    relationships = (_edge(A_URI, X_URI), _edge(X_URI, B_URI), _edge(X_URI, A_URI))
    return _view(entities, relationships)


def g3_view() -> GraphView:
    """G3, the bypass: G1 plus a fully-claimed A → C → D → B route beside it.

    The claimed route costs three hops; the route through the unresolved
    reference would cost two. D-07 is exactly the difference: at
    ``depth_limit=2`` the answer is what the bypass reaches, never what the
    phantom shortcut would have.
    """
    entities = (
        _entity(A_URI, SEED_CLASS),
        _entity(B_URI, TARGET_CLASS),
        _entity(C_URI, TARGET_CLASS),
        _entity(D_URI, TARGET_CLASS),
    )
    relationships = (
        _edge(A_URI, X_URI),
        _edge(X_URI, B_URI),
        _edge(A_URI, C_URI),
        _edge(C_URI, D_URI),
        _edge(D_URI, B_URI),
    )
    return _view(entities, relationships)


def twin_view() -> GraphView:
    """G1 with X CLAIMED — the control state in which the walk legitimately crosses.

    Every fact G1 carries, plus the one assertion G1 is missing. Whatever the
    walk is allowed to do here it is not allowed to do on G1, and the
    difference between the two answers is the whole of D-01.
    """
    entities = (
        _entity(A_URI, SEED_CLASS),
        _entity(B_URI, TARGET_CLASS),
        _entity(X_URI, UNRESOLVED_CLASS),
    )
    relationships = (_edge(A_URI, X_URI), _edge(X_URI, B_URI))
    return _view(entities, relationships)


G1 = g1_view()
G2 = g2_view()
G3 = g3_view()
TWIN = twin_view()


# --- the operator, the oracle, and the one equality --------------------------


def traversal(
    *,
    seed_classes: frozenset[str] = frozenset({SEED_CLASS}),
    admitted: frozenset[str] | None = None,
    depth: int = 2,
    operator_class: type = TraversalNeighborhood,
) -> object:
    """One traversal operator of either shape, built from its own parameter class."""
    parameters_class = PARAMETERS_FOR.get(operator_class)
    if parameters_class is None:
        # A scratch copy imported under another module name is a DIFFERENT
        # class object with the same ``key``; resolve it by key so the
        # sabotage controls can hand their copies to this helper.
        parameters_class = (
            TraversalNeighborhoodParameters
            if getattr(operator_class, "key", "") == TraversalNeighborhood.key
            else TraversalDescendantsParameters
        )
    operator = operator_class(
        parameters=parameters_class(
            seed_entity_classes=seed_classes,
            relationship_types=frozenset({EDGE_TYPE}),
            depth_limit=depth,
            admitted_entity_classes=admitted,
        )
    )
    return operator


def output_of(operator: object, view: GraphView) -> OperatorOutput:
    """What the in-process operator tier answers over ``view``."""
    result: OperatorOutput = operator.apply(  # type: ignore[attr-defined]
        view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    return result


def expected(operator: object, view: GraphView) -> GraphView:
    """The reference semantics for the operator's own question, frozen as a view.

    The operator's ``read_intent()`` renders its traverse family (`GQ-02` at
    docs/GRAPH_QUERY_SEMANTICS.md:64); ``answer`` runs the ruled sequence over
    the same records. The freeze reproduces the two sorts
    ``tests/conformance/test_substrate_differential.py::_frozen_at`` applies,
    so ordering is the interface's on both sides of the comparison (`GQ-22` at
    docs/GRAPH_QUERY_SEMANTICS.md:461) and the equality below is about
    semantics, not about collection order.
    """
    fragment = operator.read_intent()  # type: ignore[attr-defined]
    assert fragment.traverse is not None
    entities, relationships = answer(
        view.entities,
        view.relationships,
        query=GraphQuery(
            tenant_id=TENANT, as_of=view.as_of, traverse=fragment.traverse
        ),
    )
    return GraphView(
        tenant_id=TENANT,
        as_of=view.as_of,
        entities=tuple(sorted(entities, key=lambda record: record.claim.entity_uri)),
        relationships=tuple(
            sorted(relationships, key=lambda record: record.relationship_key)
        ),
    )


def assert_answers_the_reference(operator: object, view: GraphView) -> None:
    """The one equality: the operator tier answers the reference semantics, by bytes.

    Takes the operator INSTANCE rather than a class, so a scratch copy built
    from a sabotaged module can be handed to the same assertion body.
    """
    answered = output_of(operator, view).view
    reference = expected(operator, view)
    assert canonical_bytes(answered) == canonical_bytes(reference), (
        "operator tier diverges from the reference traversal semantics for"
        f" {operator.key!r}: answered"  # type: ignore[attr-defined]
        f" {sorted(record.claim.entity_uri for record in answered.entities)}"
        " where the reference answers"
        f" {sorted(record.claim.entity_uri for record in reference.entities)}"
    )


def assert_provenance_is_twin_equal(operator: object) -> None:
    """The structural form of "nothing was annotated" (D-04), for ANY operator.

    Factored out of ``test_exclusion_is_silent`` so the conditional-annotation
    sabotage below can run the very same assertion body against a scratch
    copy: the instrument is only discriminating if the sabotage makes THIS
    comparison fail, and it can only be shown to do that if both sides call
    one function.
    """
    on_g1 = output_of(operator, G1)
    on_twin = output_of(operator, TWIN)
    assert canonical_bytes(on_g1.provenance) == canonical_bytes(on_twin.provenance), (
        "the walk annotated its provenance differently when an endpoint was"
        " unresolved — exclusion is a semantic, not a finding (D-04)"
    )


def _reached(view: GraphView) -> set[str]:
    return {record.claim.entity_uri for record in view.entities}


def _edges(view: GraphView) -> set[tuple[str, str]]:
    return {
        (record.claim.subject_uri, record.claim.object_uri)
        for record in view.relationships
    }


# --- 1. the views carry the shape the module claims --------------------------


def test_the_views_carry_the_unresolved_reference_as_state() -> None:
    """X is in no entity record and in 2 / 3 / 2 edges — asserted, not assumed.

    Persisted state keeps the edge (`GQ-05` at
    docs/GRAPH_QUERY_SEMANTICS.md:122, `GQ-21` at
    docs/GRAPH_QUERY_SEMANTICS.md:446; whitepaper §7.3 INV-CH7-20): nothing
    in this phase prunes an unresolved reference out of the graph. A view
    that lost the shape would make every test below pass vacuously.
    """
    assert len({SEED_CLASS, UNRESOLVED_CLASS, TARGET_CLASS}) == 3
    assert len({A_URI, X_URI, B_URI, C_URI, D_URI}) == 5
    for view in (G1, G2, G3):
        assert X_URI not in _reached(view), "X carries an entity claim; the shape is gone"
        # ... and no CLAIMED entity carries the unresolved class either, so a
        # walk seeded on that class has no start anywhere (test 5).
        assert UNRESOLVED_CLASS not in {
            record.claim.entity_class for record in view.entities
        }
    touching = {
        "g1": sum(
            1
            for record in G1.relationships
            if X_URI in (record.claim.subject_uri, record.claim.object_uri)
        ),
        "g2": sum(
            1
            for record in G2.relationships
            if X_URI in (record.claim.subject_uri, record.claim.object_uri)
        ),
        "g3": sum(
            1
            for record in G3.relationships
            if X_URI in (record.claim.subject_uri, record.claim.object_uri)
        ),
    }
    assert touching == {"g1": 2, "g2": 3, "g3": 2}
    assert _reached(G1) == {A_URI, B_URI}
    assert _reached(G3) == {A_URI, B_URI, C_URI, D_URI}
    # The twin is G1 plus the one missing claim, and nothing else.
    assert _reached(TWIN) == {A_URI, B_URI, X_URI}
    assert _edges(TWIN) == _edges(G1)
    # ... and it is a DIFFERENT state, not a relabeling: the added claim moves
    # the bytes. Without this the provenance control in the silence test could
    # be comparing one state's answer with itself.
    assert canonical_bytes(TWIN) != canonical_bytes(G1)


# --- 2. the chain ------------------------------------------------------------


@pytest.mark.parametrize("depth", [2, 3])
@pytest.mark.parametrize("operator_class", OPERATOR_CLASSES, ids=OPERATOR_IDS)
def test_the_operator_answers_the_reference_semantics_on_the_chain(
    operator_class: type, depth: int
) -> None:
    """G1: the walk stops at the anchor, because X cannot be crossed (D-01, D-02).

    The edge A → X is persisted state and stays in the view; it is not a hop
    (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261 — hop admissibility, prune
    before walking). B is claimed, but its only route runs through an
    endpoint no entity claim covers, so no path to it exists for traversal
    (P-1). The answer is the anchor alone, with no edge among the reached.

    RED on the shipped walk, which reaches B through the phantom.
    """
    operator = traversal(depth=depth, operator_class=operator_class)
    assert_answers_the_reference(operator, G1)
    answered = output_of(operator, G1).view
    assert _reached(answered) == {A_URI}
    assert _edges(answered) == set()


# --- 3. the cycle ------------------------------------------------------------


@pytest.mark.parametrize("depth", [2, 3])
@pytest.mark.parametrize("operator_class", OPERATOR_CLASSES, ids=OPERATOR_IDS)
def test_the_cycle_answers_as_the_chain_does(
    operator_class: type, depth: int
) -> None:
    """G2: an unresolved reference participates in no cycle (D-07).

    X → A closes a loop through a node that is not a traversal member, so G2
    and G1 are the same question with the same answer, byte for byte.

    Two assertions with different jobs. The reference equality is the
    discriminating one and is RED on the shipped walk. The G1/G2 equality is
    a CONTROL: it holds under the shipped walk too (the shipped walk reaches
    ``{A, B}`` on both), and what would red it is the placeholder sabotage —
    a manufactured record for X would make the extra edge visible in one
    answer and not the other.
    """
    operator = traversal(depth=depth, operator_class=operator_class)
    assert canonical_bytes(output_of(operator, G2).view) == canonical_bytes(
        output_of(operator, G1).view
    ), "the cycle-closing edge through an unresolved reference changed the answer"
    assert_answers_the_reference(operator, G2)


# --- 4. depth accounting: the bypass -----------------------------------------


def _bypass_expectation(depth: int) -> tuple[set[str], set[tuple[str, str]]]:
    """What G3 answers at ``depth``, from D-07 — reached URIs and reached edges.

    A function rather than a module-level table: the numeric-table lint
    (CINV-01b) reads a module-level collection of constants as a Control
    Plane value, and these are the ruled figures a test asserts.
    """
    if depth == 2:
        return {A_URI, C_URI, D_URI}, {(A_URI, C_URI), (C_URI, D_URI)}
    return (
        {A_URI, B_URI, C_URI, D_URI},
        {(A_URI, C_URI), (C_URI, D_URI), (D_URI, B_URI)},
    )


@pytest.mark.parametrize("depth", [2, 3])
@pytest.mark.parametrize("operator_class", OPERATOR_CLASSES, ids=OPERATOR_IDS)
def test_a_phantom_endpoint_consumes_no_depth_on_the_bypass(
    operator_class: type, depth: int
) -> None:
    """G3: depth counts admitted hops, never persisted edge hops (D-07).

    B sits two persisted hops from A through the unresolved reference and
    three claimed hops around it. At ``depth_limit=2`` the answer is
    ``{A, C, D}`` with the two bypass edges; only at ``depth_limit=3`` does
    the claimed route reach B. An implementation that secretly walks through
    the phantom agrees on the depth-3 entity set and disagrees at depth 2 —
    which is why the readable statement is asserted at BOTH depths rather
    than at the one that diverges.

    RED at depth 2 on the shipped walk, which answers ``{A, B, C, D}``.
    """
    operator = traversal(depth=depth, operator_class=operator_class)
    assert_answers_the_reference(operator, G3)
    answered = output_of(operator, G3).view
    reached, edges = _bypass_expectation(depth)
    assert _reached(answered) == reached
    assert _edges(answered) == edges


# --- 5. the anchor control: a claim-less URI is not a start ------------------


@pytest.mark.parametrize(
    ("view", "name"), [(G1, "g1"), (G2, "g2"), (G3, "g3")], ids=["g1", "g2", "g3"]
)
@pytest.mark.parametrize("operator_class", OPERATOR_CLASSES, ids=OPERATOR_IDS)
def test_a_claim_less_uri_is_not_a_walk_start(
    operator_class: type, view: GraphView, name: str
) -> None:
    """One rule for anchors and neighbors alike (D-06): seeding on the class X
    would carry, if it carried one, starts nothing.

    Walk starts are selected over in-scope entities (`GQ-11` at
    docs/GRAPH_QUERY_SEMANTICS.md:221); no claimed entity on these views is
    of the unresolved class, so the frontier is empty and the answer is the
    empty view. A control: green in both states, and what reds it is a
    scratch copy that seeds from adjacency keys instead of entity records.
    """
    operator = traversal(
        seed_classes=frozenset({UNRESOLVED_CLASS}), operator_class=operator_class
    )
    assert_answers_the_reference(operator, view)
    answered = output_of(operator, view).view
    assert answered.entities == (), f"a claim-less URI started a walk on {name}"
    assert answered.relationships == ()


# --- 6. no record is manufactured, anywhere ----------------------------------


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
@pytest.mark.parametrize(
    ("view", "name"), [(G1, "g1"), (G2, "g2"), (G3, "g3")], ids=["g1", "g2", "g3"]
)
@pytest.mark.parametrize("operator_class", OPERATOR_CLASSES, ids=OPERATOR_IDS)
def test_exclusion_manufactures_nothing(
    operator_class: type, view: GraphView, name: str, depth: int
) -> None:
    """X is in no answer at any depth, in either direction (D-03).

    A control, green in both states: the shipped walk crosses the phantom but
    never emits it, because ``src/ccf/operators/categories.py::_substitute``
    prunes to entity records. That is precisely why an entity-set check on
    the output alone is not the G-28 instrument — the divergence is in what
    lies BEYOND X, not in X.
    """
    operator = traversal(depth=depth, operator_class=operator_class)
    answered = output_of(operator, view).view
    assert X_URI not in _reached(answered), (
        f"a record for the unresolved reference appeared on {name} at depth {depth}"
    )
    assert X_URI not in {
        uri for edge in _edges(answered) for uri in edge
    }, f"an edge naming the unresolved reference survived on {name}"


def _placeholder_classes(source: str) -> list[str]:
    """Every ``ClassDef`` name in ``source`` that reads as a stand-in type."""
    return [
        node.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef)
        and any(token in node.name.lower() for token in PLACEHOLDER_TOKENS)
    ]


def test_the_placeholder_scan_sees_a_planted_class() -> None:
    """The positive control, run BEFORE the negative claim below is believed."""
    planted = "class UnresolvedEndpointPlaceholder:\n    pass\n"
    assert _placeholder_classes(planted) == ["UnresolvedEndpointPlaceholder"]
    assert _placeholder_classes("class ClaimedEntity:\n    pass\n") == []


def test_no_placeholder_type_exists_in_the_library() -> None:
    """D-03: nothing in ``src/ccf`` is a stand-in type for an unresolved endpoint.

    Admitting the endpoint would have required a synthetic entity record, and
    a synthetic record needs a type to be. The absence of the type is the
    structural form of "no placeholder was manufactured"; the scan's own
    positive control is the test above.
    """
    modules = sorted(SRC_PACKAGE.rglob("*.py"))
    assert len(modules) > 1, "the library scan found no modules; re-anchor SRC_PACKAGE"
    found = {
        path.relative_to(REPO_ROOT).as_posix(): names
        for path in modules
        if (names := _placeholder_classes(path.read_text(encoding="utf-8")))
    }
    assert found == {}, f"a stand-in type for an unresolved endpoint exists: {found}"


# --- 7. the exclusion is silent ----------------------------------------------


@pytest.mark.parametrize("operator_class", OPERATOR_CLASSES, ids=OPERATOR_IDS)
def test_exclusion_is_silent(
    operator_class: type, caplog: pytest.LogCaptureFixture
) -> None:
    """D-04: a traversal semantic, not a finding and not an invariant failure.

    Nothing here counts, marks, warns, logs or raises on an unresolved
    reference. Whether the existence or count of excluded unresolved
    references should later become execution/completeness evidence is the
    named carry ``24.8-C-01`` and is explicitly DEFERRED — recording it would
    be a product-findings design, which the ruling holds out of G-28.

    The provenance equality against the fully-claimed twin is the structural
    form of "nothing was annotated". It is trivially true today —
    ``src/ccf/operators/base.py::mint_provenance`` never reads the view — so
    it is a control here, not a discriminating assertion; what makes it
    discriminating is the CONDITIONAL annotation sabotage that lands with the
    fix: a scratch copy that stamps provenance only when an endpoint fell
    outside the universe makes provenance(G1) differ from provenance(twin)
    for the same operator.
    """
    operator = traversal(operator_class=operator_class)
    caplog.set_level(logging.DEBUG)
    with warnings.catch_warnings(record=True) as raised:
        warnings.simplefilter("always")
        output_of(operator, G1)
    assert [str(item.message) for item in raised] == []
    assert [
        record.name for record in caplog.records if record.name.startswith("ccf")
    ] == []
    assert_provenance_is_twin_equal(operator)


# --- 8. the sabotage controls: every instrument above can still fail ---------
#
# Copy-and-mutate, never edit-and-revert: the real
# ``src/ccf/operators/categories.py`` is read, mutated in memory, written under
# ``tmp_path`` and imported under a scratch name. The pattern and its
# cleanliness assertion are
# ``tests/operators/test_traversal_admission.py::_import_sabotaged_categories``
# and ``::test_no_control_edits_the_real_source_tree``; the real-tree
# assertion is repeated at the end of this section so a control that crashed
# halfway cannot leave the tree modified and this module green.


def _import_mutated_categories(
    tmp_path: pathlib.Path,
    *,
    replace: str,
    with_: str,
    name: str,
    count: int = 1,
    extra: tuple[tuple[str, str, int], ...] = (),
    append: str = "",
) -> ModuleType:
    """A copy of ``categories.py`` with named literals replaced, under a scratch name.

    ``replace``/``with_``/``count`` is the primary edit; ``extra`` carries any
    further ``(replace, with_, count)`` triples a control needs (the
    conditional-annotation control mutates three sites at once), and ``append``
    adds scratch-only module-level helpers after the copy. Every premise is
    asserted against the REAL source before the mutation, so a control cannot
    pass vacuously against a file that no longer carries the literal it pins.
    """
    source = CATEGORIES_SOURCE.read_text(encoding="utf-8")
    edits = ((replace, with_, count), *extra)
    for original, replacement, occurrences in edits:
        assert source.count(original) == occurrences, (
            f"{original!r} occurs {source.count(original)} times in"
            f" {CATEGORIES_SOURCE}, not {occurrences}; re-anchor the control"
        )
        source = source.replace(original, replacement)
        if original not in replacement:
            # Only meaningful when the mutation REMOVES the literal; controls
            # that wrap it (``… or _note_exclusion()``) legitimately keep it.
            assert original not in source
        else:
            assert source.count(original) == occurrences
    scratch = tmp_path / f"{name}.py"
    scratch.write_text(source + append, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, scratch)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def test_control_closure_removed_reaches_through_the_phantom(
    tmp_path: pathlib.Path,
) -> None:
    """Criteria 5 and 6 (D-01, D-02, D-05, D-07): drop the closure, the walk crosses X.

    The copy is the SHIPPED walk of `D-GATE-24.5` R1 — closure removed is
    exactly the pre-`D-IMPL-268` behavior — so its answers are the divergence
    research measured, not an invented one: ``{A, B}`` on the G1 chain and
    ``{A, B, C, D}`` on the G3 bypass at ``depth_limit=2``.
    """
    copy_module = _import_mutated_categories(
        tmp_path,
        replace=CLOSURE_PREDICATE,
        with_="if True",
        name="_ccf_categories_closure_removed",
    )
    copy = traversal(operator_class=copy_module.TraversalNeighborhood)
    real = traversal()

    with pytest.raises(AssertionError, match="operator tier"):
        assert_answers_the_reference(copy, G1)
    # The positive statement: the copy reached BEYOND the unresolved reference.
    copy_on_g1 = _reached(output_of(copy, G1).view)
    assert copy_on_g1 == {A_URI, B_URI}
    assert copy_on_g1 - _reached(output_of(real, G1).view) == {B_URI}

    # And criterion 6's observed red on the bypass: the phantom shortcut costs
    # two hops, so the copy reaches B at a depth the claimed route cannot.
    copy_at_two = traversal(depth=2, operator_class=copy_module.TraversalNeighborhood)
    with pytest.raises(AssertionError, match="operator tier"):
        assert_answers_the_reference(copy_at_two, G3)
    assert _reached(output_of(copy_at_two, G3).view) == {A_URI, B_URI, C_URI, D_URI}
    assert _reached(output_of(traversal(depth=2), G3).view) == {A_URI, C_URI, D_URI}


def test_control_a_planted_placeholder_appears_in_the_answer(
    tmp_path: pathlib.Path,
) -> None:
    """Criterion 8 (D-03): manufacture a record for X and the exclusion tests red.

    Two mutations, because a placeholder is only observable once the walk
    reaches the URI: the closure is dropped, and the reached-to-records line
    additionally yields, for every reached URI carrying no claim, a record
    copied from the view's first entity with ``entity_uri`` rewritten to it
    (frozen pydantic models copy through ``model_copy``). That is the synthetic
    entity D-03 refuses — asserting context no source ever did.

    It also reds ``test_the_cycle_answers_as_the_chain_does``'s G1/G2 control:
    once X is a record it survives ``_substitute``, so the cycle-closing edge
    X -> A appears in the G2 answer and not in the G1 answer.
    """
    # The plant lives in an appended helper rather than inline in the
    # comprehension, so the replaced literal stays a single call. ``dict(...)``
    # rather than a brace literal keeps the scratch source out of the
    # prompt-shape lint's brace-density signal (CINV-01a) — the fragment is
    # Python, not prose.
    plant = (
        "\n\ndef _manufacture(view, reached):\n"
        "    claimed = set(r.claim.entity_uri for r in view.entities)\n"
        "    kept = [r for r in view.entities if r.claim.entity_uri in reached]\n"
        "    for uri in sorted(reached - claimed):\n"
        "        first = view.entities[0]\n"
        "        rewritten = first.claim.model_copy(update=dict(entity_uri=uri))\n"
        "        kept.append(first.model_copy(update=dict(claim=rewritten)))\n"
        "    return kept\n"
    )
    copy_module = _import_mutated_categories(
        tmp_path,
        replace=CLOSURE_PREDICATE,
        with_="if True",
        name="_ccf_categories_planted_placeholder",
        extra=((REACHED_ENTITIES, "_manufacture(view, reached)", 1),),
        append=plant,
    )
    copy = traversal(operator_class=copy_module.TraversalNeighborhood)

    on_g2 = output_of(copy, G2).view
    assert X_URI in _reached(on_g2), "the plant did not reach the answer"
    with pytest.raises(AssertionError, match="operator tier"):
        assert_answers_the_reference(copy, G2)
    # Discriminating for the cycle instrument: the copy's G2 answer is no
    # longer its G1 answer, because the manufactured record keeps X -> A.
    assert canonical_bytes(on_g2) != canonical_bytes(output_of(copy, G1).view)
    assert _edges(on_g2) - _edges(output_of(copy, G1).view) == {(X_URI, A_URI)}
    # The real operator manufactures nothing on the same state.
    assert X_URI not in _reached(output_of(traversal(), G2).view)


def test_control_a_raise_on_exclusion_breaks_the_walk(
    tmp_path: pathlib.Path,
) -> None:
    """Criterion 9 (D-04): exclusion is a SEMANTIC, so a refusal must be visible.

    The scratch copy's closure clause is ``or``-ed with ``_refuse_unresolved``,
    a one-line helper appended to the copy that raises ``ValueError`` the first
    time an endpoint falls outside the universe (``and`` binds tighter than
    ``or``, so the raise fires exactly on the edges closure drops). The copy
    refuses on G1 and answers normally on the fully-claimed twin, which is what
    makes the control discriminating rather than merely red: it fires on
    exclusion, not on traversal.
    """
    copy_module = _import_mutated_categories(
        tmp_path,
        replace=CLOSURE_PREDICATE,
        with_=f"{CLOSURE_PREDICATE} or _refuse_unresolved()",
        name="_ccf_categories_raises_on_exclusion",
        append=(
            "\n\ndef _refuse_unresolved() -> bool:\n"
            "    raise ValueError('unresolved reference refused by the control')\n"
        ),
    )
    copy = traversal(operator_class=copy_module.TraversalNeighborhood)

    with pytest.raises(ValueError, match="unresolved reference refused"):
        output_of(copy, G1)
    # Discriminating: on the twin every endpoint is claimed, nothing is
    # excluded, and the copy answers exactly what the real operator answers.
    assert canonical_bytes(output_of(copy, TWIN).view) == canonical_bytes(
        output_of(traversal(), TWIN).view
    )
    # ... and the real operator is silent on G1, which is the ruling.
    assert _reached(output_of(traversal(), G1).view) == {A_URI}


def test_control_a_provenance_annotation_is_not_silent(
    tmp_path: pathlib.Path,
) -> None:
    """Criterion 9 (D-04): the annotation must be CONDITIONAL to red the instrument.

    ``test_exclusion_is_silent`` compares provenance(G1) with provenance(twin)
    for the SAME operator, so an unconditional stamp would sit on both sides
    and leave the instrument green. The copy therefore records whether closure
    dropped anything — the clause is ``or``-ed with ``_note_exclusion``, which
    sets a module flag and returns ``False`` so the edge is still dropped, and
    the flag is reset at the top of every walk — and then stamps
    ``index_version`` only when the flag is set, at all four ``mint_provenance``
    call sites so the two traversal shapes cannot disagree.

    Positive statements, both required: the copy's G1 provenance carries the
    marker and its twin provenance does not; and its G1 *view* bytes equal the
    real operator's, so only the silence broke, not the walk.
    """
    marker = "unresolved-references-excluded"
    copy_module = _import_mutated_categories(
        tmp_path,
        replace=CLOSURE_PREDICATE,
        with_=f"{CLOSURE_PREDICATE} or _note_exclusion()",
        name="_ccf_categories_annotates_exclusion",
        extra=(
            (
                "    universe = {record.claim.entity_uri for record in view.entities}",
                "    _reset_exclusion()\n"
                "    universe = {record.claim.entity_uri for record in view.entities}",
                1,
            ),
            (
                PROVENANCE_CALL,
                "provenance=mint_provenance(\n"
                "                self,\n"
                "                upstream=upstream,\n"
                f"                index_version=('{marker}' if _EXCLUDED else None),\n"
                "            ),",
                4,
            ),
        ),
        append=(
            "\n\n_EXCLUDED = False\n\n\n"
            "def _reset_exclusion() -> None:\n"
            "    global _EXCLUDED\n"
            "    _EXCLUDED = False\n\n\n"
            "def _note_exclusion() -> bool:\n"
            "    global _EXCLUDED\n"
            "    _EXCLUDED = True\n"
            "    return False\n"
        ),
    )
    copy = traversal(operator_class=copy_module.TraversalNeighborhood)

    # The instrument's own shape, run against the scratch operator.
    with pytest.raises(AssertionError, match="exclusion is a semantic"):
        assert_provenance_is_twin_equal(copy)
    assert output_of(copy, G1).provenance.index_version == marker
    assert output_of(copy, TWIN).provenance.index_version is None
    # The walk itself is untouched — the copy still answers the reference.
    assert canonical_bytes(output_of(copy, G1).view) == canonical_bytes(
        output_of(traversal(), G1).view
    )
    # And the real operator passes the very same assertion.
    assert_provenance_is_twin_equal(traversal())


def test_control_seeding_from_persisted_edges_creates_a_start(
    tmp_path: pathlib.Path,
) -> None:
    """Criterion 7 (D-06): one rule for anchors and neighbors alike.

    The copy seeds from every ``subject_uri`` and ``object_uri`` over the
    PERSISTED edges instead of from the view's entity claims, which is the
    "an edge establishes an entity" reading Q2 refused. Asked to seed on the
    unresolved class, the real operator and the oracle both answer the empty
    view; the copy answers ``{A, B}`` (X itself is pruned by ``_substitute``,
    which is exactly why an entity-set check alone would not have caught it).
    """
    copy_module = _import_mutated_categories(
        tmp_path,
        replace=FRONTIER_BLOCK,
        with_=(
            "    frontier = {\n"
            "        uri\n"
            "        for edge in view.relationships\n"
            "        for uri in (edge.claim.subject_uri, edge.claim.object_uri)\n"
            "    }"
        ),
        name="_ccf_categories_seeds_from_edges",
    )
    copy = traversal(
        seed_classes=frozenset({UNRESOLVED_CLASS}),
        operator_class=copy_module.TraversalNeighborhood,
    )
    real = traversal(seed_classes=frozenset({UNRESOLVED_CLASS}))

    with pytest.raises(AssertionError, match="operator tier"):
        assert_answers_the_reference(copy, G1)
    answered = _reached(output_of(copy, G1).view)
    assert answered == {A_URI, B_URI}, "the seeding control reached nothing new"
    assert output_of(real, G1).view.entities == ()
    assert expected(real, G1).entities == ()


# --- 9. the pins the controls rest on, and the real tree ---------------------


def test_the_closure_predicate_is_in_the_real_source_once() -> None:
    """Every control's premise, asserted directly: the literals are where they claim.

    A control that pins a literal the source no longer carries would raise
    inside the importer rather than pass, but the counts are asserted here too
    so the premise is a readable fact of this module and not only a side effect
    of running a sabotage.
    """
    source = CATEGORIES_SOURCE.read_text(encoding="utf-8")
    assert source.count(CLOSURE_PREDICATE) == 1
    assert source.count(REACHED_ENTITIES) == 1
    assert source.count(PROVENANCE_CALL) == 4
    assert source.count(FRONTIER_BLOCK) == 1
    # The negative control for the count instrument: a literal one character
    # off is absent, so a count of 1 is about THIS text and not about any
    # nearby line.
    assert source.count(CLOSURE_PREDICATE.replace("universe", "universez")) == 0


def test_no_control_in_this_module_edits_the_real_source_tree() -> None:
    """The controls copy; they never edit and revert. Asserted through ``git``.

    An edit-and-revert control that crashed halfway would leave the tree
    modified and this suite green, so the real file's cleanliness is read from
    ``git status --short`` and, second leg, from the unstaged diff — scoped to
    the one file the controls copy, so an unrelated edit elsewhere under
    ``src/`` cannot make this go red. The
    ``tests/operators/test_traversal_admission.py::test_no_control_edits_the_real_source_tree``
    voice.
    """
    relative = CATEGORIES_SOURCE.relative_to(REPO_ROOT).as_posix()
    status = subprocess.run(
        ["git", "status", "--short", "--", relative],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert status.strip() == "", f"a control touched the real tree: {status!r}"
    diff = subprocess.run(
        ["git", "diff", "--", relative],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert diff == ""
