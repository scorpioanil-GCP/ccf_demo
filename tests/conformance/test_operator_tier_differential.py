"""The operator tier held to the query tier and the reference (D-05, D-08, P-2).

Dave's P-2, verbatim (``24.8-RULINGS.md`` §3, recorded at ``D-IMPL-267``):
*"Traversal semantics are execution-path invariant. In-process, fallback, and
pushed implementations may execute differently, but the same question over the
same pinned state must produce the same canonical traversal result."* The
sibling suite ``tests/conformance/test_substrate_differential.py`` already
holds every registered backend byte-identical to the fallback. It cannot see
the divergence this module exists for, because both of its columns live at the
query tier: the operator tier — ``src/ccf/operators/categories.py::TraversalNeighborhood``
and ``src/ccf/operators/categories.py::TraversalDescendants`` applied in
process over a raw ``as_of`` view — is a THIRD answerer of the same question,
and it is the one that walks persisted edges instead of admitted ones.

The shape under test is the unresolved reference (ledger row ``CP04-G-28``):
a claimed entity joined to another claimed entity through a URI that no
entity claim covers. Such an edge is legal persisted state — edges are
first-class claims (whitepaper §7.3, INV-CH7-20; `GQ-05` at
docs/GRAPH_QUERY_SEMANTICS.md:122) and L2 admits one without checking either
endpoint — but the endpoint is an *unresolved reference*, not a traversal
member: a constrained answer endpoint-closes it away before walking (`GQ-16`
at docs/GRAPH_QUERY_SEMANTICS.md:316), so the path that ran through it does
not exist for the walk (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261) and
neither does any depth or cycle it would have created (``D-IMPL-268``:
*"A phantom endpoint must not consume depth, create a path, or participate in
a cycle even if the eventual returned entity set would coincidentally
match."*). Traversal itself is whitepaper §7.4 (INV-CH7-24, INV-CH7-40);
`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201 is its clause.

**Scope: three answerers of one traverse question, compared by bytes.** The
operator tier (``apply`` over ``reader.as_of``), the query tier
(``reader.query``) and the reference (``ccf.graph.fallback.answer`` over the
same as-of state, the sibling's ``_expected``). Nothing here asserts an
engine-level fact — not a segment split, not a pin sequence, not a plan
shape; those belong to ``tests/properties/test_staged_vs_direct.py`` and to
the engine's own suite. Equality is
``ccf.contracts.canonical.canonical_bytes`` and only that: Dave's Q5 ruled
byte-identical canonical results rather than equal entity sets, because
ordering drift poisons content addressing even when the membership agrees.
A URI-set statement appears here only as a *readable* restatement beside a
byte assertion, never as the assertion.

Disciplines inherited from the sibling and from
``tests/conformance/test_graphstore.py``:

* **Nothing constructs a writer.** Every case is written through the booted
  L2 admission path (the sibling's ``_write_case``).
* **The backend params are imported, never copied** — a newly registered
  adapter joins this suite and the sibling in the same edit.
* **The oracle is ``fallback.answer``, never ``fallback._walk``.** ``_walk``
  called directly skips ``answer``'s endpoint closure, so it agrees with the
  shipped operator on exactly the graphs this module is about.
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck, given, settings

from ccf.contracts.canonical import canonical_bytes
from ccf.graph.protocols import GraphQuery, GraphView, TraversalDirection, TraversalSpec
from ccf.operators.categories import TraversalDescendants, TraversalNeighborhood
from ccf.operators.params import (
    TraversalDescendantsParameters,
    TraversalNeighborhoodParameters,
)

from tests.conformance.query_corpus import (
    EARLY,
    MID_CLASS,
    ON_BOUNDARY,
    RELATIONSHIP_TYPES,
    SEED_CLASS,
    SEED_CLASSES,
    TARGET_CLASS,
    TENANT,
    UNRESOLVED_REFERENCE_VARIANTS,
    UNRESOLVED_URI,
    CorpusCase,
    build_queries,
    entity_claim,
    unresolved_reference_case,
    unresolved_reference_cases,
)
from tests.conformance.test_substrate_differential import (
    BACKEND_PARAMS,
    _expected,
    _frozen_at,
    _write_case,
)
from tests.conformance.test_substrate_properties import PERMITTED_CLASSIFICATION

if TYPE_CHECKING:
    from datetime import datetime

    from ccf.boot import FabricHandle
    from ccf.operators.base import OperatorOutput

pytestmark = pytest.mark.conformance

#: Both walk directions, as the two operators emit them: ``TraversalNeighborhood``
#: is undirected, ``TraversalDescendants`` forward. Not a tuning value — the
#: whole domain of ``TraversalDirection``.
DIRECTIONS: tuple[TraversalDirection, ...] = ("undirected", "forward")


@pytest.fixture(params=BACKEND_PARAMS)
def backend_name(request: pytest.FixtureRequest) -> str:
    """Which substrate this run answers from — no test body knows or cares.

    The four-line fixture is redefined here over the IMPORTED
    ``tests/conformance/test_substrate_differential.py::BACKEND_PARAMS``
    (the sibling's own fixture is module-local), so the params themselves
    live in exactly one place and the ``CCF_REQUIRE_*`` session fixtures
    skip-or-fail here precisely as they do there.
    """
    return str(request.param)


# --- the three answerers ------------------------------------------------------


def _operator_for(
    traverse: TraversalSpec,
) -> TraversalNeighborhood | TraversalDescendants:
    """The operator whose ``read_intent()`` renders exactly ``traverse`` (D-05).

    The direction is fixed by which operator emitted the spec, never by a
    parameter value (``src/ccf/graph/protocols.py::TraversalSpec``), so the
    mapping is one-to-one: undirected is the neighborhood, forward the
    descendants. The parameters mirror the spec field-for-field, and the
    equality below is RESEARCH § Priority 4's first fairness condition made
    an assertion rather than a comment — a differential comparing two tiers
    asked different questions would measure nothing.
    """
    operator: TraversalNeighborhood | TraversalDescendants
    if traverse.direction == "undirected":
        operator = TraversalNeighborhood(
            parameters=TraversalNeighborhoodParameters(
                seed_entity_classes=traverse.seed_entity_classes,
                relationship_types=traverse.relationship_types,
                depth_limit=traverse.depth_limit,
                admitted_entity_classes=traverse.admitted_entity_classes,
            )
        )
    else:
        operator = TraversalDescendants(
            parameters=TraversalDescendantsParameters(
                seed_entity_classes=traverse.seed_entity_classes,
                relationship_types=traverse.relationship_types,
                depth_limit=traverse.depth_limit,
                admitted_entity_classes=traverse.admitted_entity_classes,
            )
        )
    intent = operator.read_intent()
    assert intent.traverse == traverse, (
        "the operator column is answering a different question than the query"
        f" column: intent {intent.traverse!r} vs query {traverse!r}"
    )
    return operator


def _operator_output(
    handle: "FabricHandle",
    operator: TraversalNeighborhood | TraversalDescendants,
    at: "datetime",
) -> "OperatorOutput":
    """Apply the operator over the RAW as-of view at the query's own boundary.

    The as-of view is where a dangling edge is still state (`GQ-05` at
    docs/GRAPH_QUERY_SEMANTICS.md:122; INV-CH7-20) — which is the whole
    point: the operator tier is the only answerer that sees the graph
    unclosed. Reading at the boundary the query names is RESEARCH § Priority
    4's second fairness condition: ``_substitute`` copies ``view.as_of`` into
    the output, so a view read at another instant would differ in bytes for a
    reason that has nothing to do with traversal.
    """
    view = handle.reader.as_of(tenant_id=TENANT, at=at)
    return operator.apply(
        view=view, tenant_id=TENANT, temporal_boundary=at, upstream=()
    )


def _three_views(
    handle: "FabricHandle", q: GraphQuery
) -> tuple[GraphView, GraphView, GraphView]:
    """``(operator tier, query tier, reference)`` for one fair question."""
    assert q.traverse is not None, "a three-way comparison needs a walk"
    operator = _operator_for(q.traverse)
    return (
        _operator_output(handle, operator, q.as_of).view,
        handle.reader.query(q),
        _expected(handle, q),
    )


def _uris(view: GraphView) -> set[str]:
    """The answered entity URIs — a readable restatement, never the assertion."""
    return {record.claim.entity_uri for record in view.entities}


def _edges(view: GraphView) -> set[tuple[str, str]]:
    """The answered edges as ``(subject, object)`` — readable, never the assertion."""
    return {
        (record.claim.subject_uri, record.claim.object_uri)
        for record in view.relationships
    }


def _assert_operator_tier(
    operator_view: GraphView,
    expected: GraphView,
    *,
    backend: str,
    case_name: str,
) -> None:
    """The operator tier renders the reference's answer, byte for byte (P-2).

    Held separately from the query-tier equality so the two reds are never
    confusable: this message names the *operator tier*, the other names the
    *query tier*, and a run's failure text alone says which implementation
    moved.
    """
    assert canonical_bytes(operator_view) == canonical_bytes(expected), (
        f"the operator tier diverged from the reference on {case_name!r}"
        f" under {backend}: operator answered {sorted(_uris(operator_view))}"
        f" with edges {sorted(_edges(operator_view))}, reference answered"
        f" {sorted(_uris(expected))} with edges {sorted(_edges(expected))}"
    )


def _assert_three_way(
    handle: "FabricHandle", q: GraphQuery, *, backend: str, case_name: str
) -> tuple[GraphView, GraphView, GraphView]:
    """All three answerers render the same canonical bytes (D-05, P-2)."""
    operator_view, answered, expected = _three_views(handle, q)
    _assert_operator_tier(
        operator_view, expected, backend=backend, case_name=case_name
    )
    assert canonical_bytes(answered) == canonical_bytes(expected), (
        f"the query tier diverged from the reference on {case_name!r} under"
        f" {backend}: {backend} answered {sorted(_uris(answered))}, reference"
        f" answered {sorted(_uris(expected))}"
    )
    return operator_view, answered, expected


def _question(case_name: str, q: GraphQuery) -> str:
    """A failure label that says WHICH question diverged, not only which case.

    A red recorded by case alone cannot be re-run; the depth, the direction
    and the admission set are the whole question at the ``admitted=None``
    rows this module is about.
    """
    traverse = q.traverse
    assert traverse is not None
    admitted = (
        "all" if traverse.admitted_entity_classes is None else "restricted"
    )
    return (
        f"{case_name}/{traverse.direction}/depth-{traverse.depth_limit}"
        f"/admitted-{admitted}"
    )


def _fair(q: GraphQuery) -> bool:
    """Is this question askable of the operator tier at all?

    An operator's ``read_intent`` names no walk starting points beyond the
    seed classes and carries no ``allowed_entities`` — those are
    engine-authored segment-boundary facts (`GQ-06` at
    docs/GRAPH_QUERY_SEMANTICS.md:132). A row carrying either has no
    operator column; the substrate suite asks it of every adapter, and this
    module drops it rather than inventing an operator that could not have
    emitted it.
    """
    return (
        q.traverse is not None
        and q.seeds is None
        and q.allowed_entities is None
    )


def _traverse_at(depth: int, direction: TraversalDirection) -> TraversalSpec:
    """The all-admitted walk of the fixture's own seed classes and edge types."""
    return TraversalSpec(
        seed_entity_classes=SEED_CLASSES,
        relationship_types=RELATIONSHIP_TYPES,
        depth_limit=depth,
        admitted_entity_classes=None,
        direction=direction,
    )


def _bypass_roles(case: CorpusCase) -> tuple[str, str, str, str]:
    """``(seed, near, far, target)`` of the bypass case, read off its own claims.

    The two claimed intermediates are told apart by the edges rather than by
    position: ``near`` is what the seed reaches without crossing the
    unresolved reference, ``far`` is what reaches the target the same way. A
    figure this test asserts on is derived from the case, never written down
    beside it.
    """
    claimed = {claim.entity_uri: claim.entity_class for claim in case.entities}
    seed = next(uri for uri, cls in claimed.items() if cls == SEED_CLASS)
    target = next(uri for uri, cls in claimed.items() if cls == TARGET_CLASS)
    near = next(
        edge.object_uri
        for edge in case.relationships
        if edge.subject_uri == seed and edge.object_uri != UNRESOLVED_URI
    )
    far = next(
        edge.subject_uri
        for edge in case.relationships
        if edge.object_uri == target and edge.subject_uri != UNRESOLVED_URI
    )
    assert len({seed, near, far, target}) == 4, "the bypass has four claimed nodes"
    return seed, near, far, target


# --- the differential ---------------------------------------------------------


@given(case=unresolved_reference_cases())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=25,
)
def test_the_operator_tier_answers_byte_identical_to_the_query_tier_and_the_fallback(
    backend_name: str,
    fabric_boot: Callable[..., "FabricHandle"],
    case: CorpusCase,
) -> None:
    """The D-05 bar across TIERS, on the unresolved-reference family (P-2).

    The per-family twin of the sibling's direction and admission twins, for
    the same reason it gives: ``corpus_cases()`` hands any one family a
    handful of the draws and zero on some backend, while "the operator tier
    answers this question as the query tier does" is a per-backend claim.
    Every fair question of every drawn shape is asked three ways here.
    """
    handle = fabric_boot(backend=backend_name)
    _write_case(handle, case)
    for q in build_queries(
        case, policy_bundle_version=handle.worker.policy_bundle_version
    ):
        if not _fair(q):
            continue
        _operator_view, answered, _expected_view = _assert_three_way(
            handle, q, backend=backend_name, case_name=_question(case.name, q)
        )
        # The determinism twin, as the sibling asks it: same question, same bytes.
        assert canonical_bytes(handle.reader.query(q)) == canonical_bytes(
            answered
        )


def test_a_phantom_endpoint_consumes_no_depth_on_the_bypass(
    backend_name: str, fabric_boot: Callable[..., "FabricHandle"]
) -> None:
    """Depth is admitted hops, not persisted ones (D-07; ``D-IMPL-268``).

    On the bypass the target sits two persisted hops from the seed through
    the unresolved reference and three admitted hops around it. No
    implementation emits a per-node depth — ``GraphView`` carries
    ``tenant_id``, ``as_of``, ``entities`` and ``relationships`` and no
    fourth member, and none is added here — so the observable is the
    depth-limited reach set, which IS the depth assignment read one level at
    a time (RESEARCH § Priority 3): a walk that spent a hop on the phantom
    arrives at the target one level early, and a walk that did not cannot.

    Asserted by bytes first and restated readably second, in both
    directions, at the two depths that straddle the difference.
    """
    case = unresolved_reference_case("bypass")
    seed, near, far, target = _bypass_roles(case)
    handle = fabric_boot(backend=backend_name)
    _write_case(handle, case)
    for direction in DIRECTIONS:
        for depth in (2, 3):
            q = GraphQuery(
                tenant_id=TENANT,
                as_of=ON_BOUNDARY,
                traverse=_traverse_at(depth, direction),
            )
            views = _assert_three_way(
                handle,
                q,
                backend=backend_name,
                case_name=f"{case.name}/{direction}/depth-{depth}",
            )
            reached = {seed, near, far} if depth == 2 else {seed, near, far, target}
            crossed = {(seed, near), (near, far)}
            if depth != 2:
                crossed = crossed | {(far, target)}
            for view in views:
                assert _uris(view) == reached, (
                    f"{backend_name} {direction} depth {depth}: reached"
                    f" {sorted(_uris(view))}, expected {sorted(reached)}"
                )
                assert _edges(view) == crossed, (
                    f"{backend_name} {direction} depth {depth}: crossed"
                    f" {sorted(_edges(view))}, expected {sorted(crossed)}"
                )


def test_the_cycle_through_the_unresolved_endpoint_changes_nothing(
    backend_name: str, fabric_boot: Callable[..., "FabricHandle"]
) -> None:
    """A cycle that exists only through an unresolved reference is no cycle (D-07).

    Two fabrics, one chain and one chain-plus-``X -> A``, asked the same
    questions: every column of the cycle fabric must render the chain
    fabric's bytes, because the added edge closes a loop through a URI the
    walk cannot enter.

    Honest about its own discrimination: the shipped walk *also* answers the
    cycle as the chain (RESEARCH § Priority 1, "G2 — every row identical to
    G1 row-for-row"), because the phantom is pruned from the output either
    way. What discriminates on this assertion is plan 04's planted-placeholder
    control — a manufactured record for the unresolved URI would keep the
    ``X -> A`` edge in the cycle's answer and there is no such edge in the
    chain's. The three-way equalities inside it, by contrast, are red on the
    shipped walk exactly as on the chain: this test asks them of both
    fabrics rather than only of the pair.
    """
    chain = unresolved_reference_case("chain")
    cycle = unresolved_reference_case("cycle")
    chain_handle = fabric_boot(backend=backend_name)
    cycle_handle = fabric_boot(backend=backend_name)
    _write_case(chain_handle, chain)
    _write_case(cycle_handle, cycle)
    chain_queries = build_queries(
        chain, policy_bundle_version=chain_handle.worker.policy_bundle_version
    )
    cycle_queries = build_queries(
        cycle, policy_bundle_version=cycle_handle.worker.policy_bundle_version
    )
    for chain_query, cycle_query in zip(chain_queries, cycle_queries, strict=True):
        if not _fair(chain_query):
            continue
        assert chain_query == cycle_query, "the two shapes are asked one question"
        chain_views = _assert_three_way(
            chain_handle,
            chain_query,
            backend=backend_name,
            case_name=_question(chain.name, chain_query),
        )
        cycle_views = _assert_three_way(
            cycle_handle,
            cycle_query,
            backend=backend_name,
            case_name=_question(cycle.name, cycle_query),
        )
        for tier, on_chain, on_cycle in zip(
            ("operator tier", "query tier", "reference"),
            chain_views,
            cycle_views,
            strict=True,
        ):
            assert canonical_bytes(on_chain) == canonical_bytes(on_cycle), (
                f"the {tier} answered the cycle differently from the chain on"
                f" {backend_name}: {sorted(_uris(on_cycle))} vs"
                f" {sorted(_uris(on_chain))}"
            )


def test_a_claim_less_uri_is_not_a_walk_start_at_either_tier(
    backend_name: str, fabric_boot: Callable[..., "FabricHandle"]
) -> None:
    """One rule for anchors and for neighbors (D-06) — a CONTROL, green either way.

    Dave's Q6: *"A claim-less URI is neither a valid walk start nor an
    intermediate hop. There should not be one ontology of 'entity' for
    anchors and another for neighbors."* The anchor half already holds at
    both tiers today (RESEARCH § Priority 1, the seed-at-X rows answer the
    empty view on all six adapters), so this test is here to prove the
    conforming change CREATES no start — it is expected green before and
    after, and a red here after plan 04 would mean the fix invented an
    entity.

    Two forms of the same question: the operator-fair one seeds by CLASS
    (the unresolved URI's pool class, which on the chain and the cycle no
    claimed entity carries), and the query-tier one names the URI outright
    through ``seeds``, which no operator intent can carry (`GQ-06` at
    docs/GRAPH_QUERY_SEMANTICS.md:132) and which `GQ-11` at
    docs/GRAPH_QUERY_SEMANTICS.md:221 answers: a start naming nothing in
    scope contributes no start.
    """
    empty = _frozen_at((), (), tenant_id=TENANT, as_of=ON_BOUNDARY)
    for variant in ("chain", "cycle"):
        case = unresolved_reference_case(variant)
        handle = fabric_boot(backend=backend_name)
        _write_case(handle, case)
        for direction in DIRECTIONS:
            anchored = TraversalSpec(
                seed_entity_classes=frozenset({MID_CLASS}),
                relationship_types=RELATIONSHIP_TYPES,
                depth_limit=2,
                admitted_entity_classes=None,
                direction=direction,
            )
            by_class = GraphQuery(
                tenant_id=TENANT, as_of=ON_BOUNDARY, traverse=anchored
            )
            for view in _assert_three_way(
                handle,
                by_class,
                backend=backend_name,
                case_name=f"{case.name}/anchor-by-class/{direction}",
            ):
                assert canonical_bytes(view) == canonical_bytes(empty), (
                    f"{backend_name} started a walk at an unresolved class on"
                    f" {case.name}: {sorted(_uris(view))}"
                )
            by_uri = GraphQuery(
                tenant_id=TENANT,
                as_of=ON_BOUNDARY,
                traverse=anchored,
                seeds=frozenset({UNRESOLVED_URI}),
            )
            for view in (handle.reader.query(by_uri), _expected(handle, by_uri)):
                assert canonical_bytes(view) == canonical_bytes(empty), (
                    f"{backend_name} started a walk at the unresolved URI named"
                    f" explicitly on {case.name}: {sorted(_uris(view))}"
                )


def test_exclusion_manufactures_no_record(
    backend_name: str, fabric_boot: Callable[..., "FabricHandle"]
) -> None:
    """No tier invents an entity for the unresolved reference (D-03).

    Dave's Q3: *"Creating a synthetic entity record would manufacture
    context the source never asserted. That would be worse than the current
    divergence."* So the URI appears in no answer at any tier, and — the
    stronger statement, because an answer could omit what the store now
    holds — the graph's own history for it stays empty after every walk.
    """
    for variant in UNRESOLVED_REFERENCE_VARIANTS:
        case = unresolved_reference_case(variant)
        handle = fabric_boot(backend=backend_name)
        _write_case(handle, case)
        for q in build_queries(
            case, policy_bundle_version=handle.worker.policy_bundle_version
        ):
            if not _fair(q):
                continue
            for view in _three_views(handle, q):
                assert UNRESOLVED_URI not in _uris(view), (
                    f"{backend_name} manufactured a record for the unresolved"
                    f" reference on {case.name}: {sorted(_uris(view))}"
                )
        assert (
            handle.reader.entity_history(
                tenant_id=TENANT, entity_uri=UNRESOLVED_URI
            )
            == ()
        ), f"{backend_name} persisted a record for the unresolved reference"


def test_exclusion_is_silent(
    backend_name: str,
    fabric_boot: Callable[..., "FabricHandle"],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Exclusion is a traversal semantic, not a finding or a failure (D-04).

    Dave's Q4: *"Traversal silently excludes the unresolved endpoint from
    path formation."* So the operator run raises nothing, warns nothing,
    logs nothing from a ``ccf`` logger, and mints provenance byte-identical
    to the same operator's run over a fully claimed twin of the same graph.

    The carry ``24.8-C-01`` is DEFERRED and stays deferred here: whether the
    existence or count of excluded unresolved references should become
    completeness evidence is a separate question Dave named as a future
    carry, so no count, signal or marker is emitted or asserted by this
    module.

    Honest about its own discrimination: ``mint_provenance`` is computed
    from the operator's key, category, parameter hash and upstream alone
    (``src/ccf/operators/base.py::mint_provenance``) and never from the
    view, so the provenance equality is trivially true on the shipped walk.
    What discriminates it is plan 04's CONDITIONAL annotation control — a
    provenance member written only when an endpoint is excluded makes the
    dangling side differ from the twin while leaving the twin alone.
    """
    case = unresolved_reference_case("chain")
    twin = CorpusCase(
        name=f"{case.name}-fully-claimed-twin",
        entities=case.entities
        + (
            entity_claim(
                entity_uri=UNRESOLVED_URI,
                entity_class=MID_CLASS,
                classification=PERMITTED_CLASSIFICATION,
                observed_at=EARLY,
            ),
        ),
        relationships=case.relationships,
        query_specs=case.query_specs,
    )
    dangling_handle = fabric_boot(backend=backend_name)
    twin_handle = fabric_boot(backend=backend_name)
    _write_case(dangling_handle, case)
    _write_case(twin_handle, twin)
    for direction in DIRECTIONS:
        operator = _operator_for(_traverse_at(2, direction))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            caplog.clear()
            with caplog.at_level(logging.DEBUG):
                output = _operator_output(dangling_handle, operator, ON_BOUNDARY)
        assert caught == [], (
            f"the operator warned while excluding an unresolved reference:"
            f" {[str(entry.message) for entry in caught]}"
        )
        emitted = [
            record for record in caplog.records if record.name.split(".")[0] == "ccf"
        ]
        assert emitted == [], (
            f"the operator logged while excluding an unresolved reference:"
            f" {[record.getMessage() for record in emitted]}"
        )
        twin_output = _operator_output(twin_handle, operator, ON_BOUNDARY)
        assert canonical_bytes(output.provenance) == canonical_bytes(
            twin_output.provenance
        ), (
            "the operator's provenance differs between a graph with an"
            " unresolved reference and its fully claimed twin — exclusion is"
            " not silent"
        )


def test_the_state_universe_keeps_the_dangling_edges(
    backend_name: str, fabric_boot: Callable[..., "FabricHandle"]
) -> None:
    """Persisted state and traversal membership are different universes (D-01, P-1).

    Dave's P-1: *"An edge may legally name an unresolved endpoint; that does
    not make the endpoint traversable."* The walks must therefore leave the
    store exactly as they found it — the as-of view still holds every edge
    each shape wrote, the unresolved URI still an endpoint of the ones that
    name it. A CONTROL, green before and after the change: a "fix" that
    achieved tier agreement by dropping the edge at write time would pass
    every equality above and fail here.
    """
    for variant in UNRESOLVED_REFERENCE_VARIANTS:
        case = unresolved_reference_case(variant)
        handle = fabric_boot(backend=backend_name)
        _write_case(handle, case)
        before = handle.reader.as_of(tenant_id=TENANT, at=ON_BOUNDARY)
        for q in build_queries(
            case, policy_bundle_version=handle.worker.policy_bundle_version
        ):
            if _fair(q):
                _three_views(handle, q)
        state = handle.reader.as_of(tenant_id=TENANT, at=ON_BOUNDARY)
        # By bytes, not by count: a walk that reordered or re-stamped a record
        # would leave the counts below intact and still have moved the state.
        assert canonical_bytes(state) == canonical_bytes(before), (
            f"{backend_name} changed persisted state by answering questions"
            f" about it on {case.name}"
        )
        assert len(state.relationships) == len(case.relationships), (
            f"{backend_name} lost persisted edges on {case.name}: stored"
            f" {len(case.relationships)}, read {len(state.relationships)}"
        )
        dangling = [
            edge
            for edge in state.relationships
            if UNRESOLVED_URI
            in (edge.claim.subject_uri, edge.claim.object_uri)
        ]
        written = [
            edge
            for edge in case.relationships
            if UNRESOLVED_URI in (edge.subject_uri, edge.object_uri)
        ]
        assert len(dangling) == len(written), (
            f"{backend_name} dropped an edge naming the unresolved reference"
            f" on {case.name}"
        )
