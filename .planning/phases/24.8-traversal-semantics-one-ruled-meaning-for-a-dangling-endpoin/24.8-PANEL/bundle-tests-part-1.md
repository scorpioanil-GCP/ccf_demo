# bundle-tests-part-1

READ-PROOF bundle-tests-part-1: a25c7016b2cddc69c5c52beb

The two NEW test modules of Phase 24.8, whole. These are the proving instruments; both were committed
RED against the shipped walk before the fix landed (wave 1) and are green on the shipped tree.

## 1. `tests/conformance/test_operator_tier_differential.py` — NEW, FULL TEXT

### `tests/conformance/test_operator_tier_differential.py`

```python
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

import importlib.util
import logging
import pathlib
import subprocess
import sys
import warnings
from collections.abc import Callable
from types import ModuleType
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

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CATEGORIES_SOURCE = REPO_ROOT / "src" / "ccf" / "operators" / "categories.py"

#: The exact line the byte-level control reverses in a COPY of the operator
#: source. ``src/ccf/operators/categories.py::_substitute`` hands the reached
#: entity records on in the input view's order; reversing that tuple yields the
#: SAME URI set and different canonical bytes, which is how this module proves
#: its own equality is byte-level rather than set-level. Asserted present
#: exactly once in the real source before any copy is mutated — the
#: ``tests/operators/test_traversal_admission.py::ADMISSION_PREDICATE``
#: discipline, so the control cannot pass vacuously against a file that never
#: carried the line.
SUBSTITUTE_ENTITIES_LINE = "        entities=entities,\n"

#: What the copy says instead. Order, and nothing else, differs.
SUBSTITUTE_REVERSED_LINE = "        entities=tuple(reversed(entities)),\n"

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


# --- the byte-level control ---------------------------------------------------


def _import_reordered_categories(tmp_path: pathlib.Path) -> ModuleType:
    """A copy of ``categories.py`` whose ``_substitute`` reverses its entities.

    Set-equal, order-different — the exact difference Dave's Q5 ruled must
    be visible. The real tree is never edited; the copy lives under
    ``tmp_path`` and is popped from ``sys.modules`` on the way out (the
    ``tests/operators/test_traversal_admission.py::_import_sabotaged_categories``
    template).
    """
    source = CATEGORIES_SOURCE.read_text(encoding="utf-8")
    assert source.count(SUBSTITUTE_ENTITIES_LINE) == 1, (
        "the substituted entity tuple is not where this control expects it;"
        " re-read src/ccf/operators/categories.py::_substitute"
    )
    reordered = source.replace(
        SUBSTITUTE_ENTITIES_LINE, SUBSTITUTE_REVERSED_LINE
    )
    assert SUBSTITUTE_REVERSED_LINE in reordered
    scratch = tmp_path / "reordered_categories_entities.py"
    scratch.write_text(reordered, encoding="utf-8")
    name = "tests_conformance_reordered_categories_entities"
    spec = importlib.util.spec_from_file_location(name, scratch)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def test_the_byte_check_is_byte_level(
    fabric_boot: Callable[..., "FabricHandle"], tmp_path: pathlib.Path
) -> None:
    """A set-equal, order-different answer must RED this module's equality (D-05, P-2).

    Dave's Q5 with its definition: *"The semantic result must first be
    identical … and then the normal canonical ordering/rendering must
    produce identical bytes."* A check that compared URI sets would call the
    reordered copy correct. This one must not — so the copy is asked a
    question every tier answers alike under the shipped walk AND under the
    conforming one (the bypass at depth 3, RESEARCH § Priority 1 row
    ``G3 und/d3``), which is what makes the red below attributable to the
    ordering and to nothing else.

    One backend only: this is a property of the CHECK, not of a substrate.
    """
    case = unresolved_reference_case("bypass")
    handle = fabric_boot(backend="sqlite")
    _write_case(handle, case)
    traverse = _traverse_at(3, "undirected")
    q = GraphQuery(tenant_id=TENANT, as_of=ON_BOUNDARY, traverse=traverse)
    expected = _expected(handle, q)

    reordered = _import_reordered_categories(tmp_path)
    scratch_operator = reordered.TraversalNeighborhood(
        parameters=TraversalNeighborhoodParameters(
            seed_entity_classes=traverse.seed_entity_classes,
            relationship_types=traverse.relationship_types,
            depth_limit=traverse.depth_limit,
            admitted_entity_classes=traverse.admitted_entity_classes,
        )
    )
    scratch_view = _operator_output(handle, scratch_operator, ON_BOUNDARY).view
    real_view = _operator_output(
        handle, _operator_for(traverse), ON_BOUNDARY
    ).view

    # (a) The two answers agree on membership — a set check would pass both.
    assert _uris(scratch_view) == _uris(real_view) == _uris(expected)
    assert _edges(scratch_view) == _edges(real_view) == _edges(expected)
    # (b) And differ in bytes, because the entity tuple is reversed.
    assert canonical_bytes(scratch_view) != canonical_bytes(real_view)
    # (c) So this module's own operator-tier equality reds on it.
    with pytest.raises(AssertionError, match="operator tier"):
        _assert_operator_tier(
            scratch_view, expected, backend="sqlite", case_name=case.name
        )


def test_no_control_edits_the_real_source_tree() -> None:
    """The control copies; it never edits and reverts. Asserted through ``git``.

    An edit-and-revert control that crashed halfway would leave the tree
    modified and this suite green, so the real file's cleanliness is read
    from ``git status --short`` and, second leg, from the unstaged diff —
    scoped to the one file the control copies, so an unrelated edit
    elsewhere under ``src/`` cannot make this go red. The
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
    assert SUBSTITUTE_ENTITIES_LINE in CATEGORIES_SOURCE.read_text(
        encoding="utf-8"
    )
```


READ-PROOF bundle-tests-part-1: a25c7016b2cddc69c5c52beb

## 2. `tests/operators/test_traversal_unresolved_reference.py` — NEW, FULL TEXT

### `tests/operators/test_traversal_unresolved_reference.py`

```python
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
```


READ-PROOF bundle-tests-part-1: a25c7016b2cddc69c5c52beb
