"""Banking-shaped graph-state strategies and the harness's fabric (D-14).

What this module supplies to the property suites:

* :func:`banking_graph_states` — an ``st.composite`` strategy over
  :class:`~ccf.graph.protocols.GraphView` values with entities, typed
  relationships, bitemporal claims, policy labels, and lineage;
* :func:`curated_edge_graphs` — the fixture-declared edge cases;
* :func:`shipped_operators` — a registry holding one instance of every operator
  the SDK ships, parameterized from the Control Plane fixture;
* :func:`slice_projection_plan` — the Π the staged-vs-direct suite runs.

**The shapes come from the ontology; the values come from the fixtures.** Entity
classes, relationship types, and the classification attribute map are read from
``ontology.yaml``; operator parameters from ``controlplane.yaml``; the drawable
vocabulary and the curated graphs from ``edge_graphs.yaml``. No entity class, no
threshold and no policy version is written in this file — the No-Hardcoding
discipline applies to fixture code too (CLAUDE.md §6.4, CONTEXT.md).

**Two Hypothesis profiles** (04-RESEARCH.md Pitfall 6). ``ci`` is derandomized,
so a green build means the same examples were green and a failure reproduces
without a database of past runs; ``nightly`` is randomized and runs longer,
which is where new falsifying examples are supposed to come from. The profile
is selected by the ``HYPOTHESIS_PROFILE`` environment variable and defaults to
``ci`` — an unset variable must not silently buy randomness in a build whose
green is being trusted.

**The similarity corpus is fixed, and independent of what is drawn.** The index
ranks by ``entity_uri`` over a corpus built once from the drawable pool plus the
curated fixtures. Building it from the generated view instead would make the
index a function of the input, and an operator whose index changed with its
input is not a pure function of graph state.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from hypothesis import settings
from hypothesis import strategies as st

from ccf.contracts.canonical import content_hash
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.graph.protocols import (
    ClassificationAuthority,
    EntityRecord,
    GraphView,
    RelationshipRecord,
)
from ccf.operators.categories import (
    PolicyFilter,
    SimilaritySelect,
    TemporalAsOf,
    TraversalDescendants,
    TraversalNeighborhood,
)
from ccf.operators.params import (
    PolicyFilterParameters,
    SimilaritySelectParameters,
    TemporalAsOfParameters,
    TraversalDescendantsParameters,
    TraversalNeighborhoodParameters,
)
from ccf.operators.registry import OperatorRegistry
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.operators.base import OperatorOutput
from ccf.signal.envelope import SourceIdentity
from ccf.similarity.protocol import TokenOverlapIndex

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


def _load(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


ONTOLOGY = _load("ontology.yaml")
CONTROL = _load("controlplane.yaml")
HARNESS = _load("edge_graphs.yaml")
GENERATION = HARNESS["generation"]


def _instant(value: object) -> datetime:
    """Normalize a fixture timestamp to an explicit UTC instant.

    PyYAML resolves ``...Z`` timestamps to naive datetimes and the canonical
    serializer refuses those outright (D-IMPL-38). Attaching UTC is the
    loader's job; the fabric never guesses.
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


TENANT: str = ONTOLOGY["tenant_id"]
BOUNDARY: datetime = _instant(CONTROL["decision"]["temporal_boundary"])
ENTITY_CLASSES: tuple[str, ...] = tuple(
    rule["entity_class"] for rule in ONTOLOGY["entity_rules"]
)
RELATIONSHIP_RULES: tuple[tuple[str, str, str], ...] = tuple(
    (
        rule["relationship_type"],
        rule["subject_entity_class"],
        rule["object_entity_class"],
    )
    for rule in ONTOLOGY["relationship_rules"]
)
CLASSIFICATION_ATTRIBUTE: Mapping[str, str] = ONTOLOGY[
    "classification_attribute_by_class"
]
INSTANTS: tuple[datetime, ...] = tuple(
    _instant(value) for value in GENERATION["instants"]
)


# --- the drawable pool -----------------------------------------------------


def _pool(entity_class: str) -> tuple[str, ...]:
    """The URIs the generator may draw for ``entity_class``.

    A fixed pool rather than free-form URI generation: the similarity corpus has
    to be able to cover every URI that can be drawn, and a corpus that adapted to
    the draw would make the index a function of its own input.
    """
    return tuple(
        f"{TENANT}:{entity_class}:{index}"
        for index in range(GENERATION["pool_size_per_class"])
    )


ENTITY_POOL: Mapping[str, tuple[str, ...]] = {
    entity_class: _pool(entity_class) for entity_class in ENTITY_CLASSES
}


def _corpus() -> dict[tuple[str, str], str]:
    """``(tenant, entity_uri) -> text`` over the pool and the curated fixtures."""
    texts: tuple[str, ...] = tuple(GENERATION["corpus_texts"])
    corpus: dict[tuple[str, str], str] = {}
    for uris in ENTITY_POOL.values():
        for index, uri in enumerate(uris):
            corpus[(TENANT, uri)] = texts[index % len(texts)]
    for graph in HARNESS["graphs"]:
        for entity in graph["entities"]:
            text = entity.get("corpus_text")
            if text is not None:
                corpus[(TENANT, entity["entity_uri"])] = text
    return corpus


CORPUS_INDEX = TokenOverlapIndex(
    corpus=_corpus(),
    index_version=CONTROL["operator_parameters"]["similarity"]["index_version"],
)


# --- the shipped operators, parameterized from the Control Plane fixture ----


def shipped_operators() -> OperatorRegistry:
    """One instance of every operator the SDK ships, ready to compose.

    This is what makes the composition property's parametrization ``n²``
    *automatically*: the pairs are enumerated from this registry, so an
    operator that ships without a composition test is not reachable. Two
    shapes share the ``traversal`` category (ledger row ``24.5-L-06``): the
    undirected neighborhood and its directed sibling, parameterized from the
    same fixture values — the direction is the operator's, never a value.
    """
    params = CONTROL["operator_parameters"]
    registry = OperatorRegistry()
    registry.register(
        PolicyFilter(
            parameters=PolicyFilterParameters(
                permitted_policy_bundle_versions=frozenset(
                    {GENERATION["permitted_policy_bundle_version"]}
                ),
                classification_attribute_by_class=dict(CLASSIFICATION_ATTRIBUTE),
                permitted_classifications=frozenset(
                    params["policy"]["permitted_classifications"]
                ),
            )
        ),
        version=CONTROL["product_class"]["schema_version"],
    )
    registry.register(
        SimilaritySelect(
            parameters=SimilaritySelectParameters(
                query=params["similarity"]["query"],
                minimum_score_percent=params["similarity"]["minimum_score_percent"],
                ranked_entity_classes=frozenset(
                    params["similarity"]["ranked_entity_classes"]
                ),
            ),
            index=CORPUS_INDEX,
        ),
        version=CONTROL["product_class"]["schema_version"],
    )
    registry.register(
        TemporalAsOf(
            parameters=TemporalAsOfParameters(
                require_valid_at_boundary=params["temporal"][
                    "require_valid_at_boundary"
                ]
            )
        ),
        version=CONTROL["product_class"]["schema_version"],
    )
    registry.register(
        TraversalNeighborhood(
            parameters=TraversalNeighborhoodParameters(
                seed_entity_classes=frozenset(
                    params["traversal"]["seed_entity_classes"]
                ),
                relationship_types=frozenset(params["traversal"]["relationship_types"]),
                depth_limit=params["traversal"]["depth_limit"],
            )
        ),
        version=CONTROL["product_class"]["schema_version"],
    )
    registry.register(
        TraversalDescendants(
            parameters=TraversalDescendantsParameters(
                seed_entity_classes=frozenset(
                    params["traversal"]["seed_entity_classes"]
                ),
                relationship_types=frozenset(params["traversal"]["relationship_types"]),
                depth_limit=params["traversal"]["depth_limit"],
            )
        ),
        version=CONTROL["product_class"]["schema_version"],
    )
    return registry


# --- record construction ---------------------------------------------------


def _lineage(*, envelope_id: str, system_id: str, observed_at: datetime) -> frozenset[
    LineageEntry
]:
    return frozenset(
        {
            LineageEntry(
                source=SourceIdentity(system_id=system_id),
                envelope_id=envelope_id,
                observed_at=observed_at,
            )
        }
    )


def _entity_record(
    *,
    entity_uri: str,
    entity_class: str,
    classification: str,
    policy_bundle_version: str,
    observed_at: datetime,
    valid_from: datetime,
    valid_to: datetime | None,
    superseded_at: datetime | None,
    system_id: str,
) -> EntityRecord:
    """Build one persisted entity record the way L2 would have written it."""
    claim = EntityClaim(
        tenant_id=TENANT,
        entity_uri=entity_uri,
        entity_class=entity_class,
        attributes={CLASSIFICATION_ATTRIBUTE[entity_class]: classification},
        observed_at=observed_at,
        valid_from=valid_from,
        valid_to=valid_to,
        lineage=_lineage(
            envelope_id=f"{entity_uri}@{observed_at.isoformat()}",
            system_id=system_id,
            observed_at=observed_at,
        ),
    )
    claim_id = content_hash(claim)
    return EntityRecord(
        claim_id=claim_id,
        claim=claim,
        policy_bundle_version=policy_bundle_version,
        superseded_by=None if superseded_at is None else f"{claim_id}:successor",
        superseded_at=superseded_at,
    )


def _relationship_record(
    *,
    relationship_type: str,
    subject_uri: str,
    object_uri: str,
    policy_bundle_version: str,
    observed_at: datetime,
    valid_from: datetime,
    valid_to: datetime | None,
    superseded_at: datetime | None,
    system_id: str,
) -> RelationshipRecord:
    """Build one persisted edge record the way L2 would have written it."""
    claim = RelationshipClaim(
        tenant_id=TENANT,
        relationship_type=relationship_type,
        subject_uri=subject_uri,
        object_uri=object_uri,
        observed_at=observed_at,
        valid_from=valid_from,
        valid_to=valid_to,
        lineage=_lineage(
            envelope_id=f"{relationship_type}:{subject_uri}->{object_uri}",
            system_id=system_id,
            observed_at=observed_at,
        ),
    )
    claim_id = content_hash(claim)
    return RelationshipRecord(
        relationship_key=content_hash((relationship_type, subject_uri, object_uri)),
        claim_id=claim_id,
        claim=claim,
        policy_bundle_version=policy_bundle_version,
        superseded_by=None if superseded_at is None else f"{claim_id}:successor",
        superseded_at=superseded_at,
    )


#: SEC-023 (`D-IMPL-374` ruling (3) (a)): the classification authority the
#: generated fabric's L2 would enforce — every declared source system may
#: assert each class's classification attribute. The property harness reads no
#: store, so it stamps its views itself, as a composition root reading a store
#: directly would; a Policy operator refuses an unstamped view.
AUTHORITY: ClassificationAuthority = ClassificationAuthority(
    governed={
        entity_class: {attribute: frozenset(GENERATION["source_systems"])}
        for entity_class, attribute in CLASSIFICATION_ATTRIBUTE.items()
    },
    written={
        entity_class: frozenset({attribute})
        for entity_class, attribute in CLASSIFICATION_ATTRIBUTE.items()
    },
)


def _view(
    entities: tuple[EntityRecord, ...], relationships: tuple[RelationshipRecord, ...]
) -> GraphView:
    """Assemble a view with the deterministic record ordering the contract states."""
    return GraphView(
        tenant_id=TENANT,
        as_of=BOUNDARY,
        entities=tuple(sorted(entities, key=lambda r: r.claim.entity_uri)),
        relationships=tuple(sorted(relationships, key=lambda r: r.relationship_key)),
    ).with_classification_authority(AUTHORITY)


# --- the strategies --------------------------------------------------------


@st.composite
def banking_graph_states(draw: st.DrawFn) -> GraphView:
    """Draw a banking-shaped :class:`GraphView`.

    Each drawn state carries entities across the ontology's classes with drawn
    classifications and policy-bundle versions (so Policy has something to
    exclude), bitemporal instants straddling the decision boundary on both axes
    (so Temporal has something to cut), and typed edges between drawn endpoints
    (so Traversal has something bounded to walk). Lineage is present on every
    claim, because a claim without it is not a claim the fabric could have
    written.
    """
    instant = st.sampled_from(INSTANTS)
    classification = st.sampled_from(tuple(GENERATION["classifications"]))
    bundle = st.sampled_from(tuple(GENERATION["policy_bundle_versions"]))
    system = st.sampled_from(tuple(GENERATION["source_systems"]))

    entities: list[EntityRecord] = []
    drawn_by_class: dict[str, list[str]] = {}
    for entity_class in ENTITY_CLASSES:
        uris = draw(
            st.lists(
                st.sampled_from(ENTITY_POOL[entity_class]),
                unique=True,
                max_size=len(ENTITY_POOL[entity_class]),
            )
        )
        drawn_by_class[entity_class] = uris
        for uri in uris:
            observed_at = draw(instant)
            entities.append(
                _entity_record(
                    entity_uri=uri,
                    entity_class=entity_class,
                    classification=draw(classification),
                    policy_bundle_version=draw(bundle),
                    observed_at=observed_at,
                    valid_from=draw(instant),
                    valid_to=draw(st.none() | instant),
                    superseded_at=draw(st.none() | instant),
                    system_id=draw(system),
                )
            )

    relationships: list[RelationshipRecord] = []
    for relationship_type, subject_class, object_class in RELATIONSHIP_RULES:
        subjects = drawn_by_class[subject_class]
        objects = drawn_by_class[object_class]
        if not subjects or not objects:
            continue
        pairs = draw(
            st.lists(
                st.tuples(st.sampled_from(subjects), st.sampled_from(objects)),
                unique=True,
                max_size=len(subjects) * len(objects),
            )
        )
        for subject_uri, object_uri in pairs:
            relationships.append(
                _relationship_record(
                    relationship_type=relationship_type,
                    subject_uri=subject_uri,
                    object_uri=object_uri,
                    policy_bundle_version=draw(bundle),
                    observed_at=draw(instant),
                    valid_from=draw(instant),
                    valid_to=draw(st.none() | instant),
                    superseded_at=draw(st.none() | instant),
                    system_id=draw(system),
                )
            )

    return _view(tuple(entities), tuple(relationships))


# --- the curated edge graphs -----------------------------------------------


@dataclass(frozen=True)
class CuratedGraph:
    """One fixture-declared edge-case graph, with the name D-14 knows it by."""

    name: str
    view: GraphView


def curated_edge_graphs() -> tuple[CuratedGraph, ...]:
    """Load the curated edge cases from ``edge_graphs.yaml``, in file order."""
    system_id = GENERATION["source_systems"][0]
    graphs: list[CuratedGraph] = []
    for declared in HARNESS["graphs"]:
        entities = tuple(
            _entity_record(
                entity_uri=entity["entity_uri"],
                entity_class=entity["entity_class"],
                classification=entity["classification"],
                policy_bundle_version=entity["policy_bundle_version"],
                observed_at=_instant(entity["observed_at"]),
                valid_from=_instant(entity["valid_from"]),
                valid_to=(
                    None
                    if entity.get("valid_to") is None
                    else _instant(entity["valid_to"])
                ),
                superseded_at=(
                    None
                    if entity.get("superseded_at") is None
                    else _instant(entity["superseded_at"])
                ),
                system_id=system_id,
            )
            for entity in declared["entities"]
        )
        relationships = tuple(
            _relationship_record(
                relationship_type=edge["relationship_type"],
                subject_uri=edge["subject_uri"],
                object_uri=edge["object_uri"],
                policy_bundle_version=edge["policy_bundle_version"],
                observed_at=_instant(edge["observed_at"]),
                valid_from=_instant(edge["valid_from"]),
                valid_to=(
                    None if edge.get("valid_to") is None else _instant(edge["valid_to"])
                ),
                superseded_at=(
                    None
                    if edge.get("superseded_at") is None
                    else _instant(edge["superseded_at"])
                ),
                system_id=system_id,
            )
            for edge in declared["relationships"]
        )
        graphs.append(
            CuratedGraph(name=declared["name"], view=_view(entities, relationships))
        )
    return tuple(graphs)


# --- the projection the staged-vs-direct suite runs -------------------------


class SliceProjectionPlan:
    """The harness's Π: a deterministic reading of the reconciled subgraph.

    Deliberately thin. The staged-vs-direct property is about the *engine's*
    two-stage execution, so a projection doing interesting work would only make
    a failure harder to attribute.
    """

    def __init__(self, *, plan_id: str, required: tuple[str, ...]) -> None:
        self._plan_id = plan_id
        self._required = required

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "entity_count": len(view.entities),
                "entities": [
                    {
                        "entity_uri": record.claim.entity_uri,
                        "entity_class": record.claim.entity_class,
                    }
                    for record in view.entities
                ],
                "relationship_types": sorted(
                    {edge.claim.relationship_type for edge in view.relationships}
                ),
            },
        )


def slice_projection_plan(required: tuple[str, ...]) -> SliceProjectionPlan:
    """The projection plan declaring ``required``, identified by the fixture."""
    return SliceProjectionPlan(
        plan_id=CONTROL["product_class"]["plan_id"], required=required
    )


def harness_perspective() -> Perspective:
    """The fixture's perspective — a value, so it comes from the fixture."""
    declared = CONTROL["perspective"]
    return Perspective(
        principal_id=declared["principal_id"], role=declared["role"]
    )


# --- Hypothesis profiles ---------------------------------------------------

settings.register_profile("ci", derandomize=True, deadline=None, max_examples=50)
settings.register_profile("nightly", derandomize=False, deadline=None, max_examples=500)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))
