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
boundary — that generation is unlikely to hit reliably.
"""

from __future__ import annotations

import itertools

import pytest
from hypothesis import given

from ccf.contracts.canonical import canonical_bytes
from ccf.graph.protocols import GraphView
from ccf.operators.base import Operator
from ccf.operators.params import PolicyFilterParameters
from ccf.operators.planner import IntermediateCache, compose

from .strategies import (
    BOUNDARY,
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
    """D-14 names them explicitly; a fixture set that dropped one is a defect."""
    names = {case.name for case in CURATED}
    assert {"empty-result", "policy-filtered", "temporal-boundary"} <= names
