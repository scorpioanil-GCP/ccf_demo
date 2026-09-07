"""Composition preservation, for every shipped operator pair (FABR-02, D-14).

Whitepaper §7.4: the operator algebra's guarantee is

    (A∘B)(G) = A(B(G))

and it is the reason replay is deterministic — a fabric whose composite differs
from its sequence cannot reproduce a decision it recorded as a plan. The
assertion here is on ``canonical_bytes``, bit for bit: two views that "look
equal" but serialize differently would produce two different content addresses,
two different graph-snapshot ids, and two replays that disagree while both
claiming to agree.

**Every ordered pair, including self-pairs.** The parametrization is
``itertools.product`` over the registry, so it is ``n²`` cases and grows on its
own when an operator ships. A hand-listed pair set is a list someone forgets to
extend.

**The composite comes from production code.** ``compose()`` lives in
:mod:`ccf.operators.planner` and is what the engine's composition path is built
from; a test-local re-implementation could agree with itself while disagreeing
with the fabric. The composite is additionally run *through the intermediate
cache* while the direct application is not, so a cache-key defect (D-IMPL-36)
surfaces here as a byte difference rather than as a silent wrong answer.

**Two classes of input** (D-14): Hypothesis-generated banking-shaped states,
and the curated edge graphs — empty result, fully policy-filtered, temporal
boundary, and (since 24.8) an unresolved reference — that generation is
unlikely to hit reliably.

**One algebraic consequence the pair law cannot see.** The n² law holds under
both the shipped and the conforming traversal walk on the dangling case, so
``T(T(G)) = T(G)`` is asserted separately for each traversal shape at the end
of this module (`D-IMPL-268`, whitepaper §7.4).
"""

from __future__ import annotations

import itertools

import pytest
from hypothesis import find, given

from ccf.contracts.canonical import canonical_bytes
from ccf.graph.protocols import GraphView
from ccf.operators.base import Operator
from ccf.operators.categories import TraversalNeighborhood
from ccf.operators.params import (
    PolicyFilterParameters,
    TraversalNeighborhoodParameters,
)
from ccf.operators.planner import IntermediateCache, compose

from .strategies import (
    BOUNDARY,
    CONTROL,
    TENANT,
    CuratedGraph,
    banking_graph_states,
    curated_edge_graphs,
    shipped_operators,
)

REGISTRY = shipped_operators()
OPERATOR_KEYS = REGISTRY.keys()

#: Every ordered pair (A, B), A applied second. ``n²`` by construction.
ORDERED_PAIRS: tuple[tuple[str, str], ...] = tuple(
    itertools.product(OPERATOR_KEYS, OPERATOR_KEYS)
)

CURATED = curated_edge_graphs()

#: The Policy operator's registry key — SDK vocabulary, not a domain value.
POLICY_KEY = "policy.principal-subgraph"

#: The Traversal operator's registry key — SDK vocabulary, not a domain value.
TRAVERSAL_KEY = "traversal.typed-neighborhood"

#: Every shipped key OTHER than traversal — the partners of the admission
#: variant below. Derived from the registry, so a fifth operator joins here
#: on its own.
OTHER_KEYS: tuple[str, ...] = tuple(k for k in OPERATOR_KEYS if k != TRAVERSAL_KEY)

#: Every shipped key in the TRAVERSAL category — the two shapes today
#: (ledger row ``24.5-L-06``), derived from the registry's own category
#: assignment rather than by name, so a third shape joins the idempotence
#: test below on its own.
TRAVERSAL_KEYS: tuple[str, ...] = tuple(
    key
    for key in OPERATOR_KEYS
    if REGISTRY.registration(key).category
    == REGISTRY.registration(TRAVERSAL_KEY).category
)


def admitted_traversal() -> TraversalNeighborhood:
    """The shipped traversal with ``admitted_entity_classes`` set (ledger row ``24.5-L-05``).

    NOT registered — ``OperatorRegistry.register`` refuses a second
    ``traversal.typed-neighborhood`` (``DuplicateOperatorKey``), so the
    parameter variant is built beside the registry rather than in it.
    Admission is set to the fixture's own seed classes, so the instance
    actually filters: every hop onto a non-seed class is refused, and the
    variant differs from the registered instance on any drawn state that
    has such an edge (asserted below, so the law is not proven on an
    identity).
    """
    params = CONTROL["operator_parameters"]["traversal"]
    return TraversalNeighborhood(
        parameters=TraversalNeighborhoodParameters(
            seed_entity_classes=frozenset(params["seed_entity_classes"]),
            relationship_types=frozenset(params["relationship_types"]),
            depth_limit=params["depth_limit"],
            admitted_entity_classes=frozenset(params["seed_entity_classes"]),
        )
    )


ADMITTED_TRAVERSAL = admitted_traversal()


def _assert_composition_preserved(
    *, outer: Operator, inner: Operator, view: GraphView
) -> None:
    """Assert ``(outer∘inner)(view)`` and ``outer(inner(view))`` are the same bytes."""
    composed = compose(outer, inner, cache=IntermediateCache()).apply(
        view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    intermediate = inner.apply(
        view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    direct = outer.apply(
        view=intermediate.view,
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        upstream=(intermediate.provenance,),
    )
    assert canonical_bytes(composed) == canonical_bytes(direct)


def test_the_parametrization_covers_every_ordered_pair() -> None:
    """n² cases, derived from the registry — not from a list to maintain."""
    assert len(ORDERED_PAIRS) == len(OPERATOR_KEYS) ** 2
    assert len(OPERATOR_KEYS) == len(REGISTRY)
    assert set(ORDERED_PAIRS) == {
        (outer, inner) for outer in OPERATOR_KEYS for inner in OPERATOR_KEYS
    }


@pytest.mark.parametrize(("outer_key", "inner_key"), ORDERED_PAIRS)
@given(view=banking_graph_states())
def test_composition_is_preserved_on_generated_graphs(
    outer_key: str, inner_key: str, view: GraphView
) -> None:
    """(A∘B)(G) = A(B(G)) over Hypothesis-generated banking-shaped state."""
    _assert_composition_preserved(
        outer=REGISTRY.resolve(outer_key),
        inner=REGISTRY.resolve(inner_key),
        view=view,
    )


@pytest.mark.parametrize(("outer_key", "inner_key"), ORDERED_PAIRS)
@pytest.mark.parametrize("case", CURATED, ids=[case.name for case in CURATED])
def test_composition_is_preserved_on_curated_edge_graphs(
    outer_key: str, inner_key: str, case: CuratedGraph
) -> None:
    """The same equality on the edge cases generation is unlikely to find."""
    _assert_composition_preserved(
        outer=REGISTRY.resolve(outer_key),
        inner=REGISTRY.resolve(inner_key),
        view=case.view,
    )


@pytest.mark.parametrize("other_key", OTHER_KEYS)
@given(view=banking_graph_states())
def test_composition_is_preserved_under_admission(
    other_key: str, view: GraphView
) -> None:
    """(A∘B)(G) = A(B(G)) with ``admitted_entity_classes`` set, both orderings.

    Criterion 8 (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0): the
    n² suite's law holds for the parameterized variant against every other
    shipped operator — the variant applied second and applied first — and
    for the variant composed with itself.
    """
    other = REGISTRY.resolve(other_key)
    _assert_composition_preserved(outer=ADMITTED_TRAVERSAL, inner=other, view=view)
    _assert_composition_preserved(outer=other, inner=ADMITTED_TRAVERSAL, view=view)
    _assert_composition_preserved(
        outer=ADMITTED_TRAVERSAL, inner=ADMITTED_TRAVERSAL, view=view
    )


@pytest.mark.parametrize("other_key", OTHER_KEYS)
@pytest.mark.parametrize("case", CURATED, ids=[case.name for case in CURATED])
def test_composition_is_preserved_under_admission_on_curated_edge_graphs(
    other_key: str, case: CuratedGraph
) -> None:
    """The same equality under admission on the curated edge cases."""
    other = REGISTRY.resolve(other_key)
    _assert_composition_preserved(
        outer=ADMITTED_TRAVERSAL, inner=other, view=case.view
    )
    _assert_composition_preserved(
        outer=other, inner=ADMITTED_TRAVERSAL, view=case.view
    )


def test_the_admission_variant_actually_filters() -> None:
    """A law proven on an identity proves nothing: the variant must differ somewhere.

    ``hypothesis.find`` searches the same strategy the property runs over
    for a state on which the admitted walk reaches strictly fewer entities
    than the registered, unfiltered walk — a hop onto a non-seed class that
    admission refused. If no such state exists the variant is vacuous and
    this test fails, which is the point.
    """
    unfiltered = REGISTRY.resolve(TRAVERSAL_KEY)

    def reach(operator: Operator, view: GraphView) -> set[str]:
        output = operator.apply(
            view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
        )
        return {record.claim.entity_uri for record in output.view.entities}

    def strictly_narrower(view: GraphView) -> bool:
        admitted = reach(ADMITTED_TRAVERSAL, view)
        return admitted < reach(unfiltered, view)

    witness = find(banking_graph_states(), strictly_narrower)
    assert strictly_narrower(witness)
    assert ADMITTED_TRAVERSAL.key == TRAVERSAL_KEY
    assert ADMITTED_TRAVERSAL.parameters.admitted_entity_classes is not None


@given(view=banking_graph_states())
def test_the_generated_states_are_not_vacuous(view: GraphView) -> None:
    """A property over inputs no operator can reduce would prove nothing.

    An equality that holds because both sides are the identity is not evidence
    of composition preservation, so the harness asserts its own premise on the
    operator whose exclusion rule is total: whenever a drawn state contains a
    claim the principal is not admitted to, Policy must remove it.
    """
    policy = REGISTRY.resolve(POLICY_KEY)
    parameters = policy.parameters
    assert isinstance(parameters, PolicyFilterParameters)
    inadmissible = [
        record
        for record in view.entities
        if record.policy_bundle_version
        not in parameters.permitted_policy_bundle_versions
        or record.claim.attributes.get(
            parameters.classification_attribute_by_class[record.claim.entity_class]
        )
        not in parameters.permitted_classifications
    ]
    filtered = policy.apply(
        view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    ).view
    assert len(filtered.entities) == len(view.entities) - len(inadmissible)


def test_the_policy_filtered_graph_is_actually_emptied_by_policy() -> None:
    """The curated case earns its name: Policy removes every entity and edge."""
    case = next(item for item in CURATED if item.name == "policy-filtered")
    assert case.view.entities and case.view.relationships
    filtered = (
        REGISTRY.resolve(POLICY_KEY)
        .apply(
            view=case.view,
            tenant_id=TENANT,
            temporal_boundary=BOUNDARY,
            upstream=(),
        )
        .view
    )
    assert filtered.entities == ()
    assert filtered.relationships == ()


def test_the_curated_set_covers_the_three_named_edge_cases() -> None:
    """D-14 names three explicitly; since 24.8 the set is four.

    A fixture set that dropped one is a defect, and the assertion is a subset
    check so an ADDED case never reds it — which is why the fourth has to be
    named here rather than left to arrive on its own. ``unresolved-reference``
    (G-28, `D-IMPL-267`) is the persisted-edge-onto-an-unclaimed-endpoint
    shape; it is the state the two traversal tiers disagreed on, and the
    fixture losing it would silently retire the coverage this phase added.

    The node id is deliberately unchanged: the criteria cite it, and a
    strengthened assertion under the same id is what keeps that citation
    resolvable. It reads "three named" because D-14 named three; the fourth
    is 24.8's addition and is asserted below with the rest.
    """
    names = {case.name for case in CURATED}
    assert {
        "empty-result",
        "policy-filtered",
        "temporal-boundary",
        "unresolved-reference",
    } <= names


@pytest.mark.parametrize("key", TRAVERSAL_KEYS, ids=list(TRAVERSAL_KEYS))
def test_each_traversal_operator_is_idempotent_on_the_unresolved_reference_case(
    key: str,
) -> None:
    """``T(T(G)) = T(G)`` on the dangling case, by bytes — whitepaper §7.4.

    A traversal is a selection: applying it to its own answer must be the
    answer again, or the operator algebra's fixed point does not exist and a
    replayed two-segment plan can disagree with the one-segment plan that
    recorded it. On the shipped in-process walk this FAILS for the undirected
    neighborhood (RESEARCH F-3): the first application crosses the unclaimed
    endpoint and returns the entity beyond it, the second application sees a
    view in which the phantom route is gone and returns strictly less.

    This is coverage with a sharp edge, not the phase's discriminating
    instrument: the 25-pair composition law itself holds under either walk on
    this case (24.8-VALIDATION.md, composition row), so the proof of the
    ruled semantics is the differential and the in-process oracle module.
    What this test adds is the one algebraic consequence the pair law cannot
    see. `D-IMPL-268`.
    """
    assert len(TRAVERSAL_KEYS) == 2, (
        "the traversal category's shape roster moved; a third shape joins this"
        f" test on its own, but the count is pinned so it cannot do so"
        f" unnoticed: {TRAVERSAL_KEYS}"
    )
    case = next(item for item in CURATED if item.name == "unresolved-reference")
    # The phantom URI is read OFF the case: the edge endpoint that carries no
    # entity claim. Never a module-level literal — the fixture owns the value.
    claimed = {record.claim.entity_uri for record in case.view.entities}
    endpoints = {
        uri
        for edge in case.view.relationships
        for uri in (edge.claim.subject_uri, edge.claim.object_uri)
    }
    unresolved = endpoints - claimed
    assert len(unresolved) == 1, f"the curated case lost its dangling shape: {case.name}"
    phantom = next(iter(unresolved))

    operator = REGISTRY.resolve(key)
    once = operator.apply(
        view=case.view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    twice = operator.apply(
        view=once.view,
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        upstream=(once.provenance,),
    )
    assert phantom not in {
        record.claim.entity_uri for record in once.view.entities
    }, f"{key} emitted the unresolved endpoint"
    assert canonical_bytes(twice.view) == canonical_bytes(once.view), (
        f"{key} is not idempotent on the unresolved-reference case:"
        " the second application answers"
        f" {sorted(record.claim.entity_uri for record in twice.view.entities)}"
        " where the first answered"
        f" {sorted(record.claim.entity_uri for record in once.view.entities)}"
    )
