"""Validation-gate micro-benchmarks (PERF-01; D-23).

One benchmark per validation gate — empty-operator guard, lineage strict
equality, TTL bounds (whitepaper §7.6; INV-CH7-46/47/48) — exercising the
canonical ``run_gates`` sequence on prepared candidates. Each candidate is
shaped so the gate under test is the one that renders the verdict: gate 1
sees an empty operator set; gate 2 sees a declared/resolved mismatch after
gate 1 passes; gate 3 sees an out-of-bounds TTL after gates 1 and 2 pass.

Correctness checks are on the gate *verdict value*; timing judgments
live only in ``perf/gate.py`` (D-02). ``now`` comes from
the controlplane artifact, never a clock (D-08).
"""

from __future__ import annotations

from typing import Any, NamedTuple

import pytest

from perf.conftest import register_at_composition

from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import (
    EmptyOperatorRefusal,
    LineageMismatchRefusal,
    TTLRefusal,
    run_gates,
)


class GateEnv(NamedTuple):
    """A registered product class plus a genuine engine-resolved set."""

    registry: Any
    product_class: RegisteredProductClass
    resolved: frozenset[str]
    policy_version: str


@pytest.fixture(scope="session")
def gate_env(
    fabric_1k: Any,
    engine: Any,
    full_plan: Any,
    perspective: Any,
    control: Any,
    tenant_id: str,
    boundary: Any,
) -> GateEnv:
    """One real execution supplies the engine-resolved operator set."""
    execution = engine.execute(
        plan=full_plan,
        perspective=perspective,
        tenant_id=tenant_id,
        temporal_boundary=boundary,
    )
    registry = fabric_1k.registry
    keys = control["keys"]
    policy_version, _ = registry.resolve_latest(keys["policy_bundle"])
    max_ttl_version = register_at_composition(
        registry, keys["max_ttl"], MaxTTL(seconds=control["max_ttl_seconds"])
    )
    declared_class = control["product_class"]
    product_class = register_product_class(
        registry=registry,
        schema_name=declared_class["schema_name"],
        schema_version=declared_class["schema_version"],
        ttl_anchor=declared_class["ttl_anchor"],
        assembly_mode=declared_class["assembly_mode"],
        max_ttl_key=keys["max_ttl"],
        max_ttl_version=max_ttl_version,
    )
    return GateEnv(
        registry=registry,
        product_class=product_class,
        resolved=execution.operators_invoked,
        policy_version=policy_version,
    )


def _candidate(
    gate_env: GateEnv,
    control: Any,
    tenant_id: str,
    boundary: Any,
    *,
    operators: frozenset[str],
    expires_at: Any,
) -> ContextProductContract:
    declared_class = control["product_class"]
    return ContextProductContract(
        schema_name=declared_class["schema_name"],
        schema_version=declared_class["schema_version"],
        plan_id=declared_class["plan_id"],
        tenant_id=tenant_id,
        temporal_boundary=boundary,
        expires_at=expires_at,
        ttl_anchor=gate_env.product_class.ttl_anchor,
        lineage=ProductLineage(
            operators_invoked=operators,
            policy_bundle_versions=frozenset({gate_env.policy_version}),
            graph_snapshot_at=boundary,
        ),
        payload={"entity_count": 0},
    )


def test_gate_empty_operator_guard(
    benchmark, gate_env: GateEnv, control, tenant_id, boundary, decision_now
) -> None:
    """Gate 1 verdict: a product computed by nothing is refused."""
    candidate = _candidate(
        gate_env,
        control,
        tenant_id,
        boundary,
        operators=frozenset(),
        expires_at=decision_now,
    )
    verdict = benchmark(
        run_gates,
        candidate,
        engine_resolved=gate_env.resolved,
        now=decision_now,
        registry=gate_env.registry,
        product_class=gate_env.product_class,
    )
    assert isinstance(verdict, EmptyOperatorRefusal)


def test_gate_lineage_strict_equality(
    benchmark, gate_env: GateEnv, control, tenant_id, boundary, decision_now
) -> None:
    """Gate 2 verdict: declared and engine-resolved sets must be equal."""
    declared = frozenset(sorted(gate_env.resolved)[:1])
    candidate = _candidate(
        gate_env,
        control,
        tenant_id,
        boundary,
        operators=declared,
        expires_at=decision_now,
    )
    verdict = benchmark(
        run_gates,
        candidate,
        engine_resolved=gate_env.resolved,
        now=decision_now,
        registry=gate_env.registry,
        product_class=gate_env.product_class,
    )
    assert isinstance(verdict, LineageMismatchRefusal)
    assert verdict.declared == declared
    assert verdict.resolved == gate_env.resolved


def test_gate_ttl_bounds(
    benchmark, gate_env: GateEnv, control, tenant_id, boundary, decision_now
) -> None:
    """Gate 3 verdict: gates 1 and 2 pass; an already-expired TTL refuses."""
    candidate = _candidate(
        gate_env,
        control,
        tenant_id,
        boundary,
        operators=gate_env.resolved,
        expires_at=decision_now,  # strict lower bound: expiring now is expired
    )
    verdict = benchmark(
        run_gates,
        candidate,
        engine_resolved=gate_env.resolved,
        now=decision_now,
        registry=gate_env.registry,
        product_class=gate_env.product_class,
    )
    assert isinstance(verdict, TTLRefusal)
