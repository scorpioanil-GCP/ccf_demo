"""The GraphQuery corpus generator — the shapes every adapter is held to (D-05).

Hypothesis strategies over ``(graph content, query specs)`` cases for the
differential suite (``tests/conformance/test_substrate_differential.py``).
Each case carries *claims* — written through booted L2 by the consuming
test, never through a writer this module constructs — plus query
specifications resolved into frozen :class:`~ccf.graph.protocols.GraphQuery`
values against the booted fabric's own stamped policy-bundle version.

The deliberately generated shapes, and the defects they exist to catch:

* **Mixed-admissibility multi-hop paths** (RESEARCH Pitfall 1) — the
  seed - excluded - target chain where hop admissibility must prune before
  walking, plus drawn per-node classifications over longer paths.
* **The D-IMPL-87 ``allowed_entities`` shapes** (RESEARCH Pitfall 2 — the
  resurrection defect the uniform rule closes, `GQ-15` at
  docs/GRAPH_QUERY_SEMANTICS.md:300): the RESURRECTION chain (seed and
  target in the set, intermediate out of it — the target must not be
  reached), the empty frozenset (empty answer), the full-universe set
  (byte-identical to ``None``), and allowed sets combined with each
  predicate family independently.
* **Depth 0/1/N and mixed-direction chains** (RESEARCH Pitfall 3 — the
  later-Mongo parity hazard): the fixture ontology's edges already point
  against the walk on alternating hops (``guarantees`` and ``governs`` aim
  spoke-to-hub), so every multi-hop case is a mixed-direction case.
* **Orphaned nodes** — entities with no relationships — and the DANGLING
  first-class edge (both endpoints entity-claim-less), which the degenerate
  everything-question must keep (`GQ-05` at
  docs/GRAPH_QUERY_SEMANTICS.md:122; INV-CH7-20) while any constrained
  answer endpoint-closes it away (the DI-15.2-01 closure-scoping fact,
  pinned differentially).
* **Self-loops** — an entity related to itself; the walk must neither loop
  nor drop the edge.
* **Absent seeds, empty answers, degenerate and single-family questions** —
  the edge semantics the prose decides (`GQ-03`, `GQ-23`).

Strategy discipline inherited from ``tests/properties/strategies.py``: the
shapes come from the ontology fixtures, the values from the fixture YAML —
no entity class, no classification, no bundle version and no relationship
type is written in this file. Importing ``strategies`` also registers the
two Hypothesis profiles, so the derandomized ``ci`` profile is the default
here exactly as in the property suites.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hypothesis import strategies as st

from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.graph.protocols import GraphQuery, TraversalSpec
from ccf.signal.envelope import SourceIdentity

from tests.conformance.test_substrate_properties import (
    CHAIN_TRAVERSE,
    MID_CLASS,
    PERMITTED_CLASSIFICATION,
    PERMITTED_CLASSIFICATIONS,
    SEED_CLASS,
    TARGET_CLASS,
    _RULE_A,
    _RULE_B,
)
from tests.properties.strategies import (
    CLASSIFICATION_ATTRIBUTE,
    CONTROL,
    ENTITY_POOL,
    GENERATION,
    INSTANTS,
    TENANT,
)

EARLY, ON_BOUNDARY, LATE = INSTANTS

SEED_CLASSES: frozenset[str] = frozenset(
    CONTROL["operator_parameters"]["traversal"]["seed_entity_classes"]
)
RELATIONSHIP_TYPES: frozenset[str] = frozenset(
    CONTROL["operator_parameters"]["traversal"]["relationship_types"]
)
SYSTEM: str = GENERATION["source_systems"][0]
CLASSIFICATIONS: tuple[str, ...] = tuple(GENERATION["classifications"])


# --- claim construction (values from fixtures, written through booted L2) ----


def _lineage(*, envelope_id: str, observed_at: datetime) -> frozenset[LineageEntry]:
    return frozenset(
        {
            LineageEntry(
                source=SourceIdentity(system_id=SYSTEM),
                envelope_id=envelope_id,
                observed_at=observed_at,
            )
        }
    )


def entity_claim(
    *,
    entity_uri: str,
    entity_class: str,
    classification: str,
    observed_at: datetime,
    valid_to: datetime | None = None,
    tenant_id: str = TENANT,
) -> EntityClaim:
    """One entity claim as a source would deliver it, fixture-shaped."""
    return EntityClaim(
        tenant_id=tenant_id,
        entity_uri=entity_uri,
        entity_class=entity_class,
        attributes={CLASSIFICATION_ATTRIBUTE[entity_class]: classification},
        observed_at=observed_at,
        valid_from=observed_at,
        valid_to=valid_to,
        lineage=_lineage(
            envelope_id=f"{entity_uri}@{observed_at.isoformat()}",
            observed_at=observed_at,
        ),
    )


def relationship_claim(
    *,
    relationship_type: str,
    subject_uri: str,
    object_uri: str,
    observed_at: datetime,
    valid_to: datetime | None = None,
    tenant_id: str = TENANT,
) -> RelationshipClaim:
    """One typed edge claim as a source would deliver it, fixture-shaped."""
    return RelationshipClaim(
        tenant_id=tenant_id,
        relationship_type=relationship_type,
        subject_uri=subject_uri,
        object_uri=object_uri,
        attributes={},
        observed_at=observed_at,
        valid_from=observed_at,
        valid_to=valid_to,
        lineage=_lineage(
            envelope_id=f"{relationship_type}:{subject_uri}->{object_uri}"
            f"@{observed_at.isoformat()}",
            observed_at=observed_at,
        ),
    )


def chain_claims(
    *, mid_classification: str, index: int = 0, observed_at: datetime = EARLY
) -> tuple[tuple[EntityClaim, ...], tuple[RelationshipClaim, ...]]:
    """The seed - intermediate - target chain, as admissible-through-L2 claims.

    The claim twin of ``tests/conformance/test_substrate_properties._chain``:
    same ontology-discovered classes and edge types, same two-hop
    mixed-direction shape (the second edge points target-to-mid), chosen
    ``index`` selecting distinct pool URIs so one fabric can hold an
    excluded chain and its admissible control side by side.
    """
    seed_uri = ENTITY_POOL[SEED_CLASS][index]
    mid_uri = ENTITY_POOL[MID_CLASS][index]
    target_uri = ENTITY_POOL[TARGET_CLASS][index]
    entities = (
        entity_claim(
            entity_uri=seed_uri,
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=observed_at,
        ),
        entity_claim(
            entity_uri=mid_uri,
            entity_class=MID_CLASS,
            classification=mid_classification,
            observed_at=observed_at,
        ),
        entity_claim(
            entity_uri=target_uri,
            entity_class=TARGET_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=observed_at,
        ),
    )
    relationships = (
        relationship_claim(
            relationship_type=_RULE_A[0],
            subject_uri=seed_uri,
            object_uri=mid_uri,
            observed_at=observed_at,
        ),
        relationship_claim(
            relationship_type=_RULE_B[0],
            subject_uri=target_uri,
            object_uri=mid_uri,
            observed_at=observed_at,
        ),
    )
    return entities, relationships


def chain_uris(index: int = 0) -> tuple[str, str, str]:
    """The (seed, mid, target) URIs of :func:`chain_claims` at ``index``."""
    return (
        ENTITY_POOL[SEED_CLASS][index],
        ENTITY_POOL[MID_CLASS][index],
        ENTITY_POOL[TARGET_CLASS][index],
    )


# --- query specification -----------------------------------------------------

#: Sentinel: resolve ``allowed_entities`` to the case's full entity universe.
ALLOWED_UNIVERSE = "universe"


@dataclass(frozen=True)
class QuerySpec:
    """One question, minus the facts only a booted fabric knows.

    ``policy=True`` resolves to the whole policy family (`GQ-02`) with the
    booted worker's own stamped bundle version — a corpus case cannot know
    that version at generation time, so it is bound at
    :func:`build_queries` time. ``allowed`` is a URI set, ``None``, the
    empty frozenset (a different fact than ``None`` — `GQ-04`), or the
    :data:`ALLOWED_UNIVERSE` sentinel resolved against the case's entity
    universe.
    """

    as_of: datetime
    policy: bool = False
    require_valid_at_boundary: bool | None = None
    traverse: TraversalSpec | None = None
    seeds: frozenset[str] | None = None
    allowed: frozenset[str] | str | None = None


@dataclass(frozen=True)
class CorpusCase:
    """One generated case: graph content (as claims) plus its questions."""

    name: str
    entities: tuple[EntityClaim, ...]
    relationships: tuple[RelationshipClaim, ...]
    query_specs: tuple[QuerySpec, ...]

    @property
    def universe(self) -> frozenset[str]:
        """Every entity URI the case writes — the full-universe allowed set."""
        return frozenset(claim.entity_uri for claim in self.entities)


def build_queries(
    case: CorpusCase, *, policy_bundle_version: str
) -> tuple[GraphQuery, ...]:
    """Resolve the case's specs into frozen queries against the live fabric.

    ``policy_bundle_version`` is the booted worker's own stamped version —
    the only version persisted records can carry, so the only one a policy
    family can meaningfully admit.
    """
    queries: list[GraphQuery] = []
    for spec in case.query_specs:
        allowed: frozenset[str] | None
        if spec.allowed == ALLOWED_UNIVERSE:
            allowed = case.universe
        else:
            assert not isinstance(spec.allowed, str)
            allowed = spec.allowed
        policy_family: dict[str, object] = {}
        if spec.policy:
            policy_family = {
                "permitted_policy_bundle_versions": frozenset(
                    {policy_bundle_version}
                ),
                "classification_attribute_by_class": dict(
                    CLASSIFICATION_ATTRIBUTE
                ),
                "permitted_classifications": frozenset(
                    PERMITTED_CLASSIFICATIONS
                ),
            }
        queries.append(
            GraphQuery(
                tenant_id=TENANT,
                as_of=spec.as_of,
                require_valid_at_boundary=spec.require_valid_at_boundary,
                traverse=spec.traverse,
                seeds=spec.seeds,
                allowed_entities=allowed,
                **policy_family,  # type: ignore[arg-type]
            )
        )
    return tuple(queries)


def _traverse(depth: int) -> TraversalSpec:
    """The fixture-declared traverse family at ``depth`` hops."""
    return TraversalSpec(
        seed_entity_classes=SEED_CLASSES,
        relationship_types=RELATIONSHIP_TYPES,
        depth_limit=depth,
    )


# --- the named strategies ----------------------------------------------------


@st.composite
def mixed_admissibility_path_cases(draw: st.DrawFn) -> CorpusCase:
    """Pitfall-1 shapes: multi-hop paths through drawn-admissibility middles.

    The chain's middle draws any fixture classification — permitted,
    excluded, or the empty "carries no usable classification" value — and
    the queries combine the policy family with walks at drawn depth, so hop
    admissibility (prune before walking, `GQ-13`) is exercised on every
    drawn middle, alongside a policy-only and a walk-only control.
    """
    mid_classification = draw(st.sampled_from(CLASSIFICATIONS))
    observed_at = draw(st.sampled_from(INSTANTS))
    entities, relationships = chain_claims(
        mid_classification=mid_classification, observed_at=observed_at
    )
    depth = draw(st.integers(min_value=0, max_value=3))
    specs = (
        QuerySpec(as_of=ON_BOUNDARY, policy=True, traverse=CHAIN_TRAVERSE),
        QuerySpec(as_of=ON_BOUNDARY, policy=True, traverse=_traverse(depth)),
        QuerySpec(as_of=ON_BOUNDARY, policy=True),
        QuerySpec(as_of=ON_BOUNDARY, traverse=CHAIN_TRAVERSE),
    )
    return CorpusCase(
        name="mixed-admissibility-path",
        entities=entities,
        relationships=relationships,
        query_specs=specs,
    )


@st.composite
def depth_cases(draw: st.DrawFn) -> CorpusCase:
    """Depth-0/1/N walks, absent seeds, and empty-answer boundaries.

    Depth 0 must answer the walk starting points only; an as-of before any
    observation must answer empty (`GQ-23`); a seed URI naming no in-scope
    entity contributes no start (`GQ-11`) — drawn from the pool but never
    written, so it is absent from the graph rather than merely misspelled.
    """
    observed_at = draw(st.sampled_from((ON_BOUNDARY, LATE)))
    entities, relationships = chain_claims(
        mid_classification=PERMITTED_CLASSIFICATION, observed_at=observed_at
    )
    seed_uri, _, _ = chain_uris()
    absent_uri = ENTITY_POOL[SEED_CLASS][-1]  # in the pool, never written
    depth = draw(st.integers(min_value=2, max_value=4))
    specs = (
        QuerySpec(as_of=ON_BOUNDARY, traverse=_traverse(0)),
        QuerySpec(as_of=ON_BOUNDARY, traverse=_traverse(1)),
        QuerySpec(as_of=ON_BOUNDARY, traverse=_traverse(depth)),
        # The empty-answer boundary: nothing was observed at or before EARLY
        # when the content is written later.
        QuerySpec(as_of=EARLY, traverse=_traverse(depth)),
        # Absent seeds: a walk whose explicit start names nothing in scope.
        QuerySpec(
            as_of=ON_BOUNDARY,
            traverse=_traverse(depth),
            seeds=frozenset({absent_uri}),
        ),
        QuerySpec(
            as_of=ON_BOUNDARY,
            traverse=_traverse(depth),
            seeds=frozenset({seed_uri}),
        ),
        # Single-family: temporal only.
        QuerySpec(as_of=ON_BOUNDARY, require_valid_at_boundary=True),
    )
    return CorpusCase(
        name="depth-and-seeds",
        entities=entities,
        relationships=relationships,
        query_specs=specs,
    )


@st.composite
def orphan_cases(draw: st.DrawFn) -> CorpusCase:
    """Orphaned nodes and the dangling first-class edge.

    Orphaned entities (no relationships at all) must survive degenerate and
    filter answers and contribute no walk expansion. The dangling edge —
    both endpoints entity-claim-less — is state, not a leak, in the
    degenerate everything-question (`GQ-05`; INV-CH7-20, the DI-15.2-01
    closure scoping) and endpoint-closes away on any constrained answer.
    """
    orphan_class = draw(st.sampled_from(tuple(ENTITY_POOL)))
    orphan_uri = ENTITY_POOL[orphan_class][0]
    classification = draw(st.sampled_from(CLASSIFICATIONS))
    entities = (
        entity_claim(
            entity_uri=orphan_uri,
            entity_class=orphan_class,
            classification=classification,
            observed_at=EARLY,
        ),
    )
    # The dangling edge: endpoints drawn from pools no entity claim covers.
    dangling = relationship_claim(
        relationship_type=_RULE_A[0],
        subject_uri=ENTITY_POOL[SEED_CLASS][-1],
        object_uri=ENTITY_POOL[MID_CLASS][-1],
        observed_at=EARLY,
    )
    specs = (
        QuerySpec(as_of=ON_BOUNDARY),
        QuerySpec(as_of=ON_BOUNDARY, policy=True),
        QuerySpec(as_of=ON_BOUNDARY, traverse=_traverse(2)),
        QuerySpec(as_of=ON_BOUNDARY, require_valid_at_boundary=True),
    )
    return CorpusCase(
        name="orphan-and-dangling-edge",
        entities=entities,
        relationships=(dangling,),
        query_specs=specs,
    )


@st.composite
def self_loop_cases(draw: st.DrawFn) -> CorpusCase:
    """An entity related to itself: the walk neither loops nor drops the edge."""
    loop_class = draw(st.sampled_from((SEED_CLASS, MID_CLASS)))
    loop_uri = ENTITY_POOL[loop_class][0]
    loop_type = draw(st.sampled_from(tuple(RELATIONSHIP_TYPES)))
    entities = (
        entity_claim(
            entity_uri=loop_uri,
            entity_class=loop_class,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
        ),
    )
    relationships = (
        relationship_claim(
            relationship_type=loop_type,
            subject_uri=loop_uri,
            object_uri=loop_uri,
            observed_at=EARLY,
        ),
    )
    specs = (
        QuerySpec(as_of=ON_BOUNDARY),
        QuerySpec(as_of=ON_BOUNDARY, traverse=_traverse(0)),
        QuerySpec(as_of=ON_BOUNDARY, traverse=_traverse(1)),
        QuerySpec(
            as_of=ON_BOUNDARY,
            traverse=_traverse(1),
            allowed=frozenset({loop_uri}),
        ),
    )
    return CorpusCase(
        name="self-loop",
        entities=entities,
        relationships=relationships,
        query_specs=specs,
    )


@st.composite
def allowed_entities_cases(draw: st.DrawFn) -> CorpusCase:
    """The D-IMPL-87 shapes — where the resurrection defect would hide.

    (a) the RESURRECTION chain: seed and target in the set, the intermediate
    out of it — everything policy-admissible, so only the uniform rule
    (`GQ-15`) stands between the walk and the target; (b) the empty
    frozenset (the empty answer, `GQ-04`); (c) the full entity universe
    (byte-identical to ``None``); (d) allowed sets combined with each
    predicate family independently. Every adapter is held byte-identical to
    the fallback on exactly these shapes.
    """
    observed_at = draw(st.sampled_from((EARLY, ON_BOUNDARY)))
    entities, relationships = chain_claims(
        mid_classification=PERMITTED_CLASSIFICATION, observed_at=observed_at
    )
    seed_uri, mid_uri, target_uri = chain_uris()
    resurrection = frozenset({seed_uri, target_uri})
    drawn_allowed = frozenset(
        draw(
            st.sets(
                st.sampled_from((seed_uri, mid_uri, target_uri)), max_size=3
            )
        )
    )
    specs = (
        # (a) the resurrection chain — the amendment's named defect shape.
        QuerySpec(
            as_of=ON_BOUNDARY, traverse=CHAIN_TRAVERSE, allowed=resurrection
        ),
        QuerySpec(
            as_of=ON_BOUNDARY,
            traverse=CHAIN_TRAVERSE,
            allowed=frozenset({seed_uri, mid_uri, target_uri}),
        ),
        # (b) the empty set answers the empty view.
        QuerySpec(as_of=ON_BOUNDARY, allowed=frozenset()),
        # (c) the full universe is byte-identical to None — both are asked.
        QuerySpec(as_of=ON_BOUNDARY, allowed=ALLOWED_UNIVERSE),
        QuerySpec(as_of=ON_BOUNDARY, allowed=None),
        # (d) allowed x each family independently.
        QuerySpec(as_of=ON_BOUNDARY, allowed=drawn_allowed, policy=True),
        QuerySpec(
            as_of=ON_BOUNDARY,
            allowed=drawn_allowed,
            require_valid_at_boundary=True,
        ),
        QuerySpec(
            as_of=ON_BOUNDARY, allowed=drawn_allowed, traverse=_traverse(2)
        ),
    )
    return CorpusCase(
        name="allowed-resurrection-chain",
        entities=entities,
        relationships=relationships,
        query_specs=specs,
    )


@st.composite
def degenerate_and_family_cases(draw: st.DrawFn) -> CorpusCase:
    """Degenerate everything-questions and one-family questions over drawn content.

    Content is drawn loosely — per-entity class, classification and instant,
    plus rule-conforming edges between drawn endpoints — and every question
    is either the degenerate one (`GQ-05`) or a single predicate family, at
    a drawn boundary, including boundaries that empty the answer.
    """
    instant = st.sampled_from(INSTANTS)
    classification = st.sampled_from(CLASSIFICATIONS)
    entities: list[EntityClaim] = []
    drawn_by_class: dict[str, list[str]] = {}
    for entity_class, pool in ENTITY_POOL.items():
        uris = draw(
            st.lists(st.sampled_from(pool), unique=True, max_size=len(pool))
        )
        drawn_by_class[entity_class] = uris
        for uri in uris:
            entities.append(
                entity_claim(
                    entity_uri=uri,
                    entity_class=entity_class,
                    classification=draw(classification),
                    observed_at=draw(instant),
                    valid_to=draw(st.none() | instant),
                )
            )
    relationships: list[RelationshipClaim] = []
    for relationship_type, subject_class, object_class in (
        _RULE_A,
        _RULE_B,
    ):
        subjects = drawn_by_class[subject_class]
        objects = drawn_by_class[object_class]
        if not subjects or not objects:
            continue
        pairs = draw(
            st.lists(
                st.tuples(st.sampled_from(subjects), st.sampled_from(objects)),
                unique=True,
                max_size=3,
            )
        )
        for subject_uri, object_uri in pairs:
            relationships.append(
                relationship_claim(
                    relationship_type=relationship_type,
                    subject_uri=subject_uri,
                    object_uri=object_uri,
                    observed_at=draw(instant),
                )
            )
    boundary = draw(instant)
    specs = (
        QuerySpec(as_of=boundary),
        QuerySpec(as_of=EARLY),
        QuerySpec(as_of=boundary, policy=True),
        QuerySpec(as_of=boundary, require_valid_at_boundary=True),
        QuerySpec(as_of=boundary, traverse=_traverse(2)),
    )
    return CorpusCase(
        name="degenerate-and-single-family",
        entities=tuple(entities),
        relationships=tuple(relationships),
        query_specs=specs,
    )


def corpus_cases() -> st.SearchStrategy[CorpusCase]:
    """The whole corpus: one drawn case from the named shape families."""
    return st.one_of(
        mixed_admissibility_path_cases(),
        depth_cases(),
        orphan_cases(),
        self_loop_cases(),
        allowed_entities_cases(),
        degenerate_and_family_cases(),
    )
