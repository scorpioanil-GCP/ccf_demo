# bundle-src

READ-PROOF bundle-src: 33364fe6c78b4141019dd8a4

The shipped `src/` of Phase 24.8 and the amended clauses of the query-semantics document, INLINED.
Tree `d7c4946b` on `phase-24.8`; diff base `8567d683` (the `D-IMPL-267` design sitting, the fork from `main`).
The whole phase changed exactly two `src/` files; both appear here in full, plus the full diff.

## 1. The diffstat

```
 docs/GRAPH_QUERY_SEMANTICS.md   | 102 ++++++++++++++++++++++++++++++++--------
 src/ccf/graph/fallback.py       |  26 +++++-----
 src/ccf/operators/categories.py | 100 ++++++++++++++++++++++++++++++---------
 3 files changed, 172 insertions(+), 56 deletions(-)
```

## 2. `src/ccf/operators/categories.py` — FULL CURRENT TEXT

### `src/ccf/operators/categories.py`

```python
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
```

## 3. `src/ccf/graph/fallback.py` — FULL CURRENT TEXT

### `src/ccf/graph/fallback.py`

```python
"""The reference implementation of the graph query semantics prose.

Whitepaper §7.3 (the Context Graph as queryable persisted state) and §7.4
(the operator categories whose semantics a pushed query renders). The
normative vocabulary is ``docs/GRAPH_QUERY_SEMANTICS.md`` (semantics version
1.3.0): the prose decides; this module implements it clause-for-clause; the
adapters agree with it under the differential suite (`GQ-31` at
docs/GRAPH_QUERY_SEMANTICS.md:573); and the property suite audits this module
against the named invariants — so the oracle is answerable to something it
does not define (D-05).

**This is the one BFS every adapter degrades to.** A conformant adapter
answers any well-formed :class:`~ccf.graph.protocols.GraphQuery` (`GQ-29` at
docs/GRAPH_QUERY_SEMANTICS.md:554), degrading internally to scan-and-filter
where it holds no native translation (D-04) — and "scan-and-filter" means
*this module*, so per-substrate divergence has nowhere to live. Since 1.3.0
the in-process operator walk closes for itself too, by the same rule.

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
    supposed to hold it. Its rationale is exclusion: an edge to a node the
    answer *removed* leaks that node's existence. The degenerate
    everything-question excludes nothing; its answer is the tenant's full
    as-of view (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122), in which a
    persisted first-class edge whose endpoint carries no entity claim is
    an unresolved reference (INV-CH7-20 — edges are never derived joins):
    state, not a leak, and `GQ-21` at docs/GRAPH_QUERY_SEMANTICS.md:446
    pins that answer byte-identical to the pre-seam ``as_of()``. Since
    semantics version 1.3.0 this closure precedes EVERY walk at every
    tier, the in-process operator included (`D-IMPL-268`).
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
    """The bounded typed walk — `GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201.

    Semantics, matching ``src/ccf/operators/categories.py::TraversalNeighborhood``
    and its directed sibling ``src/ccf/operators/categories.py::TraversalDescendants``
    (INV-CH7-24): directed by ``traverse.direction`` (ledger row
    ``24.5-L-06``) — under ``"undirected"`` an edge is crossable from either
    endpoint, under ``"forward"`` only from ``subject_uri`` to ``object_uri``
    as stored, and the reverse adjacency is simply never built;
    typed — only edges whose type is permitted are crossable, and edges of
    other types are absent from the answer even between reached endpoints;
    seeds are included; ``depth_limit=0`` yields the walk starting points
    only; ``depth_limit=N`` reaches at most N hops; admitted — when
    ``admitted_entity_classes`` is present a hop lands only on an entity of
    an admitted class (semantics version 1.1.0, ledger row ``24.5-L-05``):
    the predicate reads the REACHED node's class from ``entities``, never a
    walk start's, and an entity absent from ``entities`` is not admitted;
    ``None`` admits every class.

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
    undirected = traverse.direction == "undirected"
    for edge in typed:
        adjacency.setdefault(edge.claim.subject_uri, set()).add(
            edge.claim.object_uri
        )
        if undirected:
            adjacency.setdefault(edge.claim.object_uri, set()).add(
                edge.claim.subject_uri
            )

    in_scope = {record.claim.entity_uri for record in entities}
    class_of = {
        record.claim.entity_uri: record.claim.entity_class for record in entities
    }
    admitted = traverse.admitted_entity_classes
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
            and (admitted is None or class_of.get(neighbour) in admitted)
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
    5. the traverse family, when present, is the bounded typed expansion of
       `GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201 — undirected, or forward
       only under ``direction="forward"`` (1.2.0, ledger row 24.5-L-06) —
       with node-class admission when the spec names admitted classes (1.1.0,
       24.5-L-05).

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
```


READ-PROOF bundle-src: 33364fe6c78b4141019dd8a4

## 4. `docs/GRAPH_QUERY_SEMANTICS.md` — the banner (lines 1-12)

### `docs/GRAPH_QUERY_SEMANTICS.md:1-12`

```markdown
# Graph Query Semantics

**Semantics version: 1.3.0** — the query vocabulary is versioned through this
document only (D-12): the `GraphQuery` contract carries **no version field**
and evolves by additive sentinel-defaulted fields under the existing
frozen/`extra=forbid` discipline; the differential conformance suite is the
compatibility check. 1.0 added `allowed_entities`; 1.1.0 `admitted_entity_classes`; 1.2.0 `direction`; 1.3.0 the traversal universe (`GQ-10`, `GQ-13`, `GQ-16`, `GQ-35`).

This is the normative definition of what a `GraphQuery` means and what any
conformant answerer must return — D-05 artifact 1, written before the
reference implementation and before any adapter, per the D-05 ordering
(prose → fallback → adapters). The reading order is the authority order:
```

## 5. `docs/GRAPH_QUERY_SEMANTICS.md` — `GQ-10` (201-220), `GQ-13` (261-288), `GQ-16` (316-329), FULL TEXT

### `docs/GRAPH_QUERY_SEMANTICS.md:201-220 GQ-10`

```markdown
### `GQ-10` — Traversal

When the traverse family is present, the answer is a bounded breadth-first
expansion (INV-CH7-24, whitepaper §7.4) with these decided semantics:

- **The traversal universe.** Every walk — an in-process operator, the fallback, or a pushed adapter — runs over the in-scope ENTITY records, never over persisted edges alone: construct the admitted entity universe first, endpoint-close the edges against that universe (`GQ-16`), then walk (amendment 1.3.0, `GQ-35`).
- **Undirected.** An edge is crossable in either direction; subject→object order carries no traversal
  meaning — under `direction="undirected"`, the default; `direction="forward"` crosses only from `subject_uri` to `object_uri` as stored (amendment 1.2.0, `GQ-35`).
- **Typed.** The walk crosses only edges whose `relationship_type` is a member of `relationship_types`.
  Edges of other types are not crossable — and are **absent from the answer** even when both their endpoints are reached: the traverse family's answer contains exactly the permitted-type edges among reached entities.
- **Seeds are included.** Every walk starting point that is itself in scope is in the answer.
- **`depth_limit=0` yields the walk starting points only.** Zero hops is a legal, meaningful bound, not an error and not "unlimited".
- **`depth_limit=N` reaches at most N hops** from a walk starting point. Depth counts admitted traversal
  hops, not persisted edge hops through an unresolved reference; a node whose shortest admissible path from every start exceeds N is absent.
- **Admitted.** When `admitted_entity_classes` is present, a hop lands only on an entity whose `entity_class`
  is a member; walk starts (`GQ-11`) are unaffected, and an entity absent from in-scope state is not a hop — it is
  an unresolved reference, excluded below whether or not a class set is present. Absent (`None`), every class is admissible — the 1.0.x behavior (amendment 1.1.0, `GQ-35`).

An **unresolved reference** is an edge endpoint carrying no entity claim in the view: legal persisted state (INV-CH7-20) that the degenerate answer keeps (`GQ-05`, `GQ-21`), but that is never a walk start, never an intermediate hop, and consumes no depth — and for which no placeholder or synthetic record is ever manufactured. Persisted graph state and traversal membership are not the same universe.
```

### `docs/GRAPH_QUERY_SEMANTICS.md:261-288 GQ-13`

```markdown
### `GQ-13` — Every hop, not the result set

Every node and every edge on a traversal path MUST satisfy the segment's
policy (`GQ-08`) and temporal (`GQ-07`, `GQ-09`) predicates — and, when
`allowed_entities` is present, every node on the path MUST be a member of
the set. **A path through an excluded, out-of-set, or unresolved node — an
unresolved reference in `GQ-10`'s sense — does not exist.** This is
INV-CH7-40, the substitution semantics, rendered at the query tier: every
traversal operator endpoint-closes its view against the entity universe before it expands
(amendment 1.3.0, `GQ-10`, `GQ-16`), as the fallback closes before its walk and a pushed traversal closes inside its own query.

This clause is a MUST for every adapter at every tier. Applying the
predicates to the *result set* instead of to *every hop* is the named
information-disclosure defect of this seam: a path seed→X→target where X
is policy-excluded would return `target`, leaking X's existence by
reachability. The differential corpus deliberately targets multi-hop
paths through mixed-admissibility neighborhoods to expose exactly this
divergence.

---

## 4. Segmentation and the uniform rule

This section implements the D-IMPL-87 resolution entry
(`docs/DECISIONS.md`, 2026-08-07) — the ruling of record for
multi-segment pushdown. Nothing here is a planner choice; the clauses
transcribe the ruling.
```

### `docs/GRAPH_QUERY_SEMANTICS.md:316-329 GQ-16`

```markdown
### `GQ-16` — The induced subgraph

When `allowed_entities` is present, a relationship is in the answer only
when **both** endpoints are members of the set — and both endpoints
survive the segment's predicates. This is the no-leak-by-absence
substitution rule (`src/ccf/operators/categories.py::_substitute`,
INV-CH7-40) rendered at the query tier: a view retaining an edge to a
node the principal may not see leaks by absence.

The endpoint-closure half of this clause holds for every **constrained**
answer — any family present, or `allowed_entities` non-`None`: such a view never contains a
relationship whose endpoint entity is absent from it, and closure precedes EVERY walk at every tier, the
in-process operators included (amendment 1.3.0, `GQ-35`). The degenerate answer is exempt (amendment 1.0.1, stated under `GQ-35`).
```

## 6. `docs/GRAPH_QUERY_SEMANTICS.md` — `GQ-35` and the 1.3.0 entry (621-701), FULL TEXT

### `docs/GRAPH_QUERY_SEMANTICS.md:621-701 GQ-35`

```markdown
### `GQ-35` — Amendments

Semantic changes to this vocabulary ship as **versioned amendments to
this document** under the semver lane declared at the top — never as
silent behavioral drift in the fallback or an adapter. The `GraphQuery`
contract carries no version field (D-12): the vocabulary evolves by
additive sentinel-defaulted fields under the frozen/`extra=forbid`
discipline, the differential suite is the compatibility check, and this
document is the record of what each version means. Clause anchors are
stable across amendments; numbers are never reused. Adapter failure
messages MUST cite the clause anchor violated, so a dispute begins from
the sentence it is about.

**Amendment history.** New entries append here rather than rewriting the
clause they amend out of existence, and an amendment is written so it does
not move the clause headings above it — the anchored citations across
`/src` and `/tests` carry line numbers, and a renumbering edit would make
the citation guard report a hundred false moves and hide a real one.

- **1.3.0** — *plan 24.8-05 (the mechanism: plan 24.8-04), ledger row
  `CP04-G-28`, `D-IMPL-267`, `D-IMPL-268`.* No contract field changes.
  `GQ-10`, `GQ-13` and `GQ-16` gain the traversal-universe rule —
  construct the admitted entity universe first, endpoint-close the edges
  against that universe, then walk — as the definition of every walk at
  every tier: the in-process operators, the fallback, and every pushed
  adapter answer one question, not two.

  *What it means.* An edge endpoint for which the view holds no entity claim
  is an **unresolved reference**: legal persisted state that is never a walk
  start, never an intermediate hop, and never part of a path, and for which
  no placeholder or synthetic record is manufactured. Two principles carry
  the ruling (`D-IMPL-267`):

  > **Persisted graph state and traversal membership are not the same universe.
  > An edge may legally name an unresolved endpoint; that does not make the
  > endpoint traversable.**

  > **Traversal semantics are execution-path invariant. In-process,
  > fallback, and pushed implementations may execute differently, but the
  > same question over the same pinned state must produce the same
  > canonical traversal result.**

  Depth follows from the first: **Depth counts admitted traversal hops, not
  persisted edge hops through entities that do not exist in the traversal
  universe.** An unresolved reference therefore consumes no depth and
  participates in no cycle. The in-process operator conforms by
  endpoint-closing its working edge set against the entity universe before
  `_bounded_walk` traverses it — shared semantics, not a shared helper, and
  no predicate is promoted to a public surface merely to share one symbol
  (`D-IMPL-268`).

  *Why it was needed.* The SDK held two meanings of traversal. Measured
  across six backends on graphs whose only difference is a claim-less
  endpoint X: on a chain A→X→B at `depth_limit=2` with
  `admitted_entity_classes=None` the operator tier answered `{A,B}` where
  the query tier answered `{A}`; on a bypass graph where B is two persisted
  hops from A through X and three admitted hops through C and D, depth 2
  answered `{A,B,C,D}` at the operator tier against `{A,C,D}` at the query
  tier. The operator tier disagreed with the fallback on **10 of 42**
  (graph, question) pairs — each one a `depth ≥ 2`, `admitted=None` row with
  X on the shortest persisted path — while the pushed adapters agreed with
  the fallback on **252/252** backend-rows. The shipped operator walk was
  not even idempotent on that shape: it answered `{A,B}` with no edges, so
  re-applying it answers `{A}` — `T(T(G)) ≠ T(G)`. Found at the 24.5 close
  (`D-GATE-24.5` R1), carried by ruling since (`24.6-L-19`) as ledger row
  `CP04-G-28`.

  *Conformance.* A new operator-tier differential,
  `tests/conformance/test_operator_tier_differential.py`, holds
  `TraversalNeighborhood` and `TraversalDescendants` byte-identical to
  `reader.query` and to `fallback.answer` over
  `tests/conformance/query_corpus.py::unresolved_reference_cases` on every
  registered backend, and proves the depth and cycle consequences rather
  than final membership alone.

  *Behavioral in one tier, no field.* The inverse of 1.0.1's clarifying
  slot: no field is added to the vocabulary, so `content_hash(GraphQuery)`
  does NOT move (`GQ-20`) — unlike 1.1.0 and 1.2.0, each of which moved it
  for every traverse query — while one tier's behavior does change, to the
  meaning the other tiers already had.
```

## 7. The diff itself

```diff
diff --git a/docs/GRAPH_QUERY_SEMANTICS.md b/docs/GRAPH_QUERY_SEMANTICS.md
index 6eb4a972..8a88d1ab 100644
--- a/docs/GRAPH_QUERY_SEMANTICS.md
+++ b/docs/GRAPH_QUERY_SEMANTICS.md
@@ -1,10 +1,10 @@
 # Graph Query Semantics
 
-**Semantics version: 1.2.0** — the query vocabulary is versioned through this
+**Semantics version: 1.3.0** — the query vocabulary is versioned through this
 document only (D-12): the `GraphQuery` contract carries **no version field**
 and evolves by additive sentinel-defaulted fields under the existing
 frozen/`extra=forbid` discipline; the differential conformance suite is the
-compatibility check. 1.0 added `allowed_entities`; 1.1.0 `admitted_entity_classes`; 1.2.0 `direction` (`GQ-10`, `GQ-35`).
+compatibility check. 1.0 added `allowed_entities`; 1.1.0 `admitted_entity_classes`; 1.2.0 `direction`; 1.3.0 the traversal universe (`GQ-10`, `GQ-13`, `GQ-16`, `GQ-35`).
 
 This is the normative definition of what a `GraphQuery` means and what any
 conformant answerer must return — D-05 artifact 1, written before the
@@ -203,20 +203,20 @@ model, and which one a decision needs is declared, never assumed.
 When the traverse family is present, the answer is a bounded breadth-first
 expansion (INV-CH7-24, whitepaper §7.4) with these decided semantics:
 
+- **The traversal universe.** Every walk — an in-process operator, the fallback, or a pushed adapter — runs over the in-scope ENTITY records, never over persisted edges alone: construct the admitted entity universe first, endpoint-close the edges against that universe (`GQ-16`), then walk (amendment 1.3.0, `GQ-35`).
 - **Undirected.** An edge is crossable in either direction; subject→object order carries no traversal
-  meaning — under `direction="undirected"`, the default; `direction="forward"` crosses only from
-  `subject_uri` to `object_uri` as stored (amendment 1.2.0, `GQ-35`).
+  meaning — under `direction="undirected"`, the default; `direction="forward"` crosses only from `subject_uri` to `object_uri` as stored (amendment 1.2.0, `GQ-35`).
 - **Typed.** The walk crosses only edges whose `relationship_type` is a member of `relationship_types`.
-  Edges of other types are not crossable — and are **absent from the answer** even when both their
-  endpoints are reached: the traverse family's answer contains exactly the permitted-type edges among reached entities.
+  Edges of other types are not crossable — and are **absent from the answer** even when both their endpoints are reached: the traverse family's answer contains exactly the permitted-type edges among reached entities.
 - **Seeds are included.** Every walk starting point that is itself in scope is in the answer.
 - **`depth_limit=0` yields the walk starting points only.** Zero hops is a legal, meaningful bound, not an error and not "unlimited".
-- **`depth_limit=N` reaches at most N hops** from a walk starting point. A node whose shortest
-  admissible path from every start exceeds N is absent.
-- **Admitted.** When `admitted_entity_classes` is present, a hop lands only on an entity whose
-  `entity_class` is a member; walk starts (`GQ-11`) are unaffected, and an entity absent from
-  in-scope state is not a hop. Absent (`None`), every class is admissible — the 1.0.x behavior
-  (amendment 1.1.0, `GQ-35`).
+- **`depth_limit=N` reaches at most N hops** from a walk starting point. Depth counts admitted traversal
+  hops, not persisted edge hops through an unresolved reference; a node whose shortest admissible path from every start exceeds N is absent.
+- **Admitted.** When `admitted_entity_classes` is present, a hop lands only on an entity whose `entity_class`
+  is a member; walk starts (`GQ-11`) are unaffected, and an entity absent from in-scope state is not a hop — it is
+  an unresolved reference, excluded below whether or not a class set is present. Absent (`None`), every class is admissible — the 1.0.x behavior (amendment 1.1.0, `GQ-35`).
+
+An **unresolved reference** is an edge endpoint carrying no entity claim in the view: legal persisted state (INV-CH7-20) that the degenerate answer keeps (`GQ-05`, `GQ-21`), but that is never a walk start, never an intermediate hop, and consumes no depth — and for which no placeholder or synthetic record is ever manufactured. Persisted graph state and traversal membership are not the same universe.
 
 ### `GQ-11` — Walk-start selection
 
@@ -263,11 +263,11 @@ and MUST never be assumed to have been applied upstream.
 Every node and every edge on a traversal path MUST satisfy the segment's
 policy (`GQ-08`) and temporal (`GQ-07`, `GQ-09`) predicates — and, when
 `allowed_entities` is present, every node on the path MUST be a member of
-the set. **A path through an excluded or out-of-set node does not
-exist.** This is INV-CH7-40 — the substitution semantics — rendered at
-the query tier: in-process, the walk expands over a view that Policy and
-Temporal already pruned, so an edge to an excluded node is not a hop the
-walk can take, and a pushed traversal MUST behave identically.
+the set. **A path through an excluded, out-of-set, or unresolved node — an
+unresolved reference in `GQ-10`'s sense — does not exist.** This is
+INV-CH7-40, the substitution semantics, rendered at the query tier: every
+traversal operator endpoint-closes its view against the entity universe before it expands
+(amendment 1.3.0, `GQ-10`, `GQ-16`), as the fallback closes before its walk and a pushed traversal closes inside its own query.
 
 This clause is a MUST for every adapter at every tier. Applying the
 predicates to the *result set* instead of to *every hop* is the named
@@ -323,9 +323,9 @@ INV-CH7-40) rendered at the query tier: a view retaining an edge to a
 node the principal may not see leaks by absence.
 
 The endpoint-closure half of this clause holds for every **constrained**
-answer — any family present, or `allowed_entities` non-`None`: such a view
-never contains a relationship whose endpoint entity is absent from it. The
-degenerate answer is exempt (amendment 1.0.1, stated under `GQ-35`).
+answer — any family present, or `allowed_entities` non-`None`: such a view never contains a
+relationship whose endpoint entity is absent from it, and closure precedes EVERY walk at every tier, the
+in-process operators included (amendment 1.3.0, `GQ-35`). The degenerate answer is exempt (amendment 1.0.1, stated under `GQ-35`).
 
 ### `GQ-17` — Segment-boundary mechanics
 
@@ -637,6 +637,68 @@ not move the clause headings above it — the anchored citations across
 `/src` and `/tests` carry line numbers, and a renumbering edit would make
 the citation guard report a hundred false moves and hide a real one.
 
+- **1.3.0** — *plan 24.8-05 (the mechanism: plan 24.8-04), ledger row
+  `CP04-G-28`, `D-IMPL-267`, `D-IMPL-268`.* No contract field changes.
+  `GQ-10`, `GQ-13` and `GQ-16` gain the traversal-universe rule —
+  construct the admitted entity universe first, endpoint-close the edges
+  against that universe, then walk — as the definition of every walk at
+  every tier: the in-process operators, the fallback, and every pushed
+  adapter answer one question, not two.
+
+  *What it means.* An edge endpoint for which the view holds no entity claim
+  is an **unresolved reference**: legal persisted state that is never a walk
+  start, never an intermediate hop, and never part of a path, and for which
+  no placeholder or synthetic record is manufactured. Two principles carry
+  the ruling (`D-IMPL-267`):
+
+  > **Persisted graph state and traversal membership are not the same universe.
+  > An edge may legally name an unresolved endpoint; that does not make the
+  > endpoint traversable.**
+
+  > **Traversal semantics are execution-path invariant. In-process,
+  > fallback, and pushed implementations may execute differently, but the
+  > same question over the same pinned state must produce the same
+  > canonical traversal result.**
+
+  Depth follows from the first: **Depth counts admitted traversal hops, not
+  persisted edge hops through entities that do not exist in the traversal
+  universe.** An unresolved reference therefore consumes no depth and
+  participates in no cycle. The in-process operator conforms by
+  endpoint-closing its working edge set against the entity universe before
+  `_bounded_walk` traverses it — shared semantics, not a shared helper, and
+  no predicate is promoted to a public surface merely to share one symbol
+  (`D-IMPL-268`).
+
+  *Why it was needed.* The SDK held two meanings of traversal. Measured
+  across six backends on graphs whose only difference is a claim-less
+  endpoint X: on a chain A→X→B at `depth_limit=2` with
+  `admitted_entity_classes=None` the operator tier answered `{A,B}` where
+  the query tier answered `{A}`; on a bypass graph where B is two persisted
+  hops from A through X and three admitted hops through C and D, depth 2
+  answered `{A,B,C,D}` at the operator tier against `{A,C,D}` at the query
+  tier. The operator tier disagreed with the fallback on **10 of 42**
+  (graph, question) pairs — each one a `depth ≥ 2`, `admitted=None` row with
+  X on the shortest persisted path — while the pushed adapters agreed with
+  the fallback on **252/252** backend-rows. The shipped operator walk was
+  not even idempotent on that shape: it answered `{A,B}` with no edges, so
+  re-applying it answers `{A}` — `T(T(G)) ≠ T(G)`. Found at the 24.5 close
+  (`D-GATE-24.5` R1), carried by ruling since (`24.6-L-19`) as ledger row
+  `CP04-G-28`.
+
+  *Conformance.* A new operator-tier differential,
+  `tests/conformance/test_operator_tier_differential.py`, holds
+  `TraversalNeighborhood` and `TraversalDescendants` byte-identical to
+  `reader.query` and to `fallback.answer` over
+  `tests/conformance/query_corpus.py::unresolved_reference_cases` on every
+  registered backend, and proves the depth and cycle consequences rather
+  than final membership alone.
+
+  *Behavioral in one tier, no field.* The inverse of 1.0.1's clarifying
+  slot: no field is added to the vocabulary, so `content_hash(GraphQuery)`
+  does NOT move (`GQ-20`) — unlike 1.1.0 and 1.2.0, each of which moved it
+  for every traverse query — while one tier's behavior does change, to the
+  meaning the other tiers already had.
+
 - **1.2.0** — *plan 24.5-18 (the mechanism: plan 24.5-05), ledger row
   `24.5-L-06`.* `GQ-10`'s first bullet gains a direction: the traverse
   family carries `direction: "undirected" | "forward" = "undirected"` on
diff --git a/src/ccf/graph/fallback.py b/src/ccf/graph/fallback.py
index 5fb553cd..78bcd1a3 100644
--- a/src/ccf/graph/fallback.py
+++ b/src/ccf/graph/fallback.py
@@ -3,7 +3,7 @@
 Whitepaper §7.3 (the Context Graph as queryable persisted state) and §7.4
 (the operator categories whose semantics a pushed query renders). The
 normative vocabulary is ``docs/GRAPH_QUERY_SEMANTICS.md`` (semantics version
-1.0.1): the prose decides; this module implements it clause-for-clause; the
+1.3.0): the prose decides; this module implements it clause-for-clause; the
 adapters agree with it under the differential suite (`GQ-31` at
 docs/GRAPH_QUERY_SEMANTICS.md:573); and the property suite audits this module
 against the named invariants — so the oracle is answerable to something it
@@ -13,8 +13,8 @@ does not define (D-05).
 answers any well-formed :class:`~ccf.graph.protocols.GraphQuery` (`GQ-29` at
 docs/GRAPH_QUERY_SEMANTICS.md:554), degrading internally to scan-and-filter
 where it holds no native translation (D-04) — and "scan-and-filter" means
-*this module*, so no second traversal implementation exists in the tree and
-per-substrate divergence has nowhere to live.
+*this module*, so per-substrate divergence has nowhere to live. Since 1.3.0
+the in-process operator walk closes for itself too, by the same rule.
 
 Purity, by construction: pure functions over ``(entities, relationships,
 query)`` returning surviving records. No I/O, no clock reads (``as_of``
@@ -180,16 +180,16 @@ def _endpoint_closure(
     wording said "every answer", 15.2-05 found it contradicted `GQ-05`
     and `GQ-21` on the dangling-edge shape and resolved it here, and the
     15.2-14 phase-close audit moved the ruling into the document that is
-    supposed to hold it. The reasoning below is why, restated so a reader
-    of this function does not have to leave it — its rationale is
-    exclusion: an edge to a node the answer *removed* leaks
-    that node's existence. The degenerate everything-question excludes
-    nothing; its answer is the tenant's full as-of view (`GQ-05` at
-    docs/GRAPH_QUERY_SEMANTICS.md:122), in which a persisted first-class
-    edge whose endpoint carries no entity claim (INV-CH7-20 — edges are
-    never derived joins) is state, not a leak — and `GQ-21` at
-    docs/GRAPH_QUERY_SEMANTICS.md:446 pins that answer byte-identical to
-    the pre-seam ``as_of()``, which never pruned it.
+    supposed to hold it. Its rationale is exclusion: an edge to a node the
+    answer *removed* leaks that node's existence. The degenerate
+    everything-question excludes nothing; its answer is the tenant's full
+    as-of view (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122), in which a
+    persisted first-class edge whose endpoint carries no entity claim is
+    an unresolved reference (INV-CH7-20 — edges are never derived joins):
+    state, not a leak, and `GQ-21` at docs/GRAPH_QUERY_SEMANTICS.md:446
+    pins that answer byte-identical to the pre-seam ``as_of()``. Since
+    semantics version 1.3.0 this closure precedes EVERY walk at every
+    tier, the in-process operator included (`D-IMPL-268`).
     """
     surviving = {record.claim.entity_uri for record in entities}
     return tuple(
diff --git a/src/ccf/operators/categories.py b/src/ccf/operators/categories.py
index df1cf5ff..c1137917 100644
--- a/src/ccf/operators/categories.py
+++ b/src/ccf/operators/categories.py
@@ -112,27 +112,65 @@ def _bounded_walk(
 ) -> tuple[tuple[EntityRecord, ...], tuple[RelationshipRecord, ...]]:
     """The one bounded typed walk both traversal operators run (INV-CH7-24).
 
+    **The sequence is universe, close, walk** — the traversal-family rule
+    (`D-IMPL-267` D-08, mechanism `D-IMPL-268`, ledger row ``CP04-G-28``,
+    semantics version 1.3.0). The admitted entity universe is constructed
+    first from the view's entity claims; the working edge set is then
+    endpoint-closed against that universe (`GQ-16` at
+    docs/GRAPH_QUERY_SEMANTICS.md:316); only then does the walk expand.
+
+    An **unresolved reference** — an edge endpoint carrying no entity claim
+    in the view — is legal persisted state (whitepaper §7.3, INV-CH7-20:
+    edges are first-class claims, never derived joins) and stays in the
+    view the caller handed in. It is not a traversal member: never a walk
+    start, never an intermediate hop, and it consumes no depth, so it lies
+    on no path and closes no cycle. Depth counts admitted traversal hops,
+    not persisted edge hops through entities the traversal universe does
+    not hold (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261 — hop
+    admissibility, prune before walking). Persisted graph state and
+    traversal membership are not the same universe.
+
     `GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201. Breadth-first from every
-    entity of a seed class over edges of the permitted types, at most
-    ``depth_limit`` hops; a hop lands only on an admitted class when
-    ``admitted`` is a set (starts are never filtered — `GQ-11` at
-    docs/GRAPH_QUERY_SEMANTICS.md:221 selects them), and an entity absent
-    from the view's class map is not a hop. ``forward`` decides the adjacency:
-    ``False`` adds both endpoints (the undirected NEIGHBORHOOD,
-    :class:`TraversalNeighborhood`); ``True`` adds only ``subject → object``
-    as stored (the directed DESCENDANTS walk, :class:`TraversalDescendants`,
-    ledger row ``24.5-L-06``). One function rather than two copies so the two
-    walks differ in exactly that line and nothing else — the same shape
-    ``src/ccf/graph/fallback.py::_walk`` keeps, which is what holds every
-    pushed answer to these operators differentially.
-
-    Returns the reached entities and the TRAVERSABLE edges — every edge of a
-    permitted type, not only those among reached nodes; the caller's
-    :func:`_substitute` prunes to the reached endpoints (INV-CH7-40).
+    entity of a seed class over endpoint-closed edges of the permitted
+    types, at most ``depth_limit`` hops; a hop lands only on an admitted
+    class when ``admitted`` is a set (starts are never filtered — `GQ-11`
+    at docs/GRAPH_QUERY_SEMANTICS.md:221 selects them). ``forward`` decides
+    the adjacency: ``False`` adds both endpoints (the undirected
+    NEIGHBORHOOD, :class:`TraversalNeighborhood`); ``True`` adds only
+    ``subject → object`` as stored (the directed DESCENDANTS walk,
+    :class:`TraversalDescendants`, ledger row ``24.5-L-06``). One function
+    rather than two copies so the two walks differ in exactly that line and
+    nothing else — the same shape ``src/ccf/graph/fallback.py::_walk``
+    keeps, which is what holds every pushed answer to these operators
+    differentially. The query tier reaches the same rule by a different
+    route: its caller closes before handing the walk its state. Shared
+    semantics, not a shared helper (`D-IMPL-268`).
+
+    Returns the reached entities and the TRAVERSABLE edges — every
+    endpoint-closed edge of a permitted type, not only those among reached
+    nodes; the caller's :func:`_substitute` prunes to the reached endpoints
+    (whitepaper §7.4, INV-CH7-40), which is unchanged.
     """
-    traversable = tuple(
+    # Universe, then closure, then the walk (`D-IMPL-267` D-08; Dave's
+    # mechanism ruling `D-IMPL-268`: the operator "conforms by
+    # endpoint-closing its working edge set against the claimed/admitted
+    # entity universe before `_bounded_walk` traverses it … No new public
+    # helper or SDK surface is introduced solely to share the predicate").
+    # `GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316 (closure before every
+    # walk, semantics version 1.3.0) and `GQ-13` at
+    # docs/GRAPH_QUERY_SEMANTICS.md:261 (a path through an unresolved
+    # reference does not exist). P-1: the view KEEPS its dangling edges as
+    # state; this function simply does not traverse them. Ledger row
+    # ``CP04-G-28``.
+    universe = {record.claim.entity_uri for record in view.entities}
+    closed = tuple(
         edge
         for edge in view.relationships
+        if edge.claim.subject_uri in universe and edge.claim.object_uri in universe
+    )
+    traversable = tuple(
+        edge
+        for edge in closed
         if edge.claim.relationship_type in relationship_types
     )
     adjacency: dict[str, set[str]] = {}
@@ -146,8 +184,10 @@ def _bounded_walk(
             )
 
     # The class map, built once: admission reads the REACHED node's class
-    # (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0), and a node
-    # absent from the view has no class and is not admitted.
+    # (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0). It is consulted
+    # only when ``admitted`` is a set, so it is NOT what keeps an unclaimed
+    # endpoint out — the closure above already removed every edge naming one,
+    # so no such URI is an adjacency key and none can be reached at all.
     class_of = {
         record.claim.entity_uri: record.claim.entity_class
         for record in view.entities
@@ -461,9 +501,17 @@ class TraversalNeighborhood:
     semantics version 1.1.0; ledger row ``24.5-L-05``). When
     ``admitted_entity_classes`` is present, a hop lands only on an entity
     whose ``entity_class`` is a member; walk starts are selected by `GQ-11`
-    at docs/GRAPH_QUERY_SEMANTICS.md:221 and are never filtered by admission,
-    and an entity absent from the view's class map is not a hop. ``None``
-    admits every class — the behavior every earlier parameter set carried.
+    at docs/GRAPH_QUERY_SEMANTICS.md:221 and are never filtered by
+    admission. ``None`` admits every class — the behavior every earlier
+    parameter set carried.
+
+    **An unresolved reference is never a hop, under every admission
+    setting.** An edge endpoint carrying no entity claim in the view is
+    legal persisted state and is not a traversal member: the walk
+    endpoint-closes the edges against the view's entity universe before it
+    expands, so such an endpoint is never a start, never a hop, and
+    consumes no depth (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316,
+    semantics version 1.3.0; `D-IMPL-267`, ledger row ``CP04-G-28``).
     The adjacency is undirected here — ``read_intent`` emits
     ``direction="undirected"`` — and the directed walk is the sibling
     :class:`TraversalDescendants` (ledger row ``24.5-L-06``); both run
@@ -550,7 +598,13 @@ class TraversalDescendants:
     every backend that cannot express a directed walk declines to
     ``src/ccf/graph/fallback.py::_walk`` (D-04, `GQ-32` at
     docs/GRAPH_QUERY_SEMANTICS.md:583). Node-class admission is the
-    neighborhood's, unchanged. Runs last, as every traversal does.
+    neighborhood's, unchanged, and so is the closure that precedes the walk:
+    an edge endpoint carrying no entity claim in the view is an unresolved
+    reference, never a start and never a hop, because the edges are
+    endpoint-closed against the view's entity universe before the walk
+    expands (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316, semantics version
+    1.3.0; `D-IMPL-267`, ledger row ``CP04-G-28``). Runs last, as every
+    traversal does.
     """
 
     key = "traversal.typed-descendants"
```


READ-PROOF bundle-src: 33364fe6c78b4141019dd8a4
