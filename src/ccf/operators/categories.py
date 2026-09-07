"""One genuine operator per canonical category — the vertical slice's algebra.

Whitepaper §7.4 (INV-CH7-24 bounded traversal, INV-CH7-25 temporal
reconciliation as a correctness semantic, INV-CH7-26 policy as subgraph
substitution, INV-CH7-27 corpus-scoped similarity); DESIGN.md §2B.1.

These four are minimal in *coverage* and deliberately not minimal in
*behavior*: each one actually removes or reshapes graph state, so a chain of
them is a chain, not four identity functions wearing category names (D-02).
The Traversal category ships a fifth operator under the same category — the
DIRECTED sibling :class:`TraversalDescendants` (ledger row ``24.5-L-06``) —
which is a second shape, not a fifth category (D-IMPL-223): both walks call
one private :func:`_bounded_walk`, so they cannot drift from each other.

Their declared parameter contracts live in :mod:`ccf.operators.params`, they
are registered with their category and parameter schema in
:mod:`ccf.operators.registry`, and :mod:`ccf.operators.planner` is what puts
them in the canonical dependency order.

**Substitution, not filtering.** Every operator here returns a view that is
itself a valid graph for the principal (INV-CH7-40): when an entity is removed,
the edges incident to it go with it. A view retaining an edge to a node the
principal may not see leaks by absence — the reader learns that *something*
was there. Pruning dangling edges is therefore part of the contract, not
tidiness.

Every value these operators act on — policy bundle versions, classification
vocabularies, entity classes, relationship types, thresholds, depth limits —
arrives in a declared parameter set from the Control Plane. This module holds
none of them (CLAUDE.md §11, CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime

from ccf.graph.protocols import (
    EntityRecord,
    GraphView,
    QueryFragment,
    RelationshipRecord,
    TraversalSpec,
)
from ccf.operators.base import (
    Operator,
    OperatorCategory,
    OperatorOutput,
    OperatorProvenance,
    mint_provenance,
)
from ccf.operators.params import (
    PolicyFilterParameters,
    SimilaritySelectParameters,
    TemporalAsOfParameters,
    TraversalDescendantsParameters,
    TraversalNeighborhoodParameters,
)
from ccf.similarity.protocol import SimilarityIndexProtocol

__ccf_mode__ = "algorithmic"

__all__ = [
    "PolicyFilter",
    "PolicyFilterParameters",
    "SimilaritySelect",
    "SimilaritySelectParameters",
    "TemporalAsOf",
    "TemporalAsOfParameters",
    "TraversalDescendants",
    "TraversalDescendantsParameters",
    "TraversalNeighborhood",
    "TraversalNeighborhoodParameters",
]


def _substitute(
    view: GraphView,
    *,
    entities: tuple[EntityRecord, ...],
    relationships: tuple[RelationshipRecord, ...],
) -> GraphView:
    """Return the view containing exactly ``entities`` and the edges among them.

    The pruning step is the no-leak-by-absence guarantee (INV-CH7-40): an edge
    survives only if both of its endpoints did.
    """
    surviving = {record.claim.entity_uri for record in entities}
    kept = tuple(
        edge
        for edge in relationships
        if edge.claim.subject_uri in surviving and edge.claim.object_uri in surviving
    )
    return GraphView(
        tenant_id=view.tenant_id,
        as_of=view.as_of,
        entities=entities,
        relationships=kept,
    )



def _bounded_walk(
    view: GraphView,
    *,
    seed_classes: frozenset[str],
    relationship_types: frozenset[str],
    depth_limit: int,
    admitted: frozenset[str] | None,
    forward: bool,
) -> tuple[tuple[EntityRecord, ...], tuple[RelationshipRecord, ...]]:
    """The one bounded typed walk both traversal operators run (INV-CH7-24).

    **The sequence is universe, close, walk** — the traversal-family rule
    (`D-IMPL-267` D-08, mechanism `D-IMPL-268`, ledger row ``CP04-G-28``,
    semantics version 1.3.0). The admitted entity universe is constructed
    first from the view's entity claims; the working edge set is then
    endpoint-closed against that universe (`GQ-16` at
    docs/GRAPH_QUERY_SEMANTICS.md:316); only then does the walk expand.

    An **unresolved reference** — an edge endpoint carrying no entity claim
    in the view — is legal persisted state (whitepaper §7.3, INV-CH7-20:
    edges are first-class claims, never derived joins) and stays in the
    view the caller handed in. It is not a traversal member: never a walk
    start, never an intermediate hop, and it consumes no depth, so it lies
    on no path and closes no cycle. Depth counts admitted traversal hops,
    not persisted edge hops through entities the traversal universe does
    not hold (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261 — hop
    admissibility, prune before walking). Persisted graph state and
    traversal membership are not the same universe.

    `GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201. Breadth-first from every
    entity of a seed class over endpoint-closed edges of the permitted
    types, at most ``depth_limit`` hops; a hop lands only on an admitted
    class when ``admitted`` is a set (starts are never filtered — `GQ-11`
    at docs/GRAPH_QUERY_SEMANTICS.md:221 selects them). ``forward`` decides
    the adjacency: ``False`` adds both endpoints (the undirected
    NEIGHBORHOOD, :class:`TraversalNeighborhood`); ``True`` adds only
    ``subject → object`` as stored (the directed DESCENDANTS walk,
    :class:`TraversalDescendants`, ledger row ``24.5-L-06``). One function
    rather than two copies so the two walks differ in exactly that line and
    nothing else — the same shape ``src/ccf/graph/fallback.py::_walk``
    keeps, which is what holds every pushed answer to these operators
    differentially. The query tier reaches the same rule by a different
    route: its caller closes before handing the walk its state. Shared
    semantics, not a shared helper (`D-IMPL-268`).

    Returns the reached entities and the TRAVERSABLE edges — every
    endpoint-closed edge of a permitted type, not only those among reached
    nodes; the caller's :func:`_substitute` prunes to the reached endpoints
    (whitepaper §7.4, INV-CH7-40), which is unchanged.
    """
    # Universe, then closure, then the walk (`D-IMPL-267` D-08; Dave's
    # mechanism ruling `D-IMPL-268`: the operator "conforms by
    # endpoint-closing its working edge set against the claimed/admitted
    # entity universe before `_bounded_walk` traverses it … No new public
    # helper or SDK surface is introduced solely to share the predicate").
    # `GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316 (closure before every
    # walk, semantics version 1.3.0) and `GQ-13` at
    # docs/GRAPH_QUERY_SEMANTICS.md:261 (a path through an unresolved
    # reference does not exist). P-1: the view KEEPS its dangling edges as
    # state; this function simply does not traverse them. Ledger row
    # ``CP04-G-28``.
    universe = {record.claim.entity_uri for record in view.entities}
    closed = tuple(
        edge
        for edge in view.relationships
        if edge.claim.subject_uri in universe and edge.claim.object_uri in universe
    )
    traversable = tuple(
        edge
        for edge in closed
        if edge.claim.relationship_type in relationship_types
    )
    adjacency: dict[str, set[str]] = {}
    for edge in traversable:
        adjacency.setdefault(edge.claim.subject_uri, set()).add(
            edge.claim.object_uri
        )
        if not forward:
            adjacency.setdefault(edge.claim.object_uri, set()).add(
                edge.claim.subject_uri
            )

    # The class map, built once: admission reads the REACHED node's class
    # (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0). It is consulted
    # only when ``admitted`` is a set, so it is NOT what keeps an unclaimed
    # endpoint out — the closure above already removed every edge naming one,
    # so no such URI is an adjacency key and none can be reached at all.
    class_of = {
        record.claim.entity_uri: record.claim.entity_class
        for record in view.entities
    }

    frontier = {
        record.claim.entity_uri
        for record in view.entities
        if record.claim.entity_class in seed_classes
    }
    reached = set(frontier)
    for _hop in range(depth_limit):
        frontier = {
            neighbour
            for node in frontier
            for neighbour in adjacency.get(node, ())
            if neighbour not in reached
            and (admitted is None or class_of.get(neighbour) in admitted)
        }
        if not frontier:
            break
        reached |= frontier

    entities = tuple(
        record for record in view.entities if record.claim.entity_uri in reached
    )
    return entities, traversable



class PolicyFilter:
    """Policy category — principal-scoped subgraph substitution (INV-CH7-26).

    Whitepaper §7.4. Runs *first* in every plan so that no later stage can
    observe inadmissible state — with admissibility settled up front, there is
    nothing inadmissible left for a downstream filter to remove.
    """

    key = "policy.principal-subgraph"
    category: OperatorCategory = "policy"

    def __init__(self, *, parameters: PolicyFilterParameters) -> None:
        self._parameters = parameters

    @property
    def parameters(self) -> PolicyFilterParameters:
        return self._parameters

    def read_intent(self) -> QueryFragment:
        """The policy family this operator's ``apply()`` renders (D-03).

        Computed from ``self.parameters`` alone — no view, no data, no clock:
        a direct field-for-field projection of
        :class:`~ccf.operators.params.PolicyFilterParameters` onto the policy
        family of `GQ-02` at docs/GRAPH_QUERY_SEMANTICS.md:64, whose pushed
        admissibility semantics (`GQ-08` at
        docs/GRAPH_QUERY_SEMANTICS.md:163) mirror :meth:`_admits` exactly.
        """
        params = self._parameters
        return QueryFragment(
            permitted_policy_bundle_versions=(
                params.permitted_policy_bundle_versions
            ),
            classification_attribute_by_class=(
                params.classification_attribute_by_class
            ),
            permitted_classifications=params.permitted_classifications,
        )

    def _admits(self, record: EntityRecord) -> bool:
        """Admit a record whose bundle version is permitted and whose per-class
        attribute value is on the allowlist.

        The last test is a generic attribute-value allowlist (ledger row
        ``24.5-L-28``): ``classification_attribute_by_class`` names the
        attribute per entity class and ``permitted_classifications`` is the
        set of values admitted for it, by exact membership — "classification"
        is the name's origin, not a constraint on what the attribute holds
        (cp-01 binds it to jurisdiction). See
        :class:`~ccf.operators.params.PolicyFilterParameters`.
        """
        params = self._parameters
        if record.policy_bundle_version not in params.permitted_policy_bundle_versions:
            return False
        attribute = params.classification_attribute_by_class.get(
            record.claim.entity_class
        )
        if attribute is None:
            return False
        return record.claim.attributes.get(attribute) in params.permitted_classifications

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        """Substitute the principal-permissible subgraph for the full graph."""
        entities = tuple(record for record in view.entities if self._admits(record))
        edges = tuple(
            edge
            for edge in view.relationships
            if edge.policy_bundle_version
            in self._parameters.permitted_policy_bundle_versions
        )
        return OperatorOutput(
            view=_substitute(view, entities=entities, relationships=edges),
            provenance=mint_provenance(self, upstream=upstream),
        )



class SimilaritySelect:
    """Similarity category — corpus-scoped ranking with a pinned index.

    Whitepaper §7.4 / INV-CH7-27: the determinism contract is
    ``(corpus_version, embedding_model_version, query, threshold,
    policy_regime) -> same result``, so the index version is pinned into this
    operator's provenance on every invocation.

    Args:
        parameters: Declared parameter set.
        index: The ranking substrate (D-IMPL-03 seam). Injected — the operator
            never constructs one, because which index a deployment ranks
            against is deployment configuration.
    """

    key = "similarity.corpus-select"
    category: OperatorCategory = "similarity"

    def __init__(
        self,
        *,
        parameters: SimilaritySelectParameters,
        index: SimilarityIndexProtocol,
    ) -> None:
        self._parameters = parameters
        self._index = index

    @property
    def parameters(self) -> SimilaritySelectParameters:
        return self._parameters

    def read_intent(self) -> None:
        """``None``, full stop — Similarity is never pushable (D-03).

        The reason is structural, not circumstantial: :meth:`apply` consults
        the injected :class:`~ccf.similarity.protocol.SimilarityIndexProtocol`
        (the D-IMPL-03 seam), a ranking substrate the graph substrate does not
        hold — so no `GQ-02` at docs/GRAPH_QUERY_SEMANTICS.md:64 predicate
        family exists for it and there is deliberately no Similarity family
        in the query vocabulary. Substrates with native vector search are the
        Phase 15.2 Deferred-Ideas ruling (15.2-CONTEXT.md — "Similarity
        pushdown ... deliberately excluded"; revisiting is its own design
        conversation), so a drive-by "optimization" here is a decision
        reversal, and the pushability-matrix pin in
        ``tests/conformance/test_substrate_properties.py`` fails it by name.
        """
        return None

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        """Keep ranked entities scoring at or above the floor; pass the rest."""
        params = self._parameters
        ranked = tuple(
            record
            for record in view.entities
            if record.claim.entity_class in params.ranked_entity_classes
        )
        hits = self._index.rank(
            tenant_id=tenant_id,
            query=params.query,
            candidates=tuple(record.claim.entity_uri for record in ranked),
        )
        selected = {
            hit.entity_uri
            for hit in hits
            if hit.score_percent >= params.minimum_score_percent
        }
        entities = tuple(
            record
            for record in view.entities
            if record.claim.entity_class not in params.ranked_entity_classes
            or record.claim.entity_uri in selected
        )
        return OperatorOutput(
            view=_substitute(
                view, entities=entities, relationships=view.relationships
            ),
            provenance=mint_provenance(
                self, upstream=upstream, index_version=self._index.index_version
            ),
        )



class TemporalAsOf:
    """Temporal category — bitemporal reconciliation (INV-CH7-25).

    Whitepaper §7.4. This is a *correctness* semantic, not a TTL filter: state
    past its half-life remains readable for historical reconstruction, and this
    operator is what makes an as-of read free of future-information leakage.

    Three cuts, all against the boundary the caller supplied:

    1. claims the fabric had not yet observed at the boundary are absent;
    2. claims superseded at or before the boundary are absent — but claims
       superseded *after* it are still current, which is the whole point;
    3. optionally, claims whose valid interval does not cover the boundary.
    """

    key = "temporal.as-of-boundary"
    category: OperatorCategory = "temporal"

    def __init__(self, *, parameters: TemporalAsOfParameters) -> None:
        self._parameters = parameters

    @property
    def parameters(self) -> TemporalAsOfParameters:
        return self._parameters

    def read_intent(self) -> QueryFragment:
        """The temporal family this operator's ``apply()`` renders (D-03).

        Computed from ``self.parameters`` alone — no view, no data, no clock:
        the fragment carries ``require_valid_at_boundary`` (`GQ-09` at
        docs/GRAPH_QUERY_SEMANTICS.md:185, mirroring cut 3 of
        :meth:`_survives`); the as-of cut itself — cuts 1 and 2 — is not part
        of the family, because it rides the mandatory ``GraphQuery.as_of``
        and applies to every answer (`GQ-07` at
        docs/GRAPH_QUERY_SEMANTICS.md:148).
        """
        return QueryFragment(
            require_valid_at_boundary=self._parameters.require_valid_at_boundary
        )

    def _survives(
        self,
        *,
        observed_at: datetime,
        valid_from: datetime,
        valid_to: datetime | None,
        superseded_at: datetime | None,
        boundary: datetime,
    ) -> bool:
        if observed_at > boundary:
            return False
        if superseded_at is not None and superseded_at <= boundary:
            return False
        if not self._parameters.require_valid_at_boundary:
            return True
        if valid_from > boundary:
            return False
        return valid_to is None or valid_to > boundary

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        """Cut the view to the state that holds at ``temporal_boundary``."""
        entities = tuple(
            record
            for record in view.entities
            if self._survives(
                observed_at=record.claim.observed_at,
                valid_from=record.claim.valid_from,
                valid_to=record.claim.valid_to,
                superseded_at=record.superseded_at,
                boundary=temporal_boundary,
            )
        )
        edges = tuple(
            edge
            for edge in view.relationships
            if self._survives(
                observed_at=edge.claim.observed_at,
                valid_from=edge.claim.valid_from,
                valid_to=edge.claim.valid_to,
                superseded_at=edge.superseded_at,
                boundary=temporal_boundary,
            )
        )
        return OperatorOutput(
            view=_substitute(view, entities=entities, relationships=edges),
            provenance=mint_provenance(self, upstream=upstream),
        )



class TraversalNeighborhood:
    """Traversal category — bounded expansion of relevance (INV-CH7-24).

    Whitepaper §7.4. Breadth-first from the seed classes over the permitted
    relationship types, stopping at ``depth_limit``. Runs last: it expands over
    state that Policy, Similarity, and Temporal have already reconciled, so an
    edge to a node excluded upstream is not a hop this walk can take.

    **Node-class admission** (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201,
    semantics version 1.1.0; ledger row ``24.5-L-05``). When
    ``admitted_entity_classes`` is present, a hop lands only on an entity
    whose ``entity_class`` is a member; walk starts are selected by `GQ-11`
    at docs/GRAPH_QUERY_SEMANTICS.md:221 and are never filtered by
    admission. ``None`` admits every class — the behavior every earlier
    parameter set carried.

    **An unresolved reference is never a hop, under every admission
    setting.** An edge endpoint carrying no entity claim in the view is
    legal persisted state and is not a traversal member: the walk
    endpoint-closes the edges against the view's entity universe before it
    expands, so such an endpoint is never a start, never a hop, and
    consumes no depth (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316,
    semantics version 1.3.0; `D-IMPL-267`, ledger row ``CP04-G-28``).
    The adjacency is undirected here — ``read_intent`` emits
    ``direction="undirected"`` — and the directed walk is the sibling
    :class:`TraversalDescendants` (ledger row ``24.5-L-06``); both run
    :func:`_bounded_walk`. ``src/ccf/graph/fallback.py::_walk`` applies the
    identical predicate, which is what holds every pushed answer to this
    operator differentially.
    """

    key = "traversal.typed-neighborhood"
    category: OperatorCategory = "traversal"

    def __init__(self, *, parameters: TraversalNeighborhoodParameters) -> None:
        self._parameters = parameters

    @property
    def parameters(self) -> TraversalNeighborhoodParameters:
        return self._parameters

    def read_intent(self) -> QueryFragment:
        """The traverse family this operator's ``apply()`` renders (D-03).

        Computed from ``self.parameters`` alone — no view, no data, no clock:
        a field-for-field projection of
        :class:`~ccf.operators.params.TraversalNeighborhoodParameters` onto
        :class:`~ccf.graph.protocols.TraversalSpec` (`GQ-02` at
        docs/GRAPH_QUERY_SEMANTICS.md:64), whose pushed walk semantics
        (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201) mirror :meth:`apply`
        exactly. The fragment names no walk starting points beyond the seed
        classes: explicit ``seeds`` and ``allowed_entities`` are
        engine-authored segment-boundary data an operator's intent can never
        carry (`GQ-06` at docs/GRAPH_QUERY_SEMANTICS.md:132).
        """
        params = self._parameters
        return QueryFragment(
            traverse=TraversalSpec(
                seed_entity_classes=params.seed_entity_classes,
                relationship_types=params.relationship_types,
                depth_limit=params.depth_limit,
                admitted_entity_classes=params.admitted_entity_classes,
                direction="undirected",
            )
        )

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        """Expand from the seeds to the bounded typed neighborhood."""
        params = self._parameters
        entities, traversable = _bounded_walk(
            view,
            seed_classes=params.seed_entity_classes,
            relationship_types=params.relationship_types,
            depth_limit=params.depth_limit,
            admitted=params.admitted_entity_classes,
            forward=False,
        )
        return OperatorOutput(
            view=_substitute(view, entities=entities, relationships=traversable),
            provenance=mint_provenance(self, upstream=upstream),
        )


class TraversalDescendants:
    """Traversal category — the DIRECTED bounded walk (INV-CH7-24).

    Whitepaper §7.4; ledger row ``24.5-L-06``; `GQ-10` at
    docs/GRAPH_QUERY_SEMANTICS.md:201. The sibling of
    :class:`TraversalNeighborhood` under the same ``traversal`` category
    (D-IMPL-223 — a second SHAPE, not a fifth category): breadth-first from
    the seed classes over the permitted relationship types, stopping at
    ``depth_limit``, crossing an edge ONLY from ``subject_uri`` to
    ``object_uri`` as stored. Where the neighborhood walk reaches a node one
    undirected hop from a reached node — a parent's other child, a cycle's
    closing edge — this walk reaches only what the stored orientation leads
    to: descendants, in whatever sense the deployment normalized at ingest.

    Both operators run :func:`_bounded_walk`; they differ in the ``forward``
    flag and the key. ``read_intent`` emits ``direction="forward"``, which
    every backend that cannot express a directed walk declines to
    ``src/ccf/graph/fallback.py::_walk`` (D-04, `GQ-32` at
    docs/GRAPH_QUERY_SEMANTICS.md:583). Node-class admission is the
    neighborhood's, unchanged, and so is the closure that precedes the walk:
    an edge endpoint carrying no entity claim in the view is an unresolved
    reference, never a start and never a hop, because the edges are
    endpoint-closed against the view's entity universe before the walk
    expands (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316, semantics version
    1.3.0; `D-IMPL-267`, ledger row ``CP04-G-28``). Runs last, as every
    traversal does.
    """

    key = "traversal.typed-descendants"
    category: OperatorCategory = "traversal"

    def __init__(self, *, parameters: TraversalDescendantsParameters) -> None:
        self._parameters = parameters

    @property
    def parameters(self) -> TraversalDescendantsParameters:
        return self._parameters

    def read_intent(self) -> QueryFragment:
        """The traverse family this operator's ``apply()`` renders (D-03).

        Computed from ``self.parameters`` alone: a field-for-field projection
        of :class:`~ccf.operators.params.TraversalDescendantsParameters` onto
        :class:`~ccf.graph.protocols.TraversalSpec` (`GQ-02` at
        docs/GRAPH_QUERY_SEMANTICS.md:64) with ``direction="forward"`` fixed
        by this operator — the one thing the parameters do not carry, so no
        artifact value can turn the walk around. The fragment names no walk
        starting points beyond the seed classes (`GQ-06` at
        docs/GRAPH_QUERY_SEMANTICS.md:132).
        """
        params = self._parameters
        return QueryFragment(
            traverse=TraversalSpec(
                seed_entity_classes=params.seed_entity_classes,
                relationship_types=params.relationship_types,
                depth_limit=params.depth_limit,
                admitted_entity_classes=params.admitted_entity_classes,
                direction="forward",
            )
        )

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        """Expand from the seeds to the bounded typed forward reach."""
        params = self._parameters
        entities, traversable = _bounded_walk(
            view,
            seed_classes=params.seed_entity_classes,
            relationship_types=params.relationship_types,
            depth_limit=params.depth_limit,
            admitted=params.admitted_entity_classes,
            forward=True,
        )
        return OperatorOutput(
            view=_substitute(view, entities=entities, relationships=traversable),
            provenance=mint_provenance(self, upstream=upstream),
        )


# Structural conformance is asserted here, at import time, rather than left to
# a test: a class that stopped satisfying the Protocol should fail the build at
# the definition site, not in whichever suite happened to exercise it.
_CONFORMANCE: tuple[type[Operator], ...] = (
    PolicyFilter,
    SimilaritySelect,
    TemporalAsOf,
    TraversalNeighborhood,
    TraversalDescendants,
)
