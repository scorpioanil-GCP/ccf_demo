"""Operator micro-benchmarks (PERF-01; D-23 representative set, D-24 pair).

One benchmark per canonical operator category over the 1k fabric's graph
view, the full four-category composed chain through the projection engine,
and the composition-preservation pair: ``(A∘B)(G)`` as one engine execution
versus ``A(B(G))`` as two direct invocations of the same operators over the
same view — the two medians are directly comparable in Phase 14's
PERFORMANCE.md.

Every assert here is a correctness sanity check, never a timing judgment —
timing judgments live only in ``perf/gate.py`` (D-02). Auto-calibration is
appropriate for these µs–ms callables (D-25).
"""

from __future__ import annotations

from typing import Any

from ccf.operators.base import Operator, OperatorOutput
from ccf.projection.engine import ExecutionResult

from perf.suites.common import PerfPlan


def _by_category(operators: Any, category: str) -> Operator:
    """Resolve the single registered operator of ``category``."""
    for key in operators.keys():
        operator = operators.resolve(key)
        if operator.category == category:
            return operator
    raise LookupError(f"no operator of category {category!r} registered")


def _bench_category(
    benchmark: Any, operator_env: Any, graph_view: Any, tenant_id: str,
    boundary: Any, category: str,
) -> None:
    operator = _by_category(operator_env.operators, category)
    output = benchmark(
        operator.apply,
        view=graph_view,
        tenant_id=tenant_id,
        temporal_boundary=boundary,
        upstream=(),
    )
    assert isinstance(output, OperatorOutput)
    assert output.view is not None
    assert output.provenance.category == category


def test_traversal_operator(
    benchmark, operator_env, graph_view, tenant_id, boundary
) -> None:
    _bench_category(
        benchmark, operator_env, graph_view, tenant_id, boundary, "traversal"
    )


def test_temporal_operator(
    benchmark, operator_env, graph_view, tenant_id, boundary
) -> None:
    _bench_category(
        benchmark, operator_env, graph_view, tenant_id, boundary, "temporal"
    )


def test_policy_operator(
    benchmark, operator_env, graph_view, tenant_id, boundary
) -> None:
    _bench_category(
        benchmark, operator_env, graph_view, tenant_id, boundary, "policy"
    )


def test_similarity_operator(
    benchmark, operator_env, graph_view, tenant_id, boundary
) -> None:
    _bench_category(
        benchmark, operator_env, graph_view, tenant_id, boundary, "similarity"
    )


def test_composed_chain(
    benchmark, engine, full_plan, perspective, tenant_id, boundary
) -> None:
    """The full four-category composition through the engine (D-23)."""
    execution = benchmark(
        engine.execute,
        plan=full_plan,
        perspective=perspective,
        tenant_id=tenant_id,
        temporal_boundary=boundary,
    )
    assert isinstance(execution, ExecutionResult)
    assert len(execution.operators_invoked) == 4
    assert execution.projection.payload["entity_count"] >= 1


def _ab_operators(operator_env: Any) -> tuple[Operator, Operator]:
    """The D-24 pair: B = policy, A = similarity (canonical adjacency)."""
    return (
        _by_category(operator_env.operators, "similarity"),
        _by_category(operator_env.operators, "policy"),
    )


def test_composed_ab(
    benchmark, engine, operator_env, control, perspective, tenant_id, boundary
) -> None:
    """``(A∘B)(G)`` — one engine execution of the two-operator plan (D-24)."""
    a, b = _ab_operators(operator_env)
    plan = PerfPlan(
        plan_id=f'{control["product_class"]["plan_id"]}.ab',
        required=(b.key, a.key),
    )
    execution = benchmark(
        engine.execute,
        plan=plan,
        perspective=perspective,
        tenant_id=tenant_id,
        temporal_boundary=boundary,
    )
    assert isinstance(execution, ExecutionResult)
    assert execution.operators_invoked == frozenset({a.key, b.key})


def test_sequential_ab(
    benchmark, operator_env, graph_view, tenant_id, boundary
) -> None:
    """``A(B(G))`` — the same A and B as two direct invocations (D-24)."""
    a, b = _ab_operators(operator_env)

    def sequential() -> OperatorOutput:
        intermediate = b.apply(
            view=graph_view,
            tenant_id=tenant_id,
            temporal_boundary=boundary,
            upstream=(),
        )
        return a.apply(
            view=intermediate.view,
            tenant_id=tenant_id,
            temporal_boundary=boundary,
            upstream=(intermediate.provenance,),
        )

    output = benchmark(sequential)
    assert isinstance(output, OperatorOutput)
    assert output.view is not None
    assert output.provenance.operator_key == a.key
