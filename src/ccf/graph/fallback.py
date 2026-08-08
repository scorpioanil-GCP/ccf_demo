"""The reference implementation of the graph query semantics prose.

Whitepaper §7.3 (the Context Graph as queryable persisted state) and §7.4
(the operator categories whose semantics a pushed query renders). The
normative vocabulary is ``docs/GRAPH_QUERY_SEMANTICS.md`` (semantics version
1.0.1): the prose decides; this module implements it clause-for-clause; the
adapters agree with it under the differential suite (`GQ-31` at
docs/GRAPH_QUERY_SEMANTICS.md:573); and the property suite audits this module
against the named invariants — so the oracle is answerable to something it
does not define (D-05).

**This is the one BFS every adapter degrades to.** A conformant adapter
answers any well-formed :class:`~ccf.graph.protocols.GraphQuery` (`GQ-29` at
docs/GRAPH_QUERY_SEMANTICS.md:554), degrading internally to scan-and-filter
where it holds no native translation (D-04) — and "scan-and-filter" means
*this module*, so no second traversal implementation exists in the tree and
per-substrate divergence has nowhere to live.

Purity, by construction: pure functions over ``(entities, relationships,
query)`` returning surviving records. No I/O, no clock reads (``as_of``
arrives as data inside the frozen query — `GQ-01` at
docs/GRAPH_QUERY_SEMANTICS.md:48), no backend, no transport, and no
``Operator`` type: adapters and the fallback never see an Operator (D-02) —
the query *is* the rendered intent.

Ordering and freezing are deliberately absent here: they belong to the
interface, never to an answerer (`GQ-22` at
docs/GRAPH_QUERY_SEMANTICS.md:461) — the materialization core in
:mod:`ccf.graph.reader` owns both.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    RelationshipRecord,
    TraversalSpec,
)

__ccf_mode__ = "algorithmic"

__all__ = ["answer"]


def _survives_as_of(
    *,
    observed_at: datetime,
    superseded_at: datetime | None,
    boundary: datetime,
) -> bool:
    """The as-of cut — `GQ-07` at docs/GRAPH_QUERY_SEMANTICS.md:148.

    A record is in scope iff ``observed_at <= as_of`` and it was not
    superseded at or before ``as_of``. This is INV-CH7-14 rendered at the
    query tier, matching cuts 1–2 of
    ``src/ccf/operators/categories.py::TemporalAsOf`` exactly: claims the
    fabric had not yet observed at the boundary are absent, and claims
    superseded *after* the boundary are still current — no future
    information leaks into an as-of answer.
    """
    if observed_at > boundary:
        return False
    return superseded_at is None or superseded_at > boundary


def _valid_at_boundary(
    *,
    valid_from: datetime,
    valid_to: datetime | None,
    boundary: datetime,
) -> bool:
    """The validity-window rule — `GQ-09` at docs/GRAPH_QUERY_SEMANTICS.md:185.

    When the temporal family requires validity at the boundary, a record
    additionally survives only if its valid interval covers it — cut 3 of
    ``src/ccf/operators/categories.py::TemporalAsOf`` (INV-CH7-25). "What
    did we know?" and "what was true?" are the two axes of the bitemporal
    model; this predicate is the second one, applied only when declared.
    """
    if valid_from > boundary:
        return False
    return valid_to is None or valid_to > boundary


def _admissible_entity(record: EntityRecord, *, query: GraphQuery) -> bool:
    """Policy admissibility — `GQ-08` at docs/GRAPH_QUERY_SEMANTICS.md:163.

    All three cuts must hold, exactly as
    ``src/ccf/operators/categories.py::PolicyFilter`` computes in-process
    (INV-CH7-26): the record's policy bundle version is permitted; its
    entity class has a declared classification attribute — a class with no
    declared attribute is inadmissible; and the value of that attribute on
    the entity is a permitted classification — an entity carrying no value
    for its class's attribute is inadmissible. The fabric does not admit
    state it cannot prove is admissible.

    Callable only when the policy family is present; the contract
    guarantees a present family carries all of its fields (`GQ-02` at
    docs/GRAPH_QUERY_SEMANTICS.md:64), which the assertions render as type
    narrowing rather than runtime re-litigation.
    """
    permitted = query.permitted_policy_bundle_versions
    attribute_by_class = query.classification_attribute_by_class
    classifications = query.permitted_classifications
    assert permitted is not None  # noqa: S101 - GQ-02 whole-family guarantee
    assert attribute_by_class is not None  # noqa: S101
    assert classifications is not None  # noqa: S101
    if record.policy_bundle_version not in permitted:
        return False
    attribute = attribute_by_class.get(record.claim.entity_class)
    if attribute is None:
        return False
    return record.claim.attributes.get(attribute) in classifications


def _admissible_relationship(
    record: RelationshipRecord, *, query: GraphQuery
) -> bool:
    """Relationship policy admissibility — `GQ-08` at docs/GRAPH_QUERY_SEMANTICS.md:163.

    A relationship is admissible under the policy family iff its policy
    bundle version is permitted. Relationships carry no classification
    check of their own; their exposure is governed by endpoint survival
    under the substitution rule (`GQ-16` at
    docs/GRAPH_QUERY_SEMANTICS.md:316).
    """
    permitted = query.permitted_policy_bundle_versions
    assert permitted is not None  # noqa: S101 - GQ-02 whole-family guarantee
    return record.policy_bundle_version in permitted


def _restricted_universe(
    entities: Sequence[EntityRecord],
    *,
    allowed: frozenset[str] | None,
) -> tuple[EntityRecord, ...]:
    """The uniform rule's set intersection — `GQ-15` at docs/GRAPH_QUERY_SEMANTICS.md:300.

    When ``allowed_entities`` is a non-empty set, the entity universe is
    restricted to members of the set **before any family evaluates**
    (D-IMPL-87): filters select within the set, and the walk below can
    therefore never reach outside it — this ordering is what closes the
    entity-resurrection defect. The three values are three different facts
    (`GQ-04` at docs/GRAPH_QUERY_SEMANTICS.md:98): ``None`` applies no
    restriction; the empty set answers the empty view; a non-empty set is
    the survivor constraint on the whole answer.
    """
    if allowed is None:
        return tuple(entities)
    return tuple(
        record for record in entities if record.claim.entity_uri in allowed
    )


def _endpoint_closure(
    entities: tuple[EntityRecord, ...],
    relationships: Sequence[RelationshipRecord],
) -> tuple[RelationshipRecord, ...]:
    """No-leak-by-absence — `GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316.

    A relationship is kept only when **both** endpoints are among the
    surviving entities, exactly as
    ``src/ccf/operators/categories.py::_substitute`` computes in-process
    (INV-CH7-40): a view retaining an edge to a node the principal may not
    see leaks by absence. Under ``allowed_entities`` this *is* the
    induced-subgraph rule — the surviving universe is already restricted
    to the set, so closure against it closes against the set: an answer is
    a valid graph for its principal, not a row bag.

    Scope: closure applies to **constrained** answers — any predicate
    family present, or ``allowed_entities`` non-``None``. That scoping is
    the prose's, not this module's, as of semantics 1.0.1 (`GQ-35` at
    docs/GRAPH_QUERY_SEMANTICS.md:621, amendment history): the v1.0.0
    wording said "every answer", 15.2-05 found it contradicted `GQ-05`
    and `GQ-21` on the dangling-edge shape and resolved it here, and the
    15.2-14 phase-close audit moved the ruling into the document that is
    supposed to hold it. The reasoning below is why, restated so a reader
    of this function does not have to leave it — its rationale is
    exclusion: an edge to a node the answer *removed* leaks
    that node's existence. The degenerate everything-question excludes
    nothing; its answer is the tenant's full as-of view (`GQ-05` at
    docs/GRAPH_QUERY_SEMANTICS.md:122), in which a persisted first-class
    edge whose endpoint carries no entity claim (INV-CH7-20 — edges are
    never derived joins) is state, not a leak — and `GQ-21` at
    docs/GRAPH_QUERY_SEMANTICS.md:446 pins that answer byte-identical to
    the pre-seam ``as_of()``, which never pruned it.
    """
    surviving = {record.claim.entity_uri for record in entities}
    return tuple(
        edge
        for edge in relationships
        if edge.claim.subject_uri in surviving
        and edge.claim.object_uri in surviving
    )


def _walk(
    entities: tuple[EntityRecord, ...],
    relationships: tuple[RelationshipRecord, ...],
    *,
    traverse: TraversalSpec,
    seeds: frozenset[str] | None,
) -> tuple[tuple[EntityRecord, ...], tuple[RelationshipRecord, ...]]:
    """The bounded typed undirected walk — `GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201.

    Semantics, matching ``src/ccf/operators/categories.py::TraversalNeighborhood``
    (INV-CH7-24): undirected — an edge is crossable in either direction;
    typed — only edges whose type is permitted are crossable, and edges of
    other types are absent from the answer even between reached endpoints;
    seeds are included; ``depth_limit=0`` yields the walk starting points
    only; ``depth_limit=N`` reaches at most N hops.

    Walk starting points are the union of two selections computed over
    in-scope state only (`GQ-11` at docs/GRAPH_QUERY_SEMANTICS.md:221):
    entities of the seed classes, and explicit ``seeds`` intersected with
    the in-scope entities — a URI naming no in-scope entity contributes no
    start. Because the caller hands this function only surviving,
    admissible, in-set state with its edges already endpoint-closed, the
    walk expands over a pruned view: an edge to an excluded or out-of-set
    node is not a hop it can take — hop admissibility per `GQ-13` at
    docs/GRAPH_QUERY_SEMANTICS.md:261 (INV-CH7-40), prune before walking.
    """
    typed = tuple(
        edge
        for edge in relationships
        if edge.claim.relationship_type in traverse.relationship_types
    )
    adjacency: dict[str, set[str]] = {}
    for edge in typed:
        adjacency.setdefault(edge.claim.subject_uri, set()).add(
            edge.claim.object_uri
        )
        adjacency.setdefault(edge.claim.object_uri, set()).add(
            edge.claim.subject_uri
        )

    in_scope = {record.claim.entity_uri for record in entities}
    frontier = {
        record.claim.entity_uri
        for record in entities
        if record.claim.entity_class in traverse.seed_entity_classes
    }
    if seeds is not None:
        frontier |= set(seeds) & in_scope
    reached = set(frontier)
    for _hop in range(traverse.depth_limit):
        frontier = {
            neighbour
            for node in frontier
            for neighbour in adjacency.get(node, ())
            if neighbour not in reached
        }
        if not frontier:
            break
        reached |= frontier

    kept_entities = tuple(
        record for record in entities if record.claim.entity_uri in reached
    )
    kept_edges = tuple(
        edge
        for edge in typed
        if edge.claim.subject_uri in reached and edge.claim.object_uri in reached
    )
    return kept_entities, kept_edges


def answer(
    entities: Sequence[EntityRecord],
    relationships: Sequence[RelationshipRecord],
    *,
    query: GraphQuery,
) -> tuple[tuple[EntityRecord, ...], tuple[RelationshipRecord, ...]]:
    """Answer ``query`` over materialized records — the prose, executable.

    The input contract is `GQ-12` at docs/GRAPH_QUERY_SEMANTICS.md:237: the
    records received here **retain their temporal metadata** —
    ``claim.observed_at``, ``claim.valid_from`` / ``claim.valid_to``, and
    the record's ``superseded_by`` / ``superseded_at`` — and this function
    re-applies the **full** as-of survival predicate over those retained
    fields. The consequence is normative, not incidental: for substrates
    whose row acquisition already applied the as-of cut (the SQL
    ``SELECT_*_AS_OF`` paths), the re-application is an idempotent no-op;
    for sources that cannot pre-filter (a mounted product's verbatim
    payload records), this predicate **is** the as-of enforcement.
    INV-CH7-14 is therefore independently enforceable at this tier and is
    never assumed to have been applied upstream.

    Evaluation order, straight from the clauses:

    1. the ``allowed_entities`` restriction applies before any family
       evaluates — the uniform rule (`GQ-15` at
       docs/GRAPH_QUERY_SEMANTICS.md:300); an empty set answers the empty
       view (`GQ-04` at docs/GRAPH_QUERY_SEMANTICS.md:98);
    2. the as-of cut applies to every answer (`GQ-07` at
       docs/GRAPH_QUERY_SEMANTICS.md:148), and the validity window when
       the temporal family requires it (`GQ-09` at
       docs/GRAPH_QUERY_SEMANTICS.md:185);
    3. policy admissibility when the policy family is present (`GQ-08` at
       docs/GRAPH_QUERY_SEMANTICS.md:163);
    4. on a constrained answer — any family present, or
       ``allowed_entities`` non-``None`` — edges are endpoint-closed
       against the surviving universe (`GQ-16` at
       docs/GRAPH_QUERY_SEMANTICS.md:316) *before* any walk, so an
       excluded or out-of-set node is structurally absent from the walk's
       state (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261); see
       :func:`_endpoint_closure` for why the degenerate answer is exempt;
    5. the traverse family, when present, is the bounded typed undirected
       expansion of `GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201.

    The degenerate query — no families, no seeds, ``allowed_entities``
    ``None`` — returns **all** as-of-surviving records, dangling
    first-class edges included: the everything-question of `GQ-05` at
    docs/GRAPH_QUERY_SEMANTICS.md:122, which is the definition of
    ``as_of()`` (`GQ-21` at docs/GRAPH_QUERY_SEMANTICS.md:446) and
    therefore byte-identical to the pre-seam ``as_of()`` answer. An empty
    answer is an answer, never an error (`GQ-23` at
    docs/GRAPH_QUERY_SEMANTICS.md:474).

    Returns the surviving records unordered and unfrozen: ordering and
    canonical serialization belong to the interface (`GQ-22` at
    docs/GRAPH_QUERY_SEMANTICS.md:461), never to an answerer.
    """
    boundary = query.as_of

    # 1. The uniform rule: restrict before any family evaluates (GQ-15).
    universe = _restricted_universe(
        entities, allowed=query.allowed_entities
    )

    # 2. The as-of cut over retained fields, on every answer (GQ-07/GQ-12).
    surviving_entities = tuple(
        record
        for record in universe
        if _survives_as_of(
            observed_at=record.claim.observed_at,
            superseded_at=record.superseded_at,
            boundary=boundary,
        )
    )
    surviving_edges: tuple[RelationshipRecord, ...] = tuple(
        edge
        for edge in relationships
        if _survives_as_of(
            observed_at=edge.claim.observed_at,
            superseded_at=edge.superseded_at,
            boundary=boundary,
        )
    )

    # ... and the validity window when the temporal family requires it (GQ-09).
    if query.require_valid_at_boundary:
        surviving_entities = tuple(
            record
            for record in surviving_entities
            if _valid_at_boundary(
                valid_from=record.claim.valid_from,
                valid_to=record.claim.valid_to,
                boundary=boundary,
            )
        )
        surviving_edges = tuple(
            edge
            for edge in surviving_edges
            if _valid_at_boundary(
                valid_from=edge.claim.valid_from,
                valid_to=edge.claim.valid_to,
                boundary=boundary,
            )
        )

    # 3. Policy admissibility when the policy family is present (GQ-08).
    if query.permitted_policy_bundle_versions is not None:
        surviving_entities = tuple(
            record
            for record in surviving_entities
            if _admissible_entity(record, query=query)
        )
        surviving_edges = tuple(
            edge
            for edge in surviving_edges
            if _admissible_relationship(edge, query=query)
        )

    # 4. Endpoint closure on constrained answers, before any walk
    #    (GQ-16, GQ-13 prune-before-walk; degenerate exemption per GQ-05/GQ-21).
    constrained = (
        query.allowed_entities is not None
        or query.permitted_policy_bundle_versions is not None
        or query.require_valid_at_boundary is not None
        or query.traverse is not None
    )
    if constrained:
        surviving_edges = _endpoint_closure(surviving_entities, surviving_edges)

    # 5. The traverse family, when present (GQ-10/GQ-11).
    if query.traverse is not None:
        return _walk(
            surviving_entities,
            surviving_edges,
            traverse=query.traverse,
            seeds=query.seeds,
        )
    return surviving_entities, surviving_edges
