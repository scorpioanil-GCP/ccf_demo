"""Projection scale curve over the rung ladder (PERF-02; D-26).

Times ``ProjectionEngine.execute`` — the full four-category operator plan
from the controlplane artifact plus Π — against the session-scoped
pre-built per-rung fabrics (projection is read-only; no fresh graph
needed, and neither boot nor ingestion is inside the clock).

Explicit rounds with one warmup (Pitfall 3). Timing judgments live only
in ``perf/gate.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf.projection.engine import ExecutionResult, ProjectionEngine
from ccf.projection.plan import Perspective

from perf.suites.common import (
    PerfPlan,
    build_operator_registry,
    instant,
    load_artifact,
)
from perf.suites.scale.conftest import PROJECTION_ROUNDS, SCALE_RUNGS


@pytest.mark.parametrize("scale_fabric", SCALE_RUNGS, indirect=True)
def test_projection_scale(benchmark, scale_fabric: Any) -> None:
    control = load_artifact("controlplane.yaml")
    ontology = load_artifact("ontology.yaml")
    tenant_id = ontology["tenant_id"]
    boundary = instant(control["decision"]["temporal_boundary"])

    operators, _ = build_operator_registry(
        reader=scale_fabric.reader,
        registry=scale_fabric.registry,
        control=control,
        ontology=ontology,
    )
    engine = ProjectionEngine(reader=scale_fabric.reader, registry=operators)
    plan = PerfPlan(
        plan_id=control["product_class"]["plan_id"],
        required=operators.keys(),
    )
    perspective = Perspective(
        principal_id=control["perspective"]["principal_id"],
        role=control["perspective"]["role"],
    )

    execution = benchmark.pedantic(
        engine.execute,
        kwargs={
            "plan": plan,
            "perspective": perspective,
            "tenant_id": tenant_id,
            "temporal_boundary": boundary,
        },
        rounds=PROJECTION_ROUNDS,
        iterations=1,
        warmup_rounds=1,
    )
    assert isinstance(execution, ExecutionResult)
    assert len(execution.operators_invoked) == 4
    assert execution.projection.payload["entity_count"] >= 1
