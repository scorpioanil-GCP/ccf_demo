"""The planner imposes the order; the plan never gets to (INV-CH7-26/28).

Whitepaper §7.4. Two claims are asserted here, and both are structural rather
than incidental:

1. the built plan runs Policy → Similarity → Temporal → Traversal regardless of
   the order the projection declared its keys in, and
2. two operators of the same category run in a *stable* order — by key, not by
   declaration accident.

The operators below are deliberately inert. What is under test is the ordering
rule and the registry metadata, and an operator that also reshaped state would
let a passing test be explained by the reshaping instead.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphView
from ccf.operators.base import (
    CATEGORY_ORDER,
    Operator,
    OperatorCategory,
    OperatorOutput,
    OperatorParameters,
    OperatorProvenance,
    mint_provenance,
)
from ccf.operators.planner import IntermediateCache, build_operator_plan, compose
from ccf.operators.registry import (
    DuplicateOperatorKey,
    OperatorRegistry,
    UnregisteredOperator,
)

TENANT = "tenant-under-test"
BOUNDARY = datetime(2026, 3, 1, tzinfo=UTC)


class InertParameters(OperatorParameters):
    """A declared parameter set with a single distinguishing field."""

    label: str


class InertOperator:
    """A conforming operator that returns its input and its provenance."""

    def __init__(self, *, key: str, category: OperatorCategory, label: str) -> None:
        self._key = key
        self._category = category
        self._parameters = InertParameters(label=label)

    @property
    def key(self) -> str:
        return self._key

    @property
    def category(self) -> OperatorCategory:
        return self._category

    @property
    def parameters(self) -> InertParameters:
        return self._parameters

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        return OperatorOutput(
            view=view, provenance=mint_provenance(self, upstream=upstream)
        )


_CONFORMANCE: tuple[type[Operator], ...] = (InertOperator,)


def _view() -> GraphView:
    return GraphView(tenant_id=TENANT, as_of=BOUNDARY)


@pytest.fixture
def registry() -> OperatorRegistry:
    """Two operators in one category, one in each of the other three."""
    populated = OperatorRegistry()
    for key, category in (
        ("z.traversal", "traversal"),
        ("m.temporal", "temporal"),
        ("b.similarity", "similarity"),
        ("a.policy", "policy"),
        ("a.traversal", "traversal"),
    ):
        populated.register(
            InertOperator(key=key, category=category, label=key), version="1.0.0"
        )
    return populated


def test_the_plan_runs_categories_in_dependency_order(
    registry: OperatorRegistry,
) -> None:
    """Policy → Similarity → Temporal → Traversal, from a scrambled declaration."""
    declared = ("z.traversal", "m.temporal", "a.policy", "b.similarity", "a.traversal")
    plan = build_operator_plan(registry=registry, required_operators=declared)
    categories = tuple(operator.category for operator in plan.operators)
    assert categories == ("policy", "similarity", "temporal", "traversal", "traversal")
    assert tuple(sorted(set(categories), key=CATEGORY_ORDER.index)) == CATEGORY_ORDER


def test_intra_category_order_is_by_key_not_by_declaration(
    registry: OperatorRegistry,
) -> None:
    """Two traversal operators run in key order however they were declared."""
    forwards = build_operator_plan(
        registry=registry, required_operators=("a.traversal", "z.traversal")
    )
    backwards = build_operator_plan(
        registry=registry, required_operators=("z.traversal", "a.traversal")
    )
    assert forwards.keys() == ("a.traversal", "z.traversal")
    assert backwards.keys() == forwards.keys()


def test_a_key_declared_twice_yields_one_step(registry: OperatorRegistry) -> None:
    """An operator is a pure function; naming it twice does not run it twice."""
    plan = build_operator_plan(
        registry=registry, required_operators=("a.policy", "a.policy")
    )
    assert plan.keys() == ("a.policy",)
    assert len(plan) == 1


def test_planned_steps_carry_position_category_and_parameter_hash(
    registry: OperatorRegistry,
) -> None:
    """The declarative face of the plan is reviewable before anything runs."""
    plan = build_operator_plan(
        registry=registry, required_operators=("b.similarity", "a.policy")
    )
    steps = plan.steps()
    assert [step.position for step in steps] == [0, 1]
    assert [step.category for step in steps] == ["policy", "similarity"]
    assert steps[0].parameter_hash == content_hash(plan.operators[0].parameters)


def test_the_registry_records_category_schema_and_version(
    registry: OperatorRegistry,
) -> None:
    """Registration metadata describes the surface without instantiating it."""
    entry = registry.registration("a.policy")
    assert entry.category == "policy"
    assert entry.parameters_schema is InertParameters
    assert entry.version == "1.0.0"
    assert tuple(item.key for item in registry.by_category("traversal")) == (
        "a.traversal",
        "z.traversal",
    )
    assert registry.registrations()[0].key == "a.policy"


def test_a_duplicate_key_is_fatal_at_registration() -> None:
    """INV-CH7-29: one key, one operator, or every plan naming it is ambiguous."""
    populated = OperatorRegistry()
    populated.register(InertOperator(key="dup", category="policy", label="first"))
    with pytest.raises(DuplicateOperatorKey):
        populated.register(
            InertOperator(key="dup", category="temporal", label="second")
        )


def test_an_unregistered_key_fails_the_plan_rather_than_the_execution(
    registry: OperatorRegistry,
) -> None:
    """Planning is where a missing operator should be discovered."""
    with pytest.raises(UnregisteredOperator):
        build_operator_plan(registry=registry, required_operators=("nowhere",))


def test_the_intermediate_cache_returns_the_recomputed_value(
    registry: OperatorRegistry,
) -> None:
    """D-IMPL-36: a hit is what recomputation would produce, provenance included."""
    cache = IntermediateCache()
    operator = registry.resolve("a.policy")
    first = cache.run(
        operator,
        view=_view(),
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        upstream=(),
    )
    second = cache.run(
        operator,
        view=_view(),
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        upstream=(),
    )
    assert cache.hits == 1
    assert content_hash(second) == content_hash(first)


def test_the_cache_does_not_collapse_distinct_upstream_chains(
    registry: OperatorRegistry,
) -> None:
    """The upstream chain is part of the key, because it is part of the answer."""
    cache = IntermediateCache()
    policy = registry.resolve("a.policy")
    other = registry.resolve("m.temporal")
    seed = other.apply(
        view=_view(), tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    bare = cache.run(
        policy,
        view=_view(),
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        upstream=(),
    )
    chained = cache.run(
        policy,
        view=_view(),
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        upstream=(seed.provenance,),
    )
    assert cache.hits == 0
    assert content_hash(chained) != content_hash(bare)


def test_a_composite_is_itself_composable(registry: OperatorRegistry) -> None:
    """``compose(A, compose(B, C))`` is well-formed and names its own chain."""
    a = registry.resolve("a.policy")
    b = registry.resolve("b.similarity")
    c = registry.resolve("m.temporal")
    nested = compose(a, compose(b, c))
    assert nested.key == "a.policy∘b.similarity∘m.temporal"
    assert nested.category == "policy"
    output = nested.apply(
        view=_view(), tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    keys: list[str] = []
    node: OperatorProvenance | None = output.provenance
    while node is not None:
        keys.append(node.operator_key)
        node = node.upstream[0] if node.upstream else None
    assert keys == ["a.policy", "b.similarity", "m.temporal"]
