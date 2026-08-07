"""Property suite ON the fallback — the oracle audited by what it does not define.

D-05 ordering: the prose (``docs/GRAPH_QUERY_SEMANTICS.md``) decides;
``ccf.graph.fallback`` implements it; adapters agree with it under the
differential suite; and *this* suite audits the fallback against the named
SPEC_INVENTORY invariants — so the reference implementation is answerable to
commitments it did not author. Every property runs the production
:func:`ccf.graph.fallback.answer` (and, where the invariant spans the
materialization core, the production :func:`ccf.graph.reader.materialize_view`
path), and byte-level claims compare ``canonical_bytes``, never raw records.

INV-ID -> property mapping (each ID mapped to the property that ACTUALLY
asserts it — do not weaken a row without moving its claim elsewhere):

* **INV-CH7-14** (bitemporal T axis, append-only L) —
  ``test_late_observed_claims_never_appear`` (a claim observed after
  ``q.as_of`` never appears), ``test_early_superseded_claims_never_appear``
  (a claim superseded at-or-before ``q.as_of`` never appears, and — the
  completeness half — a supersession minted after ``q.as_of`` renders as
  current: every as-of-surviving input record is in the degenerate answer),
  ``test_lineage_at_the_boundary`` (a lineage entry observed after
  ``q.as_of`` is absent from the answering record's lineage and a future
  supersession renders ``(None, None)`` — asserted through the production
  ``materialize_view`` -> ``answer`` path over records that retain the raw
  survival fields, per the `GQ-12` input contract at
  docs/GRAPH_QUERY_SEMANTICS.md:237).
* **INV-CH7-23** (composition preservation) —
  ``test_family_composition_is_order_independent`` (for the filter
  families, ``answer(records, policy+temporal)`` equals
  ``answer(answer(records, policy), temporal)`` and is order-independent
  between the two single-family applications, on canonical bytes) and
  ``test_repeat_answers_are_deterministic`` (identical canonical bytes on
  a second answering of the same question).
* **INV-CH7-24** (bounded traversal expansion) —
  ``test_depth_zero_yields_exactly_the_walk_starts`` (``depth_limit=0``
  answers exactly the in-scope seed-class entities),
  ``test_depth_answers_are_monotone`` (the depth-N answer is a subset of
  the depth-N+1 answer), and
  ``test_no_node_beyond_the_depth_bound_appears`` (an independent
  distance computation confirms no answered node lies beyond N admissible
  hops from every walk start).
* **INV-CH7-26** (structural absence / policy ordering, with the
  INV-CH7-40 hop-admissibility substitution semantics) —
  ``test_policy_excluded_state_is_structurally_absent_and_unreachable_through``
  (the hand-built seed - excluded - target chain: the excluded node is
  structurally absent AND the target is not reached through it, with the
  admissible-intermediate control proving the test would catch the leak).
  The D-IMPL-87 ``allowed_entities`` pins are filed under
  INV-CH7-26/INV-CH7-40 as the resurrection-defect closure:
  ``test_allowed_entities_answers_are_contained_in_the_set`` (containment
  and the induced subgraph, `GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316),
  ``test_resurrection_shape_does_not_reach_the_target`` (in-set seed and
  target, out-of-set intermediate: the walk cannot cross outside the set
  even to pass through, `GQ-15` at docs/GRAPH_QUERY_SEMANTICS.md:300), and
  ``test_empty_set_answers_the_empty_view_and_none_is_unconstrained``
  (`GQ-04` at docs/GRAPH_QUERY_SEMANTICS.md:98).
* **D-03 (operators declare pushability)** — the read-intent section at the
  bottom of this file: ``test_pushability_matrix_is_three_pushable_one_not``
  (the Pitfall-9 pin: exactly three shipped operators return a fragment and
  ``SimilaritySelect.read_intent()`` is ``None``),
  ``test_pushed_intent_answers_what_apply_computes`` (the named
  intent/apply-divergence hazard as a standing per-operator property), and
  ``test_the_segment_answer_is_a_fixed_point_of_its_own_operator``
  (`GQ-19` at docs/GRAPH_QUERY_SEMANTICS.md:356 executable at the operator
  tier, with and without ``allowed_entities`` — the property the engine's
  per-segment re-application rests on).

Strategy discipline inherited from ``tests/properties/strategies.py``: the
shapes come from the ontology fixtures, the values from the fixture YAML —
no entity class, no classification, no bundle version and no relationship
type is written in this file.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ccf.contracts.canonical import canonical_bytes, canonical_timestamp
from ccf.contracts.claims import LineageEntry
from ccf.graph.fallback import answer
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphView,
    QueryFragment,
    RelationshipRecord,
    TraversalSpec,
)
from ccf.graph.reader import Row, materialize_view
from ccf.operators.base import (
    Operator,
    OperatorCategory,
    OperatorOutput,
    OperatorParameters,
    OperatorProvenance,
    mint_provenance,
    read_intent_of,
)
from ccf.operators.categories import SimilaritySelect
from ccf.operators.planner import build_operator_plan
from ccf.operators.registry import OperatorRegistry
from ccf.signal.envelope import SourceIdentity

from tests.properties.strategies import (
    BOUNDARY,
    CLASSIFICATION_ATTRIBUTE,
    CONTROL,
    ENTITY_POOL,
    GENERATION,
    INSTANTS,
    RELATIONSHIP_RULES,
    TENANT,
    _entity_record,
    _relationship_record,
    banking_graph_states,
    shipped_operators,
)

pytestmark = pytest.mark.conformance

# --- fixture-derived vocabulary (no domain literals in this file) -----------

PERMITTED_BUNDLE: str = GENERATION["permitted_policy_bundle_version"]
PERMITTED_CLASSIFICATIONS: tuple[str, ...] = tuple(
    CONTROL["operator_parameters"]["policy"]["permitted_classifications"]
)
PERMITTED_CLASSIFICATION: str = PERMITTED_CLASSIFICATIONS[0]
EXCLUDED_CLASSIFICATION: str = next(
    value
    for value in GENERATION["classifications"]
    if value and value not in PERMITTED_CLASSIFICATIONS
)
SYSTEM: str = GENERATION["source_systems"][0]
SECOND_SYSTEM: str = GENERATION["source_systems"][-1]

SEED_CLASSES: frozenset[str] = frozenset(
    CONTROL["operator_parameters"]["traversal"]["seed_entity_classes"]
)
RELATIONSHIP_TYPES: frozenset[str] = frozenset(
    CONTROL["operator_parameters"]["traversal"]["relationship_types"]
)
ALL_URIS: tuple[str, ...] = tuple(
    uri for uris in ENTITY_POOL.values() for uri in uris
)
EARLY, ON_BOUNDARY, LATE = INSTANTS

#: The policy family, whole (GQ-02), from the Control Plane fixture.
POLICY_FAMILY: dict[str, object] = {
    "permitted_policy_bundle_versions": frozenset({PERMITTED_BUNDLE}),
    "classification_attribute_by_class": dict(CLASSIFICATION_ATTRIBUTE),
    "permitted_classifications": frozenset(PERMITTED_CLASSIFICATIONS),
}


def _traverse(depth: int) -> TraversalSpec:
    """The fixture-declared traverse family at ``depth`` hops."""
    return TraversalSpec(
        seed_entity_classes=SEED_CLASSES,
        relationship_types=RELATIONSHIP_TYPES,
        depth_limit=depth,
    )


def _frozen(
    entities: Sequence[EntityRecord],
    relationships: Sequence[RelationshipRecord],
) -> GraphView:
    """Freeze an answer for canonical-bytes comparison (GQ-22 ordering)."""
    return GraphView(
        tenant_id=TENANT,
        as_of=BOUNDARY,
        entities=tuple(sorted(entities, key=lambda r: r.claim.entity_uri)),
        relationships=tuple(
            sorted(relationships, key=lambda r: r.relationship_key)
        ),
    )


def _survives(record: EntityRecord | RelationshipRecord) -> bool:
    """The as-of predicate, restated independently as the test's oracle."""
    if record.claim.observed_at > BOUNDARY:
        return False
    return record.superseded_at is None or record.superseded_at > BOUNDARY


# --- the seed - intermediate - target chain, from fixture vocabulary --------


def _chain_rules() -> tuple[tuple[str, str, str], tuple[str, str, str]]:
    """Two ontology relationship rules sharing an object class.

    Yields the two typed edges of a two-hop undirected chain
    ``seed -[type_a]- intermediate -[type_b]- target`` where the seed and
    target classes differ, without naming any class or type in test code.
    """
    for rule_a in RELATIONSHIP_RULES:
        for rule_b in RELATIONSHIP_RULES:
            if rule_a is rule_b:
                continue
            if (
                rule_a[2] == rule_b[2]
                and rule_a[1] != rule_b[1]
                and rule_a[1] in SEED_CLASSES
            ):
                return rule_a, rule_b
    raise AssertionError("the ontology fixture no longer offers a two-hop chain")


_RULE_A, _RULE_B = _chain_rules()
SEED_CLASS, MID_CLASS, TARGET_CLASS = _RULE_A[1], _RULE_A[2], _RULE_B[1]
SEED_URI = ENTITY_POOL[SEED_CLASS][0]
MID_URI = ENTITY_POOL[MID_CLASS][0]
TARGET_URI = ENTITY_POOL[TARGET_CLASS][0]
CHAIN_TRAVERSE = TraversalSpec(
    seed_entity_classes=frozenset({SEED_CLASS}),
    relationship_types=frozenset({_RULE_A[0], _RULE_B[0]}),
    depth_limit=2,
)


def _chain(
    *, mid_classification: str
) -> tuple[tuple[EntityRecord, ...], tuple[RelationshipRecord, ...]]:
    """Build the seed - intermediate - target chain with a chosen middle."""

    def entity(uri: str, entity_class: str, classification: str) -> EntityRecord:
        return _entity_record(
            entity_uri=uri,
            entity_class=entity_class,
            classification=classification,
            policy_bundle_version=PERMITTED_BUNDLE,
            observed_at=EARLY,
            valid_from=EARLY,
            valid_to=None,
            superseded_at=None,
            system_id=SYSTEM,
        )

    def edge(
        relationship_type: str, subject_uri: str, object_uri: str
    ) -> RelationshipRecord:
        return _relationship_record(
            relationship_type=relationship_type,
            subject_uri=subject_uri,
            object_uri=object_uri,
            policy_bundle_version=PERMITTED_BUNDLE,
            observed_at=EARLY,
            valid_from=EARLY,
            valid_to=None,
            superseded_at=None,
            system_id=SYSTEM,
        )

    entities = (
        entity(SEED_URI, SEED_CLASS, PERMITTED_CLASSIFICATION),
        entity(MID_URI, MID_CLASS, mid_classification),
        entity(TARGET_URI, TARGET_CLASS, PERMITTED_CLASSIFICATION),
    )
    relationships = (
        edge(_RULE_A[0], SEED_URI, MID_URI),
        edge(_RULE_B[0], TARGET_URI, MID_URI),
    )
    return entities, relationships


# --- INV-CH7-14: the bitemporal cut ----------------------------------------


@given(view=banking_graph_states(), boundary=st.sampled_from(INSTANTS))
def test_late_observed_claims_never_appear(
    view: GraphView, boundary: object
) -> None:
    """A claim observed after ``q.as_of`` is absent from every answer."""
    q = GraphQuery(tenant_id=TENANT, as_of=boundary)  # type: ignore[arg-type]
    entities, relationships = answer(
        view.entities, view.relationships, query=q
    )
    for record in (*entities, *relationships):
        assert record.claim.observed_at <= q.as_of


@given(view=banking_graph_states(), boundary=st.sampled_from(INSTANTS))
def test_early_superseded_claims_never_appear(
    view: GraphView, boundary: object
) -> None:
    """Superseded at-or-before the boundary: absent. After it: still current.

    The completeness half is the INV-CH7-14 sentence people forget: a
    supersession minted *after* ``q.as_of`` renders as current, so every
    as-of-surviving input record — future-superseded ones included — is in
    the degenerate answer, exactly.
    """
    q = GraphQuery(tenant_id=TENANT, as_of=boundary)  # type: ignore[arg-type]
    entities, relationships = answer(
        view.entities, view.relationships, query=q
    )
    for record in (*entities, *relationships):
        assert record.superseded_at is None or record.superseded_at > q.as_of

    surviving_entities = {
        record.claim_id
        for record in view.entities
        if record.claim.observed_at <= q.as_of
        and (record.superseded_at is None or record.superseded_at > q.as_of)
    }
    surviving_edges = {
        (record.relationship_key, record.claim_id)
        for record in view.relationships
        if record.claim.observed_at <= q.as_of
        and (record.superseded_at is None or record.superseded_at > q.as_of)
    }
    assert {record.claim_id for record in entities} == surviving_entities
    assert {
        (record.relationship_key, record.claim_id) for record in relationships
    } == surviving_edges


def test_lineage_at_the_boundary() -> None:
    """L at the boundary, through the production path (GQ-12).

    Rows materialize through :func:`materialize_view` at the boundary and
    the fallback answers the degenerate question over the result — the
    exact production sequence of ``BaseGraphReader.query``. The answering
    record's lineage carries no entry observed after ``q.as_of``, and the
    supersession minted after ``q.as_of`` renders as current
    (``superseded_by``/``superseded_at`` of ``(None, None)``).
    """
    base = _entity_record(
        entity_uri=SEED_URI,
        entity_class=SEED_CLASS,
        classification=PERMITTED_CLASSIFICATION,
        policy_bundle_version=PERMITTED_BUNDLE,
        observed_at=EARLY,
        valid_from=EARLY,
        valid_to=None,
        superseded_at=None,
        system_id=SYSTEM,
    )
    early_entry = LineageEntry(
        source=SourceIdentity(system_id=SYSTEM),
        envelope_id=f"{SEED_URI}@{EARLY.isoformat()}",
        observed_at=EARLY,
    )
    late_entry = LineageEntry(
        source=SourceIdentity(system_id=SECOND_SYSTEM),
        envelope_id=f"{SEED_URI}@{LATE.isoformat()}",
        observed_at=LATE,
    )
    entity_row = {
        "entity_uri": base.claim.entity_uri,
        "claim_id": base.claim_id,
        "claim_json": base.claim.model_dump_json(),
        "policy_bundle_version": base.policy_bundle_version,
        # Superseded after the boundary: current in the answer.
        "superseded_by": f"{base.claim_id}:successor",
        "superseded_at": canonical_timestamp(LATE),
    }
    lineage_index = {
        base.claim_id: (
            {"entry_json": early_entry.model_dump_json()},
            {"entry_json": late_entry.model_dump_json()},
        )
    }

    def rows_for(kind: str, node_key: str, claim_id: str) -> Sequence[Row]:
        return lineage_index.get(claim_id, ())

    view = materialize_view(
        entity_rows=(entity_row,),
        relationship_rows=(),
        tenant_id=TENANT,
        as_of=ON_BOUNDARY,
        lineage_rows_for=rows_for,
    )
    entities, _ = answer(
        view.entities,
        view.relationships,
        query=GraphQuery(tenant_id=TENANT, as_of=ON_BOUNDARY),
    )
    (record,) = entities
    assert record.claim.lineage == frozenset({early_entry})
    assert record.superseded_by is None
    assert record.superseded_at is None


# --- INV-CH7-23: composition preservation ----------------------------------


@given(view=banking_graph_states())
def test_family_composition_is_order_independent(view: GraphView) -> None:
    """``answer(policy+temporal)`` == the two single-family applications.

    In either order, on canonical bytes — the family predicates compose
    exactly as the operator algebra they mirror (``(A o B)(G) = A(B(G))``),
    which is what entitles the engine to split a plan into segments without
    changing the answer.
    """
    both = GraphQuery(
        tenant_id=TENANT,
        as_of=BOUNDARY,
        require_valid_at_boundary=True,
        **POLICY_FAMILY,  # type: ignore[arg-type]
    )
    policy_only = GraphQuery(
        tenant_id=TENANT,
        as_of=BOUNDARY,
        **POLICY_FAMILY,  # type: ignore[arg-type]
    )
    temporal_only = GraphQuery(
        tenant_id=TENANT, as_of=BOUNDARY, require_valid_at_boundary=True
    )
    combined = answer(view.entities, view.relationships, query=both)
    policy_then_temporal = answer(
        *answer(view.entities, view.relationships, query=policy_only),
        query=temporal_only,
    )
    temporal_then_policy = answer(
        *answer(view.entities, view.relationships, query=temporal_only),
        query=policy_only,
    )
    combined_bytes = canonical_bytes(_frozen(*combined))
    assert combined_bytes == canonical_bytes(_frozen(*policy_then_temporal))
    assert combined_bytes == canonical_bytes(_frozen(*temporal_then_policy))


@given(view=banking_graph_states())
def test_repeat_answers_are_deterministic(view: GraphView) -> None:
    """The same question over the same records answers the same bytes."""
    q = GraphQuery(
        tenant_id=TENANT,
        as_of=BOUNDARY,
        require_valid_at_boundary=True,
        traverse=_traverse(
            CONTROL["operator_parameters"]["traversal"]["depth_limit"]
        ),
        **POLICY_FAMILY,  # type: ignore[arg-type]
    )
    first = answer(view.entities, view.relationships, query=q)
    second = answer(view.entities, view.relationships, query=q)
    assert canonical_bytes(_frozen(*first)) == canonical_bytes(
        _frozen(*second)
    )


# --- INV-CH7-24: bounded traversal expansion --------------------------------


@given(view=banking_graph_states())
def test_depth_zero_yields_exactly_the_walk_starts(view: GraphView) -> None:
    """``depth_limit=0`` answers the in-scope seed-class entities, exactly."""
    q = GraphQuery(tenant_id=TENANT, as_of=BOUNDARY, traverse=_traverse(0))
    entities, _ = answer(view.entities, view.relationships, query=q)
    expected = {
        record.claim.entity_uri
        for record in view.entities
        if _survives(record) and record.claim.entity_class in SEED_CLASSES
    }
    assert {record.claim.entity_uri for record in entities} == expected


@given(view=banking_graph_states(), depth=st.integers(min_value=0, max_value=2))
def test_depth_answers_are_monotone(view: GraphView, depth: int) -> None:
    """The depth-N answer is a subset of the depth-N+1 answer."""
    smaller, _ = answer(
        view.entities,
        view.relationships,
        query=GraphQuery(
            tenant_id=TENANT, as_of=BOUNDARY, traverse=_traverse(depth)
        ),
    )
    larger, _ = answer(
        view.entities,
        view.relationships,
        query=GraphQuery(
            tenant_id=TENANT, as_of=BOUNDARY, traverse=_traverse(depth + 1)
        ),
    )
    assert {record.claim.entity_uri for record in smaller} <= {
        record.claim.entity_uri for record in larger
    }


@given(view=banking_graph_states(), depth=st.integers(min_value=0, max_value=3))
def test_no_node_beyond_the_depth_bound_appears(
    view: GraphView, depth: int
) -> None:
    """No answered node lies beyond N admissible hops from every walk start.

    The distance computation here is independent of the fallback's own
    BFS: hop distances are derived in the test over the as-of-surviving
    typed edges among surviving entities, and every answered entity must
    sit at a distance the bound admits.
    """
    q = GraphQuery(
        tenant_id=TENANT, as_of=BOUNDARY, traverse=_traverse(depth)
    )
    entities, _ = answer(view.entities, view.relationships, query=q)

    survivors = {
        record.claim.entity_uri
        for record in view.entities
        if _survives(record)
    }
    adjacency: dict[str, set[str]] = {}
    for edge in view.relationships:
        if edge.claim.relationship_type not in RELATIONSHIP_TYPES:
            continue
        if not _survives(edge):
            continue
        subject, obj = edge.claim.subject_uri, edge.claim.object_uri
        if subject not in survivors or obj not in survivors:
            continue
        adjacency.setdefault(subject, set()).add(obj)
        adjacency.setdefault(obj, set()).add(subject)

    starts = {
        record.claim.entity_uri
        for record in view.entities
        if _survives(record) and record.claim.entity_class in SEED_CLASSES
    }
    distance = {uri: 0 for uri in starts}
    frontier = set(starts)
    hops = 0
    while frontier:
        hops += 1
        frontier = {
            neighbour
            for node in frontier
            for neighbour in adjacency.get(node, ())
            if neighbour not in distance
        }
        for neighbour in frontier:
            distance[neighbour] = hops

    for record in entities:
        assert distance.get(record.claim.entity_uri, depth + 1) <= depth


# --- INV-CH7-26 / INV-CH7-40: structural absence and hop admissibility ------


def test_policy_excluded_state_is_structurally_absent_and_unreachable_through() -> (
    None
):
    """The seed - excluded - target chain: absent AND unreachable-through.

    INV-CH7-26: policy-excluded state is structurally absent from the
    answer, not hidden by a predicate. INV-CH7-40 (`GQ-13` at
    docs/GRAPH_QUERY_SEMANTICS.md:261): a path through an excluded node
    does not exist, so the admissible target two hops away is NOT reached
    — applying the predicates to the result set instead of to every hop is
    the named information-disclosure defect of this seam. The control leg
    proves the test would catch the leak: with an admissible intermediate,
    the same walk reaches the target.
    """
    excluded_entities, excluded_edges = _chain(
        mid_classification=EXCLUDED_CLASSIFICATION
    )
    q = GraphQuery(
        tenant_id=TENANT,
        as_of=BOUNDARY,
        traverse=CHAIN_TRAVERSE,
        **POLICY_FAMILY,  # type: ignore[arg-type]
    )
    entities, relationships = answer(excluded_entities, excluded_edges, query=q)
    answered = {record.claim.entity_uri for record in entities}
    assert MID_URI not in answered, "excluded state must be structurally absent"
    assert TARGET_URI not in answered, "a path through an excluded node exists"
    assert answered == {SEED_URI}
    assert relationships == ()

    control_entities, control_edges = _chain(
        mid_classification=PERMITTED_CLASSIFICATION
    )
    control, _ = answer(control_entities, control_edges, query=q)
    assert {record.claim.entity_uri for record in control} == {
        SEED_URI,
        MID_URI,
        TARGET_URI,
    }


# --- the D-IMPL-87 allowed_entities pins (filed under INV-CH7-26/-40) -------


@given(
    view=banking_graph_states(),
    allowed=st.frozensets(st.sampled_from(ALL_URIS)),
)
def test_allowed_entities_answers_are_contained_in_the_set(
    view: GraphView, allowed: frozenset[str]
) -> None:
    """Containment and the induced subgraph (`GQ-15`, `GQ-16`).

    Every entity in an ``allowed_entities``-constrained answer is a member
    of the set; every relationship's two endpoints are members — with and
    without a walk.
    """
    for q in (
        GraphQuery(tenant_id=TENANT, as_of=BOUNDARY, allowed_entities=allowed),
        GraphQuery(
            tenant_id=TENANT,
            as_of=BOUNDARY,
            allowed_entities=allowed,
            traverse=_traverse(
                CONTROL["operator_parameters"]["traversal"]["depth_limit"]
            ),
        ),
    ):
        entities, relationships = answer(
            view.entities, view.relationships, query=q
        )
        for record in entities:
            assert record.claim.entity_uri in allowed
        for edge in relationships:
            assert edge.claim.subject_uri in allowed
            assert edge.claim.object_uri in allowed


def test_resurrection_shape_does_not_reach_the_target() -> None:
    """The D-IMPL-87 pin: the walk cannot cross outside the set to pass through.

    Seed and target IN the set, intermediate OUT of it — everything policy-
    admissible, so only the survivor-set constraint stands between the walk
    and the target. Under the uniform rule (`GQ-15` at
    docs/GRAPH_QUERY_SEMANTICS.md:300) the out-of-set intermediate is not a
    hop, so the target is provably NOT re-reached — the entity-resurrection
    defect, closed at the oracle tier. The control leg (intermediate
    in-set) proves the walk does reach the target when the set admits the
    path.
    """
    entities, relationships = _chain(
        mid_classification=PERMITTED_CLASSIFICATION
    )
    resurrection = GraphQuery(
        tenant_id=TENANT,
        as_of=BOUNDARY,
        allowed_entities=frozenset({SEED_URI, TARGET_URI}),
        traverse=CHAIN_TRAVERSE,
    )
    answered_entities, answered_edges = answer(
        entities, relationships, query=resurrection
    )
    answered = {record.claim.entity_uri for record in answered_entities}
    assert TARGET_URI not in answered, "the walk crossed outside the set"
    assert answered == {SEED_URI}
    assert answered_edges == ()

    control = GraphQuery(
        tenant_id=TENANT,
        as_of=BOUNDARY,
        allowed_entities=frozenset({SEED_URI, MID_URI, TARGET_URI}),
        traverse=CHAIN_TRAVERSE,
    )
    control_entities, _ = answer(entities, relationships, query=control)
    assert {record.claim.entity_uri for record in control_entities} == {
        SEED_URI,
        MID_URI,
        TARGET_URI,
    }


@given(view=banking_graph_states())
def test_empty_set_answers_the_empty_view_and_none_is_unconstrained(
    view: GraphView,
) -> None:
    """The empty set and ``None`` are different facts (`GQ-04`).

    An empty ``allowed_entities`` answers the empty view; ``None`` applies
    no restriction and answers byte-for-byte the unconstrained question.
    """
    empty = answer(
        view.entities,
        view.relationships,
        query=GraphQuery(
            tenant_id=TENANT, as_of=BOUNDARY, allowed_entities=frozenset()
        ),
    )
    assert empty == ((), ())

    unconstrained_none = answer(
        view.entities,
        view.relationships,
        query=GraphQuery(
            tenant_id=TENANT, as_of=BOUNDARY, allowed_entities=None
        ),
    )
    degenerate = answer(
        view.entities,
        view.relationships,
        query=GraphQuery(tenant_id=TENANT, as_of=BOUNDARY),
    )
    assert canonical_bytes(_frozen(*unconstrained_none)) == canonical_bytes(
        _frozen(*degenerate)
    )


# --- D-03: read_intent — the matrix pin, equivalence, and the fixed point ---


def _pushable_shipped() -> tuple[Operator, ...]:
    """The shipped operators that declare a fragment, in canonical order."""
    return tuple(
        registration.operator
        for registration in shipped_operators().registrations()
        if read_intent_of(registration.operator) is not None
    )


def _fragment_query(
    fragment: QueryFragment, *, allowed: frozenset[str] | None = None
) -> GraphQuery:
    """Render one fragment as its segment query — the test's own compilation.

    Deliberately independent of ``ccf.projection.segmentation`` (the
    production compiler): the property audits what a fragment *means*, so its
    rendering must not be the code under audit. Field-wise copy per `GQ-06`
    at docs/GRAPH_QUERY_SEMANTICS.md:132; ``allowed`` is the engine-authored
    survivor set of `GQ-04` at docs/GRAPH_QUERY_SEMANTICS.md:98.
    """
    fields: dict[str, object] = {"tenant_id": TENANT, "as_of": BOUNDARY}
    if fragment.permitted_policy_bundle_versions is not None:
        fields["permitted_policy_bundle_versions"] = (
            fragment.permitted_policy_bundle_versions
        )
        fields["classification_attribute_by_class"] = (
            fragment.classification_attribute_by_class
        )
        fields["permitted_classifications"] = fragment.permitted_classifications
    if fragment.require_valid_at_boundary is not None:
        fields["require_valid_at_boundary"] = fragment.require_valid_at_boundary
    if fragment.traverse is not None:
        fields["traverse"] = fragment.traverse
    if allowed is not None:
        fields["allowed_entities"] = allowed
    return GraphQuery(**fields)  # type: ignore[arg-type]


def _answer_form(view: GraphView) -> GraphView:
    """The everything-answer in answer form — endpoint-closed (`GQ-16`).

    Every view an operator receives mid-plan is an *answer*: a pushed
    segment's answer is endpoint-closed because it is constrained (`GQ-16` at
    docs/GRAPH_QUERY_SEMANTICS.md:316), and every in-process operator's
    output is closed by ``_substitute`` (INV-CH7-40). The one unclosed view
    in the system — the raw degenerate everything-answer, exempt for
    pre-seam byte-compatibility (`GQ-05` at
    docs/GRAPH_QUERY_SEMANTICS.md:122) — is never an operator's input after
    the first segment compiles at least one family. So the per-operator
    equivalence feeds ``apply()`` the answer *form*: the everything-answer
    under a vacuous ``allowed_entities`` covering the whole drawable pool,
    which restricts nothing and closes edges through the production path.
    """
    return _frozen(
        *answer(
            view.entities,
            view.relationships,
            query=GraphQuery(
                tenant_id=TENANT,
                as_of=BOUNDARY,
                allowed_entities=frozenset(ALL_URIS),
            ),
        )
    )


def test_pushability_matrix_is_three_pushable_one_not() -> None:
    """The D-03 matrix pin (RESEARCH Pitfall 9): 3 pushable, 1 not, by name.

    Exactly three shipped operators return a fragment; SimilaritySelect
    returns ``None``, full stop — it consults an injected
    ``SimilarityIndexProtocol`` the substrate does not hold, and making it
    pushable is a Deferred-Ideas decision reversal, not an optimization. A
    drive-by change to any of the four answers fails this named test.
    """
    registry = shipped_operators()
    intent_by_category = {
        registration.category: read_intent_of(registration.operator)
        for registration in registry.registrations()
    }
    assert intent_by_category["policy"] is not None
    assert intent_by_category["temporal"] is not None
    assert intent_by_category["traversal"] is not None
    assert intent_by_category["similarity"] is None
    assert (
        sum(1 for intent in intent_by_category.values() if intent is not None)
        == 3
    )

    (similarity_registration,) = registry.by_category("similarity")
    similarity = similarity_registration.operator
    assert isinstance(similarity, SimilaritySelect)
    assert similarity.read_intent() is None

    # The three fragments carry exactly the family their operator applies.
    policy_fragment = intent_by_category["policy"]
    assert policy_fragment is not None
    assert policy_fragment.permitted_policy_bundle_versions is not None
    temporal_fragment = intent_by_category["temporal"]
    assert temporal_fragment is not None
    assert temporal_fragment.require_valid_at_boundary is not None
    traversal_fragment = intent_by_category["traversal"]
    assert traversal_fragment is not None
    assert traversal_fragment.traverse is not None


@given(view=banking_graph_states())
def test_pushed_intent_answers_what_apply_computes(view: GraphView) -> None:
    """The D-03 equivalence: ``apply(full_view) == pushed(intent)``, per operator.

    The named hazard of the read-intent seam — ``read_intent()`` and
    ``apply()`` diverging returns silently different rows — as a standing
    property: over corpus-generated states, applying the operator in-process
    over the full answer-form view produces byte-for-byte the fallback's
    answer to the fragment-derived query over the same records. Weaker
    pushed predicates are the access-control regression this guards
    (T-15.2-04).
    """
    full_view = _answer_form(view)
    for operator in _pushable_shipped():
        fragment = read_intent_of(operator)
        assert fragment is not None
        applied = operator.apply(
            view=full_view,
            tenant_id=TENANT,
            temporal_boundary=BOUNDARY,
            upstream=(),
        ).view
        pushed = _frozen(
            *answer(
                view.entities,
                view.relationships,
                query=_fragment_query(fragment),
            )
        )
        assert canonical_bytes(applied) == canonical_bytes(pushed), (
            f"{operator.key}: declared intent and applied behavior diverge"
        )


@given(
    view=banking_graph_states(),
    allowed=st.none() | st.frozensets(st.sampled_from(ALL_URIS)),
)
def test_the_segment_answer_is_a_fixed_point_of_its_own_operator(
    view: GraphView, allowed: frozenset[str] | None
) -> None:
    """`GQ-19` at docs/GRAPH_QUERY_SEMANTICS.md:356, at the operator tier.

    The answer to a fragment-derived query is a fixed point of the operator
    that declared the fragment: re-applying it to its own answer returns the
    answer, bit for bit — INCLUDING under an engine-authored
    ``allowed_entities`` constraint (`GQ-15` at
    docs/GRAPH_QUERY_SEMANTICS.md:300), because membership is preserved
    under subsetting. This is the property the engine's per-segment
    re-application rests on (T-15.2-24), tested where a failure is cheapest
    to localize.
    """
    for operator in _pushable_shipped():
        fragment = read_intent_of(operator)
        assert fragment is not None
        answered = _frozen(
            *answer(
                view.entities,
                view.relationships,
                query=_fragment_query(fragment, allowed=allowed),
            )
        )
        reapplied = operator.apply(
            view=answered,
            tenant_id=TENANT,
            temporal_boundary=BOUNDARY,
            upstream=(),
        ).view
        assert canonical_bytes(reapplied) == canonical_bytes(answered), (
            f"{operator.key}: the segment answer is not a fixed point"
        )


class _OpaqueOperator:
    """A third-party operator that never heard of pushdown (D-03).

    Satisfies the ``Operator`` Protocol exactly as it stood before
    ``read_intent`` existed: no ``read_intent`` method at all. Identity over
    the view, provenance minted through the production helper.
    """

    key = "custom.opaque"
    category: OperatorCategory = "temporal"

    @property
    def parameters(self) -> OperatorParameters:
        return OperatorParameters()

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: object,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        return OperatorOutput(
            view=view, provenance=mint_provenance(self, upstream=upstream)
        )


def test_an_operator_without_read_intent_still_registers_and_executes() -> None:
    """The capability is optional: a pre-D-03 operator is untouched.

    It registers, resolves through the planner, and executes — and
    ``read_intent_of`` answers ``None`` for it rather than raising, which is
    what keeps the segment split total over plans containing third-party
    operators.
    """
    registry = OperatorRegistry()
    registry.register(_OpaqueOperator())
    plan = build_operator_plan(
        registry=registry, required_operators=(_OpaqueOperator.key,)
    )
    (operator,) = plan.operators
    assert read_intent_of(operator) is None

    empty = GraphView(tenant_id=TENANT, as_of=BOUNDARY)
    output = operator.apply(
        view=empty, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    assert output.view == empty
    assert output.provenance.operator_key == _OpaqueOperator.key


def test_an_operator_with_read_intent_is_seen_by_read_intent_of() -> None:
    """The capability is honored: a declared fragment reaches the seam."""
    declared_require = CONTROL["operator_parameters"]["temporal"][
        "require_valid_at_boundary"
    ]

    class _DeclaredOperator(_OpaqueOperator):
        key = "custom.declared"

        def read_intent(self) -> QueryFragment:
            return QueryFragment(require_valid_at_boundary=declared_require)

    assert read_intent_of(_DeclaredOperator()) == QueryFragment(
        require_valid_at_boundary=declared_require
    )
