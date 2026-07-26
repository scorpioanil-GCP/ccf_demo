"""One genuine operator per canonical category — the vertical slice's algebra.

Whitepaper §7.4 (INV-CH7-24 bounded traversal, INV-CH7-25 temporal
reconciliation as a correctness semantic, INV-CH7-26 policy as subgraph
substitution, INV-CH7-27 corpus-scoped similarity); DESIGN.md §2B.1.

These four are minimal in *coverage* and deliberately not minimal in
*behavior*: each one actually removes or reshapes graph state, so a chain of
them is a chain, not four identity functions wearing category names (D-02).

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

from ccf.graph.protocols import EntityRecord, GraphView, RelationshipRecord
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



class PolicyFilter:
    """Policy category — principal-scoped subgraph substitution (INV-CH7-26).

    Whitepaper §7.4. Runs *first* in every plan so that no later stage can
    observe inadmissible state; "no filter runs after retrieval because no
    retrieval of inadmissible content happened".
    """

    key = "policy.principal-subgraph"
    category: OperatorCategory = "policy"

    def __init__(self, *, parameters: PolicyFilterParameters) -> None:
        self._parameters = parameters

    @property
    def parameters(self) -> PolicyFilterParameters:
        return self._parameters

    def _admits(self, record: EntityRecord) -> bool:
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
    """

    key = "traversal.typed-neighborhood"
    category: OperatorCategory = "traversal"

    def __init__(self, *, parameters: TraversalNeighborhoodParameters) -> None:
        self._parameters = parameters

    @property
    def parameters(self) -> TraversalNeighborhoodParameters:
        return self._parameters

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
        traversable = tuple(
            edge
            for edge in view.relationships
            if edge.claim.relationship_type in params.relationship_types
        )
        adjacency: dict[str, set[str]] = {}
        for edge in traversable:
            adjacency.setdefault(edge.claim.subject_uri, set()).add(
                edge.claim.object_uri
            )
            adjacency.setdefault(edge.claim.object_uri, set()).add(
                edge.claim.subject_uri
            )

        frontier = {
            record.claim.entity_uri
            for record in view.entities
            if record.claim.entity_class in params.seed_entity_classes
        }
        reached = set(frontier)
        for _hop in range(params.depth_limit):
            frontier = {
                neighbour
                for node in frontier
                for neighbour in adjacency.get(node, ())
                if neighbour not in reached
            }
            if not frontier:
                break
            reached |= frontier

        entities = tuple(
            record for record in view.entities if record.claim.entity_uri in reached
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
)
